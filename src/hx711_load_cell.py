import time
import sys
from hx711 import HX711


class HX711LoadCell:
    def __init__(self):
        self.dt_pin = 5
        self.sck_pin = 6

        self.offset = -250081.6
        self.ratio = 430.64

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

        self.ratio = 433.0 

    def get_average_raw(self, times=10):
        """相容性極強的讀取與平均計算函式"""
        try:
            data = self.hx.get_raw_data(times)
            
            if isinstance(data, list) and len(data) > 0:
                return sum(data) / len(data)
            elif isinstance(data, (int, float)):
                return data
                
        except TypeError:
            total = 0
            valid_reads = 0
            for _ in range(times):
                val = self.hx.get_raw_data()
                
                if isinstance(val, list) and len(val) > 0:
                    total += val[0]
                    valid_reads += 1
                elif isinstance(val, (int, float)):
                    total += val
                    valid_reads += 1
                time.sleep(0.05)
                
            if valid_reads > 0:
                return total / valid_reads
                
        return 0


    def get_weight(self):
        current_raw = self.get_average_raw(5)
                
        if current_raw is not None:
            weight = (current_raw - self.offset) / self.ratio
            return weight
        return None
