import numpy as np
import pandas as pd
import pytest

from mora.canales import historical_decomposition, simulate
from mora.satelite import Spec, design, fit, inv_logit, logit

IDX = pd.date_range("2015-01-01", periods=140, freq="MS")


def _df(seed=0):
    rng = np.random.default_rng(seed)
    x = pd.Series(rng.normal(0, 5, len(IDX)), index=IDX)
    z = pd.Series(rng.normal(0, 5, len(IDX)), index=IDX)
    dy = 0.01 + 0.004 * x.shift(3).fillna(0) + rng.normal(0, 0.01, len(IDX))
    y = logit(pd.Series([3.0])).iloc[0] + dy.cumsum()
    df = pd.DataFrame({"y": y, "dy": y.diff(), "salario_real_ia": x, "tcr_ia": z, "mora": inv_logit(y)}, index=IDX)
    df["excluir"] = False
    return df


def test_simulation_with_residuals_reproduces_observed_path():
    df = _df()
    spec = Spec({"salario_real_ia": 3, "tcr_ia": 3}, 1)
    res = fit(df, spec)
    y, X = design(df, spec)
    resid = (y - X[res.params.index].mul(res.params).sum(axis=1)).dropna()
    desde, hasta = IDX[100], IDX[-1]
    sim = simulate(res.params, df, spec, desde, hasta, resid)
    np.testing.assert_allclose(sim.values, df.loc[desde:hasta, "mora"].values, rtol=1e-9)


def test_channel_with_zero_coefficient_contributes_nothing():
    df = _df()
    spec = Spec({"salario_real_ia": 3, "tcr_ia": 3}, 1)
    res = fit(df, spec)
    res.params["tcr_ia_l3"] = 0.0
    out = historical_decomposition(res, df, spec, IDX[100], IDX[-1], {"salario_real_ia": 0.0, "tcr_ia": 0.0}).set_index("variable")
    assert out.loc["tcr_ia", "aporte_pp"] == pytest.approx(0.0, abs=1e-12)
    assert abs(out.loc["salario_real_ia", "aporte_pp"]) > 0
