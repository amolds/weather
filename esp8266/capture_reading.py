import requests
import json
import pyodbc
import os
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime

SENSOR_HOSTNAME = os.getenv("SENSOR_HOSTNAME", "weather-sensor")
SENSOR_PORT = int(os.getenv("SENSOR_PORT", "80"))
SCAN_WORKERS = int(os.getenv("SENSOR_SCAN_WORKERS", "32"))
SCAN_TIMEOUT_S = float(os.getenv("SENSOR_SCAN_TIMEOUT_S", "1.0"))

# SQL Server connection info
CONN_STR = (
    "Driver={ODBC Driver 18 for SQL Server};"
    "Server=localhost;"
    "Database=master;"
    "UID=sa;"
    "PWD=Passw0rd!;"
    "Encrypt=no;"
    "TrustServerCertificate=yes;"
)


def build_base_url(host_or_ip, port):
    if port == 80:
        return "http://{0}".format(host_or_ip)
    return "http://{0}:{1}".format(host_or_ip, port)


def appears_to_be_sensor_payload(data):
    if not isinstance(data, dict):
        return False

    required_keys = ("temperature_c", "pressure_pa", "humidity_pct", "lux")
    for key in required_keys:
        if key not in data:
            return False

    return True


def get_local_ipv4():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    finally:
        sock.close()


def probe_sensor(host_or_ip, port, timeout_s):
    base_url = build_base_url(host_or_ip, port)
    response = requests.get(base_url, timeout=timeout_s)
    response.raise_for_status()
    data = response.json()
    if appears_to_be_sensor_payload(data):
        return base_url
    return None


def discover_sensor_url(hostname, port):
    candidates = [hostname, "{0}.local".format(hostname)]
    for candidate in candidates:
        try:
            ip = socket.gethostbyname(candidate)
            discovered = probe_sensor(ip, port, SCAN_TIMEOUT_S)
            if discovered:
                print("Discovered sensor via hostname '{0}' at {1}".format(candidate, discovered))
                return discovered
        except Exception:
            pass

    local_ip = get_local_ipv4()
    prefix = ".".join(local_ip.split(".")[:3])
    own_last_octet = int(local_ip.split(".")[-1])
    ip_candidates = []
    for i in range(1, 255):
        if i == own_last_octet:
            continue
        ip_candidates.append("{0}.{1}".format(prefix, i))

    print("Hostname lookup failed; scanning subnet {0}.0/24 for sensor...".format(prefix))
    with ThreadPoolExecutor(max_workers=SCAN_WORKERS) as executor:
        futures = [executor.submit(probe_sensor, ip, port, SCAN_TIMEOUT_S) for ip in ip_candidates]
        for future in as_completed(futures):
            try:
                discovered = future.result()
                if discovered:
                    print("Discovered sensor at {0}".format(discovered))
                    return discovered
            except Exception:
                pass

    raise RuntimeError(
        "Could not discover sensor host by hostname or subnet scan. "
        "Set SENSOR_HOSTNAME or verify network connectivity."
    )


def insert_into_sql(data):
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    query = """
        INSERT INTO SensorReadings (Temperature, Pressure, Humidity, Lux, Timestamp)
        VALUES (?, ?, ?, ?, ?)
    """

    cursor.execute(
        query,
        data.get("temperature_c"),
        data.get("pressure_pa"),
        data.get("humidity_pct"),
        data.get("lux"),
        datetime.now()
    )

    conn.commit()
    cursor.close()
    conn.close()


def fetch_and_store():
    MAX_ATTEMPTS = 10
    RETRY_DELAY = 30  # seconds between attempts
    sensor_url = None
    
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            if sensor_url is None:
                sensor_url = discover_sensor_url(SENSOR_HOSTNAME, SENSOR_PORT)

            # Fetch JSON from the server
            response = requests.get(sensor_url, timeout=10)  # 10 second timeout
            response.raise_for_status()

            # Parse JSON response
            data = response.json()
            print("Attempt {0}/{1} - Raw response: {2}".format(attempt, MAX_ATTEMPTS, json.dumps(data, indent=2)))

            # Check for errors
            if "error" in data:
                print("Attempt {0}/{1} - Error from sensor: {2}".format(attempt, MAX_ATTEMPTS, data["error"]))
                if attempt < MAX_ATTEMPTS:
                    print("Retrying in {0} seconds...".format(RETRY_DELAY))
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    print("All attempts failed. Giving up.")
                    return

            print("Attempt {0}/{1} - Success!".format(attempt, MAX_ATTEMPTS))
            print("\nSensor values:")
            print("  Temperature: {0:.2f} C".format(data.get("temperature_c")))
            print("  Pressure: {0:.2f} Pa".format(data.get("pressure_pa")))
            print("  Humidity: {0:.2f} %".format(data.get("humidity_pct")))
            print("  Lux: {0}".format(data.get("lux")))
            print("\nDevice status:")
            print("  Uptime: {0} seconds".format(data.get("uptime_seconds")))
            print("  Memory free: {0} bytes".format(data.get("memory_free_bytes")))
            print("  Memory allocated: {0} bytes".format(data.get("memory_allocated_bytes")))

            # Store in SQL Server
            insert_into_sql(data)
            print("\nData successfully stored in SQL Server.")
            return  # Success - exit function

        except requests.exceptions.RequestException as e:
            print("Attempt {0}/{1} - Connection error: {2}".format(attempt, MAX_ATTEMPTS, e))
            sensor_url = None
        except json.JSONDecodeError as e:
            print("Attempt {0}/{1} - JSON parse error: {2}".format(attempt, MAX_ATTEMPTS, e))
            sensor_url = None
        except Exception as e:
            print("Attempt {0}/{1} - Unexpected error: {2}".format(attempt, MAX_ATTEMPTS, e))
            sensor_url = None
        
        # If we get here, the attempt failed
        if attempt < MAX_ATTEMPTS:
            print("Retrying in {0} seconds...".format(RETRY_DELAY))
            time.sleep(RETRY_DELAY)
        else:
            print("All {0} attempts failed.".format(MAX_ATTEMPTS))


if __name__ == "__main__":
    fetch_and_store()

