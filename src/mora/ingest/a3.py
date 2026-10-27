"""Futuros de dólar (DLR) de A3 Mercados: precio de ajuste, tasa implícita e interés abierto.

API pública de precios de cierre. Un registro por día y por contrato abierto. Sirve para medir
la intervención cambiaria vía futuros: la tasa implícita de devaluación, el "dólar sintético"
(tasa en pesos contra devaluación implícita) y el interés abierto, del que el BCRA llegó a
tener ~83% en sep-2025.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from mora.config import settings
from mora.ingest.http import get_json

COLUMNS = ["fecha", "contrato", "vencimiento", "ajuste", "tasa_implicita", "interes_abierto", "volumen"]


def fetch_range(desde: pd.Timestamp, hasta: pd.Timestamp) -> list[dict]:
    cfg = settings()["a3"]
    rows, page = [], 1
    while True:
        payload = get_json(
            cfg["url"],
            params={
                "product": "DLR",
                "from": desde.strftime("%Y-%m-%d"),
                "to": hasta.strftime("%Y-%m-%d"),
                "pageSize": cfg["page_size"],
                "page": page,
            },
        )
        data = payload.get("data", [])
        rows.extend(data)
        if not data or len(rows) >= payload.get("totalEntries", 0):
            return rows
        page += 1


def parse(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    df = pd.DataFrame(rows)
    # Sólo futuros mensuales DLRMMAAAA (se descartan opciones y otros símbolos)
    df = df[df["symbol"].str.fullmatch(r"DLR\d{6}") & df["optionType"].isna()]
    out = pd.DataFrame(
        {
            "fecha": pd.to_datetime(df["dateTime"]).dt.tz_localize(None).dt.normalize(),
            "contrato": df["symbol"],
            # vence el último día hábil del mes: se aproxima con el último día calendario
            "vencimiento": pd.to_datetime(df["symbol"].str[3:], format="%m%Y") + pd.offsets.MonthEnd(0),
            "ajuste": pd.to_numeric(df["settlement"], errors="coerce"),
            "tasa_implicita": pd.to_numeric(df["impliedRate"], errors="coerce"),
            "interes_abierto": pd.to_numeric(df["openInterest"], errors="coerce"),
            "volumen": pd.to_numeric(df["volume"], errors="coerce"),
        }
    )
    return out.drop_duplicates(["fecha", "contrato"]).sort_values(["fecha", "vencimiento"])


def update(out_file: Path, hoy: pd.Timestamp | None = None) -> pd.DataFrame:
    """Baja por meses lo que falte desde el último día guardado (o desde `inicio`)."""
    cfg = settings()["a3"]
    hoy = (hoy or pd.Timestamp.today()).normalize()
    hist = pd.read_csv(out_file, parse_dates=["fecha", "vencimiento"]) if out_file.exists() else None
    desde = hist["fecha"].max() + pd.Timedelta(days=1) if hist is not None else pd.Timestamp(cfg["inicio"])
    frames = [hist] if hist is not None else []
    for start in pd.date_range(desde.replace(day=1), hoy, freq="MS"):
        chunk_from = max(start, desde)
        chunk_to = min(start + pd.offsets.MonthEnd(0), hoy)
        frames.append(parse(fetch_range(chunk_from, chunk_to)))
    out = pd.concat([f for f in frames if f is not None and not f.empty], ignore_index=True)
    out = out.drop_duplicates(["fecha", "contrato"]).sort_values(["fecha", "vencimiento"])
    out.to_csv(out_file, index=False, date_format="%Y-%m-%d")
    return out
