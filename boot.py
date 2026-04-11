import gc
import machine
from app_config import ENABLE_WATCHDOG
from app_config import DEBUG
from app_config import GC_EVERY_N_REQUESTS
from app_config import RESET_ON_SENSOR_HANG
from app_config import SENSOR_HANG_TOLERANCE_MS
from app_config import SENSOR_INIT_RETRY_MS
from app_config import SENSOR_READ_INTERVAL_MS
from app_config import SENSOR_SCL_PIN
from app_config import SENSOR_SDA_PIN
from app_config import SENSOR_STALE_TOLERANCE_MS
from app_config import SERVER_ACCEPT_TIMEOUT_S
from app_config import SERVER_CLIENT_TIMEOUT_S
from app_config import SERVER_HOST
from app_config import SERVER_PORT
from app_config import WATCHDOG_TIMEOUT_MS
from app_config import WIFI_CONNECT_TIMEOUT_S
from app_config import WIFI_MAX_RECONNECT_ATTEMPTS
from app_config import WIFI_PASSWORD
from app_config import WIFI_RECONNECT_DELAY
from app_config import WIFI_RECONNECT_WAIT_S
from app_config import WIFI_SSID
from sensor_cache import SensorCache
from web_server import SensorHttpServer
from wifi_manager import WifiManager


def build_sensor_cache():
    sensor_reader = SensorCache(
        scl_pin=SENSOR_SCL_PIN,
        sda_pin=SENSOR_SDA_PIN,
        read_interval_ms=SENSOR_READ_INTERVAL_MS,
        init_retry_ms=SENSOR_INIT_RETRY_MS,
        stale_tolerance_ms=SENSOR_STALE_TOLERANCE_MS,
        hang_tolerance_ms=SENSOR_HANG_TOLERANCE_MS,
        debug=DEBUG,
    )
    sensor_reader.start()
    return sensor_reader


def build_wifi_manager():
    return WifiManager(
        ssid=WIFI_SSID,
        password=WIFI_PASSWORD,
        reconnect_delay=WIFI_RECONNECT_DELAY,
        max_reconnect_attempts=WIFI_MAX_RECONNECT_ATTEMPTS,
        connect_timeout_s=WIFI_CONNECT_TIMEOUT_S,
        reconnect_wait_s=WIFI_RECONNECT_WAIT_S,
        debug=DEBUG,
    )


def build_http_server(sensor_reader):
    http_server = SensorHttpServer(
        sensor_cache=sensor_reader,
        host=SERVER_HOST,
        port=SERVER_PORT,
        accept_timeout_s=SERVER_ACCEPT_TIMEOUT_S,
        client_timeout_s=SERVER_CLIENT_TIMEOUT_S,
        debug=DEBUG,
    )
    http_server.start()
    return http_server


def build_watchdog():
    if not ENABLE_WATCHDOG:
        return None

    try:
        return machine.WDT(timeout=WATCHDOG_TIMEOUT_MS)
    except (TypeError, ValueError):
        pass

    try:
        return machine.WDT(WATCHDOG_TIMEOUT_MS)
    except (TypeError, ValueError):
        pass

    try:
        return machine.WDT()
    except Exception as error:
        if DEBUG:
            print("Watchdog unavailable:", error)
        return None


def main():
    sensor_reader = build_sensor_cache()
    wifi_manager = build_wifi_manager()
    wifi = wifi_manager.connect()
    http_server = build_http_server(sensor_reader)
    watchdog = build_watchdog()
    request_count = 0

    while True:
        sensor_reader.poll()

        if sensor_reader.get_health()["read_appears_hung"]:
            sensor_reader.mark_hung()
            if RESET_ON_SENSOR_HANG:
                machine.reset()

        wifi = wifi_manager.ensure_connected(wifi)
        client, client_addr = http_server.accept()
        if client is None:
            if watchdog is not None:
                watchdog.feed()
            continue

        if DEBUG:
            print("Client connected:", client_addr)

        http_server.handle_client(client)
        if watchdog is not None:
            watchdog.feed()
        request_count += 1
        if request_count >= GC_EVERY_N_REQUESTS:
            gc.collect()
            request_count = 0


main()
