"""
FIFA World Cup 2026 match schedule for all US venues.

Sources: FIFA.com, NBC Sports, Fox Sports (confirmed December 2025).
Tournament runs June 11 – July 19, 2026.
Final is at MetLife Stadium on July 19, 2026.

Kickoff times are stored in LOCAL venue time.
Stage importance scores used by the traffic model:
  1 = Group Stage
  2 = Round of 32
  3 = Round of 16
  4 = Quarter-Final
  5 = Semi-Final
  6 = Final / Third Place
"""

from datetime import date, time

# ---------------------------------------------------------------------------
# expected_capacity_pct: our estimate of what % of seats will be filled.
# WC 2026 demand is extraordinary — even group stage games expect 90–99%.
# Knockout rounds are effectively 100%.
# ---------------------------------------------------------------------------

WC_SCHEDULE = [

    # ── SoFi Stadium (Los Angeles) ──────────────────────────────────────────
    {
        "game_id": "GS_LAX_01",
        "venue_id": "sofi",
        "stage": "Group Stage",
        "stage_importance": 1,
        "group": "D",
        "home": "USA",
        "away": "Paraguay",
        "date": date(2026, 6, 12),
        "kickoff_local": time(18, 0),   # 6pm PT (9pm ET)
        "expected_capacity_pct": 0.99,
    },
    {
        "game_id": "GS_LAX_02",
        "venue_id": "sofi",
        "stage": "Group Stage",
        "stage_importance": 1,
        "group": "E",
        "home": "Iran",
        "away": "New Zealand",
        "date": date(2026, 6, 15),
        "kickoff_local": time(18, 0),   # 6pm PT
        "expected_capacity_pct": 0.88,
    },
    {
        "game_id": "GS_LAX_03",
        "venue_id": "sofi",
        "stage": "Group Stage",
        "stage_importance": 1,
        "group": "D",
        "home": "USA",
        "away": "Türkiye",
        "date": date(2026, 6, 22),
        "kickoff_local": time(21, 0),   # 9pm PT
        "expected_capacity_pct": 0.99,
    },

    # ── Levi's Stadium (San Francisco) ──────────────────────────────────────
    {
        "game_id": "GS_SFO_01",
        "venue_id": "levis",
        "stage": "Group Stage",
        "stage_importance": 1,
        "group": "D",
        "home": "Türkiye",
        "away": "Paraguay",
        "date": date(2026, 6, 19),
        "kickoff_local": time(21, 0),   # 9pm PT (midnight ET)
        "expected_capacity_pct": 0.90,
    },
    {
        "game_id": "GS_SFO_02",
        "venue_id": "levis",
        "stage": "Group Stage",
        "stage_importance": 1,
        "group": "D",
        "home": "Paraguay",
        "away": "Australia",
        "date": date(2026, 6, 25),
        "kickoff_local": time(19, 0),   # 7pm PT (10pm ET)
        "expected_capacity_pct": 0.92,
    },

    # ── Lumen Field (Seattle) ────────────────────────────────────────────────
    {
        "game_id": "GS_SEA_01",
        "venue_id": "lumen_field",
        "stage": "Group Stage",
        "stage_importance": 1,
        "group": "D",
        "home": "USA",
        "away": "Australia",
        "date": date(2026, 6, 19),
        "kickoff_local": time(12, 0),   # Noon PT (3pm ET)
        "expected_capacity_pct": 0.99,
    },

    # ── AT&T Stadium (Dallas) ────────────────────────────────────────────────
    {
        "game_id": "GS_DAL_01",
        "venue_id": "att",
        "stage": "Group Stage",
        "stage_importance": 1,
        "group": "C",
        "home": "Netherlands",
        "away": "Japan",
        "date": date(2026, 6, 14),
        "kickoff_local": time(15, 0),   # 3pm CT (4pm ET)
        "expected_capacity_pct": 0.93,
    },
    {
        "game_id": "GS_DAL_02",
        "venue_id": "att",
        "stage": "Group Stage",
        "stage_importance": 1,
        "group": "C",
        "home": "Japan",
        "away": "Sweden",
        "date": date(2026, 6, 25),
        "kickoff_local": time(18, 0),   # 6pm CT (7pm ET)
        "expected_capacity_pct": 0.91,
    },

    # ── NRG Stadium (Houston) ────────────────────────────────────────────────
    {
        "game_id": "GS_HOU_01",
        "venue_id": "nrg",
        "stage": "Group Stage",
        "stage_importance": 1,
        "group": "B",
        "home": "Germany",
        "away": "Curaçao",
        "date": date(2026, 6, 14),
        "kickoff_local": time(12, 0),   # Noon CT (1pm ET)
        "expected_capacity_pct": 0.94,
    },
    {
        "game_id": "GS_HOU_02",
        "venue_id": "nrg",
        "stage": "Group Stage",
        "stage_importance": 1,
        "group": "C",
        "home": "Netherlands",
        "away": "Sweden",
        "date": date(2026, 6, 20),
        "kickoff_local": time(12, 0),   # Noon CT (1pm ET)
        "expected_capacity_pct": 0.93,
    },

    # ── Arrowhead Stadium (Kansas City) ─────────────────────────────────────
    {
        "game_id": "GS_KC_01",
        "venue_id": "arrowhead",
        "stage": "Group Stage",
        "stage_importance": 1,
        "group": "A",
        "home": "Ecuador",
        "away": "Curaçao",
        "date": date(2026, 6, 20),
        "kickoff_local": time(19, 0),   # 7pm CT (8pm ET)
        "expected_capacity_pct": 0.88,
    },
    {
        "game_id": "GS_KC_02",
        "venue_id": "arrowhead",
        "stage": "Group Stage",
        "stage_importance": 1,
        "group": "C",
        "home": "Tunisia",
        "away": "Netherlands",
        "date": date(2026, 6, 25),
        "kickoff_local": time(18, 0),   # 6pm CT (7pm ET)
        "expected_capacity_pct": 0.90,
    },

    # ── MetLife Stadium (New York / New Jersey) ──────────────────────────────
    {
        "game_id": "GS_NYJ_01",
        "venue_id": "metlife",
        "stage": "Group Stage",
        "stage_importance": 1,
        "group": "F",
        "home": "Brazil",
        "away": "Morocco",
        "date": date(2026, 6, 13),
        "kickoff_local": time(18, 0),   # 6pm ET
        "expected_capacity_pct": 0.99,
    },
    {
        "game_id": "GS_NYJ_02",
        "venue_id": "metlife",
        "stage": "Group Stage",
        "stage_importance": 1,
        "group": "A",
        "home": "Ecuador",
        "away": "Germany",
        "date": date(2026, 6, 25),
        "kickoff_local": time(16, 0),   # 4pm ET
        "expected_capacity_pct": 0.96,
    },

    # ── Hard Rock Stadium (Miami) ────────────────────────────────────────────
    {
        "game_id": "GS_MIA_01",
        "venue_id": "hard_rock",
        "stage": "Group Stage",
        "stage_importance": 1,
        "group": "F",
        "home": "Scotland",
        "away": "Brazil",
        "date": date(2026, 6, 24),
        "kickoff_local": time(18, 0),   # 6pm ET
        "expected_capacity_pct": 0.97,
    },

    # ── Gillette Stadium (Boston) ────────────────────────────────────────────
    {
        "game_id": "GS_BOS_01",
        "venue_id": "gillette",
        "stage": "Group Stage",
        "stage_importance": 1,
        "group": "F",
        "home": "Haiti",
        "away": "Scotland",
        "date": date(2026, 6, 13),
        "kickoff_local": time(21, 0),   # 9pm ET
        "expected_capacity_pct": 0.86,
    },
    {
        "game_id": "GS_BOS_02",
        "venue_id": "gillette",
        "stage": "Group Stage",
        "stage_importance": 1,
        "group": "F",
        "home": "Scotland",
        "away": "Morocco",
        "date": date(2026, 6, 19),
        "kickoff_local": time(18, 0),   # 6pm ET
        "expected_capacity_pct": 0.91,
    },

    # ── Lincoln Financial Field (Philadelphia) ───────────────────────────────
    {
        "game_id": "GS_PHI_01",
        "venue_id": "lincoln_financial",
        "stage": "Group Stage",
        "stage_importance": 1,
        "group": "A",
        "home": "Ivory Coast",
        "away": "Ecuador",
        "date": date(2026, 6, 14),
        "kickoff_local": time(19, 0),   # 7pm ET
        "expected_capacity_pct": 0.90,
    },
    {
        "game_id": "GS_PHI_02",
        "venue_id": "lincoln_financial",
        "stage": "Group Stage",
        "stage_importance": 1,
        "group": "A",
        "home": "Curaçao",
        "away": "Ivory Coast",
        "date": date(2026, 6, 25),
        "kickoff_local": time(16, 0),   # 4pm ET
        "expected_capacity_pct": 0.88,
    },

    # ── Mercedes-Benz Stadium (Atlanta) ─────────────────────────────────────
    {
        "game_id": "GS_ATL_01",
        "venue_id": "mercedes_benz",
        "stage": "Group Stage",
        "stage_importance": 1,
        "group": "F",
        "home": "Morocco",
        "away": "Haiti",
        "date": date(2026, 6, 24),
        "kickoff_local": time(18, 0),   # 6pm ET
        "expected_capacity_pct": 0.93,
    },

    # ── KNOCKOUT ROUNDS ──────────────────────────────────────────────────────
    # Exact matchups are TBD (determined by group stage results),
    # but venues are pre-assigned. These are labeled with TBD teams.
    # The app will display them as "Round of 32 Match" etc.

    # Round of 32 — June 28–July 3 (actual matchups)
    # Times are venue-LOCAL. Four R32 games (Netherlands–Morocco, Mexico–Ecuador,
    # Portugal–Croatia, Switzerland–Algeria) are played in Mexico/Canada and are
    # not included because this app only covers the 11 US venues.

    # Sun Jun 28
    {
        "game_id": "R32_LAX_01",
        "venue_id": "sofi",
        "stage": "Round of 32",
        "stage_importance": 2,
        "group": None,
        "home": "South Africa",
        "away": "Canada",
        "date": date(2026, 6, 28),
        "kickoff_local": time(12, 0),   # 12pm PT
        "expected_capacity_pct": 0.97,
    },

    # Mon Jun 29
    {
        "game_id": "R32_HOU_01",
        "venue_id": "nrg",
        "stage": "Round of 32",
        "stage_importance": 2,
        "group": None,
        "home": "Brazil",
        "away": "Japan",
        "date": date(2026, 6, 29),
        "kickoff_local": time(12, 0),   # 12pm CT (1pm ET)
        "expected_capacity_pct": 0.99,
    },
    {
        "game_id": "R32_BOS_01",
        "venue_id": "gillette",
        "stage": "Round of 32",
        "stage_importance": 2,
        "group": None,
        "home": "Germany",
        "away": "Paraguay",
        "date": date(2026, 6, 29),
        "kickoff_local": time(16, 30),  # 4:30pm ET
        "expected_capacity_pct": 0.97,
    },

    # Tue Jun 30
    {
        "game_id": "R32_DAL_01",
        "venue_id": "att",
        "stage": "Round of 32",
        "stage_importance": 2,
        "group": None,
        "home": "Ivory Coast",
        "away": "Norway",
        "date": date(2026, 6, 30),
        "kickoff_local": time(12, 0),   # 12pm CT (1pm ET)
        "expected_capacity_pct": 0.94,
    },
    {
        "game_id": "R32_NYJ_01",
        "venue_id": "metlife",
        "stage": "Round of 32",
        "stage_importance": 2,
        "group": None,
        "home": "France",
        "away": "Sweden",
        "date": date(2026, 6, 30),
        "kickoff_local": time(17, 0),   # 5pm ET
        "expected_capacity_pct": 0.98,
    },

    # Wed Jul 1
    {
        "game_id": "R32_ATL_01",
        "venue_id": "mercedes_benz",
        "stage": "Round of 32",
        "stage_importance": 2,
        "group": None,
        "home": "England",
        "away": "Congo DR",
        "date": date(2026, 7, 1),
        "kickoff_local": time(12, 0),   # 12pm ET
        "expected_capacity_pct": 0.97,
    },
    {
        "game_id": "R32_SEA_01",
        "venue_id": "lumen_field",
        "stage": "Round of 32",
        "stage_importance": 2,
        "group": None,
        "home": "Belgium",
        "away": "Senegal",
        "date": date(2026, 7, 1),
        "kickoff_local": time(13, 0),   # 1pm PT
        "expected_capacity_pct": 0.96,
    },
    {
        "game_id": "R32_SFO_01",
        "venue_id": "levis",
        "stage": "Round of 32",
        "stage_importance": 2,
        "group": None,
        "home": "USA",
        "away": "Bosnia and Herzegovina",
        "date": date(2026, 7, 1),
        "kickoff_local": time(17, 0),   # 5pm PT
        "expected_capacity_pct": 0.99,
    },

    # Thu Jul 2
    {
        "game_id": "R32_LAX_02",
        "venue_id": "sofi",
        "stage": "Round of 32",
        "stage_importance": 2,
        "group": None,
        "home": "Spain",
        "away": "Austria",
        "date": date(2026, 7, 2),
        "kickoff_local": time(12, 0),   # 12pm PT
        "expected_capacity_pct": 0.98,
    },

    # Fri Jul 3
    {
        "game_id": "R32_DAL_02",
        "venue_id": "att",
        "stage": "Round of 32",
        "stage_importance": 2,
        "group": None,
        "home": "Australia",
        "away": "Egypt",
        "date": date(2026, 7, 3),
        "kickoff_local": time(13, 0),   # 1pm CT (2pm ET)
        "expected_capacity_pct": 0.94,
    },
    {
        "game_id": "R32_MIA_01",
        "venue_id": "hard_rock",
        "stage": "Round of 32",
        "stage_importance": 2,
        "group": None,
        "home": "Argentina",
        "away": "Cape Verde",
        "date": date(2026, 7, 3),
        "kickoff_local": time(18, 0),   # 6pm ET
        "expected_capacity_pct": 0.99,
    },
    {
        "game_id": "R32_KC_01",
        "venue_id": "arrowhead",
        "stage": "Round of 32",
        "stage_importance": 2,
        "group": None,
        "home": "Colombia",
        "away": "Ghana",
        "date": date(2026, 7, 3),
        "kickoff_local": time(20, 30),  # 8:30pm CT
        "expected_capacity_pct": 0.96,
    },

    # Round of 16 — July 4–6 (actual matchups)
    # Times are venue-LOCAL. Mexico–England is played at Estadio Azteca
    # (Mexico City) and is not included — this app only covers US venues.

    # Sat Jul 4
    {
        "game_id": "R16_HOU_01",
        "venue_id": "nrg",
        "stage": "Round of 16",
        "stage_importance": 3,
        "group": None,
        "home": "Canada",
        "away": "Morocco",
        "date": date(2026, 7, 4),
        "kickoff_local": time(12, 0),   # 10am PT → 12pm CT
        "expected_capacity_pct": 0.97,
    },
    {
        "game_id": "R16_PHI_01",
        "venue_id": "lincoln_financial",
        "stage": "Round of 16",
        "stage_importance": 3,
        "group": None,
        "home": "Paraguay",
        "away": "France",
        "date": date(2026, 7, 4),
        "kickoff_local": time(17, 0),   # 2pm PT → 5pm ET
        "expected_capacity_pct": 0.98,
    },

    # Sun Jul 5
    {
        "game_id": "R16_NYJ_01",
        "venue_id": "metlife",
        "stage": "Round of 16",
        "stage_importance": 3,
        "group": None,
        "home": "Brazil",
        "away": "Norway",
        "date": date(2026, 7, 5),
        "kickoff_local": time(16, 0),   # 1pm PT → 4pm ET
        "expected_capacity_pct": 0.99,
    },

    # Mon Jul 6
    {
        "game_id": "R16_DAL_01",
        "venue_id": "att",
        "stage": "Round of 16",
        "stage_importance": 3,
        "group": None,
        "home": "Portugal",
        "away": "Spain",
        "date": date(2026, 7, 6),
        "kickoff_local": time(14, 0),   # 12pm PT → 2pm CT
        "expected_capacity_pct": 0.99,
    },
    {
        "game_id": "R16_SEA_01",
        "venue_id": "lumen_field",
        "stage": "Round of 16",
        "stage_importance": 3,
        "group": None,
        "home": "USA",
        "away": "Belgium",
        "date": date(2026, 7, 6),
        "kickoff_local": time(17, 0),   # 5pm PT
        "expected_capacity_pct": 0.99,
    },

    # Tue Jul 7  (Colombia v Switzerland is at BC Place, Vancouver — out of scope)
    {
        "game_id": "R16_ATL_01",
        "venue_id": "mercedes_benz",
        "stage": "Round of 16",
        "stage_importance": 3,
        "group": None,
        "home": "Argentina",
        "away": "Egypt",
        "date": date(2026, 7, 7),
        "kickoff_local": time(12, 0),   # 9am PT → 12pm ET
        "expected_capacity_pct": 0.98,
    },

    # Quarter-Finals — July 9–11 (actual matchups)
    # Thu Jul 9
    {
        "game_id": "QF_BOS_01",
        "venue_id": "gillette",
        "stage": "Quarter-Final",
        "stage_importance": 4,
        "group": None,
        "home": "France",
        "away": "Morocco",
        "date": date(2026, 7, 9),
        "kickoff_local": time(16, 0),   # 1pm PT → 4pm ET
        "expected_capacity_pct": 1.0,
    },
    # Fri Jul 10
    {
        "game_id": "QF_LAX_01",
        "venue_id": "sofi",
        "stage": "Quarter-Final",
        "stage_importance": 4,
        "group": None,
        "home": "Spain",
        "away": "Belgium",
        "date": date(2026, 7, 10),
        "kickoff_local": time(12, 0),   # 12pm PT
        "expected_capacity_pct": 1.0,
    },
    # Sat Jul 11
    {
        "game_id": "QF_MIA_01",
        "venue_id": "hard_rock",
        "stage": "Quarter-Final",
        "stage_importance": 4,
        "group": None,
        "home": "Norway",
        "away": "England",
        "date": date(2026, 7, 11),
        "kickoff_local": time(17, 0),   # 2pm PT → 5pm ET
        "expected_capacity_pct": 1.0,
    },
    {
        "game_id": "QF_KC_01",
        "venue_id": "arrowhead",
        "stage": "Quarter-Final",
        "stage_importance": 4,
        "group": None,
        "home": "Argentina",
        "away": "Switzerland",
        "date": date(2026, 7, 11),
        "kickoff_local": time(20, 0),   # 6pm PT → 8pm CT
        "expected_capacity_pct": 1.0,
    },

    # Semi-Finals — July 14–15
    {
        "game_id": "SF_DAL_01",
        "venue_id": "att",
        "stage": "Semi-Final",
        "stage_importance": 5,
        "group": None,
        "home": "TBD",
        "away": "TBD",
        "date": date(2026, 7, 14),
        "kickoff_local": time(18, 0),
        "expected_capacity_pct": 1.0,
    },
    {
        "game_id": "SF_NYJ_01",
        "venue_id": "metlife",
        "stage": "Semi-Final",
        "stage_importance": 5,
        "group": None,
        "home": "TBD",
        "away": "TBD",
        "date": date(2026, 7, 15),
        "kickoff_local": time(18, 0),
        "expected_capacity_pct": 1.0,
    },

    # Third Place — July 18
    {
        "game_id": "3RD_MIA_01",
        "venue_id": "hard_rock",
        "stage": "Third Place",
        "stage_importance": 6,
        "group": None,
        "home": "TBD",
        "away": "TBD",
        "date": date(2026, 7, 18),
        "kickoff_local": time(15, 0),
        "expected_capacity_pct": 0.92,
    },

    # Final — July 19 at MetLife
    {
        "game_id": "FINAL_NYJ",
        "venue_id": "metlife",
        "stage": "Final",
        "stage_importance": 6,
        "group": None,
        "home": "TBD",
        "away": "TBD",
        "date": date(2026, 7, 19),
        "kickoff_local": time(18, 0),   # 6pm ET
        "expected_capacity_pct": 1.0,
    },
]


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
