"""
SentinelChain — SQLite User Database
Replaces the flat users_db.json with a proper relational store.
Zero extra dependencies — uses Python's built-in sqlite3.
"""
import sqlite3
import json
import os
from datetime import datetime
import bcrypt

DB_PATH = os.path.join(os.path.dirname(__file__), "sentinelchain.db")

def hash_password_demo(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and seed demo users on first run."""
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            business_name TEXT,
            business_type TEXT,
            location TEXT,
            language TEXT DEFAULT 'english',
            alert_channel TEXT DEFAULT 'app',
            phone TEXT,
            suppliers TEXT DEFAULT '[]',
            highways TEXT DEFAULT '[]',
            active_shipments TEXT DEFAULT '[]',
            role TEXT DEFAULT 'user',
            created_at TEXT,
            alerts_received INTEGER DEFAULT 0,
            alerts_acted INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS alert_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id TEXT,
            user_id TEXT,
            highway TEXT,
            severity TEXT,
            language TEXT,
            alert_text TEXT,
            counterfactual_cost_inr REAL,
            action TEXT DEFAULT 'pending',
            created_at TEXT,
            acted_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS cycle_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT,
            threats_detected INTEGER,
            users_affected INTEGER,
            alerts_generated INTEGER,
            threat_level TEXT,
            max_corridor_risk REAL,
            created_at TEXT
        )
    """)

    # Seed demo users only if table is empty
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        demo_users = [
            {
                "id": "U001",
                "name": "Arjun Mehta",
                "email": "arjun@mehtagarments.com",
                "hashed_password": hash_password_demo("demo123"),
                "business_name": "Mehta Garments Pvt Ltd",
                "business_type": "textile_north",
                "location": "Ludhiana",
                "language": "hindi",
                "alert_channel": "whatsapp",
                "phone": "+91-98765-43210",
                "suppliers": json.dumps(["Surat", "Ahmedabad"]),
                "highways": json.dumps(["NH48"]),
                "active_shipments": json.dumps([
                    {"id": "SH001", "from": "Surat", "to": "Ludhiana",
                     "via": "NH48", "commodity": "textile",
                     "expected_arrival": "2026-05-10", "value_inr": 320000}
                ]),
                "role": "user",
            },
            {
                "id": "U002",
                "name": "Meena Kulkarni",
                "email": "meena@kulkarnimedical.com",
                "hashed_password": hash_password_demo("demo123"),
                "business_name": "Kulkarni Medical Stores",
                "business_type": "pharma_west",
                "location": "Dharwad",
                "language": "kannada",
                "alert_channel": "sms",
                "phone": "+91-87654-32109",
                "suppliers": json.dumps(["Pune", "Mumbai"]),
                "highways": json.dumps(["NH47"]),
                "active_shipments": json.dumps([
                    {"id": "SH002", "from": "Pune", "to": "Dharwad",
                     "via": "NH47", "commodity": "pharma",
                     "expected_arrival": "2026-05-08", "value_inr": 85000}
                ]),
                "role": "user",
            },
            {
                "id": "U003",
                "name": "Ravi Patil",
                "email": "ravi@patilcooperative.com",
                "hashed_password": hash_password_demo("demo123"),
                "business_name": "Patil Agri Cooperative",
                "business_type": "agri_south",
                "location": "Nashik",
                "language": "marathi",
                "alert_channel": "sms",
                "phone": "+91-76543-21098",
                "suppliers": json.dumps(["Nashik", "Pune"]),
                "highways": json.dumps(["NH47"]),
                "active_shipments": json.dumps([
                    {"id": "SH003", "from": "Nashik", "to": "Pune",
                     "via": "NH47", "commodity": "agri",
                     "expected_arrival": "2026-05-06", "value_inr": 48000}
                ]),
                "role": "user",
            },
            {
                "id": "ADMIN",
                "name": "SentinelChain Admin",
                "email": "admin@sentinelchain.in",
                "hashed_password": hash_password_demo("admin2026"),
                "business_name": "SentinelChain",
                "business_type": "admin",
                "location": "Bangalore",
                "language": "english",
                "alert_channel": "app",
                "phone": "+91-00000-00000",
                "suppliers": json.dumps([]),
                "highways": json.dumps([]),
                "active_shipments": json.dumps([]),
                "role": "admin",
            },
        ]
        for u in demo_users:
            c.execute("""
                INSERT INTO users (id, name, email, hashed_password, business_name,
                    business_type, location, language, alert_channel, phone,
                    suppliers, highways, active_shipments, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                u["id"], u["name"], u["email"], u["hashed_password"],
                u["business_name"], u["business_type"], u["location"],
                u["language"], u["alert_channel"], u["phone"],
                u["suppliers"], u["highways"], u["active_shipments"],
                u["role"], datetime.now().isoformat()
            ))

    conn.commit()
    conn.close()
    print("[DB] SQLite database initialized.")


def row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    for field in ["suppliers", "highways", "active_shipments"]:
        if field in d and isinstance(d[field], str):
            try:
                d[field] = json.loads(d[field])
            except Exception:
                d[field] = []
    return d


def get_user_by_email(email: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row_to_dict(row)


def get_user_by_id(user_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row_to_dict(row)


def create_user(data: dict) -> dict:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    user_id = f"U{count + 1:03d}"

    c.execute("""
        INSERT INTO users (id, name, email, hashed_password, business_name,
            business_type, location, language, alert_channel, phone,
            suppliers, highways, active_shipments, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, data["name"], data["email"], data["hashed_password"],
        data["business_name"], data["business_type"], data["location"],
        data["language"], data["alert_channel"], data["phone"],
        json.dumps(data.get("suppliers", [])),
        json.dumps(data.get("highways", [])),
        json.dumps([]),
        "user", datetime.now().isoformat()
    ))
    conn.commit()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row_to_dict(row)


