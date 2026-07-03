"""
WC 2026 Traffic Predictor
─────────────────────────
Enter your address + which World Cup game you're attending,
and we'll tell you exactly when to leave to make it on time.

Built with Streamlit. Powered by:
  - Google Maps API (baseline travel time + geocoding)
  - Two interchangeable traffic models you can switch between:

    1. Hand-tuned Gaussian model — calibrated against Copa América 2024,
       Club World Cup 2025, NFL playoffs, and major concerts at each venue.
       Uses a lookup table of stage-importance multipliers shaped by venue
       characteristics (transit score, parking, WC premium, city factor).

    2. XGBoost ML model — trains on the same 53 reference events and learns
       venue × event-type × attendance interactions via gradient boosting.
       5-fold cross-validated MAE ≈ ±0.14 multiplier units.

Run with:  streamlit run app.py
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import pytz
from datetime import datetime, date, time, timedelta

from data.venues import VENUES
from data.schedule import WC_SCHEDULE, get_game_label
from model.multiplier import find_departure_time, get_peak_multiplier
from model.xgboost_multiplier import (
    load_or_train,
    find_departure_time_xgb,
)
from utils.maps import (
    geocode_address,
    get_baseline_travel_time,
    is_api_configured,
)

# ─── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="WC 2026 Traffic Predictor",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-metric {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        border: 1px solid #0f3460;
    }
    .main-metric .label {
        color: #a0aec0;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    .main-metric .value {
        color: #ffffff;
        font-size: 42px;
        font-weight: 700;
        line-height: 1;
    }
    .main-metric .sub {
        color: #718096;
        font-size: 13px;
        margin-top: 6px;
    }
    .severity-box {
        border-radius: 10px;
        padding: 16px 20px;
        text-align: center;
        font-size: 18px;
        font-weight: 600;
        margin-top: 8px;
    }
    .info-box {
        background: #1e293b;
        border-left: 4px solid #3b82f6;
        border-radius: 6px;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 13px;
        color: #94a3b8;
    }
    .api-warning {
        background: #2d1b00;
        border-left: 4px solid #f59e0b;
        border-radius: 6px;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 13px;
        color: #fcd34d;
    }
    .model-info-box {
        background: #1a1040;
        border-left: 4px solid #8b5cf6;
        border-radius: 6px;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 13px;
        color: #c4b5fd;
    }
    .model-badge-ht {
        background: #1e3a5f;
        color: #60a5fa;
        border-radius: 6px;
        padding: 3px 10px;
        font-size: 12px;
        font-weight: 600;
    }
    .model-badge-ml {
        background: #2d1b5e;
        color: #c4b5fd;
        border-radius: 6px;
        padding: 3px 10px;
        font-size: 12px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ─── XGBoost model loading (lazy + from disk) ────────────────────────────────

@st.cache_resource(show_spinner="🤖 Loading XGBoost model…")
def load_xgb_model():
    """
    Load the pre-trained XGBoost model artifact from disk.

    The model is trained once offline (see model/xgb_model.json) and committed,
    so this is a fast file read — not a retrain. If the artifact is somehow
    missing, load_or_train() falls back to training on the fly.

    This is called LAZILY — only when the user actually selects the XGBoost
    model — so the landing page and the hand-tuned model load instantly on a
    cold start instead of waiting for any model work.
    """
    return load_or_train()


# ─── Helper functions ────────────────────────────────────────────────────────

def format_minutes(minutes: float) -> str:
    """Format minutes into human-readable string like '1h 23m' or '45 min'."""
    minutes = int(round(minutes))
    if minutes < 60:
        return f"{minutes} min"
    h, m = divmod(minutes, 60)
    return f"{h}h {m}m" if m else f"{h}h"


def format_time(dt: datetime) -> str:
    """Format datetime as '6:45 PM'."""
    return dt.strftime("%-I:%M %p")


def localize_kickoff(game: dict) -> datetime:
    """Combine the game date and kickoff_local time into a timezone-aware datetime."""
    venue = VENUES[game["venue_id"]]
    tz = pytz.timezone(venue["timezone"])
    naive = datetime.combine(game["date"], game["kickoff_local"])
    return tz.localize(naive)


def build_chart(result: dict, kickoff_dt: datetime, baseline_min: float, use_xgb: bool = False) -> go.Figure:
    """Build the Plotly traffic multiplier + travel time chart."""
    chart = result["chart"]
    # Strip timezone info — Plotly on Python 3.9 can't handle tz-aware datetimes
    times = [t.strftime("%Y-%m-%d %H:%M:%S") for t in chart["times"]]
    multipliers = chart["multipliers"]
    travel_mins = chart["travel_minutes"]

    # Color gradient based on multiplier severity
    colors = []
    for m in multipliers:
        if m < 1.3:
            colors.append("#2ecc71")
        elif m < 1.8:
            colors.append("#f1c40f")
        elif m < 2.5:
            colors.append("#e67e22")
        elif m < 3.2:
            colors.append("#e74c3c")
        else:
            colors.append("#8e44ad")

    line_color   = "#8b5cf6" if use_xgb else "#3b82f6"
    fill_color   = "rgba(139, 92, 246, 0.08)" if use_xgb else "rgba(59, 130, 246, 0.08)"
    model_label  = "🤖 XGBoost Model" if use_xgb else "📐 Hand-tuned Model"

    fig = go.Figure()

    # Travel time area chart
    fig.add_trace(go.Scatter(
        x=times,
        y=travel_mins,
        mode="lines",
        name="Expected travel time (min)",
        line=dict(color=line_color, width=2.5),
        fill="tozeroy",
        fillcolor=fill_color,
        hovertemplate="<b>%{x|%-I:%M %p}</b><br>Travel time: %{y:.0f} min<extra></extra>",
    ))

    # Baseline travel time reference line
    fig.add_hline(
        y=baseline_min,
        line_dash="dash",
        line_color="#64748b",
        line_width=1.5,
        annotation_text=f"Normal: {format_minutes(baseline_min)}",
        annotation_position="top left",
        annotation_font_color="#94a3b8",
        annotation_font_size=11,
    )

    # Kickoff vertical line — use add_shape instead of add_vline because
    # add_vline internally calls sum() on the x string and crashes on Python 3.9
    kickoff_str = kickoff_dt.strftime("%Y-%m-%d %H:%M:%S")
    fig.add_shape(
        type="line",
        x0=kickoff_str,
        x1=kickoff_str,
        y0=0,
        y1=1,
        yref="paper",
        line=dict(dash="dot", color="#f59e0b", width=2),
    )
    fig.add_annotation(
        x=kickoff_str,
        y=1,
        yref="paper",
        text="⚽ Kickoff",
        showarrow=False,
        xanchor="left",
        font=dict(color="#f59e0b", size=12),
    )

    # Recommended departure marker
    dep_time   = result["departure_time"]
    dep_travel = result["expected_travel_minutes"]
    fig.add_trace(go.Scatter(
        x=[dep_time.strftime("%Y-%m-%d %H:%M:%S")],
        y=[dep_travel],
        mode="markers",
        name="Recommended departure",
        marker=dict(
            color="#22c55e",
            size=14,
            symbol="circle",
            line=dict(color="white", width=2),
        ),
        hovertemplate=(
            f"<b>Recommended: {format_time(dep_time)}</b><br>"
            f"Travel time: {dep_travel:.0f} min<extra></extra>"
        ),
    ))

    fig.update_layout(
        title=dict(
            text=f"Expected Travel Time by Departure  "
                 f"<span style='font-size:13px; color:{'#8b5cf6' if use_xgb else '#3b82f6'}'>{model_label}</span>",
            font=dict(size=16, color="#e2e8f0"),
        ),
        xaxis=dict(
            title="Departure Time",
            tickformat="%-I %p",
            gridcolor="#1e293b",
            color="#94a3b8",
        ),
        yaxis=dict(
            title="Travel Time (minutes)",
            gridcolor="#1e293b",
            color="#94a3b8",
        ),
        plot_bgcolor="#0f172a",
        paper_bgcolor="#0f172a",
        font=dict(color="#e2e8f0"),
        legend=dict(
            bgcolor="#1e293b",
            bordercolor="#334155",
            borderwidth=1,
            font=dict(color="#94a3b8"),
        ),
        hovermode="x unified",
        margin=dict(l=20, r=20, t=50, b=20),
    )

    return fig


def build_importance_chart(importances: dict) -> go.Figure:
    """Horizontal bar chart of XGBoost feature importances."""
    labels = {
        "event_type_score":    "Event type score",
        "attendance_pct":      "Attendance %",
        "is_sold_out":         "Sold out",
        "transit_score":       "Transit access",
        "parking_factor":      "Parking ease",
        "city_traffic_factor": "City congestion",
        "capacity_norm":       "Venue capacity",
        "kickoff_hour":        "Kickoff hour",
        "is_evening":          "Evening kickoff",
    }

    names  = [labels.get(k, k) for k in importances]
    values = list(importances.values())

    fig = go.Figure(go.Bar(
        x=values,
        y=names,
        orientation="h",
        marker=dict(color=values, colorscale="Purp", showscale=False),
        text=[f"{v:.3f}" for v in values],
        textposition="outside",
        textfont=dict(color="#c4b5fd", size=10),
    ))

    fig.update_layout(
        title=dict(text="Feature Importances", font=dict(size=13, color="#e2e8f0")),
        xaxis=dict(
            title="Importance",
            gridcolor="#1e293b",
            color="#94a3b8",
            range=[0, max(values) * 1.30],
        ),
        yaxis=dict(color="#94a3b8", autorange="reversed"),
        plot_bgcolor="#0f172a",
        paper_bgcolor="#0f172a",
        font=dict(color="#e2e8f0"),
        margin=dict(l=10, r=50, t=40, b=10),
        height=300,
    )

    return fig


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/en/thumb/c/cf/2026_FIFA_World_Cup.svg/200px-2026_FIFA_World_Cup.svg.png",
        width=80,
    )
    st.title("WC 2026\nTraffic Predictor")
    st.markdown("---")

    # ── Model selector ────────────────────────────────────────────────────────
    st.markdown("### 🔬 Prediction Model")
    model_choice = st.radio(
        "Choose which model to use",
        options=["📐 Hand-tuned", "🤖 XGBoost (ML)"],
        help=(
            "**Hand-tuned:** Uses calibrated stage multipliers and venue "
            "characteristics (transit score, WC premium, city factor) shaped "
            "by hand against Copa América and CWC reference data.\n\n"
            "**XGBoost:** Trains on 53 real reference events and learns "
            "venue × event-type × attendance interactions automatically. "
            "5-fold CV MAE: ±0.14 multiplier units."
        ),
    )
    use_xgb = model_choice.startswith("🤖")

    # Lazy-load the XGBoost model ONLY when it's actually selected, so the
    # hand-tuned path and the landing page never wait on model loading.
    # load_xgb_model() reads the committed artifact from disk (fast) and is
    # cached, so it runs at most once per session.
    if use_xgb:
        xgb_model, xgb_cv_mae, xgb_feature_names, xgb_importances = load_xgb_model()
        st.markdown(f"""
