# app/nve_fetcher.py
import requests
from datetime import datetime

def fetch_nve_prices(area: str = "NO1", date: datetime | None = None):
    """
    Henter norske spotpriser fra hvakosterstrommen.no (NVE-data).
    Returnerer listen fra API-et direkte (eller en dict med 'error').
    """
    if date is None:
        date = datetime.utcnow()

    # API-format: YYYY/MM-DD_area.json, f.eks 2025/12-11_NO1.json
    date_str = date.strftime("%Y/%m-%d")
    url = f"https://www.hvakosterstrommen.no/api/v1/prices/{date_str}_{area}.json"

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except Exception as exc:
        return {"error": f"NVE API feilet: {exc}"}

    return resp.json()
