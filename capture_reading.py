import requests
import json
import pyodbc
import time
from datetime import datetime

# URL of your local web server endpoint
URL = "http://192.168.1.36"   # <-- change to your actual endpoint

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
    
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            # Fetch JSON from the server
            response = requests.get(URL, timeout=10)  # 10 second timeout
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
        except json.JSONDecodeError as e:
            print("Attempt {0}/{1} - JSON parse error: {2}".format(attempt, MAX_ATTEMPTS, e))
        except Exception as e:
            print("Attempt {0}/{1} - Unexpected error: {2}".format(attempt, MAX_ATTEMPTS, e))
        
        # If we get here, the attempt failed
        if attempt < MAX_ATTEMPTS:
            print("Retrying in {0} seconds...".format(RETRY_DELAY))
            time.sleep(RETRY_DELAY)
        else:
            print("All {0} attempts failed.".format(MAX_ATTEMPTS))


if __name__ == "__main__":
    fetch_and_store()

