from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # Where the SD card is mounted by Linux (the OS is responsible for mounting).
    # Put your .gif files directly here (or adjust as desired).
    gif_dir: str = "/media/pi/GIFS"

    # Slideshow behavior
    advance_every_s: float = 5.0  # select next GIF every N seconds
    replay_on_selection_change: bool = True  # play immediately when next/prev pressed

    # Buttons (BCM numbering)
    gpio_btn_next: int = 17
    gpio_btn_prev: int = 27
    button_bounce_ms: int = 150

    # SPI display wiring
    spi_bus: int = 0
    spi_device: int = 0  # CE0
    spi_hz: int = 62_500_000  # GC9A01A can run fast; reduce if you see artifacts
    gpio_dc: int = 25
    gpio_rst: int = 24
    gpio_bl: int | None = 18  # set None if hard-wired to 3V3

    # Display geometry
    width: int = 240
    height: int = 240
