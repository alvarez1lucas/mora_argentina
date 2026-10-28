import numpy as np
import pandas as pd
import pytest

from mora.alertas import completar_cola, episodios, umbral_optimo

IDX = pd.date_range("2015-01-01", periods=10, freq="MS")


def test_episodio_mira_los_meses_siguientes():
    mora = pd.Series([2.0, 2.1, 2.2, 3.5, 3.6, 3.6, 3.6, 3.6, 3.6, 3.6], index=IDX)
    e = episodios(mora, 1.0, 3)
    assert e.iloc[0] == 1.0 and e.iloc[2] == 1.0  # dentro de 3 meses sube 1,5 / 1,3 puntos
    assert e.iloc[3] == 0.0
    assert np.isnan(e.iloc[-1])  # todavía no se sabe


def test_umbral_separa_senal_de_ruido():
    x = pd.Series(np.r_[np.linspace(0, 1, 80), np.linspace(2, 3, 20)])
    y = pd.Series(np.r_[np.zeros(80), np.ones(20)])
    u = umbral_optimo(x, y, "alto", 0.25)
    assert u["nsr"] == pytest.approx(0.0)  # el umbral elegido no da falsas alarmas
    assert 1 < u["umbral"] <= 2.5 and u["cobertura"] >= 0.25
    malo = umbral_optimo(x, y, "bajo", 0.25)  # dirección equivocada: no le gana al azar
    assert not malo["nsr"] < 1


def test_completar_cola_solo_al_final():
    df = pd.DataFrame({"a": [1.0, np.nan, 3.0, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan]}, index=IDX)
    out = completar_cola(df, 2)
    assert np.isnan(out["a"].iloc[1])  # un hueco intermedio no se rellena
    assert out["a"].iloc[3] == 3.0 and out["a"].iloc[4] == 3.0 and np.isnan(out["a"].iloc[5])