<div class="model-info-box">
🤖 <b>XGBoost model ready</b><br>
Trained on <b>53 reference events</b> across all 11 venues.<br>
5-fold CV MAE: <b>±{xgb_cv_mae} multiplier units</b>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # API key status
    if not is_api_configured():
        st.markdown("""
<div class="api-warning">
⚠️ <b>No Google Maps API key detected.</b><br>
Travel times will use straight-line distance estimates.<br><br>
Add your key to a <code>.env</code> file:<br>
<code>GOOGLE_MAPS_API_KEY=your_key</code>
</div>
""", unsafe_allow_html=True)

    st.markdown("### 📍 Your Location")
    address = st.text_input(
        "Home address",
        placeholder="e.g. 350 5th Ave, New York, NY 10118",
        help="We use this to calculate your drive time to the stadium.",
    )

    st.markdown("### ⚽ Select Your Game")

    # Sort schedule by date
    sorted_schedule = sorted(WC_SCHEDULE, key=lambda g: (g["date"], g["kickoff_local"]))

    # Venue filter
    venue_options = ["All venues"] + sorted(
        {VENUES[g["venue_id"]]["city"] for g in sorted_schedule}
    )
    selected_city = st.selectbox("Filter by city", venue_options)

    filtered = sorted_schedule
    if selected_city != "All venues":
        filtered = [g for g in sorted_schedule if VENUES[g["venue_id"]]["city"] == selected_city]

    game_labels = [get_game_label(g) for g in filtered]
    selected_idx = st.selectbox(
        "Game",
        range(len(filtered)),
        format_func=lambda i: game_labels[i],
    )
    selected_game = filtered[selected_idx]

    st.markdown("### 🕐 Arrival Goal")
    arrival_buffer = st.slider(
        "I want to arrive this many minutes before kickoff",
        min_value=15,
        max_value=120,
        value=60,
        step=15,
        help="Buffer for finding your seat, grabbing food, etc.",
    )

    st.markdown("---")
    calculate = st.button("🚗 Calculate Departure Time", type="primary", use_container_width=True)


