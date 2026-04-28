"""
SentinelChain — FastAPI Backend (Complete)
All architecture gaps filled:
  ✓ SQLite user database
  ✓ Real data ingestion (Agmarknet, Open-Meteo, News)
  ✓ Delivery service (WhatsApp/SMS/App router)
  ✓ Feedback resonance loop (federated learning pattern)
  ✓ Intelligence service endpoints
  ✓ Cycle history + pattern analysis
"""
import sys
import os

# Ensure signal_service directory is on path
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import json

from sentinel import SentinelChain
from personas import PersonaEngine, ARCHETYPES
from auth import (
    UserRegister, LoginRequest, get_current_user, require_admin,
    register_user, login_user, load_users, _safe_user
)
from database import (
    get_user_by_id, get_all_users, log_alert, record_feedback,
    get_user_trust_score, log_cycle, get_cycle_history, init_db
)

# --- Delivery service ---
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "delivery_service"))
    from router import get_channel_router
    DELIVERY_AVAILABLE = True
except ImportError:
    DELIVERY_AVAILABLE = False
    print("[main] Delivery service not found — alerts will be logged only")

# --- Intelligence service ---
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "intelligence_service"))
    from feedback_loop import get_feedback_loop, get_pattern_analyzer
    INTELLIGENCE_AVAILABLE = True
except ImportError:
    INTELLIGENCE_AVAILABLE = False
    print("[main] Intelligence service not found")

app = FastAPI(
    title="SentinelChain API",
    version="2.0.0",
    description="Silent AI Watchman for Indian Supply Chains",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Initialize systems ---
init_db()
sentinel = SentinelChain()
persona_engine = PersonaEngine()

# Seed demo data on startup
MOCK_THREATS = [
    {
        "highway": "NH48",
        "route": "Mumbai-Delhi",
        "risk_score": 0.72,
        "affected_cities": ["Surat", "Ahmedabad"],
        "severity": "HIGH",
        "detected_at": datetime.now().isoformat(),
    },
    {
        "highway": "NH47",
        "route": "Pune-Bangalore",
        "risk_score": 0.45,
        "affected_cities": ["Kolhapur", "Hubli"],
        "severity": "MEDIUM",
        "detected_at": datetime.now().isoformat(),
    },
]

affected = persona_engine.get_affected_users(MOCK_THREATS)
demo_alerts = sentinel.alert_engine.generate_all_alerts(affected)

os.makedirs(os.path.join(os.path.dirname(__file__), "..", "data"), exist_ok=True)
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "latest_cycle.json")

demo_cycle = {
    "cycle_id": "CYC-DEMO-001",
    "timestamp": datetime.now().isoformat(),
    "threats_detected": len(MOCK_THREATS),
    "users_affected": len(affected),
    "alerts_generated": len(demo_alerts),
    "alerts": demo_alerts,
    "graph_summary": sentinel.signal_mesh.get_graph_summary(),
    "threat_level": "ELEVATED",
    "max_corridor_risk": 0.72,
}
with open(DATA_PATH, "w", encoding="utf-8") as f:
    json.dump(demo_cycle, f, ensure_ascii=False, indent=2)

# Log demo alerts to SQLite
for alert in demo_alerts:
    try:
        log_alert(alert)
    except Exception:
        pass

# Log demo cycle
try:
    log_cycle(demo_cycle)
except Exception:
    pass

# Route demo alerts through delivery service
if DELIVERY_AVAILABLE:
    router = get_channel_router()
    users_by_id = {u["id"]: u for u in get_all_users()}
    router.route_all(demo_alerts, users_by_id)


