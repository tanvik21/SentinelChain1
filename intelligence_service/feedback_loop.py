"""
SentinelChain — Intelligence Service
Handles the feedback resonance loop:
  - Records user responses (acted / ignored / already_knew)
  - Computes per-archetype accuracy scores
  - Adjusts alert thresholds based on collective behaviour
  - Implements the federated learning pattern:
      local user response → archetype update → global signal mesh calibration
  - Generates weekly intelligence reports
"""
import json
import os
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

FEEDBACK_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "feedback_intelligence.json")


def _load_feedback_db() -> Dict:
    os.makedirs(os.path.dirname(FEEDBACK_DB_PATH), exist_ok=True)
    if not os.path.exists(FEEDBACK_DB_PATH):
        return {
            "archetype_scores": {},
            "corridor_accuracy": {},
            "threat_type_accuracy": {},
            "global_threshold_multiplier": 1.0,
            "total_alerts": 0,
            "total_acted": 0,
            "total_ignored": 0,
            "total_already_knew": 0,
            "last_updated": None,
        }
    with open(FEEDBACK_DB_PATH, "r") as f:
        return json.load(f)


def _save_feedback_db(db: Dict):
    with open(FEEDBACK_DB_PATH, "w") as f:
        json.dump(db, f, indent=2)


class FeedbackResonanceLoop:
    """
    Federated learning pattern for SentinelChain.

    Every user response propagates through three levels:
      1. User level  — personal trust score (in SQLite)
      2. Archetype level — collective accuracy per business type
      3. Global level — system-wide threshold calibration

    This means: if 40 textile manufacturers ignore a flood alert on NH48,
    the system learns that NH48 flood risk is LESS relevant to textiles
    and requires higher confidence before alerting that archetype again.
    """

    def record_feedback(self, user_id: str, alert_id: str, action: str,
                        alert_metadata: Dict) -> Dict:
        """
        action: 'acted' | 'ignored' | 'already_knew'
        alert_metadata: {archetype, highway, threat_type, risk_score}
        """
        db = _load_feedback_db()
        db["total_alerts"] += 1

        if action == "acted":
            db["total_acted"] += 1
            score_delta = +0.1
        elif action == "already_knew":
            db["total_already_knew"] += 1
            score_delta = +0.05  # good signal, slightly less credit
        else:  # ignored
            db["total_ignored"] += 1
            score_delta = -0.08

        archetype = alert_metadata.get("archetype", "unknown")
        highway = alert_metadata.get("highway", "unknown")
        threat_type = alert_metadata.get("threat_type", "unknown")

        # Archetype-level update
        if archetype not in db["archetype_scores"]:
            db["archetype_scores"][archetype] = {"score": 0.5, "count": 0}
        arch = db["archetype_scores"][archetype]
        arch["count"] += 1
        arch["score"] = max(0.1, min(0.95,
            arch["score"] * 0.9 + (0.5 + score_delta) * 0.1
        ))

        # Corridor accuracy update
        corridor_key = f"{highway}:{archetype}"
        if corridor_key not in db["corridor_accuracy"]:
            db["corridor_accuracy"][corridor_key] = {"acted": 0, "ignored": 0, "total": 0}
        corr = db["corridor_accuracy"][corridor_key]
        corr["total"] += 1
        if action == "acted":
            corr["acted"] += 1
        elif action == "ignored":
            corr["ignored"] += 1

        # Threat type accuracy
        if threat_type not in db["threat_type_accuracy"]:
            db["threat_type_accuracy"][threat_type] = {"acted": 0, "total": 0}
        db["threat_type_accuracy"][threat_type]["total"] += 1
        if action == "acted":
            db["threat_type_accuracy"][threat_type]["acted"] += 1

        # Global threshold recalibration
        # If act rate drops below 30%, raise global threshold (reduce noise)
        # If act rate exceeds 70%, lower threshold (more sensitive)
        global_act_rate = db["total_acted"] / max(db["total_alerts"], 1)
        if global_act_rate < 0.30:
            db["global_threshold_multiplier"] = min(1.5, db["global_threshold_multiplier"] + 0.02)
        elif global_act_rate > 0.70:
            db["global_threshold_multiplier"] = max(0.7, db["global_threshold_multiplier"] - 0.02)

        db["last_updated"] = datetime.now().isoformat()
        _save_feedback_db(db)

        return {
            "feedback_recorded": True,
            "action": action,
            "archetype_score": arch["score"],
            "global_threshold_multiplier": db["global_threshold_multiplier"],
            "global_act_rate": round(global_act_rate, 3),
        }

    def get_threshold_for_archetype(self, archetype: str,
                                     base_threshold: float) -> float:
        """
        Returns calibrated alert threshold for this archetype.
        Higher score = more trusted = lower threshold needed.
        """
        db = _load_feedback_db()
        arch_score = db["archetype_scores"].get(archetype, {}).get("score", 0.5)
        global_mult = db["global_threshold_multiplier"]

        # Inverse: higher trust score = more sensitive (lower threshold)
        calibrated = base_threshold * global_mult * (1.5 - arch_score)
        return round(max(0.15, min(0.85, calibrated)), 3)

    def get_corridor_relevance(self, highway: str, archetype: str) -> float:
        """
        How relevant is this highway for this archetype, based on feedback history?
        Returns 0.0–1.0 multiplier for corridor risk boost.
        """
        db = _load_feedback_db()
        key = f"{highway}:{archetype}"
        corr = db["corridor_accuracy"].get(key, {})
        total = corr.get("total", 0)
        if total < 3:
            return 0.8  # not enough data, use neutral relevance
        acted = corr.get("acted", 0)
        return round(acted / total, 3)

    def get_intelligence_report(self) -> Dict:
        """
        Weekly intelligence summary — what threats are real vs noise.
        """
        db = _load_feedback_db()
        total = max(db["total_alerts"], 1)

        # Best performing threat types
        threat_accuracy = {}
        for threat, stats in db["threat_type_accuracy"].items():
            if stats["total"] >= 2:
                acc = stats["acted"] / stats["total"]
                threat_accuracy[threat] = round(acc, 3)

        # Most reliable corridors
        corridor_reliability = {}
        for key, stats in db["corridor_accuracy"].items():
            if stats["total"] >= 2:
                corridor_reliability[key] = round(stats["acted"] / stats["total"], 3)

        return {
            "total_alerts_sent": db["total_alerts"],
            "act_rate": round(db["total_acted"] / total, 3),
            "ignore_rate": round(db["total_ignored"] / total, 3),
            "already_knew_rate": round(db["total_already_knew"] / total, 3),
            "global_threshold_multiplier": db["global_threshold_multiplier"],
            "archetype_trust_scores": {
                k: round(v["score"], 3)
                for k, v in db["archetype_scores"].items()
            },
            "threat_type_accuracy": dict(
                sorted(threat_accuracy.items(), key=lambda x: -x[1])
            ),
            "most_reliable_corridors": dict(
                sorted(corridor_reliability.items(), key=lambda x: -x[1])[:5]
            ),
            "system_health": "GOOD" if db["total_acted"] / total > 0.4 else
                             "WARNING" if db["total_acted"] / total > 0.2 else "POOR",
            "generated_at": datetime.now().isoformat(),
        }


