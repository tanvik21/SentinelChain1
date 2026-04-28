import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import LabelEncoder
import joblib
import os

def generate_training_data(n_samples=2000):
    """
    Generate realistic synthetic training data based on
    known Indian weather-disruption patterns.
    In production: replace with real historical data.
    """
    np.random.seed(42)
    
    data = []
    for _ in range(n_samples):
        month = np.random.randint(1, 13)
        precipitation_mm = np.random.exponential(15)
        wind_kmh = np.random.exponential(20)
        weather_code = np.random.choice([0, 1, 2, 3, 61, 63, 65, 71, 80, 95],
                                         p=[0.3, 0.15, 0.1, 0.1, 0.1, 0.07, 0.05, 0.03, 0.07, 0.03])
        highway_vulnerability = np.random.uniform(0.1, 1.0)
        commodity_sensitivity = np.random.uniform(0.1, 1.0)
        is_monsoon = 1 if 6 <= month <= 9 else 0
        is_winter = 1 if month in [12, 1, 2] else 0

        # Learned disruption probability — based on real patterns
        # Monsoon + heavy rain + vulnerable highway = high disruption chance
        base_prob = 0.05
        if is_monsoon:
            base_prob += 0.2
        if precipitation_mm > 50:
            base_prob += 0.35
        elif precipitation_mm > 25:
            base_prob += 0.2
        elif precipitation_mm > 10:
            base_prob += 0.08
        if wind_kmh > 60:
            base_prob += 0.2
        elif wind_kmh > 40:
            base_prob += 0.1
        if weather_code >= 95:
            base_prob += 0.25
        elif weather_code >= 65:
            base_prob += 0.15
        base_prob *= highway_vulnerability
        base_prob = min(base_prob + np.random.normal(0, 0.05), 1.0)
        disruption = 1 if base_prob > 0.35 else 0

        data.append({
            "month": month,
            "precipitation_mm": round(precipitation_mm, 2),
            "wind_kmh": round(wind_kmh, 2),
            "weather_code": weather_code,
            "highway_vulnerability": round(highway_vulnerability, 3),
            "commodity_sensitivity": round(commodity_sensitivity, 3),
            "is_monsoon": is_monsoon,
            "is_winter": is_winter,
            "disruption": disruption,
        })

    return pd.DataFrame(data)


def train_disruption_model():
    print("[DisruptionModel] Generating training data...")
    df = generate_training_data(2000)

    print(f"[DisruptionModel] Dataset: {len(df)} samples")
    print(f"[DisruptionModel] Disruption rate: {df['disruption'].mean():.1%}")

    features = [
        "month", "precipitation_mm", "wind_kmh", "weather_code",
        "highway_vulnerability", "commodity_sensitivity",
        "is_monsoon", "is_winter"
    ]
    X = df[features]
    y = df["disruption"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=(y_train == 0).sum() / (y_train == 1).sum(),
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
    )

    print("[DisruptionModel] Training XGBoost classifier...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False
    )

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    print("\n[DisruptionModel] — EVALUATION REPORT —")
    print(classification_report(y_test, y_pred, target_names=["Clear", "Disruption"]))
    print(f"ROC-AUC Score: {roc_auc_score(y_test, y_prob):.4f}")

    # Feature importance
    importance = dict(zip(features, model.feature_importances_))
    print("\n[DisruptionModel] Feature Importances:")
    for feat, imp in sorted(importance.items(), key=lambda x: -x[1]):
        bar = "█" * int(imp * 40)
        print(f"  {feat:<30} {bar} {imp:.4f}")

    # Save model
    os.makedirs("models", exist_ok=True)
    joblib.dump(model, "models/disruption_model.pkl")
    joblib.dump(features, "models/feature_names.pkl")
    print("\n[DisruptionModel] Model saved to models/disruption_model.pkl")

    return model, features


def load_model():
    model = joblib.load("models/disruption_model.pkl")
    features = joblib.load("models/feature_names.pkl")
    return model, features


def predict_disruption(weather_data: dict, highway_vulnerability: float,
                        commodity_sensitivity: float) -> dict:
    """
    Given weather data for a corridor, predict disruption probability.
    Returns probability and confidence tier.
    """
    model, features = load_model()

    from datetime import datetime
    month = datetime.now().month
    is_monsoon = 1 if 6 <= month <= 9 else 0
    is_winter = 1 if month in [12, 1, 2] else 0

    X = pd.DataFrame([{
        "month": month,
        "precipitation_mm": weather_data.get("precipitation_mm", 0),
        "wind_kmh": weather_data.get("wind_kmh", 0),
        "weather_code": weather_data.get("weather_code", 0),
        "highway_vulnerability": highway_vulnerability,
        "commodity_sensitivity": commodity_sensitivity,
        "is_monsoon": is_monsoon,
        "is_winter": is_winter,
    }])

    prob = model.predict_proba(X)[0][1]

    # Asymmetric confidence tiers
    if prob >= 0.75:
        tier = "HIGH"
    elif prob >= 0.45:
        tier = "MEDIUM"
    elif prob >= 0.25:
        tier = "LOW"
    else:
        tier = "CLEAR"

    return {
        "disruption_probability": round(float(prob), 4),
        "risk_tier": tier,
        "risk_score": round(float(prob), 4),
    }


if __name__ == "__main__":
    train_disruption_model()
    
    print("\n[DisruptionModel] Testing prediction...")
    test_cases = [
        {"name": "Monsoon flood scenario", "data": {"precipitation_mm": 80, "wind_kmh": 55, "weather_code": 65}, "vuln": 0.8, "sens": 0.7},
        {"name": "Normal clear day", "data": {"precipitation_mm": 2, "wind_kmh": 15, "weather_code": 1}, "vuln": 0.3, "sens": 0.4},
        {"name": "Cyclone warning", "data": {"precipitation_mm": 120, "wind_kmh": 90, "weather_code": 95}, "vuln": 0.9, "sens": 0.9},
    ]
    
    for tc in test_cases:
        result = predict_disruption(tc["data"], tc["vuln"], tc["sens"])
        print(f"\n  Scenario : {tc['name']}")
        print(f"  Probability : {result['disruption_probability']:.1%}")
        print(f"  Risk Tier   : {result['risk_tier']}")
