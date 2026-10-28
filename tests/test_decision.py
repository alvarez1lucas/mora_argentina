import numpy as np
import pandas as pd
import pytest

from mora.decision import cft_desde_tea, cortes, pd_equilibrio, sensibilidad_linea, tasa_minima
from mora.decision import inv_logit, logit


def test_tasa_minima_sin_riesgo_es_estado_mas_costo():
    assert tasa_minima(0.0, 0.38, 0.12, 0.75) == pytest.approx(0.50)


def test_tasa_minima_y_pd_de_equilibrio_son_inversas():
    r = tasa_minima(0.2, 0.38, 0.12, 0.75)
    assert pd_equilibrio(r, 0.38, 0.12, 0.75) == pytest.approx(0.2)
    # a la tasa mínima, el valor esperado del préstamo empata al Estado + costo
    assert (1 - 0.2) * (1 + r) + 0.2 * 0.25 == pytest.approx(1.5)


def test_cft_suma_iva_sobre_intereses():
    assert cft_desde_tea(0.0) == 0.0
    assert cft_desde_tea(0.8) > 0.8


def test_logit_en_fraccion():
    assert logit(0.5) == pytest.approx(0.0)
    assert float(inv_logit(logit(0.2))) == pytest.approx(0.2)
    # números calculados a mano: logit(0,1) = ln(0,1/0,9)
    assert logit(0.1) == pytest.approx(-2.1972, abs=1e-4)


def test_corte_equivalente_mantiene_el_riesgo_efectivo():
    pds = pd.DataFrame([{"deflactor": "publico", "linea": "personales", "escenario": "base", "delta_logit_vs_ttc": 1.3}])
    c = cortes(pds, [0.10]).iloc[0]
    # un solicitante en el corte nuevo, con el desplazamiento del escenario, queda en el corte original
    assert float(inv_logit(logit(c["corte_equivalente_pct"] / 100) + 1.3)) == pytest.approx(0.10)


def test_sensibilidad_linea_recupera_beta():
    idx = pd.date_range("2015-01-01", periods=120, freq="MS")
    rng = np.random.default_rng(0)
    z = -3 + np.cumsum(rng.normal(0, 0.05, 120))
    total = pd.Series(100 * inv_logit(z), index=idx)
    linea = pd.Series(100 * inv_logit(1.2 * z + 0.5 + rng.normal(0, 0.01, 120)), index=idx)
    s = sensibilidad_linea(pd.DataFrame({"total": total, "x": linea}), "x", "2015-01-01")
    assert s["beta"] == pytest.approx(1.2, abs=0.05)
