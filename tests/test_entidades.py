import pandas as pd

from mora.ingest.entidades import parse_balhist, parse_indicator_file


def _line(*fields):
    return "\t".join(f'"{f}"' if isinstance(f, str) else str(f) for f in fields)


INDICAD = "\n".join(
    [
        # 5 valores de la entidad (dic t-2, dic t-1, m-2, m-1, m) + grupo + top10 + sistema + formato
        _line("00007", "BANCO DE GALICIA", "202607", "800010200160", "A16 - Cartera Irregular Consumo",
              3.49, 14.65, 17.42, 17.91, 18.43, 13.57, 14.34, 12.87, "P"),
        _line("00007", "BANCO DE GALICIA", "202607", "800010200999", "Otro indicador",
              1, 2, 3, 4, 5, 6, 7, 8, "P"),
        # fila de otro mes: se descarta
        _line("00007", "BANCO DE GALICIA", "202606", "800010200160", "A16", 1, 1, 1, 1, 99, 1, 1, 1, "P"),
        _line("AA000", "SISTEMA FINANCIERO", "202607", "800010200160", "A16 - Cartera Irregular Consumo",
              4.1, 12.0, 12.5, 12.7, 12.87, 12.87, 12.87, 12.87, "P"),
    ]
).encode("latin-1")


def test_parse_indicator_file_takes_current_month_column():
    recs = parse_indicator_file(INDICAD, "202607", keep={"800010200160": "a16_irregular_consumo"})
    df = pd.DataFrame(recs)
    assert len(df) == 2
    assert df.set_index("entidad").loc["00007", "valor"] == 18.43
    assert (df["fecha"] == pd.Timestamp("2026-07-01")).all()
    assert set(df["variable"]) == {"a16_irregular_consumo"}


def test_parse_indicator_file_decodes_latin1():
    raw = _line("00007", "BANCO ÑANDÚ", "202607", "1", "x", 0, 0, 0, 0, 5, 0, 0, 0, "N").encode("latin-1")
    recs = parse_indicator_file(raw, "202607", keep={"1": "v"})
    assert recs[0]["nombre"] == "BANCO ÑANDÚ"


def test_parse_balhist_filters_accounts_and_dates():
    raw = "\n".join(
        [
            _line("00007", "201012", "711046", 100),
            _line("00007", "201101", "711046", 110),
            _line("00007", "201101", "999999", 5),
            _line("00011", "202607", "131731", 7.5),
        ]
    ).encode("latin-1")
    df = parse_balhist(raw, cuentas={"711046": "irrecuperables", "131731": "personales"}, desde="201101")
    assert len(df) == 2
    assert set(df["variable"]) == {"irrecuperables", "personales"}
    assert df["fecha"].min() == pd.Timestamp("2011-01-01")
