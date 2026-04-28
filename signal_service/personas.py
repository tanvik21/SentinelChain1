from datetime import datetime

# Archetype definitions — India's core SME supply chain personas
ARCHETYPES = {
    "textile_north": {
        "label": "Textile Manufacturer — North India",
        "key_corridors": ["NH48", "NH27", "NH19"],
        "key_suppliers_in": ["Surat", "Ahmedabad", "Ludhiana"],
        "commodity": "textile",
        "peak_months": [10, 11, 12, 1],  # Oct-Jan festive + winter
        "lead_time_days": 5,
        "loss_per_delay_inr": 80000,
        "risk_tolerance": "low",
    },
    "pharma_west": {
        "label": "Pharma Distributor — West India",
        "key_corridors": ["NH48", "NH47"],
        "key_suppliers_in": ["Mumbai", "Pune", "Ahmedabad"],
        "commodity": "pharma",
        "peak_months": [6, 7, 8, 9],  # Monsoon = illness spike
        "lead_time_days": 3,
        "loss_per_delay_inr": 150000,
        "risk_tolerance": "very_low",
    },
    "agri_south": {
        "label": "Agri Cooperative — South India",
        "key_corridors": ["NH44", "NH16", "NH47"],
        "key_suppliers_in": ["Bangalore", "Chennai", "Hyderabad"],
        "commodity": "agri",
        "peak_months": [3, 4, 5, 10, 11],  # Harvest seasons
        "lead_time_days": 2,
        "loss_per_delay_inr": 40000,
        "risk_tolerance": "medium",
    },
    "auto_central": {
        "label": "Auto Parts Manufacturer — Central India",
        "key_corridors": ["NH44", "NH27", "NH19"],
        "key_suppliers_in": ["Nagpur", "Pune", "Chennai"],
        "commodity": "auto_parts",
        "peak_months": [1, 2, 3, 7, 8],
        "lead_time_days": 7,
        "loss_per_delay_inr": 200000,
        "risk_tolerance": "medium",
    },
    "ecommerce_east": {
        "label": "E-commerce Seller — East India",
        "key_corridors": ["NH19", "NH16"],
        "key_suppliers_in": ["Kolkata", "Patna"],
        "commodity": "electronics",
        "peak_months": [10, 11, 12],  # Festive season
        "lead_time_days": 4,
        "loss_per_delay_inr": 30000,
        "risk_tolerance": "high",
    },
}


