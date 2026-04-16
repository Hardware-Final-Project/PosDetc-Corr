#Libraries
import RPi.GPIO as GPIO
import time


class Ultrasonic:
    def __init__(self):
        #GPIO Mode (BOARD / BCM)
        GPIO.setmode(GPIO.BCM)
        
        #set GPIO Pins
        self.gpio_trigger = 23
        self.gpio_echo = 24
        
        #set GPIO direction (IN / OUT)
        GPIO.setup(self.gpio_trigger, GPIO.OUT)
        GPIO.setup(self.gpio_echo, GPIO.IN)
 
    def get_distance(self):
        # set Trigger to HIGH
        GPIO.output(self.gpio_trigger, True)
    
        # set Trigger after 0.01ms to LOW
        time.sleep(0.00001)
        GPIO.output(self.gpio_trigger, False)
    
        start_time = time.time()
        stop_time = time.time()
    
        # save start_time
        while GPIO.input(self.gpio_echo) == 0:
            start_time = time.time()
    
        # save time of arrival
        while GPIO.input(self.gpio_echo) == 1:
            stop_time = time.time()
    
        # time difference between start and arrival
        time_elapsed = stop_time - start_time
        # multiply with the sonic speed (34300 cm/s)
        # and divide by 2, because there and back
        distance = (time_elapsed * 34300) / 2
    
        return distance
 
