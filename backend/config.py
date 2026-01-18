from __future__ import annotations

from dataclasses import dataclass
import os


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

    def __post_init__(self) -> None:
        """
        Environment variable overrides for deploy/dev convenience.

        Examples:
          - GIF_DIR=/path/to/gifs
          - ADVANCE_EVERY_S=2.5
          - REPLAY_ON_SELECTION_CHANGE=0
        """

        def _get(name: str) -> str | None:
            v = os.environ.get(name)
            return v if v is not None and v.strip() != "" else None

        def _bool(v: str) -> bool:
            return v.strip().lower() in ("1", "true", "t", "yes", "y", "on")

        def _set_str(field_name: str, env_name: str) -> None:
            v = _get(env_name)
            if v is not None:
                object.__setattr__(self, field_name, v)

        def _set_int(field_name: str, env_name: str) -> None:
            v = _get(env_name)
            if v is not None:
                object.__setattr__(self, field_name, int(v))

        def _set_float(field_name: str, env_name: str) -> None:
            v = _get(env_name)
            if v is not None:
                object.__setattr__(self, field_name, float(v))

        def _set_bool(field_name: str, env_name: str) -> None:
            v = _get(env_name)
            if v is not None:
                object.__setattr__(self, field_name, _bool(v))

        # Core behavior
        _set_str("gif_dir", "GIF_DIR")
        _set_float("advance_every_s", "ADVANCE_EVERY_S")
        _set_bool("replay_on_selection_change", "REPLAY_ON_SELECTION_CHANGE")

        # Buttons
        _set_int("gpio_btn_next", "GPIO_BTN_NEXT")
        _set_int("gpio_btn_prev", "GPIO_BTN_PREV")
        _set_int("button_bounce_ms", "BUTTON_BOUNCE_MS")

        # SPI + display pins
        _set_int("spi_bus", "SPI_BUS")
        _set_int("spi_device", "SPI_DEVICE")
        _set_int("spi_hz", "SPI_HZ")
        _set_int("gpio_dc", "GPIO_DC")
        _set_int("gpio_rst", "GPIO_RST")

        # Backlight pin: allow disabling with GPIO_BL=none
        v_bl = _get("GPIO_BL")
        if v_bl is not None:
            if v_bl.strip().lower() in ("none", "null", "off", "disabled"):
                object.__setattr__(self, "gpio_bl", None)
            else:
                object.__setattr__(self, "gpio_bl", int(v_bl))
