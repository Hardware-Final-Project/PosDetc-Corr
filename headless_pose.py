import cv2
import mediapipe as mp
import time
import math


# 初始化 MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    model_complexity=0, 
    min_detection_confidence=0.5, 
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils

# 填入你手機 IP Cam 的網址
url = "http://192.168.0.236:8080/video" 

cap = cv2.VideoCapture(url)

print("正在連線至手機攝影機 (無頭模式)...")
print("提示：按下 Ctrl+C 可以停止程式")

saved_first_image = False


def calculate_neck_angle(ear_landmark, shoulder_landmark):
    """
    計算耳朵與肩膀連線與垂直線的夾角
    ear_landmark, shoulder_landmark 為 mediapipe 的 landmark 物件
    """
    # 取得座標 (注意：MediaPipe 的 y 座標是向下增長的)
    x1, y1 = ear_landmark.x, ear_landmark.y
    x2, y2 = shoulder_landmark.x, shoulder_landmark.y

    # 計算弧度 (使用 atan2 處理座標差)
    # 我們想算的是跟垂直線的夾角，所以 dx 放前面
    radians = math.atan2(abs(x1 - x2), abs(y1 - y2))
    
    # 轉為角度
    angle = math.degrees(radians)
    return angle



try:
    while cap.isOpened():
        # --- 核心修改：清空緩衝區，只拿「最新」的一張圖 ---
        # 連續讀取直到緩衝區空了，最後留下的就是當下的影像
        for _ in range(10): # 根據延遲程度，可以嘗試抓掉 5-10 張舊圖
            cap.grab() 
        
        success, image = cap.read() # 拿到最後一張最新的
        
        if not success:
            break

        # 1. 效能優化：如果是在 PC 上測試，解析度可以大一點；RPi 則維持小解析度
        image = cv2.resize(image, (640, 360))
        
        # 2. 轉換顏色並偵測
        image.flags.writeable = False
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = pose.process(image)

        # 3. 轉回 BGR
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # 4. 處理偵測結果
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            ear = landmarks[7]
            shoulder = landmarks[11]
            
            if ear.visibility > 0.5 and shoulder.visibility > 0.5:
                angle = calculate_neck_angle(ear, shoulder)
                
                # 輸出當下狀態
                status = "⚠️ BAD" if angle > 25 else "✅ GOOD"
                print(f"{status} | Angle: {angle:.2f}° (最新影格)", end='\r')

        # --- 移除 time.sleep(0.5) ---
        # 在 PC 上測試不需要 sleep。
        # 如果在 RPi 上怕過熱，改用 cv2.waitKey(1) 稍微緩衝幾毫秒即可。
        cv2.waitKey(1)
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     break

except KeyboardInterrupt:
    print("\n停止偵測。")

finally:
    cap.release()
    print("資源已釋放。")
