"""Información de Entidades Financieras (BCRA): panel mensual por entidad.

Cada mes el BCRA publica un 7z (`YYYYMMd.7z`). De cada archivo se extrae:

- `Tec_Cont/indicad`: indicadores (A16 = irregularidad de la cartera de consumo, etc.).
- `Tec_Cont/esd`: Estado de Situación de Deudores (cartera de consumo por situación 1-5).

En ambos, la 5ta columna numérica es el mes del archivo: las anteriores son
diciembre de los dos años previos y los dos meses anteriores. Por eso un
panel mensual necesita un archivo por mes.

- `Tec_Cont/bal_hist/balhist.txt`: balance histórico de todas las entidades y cuentas
  desde 1994. Basta leerlo del archivo más reciente.
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

import pandas as pd
import py7zr

from mora.config import path, settings
from mora.ingest.http import download, get_json

# Columnas de indicad/esd: entidad, nombre, fecha, código de línea, descripción, 5 valores...
_COL_ENTIDAD, _COL_NOMBRE, _COL_FECHA, _COL_CODIGO = 0, 1, 2, 3
_COL_VALOR_MES = 9
_MEMBER_RE = re.compile(r"Tec_Cont/(indicad|esd)/(completo|AA\d{3})\.txt$", re.I)
_BALHIST_RE = re.compile(r"Tec_Cont/bal_hist/balhist\.txt$", re.I)


def available_months() -> list[str]:
    """Meses publicados (YYYYMM) desde `first_month`, en orden ascendente."""
    cfg = settings()["entidades"]
    payload = get_json(cfg["api_url"], params={"action": "fechas", "lang": "es"})
    first = cfg["first_month"].replace("-", "")
    months = sorted(f["value"] for f in payload["data"]["fechas"])
    return [m for m in months if m >= first]


def download_month(yyyymm: str) -> Path:
    url = settings()["entidades"]["file_url"].format(yyyymm=yyyymm)
    return download(url, path("raw") / "entidades" / f"{yyyymm}d.7z")


def _read_members(archive: Path, pattern: re.Pattern) -> dict[str, bytes]:
    with py7zr.SevenZipFile(archive) as z:
        targets = [n for n in z.getnames() if pattern.search(n)]
    if not targets:
        return {}
    out_dir = path("interim") / "entidades" / archive.stem
    with py7zr.SevenZipFile(archive) as z:
        z.extract(path=out_dir, targets=targets)
    data = {t: (out_dir / t).read_bytes() for t in targets}
    for t in targets:
        (out_dir / t).unlink()
    return data


def parse_indicator_file(raw: bytes, yyyymm: str, keep: dict[str, str]) -> list[dict]:
    """Filas de indicad/esd -> registros del mes `yyyymm` para los códigos en `keep`."""
    reader = csv.reader(io.StringIO(raw.decode("latin-1")), delimiter="\t", quotechar='"')
    out = []
    for row in reader:
        if len(row) <= _COL_VALOR_MES or row[_COL_FECHA] != yyyymm:
            continue
        name = keep.get(row[_COL_CODIGO])
        if name is None:
            continue
        out.append(
            {
                "entidad": row[_COL_ENTIDAD],
                "nombre": row[_COL_NOMBRE].strip(),
                "fecha": pd.Timestamp(f"{yyyymm[:4]}-{yyyymm[4:]}-01"),
                "variable": name,
                "valor": pd.to_numeric(row[_COL_VALOR_MES], errors="coerce"),
            }
        )
    return out


def extract_month(archive: Path, yyyymm: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (panel ancho entidad x mes, tabla entidad -> nombre) para un archivo mensual."""
    cfg = settings()["entidades"]
    keep = {**cfg["indicadores"], **cfg["esd"]}
    records = []
    for raw in _read_members(archive, _MEMBER_RE).values():
        records.extend(parse_indicator_file(raw, yyyymm, keep))
    long = pd.DataFrame.from_records(records, columns=["entidad", "nombre", "fecha", "variable", "valor"])
    long = long.drop_duplicates(["entidad", "fecha", "variable"])
    wide = long.pivot(index=["entidad", "fecha"], columns="variable", values="valor").reset_index()
    wide.columns.name = None
    names = long[["entidad", "nombre"]].drop_duplicates("entidad").assign(ultimo_mes=yyyymm)
    return wide, names


