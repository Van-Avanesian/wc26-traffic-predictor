"""
Team-based traffic demand for WC 2026.

The lookup data (FIFA rankings + diaspora/brand bonuses) lives in ``teams.json``;
the scoring *logic* stays here in Python.

HOW IT WORKS
------------
Not all games draw the same crowd to the ROADS, even at the same stadium. USA
games bring out a massive domestic fanbase far beyond ticket holders — watch
parties, fan zones, and people driving near the stadium. Brazil/Argentina/Mexico
have similarly outsized US-based followings.

Two factors drive the multiplier:
  1. FIFA World Ranking — proxy for global interest / quality of matchup.
  2. Host-nation / diaspora bonus — USA (enormous), Mexico (large US fanbase),
     Canada (host, smaller following).

The result is a modest adjustment (±15–30%) layered on top of the stage
multiplier. It is NOT the dominant factor — stage and venue still matter more —
but USA vs Brazil should meaningfully outpace Iran vs New Zealand at the same
stadium.
"""

import json
from pathlib import Path

_DATA_PATH = Path(__file__).with_name("teams.json")

with open(_DATA_PATH, encoding="utf-8") as _f:
    _data = json.load(_f)

# FIFA World Rankings (approx. May 2026). Lower = better = more global interest.
FIFA_RANKINGS: dict = _data["fifa_rankings"]

# Host-nation / diaspora bonuses, added on top of the ranking-based score.
# Reflects road congestion from fans who aren't attending but are watching
# nearby, driving toward fan zones, or simply caught in event-zone traffic.
HOST_NATION_BONUS: dict = _data["host_nation_bonus"]

# Some teams have worldwide fanbases beyond their ranking (Brazil, Argentina).
GLOBAL_BRAND_BONUS: dict = _data["global_brand_bonus"]

# Neutral reference: two average WC-caliber teams (~rank 35) → multiplier 1.0.
_NEUTRAL_COMBINED = 0.65

# How strongly the matchup scales the multiplier (0.30 → USA vs Brazil ≈ +20%).
_SENSITIVITY = 0.30


def _team_interest_score(team: str) -> float:
    """
    Interest score for a single team (0.25 – ~1.4).
    Combines FIFA ranking, host-nation bonus, and global-brand bonus.
    """
    if team == "TBD":
        # Unknown knockout-stage team — assume average WC quality.
        return _NEUTRAL_COMBINED

    rank = FIFA_RANKINGS.get(team, 65)

    # Rank 1 → 1.00, rank 10 → 0.88, rank 30 → 0.63, rank 60 → 0.24 (floored 0.25)
    base = max(0.25, 1.01 - (rank - 1) * 0.013)

    bonus = HOST_NATION_BONUS.get(team, 0.0)
    brand = GLOBAL_BRAND_BONUS.get(team, 0.0)

    return base + bonus + brand


def get_team_demand_multiplier(home: str, away: str) -> float:
    """
    Traffic demand multiplier for a specific matchup, centered around 1.0:
      < 1.0  weaker matchup, slightly less road traffic
      = 1.0  average WC matchup
      > 1.0  high-demand matchup (USA, Brazil, top-ranked teams)

    Typical range 0.88 – 1.30. Examples:
      Curaçao vs Haiti  → ~0.88     Brazil vs Morocco → ~1.08
      Japan vs Sweden   → ~1.04     USA vs Paraguay   → ~1.11

    "TBD" is handled gracefully (returns 1.0 — no adjustment).
    """
    if home == "TBD" and away == "TBD":
        return 1.0

    score_home = _team_interest_score(home)
    score_away = _team_interest_score(away)
    combined   = (score_home + score_away) / 2.0

    multiplier = 1.0 + (combined - _NEUTRAL_COMBINED) * _SENSITIVITY

    # Floor at 0.85 — even the weakest game doesn't cut traffic below 85%.
    return round(max(0.85, multiplier), 3)


def get_matchup_demand_info(home: str, away: str) -> dict:
    """
    Return a breakdown of the team demand calculation for display.
    Keys: home_score, away_score, combined, multiplier, label.
    """
    score_home = _team_interest_score(home)
    score_away = _team_interest_score(away)
    combined   = (score_home + score_away) / 2.0
    multiplier = get_team_demand_multiplier(home, away)

    if multiplier >= 1.20:
        label = "Marquee"
    elif multiplier >= 1.10:
        label = "High Demand"
    elif multiplier >= 1.00:
        label = "Standard"
    elif multiplier >= 0.92:
        label = "Moderate"
    else:
        label = "Low Draw"

    return {
        "home_score":  round(score_home, 3),
        "away_score":  round(score_away, 3),
        "combined":    round(combined, 3),
        "multiplier":  multiplier,
        "label":       label,
    }