class AlertPatternAnalyzer:
    """
    Analyzes patterns across all alerts to surface meta-intelligence.
    Answers questions like:
      - Which highways are disrupted most often?
      - What time of day do most disruptions happen?
      - Which business types are most exposed?
    """

    def analyze_cycle_history(self, cycle_history: List[Dict]) -> Dict:
        if not cycle_history:
            return {"patterns": [], "insights": []}

        threat_counts = defaultdict(int)
        hourly_distribution = defaultdict(int)
        severity_distribution = defaultdict(int)

        for cycle in cycle_history:
            hour = datetime.fromisoformat(cycle.get("created_at", datetime.now().isoformat())).hour
            hourly_distribution[hour] += cycle.get("threats_detected", 0)
            severity_distribution[cycle.get("threat_level", "NORMAL")] += 1

        # Peak disruption hours
        peak_hour = max(hourly_distribution, key=hourly_distribution.get) if hourly_distribution else 0

        insights = []
        if severity_distribution.get("CRITICAL", 0) > 0:
            insights.append(f"System has seen {severity_distribution['CRITICAL']} CRITICAL threat events")
        if severity_distribution.get("ELEVATED", 0) > 2:
            insights.append(f"Elevated threat conditions occurred {severity_distribution['ELEVATED']} times")
        if peak_hour:
            insights.append(f"Peak disruption signals detected around {peak_hour:02d}:00 IST")

        return {
            "total_cycles_analyzed": len(cycle_history),
            "threat_level_distribution": dict(severity_distribution),
            "peak_disruption_hour": peak_hour,
            "avg_threats_per_cycle": round(
                sum(c.get("threats_detected", 0) for c in cycle_history) / len(cycle_history), 2
            ),
            "insights": insights,
        }


# Singletons
_feedback_loop = None
_pattern_analyzer = None

def get_feedback_loop() -> FeedbackResonanceLoop:
    global _feedback_loop
    if _feedback_loop is None:
        _feedback_loop = FeedbackResonanceLoop()
    return _feedback_loop

def get_pattern_analyzer() -> AlertPatternAnalyzer:
    global _pattern_analyzer
    if _pattern_analyzer is None:
        _pattern_analyzer = AlertPatternAnalyzer()
    return _pattern_analyzer
