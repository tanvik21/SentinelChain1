"""
SentinelChain — Delivery Service
Channel-agnostic alert router:
  - WhatsApp: webhook-ready (simulated when WHATSAPP_TOKEN not set)
  - SMS: MSG91 / Twilio (simulated when keys not set)
  - App Push: in-app notification log (always works)
  - Missed-call feedback: stub for IVR integration

Architecture is channel-agnostic — swap any channel without touching intelligence layer.
"""
import os
import json
import requests
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
MSG91_KEY = os.getenv("MSG91_KEY", "")
TWILIO_SID = os.getenv("TWILIO_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN", "")
TWILIO_FROM = os.getenv("TWILIO_FROM", "")

DELIVERY_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "delivery_log.json")


def _load_delivery_log() -> List[Dict]:
    os.makedirs(os.path.dirname(DELIVERY_LOG_PATH), exist_ok=True)
    if not os.path.exists(DELIVERY_LOG_PATH):
        return []
    with open(DELIVERY_LOG_PATH, "r") as f:
        return json.load(f)


def _save_delivery_log(log: List[Dict]):
    with open(DELIVERY_LOG_PATH, "w") as f:
        json.dump(log[-500:], f, indent=2)  # keep last 500 deliveries


def _log_delivery(entry: Dict):
    log = _load_delivery_log()
    log.append(entry)
    _save_delivery_log(log)


class WhatsAppDelivery:
    """
    WhatsApp Business Cloud API delivery.
    Falls back to simulation log when credentials not set.
    """

    def send(self, phone: str, message: str, alert_id: str) -> Dict:
        if WHATSAPP_TOKEN and WHATSAPP_PHONE_ID:
            return self._send_live(phone, message, alert_id)
        else:
            return self._simulate(phone, message, alert_id)

    def _send_live(self, phone: str, message: str, alert_id: str) -> Dict:
        url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": phone.replace("+", "").replace("-", ""),
            "type": "text",
            "text": {"body": f"⬡ SentinelChain Alert\n\n{message}\n\n_Reply ACTED / IGNORED / KNEW_"},
        }
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=10)
            data = r.json()
            success = r.status_code == 200
            return {
                "channel": "whatsapp",
                "status": "sent" if success else "failed",
                "message_id": data.get("messages", [{}])[0].get("id", ""),
                "phone": phone,
                "alert_id": alert_id,
                "mode": "live",
                "delivered_at": datetime.now().isoformat(),
            }
        except Exception as e:
            return {"channel": "whatsapp", "status": "error", "error": str(e), "mode": "live"}

    def _simulate(self, phone: str, message: str, alert_id: str) -> Dict:
        entry = {
            "channel": "whatsapp",
            "status": "simulated",
            "phone": phone,
            "alert_id": alert_id,
            "preview": message[:120] + "..." if len(message) > 120 else message,
            "mode": "simulation",
            "delivered_at": datetime.now().isoformat(),
            "note": "Set WHATSAPP_TOKEN + WHATSAPP_PHONE_ID env vars to go live",
        }
        _log_delivery(entry)
        print(f"  [WhatsApp:SIM] → {phone} | {message[:60]}...")
        return entry


class SMSDelivery:
    """
    SMS delivery via MSG91 (India-preferred) or Twilio fallback.
    Simulates when credentials not set.
    """

    def send(self, phone: str, message: str, alert_id: str) -> Dict:
        if MSG91_KEY:
            return self._send_msg91(phone, message, alert_id)
        elif TWILIO_SID and TWILIO_TOKEN:
            return self._send_twilio(phone, message, alert_id)
        else:
            return self._simulate(phone, message, alert_id)

    def _send_msg91(self, phone: str, message: str, alert_id: str) -> Dict:
        url = "https://api.msg91.com/api/v5/flow/"
        payload = {
            "template_id": os.getenv("MSG91_TEMPLATE_ID", ""),
            "sender": "SNTLCH",
            "short_url": "0",
            "mobiles": phone.replace("+", "").replace("-", ""),
            "VAR1": message[:140],
        }
        headers = {"authkey": MSG91_KEY, "Content-Type": "application/json"}
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=8)
            return {
                "channel": "sms",
                "status": "sent" if r.status_code == 200 else "failed",
                "phone": phone,
                "alert_id": alert_id,
                "mode": "msg91-live",
                "delivered_at": datetime.now().isoformat(),
            }
        except Exception as e:
            return {"channel": "sms", "status": "error", "error": str(e)}

    def _send_twilio(self, phone: str, message: str, alert_id: str) -> Dict:
        try:
            from twilio.rest import Client
            client = Client(TWILIO_SID, TWILIO_TOKEN)
            msg = client.messages.create(body=message[:160], from_=TWILIO_FROM, to=phone)
            return {
                "channel": "sms",
                "status": "sent",
                "sid": msg.sid,
                "phone": phone,
                "alert_id": alert_id,
                "mode": "twilio-live",
                "delivered_at": datetime.now().isoformat(),
            }
        except Exception as e:
            return {"channel": "sms", "status": "error", "error": str(e)}

    def _simulate(self, phone: str, message: str, alert_id: str) -> Dict:
        entry = {
            "channel": "sms",
            "status": "simulated",
            "phone": phone,
            "alert_id": alert_id,
            "preview": message[:140],
            "mode": "simulation",
            "delivered_at": datetime.now().isoformat(),
            "note": "Set MSG91_KEY or TWILIO_SID/TWILIO_TOKEN env vars to go live",
        }
        _log_delivery(entry)
        print(f"  [SMS:SIM] → {phone} | {message[:60]}...")
        return entry


