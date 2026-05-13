# Pico W Weather Station

This folder contains a new, from-scratch MicroPython build for a Raspberry Pi Pico W weather station.

## Project Goal

Build a reliable weather station that reads environmental sensors, stores timestamped readings on a micro SD card, and optionally serves or publishes data over Wi-Fi.

## Hardware Components

- Raspberry Pi Pico W
- SHT31 (temperature + humidity)
- BMP390 (barometric pressure + temperature)
- TSL2591 (light intensity)
- UMLIFE Micro SD SDHC TF Card Adapter (data logging)

## What We Are Building

The final system will:

- Initialize all sensors and validate communication
- Collect readings on a schedule
- Add timestamps (from RTC and/or NTP)
- Write readings to CSV files on micro SD card
- Handle failures safely (sensor retry, log errors, recover gracefully)
- Connect to Wi-Fi for time sync and optional remote status/data access

## Development Approach

We will build in small, testable phases and deploy incrementally from VS Code to the Pico W.

- Edit code in this `pico-w` folder
- Upload changed files to Pico W over USB serial
- Verify each feature before adding the next one

## Planned Build Phases

1. Board + toolchain baseline
- Confirm MicroPython firmware and serial connection
- Validate file upload workflow from VS Code

2. Bus and pin mapping
- Define final I2C and SPI pin assignments
- Confirm all devices can be addressed reliably

3. Sensor bring-up
- Implement and test SHT31 readings
- Implement and test BMP390 readings
- Implement and test TSL2591 readings

4. Wi-Fi + time
- Connect Pico W to Wi-Fi
- Add NTP sync and stable local timestamp handling

5. SD logging
- Mount SD card over SPI
- Create/append CSV logs with headers and rotation policy

6. Runtime loop
- Add scheduler for periodic sampling
- Add structured error handling and retry/backoff behavior

7. Optional serving/publishing
- Local status endpoint or simple web output
- Optional integration for upstream data publishing

## Expected Folder Structure (Initial)

As we implement features, files will be added in this folder. Expected modules include:

- `boot.py` - basic startup behavior
- `main.py` - main runtime loop
- `config.py` - board pins and runtime settings
- `wifi.py` - Wi-Fi and time sync helpers
- `sensors/` - per-sensor drivers/wrappers
- `storage/` - SD mount + CSV log helpers
- `utils/` - shared helpers (time, formatting, retries)

## Design Principles

- Keep modules small and focused
- Fail safely and log useful error details
- Prefer explicit configuration over hidden magic
- Make every phase runnable and testable on-device

## Notes

- Sensor and SD drivers may be vendor-specific; we will validate each with a minimal smoke test before integrating into the full loop.
- The exact pin map and sampling interval will be finalized before writing production runtime logic.
