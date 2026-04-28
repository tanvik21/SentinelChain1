import json
import time
from datetime import datetime
from signal_mesh import SignalMesh
from personas import PersonaEngine
from alert_engine import AlertEngine


class SentinelChain:
    def __init__(self):
        print("\n" + "="*60)
        print("   SENTINELCHAIN — Supply Chain Guardian for India")
        print("   Initializing systems...")
        print("="*60)

        self.signal_mesh = SignalMesh()
        self.persona_engine = PersonaEngine()
        self.alert_engine = AlertEngine()
        self.run_history = []

        print("[SentinelChain] All systems online.\n")

    def run_cycle(self):
        cycle_start = datetime.now()
        print(f"\n{'='*60}")
        print(f"  CYCLE START — {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        # Step 1 — Update Signal Mesh
        print("\n[1/4] Scanning India's supply chain signals...")
        threats = self.signal_mesh.run_full_update()
        print(f"      {len(threats)} threats detected in signal mesh")

        if not threats:
            print("\n✅ All corridors clear. No alerts needed.")
            return []

        # Step 2 — Find affected users
        print("\n[2/4] Identifying affected businesses...")
        affected_users = self.persona_engine.get_affected_users(threats)
        print(f"      {len(affected_users)} businesses at risk")

        if not affected_users:
            print("\n✅ No active shipments affected. No alerts needed.")
            return []

        # Step 3 — Generate vernacular alerts
        print("\n[3/4] Generating personalized alerts...")
        alerts = self.alert_engine.generate_all_alerts(affected_users)
        print(f"      {len(alerts)} alerts generated")

        # Step 4 — Log cycle
        print("\n[4/4] Logging cycle results...")
        cycle_result = {
            "cycle_id": f"CYC-{cycle_start.strftime('%Y%m%d%H%M%S')}",
            "timestamp": cycle_start.isoformat(),
            "threats_detected": len(threats),
            "users_affected": len(affected_users),
            "alerts_generated": len(alerts),
            "alerts": alerts,
            "graph_summary": self.signal_mesh.get_graph_summary(),
        }
        self.run_history.append(cycle_result)

        # Save to file for frontend to read
        with open("../data/latest_cycle.json", "w", encoding="utf-8") as f:
            json.dump(cycle_result, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*60}")
        print(f"  CYCLE COMPLETE")
        print(f"  Threats detected : {len(threats)}")
        print(f"  Businesses warned: {len(affected_users)}")
        print(f"  Alerts delivered : {len(alerts)}")
        print(f"  Cycle duration   : {(datetime.now() - cycle_start).seconds}s")
        print(f"{'='*60}\n")

        return alerts

    def get_status(self):
        return {
            "status": "online",
            "total_cycles": len(self.run_history),
            "last_cycle": self.run_history[-1] if self.run_history else None,
            "graph_summary": self.signal_mesh.get_graph_summary(),
            "users_monitored": len(self.persona_engine.users),
        }


if __name__ == "__main__":
    import os
    os.makedirs("../data", exist_ok=True)

    sentinel = SentinelChain()
    alerts = sentinel.run_cycle()

    print("\n--- FINAL STATUS ---")
    status = sentinel.get_status()
    print(f"Total cycles run : {status['total_cycles']}")
    print(f"Users monitored  : {status['users_monitored']}")
    print(f"System status    : {status['status']}")
