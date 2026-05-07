"""
server/http.py — Minimal HTTP server for the weather station.

Runs on core 1. Reads the shared `state` dict (protected by a lock)
and serves the latest sensor reading as JSON on port 80.

Endpoints:
  GET /          -> JSON of latest reading
  GET /data      -> same
  anything else  -> 404
"""

import socket


_HTML_TEMPLATE = """\
HTTP/1.0 200 OK\r
Content-Type: application/json\r
Connection: close\r
\r
{}\
"""

_NOT_FOUND = """\
HTTP/1.0 404 Not Found\r
Content-Type: text/plain\r
Connection: close\r
\r
Not Found\
"""


def _make_json(state, lock):
    lock.acquire()
    try:
        d = dict(state)
    finally:
        lock.release()

    if not d:
        return '{"error":"no data yet"}'

    return (
        '{{'
        '"timestamp":"{timestamp}",'
        '"temp_c":{temp_c:.2f},'
        '"temp_f":{temp_f:.2f},'
        '"humidity":{humidity:.1f},'
        '"pressure_hpa":{pressure:.2f},'
        '"lux":{lux:.1f}'
        '}}'
    ).format(**d)


def serve(state, lock, port=80, led=None):
    """Block forever serving HTTP requests. Run this on core 1."""
    addr = socket.getaddrinfo('0.0.0.0', port)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)
    print("HTTP server listening on port", port)

    while True:
        conn = None
        try:
            conn, _ = s.accept()
            conn.settimeout(3)
            request = conn.recv(1024).decode('utf-8', 'ignore')
            first_line = request.split('\r\n')[0] if request else ''
            path = first_line.split(' ')[1] if len(first_line.split(' ')) > 1 else '/'

            if path in ('/', '/data'):
                if led:
                    led.on()
                body = _make_json(state, lock)
                conn.send(_HTML_TEMPLATE.format(body))
                if led:
                    led.off()
            else:
                conn.send(_NOT_FOUND)
        except Exception as e:
            print("HTTP error:", e)
            if led:
                led.off()
        finally:
            if conn:
                conn.close()
