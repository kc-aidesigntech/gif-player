from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MockDisplayConfig:
    width: int = 240
    height: int = 240


class MockDisplay:
    """
    Dev-friendly display stub (no hardware required).
    """

    def __init__(self, cfg: MockDisplayConfig):
        self.cfg = cfg
        self.frame_count = 0

    def open(self) -> None:
        return

    def close(self) -> None:
        return

    def set_backlight(self, on: bool) -> None:
        return

    def blit_rgb565(self, rgb565_be: bytes) -> None:
        # No-op by default (keeps it fast). Useful for CI / dev on laptops.
        self.frame_count += 1

