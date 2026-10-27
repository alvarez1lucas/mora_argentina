"""Información de Entidades Financieras (BCRA): panel mensual por entidad.

Cada mes el BCRA publica un 7z (`YYYYMMd.7z`). De cada archivo se extrae:

- `Tec_Cont/indicad`: indicadores (A16 = irregularidad de la cartera de consumo, etc.).
- `Tec_Cont/esd`: Estado de Situación de Deudores (cartera de consumo por situación 1-5).

En ambos, la 5ta columna numérica es el mes del archivo y la 4ta el mes anterior; las
dos primeras son diciembre de los dos años previos. Por eso un panel mensual necesita
un archivo por mes. Los pocos meses publicados sólo en PDF se recuperan de la columna
"mes anterior" del archivo siguiente.

- `Tec_Cont/bal_hist/balhist.txt`: balance histórico de todas las entidades y cuentas
  desde 1994. Basta leerlo del archivo más reciente.
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import py7zr

from mora.config import path, settings
from mora.ingest.http import download, get_json

# Columnas de indicad/esd: entidad, nombre, fecha, código de línea, descripción, 5 valores...
_COL_ENTIDAD, _COL_NOMBRE, _COL_FECHA, _COL_DESCRIPCION = 0, 1, 2, 4
# Columna del mes del archivo (rezago 0) y del mes anterior (rezago 1)
_COL_POR_REZAGO = {0: 9, 1: 8}
_MEMBER_RE = re.compile(r"Tec_Cont/(indicad|esd)/(completo|AA\d{3})\.txt$", re.I)
_BALHIST_RE = re.compile(r"Tec_Cont/(bal_hist/balhist|cuentas/cuentas)\.txt$", re.I)


def available_months() -> list[str]:
    """Meses publicados (YYYYMM) desde `first_month`, en orden ascendente."""
    cfg = settings()["entidades"]
    payload = get_json(cfg["api_url"], params={"action": "fechas", "lang": "es"})
    first = cfg["first_month"].replace("-", "")
    months = sorted(f["value"] for f in payload["data"]["fechas"])
    return [m for m in months if m >= first]


def archive_url(yyyymm: str) -> str | None:
    """URL del 7z de datos abiertos de un mes, o None si ese mes sólo se publicó en PDF."""
    cfg = settings()["entidades"]
    payload = get_json(cfg["api_url"], params={"action": "archivos", "desde": yyyymm, "lang": "es"})
    for f in payload["data"]["archivos"]:
        if f["url"].endswith(".7z"):
            return urljoin(cfg["api_url"], f["url"])
    return None


def download_month(yyyymm: str, url: str) -> Path:
    """Baja el 7z del mes (reutiliza el archivo si ya está en disco: los meses cerrados no cambian)."""
    dest = path("raw") / "entidades" / f"{yyyymm}d.7z"
    return dest if dest.exists() else download(url, dest)


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


def _month_start(yyyymm: str) -> pd.Timestamp:
    return pd.Timestamp(f"{yyyymm[:4]}-{yyyymm[4:]}-01")


def compile_patterns(variables: dict[str, str]) -> dict[str, re.Pattern]:
    return {name: re.compile(rx, re.I) for name, rx in variables.items()}


def parse_indicator_file(
    raw: bytes,
    yyyymm: str,
    patterns: dict[str, re.Pattern],
    rezago: int = 0,
    sentinel: float | None = 99999,
) -> list[dict]:
    """Filas de indicad/esd del archivo del mes `yyyymm` -> registros de las variables en `patterns`.

    Cada variable se identifica por la descripción de la fila (no por el código, que cambió de
    significado en 2014). Con `rezago=1` toma la columna del mes anterior y le asigna esa fecha.
    El valor centinela se convierte en faltante.
    """
    col = _COL_POR_REZAGO[rezago]
    fecha = _month_start(yyyymm) - pd.DateOffset(months=rezago)
    reader = csv.reader(io.StringIO(raw.decode("latin-1")), delimiter="\t", quotechar='"')
    out = []
    for row in reader:
        if len(row) <= col or row[_COL_FECHA] != yyyymm:
            continue
        desc = row[_COL_DESCRIPCION].strip()
        name = next((n for n, rx in patterns.items() if rx.search(desc)), None)
        if name is None:
            continue
        valor = pd.to_numeric(row[col], errors="coerce")
        if sentinel is not None and valor == sentinel:
            valor = float("nan")
        out.append(
            {
                "entidad": row[_COL_ENTIDAD],
                "nombre": row[_COL_NOMBRE].strip(),
                "fecha": fecha,
                "variable": name,
                "valor": valor,
            }
        )
    return out


def extract_month(archive: Path, yyyymm: str, rezago: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (panel ancho entidad x mes, tabla entidad -> nombre) para un archivo mensual.

    La columna `rezago` del panel indica si el dato salió del archivo de su propio mes (0)
    o del archivo del mes siguiente (1).
    """
    cfg = settings()["entidades"]
    patterns = compile_patterns(cfg["variables"])
    records = []
    for raw in _read_members(archive, _MEMBER_RE).values():
        records.extend(parse_indicator_file(raw, yyyymm, patterns, rezago=rezago, sentinel=cfg["valor_centinela"]))
    long = pd.DataFrame.from_records(records, columns=["entidad", "nombre", "fecha", "variable", "valor"])
    long = long.drop_duplicates(["entidad", "fecha", "variable"])
    wide = long.pivot(index=["entidad", "fecha"], columns="variable", values="valor").reset_index()
    wide.columns.name = None
    wide.insert(2, "rezago", rezago)
    names = long[["entidad", "nombre"]].drop_duplicates("entidad").assign(ultimo_mes=yyyymm)
    return wide, names


