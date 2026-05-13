"""Smoke test for SDLogger — writes 2 rows and reads them back."""
from storage.sdlogger import SDLogger
import uos, config

logger = SDLogger()

# Write two test rows
logger.log("2026-05-07T00:00:00", 21.5, 70.7, 48.3, 1013.25, 420.0)
logger.log("2026-05-07T00:01:00", 21.6, 70.9, 48.1, 1013.20, 415.5)
print("Rows written OK")

# Read back and print
logger._mount()
with open(config.SD_LOG_FILE) as f:
    print(f.read())
logger._unmount()
print("Done")
