from datetime import datetime, timedelta
from typing import Dict, List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .nve_fetcher import fetch_nve_prices
from .history_api import router as history_router
from .db import Base, engine
from .models import SpotPrice
from .spot_api import router as spot_router

app = FastAPI(
    title="Forecast24 API",
    description="Backend-API for Forecast24",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://forecast24-frontend.onrender.com",
        # senere: "https://DITT-DOMENE.NO"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ALT under /api
app.include_router(history_router, prefix="/api")
app.include_router(spot_router)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "forecast24-backend",
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