def get_all_users():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


def log_alert(alert: dict):
    conn = get_conn()
    conn.execute("""
        INSERT INTO alert_logs
            (alert_id, user_id, highway, severity, language, alert_text,
             counterfactual_cost_inr, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        alert.get("alert_id"), alert.get("user_id"),
        alert.get("highway"), alert.get("severity"),
        alert.get("language"), alert.get("alert_text"),
        alert.get("counterfactual_cost_inr"),
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()


def record_feedback(user_id: str, alert_id: str, action: str):
    conn = get_conn()
    conn.execute("""
        UPDATE alert_logs SET action = ?, acted_at = ?
        WHERE alert_id = ? AND user_id = ?
    """, (action, datetime.now().isoformat(), alert_id, user_id))
    if action == "acted":
        conn.execute(
            "UPDATE users SET alerts_acted = alerts_acted + 1 WHERE id = ?",
            (user_id,)
        )
    conn.execute(
        "UPDATE users SET alerts_received = alerts_received + 1 WHERE id = ?",
        (user_id,)
    )
    conn.commit()
    conn.close()


def get_user_trust_score(user_id: str) -> float:
    conn = get_conn()
    row = conn.execute(
        "SELECT alerts_received, alerts_acted FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    if not row or row["alerts_received"] == 0:
        return 1.0
    return round(row["alerts_acted"] / row["alerts_received"], 3)


def log_cycle(cycle: dict):
    conn = get_conn()
    conn.execute("""
        INSERT INTO cycle_history
            (cycle_id, threats_detected, users_affected, alerts_generated,
             threat_level, max_corridor_risk, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        cycle.get("cycle_id"), cycle.get("threats_detected", 0),
        cycle.get("users_affected", 0), cycle.get("alerts_generated", 0),
        cycle.get("threat_level", "NORMAL"),
        cycle.get("max_corridor_risk", 0.0),
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()


def get_cycle_history(limit: int = 20):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM cycle_history ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialize on import
init_db()
