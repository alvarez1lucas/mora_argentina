import datetime as dt

import numpy as np

from mora.ingest.bcra_anexo import _slug, familias_por_linea, parse_sheet

D1, D2 = dt.datetime(2026, 7, 1), dt.datetime(2026, 8, 1)
SHEET = "Calidad de Cartera (por líneas)"

ROWS = [
    ("Apertura de Calidad de la Cartera Crediticia", None, None),
    ("Sistema financiero", None, None),
    ('Ver referencias en la hoja "Metodología y Referencias"', None, None),
    ("2. Familias - Total", None, None),
    (".. Ratio de irregularidad", None, None),
    ("En porcentaje", D1, D2),
    ("Cartera irregular total", 12.94, 12.81),
    ("Personales", 16.71, 17.04),
    ("Con garantía hipotecaria", 1.61, "-"),
    ("Fuente: BCRA", None, None),
    (None, None, None),
    (".. Saldo total de financiaciones", None, None),
    ("En mill. de $ corrientes", D1, D2),
    ("Cartera total", 70934264.02, 72156301.6),
    ("Personales", 22281111.84, 22542014.03),
    ("Fuente: BCRA", None, None),
    ("3. Empresas - Total", None, None),
    (".. Ratio de irregularidad", None, None),
    ("En porcentaje", D1, D2),
    ("Cartera irregular total", 3.62, 3.80),
    ("    Indentado", 1.0, 2.0),
    ("Fuente: BCRA", None, None),
]


def test_parse_sheet_assigns_sections_and_metrics():
    df = parse_sheet(ROWS, hoja=SHEET)
    assert set(df["seccion"]) == {"2. Familias - Total", "3. Empresas - Total"}
    fam = df[df["seccion"] == "2. Familias - Total"]
    assert set(fam["metrica"]) == {"Ratio de irregularidad", "Saldo total de financiaciones"}
    v = fam[(fam["concepto"] == "Personales") & (fam["metrica"] == "Ratio de irregularidad") & (fam["fecha"] == D2)]
    assert v["valor"].item() == 17.04


def test_parse_sheet_non_numeric_is_nan_and_indent_flag():
    df = parse_sheet(ROWS, hoja=SHEET)
    hip = df[(df["concepto"] == "Con garantía hipotecaria") & (df["fecha"] == D2)]
    assert np.isnan(hip["valor"].item())
    assert df.loc[df["concepto"] == "Indentado", "indentado"].all()
    assert not df.loc[df["concepto"] == "Personales", "indentado"].any()


def test_familias_por_linea_wide():
    wide = familias_por_linea(parse_sheet(ROWS, hoja=SHEET))
    assert wide.loc[D1, "ratio_cartera_irregular_total"] == 12.94
    assert wide.loc[D2, "saldo_personales"] == 22542014.03
    assert "ratio_hipotecaria" in wide.columns


def test_slug():
    assert _slug("Tarjetas de crédito") == "tarjetas_de_credito"
    assert _slug("Con garantía prendaria") == "prendaria"


def test_every_configured_sheet_has_output_file():
    from mora.config import settings
    from mora.ingest.bcra_anexo import ARCHIVOS_POR_HOJA

    cfg = settings()["bcra_anexo"]
    sheets = {cfg["sheet_lineas"], cfg["sheet_grupos"], cfg["sheet_balance"]}
    assert sheets == set(ARCHIVOS_POR_HOJA)
