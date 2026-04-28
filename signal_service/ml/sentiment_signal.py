import google.generativeai as genai
import os
import json
import requests
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Keywords that matter for Indian supply chains
THREAT_KEYWORDS = {
    "transport_strike": {
        "keywords": ["truck strike", "trucker strike", "transport bandh", 
                     "lorry strike", "chakka jam", "transport union"],
        "base_weight": 0.8,
        "affected_commodities": ["all"],
        "duration_days": 3,
    },
    "port_congestion": {
        "keywords": ["JNPT congestion", "port delay", "container backlog",
                     "customs delay", "port strike", "Mundra port"],
        "base_weight": 0.6,
        "affected_commodities": ["electronics", "auto_parts"],
        "duration_days": 5,
    },
    "highway_closure": {
        "keywords": ["highway blocked", "NH48 closed", "flood NH", 
                     "landslide highway", "road blocked", "highway accident"],
        "base_weight": 0.7,
        "affected_commodities": ["all"],
        "duration_days": 2,
    },
    "fuel_price_spike": {
        "keywords": ["diesel price hike", "petrol diesel", "fuel price increase",
                     "oil price surge"],
        "base_weight": 0.4,
        "affected_commodities": ["all"],
        "duration_days": 7,
    },
    "political_disruption": {
        "keywords": ["bandh", "rail roko", "bharat bandh", 
                     "protest highway", "agitation"],
        "base_weight": 0.65,
        "affected_commodities": ["all"],
        "duration_days": 1,
    },
    "monsoon_flooding": {
        "keywords": ["flood", "waterlogging", "inundated", "heavy rain alert",
                     "IMD warning", "cyclone warning", "red alert rain"],
        "base_weight": 0.75,
        "affected_commodities": ["agri", "textile"],
        "duration_days": 4,
    },
    "agri_crisis": {
        "keywords": ["crop damage", "mandi closed", "farmer protest",
                     "harvest loss", "agri disruption", "vegetable prices"],
        "base_weight": 0.55,
        "affected_commodities": ["agri"],
        "duration_days": 7,
    },
}

# Simulated real Indian news headlines
# In production: replace with NewsAPI, Google News RSS, or GDELT
SIMULATED_HEADLINES = [
    "Truck drivers in Maharashtra threaten indefinite strike over toll hike",
    "Heavy rainfall warning issued for Gujarat coast, NH48 traffic slowing",
    "JNPT customs officials report 30% container backlog due to IT system outage",
    "Diesel prices hiked by Rs 2 per litre across India effective midnight",
    "Farmer unions call for mandi bandh in Punjab and Haryana next week",
    "Cyclone warning: IMD issues red alert for Odisha and Andhra coast",
    "Transport union in Rajasthan suspends strike after government talks",
    "NH44 blocked near Nagpur due to massive multi-vehicle accident",
    "Mumbai port workers resume duty after 48-hour strike",
    "Tomato prices crash in Nashik mandi due to bumper harvest surplus",
    "Textile exporters warn of order cancellations due to yarn shortage",
    "Auto parts manufacturers face supply crunch as steel prices surge 18%",
    "Delhi-NCR highway projects cause major diversions on NH19 corridor",
    "Pharmaceutical distributors warn of medicine shortage in tier-2 cities",
    "E-commerce deliveries delayed in flood-hit districts of Kerala and Karnataka",
]


