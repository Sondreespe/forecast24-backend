from fastapi import FastAPI
from datetime import datetime
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
def get_forecast():
    """
    Midlertidig dummy-endepunkt for forecast.
    Senere skal dette hente ekte prediksjoner fra modell/database.
    """
    return {
        "area": "NO1",
        "horizon_hours": 24,
        "status": "placeholder",
        "message": "Forecast-endepunktet er satt opp, men ingen modell er koblet til enda.",
    }