def parse_catalog(raw: bytes) -> dict[str, str]:
    """cuentas.txt -> {código de cuenta: descripción}."""
    reader = csv.reader(io.StringIO(raw.decode("latin-1")), delimiter="\t", quotechar='"')
    return {r[0]: r[1].strip() for r in reader if len(r) >= 2}


def account_map(catalog: dict[str, str], cuentas: dict[str, str], agregados: dict[str, dict]) -> dict[str, list[str]]:
    """{código de cuenta: [variables a las que suma]}: cuentas individuales + agregados por prefijo."""
    out: dict[str, list[str]] = {c: [name] for c, name in cuentas.items()}
    for name, rule in agregados.items():
        inc = re.compile(rule["incluye"], re.I) if "incluye" in rule else None
        exc = re.compile(rule["excluye"], re.I) if "excluye" in rule else None
        for code, desc in catalog.items():
            if not code.startswith(rule["prefijo"]):
                continue
            if inc and not inc.search(desc):
                continue
            if exc and exc.search(desc):
                continue
            out.setdefault(code, []).append(name)
    return out


def parse_balhist(raw: bytes, mapping: dict[str, list[str]], desde: str) -> pd.DataFrame:
    """balhist.txt (entidad, fecha, cuenta, saldo) -> panel ancho entidad x mes con las variables de `mapping`."""
    totals: dict[tuple[str, str, str], float] = {}
    reader = csv.reader(io.StringIO(raw.decode("latin-1")), delimiter="\t", quotechar='"')
    for r in reader:
        if len(r) < 4 or r[1] < desde or r[2] not in mapping:
            continue
        saldo = float(r[3])
        for name in mapping[r[2]]:
            key = (r[0], r[1], name)
            totals[key] = totals.get(key, 0.0) + saldo
    long = pd.DataFrame([(*k, v) for k, v in totals.items()], columns=["entidad", "yyyymm", "variable", "saldo"])
    long["fecha"] = pd.to_datetime(long.pop("yyyymm"), format="%Y%m")
    wide = long.pivot(index=["entidad", "fecha"], columns="variable", values="saldo").reset_index()
    wide.columns.name = None
    return wide.sort_values(["fecha", "entidad"])


