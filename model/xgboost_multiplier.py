"""
XGBoost-based traffic multiplier for WC 2026.

Learns venue × event-type × attendance interactions from 53 reference events
(Copa América, CWC, NFL playoffs, concerts, Super Bowl) then applies WC-specific
stage and team factors to extrapolate beyond the training distribution.

Architecture
------------
  1. XGBRegressor trained on reference events
       → captures venue characteristics and event-type baseline multipliers
         from real observed congestion data
  2. WC stage factor
       → scales the Copa-América-level prediction up to WC importance level
         (group stage = +22%, Final = +88% above Copa América equivalent)
  3. Team demand multiplier
       → adjusts for matchup appeal based on FIFA rankings + host nation bonus
         (USA games get the largest boost; weak matchups get a slight reduction)

Why XGBoost over a simple lookup table?
  - The hand-tuned model uses fixed STAGE_BASE_MULTIPLIERS that ignore interactions
    between venue, attendance, and event type.
  - XGBoost learns, for example, that a sold-out concert at car-dependent AT&T
    causes disproportionate congestion vs the same event at transit-friendly Lumen Field.
  - Cross-validated MAE gives an honest estimate of prediction uncertainty.
"""

import numpy as np
import pandas as pd
from datetime import timedelta
from xgboost import XGBRegressor
from sklearn.model_selection import KFold, cross_val_score

from data.venues import VENUES
from data.reference_events import REFERENCE_EVENTS
from data.teams import get_team_demand_multiplier
from model.multiplier import _build_curve, _severity_label


# ---------------------------------------------------------------------------
# Event type ordinal encoding
# Ordered by expected traffic impact: higher score = more intense event.
# ---------------------------------------------------------------------------
EVENT_TYPE_SCORE: dict = {
    "soccer_mid":   0,   # CWC group stage with low attendance
    "concert":      1,   # Wide arrival window → lower peak, wider curve
    "boxing":       2,   # Sharp arrival, moderate peak
    "nfl_regular":  2,   # NFL regular season sellout
    "college_fb":   3,   # College football championship games
    "nfl_playoff":  4,   # NFL playoff / conference championship
    "soccer_mega":  5,   # Copa América / CWC — high-stakes soccer, best reference for WC
    "super_bowl":   6,   # Super Bowl — WC Final analog (highest training data point)
}

# ---------------------------------------------------------------------------
# WC 2026 stage scaling factors
# Applied on top of the XGBoost base prediction (which is Copa-América-calibrated).
# Extrapolates from the observed Copa/CWC range to WC 2026's larger scale.
#
# Calibration rationale:
#   Copa América group stage (soccer_mega, ~97% att.) → model predicts ~2.7–3.4
#   WC group stage should be ~22% above that → factor 1.22
#   WC Final should be ~88% above Copa América Final → factor 1.88
# ---------------------------------------------------------------------------
WC_STAGE_FACTOR: dict = {
    1: 1.22,   # Group Stage
    2: 1.32,   # Round of 32
    3: 1.43,   # Round of 16
    4: 1.56,   # Quarter-Final
    5: 1.70,   # Semi-Final
    6: 1.88,   # Final / Third Place (3rd place gets THIRD_PLACE_DISCOUNT below)
}

THIRD_PLACE_DISCOUNT = 0.85

# WC games are treated as "soccer_mega" (Copa América equivalent) by the model.
# WC premium is captured by WC_STAGE_FACTOR, not by inflating event_type_score.
WC_EVENT_TYPE_SCORE: int = EVENT_TYPE_SCORE["soccer_mega"]   # = 5


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

_FEATURE_COLS = [
    "event_type_score",
    "attendance_pct",
    "is_sold_out",
    "transit_score",
    "parking_factor",
    "city_traffic_factor",
    "capacity_norm",
    "kickoff_hour",
    "is_evening",
]


def _build_feature_df(events: list, venues: dict) -> pd.DataFrame:
    """
    Engineer features from reference events + venue data.

    Returns a DataFrame with one row per reference event.

    Feature descriptions
    --------------------
    event_type_score   : Ordinal encoding of event intensity (0 = low, 6 = Super Bowl)
    attendance_pct     : Fraction of capacity filled (capped at 1.05 for oversold events)
    is_sold_out        : Binary flag — sold-out events cause disproportionate fan clustering
    transit_score      : How transit-accessible the venue is (0–1); higher → fewer cars
    parking_factor     : Relative ease of parking (0–1); higher → traffic disperses faster
    city_traffic_factor: Metro-level congestion multiplier (1.05 = KC, 1.22 = LA/SoFi)
    capacity_norm      : Venue capacity relative to MetLife (82,500); larger venues draw more cars
    kickoff_hour       : Local hour of kickoff (0–23); afternoon/evening = peak traffic overlap
    is_evening         : 1 if kickoff >= 18:00; evening events compound rush-hour congestion
    """
    rows = []
    for ev in events:
        venue = venues[ev["venue_id"]]
        kickoff_hour = int(ev["kickoff_local"].split(":")[0])

        rows.append({
            "event_type_score":    EVENT_TYPE_SCORE.get(ev["event_type"], 3),
            "attendance_pct":      min(ev["attendance_pct"], 1.05),
            "is_sold_out":         int(ev["is_sold_out"]),
            "transit_score":       venue["transit_score"],
            "parking_factor":      venue["parking_factor"],
            "city_traffic_factor": venue["city_traffic_factor"],
            "capacity_norm":       venue["capacity"] / 82500,
            "kickoff_hour":        kickoff_hour,
            "is_evening":          int(kickoff_hour >= 18),
        })

    return pd.DataFrame(rows, columns=_FEATURE_COLS)