# ─── Main content ─────────────────────────────────────────────────────────────

model_badge_html = (
    '<span class="model-badge-ml">🤖 XGBoost ML</span>'
    if use_xgb else
    '<span class="model-badge-ht">📐 Hand-tuned</span>'
)

st.markdown(
    f"## ⚽ WC 2026 Traffic Predictor &nbsp; {model_badge_html}",
    unsafe_allow_html=True,
)
st.markdown(
    "Find out when to leave home to beat the World Cup traffic and "
    "arrive at the stadium on time."
)

if not calculate:
    # Landing state — show venue summary cards + model comparison
    st.markdown("---")

    if use_xgb:
        # XGBoost landing: show feature importances prominently
        game_col, model_col = st.columns([3, 2])
        with game_col:
            st.markdown("### 📅 Upcoming Games at a Glance")
            today    = date.today()
            upcoming = [g for g in sorted_schedule if g["date"] >= today][:9]
            cols     = st.columns(3)
            for i, game in enumerate(upcoming):
                venue   = VENUES[game["venue_id"]]
                home    = game["home"]
                away    = game["away"]
                matchup = f"{home} vs {away}" if home != "TBD" else game["stage"]
                with cols[i % 3]:
                    st.markdown(f"""
**{matchup}**
📍 {venue['city']}
📅 {game['date'].strftime('%b %d')} · {game['kickoff_local'].strftime('%-I:%M %p')}
🏆 {game['stage']}
                    """)
                    st.markdown("---")

        with model_col:
            st.markdown("### 🤖 About the XGBoost Model")
            st.markdown(f"""
<div class="model-info-box">
<b>Training data:</b> 53 reference events across all 11 WC 2026 venues<br>
(Copa América 2024, CWC 2025, NFL playoffs, Taylor Swift Eras Tour,
Super Bowl, Beyoncé, boxing, college football)<br><br>
<b>5-fold CV MAE: ±{xgb_cv_mae}</b> — on held-out test folds, predictions
were within ±{xgb_cv_mae}× of the real observed multiplier on average.<br><br>
<b>WC extrapolation:</b> WC stage scaling factors are applied on top of
the Copa-América-level base prediction. The Final gets a 1.88× uplift.
</div>
""", unsafe_allow_html=True)
            fig_imp = build_importance_chart(xgb_importances)
            st.plotly_chart(fig_imp, use_container_width=True)

    else:
        # Hand-tuned landing: standard game cards
        st.markdown("### 📅 Upcoming Games at a Glance")
        today    = date.today()
        upcoming = [g for g in sorted_schedule if g["date"] >= today][:12]
        cols     = st.columns(3)
        for i, game in enumerate(upcoming):
            venue   = VENUES[game["venue_id"]]
            home    = game["home"]
            away    = game["away"]
            matchup = f"{home} vs {away}" if home != "TBD" else game["stage"]
            with cols[i % 3]:
                st.markdown(f"""
**{matchup}**
📍 {venue['city']}
📅 {game['date'].strftime('%b %d, %Y')} · {game['kickoff_local'].strftime('%-I:%M %p')} local
🏆 {game['stage']}
                """)
                st.markdown("---")

    st.markdown("""
<div class="info-box">
ℹ️ <b>How it works:</b> Enter your address, pick a game, and set how early you want to arrive.
Switch between models using the selector in the sidebar to compare hand-tuned vs ML predictions.
</div>
""", unsafe_allow_html=True)

