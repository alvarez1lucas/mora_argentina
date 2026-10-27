"""IPC del INDEC por división COICOP (nacional y regiones), mensual desde dic-2016.

Insumo de los deflactores alternativos: con las divisiones se re-pondera el índice con la
estructura de gasto de la ENGHo 2017/18 (ver mora.deflactores).
"""

from __future__ import annotations

import io

import pandas as pd

from mora.config import settings
from mora.ingest.http import session


def fetch_divisiones() -> pd.DataFrame:
    cfg = settings()["indec_ipc"]
    r = session().get(cfg["url_divisiones"], timeout=settings()["http"]["timeout"])
    r.raise_for_status()
    return parse_divisiones(r.content)


def parse_divisiones(raw: bytes) -> pd.DataFrame:
    """CSV del INDEC (separador ';', decimal ',', latin-1) -> formato ancho: fecha x (región, código)."""
    df = pd.read_csv(io.BytesIO(raw), sep=";", encoding="latin-1", dtype={"Codigo": str})
    df = df.dropna(subset=["Descripcion"])
    df["indice"] = pd.to_numeric(df["Indice_IPC"].astype(str).str.replace(",", "."), errors="coerce")
    df["fecha"] = pd.to_datetime(df["Periodo"].astype(str), format="%Y%m")
    df["Codigo"] = df["Codigo"].str.zfill(2)
    wide = df.pivot_table(index="fecha", columns=["Region", "Codigo"], values="indice")
    wide.columns = [f"{reg.lower()}_{cod}" for reg, cod in wide.columns]
    wide.index.name = "fecha"
    return wide.sort_index()
