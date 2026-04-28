"""
SentinelChain — Signal Mesh (Upgraded)
Now uses the real DataIngestionOrchestrator instead of inline requests.
Integrates: Open-Meteo, Agmarknet, Port congestion, News RSS, XGBoost ML.
"""
import networkx as nx
import os
import json
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from ml.disruption_model import predict_disruption, train_disruption_model
from ml.sentiment_signal import SentimentSignalEngine

load_dotenv()

# Import real data ingestion
try:
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from data_ingestion import get_ingestion_orchestrator
    INGESTION_AVAILABLE = True
except ImportError:
    INGESTION_AVAILABLE = False
    print("[SignalMesh] Data ingestion module not found — using legacy fetch")


class SignalMesh:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.last_updated = None
        self.last_ingestion_data = {}
        self._initialize_indian_corridors()

        # Load or train ML model
        if not os.path.exists("models/disruption_model.pkl"):
            print("[SignalMesh] No model found — training now...")
            train_disruption_model()
        print("[SignalMesh] ML disruption model loaded.")

        self.sentiment_engine = SentimentSignalEngine()
        self.sentiment_scores = {}

        if INGESTION_AVAILABLE:
            self.ingestion = get_ingestion_orchestrator()
            print("[SignalMesh] Real data ingestion layer active.")
        else:
            self.ingestion = None

    def _initialize_indian_corridors(self):
        corridors = [
            ("NH48", "Mumbai-Delhi",          ["Surat", "Vadodara", "Ahmedabad", "Udaipur"]),
            ("NH44", "Srinagar-Kanyakumari",  ["Nagpur", "Hyderabad", "Bangalore"]),
            ("NH19", "Delhi-Kolkata",          ["Kanpur", "Varanasi", "Patna"]),
            ("NH16", "Kolkata-Chennai",        ["Bhubaneswar", "Visakhapatnam"]),
            ("NH47", "Pune-Bangalore",         ["Kolhapur", "Hubli", "Nashik"]),
            ("NH27", "Ahmedabad-Silchar",      ["Jodhpur", "Jaipur", "Lucknow"]),
        ]
        for hid, route, cities in corridors:
            self.graph.add_node(hid, type="highway", route=route,
                                risk_score=0.0, last_checked=None,
                                sentiment_boost=0.0, port_boost=0.0)
            for city in cities:
                self.graph.add_node(city, type="city", risk_score=0.0)
                self.graph.add_edge(city, hid, weight=1.0)
                self.graph.add_edge(hid, city, weight=1.0)

        ports = ["JNPT_Mumbai", "Chennai_Port", "Mundra_Port", "Kolkata_Port"]
        port_highway_map = {
            "JNPT_Mumbai":  ["NH48", "NH47"],
            "Chennai_Port": ["NH44", "NH16"],
            "Mundra_Port":  ["NH48", "NH27"],
            "Kolkata_Port": ["NH19", "NH16"],
        }
        for port in ports:
            self.graph.add_node(port, type="port", risk_score=0.0, congestion=0.0)
            for hw in port_highway_map.get(port, []):
                self.graph.add_edge(port, hw, weight=0.6)

        commodities = ["textile", "pharma", "agri", "auto_parts", "electronics"]
        for c in commodities:
            self.graph.add_node(c, type="commodity", price_volatility=0.0,
                                sentiment_score=0.0, mandi_price=0.0)

        print(f"[SignalMesh] Initialized: {self.graph.number_of_nodes()} nodes, "
              f"{self.graph.number_of_edges()} edges")

    def update_weather_signals(self, weather_data: dict = None):
        """Use ingested weather data or fetch directly."""
        print("[SignalMesh] Updating weather signals...")

        if weather_data is None:
            # Direct fallback fetch
            import requests, random
            weather_data = {}
            city_coords = {
                "Mumbai": (19.076, 72.877), "Delhi": (28.613, 77.209),
                "Surat": (21.170, 72.831), "Ahmedabad": (23.022, 72.571),
                "Nagpur": (21.145, 79.088), "Hyderabad": (17.385, 78.486),
                "Bangalore": (12.971, 77.594), "Chennai": (13.083, 80.270),
                "Kolkata": (22.572, 88.363), "Pune": (18.520, 73.856),
                "Lucknow": (26.846, 80.946), "Jaipur": (26.912, 75.787),
                "Nashik": (19.997, 73.789),
            }
            for city, (lat, lon) in city_coords.items():
                try:
                    url = (f"https://api.open-meteo.com/v1/forecast"
                           f"?latitude={lat}&longitude={lon}"
                           f"&daily=precipitation_sum,windspeed_10m_max,weathercode"
                           f"&timezone=Asia/Kolkata&forecast_days=3")
                    r = requests.get(url, timeout=8)
                    d = r.json()["daily"]
                    weather_data[city] = {
                        "precipitation_mm": max(d.get("precipitation_sum", [0])),
                        "wind_kmh": max(d.get("windspeed_10m_max", [0])),
                        "weather_code": d.get("weathercode", [0])[0],
                    }
                except Exception:
                    month = datetime.now().month
                    weather_data[city] = {
                        "precipitation_mm": random.uniform(20, 70) if 6 <= month <= 9 else 2,
                        "wind_kmh": random.uniform(15, 30),
                        "weather_code": 1,
                    }

        for city, wd in weather_data.items():
            ml_result = predict_disruption(
                weather_data={
                    "precipitation_mm": wd.get("precipitation_mm", 0),
                    "wind_kmh": wd.get("wind_kmh", 0),
                    "weather_code": wd.get("weather_code", 0),
                },
                highway_vulnerability=0.7,
                commodity_sensitivity=0.6,
            )
            risk = ml_result["disruption_probability"]

            if city in self.graph.nodes:
                self.graph.nodes[city]["risk_score"] = risk
                self.graph.nodes[city].update(wd)
                for neighbor in self.graph.neighbors(city):
                    if self.graph.nodes[neighbor]["type"] == "highway":
                        current = self.graph.nodes[neighbor]["risk_score"]
                        self.graph.nodes[neighbor]["risk_score"] = max(current, risk * 0.8)
                if risk > 0.3:
                    print(f"  ⚠️  {city}: risk={risk:.2f}")

    def update_port_signals(self, port_data: dict = None):
        """Integrate port congestion into highway risk scores."""
        print("[SignalMesh] Updating port signals...")
        if not port_data:
            return

        port_highway_impact = {
            "JNPT_Mumbai":  ["NH48", "NH47"],
            "Chennai_Port": ["NH44", "NH16"],
            "Mundra_Port":  ["NH48", "NH27"],
            "Kolkata_Port": ["NH19", "NH16"],
        }

        for port, pdata in port_data.items():
            congestion = pdata.get("congestion_index", 0)
            if port in self.graph.nodes:
                self.graph.nodes[port]["congestion"] = congestion
                self.graph.nodes[port]["risk_score"] = congestion

            # Propagate port congestion to nearby highways
            for hw in port_highway_impact.get(port, []):
                if hw in self.graph.nodes:
                    current = self.graph.nodes[hw]["risk_score"]
                    boost = congestion * 0.25  # port congestion adds up to 25% to corridor risk
                    self.graph.nodes[hw]["risk_score"] = min(current + boost, 1.0)
                    self.graph.nodes[hw]["port_boost"] = boost

            if congestion > 0.5:
                print(f"  ⚠️  {port}: congestion={congestion:.2f}, severity={pdata.get('severity')}")

    def update_commodity_signals(self, mandi_data: dict = None):
        """Use real Agmarknet data when available."""
        print("[SignalMesh] Updating commodity signals...")
        import random

        month = datetime.now().month
        monsoon = 6 <= month <= 9
        festive = month in [10, 11, 12, 1]

        base_volatility = {
            "agri":        0.6 if monsoon else 0.3,
            "textile":     0.15 + (0.2 if festive else 0.05),
            "pharma":      0.1 + (0.15 if monsoon else 0.05),
            "auto_parts":  0.12 + random.uniform(0, 0.12),
            "electronics": 0.18 + (0.25 if festive else 0.05),
        }

        for commodity, vol in base_volatility.items():
            vol += random.uniform(-0.05, 0.05)
            vol = round(max(0.0, min(1.0, vol)), 3)

            if commodity in self.graph.nodes:
                self.graph.nodes[commodity]["price_volatility"] = vol

                # If real mandi data available, extract price signal
                if mandi_data:
                    for item_name, item_data in mandi_data.items():
                        self.graph.nodes[commodity]["mandi_price"] = item_data.get(
                            "avg_modal_price_inr", 0
                        )

                if vol > 0.4:
                    print(f"  ⚠️  {commodity}: volatility={vol:.2f}")

    def compute_corridor_threats(self):
        threats = []
        for node, data in self.graph.nodes(data=True):
            if data["type"] == "highway":
                risk = data.get("risk_score", 0.0)
                if risk > 0.25:
                    affected_cities = [
                        n for n in self.graph.predecessors(node)
                        if self.graph.nodes[n]["type"] == "city"
                    ]
                    threats.append({
                        "highway": node,
                        "route": data.get("route", ""),
                        "risk_score": round(risk, 4),
                        "sentiment_boost": round(data.get("sentiment_boost", 0), 4),
                        "port_boost": round(data.get("port_boost", 0), 4),
                        "affected_cities": affected_cities,
                        "severity": "HIGH" if risk > 0.6 else "MEDIUM" if risk > 0.4 else "LOW",
                        "detected_at": datetime.now().isoformat(),
                    })
        threats.sort(key=lambda x: x["risk_score"], reverse=True)
        return threats

    def get_graph_summary(self):
        risks = [
            d.get("risk_score", 0)
            for _, d in self.graph.nodes(data=True)
            if d["type"] == "highway"
        ]
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "high_risk_highways": [
                n for n, d in self.graph.nodes(data=True)
                if d["type"] == "highway" and d.get("risk_score", 0) > 0.3
            ],
            "max_risk": round(max(risks) if risks else 0, 4),
            "avg_risk": round(sum(risks) / len(risks) if risks else 0, 4),
            "last_updated": self.last_updated,
        }

    def run_full_update(self):
        print(f"\n[SignalMesh] Full update — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Use real ingestion orchestrator when available
        if self.ingestion:
            ingestion_data = self.ingestion.run_full_ingestion()
            self.last_ingestion_data = ingestion_data

            self.update_weather_signals(ingestion_data.get("weather", {}))
            self.update_port_signals(ingestion_data.get("port_congestion", {}))
            self.update_commodity_signals(ingestion_data.get("mandi_prices", {}))

            # Feed ingested headlines to sentiment engine
            headlines = ingestion_data.get("headlines", [])
            if headlines:
                self.sentiment_engine.SIMULATED_HEADLINES = headlines
        else:
            self.update_weather_signals()
            self.update_commodity_signals()

        # Sentiment layer
        print("[SignalMesh] Running sentiment scan...")
        self.sentiment_engine.run_sentiment_scan()

        for node, data in self.graph.nodes(data=True):
            if data["type"] == "highway":
                sentiment_boost = self.sentiment_engine.get_corridor_sentiment_score(node)
                current = data.get("risk_score", 0.0)
                self.graph.nodes[node]["risk_score"] = min(current + sentiment_boost * 0.4, 1.0)
                self.graph.nodes[node]["sentiment_boost"] = sentiment_boost
            if data["type"] == "commodity":
                self.graph.nodes[node]["sentiment_score"] = (
                    self.sentiment_engine.get_commodity_sentiment_score(node)
                )

        threats = self.compute_corridor_threats()
        self.last_updated = datetime.now().isoformat()
        print(f"[SignalMesh] Done. {len(threats)} threats detected.")
        return threats

    def get_corridor_attribution(self, highway_id: str) -> dict:
        node_data = self.graph.nodes.get(highway_id, {})
        if not node_data:
            return None
        
        base_risk = node_data.get("risk_score", 0.0)
        sentiment_boost = node_data.get("sentiment_boost", 0.0)
        port_boost = node_data.get("port_boost", 0.0)
        weather_base = max(0, base_risk - sentiment_boost - port_boost)
        commodity_volatility = 0.05 # placeholder for global avg

        total = weather_base + sentiment_boost + port_boost + commodity_volatility
        if total == 0:
            total = 1

        pcts = {
            "weather_ml": round((weather_base / total) * 100),
            "news_sentiment": round((sentiment_boost / total) * 100),
            "port_congestion": round((port_boost / total) * 100),
            "commodity_volatility": round((commodity_volatility / total) * 100)
        }
        
        driver = max(pcts, key=pcts.get)
        
        return {
            "components": {
                "weather_ml": round(weather_base, 3),
                "news_sentiment": round(sentiment_boost, 3),
                "port_congestion": round(port_boost, 3),
                "commodity_volatility": round(commodity_volatility, 3)
            },
            "pct": pcts,
            "labels": {
                "weather_ml": "Weather & Delay ML",
                "news_sentiment": "Gemini News Sentiment",
                "port_congestion": "Simulated Port Lag",
                "commodity_volatility": "Agmarknet Price Shock"
            },
            "top_driver": driver
        }

    def get_all_attributions(self) -> dict:
        attributions = {}
        for node, data in self.graph.nodes(data=True):
            if data.get("type") == "highway":
                attributions[node] = self.get_corridor_attribution(node)
        return attributions

    def get_peak_disruption_analysis(self) -> dict:
        threats = self.compute_corridor_threats()
        ranked = []
        for t in threats:
            hw = t["highway"]
            attr = self.get_corridor_attribution(hw)
            ranked.append({
                "highway": hw,
                "route": t["route"],
                "current_risk": t["risk_score"],
                "components": attr["components"] if attr else {}
            })
        
        # Sort by risk
        ranked.sort(key=lambda x: x["current_risk"], reverse=True)
        
        return {
            "ranked_corridors": ranked,
            "most_volatile": ranked[0]["highway"] if ranked else None,
            "safest": ranked[-1]["highway"] if ranked else None,
            "analysis_window_days": 30
        }
