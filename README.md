# twitch-points-tracker

Periodically polls your Twitch channel-points balance across a configured list of channels,
stores each reading in SQLite, and serves a small local web dashboard that plots the
balances over time.

> **Note:** Twitch's official Helix API does not expose a viewer's channel-points
> balance. This tool talks to the same private GQL endpoint
> (`https://gql.twitch.tv/gql`) that the Twitch website uses, with the OAuth token
> from your browser session. It's stable in practice but unofficial — use at your
> own risk.

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env
cp config.example.toml config.toml
```

Edit `config.toml` to list the channels you want to track.

### Get your OAuth token

1. Log into <https://www.twitch.tv> in your browser.
2. Open DevTools → **Application** → **Cookies** → `https://www.twitch.tv`.
3. Copy the value of the `auth-token` cookie.
4. Paste it into `.env` as `TWITCH_OAUTH_TOKEN=...` (no `OAuth ` prefix — the tool
   adds that itself).

The token is long-lived but not forever; if requests start failing with auth errors,
grab a fresh one.

## Usage

```bash
# One-off poll (good for verifying setup):
uv run twitch-points collect --once

# Long-running daemon (poll every interval_seconds from config.toml):
uv run twitch-points collect

# Override interval ad-hoc:
uv run twitch-points collect --interval 60

# Backfill from an exported JSON dump (e.g. moonmoon.json):
uv run twitch-points backfill /path/to/moonmoon.json

# Web dashboard at http://127.0.0.1:8765:
uv run twitch-points serve
```

### Backfill format

`backfill` accepts JSON files of the form:

```json
{
  "series": [
    { "x": 1707189446000, "y": 417827, "z": "Watch" },
    { "x": 1707189746000, "y": 418189, "z": "Claim" }
  ]
}
```

`x` is a unix timestamp in milliseconds, `y` is the balance, `z` is an event label.
The channel name defaults to the JSON file's stem (`moonmoon.json` → `moonmoon`); pass
`--channel NAME` to override. Re-running on the same file is a no-op.

### Running the daemon long-term

Easiest path is the bundled installer, which writes a `systemd --user` unit
(no sudo) that runs `collect` from your project directory:

```bash
uv run twitch-points install            # writes the unit; tells you next steps
uv run twitch-points install --enable   # writes, daemon-reloads, and starts it
```

Useful follow-ups:

```bash
systemctl --user status twitch-points
journalctl --user -u twitch-points -f
systemctl --user disable --now twitch-points  # stop & forget
```

Re-run `install --force` whenever you move the project directory.

## Schema

```sql
CREATE TABLE points_snapshot (
  id      INTEGER PRIMARY KEY,
  ts      INTEGER NOT NULL,   -- unix seconds, UTC
  channel TEXT    NOT NULL,
  balance INTEGER NOT NULL,
  event   TEXT                -- NULL for live polls; populated for backfilled rows
);
```
