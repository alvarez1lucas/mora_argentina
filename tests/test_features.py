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
