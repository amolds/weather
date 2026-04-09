import network
import socket
import time
import gc
import machine
import sys
import io
from bme280 import BME280
from bh1750 import BH1750

# --- Configuration ---
ssid = "<ssid>"
password = "<pwd>"

SECRET_REPL_TOKEN = "<pwd>"
# If a button is held at boot the device will start WebREPL and not run the HTTP server
REPL_BUTTON_PIN = 0
REPL_BUTTON_ACTIVE_LOW = True
TCP_REPL_ENABLED = True
TCP_REPL_PORT = 2323
TCP_REPL_TIMEOUT = 0.1
ENABLE_WDT = True
WDT_TIMEOUT_MS = 15000

wifi = network.WLAN(network.STA_IF)

# Sensor/cache config
SENSOR_SAMPLE_INTERVAL = 5
SENSOR_REINIT_INTERVAL = 30
SENSOR_CACHE_TTL = 60

# Error thresholds
ERROR_REBOOT_THRESHOLD = 8


def connect_wifi(ssid, password, timeout=15):
    wifi.active(True)
    if wifi.isconnected():
        return True
    try:
        wifi.connect(ssid, password)
    except Exception as e:
        print("WiFi connect error:", e)

    start = time.time()
    while not wifi.isconnected():
        if time.time() - start > timeout:
            print("WiFi connect timed out")
            return False
        time.sleep(0.5)
    print("Connected:", wifi.ifconfig())
    return True


if not connect_wifi(ssid, password):
    print("Failed to connect to WiFi on boot, resetting...")
    time.sleep(2)
    machine.reset()

# --- Sensors ---
i2c = machine.I2C(scl=machine.Pin(5), sda=machine.Pin(4))
bme = BME280(i2c=i2c)
bh = BH1750(i2c)

# Sensor cache and init tracking
sensor_cache = {'t': None, 'p': None, 'h': None, 'l': None, 'timestamp': 0}
last_sensor_init = time.time()

# --- REPL / WebREPL ---
# Change this token to something secret before exposing on a network!

def parse_path_from_req(req_bytes):
    try:
        first_line = req_bytes.split(b"\r\n", 1)[0]
        parts = first_line.split(b" ")
        if len(parts) >= 2:
            return parts[1].decode('utf-8')
    except Exception:
        pass
    return "/"

def start_webrepl():
    try:
        import webrepl
        try:
            webrepl.start()
            print("WebREPL started")
            return True
        except Exception as e:
            print("webrepl.start() failed:", e)
    except Exception as e:
        print("webrepl module not available:", e)
    return False

def stop_webrepl():
    try:
        import webrepl
        if hasattr(webrepl, 'stop'):
            try:
                webrepl.stop()
                print("WebREPL stopped")
                return True
            except Exception as e:
                print("webrepl.stop() failed:", e)
        else:
            print("webrepl.stop() not available in this build")
    except Exception as e:
        print("webrepl module not available:", e)
    return False

# --- Web Server ---
def setup_server(port=80, backlog=2, accept_timeout=0.5):
    addr = socket.getaddrinfo('0.0.0.0', port)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(backlog)
    s.settimeout(accept_timeout)
    print("Listening on", addr)
    return s


