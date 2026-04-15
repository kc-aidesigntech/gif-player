import gc
import os
import struct
import time

import board
import displayio
import gifio

try:
    import sdcardio
    import storage
except ImportError:
    sdcardio = None
    storage = None

import digitalio

from fourwire import FourWire

from adafruit_gc9a01a import GC9A01A


def _getenv(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v is not None and v.strip() != "" else default


def _get_pin(pin_name: str):
    name = pin_name.strip()
    if name.lower() in ("none", "null", "off", "disabled"):
        return None
    try:
        return getattr(board, name)
    except AttributeError as e:
        raise RuntimeError(f"Unknown pin name in settings.toml: {pin_name}") from e


def _list_gifs(dir_path: str):
    try:
        names = [n for n in os.listdir(dir_path) if n.lower().endswith(".gif")]
        names.sort()
        return [dir_path.rstrip("/") + "/" + n for n in names]
    except OSError:
        return []


def _try_mount_sd(spi, mount_point: str, sd_cs_pin) -> bool:
    if sdcardio is None or storage is None:
        return False
    # If it's already mounted, treat as success.
    try:
        os.listdir(mount_point)
        return True
    except Exception:
        pass
    try:
        sd = sdcardio.SDCard(spi, sd_cs_pin)
        vfs = storage.VfsFat(sd)
        storage.mount(vfs, mount_point)
        return True
    except Exception:
        return False


class _Buttons:
    def __init__(self, next_pin_name: str, prev_pin_name: str, debounce_ms: int):
        self._debounce_s = debounce_ms / 1000.0
        self._last_s = 0.0

        self._next = None
        self._prev = None

        next_pin = _get_pin(next_pin_name)
        prev_pin = _get_pin(prev_pin_name)

        if next_pin is not None:
            btn = digitalio.DigitalInOut(next_pin)
            btn.switch_to_input(pull=digitalio.Pull.UP)
            self._next = btn

        if prev_pin is not None:
            btn = digitalio.DigitalInOut(prev_pin)
            btn.switch_to_input(pull=digitalio.Pull.UP)
            self._prev = btn

    def read_delta(self) -> int:
        now = time.monotonic()
        if (now - self._last_s) < self._debounce_s:
            return 0

        # Pull-ups: pressed == False
        if self._next is not None and (not self._next.value):
            self._last_s = now
            return 1

        if self._prev is not None and (not self._prev.value):
            self._last_s = now
            return -1

        return 0


def _play_gif(bus, width: int, height: int, gif_path: str, max_seconds, buttons: _Buttons) -> int:
    # Standard commands: CASET=0x2A (42), RASET=0x2B (43), RAMWR=0x2C (44)
    x1 = width - 1
    y1 = height - 1
    caset = struct.pack(">HH", 0, x1)
    raset = struct.pack(">HH", 0, y1)

    odg = gifio.OnDiskGif(gif_path)
    try:
        # Prime the first frame and measure overhead
        t0 = time.monotonic()
        next_delay = odg.next_frame()
        overhead = time.monotonic() - t0

        # If max_seconds is 0, try to play a single full GIF duration once.
        if max_seconds == 0:
            try:
                dur = float(odg.duration)
                max_seconds = dur if dur > 0 else None
            except Exception:
                max_seconds = None

        stop_at = None
        if max_seconds is not None:
            stop_at = time.monotonic() + float(max_seconds)

        while True:
            # Button check before sleeping so presses feel responsive.
            delta = buttons.read_delta()
            if delta != 0:
                return delta

            time.sleep(max(0, next_delay - overhead))
            next_delay = odg.next_frame()

            bus.send(42, caset)
            bus.send(43, raset)
            bus.send(44, odg.bitmap)

            if stop_at is not None and time.monotonic() >= stop_at:
                return 0
    finally:
        try:
            odg.deinit()
        except Exception:
            pass


def main() -> None:
    # Pin defaults match EYESPI BFF for QT Py (PID 5772):
    # - TFT CS -> TX
    # - TFT DC -> RX
    # - SD CS  -> A3
    tft_cs = _get_pin(_getenv("TFT_CS", "TX"))
    tft_dc = _get_pin(_getenv("TFT_DC", "RX"))
    tft_rst = _get_pin(_getenv("TFT_RST", "none"))
    sd_cs = _get_pin(_getenv("SD_CS", "A3"))

    spi_baudrate = int(_getenv("SPI_BAUDRATE", "40000000"))
    sd_mount = _getenv("SD_MOUNT", "/sd")
    sd_gif_dir = _getenv("SD_GIF_DIR", "/sd/gifs")
    circuitpy_gif = _getenv("CIRCUITPY_GIF", "/sample.gif")
    playlist_mode = _getenv("PLAYLIST_MODE", "loop").strip().lower()
    per_gif_seconds = float(_getenv("PER_GIF_SECONDS", "0"))

    btn_next = _getenv("BTN_NEXT", "none")
    btn_prev = _getenv("BTN_PREV", "none")
    btn_debounce_ms = int(_getenv("BTN_DEBOUNCE_MS", "150"))

    displayio.release_displays()

    spi = board.SPI()

    # Best-effort SD mount (optional; app still works with CIRCUITPY_GIF)
    sd_ok = _try_mount_sd(spi, sd_mount, sd_cs)

    buttons = _Buttons(btn_next, btn_prev, btn_debounce_ms)

    # Display bring-up
    display_bus = FourWire(
        spi,
        command=tft_dc,
        chip_select=tft_cs,
        reset=tft_rst,
        baudrate=spi_baudrate,
    )
    display = GC9A01A(display_bus, width=240, height=240)

    # Direct drive for speed
    display.auto_refresh = False
    bus = display.bus

    # Pick playlist source
    idx = 0
    while True:
        try:
            if not sd_ok:
                sd_ok = _try_mount_sd(spi, sd_mount, sd_cs)

            playlist = _list_gifs(sd_gif_dir) if sd_ok else []
            if not playlist:
                playlist = [circuitpy_gif]

            # If only one file, default to infinite playback unless PER_GIF_SECONDS is set.
            if len(playlist) == 1 and per_gif_seconds == 0:
                max_seconds = None
            else:
                max_seconds = per_gif_seconds if per_gif_seconds > 0 else 0

            path = playlist[idx % len(playlist)]
            delta = _play_gif(bus, 240, 240, path, max_seconds, buttons)
            if delta != 0:
                idx += delta
            else:
                idx += 1

            if playlist_mode == "once" and idx >= len(playlist):
                # Stop after one pass
                while True:
                    time.sleep(1.0)
            if idx >= len(playlist):
                idx = 0
        except MemoryError:
            gc.collect()
            time.sleep(0.2)
        except OSError:
            # Missing file or SD removed: rescan SD, then fallback
            gc.collect()
            time.sleep(0.2)
            idx += 1
        except Exception:
            gc.collect()
            time.sleep(0.2)
            idx += 1


main()

