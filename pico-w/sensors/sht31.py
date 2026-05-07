import time


class SHT31:
    ADDR = 0x44

    def __init__(self, i2c, addr=ADDR):
        self._i2c = i2c
        self._addr = addr

    def read(self):
        self._i2c.writeto(self._addr, bytes([0x24, 0x00]))
        time.sleep_ms(20)
        data = self._i2c.readfrom(self._addr, 6)

        raw_temp = (data[0] << 8) | data[1]
        raw_hum  = (data[3] << 8) | data[4]

        temp_c = -45 + (175 * raw_temp / 65535)
        temp_f = (temp_c * 9 / 5) + 32
        humidity = 100 * raw_hum / 65535

        return {
            "temp_c": round(temp_c, 2),
            "temp_f": round(temp_f, 2),
            "humidity": round(humidity, 2),
        }
