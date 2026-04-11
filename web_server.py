import gc
import json
import socket
import time


class SensorHttpServer:
    def __init__(
        self,
        sensor_cache,
        host,
        port,
        accept_timeout_s,
        client_timeout_s,
        debug=False,
    ):
        self.sensor_cache = sensor_cache
        self.host = host
        self.port = port
        self.accept_timeout_s = accept_timeout_s
        self.client_timeout_s = client_timeout_s
        self.debug = debug
        self.socket = None

    def start(self):
        addr = socket.getaddrinfo(self.host, self.port)[0][-1]
        server_socket = socket.socket()
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(addr)
        server_socket.listen(1)
        server_socket.settimeout(self.accept_timeout_s)
        self.socket = server_socket
        print("Listening on", addr)

    def accept(self):
        try:
            return self.socket.accept()
        except OSError:
            gc.collect()
            time.sleep_ms(50)
            return None, None

    def _build_payload(self):
        snapshot = self.sensor_cache.get_snapshot()
        sensor_health = self.sensor_cache.get_health(snapshot)
        sensor_mode = "threaded" if snapshot.get("thread_available") else "polled"
        temperature_c = snapshot.get("temperature_c")
        pressure_pa = snapshot.get("pressure_pa")
        humidity_pct = snapshot.get("humidity_pct")
        lux = snapshot.get("lux")
        last_success_age_ms = sensor_health["last_success_age_ms"]
        last_attempt_age_ms = sensor_health["last_attempt_age_ms"]
        data_is_stale = sensor_health["data_is_stale"]
        read_appears_hung = sensor_health["read_appears_hung"]

        data = {
            "temperature_c": temperature_c,
            "pressure_pa": pressure_pa,
            "humidity_pct": humidity_pct,
            "lux": lux,
            "sensor_thread_running": snapshot.get("thread_running"),
            "sensor_thread_available": snapshot.get("thread_available"),
            "sensor_mode": sensor_mode,
            "sensor_reads_completed": snapshot.get("read_count"),
            "sensor_failures": snapshot.get("failure_count"),
            "sensor_read_in_progress": snapshot.get("read_in_progress"),
            "last_sensor_success_age_ms": last_success_age_ms,
            "last_sensor_attempt_age_ms": last_attempt_age_ms,
            "last_sensor_error": snapshot.get("last_error"),
            "sensor_data_stale": data_is_stale,
            "sensor_read_appears_hung": read_appears_hung,
            "uptime_seconds": int(time.time()),
            "memory_free_bytes": gc.mem_free(),
            "memory_allocated_bytes": gc.mem_alloc(),
        }

        if temperature_c is not None and pressure_pa is not None and humidity_pct is not None and lux is not None and not data_is_stale:
            return "HTTP/1.1 200 OK", data

        if temperature_c is None or pressure_pa is None or humidity_pct is None or lux is None:
            data["error"] = "No cached sensor data available"
        elif read_appears_hung:
            data["error"] = "Sensor read exceeded hang tolerance"
        else:
            data["error"] = "Cached sensor data is stale"

        return "HTTP/1.1 503 Service Unavailable", data

    def handle_client(self, client):
        try:
            client.settimeout(self.client_timeout_s)

            try:
                request = client.recv(1024)
            except OSError:
                if self.debug:
                    print("Request timeout")
                return False

            if not request:
                if self.debug:
                    print("Empty request")
                return False

            try:
                request = request.decode()
            except Exception as e:
                if self.debug:
                    print("Decode error:", e)
                return False

            if self.debug:
                print("Request:", request[:50])

            http_status, payload = self._build_payload()
            body = json.dumps(payload)
            response = (
                http_status + "\r\n"
                + "Content-Type: application/json\r\n"
                + "Connection: close\r\n"
                + "Content-Length: {0}\r\n".format(len(body))
                + "\r\n"
                + body
            )

            try:
                client.send(response.encode())
            except Exception as e:
                if self.debug:
                    print("Send error:", e)
                return False

            return True

        except Exception as e:
            if self.debug:
                print("Unexpected error:", e)
            return False

        finally:
            try:
                client.close()
            except Exception:
                pass