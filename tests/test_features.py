import numpy as np
import pandas as pd
import pytest

from mora.features import decompose_ratio_change, price_index

IDX = pd.date_range("2025-01-01", periods=24, freq="MS")


def test_decomposition_is_exact():
    rng = np.random.default_rng(0)
    d = pd.Series(100 * np.cumprod(1 + rng.uniform(0, 0.05, 24)), index=IDX)
    n = d * rng.uniform(0.02, 0.15, 24)
    dec = decompose_ratio_change(n, d, h=12).dropna()
    np.testing.assert_allclose(dec["efecto_numerador"] + dec["efecto_denominador"], dec["cambio_ratio"])


def test_pure_denominator_effect():
    # saldo irregular constante y cartera que se duplica: el ratio cae a la mitad, todo por denominador
    n = pd.Series(10.0, index=IDX)
    d = pd.Series(np.where(IDX >= "2026-01-01", 200.0, 100.0), index=IDX)
    row = decompose_ratio_change(n, d, h=12).loc["2026-01-01"]
    assert row["cambio_ratio"] == pytest.approx(-5.0)
    assert row["efecto_numerador"] == pytest.approx(0.0)
    assert row["efecto_denominador"] == pytest.approx(-5.0)


def test_price_index_backcasts_with_monthly_inflation():
    idx = pd.date_range("2016-10-01", periods=5, freq="MS")
    ipc = pd.Series([np.nan, np.nan, 100.0, 101.0, 103.02], index=idx)
    infl = pd.Series([2.0, 10.0, 1.0, 1.0, 2.0], index=idx)
    p = price_index(ipc, infl)
    # dic-16 = 100 con inflación de dic 1% -> nov-16 = 100/1.01; nov tuvo 10% -> oct = nov/1.10
    assert p.loc["2016-11-01", "ipc"] == pytest.approx(100 / 1.01)
    assert p.loc["2016-10-01", "ipc"] == pytest.approx(100 / 1.01 / 1.10)
    assert p.loc["2016-12-01", "ipc"] == 100.0
    assert p["ipc_empalmado"].tolist() == [True, True, False, False, False]


def test_tasas_reales_ex_post_uses_following_inflation():
    from mora.features import tasas_reales

    idx = pd.date_range("2025-01-01", periods=36, freq="MS")
    infl = pd.Series(np.where(idx < "2026-01-01", 5.0, 1.0), index=idx)  # desinflación en 2026
    tna = pd.Series(60.0, index=idx)
    t = tasas_reales(tna, infl, h=12)
    tea = (1 + 0.05) ** 12 - 1
    assert t.loc["2025-12-01", "tea"] == pytest.approx(100 * tea)
    # originado en dic-25: la inflación de los 12 meses siguientes es 1% mensual
    assert t.loc["2025-12-01", "real_ex_post"] == pytest.approx(100 * ((1 + tea) / 1.01**12 - 1))
    # la expectativa ingenua (inflación previa al 5% mensual) da tasa real casi nula
    assert t.loc["2025-12-01", "real_ex_ante_ingenua"] == pytest.approx(100 * ((1 + tea) / 1.05**12 - 1))
    assert t["real_ex_post"].iloc[-12:].isna().all()
