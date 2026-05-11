"""
Simple NMEA GPS reader for GT-U7 style modules.

Parses only RMC sentences and exposes latest decimal coordinates
when a valid fix is available.
"""

import machine


class GPS:
    def __init__(self, uart_id=1, tx_pin=4, rx_pin=5, baudrate=9600):
        self._uart = machine.UART(
            uart_id,
            baudrate=baudrate,
            tx=machine.Pin(tx_pin),
            rx=machine.Pin(rx_pin),
        )
        self._lat = None
        self._lng = None
        self._time = None
        self._date = None
        self._has_fix = False

    def update(self, max_sentences=20):
        """Read and parse up to max_sentences available UART lines."""
        for _ in range(max_sentences):
            if not self._uart.any():
                break
            raw = self._uart.readline()
            if not raw:
                continue
            try:
                line = raw.decode("ascii", "ignore").strip()
            except Exception:
                continue
            if line:
                self._parse_rmc(line)

    def get_position(self):
        """Return latest GPS fix dict or None if no valid fix yet."""
        if not self._has_fix:
            return None
        return {
            "latitude": self._lat,
            "longitude": self._lng,
            "time": self._time,
            "date": self._date,
        }

    def _parse_rmc(self, sentence):
        if not (sentence.startswith("$GPRMC") or sentence.startswith("$GNRMC")):
            return

        parts = sentence.split(",")
        if len(parts) < 10:
            return

        # RMC status: A=valid, V=warning/invalid
        status = parts[2]
        if status != "A":
            self._has_fix = False
            return

        lat_raw = parts[3]
        lat_hemi = parts[4]
        lng_raw = parts[5]
        lng_hemi = parts[6]
        utc_time = parts[1]
        utc_date = parts[9].split("*")[0]

        if not lat_raw or not lng_raw or not lat_hemi or not lng_hemi:
            self._has_fix = False
            return

        lat = self._nmea_to_decimal(lat_raw, lat_hemi)
        lng = self._nmea_to_decimal(lng_raw, lng_hemi)
        if lat is None or lng is None:
            self._has_fix = False
            return

        self._lat = lat
        self._lng = lng
        self._time = utc_time
        self._date = utc_date
        self._has_fix = True

    def _nmea_to_decimal(self, raw, hemisphere):
        try:
            # Latitude uses DDMM.MMMM, longitude uses DDDMM.MMMM.
            if hemisphere in ("N", "S"):
                deg_len = 2
            elif hemisphere in ("E", "W"):
                deg_len = 3
            else:
                return None

            degrees = int(raw[:deg_len])
            minutes = float(raw[deg_len:])
            decimal = degrees + (minutes / 60.0)
            if hemisphere in ("S", "W"):
                decimal = -decimal
            return decimal
        except Exception:
            return None
