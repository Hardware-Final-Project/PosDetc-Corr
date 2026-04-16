import time
import sys
import RPi.GPIO as GPIO
from hx711 import HX711


class HX711LoadCell:
    def __init__(self):
        self.dt_pin = 5
        self.sck_pin = 6

        self.offset = -250081.6
        self.ratio = 430.64


        # 建立 HX711 物件
        try:
            self.hx = HX711(self.dt_pin, self.sck_pin)
        except Exception as e:
            print(f"初始化失敗，請檢查接線與模組: {e}")
            sys.exit()
    
    def config_hx711(self):
        print("="*30)
        print("   HX711 智慧校正與測重系統   ")
        print("="*30)
        
        # ---------------- 步驟 1：歸零 ----------------
        print("\n[步驟 1] 請【清空秤盤】，準備進行歸零...")
        time.sleep(2) 
        
        print("正在計算歸零基準點 (Offset)...")
        self.offset = self.get_average_raw(15)
        print(f"✅ 歸零完成！基準點 (Offset) = {self.offset:.1f}")
        
        # ---------------- 步驟 2：校正 ----------------
        # print("\n[步驟 2] 開始校正比例")
        # print("請將一個【已知重量】的物品放到秤上 (例如一瓶 600g 的水)。")
        
        # user_input = input("請輸入該物品的真實重量 (例如輸入 600，直接按 Enter 略過校正): ")
        
        # if user_input.strip() == "":
        #     self.ratio = 1.0
        #     print("⚠ 略過校正，將顯示原始差距數值。")
        # else:
        #     known_weight = float(user_input)
        #     print("讀取物品數值中，請勿觸碰秤盤...")
        #     time.sleep(2) 
            
        #     raw_val = self.get_average_raw(15)
        #     self.ratio = (raw_val - self.offset) / known_weight
        #     print(f"✅ 校正完成！計算出的比例 (Ratio) = {self.ratio:.2f}")
    
        # Directly set the ratio
        self.ratio = 433.0 

    def get_average_raw(self, times=10):
        """相容性極強的讀取與平均計算函式"""
        try:
            # 嘗試直接傳入數字，不寫參數名稱 (解決 TypeError)
            data = self.hx.get_raw_data(times)
            
            # 處理回傳結果 (有些版本回傳 list，有些直接回傳數值)
            if isinstance(data, list) and len(data) > 0:
                return sum(data) / len(data)
            elif isinstance(data, (int, float)):
                return data
                
        except TypeError:
            # 如果這個版本連數字都不給傳，我們就手動用迴圈讀取！
            total = 0
            valid_reads = 0
            for _ in range(times):
                val = self.hx.get_raw_data() # 什麼參數都不帶
                
                if isinstance(val, list) and len(val) > 0:
                    total += val[0]
                    valid_reads += 1
                elif isinstance(val, (int, float)):
                    total += val
                    valid_reads += 1
                time.sleep(0.05) # 短暫延遲避免感測器來不及反應
                
            if valid_reads > 0:
                return total / valid_reads
                
        return 0


    def get_weight(self):
        current_raw = self.get_average_raw(5)
                
        if current_raw is not None:
            weight = (current_raw - self.offset) / self.ratio
            return weight
        return None