def _build_targets(events: list) -> np.ndarray:
    return np.array([ev["peak_multiplier_estimate"] for ev in events])


# ---------------------------------------------------------------------------
# Model training
# ---------------------------------------------------------------------------

def train_model(events=None, venues=None):
    """
    Train XGBoost regressor on reference events. Returns (model, cv_mae, feature_names).

    Hyperparameter choices
    ----------------------
    max_depth=3        : Shallow trees prevent overfitting on 53 training samples
    n_estimators=200   : Enough rounds for the low learning rate to converge
    learning_rate=0.04 : Slow learning + more rounds → better generalization
    subsample=0.80     : Row sampling adds stochasticity, reduces variance
    colsample_bytree=0.80 : Feature sampling per tree
    reg_alpha=0.20     : L1 regularization → pushes low-importance features toward zero
    reg_lambda=1.50    : L2 regularization → standard ridge penalty
    min_child_weight=3 : Require ≥3 samples per leaf → prevents overfitting on outliers

    Evaluation
    ----------
    5-fold CV is used for honest performance estimation. The final model is
    then re-fitted on the full 53-sample dataset for production use.

    Returns
    -------
    model         : XGBRegressor  fitted on all reference events
    cv_mae        : float          5-fold CV mean absolute error (in multiplier units)
    feature_names : list[str]      column names (for feature importance display)
    """
    if events is None:
        events = REFERENCE_EVENTS
    if venues is None:
        venues = VENUES

    X = _build_feature_df(events, venues)
    y = _build_targets(events)
    feature_names = list(X.columns)

    model = XGBRegressor(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.04,
        subsample=0.80,
        colsample_bytree=0.80,
        reg_alpha=0.20,
        reg_lambda=1.50,
        min_child_weight=3,
        random_state=42,
        verbosity=0,
    )

    # 5-fold cross-validation
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(
        model, X, y,
        cv=kf,
        scoring="neg_mean_absolute_error",
    )
    cv_mae = round(float(-cv_scores.mean()), 3)

    # Fit on full dataset for production use
    model.fit(X, y)

    return model, cv_mae, feature_names


# ---------------------------------------------------------------------------
# WC game feature vector
# ---------------------------------------------------------------------------

def _wc_feature_vector(
    venue_id: str,
    attendance_pct: float,
    kickoff_hour: int,
    venues: dict = None,
) -> pd.DataFrame:
    """Build a single-row feature DataFrame for predicting a WC game."""
    if venues is None:
        venues = VENUES
    venue = venues[venue_id]

    return pd.DataFrame([{
        "event_type_score":    WC_EVENT_TYPE_SCORE,
        "attendance_pct":      min(attendance_pct, 1.05),
        "is_sold_out":         int(attendance_pct >= 0.98),
        "transit_score":       venue["transit_score"],
        "parking_factor":      venue["parking_factor"],
        "city_traffic_factor": venue["city_traffic_factor"],
        "capacity_norm":       venue["capacity"] / 82500,
        "kickoff_hour":        kickoff_hour,
        "is_evening":          int(kickoff_hour >= 18),
    }], columns=_FEATURE_COLS)


# ---------------------------------------------------------------------------
# Peak multiplier prediction
# ---------------------------------------------------------------------------

def get_peak_multiplier_xgb(
    model,
    venue_id: str,
    stage_importance: int,
    expected_capacity_pct: float,
    stage: str = "",
    kickoff_hour: int = 18,
    home: str = "TBD",
    away: str = "TBD",
) -> float:
    """
    Predict peak traffic multiplier for a WC 2026 game.

    Prediction pipeline
    -------------------
    1. Build feature vector as if this were a Copa América (soccer_mega) event
       at the same venue, attendance %, and kickoff hour.
    2. XGBoost predicts the Copa-level base multiplier.
    3. Multiply by WC_STAGE_FACTOR[stage_importance] to scale up to WC demand.
    4. Apply third-place discount if applicable.
    5. Multiply by team demand multiplier (FIFA rankings + host nation bonus).

    Parameters
    ----------
    model               : XGBRegressor from train_model()
    venue_id            : Key from data/venues.VENUES
    stage_importance    : 1 (Group Stage) → 6 (Final)
    expected_capacity_pct : Expected fraction of capacity filled
    stage               : Stage name string (detects "third" for discount)
    kickoff_hour        : Local hour of kickoff
    home, away          : Team names for demand multiplier

    Returns
    -------
    float  Peak traffic multiplier at the worst-case departure time
    """
    X = _wc_feature_vector(venue_id, expected_capacity_pct, kickoff_hour)
    xgb_base = float(model.predict(X)[0])

    stage_factor = WC_STAGE_FACTOR.get(stage_importance, 1.22)
    peak = xgb_base * stage_factor

    if "third" in stage.lower() or "3rd" in stage.lower():
        peak *= THIRD_PLACE_DISCOUNT

    peak *= get_team_demand_multiplier(home, away)

    return round(peak, 3)