class SentimentSignalEngine:
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-2.0-flash-lite")
        self.active_signals = []
        self.signal_history = []

    def fetch_headlines(self):
        """
        Fetch real headlines using NewsAPI if available, fallback to Google News RSS,
        and finally fallback to simulated headlines if all else fails.
        """
        headlines = SIMULATED_HEADLINES.copy()
        
        news_api_key = os.getenv("NEWS_API_KEY")
        if news_api_key:
            try:
                url = f"https://newsapi.org/v2/everything?q=india+AND+(supply+chain+OR+logistics+OR+highway+OR+port+OR+strike)&sortBy=publishedAt&language=en&apiKey={news_api_key}"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    articles = response.json().get("articles", [])
                    newsapi_titles = [a["title"] for a in articles[:10] if a.get("title")]
                    if newsapi_titles:
                        print(f"[SentimentSignal] Fetched {len(newsapi_titles)} real headlines from NewsAPI")
                        return newsapi_titles + headlines
            except Exception as e:
                print(f"[SentimentSignal] NewsAPI fetch failed: {e}. Falling back to Google News...")

        # Fallback to Google News RSS (free, no key needed)
        try:
            rss_url = "https://news.google.com/rss/search?q=india+supply+chain+logistics+highway&hl=en-IN&gl=IN&ceid=IN:en"
            response = requests.get(rss_url, timeout=8)
            if response.status_code == 200:
                import re
                titles = re.findall(r'<title>(.*?)</title>', response.text)[2:12]
                titles = [t.replace('<![CDATA[', '').replace(']]>', '').strip() for t in titles]
                headlines = titles + headlines
                print(f"[SentimentSignal] Fetched {len(titles)} real headlines from Google News")
        except Exception as e:
            print(f"[SentimentSignal] Google News fetch failed: {e}. Using simulated headlines.")

        return headlines

    def analyze_with_gemini(self, headlines):
        """
        Use Gemini to analyze headlines for supply chain threat signals.
        Returns structured threat assessments.
        """
        headlines_text = "\n".join([f"{i+1}. {h}" for i, h in enumerate(headlines[:20])])

        prompt = f"""
You are a supply chain risk analyst for India. Analyze these news headlines and identify threats to Indian supply chains.

HEADLINES:
{headlines_text}

For each relevant threat found, respond with a JSON array. Each item must have:
- "headline": the original headline text (shortened)
- "threat_type": one of [transport_strike, port_congestion, highway_closure, fuel_price_spike, political_disruption, monsoon_flooding, agri_crisis, other]
- "severity": one of [HIGH, MEDIUM, LOW]
- "affected_corridors": list of highway IDs from [NH48, NH44, NH19, NH16, NH47, NH27] or ["ALL"]
- "affected_commodities": list from [agri, textile, pharma, auto_parts, electronics] or ["all"]
- "threat_score": float between 0.0 and 1.0
- "summary": one sentence explaining the supply chain impact in plain language
- "action": one sentence telling an SME what to do right now

Return ONLY a valid JSON array. No preamble, no markdown, no explanation.
If no supply chain threats found, return an empty array [].
"""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            # Clean any markdown fences
            text = text.replace("```json", "").replace("```", "").strip()
            signals = json.loads(text)
            print(f"[SentimentSignal] Gemini identified {len(signals)} threats from headlines")
            return signals
        except Exception as e:
            print(f"[SentimentSignal] Gemini analysis failed: {e}")
            return self._keyword_fallback(headlines)

    def _keyword_fallback(self, headlines):
        """
        Pure keyword matching fallback when Gemini is unavailable.
        Less intelligent but always works.
        """
        signals = []
        headlines_lower = " ".join(headlines).lower()

        for threat_type, config in THREAT_KEYWORDS.items():
            matched_keywords = [
                kw for kw in config["keywords"]
                if kw.lower() in headlines_lower
            ]
            if matched_keywords:
                signals.append({
                    "headline": f"Keyword match: {matched_keywords[0]}",
                    "threat_type": threat_type,
                    "severity": "MEDIUM",
                    "affected_corridors": ["ALL"],
                    "affected_commodities": config["affected_commodities"],
                    "threat_score": config["base_weight"] * 0.7,
                    "summary": f"Potential {threat_type.replace('_', ' ')} detected via keyword matching",
                    "action": "Monitor situation and consider alternative routes",
                })

        return signals

    def run_sentiment_scan(self):
        """
        Full pipeline: fetch headlines -> analyze -> return active signals
        """
        print(f"\n[SentimentSignal] Running sentiment scan -- {datetime.now().strftime('%H:%M:%S')}")

        headlines = self.fetch_headlines()
        print(f"[SentimentSignal] Analyzing {len(headlines)} headlines...")

        signals = self.analyze_with_gemini(headlines)

        # Store active signals with timestamp
        self.active_signals = []
        for signal in signals:
            enriched = {
                **signal,
                "detected_at": datetime.now().isoformat(),
                "signal_id": f"SIG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{signal.get('threat_type', 'UNK')[:3].upper()}",
            }
            self.active_signals.append(enriched)
            self.signal_history.append(enriched)

        return self.active_signals

    def get_corridor_sentiment_score(self, corridor_id):
        """
        Returns combined sentiment threat score for a specific corridor.
        Used by Signal Mesh to boost corridor risk scores.
        """
        if not self.active_signals:
            return 0.0

        corridor_signals = [
            s for s in self.active_signals
            if corridor_id in s.get("affected_corridors", [])
            or "ALL" in s.get("affected_corridors", [])
        ]

        if not corridor_signals:
            return 0.0

        # Weighted combination -- higher severity signals dominate
        severity_weights = {"HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.3}
        scores = [
            s["threat_score"] * severity_weights.get(s["severity"], 0.5)
            for s in corridor_signals
        ]

        # Don't just average -- take max with dampened sum
        combined = max(scores) * 0.7 + sum(scores) * 0.1
        return min(combined, 1.0)

    def get_commodity_sentiment_score(self, commodity):
        """
        Returns sentiment threat score for a specific commodity.
        """
        commodity_signals = [
            s for s in self.active_signals
            if commodity in s.get("affected_commodities", [])
            or "all" in s.get("affected_commodities", [])
        ]

        if not commodity_signals:
            return 0.0

        scores = [s["threat_score"] for s in commodity_signals]
        return min(max(scores) * 0.6 + np.mean(scores) * 0.4, 1.0) if scores else 0.0


if __name__ == "__main__":
    print("=" * 60)
    print("  SENTINELCHAIN -- Sentiment Signal Engine")
    print("=" * 60)

    engine = SentimentSignalEngine()
    signals = engine.run_sentiment_scan()

    print(f"\n[Results] {len(signals)} active threat signals detected\n")
    print("-" * 60)

    for s in signals:
        severity_icon = {"HIGH": "[!!!]", "MEDIUM": "[!!]", "LOW": "[!]"}.get(s["severity"], "[?]")
        print(f"\n{severity_icon} [{s['threat_type'].upper()}] -- Score: {s['threat_score']:.2f}")
        print(f"   Headline  : {s['headline']}")
        print(f"   Summary   : {s['summary']}")
        print(f"   Action    : {s['action']}")
        print(f"   Corridors : {s['affected_corridors']}")
        print(f"   Commodities: {s['affected_commodities']}")

    print("\n" + "-" * 60)
    print("\n[Corridor Sentiment Scores]")
    for corridor in ["NH48", "NH44", "NH47", "NH19", "NH16", "NH27"]:
        score = engine.get_corridor_sentiment_score(corridor)
        bar = "#" * int(score * 20)
        print(f"  {corridor}: {bar} {score:.3f}")

    print("\n[Commodity Sentiment Scores]")
    for commodity in ["agri", "textile", "pharma", "auto_parts", "electronics"]:
        score = engine.get_commodity_sentiment_score(commodity)
        bar = "#" * int(score * 20)
        print(f"  {commodity:<12}: {bar} {score:.3f}")
