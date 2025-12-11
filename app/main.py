from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .nve_fetcher import fetch_nve_prices

app = FastAPI(
    title="Forecast24 API",
    description="Backend-API for Forecast24 – prediksjon av strømpris neste 24 timer.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # kan strammes inn til forecast24.no senere
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "forecast24-backend",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/forecast")
def get_forecast() -> Dict:
    """
    Dummy-forecast:
    """
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    points: List[Dict] = []

    base_price = 0.8  # 0.8 kr/kWh (80 øre)

    for i in range(24):
        ts = now + timedelta(hours=i)
        hour = ts.hour

        # enkel dagkurve
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
            {
                "timestamp": ts.isoformat() + "Z",
                "price_nok_per_kwh": round(price, 3),
                "hour": hour,
            }
        )

    prices = [p["price_nok_per_kwh"] for p in points]
    cheapest = min(points, key=lambda p: p["price_nok_per_kwh"])
    priciest = max(points, key=lambda p: p["price_nok_per_kwh"])

    summary = {
        "currency": "NOK",
        "unit": "kr/kWh",
        "horizon_hours": 24,
        "min_price": min(prices),
        "max_price": max(prices),
        "cheapest_hour": cheapest["hour"],
        "cheapest_timestamp": cheapest["timestamp"],
        "priciest_hour": priciest["hour"],
        "priciest_timestamp": priciest["timestamp"],
    }

    return {
        "status": "ok",
        "area": "NO1",
        "generated_at": now.isoformat() + "Z",
        "summary": summary,
        "points": points,
    }


@app.get("/spotprices")
def get_spotprices(area: str = "NO1"):
    """
    Returnerer dagens spotpriser for valgt område (default NO1).
    """
    data = fetch_nve_prices(area=area)
    return {"area": area, "data": data}