# ---------------------------------------------------------------------------
# Feature importances
# ---------------------------------------------------------------------------

def get_feature_importances(model, feature_names: list) -> dict:
    """
    Return feature importances sorted by descending importance.

    Returns
    -------
    dict {feature_name: importance_score}  (sum ≈ 1.0)
    """
    importances = model.feature_importances_
    result = {
        name: round(float(imp), 4)
        for name, imp in zip(feature_names, importances)
    }
    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))


# ---------------------------------------------------------------------------
# Departure time finder (XGBoost version)
# Drop-in replacement for model.multiplier.find_departure_time
# ---------------------------------------------------------------------------

def find_departure_time_xgb(
    model,
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
    Find the optimal departure time using the XGBoost-predicted peak multiplier.

    Identical interface to model.multiplier.find_departure_time — drop-in
    replacement. The Gaussian curve shape (sigma, offsets) is the same as the
    hand-tuned model; only the peak amplitude changes (driven by XGBoost).

    Sweeps departure times from T-5h to T+0h in 5-minute steps, computing
    expected travel time at each, and returns the latest departure that still
    gets the user to the stadium by desired_arrival_dt.

    Parameters
    ----------
    model               : XGBRegressor from train_model()
    baseline_minutes    : Normal (no-event) travel time in minutes
    venue_id            : Key from data/venues.VENUES
    stage_importance    : 1 → 6
    expected_capacity_pct : Expected fraction of seats filled
    stage               : Stage name string
    kickoff_dt          : Kickoff datetime (timezone-aware, local venue time)
    desired_arrival_dt  : When the user wants to arrive

    Returns
    -------
    dict with keys:
        departure_time, expected_travel_minutes, multiplier_at_departure,
        normal_travel_minutes, extra_minutes, severity, peak_multiplier, chart
    """
    peak = get_peak_multiplier_xgb(
        model=model,
        venue_id=venue_id,
        stage_importance=stage_importance,
        expected_capacity_pct=expected_capacity_pct,
        stage=stage,
        kickoff_hour=kickoff_dt.hour,
        home=home,
        away=away,
    )

    # Sigma (Gaussian spread) by kickoff hour — same logic as hand-tuned model
    if kickoff_dt.hour < 14:
        pre_sigma = 1.4
        pre_peak_offset = -1.0
    elif kickoff_dt.hour < 17:
        pre_sigma = 1.6
        pre_peak_offset = -1.2
    else:
        pre_sigma = 1.9       # Evening games: gradual buildup all afternoon
        pre_peak_offset = -1.2

    curve = _build_curve(
        peak_multiplier=peak,
        pre_peak_offset=pre_peak_offset,
        pre_sigma=pre_sigma,
    )

    # Sweep departure times T-5h → T+0h in 5-minute steps
    sweep_offsets_h = np.arange(-5.0, 0.05, 5 / 60)
    best_departure  = None
    best_travel_min = None
    best_multiplier = None

    for offset_h in sweep_offsets_h:
        departure_dt = kickoff_dt + timedelta(hours=float(offset_h))
        mult         = float(curve(offset_h))
        travel_min   = baseline_minutes * mult
        arrival_dt   = departure_dt + timedelta(minutes=travel_min)

        if arrival_dt <= desired_arrival_dt:
            best_departure  = departure_dt
            best_travel_min = travel_min
            best_multiplier = mult

    # Fallback: if no window works, use T-5h
    if best_departure is None:
        offset_h        = -5.0
        mult            = float(curve(offset_h))
        best_departure  = kickoff_dt + timedelta(hours=offset_h)
        best_travel_min = baseline_minutes * mult
        best_multiplier = mult

    extra_min = best_travel_min - baseline_minutes
    severity  = _severity_label(best_multiplier)

    # Full chart data (T-5h → T+4h in 15-min steps)
    chart_offsets    = np.arange(-5.0, 4.1, 0.25)
    chart_times      = [kickoff_dt + timedelta(hours=float(h)) for h in chart_offsets]
    chart_multipliers = [float(curve(h)) for h in chart_offsets]
    chart_travel_min  = [baseline_minutes * m for m in chart_multipliers]

    return {
        "departure_time":          best_departure,
        "expected_travel_minutes": round(best_travel_min),
        "multiplier_at_departure": round(best_multiplier, 2),
        "normal_travel_minutes":   round(baseline_minutes),
        "extra_minutes":           round(extra_min),
        "severity":                severity,
        "peak_multiplier":         peak,
        "chart": {
            "times":          chart_times,
            "multipliers":    chart_multipliers,
            "travel_minutes": chart_travel_min,
        },
    }
