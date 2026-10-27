import numpy as np
import pandas as pd
import pytest

from mora.panel import cosecha_fe, event_study


def _synthetic_panel(n_ent=40, efecto_evento=2.0, efecto_cosecha=0.03, seed=0):
    """Panel con un shock común por mes, un efecto del evento proporcional a la exposición y cosecha."""
    rng = np.random.default_rng(seed)
    fechas = pd.date_range("2020-01-01", "2026-07-01", freq="MS")
    shock_mes = pd.Series(rng.normal(0, 1, len(fechas)), index=fechas)
    rows = []
    for i in range(n_ent):
        expo = rng.uniform(5, 50)
        g = rng.normal(20, 30, len(fechas))  # crecimiento del crédito
        for j, f in enumerate(fechas):
            post = f >= pd.Timestamp("2025-07-01")
            rows.append({"entidad": f"{i:05d}", "fecha": f, "exposicion_sp": expo, "g_consumo_12": g[j],
                         "part_tarjetas": rng.uniform(20, 80), "log_activo_real": rng.normal(10, 1),
                         "consumo_real": 100.0, "shock": shock_mes[f], "post": post})
    df = pd.DataFrame(rows).sort_values(["entidad", "fecha"])
    gr = df.groupby("entidad")
    df["d12_irr"] = efecto_cosecha * gr["g_consumo_12"].shift(12) + df["shock"] + rng.normal(0, 0.1, len(df))
    expo_std = (df["exposicion_sp"] - df.groupby("fecha")["exposicion_sp"].transform("mean")) / df.groupby("fecha")["exposicion_sp"].transform("std")
    df["irr"] = 5 + df["shock"] + efecto_evento * expo_std * df["post"] + rng.normal(0, 0.1, len(df))
    return df


def test_cosecha_fe_recovers_effect_net_of_common_shocks():
    df = _synthetic_panel()
    res = cosecha_fe(df).set_index("termino")
    assert res.loc["g_consumo_12_l12", "coef"] == pytest.approx(0.03, abs=0.005)
    assert res.loc["g_consumo_12_l12", "pvalor"] < 0.01


def test_event_study_detects_post_effect_and_flat_pretrends():
    df = _synthetic_panel()
    es = event_study(df, "irr", "2025-07-01", (-6, 6), "2025-06-01").set_index("k")
    assert es.loc[3, "coef"] == pytest.approx(2.0, abs=0.1)
    assert abs(es.loc[-3, "coef"]) < 0.1
    assert -1 not in es.index
