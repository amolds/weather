import network
import socket
import time
import gc
from machine import I2C, Pin
from bme280 import BME280
from bh1750 import BH1750

# --- Connect to WiFi ---
ssid = "<your-wifi>"
password = "<your-password>"

wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(ssid, password)

while not wifi.isconnected():
    time.sleep(0.1)

print("Connected:", wifi.ifconfig())

# --- Initialize sensors ONCE ---
i2c = I2C(scl=Pin(5), sda=Pin(4))
bme = BME280(i2c=i2c)
bh = BH1750(i2c)

# --- Start Web Server ---
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(addr)
s.listen(1)
s.settimeout(0.1)   # <-- prevents blocking forever

print("Listening on", addr)

while True:
    try:
        client, client_addr = s.accept()
    except OSError:
        # No client — yield to REPL
        time.sleep_ms(1)
        continue

    print("Client connected:", client_addr)

    try:
        request = client.recv(1024).decode()
        print("Request:", request)

        # Read sensors
        t, p, h = bme.read_compensated()
        l = bh.luminance()

        # Build response
        body = (
            f"BME280 Temperature: {t:.2f} C\n"
            f"BME280 Pressure: {p:.2f} Pa\n"
            f"BME280 Humidity: {h:.2f} %\n"
            f"Lux: {l}\n"
        )

        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain\r\n"
            "Connection: close\r\n"
            "\r\n" +
            body
        )

        client.send(response)

    except Exception as e:
        print("Error:", e)

    finally:
        client.close()
        gc.collect()

    # Yield again after each request
    time.sleep_ms(1)
