import numpy as np
import pandas as pd
import pytest

from mora.cadena import partes_tasa, traspaso
from mora.features import cft_aproximado

IDX = pd.date_range("2017-01-01", periods=120, freq="MS")


def test_las_partes_suman_la_tasa_real_del_cft():
    rng = np.random.default_rng(0)
    tna = pd.Series(rng.uniform(30, 120, len(IDX)), index=IDX)
    estado = pd.Series(rng.uniform(20, 100, len(IDX)), index=IDX)
    pi = pd.Series(rng.uniform(0.2, 1.5, len(IDX)), index=IDX)
    p = partes_tasa(tna, estado, pi)
    real_cft = 100 * ((1 + cft_aproximado(tna) / 100) / (1 + pi) - 1)
    np.testing.assert_allclose(p["tasa_real_cft"], real_cft, rtol=1e-12)
    # a mano: TNA 60% → TEA (1 + 0,05)^12 − 1; Estado 40%, sin inflación → prima = TEA − 40
    q = partes_tasa(pd.Series([60.0]), pd.Series([40.0]), pd.Series([0.0]))
    assert q["estado"].iloc[0] == pytest.approx(40.0)
    assert q["prima"].iloc[0] == pytest.approx(100 * (1.05 ** 12 - 1) - 40, rel=1e-12)
    assert q["impuestos"].iloc[0] > 0  # el IVA sobre intereses siempre suma


def test_traspaso_recupera_el_coeficiente():
    rng = np.random.default_rng(1)
    estado = pd.Series(np.cumsum(rng.normal(0, 3, len(IDX))), index=IDX)
    prima = 0.4 * estado + pd.Series(rng.normal(0, 0.5, len(IDX)), index=IDX)  # tasa = 1,4 × Estado
    comp = pd.DataFrame({"estado": estado, "prima": prima})
    mora = pd.Series(rng.normal(5, 1, len(IDX)), index=IDX)
    t = traspaso(comp, mora)
    assert t["beta_estado"] == pytest.approx(1.4, abs=0.05)
    assert t["p_mora_previa"] > 0.01
