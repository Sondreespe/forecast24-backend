
"""
XGBoost prediksjon: Gradient boosting på tidsseriefeatures.

Trener en XGBoost-modell på historiske timespriser med følgende features:
- hour: time på dagen (0-23)
- day_of_week: ukedag (0=mandag, 6=søndag)
- month: måned (1-12)
- lag_24: pris 24 timer siden
- lag_48: pris 48 timer siden
- lag_168: pris 7 dager siden (samme time forrige uke)
- rolling_mean_7d: snitt av samme time siste 7 dager
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models_db import SpotPrice


import xgboost as xgb



def _fetch_history(db: Session, area: str, days: int = 60) -> pd.DataFrame:
    """Henter historiske priser fra databasen og returnerer som DataFrame."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(SpotPrice)
        .where(SpotPrice.area == area)
        .where(SpotPrice.time_start >= cutoff)
        .where(SpotPrice.nok_per_kwh.isnot(None))
        .order_by(SpotPrice.time_start.asc())
    )
    rows = db.execute(stmt).scalars().all()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame([{
        "time_start": r.time_start if r.time_start.tzinfo else r.time_start.replace(tzinfo=timezone.utc),
        "nok_per_kwh": r.nok_per_kwh,
    } for r in rows])

    df = df.set_index("time_start").sort_index()
    return df


def _build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Lager features fra tidsseriedata."""
    df = df.copy()

    # Tidsbaserte features
    df["hour"] = df.index.hour
    df["day_of_week"] = df.index.dayofweek
    df["month"] = df.index.month

    # priser på samme tidspunkt i fortiden
    df["lag_24"] = df["nok_per_kwh"].shift(24)
    df["lag_48"] = df["nok_per_kwh"].shift(48)
    df["lag_168"] = df["nok_per_kwh"].shift(168)

    # Rullende snitt siste 7 dager (168 timer) per time
    df["rolling_mean_7d"] = (
        df["nok_per_kwh"]
        .shift(24)
        .rolling(window=168, min_periods=24)
        .mean()
    )

    return df.dropna()


def predict_xgboost(db: Session, area: str) -> list[dict]:
    """
    Trener XGBoost på historiske data og predikerer neste 24 timer.
    Returnerer samme format som baseline for enkel sammenligning.
    """

    # Hent historikk
    df = _fetch_history(db, area, days=60)
    if df.empty or len(df) < 48:
        raise ValueError(f"Ikke nok historiske data for {area}")

    # Bygg features
    df_feat = _build_features(df)
    if len(df_feat) < 24:
        raise ValueError("Ikke nok data etter feature engineering")

    feature_cols = ["hour", "day_of_week", "month", "lag_24", "lag_48", "lag_168", "rolling_mean_7d"]
    X = df_feat[feature_cols].values
    y = df_feat["nok_per_kwh"].values

    # Tren modellen
    model = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=0,
    )
    model.fit(X, y)

    # Lag prediksjonspunkter for neste 24 timer
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    tomorrow_midnight = (now + timedelta(days=1)).replace(hour=0)

    # Hent siste kjente priser for lag-features
    recent = df["nok_per_kwh"].tail(200)

    points = []
    for h in range(24):
        ts = tomorrow_midnight + timedelta(hours=h)

        # Finn lag-verdier fra historikken
        lag_24_ts = ts - timedelta(hours=24)
        lag_48_ts = ts - timedelta(hours=48)
        lag_168_ts = ts - timedelta(hours=168)

        def get_price_at(target_ts):
            try:
                idx = recent.index.get_indexer([target_ts], method="nearest")[0]
                return float(recent.iloc[idx])
            except Exception:
                return float(recent.mean())

        lag_24_val = get_price_at(lag_24_ts)
        lag_48_val = get_price_at(lag_48_ts)
        lag_168_val = get_price_at(lag_168_ts)

        # Rullende snitt: gjennomsnittet av samme time siste 7 dager
        same_hour = df[df.index.hour == h]["nok_per_kwh"].tail(7)
        rolling_mean = float(same_hour.mean()) if len(same_hour) > 0 else float(recent.mean())

        features = np.array([[h, ts.weekday(), ts.month, lag_24_val, lag_48_val, lag_168_val, rolling_mean]])
        predicted_price = float(model.predict(features)[0])
        predicted_price = max(0.0, round(predicted_price, 4))

        points.append({
            "timestamp": ts.isoformat(),
            "hour": h,
            "price_nok_per_kwh": predicted_price,
            "n_samples": int(len(df_feat)),
        })

    return points