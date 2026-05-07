# Board configuration — edit this file for your environment

# Wi-Fi
WIFI_SSID     = "<your-ssid>"
WIFI_PASSWORD = "<your-password>"

# I2C
I2C_BUS = 0
I2C_SDA = 0   # GP0
I2C_SCL = 1   # GP1
I2C_FREQ = 400000

# SPI (SD card)
SPI_BUS  = 1
SPI_SCK  = 10  # GP10 — Pin 14
SPI_MOSI = 11  # GP11 — Pin 15
SPI_MISO = 12  # GP12 — Pin 16
SPI_CS   = 13  # GP13 — Pin 17
SPI_BAUD = 1000000

# SD card
SD_MOUNT = '/sd'
SD_LOG_FILE = '/sd/weather.csv'

# Logging
LOG_INTERVAL_S = 900  # 15 minutes

# Status LEDs
LED_HTTP_PIN = 14  # GP14 — Pin 19: on during HTTP client connection
LED_SD_PIN   = 15  # GP15 — Pin 20: on during SD card write
