"""Fase 5 (ML): causalidad con machine learning y alerta temprana por entidad.

`python -m mora.panel_ml` escribe outputs/panel_ml/.

1. Double ML (Chernozhukov et al.): efecto de la cosecha (crecimiento del crédito 12 meses antes)
   sobre la variación de la mora, con controles flexibles (LightGBM) y muestras partidas por
   entidad. Robustez del efecto fijo lineal de mora.panel.
2. Causal Forest (EconML): heterogeneidad del efecto cosecha según el perfil de la entidad
   (mezcla tarjetas/personales, tamaño, exposición al sector público) y la etapa macro.
3. Alerta temprana: LightGBM pronostica la suba de mora de cada entidad a 12 meses. Se compara
   contra un pronóstico ingenuo y contra un modelo lineal con las mismas variables; validación
   temporal (se entrena con orígenes anteriores al corte y se evalúa después). SHAP para leerlo.
"""

from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.linear_model import LinearRegression

from mora.config import path, settings
from mora.panel import build_panel
from mora.satelite import build_dataset

warnings.filterwarnings("ignore", category=UserWarning)

MACRO = ["tasa_real_cft", "empleo_ia", "emae_ia", "credito_real_ia"]


def ml_dataset(deflactor: str = "publico") -> pd.DataFrame:
    """Panel con rezagos por entidad, macro nacional y el objetivo a 12 meses."""
    d = build_panel(deflactor).sort_values(["entidad", "fecha"])
    g = d.groupby("entidad")
    d["irr_sit2"] = d["esd_consumo_sit2"]  # atraso temprano: anticipa la irregularidad
    for c in ("g_consumo_12", "exposicion_sp", "part_tarjetas", "log_activo_real", "irr"):
        d[f"{c}_l12"] = g[c].shift(12)
    d["d12_irr_futuro"] = g["irr"].shift(-12) - d["irr"]
    macro = build_dataset(deflactor=deflactor)[MACRO]
    d = d.merge(macro, left_on="fecha", right_index=True, how="left")
    d["post_2023"] = (d["fecha"] >= "2023-12-01").astype(int)
    d["mes_num"] = (d["fecha"].dt.year - 2011) * 12 + d["fecha"].dt.month
    lo, hi = settings()["panel"]["recorte_crecimiento"]
    return d[d["g_consumo_12_l12"].between(lo, hi) | d["g_consumo_12_l12"].isna()]


def _lgbm(seed: int = 0) -> LGBMRegressor:
    return LGBMRegressor(n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=40,
                         subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=seed, verbose=-1)


# --------------------------------------------------------------------------- Double ML

def double_ml_cosecha(d: pd.DataFrame) -> pd.DataFrame:
    import doubleml as dml

    controls = ["irr_l12", "exposicion_sp_l12", "part_tarjetas_l12", "log_activo_real_l12", *MACRO, "mes_num"]
    data = d[["entidad", "d12_irr", "g_consumo_12_l12", *controls]].dropna().copy()
    data["entidad_id"] = data["entidad"].astype("category").cat.codes
    obj = dml.DoubleMLClusterData(data.drop(columns="entidad"), y_col="d12_irr", d_cols="g_consumo_12_l12",
                                  cluster_cols="entidad_id", x_cols=controls)
    m = dml.DoubleMLPLR(obj, ml_l=_lgbm(1), ml_m=_lgbm(2), n_folds=5, n_rep=3)
    m.fit()
    ci = m.confint()
    return pd.DataFrame({"modelo": ["double_ml_plr"], "tratamiento": ["g_consumo_12_l12"], "coef": [m.coef[0]],
                         "se": [m.se[0]], "pvalor": [m.pval[0]], "ic95_inf": [ci.iloc[0, 0]], "ic95_sup": [ci.iloc[0, 1]],
                         "n": [len(data)], "n_entidades": [data["entidad_id"].nunique()]})


# --------------------------------------------------------------------------- Causal Forest

