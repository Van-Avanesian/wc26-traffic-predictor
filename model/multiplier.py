"""
Traffic multiplier model for WC 2026 game days.

HOW IT WORKS
------------
Traffic multiplier = how much longer your trip takes on game day vs a
normal day. A multiplier of 2.5 means a 30-min drive becomes 75 min.

The model builds a smooth curve over time (hours relative to kickoff)
using two Gaussian components:
  1. Pre-game buildup  — peaks ~1h before kickoff
  2. Post-game egress  — peaks ~1.5h after kickoff

Curve parameters are set based on:
  • stage_importance  (group stage → final, 1–6)
  • expected_capacity_pct  (how full the stadium will be)
  • venue characteristics (transit score, parking, WC premium)
  • event_type (soccer peaks are narrower than concerts)

CALIBRATION
-----------
Peak multiplier values were anchored against real reference events
(Copa América 2024, CWC 2025, NFL playoffs, concerts) documented in
data/reference_events.py. WC 2026 applies an additional premium over
Copa América because:
  - More international fans unfamiliar with local transit
  - Larger security perimeters around stadiums
  - Fan zones create secondary congestion nearby
  - Higher global media presence (more production vehicles)
"""

import numpy as np
from scipy.interpolate import interp1d
from typing import List
from data.venues import VENUES
from data.teams import get_team_demand_multiplier


# ---------------------------------------------------------------------------
# Base peak multipliers by stage (calibrated to Copa América as reference)
# WC 2026 stages are universally bigger than Copa América equivalents.
# ---------------------------------------------------------------------------
STAGE_BASE_MULTIPLIERS = {
    1: 2.8,   # Group Stage   — WC group games ≈ Copa América QF demand
    2: 3.2,   # Round of 32   — novel WC stage, similar to Copa América QF
    3: 3.5,   # Round of 16
    4: 3.8,   # Quarter-Final
    5: 4.2,   # Semi-Final
    6: 4.6,   # Final / Third Place (Final gets full value, 3rd place gets 85%)
}

# Third-place match gets a discount — less demand than a true final
THIRD_PLACE_DISCOUNT = 0.85

# WC 2026 global premium over Copa América baseline
WC_GLOBAL_PREMIUM = 1.20

# How strongly attendance % scales the peak multiplier
# (0.0 = attendance doesn't matter, 1.0 = perfectly linear)
ATTENDANCE_SENSITIVITY = 0.7

# Time axis: hours relative to kickoff (negative = before, positive = after)
T_HOURS = np.linspace(-5.0, 4.0, 1000)


def _build_curve(
    peak_multiplier: float,
    pre_peak_offset: float = -1.0,    # hours before kickoff where pre-game peaks
    pre_sigma: float = 1.1,           # spread of pre-game Gaussian
    post_peak_offset: float = 1.5,    # hours after kickoff where post-game peaks
    post_sigma: float = 0.75,         # spread of post-game Gaussian
    post_ratio: float = 0.72,         # post-game peak as fraction of pre-game peak
) -> interp1d:
    """
    Build a smooth traffic multiplier curve over time.

    Returns a scipy interpolation function: f(hours_from_kickoff) → multiplier.
    Outside the [-5, 4] hour window, returns 1.0 (normal traffic).
    """
    amplitude = peak_multiplier - 1.0

    pre_game = amplitude * np.exp(
        -0.5 * ((T_HOURS - pre_peak_offset) / pre_sigma) ** 2
    )
    post_game = (amplitude * post_ratio) * np.exp(
        -0.5 * ((T_HOURS - post_peak_offset) / post_sigma) ** 2
    )

    combined = 1.0 + np.maximum(pre_game, post_game)

    return interp1d(
        T_HOURS,
        combined,
        kind="cubic",
        bounds_error=False,
        fill_value=1.0,
    )


