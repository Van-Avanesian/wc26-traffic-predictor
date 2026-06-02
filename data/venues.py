"""
WC 2026 venue data — coordinates, capacity, and traffic characteristics.

transit_score: 0–1 scale. How transit-accessible the venue is.
  - High (0.7+): significant portion of fans arrive via public transit,
    so car traffic is partially absorbed → slightly lower road multiplier.
  - Low (<0.4): highly car-dependent → higher road multiplier.

parking_factor: 0–1 scale. Relative ease of parking near venue.
  - High: large on-site lots, traffic disperses faster post-game.
  - Low: limited parking, fans circle longer → longer post-game tail.

wc_premium: additional multiplier applied on top of base curves
  because WC fans are more international (less transit-savvy),
  there are more fan zones, and security perimeters are larger.

city_traffic_factor: multiplier reflecting how much worse congestion gets
  in this metro relative to a typical US city at the same time of day.
  1.0 = baseline (Kansas City). 1.40 = LA (405 near SoFi is among the
  most congested highway segments in the country).
  Applied to the normal baseline drive, independent of the WC event.
"""

VENUES = {
    "metlife": {
        "name": "MetLife Stadium",
        "city": "East Rutherford, NJ",
        "display": "MetLife Stadium — East Rutherford, NJ",
        "lat": 40.8135,
        "lon": -74.0745,
        "capacity": 82500,
        "timezone": "America/New_York",
        "transit_score": 0.65,       # NJ Transit game-day trains run directly
        "parking_factor": 0.55,      # Massive lots but they bottleneck on exit
        "wc_premium": 1.20,          # Hosting the Final + biggest NYC metro
        "city_traffic_factor": 1.18, # NJ Turnpike / Route 3 approach is punishing; NYC metro density
    },
    "hard_rock": {
        "name": "Hard Rock Stadium",
        "city": "Miami Gardens, FL",
        "display": "Hard Rock Stadium — Miami Gardens, FL",
        "lat": 25.9580,
        "lon": -80.2389,
        "capacity": 65326,
        "timezone": "America/New_York",
        "transit_score": 0.25,       # Very car-dependent, limited transit
        "parking_factor": 0.60,
        "wc_premium": 1.15,
        "city_traffic_factor": 1.14, # I-95 and US-1 corridor notoriously congested
    },
    "mercedes_benz": {
        "name": "Mercedes-Benz Stadium",
        "city": "Atlanta, GA",
        "display": "Mercedes-Benz Stadium — Atlanta, GA",
        "lat": 33.7554,
        "lon": -84.4010,
        "capacity": 71000,
        "timezone": "America/New_York",
        "transit_score": 0.60,       # MARTA rail direct to stadium
        "parking_factor": 0.45,      # Downtown Atlanta parking is tight
        "wc_premium": 1.12,
        "city_traffic_factor": 1.16, # Consistently top 3 worst in US; Spaghetti Junction, I-285
    },
    "lincoln_financial": {
        "name": "Lincoln Financial Field",
        "city": "Philadelphia, PA",
        "display": "Lincoln Financial Field — Philadelphia, PA",
        "lat": 39.9008,
        "lon": -75.1675,
        "capacity": 69796,
        "timezone": "America/New_York",
        "transit_score": 0.55,       # SEPTA Broad Street Line to stadium
        "parking_factor": 0.50,
        "wc_premium": 1.12,
        "city_traffic_factor": 1.12, # Significant but not extreme vs. NYC/LA/ATL
    },
    "lumen_field": {
        "name": "Lumen Field",
        "city": "Seattle, WA",
        "display": "Lumen Field — Seattle, WA",
        "lat": 47.5952,
        "lon": -122.3316,
        "capacity": 68740,
        "timezone": "America/Los_Angeles",
        "transit_score": 0.70,       # Link Light Rail nearby, very transit-friendly city
        "parking_factor": 0.40,      # Limited downtown parking
        "wc_premium": 1.10,
        "city_traffic_factor": 1.14, # Geographic bottlenecks (water), I-5 downtown brutal
    },
    "att": {
        "name": "AT&T Stadium",
        "city": "Arlington, TX",
        "display": "AT&T Stadium — Arlington (Dallas), TX",
        "lat": 32.7473,
        "lon": -97.0945,
        "capacity": 80000,
        "timezone": "America/Chicago",
        "transit_score": 0.10,       # No meaningful transit, fully car-dependent
        "parking_factor": 0.70,      # Massive parking inventory around stadium
        "wc_premium": 1.15,
        "city_traffic_factor": 1.13, # Heavy DFW sprawl; I-20/I-30/I-35 corridors
    },
    "nrg": {
        "name": "NRG Stadium",
        "city": "Houston, TX",
        "display": "NRG Stadium — Houston, TX",
        "lat": 29.6847,
        "lon": -95.4107,
        "capacity": 72220,
        "timezone": "America/Chicago",
        "transit_score": 0.30,       # METRORail Red Line nearby
        "parking_factor": 0.65,
        "wc_premium": 1.15,
        "city_traffic_factor": 1.08, # Everyone drives but highway network is massive
    },
    "arrowhead": {
        "name": "Arrowhead Stadium",
        "city": "Kansas City, MO",
        "display": "Arrowhead Stadium — Kansas City, MO",
        "lat": 39.0489,
        "lon": -94.4839,
        "capacity": 76416,
        "timezone": "America/Chicago",
        "transit_score": 0.15,       # Very car-dependent
        "parking_factor": 0.65,
        "wc_premium": 1.12,
        "city_traffic_factor": 1.05, # Minimum — smaller metro, manageable congestion
    },
    "sofi": {
        "name": "SoFi Stadium",
        "city": "Inglewood, CA",
        "display": "SoFi Stadium — Inglewood (Los Angeles), CA",
        "lat": 33.9535,
        "lon": -118.3392,
        "capacity": 70240,
        "timezone": "America/Los_Angeles",
        "transit_score": 0.45,       # Metro K Line nearby but LA is car-heavy
        "parking_factor": 0.55,
        "wc_premium": 1.18,          # LA traffic already notorious + WC premium
        "city_traffic_factor": 1.22, # 405 near Inglewood = one of the most congested segments in the US
    },
    "levis": {
        "name": "Levi's Stadium",
        "city": "Santa Clara, CA",
        "display": "Levi's Stadium — Santa Clara (San Francisco), CA",
        "lat": 37.4033,
        "lon": -121.9694,
        "capacity": 68500,
        "timezone": "America/Los_Angeles",
        "transit_score": 0.50,       # VTA light rail + Caltrain nearby
        "parking_factor": 0.55,
        "wc_premium": 1.12,
        "city_traffic_factor": 1.15, # 101 and 880 Silicon Valley corridor severely congested
    },
    "gillette": {
        "name": "Gillette Stadium",
        "city": "Foxborough, MA",
        "display": "Gillette Stadium — Foxborough (Boston), MA",
        "lat": 42.0909,
        "lon": -71.2643,
        "capacity": 65878,
        "timezone": "America/New_York",
        "transit_score": 0.35,       # Commuter rail runs on event days only
        "parking_factor": 0.60,
        "wc_premium": 1.15,
        "city_traffic_factor": 1.06, # Foxborough is suburban; Route 1 only bad on event days
    },
}
