from datetime import datetime, timedelta
from typing import Dict, List
from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .nve_fetcher import fetch_nve_prices
from .history_api import router as history_router
from .db import Base, engine, get_db
from app.models.xgboost_model import predict_xgboost
from app.models.baseline import predict_baseline
from app.models.evaluator import evaluate_model
from .spot_api import router as spot_router
import asyncio
from concurrent.futures import ThreadPoolExecutor

#Check check check
app = FastAPI(
    title="Forecast24 API",
    description="Backend-API for Forecast24",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://forecast24-frontend.onrender.com",
        "https://forecast24.no",
        "https://www.forecast24.no",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ALT under /api
app.include_router(history_router, prefix="/api")
app.include_router(spot_router)

@app.on_event("startup")
async def on_startup():
    Base.metadata.create_all(bind=engine)
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=1)
    loop.run_in_executor(executor, lambda: __import__('app.collector_db', fromlist=['collect_all']).collect_all(days=30))

@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "forecast24-backend",
        "cors_fingerprint": "CORS-TEST-2025-12-12",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

@app.get("/api/forecast")
def get_forecast() -> Dict:
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    points: List[Dict] = []

    base_price = 0.8
    for i in range(24):
        ts = now + timedelta(hours=i)
        hour = ts.hour

        if 0 <= hour <= 5:
            fluct = -0.15
        elif 6 <= hour <= 9:
            fluct = 0.2
        elif 16 <= hour <= 20:
            fluct = 0.35
        else:
            fluct = 0.05

        price = base_price + fluct
        points.append(
            {"timestamp": ts.isoformat() + "Z", "price_nok_per_kwh": round(price, 3), "hour": hour}
        )

    prices = [p["price_nok_per_kwh"] for p in points]
    cheapest = min(points, key=lambda p: p["price_nok_per_kwh"])
    priciest = max(points, key=lambda p: p["price_nok_per_kwh"])

    return {
        "status": "ok",
        "area": "NO1",
        "generated_at": now.isoformat() + "Z",
        "summary": {
            "currency": "NOK",
            "unit": "kr/kWh",
            "horizon_hours": 24,
            "min_price": min(prices),
            "max_price": max(prices),
            "cheapest_hour": cheapest["hour"],
            "cheapest_timestamp": cheapest["timestamp"],
            "priciest_hour": priciest["hour"],
            "priciest_timestamp": priciest["timestamp"],
        },
        "points": points,
    }

@app.get("/api/spotprices")
def get_spotprices(area: str = "NO1"):
    data = fetch_nve_prices(area=area)
    return {"area": area, "data": data}

#models

@app.get("/api/forecast/baseline")
def get_forecast_baseline(
        area: str = Query("NO1", description="NO1..NO5"),
        db: Session = Depends(get_db),
) -> Dict:
    area = area.upper().strip()
    points = predict_baseline(db, area)

    valid = [p for p in points if p["price_nok_per_kwh"] is not None]
    prices = [p["price_nok_per_kwh"] for p in valid]

    if not prices:
        return {
            "status": "no_data",
            "model": "baseline",
            "area": area,
            "points": points,
            "summary": None,
        }

    cheapest = min(valid, key=lambda p: p["price_nok_per_kwh"])
    priciest = max(valid, key=lambda p: p["price_nok_per_kwh"])
    now = datetime.utcnow()

    return {
        "status": "ok",
        "model": "baseline",
        "area": area,
        "generated_at": now.isoformat() + "Z",
        "summary": {
            "currency": "NOK",
            "unit": "kr/kWh",
            "horizon_hours": 24,
            "min_price": min(prices),
            "max_price": max(prices),
            "avg_price": round(sum(prices) / len(prices), 4),
            "cheapest_hour": cheapest["hour"],
            "cheapest_timestamp": cheapest["timestamp"],
            "priciest_hour": priciest["hour"],
            "priciest_timestamp": priciest["timestamp"],
        },
        "points": points,
    }

@app.get("/api/forecast/xgboost")
def get_forecast_xgboost(
        area: str = Query("NO1", description="NO1..NO5"),
        db: Session = Depends(get_db),
) -> Dict:
    area = area.upper().strip()

    try:
        points = predict_xgboost(db, area)
    except Exception as e:
        return {"status": "error", "model": "xgboost", "area": area, "detail": str(e)}

    valid = [p for p in points if p["price_nok_per_kwh"] is not None]
    prices = [p["price_nok_per_kwh"] for p in valid]
    cheapest = min(valid, key=lambda p: p["price_nok_per_kwh"])
    priciest = max(valid, key=lambda p: p["price_nok_per_kwh"])
    now = datetime.utcnow()

    return {
        "status": "ok",
        "model": "xgboost",
        "area": area,
        "generated_at": now.isoformat() + "Z",
        "summary": {
            "currency": "NOK",
            "unit": "kr/kWh",
            "horizon_hours": 24,
            "min_price": min(prices),
            "max_price": max(prices),
            "avg_price": round(sum(prices) / len(prices), 4),
            "cheapest_hour": cheapest["hour"],
            "cheapest_timestamp": cheapest["timestamp"],
            "priciest_hour": priciest["hour"],
            "priciest_timestamp": priciest["timestamp"],
        },
        "points": points,
    }


@app.get("/api/evaluate/{model_id}")
def get_model_evaluation(
        model_id: str,
        area: str = Query("NO1", description="NO1..NO5"),
        db: Session = Depends(get_db),
) -> Dict:
    area = area.upper().strip()
    try:
        return evaluate_model(db, model_id, area)
    except Exception as e:
        return {"status": "error", "detail": str(e)}
