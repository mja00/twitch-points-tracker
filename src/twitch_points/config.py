from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class ServerConfig:
    host: str
    port: int


@dataclass(frozen=True)
class Config:
    channels: tuple[str, ...]
    interval_seconds: int
    db_path: Path
    server: ServerConfig
    oauth_token: str


def load_config(
    config_path: str | Path = "config.toml",
    env_path: str | Path = ".env",
) -> Config:
    load_dotenv(env_path, override=False)

    p = Path(config_path)
    if not p.exists():
        raise FileNotFoundError(
            f"Config file not found at {p}. Copy config.example.toml to config.toml."
        )
    with p.open("rb") as f:
        data = tomllib.load(f)

    channels = tuple(data.get("channels", ()))
    interval = int(data.get("interval_seconds", 300))
    db_path = Path(data.get("db_path", "points.db"))
    server_data = data.get("server", {})
    server = ServerConfig(
        host=str(server_data.get("host", "127.0.0.1")),
        port=int(server_data.get("port", 8765)),
    )

    return Config(
        channels=channels,
        interval_seconds=interval,
        db_path=db_path,
        server=server,
        oauth_token=os.environ.get("TWITCH_OAUTH_TOKEN", ""),
    )