else:
    # ── Validate inputs ──────────────────────────────────────────────────────
    if not address.strip():
        st.error("Please enter your home address in the sidebar.")
        st.stop()

    with st.spinner("Geocoding your address and calculating travel time..."):
        coords = geocode_address(address)

    if coords is None:
        st.error(
            "Could not geocode that address. "
            "Please check the address or add a Google Maps API key to your .env file."
        )
        st.stop()

    venue      = VENUES[selected_game["venue_id"]]
    kickoff_dt = localize_kickoff(selected_game)

    # Desired arrival = kickoff - buffer
    desired_arrival_dt = kickoff_dt - timedelta(minutes=arrival_buffer)

    # Baseline = free-flow time × day/time congestion factor × city traffic factor
    with st.spinner("Fetching baseline travel time for this day and time..."):
        baseline_min = get_baseline_travel_time(
            coords["lat"], coords["lon"],
            venue["lat"], venue["lon"],
            reference_dt=desired_arrival_dt,
            city_traffic_factor=venue.get("city_traffic_factor", 1.0),
        )

    if baseline_min is None or baseline_min <= 0:
        st.error("Could not calculate travel time. Please check your address.")
        st.stop()

    # ── Run selected model ───────────────────────────────────────────────────
    if use_xgb:
        result = find_departure_time_xgb(
            model=xgb_model,
            baseline_minutes=baseline_min,
            venue_id=selected_game["venue_id"],
            stage_importance=selected_game["stage_importance"],
            expected_capacity_pct=selected_game["expected_capacity_pct"],
            stage=selected_game["stage"],
            kickoff_dt=kickoff_dt,
            desired_arrival_dt=desired_arrival_dt,
            home=selected_game["home"],
            away=selected_game["away"],
        )
    else:
        result = find_departure_time(
            baseline_minutes=baseline_min,
            venue_id=selected_game["venue_id"],
            stage_importance=selected_game["stage_importance"],
            expected_capacity_pct=selected_game["expected_capacity_pct"],
            stage=selected_game["stage"],
            kickoff_dt=kickoff_dt,
            desired_arrival_dt=desired_arrival_dt,
            home=selected_game["home"],
            away=selected_game["away"],
        )

    severity = result["severity"]

    # ── Header ───────────────────────────────────────────────────────────────
    home    = selected_game["home"]
    away    = selected_game["away"]
    matchup = f"{home} vs {away}" if home != "TBD" else selected_game["stage"]

    st.markdown(f"## {matchup}")
    st.markdown(
        f"📍 **{venue['name']}** · {venue['city']}  \n"
        f"📅 **{kickoff_dt.strftime('%A, %B %d, %Y')}** · "
        f"Kickoff {kickoff_dt.strftime('%-I:%M %p')} local  \n"
        f"🏆 **{selected_game['stage']}**"
    )

    if coords.get("formatted_address"):
        st.markdown(f"🏠 Routing from: *{coords['formatted_address']}*")

    st.markdown("---")

    # ── Key metrics ──────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
