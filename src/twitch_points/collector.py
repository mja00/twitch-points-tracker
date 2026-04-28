from __future__ import annotations

import logging
import signal
import time
from types import FrameType

from twitch_points.config import Config
from twitch_points.db import connect, init_schema, insert_snapshot
from twitch_points.twitch import (
    TwitchAuthError,
    TwitchChannelNotFound,
    TwitchClient,
    TwitchError,
)

log = logging.getLogger(__name__)


def one_shot(cfg: Config) -> int:
    """Poll every channel once. Returns the number of new snapshots inserted."""
    if not cfg.channels:
        log.warning("No channels configured")
        return 0

    inserted = 0
    conn = connect(cfg.db_path)
    try:
        init_schema(conn)
        with TwitchClient(cfg.oauth_token) as client:
            for ch in cfg.channels:
                try:
                    balance = client.get_balance(ch)
                except TwitchChannelNotFound:
                    log.error("channel not found: %s", ch)
                    continue
                except TwitchAuthError as e:
                    log.error("auth error for %s: %s", ch, e)
                    raise
                except TwitchError as e:
                    log.error("twitch error for %s: %s", ch, e)
                    continue
                except Exception as e:
                    log.exception("unexpected error for %s: %s", ch, e)
                    continue

                if insert_snapshot(conn, ch, balance):
                    inserted += 1
                log.info("polled %s: balance=%d", ch, balance)
    finally:
        conn.close()
    return inserted


_shutdown = False


def _handle_sigint(signum: int, frame: FrameType | None) -> None:
    global _shutdown
    _shutdown = True
    log.info("shutdown signal received, exiting after current poll")


def run_forever(cfg: Config, interval: int | None = None) -> None:
    interval = interval or cfg.interval_seconds
    if interval < 5:
        raise ValueError(f"interval too small: {interval}s")

    signal.signal(signal.SIGINT, _handle_sigint)
    signal.signal(signal.SIGTERM, _handle_sigint)

    backoff = interval
    log.info("starting collector: %d channels, every %ds", len(cfg.channels), interval)

    while not _shutdown:
        try:
            one_shot(cfg)
            backoff = interval
        except TwitchAuthError:
            log.error("auth failure — sleeping %ds before retry; refresh your token", backoff)
            backoff = min(backoff * 2, 3600)
        except Exception:
            log.exception("poll cycle failed")
            backoff = min(backoff * 2, 3600)

        # Sleep in 1s slices so SIGINT is responsive.
        slept = 0
        sleep_for = backoff
        while not _shutdown and slept < sleep_for:
            time.sleep(1)
            slept += 1
