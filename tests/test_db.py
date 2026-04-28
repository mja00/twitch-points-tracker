from twitch_points.db import (
    connect,
    init_schema,
    insert_many,
    insert_snapshot,
    list_channels,
    query_series,
)


def test_insert_and_query(tmp_path):
    db = tmp_path / "t.db"
    conn = connect(db)
    init_schema(conn)

    assert insert_snapshot(conn, "alice", 100, ts=1000) is True
    assert insert_snapshot(conn, "alice", 110, ts=1300) is True
    assert insert_snapshot(conn, "bob", 50, ts=1100) is True

    # Duplicate (channel, ts, balance) is a no-op.
    assert insert_snapshot(conn, "alice", 100, ts=1000) is False

    assert list_channels(conn) == ["alice", "bob"]
    assert query_series(conn, "alice") == [(1000, 100), (1300, 110)]
    assert query_series(conn, "alice", since=1200) == [(1300, 110)]
    assert query_series(conn, "bob") == [(1100, 50)]


def test_insert_many_idempotent(tmp_path):
    db = tmp_path / "t.db"
    conn = connect(db)
    init_schema(conn)

    rows = [
        (1000, "alice", 100, "Watch"),
        (1300, "alice", 110, "Claim"),
        (1100, "bob", 50, None),
    ]
    assert insert_many(conn, rows) == 3
    # Re-import the same rows: nothing new.
    assert insert_many(conn, rows) == 0
    # Add one more new row alongside the duplicates.
    assert insert_many(conn, rows + [(1500, "alice", 120, "Watch")]) == 1


def test_insert_many_empty(tmp_path):
    db = tmp_path / "t.db"
    conn = connect(db)
    init_schema(conn)
    assert insert_many(conn, []) == 0
