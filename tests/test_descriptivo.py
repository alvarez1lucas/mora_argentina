import numpy as np
import pandas as pd
import pytest

from mora.descriptivo import ajuste_por_castigos, irregular_consumo, normalize_esd_saldo

IDX = pd.date_range("2025-01-01", periods=13, freq="MS")


def test_ajuste_por_castigos_suma_flujo_a_numerador_y_denominador():
    irregular = pd.Series(10.0, index=IDX)
    cartera = pd.Series(100.0, index=IDX)
    castigos = pd.Series(np.r_[np.zeros(12), 5.0], index=IDX)
    row = ajuste_por_castigos(irregular, cartera, castigos, h=12).iloc[-1]
    assert row["ratio_oficial"] == pytest.approx(10.0)
    assert row["castigos_flujo"] == 5.0
    assert row["ratio_ajustado"] == pytest.approx(100 * 15 / 105)


def test_ajuste_por_castigos_ignora_bajas_de_la_cuenta_de_orden():
    castigos = pd.Series(np.r_[np.full(12, 10.0), 4.0], index=IDX)  # el stock baja: flujo negativo
    row = ajuste_por_castigos(pd.Series(10.0, index=IDX), pd.Series(100.0, index=IDX), castigos).iloc[-1]
    assert row["castigos_flujo"] == 0
    assert row["ratio_ajustado"] == pytest.approx(row["ratio_oficial"])


def test_normalize_esd_saldo_detecta_cambio_de_unidad():
    fechas = pd.to_datetime(["2018-01-01", "2018-02-01", "2018-03-01"])
    panel = pd.DataFrame(
        {
            "entidad": ["AA000"] * 3 + ["00007"] * 3,
            "fecha": list(fechas) * 2,
            "esd_consumo_saldo": [5_000_000.0, 5_100_000.0, 5_200.0, 500_000.0, 510_000.0, 520.0],
        }
    )
    out = normalize_esd_saldo(panel).set_index(["entidad", "fecha"])["esd_consumo_saldo"]
    assert out[("AA000", fechas[0])] == pytest.approx(5_000.0)
    assert out[("00007", fechas[1])] == pytest.approx(510.0)
    assert out[("00007", fechas[2])] == pytest.approx(520.0)


def test_irregular_consumo_requiere_las_tres_situaciones():
    p = pd.DataFrame({"esd_consumo_sit3": [1.0, 1.0], "esd_consumo_sit4": [2.0, np.nan], "esd_consumo_sit5": [3.0, 1.0]})
    s = irregular_consumo(p)
    assert s.iloc[0] == 6.0
    assert np.isnan(s.iloc[1])
