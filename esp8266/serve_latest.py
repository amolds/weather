from http.server import BaseHTTPRequestHandler, HTTPServer
import pyodbc
from datetime import datetime
import json

CONN_STR = (
    "Driver={ODBC Driver 18 for SQL Server};"
    "Server=192.168.1.41;"
    "Database=master;"
    "UID=sa;"
    "PWD=Passw0rd!;"
    "Encrypt=no;"
    "TrustServerCertificate=yes;"
)

def c_to_f(c):
    return c * 9.0 / 5.0 + 32.0

def get_latest_reading():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT TOP 1 Temperature, Pressure, Humidity, Lux, Timestamp
        FROM SensorReadings
        ORDER BY Timestamp DESC
    """)

    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return None

    temp_c = float(row[0])
    temp_f = c_to_f(temp_c)

    return {
        "temperature_c": temp_c,
        "temperature_f": temp_f,
        "pressure": row[1],
        "humidity": row[2],
        "lux": float(row[3]),
        "timestamp": row[4]
    }

def get_last_24h_temps():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT Timestamp, Temperature
        FROM SensorReadings
        WHERE Timestamp >= DATEADD(day, -1, GETDATE())
        ORDER BY Timestamp ASC
    """)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    labels = []
    temps_f = []

    for ts, temp_c in rows:
        labels.append(ts.strftime("%H:%M"))
        temps_f.append(c_to_f(float(temp_c)))

    return labels, temps_f

def get_last_24h_humidity():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT Timestamp, Humidity
        FROM SensorReadings
        WHERE Timestamp >= DATEADD(day, -1, GETDATE())
        ORDER BY Timestamp ASC
    """)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    labels = []
    humidity_values = []

    for ts, humidity in rows:
        labels.append(ts.strftime("%H:%M"))
        humidity_values.append(float(humidity))

    return labels, humidity_values

def get_last_24h_pressure():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT Timestamp, Pressure
        FROM SensorReadings
        WHERE Timestamp >= DATEADD(day, -1, GETDATE())
        ORDER BY Timestamp ASC
    """)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    labels = []
    pressure_values = []

    for ts, pressure in rows:
        labels.append(ts.strftime("%H:%M"))
        pressure_values.append(float(pressure))

    return labels, pressure_values

def get_recent_lux_readings(days=2):
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT Timestamp, Lux
        FROM SensorReadings
        WHERE Timestamp >= DATEADD(day, -?, GETDATE())
        ORDER BY Timestamp ASC
    """, (days,))

    rows = [(ts, float(lux)) for ts, lux in cursor.fetchall()]
    cursor.close()
    conn.close()

    return rows

def find_sustained_transition(rows, start_hour, from_above, threshold, sustain_count=2):
    if not rows:
        return None

    last_transition_time = None

    for index in range(1, len(rows)):
        previous_ts, previous_lux = rows[index - 1]
        current_ts, current_lux = rows[index]

        if current_ts.hour < start_hour:
            continue

        if from_above:
            crossed = previous_lux >= threshold and current_lux < threshold
            sustained = all(next_lux < threshold for _, next_lux in rows[index:index + sustain_count])
        else:
            crossed = previous_lux <= threshold and current_lux > threshold
            sustained = all(next_lux > threshold for _, next_lux in rows[index:index + sustain_count])

        if crossed and sustained:
            last_transition_time = current_ts.strftime("%H:%M")

    return last_transition_time

def find_daily_transition(rows, start_hour, from_above, threshold, sustain_count=2):
    if not rows:
        return None

    for index in range(1, len(rows)):
        previous_ts, previous_lux = rows[index - 1]
        current_ts, current_lux = rows[index]

        if current_ts.hour < start_hour:
            continue

        if from_above:
            crossed = previous_lux >= threshold and current_lux < threshold
            sustained = all(next_lux < threshold for _, next_lux in rows[index:index + sustain_count])
        else:
            crossed = previous_lux <= threshold and current_lux > threshold
            sustained = all(next_lux > threshold for _, next_lux in rows[index:index + sustain_count])

        if crossed and sustained:
            return current_ts.strftime("%H:%M")

    return None

def get_dawn_time():
    """Get the most recent sustained dawn time from recent lux history."""
    rows = get_recent_lux_readings(days=2)
    dawn_time = find_sustained_transition(rows, start_hour=4, from_above=False, threshold=10, sustain_count=2)
    return dawn_time or "N/A"

def get_dusk_time():
    """Get the most recent sustained dusk time, or 'Not yet' while current lux is still above threshold."""
    rows = get_recent_lux_readings(days=2)
    if not rows:
        return "N/A"

    current_lux = rows[-1][1]
    if current_lux >= 10:
        return "Not yet"

    dusk_time = find_sustained_transition(rows, start_hour=16, from_above=True, threshold=10, sustain_count=2)
    return dusk_time or "N/A"

def get_daily_high_low():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            CAST(Timestamp AS date) AS Day,
            MIN(Temperature) AS LowTemp,
            MAX(Temperature) AS HighTemp,
            MIN(Humidity) AS LowHumidity,
            MAX(Humidity) AS HighHumidity,
            MIN(Pressure) AS LowPressure,
            MAX(Pressure) AS HighPressure
        FROM SensorReadings
        GROUP BY CAST(Timestamp AS date)
        ORDER BY Day ASC
    """)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    labels = []
    temp_lows_f = []
    temp_highs_f = []
    humidity_lows = []
    humidity_highs = []
    pressure_lows = []
    pressure_highs = []

    for day, low_temp_c, high_temp_c, low_humidity, high_humidity, low_pressure, high_pressure in rows:
        labels.append(day.strftime("%Y-%m-%d"))
        temp_lows_f.append(c_to_f(float(low_temp_c)))
        temp_highs_f.append(c_to_f(float(high_temp_c)))
        humidity_lows.append(float(low_humidity))
        humidity_highs.append(float(high_humidity))
        pressure_lows.append(float(low_pressure))
        pressure_highs.append(float(high_pressure))

    return labels, temp_lows_f, temp_highs_f, humidity_lows, humidity_highs, pressure_lows, pressure_highs

