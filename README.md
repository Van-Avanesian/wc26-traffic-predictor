# ⚽ WC 2026 Traffic Predictor

A Streamlit web app that tells you exactly when to leave home to beat the traffic for any FIFA World Cup 2026 match across all 11 US venues — powered by two interchangeable prediction models.

> **Live demo:** [wc26-traffic-predictor.streamlit.app](https://wc26-traffic-predictor.streamlit.app)

---

## What It Does

Enter your home address, pick a World Cup game, and set how early you want to arrive. The app:

- Fetches your **real baseline drive time** using Google Maps (accounting for the day of week and time of day)
- Predicts how much **longer the drive will take on game day** using a traffic multiplier model
- Recommends a **departure time** so you arrive when you want
- Shows a **traffic severity chart** over the entire pre/post-game window
- Provides **venue-specific transit tips** and a day-of timeline

---

## Models

You can switch between two models in the sidebar:

### 📐 Hand-Tuned Gaussian Model
A physics-inspired model that builds a smooth traffic curve using two overlapping Gaussian (bell curve) components:
- **Pre-game buildup** — peaks ~1 hour before kickoff
- **Post-game egress** — peaks ~1.5 hours after final whistle

Peak multiplier is calculated from:
- **Stage importance** (Group Stage → Final, multipliers 2.8× – 4.6×)
- **WC global premium** (1.20×) — larger security perimeters, international fan zones, more media vehicles
- **Venue WC premium** — MetLife hosting the Final gets 1.20×; smaller venues get less
- **Transit score** — venues with strong public transit (Lumen Field, Mercedes-Benz) see slightly reduced road multipliers
- **Team demand multiplier** — based on FIFA rankings + host-nation bonuses (USA games get a significant boost)

### 🤖 XGBoost ML Model
A gradient boosting model trained on **53 real reference events** at all 11 WC 2026 venues:

| Event Type | Examples |
|---|---|
| Soccer mega | Copa América 2024, Club World Cup 2025 |
| NFL playoff | AFC/NFC Championship games |
| Super Bowl | Super Bowl LVI at SoFi, Super Bowl LX at Levi's |
| Concert | Taylor Swift Eras Tour (6-night SoFi run, 3-night Gillette), Beyoncé |
| Boxing | Canelo vs. Saunders at AT&T |
| College football | CFP National Championship, Cotton Bowl |

**Features learned:**
- Event type intensity score
- Attendance % and sold-out status
- Venue transit accessibility
- Parking capacity
- City-level congestion factor
- Kickoff hour and evening flag

**5-fold cross-validated MAE: ±0.14 multiplier units**

WC-specific stage scaling factors are applied on top of the Copa América–level base prediction, since WC 2026 is the largest soccer event ever held in the US.

---

## Venues

| Venue | City | Capacity |
|---|---|---|
| MetLife Stadium | East Rutherford, NJ | 82,500 |
| Hard Rock Stadium | Miami Gardens, FL | 65,326 |
| Mercedes-Benz Stadium | Atlanta, GA | 71,000 |
| Lincoln Financial Field | Philadelphia, PA | 69,796 |
| Lumen Field | Seattle, WA | 68,740 |
| AT&T Stadium | Arlington (Dallas), TX | 80,000 |
| NRG Stadium | Houston, TX | 72,220 |
| Arrowhead Stadium | Kansas City, MO | 76,416 |
| SoFi Stadium | Inglewood (Los Angeles), CA | 70,240 |
| Levi's Stadium | Santa Clara (San Francisco), CA | 68,500 |
| Gillette Stadium | Foxborough (Boston), MA | 65,878 |

---

## Tech Stack

| Layer | Tools |
|---|---|
| Frontend | Streamlit |
| Traffic multiplier | NumPy, SciPy (Gaussian interpolation) |
| ML model | XGBoost, scikit-learn (5-fold CV) |
| Maps & geocoding | Google Maps Directions + Geocoding API |
| Charts | Plotly |
| Data | Pandas, PyTZ |

---

## Run Locally

**1. Clone the repo**
```bash
git clone https://github.com/vanavanesian/wc26-traffic-predictor.git
cd wc26-traffic-predictor
```

**2. Install dependencies**
```bash
pip3 install -r requirements.txt
```

**3. Add your Google Maps API key**

Create a `.env` file in the project root:
```
GOOGLE_MAPS_API_KEY=your_key_here
```

Get a free key at [console.cloud.google.com](https://console.cloud.google.com). Enable the **Directions API** and **Geocoding API**.

> The app works without an API key — it falls back to straight-line distance estimates.

**4. Run**
```bash
python3 -m streamlit run app.py
```

---

## Project Structure

```
wc26-traffic-predictor/
├── app.py                      # Main Streamlit app
├── requirements.txt
│
├── model/
│   ├── multiplier.py           # Hand-tuned Gaussian traffic model
│   └── xgboost_multiplier.py  # XGBoost ML model + feature engineering
│
├── data/
│   ├── venues.py               # All 11 venues with traffic characteristics
│   ├── schedule.py             # Full WC 2026 match schedule
│   ├── teams.py                # FIFA rankings + team demand multipliers
│   └── reference_events.py    # 53 calibration events (training data)
│
└── utils/
    └── maps.py                 # Google Maps API + baseline travel time logic
```

---

## How the Baseline Is Calculated

The "normal drive time" shown in the app is not a simple Google Maps lookup. It uses a three-layer approach:

```
baseline = free_flow_time × time_of_day_factor × city_traffic_factor
```

- **Free-flow time** — Google Maps route duration with no traffic model applied
- **Time-of-day factor** — multiplier reflecting typical congestion patterns (Friday 5pm ≈ 1.8×, Tuesday 10am ≈ 1.04×)
- **City traffic factor** — metro-level congestion baseline (SoFi/LA: 1.55×, Arrowhead/KC: 1.05×)

The WC event multiplier is then stacked on top of this baseline.

---

## Disclaimer

Traffic predictions are estimates based on historical patterns from comparable events. WC 2026 will be the largest soccer tournament ever held in the US — actual conditions may exceed model estimates. Always monitor real-time traffic apps (Waze, Google Maps) as game day approaches.
