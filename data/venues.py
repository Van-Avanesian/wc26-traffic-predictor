"""
WC 2026 venue data — coordinates, capacity, and traffic characteristics.

The data itself lives in ``venues.json`` (loaded below). This module exposes it
as the ``VENUES`` dict, keyed by venue id. Field meanings:

  transit_score: 0–1. How transit-accessible the venue is. High (0.7+) means a
    real share of fans arrive by rail, so car traffic is partly absorbed →
    slightly lower road multiplier. Low (<0.4) is car-dependent → higher.

  parking_factor: 0–1. Relative ease of parking. High = big on-site lots,
    traffic disperses faster post-game. Low = limited parking, longer tail.

  wc_premium: extra multiplier on top of the base curves, because WC crowds are
    more international (less transit-savvy), have larger fan zones, and sit
    inside bigger security perimeters.

  city_traffic_factor: metro-level congestion multiplier applied to the normal
    baseline drive. This carries the city-to-city variation in the model.
    Range 1.05 (Arrowhead/KC — suburban, mild) to 1.55 (SoFi/LA — the I-405
    near Inglewood is among the most congested segments in the country).
    Other anchors: MetLife/NJ 1.38 (Turnpike approach), Mercedes-Benz/ATL 1.28
    (Spaghetti Junction), Hard Rock/Miami 1.18, AT&T/Arlington 1.06 (suburban).
"""

import json
from pathlib import Path

_DATA_PATH = Path(__file__).with_name("venues.json")

with open(_DATA_PATH, encoding="utf-8") as _f:
    VENUES = json.load(_f)
