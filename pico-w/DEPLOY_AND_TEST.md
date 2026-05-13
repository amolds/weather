# Pico W Deploy and Test Workflow

This document defines the standard workflow for uploading scripts to the Raspberry Pi Pico W and verifying they run correctly.

## Preconditions

- Pico W is connected over USB.
- MicroPython firmware is installed on the Pico W.
- Python 3 is available on macOS.
- `mpremote` is installed:

```bash
python3 -m pip install --user mpremote
```

## Why We Use `python3 -m mpremote`

`mpremote` may install outside your shell PATH on macOS. Running it as a Python module is reliable and avoids PATH issues.

## 1. Confirm Pico Serial Port

```bash
ls /dev/tty.usbmodem*
```

Expected example output:

```text
/dev/tty.usbmodem214401
```

## 2. Upload a Script to the Pico Filesystem

From this folder (`pico-w`), copy a local script to the device:

```bash
python3 -m mpremote connect /dev/tty.usbmodem214401 fs cp hello-world.py :hello-world.py
```

## 3. Execute the Script on the Pico

```bash
python3 -m mpremote connect /dev/tty.usbmodem214401 exec "exec(open('hello-world.py').read())"
```

Expected output:

```text
Hello from Raspberry Pi Pico W!
```

## 4. Optional: List Device Files

```bash
python3 -m mpremote connect /dev/tty.usbmodem214401 fs ls
```

## Common Issue: Port In Use

If you get:

```text
mpremote: failed to access /dev/tty.usbmodem214401 (it may be in use by another program)
```

Find the locking process:

```bash
lsof /dev/tty.usbmodem214401
```

If `screen` is holding the port, stop it using its PID:

```bash
kill <PID>
```

Then rerun upload and execute commands.

## Optional PATH Fix (Quality of Life)

If you want to run `mpremote` directly without `python3 -m`:

```bash
echo 'export PATH="$HOME/Library/Python/3.14/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## Recommended Development Pattern

- Edit scripts locally in `pico-w`.
- Upload only changed files.
- Run quick on-device tests after each change.
- Keep tests small and focused while building features incrementally.
