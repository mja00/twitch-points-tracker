from __future__ import annotations

import sqlite3
import time
from collections.abc import Iterable
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS points_snapshot (
    id      INTEGER PRIMARY KEY,
    ts      INTEGER NOT NULL,
    channel TEXT    NOT NULL,
    balance INTEGER NOT NULL,
    event   TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_points_unique
    ON points_snapshot(channel, ts, balance);
CREATE INDEX IF NOT EXISTS idx_points_channel_ts
    ON points_snapshot(channel, ts);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def insert_snapshot(
    conn: sqlite3.Connection,
    channel: str,
    balance: int,
    ts: int | None = None,
    event: str | None = None,
) -> bool:
    """Insert one row. Returns True if inserted, False if it was a duplicate."""
    if ts is None:
        ts = int(time.time())
    cur = conn.execute(
        "INSERT OR IGNORE INTO points_snapshot (ts, channel, balance, event) "
        "VALUES (?, ?, ?, ?)",
        (ts, channel, balance, event),
    )
    return cur.rowcount > 0


def insert_many(
    conn: sqlite3.Connection,
    rows: Iterable[tuple[int, str, int, str | None]],
) -> int:
    """Bulk insert (ts, channel, balance, event) tuples. Returns number inserted."""
    rows = list(rows)
    if not rows:
        return 0
    before = conn.execute("SELECT COUNT(*) FROM points_snapshot").fetchone()[0]
    conn.executemany(
        "INSERT OR IGNORE INTO points_snapshot (ts, channel, balance, event) "
        "VALUES (?, ?, ?, ?)",
        rows,
    )
    after = conn.execute("SELECT COUNT(*) FROM points_snapshot").fetchone()[0]
    return after - before


def list_channels(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT channel FROM points_snapshot ORDER BY channel"
    ).fetchall()
    return [r[0] for r in rows]


def query_series(
    conn: sqlite3.Connection,
    channel: str,
    since: int | None = None,
) -> list[tuple[int, int]]:
    if since is None:
        rows = conn.execute(
            "SELECT ts, balance FROM points_snapshot WHERE channel = ? ORDER BY ts",
            (channel,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT ts, balance FROM points_snapshot "
            "WHERE channel = ? AND ts >= ? ORDER BY ts",
            (channel, since),
        ).fetchall()
    return [(int(ts), int(bal)) for ts, bal in rows]
