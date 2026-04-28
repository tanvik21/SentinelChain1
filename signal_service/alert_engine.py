import google.generativeai as genai
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

LANGUAGE_CONFIGS = {
    "hindi": {
        "name": "Hindi",
        "action_word": "अभी करें",
        "safe_word": "सुरक्षित",
    },
    "kannada": {
        "name": "Kannada", 
        "action_word": "ಈಗಲೇ ಮಾಡಿ",
        "safe_word": "ಸುರಕ್ಷಿತ",
    },
    "marathi": {
        "name": "Marathi",
        "action_word": "आत्ता करा",
        "safe_word": "सुरक्षित",
    },
    "english": {
        "name": "English",
        "action_word": "Act now",
        "safe_word": "safe",
    },
}

ALTERNATE_SUPPLIERS = {
    "Surat": [
        {"name": "Ahmedabad Textile Hub", "contact": "079-2630-1234"},
        {"name": "Rajkot Fabric Mills", "contact": "0281-2480-567"},
    ],
    "Pune": [
        {"name": "Mumbai Pharma Distributors", "contact": "022-2617-8900"},
        {"name": "Nashik MedSupply", "contact": "0253-2310-456"},
    ],
    "Nashik": [
        {"name": "Pune Agri Markets", "contact": "020-2445-6789"},
        {"name": "Sangamner Farmers Hub", "contact": "02425-222-345"},
    ],
}


