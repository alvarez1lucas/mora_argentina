import pandas as pd
import pytest

from mora.ingest.cafci import parse_texto, serie
from mora.ingest.pnfc import _numero

TEXTO = """Industria de Fondos Comunes de Inversión
Evolución de las Principales Tenencias por Clase de Activos
2023 2024 2025 2026
Títulos Públicos $ 6.052.519 $ 13.408.800 $ 13.899.740 $ 23.717.247
Deuda Nacional $ 5.374.804 $ 12.638.418 $ 12.149.082 $ 21.217.181
Patrimonio Industria FCIs $ 26.609.402 $ 57.918.413 $ 80.829.191 $ 115.088.436
Participación por Clase de Activo en la Variación anual absoluta
Títulos Públicos $ 299.313 $ 679.419 $ 473.449 $ 2.680.639
Fondos Mercado de Dinero
Títulos Públicos $ 1.928 $ 9.078 $ 18.445 $ 590
Patrimonio Fondos Mercado de Dinero $ 896.122 $ 1.694.855 $ 3.621.774 $ 10.975.209
"""


def test_parse_toma_la_tabla_de_cada_bloque():
    f = parse_texto(TEXTO)
    assert f["industria_titulos_publicos"][-1] == 23717247
    assert f["industria_patrimonio"] == [26609402, 57918413, 80829191, 115088436]
    # la tabla de variación anual que aparece antes no se confunde con la del money market
    assert f["money_market_titulos_publicos"][-1] == 590


def test_columnas_previas_son_diciembre(monkeypatch):
    monkeypatch.setattr("mora.ingest.cafci.settings", lambda: {"cafci": {"inicio": "2023-01-01"}})
    df = serie({"2026-09": parse_texto(TEXTO)}).set_index("fecha")
    assert df.loc["2026-09-01", "industria_titulos_publicos"] == 23717247
    assert df.loc["2025-12-01", "industria_titulos_publicos"] == 13899740
    assert pd.Timestamp("2025-09-01") not in df.index  # no se inventan meses


def test_dato_directo_tiene_prioridad(monkeypatch):
    monkeypatch.setattr("mora.ingest.cafci.settings", lambda: {"cafci": {"inicio": "2023-01-01"}})
    cache = {"2026-09": parse_texto(TEXTO), "2025-12": {"industria_titulos_publicos": [1.0, 2.0, 3.0, 99.0]}}
    df = serie(cache).set_index("fecha")
    assert df.loc["2025-12-01", "industria_titulos_publicos"] == 99.0


def test_numero_de_la_cita():
    assert _numero("$13,9 billones en febrero de 2026") == pytest.approx(13.9)
    assert _numero("$8 billones en enero de 2025") == 8.0
    assert _numero("mínimo histórico de 10,6%") == pytest.approx(10.6)


def test_carga_saca_el_aguinaldo(monkeypatch):
    import pandas as pd

    from mora import carga as c
    idx = pd.date_range("2024-01-01", periods=12, freq="MS")
    rem = pd.Series(100.0, index=idx)
    rem[idx.month.isin([6, 12])] = 150.0  # medio aguinaldo en junio y diciembre
    macro = pd.DataFrame({"remuneracion_privada": rem, "empleo_registrado": 1.0}, index=idx)
    bcra = pd.DataFrame({"prestamos_personales": 1.0, "prestamos_tarjetas": 1.0, "tasa_prestamos_personales": 12.0}, index=idx)
    monkeypatch.setattr(c, "load", lambda n: {"macro_mensual": macro, "bcra_mensual": bcra}[n])
    monkeypatch.setattr(c, "settings", lambda: {"carga": {"desde": "2024-01-01", "plazos_meses": [10]}})
    out = c.carga()
    # masa = 100 × 13/12 × 1000 / 1e6 todos los meses: el aguinaldo queda repartido
    assert out["masa_salarial"].nunique() == 1
    # cuota = 1 × (0,01 + 0,1) sobre esa masa
    assert out["cuota_personales_pct_masa_10m"].iloc[0] == pytest.approx(100 * 0.11 / (100 * 13 / 12 / 1000))
