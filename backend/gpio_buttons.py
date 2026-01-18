from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ButtonsConfig:
    gpio_next: int
    gpio_prev: int
    bounce_ms: int = 150


class Buttons:
    """
    Two-button (next/prev) handler using RPi.GPIO, with a safe no-op fallback for dev.
    """

    def __init__(self, cfg: ButtonsConfig, on_next: Callable[[], None], on_prev: Callable[[], None]):
        self.cfg = cfg
        self._on_next = on_next
        self._on_prev = on_prev

        try:
            import RPi.GPIO as GPIO  # type: ignore
        except Exception as e:  # pragma: no cover
            log.warning("RPi.GPIO unavailable (%s); buttons disabled", e)
            self.GPIO = None
            return

        self.GPIO = GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        for pin in (cfg.gpio_next, cfg.gpio_prev):
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def start(self) -> None:
        if self.GPIO is None:
            return
        GPIO = self.GPIO
        GPIO.add_event_detect(
            self.cfg.gpio_next, GPIO.FALLING, callback=lambda _ch: self._on_next(), bouncetime=self.cfg.bounce_ms
        )
        GPIO.add_event_detect(
            self.cfg.gpio_prev, GPIO.FALLING, callback=lambda _ch: self._on_prev(), bouncetime=self.cfg.bounce_ms
        )

    def stop(self) -> None:
        if self.GPIO is None:
            return
        GPIO = self.GPIO
        for pin in (self.cfg.gpio_next, self.cfg.gpio_prev):
            try:
                GPIO.remove_event_detect(pin)
            except Exception:
                pass

