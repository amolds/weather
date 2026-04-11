import network
import time


class WifiManager:
    def __init__(
        self,
        ssid,
        password,
        reconnect_delay,
        max_reconnect_attempts,
        connect_timeout_s,
        reconnect_wait_s,
        debug=False,
    ):
        self.ssid = ssid
        self.password = password
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        self.connect_timeout_s = connect_timeout_s
        self.reconnect_wait_s = reconnect_wait_s
        self.debug = debug
        self.last_check = 0
        self.reconnect_attempts = 0

    def _new_interface(self):
        wifi = network.WLAN(network.STA_IF)
        wifi.active(True)
        return wifi

    def connect(self):
        wifi = self._new_interface()
        wifi.connect(self.ssid, self.password)

        start = time.time()
        while not wifi.isconnected():
            if time.time() - start > self.connect_timeout_s:
                print("WiFi connection failed")
                break
            time.sleep(0.5)

        print("Connected:", wifi.ifconfig())
        return wifi

    def ensure_connected(self, wifi):
        now = time.time()
        if wifi.isconnected() or (now - self.last_check) <= self.reconnect_delay:
            return wifi

        if self.debug:
            print("WiFi lost, attempting reconnection...")

        if self.reconnect_attempts >= self.max_reconnect_attempts:
            if self.debug:
                print("Too many reconnection failures, recreating WiFi object")
            wifi = self._new_interface()
            self.reconnect_attempts = 0

        wifi.connect(self.ssid, self.password)
        self.last_check = now
        self.reconnect_attempts += 1

        time.sleep(self.reconnect_wait_s)
        if wifi.isconnected():
            if self.debug:
                print("WiFi reconnected:", wifi.ifconfig())
            self.reconnect_attempts = 0
        elif self.debug:
            print(
                "WiFi reconnection failed ({0}/{1}), will retry in {2} seconds".format(
                    self.reconnect_attempts,
                    self.max_reconnect_attempts,
                    self.reconnect_delay,
                )
            )

        return wifi