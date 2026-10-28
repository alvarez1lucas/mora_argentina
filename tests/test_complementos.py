import numpy as np
import pandas as pd
import pytest

from mora.complementos import aportes, proyeccion_local, remuestra
from mora.satelite import Spec, fit, inv_logit, logit

IDX = pd.date_range("2012-01-01", periods=160, freq="MS")


def _df(seed=0, beta=0.004):
    rng = np.random.default_rng(seed)
    x = pd.Series(rng.normal(0, 5, len(IDX)), index=IDX)
    dy = 0.002 + beta * x.shift(3).fillna(0) + rng.normal(0, 0.005, len(IDX))
    y = logit(pd.Series([3.0])).iloc[0] + dy.cumsum()
    df = pd.DataFrame({"y": y, "dy": y.diff(), "x": x, "z": rng.normal(0, 1, len(IDX)), "mora": inv_logit(y)}, index=IDX)
    df["excluir"] = False
    return df


def test_proyeccion_local_recupera_respuesta_acumulada():
    # x_t mueve Δy_{t+3}: la respuesta acumulada es 0 hasta h=2 y beta desde h=3
    df = _df(beta=0.004)
    lp = proyeccion_local(df, "x", ["z"], horizontes=6, rezagos=2).set_index("h")
    assert abs(lp.loc[1, "beta_logit"]) < 0.002
    assert lp.loc[4, "beta_logit"] == pytest.approx(0.004, abs=0.0015)
    assert lp.loc[4, "pvalor"] < 0.01


def test_remuestra_conserva_la_dinamica():
    df = _df()
    spec = Spec({"x": 3}, 1)
    res = fit(df, spec)
    sint = remuestra(df, res, spec, bloque=12, rng=np.random.default_rng(1))
    assert len(sint) == len(df) and sint["dy"].notna().sum() >= len(df) - 5
    assert fit(sint, spec).params["x_l3"] == pytest.approx(res.params["x_l3"], abs=0.0015)


def test_aportes_cero_si_el_coeficiente_es_cero():
    df = _df()
    spec = Spec({"x": 3}, 1)
    p = fit(df, spec).params.copy()
    p["x_l3"] = 0.0
    a = aportes(p, df, spec, IDX[140], IDX[-1], {"x": 0.0})
    assert a["x"] == pytest.approx(0.0, abs=1e-12)
