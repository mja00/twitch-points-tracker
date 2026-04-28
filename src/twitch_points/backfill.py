from __future__ import annotations

import json
import logging
from pathlib import Path

from twitch_points.db import connect, init_schema, insert_many

log = logging.getLogger(__name__)


def backfill_file(
    json_path: str | Path,
    db_path: str | Path,
    channel: str | None = None,
) -> tuple[int, int]:
    """Import a {"series":[{x,y,z},...]} JSON dump into the points DB.

    Returns (inserted, total_in_file).
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(path)

    channel_name = channel or path.stem
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    series = data.get("series")
    if not isinstance(series, list):
        raise ValueError(f"{path}: expected top-level 'series' array")

    rows: list[tuple[int, str, int, str | None]] = []
    skipped = 0
    for i, entry in enumerate(series):
        try:
            ts_ms = int(entry["x"])
            balance = int(entry["y"])
            event = entry.get("z")
            event_str = str(event) if event is not None else None
        except (KeyError, TypeError, ValueError) as e:
            skipped += 1
            log.warning("skipping malformed entry %d in %s: %s", i, path.name, e)
            continue
        rows.append((ts_ms // 1000, channel_name, balance, event_str))

    conn = connect(db_path)
    try:
        init_schema(conn)
        inserted = insert_many(conn, rows)
    finally:
        conn.close()

    log.info(
        "backfilled %s: channel=%s, %d/%d new rows (%d duplicates, %d malformed)",
        path.name,
        channel_name,
        inserted,
        len(rows),
        len(rows) - inserted,
        skipped,
    )
    return inserted, len(series)