def parse_balhist(raw: bytes, cuentas: dict[str, str], desde: str) -> pd.DataFrame:
    """Filtra balhist.txt (entidad, fecha, cuenta, saldo) a las cuentas configuradas."""
    reader = csv.reader(io.StringIO(raw.decode("latin-1")), delimiter="\t", quotechar='"')
    rows = [
        (r[0], r[1], cuentas[r[2]], float(r[3]))
        for r in reader
        if len(r) >= 4 and r[2] in cuentas and r[1] >= desde
    ]
    df = pd.DataFrame(rows, columns=["entidad", "yyyymm", "variable", "saldo"])
    df["fecha"] = pd.to_datetime(df.pop("yyyymm"), format="%Y%m")
    return df[["entidad", "fecha", "variable", "saldo"]]


def extract_balhist(archive: Path) -> pd.DataFrame:
    cfg = settings()["entidades"]
    members = _read_members(archive, _BALHIST_RE)
    if not members:
        raise FileNotFoundError(f"{archive.name} no contiene bal_hist/balhist.txt")
    desde = cfg["first_month"].replace("-", "")
    return parse_balhist(next(iter(members.values())), cfg["cuentas_balance"], desde)


def _read_csv(file: Path) -> pd.DataFrame | None:
    if not file.exists():
        return None
    return pd.read_csv(file, dtype={"entidad": str, "ultimo_mes": str})


def update_panel(out_dir: Path, max_months: int | None = None) -> pd.DataFrame:
    """Agrega al panel los meses publicados que falten y refresca el balance histórico.

    Escribe en `out_dir`: entidades_panel.csv, entidades_nombres.csv y entidades_balance.csv.
    """
    cfg = settings()["entidades"]
    panel_file = out_dir / "entidades_panel.csv"
    names_file = out_dir / "entidades_nombres.csv"
    balance_file = out_dir / "entidades_balance.csv"

    panel, names = _read_csv(panel_file), _read_csv(names_file)
    done = set(pd.to_datetime(panel["fecha"]).dt.strftime("%Y%m")) if panel is not None else set()
    months = available_months()
    pending = [m for m in months if m not in done]
    if max_months is not None:
        pending = pending[:max_months]
    need_balance = not balance_file.exists() or months[-1] in pending

    panels = [panel] if panel is not None else []
    name_tables = [names] if names is not None else []
    for yyyymm in pending:
        archive = download_month(yyyymm)
        wide, nm = extract_month(archive, yyyymm)
        panels.append(wide)
        name_tables.append(nm)
        if yyyymm == months[-1]:
            extract_balhist(archive).to_csv(balance_file, index=False)
            need_balance = False
        if not cfg["keep_archives"]:
            archive.unlink()
        print(f"entidades {yyyymm}: {len(wide)} entidades")

    if need_balance:
        archive = download_month(months[-1])
        extract_balhist(archive).to_csv(balance_file, index=False)
        if not cfg["keep_archives"]:
            archive.unlink()

    out = pd.concat(panels, ignore_index=True)
    out["fecha"] = pd.to_datetime(out["fecha"])
    out = out.sort_values(["fecha", "entidad"])
    out.to_csv(panel_file, index=False, date_format="%Y-%m-%d")
    nm = pd.concat(name_tables, ignore_index=True).sort_values("ultimo_mes").drop_duplicates("entidad", keep="last")
    nm.sort_values("entidad").to_csv(names_file, index=False)
    return out
