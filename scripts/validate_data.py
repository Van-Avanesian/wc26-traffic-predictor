#!/usr/bin/env python3
"""
Validate the JSON data files for referential integrity.

Run this after editing any data file (especially schedule.json when adding a new
round) to catch typos before they reach the live app:

    python3 scripts/validate_data.py

Checks:
  • every game's venue_id exists in venues
  • every game's stage_importance is 1–6 and expected_capacity_pct is sane
  • every reference event's venue_id exists in venues
  • warns (doesn't fail) when a non-TBD team is missing from the FIFA rankings,
    since the demand model silently falls back to a default rank for those

Exits with status 1 if any hard error is found, 0 otherwise — so it can be
wired into a pre-deploy check or CI later.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.venues import VENUES
from data.schedule import WC_SCHEDULE
from data.teams import FIFA_RANKINGS
from data.reference_events import REFERENCE_EVENTS

errors: list[str] = []
warnings: list[str] = []


def check_games() -> None:
    for g in WC_SCHEDULE:
        gid = g.get("game_id", "<no id>")

        if g["venue_id"] not in VENUES:
            errors.append(f"[schedule] {gid}: unknown venue_id '{g['venue_id']}'")

        if not (1 <= g["stage_importance"] <= 6):
            errors.append(f"[schedule] {gid}: stage_importance {g['stage_importance']} out of range 1–6")

        if not (0.0 < g["expected_capacity_pct"] <= 1.1):
            errors.append(f"[schedule] {gid}: expected_capacity_pct {g['expected_capacity_pct']} looks wrong")

        for side in ("home", "away"):
            team = g[side]
            if team != "TBD" and team not in FIFA_RANKINGS:
                warnings.append(f"[schedule] {gid}: team '{team}' not in FIFA_RANKINGS (defaults to rank 65)")


def check_reference_events() -> None:
    for e in REFERENCE_EVENTS:
        if e["venue_id"] not in VENUES:
            errors.append(f"[reference_events] '{e.get('event_name', '?')}': unknown venue_id '{e['venue_id']}'")


def main() -> int:
    check_games()
    check_reference_events()

    print(f"Checked {len(WC_SCHEDULE)} games, {len(REFERENCE_EVENTS)} reference events, "
          f"{len(VENUES)} venues.\n")

    for w in warnings:
        print(f"  WARN  {w}")
    for e in errors:
        print(f"  ERROR {e}")

    if errors:
        print(f"\n❌ {len(errors)} error(s) found.")
        return 1

    print(f"\n✅ All checks passed" + (f" ({len(warnings)} warning(s))." if warnings else "."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
