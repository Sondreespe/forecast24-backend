# app/spot_api.py
from datetime import date, datetime, time, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from .db import get_db
from .models import SpotPrice

router = APIRouter(prefix="/spot", tags=["spot"])

class SpotPriceOut(BaseModel):
    area: str
    date: date
    time_start: datetime
    time_end: datetime
    nok_per_kwh: Optional[float] = None
    eur_per_kwh: Optional[float] = None
    exr: Optional[float] = None

    class Config:
        from_attributes = True  # pydantic v2

def _day_range_utc(d: date):
    # DB lagrer timestart som tz-aware; vi filtrerer på dato-kolonnen 
    return d

@router.get("", response_model=List[SpotPriceOut])
def get_spot_prices_for_day(
    area: str = Query(..., min_length=3, max_length=3, description="NO1..NO5"),
    d: date = Query(..., alias="date", description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    q = (
        select(SpotPrice)
        .where(SpotPrice.area == area)
        .where(SpotPrice.date == d)
        .order_by(SpotPrice.time_start.asc())
    )
    rows = db.execute(q).scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail="Ingen priser funnet for area+date")
    return rows

@router.get("/latest", response_model=List[SpotPriceOut])
def get_latest_spot_prices(
    area: str = Query(..., min_length=3, max_length=3),
    hours: int = Query(48, ge=1, le=168),
    db: Session = Depends(get_db),
):
    
    last_ts = db.execute(
        select(SpotPrice.time_start)
        .where(SpotPrice.area == area)
        .order_by(SpotPrice.time_start.desc())
        .limit(1)
    ).scalar_one_or_none()

    if last_ts is None:
        raise HTTPException(status_code=404, detail="Ingen priser funnet for area")

    since = last_ts - timedelta(hours=hours - 1)

    q = (
        select(SpotPrice)
        .where(SpotPrice.area == area)
        .where(SpotPrice.time_start >= since)
        .order_by(SpotPrice.time_start.asc())
    )
    return db.execute(q).scalars().all()