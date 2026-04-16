import threading


class ThreadData:
    def __init__(self):
        # weight
        self.weight = 0.0
        # self.weight_lock = threading.Lock()
    
        # posture angle
        self.angle = 0.0
        # self.angle_lock = threading.Lock()

        # ultrasonic
        self.distance = 0.0
        # self.distance_lock = threading.Lock()
