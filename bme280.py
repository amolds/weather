# MicroPython BME280 driver
# Works with ESP8266/ESP32 over I2C

import time
from machine import I2C

BME280_I2CADDR = 0x76

class BME280:
    def __init__(self, i2c=None, address=BME280_I2CADDR):
        self.i2c = i2c
        self.address = address

        # Read calibration data
        dig = []
        for i in range(0x88, 0x88+24):
            dig.append(self.i2c.readfrom_mem(self.address, i, 1)[0])
        dig.append(self.i2c.readfrom_mem(self.address, 0xA1, 1)[0])
        for i in range(0xE1, 0xE1+7):
            dig.append(self.i2c.readfrom_mem(self.address, i, 1)[0])

        self.dig_T1 = dig[1] << 8 | dig[0]
        self.dig_T2 = self._signed(dig[3] << 8 | dig[2])
        self.dig_T3 = self._signed(dig[5] << 8 | dig[4])

        self.dig_P1 = dig[7] << 8 | dig[6]
        self.dig_P2 = self._signed(dig[9] << 8 | dig[8])
        self.dig_P3 = self._signed(dig[11] << 8 | dig[10])
        self.dig_P4 = self._signed(dig[13] << 8 | dig[12])
        self.dig_P5 = self._signed(dig[15] << 8 | dig[14])
        self.dig_P6 = self._signed(dig[17] << 8 | dig[16])
        self.dig_P7 = self._signed(dig[19] << 8 | dig[18])
        self.dig_P8 = self._signed(dig[21] << 8 | dig[20])
        self.dig_P9 = self._signed(dig[23] << 8 | dig[22])

        self.dig_H1 = dig[24]
        self.dig_H2 = self._signed(dig[26] << 8 | dig[25])
        self.dig_H3 = dig[27]
        e4 = dig[28]
        e5 = dig[29]
        e6 = dig[30]
        self.dig_H4 = self._signed((e4 << 4) | (e5 & 0x0F))
        self.dig_H5 = self._signed((e6 << 4) | (e5 >> 4))
        self.dig_H6 = self._signed(dig[31])

        # Set oversampling and mode
        self.i2c.writeto_mem(self.address, 0xF2, b'\x01')  # humidity oversampling x1
        self.i2c.writeto_mem(self.address, 0xF4, b'\x27')  # temp/press oversampling x1, normal mode
        self.i2c.writeto_mem(self.address, 0xF5, b'\xA0')  # config

    def _signed(self, n):
        return n - 65536 if n > 32767 else n

    def read_raw(self):
        data = self.i2c.readfrom_mem(self.address, 0xF7, 8)
        pres = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
        temp = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
        hum  = (data[6] << 8) | data[7]
        return temp, pres, hum

    def read_compensated(self):
        temp_raw, pres_raw, hum_raw = self.read_raw()

        # Temperature compensation
        var1 = (temp_raw/16384.0 - self.dig_T1/1024.0) * self.dig_T2
        var2 = ((temp_raw/131072.0 - self.dig_T1/8192.0) ** 2) * self.dig_T3
        t_fine = var1 + var2
        temperature = t_fine / 5120.0

        # Pressure compensation
        var1 = t_fine/2.0 - 64000.0
        var2 = var1 * var1 * self.dig_P6 / 32768.0
        var2 = var2 + var1 * self.dig_P5 * 2.0
        var2 = var2/4.0 + self.dig_P4 * 65536.0
        var1 = (self.dig_P3 * var1 * var1 / 524288.0 + self.dig_P2 * var1) / 524288.0
        var1 = (1.0 + var1/32768.0) * self.dig_P1
        if var1 == 0:
            pressure = 0
        else:
            pressure = 1048576.0 - pres_raw
            pressure = (pressure - var2/4096.0) * 6250.0 / var1
            var1 = self.dig_P9 * pressure * pressure / 2147483648.0
            var2 = pressure * self.dig_P8 / 32768.0
            pressure = pressure + (var1 + var2 + self.dig_P7) / 16.0

        # Humidity compensation
        h = t_fine - 76800.0
        h = (hum_raw - (self.dig_H4 * 64.0 + self.dig_H5 / 16384.0 * h)) * \
            (self.dig_H2 / 65536.0 * (1.0 + self.dig_H6 / 67108864.0 * h * (1.0 + self.dig_H3 / 67108864.0 * h)))
        h = max(0, min(h, 100))

        return temperature, pressure, h