# If boot button pressed, start WebREPL and don't start HTTP server
try:
    btn = machine.Pin(REPL_BUTTON_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
    pressed = (btn.value() == 0) if REPL_BUTTON_ACTIVE_LOW else (btn.value() == 1)
except Exception:
    pressed = False

if pressed:
    print("REPL boot button pressed; starting WebREPL and entering REPL mode")
    start_webrepl()
    # Sit in a minimal loop so REPL (serial or web) stays available
    while True:
        feed_wdt()
        time.sleep(1)

s = setup_server()
repl_s = None
if TCP_REPL_ENABLED:
    def setup_repl_server(port=TCP_REPL_PORT, accept_timeout=TCP_REPL_TIMEOUT):
        addr = socket.getaddrinfo('0.0.0.0', port)[0][-1]
        rs = socket.socket()
        rs.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        rs.bind(addr)
        rs.listen(1)
        rs.settimeout(accept_timeout)
        print("REPL Listening on", addr)
        return rs

    def handle_repl_client(c):
        try:
            try:
                c.send(b"MicroPython remote REPL. Type 'exit' to quit.\r\n")
            except:
                pass
            while True:
                try:
                    c.send(b">>> ")
                except:
                    break
                line = b""
                try:
                    while True:
                        ch = c.recv(1)
                        if not ch:
                            raise OSError()
                        if ch in (b'\r', b'\n'):
                            # consume possible \n after \r
                            break
                        line += ch
                except Exception:
                    break
                try:
                    sline = line.decode('utf-8').strip()
                except Exception:
                    sline = ''
                if sline == 'exit':
                    break
                if not sline:
                    continue
                old_stdout = sys.stdout
                sio = io.StringIO()
                sys.stdout = sio
                try:
                    try:
                        val = eval(sline, globals(), locals())
                        if val is not None:
                            print(repr(val))
                    except SyntaxError:
                        exec(sline, globals(), locals())
                    except Exception as e:
                        print('Error:', e)
                finally:
                    sys.stdout = old_stdout
                out = sio.getvalue()
                try:
                    if out:
                        c.send(out.encode())
                    c.send(b"\r\n")
                except Exception:
                    break
                feed_wdt()  # Feed WDT during REPL session
        finally:
            try:
                c.close()
            except:
                pass

    try:
        repl_s = setup_repl_server()
    except Exception as e:
        repl_s = None
        print("Failed to setup TCP REPL socket:", e)

def safe_read_sensors():
    global sensor_cache, last_sensor_init, bme, bh, i2c
    now = time.time()
    
    # Return cached data if fresh
    if sensor_cache['timestamp'] > 0 and (now - sensor_cache['timestamp']) < SENSOR_CACHE_TTL:
        return sensor_cache['t'], sensor_cache['p'], sensor_cache['h'], sensor_cache['l']
    
    # Try to read sensors
    t, p, h, l = None, None, None, None
    try:
        t, p, h = bme.read_compensated()
    except Exception as e:
        print("BME280 read error:", e)
    
    try:
        l = bh.luminance()
    except Exception as e:
        print("BH1750 read error:", e)
    
    # If any sensor failed, try reinit if time has passed
    if (t is None or p is None or h is None or l is None) and (now - last_sensor_init) > SENSOR_REINIT_INTERVAL:
        print("Reinitializing sensors...")
        try:
            i2c = machine.I2C(scl=machine.Pin(5), sda=machine.Pin(4))
            bme = BME280(i2c=i2c)
            bh = BH1750(i2c)
            last_sensor_init = now
            # Try reading again after reinit
            try:
                t, p, h = bme.read_compensated()
            except:
                pass
            try:
                l = bh.luminance()
            except:
                pass
        except Exception as e:
            print("Sensor reinit failed:", e)
    
    # Update cache if we have data
    if t is not None and p is not None and h is not None and l is not None:
        sensor_cache = {'t': t, 'p': p, 'h': h, 'l': l, 'timestamp': now}
    
    # Return current or cached
    if t is not None and p is not None and h is not None and l is not None:
        return t, p, h, l
    elif sensor_cache['timestamp'] > 0:
        print("Using cached sensor data")
        return sensor_cache['t'], sensor_cache['p'], sensor_cache['h'], sensor_cache['l']
    else:
        return None, None, None, None

error_count = 0
# --- Watchdog (WDT) ---
# Enable to recover from hangs where exceptions or deadlocks prevent the main loop
wdt = None
if ENABLE_WDT:
    try:
        wdt = machine.WDT(timeout=WDT_TIMEOUT_MS)
        print("WDT enabled, timeout:", WDT_TIMEOUT_MS)
    except Exception as e:
        print("WDT init failed:", e)

def feed_wdt():
    try:
        if wdt:
            wdt.feed()
    except Exception:
        pass
while True:
    if not wifi.isconnected():
        print("WiFi lost; attempting reconnect")
        if not connect_wifi(ssid, password, timeout=30):
            print("Reconnect failed; resetting device")
            time.sleep(2)
            machine.reset()
        # recreate server socket after reconnect
        try:
            s.close()
        except:
            pass
        s = setup_server()
        # recreate repl socket after reconnect
        if TCP_REPL_ENABLED and repl_s:
            try:
                repl_s.close()
            except:
                pass
            try:
                repl_s = setup_repl_server()
            except Exception as e:
                repl_s = None
                print("Failed to recreate TCP REPL socket:", e)

    client = None
    # Accept incoming TCP REPL connections if enabled
    if TCP_REPL_ENABLED and repl_s:
        try:
            try:
                rclient, raddr = repl_s.accept()
                rclient.settimeout(30000)
                handle_repl_client(rclient)
            except OSError:
                pass
        except Exception as e:
            print("REPL accept error:", e)
    try:
        try:
            client, addr = s.accept()
        except OSError:
            time.sleep_ms(50)
            continue

        client.settimeout(2)

        # Read full request safely
        req = b""
        try:
            while True:
                chunk = client.recv(256)
                if not chunk:
                    break
                req += chunk
                if b"\r\n\r\n" in req:
                    break
        except Exception:
            pass

        # parse path and handle special REPL endpoints
        path = parse_path_from_req(req)
        if path.startswith("/webrepl-stop"):
            if ("token=" + SECRET_REPL_TOKEN) in path:
                ok = stop_webrepl()
                body = "WebREPL stopped\n" if ok else "WebREPL stop failed\n"
            else:
                body = "Missing or invalid token\n"
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                "Connection: close\r\n"
                "\r\n"
                + body
            )
            try:
                client.send(response.encode())
            except Exception:
                pass
            error_count = 0
            continue

        if path.startswith("/webrepl"):
            # require token in query string, simple check
            if ("token=" + SECRET_REPL_TOKEN) in path:
                ok = start_webrepl()
                body = "WebREPL started\n" if ok else "WebREPL failed\n"
            else:
                body = "Missing or invalid token\n"
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                "Connection: close\r\n"
                "\r\n"
                + body
            )
            try:
                client.send(response.encode())
            except Exception:
                pass
            error_count = 0
            continue

        # Read sensors
        t, p, h, l = safe_read_sensors()

        if t is None:
            body = "Sensor Read Error\n"
        else:
            try:
                body = (
                    "Temp: {0:.2f} C\n".format(t)
                    + "Pressure: {0:.2f} Pa\n".format(p)
                    + "Humidity: {0:.2f} %\n".format(h)
                    + "Lux: {0}\n".format(l)
                )
            except Exception:
                body = "Sensor Read Error\n"

        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain\r\n"
            "Connection: close\r\n"
            "\r\n"
            + body
        )

        try:
            client.send(response.encode())
        except Exception:
            # some sockets/platforms need sendall
            try:
                client.sendall(response.encode())
            except Exception as e:
                print("Send failed:", e)

        error_count = 0

    except Exception as e:
        print("Error in loop at", time.time(), ":", e)
        error_count += 1
        # if socket seems bad, recreate it
        if error_count > ERROR_REBOOT_THRESHOLD:
            print("Too many errors, rebooting device")
            try:
                time.sleep(2)
            except:
                pass
            try:
                machine.reset()
            except Exception as e:
                print("Reset failed:", e)
            error_count = 0

    finally:
        try:
            if client:
                client.close()
        except:
            pass
        gc.collect()
        # feed watchdog to indicate liveness
        feed_wdt()
        time.sleep_ms(10)
