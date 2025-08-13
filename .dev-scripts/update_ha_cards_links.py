#!/usr/bin/env python3
"""
Scans ha_card/*.yaml and updates the README.md HA cards links section between
BEGIN/END markers. Keeps existing concise notes for known cards where possible.
"""

from __future__ import annotations

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
CARDS_DIR = REPO_ROOT / "ha_card"

BEGIN = "<!-- BEGIN: ha_cards_list (auto-managed) -->"
END = "<!-- END: ha_cards_list -->"

# Optional per-file notes map (extend as needed)
NOTES = {
    "mshrm_twickenham_events_short_card.yaml": "Uses `sensor.twickenham_events_next` with flat attributes (date, start_time, fixture_short, emoji, event_index, event_count); state is the full `fixture`.",
    "md_twickenham_events_upcoming.yaml": "Renders `events_json.by_month[].days[].events[]` with `ev.start_time`, `ev.emoji`, `ev.fixture`, `ev.crowd`.",
}


def make_entry(fname: str) -> str:
    path = f"ha_card/{fname}"
    title = fname.replace("_", " ").replace(".yaml", "").strip()
    line = f"- {title}: [{path}]({path})\n"
    note = NOTES.get(fname)
    if note:
        line += f"  - {note}\n"
    return line


def main() -> int:
    if not README.exists() or not CARDS_DIR.exists():
        return 1

    content = README.read_text(encoding="utf-8")
    m = re.search(re.escape(BEGIN) + r"[\s\S]*?" + re.escape(END), content)
    if not m:
        return 2

    files = sorted(p.name for p in CARDS_DIR.glob("*.yaml"))
    body = "\n\n" + "".join(make_entry(f) for f in files) + "\n"
    replacement = BEGIN + body + END
    new_content = content[: m.start()] + replacement + content[m.end() :]

    if new_content != content:
        README.write_text(new_content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
