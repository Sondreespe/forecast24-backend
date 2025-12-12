from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, List, Dict, Any

import requests


AREAS = ["NO1", "NO2", "NO3", "NO4", "NO5"]


@dataclass
class PriceRow:
    area: str
    date: str          # YYYY-MM-DD
    time_start: str    # ISO
    time_end: str      # ISO
    nok_per_kwh: float
    eur_per_kwh: float
    exr: float


def fetch_day(area: str, d: date) -> List[Dict[str, Any]]:
    # API bruker format: YYYY/MM-DD_NO1.json (merk slash)
    date_str = d.strftime("%Y/%m-%d")
    url = f"https://www.hvakosterstrommen.no/api/v1/prices/{date_str}_{area}.json"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()


def normalize(area: str, payload: List[Dict[str, Any]]) -> List[PriceRow]:
    rows: List[PriceRow] = []
    for item in payload:
        ts = item.get("time_start")
        te = item.get("time_end")
        nok = float(item.get("NOK_per_kWh"))
        eur = float(item.get("EUR_per_kWh"))
        exr = float(item.get("EXR"))

        # time_start starter med YYYY-MM-DD...
        day = ts[:10] if isinstance(ts, str) and len(ts) >= 10 else ""

        rows.append(
            PriceRow(
                area=area,
                date=day,
                time_start=ts,
                time_end=te,
                nok_per_kwh=nok,
                eur_per_kwh=eur,
                exr=exr,
            )
        )
    return rows


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def csv_path(base_dir: str, area: str) -> str:
    return os.path.join(base_dir, f"spotprices_{area}.csv")


def existing_dates_in_csv(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    dates = set()
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("date"):
                dates.add(row["date"])
    return dates


def append_rows(path: str, rows: Iterable[PriceRow]) -> int:
    is_new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(
                ["area", "date", "time_start", "time_end", "nok_per_kwh", "eur_per_kwh", "exr"]
            )
        count = 0
        for r in rows:
            writer.writerow(
                [r.area, r.date, r.time_start, r.time_end, r.nok_per_kwh, r.eur_per_kwh, r.exr]
            )
            count += 1
        return count


def daterange(start: date, end: date) -> Iterable[date]:
    # inclusive start, inclusive end
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def collect(
    area: str,
    start: date,
    end: date,
    out_dir: str = "data",
    skip_existing: bool = True,
) -> None:
    ensure_dir(out_dir)
    path = csv_path(out_dir, area)

    existing = existing_dates_in_csv(path) if skip_existing else set()

    total = 0
    for d in daterange(start, end):
        d_str = d.isoformat()
        if skip_existing and d_str in existing:
            print(f"[{area}] {d_str}: finnes allerede, skipper")
            continue

        try:
            payload = fetch_day(area, d)
            rows = normalize(area, payload)
            added = append_rows(path, rows)
            total += added
            print(f"[{area}] {d_str}: +{added} rader")
        except requests.HTTPError as e:
            # API kan mangle enkelte datoer (fremtid, eller historikk begrensning)
            print(f"[{area}] {d_str}: HTTP-feil: {e}")
        except Exception as e:
            print(f"[{area}] {d_str}: feil: {e}")

    print(f"Ferdig {area}. La til totalt {total} rader. Fil: {path}")


if __name__ == "__main__":
    # laster siste 30 dager for de 5 områdene
    for i in AREAS:
        today = date.today()
        start = today - timedelta(days=30)
        collect(i, start, today)