def extract_balhist(archive: Path) -> pd.DataFrame:
    cfg = settings()["entidades"]
    members = _read_members(archive, _BALHIST_RE)
    balhist = next((v for k, v in members.items() if k.lower().endswith("balhist.txt")), None)
    catalog = next((v for k, v in members.items() if k.lower().endswith("cuentas.txt")), None)
    if balhist is None or catalog is None:
        raise FileNotFoundError(f"{archive.name} no contiene bal_hist/balhist.txt y cuentas/cuentas.txt")
    mapping = account_map(parse_catalog(catalog), cfg["cuentas_balance"], cfg["agregados_balance"])
    desde = cfg["first_month"].replace("-", "")
    return parse_balhist(balhist, mapping, desde)


def _read_csv(file: Path, dates: bool = False) -> pd.DataFrame | None:
    if not file.exists():
        return None
    return pd.read_csv(file, dtype={"entidad": str, "ultimo_mes": str}, parse_dates=["fecha"] if dates else None)


def _save(panels: list[pd.DataFrame], names: list[pd.DataFrame], panel_file: Path, names_file: Path) -> pd.DataFrame:
    out = pd.concat(panels, ignore_index=True)
    out["fecha"] = pd.to_datetime(out["fecha"])
    out = out.sort_values(["fecha", "entidad"])
    out.to_csv(panel_file, index=False, date_format="%Y-%m-%d")
    nm = pd.concat(names, ignore_index=True).sort_values("ultimo_mes").drop_duplicates("entidad", keep="last")
    nm.sort_values("entidad").to_csv(names_file, index=False)
    return out


def update_panel(
    out_dir: Path,
    max_months: int | None = None,
    keep_archives: bool | None = None,
    rebuild: bool = False,
) -> pd.DataFrame:
    """Agrega al panel los meses publicados que falten y refresca el balance histórico.

    Escribe en `out_dir`: entidades_panel.csv, entidades_nombres.csv y entidades_balance.csv.
    El panel se guarda después de cada mes, así una corrida cortada no pierde lo avanzado.
    `rebuild=True` descarta el panel existente (los 7z conservados en disco se reutilizan).
    """
    cfg = settings()["entidades"]
    keep = cfg["keep_archives"] if keep_archives is None else keep_archives
    panel_file = out_dir / "entidades_panel.csv"
    names_file = out_dir / "entidades_nombres.csv"
    balance_file = out_dir / "entidades_balance.csv"
    if rebuild:
        for f in (panel_file, names_file, balance_file):
            f.unlink(missing_ok=True)

    panel, names = _read_csv(panel_file, dates=True), _read_csv(names_file)
    done = set(panel["fecha"].dt.strftime("%Y%m")) if panel is not None else set()
    months = available_months()
    pending = [m for m in months if m not in done]
    if max_months is not None:
        pending = pending[:max_months]

    panels = [panel] if panel is not None else []
    name_tables = [names] if names is not None else []
    used_archives: set[Path] = set()
    for yyyymm in pending:
        rezago, source = 0, yyyymm
        url = archive_url(yyyymm)
        if url is None:
            nxt = months.index(yyyymm) + 1
            source = months[nxt] if nxt < len(months) else None
            url = archive_url(source) if source else None
            rezago = 1
        if url is None:
            print(f"entidades {yyyymm}: sin archivo (se reintenta en la próxima corrida)")
            continue
        archive = download_month(source, url)
        used_archives.add(archive)
        wide, nm = extract_month(archive, source, rezago=rezago)
        panels.append(wide)
        name_tables.append(nm)
        _save(panels, name_tables, panel_file, names_file)
        note = f" (recuperado de {source})" if rezago else ""
        print(f"entidades {yyyymm}: {len(wide)} entidades{note}")
        if not keep and rezago == 0:
            archive.unlink()
            used_archives.discard(archive)

    if not balance_file.exists() or months[-1] in pending:
        archive = download_month(months[-1], archive_url(months[-1]))
        used_archives.add(archive)
        extract_balhist(archive).to_csv(balance_file, index=False, date_format="%Y-%m-%d")

    if not keep:
        for archive in used_archives:
            archive.unlink(missing_ok=True)
    return pd.concat(panels, ignore_index=True) if panels else pd.DataFrame()
