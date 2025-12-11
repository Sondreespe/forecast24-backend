import math
from typing import Dict, List
from fastapi import FastAPI
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Forecast24 API",
    description="Backend-API for Forecast24 – prediksjon av strømpris neste 24 timer.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # senere kan vi låse dette til forecast24.no
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Enkel sjekk for å se at API-et kjører."""
    return {
        "status": "ok",
        "service": "forecast24-backend",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/forecast")
def get_forecast() -> Dict:
    """
    Midlertidig dummy-forecast:
    24 punkter (én per time), med fiktive priser i øre/kWh.
    Vi lager et litt realistisk døgnmønster: lav natt, høy ettermiddag.
    """
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    points: List[Dict] = []

    base_price = 80  

    for i in range(24):
        ts = now + timedelta(hours=i)

        
        hour = ts.hour
        
        fluct = (
            -15 if 0 <= hour <= 5 else
            20 if 6 <= hour <= 9 else
            35 if 16 <= hour <= 20 else
            5
        )

        
        wave = 5 * math.sin(i / 3)
        price = base_price + fluct + wave

        points.append(
            {
                "timestamp": ts.isoformat() + "Z",
                "price_ore_per_kwh": round(price, 1),
                "hour": hour,
            }
        )

    prices = [p["price_ore_per_kwh"] for p in points]
    cheapest = min(points, key=lambda p: p["price_ore_per_kwh"])
    priciest = max(points, key=lambda p: p["price_ore_per_kwh"])

    summary = {
        "currency": "NOK",
        "unit": "øre/kWh",
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

