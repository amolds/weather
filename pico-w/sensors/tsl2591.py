import time

# Gain and integration time options
GAIN_LOW    = 0x00   #   1x
GAIN_MED    = 0x10   #  25x
GAIN_HIGH   = 0x20   # 428x
GAIN_MAX    = 0x30   # 9876x

INTEGTIME_100MS = 0x00
INTEGTIME_200MS = 0x01
INTEGTIME_300MS = 0x02
INTEGTIME_400MS = 0x03
INTEGTIME_500MS = 0x04
INTEGTIME_600MS = 0x05

# Lux calculation coefficients (from Adafruit datasheet)
_LUX_DF   = 408.0
_LUX_COEFB = 1.64
_LUX_COEFC = 0.59
_LUX_COEFD = 0.86

_COMMAND_BIT  = 0xA0
_REG_ENABLE   = 0x00
_REG_CONTROL  = 0x01
_REG_CHAN0_L  = 0x14
_REG_CHAN1_L  = 0x16

_ENABLE_POWERON = 0x01
_ENABLE_AEN     = 0x02


class TSL2591:
    ADDR = 0x29

    def __init__(self, i2c, addr=ADDR, gain=GAIN_MED, integration=INTEGTIME_100MS):
        self._i2c = i2c
        self._addr = addr
        self._gain = gain
        self._integration = integration
        self._enable()
        self._set_control()

    def _enable(self):
        self._i2c.writeto_mem(
            self._addr,
            _COMMAND_BIT | _REG_ENABLE,
            bytes([_ENABLE_POWERON | _ENABLE_AEN])
        )

    def _set_control(self):
        self._i2c.writeto_mem(
            self._addr,
            _COMMAND_BIT | _REG_CONTROL,
            bytes([self._gain | self._integration])
        )
        # Wait for integration to complete
        delay_ms = (self._integration + 1) * 120
        time.sleep_ms(delay_ms)

    def _raw(self):
        ch0 = self._i2c.readfrom_mem(self._addr, _COMMAND_BIT | 0x20 | _REG_CHAN0_L, 2)
        ch1 = self._i2c.readfrom_mem(self._addr, _COMMAND_BIT | 0x20 | _REG_CHAN1_L, 2)
        full = (ch0[1] << 8) | ch0[0]
        ir   = (ch1[1] << 8) | ch1[0]
        return full, ir

    def read(self):
        full, ir = self._raw()
        visible = full - ir

        # Avoid division by zero or overflow
        if full == 0 or full == 65535 or ir == 65535:
            lux = 0.0
        else:
            again = {GAIN_LOW: 1, GAIN_MED: 25, GAIN_HIGH: 428, GAIN_MAX: 9876}.get(self._gain, 1)
            atime = (self._integration + 1) * 100
            cpl = (atime * again) / _LUX_DF
            lux = (full - (_LUX_COEFB * ir)) / cpl
            lux = max(lux, 0.0)

        return {
            "full": full,
            "ir": ir,
            "visible": visible,
            "lux": round(lux, 2),
        }