def get_peak_multiplier(
    venue_id: str,
    stage_importance: int,
    expected_capacity_pct: float,
    stage: str = "",
    home: str = "TBD",
    away: str = "TBD",
) -> float:
    """
    Compute the expected peak traffic multiplier for a WC 2026 game.

    Parameters
    ----------
    venue_id : str
        Key from data/venues.VENUES
    stage_importance : int
        1 (Group Stage) through 6 (Final)
    expected_capacity_pct : float
        Expected fraction of capacity filled (0–1+)
    stage : str
        Stage name string (used to apply third-place discount)
    home, away : str
        Team names — used to apply team demand multiplier based on
        FIFA rankings and host-nation bonuses (USA/Mexico/Canada)

    Returns
    -------
    float
        Peak multiplier at the worst departure time
    """
    venue = VENUES[venue_id]

    # 1. Base multiplier from stage importance
    base = STAGE_BASE_MULTIPLIERS.get(stage_importance, 2.5)

    # 2. Third-place match discount
    if "third" in stage.lower() or "3rd" in stage.lower():
        base *= THIRD_PLACE_DISCOUNT

    # 3. Scale by attendance — more fans = more traffic
    #    At 100% capacity: full base. At 80%: slightly lower.
    attendance_scale = 1.0 - ATTENDANCE_SENSITIVITY * (1.0 - min(expected_capacity_pct, 1.0))
    base *= attendance_scale

    # 4. WC global premium
    base *= WC_GLOBAL_PREMIUM

    # 5. Venue-specific WC premium (from data/venues.py)
    base *= venue["wc_premium"]

    # 6. Transit adjustment — high transit score slightly reduces peak car multiplier
    #    (some fans take trains instead of cars, reducing road congestion)
    transit_reduction = 0.12 * venue["transit_score"]
    base *= (1.0 - transit_reduction)

    # 7. Team demand multiplier — based on FIFA rankings + host nation bonus
    #    USA games get a significant boost; Brazil/Argentina/Mexico get moderate boosts.
    #    Weak matchups (low-ranked teams, no diaspora) get a slight reduction.
    base *= get_team_demand_multiplier(home, away)

    return round(base, 3)


def get_multiplier_curve(
    venue_id: str,
    stage_importance: int,
    expected_capacity_pct: float,
    stage: str = "",
    kickoff_hour: int = 18,
    home: str = "TBD",
    away: str = "TBD",
) -> interp1d:
    """
    Get the full traffic multiplier curve for a game.

    The curve shape (sigma) adjusts slightly based on kickoff time:
      - Midday kickoffs → narrower pre-game buildup (less time to arrive)
      - Evening kickoffs → slightly wider spread (fans arrive over more hours)

    Parameters
    ----------
    kickoff_hour : int
        Local hour of kickoff (e.g. 18 for 6pm)

    Returns
    -------
    scipy interp1d function
        Call with hours_from_kickoff → returns multiplier float
    """
    peak = get_peak_multiplier(venue_id, stage_importance, expected_capacity_pct, stage, home, away)

    # Sigma controls how gradually traffic builds before the game.
    # Wider sigma = smoother curve = a 30-min shift in departure produces
    # a proportional (not cliff-like) change in travel time.
    # Previous values (0.85/1.0/1.15) were too narrow — the multiplier
    # doubled over a 30-min window, making the model extremely sensitive.
    if kickoff_hour < 14:
        pre_sigma = 1.4    # Noon games: fans still spread across morning
        pre_peak_offset = -1.0
    elif kickoff_hour < 17:
        pre_sigma = 1.6    # Afternoon games
        pre_peak_offset = -1.2
    else:
        pre_sigma = 1.9    # Evening games: traffic builds gradually all afternoon
        pre_peak_offset = -1.2

    return _build_curve(
        peak_multiplier=peak,
        pre_peak_offset=pre_peak_offset,
        pre_sigma=pre_sigma,
    )


