"""
FIFA World Cup 2026 match schedule for all US venues.

The fixtures live in ``schedule.json``; this module loads them, parses the
date/time strings into real ``date``/``time`` objects, and exposes the list as
``WC_SCHEDULE`` (same shape as before) plus a couple of helper functions.

In the JSON, each game stores:
  "date":          "YYYY-MM-DD"   (parsed to datetime.date)
  "kickoff_local": "HH:MM"        (parsed to datetime.time, LOCAL venue time)

Stage importance scores used by the traffic model:
  1 = Group Stage   2 = Round of 32   3 = Round of 16
  4 = Quarter-Final 5 = Semi-Final    6 = Final / Third Place

expected_capacity_pct is our estimate of what % of seats will be filled. WC 2026
demand is extraordinary — even group games expect 90–99%, knockouts ~100%.
"""

import json
from datetime import date, time
from pathlib import Path

_DATA_PATH = Path(__file__).with_name("schedule.json")


def _parse_game(raw: dict) -> dict:
    """Convert a raw JSON game into one with real date/time objects."""
    game = dict(raw)
    game["date"] = date.fromisoformat(raw["date"])
    hour, minute = (int(p) for p in raw["kickoff_local"].split(":"))
    game["kickoff_local"] = time(hour, minute)
    return game


with open(_DATA_PATH, encoding="utf-8") as _f:
    WC_SCHEDULE = [_parse_game(g) for g in json.load(_f)]


def get_game_label(game: dict) -> str:
    """Return a human-readable label for a game (for the Streamlit dropdown)."""
    home = game["home"]
    away = game["away"]
    matchup = f"{home} vs {away}" if home != "TBD" else game["stage"]
    venue_city = {
        "metlife": "New York/NJ",
        "hard_rock": "Miami",
        "mercedes_benz": "Atlanta",
        "lincoln_financial": "Philadelphia",
        "lumen_field": "Seattle",
        "att": "Dallas",
        "nrg": "Houston",
        "arrowhead": "Kansas City",
        "sofi": "Los Angeles",
        "levis": "San Francisco",
        "gillette": "Boston",
    }
    city = venue_city.get(game["venue_id"], game["venue_id"])
    return f"{game['date'].strftime('%b %d')} | {matchup} | {city} ({game['stage']})"


def get_games_for_venue(venue_id: str) -> list:
    """Return all scheduled games at a given venue."""
    return [g for g in WC_SCHEDULE if g["venue_id"] == venue_id]
