from __future__ import annotations

import time
from dataclasses import dataclass

try:
    import RPi.GPIO as GPIO  # type: ignore
    import spidev  # type: ignore
except Exception as e:  # pragma: no cover
    GPIO = None  # type: ignore
    spidev = None  # type: ignore
    _IMPORT_ERR = e


def _sleep_ms(ms: int) -> None:
    time.sleep(ms / 1000.0)


@dataclass(frozen=True)
class GC9A01AConfig:
    width: int = 240
    height: int = 240
    spi_bus: int = 0
    spi_device: int = 0
    spi_hz: int = 62_500_000
    gpio_dc: int = 25
    gpio_rst: int = 24
    gpio_bl: int | None = 18


class GC9A01A:
    """
    Minimal GC9A01A SPI driver for Raspberry Pi.

    - Assumes SPI mode 0, 8-bit transfers.
    - Pushes full-frame RGB565 (big-endian) for simplicity.
    """

    def __init__(self, cfg: GC9A01AConfig):
        if GPIO is None or spidev is None:  # pragma: no cover
            raise RuntimeError(
                "GC9A01A driver requires Raspberry Pi libs. "
                "Install `spidev` + `RPi.GPIO` and run on a Pi, "
                "or set DISPLAY_DRIVER=mock."
            ) from _IMPORT_ERR

        self.cfg = cfg
        self.spi = spidev.SpiDev()

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(cfg.gpio_dc, GPIO.OUT)
        GPIO.setup(cfg.gpio_rst, GPIO.OUT)
        if cfg.gpio_bl is not None:
            GPIO.setup(cfg.gpio_bl, GPIO.OUT)

    def open(self) -> None:
        self.spi.open(self.cfg.spi_bus, self.cfg.spi_device)
        self.spi.max_speed_hz = self.cfg.spi_hz
        self.spi.mode = 0
        self.spi.bits_per_word = 8

        self._hw_reset()
        self._init_sequence()
        self.set_backlight(True)

    def close(self) -> None:
        try:
            self.set_backlight(False)
        except Exception:
            pass
        try:
            self.spi.close()
        except Exception:
            pass
        try:
            pins = [self.cfg.gpio_dc, self.cfg.gpio_rst]
            if self.cfg.gpio_bl is not None:
                pins.append(self.cfg.gpio_bl)
            GPIO.cleanup(pins)
        except Exception:
            pass

    def set_backlight(self, on: bool) -> None:
        if self.cfg.gpio_bl is None:
            return
        GPIO.output(self.cfg.gpio_bl, GPIO.HIGH if on else GPIO.LOW)

    def _hw_reset(self) -> None:
        GPIO.output(self.cfg.gpio_rst, GPIO.HIGH)
        _sleep_ms(10)
        GPIO.output(self.cfg.gpio_rst, GPIO.LOW)
        _sleep_ms(50)
        GPIO.output(self.cfg.gpio_rst, GPIO.HIGH)
        _sleep_ms(120)

    def _cmd(self, c: int) -> None:
        GPIO.output(self.cfg.gpio_dc, GPIO.LOW)
        self.spi.writebytes([c & 0xFF])

    def _data(self, data: bytes | bytearray | list[int]) -> None:
        GPIO.output(self.cfg.gpio_dc, GPIO.HIGH)
        if isinstance(data, list):
            self.spi.writebytes(data)
        else:
            # spidev prefers list[int] but writebytes2 accepts bytes-like
            self.spi.writebytes2(data)

    def _init_sequence(self) -> None:
        """
        Ported (lightly simplified) from common GC9A01A init sequences.
        This should work for Adafruit's GC9A01A round 240x240 module.
        """
        self._cmd(0xFE)
        self._cmd(0xEF)

        self._cmd(0x36)  # MADCTL
        self._data([0x48])  # MX, BGR

        self._cmd(0x3A)  # COLMOD
        self._data([0x55])  # 16-bit/pixel

        # Porch / gate / VCOM / power settings (typical values)
        self._cmd(0xC5)  # VCOM
        self._data([0x00, 0x18])

        self._cmd(0xC6)  # Display function control
        self._data([0x01])

        self._cmd(0xB0)  # Interface
        self._data([0x00])

        self._cmd(0xB6)
        self._data([0x2A, 0x2A])

        self._cmd(0xE8)
        self._data([0x40, 0x8A, 0x00, 0x00, 0x29, 0x19, 0xA5, 0x33])

        self._cmd(0xE0)  # Positive gamma
        self._data([0xF0, 0x04, 0x0A, 0x0E, 0x09, 0x0F, 0x36, 0x33, 0x4A, 0x1A, 0x17, 0x16, 0x1B, 0x1F])

        self._cmd(0xE1)  # Negative gamma
        self._data([0xF0, 0x09, 0x0B, 0x06, 0x04, 0x15, 0x2F, 0x54, 0x42, 0x3C, 0x17, 0x14, 0x18, 0x1B])

        self._cmd(0x21)  # INVON (many round panels want inversion on)

        self._cmd(0x11)  # SLPOUT
        _sleep_ms(120)

        self._cmd(0x29)  # DISPON
        _sleep_ms(20)

    def _set_window(self, x0: int, y0: int, x1: int, y1: int) -> None:
        self._cmd(0x2A)  # CASET
        self._data([(x0 >> 8) & 0xFF, x0 & 0xFF, (x1 >> 8) & 0xFF, x1 & 0xFF])
        self._cmd(0x2B)  # RASET
        self._data([(y0 >> 8) & 0xFF, y0 & 0xFF, (y1 >> 8) & 0xFF, y1 & 0xFF])
        self._cmd(0x2C)  # RAMWR

    def blit_rgb565(self, rgb565_be: bytes) -> None:
        """
        Push a full 240x240 frame of big-endian RGB565.
        """
        w = self.cfg.width
        h = self.cfg.height
        expected = w * h * 2
        if len(rgb565_be) != expected:
            raise ValueError(f"Expected {expected} bytes for {w}x{h} RGB565, got {len(rgb565_be)}")

        self._set_window(0, 0, w - 1, h - 1)
        self._data(rgb565_be)

