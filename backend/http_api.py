from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import Config
from display_factory import create_display
from gpio_buttons import Buttons, ButtonsConfig
from player_service import PlayerService


def create_app() -> FastAPI:
    cfg = Config()
    display = create_display(cfg)
    player = PlayerService(cfg, display)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        player.start()

        buttons = Buttons(
            ButtonsConfig(gpio_next=cfg.gpio_btn_next, gpio_prev=cfg.gpio_btn_prev, bounce_ms=cfg.button_bounce_ms),
            on_next=player.next,
            on_prev=player.prev,
        )
        buttons.start()

        try:
            yield
        finally:
            buttons.stop()
            player.stop()

    app = FastAPI(title="gif-player", lifespan=lifespan)

    # Local-only dev convenience. In production, run behind same-origin or lock this down.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/status")
    def get_status():
        return player.status()

    @app.get("/api/gifs")
    def get_gifs():
        return player.gifs()

    @app.post("/api/rescan")
    def post_rescan():
        player.rescan()
        return {"ok": True, "count": len(player.gifs())}

    @app.post("/api/next")
    def post_next():
        player.next()
        return {"ok": True}

    @app.post("/api/prev")
    def post_prev():
        player.prev()
        return {"ok": True}

    @app.post("/api/select/{index}")
    def post_select(index: int):
        player.select(index)
        return {"ok": True}

    return app

