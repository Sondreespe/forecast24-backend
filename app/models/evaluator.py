"""
Evaluerer modeller ved å sammenligne hva de ville predikert for i dag
(basert på gårsdagens data) mot faktiske priser for i dag.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone, date as dt_date

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_db import SpotPrice


def _get_actual_today(db: Session, area: str, today: dt_date) -> dict[int, float]:
    """Henter faktiske priser for i dag. Returnerer {hour: price}."""
    rows = db.execute(
        select(SpotPrice)
        .where(SpotPrice.area == area)
        .where(SpotPrice.date == today)
        .where(SpotPrice.nok_per_kwh.isnot(None))
        .order_by(SpotPrice.time_start.asc())
    ).scalars().all()

    result = {}
    for r in rows:
        ts = r.time_start
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        result[ts.hour] = r.nok_per_kwh
    return result


def _predict_baseline_for_today(db: Session, area: str, today: dt_date) -> dict[int, float]:
    """Baseline: 7-dagers rullende snitt for i dag, kun data FØR i dag."""
    today_midnight = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    cutoff_start = today_midnight - timedelta(days=7)

    rows = db.execute(
        select(SpotPrice)
        .where(SpotPrice.area == area)
        .where(SpotPrice.time_start >= cutoff_start)
        .where(SpotPrice.time_start < today_midnight)
        .where(SpotPrice.nok_per_kwh.isnot(None))
        .order_by(SpotPrice.time_start.asc())
    ).scalars().all()

    hourly: dict[int, list[float]] = defaultdict(list)
    for r in rows:
        ts = r.time_start
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        hourly[ts.hour].append(r.nok_per_kwh)

    return {h: round(sum(p) / len(p), 4) for h, p in hourly.items() if p}


def _predict_xgboost_for_today(db: Session, area: str, today: dt_date) -> dict[int, float]:
    """XGBoost: trener på data FØR i dag, predikerer i dag."""
    import xgboost as xgb

    today_midnight = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    cutoff_start = today_midnight - timedelta(days=60)

    rows = db.execute(
        select(SpotPrice)
        .where(SpotPrice.area == area)
        .where(SpotPrice.time_start >= cutoff_start)
        .where(SpotPrice.time_start < today_midnight)
        .where(SpotPrice.nok_per_kwh.isnot(None))
        .order_by(SpotPrice.time_start.asc())
    ).scalars().all()

    if not rows or len(rows) < 48:
        raise ValueError(f"Ikke nok historiske data for evaluering ({len(rows)} rader)")

    df = pd.DataFrame([{
        "time_start": r.time_start if r.time_start.tzinfo else r.time_start.replace(tzinfo=timezone.utc),
        "nok_per_kwh": r.nok_per_kwh,
    } for r in rows]).set_index("time_start").sort_index()

    df["hour"] = df.index.hour
    df["day_of_week"] = df.index.dayofweek
    df["month"] = df.index.month
    df["lag_24"] = df["nok_per_kwh"].shift(24)
    df["lag_48"] = df["nok_per_kwh"].shift(48)
    df["lag_168"] = df["nok_per_kwh"].shift(168)
    df["rolling_mean_7d"] = df["nok_per_kwh"].shift(24).rolling(window=168, min_periods=24).mean()
    df = df.dropna()

    feature_cols = ["hour", "day_of_week", "month", "lag_24", "lag_48", "lag_168", "rolling_mean_7d"]
    model = xgb.XGBRegressor(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, random_state=42, verbosity=0,
    )
    model.fit(df[feature_cols].values, df["nok_per_kwh"].values)

    recent = df["nok_per_kwh"]
    result = {}

    for h in range(24):
        ts = today_midnight + timedelta(hours=h)

        def get_price_at(target_ts):
            try:
                idx = recent.index.get_indexer([target_ts], method="nearest")[0]
                return float(recent.iloc[idx])
            except Exception:
                return float(recent.mean())

        lag_24_val = get_price_at(ts - timedelta(hours=24))
        lag_48_val = get_price_at(ts - timedelta(hours=48))
        lag_168_val = get_price_at(ts - timedelta(hours=168))
        same_hour = df[df.index.hour == h]["nok_per_kwh"].tail(7)
        rolling_mean = float(same_hour.mean()) if len(same_hour) > 0 else float(recent.mean())

        features = np.array([[h, ts.weekday(), ts.month, lag_24_val, lag_48_val, lag_168_val, rolling_mean]])
        result[h] = max(0.0, round(float(model.predict(features)[0]), 4))

    return result


def evaluate_model(db: Session, model_id: str, area: str) -> dict:
    """Evaluerer modell mot faktiske priser for i dag."""
    today = datetime.now(timezone.utc).date()

    actual = _get_actual_today(db, area, today)
    if len(actual) < 24:
        return {
            "status": "incomplete",
            "message": f"Dagens data er ikke tilgjengelig ennå. Har {len(actual)} av 24 timer.",
            "hours_available": len(actual),
        }

    if model_id == "baseline":
        predicted = _predict_baseline_for_today(db, area, today)
    elif model_id == "xgboost":
        predicted = _predict_xgboost_for_today(db, area, today)
    else:
        raise ValueError(f"Ukjent modell: {model_id}")

    hours = sorted(set(actual.keys()) & set(predicted.keys()))
    n = len(hours)
    errors = [abs(actual[h] - predicted[h]) for h in hours]
    sq_errors = [(actual[h] - predicted[h]) ** 2 for h in hours]
    pct_errors = [abs((actual[h] - predicted[h]) / actual[h]) for h in hours if actual[h] != 0]

    mae = round(sum(errors) / n, 4)
    rmse = round(math.sqrt(sum(sq_errors) / n), 4)
    mape = round(sum(pct_errors) / len(pct_errors) * 100, 2) if pct_errors else None

    best_hour = hours[errors.index(min(errors))]
    worst_hour = hours[errors.index(max(errors))]

    points = [
        {
            "hour": h,
            "time": f"{h:02d}:00",
            "predicted": predicted.get(h),
            "actual": actual.get(h),
        }
        for h in range(24)
    ]

    return {
        "status": "ok",
        "model": model_id,
        "area": area,
        "date": today.isoformat(),
        "metrics": {"mae": mae, "rmse": rmse, "mape": mape},
        "best_hour": best_hour,
        "worst_hour": worst_hour,
        "n_hours": n,
        "points": points,
    }
