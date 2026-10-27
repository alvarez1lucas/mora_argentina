"""API de Series de Tiempo de datos.gob.ar (INDEC).

Cada serie se pide por separado: si se piden juntas series de distinta frecuencia,
la API las lleva a la frecuencia más baja.
"""

from __future__ import annotations

import pandas as pd

from mora.config import settings
from mora.ingest.http import get_json

PAGE = 1000  # máximo que acepta la API por pedido


def fetch_series(series_id: str) -> pd.Series:
    cfg = settings()["datos_gob"]
    rows, start = [], 0
    while True:
        payload = get_json(cfg["base_url"], params={"ids": series_id, "limit": PAGE, "start": start, "format": "json"})
        page = payload.get("data", [])
        rows.extend(page)
        start += len(page)
        if not page or start >= payload.get("count", 0):
            break
    s = parse_payload({"data": rows}, name=series_id)
    if s.dropna().empty:
        raise ValueError(f"datos.gob.ar devolvió la serie {series_id} vacía")
    return s


def parse_payload(payload: dict, name: str) -> pd.Series:
    data = payload.get("data", [])
    if not data:
        return pd.Series(dtype=float, name=name)
    idx = pd.to_datetime([row[0] for row in data])
    vals = pd.to_numeric(pd.Series([row[1] for row in data]), errors="coerce").values
    return pd.Series(vals, index=idx, name=name).sort_index()


def frequency(s: pd.Series) -> str:
    step = s.index.to_series().diff().dt.days.median() if len(s) > 1 else 31
    if step < 7:
        return "diaria"
    return "trimestral" if step > 45 else "mensual"


def build_panel() -> dict[str, pd.DataFrame]:
    """Devuelve {'diaria': df, 'mensual': df, 'trimestral': df} según la frecuencia de cada serie."""
    groups: dict[str, dict[str, pd.Series]] = {"diaria": {}, "mensual": {}, "trimestral": {}}
    for name, sid in settings()["datos_gob"]["series"].items():
        s = fetch_series(sid)
        groups[frequency(s)][name] = s
    out = {}
    for key, cols in groups.items():
        if not cols:
            continue
        df = pd.DataFrame(cols).sort_index()
        df.index.name = "fecha"
        out[key] = df
    return out
