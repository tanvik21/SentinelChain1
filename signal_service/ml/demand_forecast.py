import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler
import joblib
import os
from datetime import datetime, timedelta


COMMODITY_PROFILES = {
    "agri": {
        "base_price": 4000,
        "monsoon_sensitivity": 0.8,
        "festive_sensitivity": 0.6,
        "volatility": 0.3,
    },
    "textile": {
        "base_price": 180,
        "monsoon_sensitivity": 0.3,
        "festive_sensitivity": 0.9,
        "volatility": 0.2,
    },
    "pharma": {
        "base_price": 850,
        "monsoon_sensitivity": 0.5,
        "festive_sensitivity": 0.1,
        "volatility": 0.1,
    },
    "auto_parts": {
        "base_price": 2200,
        "monsoon_sensitivity": 0.2,
        "festive_sensitivity": 0.4,
        "volatility": 0.15,
    },
    "electronics": {
        "base_price": 12000,
        "monsoon_sensitivity": 0.1,
        "festive_sensitivity": 0.95,
        "volatility": 0.25,
    },
}

FESTIVE_MONTHS = {
    10: 0.9,  # Navratri/Dussehra
    11: 0.7,  # Diwali
    12: 0.5,  # Christmas/New Year
    1: 0.3,   # Pongal/Makar Sankranti
    3: 0.4,   # Holi
    8: 0.3,   # Raksha Bandhan
    9: 0.5,   # Ganesh Chaturthi
}


def generate_commodity_timeseries(commodity, n_days=730):
    profile = COMMODITY_PROFILES[commodity]
    np.random.seed(hash(commodity) % 1000)

    dates = pd.date_range(end=datetime.now(), periods=n_days, freq="D")
    prices = []
    base = profile["base_price"]

    for i, date in enumerate(dates):
        month = date.month
        is_monsoon = 1 if 6 <= month <= 9 else 0
        festive_boost = FESTIVE_MONTHS.get(month, 0)

        # Trend component
        trend = base * (1 + 0.0002 * i)

        # Seasonal component
        seasonal = (
            profile["monsoon_sensitivity"] * is_monsoon * 0.15 +
            profile["festive_sensitivity"] * festive_boost * 0.2
        ) * trend

        # Noise
        noise = np.random.normal(0, profile["volatility"] * base * 0.05)

        # Supply shock — random disruptions
        shock = 0
        if np.random.random() < 0.02:
            shock = np.random.uniform(0.1, 0.3) * trend

        price = trend + seasonal + noise + shock
        prices.append(max(price, base * 0.5))

    df = pd.DataFrame({"date": dates, "price": prices, "commodity": commodity})
    return df


def create_features(df):
    df = df.copy()
    df["month"] = df["date"].dt.month
    df["day_of_year"] = df["date"].dt.dayofyear
    df["day_of_week"] = df["date"].dt.dayofweek
    df["is_monsoon"] = df["month"].apply(lambda m: 1 if 6 <= m <= 9 else 0)
    df["is_festive"] = df["month"].apply(lambda m: 1 if m in FESTIVE_MONTHS else 0)
    df["festive_intensity"] = df["month"].apply(lambda m: FESTIVE_MONTHS.get(m, 0))

    # Lag features — past prices as predictors
    for lag in [1, 3, 7, 14, 30]:
        df[f"price_lag_{lag}"] = df["price"].shift(lag)

    # Rolling statistics
    df["price_roll_7"] = df["price"].shift(1).rolling(7).mean()
    df["price_roll_30"] = df["price"].shift(1).rolling(30).mean()
    df["price_volatility_7"] = df["price"].shift(1).rolling(7).std()

    # Price momentum
    df["price_momentum"] = df["price"].shift(1) - df["price"].shift(7)

    df = df.dropna()
    return df


def train_demand_model(commodity):
    print(f"\n[DemandForecast] Training model for: {commodity}")

    df = generate_commodity_timeseries(commodity)
    df = create_features(df)

    feature_cols = [
        "month", "day_of_year", "day_of_week",
        "is_monsoon", "is_festive", "festive_intensity",
        "price_lag_1", "price_lag_3", "price_lag_7",
        "price_lag_14", "price_lag_30",
        "price_roll_7", "price_roll_30",
        "price_volatility_7", "price_momentum",
    ]

    X = df[feature_cols]
    y = df["price"]

    # Time-based split — train on past, test on recent
    split = int(len(df) * 0.85)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc = scaler.transform(X_test)

    model = GradientBoostingRegressor(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42,
    )

    model.fit(X_train_sc, y_train)
    y_pred = model.predict(X_test_sc)

    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100

    print(f"  MAE  : ₹{mae:.2f}")
    print(f"  RMSE : ₹{rmse:.2f}")
    print(f"  MAPE : {mape:.2f}%")

    os.makedirs("models", exist_ok=True)
    joblib.dump(model, f"models/demand_{commodity}.pkl")
    joblib.dump(scaler, f"models/scaler_{commodity}.pkl")
    joblib.dump(feature_cols, f"models/features_{commodity}.pkl")

    # Save recent data for forecasting context
    df.to_csv(f"models/history_{commodity}.csv", index=False)

    return model, scaler, feature_cols, mae, mape


