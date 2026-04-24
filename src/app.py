import cv2
import mediapipe as mp
import math
import time
import os
import threading
import collections
from flask import Flask, render_template, Response
from hx711_load_cell import HX711LoadCell
from ssd1306_display import OLED
from ultrasonic import Ultrasonic
from audio import gTTS_audio
from data import ThreadData
import RPi.GPIO as GPIO
import warnings
import logging

# Disable warning
warnings.filterwarnings("ignore", category=UserWarning, module='gtts')
logging.getLogger('gtts').setLevel(logging.ERROR)

class MovingAverage:
    def __init__(self, max_len):
        self.queue = collections.deque(maxlen=max_len)
    
    def next(self, val):
        self.queue.append(val)
        return sum(self.queue) / len(self.queue)
    
    def reset(self, val):
        for _ in range(self.queue.maxlen):
            self.queue.append(val)
        return val

app = Flask(__name__)

# 全域變數用於存儲處理後的影像與鎖定機制
output_frame = None
lock = threading.Lock()

BAD_ANGLE = 28.0

# init thread shared data
shared_data = ThreadData()
hx711_init_event = threading.Event()
press_button_place_cup_event = threading.Event()

# camera device
#cam_device = "http://admin:admin@192.168.208.49:8081/video"
cam_device = 0

# --- 初始化 MediaPipe ---
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    model_complexity=0, # 針對 RPi 3B+ 必須使用 Lite 模型
    min_detection_confidence=0.5, 
    min_tracking_confidence=0.5
)


# init classes
def process_oled():
    _oled = OLED()
    _oled.update_display(
        line1="Please init the hx711."
    )
    hx711_init_event.wait()
    _oled.clean_display()

    _oled.update_display(line1="Please press button" , line2="and place an empty cup")
    press_button_place_cup_event.wait()
    _oled.clean_display()

    while True:
        _oled.update_display(
            line1=f"Weight: {shared_data.weight:.2f}, Angle: {shared_data.angle:.2f}",
            line2=f"Distance: {shared_data.distance:.2f}"
        )

        time.sleep(0.1)
        

def process_hx711():
    _hx711 = HX711LoadCell()
    _hx711.config_hx711()
    hx711_init_event.set()
    # Get the empty weight of the cup
    
    # Button init
    GPIO.setmode(GPIO.BCM)
    BUTTON_PIN = 7
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    while True:
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:
            break

    shared_data.empty_weight = _hx711.get_weight()
    print(f"The empty weight: {shared_data.empty_weight}")
    press_button_place_cup_event.set()

    weight_ma = MovingAverage(5)

    while True:
        weight = _hx711.get_weight()
        if weight:
            if abs(weight - shared_data.weight) > 50:
                shared_data.weight = weight_ma.reset(weight)
            else:
                shared_data.weight = weight_ma.next(weight)
        
        time.sleep(1)

def process_ultrasonic():
    hx711_init_event.wait()
    press_button_place_cup_event.wait()

    distance_ma = MovingAverage(5)

    _ultrasonic = Ultrasonic()
    while True:
        distance = _ultrasonic.get_distance()
        # print(f"Distance: {distance:.2f}")
        shared_data.distance = distance_ma.next(distance)
        time.sleep(1)

def process_call_tts():
    hx711_init_event.wait()
    press_button_place_cup_event.wait()
    
    while True:
        output_str = ""
        empty_weight = shared_data.empty_weight
        if (empty_weight - 100) < shared_data.weight < (empty_weight - 5):
            if len(output_str) != 0: output_str += "，"
            output_str += "請儘快加水"
        if shared_data.angle > BAD_ANGLE:
            if len(output_str) != 0: output_str += "，"
            output_str += "請坐直"
        if shared_data.distance < 35.0:
            if len(output_str) != 0: output_str += "，"
            output_str += "請離螢幕遠點"
        
        if len(output_str) > 0:
            print(output_str)
            filename = 'temp.mp3'
            gTTS_audio(output_str, filename)
            os.system(f"mpg123 -q {filename}")
            os.system(f"rm {filename}")
            time.sleep(3)


def calculate_neck_angle(ear, shoulder):
    x1, y1 = ear.x, ear.y
    x2, y2 = shoulder.x, shoulder.y
    radians = math.atan2(abs(x1 - x2), abs(y1 - y2))
    return math.degrees(radians)

def process_pose():
    hx711_init_event.wait()
    global output_frame, lock, cam_device
    # 0 代表板載相機或 USB 相機，如果是 IP Cam 請換成 URL
    cap = cv2.VideoCapture(cam_device) 
    
    # 設定解析度降低 RPi 負擔 (建議 320x240)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
    #cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 限制 Buffer 只有 1，確保總是讀到最新畫面

    angle_ma = MovingAverage(15)

    while cap.isOpened():
        for _ in range(0, 5):
            cap.grab()

        success, frame = cap.read()
        if not success:
            break

        # 1. 轉顏色進行偵測
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb_frame)

        # 2. 在畫面上繪製結果
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            ear = landmarks[7]
            shoulder = landmarks[11]
            
            if ear.visibility > 0.5 and shoulder.visibility > 0.5:
                angle = calculate_neck_angle(ear, shoulder)
                avg_angle = shared_data.angle = angle_ma.next(angle)

                status = "BAD" if avg_angle > BAD_ANGLE else "GOOD"
                color = (0, 0, 255) if status == "BAD" else (0, 255, 0)
                
                # 繪製文字到影像上
                cv2.putText(frame, f"{status} ({avg_angle:.1f})", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                
                # 畫出關鍵點 (可選)
                h, w, _ = frame.shape
                cv2.circle(frame, (int(ear.x*w), int(ear.y*h)), 5, color, -1)
                cv2.circle(frame, (int(shoulder.x*w), int(shoulder.y*h)), 5, color, -1)

        # 3. 更新全域影像供 Flask 使用
        with lock:
            output_frame = frame.copy()

        time.sleep(0.1)

    cap.release()

def generate():
    global output_frame, lock
    while True:
        with lock:
            if output_frame is None:
                continue
            # 將影像編碼為 JPG 格式
            (flag, encodedImage) = cv2.imencode(".jpg", output_frame)
            if not flag:
                continue
        
        # 產生串流格式
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
              bytearray(encodedImage) + b'\r\n')

@app.route("/")
def index():
    return "<h1>RPi Pose Monitor</h1><img src='/video_feed' width='640'>"

@app.route("/video_feed")
def video_feed():
    return Response(generate(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    t_weight = threading.Thread(target=process_hx711)
    t_weight.daemon = True
    t_weight.start()

    t_pose = threading.Thread(target=process_pose)
    t_pose.daemon = True
    t_pose.start()

    t_oled = threading.Thread(target=process_oled)
    t_oled.daemon = True
    t_oled.start()

    t_ultrasonic = threading.Thread(target=process_ultrasonic)
    t_ultrasonic.daemon = True
    t_ultrasonic.start()

    t_tts = threading.Thread(target=process_call_tts)
    t_tts.daemon = True
    t_tts.start()
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
