from machine import I2C, Pin
from sensors.sht31 import SHT31

i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
sensor = SHT31(i2c)
data = sensor.read()

print("Temperature: {} C  /  {} F".format(data["temp_c"], data["temp_f"]))
print("Humidity:    {} %".format(data["humidity"]))