def forecast_price(commodity, days_ahead=7):
    """
    Forecast commodity price for next N days.
    Returns price trajectory and spike alert if detected.
    """
    model = joblib.load(f"models/demand_{commodity}.pkl")
    scaler = joblib.load(f"models/scaler_{commodity}.pkl")
    feature_cols = joblib.load(f"models/features_{commodity}.pkl")
    history = pd.read_csv(f"models/history_{commodity}.csv", parse_dates=["date"])

    forecasts = []
    current_history = history.copy()

    for day in range(days_ahead):
        future_date = datetime.now() + timedelta(days=day + 1)

        # Build feature row
        recent_prices = current_history["price"].values

        row = {
            "month": future_date.month,
            "day_of_year": future_date.timetuple().tm_yday,
            "day_of_week": future_date.weekday(),
            "is_monsoon": 1 if 6 <= future_date.month <= 9 else 0,
            "is_festive": 1 if future_date.month in FESTIVE_MONTHS else 0,
            "festive_intensity": FESTIVE_MONTHS.get(future_date.month, 0),
            "price_lag_1": recent_prices[-1],
            "price_lag_3": recent_prices[-3] if len(recent_prices) >= 3 else recent_prices[-1],
            "price_lag_7": recent_prices[-7] if len(recent_prices) >= 7 else recent_prices[-1],
            "price_lag_14": recent_prices[-14] if len(recent_prices) >= 14 else recent_prices[-1],
            "price_lag_30": recent_prices[-30] if len(recent_prices) >= 30 else recent_prices[-1],
            "price_roll_7": np.mean(recent_prices[-7:]),
            "price_roll_30": np.mean(recent_prices[-30:]) if len(recent_prices) >= 30 else np.mean(recent_prices),
            "price_volatility_7": np.std(recent_prices[-7:]),
            "price_momentum": recent_prices[-1] - recent_prices[-7] if len(recent_prices) >= 7 else 0,
        }

        X = pd.DataFrame([row])[feature_cols]
        X_sc = scaler.transform(X)
        predicted_price = model.predict(X_sc)[0]

        forecasts.append({
            "date": future_date.strftime("%Y-%m-%d"),
            "predicted_price": round(float(predicted_price), 2),
            "commodity": commodity,
        })

        # Add prediction to rolling history
        new_row = pd.DataFrame([{"date": future_date, "price": predicted_price, "commodity": commodity}])
        new_row = create_features(pd.concat([current_history.tail(60), new_row], ignore_index=True))
        current_history = pd.concat([current_history, new_row.tail(1)[["date", "price", "commodity"]]], ignore_index=True)

    # Spike detection
    current_price = history["price"].iloc[-1]
    max_forecast = max(f["predicted_price"] for f in forecasts)
    price_change_pct = ((max_forecast - current_price) / current_price) * 100

    spike_alert = None
    if price_change_pct > 15:
        spike_alert = {
            "type": "PRICE_SPIKE",
            "commodity": commodity,
            "current_price": round(float(current_price), 2),
            "predicted_peak": round(float(max_forecast), 2),
            "change_pct": round(float(price_change_pct), 2),
            "severity": "HIGH" if price_change_pct > 25 else "MEDIUM",
        }
    elif price_change_pct < -15:
        spike_alert = {
            "type": "PRICE_CRASH",
            "commodity": commodity,
            "current_price": round(float(current_price), 2),
            "predicted_trough": round(float(max_forecast), 2),
            "change_pct": round(float(price_change_pct), 2),
            "severity": "HIGH" if price_change_pct < -25 else "MEDIUM",
        }

    return {
        "commodity": commodity,
        "forecasts": forecasts,
        "spike_alert": spike_alert,
        "current_price": round(float(current_price), 2),
        "unit": "₹/quintal" if commodity == "agri" else "₹/metre" if commodity == "textile" else "₹/unit",
    }


if __name__ == "__main__":
    print("=" * 60)
    print("  SENTINELCHAIN — Demand Forecast Engine")
    print("=" * 60)

    all_maes = {}
    for commodity in COMMODITY_PROFILES.keys():
        _, _, _, mae, mape = train_demand_model(commodity)
        all_maes[commodity] = {"mae": mae, "mape": mape}

    print("\n" + "=" * 60)
    print("  FORECAST TEST — Next 7 Days")
    print("=" * 60)

    for commodity in COMMODITY_PROFILES.keys():
        result = forecast_price(commodity, days_ahead=7)
        print(f"\n📦 {commodity.upper()}")
        print(f"   Current price : {result['unit']} {result['current_price']:,.2f}")
        print(f"   7-day forecast:")
        for f in result["forecasts"][:3]:
            print(f"     {f['date']} → ₹{f['predicted_price']:,.2f}")
        if result["spike_alert"]:
            alert = result["spike_alert"]
            print(f"   ⚠️  {alert['type']}: {alert['change_pct']:+.1f}% change predicted [{alert['severity']}]")
        else:
            print(f"   ✅ Price stable — no spike detected")
