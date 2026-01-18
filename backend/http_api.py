from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from config import Config
from display_factory import create_display
from gpio_buttons import Buttons, ButtonsConfig
from player_service import PlayerService


def create_app() -> FastAPI:
    cfg = Config()
    display = create_display(cfg)
    player = PlayerService(cfg, display)

    gif_dir_real = os.path.realpath(cfg.gif_dir)

    def _assert_safe_gif_path(path: str) -> str:
        # `scan_gifs()` stores realpaths already, but re-check at serve time for safety.
        real = os.path.realpath(path)
        if not (real == gif_dir_real or real.startswith(gif_dir_real + os.sep)):
            raise HTTPException(status_code=403, detail="GIF path not allowed")
        if not real.lower().endswith(".gif"):
            raise HTTPException(status_code=400, detail="Not a GIF")
        if not os.path.isfile(real):
            raise HTTPException(status_code=404, detail="File not found")
        return real

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

    @app.get("/api/gif/current")
    def get_current_gif():
        item = player.current()
        if item is None:
            raise HTTPException(status_code=404, detail="No GIF selected")
        path = _assert_safe_gif_path(item.path)
        return FileResponse(path, media_type="image/gif", filename=item.name, headers={"Cache-Control": "no-store"})

    @app.get("/api/gif/{index}")
    def get_gif(index: int):
        item = player.get(index)
        if item is None:
            raise HTTPException(status_code=404, detail="No GIFs available")
        path = _assert_safe_gif_path(item.path)
        return FileResponse(path, media_type="image/gif", filename=item.name, headers={"Cache-Control": "no-store"})

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

