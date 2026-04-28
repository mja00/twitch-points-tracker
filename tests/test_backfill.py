import json

from twitch_points.backfill import backfill_file
from twitch_points.db import connect, init_schema, list_channels, query_series


def _write_sample(path, series):
    path.write_text(json.dumps({"series": series}))


def test_backfill_basic(tmp_path):
    src = tmp_path / "moonmoon.json"
    _write_sample(
        src,
        [
            {"x": 1707189446000, "y": 417827, "z": "Watch"},
            {"x": 1707189746000, "y": 418189, "z": "Claim"},
            {"x": 1707192224000, "y": 397542, "z": "Spent"},
        ],
    )
    db = tmp_path / "p.db"

    inserted, total = backfill_file(src, db)
    assert (inserted, total) == (3, 3)

    conn = connect(db)
    init_schema(conn)
    assert list_channels(conn) == ["moonmoon"]
    series = query_series(conn, "moonmoon")
    # Sorted by ts (ms / 1000).
    assert series == [
        (1707189446, 417827),
        (1707189746, 418189),
        (1707192224, 397542),
    ]
    rows = conn.execute(
        "SELECT event FROM points_snapshot ORDER BY ts"
    ).fetchall()
    assert [r[0] for r in rows] == ["Watch", "Claim", "Spent"]
    conn.close()


def test_backfill_idempotent(tmp_path):
    src = tmp_path / "moonmoon.json"
    _write_sample(
        src,
        [{"x": 1707189446000, "y": 417827, "z": "Watch"}],
    )
    db = tmp_path / "p.db"

    assert backfill_file(src, db)[0] == 1
    assert backfill_file(src, db)[0] == 0


def test_backfill_channel_override(tmp_path):
    src = tmp_path / "data.json"
    _write_sample(src, [{"x": 1707189446000, "y": 1, "z": "Watch"}])
    db = tmp_path / "p.db"

    backfill_file(src, db, channel="custom_name")
    conn = connect(db)
    init_schema(conn)
    assert list_channels(conn) == ["custom_name"]
    conn.close()


def test_backfill_skips_malformed(tmp_path):
    src = tmp_path / "moonmoon.json"
    src.write_text(
        json.dumps(
            {
                "series": [
                    {"x": 1707189446000, "y": 417827, "z": "Watch"},
                    {"x": "garbage", "y": 1, "z": "Watch"},
                    {"x": 1707189747000, "y": 418249},
                ]
            }
        )
    )
    db = tmp_path / "p.db"

    inserted, total = backfill_file(src, db)
    # Two valid rows (one missing z is fine, just no event), one malformed skipped.
    assert inserted == 2
    assert total == 3
