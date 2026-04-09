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

def get_daily_high_low():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            CAST(Timestamp AS date) AS Day,
            MIN(Temperature) AS LowTemp,
            MAX(Temperature) AS HighTemp
        FROM SensorReadings
        GROUP BY CAST(Timestamp AS date)
        ORDER BY Day ASC
    """)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    labels = []
    lows_f = []
    highs_f = []

    for day, low_c, high_c in rows:
        labels.append(day.strftime("%Y-%m-%d"))
        lows_f.append(c_to_f(float(low_c)))
        highs_f.append(c_to_f(float(high_c)))

    return labels, lows_f, highs_f

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

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        reading = get_latest_reading()

        if not reading:
            html = "<h1>No readings found</h1>"
        else:
            temp_f = reading["temperature_f"]
            temp_color = temperature_color_f(temp_f)

            last24_labels, last24_temps_f = get_last_24h_temps()
            daily_labels, daily_lows_f, daily_highs_f = get_daily_high_low()

            last24_labels_json = json.dumps(last24_labels)
            last24_temps_json = json.dumps(last24_temps_f)
            daily_labels_json = json.dumps(daily_labels)
            daily_lows_json = json.dumps(daily_lows_f)
            daily_highs_json = json.dumps(daily_highs_f)

            lux = reading["lux"]
            lux_icon, lux_desc = lux_icon_and_label(lux)

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
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
                    }}
                    .toggle-btn {{
                        padding: 8px 16px;
                        border-radius: 20px;
                        border: none;
                        cursor: pointer;
                        font-size: 14px;
                        background: rgba(255,255,255,0.8);
                        transition: background 0.3s;
                    }}
                    body.dark .toggle-btn {{
                        background: rgba(50,50,50,0.8);
                        color: #e0e0e0;
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
                    .reading {{
                        font-size: 20px;
                        margin: 10px 0;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        gap: 10px;
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
                    }}
                    .charts {{
                        display: grid;
                        grid-template-columns: 1fr;
                        gap: 20px;
                    }}
                    @media (min-width: 900px) {{
                        .charts {{
                            grid-template-columns: 1fr 1fr;
                        }}
                    }}
                    canvas {{
                        width: 100% !important;
                        height: 300px !important;
                    }}
                </style>
            </head>
            <body>
                <div class="top-bar">
                    <button class="toggle-btn" onclick="toggleMode()">Toggle Mode</button>
                </div>

                <div class="content">
                    <div class="card latest-card">
                        <h1>Latest Sensor Reading</h1>

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
                            <span class="icon">{lux_icon}</span>
                            <span class="label">Lux:</span> {lux:.1f}
                        </div>
                        <div class="lux-desc">{lux_desc}</div>

                        <div class="reading">
                            <span class="label">Pressure:</span> {reading['pressure']} Pa
                        </div>

                        <div class="timestamp">Timestamp: {reading['timestamp']}</div>
                    </div>

                    <div class="charts">
                        <div class="card">
                            <h2>Last 24 Hours (Temperature °F)</h2>
                            <canvas id="last24Chart"></canvas>
                        </div>

                        <div class="card">
                            <h2>Daily High / Low (Temperature °F)</h2>
                            <canvas id="dailyChart"></canvas>
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
                    const saved = localStorage.getItem("mode") || "light";
                    applyMode(saved);

                    const last24Labels = {last24_labels_json};
                    const last24Temps = {last24_temps_json};
                    const dailyLabels = {daily_labels_json};
                    const dailyLows = {daily_lows_json};
                    const dailyHighs = {daily_highs_json};

                    const last24Ctx = document.getElementById('last24Chart').getContext('2d');
                    const dailyCtx = document.getElementById('dailyChart').getContext('2d');

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
                                pointRadius: 2
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            plugins: {{
                                legend: {{ display: true }}
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

                    new Chart(dailyCtx, {{
                        type: 'bar',
                        data: {{
                            labels: dailyLabels,
                            datasets: [
                                {{
                                    label: 'Low (°F)',
                                    data: dailyLows,
                                    backgroundColor: 'rgba(74,144,226,0.7)'
                                }},
                                {{
                                    label: 'High (°F)',
                                    data: dailyHighs,
                                    backgroundColor: 'rgba(208,2,27,0.7)'
                                }}
                            ]
                        }},
                        options: {{
                            responsive: true,
                            plugins: {{
                                legend: {{ display: true }}
                            }},
                            scales: {{
                                x: {{
                                    title: {{ display: true, text: 'Day' }}
                                }},
                                y: {{
                                    title: {{ display: true, text: 'Temperature (°F)' }}
                                }}
                            }}
                        }}
                    }});
                </script>
            </body>
            </html>
            """

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

def run():
    server = HTTPServer(("0.0.0.0", 8080), Handler)
    print("Server running on port 8080")
    server.serve_forever()

if __name__ == "__main__":
    run()