def causal_forest_cosecha(d: pd.DataFrame) -> pd.DataFrame:
    from econml.dml import CausalForestDML

    X_cols = ["part_tarjetas_l12", "log_activo_real_l12", "exposicion_sp_l12", "post_2023"]
    W_cols = ["irr_l12", *MACRO, "mes_num"]
    data = d[["entidad", "d12_irr", "g_consumo_12_l12", *X_cols, *W_cols]].dropna()
    cf = CausalForestDML(model_y=_lgbm(3), model_t=_lgbm(4), n_estimators=400, min_samples_leaf=50,
                         max_depth=6, random_state=0, cv=5)
    cf.fit(data["d12_irr"], data["g_consumo_12_l12"], X=data[X_cols], W=data[W_cols], groups=data["entidad"])
    eff = cf.effect(data[X_cols])
    lo, hi = cf.effect_interval(data[X_cols], alpha=0.05)
    data = data.assign(efecto=eff, ic_inf=lo, ic_sup=hi)
    rows = [{"grupo": "todas", "categoria": "todas", "efecto_medio": eff.mean(), "n": len(data)}]
    for col in ("part_tarjetas_l12", "log_activo_real_l12", "exposicion_sp_l12"):
        q = pd.qcut(data[col], 4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop")
        for cat, sub in data.groupby(q, observed=True):
            rows.append({"grupo": col, "categoria": str(cat), "efecto_medio": sub["efecto"].mean(), "n": len(sub)})
    for cat, sub in data.groupby("post_2023"):
        rows.append({"grupo": "etapa", "categoria": "desde dic-2023" if cat else "antes de dic-2023",
                     "efecto_medio": sub["efecto"].mean(), "n": len(sub)})
    ate = cf.ate_inference(data[X_cols])
    out = pd.DataFrame(rows)
    out.attrs["ate"] = {"ate": float(ate.mean_point), "ic95": [float(x) for x in ate.conf_int_mean(alpha=0.05)]}
    return out


# --------------------------------------------------------------------------- alerta temprana

FEATURES = ["irr", "d12_irr", "irr_sit2", "g_consumo_12", "g_consumo_12_l12", "exposicion_sp", "part_tarjetas",
            "log_activo_real", *MACRO]


def early_warning(d: pd.DataFrame, corte: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Entrena con orígenes anteriores a `corte` (cuyo objetivo a 12 meses ya se conocía al corte) y evalúa después."""
    data = d[["entidad", "fecha", "d12_irr_futuro", *FEATURES]].dropna()
    corte = pd.Timestamp(corte)
    train = data[data["fecha"] <= corte - pd.DateOffset(months=12)]
    test = data[data["fecha"] > corte]
    X_tr, y_tr, X_te, y_te = train[FEATURES], train["d12_irr_futuro"], test[FEATURES], test["d12_irr_futuro"]
    preds = {
        "ingenuo_sin_cambio": np.zeros(len(test)),
        "lineal": LinearRegression().fit(X_tr, y_tr).predict(X_te),
        "lightgbm": _lgbm(5).fit(X_tr, y_tr).predict(X_te),
    }
    rows = []
    top = y_te >= y_te.quantile(0.9)
    for name, p in preds.items():
        err = p - y_te.values
        flagged = p >= np.quantile(p, 0.9) if name != "ingenuo_sin_cambio" else np.zeros(len(p), bool)
        rows.append({"modelo": name, "rmse": float(np.sqrt((err**2).mean())), "mae": float(np.abs(err).mean()),
                     "precision_decil_superior": float(top[flagged].mean()) if flagged.any() else None,
                     "n_test": len(test), "n_train": len(train)})
    model = _lgbm(5).fit(X_tr, y_tr)
    import shap

    sv = shap.TreeExplainer(model).shap_values(X_te)
    imp = pd.DataFrame({"variable": FEATURES, "shap_medio_abs": np.abs(sv).mean(axis=0)}).sort_values("shap_medio_abs", ascending=False)
    pred_df = test[["entidad", "fecha"]].assign(real=y_te.values, lightgbm=preds["lightgbm"], lineal=preds["lineal"])
    return pd.DataFrame(rows), imp, pred_df


def run(deflactor: str, out) -> dict:
    cfg = settings()["panel_ml"]
    out.mkdir(parents=True, exist_ok=True)
    d = ml_dataset(deflactor)
    dml_res = double_ml_cosecha(d)
    cf = causal_forest_cosecha(d)
    ew, imp, preds = early_warning(d, cfg["corte_alerta_temprana"])
    dml_res.to_csv(out / "double_ml_cosecha.csv", index=False)
    cf.to_csv(out / "causal_forest_cosecha.csv", index=False)
    ew.to_csv(out / "alerta_temprana_evaluacion.csv", index=False)
    imp.to_csv(out / "alerta_temprana_shap.csv", index=False)
    preds.to_csv(out / "alerta_temprana_predicciones.csv", index=False, date_format="%Y-%m-%d")
    with open(out / "resumen_panel_ml.json", "w", encoding="utf-8") as fh:
        json.dump({"deflactor": deflactor, "causal_forest_ate": cf.attrs["ate"], "corte_alerta_temprana": cfg["corte_alerta_temprana"]},
                  fh, ensure_ascii=False, indent=2)
    return {"dml": dml_res, "cf": cf, "ew": ew, "shap": imp}


def main() -> None:
    run(settings()["deflactores"]["principal"], path("outputs") / "panel_ml")
    print("panel_ml: ok")


if __name__ == "__main__":
    main()
