"""Anexo estadístico del Informe sobre Bancos (BCRA).

Fuente principal de la variable objetivo: irregularidad y saldos de financiaciones a
familias por línea (mensual desde 2010) e irregularidad por grupo de entidades.

Las hojas tienen bloques apilados con esta forma:

    <título de sección>            p. ej. "2. Familias - Total" o "Bancos públicos"
    .. <métrica>                   p. ej. ".. Ratio de irregularidad" (opcional)
    En porcentaje | fecha | fecha  fila de encabezado con las fechas
    <concepto>    | valor | valor
    ...
    Fuente: BCRA                   cierre del bloque
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import openpyxl
import pandas as pd

from mora.config import path, settings
from mora.ingest.http import download

_SKIP_TITLES = ("Fuente", "Ver ", "Apertura", "Calidad de Cartera")

# Hoja del anexo -> sufijo del archivo procesado (data/processed/anexo_<sufijo>.csv)
ARCHIVOS_POR_HOJA = {
    "Calidad de Cartera (por líneas)": "calidad_por_linea",
    "Calidad de Cartera": "calidad_por_grupo",
    "Estado de Sit. Financiera ($)": "balance_por_grupo",
}


def download_anexo() -> Path:
    cfg = settings()["bcra_anexo"]
    return download(cfg["url"], path("raw") / "bcra" / "informe-bancos-anexo.xlsx")


def parse_sheet(rows: list[tuple], hoja: str) -> pd.DataFrame:
    """Convierte una hoja de bloques apilados en formato largo."""
    records = []
    seccion = metrica = None
    fechas: dict[int, dt.datetime] | None = None
    unidad = None
    for row in rows:
        if not row or row[0] is None:
            continue
        label = str(row[0])
        stripped = label.strip()
        rest = [v for v in row[1:] if v is not None]
        date_cells = {j: v for j, v in enumerate(row) if j > 0 and isinstance(v, dt.datetime)}

        if stripped.startswith("Fuente"):
            fechas = None
            continue
        if date_cells and stripped.startswith("En "):
            fechas, unidad = date_cells, stripped
            continue
        if stripped.startswith(".."):
            metrica = stripped.lstrip(". ").strip()
            continue
        if fechas is None:
            if not rest and not stripped.startswith(_SKIP_TITLES):
                seccion, metrica = stripped, None
            continue

        for j, fecha in fechas.items():
            v = row[j] if j < len(row) else None
            records.append(
                {
                    "hoja": hoja,
                    "seccion": seccion,
                    "metrica": metrica,
                    "unidad": unidad,
                    "concepto": stripped,
                    "indentado": label != label.lstrip(),
                    "fecha": pd.Timestamp(fecha),
                    "valor": pd.to_numeric(v, errors="coerce"),
                }
            )
    df = pd.DataFrame.from_records(records)
    if df.empty:
        return df
    keys = ["hoja", "seccion", "metrica", "concepto", "indentado", "fecha"]
    return df.drop_duplicates(keys, keep="last").reset_index(drop=True)


def read_anexo(xlsx: Path) -> pd.DataFrame:
    cfg = settings()["bcra_anexo"]
    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    frames = [
        parse_sheet(list(wb[sheet].iter_rows(values_only=True)), hoja=sheet)
        for sheet in (cfg["sheet_lineas"], cfg["sheet_grupos"], cfg["sheet_balance"])
    ]
    wb.close()
    return pd.concat(frames, ignore_index=True)


def familias_por_linea(anexo: pd.DataFrame) -> pd.DataFrame:
    """Ratio de irregularidad (%) y saldo (millones de $ corrientes) de familias por línea, en formato ancho."""
    df = anexo[(anexo["hoja"] == settings()["bcra_anexo"]["sheet_lineas"]) & (anexo["seccion"] == "2. Familias - Total")]
    metric_key = {"Ratio de irregularidad": "ratio", "Saldo total de financiaciones": "saldo"}
    df = df.assign(var=df["metrica"].map(metric_key) + "_" + df["concepto"].map(_slug))
    wide = df.pivot_table(index="fecha", columns="var", values="valor", aggfunc="last")
    wide.columns.name = None
    return wide.sort_index()


def _slug(text: str) -> str:
    table = str.maketrans("áéíóúñ", "aeioun")
    return "_".join(text.lower().translate(table).replace("con garantia ", "").split())
