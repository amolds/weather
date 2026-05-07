import config
import wifi

wlan = wifi.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
wifi.sync_time()