class AppPushDelivery:
    """
    In-app notification — always works, no external dependency.
    Writes to delivery log; frontend polls /delivery-log endpoint.
    """

    def send(self, user_id: str, message: str, alert_id: str, alert_data: Dict) -> Dict:
        entry = {
            "channel": "app",
            "status": "delivered",
            "user_id": user_id,
            "alert_id": alert_id,
            "message": message,
            "alert_data": alert_data,
            "read": False,
            "delivered_at": datetime.now().isoformat(),
        }
        _log_delivery(entry)
        return entry


class ChannelRouter:
    """
    Routes each alert to the correct delivery channel based on user preference.
    Always delivers to app push regardless of primary channel (redundancy).
    """

    def __init__(self):
        self.whatsapp = WhatsAppDelivery()
        self.sms = SMSDelivery()
        self.app_push = AppPushDelivery()
        self.delivery_results = []

    def route(self, alert: Dict, user: Dict) -> Dict:
        """
        Route a single alert to the user's preferred channel.
        Always logs to app push as secondary channel.
        """
        channel = user.get("alert_channel", "app")
        phone = user.get("phone", "")
        user_id = user.get("id", user.get("user_id", ""))
        message = alert.get("alert_text", alert.get("alert_text_english", ""))
        alert_id = alert.get("alert_id", "")

        results = []

        # Primary channel
        if channel == "whatsapp" and phone:
            result = self.whatsapp.send(phone, message, alert_id)
            results.append(result)
        elif channel == "sms" and phone:
            result = self.sms.send(phone, message, alert_id)
            results.append(result)

        # Always send app push (secondary/redundant)
        app_result = self.app_push.send(user_id, message, alert_id, alert)
        results.append(app_result)

        delivery_record = {
            "alert_id": alert_id,
            "user_id": user_id,
            "primary_channel": channel,
            "delivery_results": results,
            "all_delivered": all(r["status"] in ["sent", "delivered", "simulated"] for r in results),
            "routed_at": datetime.now().isoformat(),
        }

        self.delivery_results.append(delivery_record)
        return delivery_record

    def route_all(self, alerts: List[Dict], users_by_id: Dict) -> List[Dict]:
        """Route a batch of alerts."""
        records = []
        for alert in alerts:
            user_id = alert.get("user_id")
            user = users_by_id.get(user_id)
            if user:
                record = self.route(alert, user)
                records.append(record)
        print(f"[ChannelRouter] Routed {len(records)} alerts")
        return records

    def get_delivery_log(self, limit: int = 50) -> List[Dict]:
        log = _load_delivery_log()
        return log[-limit:]

    def get_unread_notifications(self, user_id: str) -> List[Dict]:
        log = _load_delivery_log()
        return [
            entry for entry in log
            if entry.get("channel") == "app"
            and entry.get("user_id") == user_id
            and not entry.get("read", False)
        ]

    def mark_read(self, alert_id: str, user_id: str):
        log = _load_delivery_log()
        for entry in log:
            if entry.get("alert_id") == alert_id and entry.get("user_id") == user_id:
                entry["read"] = True
        _save_delivery_log(log)


# Singleton
_router = None

def get_channel_router() -> ChannelRouter:
    global _router
    if _router is None:
        _router = ChannelRouter()
    return _router
