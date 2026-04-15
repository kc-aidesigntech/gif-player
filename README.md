## GIF Player for GC9A01A (EYESPI) on QT Py ESP32‑S3 (CircuitPython)

This repo is building a small **GIF player appliance** targeting **QT Py ESP32‑S3 + CircuitPython**:

- **Reads GIFs from microSD** (preferred) or `CIRCUITPY`
- **Plays them on a 240×240 round GC9A01A TFT** over SPI (EYESPI)
- Designed to extend later with **buttons** (next / previous)

If you’re new here, start with:

- `ENGINEERING_PLAN.md` — the “source of truth” for architecture, wiring, and decisions.

## Quickstart (QT Py S3 / CircuitPython)
Use the drop-in fileset under `circuitpython/`.

- Instructions: `circuitpython/README.md`
- Main entrypoint: `circuitpython/code.py`
- Settings: `circuitpython/settings.toml`

### Hardware (v0 target)

- **Display**: Adafruit 1.28" 240×240 Round TFT LCD Display with MicroSD - GC9A01A with EYESPI Connector (6178)
  - Wiring reference image: `https://cdn-shop.adafruit.com/product-files/6178/round+TFT+1.28in+GC9A01.png`
- **Connector board**: Adafruit EYESPI BFF for QT Py or Xiao (5772)
  - Product page: `https://www.adafruit.com/product/5772`
- **MCU**: Adafruit QT Py ESP32‑S3 with 2MB PSRAM (5700)
- **Inputs (planned)**: 2 momentary push-buttons

### What’s in the repo today

This repo includes two tracks:

- **CircuitPython (primary)**: `circuitpython/` — copy-to-`CIRCUITPY` app for QT Py S3 + GC9A01A.
- **Legacy Raspberry Pi (secondary/archived)**: `backend/`, `frontend/`, `deploy/` — the earlier Linux appliance approach (kept for reference).

### Design goals

- **Works offline** as a standalone “appliance” using only SD + buttons
- **Portability**: keep a path open for Adafruit/Blinka-style drivers
- **Performance**: keep a direct `spidev` fast-path for full-frame GIF animation
- **Extensibility**: a clean foundation for later features (remote control, playlists, AI GIF generation workflow, etc.)

## Legacy (Raspberry Pi) quickstart (optional)

The sections below describe the older Pi/Linux service; they’re kept for reference but are not the primary deployment target anymore.

### Run the local API server (needed for the React UI)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_server.py
```

This starts a local server at `http://localhost:8000` with endpoints under `/api/*`.

### Run the UI (minimal “fullscreen GIF” viewer)

The UI is intentionally simple: it shows the **current GIF centered** and briefly overlays the **GIF filename** when it changes.

1) Start the backend (mock display is fine on laptops):

```bash
cd backend
source .venv/bin/activate
mkdir -p ../_local_gifs
DISPLAY_DRIVER=mock GIF_DIR="$(pwd)/../_local_gifs" python run_server.py
```

If port `8000` is already in use, pick another:

```bash
PORT=8001 DISPLAY_DRIVER=mock GIF_DIR="$(pwd)/../_local_gifs" python run_server.py
```

2) Start the UI dev server:

```bash
cd frontend
npm install
npm run dev
```

If your backend is on a different port, easiest is to point the Vite dev proxy at it (keeps requests same-origin on `localhost:5173`):

```bash
VITE_API_TARGET=http://127.0.0.1:8001 npm run dev
```

Then open the UI at `http://localhost:5173`.

Notes:
- The UI loads the current GIF from `GET /api/gif/current`.
- You can still use the API directly via `http://localhost:8000/docs`.

Troubleshooting:
- If the UI shows `GET http://localhost:5173/api/... 404`, your proxy is pointing at the wrong port (set `VITE_API_TARGET` and restart `npm run dev`).
- If you see `net::ERR_CONNECTION_REFUSED` for `http://127.0.0.1:8001/api/status`, the backend isn't actually running on that port (re-run the backend command and keep it running).

## One-command run (single-process: backend serves UI + API)

If you build the UI once, the backend will serve it from `frontend/dist/`, so you can run everything as **one process** (ideal for `systemd`).

From the repo root:

```bash
make run
```

Then open:
- UI: `http://localhost:8000/`
- API docs: `http://localhost:8000/docs`

## systemd (.service) deploy (Raspberry Pi)

A sample unit file is included at `deploy/gif-player.service`.

High-level steps (typical setup):
- Copy this repo to `~/gif-player`
- Create backend venv and install deps
- Build the UI to `frontend/dist`
- Copy the unit file into `/etc/systemd/system/gif-player.service`
- Enable + start the service

