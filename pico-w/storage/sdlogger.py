"""
SD card CSV logger.

Usage:
    from storage.sdlogger import SDLogger
    logger = SDLogger()
    logger.log(timestamp, temp_c, temp_f, humidity, pressure, lux, gps_data=None)
    logger.close()

The logger mounts the SD card on first use, writes a header row if the
file is new, appends a data row, then flushes and unmounts cleanly.
"""

import machine
import sdcard
import uos
import config


_HEADER = "site_name,timestamp,temp_c,temp_f,humidity,pressure_hpa,lux,latitude,longitude,gps_time,gps_date\n"


class SDLogger:
    def __init__(self, led=None):
        self._spi = machine.SPI(
            config.SPI_BUS,
            baudrate=config.SPI_BAUD,
            polarity=0, phase=0, bits=8,
            firstbit=machine.SPI.MSB,
            sck=machine.Pin(config.SPI_SCK),
            mosi=machine.Pin(config.SPI_MOSI),
            miso=machine.Pin(config.SPI_MISO),
        )
        self._cs = machine.Pin(config.SPI_CS, machine.Pin.OUT)
        self._mounted = False
        self._led = led

    def _mount(self):
        if not self._mounted:
            sd = sdcard.SDCard(self._spi, self._cs)
            vfs = uos.VfsFat(sd)
            uos.mount(vfs, config.SD_MOUNT)
            self._mounted = True

    def _unmount(self):
        if self._mounted:
            uos.umount(config.SD_MOUNT)
            self._mounted = False

    def log(self, timestamp, temp_c, temp_f, humidity, pressure, lux, gps_data=None):
        """Append one row to the CSV file on the SD card."""
        if self._led:
            self._led.on()
        try:
            self._mount()
            path = config.SD_LOG_FILE
            # Write header only if file does not exist yet
            try:
                uos.stat(path)
                new_file = False
            except OSError:
                new_file = True

            with open(path, 'a') as f:
                if new_file:
                    f.write(_HEADER)
                lat = ""
                lng = ""
                gps_time = ""
                gps_date = ""
                if gps_data:
                    lat = gps_data.get("latitude", "")
                    lng = gps_data.get("longitude", "")
                    gps_time = gps_data.get("time", "")
                    gps_date = gps_data.get("date", "")

                row = "{},{},{:.2f},{:.2f},{:.1f},{:.2f},{:.1f},{},{},{},{}\n".format(
                    config.HOSTNAME, timestamp, temp_c, temp_f, humidity, pressure, lux,
                    lat, lng, gps_time, gps_date
                )
                f.write(row)
            self._unmount()
        finally:
            if self._led:
                self._led.off()

    def close(self):
        """Ensure the SD card is unmounted."""
        self._unmount()
