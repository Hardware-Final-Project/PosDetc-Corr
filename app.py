import cv2
import mediapipe as mp
import math
import time
import threading
from flask import Flask, render_template, Response
from hx711_load_cell import HX711LoadCell
from ssd1306_display import OLED
from ultrasonic import Ultrasonic
from data import ThreadData


app = Flask(__name__)
# 全域變數用於存儲處理後的影像與鎖定機制
output_frame = None
lock = threading.Lock()
# init thread shared data
shared_data = ThreadData()
hx711_init_event = threading.Event()


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

    while True:
        _oled.update_display(
            line1=f"Weight: {shared_data.weight:.2f}, Angle: {shared_data.angle:.2f}",
            line2=f"Distance: {shared_data.distance:.2f}"
        )
        

def process_hx711():
    _hx711 = HX711LoadCell()
    _hx711.config_hx711()
    hx711_init_event.set()
    while True:
        weight = _hx711.get_weight()
        if weight:
            shared_data.weight = weight 

def process_ultrasonic():
    hx711_init_event.wait()
    _ultrasonic = Ultrasonic()
    while True:
        distance = _ultrasonic.get_distance()
        # print(f"Distance: {distance:.2f}")
        shared_data.distance = distance
        time.sleep(0.1)

def calculate_neck_angle(ear, shoulder):
    x1, y1 = ear.x, ear.y
    x2, y2 = shoulder.x, shoulder.y
    radians = math.atan2(abs(x1 - x2), abs(y1 - y2))
    return math.degrees(radians)

def process_pose():
    hx711_init_event.wait()
    global output_frame, lock
    # 0 代表板載相機或 USB 相機，如果是 IP Cam 請換成 URL
    cap = cv2.VideoCapture(0) 
    
    # 設定解析度降低 RPi 負擔 (建議 320x240)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)

    while cap.isOpened():
        for _ in range(10): # 根據延遲程度，可以嘗試抓掉 5-10 張舊圖
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
                shared_data.angle = angle
                status = "BAD" if angle > 25 else "GOOD"
                color = (0, 0, 255) if status == "BAD" else (0, 255, 0)
                
                # 繪製文字到影像上
                cv2.putText(frame, f"{status} ({angle:.1f})", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                
                # 畫出關鍵點 (可選)
                h, w, _ = frame.shape
                cv2.circle(frame, (int(ear.x*w), int(ear.y*h)), 5, color, -1)
                cv2.circle(frame, (int(shoulder.x*w), int(shoulder.y*h)), 5, color, -1)

        # 3. 更新全域影像供 Flask 使用
        with lock:
            output_frame = frame.copy()

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

    
    # 啟動 Flask (host='0.0.0.0' 允許區域網路訪問)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)