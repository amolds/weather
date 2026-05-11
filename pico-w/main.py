"""
main.py — Pico W weather station runtime loop (dual-core).

Core 0 — sensor loop:
  1. Connect Wi-Fi, sync NTP
  2. Init sensors (SHT31, TSL2591, BMP390) on shared I2C bus
  3. Every LOG_INTERVAL_S: read sensors, log to SD, update shared state

Core 1 — HTTP server:
  Serves latest reading as JSON on port 80.
  GET /  or  GET /data  ->  {"timestamp":…,"temp_c":…,…}
"""

import time
import machine
import _thread
import config
import wifi
from sensors.sht31 import SHT31
from sensors.tsl2591 import TSL2591
from sensors.bmp390 import BMP390
from sensors.gps import GPS

try:
    from storage.sdlogger import SDLogger
    _has_sdlogger = True
except ImportError:
    _has_sdlogger = False
    print("Warning: SDLogger not available (sdcard module missing)")

from server.http import serve

# Shared state between cores — protected by a lock
latest = {}
state_lock = _thread.allocate_lock()

# How often to take a reading — controlled via config.LOG_INTERVAL_S
LOG_INTERVAL_S = config.LOG_INTERVAL_S


def timestamp():
    t = time.localtime()
    return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}".format(
        t[0], t[1], t[2], t[3], t[4], t[5]
    )


def main():
    # --- Wi-Fi + NTP ---
    wlan = None
    try:
        wlan = wifi.connect(config.WIFI_SSID, config.WIFI_PASSWORD, config.HOSTNAME)
        wifi.sync_time()
    except Exception as e:
        print("Wi-Fi/NTP error (continuing without time sync):", e)

    # --- Status LEDs ---
    led_http = machine.Pin(config.LED_HTTP_PIN, machine.Pin.OUT)
    led_sd   = machine.Pin(config.LED_SD_PIN,   machine.Pin.OUT)
    led_http.off()
    led_sd.off()

    # --- Start HTTP server on core 1 (only if Wi-Fi is up) ---
    if wlan and wlan.isconnected():
        _thread.start_new_thread(serve, (latest, state_lock, 80, led_http))

    # --- Sensor init ---
    i2c = machine.I2C(
        config.I2C_BUS,
        sda=machine.Pin(config.I2C_SDA),
        scl=machine.Pin(config.I2C_SCL),
        freq=config.I2C_FREQ,
    )
    sht31  = SHT31(i2c)
    tsl    = TSL2591(i2c)
    bmp    = BMP390(i2c)
    logger = None
    if _has_sdlogger:
        try:
            logger = SDLogger(led=led_sd)
        except Exception as e:
            print("SDLogger init failed:", e)

    # --- GPS init (optional) ---
    gps = None
    if config.ENABLE_GPS:
        try:
            gps = GPS(
                uart_id=config.GPS_UART,
                tx_pin=config.GPS_TX,
                rx_pin=config.GPS_RX,
                baudrate=config.GPS_BAUD,
            )
            print("GPS initialized on UART{}".format(config.GPS_UART))
        except Exception as e:
            print("GPS init failed:", e)

    print("Weather station running — logging every {}s".format(LOG_INTERVAL_S))

    while True:
        try:
            sht_data = sht31.read()
            tsl_data = tsl.read()
            bmp_data = bmp.read()

            ts       = timestamp()
            temp_c   = sht_data["temp_c"]
            temp_f   = sht_data["temp_f"]
            humidity = sht_data["humidity"]
            pressure = bmp_data["pressure"]
            lux      = tsl_data["lux"]

            gps_data = None
            if gps:
                try:
                    gps.update(max_sentences=20)
                    gps_data = gps.get_position()
                except Exception as e:
                    print("GPS read error:", e)

            # Update shared state for the HTTP server
            state_lock.acquire()
            try:
                latest.update(dict(
                    timestamp=ts,
                    temp_c=temp_c,
                    temp_f=temp_f,
                    humidity=humidity,
                    pressure=pressure,
                    lux=lux,
                    lat=(gps_data["latitude"] if gps_data else None),
                    lng=(gps_data["longitude"] if gps_data else None),
                    gps_time=(gps_data["time"] if gps_data else None),
                    gps_date=(gps_data["date"] if gps_data else None),
                ))
            finally:
                state_lock.release()

            if logger:
                try:
                    logger.log(ts, temp_c, temp_f, humidity, pressure, lux, gps_data=gps_data)
                except Exception as e:
                    print("SD log error:", e)

            print("{} | {:.1f}°C {:.1f}°F | RH {:.1f}% | {:.2f} hPa | {:.1f} lux".format(
                ts, temp_c, temp_f, humidity, pressure, lux
            ))

        except Exception as e:
            print("Read/log error:", e)

        time.sleep(LOG_INTERVAL_S)


main()
