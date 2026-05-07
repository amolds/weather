from machine import I2C, Pin

# I2C0 - SDA=GP0, SCL=GP1
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)

devices = i2c.scan()

if devices:
    print("I2C devices found:")
    for addr in devices:
        print("  0x{:02X}".format(addr))
else:
    print("No I2C devices found - check wiring")

# Quick sanity check for expected sensor addresses
EXPECTED = {
    0x44: "SHT31",
    0x29: "TSL2591",
    0x77: "BMP390",
    0x76: "BMP390 (alt)",
}

print()
for addr, name in EXPECTED.items():
    status = "OK" if addr in devices else "NOT FOUND"
    print("  {} (0x{:02X}) ... {}".format(name, addr, status))
