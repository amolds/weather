import gc
import time
import machine

from bme280 import BME280
from bh1750 import BH1750

try:
    import _thread
except ImportError:
    _thread = None


class SensorCache:
    def __init__(
        self,
        scl_pin,
        sda_pin,
        read_interval_ms,
        init_retry_ms,
        stale_tolerance_ms,
        hang_tolerance_ms,
        debug=False,
    ):
        self.scl_pin = scl_pin
        self.sda_pin = sda_pin
        self.read_interval_ms = read_interval_ms
        self.init_retry_ms = init_retry_ms
        self.stale_tolerance_ms = stale_tolerance_ms
        self.hang_tolerance_ms = hang_tolerance_ms
        self.debug = debug
        self.thread_supported = _thread is not None
        self.lock = _thread.allocate_lock() if self.thread_supported else None
        self.state = {
            "temperature_c": None,
            "pressure_pa": None,
            "humidity_pct": None,
            "lux": None,
            "last_success_ticks_ms": None,
            "last_attempt_ticks_ms": None,
            "last_completion_ticks_ms": None,
            "last_error": "Sensor thread not started",
            "read_count": 0,
            "failure_count": 0,
            "read_in_progress": False,
            "thread_running": False,
            "thread_available": self.thread_supported,
        }
        self.devices = {
            "i2c": None,
            "bme": None,
            "bh": None,
        }
        self.next_poll_ticks_ms = 0

    def _update_state(self, **changes):
        if self.lock is None:
            self.state.update(changes)
            return

        self.lock.acquire()
        try:
            self.state.update(changes)
        finally:
            self.lock.release()

    def get_snapshot(self):
        if self.lock is None:
            return dict(self.state)

        self.lock.acquire()
        try:
            return dict(self.state)
        finally:
            self.lock.release()

    def _ensure_devices(self):
        if self.devices["i2c"] is None or self.devices["bme"] is None or self.devices["bh"] is None:
            i2c = machine.I2C(scl=machine.Pin(self.scl_pin), sda=machine.Pin(self.sda_pin))
            self.devices["i2c"] = i2c
            self.devices["bme"] = BME280(i2c=i2c)
            self.devices["bh"] = BH1750(i2c)

    def _reset_devices(self):
        self.devices["i2c"] = None
        self.devices["bme"] = None
        self.devices["bh"] = None

    def get_health(self, snapshot=None):
        if snapshot is None:
            snapshot = self.get_snapshot()

        now_ticks = time.ticks_ms()
        last_success_ticks_ms = snapshot.get("last_success_ticks_ms")
        last_attempt_ticks_ms = snapshot.get("last_attempt_ticks_ms")

        if last_success_ticks_ms is None:
            last_success_age_ms = None
        else:
            last_success_age_ms = time.ticks_diff(now_ticks, last_success_ticks_ms)

        if last_attempt_ticks_ms is None:
            last_attempt_age_ms = None
        else:
            last_attempt_age_ms = time.ticks_diff(now_ticks, last_attempt_ticks_ms)

        read_in_progress = snapshot.get("read_in_progress", False)
        data_is_stale = last_success_age_ms is None or last_success_age_ms > self.stale_tolerance_ms
        read_appears_hung = (
            read_in_progress
            and last_attempt_age_ms is not None
            and last_attempt_age_ms > self.hang_tolerance_ms
        )

        return {
            "last_success_age_ms": last_success_age_ms,
            "last_attempt_age_ms": last_attempt_age_ms,
            "data_is_stale": data_is_stale,
            "read_appears_hung": read_appears_hung,
        }

    def sample_once(self):
        now_ticks = time.ticks_ms()
        snapshot = self.get_snapshot()
        self._update_state(last_attempt_ticks_ms=now_ticks, read_in_progress=True)

        try:
            self._ensure_devices()

            temperature_c, pressure_pa, humidity_pct = self.devices["bme"].read_compensated()
            lux = self.devices["bh"].luminance()

            self._update_state(
                temperature_c=temperature_c,
                pressure_pa=pressure_pa,
                humidity_pct=humidity_pct,
                lux=lux,
                last_success_ticks_ms=now_ticks,
                last_completion_ticks_ms=time.ticks_ms(),
                last_error=None,
                read_count=snapshot["read_count"] + 1,
                failure_count=0,
                read_in_progress=False,
            )

            if self.debug:
                print("Sensor cache refreshed")

            return True

        except Exception as e:
            self._update_state(
                last_error=str(e),
                last_completion_ticks_ms=time.ticks_ms(),
                failure_count=snapshot["failure_count"] + 1,
                read_in_progress=False,
            )
            self._reset_devices()

            if self.debug:
                print("Sensor background read error:", e)

            return False

    def mark_hung(self):
        self._update_state(last_error="Sensor read exceeded hang tolerance")

    def _reader_loop(self):
        self._update_state(thread_running=True, last_error=None)

        while True:
            if self.sample_once():
                time.sleep_ms(self.read_interval_ms)
            else:
                time.sleep_ms(self.init_retry_ms)

            gc.collect()

    def start(self):
        if self.thread_supported:
            _thread.start_new_thread(self._reader_loop, ())
        else:
            self._update_state(last_error="_thread is unavailable on this firmware")

    def poll(self):
        if self.thread_supported:
            return

        now_ticks = time.ticks_ms()
        if time.ticks_diff(now_ticks, self.next_poll_ticks_ms) < 0:
            return

        if self.sample_once():
            self.next_poll_ticks_ms = time.ticks_add(now_ticks, self.read_interval_ms)
        else:
            self.next_poll_ticks_ms = time.ticks_add(now_ticks, self.init_retry_ms)