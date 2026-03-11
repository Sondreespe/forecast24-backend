# forecast24-backend

Backend-API for [Forecast24](https://forecast24.no) – et sideprosjekt for prediksjon av norske strømpriser.

Bygget med **FastAPI** og **Python**, med PostgreSQL som database (hostet på [Neon](https://neon.tech)) og deployment via [Render](https://render.com).

---

## Tech Stack

| Lag | Teknologi |
|---|---|
| API-rammeverk | FastAPI |
| Database | PostgreSQL (Neon) |
| ORM | SQLAlchemy 2.0 |
| Validering | Pydantic |
| Datakilde | NVE / hvakosterstrommen.no |
| Deployment | Render |

---

## Endepunkter

### Helse
```
GET /api/health
```
Returnerer status og tidsstempel. Brukes til å verifisere at APIet er oppe.

---

### Spotpriser – i dag
```
GET /spot?area=NO1&date=YYYY-MM-DD
```
Returnerer time-for-time spotpriser for et gitt område og dato.

**Parametere:**
- `area` – prisområde: `NO1`, `NO2`, `NO3`, `NO4` eller `NO5`
- `date` – dato på formatet `YYYY-MM-DD`

---

### Spotpriser – historikk
```
GET /api/spotprices/history?area=NO1&start=YYYY-MM-DD&end=YYYY-MM-DD
```
Returnerer historiske spotpriser for et område innenfor et datointerval.

**Parametere:**
- `area` – prisområde
- `start` *(valgfri)* – startdato
- `end` *(valgfri)* – sluttdato
- `limit` *(valgfri, standard 5000)* – maks antall rader

---

### Spotpriser – siste N timer
```
GET /spot/latest?area=NO1&hours=48
```
Returnerer de siste `hours` timene med spotpriser for et område.

---

### Forecast (under utvikling)
```
GET /api/forecast
```
Returnerer en 24-timers prognose for NO1. Foreløpig regelbasert – ML-modell kommer.

---

## Lokal kjøring

### 1. Klon repoet
```bash
git clone https://github.com/Sondreespe/forecast24-backend.git
cd forecast24-backend
```

### 2. Sett opp miljø
```bash
pip install -r requirements.txt
```

### 3. Konfigurer miljøvariabler
Opprett en `.env`-fil i rotmappen:
```
DATABASE_URL=postgresql://...
```

### 4. Start serveren
```bash
uvicorn app.main:app --reload
```

APIet er nå tilgjengelig på `http://localhost:8000`.

---

## Prosjektstruktur

```
forecast24-backend/
├── app/
│   ├── main.py          # FastAPI-app, CORS, startup
│   ├── models.py        # SQLAlchemy-modeller
│   ├── db.py            # Databasetilkobling
│   ├── spot_api.py      # /spot-endepunkter
│   ├── history_api.py   # /api/spotprices/history
│   ├── collector.py     # Datahenting fra ekstern API
│   ├── collector_db.py  # Lagring av innsamlet data
│   └── nve_fetcher.py   # NVE-integrasjon
├── requirements.txt
└── runtime.txt
```

---

## Status

> 🚧 **Under aktiv utvikling**
>
> Forecast-endepunktet bruker foreløpig en regelbasert modell. En ekte ML-basert tidsseriemodell er under planlegging.

---

## Relatert

- **Frontend:** [forecast24-frontend](https://github.com/Sondreespe/forecast24-frontend)
- **Live app:** [forecast24.no](https://forecast24.no)

---

*Built by Sondre Espe*