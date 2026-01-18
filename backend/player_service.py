from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageSequence

from config import Config
from gif_playlist import GifItem, clamp_index, scan_gifs
from image_rgb565 import fit_center_square, to_rgb565_bytes

log = logging.getLogger(__name__)


@dataclass
class PlayerStatus:
    gif_dir: str
    gif_count: int
    index: int
    current_name: str | None
    playing: bool
    last_error: str | None


class PlayerService:
    """
    Owns playlist state + playback loop. Thread-safe operations for next/prev/select/rescan.
    """

    def __init__(self, cfg: Config, display: Any):
        self.cfg = cfg
        self.display = display

        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

        self._items: list[GifItem] = []
        self._index: int = 0
        self._play_now = threading.Event()
        self._playing = False
        self._last_error: str | None = None
        self._last_advance_monotonic = 0.0

    def start(self) -> None:
        self.display.open()
        self.rescan()
        self._last_advance_monotonic = time.monotonic()
        self._thread = threading.Thread(target=self._loop, name="gif-player", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._play_now.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self.display.close()

    # --- Public control plane (thread-safe) ---

    def rescan(self) -> None:
        items = scan_gifs(self.cfg.gif_dir)
        with self._lock:
            self._items = items
            self._index = clamp_index(self._index, len(self._items))

    def gifs(self) -> list[GifItem]:
        with self._lock:
            return list(self._items)

    def status(self) -> PlayerStatus:
        with self._lock:
            name = self._items[self._index].name if self._items else None
            return PlayerStatus(
                gif_dir=self.cfg.gif_dir,
                gif_count=len(self._items),
                index=self._index,
                current_name=name,
                playing=self._playing,
                last_error=self._last_error,
            )

    def select(self, index: int) -> None:
        with self._lock:
            self._index = clamp_index(index, len(self._items))
        if self.cfg.replay_on_selection_change:
            self._play_now.set()

    def next(self) -> None:
        with self._lock:
            self._index = clamp_index(self._index + 1, len(self._items))
        if self.cfg.replay_on_selection_change:
            self._play_now.set()

    def prev(self) -> None:
        with self._lock:
            self._index = clamp_index(self._index - 1, len(self._items))
        if self.cfg.replay_on_selection_change:
            self._play_now.set()

    # --- Playback ---

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                # If there are no GIFs, keep rescanning periodically.
                with self._lock:
                    has_items = bool(self._items)
                if not has_items:
                    self._playing = False
                    self._last_error = None
                    time.sleep(1.0)
                    self.rescan()
                    continue

                now = time.monotonic()
                due = (now - self._last_advance_monotonic) >= self.cfg.advance_every_s

                # Play immediately if requested (button/API), else if slideshow says due.
                if not self._play_now.is_set() and not due:
                    # Sleep in small increments so stop() is responsive
                    self._play_now.wait(timeout=0.25)
                    continue

                self._play_now.clear()

                # Slideshow advance (only on the timer path)
                if due:
                    self.next()
                    self._last_advance_monotonic = time.monotonic()

                item = self._current_item()
                if item is None:
                    continue

                self._playing = True
                self._last_error = None
                self._play_gif_once(item.path)
                self._playing = False

            except Exception as e:
                log.exception("Playback loop error: %s", e)
                self._last_error = str(e)
                self._playing = False
                time.sleep(0.5)

    def _current_item(self) -> GifItem | None:
        with self._lock:
            if not self._items:
                return None
            return self._items[self._index]

    def _play_gif_once(self, path: str) -> None:
        # Pillow will decode frames; durations come from frame.info["duration"] in ms.
        with Image.open(path) as im:
            for frame in ImageSequence.Iterator(im):
                if self._stop.is_set() or self._play_now.is_set():
                    return

                rgb = fit_center_square(frame, self.cfg.width)
                payload = to_rgb565_bytes(rgb)
                self.display.blit_rgb565(payload)

                duration_ms = int(frame.info.get("duration", 80))
                duration_ms = max(10, min(duration_ms, 2000))
                time.sleep(duration_ms / 1000.0)

