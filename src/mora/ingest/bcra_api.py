"""API de Estadísticas del BCRA (v4.0): series monetarias, de crédito y tasas."""

from __future__ import annotations

import pandas as pd

from mora.config import settings
from mora.ingest.http import get_json

AGGS = {"last", "mean", "sum"}


def fetch_series(id_variable: int) -> pd.Series:
    """Serie completa (todas las fechas) de una variable, paginando la API."""
    cfg = settings()["bcra_api"]
    url = f"{cfg['base_url']}/{id_variable}"
    rows, offset = [], 0
    while True:
        payload = get_json(url, params={"limit": cfg["page_size"], "offset": offset})
        detalle = payload["results"][0]["detalle"] if payload["results"] else []
        rows.extend(detalle)
        total = payload["metadata"]["resultset"]["count"]
        offset += len(detalle)
        if not detalle or offset >= total:
            break
    return parse_detalle(rows, name=str(id_variable))


def parse_detalle(rows: list[dict], name: str) -> pd.Series:
    if not rows:
        return pd.Series(dtype=float, name=name)
    df = pd.DataFrame(rows)
    s = pd.Series(df["valor"].astype(float).values, index=pd.to_datetime(df["fecha"]), name=name)
    return s[~s.index.duplicated()].sort_index()


def to_monthly(s: pd.Series, agg: str) -> pd.Series:
    """Agrega a frecuencia mensual con índice en el primer día del mes.

    En series diarias, el último mes se descarta si la serie termina más de 4 días antes
    de fin de mes (mes en curso o serie discontinuada a mitad de mes: un promedio o una
    suma parcial sesgaría el dato).
    """
    if agg not in AGGS:
        raise ValueError(f"agg inválido: {agg}")
    if s.empty:
        return s
    m = getattr(s.resample("MS"), agg)()
    if agg == "sum":
        # resample.sum rellena meses sin datos con 0: los marcamos como faltantes
        counts = s.resample("MS").count()
        m = m.where(counts > 0)
    is_daily = len(s) > 1 and s.index.to_series().diff().dt.days.median() < 7
    last = s.index.max()
    if is_daily and last < last + pd.offsets.MonthEnd(0) - pd.Timedelta(days=4):
        m = m.iloc[:-1]
    return m


def build_panel() -> pd.DataFrame:
    """Todas las series configuradas, mensualizadas, en un DataFrame ancho."""
    out = {}
    for name, spec in settings()["bcra_api"]["series"].items():
        raw = fetch_series(spec["id"])
        if raw.empty:
            raise ValueError(f"La API del BCRA devolvió la variable {spec['id']} ({name}) vacía")
        out[name] = to_monthly(raw, spec["agg"])
    df = pd.DataFrame(out).sort_index()
    df.index.name = "fecha"
    return df