def temperature_color_f(temp_f):
    if temp_f <= 32:
        return "#4a90e2"   # freezing / cold blue
    elif temp_f <= 50:
        return "#50e3c2"   # cool teal
    elif temp_f <= 68:
        return "#7ed321"   # mild green
    elif temp_f <= 86:
        return "#f5a623"   # warm orange
    else:
        return "#d0021b"   # hot red

def lux_icon_and_label(lux):
    if lux < 1:
        return "🌌", "Very dark – starlight / dim night"
    elif lux < 10:
        return "🌙", "Twilight / moonlight"
    elif lux < 100:
        return "🌫️", "Very dim / gloomy"
    elif lux < 1000:
        return "☁️", "Overcast / bright indoors"
    elif lux < 10000:
        return "🌤️", "Normal daylight"
    elif lux < 50000:
        return "☀️", "Very bright daylight"
    else:
        return "🌞", "Intense sun"

def get_year_to_date_calendar():
    """Get year-to-date daily dawn/dusk plus low/high for temperature, humidity, and pressure"""
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            CAST(Timestamp AS date) AS Day,
            MIN(Temperature) AS LowTemp,
            MAX(Temperature) AS HighTemp,
            MIN(Humidity) AS LowHumidity,
            MAX(Humidity) AS HighHumidity,
            MIN(Pressure) AS LowPressure,
            MAX(Pressure) AS HighPressure
        FROM SensorReadings
        WHERE CAST(Timestamp AS date) >= DATEFROMPARTS(YEAR(GETDATE()), 1, 1)
        GROUP BY CAST(Timestamp AS date)
        ORDER BY Day ASC
    """)

    rows = cursor.fetchall()

    calendar_data = {}
    for day, low_temp_c, high_temp_c, low_humidity, high_humidity, low_pressure, high_pressure in rows:
        day_str = day.strftime("%Y-%m-%d")
        calendar_data[day_str] = {
            "dawn": "N/A",
            "temp_low": c_to_f(float(low_temp_c)),
            "temp_high": c_to_f(float(high_temp_c)),
            "dusk": "N/A",
            "humidity_low": float(low_humidity),
            "humidity_high": float(high_humidity),
            "pressure_low": float(low_pressure),
            "pressure_high": float(high_pressure)
        }

    cursor.execute("""
        SELECT CAST(Timestamp AS date) AS Day, Timestamp, Lux
        FROM SensorReadings
        WHERE CAST(Timestamp AS date) >= DATEFROMPARTS(YEAR(GETDATE()), 1, 1)
        ORDER BY Timestamp ASC
    """)

    lux_rows = cursor.fetchall()
    cursor.close()
    conn.close()

    daily_lux = {}
    for day, ts, lux in lux_rows:
        day_str = day.strftime("%Y-%m-%d")
        daily_lux.setdefault(day_str, []).append((ts, float(lux)))

    for day_str, day_rows in daily_lux.items():
        if day_str not in calendar_data:
            continue

        dawn_time = find_daily_transition(day_rows, start_hour=4, from_above=False, threshold=10, sustain_count=2)
        dusk_time = find_daily_transition(day_rows, start_hour=16, from_above=True, threshold=10, sustain_count=2)

        calendar_data[day_str]["dawn"] = dawn_time or "N/A"
        calendar_data[day_str]["dusk"] = dusk_time or "N/A"

    return calendar_data

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        reading = get_latest_reading()

        if not reading:
            html = "<h1>No readings found</h1>"
        else:
            temp_f = reading["temperature_f"]
            temp_color = temperature_color_f(temp_f)

            last24_labels, last24_temps_f = get_last_24h_temps()
            last24_humidity_labels, last24_humidity_values = get_last_24h_humidity()
            last24_pressure_labels, last24_pressure_values = get_last_24h_pressure()
            dawn_time = get_dawn_time()
            dusk_time = get_dusk_time()
            daily_labels, temp_lows_f, temp_highs_f, humidity_lows, humidity_highs, pressure_lows, pressure_highs = get_daily_high_low()
            calendar_data = get_year_to_date_calendar()
            calendar_data_json = json.dumps(calendar_data)

            # Calculate min/max for 24-hour charts
            if last24_temps_f:
                temp_24h_min = min(last24_temps_f)
                temp_24h_max = max(last24_temps_f)
            else:
                temp_24h_min = temp_24h_max = 0

            if last24_humidity_values:
                humidity_24h_min = min(last24_humidity_values)
                humidity_24h_max = max(last24_humidity_values)
            else:
                humidity_24h_min = humidity_24h_max = 0

            if last24_pressure_values:
                pressure_24h_min = min(last24_pressure_values)
                pressure_24h_max = max(last24_pressure_values)
            else:
                pressure_24h_min = pressure_24h_max = 0

            last24_labels_json = json.dumps(last24_labels)
            last24_temps_json = json.dumps(last24_temps_f)
            last24_humidity_json = json.dumps(last24_humidity_values)
            last24_pressure_json = json.dumps(last24_pressure_values)

            # Group daily high/low by ISO week (most recent week first)
            weeks = {}
            for lbl, temp_low, temp_high, hum_low, hum_high, pres_low, pres_high in zip(daily_labels, temp_lows_f, temp_highs_f, humidity_lows, humidity_highs, pressure_lows, pressure_highs):
                try:
                    day = datetime.strptime(lbl, "%Y-%m-%d").date()
                except Exception:
                    day = None

                if day is not None:
                    iso = day.isocalendar()
                    key = (iso[0], iso[1])  # (year, week)
                    week_label = f"{day.strftime('%a %m-%d')}"
                else:
                    key = (0, 0)
                    week_label = lbl

                if key not in weeks:
                    weeks[key] = {
                        "labels": [], 
                        "temp_lows": [], "temp_highs": [],
                        "humidity_lows": [], "humidity_highs": [],
                        "pressure_lows": [], "pressure_highs": [],
                        "year": key[0], "week": key[1]
                    }

                weeks[key]["labels"].append(week_label)
                weeks[key]["temp_lows"].append(temp_low)
                weeks[key]["temp_highs"].append(temp_high)
                weeks[key]["humidity_lows"].append(hum_low)
                weeks[key]["humidity_highs"].append(hum_high)
                weeks[key]["pressure_lows"].append(pres_low)
                weeks[key]["pressure_highs"].append(pres_high)

            # Sort weeks most recent first
            sorted_weeks = sorted(weeks.items(), key=lambda x: x[0], reverse=True)

            weekly_data = []
            weekly_canvases_html = ""
            humidity_weekly_data = []
            humidity_weekly_canvases_html = ""
            pressure_weekly_data = []
            pressure_weekly_canvases_html = ""
            for (year, wnum), data in sorted_weeks:
                # Calculate Monday and Sunday of the ISO week
                monday = datetime.fromisocalendar(year, wnum, 1)
                sunday = datetime.fromisocalendar(year, wnum, 7)
                
                # Calculate weekly ranges
                if data["temp_lows"] and data["temp_highs"]:
                    temp_week_min = min(data["temp_lows"])
                    temp_week_max = max(data["temp_highs"])
                else:
                    temp_week_min = temp_week_max = 0
                
                if data["humidity_lows"] and data["humidity_highs"]:
                    humidity_week_min = min(data["humidity_lows"])
                    humidity_week_max = max(data["humidity_highs"])
                else:
                    humidity_week_min = humidity_week_max = 0
                    
                if data["pressure_lows"] and data["pressure_highs"]:
                    pressure_week_min = min(data["pressure_lows"])
                    pressure_week_max = max(data["pressure_highs"])
                else:
                    pressure_week_min = pressure_week_max = 0
                
                # Temperature chart
                temp_week_range = f"{monday.strftime('%b %d')} - {sunday.strftime('%b %d, %Y')} (Temperature °F) - Low: {temp_week_min:.1f}°F, High: {temp_week_max:.1f}°F"
                temp_canvas_id = f"weeklyTempChart_{year}_{wnum}"
                weekly_canvases_html += f'<div class="card"><h3>{temp_week_range}</h3><canvas id="{temp_canvas_id}"></canvas></div>'
                weekly_data.append({
                    "id": temp_canvas_id,
                    "labels": data["labels"],
                    "temp_lows": data["temp_lows"],
                    "temp_highs": data["temp_highs"]
                })
                
                # Humidity chart
                hum_week_range = f"{monday.strftime('%b %d')} - {sunday.strftime('%b %d, %Y')} (Humidity %) - Low: {humidity_week_min:.1f}%, High: {humidity_week_max:.1f}%"
                hum_canvas_id = f"weeklyHumidityChart_{year}_{wnum}"
                humidity_weekly_canvases_html += f'<div class="card"><h3>{hum_week_range}</h3><canvas id="{hum_canvas_id}"></canvas></div>'
                humidity_weekly_data.append({
                    "id": hum_canvas_id,
                    "labels": data["labels"],
                    "humidity_lows": data["humidity_lows"],
                    "humidity_highs": data["humidity_highs"]
                })
                
                # Pressure chart
                pres_week_range = f"{monday.strftime('%b %d')} - {sunday.strftime('%b %d, %Y')} (Pressure Pa) - Low: {pressure_week_min:.1f} Pa, High: {pressure_week_max:.1f} Pa"
                pres_canvas_id = f"weeklyPressureChart_{year}_{wnum}"
                pressure_weekly_canvases_html += f'<div class="card"><h3>{pres_week_range}</h3><canvas id="{pres_canvas_id}"></canvas></div>'
                pressure_weekly_data.append({
                    "id": pres_canvas_id,
                    "labels": data["labels"],
                    "pressure_lows": data["pressure_lows"],
                    "pressure_highs": data["pressure_highs"]
                })

            weekly_data_json = json.dumps(weekly_data)
            humidity_weekly_data_json = json.dumps(humidity_weekly_data)
            pressure_weekly_data_json = json.dumps(pressure_weekly_data)

            lux = reading["lux"]
            lux_icon, lux_desc = lux_icon_and_label(lux)

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta http-equiv="refresh" content="300">
                <title>Weather Dashboard</title>
                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 0;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        min-height: 100vh;
                        transition: background 0.4s, color 0.4s;
                    }}
                    body.light {{
                        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                        color: #333;
                    }}
                    body.dark {{
                        background: #1e1e1e;
                        color: #e0e0e0;
                    }}
                    .top-bar {{
                        width: 100%;
                        display: flex;
                        justify-content: flex-end;
                        padding: 15px 20px;
                        box-sizing: border-box;
                        position: relative;
                    }}
                    .toggle-btn {{
                        position: fixed;
                        top: 20px;
                        right: 20px;
                        width: 50px;
                        height: 50px;
                        border-radius: 50%;
                        border: none;
                        cursor: pointer;
                        font-size: 20px;
                        background: rgba(255,255,255,0.9);
                        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                        transition: all 0.3s ease;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        z-index: 1000;
                    }}
                    .toggle-btn:hover {{
                        transform: scale(1.1);
                        box-shadow: 0 6px 20px rgba(0,0,0,0.25);
                    }}
                    .sticky-temp {{
                        position: fixed;
                        top: 14px;
                        left: 50%;
                        transform: translateX(-50%);
                        background: rgba(255,255,255,0.92);
                        color: #333;
                        border-radius: 999px;
                        padding: 14px 24px;
                        font-weight: bold;
                        font-size: 24px;
                        line-height: 1;
                        box-shadow: 0 4px 14px rgba(0,0,0,0.18);
                        z-index: 900;
                        display: none;
                    }}
                    .sticky-temp.show {{
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    }}
                    body.dark .toggle-btn {{
                        background: rgba(50,50,50,0.9);
                        color: #e0e0e0;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                    }}
                    body.dark .sticky-temp {{
                        background: rgba(50,50,50,0.92);
                        color: #e0e0e0;
                        box-shadow: 0 4px 14px rgba(0,0,0,0.45);
                    }}
                    body.dark .toggle-btn:hover {{
                        box-shadow: 0 6px 20px rgba(0,0,0,0.5);
                    }}
                    .content {{
                        width: 100%;
                        max-width: 1100px;
                        padding: 0 20px 40px 20px;
                        box-sizing: border-box;
                        display: flex;
                        flex-direction: column;
                        gap: 20px;
                    }}
                    .card {{
                        background: white;
                        padding: 20px 30px;
                        border-radius: 12px;
                        box-shadow: 0 8px 20px rgba(0,0,0,0.15);
                        transition: background 0.4s, color 0.4s;
                    }}
                    body.dark .card {{
                        background: #2c2c2c;
                        color: #e0e0e0;
                        box-shadow: 0 8px 20px rgba(255,255,255,0.05);
                    }}
                    .card h1, .card h2 {{
                        margin-top: 0;
                    }}
                    .latest-card {{
                        text-align: center;
                    }}
                    .readings-grid {{
                        display: grid;
                        grid-template-columns: 1fr 1fr;
                        gap: 20px;
                        margin: 20px 0;
                    }}
                    .reading {{
                        font-size: 20px;
                        margin: 10px 0;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        gap: 10px;
                    }}
                    .reading-column {{
                        display: flex;
                        flex-direction: column;
                        gap: 15px;
                    }}
                    .label {{
                        font-weight: bold;
                    }}
                    .icon {{
                        font-size: 26px;
                    }}
                    .temp-value {{
                        font-weight: bold;
                        color: {temp_color};
                    }}
                    .timestamp {{
                        margin-top: 15px;
                        font-size: 14px;
                        opacity: 0.8;
                    }}
                    .lux-desc {{
                        font-size: 14px;
                        opacity: 0.85;
                        margin-left: 10px;
                    }}
                    .charts {{
                        display: grid;
                        grid-template-columns: 1fr;
                        gap: 20px;
                    }}
                    /* Keep charts stacked so the Last 24 Hours card matches Latest Reading width */
                    canvas {{
                        width: 100% !important;
                        height: 300px !important;
                    }}
                    .calendar-grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
                        gap: 8px;
                        margin-bottom: 15px;
                    }}
                    .calendar-day {{
                        background: rgba(100,100,100,0.1);
                        border: 1px solid rgba(100,100,100,0.2);
                        border-radius: 6px;
                        padding: 8px;
                        font-size: 12px;
                        text-align: left;
                        transition: all 0.2s;
                        cursor: default;
                    }}
                    .calendar-day:hover {{
                        background: rgba(100,100,100,0.2);
                        border-color: rgba(100,100,100,0.4);
                        transform: scale(1.02);
                    }}
                    body.dark .calendar-day {{
                        background: rgba(200,200,200,0.1);
                        border-color: rgba(200,200,200,0.2);
                    }}
                    body.dark .calendar-day:hover {{
                        background: rgba(200,200,200,0.2);
                        border-color: rgba(200,200,200,0.4);
                    }}
                    .calendar-day-date {{
                        font-weight: bold;
                        margin-bottom: 4px;
                        font-size: 11px;
                        text-align: center;
                    }}
                    .calendar-day-dawn,
                    .calendar-day-dusk {{
                        font-size: 10px;
                        opacity: 0.85;
                        text-align: center;
                    }}
                    .calendar-measurement {{
                        margin-top: 6px;
                        padding-top: 6px;
                        border-top: 1px solid rgba(100,100,100,0.15);
                    }}
                    body.dark .calendar-measurement {{
                        border-top-color: rgba(200,200,200,0.15);
                    }}
                    .calendar-measurement-label {{
                        font-size: 10px;
                        font-weight: bold;
                        opacity: 0.9;
                        margin-bottom: 2px;
                    }}
                    .calendar-day-low {{
                        color: #4a90e2;
                        font-size: 11px;
                    }}
                    .calendar-day-high {{
                        color: #d0021b;
                        font-size: 11px;
                    }}
                </style>
            </head>
            <body>
                <div class="top-bar">
                    <button class="toggle-btn" onclick="toggleMode()" title="Toggle Dark/Light Mode">🌓</button>
                </div>
                <div id="stickyTemp" class="sticky-temp">Current Temperature: {temp_f:.1f} °F</div>

                <div class="content">
                    <div class="card latest-card">
                        <h1>Latest Sensor Reading</h1>
                        <div class="timestamp">Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>

                        <div class="readings-grid">
                            <div class="reading-column">
                                <div class="reading">
                                    <span class="icon">🌡️</span>
                                    <span class="label">Temperature:</span>
                                    <span class="temp-value">{temp_f:.1f} °F</span>
                                    <span>( {reading['temperature_c']:.1f} °C )</span>
                                </div>
                                <div class="reading">
                                    <span class="icon">💧</span>
                                    <span class="label">Humidity:</span> {reading['humidity']} %
                                </div>
                                <div class="reading">
                                    <span class="icon">🌅</span>
                                    <span class="label">Dawn:</span> {dawn_time}
                                </div>
                            </div>
                            <div class="reading-column">
                                <div class="reading">
                                    <span class="icon">{lux_icon}</span>
                                    <span class="label">Lux:</span> {lux:.1f}
                                    <span class="lux-desc">{lux_desc}</span>
                                </div>
                                <div class="reading">
                                    <span class="icon">🌪️</span>
                                    <span class="label">Pressure:</span> {reading['pressure']} Pa
                                </div>
                                <div class="reading">
                                    <span class="icon">🌇</span>
                                    <span class="label">Dusk:</span> {dusk_time}
                                </div>
                            </div>
                        </div>

                        <div class="timestamp">Sensor reading on {reading['timestamp']}</div>
                    </div>

                    <div class="charts">
                        <div class="card">
                            <h2>Last 24 Hours (Temperature °F) - Low: {temp_24h_min:.1f}°F, High: {temp_24h_max:.1f}°F</h2>
                            <canvas id="last24Chart"></canvas>
                        </div>

                        <div class="card">
                            <h2>Last 24 Hours (Humidity %) - Low: {humidity_24h_min:.1f}%, High: {humidity_24h_max:.1f}%</h2>
                            <canvas id="last24HumidityChart"></canvas>
                        </div>

                        <div class="card">
                            <h2>Last 24 Hours (Pressure Pa) - Low: {pressure_24h_min:.1f} Pa, High: {pressure_24h_max:.1f} Pa</h2>
                            <canvas id="last24PressureChart"></canvas>
                        </div>

                        <!-- Weekly stacked daily high/low cards (most recent week first) -->
                        {weekly_canvases_html}
                        {humidity_weekly_canvases_html}
                        {pressure_weekly_canvases_html}

                        <!-- Year-to-Date Calendar -->
                        <div class="card">
                            <h2>Year-to-Date Calendar</h2>
                            <div id="ytdCalendar" class="calendar-grid"></div>
                        </div>
                    </div>
                </div>

                <script>
                    function applyMode(mode) {{
                        document.body.className = mode;
                        localStorage.setItem("mode", mode);
                    }}
                    function toggleMode() {{
                        const current = document.body.classList.contains("dark") ? "dark" : "light";
                        applyMode(current === "dark" ? "light" : "dark");
                    }}
                    const saved = localStorage.getItem("mode") || "dark";
                    applyMode(saved);

                    let autoScrollTimer = null;
                    let autoScrollResumeAt = 0;
                    let pendingScrollReset = false;

                    function startAutoScroll() {{
                        const stickyTempEl = document.getElementById('stickyTemp');
                        if (stickyTempEl) {{
                            stickyTempEl.classList.add('show');
                        }}

                        if (autoScrollTimer) {{
                            return;
                        }}

                        const scrollStepPx = 1;
                        const intervalMs = 50;

                        autoScrollTimer = setInterval(() => {{
                            if (pendingScrollReset) {{
                                if (Date.now() < autoScrollResumeAt) {{
                                    return;
                                }}

                                window.scrollTo(0, 0);
                                pendingScrollReset = false;
                                autoScrollResumeAt = 0;
                                return;
                            }}

                            if (Date.now() < autoScrollResumeAt) {{
                                return;
                            }}

                            const atBottom = (window.innerHeight + window.scrollY) >= (document.body.scrollHeight - 2);
                            if (atBottom) {{
                                pendingScrollReset = true;
                                autoScrollResumeAt = Date.now() + 10000;
                            }} else {{
                                window.scrollBy(0, scrollStepPx);
                            }}
                        }}, intervalMs);
                    }}

                    window.addEventListener('load', () => {{
                        setTimeout(startAutoScroll, 10000);
                    }});

                    const last24Labels = {last24_labels_json};
                    const last24Temps = {last24_temps_json};
                    const last24Humidity = {last24_humidity_json};
                    const last24Pressure = {last24_pressure_json};
                    const weeklyData = {weekly_data_json};
                    const humidityWeeklyData = {humidity_weekly_data_json};
                    const pressureWeeklyData = {pressure_weekly_data_json};
                    const calendarData = {calendar_data_json};

                    // Function to render the combined year-to-date calendar
                    function renderCalendar(containerId) {{
                        const container = document.getElementById(containerId);
                        container.innerHTML = '';
                        
                        for (const [dateStr, dayData] of Object.entries(calendarData).sort()) {{
                            const dayDiv = document.createElement('div');
                            dayDiv.className = 'calendar-day';
                            
                            const dateParts = dateStr.split('-');
                            const monthDay = `${{dateParts[1]}}/${{dateParts[2]}}`;
                            let dawnValue = dayData.dawn || 'N/A';
                            let duskValue = dayData.dusk || 'N/A';
                            
                            dayDiv.innerHTML = `
                                <div class="calendar-day-date">${{monthDay}}</div>
                                <div class="calendar-day-dawn">Dawn: ${{dawnValue}}</div>
                                <div class="calendar-measurement">
                                    <div class="calendar-measurement-label">Temperature (°F)</div>
                                    <div class="calendar-day-low">L: ${{dayData.temp_low.toFixed(1)}}</div>
                                    <div class="calendar-day-high">H: ${{dayData.temp_high.toFixed(1)}}</div>
                                </div>
                                <div class="calendar-measurement">
                                    <div class="calendar-measurement-label">Humidity (%)</div>
                                    <div class="calendar-day-low">L: ${{dayData.humidity_low.toFixed(1)}}</div>
                                    <div class="calendar-day-high">H: ${{dayData.humidity_high.toFixed(1)}}</div>
                                </div>
                                <div class="calendar-measurement">
                                    <div class="calendar-measurement-label">Pressure (Pa)</div>
                                    <div class="calendar-day-low">L: ${{dayData.pressure_low.toFixed(1)}}</div>
                                    <div class="calendar-day-high">H: ${{dayData.pressure_high.toFixed(1)}}</div>
                                </div>
                                <div class="calendar-day-dusk">Dusk: ${{duskValue}}</div>
                            `;
                            
                            container.appendChild(dayDiv);
                        }}
                    }}

                    // Render the combined calendar
                    renderCalendar('ytdCalendar');

                    const last24Ctx = document.getElementById('last24Chart').getContext('2d');

                    new Chart(last24Ctx, {{
                        type: 'line',
                        data: {{
                            labels: last24Labels,
                            datasets: [{{
                                label: 'Temperature (°F)',
                                data: last24Temps,
                                borderColor: '#f5a623',
                                backgroundColor: 'rgba(245,166,35,0.2)',
                                tension: 0.3,
                                pointRadius: 4,
                                pointHoverRadius: 6
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            plugins: {{
                                legend: {{ display: true }},
                                tooltip: {{
                                    enabled: true,
                                    mode: 'nearest',
                                    intersect: false
                                }}
                            }},
                            scales: {{
                                x: {{
                                    title: {{ display: true, text: 'Time (last 24h)' }}
                                }},
                                y: {{
                                    title: {{ display: true, text: 'Temperature (°F)' }}
                                }}
                            }}
                        }}
                    }});

                    const last24HumidityCtx = document.getElementById('last24HumidityChart').getContext('2d');

                    new Chart(last24HumidityCtx, {{
                        type: 'line',
                        data: {{
                            labels: last24Labels,
                            datasets: [{{
                                label: 'Humidity (%)',
                                data: last24Humidity,
                                borderColor: '#50e3c2',
                                backgroundColor: 'rgba(80,227,194,0.2)',
                                tension: 0.3,
                                pointRadius: 4,
                                pointHoverRadius: 6
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            plugins: {{
                                legend: {{ display: true }},
                                tooltip: {{
                                    enabled: true,
                                    mode: 'nearest',
                                    intersect: false
                                }}
                            }},
                            scales: {{
                                x: {{
                                    title: {{ display: true, text: 'Time (last 24h)' }}
                                }},
                                y: {{
                                    title: {{ display: true, text: 'Humidity (%)' }}
                                }}
                            }}
                        }}
                    }});

                    const last24PressureCtx = document.getElementById('last24PressureChart').getContext('2d');

                    new Chart(last24PressureCtx, {{
                        type: 'line',
                        data: {{
                            labels: last24Labels,
                            datasets: [{{
                                label: 'Pressure (Pa)',
                                data: last24Pressure,
                                borderColor: '#7ed321',
                                backgroundColor: 'rgba(126,211,33,0.2)',
                                tension: 0.3,
                                pointRadius: 4,
                                pointHoverRadius: 6
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            plugins: {{
                                legend: {{ display: true }},
                                tooltip: {{
                                    enabled: true,
                                    mode: 'nearest',
                                    intersect: false
                                }}
                            }},
                            scales: {{
                                x: {{
                                    title: {{ display: true, text: 'Time (last 24h)' }}
                                }},
                                y: {{
                                    title: {{ display: true, text: 'Pressure (Pa)' }}
                                }}
                            }}
                        }}
                    }});

                    // Render temperature bar charts for each week
                    weeklyData.forEach(w => {{
                        const ctx = document.getElementById(w.id).getContext('2d');
                        new Chart(ctx, {{
                            type: 'bar',
                            data: {{
                                labels: w.labels,
                                datasets: [
                                    {{
                                        label: 'Low (°F)',
                                        data: w.temp_lows,
                                        backgroundColor: 'rgba(74,144,226,0.7)'
                                    }},
                                    {{
                                        label: 'High (°F)',
                                        data: w.temp_highs,
                                        backgroundColor: 'rgba(208,2,27,0.7)'
                                    }}
                                ]
                            }},
                            options: {{
                                responsive: true,
                                plugins: {{ legend: {{ display: true }} }},
                                scales: {{
                                    x: {{ title: {{ display: true, text: 'Day' }} }},
                                    y: {{ title: {{ display: true, text: 'Temperature (°F)' }} }}
                                }}
                            }}
                        }});
                    }});

                    // Render humidity bar charts for each week
                    humidityWeeklyData.forEach(w => {{
                        const ctx = document.getElementById(w.id).getContext('2d');
                        new Chart(ctx, {{
                            type: 'bar',
                            data: {{
                                labels: w.labels,
                                datasets: [
                                    {{
                                        label: 'Low (%)',
                                        data: w.humidity_lows,
                                        backgroundColor: 'rgba(80,227,194,0.7)'
                                    }},
                                    {{
                                        label: 'High (%)',
                                        data: w.humidity_highs,
                                        backgroundColor: 'rgba(0,184,148,0.7)'
                                    }}
                                ]
                            }},
                            options: {{
                                responsive: true,
                                plugins: {{ legend: {{ display: true }} }},
                                scales: {{
                                    x: {{ title: {{ display: true, text: 'Day' }} }},
                                    y: {{ title: {{ display: true, text: 'Humidity (%)' }} }}
                                }}
                            }}
                        }});
                    }});

                    // Render pressure bar charts for each week
                    pressureWeeklyData.forEach(w => {{
                        const ctx = document.getElementById(w.id).getContext('2d');
                        new Chart(ctx, {{
                            type: 'bar',
                            data: {{
                                labels: w.labels,
                                datasets: [
                                    {{
                                        label: 'Low (Pa)',
                                        data: w.pressure_lows,
                                        backgroundColor: 'rgba(126,211,33,0.7)'
                                    }},
                                    {{
                                        label: 'High (Pa)',
                                        data: w.pressure_highs,
                                        backgroundColor: 'rgba(88,214,141,0.7)'
                                    }}
                                ]
                            }},
                            options: {{
                                responsive: true,
                                plugins: {{ legend: {{ display: true }} }},
                                scales: {{
                                    x: {{ title: {{ display: true, text: 'Day' }} }},
                                    y: {{ title: {{ display: true, text: 'Pressure (Pa)' }} }}
                                }}
                            }}
                        }});
                    }});
                </script>
            </body>
            </html>
            """

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

if __name__ == '__main__':
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, Handler)
    print('Serving on port 8000...')
    httpd.serve_forever()
