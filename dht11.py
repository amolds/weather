import time
import dht
from machine import Pin

class DHT11:
    def __init__(self, pin_number):
        self.sensor = dht.DHT11(Pin(pin_number))

    def read(self):
        """Returns a tuple: (temperature_c, humidity_percent)"""
        try:
            self.sensor.measure()
            temp = self.sensor.temperature()
            hum = self.sensor.humidity()
            return temp, hum
        except Exception as e:
            print("DHT11 read error:", e)
            return None, None

    def read_formatted(self):
        """Returns a formatted string for printing."""
        temp, hum = self.read()
        if temp is None:
            return "Sensor error"
        return f"Temperature: {temp} C | Humidity: {hum} %"
