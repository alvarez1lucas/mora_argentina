import numpy as np
import pandas as pd
import pytest

from mora.satelite import Spec, fit, forecast_path, inv_logit, logit, select_spec, signs_ok

IDX = pd.date_range("2012-01-01", periods=160, freq="MS")


def _synthetic(seed=0, beta=0.004, lag=6):
    """dy depende de x con rezago `lag`; z es ruido sin relación."""
    rng = np.random.default_rng(seed)
    x = pd.Series(rng.normal(0, 10, len(IDX)), index=IDX)
    z = pd.Series(rng.normal(0, 10, len(IDX)), index=IDX)
    dy = 0.002 + beta * x.shift(lag).fillna(0) + rng.normal(0, 0.01, len(IDX))
    y = logit(pd.Series(3.0, index=IDX)).iloc[0] + dy.cumsum()
    df = pd.DataFrame({"y": y, "dy": y.diff(), "x": x, "z": z, "mora": inv_logit(y)}, index=IDX)
    df["excluir"] = False
    return df


def test_logit_roundtrip():
    p = pd.Series([1.0, 12.9, 50.0])
    np.testing.assert_allclose(inv_logit(logit(p)), p)


def test_select_spec_recovers_true_lag():
    df = _synthetic(lag=6)
    spec, ranking = select_spec(df, {"x": [3, 6, 9]}, ar_max=1, expected={"x": 1})
    assert spec.lags["x"] == 6
    assert ranking["n"].nunique() == 1  # todas en la misma muestra


def test_sign_restriction_prefers_expected_sign():
    df = _synthetic(beta=-0.004, lag=6)  # el verdadero efecto es negativo
    spec, ranking = select_spec(df, {"x": [3, 6, 9]}, ar_max=1, expected={"x": 1})
    res = fit(df, spec)
    # ninguna especificación con signo positivo le gana a la verdadera: si la elegida no cumple, queda marcada
    assert signs_ok(res, spec, {"x": 1}) == bool(ranking.iloc[0]["signos_ok"])


def test_excluded_rows_do_not_enter_estimation():
    df = _synthetic()
    df.loc["2020-03-01":"2021-11-01", "excluir"] = True
    res = fit(df, Spec({"x": 6}, 1))
    assert pd.Timestamp("2020-06-01") not in res.model.data.row_labels


def test_forecast_path_matches_manual_recursion():
    df = _synthetic()
    spec = Spec({"x": 6}, 1)
    res = fit(df, spec)
    origin = IDX[120]
    path = forecast_path(res, df, spec, origin, 3)
    p = res.params
    y, dy = df.loc[origin, "y"], df.loc[origin, "dy"]
    for t in path.index:
        dy = p["const"] + p["dy_l1"] * dy + p["x_l6"] * df["x"].shift(6).loc[t]
        y += dy
        assert path[t] == pytest.approx(float(inv_logit(y)))


def test_residuos_solo_en_filas_completas():
    from mora.satelite import Spec, design, fit, residuos

    idx = pd.date_range("2015-01-01", periods=60, freq="MS")
    rng = np.random.default_rng(3)
    df = pd.DataFrame({"x": rng.normal(size=60)}, index=idx)
    df["dy"] = 0.01 * df["x"].shift(3).fillna(0) + rng.normal(0, 0.01, 60)
    df["excluir"] = False
    spec = Spec({"x": 3}, 1)
    r = residuos(fit(df, spec).params, df, spec)
    _, X = design(df, spec)
    assert r.index.min() == X.dropna().index.min()  # sin residuos "contaminados" al inicio
    assert np.isfinite(r).all()