class PersonaEngine:
    def __init__(self):
        # In production this comes from database
        # For hackathon — seeded demo users
        self.users = {
            "U001": {
                "name": "Arjun Mehta",
                "business": "Mehta Garments Pvt Ltd",
                "location": "Ludhiana",
                "archetype": "textile_north",
                "language": "hindi",
                "alert_channel": "whatsapp",
                "phone": "+91-98765-43210",
                "active_shipments": [
                    {
                        "id": "SH001",
                        "from": "Surat",
                        "to": "Ludhiana",
                        "via": "NH48",
                        "commodity": "textile",
                        "expected_arrival": "2026-04-21",
                        "value_inr": 320000
                    }
                ],
                "feedback_history": [],
                "alerts_sent": 0,
                "alerts_acted": 0,
            },
            "U002": {
                "name": "Meena Kulkarni",
                "business": "Kulkarni Medical Stores",
                "location": "Dharwad",
                "archetype": "pharma_west",
                "language": "kannada",
                "alert_channel": "sms",
                "phone": "+91-87654-32109",
                "active_shipments": [
                    {
                        "id": "SH002",
                        "from": "Pune",
                        "to": "Dharwad",
                        "via": "NH47",
                        "commodity": "pharma",
                        "expected_arrival": "2026-04-20",
                        "value_inr": 85000
                    }
                ],
                "feedback_history": [],
                "alerts_sent": 0,
                "alerts_acted": 0,
            },
            "U003": {
                "name": "Ravi Patil",
                "business": "Patil Agri Cooperative",
                "location": "Nashik",
                "archetype": "agri_south",
                "language": "marathi",
                "alert_channel": "sms",
                "phone": "+91-76543-21098",
                "active_shipments": [
                    {
                        "id": "SH003",
                        "from": "Nashik",
                        "to": "Pune",
                        "via": "NH47",
                        "commodity": "agri",
                        "expected_arrival": "2026-04-20",
                        "value_inr": 48000
                    }
                ],
                "feedback_history": [],
                "alerts_sent": 0,
                "alerts_acted": 0,
            },
        }

    def get_affected_users(self, threats):
        """
        Given a list of threats from SignalMesh,
        return which users are actually affected and how severely
        """
        affected = []

        for threat in threats:
            highway = threat["highway"]
            risk_score = threat["risk_score"]

            for user_id, user in self.users.items():
                archetype = ARCHETYPES[user["archetype"]]

                # Check if this highway is in user's key corridors
                if highway not in archetype["key_corridors"]:
                    continue

                # Check if user has active shipment on this highway
                shipment_at_risk = None
                for shipment in user.get("active_shipments", []):
                    if shipment["via"] == highway:
                        shipment_at_risk = shipment
                        break

                if not shipment_at_risk:
                    continue

                # Compute personalized impact
                loss_potential = archetype["loss_per_delay_inr"]
                is_peak_month = datetime.now().month in archetype["peak_months"]
                peak_multiplier = 1.5 if is_peak_month else 1.0

                # Counterfactual cost of silence
                # How bad is it if we DON'T warn this user?
                counterfactual_cost = (
                    risk_score *
                    loss_potential *
                    peak_multiplier
                )

                # Dynamic alert threshold based on risk tolerance
                thresholds = {
                    "very_low": 0.25,
                    "low": 0.35,
                    "medium": 0.45,
                    "high": 0.55,
                }
                threshold = thresholds[archetype["risk_tolerance"]]

                # Fire alert only if risk exceeds personal threshold
                if risk_score >= threshold:
                    affected.append({
                        "user_id": user_id,
                        "user": user,
                        "archetype": archetype,
                        "threat": threat,
                        "shipment_at_risk": shipment_at_risk,
                        "counterfactual_cost_inr": counterfactual_cost,
                        "should_alert": True,
                    })

        # Sort by counterfactual cost — most critical first
        affected.sort(key=lambda x: x["counterfactual_cost_inr"], reverse=True)
        return affected

    def record_feedback(self, user_id, alert_id, action):
        """
        Record whether user acted on the alert
        action: 'acted' | 'ignored' | 'already_knew'
        """
        if user_id in self.users:
            self.users[user_id]["feedback_history"].append({
                "alert_id": alert_id,
                "action": action,
                "timestamp": datetime.now().isoformat()
            })
            if action == "acted":
                self.users[user_id]["alerts_acted"] += 1

    def get_user_trust_score(self, user_id):
        """
        How much does this user trust our alerts?
        Based on historical act rate
        """
        user = self.users.get(user_id, {})
        sent = user.get("alerts_sent", 0)
        acted = user.get("alerts_acted", 0)
        if sent == 0:
            return 1.0  # New user — full trust assumed
        return acted / sent


if __name__ == "__main__":
    # Test with a mock threat
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

    print(f"\n[PersonaEngine] {len(affected)} users affected\n")
    for a in affected:
        print(f"👤 {a['user']['name']} — {a['user']['business']}")
        print(f"   Threat    : {a['threat']['highway']} ({a['threat']['severity']})")
        print(f"   Shipment  : {a['shipment_at_risk']['from']} → {a['shipment_at_risk']['to']}")
        print(f"   Cost if silent : ₹{a['counterfactual_cost_inr']:,.0f}")
        print(f"   Alert channel  : {a['user']['alert_channel']}")
        print()
