from machine import I2C, Pin
from sensors.bmp390 import BMP390

i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
sensor = BMP390(i2c)
data = sensor.read()

print("Temperature: {} C  /  {} F".format(data["temp_c"], data["temp_f"]))
print("Pressure:    {} hPa".format(data["pressure"]))
