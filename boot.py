import network
import socket
import time
import gc
import json
from machine import I2C, Pin
from bme280 import BME280
from bh1750 import BH1750

# --- Configuration ---
ssid = "<ssid>"
password = "<password>"
DEBUG = True

# WiFi reconnection settings
WIFI_RECONNECT_DELAY = 30  # seconds between reconnection attempts
WIFI_MAX_RECONNECT_ATTEMPTS = 3  # Recreate WiFi object after this many failures
last_wifi_check = 0
wifi_reconnect_attempts = 0

# Memory management
GC_EVERY_N_REQUESTS = 10  # Collect garbage every 10 requests
request_count = 0

# --- Connect to WiFi ---
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(ssid, password)

start = time.time()
while not wifi.isconnected():
    if time.time() - start > 15:
        print("WiFi connection failed")
        break
    time.sleep(0.5)

print("Connected:", wifi.ifconfig())

# --- Start Web Server ---
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(addr)
s.listen(1)
s.settimeout(1)  # 1 second timeout on accept()
print("Listening on", addr)

while True:
    # Check WiFi connection with backoff and object recreation
    now = time.time()
    if not wifi.isconnected() and (now - last_wifi_check) > WIFI_RECONNECT_DELAY:
        if DEBUG:
            print("WiFi lost, attempting reconnection...")
        
        # If we've failed too many times, recreate the WiFi object
        if wifi_reconnect_attempts >= WIFI_MAX_RECONNECT_ATTEMPTS:
            if DEBUG:
                print("Too many reconnection failures, recreating WiFi object")
            wifi = network.WLAN(network.STA_IF)
            wifi.active(True)
            wifi_reconnect_attempts = 0
        
        wifi.connect(ssid, password)
        last_wifi_check = now
        wifi_reconnect_attempts += 1
        
        # Wait a bit for connection to establish
        time.sleep(5)
        if wifi.isconnected():
            if DEBUG:
                print("WiFi reconnected:", wifi.ifconfig())
            wifi_reconnect_attempts = 0  # Reset counter on success
        else:
            if DEBUG:
                print("WiFi reconnection failed ({0}/{1}), will retry in {2} seconds".format(
                    wifi_reconnect_attempts, WIFI_MAX_RECONNECT_ATTEMPTS, WIFI_RECONNECT_DELAY))

    client = None
    try:
        try:
            client, client_addr = s.accept()
        except OSError:
            # Timeout waiting for connection - continue loop
            gc.collect()
            time.sleep_ms(50)
            continue

        # Set timeout on client socket
        client.settimeout(2)

        try:
            request = client.recv(1024)
        except OSError:
            # Timeout reading request
            if DEBUG:
                print("Request timeout")
            continue

        # Check for empty request
        if not request:
            if DEBUG:
                print("Empty request")
            continue

        try:
            request = request.decode()
        except Exception as e:
            if DEBUG:
                print("Decode error:", e)
            continue

        if DEBUG:
            print("Request:", request[:50])

        # Initialize sensors for this request
        bme = None
        bh = None
        try:
            i2c = I2C(scl=Pin(5), sda=Pin(4))
            bme = BME280(i2c=i2c)
            bh = BH1750(i2c)
        except Exception as e:
            if DEBUG:
                print("Sensor init error:", e)

        # Read sensors with timeout protection
        t, p, h, l = None, None, None, None
        
        if bme is not None:
            try:
                start_sensor = time.time()
                t, p, h = bme.read_compensated()
                elapsed = time.time() - start_sensor
                if DEBUG and elapsed > 1:
                    print("BME280 slow read: {0:.2f}s".format(elapsed))
            except Exception as e:
                if DEBUG:
                    print("BME280 error:", e)

        if bh is not None:
            try:
                start_sensor = time.time()
                l = bh.luminance()
                elapsed = time.time() - start_sensor
                if DEBUG and elapsed > 1:
                    print("BH1750 slow read: {0:.2f}s".format(elapsed))
            except Exception as e:
                if DEBUG:
                    print("BH1750 error:", e)

        # Build response
        if t is not None and p is not None and h is not None and l is not None:
            data = {
                "temperature_c": t,
                "pressure_pa": p,
                "humidity_pct": h,
                "lux": l,
                "uptime_seconds": int(time.time()),
                "memory_free_bytes": gc.mem_free(),
                "memory_allocated_bytes": gc.mem_alloc()
            }
            body = json.dumps(data)
            http_status = "HTTP/1.1 200 OK"
        else:
            data = {
                "error": "Sensor read error",
                "uptime_seconds": int(time.time()),
                "memory_free_bytes": gc.mem_free(),
                "memory_allocated_bytes": gc.mem_alloc()
            }
            body = json.dumps(data)
            http_status = "HTTP/1.1 503 Service Unavailable"

        response = (
            http_status + "\r\n"
            + "Content-Type: application/json\r\n"
            + "Connection: close\r\n"
            + "Content-Length: {0}\r\n".format(len(body))
            + "\r\n"
            + body
        )

        try:
            client.send(response.encode())
        except Exception as e:
            if DEBUG:
                print("Send error:", e)

    except Exception as e:
        if DEBUG:
            print("Unexpected error:", e)

    finally:
        if client:
            try:
                client.close()
            except Exception:
                pass
        
        # Collect garbage periodically to avoid GC pauses on every request
        request_count += 1
        if request_count >= GC_EVERY_N_REQUESTS:
            gc.collect()
            request_count = 0
