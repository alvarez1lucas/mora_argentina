"""Cartera de la industria de fondos comunes de inversión (CAFCI, resumen mensual en PDF).

Sirve para medir la exposición al Estado fuera de los bancos: los FCI (por donde pasan también
los saldos de las billeteras virtuales y buena parte de la inversión minorista vía brokers)
compran Lecap, Boncap y otros títulos públicos.

Cada resumen mensual trae, por tipo de fondo, una tabla de "Evolución de las principales
tenencias por clase de activos" que cierra con la fila "Patrimonio ...": la última columna es el
mes del informe y las anteriores, el cierre de cada año previo (tres años, o más en los informes
de enero). Se toma la
industria total, Mercado de Dinero (money market) y Renta Fija. Cifras en millones de pesos.

Los PDF pesan 10-16 MB: se baja sólo lo que falta y se borran después de leerlos.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import pypdf

from mora.config import path, settings
from mora.ingest.http import download

BLOQUES = {"Patrimonio Industria FCIs": "industria", "Patrimonio Fondos Mercado de Dinero": "money_market",
           "Patrimonio Fondos de Renta Fija": "renta_fija"}
ACTIVOS = {"Títulos Públicos": "titulos_publicos", "Deuda Nacional": "deuda_nacional",
           "Operaciones a Plazo": "operaciones_plazo", "Disponibilidades": "disponibilidades"}
_SERIE = r"((?:-?\$ ?-?[\d.]+\s+)+-?\$ ?-?[\d.]+)"  # dos o más columnas


def _valores(cols: str) -> list[float]:
    """Valores '$ 1.234.567' de la fila (millones de pesos), del año más viejo al del informe."""
    return [float(x.replace(".", "")) for x in re.findall(r"-?[\d.]+", cols.replace("$ ", "$").replace("$", ""))]


def parse_texto(texto: str) -> dict[str, list[float]]:
    """Tenencias por bloque (industria, money market, renta fija): una lista por fila con el mismo mes
    de cada año; el último valor es el mes del informe."""
    lineas = [re.sub(r"\s+", " ", x).strip() for x in texto.splitlines()]
    out, inicio = {}, 0
    for i, linea in enumerate(lineas):
        for rotulo, bloque in BLOQUES.items():
            m = re.match(re.escape(rotulo) + r" " + _SERIE + r"$", linea)
            if not m or f"{bloque}_patrimonio" in out:
                continue
            out[f"{bloque}_patrimonio"] = _valores(m.group(1))
            # la tabla de tenencias es la última antes del total (antes puede haber otras, como la
            # de variación anual absoluta): se queda la última coincidencia del bloque
            for previa in lineas[inicio:i]:
                for activo, col in ACTIVOS.items():
                    a = re.match(re.escape(activo) + r" " + _SERIE + r"$", previa)
                    if a:
                        out[f"{bloque}_{col}"] = _valores(a.group(1))
        if re.match(r"Patrimonio .*" + _SERIE + r"$", linea):
            inicio = i + 1
    return out


def parse_pdf(archivo: Path) -> dict[str, list[float]]:
    texto = "\n".join(p.extract_text() or "" for p in pypdf.PdfReader(archivo).pages)
    return parse_texto(texto)


def serie(cache: dict[str, dict[str, list[float]]]) -> pd.DataFrame:
    """Tabla mensual desde los informes leídos ({"AAAA-MM": filas}).

    En cada fila la última columna es el mes del informe y las anteriores son el cierre (diciembre)
    de los años previos. El dato del propio informe tiene prioridad; los diciembres cuyo informe no
    se pudo leer (en algunos meses CAFCI publicó las tablas como imagen) se completan con la columna
    de cierre de informes posteriores. Los demás meses ilegibles quedan sin dato.
    """
    valores: dict[tuple[pd.Timestamp, str], tuple[int, float]] = {}
    for clave, filas in cache.items():
        informe = pd.Timestamp(clave + "-01")
        for col, vals in filas.items():
            for atras, v in enumerate(reversed(vals)):
                fecha = informe if atras == 0 else pd.Timestamp(year=informe.year - atras, month=12, day=1)
                previo = valores.get((fecha, col))
                if previo is None or atras < previo[0]:  # gana el informe más cercano al mes
                    valores[(fecha, col)] = (atras, v)
    if not valores:
        return pd.DataFrame(columns=["fecha"])
    s = pd.Series({k: v[1] for k, v in valores.items()})
    df = s.unstack().rename_axis("fecha").reset_index()
    return df[df["fecha"] >= pd.Timestamp(settings()["cafci"]["inicio"])].sort_values("fecha").reset_index(drop=True)


def update(out_file: Path, cache_file: Path, hoy: pd.Timestamp | None = None) -> pd.DataFrame:
    """Lee los resúmenes que falten desde `inicio` y rearma la serie mensual.

    `cache_file` (JSON chico, versionado) guarda lo leído de cada informe, para no volver a bajar
    los PDF. Los informes ilegibles quedan marcados como vacíos y su PDF en data/raw/cafci/.
    """
    cfg = settings()["cafci"]
    hoy = (hoy or pd.Timestamp.today()).normalize()
    cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
    for mes in pd.date_range(cfg["inicio"], hoy, freq="MS"):
        clave = f"{mes:%Y-%m}"
        if clave in cache:
            continue
        destino = path("raw") / "cafci" / f"{mes:%Y%m}01_Resumen_Industria.pdf"
        try:
            download(cfg["url"].format(yyyymm=f"{mes:%Y%m}"), destino)
        except Exception:  # el resumen del mes todavía no se publicó (o el servidor no lo tiene)
            continue
        filas = parse_pdf(destino)
        if "industria_titulos_publicos" in filas:
            destino.unlink()
        else:
            print(f"cafci {clave}: tablas sin texto, mes sin dato salvo diciembre (PDF en {destino})")
        cache[clave] = filas
        cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    out = serie(cache)
    out.to_csv(out_file, index=False, date_format="%Y-%m-%d")
    return out
