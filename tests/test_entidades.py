import numpy as np
import pandas as pd

from mora.config import settings
from mora.ingest.entidades import account_map, compile_patterns, parse_balhist, parse_indicator_file


def _line(*fields):
    return "\t".join(f'"{f}"' if isinstance(f, str) else str(f) for f in fields)


A16 = "A16 - Cartera Irregular Consumo Sector Privado (%)"
INDICAD = "\n".join(
    [
        # 5 valores de la entidad (dic t-2, dic t-1, m-2, m-1, m) + grupo + top10 + sistema + formato
        _line("00007", "BANCO DE GALICIA", "202607", "800010200160", A16,
              3.49, 14.65, 17.42, 17.91, 18.43, 13.57, 14.34, 12.87, "P"),
        _line("00007", "BANCO DE GALICIA", "202607", "800010200999", "Otro indicador", 1, 2, 3, 4, 5, 6, 7, 8, "P"),
        # fila de otro mes: se descarta
        _line("00007", "BANCO DE GALICIA", "202606", "800010200160", A16, 1, 1, 1, 1, 99, 1, 1, 1, "P"),
        _line("AA000", "SISTEMA FINANCIERO", "202607", "800010200160", A16,
              4.1, 12.0, 12.5, 12.7, 12.87, 12.87, 12.87, 12.87, "P"),
        _line("00011", "BANCO X", "202607", "800010200160", A16, 0, 0, 0, 0, 99999, 0, 0, 0, "P"),
    ]
).encode("latin-1")

PATTERNS = compile_patterns({"a16_irregular_consumo": "^A16 - Cartera Irregular Consumo"})


def test_parse_indicator_file_takes_current_month_column():
    df = pd.DataFrame(parse_indicator_file(INDICAD, "202607", PATTERNS)).set_index("entidad")
    assert df.loc["00007", "valor"] == 18.43
    assert df.loc["AA000", "valor"] == 12.87
    assert (df["fecha"] == pd.Timestamp("2026-07-01")).all()


def test_parse_indicator_file_sentinel_is_nan():
    df = pd.DataFrame(parse_indicator_file(INDICAD, "202607", PATTERNS)).set_index("entidad")
    assert np.isnan(df.loc["00011", "valor"])


def test_parse_indicator_file_recovers_previous_month():
    df = pd.DataFrame(parse_indicator_file(INDICAD, "202607", PATTERNS, rezago=1)).set_index("entidad")
    assert df.loc["00007", "valor"] == 17.91
    assert df.loc["00007", "fecha"] == pd.Timestamp("2026-06-01")


def test_matches_by_description_not_code():
    # mismo código, otra descripción (esquema viejo): no debe tomarse como A16
    raw = _line("00007", "B", "201101", "800010200160", "A16 - Otra cosa", 0, 0, 0, 0, 5, 0, 0, 0, "P").encode("latin-1")
    assert parse_indicator_file(raw, "201101", PATTERNS) == []


def test_configured_patterns_cover_both_schemes():
    pats = compile_patterns(settings()["entidades"]["variables"])

    def match(desc):
        return [n for n, rx in pats.items() if rx.search(desc)]

    assert match("A16 - Cartera Irregular Consumo Sector Privado (%)") == ["a16_irregular_consumo"]
    assert match("A12 - Cartera de Consumo irregular sobre financiaciones") == ["a12_irregular_consumo_viejo"]
    assert match("C.CON.Sit.3: Riesgo medio (%)") == ["esd_consumo_sit3"]
    assert match("C.CON.Sit.3: Cumplimiento deficiente") == ["esd_consumo_sit3"]
    assert match("C.CON.G.Sit.3: Riesgo medio") == []  # garantizada: no es la cartera total
    assert match("CARTERA DE CONSUMO O VIVIENDA ($)") == ["esd_consumo_saldo"]


def test_parse_indicator_file_decodes_latin1():
    raw = _line("00007", "BANCO ÑANDÚ", "202607", "1", A16, 0, 0, 0, 0, 5, 0, 0, 0, "N").encode("latin-1")
    assert parse_indicator_file(raw, "202607", PATTERNS)[0]["nombre"] == "BANCO ÑANDÚ"


def test_account_map_prefix_and_description_filters():
    catalog = {
        "121003": "TÍTULOS PÚBLICOS - MEDICIÓN A VALOR",
        "121017": "TÍTULOS PRIVADOS - ACCIONES",
        "121024": "LETRAS DEL BCRA - MEDICIÓN A VALOR",
        "131731": "PERSONALES",
        "141101": "RESPONSAB.DE TERCEROS POR PASES",
    }
    rules = {
        "activo_total": {"prefijo": "1"},
        "titulos": {"prefijo": "12", "incluye": "P[UÚ]B|BCRA", "excluye": "PRIVAD"},
        "pases": {"prefijo": "14", "incluye": "PASE"},
    }
    m = account_map(catalog, {"131731": "prestamos_personales"}, rules)
    assert m["131731"] == ["prestamos_personales", "activo_total"]
    assert sorted(m["121003"]) == ["activo_total", "titulos"]
    assert m["121017"] == ["activo_total"]
    assert sorted(m["141101"]) == ["activo_total", "pases"]


def test_parse_balhist_sums_and_filters_dates():
    raw = "\n".join(
        [
            _line("00007", "201012", "121003", 100),
            _line("00007", "201101", "121003", 110),
            _line("00007", "201101", "121024", 40),
            _line("00007", "201101", "999999", 5),
        ]
    ).encode("latin-1")
    mapping = {"121003": ["titulos"], "121024": ["titulos"]}
    df = parse_balhist(raw, mapping, desde="201101")
    assert len(df) == 1
    assert df["titulos"].item() == 150
    assert df["fecha"].item() == pd.Timestamp("2011-01-01")
