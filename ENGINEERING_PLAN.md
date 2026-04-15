## Overview

This repo’s **primary target is now QT Py ESP32‑S3 + CircuitPython** (see `circuitpython/README.md`).

This document describes the **legacy Raspberry Pi/Linux** architecture and wiring assumptions from the earlier version of the project:

- Reads `.gif` files from the **microSD card** on the Adafruit GC9A01A round TFT breakout (mounted by Linux).
- Displays GIFs on a **240×240 SPI TFT (GC9A01A)**.
- Provides **two physical buttons**: next / previous GIF.
- Auto-advances to the next GIF on a timer (target: **once every 5 seconds** as an initial baseline).
- Optionally exposes a **modern web UI (React/TypeScript)** as a control panel.

This document is the **source of truth** for architecture, wiring, configuration surfaces, milestones, and known risks. We expect the plan to evolve as hardware changes.

## References

- **Display breakout**: Adafruit 1.28" 240×240 Round TFT LCD Display with microSD - GC9A01A with EYESPI Connector (product 6178 wiring image: `https://cdn-shop.adafruit.com/product-files/6178/round+TFT+1.28in+GC9A01.png`)
- **Connector board**: Adafruit EYESPI BFF for QT Py or Xiao - 18 Pin FPC Connector (product 5772: `https://www.adafruit.com/product/5772`)
- **Adafruit driver ecosystem (related, but not GC9A01A-specific)**: `https://github.com/adafruit/Adafruit_CircuitPython_RGB_Display`

## Hardware Plan

### Target hardware (v0)

- **Host**: Raspberry Pi (tested assumptions: Pi 3/4/5 class, Linux with SPI enabled).
- **Display**: GC9A01A 240×240 round TFT breakout with microSD and EYESPI connector (Adafruit 6178).
- **Connector**: EYESPI BFF board (Adafruit 5772) to simplify wiring/connectorization.
- **Input**: 2 momentary push-buttons (normally-open).

### Display electrical interface (from the wiring image)

From `round+TFT+1.28in+GC9A01.png` the panel’s functional signals include:

- **Power**: `VDD (3.3V)` and multiple `GND`
- **SPI**: `SCL` (SPI clock / SCK), `SDA` (SPI MOSI)
- **Control**: `CS`, `D/C`, `RESET`
- **Backlight**: `LEDA` / `LEDK`

Notes:

- The panel itself does **not require MISO** for display updates (write-only is sufficient).
- microSD is separate from the TFT controller and is exposed via the breakout; the OS is responsible for mounting it.

### Raspberry Pi pin mapping (default assumptions)

We will use **SPI0** (hardware SPI) on the Pi:

- **SCK**: SPI0 SCLK (BCM 11, physical pin 23)
- **MOSI**: SPI0 MOSI (BCM 10, physical pin 19)
- **CS**: SPI0 CE0 (BCM 8, physical pin 24) by default

Additional control pins (BCM numbering; defaults are configurable):

- **D/C**: BCM 25
- **RESET**: BCM 24
- **Backlight**: BCM 18 (optional; can be hardwired to 3V3)

Buttons (BCM numbering; defaults are configurable):

- **NEXT**: BCM 17
- **PREV**: BCM 27

Button wiring guidance:

- Wire each button between the GPIO pin and **GND**.
- Use internal pull-ups (`GPIO.PUD_UP`) and trigger on falling edge.

### SD card mounting assumptions

- Linux auto-mounts removable media under a distro-specific path.
- Our app will treat the microSD as a **directory containing GIFs**.
- Default expected directory (configurable): `/media/pi/GIFS`

We may later add:

- Auto-discovery of mount points
- Optional “hot reload” when the card content changes (inotify-based)

## Software Plan

### High-level architecture

We split the system into three layers:

- **Application layer**: playlist, selection state, “play once every N seconds”, next/prev behavior.
- **Hardware abstraction layer**: display driver + button driver.
- **Control/UI layer (optional)**: HTTP API + React/TypeScript UI.

### Display driver strategy (hybrid, portable + performance)

We will support two interchangeable display backends behind a common interface:

- **Backend A: Blinka/Adafruit ecosystem driver (portable path)**
  - Uses `board` / `busio` / `digitalio` when running on supported hardware.
  - Intended benefit: portability across boards, consistent APIs, lower maintenance.
  - Constraint: Must have a GC9A01A-compatible driver package; the referenced Adafruit RGB Display repo lists support for other controllers and is not a GC9A01A driver by itself.

- **Backend B: Direct `spidev` + `RPi.GPIO` (fast-path)**
  - Used when we need maximum throughput and predictable full-frame updates.
  - Works even when Blinka driver support is incomplete.

Selection mechanism:

- Environment or config switch (e.g., `DISPLAY_DRIVER=blinka_gc9a01a|spidev_gc9a01a|mock`)
- Our current repo already includes a “mock display” path for laptop/dev usage.

Common interface (conceptual):

- `open()`
- `close()`
- `set_backlight(on: bool)`
- `blit_rgb565(frame_bytes: bytes)` where `frame_bytes` is full-frame, big-endian RGB565

### GIF decoding + rendering

