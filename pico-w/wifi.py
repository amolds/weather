import network
import time


def connect(ssid, password, timeout=20):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return wlan

    print("Connecting to '{}'...".format(ssid))
    wlan.connect(ssid, password)

    for _ in range(timeout):
        if wlan.isconnected():
            print("Connected:", wlan.ifconfig())
            return wlan
        time.sleep(1)

    raise RuntimeError("Wi-Fi connection failed after {}s".format(timeout))


def sync_time():
    import ntptime
    ntptime.settime()
    print("Time synced (UTC):", time.gmtime())