class AlertEngine:
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-2.0-flash-lite")
        self.alerts_generated = []

    def _build_prompt(self, affected_user):
        user = affected_user["user"]
        threat = affected_user["threat"]
        shipment = affected_user["shipment_at_risk"]
        archetype = affected_user["archetype"]
        language = user["language"]
        lang_config = LANGUAGE_CONFIGS.get(language, LANGUAGE_CONFIGS["english"])

        # Find alternate suppliers
        supplier_city = shipment["from"]
        alternates = ALTERNATE_SUPPLIERS.get(supplier_city, [])
        alternate_text = ""
        if alternates:
            alt = alternates[0]
            alternate_text = f"Alternate supplier: {alt['name']}, contact {alt['contact']}"

        prompt = f"""
You are SentinelChain — an AI supply chain guardian for Indian SME businesses.

Write an alert message for {user['name']} who runs {user['business']} in {user['location']}.

SITUATION:
- Highway {threat['highway']} ({threat['route']}) has a risk score of {threat['risk_score']:.0%}
- Severity: {threat['severity']}
- Their shipment of {shipment['commodity']} from {shipment['from']} to {shipment['to']} is at risk
- Shipment value: ₹{shipment['value_inr']:,}
- Expected arrival: {shipment['expected_arrival']}
- If delayed, estimated loss: ₹{affected_user['counterfactual_cost_inr']:,.0f}
- {alternate_text}

STRICT RULES:
1. Write ONLY in {lang_config['name']} language
2. EXACTLY 2 sentences — no more, no less
3. Sentence 1: What will happen and when (specific, concrete)
4. Sentence 2: One single action they must take right now
5. Use simple words — Class 8 education level
6. Never use technical jargon like "risk score" or "corridor"
7. Sound like a trusted friend warning them, not a system notification
8. Include the alternate supplier contact if provided
9. End with the word "{lang_config['action_word']}"

Write the alert now:
"""
        return prompt

    def generate_alert(self, affected_user):
        user = affected_user["user"]
        threat = affected_user["threat"]
        shipment = affected_user["shipment_at_risk"]

        try:
            prompt = self._build_prompt(affected_user)
            response = self.model.generate_content(prompt)
            alert_text = response.text.strip()

            # Also generate English version for dashboard
            english_prompt = self._build_prompt({
                **affected_user,
                "user": {**user, "language": "english"}
            })
            english_response = self.model.generate_content(english_prompt)
            english_text = english_response.text.strip()

            alert = {
                "alert_id": f"ALT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{user['name'][:3].upper()}",
                "user_id": affected_user["user_id"],
                "user_name": user["name"],
                "business": user["business"],
                "channel": user["alert_channel"],
                "language": user["language"],
                "alert_text": alert_text,
                "alert_text_english": english_text,
                "highway": threat["highway"],
                "severity": threat["severity"],
                "risk_score": threat["risk_score"],
                "shipment": shipment,
                "counterfactual_cost_inr": affected_user["counterfactual_cost_inr"],
                "generated_at": datetime.now().isoformat(),
                "status": "generated",
            }

            self.alerts_generated.append(alert)
            return alert

        except Exception as e:
            language = user.get("language", "english")
            print(f"[AlertEngine] Failed for {user['name']}: {e}")
            print(f"[AlertEngine] Using fallback mock generation for {user['name']} due to API error.")
            
            # Fallback mock text generator if API is exhausted
            if language == "hindi":
                alert_text = f"चेतावनी: {threat['route']} पर मौसम खराब है, आपकी {shipment['commodity']} डिलीवरी प्रभावित हो सकती है। कृपया अपने ड्राइवर से अभी संपर्क करें और उन्हें सुरक्षित रहने के लिए कहें।"
            elif language == "kannada":
                alert_text = f"ಎಚ್ಚರಿಕೆ: {threat['route']} ನಲ್ಲಿ ಹವಾಮಾನ ಹದಗೆಟ್ಟಿದೆ, ನಿಮ್ಮ {shipment['commodity']} ಸಾಗಣೆ ವಿಳಂಬವಾಗಬಹುದು. ದಯವಿಟ್ಟು ಈಗಲೇ ಪರ್ಯಾಯ ಮಾರ್ಗವನ್ನು ಪರಿಶೀಲಿಸಿ."
            elif language == "marathi":
                alert_text = f"इशारा: {threat['route']} वर हवामान खराब आहे. तुमचे {shipment['commodity']} नुकसान होण्यापासून वाचवण्यासाठी कृपया त्वरित कारवाई करा."
            else:
                alert_text = f"Warning: High risk on {threat['route']} due to weather. Act now to protect your {shipment['commodity']}."
                
            english_text = f"Warning: High risk on {threat['route']} due to weather. Act now to protect your {shipment['commodity']}."
            
            alert = {
                "alert_id": f"ALT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{user['name'][:3].upper()}",
                "user_id": affected_user["user_id"],
                "user_name": user["name"],
                "business": user["business"],
                "channel": user["alert_channel"],
                "language": user["language"],
                "alert_text": alert_text,
                "alert_text_english": english_text,
                "highway": threat["highway"],
                "severity": threat["severity"],
                "risk_score": threat["risk_score"],
                "shipment": shipment,
                "counterfactual_cost_inr": affected_user["counterfactual_cost_inr"],
                "generated_at": datetime.now().isoformat(),
                "status": "generated_mock",
            }
            
            self.alerts_generated.append(alert)
            return alert

    def generate_all_alerts(self, affected_users):
        print(f"\n[AlertEngine] Generating alerts for {len(affected_users)} users...\n")
        alerts = []
        for affected in affected_users:
            alert = self.generate_alert(affected)
            if alert:
                alerts.append(alert)
                print(f"[AlertEngine] Alert generated for {alert['user_name']}")
                print(f"   ID       : {alert['alert_id']}")
                print(f"   Channel  : {alert['channel'].upper()}")
                print(f"   Language : {alert['language']}")
                print(f"   Severity : {alert['severity']}")
                print(f"\n   --- MESSAGE ({alert['language'].upper()}) ---")
                print(f"   {alert['alert_text']}")
                print(f"\n   --- MESSAGE (ENGLISH) ---")
                print(f"   {alert['alert_text_english']}")
                print(f"\n   Cost of silence : ₹{alert['counterfactual_cost_inr']:,.0f}")
                print("-" * 60)

        return alerts


if __name__ == "__main__":
    # Test with mock affected users
    from personas import PersonaEngine
    from datetime import datetime

    engine = PersonaEngine()

    mock_threats = [
        {
            "highway": "NH48",
            "route": "Mumbai-Delhi",
            "risk_score": 0.72,
            "affected_cities": ["Surat", "Ahmedabad"],
            "severity": "HIGH",
            "detected_at": datetime.now().isoformat()
        },
        {
            "highway": "NH47",
            "route": "Pune-Bangalore",
            "risk_score": 0.45,
            "affected_cities": ["Kolhapur", "Hubli"],
            "severity": "MEDIUM",
            "detected_at": datetime.now().isoformat()
        }
    ]

    affected = engine.get_affected_users(mock_threats)
    alert_engine = AlertEngine()
    alerts = alert_engine.generate_all_alerts(affected)

    print(f"\n[AlertEngine] {len(alerts)} alerts ready for delivery")
