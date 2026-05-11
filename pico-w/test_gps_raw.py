"""
Simple GT-U7 GPS raw sentence reader for MicroPython.

Reads UART1 (TX=GP4, RX=GP5, 9600 baud) and prints NMEA lines.
Press Ctrl+C to stop.
"""

import time
import machine


UART_ID = 1
BAUDRATE = 9600
TX_PIN = 4
RX_PIN = 5
RUN_SECONDS = 30


def main():
    uart = machine.UART(
        UART_ID,
        baudrate=BAUDRATE,
        tx=machine.Pin(TX_PIN),
        rx=machine.Pin(RX_PIN),
    )

    print("Starting GPS raw read")
    print("UART{} baud={} TX=GP{} RX=GP{}".format(UART_ID, BAUDRATE, TX_PIN, RX_PIN))
    print("Listening for {}s...".format(RUN_SECONDS))

    deadline = time.ticks_add(time.ticks_ms(), RUN_SECONDS * 1000)
    count = 0

    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        if uart.any():
            raw = uart.readline()
            if not raw:
                continue
            try:
                line = raw.decode("ascii", "ignore").strip()
            except Exception:
                continue
            if not line:
                continue
            print(line)
            count += 1
        else:
            time.sleep_ms(100)

    print("Done. Lines received: {}".format(count))


if __name__ == "__main__":
    main()
