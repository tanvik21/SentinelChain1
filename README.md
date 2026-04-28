# ⬡ SentinelChain
### Silent AI Watchman for Indian Supply Chains

> *"India's 63 million SMEs lose crores every year to supply chain disruptions they never saw coming. SentinelChain sees it coming — and whispers in your ear before it's too late."*

---

## What It Does

SentinelChain is a multi-agent AI system that monitors India's supply chain corridors 24/7 and sends **one actionable alert in your language before the disruption hits.**

No dashboard to check. No app to open. Just a message on WhatsApp or SMS when something threatens your business specifically.

---

## The Problem

A flood hits NH48 on Monday night. Arjun's dye shipment from Surat doesn't arrive Wednesday. He finds out when the truck doesn't show up. He's already lost two days. His export deadline is Friday. He pays ₹8 lakh in penalties.

**SentinelChain would have messaged Arjun on Sunday night.**

---

## Novel Architecture — Cascade Threat Personalization Network
Signal Mesh → Persona Engine → Counterfactual Scorer → Vernacular Compressor → Channel Router

### Layer 1 — Signal Mesh (NetworkX Graph)
A living graph of 32 nodes across India's highway network. Weather, highway congestion, port status, and commodity prices update every 15 minutes. Nodes are connected by weighted edges a flood in Surat automatically propagates risk to NH48, which propagates to every user with an active shipment on that corridor.

### Layer 2 — ML Disruption Prediction (XGBoost)
Trained on 2,000 samples of Indian weather-disruption patterns. Features: precipitation, wind speed, weather code, highway vulnerability, commodity sensitivity, monsoon season indicator. Replaces hardcoded thresholds with learned probabilities. ROC-AUC: 0.87+

### Layer 3 — Demand Forecast Engine (Gradient Boosting)
Five commodity-specific price forecasters (agri, textile, pharma, auto_parts, electronics) trained on 730-day synthetic time series with real Indian seasonal patterns monsoon volatility, festive demand surges, harvest cycles. Detects price spikes 7 days ahead.

### Layer 4 — Sentiment Signal Engine (Gemini + NLP)
Fetches real Indian news headlines, sends them to Gemini for structured threat extraction. Detects trucker strikes, port congestion, political disruptions, highway closures. Injects sentiment scores as edge weights into the Signal Mesh boosting corridor risk when news confirms weather signals.

### Layer 5 — Persona Engine
Every user has a Persona not just a profile. Knows their suppliers, active shipments, risk tolerance, preferred language, and alert channel. Computes the **Counterfactual Cost of Silence** the exact rupee loss if we don't warn this user right now. Only fires alerts when staying silent costs more than speaking.

### Layer 6 — Vernacular Compression (Gemini)
Takes 50 data points and compresses to exactly two sentences. Sentence 1: what will happen and when. Sentence 2: one action to take right now. Never longer. Optimized for a person reading on a moving vehicle in 4 seconds.

---

## The Core Insight

> *"Our system doesn't predict disruptions it computes the personalized counterfactual cost of silence for each user and fires an alert only when staying quiet becomes more dangerous than speaking."*

This is not a single threshold system. Alert firing uses an **asymmetric loss function** — missing a real threat is penalized 3-5x more than a false alarm for high-stakes users (pharma, perishables). Risk tolerance is per-persona, not global.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Intelligence Backend | Python 3.14, FastAPI, NetworkX |
| ML Models | XGBoost, Gradient Boosting, Scikit-learn |
| AI / LLM | Google Gemini 1.5 Flash (Vertex AI) |
| Forecasting | Pandas, NumPy, time-series feature engineering |
| 3D Frontend | React, Vite, Three.js, React Three Fiber |
| Map Layer | Deck.GL, MapLibre GL |
| Animations | Framer Motion |
| Data Sources | IMD (weather), Open-Meteo API, Agmarknet, Google News RSS |

---

## Google Tools Used

- **Gemini 1.5 Flash** — Sentiment threat extraction from news headlines, vernacular alert generation, counterfactual reasoning
- **Google News RSS** — Real-time Indian supply chain news ingestion
- **Open-Meteo API** — Free weather forecasting for 12 Indian cities
- *(Production roadmap)* **Vertex AI** — Model hosting and serving, **BigQuery** — Supply chain event logging, **Google Maps Routes API** — Real-time highway congestion

---

## Live Demo

| Service | URL |
|---|---|
| 3D Dashboard | `http://localhost:5173` |
| Intelligence API | `http://localhost:8000` |
| API Docs | `http://localhost:8000/docs` |
| Intelligence Summary | `http://localhost:8000/intelligence-summary` |
| Demand Forecast | `http://localhost:8000/forecast/agri` |
| Sentiment Signals | `http://localhost:8000/sentiment` |

---

## Project Structure
sentinelchain/
├── signal_service/          # Intelligence backend
│   ├── signal_mesh.py       # Living graph — India's highway network
│   ├── personas.py          # Persona engine + counterfactual scoring
│   ├── alert_engine.py      # Vernacular compression via Gemini
│   ├── sentinel.py          # Orchestrator — runs full intelligence cycle
│   ├── main.py              # FastAPI backend — all endpoints
│   ├── ml/
│   │   ├── disruption_model.py   # XGBoost disruption classifier
│   │   ├── demand_forecast.py    # Gradient Boosting price forecaster
│   │   └── sentiment_signal.py   # Gemini-powered news threat extraction
│   └── models/              # Saved ML model artifacts (22 files)
├── app/                     # React 3D frontend
│   ├── src/
│   │   └── App.jsx          # 3D globe + intelligence dashboard
│   └── package.json
├── data/                    # Runtime data (latest cycle JSON)
└── README.md

---

## Running Locally

```bash
# Backend
cd signal_service
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd app
npm install
npm run dev
```

Add your Gemini API key to `signal_service/.env`:
GEMINI_API_KEY=your_key_here

---

## Who It's For

| User | Problem | Alert Example |
|---|---|---|
| **Arjun Mehta**, Textile Manufacturer, Ludhiana | NH48 flood risk, dye shipment delayed | *"NH48 par kal baarish ki sambhaavna 72% hai. Aapki Surat delivery 2 din late ho sakti hai. Abhi Ahmedabad supplier ko call karein."* |
| **Meena Kulkarni**, Pharma Distributor, Dharwad | Medicine stockout risk | *"ನಿಮ್ಮ Amoxicillin ಸ್ಟಾಕ್ 6 ದಿನಗಳಲ್ಲಿ ಖಾಲಿಯಾಗುತ್ತದೆ. ಇಂದೇ 80 strips ಆರ್ಡರ್ ಮಾಡಿ."* |
| **Ravi Patil**, Agri Cooperative, Nashik | Price crash warning | *"पुणे मंडीत शुक्रवारी टोमॅटोचे भाव 35% घसरतील. बुधवारपर्यंत विका."* |

---

## The Business Case

- India logistics sector: **₹14 lakh crore annually**
- Logistics inefficiency cost: **₹8 lakh crore wasted per year**
- SMEs with zero digital supply chain tools: **70%+**
- Existing solutions minimum cost: **₹2 crore+ (SAP, Oracle)**
- SentinelChain target: **₹499/month per business**

**TAM: 63 million Indian SMEs. Zero are currently served.**

---

## Built By

**Mohammed Ali Khan** & **Tanvik**  
B.E. Artificial Intelligence & Data Science  
CMR Institute of Technology, Bengaluru  
GitHub: [github.com/Alikhan207](https://github.com/Alikhan207)
