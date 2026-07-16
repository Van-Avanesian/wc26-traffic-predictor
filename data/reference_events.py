"""
Reference events used to calibrate / train the traffic models.

The event records live in ``reference_events.json``; this module loads them as
``REFERENCE_EVENTS`` and provides helpers to slice/summarize them.

These are real sold-out (or near-sold-out) events at WC 2026 venues from the
past ~5 years. They anchor the models to observed traffic patterns rather than
pure theory.

event_type categories:
  soccer_mega  Copa América / CWC match, high stakes
  soccer_mid   CWC group stage, lower demand
  nfl_playoff  NFL playoff game
  nfl_regular  NFL regular-season sellout
  concert      Sold-out concert (wider arrival curve)
  super_bowl   Super Bowl (closest analog to a WC final)
  boxing       Major boxing event
  college_fb   College football major bowl

Key fields per event:
  peak_multiplier_estimate  best estimate of peak traffic multiplier
                            (event-day travel time ÷ normal-day travel time)
  sigma_h                   spread of the traffic curve in hours (soccer ~1h,
                            concerts ~1.5h because fans arrive over a longer window)
  attendance_pct, is_sold_out, kickoff_local ("HH:MM"), date ("YYYY-MM-DD"), notes
"""

import json
from pathlib import Path

_DATA_PATH = Path(__file__).with_name("reference_events.json")

with open(_DATA_PATH, encoding="utf-8") as _f:
    REFERENCE_EVENTS = json.load(_f)


def get_events_for_venue(venue_id: str) -> list:
    """Return all reference events for a given venue."""
    return [e for e in REFERENCE_EVENTS if e["venue_id"] == venue_id]


def get_venue_calibration(venue_id: str) -> dict:
    """
    Summarize reference-event data for a venue into calibration parameters.
    Returns the average peak multiplier by event type.
    """
    events = get_events_for_venue(venue_id)
    by_type = {}
    for e in events:
        by_type.setdefault(e["event_type"], []).append(e["peak_multiplier_estimate"])

    return {t: sum(v) / len(v) for t, v in by_type.items()}
