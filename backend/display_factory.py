from __future__ import annotations

import os
from typing import Any

from config import Config
from display_mock import MockDisplay, MockDisplayConfig


def create_display(cfg: Config) -> Any:
    """
    Returns an object with:
      - open()
      - close()
      - set_backlight(bool)
      - blit_rgb565(bytes)
    """
    driver = os.environ.get("DISPLAY_DRIVER", "gc9a01a").strip().lower()

    if driver == "mock":
        return MockDisplay(MockDisplayConfig(width=cfg.width, height=cfg.height))

    # Default: real hardware
    from display_gc9a01a import GC9A01A, GC9A01AConfig

    return GC9A01A(
        GC9A01AConfig(
            width=cfg.width,
            height=cfg.height,
            spi_bus=cfg.spi_bus,
            spi_device=cfg.spi_device,
            spi_hz=cfg.spi_hz,
            gpio_dc=cfg.gpio_dc,
            gpio_rst=cfg.gpio_rst,
            gpio_bl=cfg.gpio_bl,
        )
    )

