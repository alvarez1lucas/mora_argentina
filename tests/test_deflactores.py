import numpy as np
import pandas as pd
import pytest

from mora.deflactores import chain_backwards, laspeyres, price_updated_weights, recover_weights, splice_ratio

IDX = pd.date_range("2016-12-01", periods=24, freq="MS")


def _divisions():
    # dos divisiones: una sube 1% mensual, la otra 3%
    return pd.DataFrame({"01": 100 * 1.01 ** np.arange(24), "04": 100 * 1.03 ** np.arange(24)}, index=IDX)


def test_laspeyres_with_base_weights():
    d = _divisions()
    w = pd.Series({"01": 0.75, "04": 0.25})
    idx = laspeyres(d, w)
    assert idx.iloc[0] == pytest.approx(100)
    assert idx.iloc[-1] == pytest.approx(0.75 * d["01"].iloc[-1] + 0.25 * d["04"].iloc[-1])


def test_price_updated_weights_deflate_shares_by_relative_prices():
    d = _divisions()
    w = price_updated_weights({"01": 50.0, "04": 50.0}, d, ("2017-11-01", "2017-11-01"))
    rel = d.loc["2017-11-01"] / 100
    expected = (0.5 / rel) / (0.5 / rel).sum()
    pd.testing.assert_series_equal(w, expected, check_names=False)
    assert w["04"] < 0.5  # la división que más subió pierde peso a precios de la base


def test_recover_weights_reproduces_known_index():
    d = _divisions()
    general = laspeyres(d, pd.Series({"01": 0.6, "04": 0.4}))
    w, err = recover_weights(general, d)
    assert w["01"] == pytest.approx(0.6, abs=1e-6)
    assert err < 1e-9


def test_splice_ratio_keeps_new_series_and_rescales_old():
    old = pd.Series([100.0, 110.0, 121.0], index=pd.date_range("2022-01-01", periods=3, freq="MS"))
    new = pd.Series([50.0, 55.0], index=pd.date_range("2022-02-01", periods=2, freq="MS"))
    s = splice_ratio(old, new)
    assert s.loc["2022-02-01"] == 50.0
    assert s.loc["2022-01-01"] == pytest.approx(100 * 50 / 110)


def test_chain_backwards_uses_monthly_inflation():
    level = pd.Series([100.0, 102.0], index=pd.to_datetime(["2016-12-01", "2017-01-01"]))
    infl = pd.Series([5.0, 2.0, 2.0], index=pd.to_datetime(["2016-11-01", "2016-12-01", "2017-01-01"]))
    s = chain_backwards(level, infl)
    assert s.loc["2016-11-01"] == pytest.approx(100 / 1.02)
