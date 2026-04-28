from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from twitch_points.config import Config
from twitch_points.db import connect, init_schema, list_channels, query_series

STATIC_DIR = Path(__file__).parent / "static"


def create_app(cfg: Config) -> FastAPI:
    app = FastAPI(title="Twitch Points Tracker")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/channels")
    def channels() -> list[str]:
        conn = connect(cfg.db_path)
        try:
            init_schema(conn)
            return list_channels(conn)
        finally:
            conn.close()

    @app.get("/api/series")
    def series(
        channel: str = Query(...),
        since: int | None = Query(None, description="Unix seconds; only points >= this"),
    ) -> list[dict]:
        if not channel:
            raise HTTPException(400, "channel required")
        conn = connect(cfg.db_path)
        try:
            init_schema(conn)
            rows = query_series(conn, channel, since=since)
        finally:
            conn.close()
        return [{"ts": ts, "balance": bal} for ts, bal in rows]

    return app


def serve(cfg: Config) -> None:
    import uvicorn

    app = create_app(cfg)
    uvicorn.run(app, host=cfg.server.host, port=cfg.server.port, log_level="info")
