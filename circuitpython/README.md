# QT Py S3 + GC9A01A (EYESPI) CircuitPython GIF Player

## Hardware specs (this project’s target)
- **MCU**: Adafruit **QT Py ESP32‑S3** (4MB flash + **2MB PSRAM**) (PID 5700)
- **Display**: Adafruit **1.28\" Round TFT** — **240×240**, **GC9A01A**, SPI, EYESPI + microSD (PID 6178)
- **Connector**: Adafruit **EYESPI BFF for QT Py / Xiao** (PID 5772)

## Default pin mapping (EYESPI BFF)
Per the EYESPI BFF defaults:
- **TFT CS** → `TX`
- **TFT DC** → `RX`
- **SD CS** → `A3`
- **SPI SCK/MOSI/MISO** → QT Py’s default SPI pins
- **Reset / Backlight** are optional (not used by default in this repo)

## Copy-to-CIRCUITPY deploy (drop-in)
1) Flash CircuitPython for **QT Py ESP32‑S3 4MB Flash 2MB PSRAM**.
2) Copy this folder’s contents onto the `CIRCUITPY` drive:
   - `code.py`
   - `settings.toml`
   - `lib/adafruit_gc9a01a.py`
3) Put a test GIF at `CIRCUITPY/sample.gif` (you can use `assets/sample.gif` from this repo).

If you have a microSD in the TFT breakout:
- Create `/gifs` on the SD card and put `.gif` files inside.
- The player will try to mount SD at `/sd` and play from `/sd/gifs` first.
  - For the Arduino sketch, copy `assets/sample.gif` to the SD card as `/gifs/sample.gif`.

## Settings
Edit `settings.toml`:
- `SPI_BAUDRATE`: lower if you see instability (e.g. `24000000`)
- `SD_GIF_DIR`: where GIFs live on SD (default `/sd/gifs`)
- `CIRCUITPY_GIF`: fallback single GIF path (default `/sample.gif`)

## Troubleshooting
- **Black screen**: often backlight. This build assumes backlight is handled by the display breakout defaults.
- **Boots into safe mode / crashes**: reduce `SPI_BAUDRATE`.
- **Nothing plays**: ensure either `/sample.gif` exists on `CIRCUITPY` or SD mounts and `/sd/gifs` contains `.gif` files.

