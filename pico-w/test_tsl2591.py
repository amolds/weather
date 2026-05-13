from machine import I2C, Pin
from sensors.tsl2591 import TSL2591

i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
sensor = TSL2591(i2c)
data = sensor.read()

print("Full spectrum: {}".format(data["full"]))
print("IR:            {}".format(data["ir"]))
print("Visible:       {}".format(data["visible"]))
print("Lux:           {}".format(data["lux"]))
