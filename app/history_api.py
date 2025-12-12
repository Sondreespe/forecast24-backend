# app/history_api.py
from __future__ import annotations

from datetime import datetime, date as dt_date
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from .db import get_db
from .models import SpotPrice

router = APIRouter(tags=["history"])

AREAS = {"NO1", "NO2", "NO3", "NO4", "NO5"}

def _parse_date(s: str) -> dt_date:
    return datetime.strptime(s, "%Y-%m-%d").date()

@router.get("/spotprices/history")
def spotprices_history(
    area: str = Query(..., description="NO1..NO5"),
    start: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="YYYY-MM-DD"),
    limit: int = Query(5000, ge=1, le=20000),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    area = area.upper().strip()
    if area not in AREAS:
        raise HTTPException(status_code=400, detail="Ugyldig område. Bruk NO1..NO5")

    start_d = _parse_date(start) if start else None
    end_d = _parse_date(end) if end else None

    stmt = select(SpotPrice).where(SpotPrice.area == area)

    if start_d:
        stmt = stmt.where(SpotPrice.date >= start_d)
    if end_d:
        stmt = stmt.where(SpotPrice.date <= end_d)

    stmt = stmt.order_by(SpotPrice.time_start.asc()).limit(limit)

    rows = db.execute(stmt).scalars().all()

    return [
        {
            "area": r.area,
            "date": r.date.isoformat(),
            "time_start": r.time_start.isoformat(),
            "time_end": r.time_end.isoformat(),
            "NOK_per_kWh": r.nok_per_kwh,
            "EUR_per_kWh": r.eur_per_kwh,
            "EXR": r.exr,
        }
        for r in rows
    ]