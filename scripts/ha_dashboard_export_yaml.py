#!/usr/bin/env python3
"""Export Home Assistant Lovelace (raw storage) dashboard to YAML.

Fetches /api/lovelace/config using a Long-Lived Access Token and writes:
  * A single YAML file (default)
  * Optionally one YAML file per view (--split) in a target directory

Environment variables (required):
  HA_BASE_URL   e.g. https://homeassistant.local:8123
  HA_TOKEN      Long-Lived Access Token (profile > security)

Examples:
  # Single YAML file lovelace_export.yaml
  HA_BASE_URL=https://ha.local:8123 HA_TOKEN=$LLAT \
    poetry run python scripts/ha_dashboard_export_yaml.py

  # Custom output filename
  HA_BASE_URL=... HA_TOKEN=... \
    poetry run python scripts/ha_dashboard_export_yaml.py --out dashboards/main.yaml

  # Split per view (creates directory if needed)
  HA_BASE_URL=... HA_TOKEN=... \
    poetry run python scripts/ha_dashboard_export_yaml.py --split --out dashboards/

Notes:
  - Script is read-only (no POST updates).
  - The exported YAML mirrors the JSON structure (views, cards, etc.).
  - You can re-import manually via Raw Editor (convert back to JSON if required).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml


def fetch_lovelace(base_url: str, token: str) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/api/lovelace/config"
    req = Request(
        url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}
    )
    with urlopen(req, timeout=20) as resp:  # nosec B310
        return json.loads(resp.read().decode("utf-8"))


def write_single_yaml(cfg: dict[str, Any], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)
    return out_path


def write_split_yaml(cfg: dict[str, Any], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    meta = {k: v for k, v in cfg.items() if k != "views"}
    meta_path = out_dir / "_lovelace_meta.yaml"
    with meta_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(meta, f, sort_keys=False, allow_unicode=True)
    written.append(meta_path)
    for idx, view in enumerate(cfg.get("views", [])):
        view_id = view.get("path") or view.get("title") or f"view_{idx}"
        safe_id = (
            "".join(c for c in view_id if c.isalnum() or c in ("_", "-")).strip("_")
            or f"view_{idx}"
        )
        path = out_dir / f"{idx:02d}_{safe_id}.yaml"
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(view, f, sort_keys=False, allow_unicode=True)
        written.append(path)
    return written


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Export HA Lovelace dashboard to YAML")
    p.add_argument(
        "--out",
        default="lovelace_export.yaml",
        help="Output file or directory (when --split)",
    )
    p.add_argument(
        "--split", action="store_true", help="Write one YAML file per view + meta file"
    )
    p.add_argument(
        "--timestamp",
        action="store_true",
        help="Append UTC timestamp to output name(s)",
    )
    return p


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    base_url = os.environ.get("HA_BASE_URL")
    token = os.environ.get("HA_TOKEN")
    if not base_url or not token:
        print(
            "ERROR: HA_BASE_URL and HA_TOKEN environment variables are required",
            file=sys.stderr,
        )
        return 2

    try:
        cfg = fetch_lovelace(base_url, token)
    except HTTPError as e:
        print(f"HTTP error {e.code}: {e}", file=sys.stderr)
        return 1
    except URLError as e:
        print(f"Connection error: {e}", file=sys.stderr)
        return 1

    timestamp_suffix = ""
    if args.timestamp:
        timestamp_suffix = "_" + dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    if args.split:
        out_dir = Path(args.out)
        if not out_dir.name:  # handle trailing slash
            out_dir = out_dir / "lovelace"
        if args.timestamp:
            out_dir = out_dir.with_name(out_dir.name + timestamp_suffix)
        written = write_split_yaml(cfg, out_dir)
        print("Wrote:")
        for p in written:
            print(f"  - {p}")
    else:
        out_file = Path(args.out)
        if args.timestamp:
            out_file = out_file.with_name(
                out_file.stem + timestamp_suffix + out_file.suffix
            )
        path = write_single_yaml(cfg, out_file)
        print(f"Wrote {path}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
