from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

UNIT_NAME = "twitch-points.service"

UNIT_TEMPLATE = """[Unit]
Description=Twitch channel-points collector
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory={workdir}
ExecStart={uv} run twitch-points collect
Restart=on-failure
RestartSec=30

[Install]
WantedBy=default.target
"""


def install_service(
    workdir: Path | None = None,
    enable: bool = False,
    force: bool = False,
) -> int:
    if sys.platform != "linux":
        print(f"error: install only supports Linux (got {sys.platform})", file=sys.stderr)
        return 2

    workdir = (workdir or Path.cwd()).resolve()
    if not (workdir / "config.toml").exists():
        print(
            f"error: no config.toml in {workdir} — run from the project dir or pass --workdir",
            file=sys.stderr,
        )
        return 2
    if not (workdir / ".env").exists():
        print(
            f"warning: no .env in {workdir} — collect will fail without TWITCH_OAUTH_TOKEN",
            file=sys.stderr,
        )

    uv = shutil.which("uv")
    if not uv:
        print("error: `uv` not found on PATH", file=sys.stderr)
        return 2

    unit_dir = Path(
        os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
    ) / "systemd" / "user"
    unit_dir.mkdir(parents=True, exist_ok=True)
    unit_path = unit_dir / UNIT_NAME

    if unit_path.exists() and not force:
        print(f"{unit_path} already exists. Pass --force to overwrite.", file=sys.stderr)
        return 1

    contents = UNIT_TEMPLATE.format(workdir=workdir, uv=uv)
    unit_path.write_text(contents)
    print(f"wrote {unit_path}")
    print(contents)

    # Reload systemd so the new unit is visible.
    rc = subprocess.run(
        ["systemctl", "--user", "daemon-reload"], check=False
    ).returncode
    if rc != 0:
        print(
            "warning: `systemctl --user daemon-reload` failed — is systemd-user running?",
            file=sys.stderr,
        )

    if enable:
        rc = subprocess.run(
            ["systemctl", "--user", "enable", "--now", UNIT_NAME], check=False
        ).returncode
        if rc != 0:
            print("error: enable --now failed", file=sys.stderr)
            return rc
        print(f"enabled and started {UNIT_NAME}")
        print(f"check status:  systemctl --user status {UNIT_NAME}")
        print(f"follow logs:   journalctl --user -u {UNIT_NAME} -f")
    else:
        print()
        print("Next steps:")
        print(f"  systemctl --user enable --now {UNIT_NAME}")
        print(f"  systemctl --user status {UNIT_NAME}")
        print(f"  journalctl --user -u {UNIT_NAME} -f")
        print()
        print("Or re-run `twitch-points install --enable` to do that automatically.")
    return 0
