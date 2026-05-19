# Arduino GIF player (QT Py ESP32-S3 + EYESPI)

## Hardware

- **QT Py ESP32-S3** stacked on **EYESPI BFF**
- **1.28" GC9A01A round TFT** connected by the **ribbon (FPC) cable** to the BFF

SPI goes through the ribbon. The sketch still uses the pin names `TX` and `RX` for **chip select** and **data/command** — that is how the BFF is wired to the QT Py, not a separate UART cable.

## Libraries (Arduino Library Manager)

- Adafruit GC9A01A
- Adafruit GFX Library
- AnimatedGIF (Larry Bank)

Board: **Adafruit QT Py ESP32-S3** (4MB flash / 2MB PSRAM).

## Gift setup

1. Format the display’s microSD as FAT32.
2. Create folder `gifs` on the card.
3. Copy [`assets/sample.gif`](../assets/sample.gif) to `gifs/sample.gif` on the SD card.
4. Open `qtpy_s3_gc9a01a_gif/qtpy_s3_gc9a01a_gif.ino`, upload, power cycle.

On boot you should see a brief green **GIF** splash, then the animation loops.

## If something’s wrong

| Screen | Meaning |
|--------|---------|
| **SD?** (red) | SD card not mounting — reseat card, check FAT32 |
| **No GIF** (yellow) | SD OK but no file at `/gifs/sample.gif` or `/sample.gif` |
| Black / garbage | Try lowering `TFT_SPI_HZ` in the sketch (e.g. `20000000`) |

## Different wiring?

If you are **not** using the EYESPI BFF, change `TFT_CS`, `TFT_DC`, and `SD_CS` at the top of the sketch to match your board.