<div class="main-metric">
  <div class="label">Leave By</div>
  <div class="value">{format_time(result['departure_time'])}</div>
  <div class="sub">{result['departure_time'].strftime('%a, %b %-d')}</div>
</div>
""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
<div class="main-metric">
  <div class="label">Expected Drive</div>
  <div class="value">{format_minutes(result['expected_travel_minutes'])}</div>
  <div class="sub">vs {format_minutes(result['normal_travel_minutes'])} normally</div>
</div>
""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
<div class="main-metric">
  <div class="label">Extra Time</div>
  <div class="value">+{format_minutes(result['extra_minutes'])}</div>
  <div class="sub">{result['multiplier_at_departure']}× normal travel time</div>
</div>
""", unsafe_allow_html=True)

    with col4:
        sev = result["severity"]
        st.markdown(f"""
<div class="main-metric">
  <div class="label">Traffic Severity</div>
  <div class="value">{sev['emoji']}</div>
  <div class="sub" style="font-size:16px; color:{sev['color']}; font-weight:600">{sev['label']}</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Chart (+ feature importances sidebar when XGBoost is active) ─────────
    if use_xgb:
        chart_col, imp_col = st.columns([3, 1])
        with chart_col:
            fig = build_chart(result, kickoff_dt, baseline_min, use_xgb=True)
            st.plotly_chart(fig, use_container_width=True)
        with imp_col:
            st.markdown("##### Feature Importances")
            fig_imp = build_importance_chart(xgb_importances)
            st.plotly_chart(fig_imp, use_container_width=True)
    else:
        fig = build_chart(result, kickoff_dt, baseline_min, use_xgb=False)
        st.plotly_chart(fig, use_container_width=True)

    # ── Departure timeline ───────────────────────────────────────────────────
    st.markdown("### 🗓️ Your Day-Of Timeline")

    arrival_est = result["departure_time"] + timedelta(minutes=result["expected_travel_minutes"])

    timeline_data = {
        "Event": [
            "🚗 Leave home",
            f"🚦 Expected arrival at {venue['name']}",
            "⚽ Kickoff",
        ],
        "Time": [
            format_time(result["departure_time"]),
            format_time(arrival_est),
            format_time(kickoff_dt),
        ],
        "Notes": [
            f"Drive time: {format_minutes(result['expected_travel_minutes'])} (normally {format_minutes(result['normal_travel_minutes'])})",
            f"{arrival_buffer} min before kickoff",
            matchup,
        ],
    }

    st.table(pd.DataFrame(timeline_data))

    # ── Contextual warnings & tips ───────────────────────────────────────────
    st.markdown("### 💡 Tips for This Game")

    tips = []

    # Stage-based tips
    if selected_game["stage_importance"] >= 5:
        tips.append(
            "🚨 **Semi-Final / Final level event.** Expect the worst traffic this "
            "venue has ever seen. The model's peak multiplier of "
            f"**{result['peak_multiplier']}×** is calibrated against Copa América "
            "finals and Super Bowls. Leaving even earlier than recommended is wise."
        )
    elif selected_game["stage_importance"] >= 3:
        tips.append(
            "⚠️ **Knockout stage.** Traffic will be significantly heavier than a "
            "regular group stage game. Build in extra buffer if possible."
        )

    # Transit tips per venue
    transit_tips = {
        "metlife":           "🚆 **NJ Transit** runs dedicated game-day trains directly to the stadium. "
                             "This is strongly recommended — it bypasses the worst road congestion.",
        "mercedes_benz":     "🚇 **MARTA** runs directly to the stadium (Vine City station). "
                             "Atlanta traffic is notoriously bad; take the train if you can.",
        "lincoln_financial": "🚇 **SEPTA** Broad Street Line to Pattison station is a direct, "
                             "fast option. Eagles fans know — take the train.",
        "lumen_field":       "🚇 **Link Light Rail** stops nearby. Seattle's transit system is excellent "
                             "for stadium events. Highly recommended.",
        "sofi":              "🚇 **Metro K Line** (Crenshaw) has a direct stop. LA traffic is brutal — "
                             "even a partial transit trip (drive + rail) helps significantly.",
        "att":               "🚗 **Car only.** AT&T Stadium is one of the most car-dependent major venues in "
                             "the US. The surrounding I-20/I-30/SH-360 interchange is your main challenge.",
        "arrowhead":         "🚗 **Car only.** Almost no transit to Arrowhead. Factor in parking lot exit time "
                             "(30–45 min post-game is common).",
        "gillette":          "🚗 **Mostly car.** Commuter rail runs on event days but is limited. "
                             "Route 1 southbound is your main headache — allow extra time.",
        "hard_rock":         "🚗 **Mostly car.** Limited transit options in suburban Miami Gardens. "
                             "I-95 and the Palmetto Expressway are your main arteries.",
        "levis":             "🚇 **VTA + Caltrain** options exist. The Santa Clara stadium is more transit-friendly "
                             "than it looks — worth checking game-day shuttles.",
        "nrg":               "🚇 **METRORail Red Line** stops at NRG Park. Houston traffic on I-610/US-59 "
                             "is severe on event days — transit saves significant time.",
    }
    if selected_game["venue_id"] in transit_tips:
        tips.append(transit_tips[selected_game["venue_id"]])

    # Timing tips
    peak_multiplier = result["peak_multiplier"]
    if peak_multiplier >= 3.5:
        tips.append(
            "⏰ **Post-game egress will also be brutal.** If you're driving, "
            "expect 45–90 minutes to clear the stadium area after the final whistle."
        )

    if selected_game["kickoff_local"].hour >= 20:
        tips.append(
            "🌙 **Evening kickoff.** Late-night games mean post-game traffic extends into "
            "midnight. If you have a long drive, consider hotel options near the venue."
        )
    elif selected_game["kickoff_local"].hour <= 13:
        tips.append(
            "☀️ **Midday kickoff.** Traffic builds from early morning. Your departure "
            "time may be during normal rush hours — extra caution needed."
        )

    if not is_api_configured():
        tips.append(
            "⚠️ **Note:** Travel time is estimated from straight-line distance (no API key). "
            "For accurate routing, add a Google Maps API key to your `.env` file."
        )

    for tip in tips:
        st.markdown(f'<div class="info-box">{tip}</div>', unsafe_allow_html=True)

    # ── Model details expander ───────────────────────────────────────────────
    expander_label = (
        "🤖 How the XGBoost Model Made This Prediction"
        if use_xgb else
        "📊 Model Calibration Data — What This Prediction Is Based On"
    )

    with st.expander(expander_label):
        if use_xgb:
            from data.teams import get_matchup_demand_info
            from model.xgboost_multiplier import WC_STAGE_FACTOR

            demand_info  = get_matchup_demand_info(home, away)
            stage_factor = WC_STAGE_FACTOR.get(selected_game["stage_importance"], 1.22)
            team_mult    = demand_info["multiplier"]
            is_3rd       = "third" in selected_game["stage"].lower() or "3rd" in selected_game["stage"].lower()
            third_disc   = 0.85 if is_3rd else 1.0
            xgb_base     = round(result["peak_multiplier"] / (stage_factor * team_mult * third_disc), 3)

            st.markdown(f"""
**Step-by-step XGBoost prediction for {matchup} at {venue['name']}:**

| Step | Factor | Value | Explanation |
|---|---|---|---|
| 1 | XGBoost base prediction | **{xgb_base}×** | Trained on Copa/CWC/NFL/concert events — predicts Copa-level baseline |
| 2 | WC stage factor (stage {selected_game['stage_importance']}) | **{stage_factor}×** | Scales prediction up to WC {selected_game['stage']} demand |
| 3 | Third-place discount | **{third_disc}×** | {"Applied (3rd place match)" if is_3rd else "Not applied"} |
| 4 | Team demand multiplier | **{team_mult}×** | {demand_info['label']} matchup — {home} (score: {demand_info['home_score']}) vs {away} (score: {demand_info['away_score']}) |
| **Final** | **Peak multiplier** | **{result['peak_multiplier']}×** | Worst-case travel time is {result['peak_multiplier']}× the normal drive |

**5-fold CV MAE: ±{xgb_cv_mae} multiplier units**
""")
        else:
            st.markdown(f"""
The traffic multiplier for this game was estimated using **{selected_game['stage']}**
parameters for **{venue['name']}**, calibrated against real historical events at this venue.

| Parameter | Value |
|---|---|
| Stage importance | {selected_game['stage_importance']} / 6 |
| Expected capacity | {selected_game['expected_capacity_pct']*100:.0f}% |
| Peak multiplier (worst-case departure) | **{result['peak_multiplier']}×** |
| Venue transit score | {venue['transit_score']} / 1.0 |
| WC 2026 venue premium | {venue['wc_premium']}× |

**Key reference events used for this venue:**
""")

        from data.reference_events import get_events_for_venue
        ref_events = get_events_for_venue(selected_game["venue_id"])
        if ref_events:
            ref_df = pd.DataFrame([{
                "Event":          e["event_name"][:55] + ("..." if len(e["event_name"]) > 55 else ""),
                "Attendance":     f"{e['attendance']:,} ({e['attendance_pct']*100:.0f}%)",
                "Sold Out":       "✅" if e["is_sold_out"] else "❌",
                "Peak Mult. Est.": f"{e['peak_multiplier_estimate']}×",
            } for e in ref_events])
            st.dataframe(ref_df, use_container_width=True, hide_index=True)

    # ── Footer ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        "<small style='color:#475569'>**Disclaimer:** Traffic predictions are estimates based on "
        "historical patterns from comparable events. Actual conditions on game day may vary. "
        "Always allow extra buffer time and monitor real-time traffic apps (Waze, Google Maps) "
        "as the event approaches. WC 2026 multipliers are calibrated against Copa América 2024, "
        "Club World Cup 2025, NFL playoff games, and major concert events at each venue.</small>",
        unsafe_allow_html=True,
    )