def find_departure_time(
    baseline_minutes: float,
    venue_id: str,
    stage_importance: int,
    expected_capacity_pct: float,
    stage: str,
    kickoff_dt,
    desired_arrival_dt,
    home: str = "TBD",
    away: str = "TBD",
) -> dict:
    """
    Find the optimal departure time for a given game and desired arrival.

    Sweeps departure times from 5h before kickoff to kickoff, computing
    expected travel time at each point, and returns the latest departure
    that still gets you there by desired_arrival_dt.

    Parameters
    ----------
    baseline_minutes : float
        Normal (no-event) travel time in minutes from origin to venue
    kickoff_dt : datetime
        Kickoff datetime in local venue time
    desired_arrival_dt : datetime
        When the user wants to arrive (local venue time)

    Returns
    -------
    dict with keys:
        departure_time, expected_travel_minutes, multiplier_at_departure,
        normal_travel_minutes, extra_minutes, severity, curve_data
    """
    from datetime import timedelta

    curve = get_multiplier_curve(
        venue_id=venue_id,
        stage_importance=stage_importance,
        expected_capacity_pct=expected_capacity_pct,
        stage=stage,
        kickoff_hour=kickoff_dt.hour,
        home=home,
        away=away,
    )

    # Sweep departure times from T-5h to T+0h in 5-minute increments
    sweep_offsets_h = np.arange(-5.0, 0.05, 5 / 60)  # every 5 min
    best_departure = None
    best_travel_min = None
    best_multiplier = None

    for offset_h in sweep_offsets_h:
        departure_dt = kickoff_dt + timedelta(hours=offset_h)
        mult = float(curve(offset_h))
        travel_min = baseline_minutes * mult
        arrival_dt = departure_dt + timedelta(minutes=travel_min)

        if arrival_dt <= desired_arrival_dt:
            # This departure time gets you there in time — keep the latest one
            best_departure = departure_dt
            best_travel_min = travel_min
            best_multiplier = mult

    # If no departure time works even at T-5h, use T-5h and warn
    if best_departure is None:
        offset_h = -5.0
        mult = float(curve(offset_h))
        best_departure = kickoff_dt + timedelta(hours=offset_h)
        best_travel_min = baseline_minutes * mult
        best_multiplier = mult

    extra_min = best_travel_min - baseline_minutes
    severity = _severity_label(best_multiplier)

    # Build full curve data for the chart (T-5h to T+4h in 15-min steps)
    chart_offsets = np.arange(-5.0, 4.1, 0.25)
    chart_times = [kickoff_dt + timedelta(hours=float(h)) for h in chart_offsets]
    chart_multipliers = [float(curve(h)) for h in chart_offsets]
    chart_travel_min = [baseline_minutes * m for m in chart_multipliers]

    return {
        "departure_time": best_departure,
        "expected_travel_minutes": round(best_travel_min),
        "multiplier_at_departure": round(best_multiplier, 2),
        "normal_travel_minutes": round(baseline_minutes),
        "extra_minutes": round(extra_min),
        "severity": severity,
        "peak_multiplier": get_peak_multiplier(
            venue_id, stage_importance, expected_capacity_pct, stage, home, away
        ),
        "chart": {
            "times": chart_times,
            "multipliers": chart_multipliers,
            "travel_minutes": chart_travel_min,
        },
    }


def _severity_label(multiplier: float) -> dict:
    """Map a multiplier to a human-readable severity label and emoji."""
    if multiplier < 1.3:
        return {"label": "Light", "emoji": "🟢", "color": "#2ecc71"}
    elif multiplier < 1.8:
        return {"label": "Moderate", "emoji": "🟡", "color": "#f39c12"}
    elif multiplier < 2.5:
        return {"label": "Heavy", "emoji": "🟠", "color": "#e67e22"}
    elif multiplier < 3.2:
        return {"label": "Severe", "emoji": "🔴", "color": "#e74c3c"}
    else:
        return {"label": "Extreme", "emoji": "🚨", "color": "#8e44ad"}


def get_curve_summary_for_display(
    venue_id: str,
    stage_importance: int,
    expected_capacity_pct: float,
    stage: str,
    kickoff_dt,
) -> List[dict]:
    """
    Return a list of {time, multiplier, travel_minutes} for display in a chart.
    Time offsets: every 15 minutes from T-5h to T+4h.
    """
    from datetime import timedelta

    curve = get_multiplier_curve(
        venue_id=venue_id,
        stage_importance=stage_importance,
        expected_capacity_pct=expected_capacity_pct,
        stage=stage,
        kickoff_hour=kickoff_dt.hour,
    )

    rows = []
    for offset_h in np.arange(-5.0, 4.1, 0.25):
        t = kickoff_dt + timedelta(hours=float(offset_h))
        m = float(curve(offset_h))
        rows.append({"time": t, "hours_from_kickoff": offset_h, "multiplier": m})

    return rows
