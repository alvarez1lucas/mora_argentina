import numpy as np
import pandas as pd
import pytest

from mora.escenarios import meses_determinados, shock, simular, trayectoria_base
from mora.satelite import Spec, fit, forecast_path, inv_logit, logit

IDX = pd.date_range("2015-01-01", periods=120, freq="MS")


def _df(seed=0):
    rng = np.random.default_rng(seed)
    x = pd.Series(rng.normal(0, 5, len(IDX)), index=IDX)
    dy = 0.01 + 0.004 * x.shift(3).fillna(0) + rng.normal(0, 0.01, len(IDX))
    y = logit(pd.Series([3.0])).iloc[0] + dy.cumsum()
    df = pd.DataFrame({"y": y, "dy": y.diff(), "x": x, "mora": inv_logit(y)}, index=IDX)
    df["excluir"] = False
    return df


def test_camino_central_coincide_con_el_pronostico_del_satelite():
    df = _df()
    spec = Spec({"x": 3}, 2)
    res = fit(df, spec)
    origen = IDX[100]
    central = simular(res, df, df[["x"]], spec, origen, IDX[103], 1, None)[0]
    esperado = forecast_path(res, df, spec, origen, 3)
    np.testing.assert_allclose(central, esperado.values, rtol=1e-10)


def test_trayectoria_base_nivel_y_variacion():
    s = pd.Series([1.0, 2.0, 3.0, 6.0], index=IDX[:4])
    fechas = IDX[:10]
    nivel = trayectoria_base(s, fechas, nivel=True, meses_convergencia=3)
    assert nivel.index.min() == IDX[4]
    np.testing.assert_allclose(nivel.values, (2 + 3 + 6) / 3)
    var = trayectoria_base(s, fechas, nivel=False, meses_convergencia=3)
    np.testing.assert_allclose(var.values[:4], [4.0, 2.0, 0.0, 0.0])


def test_shock_sigue_el_signo_del_coeficiente():
    s = pd.Series(np.arange(60, dtype=float) ** 1.5, index=IDX[:60])
    sube = shock(s, coef=0.5, cuantil=0.9)
    baja = shock(s, coef=-0.5, cuantil=0.9)
    assert sube["adverso"] > sube["favorable"]
    assert baja["adverso"] == sube["favorable"] and baja["favorable"] == sube["adverso"]


def test_meses_determinados():
    df = _df()
    df.loc[IDX[-2]:, "x"] = np.nan  # el regresor llega dos meses menos que la mora
    assert meses_determinados(df, Spec({"x": 3}, 1), IDX[-1]) == 1
