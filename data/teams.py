"""
Team-based traffic demand data for WC 2026.

HOW IT WORKS
------------
Not all games draw the same crowd to the ROADS even at the same stadium.
USA games in the US bring out a massive domestic fanbase far beyond ticket
holders — surrounding roads flood with watch-party traffic, fan zone crowds,
and people trying to drive near the stadium. Brazil/Argentina/Mexico have
similarly outsized US-based fanbases.

Two factors drive the team multiplier:
  1. FIFA World Ranking  — proxy for global interest / quality of matchup
  2. Host nation / diaspora bonus — USA (enormous), Mexico (large US fanbase),
     Canada (host nation, smaller soccer following)

The combined team multiplier is a modest adjustment (±15–30%) applied
on top of the stage-importance multiplier. It is NOT the dominant factor —
stage importance and venue still matter more. But USA vs Brazil will
meaningfully outpace Iran vs New Zealand at the same stadium.
"""

from typing import Tuple

# ---------------------------------------------------------------------------
# FIFA World Rankings — approximate May 2026 estimates.
# Lower number = better team = more global interest.
# ---------------------------------------------------------------------------
FIFA_RANKINGS: dict = {
    # Top tier (1–10)
    "Argentina":    1,
    "France":       2,
    "Spain":        3,
    "England":      4,
    "Brazil":       5,
    "Portugal":     6,
    "Netherlands":  7,
    "Belgium":      8,
    "Italy":        9,
    "Germany":     10,

    # Strong (11–25)
    "Croatia":     11,
    "Colombia":    12,
    "Uruguay":     13,
    "USA":         14,
    "Morocco":     15,
    "Japan":       16,
    "Senegal":     17,
    "Switzerland": 18,
    "Mexico":      19,
    "Denmark":     20,
    "Austria":     21,
    "South Korea": 22,
    "Australia":   23,
    "Ecuador":     24,
    "Hungary":     25,

    # Competitive (26–45)
    "Ukraine":       26,
    "Türkiye":       27,
    "Turkey":        27,   # alternate spelling
    "Chile":         28,
    "Serbia":        29,
    "Poland":        30,
    "Saudi Arabia":  31,
    "Egypt":         32,
    "Nigeria":       33,
    "Algeria":       34,
    "Ivory Coast":   35,
    "Côte d'Ivoire": 35,
    "Norway":        36,
    "Wales":         37,
    "Sweden":        38,
    "Scotland":      39,
    "Venezuela":     40,
    "Iran":          41,
    "Paraguay":      42,
    "Costa Rica":    43,
    "Mali":          44,
    "Ghana":         45,

    # Mid-tier (46–65)
    "Cameroon":    46,
    "Canada":      47,
    "Panama":      48,
    "Tunisia":     49,
    "Honduras":    50,
    "Qatar":       51,
    "Uzbekistan":  52,
    "Iraq":        53,
    "Bolivia":     54,
    "Jamaica":     55,
    "El Salvador": 56,
    "New Zealand": 57,

    # Lower tier (66+)
    "Curaçao":     72,
    "Curacao":     72,   # alternate spelling
    "Haiti":       78,
}

# ---------------------------------------------------------------------------
# Host nation / diaspora bonuses
# Added on top of the ranking-based score. Reflects road congestion from
# fans who aren't attending the game but are watching nearby, driving toward
# fan zones, or simply caught in event-zone traffic.
# ---------------------------------------------------------------------------
HOST_NATION_BONUS: dict = {
    "USA":          0.42,  # Enormous domestic fanbase + home tournament fever
    "Mexico":       0.22,  # Massive US-based Mexican fanbase (LA, Houston, Dallas)
    "Canada":       0.09,  # Host nation but smaller soccer following than USA/Mexico
}

# ---------------------------------------------------------------------------
# Global brand bonuses
# Some teams have outsized worldwide fanbases relative to their ranking.
# Brazil and Argentina, in particular, have enormous US-based diaspora
# communities and universal appeal beyond local fans.
# ---------------------------------------------------------------------------
GLOBAL_BRAND_BONUS: dict = {
    "Brazil":      0.06,
    "Argentina":   0.05,
    "England":     0.03,
    "Germany":     0.03,
    "France":      0.02,
    "Portugal":    0.02,
}

# Neutral reference score — two average WC-caliber teams (approx rank 35)
# Combined score at this level maps to a multiplier of exactly 1.0
_NEUTRAL_COMBINED = 0.65

# How strongly the team matchup scales the multiplier
# 0.30 → a maximal-interest game (USA vs Brazil) adds ~+20% over neutral
_SENSITIVITY = 0.30


def _team_interest_score(team: str) -> float:
    """
    Interest score for a single team (0.25 – ~1.4).
    Combines FIFA ranking, host nation bonus, and global brand bonus.
    """
    if team == "TBD":
        # Unknown knockout-stage team — assume average WC quality
        return _NEUTRAL_COMBINED

    rank = FIFA_RANKINGS.get(team, 65)

    # Rank 1  → 1.00
    # Rank 10 → 0.88
    # Rank 30 → 0.63
    # Rank 60 → 0.24 (floored at 0.25)
    base = max(0.25, 1.01 - (rank - 1) * 0.013)

    bonus = HOST_NATION_BONUS.get(team, 0.0)
    brand = GLOBAL_BRAND_BONUS.get(team, 0.0)

    return base + bonus + brand


def get_team_demand_multiplier(home: str, away: str) -> float:
    """
    Traffic demand multiplier for a specific matchup.

    Returns a value centered around 1.0:
      < 1.0  → less interesting matchup (weaker teams), slightly less road traffic
      = 1.0  → average WC matchup
      > 1.0  → high-demand matchup (USA, Brazil, top-ranked teams)

    Typical range: 0.88 – 1.30
    Examples:
      Curaçao vs Haiti    → ~0.88  (both low-ranked, low diaspora)
      Japan vs Sweden     → ~1.04
      Brazil vs Morocco   → ~1.08
      USA vs Paraguay     → ~1.11
      USA vs Türkiye      → ~1.12
      USA vs Brazil       → ~1.25  (hypothetical — both get strong boosts)

    Parameters
    ----------
    home, away : str
        Team names as they appear in data/schedule.py
        "TBD" is handled gracefully (returns 1.0 — no adjustment)

    Returns
    -------
    float
        Multiplier to apply to the peak traffic value
    """
    if home == "TBD" and away == "TBD":
        return 1.0   # Unknown matchup — no adjustment

    score_home = _team_interest_score(home)
    score_away = _team_interest_score(away)
    combined   = (score_home + score_away) / 2.0

    multiplier = 1.0 + (combined - _NEUTRAL_COMBINED) * _SENSITIVITY

    # Floor at 0.85 — even the weakest game doesn't reduce traffic below 85%
    return round(max(0.85, multiplier), 3)


def get_matchup_demand_info(home: str, away: str) -> dict:
    """
    Return a breakdown of the team demand calculation for display.

    Returns
    -------
    dict with keys: home_score, away_score, combined, multiplier, label
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
