import network
import time


def _configure_power_mode(wlan):
    # Disable power-save where supported; this improves connection stability on some APs.
    for pm in (
        getattr(network, "PM_NONE", None),
        getattr(network.WLAN, "PM_NONE", None),
        0xA11140,
    ):
        if pm is None:
            continue
        try:
            wlan.config(pm=pm)
            return
        except Exception:
            pass


def connect(ssid, password, hostname=None, timeout=20):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    _configure_power_mode(wlan)

    if hostname:
        try:
            wlan.config(dhcp_hostname=hostname)
        except Exception:
            pass

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


def ensure_connected(wlan, ssid, password, hostname=None, timeout=20):
    if wlan is None:
        return connect(ssid, password, hostname=hostname, timeout=timeout)

    if not wlan.active():
        wlan.active(True)

    _configure_power_mode(wlan)

    if hostname:
        try:
            wlan.config(dhcp_hostname=hostname)
        except Exception:
            pass

    if wlan.isconnected():
        return wlan

    wlan.connect(ssid, password)
    for _ in range(timeout):
        if wlan.isconnected():
            print("Wi-Fi reconnected:", wlan.ifconfig())
            return wlan
        time.sleep(1)

    return wlan


def sync_time():
    import ntptime
    ntptime.settime()
    print("Time synced (UTC):", time.gmtime())
