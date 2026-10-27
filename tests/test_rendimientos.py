import numpy as np
import pandas as pd
import pytest

from mora.rendimientos import factor_reexpresion, flujo_mensual, tasa_efectiva_anual

IDX = pd.date_range("2019-10-01", periods=8, freq="MS")  # oct-19 a may-20


def test_flujo_desacumula_y_reinicia_en_enero():
    flujos = pd.Series([10.0, 20, 30, 5, 6, 7, 8, 9], index=IDX)
    acum = flujos.groupby(IDX.year).cumsum()
    factor = pd.Series(1.0, index=IDX)
    out = flujo_mensual(acum, factor)
    assert np.isnan(out.iloc[0])  # sin el acumulado previo, el primer mes (no enero) queda sin dato
    np.testing.assert_allclose(out.iloc[1:].values, flujos.iloc[1:].values)


def test_flujo_con_reexpresion_por_inflacion():
    # Desde ene-20 el acumulado del mes previo se reexpresa: con 10% de inflación mensual,
    # un flujo constante de 100 en moneda de cada mes se acumula como a_t = a_{t-1}·1,1 + 100
    ipc = pd.Series(1.1 ** np.arange(len(IDX)), index=IDX)
    factor = factor_reexpresion(ipc, "2020-01-01")
    assert factor.loc[:"2019-12-01"].eq(1.0).all()
    assert factor.loc["2020-02-01"] == pytest.approx(1.1)
    acum, a = [], 0.0
    for t in IDX:
        a = 100.0 if t.month == 1 else a * factor.loc[t] + 100.0
        acum.append(a)
    out = flujo_mensual(pd.Series(acum, index=IDX), factor)
    np.testing.assert_allclose(out.loc["2020-01-01":].values, 100.0)


def test_tasa_efectiva_anual():
    flujo = pd.Series([np.nan, 2.0], index=IDX[:2])
    stock = pd.Series([100.0, 100.0], index=IDX[:2])
    tea = tasa_efectiva_anual(flujo, stock, pd.Series(1.0, index=IDX[:2]))
    assert tea.iloc[1] == pytest.approx(100 * (1.02 ** 12 - 1))
