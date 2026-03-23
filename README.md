# forecast24-backend

Backend API for [Forecast24](https://forecast24.no) – a side project for predicting Norwegian electricity prices.
Built with **FastAPI** and **Python**, using PostgreSQL as the database (hosted on [Neon](https://neon.tech)) and deployed via [Render](https://render.com).

---

## Tech Stack

| Layer         | Technology                 |
|---------------|----------------------------|
| API Framework | FastAPI                    |
| Database      | PostgreSQL (Neon)          |
| ORM           | SQLAlchemy 2.0             |
| Validation    | Pydantic                   |
| Data Source   | NVE / hvakosterstrommen.no |
| Deployment    | Render                     |

---

## Endpoints

### Health
```
GET /api/health
```
Returns status and timestamp. Used to verify that the API is up and running.

---

### Spot Prices – Today
```
GET /spot?area=NO1&date=YYYY-MM-DD
```
Returns hour-by-hour spot prices for a given area and date.

**Parameters:**
- `area` – price zone: `NO1`, `NO2`, `NO3`, `NO4`, or `NO5`
- `date` – date in `YYYY-MM-DD` format

---

### Spot Prices – History
```
GET /api/spotprices/history?area=NO1&start=YYYY-MM-DD&end=YYYY-MM-DD
```
Returns historical spot prices for an area within a given date range.

**Parameters:**
- `area` – price zone
- `start` *(optional)* – start date
- `end` *(optional)* – end date
- `limit` *(optional, default 5000)* – maximum number of rows

---

### Spot Prices – Latest N Hours
```
GET /spot/latest?area=NO1&hours=48
```
Returns the last `hours` hours of spot prices for a given area.

---

### Forecast *(in development)*
```
GET /api/forecast
```
Returns a 24-hour price forecast for NO1. Currently rule-based – an ML model is planned.

---

## Running Locally

### 1. Clone the repository
```bash
git clone https://github.com/Sondreespe/forecast24-backend.git
cd forecast24-backend
```

### 2. Set up the environment
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
Create a `.env` file in the root directory:
```
DATABASE_URL=postgresql://...
```

### 4. Start the server
```bash
uvicorn app.main:app --reload
```

The API is now available at `http://localhost:8000`.

---

## Project Structure

```
forecast24-backend/
├── app/
│   ├── main.py          # FastAPI app, CORS, startup
│   ├── models.py        # SQLAlchemy models
│   ├── db.py            # Database connection
│   ├── spot_api.py      # /spot endpoints
│   ├── history_api.py   # /api/spotprices/history
│   ├── collector.py     # Data fetching from external API
│   ├── collector_db.py  # Storage of collected data
│   └── nve_fetcher.py   # NVE integration
├── requirements.txt
└── runtime.txt
```

---

## Status

> **Under active development**
>
> The forecast endpoint currently uses a rule-based model. A proper ML-based time series model is in planning.

---

## Related

- **Frontend:** [forecast24-frontend](https://github.com/Sondreespe/forecast24-frontend)
- **Live app:** [forecast24.no](https://forecast24.no)

---

*Built by Sondre Espe*