- Decode GIF frames with **Pillow** (`PIL.ImageSequence.Iterator`).
- For each frame:
  - Convert to RGB
  - Center-crop/scale to 240×240 (preserving aspect ratio)
  - Convert to RGB565 bytes
  - Send to display via `blit_rgb565()`
- Respect GIF frame timing via `frame.info["duration"]` (ms) with safety clamps.

Important performance note:

- Full-frame update is `240×240×2 = 115,200` bytes per frame (~112.5 KiB).
- With SPI at ~62.5 MHz theoretical, raw transfer time is small; real-world overhead comes from Python frame conversion + SPI driver overhead.
- If needed, we can later:
  - Pre-decode and cache frames (RAM tradeoff)
  - Use NumPy for faster RGB565 conversion
  - Use partial updates (rarely worth it for GIFs)

### Playback + controls

- Default behavior: **advance to next GIF every 5 seconds**.
- Buttons:
  - NEXT increments index (wrap-around)
  - PREV decrements index (wrap-around)
  - On selection change: play immediately (configurable)
- The player loop should:
  - Keep running even if the SD card is temporarily empty/unmounted
  - Recover from bad/corrupt GIFs (skip with error reporting)

### Web UI (optional, modern control plane)

We will treat the React UI as a “control panel” rather than a display pipeline:

- Backend (Python) exposes an HTTP API:
  - `GET /api/status`
  - `GET /api/gifs`
  - `POST /api/next`
  - `POST /api/prev`
  - `POST /api/select/{index}`
  - `POST /api/rescan`
- Frontend (React/TypeScript):
  - Shows list of GIFs
  - Shows currently selected GIF name/index
  - Provides next/prev buttons
  - Optional settings panel (timer seconds, driver selection, brightness)

Rationale:

- Playback and GPIO should work standalone with no browser.
- UI is strictly additive and should never be required for core operation.

## Configuration Plan

### Configuration sources (order of precedence)

Initial approach:

- Defaults in `backend/config.py`
- Environment variable overrides (for deploy convenience)
- Later: a persisted config file (e.g., `config.toml`) stored on the SD card or `/etc/gif-player/`

### Key configuration knobs (v0)

- **GIF directory**: `gif_dir`
- **Auto-advance**: `advance_every_s`
- **Button pins**: `gpio_btn_next`, `gpio_btn_prev`, `button_bounce_ms`
- **SPI**: `spi_bus`, `spi_device`, `spi_hz`
- **Display pins**: `gpio_dc`, `gpio_rst`, `gpio_bl`
- **Geometry**: `width`, `height` (fixed 240×240 for this display family)

## Milestones

### Milestone 0 — “Hello, pixels”

- Verify SPI wiring and bring up the panel (fill screen, color bars).
- Validate `RESET` and `D/C` behavior.
- Confirm backlight control if wired.

### Milestone 1 — “GIF plays once”

- Load a single known-good GIF from SD mount directory.
- Decode + render frames to display with correct timing.

### Milestone 2 — “Playlist + buttons”

- Directory scan → ordered GIF list.
- Auto-advance every N seconds.
- NEXT/PREV physical buttons interrupt playback and switch selection.

### Milestone 3 — “Service + UI”

- Add a lightweight HTTP API.
- Add React/TypeScript UI for selection and status.
- Deployable service model (systemd unit) documented.

### Milestone 4 — “Hardening”

- Handle corrupt GIFs gracefully (skip/report).
- Handle SD unmount/remount with rescan.
- Add logging, metrics, and a basic health endpoint.

## Testing Plan

### Hardware tests

- SPI signal integrity: stable display updates at target SPI clock; reduce Hz if artifacts appear.
- Button debounce: validate no double-triggers.
- SD behavior: boot with and without card inserted; rescan after insertion.

### Software tests (where feasible)

- Unit tests for:
  - playlist scanning order
  - index wrap-around
  - RGB565 conversion correctness (spot-check known pixels)
- “Mock display” mode for dev machines (no Pi required).

## Known Risks / Open Questions

- **Driver correctness**: GC9A01A init sequences can vary across panels; inversion/rotation offsets might need tuning.
- **Performance**: Python RGB565 conversion might bottleneck for high-FPS GIFs; may require NumPy and/or caching.
- **EYESPI mapping**: The EYESPI 18-pin connector abstracts signals; we must keep a definitive mapping to Pi pins and document it as wiring evolves.
- **Backlight control**: Some breakouts expect LEDA/LEDK with a driver transistor; confirm whether direct GPIO is acceptable or use PWM/transistor.
- **Touch / extras**: Some round displays have optional touch or extra pins; out-of-scope for v0.

## Decision Log (append-only)

- **2026-01-18**: Adopt hybrid display driver plan: Blinka/Adafruit ecosystem path for portability, plus direct `spidev` path for performance and guaranteed compatibility with GC9A01A. (Refs: Adafruit RGB Display repo `https://github.com/adafruit/Adafruit_CircuitPython_RGB_Display`, GC9A01 wiring image `https://cdn-shop.adafruit.com/product-files/6178/round+TFT+1.28in+GC9A01.png`)

