import requests
import re
import pyodbc
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

def parse_sensor_data(text):
    data = {}

    patterns = {
        "temperature": r"BME280 Temperature:\s*([0-9.]+)\s*C",
        "pressure": r"BME280 Pressure:\s*([0-9.]+)\s*Pa",
        "humidity": r"BME280 Humidity:\s*([0-9.]+)\s*%",
        "lux": r"Lux:\s*([0-9.]+)"
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            data[key] = float(match.group(1))

    return data


def insert_into_sql(data):
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    query = """
        INSERT INTO SensorReadings (Temperature, Pressure, Humidity, Lux, Timestamp)
        VALUES (?, ?, ?, ?, ?)
    """

    cursor.execute(
        query,
        data.get("temperature"),
        data.get("pressure"),
        data.get("humidity"),
        data.get("lux"),
        datetime.now()
    )

    conn.commit()
    cursor.close()
    conn.close()


def fetch_and_store():
    # Fetch raw text from the server
    response = requests.get(URL)
    response.raise_for_status()

    raw_text = response.text
    print("Raw response:\n", raw_text)

    # Parse the sensor values
    parsed = parse_sensor_data(raw_text)
    print("\nParsed values:", parsed)

    # Store in SQL Server
    insert_into_sql(parsed)
    print("\nData successfully stored in SQL Server.")


if __name__ == "__main__":
    fetch_and_store()