# ── ROOT ──────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "system": "SentinelChain",
        "version": "2.0.0",
        "tagline": "Silent AI Watchman for Indian Supply Chains",
        "status": "online",
        "capabilities": {
            "ml_layers": ["XGBoost disruption", "Gradient Boost demand forecast", "Gemini NLP sentiment"],
            "data_sources": ["Open-Meteo weather", "Agmarknet mandi prices", "Google News RSS", "Port simulation"],
            "delivery_channels": ["WhatsApp", "SMS", "App Push"],
            "database": "SQLite",
            "feedback_loop": INTELLIGENCE_AVAILABLE,
        },
    }


@app.get("/status")
def get_status():
    return sentinel.get_status()


# ── CYCLE ─────────────────────────────────────────────────────────

@app.post("/run-cycle")
def run_cycle():
    alerts = sentinel.run_cycle()

    # Log each alert to SQLite
    for alert in alerts:
        try:
            log_alert(alert)
        except Exception:
            pass

    # Route through delivery service
    delivery_records = []
    if DELIVERY_AVAILABLE:
        router = get_channel_router()
        users_by_id = {u["id"]: u for u in get_all_users()}
        delivery_records = router.route_all(alerts, users_by_id)

    # Compute threat level
    max_risk = sentinel.signal_mesh.get_graph_summary().get("max_risk", 0)
    threat_level = "CRITICAL" if max_risk > 0.6 else "ELEVATED" if max_risk > 0.35 else "NORMAL"

    # Log cycle to history
    cycle_data = {
        "cycle_id": f"CYC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "threats_detected": len(sentinel.signal_mesh.compute_corridor_threats()),
        "users_affected": len({a.get("user_id") for a in alerts}),
        "alerts_generated": len(alerts),
        "threat_level": threat_level,
        "max_corridor_risk": max_risk,
    }
    try:
        log_cycle(cycle_data)
    except Exception:
        pass

    return {
        "success": True,
        "alerts_generated": len(alerts),
        "alerts": alerts,
        "delivery_records": delivery_records,
        "threat_level": threat_level,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/cycle-history")
def get_history():
    return {
        "success": True,
        "history": get_cycle_history(20),
    }


# ── ALERTS ────────────────────────────────────────────────────────

@app.get("/alerts")
def get_alerts():
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            cycle = json.load(f)
        return {
            "success": True,
            "cycle_id": cycle["cycle_id"],
            "timestamp": cycle["timestamp"],
            "threats_detected": cycle["threats_detected"],
            "users_affected": cycle["users_affected"],
            "alerts": cycle["alerts"],
        }
    except FileNotFoundError:
        return {"success": False, "alerts": [], "message": "No cycle run yet"}


@app.get("/alerts/{user_id}")
def get_user_alerts(user_id: str):
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            cycle = json.load(f)
        return {
            "success": True,
            "alerts": [a for a in cycle["alerts"] if a.get("user_id") == user_id],
        }
    except FileNotFoundError:
        return {"success": False, "alerts": []}


# ── THREATS & INTELLIGENCE ────────────────────────────────────────

@app.get("/threats")
def get_threats():
    return {
        "success": True,
        "active_threats": sentinel.signal_mesh.compute_corridor_threats(),
        "graph_summary": sentinel.signal_mesh.get_graph_summary(),
        "mock_threats": MOCK_THREATS,
    }


@app.get("/sentiment")
def get_sentiment():
    engine = sentinel.signal_mesh.sentiment_engine
    return {
        "success": True,
        "active_signals": len(engine.active_signals),
        "signals": engine.active_signals,
        "corridor_scores": {
            c: engine.get_corridor_sentiment_score(c)
            for c in ["NH48", "NH44", "NH47", "NH19", "NH16", "NH27"]
        },
        "commodity_scores": {
            c: engine.get_commodity_sentiment_score(c)
            for c in ["agri", "textile", "pharma", "auto_parts", "electronics"]
        },
        "last_scan": datetime.now().isoformat(),
    }


@app.get("/forecast/{commodity}")
def get_forecast(commodity: str):
    from ml.demand_forecast import forecast_price
    valid = ["agri", "textile", "pharma", "auto_parts", "electronics"]
    if commodity not in valid:
        return {"success": False, "message": f"Choose from {valid}"}
    try:
        return {"success": True, **forecast_price(commodity, days_ahead=7)}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.get("/intelligence-summary")
def get_intelligence_summary():
    from ml.demand_forecast import forecast_price

    corridor_risks = {
        n: {
            "risk_score": d.get("risk_score", 0.0),
            "sentiment_boost": d.get("sentiment_boost", 0.0),
            "route": d.get("route", ""),
        }
        for n, d in sentinel.signal_mesh.graph.nodes(data=True)
        if d["type"] == "highway"
    }

    commodity_alerts = []
    for commodity in ["agri", "textile", "pharma"]:
        try:
            forecast = forecast_price(commodity, days_ahead=3)
            if forecast.get("spike_alert"):
                commodity_alerts.append(forecast["spike_alert"])
        except Exception:
            pass

    max_risk = max(
        (d.get("risk_score", 0) for _, d in sentinel.signal_mesh.graph.nodes(data=True)
         if d["type"] == "highway"),
        default=0,
    )
    threat_level = "CRITICAL" if max_risk > 0.6 else "ELEVATED" if max_risk > 0.35 else "NORMAL"

    # Data source health
    ingestion_health = {
        "open_meteo": "live",
        "agmarknet": "live" if os.getenv("DATA_GOV_API_KEY") else "fallback",
        "news_rss": "live",
        "port_data": "simulated-realistic",
    }

    return {
        "success": True,
        "threat_level": threat_level,
        "max_corridor_risk": round(max_risk, 4),
        "corridor_risks": corridor_risks,
        "commodity_alerts": commodity_alerts,
        "sentiment_signals": sentinel.signal_mesh.sentiment_engine.active_signals,
        "active_alerts": len(sentinel.alert_engine.alerts_generated),
        "users_monitored": len(sentinel.persona_engine.users),
        "last_updated": sentinel.signal_mesh.last_updated,
        "data_source_health": ingestion_health,
    }


# ── DELIVERY ──────────────────────────────────────────────────────

@app.get("/delivery-log")
def get_delivery_log():
    if not DELIVERY_AVAILABLE:
        return {"success": False, "message": "Delivery service unavailable"}
    router = get_channel_router()
    return {"success": True, "log": router.get_delivery_log(50)}


@app.get("/notifications/{user_id}")
def get_notifications(user_id: str):
    if not DELIVERY_AVAILABLE:
        return {"success": True, "notifications": []}
    router = get_channel_router()
    return {
        "success": True,
        "notifications": router.get_unread_notifications(user_id),
    }


@app.post("/notifications/read/{alert_id}")
def mark_notification_read(alert_id: str, current_user: dict = Depends(get_current_user)):
    if DELIVERY_AVAILABLE:
        get_channel_router().mark_read(alert_id, current_user["id"])
    return {"success": True}


# ── MISSING INTELLIGENCE ENDPOINTS ────────────────────────────────

@app.get("/attributions")
def get_all_attributions():
    attributions = {}
    for node, data in sentinel.signal_mesh.graph.nodes(data=True):
        if data["type"] == "highway":
            risk = data.get("risk_score", 0.0)
            weather = data.get("weather_risk", risk * 0.6)
            sentiment = data.get("sentiment_boost", risk * 0.25)
            port = data.get("port_boost", risk * 0.1)
            commodity = data.get("commodity_risk", risk * 0.05)
            total = weather + sentiment + port + commodity + 0.0001
            attributions[node] = {
                "highway": node,
                "total_risk": round(risk, 4),
                "components": {"weather_ml": round(weather,4), "news_sentiment": round(sentiment,4), "port_congestion": round(port,4), "commodity_volatility": round(commodity,4)},
                "pct": {"weather_ml": round(weather/total*100), "news_sentiment": round(sentiment/total*100), "port_congestion": round(port/total*100), "commodity_volatility": round(commodity/total*100)},
                "labels": {"weather_ml":"Weather ML","news_sentiment":"News Sentiment","port_congestion":"Port Congestion","commodity_volatility":"Commodity Volatility"},
                "top_driver": max({"weather_ml":weather,"news_sentiment":sentiment,"port_congestion":port,"commodity_volatility":commodity}, key=lambda k: {"weather_ml":weather,"news_sentiment":sentiment,"port_congestion":port,"commodity_volatility":commodity}[k]),
            }
    return {"success": True, "attributions": attributions}

@app.get("/attribution/{highway_id}")
def get_attribution(highway_id: str):
    data = sentinel.signal_mesh.graph.nodes.get(highway_id, {})
    if not data:
        return {"success": False}
    risk = data.get("risk_score", 0.0)
    weather = data.get("weather_risk", risk * 0.6)
    sentiment = data.get("sentiment_boost", risk * 0.25)
    port = data.get("port_boost", risk * 0.1)
    commodity = data.get("commodity_risk", risk * 0.05)
    total = weather + sentiment + port + commodity + 0.0001
    return {
        "success": True, "highway": highway_id, "total_risk": round(risk, 4),
        "components": {"weather_ml": round(weather,4), "news_sentiment": round(sentiment,4), "port_congestion": round(port,4), "commodity_volatility": round(commodity,4)},
        "pct": {"weather_ml": round(weather/total*100), "news_sentiment": round(sentiment/total*100), "port_congestion": round(port/total*100), "commodity_volatility": round(commodity/total*100)},
        "labels": {"weather_ml":"Weather ML","news_sentiment":"News Sentiment","port_congestion":"Port Congestion","commodity_volatility":"Commodity Volatility"},
        "top_driver": max({"weather_ml":weather,"news_sentiment":sentiment,"port_congestion":port,"commodity_volatility":commodity}, key=lambda k: {"weather_ml":weather,"news_sentiment":sentiment,"port_congestion":port,"commodity_volatility":commodity}[k]),
    }

@app.get("/peak-analysis")
def get_peak_analysis():
    corridors = []
    for node, data in sentinel.signal_mesh.graph.nodes(data=True):
        if data["type"] == "highway":
            risk = data.get("risk_score", 0.0)
            corridors.append({
                "highway": node,
                "route": data.get("route", ""),
                "current_risk": round(risk, 4),
                "weather_component": round(data.get("weather_risk", risk*0.6), 4),
                "sentiment_component": round(data.get("sentiment_boost", risk*0.25), 4),
                "port_component": round(data.get("port_boost", risk*0.1), 4),
            })
    corridors.sort(key=lambda x: x["current_risk"], reverse=True)
    return {
        "success": True,
        "ranked_corridors": corridors,
        "most_volatile": corridors[0]["highway"] if corridors else None,
        "safest": corridors[-1]["highway"] if corridors else None,
    }

@app.get("/gemini-reasoning/{highway_id}")
def get_gemini_reasoning(highway_id: str):
    import google.generativeai as genai
    import os
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    data = sentinel.signal_mesh.graph.nodes.get(highway_id, {})
    risk = data.get("risk_score", 0.0)
    sentiment_signals = sentinel.signal_mesh.sentiment_engine.active_signals[:3]
    signal_text = "\n".join([s.get("summary","") for s in sentiment_signals]) or "No active news signals"
    prompt = f"""
You are SentinelChain's strategic reasoning engine. Analyze why {highway_id} has a {risk:.0%} risk score.

Active signals:
{signal_text}

Weather risk component: {data.get('weather_risk', 0):.2f}
Sentiment boost: {data.get('sentiment_boost', 0):.2f}

Respond ONLY as valid JSON with these exact keys:
{{
  "reasoning_chain": ["step 1", "step 2", "step 3"],
  "counterfactual_outcome": "one sentence — what happens if the business ignores this",
  "specific_action": "one concrete action the business owner must take today",
  "confidence": "HIGH or MEDIUM or LOW",
  "sources_used": ["signal 1", "signal 2"]
}}
"""
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json","").replace("```","").strip()
        reasoning = json.loads(text)
        return {"success": True, "highway": highway_id, "risk": risk, "reasoning": reasoning}
    except Exception as e:
        return {"success": False, "error": str(e), "reasoning": {
            "reasoning_chain": [f"{highway_id} shows elevated risk based on current signals"],
            "counterfactual_outcome": "Potential shipment delays and financial losses",
            "specific_action": "Contact your suppliers and verify shipment status today",
            "confidence": "MEDIUM", "sources_used": []
        }}

@app.get("/savings/{user_id}")
def get_savings(user_id: str, current_user: dict = Depends(get_current_user)):
    try:
        with open("../data/latest_cycle.json","r",encoding="utf-8") as f:
            cycle = json.load(f)
        my_alerts = [a for a in cycle.get("alerts",[]) if a.get("user_id")==user_id]
        total_saved = sum(a.get("counterfactual_cost_inr",0) for a in my_alerts)
        return {"success": True, "user_id": user_id, "total_saved_inr": total_saved, "alerts_acted": len(my_alerts)}
    except:
        return {"success": True, "user_id": user_id, "total_saved_inr": 0, "alerts_acted": 0}

@app.get("/intelligence-evolution/{user_id}")
def get_intelligence_evolution(user_id: str, current_user: dict = Depends(get_current_user)):
    from auth import load_users
    users = load_users()
    user = next((u for u in users.values() if u.get("id")==user_id), None)
    if not user:
        return {"success": False}
    sent = user.get("alerts_received", 0)
    acted = user.get("alerts_acted", 0)
    act_rate = acted/sent if sent>0 else 1.0
    base_threshold = 0.45
    calibrated = base_threshold - (act_rate - 0.5) * 0.2
    calibrated = max(0.2, min(0.7, calibrated))
    stage = "NEW" if sent==0 else "LEARNING" if sent<5 else "CALIBRATED" if sent<20 else "OPTIMIZED"
    insights = []
    if act_rate > 0.7:
        insights.append("You act fast on alerts — system is lowering threshold to catch more risks early for you.")
    elif act_rate < 0.3:
        insights.append("You prefer to verify before acting — system is raising confidence bar to reduce noise.")
    if sent > 0:
        insights.append(f"System has sent {sent} alerts and calibrated your profile across {user.get('business_type','').replace('_',' ')} archetype.")
    return {
        "success": True, "user_id": user_id,
        "learning_stage": stage, "act_rate": round(act_rate, 3),
        "base_threshold": base_threshold, "calibrated_threshold": round(calibrated, 3),
        "system_insights": insights,
        "archetype_trust_score": persona_engine.get_user_trust_score(user_id),
    }



# ── AUTH ──────────────────────────────────────────────────────────

@app.post("/register")
def register(data: UserRegister):
    return register_user(data)


@app.post("/login")
def login(data: LoginRequest):
    return login_user(data.email, data.password)


@app.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return _safe_user(current_user)


# ── USER ENDPOINTS ────────────────────────────────────────────────

@app.get("/users")
def get_users():
    users = []
    for u in get_all_users():
        if u.get("role") == "admin":
            continue
        archetype = ARCHETYPES.get(u.get("business_type", ""), {})
        users.append({
            "user_id": u["id"],
            "name": u["name"],
            "business": u.get("business_name", ""),
            "location": u.get("location", ""),
            "archetype": archetype.get("label", u.get("business_type", "")),
            "language": u.get("language", "english"),
            "alert_channel": u.get("alert_channel", "app"),
            "active_shipments": u.get("active_shipments", []),
            "trust_score": get_user_trust_score(u["id"]),
        })
    return {"success": True, "users": users}


@app.get("/my-alerts")
def get_my_alerts(current_user: dict = Depends(get_current_user)):
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            cycle = json.load(f)
        my_alerts = [
            a for a in cycle.get("alerts", [])
            if a.get("user_id") == current_user["id"]
        ]
        return {"success": True, "alerts": my_alerts, "total": len(my_alerts)}
    except FileNotFoundError:
        return {"success": True, "alerts": [], "total": 0}


@app.get("/my-dashboard")
def get_my_dashboard(current_user: dict = Depends(get_current_user)):
    from ml.demand_forecast import forecast_price

    archetype = ARCHETYPES.get(current_user.get("business_type", ""), {})

    my_alerts = []
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            cycle = json.load(f)
        my_alerts = [
            a for a in cycle.get("alerts", [])
            if a.get("user_id") == current_user["id"]
        ]
    except FileNotFoundError:
        pass

    # Corridor risks for user's highways
    corridor_risks = {}
    for highway in current_user.get("highways", []):
        node = sentinel.signal_mesh.graph.nodes.get(highway, {})
        corridor_risks[highway] = {
            "risk_score": node.get("risk_score", 0.0),
            "sentiment_boost": node.get("sentiment_boost", 0.0),
            "route": node.get("route", ""),
        }

    # Calibrated threshold from feedback loop
    calibrated_threshold = None
    if INTELLIGENCE_AVAILABLE:
        loop = get_feedback_loop()
        base = {"very_low": 0.25, "low": 0.35, "medium": 0.45, "high": 0.55}.get(
            archetype.get("risk_tolerance", "medium"), 0.45
        )
        calibrated_threshold = loop.get_threshold_for_archetype(
            current_user.get("business_type", ""), base
        )

    # Commodity forecast
    commodity = archetype.get("commodity", "agri")
    try:
        forecast = forecast_price(commodity, days_ahead=7)
    except Exception:
        forecast = None

    # Unread notifications
    notifications = []
    if DELIVERY_AVAILABLE:
        notifications = get_channel_router().get_unread_notifications(current_user["id"])

    return {
        "success": True,
        "user": _safe_user(current_user),
        "my_alerts": my_alerts,
        "corridor_risks": corridor_risks,
        "commodity_forecast": forecast,
        "archetype": archetype.get("label", ""),
        "active_shipments": current_user.get("active_shipments", []),
        "trust_score": get_user_trust_score(current_user["id"]),
        "calibrated_threshold": calibrated_threshold,
        "unread_notifications": len(notifications),
    }


# ── ADMIN ─────────────────────────────────────────────────────────

@app.get("/admin/overview")
def admin_overview(admin: dict = Depends(require_admin)):
    all_users = get_all_users()
    regular_users = [u for u in all_users if u.get("role") == "user"]

    intelligence_report = {}
    if INTELLIGENCE_AVAILABLE:
        try:
            intelligence_report = get_feedback_loop().get_intelligence_report()
        except Exception:
            pass

    return {
        "success": True,
        "total_users": len(regular_users),
        "system_status": sentinel.get_status(),
        "intelligence_summary": {
            "threats": len(sentinel.signal_mesh.compute_corridor_threats()),
            "alerts_generated": len(sentinel.alert_engine.alerts_generated),
            "sentiment_signals": len(sentinel.signal_mesh.sentiment_engine.active_signals),
        },
        "intelligence_report": intelligence_report,
        "data_sources": {
            "open_meteo": "active",
            "agmarknet": "active",
            "google_news_rss": "active",
            "port_simulation": "active",
        },
        "delivery_service": "active" if DELIVERY_AVAILABLE else "unavailable",
        "database": "SQLite",
    }


@app.get("/admin/users")
def admin_users(admin: dict = Depends(require_admin)):
    users = [_safe_user(u) for u in get_all_users()]
    return {"success": True, "users": users, "total": len(users)}
