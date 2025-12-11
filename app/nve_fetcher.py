import requests
from datetime import datetime

def fetch_nve_prices(area="NO1", date=None):
    """
    collects data from nve
    """
    if date is None:
        date = datetime.utcnow()

    # API needs YYYY/MM-DD and area
    date_str = date.strftime("%Y/%m-%d")
    url = f"https://www.hvakosterstrommen.no/api/v1/prices/{date_str}_{area}.json"

    response = requests.get(url)
    if response.status_code != 200:
        return {
            "error": f"NVE API feilet ({response.status_code}): {response.text}"
        }

    return response.json()
