import time
import struct

BMP390_ADDR = 0x77

# Registers
_REG_CHIP_ID    = 0x00
_REG_STATUS     = 0x03
_REG_PRESS_MSB  = 0x06  # 0x04=LSB, 0x05=XLSB, 0x06=MSB (3 bytes from 0x04)
_REG_TEMP_MSB   = 0x09  # 0x07=LSB, 0x08=XLSB, 0x09=MSB (3 bytes from 0x07)
_REG_PWR_CTRL   = 0x1B
_REG_OSR        = 0x1C
_REG_ODR        = 0x1D
_REG_IIR        = 0x1F
_REG_CALIB      = 0x31  # 21 bytes of calibration data


class BMP390:
    ADDR = BMP390_ADDR

    def __init__(self, i2c, addr=ADDR):
        self._i2c = i2c
        self._addr = addr
        self._load_calibration()
        # Enable pressure + temperature, normal mode
        self._i2c.writeto_mem(self._addr, _REG_PWR_CTRL, bytes([0x33]))
        time.sleep_ms(20)

    def _read_reg(self, reg, length):
        return self._i2c.readfrom_mem(self._addr, reg, length)

    def _load_calibration(self):
        raw = self._read_reg(_REG_CALIB, 21)
        # Unpack calibration coefficients per datasheet
        T1, T2 = struct.unpack_from('<HH', raw, 0)
        T3,     = struct.unpack_from('<b', raw, 4)
        P1, P2  = struct.unpack_from('<hh', raw, 5)
        P3, P4  = struct.unpack_from('<bb', raw, 9)
        P5, P6  = struct.unpack_from('<HH', raw, 11)
        P7, P8  = struct.unpack_from('<bb', raw, 15)
        P9,     = struct.unpack_from('<h', raw, 17)
        P10,    = struct.unpack_from('<b', raw, 19)
        P11,    = struct.unpack_from('<b', raw, 20)

        # Convert per datasheet section 8.4
        self._T1  = T1  / 2**-8
        self._T2  = T2  / 2**30
        self._T3  = T3  / 2**48
        self._P1  = (P1 - 2**14) / 2**20
        self._P2  = (P2 - 2**14) / 2**29
        self._P3  = P3  / 2**32
        self._P4  = P4  / 2**37
        self._P5  = P5  / 2**-3
        self._P6  = P6  / 2**6
        self._P7  = P7  / 2**8
        self._P8  = P8  / 2**15
        self._P9  = P9  / 2**48
        self._P10 = P10 / 2**48
        self._P11 = P11 / 2**65

    def _compensate_temp(self, raw_temp):
        pd1 = raw_temp - self._T1
        pd2 = pd1 * self._T2
        self._t_lin = pd2 + (pd1 * pd1) * self._T3
        return self._t_lin

    def _compensate_press(self, raw_press):
        t = self._t_lin
        pd1  = self._P6 * t
        pd2  = self._P7 * t * t
        pd3  = self._P8 * t * t * t
        po1  = self._P5 + pd1 + pd2 + pd3

        pd1  = self._P2 * t
        pd2  = self._P3 * t * t
        pd3  = self._P4 * t * t * t
        po2  = raw_press * (self._P1 + pd1 + pd2 + pd3)

        pd1  = raw_press * raw_press
        pd2  = self._P9 + self._P10 * t
        pd3  = pd1 * pd2
        pd4  = pd3 + self._P11 * raw_press * raw_press * raw_press

        return po1 + po2 + pd4

    def read(self):
        data = self._read_reg(0x04, 6)
        raw_press = (data[2] << 16) | (data[1] << 8) | data[0]
        raw_temp  = (data[5] << 16) | (data[4] << 8) | data[3]

        temp_c    = self._compensate_temp(raw_temp)
        temp_f    = (temp_c * 9 / 5) + 32
        pressure  = self._compensate_press(raw_press)
        hpa       = pressure / 100.0

        return {
            "temp_c":    round(temp_c, 2),
            "temp_f":    round(temp_f, 2),
            "pressure":  round(hpa, 2),
        }
