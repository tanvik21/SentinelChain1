import sqlite3
import os

DB_PATH = "c:/Users/nawaz/OneDrive/Desktop/Senitalchain/sentinelchain/signal_service/sentinelchain.db"

def check_db():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    print("Users in database:")
    rows = c.execute("SELECT id, name, email, role FROM users").fetchall()
    for row in rows:
        print(dict(row))
    
    conn.close()

if __name__ == "__main__":
    check_db()
