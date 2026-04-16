import RPi.GPIO as GPIO
import time 
import board
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306


class OLED:
    def __init__(self):
        # Create a permanent image buffer and drawing object
        self.i2c = board.I2C()
        self.disp = adafruit_ssd1306.SSD1306_I2C(128, 32, self.i2c)
        self.width = self.disp.width
        self.height = self.disp.height
        self.image = Image.new('1', (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)
        self.font = ImageFont.load_default()


    def update_display(self, line1, line2=""):
        # 1. Clear the DRAWING BUFFER (not the physical screen)
        # This prevents the "flicker" because the pixels only change when .show() is called
        self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
    
        # 2. Draw the new text into the buffer
        self.draw.text((0, 0), line1, font=self.font, fill=255)
        if line2:
            self.draw.text((0, 16), line2, font=self.font, fill=255)

        # 3. Push the buffer to the screen all at once
        self.disp.image(self.image)
        self.disp.show()
    
    def clean_display(self):
        self.disp.fill(0)
        self.disp.show()