Example install (on the Pi, as user `pi`):

```bash
cd ~/gif-player/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Build UI:

```bash
cd ~/gif-player/frontend
npm install
npm run build
```

Install + start service (uses port 8001 by default):

```bash
sudo cp ~/gif-player/deploy/gif-player.service /etc/systemd/system/gif-player.service
sudo systemctl daemon-reload
sudo systemctl enable --now gif-player.service
```

Check logs:

```bash
sudo journalctl -u gif-player.service -f
```


### 1) Enable SPI on Raspberry Pi

Enable SPI using `raspi-config` (or equivalent for your distro), then reboot.

### 2) Put GIFs on the SD card

- Mount the microSD via Linux.
- Put `.gif` files into the configured directory (default: `/media/pi/GIFS`).

If your system mounts removable media somewhere else, update `gif_dir` in `backend/config.py` (or later via env/config file when added).

### 3) Install backend dependencies

From the repo root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4) Run (mock mode, no hardware required)

Mock mode runs the full player loop without touching SPI/GPIO:

```bash
cd backend
source .venv/bin/activate
DISPLAY_DRIVER=mock python -c "from config import Config; from display_factory import create_display; from player_service import PlayerService; import time; cfg=Config(); d=create_display(cfg); p=PlayerService(cfg,d); p.start(); time.sleep(10); p.stop()"
```

### 5) Run (real hardware, GC9A01A over SPI)

```bash
cd backend
source .venv/bin/activate
DISPLAY_DRIVER=gc9a01a python -c "from config import Config; from display_factory import create_display; from player_service import PlayerService; import time; cfg=Config(); d=create_display(cfg); p=PlayerService(cfg,d); p.start(); time.sleep(60); p.stop()"
```

Notes:

- The default SPI pins assume **SPI0** on Raspberry Pi.
- The `gc9a01a` driver uses `spidev` + `RPi.GPIO`. Run on a Pi with SPI enabled.

## Wiring overview (defaults)

### Display (SPI0)

Default assumptions (BCM numbering):

- **SCK**: BCM 11 (SPI0 SCLK)
- **MOSI**: BCM 10 (SPI0 MOSI)
- **CS**: SPI0 CE0 (BCM 8) via `spi_device=0`
- **D/C**: BCM 25
- **RESET**: BCM 24
- **Backlight (optional)**: BCM 18 (or hard-wire backlight to 3V3)

The panel signal names in the reference image map as:

- `SCL` → SCK
- `SDA` → MOSI
- `CS` → CE0 (or another GPIO/CE if rewired)
- `D/C` → data/command GPIO
- `RESET` → reset GPIO
- `LEDA/LEDK` → backlight power/control

### Buttons

Default assumptions (BCM numbering):

- **NEXT**: BCM 17
- **PREV**: BCM 27

Wire each button between its GPIO and **GND** (internal pull-up enabled in code).

## Configuration

Configuration defaults live in `backend/config.py`:

- **GIF directory**: `gif_dir` (default `/media/pi/GIFS`)
- **Auto-advance**: `advance_every_s` (default 5.0)
- **GPIO pins**: next/prev/DC/RST/BL
- **SPI**: bus/device/Hz

## Driver modes

Today:

- `DISPLAY_DRIVER=gc9a01a` — real GC9A01A over SPI using `spidev` + `RPi.GPIO`
- `DISPLAY_DRIVER=mock` — no-hardware development mode

Planned:

- `DISPLAY_DRIVER=blinka_gc9a01a` — portable Blinka/CircuitPython-style driver backend (hybrid approach)

Related Adafruit ecosystem context:

- Adafruit’s `Adafruit_CircuitPython_RGB_Display` repo provides a well-tested driver framework for several controllers, but GC9A01A isn’t in its supported list, so we’ll integrate a GC9A01A-specific Blinka driver when we add that path: `https://github.com/adafruit/Adafruit_CircuitPython_RGB_Display`

## Project scope

### In-scope (now)

- Simple GIF playback loop
- Auto-advance every N seconds
- Two-button next/prev selection
- Solid wiring + config documentation

### Planned (next)

- Python HTTP API + React/TypeScript UI (control panel)
- Systemd service for “appliance mode”
- Better SD mount discovery + hot reload
- Performance improvements (NumPy RGB565 conversion, frame caching)
- AI GIF generation workflow (kept “in the back pocket” for now)

## React UI (local-only, no internet services)

The UI runs entirely on your machine and talks to the local API server.

Planned directory: `frontend/`

## Contributing / workflow

- Treat `ENGINEERING_PLAN.md` as the living plan and append decisions to the decision log.
- Keep hardware assumptions explicit and configurable (pins, SPI bus/device, mount paths).

