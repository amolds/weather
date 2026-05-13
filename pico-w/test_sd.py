import machine
import sdcard
import uos

# SPI1 pins
spi = machine.SPI(1,
    baudrate=100000,
    polarity=0,
    phase=0,
    bits=8,
    firstbit=machine.SPI.MSB,
    sck=machine.Pin(10),
    mosi=machine.Pin(11),
    miso=machine.Pin(12))

cs = machine.Pin(13, machine.Pin.OUT)

try:
    sd = sdcard.SDCard(spi, cs)
    vfs = uos.VfsFat(sd)
    uos.mount(vfs, '/sd')
    print("SD card mounted OK")
    print("Contents:", uos.listdir('/sd'))
    uos.umount('/sd')
    print("SD card unmounted cleanly")
except Exception as e:
    print("SD card error:", e)
