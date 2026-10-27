"""Régimen de transparencia del BCRA: tasas y CFT ofrecidos por entidad y producto.

La API sólo devuelve la foto vigente (sin historia). Cada corrida agrega la foto del día a
`transparencia_entidades.csv`, así la serie de CFT se construye hacia adelante.

Se conservan medianas por entidad y producto de los productos en pesos a tasa fija informados
en los últimos `antiguedad_max_dias` (hay productos con datos de años atrás que no se actualizan).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from mora.config import settings
from mora.ingest.http import get_json

COLUMNS = ["fecha_descarga", "producto", "codigo_entidad", "entidad", "tipo", "n_productos", "tea_mediana", "cft_mediana"]


def fetch_product(producto: str) -> pd.DataFrame:
    cfg = settings()["transparencia"]
    payload = get_json(f"{cfg['base_url']}/Prestamos/{producto}")
    return pd.DataFrame(payload.get("results", []))


def summarize(raw: pd.DataFrame, producto: str, hoy: date, antiguedad_max_dias: int) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(columns=COLUMNS)
    df = raw.copy()
    df["fechaInformacion"] = pd.to_datetime(df["fechaInformacion"], errors="coerce")
    limite = pd.Timestamp(hoy) - pd.Timedelta(days=antiguedad_max_dias)
    df = df[
        (df["denominacion"] == "Pesos")
        & (df["tipoTasa"] == "Fija")
        & (df["tasaEfectivaAnualMaxima"] > 0)
        & (df["fechaInformacion"] >= limite)
    ]
    out = (
        df.groupby(["codigoEntidad", "descripcionEntidad"])
        .agg(
            n_productos=("tasaEfectivaAnualMaxima", "size"),
            tea_mediana=("tasaEfectivaAnualMaxima", "median"),
            cft_mediana=("costoFinancieroEfectivoTotalMaximo", "median"),
        )
        .reset_index()
        .rename(columns={"codigoEntidad": "codigo_entidad", "descripcionEntidad": "entidad"})
    )
    # Los códigos de entidades financieras son de 5 dígitos < 1000; los mayores son otros proveedores (PNFC)
    out["tipo"] = out["codigo_entidad"].map(lambda c: "entidad_financiera" if c < 1000 else "pnfc")
    out.insert(0, "producto", producto)
    out.insert(0, "fecha_descarga", pd.Timestamp(hoy))
    return out[COLUMNS]


def update(out_file: Path, hoy: date | None = None) -> pd.DataFrame:
    """Agrega la foto de hoy (si todavía no está) y devuelve el historial completo."""
    cfg = settings()["transparencia"]
    hoy = hoy or date.today()
    hist = pd.read_csv(out_file, parse_dates=["fecha_descarga"]) if out_file.exists() else pd.DataFrame(columns=COLUMNS)
    if not hist.empty and (hist["fecha_descarga"].dt.to_period("M") == pd.Period(hoy, "M")).any():
        return hist  # una foto por mes alcanza
    fotos = [summarize(fetch_product(p), p, hoy, cfg["antiguedad_max_dias"]) for p in cfg["productos"]]
    out = pd.concat([f for f in (hist, *fotos) if not f.empty], ignore_index=True)
    out.to_csv(out_file, index=False, date_format="%Y-%m-%d")
    return out
