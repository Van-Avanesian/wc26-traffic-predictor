"""
Google Maps API utilities.

Handles:
  - Geocoding a user's address to (lat, lon)
  - Getting baseline travel time (normal day, no event)
  - Graceful fallback if no API key is configured

IMPORTANT: Set GOOGLE_MAPS_API_KEY in your .env file.
Get a key at https://console.cloud.google.com/
Enable: Directions API, Geocoding API
"""

import os
import math
from datetime import datetime, timedelta
from typing import Optional
import googlemaps
from dotenv import load_dotenv

load_dotenv()

_client = None


def _get_api_key() -> str:
    """
    Retrieve the Google Maps API key from environment or Streamlit secrets.

    Checks in order:
      1. GOOGLE_MAPS_API_KEY environment variable (local .env via python-dotenv)
      2. st.secrets["GOOGLE_MAPS_API_KEY"] (Streamlit Community Cloud deployment)
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key or api_key == "your_google_maps_api_key_here":
        try:
            import streamlit as st
            api_key = st.secrets.get("GOOGLE_MAPS_API_KEY", "")
        except Exception:
            pass
    return api_key


def _get_client():
    """Lazy-initialize the Google Maps client."""
    global _client
    if _client is None:
        api_key = _get_api_key()
        if not api_key or api_key == "your_google_maps_api_key_here":
            return None
        _client = googlemaps.Client(key=api_key)
    return _client


def geocode_address(address: str) -> Optional[dict]:
    """
    Convert a street address to coordinates.

    Returns dict with 'lat', 'lon', 'formatted_address', or None on failure.
    """
    client = _get_client()
    if client is None:
        return _estimate_coords_from_address(address)

    try:
        results = client.geocode(address)
        if not results:
            return None
        loc = results[0]["geometry"]["location"]
        return {
            "lat": loc["lat"],
            "lon": loc["lng"],
            "formatted_address": results[0]["formatted_address"],
        }
    except Exception:
        return None


def get_baseline_travel_time(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    reference_dt: Optional[datetime] = None,
    city_traffic_factor: float = 1.0,
) -> Optional[float]:
    """
    Get baseline (normal day, no event) driving travel time in minutes.

    If reference_dt is provided, the baseline uses the same day-of-week and
    hour as the actual departure window (e.g. Saturday at 4pm) — but on a
    non-event week 3 weeks out. This gives a true apples-to-apples comparison:
    "how long does this drive normally take at this time on this day?"

    Without reference_dt, falls back to next Tuesday at 10am — the lightest
    representative traffic for most US metros, but less accurate for evening
    or weekend games.

    Returns minutes as float, or None if the API call fails.
    Falls back to straight-line distance estimate if no API key.
    """
    client = _get_client()
    if client is None:
        # No API key — use haversine estimate as free-flow, then apply factors
        free_flow_min = _estimate_drive_time(origin_lat, origin_lon, dest_lat, dest_lon)
        if reference_dt is not None:
            approx_departure = reference_dt - timedelta(hours=1)
            dt_naive = approx_departure.replace(tzinfo=None) if approx_departure.tzinfo else approx_departure
            factor = _time_of_day_factor(dt_naive.weekday(), dt_naive.hour)
        else:
            factor = _time_of_day_factor(1, 10)
        return round(free_flow_min * factor * city_traffic_factor, 1)

    # ── Step 1: free-flow time from Google Maps ────────────────────────────
    # No departure_time or traffic_model — the plain `duration` field is
    # pure route distance ÷ road speed. Clean free-flow, no guessing.
    try:
        result = client.directions(
            origin=(origin_lat, origin_lon),
            destination=(dest_lat, dest_lon),
            mode="driving",
        )
        if not result:
            free_flow_min = _estimate_drive_time(origin_lat, origin_lon, dest_lat, dest_lon)
        else:
            leg = result[0]["legs"][0]
            free_flow_min = leg["duration"]["value"] / 60.0
    except Exception:
        free_flow_min = _estimate_drive_time(origin_lat, origin_lon, dest_lat, dest_lon)

    # ── Step 2: apply day-of-week × time-of-day congestion factor ──────────
    if reference_dt is not None:
        # Approximate departure = desired arrival minus 1 hour.
        # This gets us into the right traffic window without a circular lookup.
        approx_departure = reference_dt - timedelta(hours=1)
        # Strip timezone if present — we just need weekday and hour
        dt_naive = approx_departure.replace(tzinfo=None) if approx_departure.tzinfo else approx_departure
        factor = _time_of_day_factor(dt_naive.weekday(), dt_naive.hour)
    else:
        # No time context: use Tuesday 10am (lightest traffic)
        factor = _time_of_day_factor(1, 10)

    return round(free_flow_min * factor * city_traffic_factor, 1)


# ---------------------------------------------------------------------------
# Day-of-week × time-of-day traffic factors
# ---------------------------------------------------------------------------

def _time_of_day_factor(weekday: int, hour: int) -> float:
    """
    Multiplier over free-flow drive time for a NEUTRAL mid-sized US city.

    City-specific congestion is layered on separately via city_traffic_factor
    (see data/venues.py), so these base factors are intentionally modest:
      - Tuesday 10am is the lightest (~1.04×)
      - Friday 5pm is the heaviest (1.28 × 1.15 Friday bump ≈ 1.47×)
      - Weekends are lighter than weekday PM rush but not free-flow

    weekday : 0=Monday … 6=Sunday
    hour    : 0–23 local time
    """
    is_friday  = (weekday == 4)
    is_weekend = (weekday >= 5)

    if is_weekend:
        if   hour <  7: return 1.00   # overnight
        elif hour < 10: return 1.02   # weekend morning — light
        elif hour < 14: return 1.06   # midday activity
        elif hour < 18: return 1.09   # afternoon errands / events
        elif hour < 21: return 1.06   # weekend evening
        else:           return 1.02   # night

    # ── Weekday base (Mon–Thu; Friday overrides PM below) ──────────────────
    # These factors represent a neutral mid-sized US city (Kansas City level).
    # City-specific congestion is captured by city_traffic_factor in venues.py,
    # which is applied multiplicatively on top. Keeping the base factors modest
    # prevents double-counting — suburban routes (e.g. Dallas → Arlington) stay
    # close to free-flow while high city_factor venues (e.g. SoFi/LA) scale up.
    if   hour <  6: base = 1.00   # overnight
    elif hour <  7: base = 1.03   # pre-rush
    elif hour <  8: base = 1.20   # AM rush building
    elif hour <  9: base = 1.42   # peak AM rush
    elif hour < 10: base = 1.22   # post AM rush taper
    elif hour < 14: base = 1.04   # midday — near free-flow for most cities
    elif hour < 15: base = 1.06   # early afternoon
    elif hour < 16: base = 1.08   # pre-PM rush
    elif hour < 17: base = 1.12   # PM rush building
    elif hour < 18: base = 1.28   # peak PM rush
    elif hour < 19: base = 1.18   # evening taper
    elif hour < 20: base = 1.10
    elif hour < 21: base = 1.06
    elif hour < 22: base = 1.03
    else:           base = 1.01   # night

    # Friday afternoon is the worst commute of the week
    if is_friday and 14 <= hour <= 19:
        base *= 1.15

    return base


# ---------------------------------------------------------------------------
# Fallback estimators (used when no API key is configured)
# ---------------------------------------------------------------------------

def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Straight-line distance in km between two lat/lon points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _estimate_drive_time(lat1, lon1, lat2, lon2) -> float:
    """
    Rough driving time estimate from straight-line distance.

    Assumes average driving speed of 50 km/h (accounts for stops,
    turns, and urban road network factor of ~1.4× straight line).
    """
    dist_km = _haversine_km(lat1, lon1, lat2, lon2)
    road_dist_km = dist_km * 1.4   # road network is ~40% longer than straight line
    avg_speed_kmh = 50.0
    return (road_dist_km / avg_speed_kmh) * 60.0   # convert to minutes


def _estimate_coords_from_address(address: str) -> Optional[dict]:
    """
    Very rough fallback: can't geocode without API key.
    Returns None — the app will prompt the user to add a key or enter coords.
    """
    return None


def is_api_configured() -> bool:
    """Check whether a valid Google Maps API key is present."""
    key = _get_api_key()
    return bool(key) and key != "your_google_maps_api_key_here"
