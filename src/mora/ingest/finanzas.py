"""Deuda del Tesoro (Secretaría de Finanzas): stock en moneda local, colocaciones y vencimientos, capitalización.

Fuente: boletín mensual de la deuda bruta de la Administración Central (Excel, serie mensual desde
2019, en millones de dólares). La URL del archivo cambia cada mes: se toma de la página de datos.

- Hoja A.3: deuda en situación de pago normal por moneda (moneda local, CER y no CER).
- Hoja A.4: flujos por instrumento. Se suman los instrumentos de mercado en pesos (los que se licitan:
  LECAP, LEFI, BONCAP, BONCER, BONTE, BONAR en pesos, TAMAR, duales y letras dollar-linked que se pagan
  en pesos) en emisiones y en amortizaciones. Quedan afuera las letras intra sector público (ANSES,
  FGS, AFIP, fondos fiduciarios, etc.), los adelantos del BCRA y los pagarés. Con eso se mide el
  rollover del mercado en pesos: colocado / vencido. Incluye canjes, que inflan ambos lados.
- También de A.4: capitalización de intereses y variación por CER (toda la deuda).
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from mora.config import path, settings
from mora.ingest.http import download, session

MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}
# Familias de instrumentos de mercado en pesos (primera palabra de la descripción)
MERCADO = {"LECAP", "LEFI", "LETES", "BONCAP", "BONCER", "BONCER-BTS", "BONTE", "BONAR", "BONO", "BOTAPO", "BONAD",
           "DISCOUNT", "PAR", "LETAM", "LELINK"}


def url_boletin() -> str:
    """Busca en la página de datos mensuales el enlace al Excel vigente."""
    html = session().get(settings()["finanzas"]["pagina"], timeout=settings()["http"]["timeout"]).text
    enlaces = re.findall(r'href="([^"]*boletin_mensual[^"]*\.xlsx)"', html)
    if not enlaces:
        raise FileNotFoundError("No se encontró el Excel del boletín mensual de deuda")
    u = enlaces[0]
    return u if u.startswith("http") else "https://www.argentina.gob.ar" + u


def _fecha(v) -> pd.Timestamp | None:
    if isinstance(v, pd.Timestamp) or hasattr(v, "year"):
        return pd.Timestamp(v).to_period("M").to_timestamp()
    m = re.match(r"([a-z]{3})-(\d{2})", str(v).strip().lower())
    return pd.Timestamp(2000 + int(m.group(2)), MESES[m.group(1)], 1) if m else None


def _columnas_fecha(fila: pd.Series) -> dict[int, pd.Timestamp]:
    return {j: f for j, v in fila.items() if (f := _fecha(v)) is not None}


def es_mercado_pesos(descripcion: str) -> bool:
    """Instrumento de mercado pagadero en pesos (no 'U$S' a secas, no letras intra sector público)."""
    d = descripcion.strip()
    en_pesos = re.search(r"(?<!U)\$", d) is not None or "pagan en pesos" in d.lower()
    if not en_pesos:
        return False
    familia = re.split(r"[/ ]", d)[0].upper()
    if familia == "LETRA":  # 'LETRA - ...' es de mercado (lelink); 'LETRA ANSES - $' etc. es intra sector público
        return d.upper().startswith("LETRA - ") or d.upper().startswith("LETRA/")
    return familia in MERCADO


def parse(archivo: Path) -> pd.DataFrame:
    a3 = pd.read_excel(archivo, sheet_name="A.3", header=None)
    a4 = pd.read_excel(archivo, sheet_name="A.4", header=None)
    lab3, lab4 = a3[1].astype(str).str.strip(), a4[1].astype(str).str.strip()

    fila_hdr3 = next(i for i in range(len(a3)) if len(_columnas_fecha(a3.iloc[i])) > 12)
    cols3 = _columnas_fecha(a3.iloc[fila_hdr3])

    def fila3(texto: str) -> pd.Series:
        i = lab3[lab3.str.startswith(texto)].index[0]  # primera aparición: bloque por moneda y tasa
        return pd.Series({f: a3.iloc[i, j] for j, f in cols3.items()}, dtype=float)

    fila_hdr4 = next(i for i in range(len(a4)) if len(_columnas_fecha(a4.iloc[i])) > 12)
    cols4 = _columnas_fecha(a4.iloc[fila_hdr4])
    ini_emis = lab4[lab4.str.startswith("1 - Financiamiento")].index[0]
    ini_amort = lab4[lab4.str.startswith("2 - Amortizaciones")].index[0]
    fin_amort = lab4[lab4.str.startswith("a) Operaciones netas")].index[0]

    def suma(desde: int, hasta: int) -> pd.Series:
        filas = [i for i in range(desde + 1, hasta) if es_mercado_pesos(lab4[i])]
        bloque = a4.iloc[filas, list(cols4)].apply(pd.to_numeric, errors="coerce").fillna(0)
        return pd.Series(bloque.sum().values, index=list(cols4.values()))

    def fila4(texto: str) -> pd.Series:
        i = lab4[lab4.str.startswith(texto)].index[0]
        return pd.Series({f: a4.iloc[i, j] for j, f in cols4.items()}, dtype=float)

    out = pd.DataFrame({
        "deuda_moneda_local_usd": fila3("Moneda local"),
        "deuda_no_cer_usd": fila3("Deuda no ajustable por CER"),
        "deuda_cer_usd": fila3("Deuda ajustable por CER"),
        "deuda_total_pago_normal_usd": fila3("DEUDA BRUTA EN SITUACIÓN DE PAGO NORMAL"),
        "emisiones_mercado_pesos_usd": suma(ini_emis, ini_amort),
        "amortizaciones_mercado_pesos_usd": suma(ini_amort, fin_amort),
        "capitalizacion_usd": fila4("Capitalización de Bonos, Letras"),
        "variacion_cer_usd": fila4("Variación de la deuda ajustable por CER"),
    })
    out.index.name = "fecha"
    return out.sort_index()


def update(out_file: Path) -> pd.DataFrame:
    destino = path("raw") / "finanzas" / "boletin_mensual_deuda.xlsx"
    download(url_boletin(), destino)
    df = parse(destino)
    df.to_csv(out_file, date_format="%Y-%m-%d")
    return df
