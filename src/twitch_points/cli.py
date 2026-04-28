from __future__ import annotations

import argparse
import logging
import sys

from twitch_points.backfill import backfill_file
from twitch_points.collector import one_shot, run_forever
from twitch_points.config import load_config


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="twitch-points")
    p.add_argument("--config", default="config.toml", help="path to config.toml")
    p.add_argument("--env", default=".env", help="path to .env file")

    sub = p.add_subparsers(dest="cmd", required=True)

    coll = sub.add_parser("collect", help="poll channel-point balances")
    coll.add_argument("--once", action="store_true", help="poll a single time and exit")
    coll.add_argument(
        "--interval",
        type=int,
        default=None,
        help="override poll interval (seconds); daemon mode only",
    )

    bf = sub.add_parser("backfill", help="import a {series:[{x,y,z}]} JSON dump")
    bf.add_argument("file", help="path to JSON file")
    bf.add_argument(
        "--channel",
        default=None,
        help="channel name (defaults to file stem, e.g. moonmoon.json -> moonmoon)",
    )

    sub.add_parser("serve", help="run the local web dashboard")

    inst = sub.add_parser(
        "install",
        help="write a systemd --user unit that runs `collect` as a daemon",
    )
    inst.add_argument(
        "--workdir",
        default=None,
        help="working directory for the service (defaults to current dir)",
    )
    inst.add_argument(
        "--enable",
        action="store_true",
        help="also `systemctl --user enable --now` the service",
    )
    inst.add_argument(
        "--force", action="store_true", help="overwrite an existing unit file"
    )

    return p


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    args = build_parser().parse_args(argv)

    if args.cmd == "backfill":
        # Backfill doesn't need OAuth or channels, only db_path. Try config but tolerate missing.
        try:
            cfg = load_config(args.config, args.env)
            db_path = cfg.db_path
        except FileNotFoundError:
            db_path = "points.db"
            logging.info("no config.toml found, defaulting db_path=points.db")
        inserted, total = backfill_file(args.file, db_path, channel=args.channel)
        print(f"inserted {inserted} new rows out of {total} entries in {args.file}")
        return 0

    if args.cmd == "install":
        from pathlib import Path

        from twitch_points.install import install_service
        return install_service(
            workdir=Path(args.workdir) if args.workdir else None,
            enable=args.enable,
            force=args.force,
        )

    cfg = load_config(args.config, args.env)

    if args.cmd == "collect":
        if not cfg.oauth_token:
            print("error: TWITCH_OAUTH_TOKEN not set in .env", file=sys.stderr)
            return 2
        if args.once:
            inserted = one_shot(cfg)
            print(f"inserted {inserted} new snapshot(s)")
            return 0
        run_forever(cfg, interval=args.interval)
        return 0

    if args.cmd == "serve":
        from twitch_points.dashboard import serve
        serve(cfg)
        return 0

    return 1
