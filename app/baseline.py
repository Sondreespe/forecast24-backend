# app/baseline.py
"""
Baseline prediksjon: 7-dagers rullende timebasert snitt.

For hver av de 24 timene i morgen beregnes gjennomsnittet av
samme time de siste 7 dagene.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from sqlalchemy import select

from .models import SpotPrice


def predict_baseline(db: Session, area: str) -> list[dict]:
    """
    Returnerer en 24-timers prediksjon for neste dag basert på
    gjennomsnittet av samme time de siste 7 dagene.
    """
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    cutoff = now - timedelta(days=7)

    stmt = (
        select(SpotPrice)
        .where(SpotPrice.area == area)
        .where(SpotPrice.time_start >= cutoff)
        .where(SpotPrice.nok_per_kwh.isnot(None))
        .order_by(SpotPrice.time_start.asc())
    )
    rows = db.execute(stmt).scalars().all()

    # Grupper priser per time på dagen (0-23)
    hourly: dict[int, list[float]] = defaultdict(list)
    for r in rows:
        ts = r.time_start
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        hourly[ts.hour].append(r.nok_per_kwh)

    # Bygg prediksjon for neste dag (starter midnatt neste dag UTC)
    tomorrow_midnight = (now + timedelta(days=1)).replace(hour=0)
    points = []
    for h in range(24):
        ts = tomorrow_midnight + timedelta(hours=h)
        prices = hourly.get(h, [])
        avg = round(sum(prices) / len(prices), 4) if prices else None
        points.append({
            "timestamp": ts.isoformat(),
            "hour": h,
            "price_nok_per_kwh": avg,
            "n_samples": len(prices),
        })

    return points
