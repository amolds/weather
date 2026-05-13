# bh1750.py
import time

class BH1750:
    PWR_ON  = 0x01
    RESET   = 0x07
    CONT_HIRES_1 = 0x10  # 1 lx resolution, 120ms

    def __init__(self, i2c, addr=0x23):
        self.i2c = i2c
        self.addr = addr
        self.i2c.writeto(self.addr, bytes([self.PWR_ON]))
        time.sleep_ms(10)

    def luminance(self, mode=CONT_HIRES_1):
        self.i2c.writeto(self.addr, bytes([mode]))
        time.sleep_ms(180)  # allow measurement
        data = self.i2c.readfrom(self.addr, 2)
        raw = (data[0] << 8) | data[1]
        return raw / 1.2  # convert to lux
