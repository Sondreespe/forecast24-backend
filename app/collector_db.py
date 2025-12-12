from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

import requests
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .db import SessionLocal
from .models import SpotPrice


AREAS = ["NO1", "NO2", "NO3", "NO4", "NO5"]


def hvakoster_url(area: str, d: date) -> str:
    return f"https://www.hvakosterstrommen.no/api/v1/prices/{d.strftime('%Y/%m-%d')}_{area}.json"


def fetch_day(area: str, d: date) -> List[Dict[str, Any]]:
    r = requests.get(hvakoster_url(area, d), timeout=20)
    r.raise_for_status()
    return r.json() if isinstance(r.json(), list) else []


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def normalize_rows(area: str, payload: List[Dict[str, Any]]) -> List[SpotPrice]:
    rows: List[SpotPrice] = []

    for item in payload:
        ts = parse_dt(item.get("time_start"))
        te = parse_dt(item.get("time_end"))

        if ts is None or te is None:
            continue

        try:
            nok = float(item["NOK_per_kWh"])
        except Exception:
            continue

        rows.append(
            SpotPrice(
                area=area,
                date=ts.date(),          # ✅ Date, ikke string
                time_start=ts,
                time_end=te,
                nok_per_kwh=nok,
                eur_per_kwh=float(item["EUR_per_kWh"]) if item.get("EUR_per_kWh") else None,
                exr=float(item["EXR"]) if item.get("EXR") else None,
            )
        )

    return rows


def exists(db, area: str, time_start: datetime) -> bool:
    stmt = select(SpotPrice.id).where(
        SpotPrice.area == area,
        SpotPrice.time_start == time_start,
    )
    return db.execute(stmt).scalar_one_or_none() is not None


def insert_day(db, area: str, d: date) -> tuple[int, int]:
    payload = fetch_day(area, d)
    rows = normalize_rows(area, payload)

    added = skipped = 0

    for row in rows:
        try:
            if exists(db, row.area, row.time_start):
                skipped += 1
                continue

            db.add(row)
            db.flush()      # fanger UNIQUE-brudd her
            added += 1

        except IntegrityError:
            db.rollback()   # 🔑 helt kritisk
            skipped += 1

    return added, skipped


def collect_area(area: str, start: date, end: date):
    db = SessionLocal()
    total_added = total_skipped = 0

    try:
        cur = start
        while cur <= end:
            try:
                a, s = insert_day(db, area, cur)
                db.commit()
                total_added += a
                total_skipped += s
                print(f"[{area}] {cur}: +{a}, skipped {s}")

            except Exception as e:
                db.rollback()
                print(f"[{area}] {cur}: feil: {e}")

            cur += timedelta(days=1)

    finally:
        db.close()

    print(f"Ferdig {area}: +{total_added}, skipped {total_skipped}")


def collect_all(days: int = 30):
    end = date.today()
    start = end - timedelta(days=days - 1)

    for area in AREAS:
        collect_area(area, start, end)


if __name__ == "__main__":
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL mangler")

    collect_all(30)