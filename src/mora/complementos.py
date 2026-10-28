"""Análisis complementarios (no integrados al sitio, al README ni al workflow semanal).

`python -m mora.complementos` escribe outputs/complementos/.

1. ARDL con bounds test (Pesaran, Shin y Smith, 2001): ¿hay relación de largo plazo en niveles entre
   el logit de la mora, la tasa real del CFT, el salario real y el crédito real? Válido con regresores
   I(0) o I(1); es el chequeo formal de que la relación no es espuria.
2. Proyecciones locales (Jordà, 2005): respuesta acumulada de la mora a h meses de 1 pp más de tasa
   real o de salario real, una regresión por horizonte, sin imponer la dinámica de un VAR.
3. Bootstrap por bloques de la ponderación de canales: se remuestrean residuos en bloques, se
   reconstruye la mora, se reestima la ecuación con la misma especificación y se recalcula el aporte
   de cada canal sobre los datos observados. Bandas por percentiles, comparables con las de
   outputs/canales/ (que mueven un coeficiente por vez).
"""

from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.ardl import UECM, ardl_select_order

from mora.config import path, settings
from mora.deflactores import DEFLACTORES
from mora.features import load, precios
from mora.satelite import build_dataset, design, fit, residuos, select_spec


def _muestra(deflactor: str, muestra: str) -> pd.DataFrame:
    df = build_dataset(deflactor=deflactor)
    if muestra == "limpia":
        df.loc[df["ipc_empalmado"], ["tasa_real_cft", "credito_real_ia", "salario_real_ia"]] = np.nan
    return df.loc[settings()["sample"]["muestras"][muestra]["inicio"]:]


# --------------------------------------------------------------------------- 1. ARDL / bounds

def niveles(deflactor: str, muestra: str) -> pd.DataFrame:
    """Logit de la mora y regresores en niveles (logs de salario y crédito reales)."""
    df = _muestra(deflactor, muestra)
    bcra, macro = load("bcra_mensual"), load("macro_mensual")
    ipc = precios(deflactor)["ipc"].reindex(df.index)
    out = pd.DataFrame({
        "y": df["y"],
        "tasa_real_cft": df["tasa_real_cft"],
        "log_salario_real": np.log(macro["salarios_registrados"].reindex(df.index) / ipc),
        "log_credito_real": np.log((bcra["prestamos_personales"] + bcra["prestamos_tarjetas"]).reindex(df.index) / ipc),
        "excluir": df["excluir"].astype(float),
    })
    if muestra == "limpia":
        out.loc[df["ipc_empalmado"], ["log_salario_real", "log_credito_real"]] = np.nan
    return out.dropna()


def bounds(deflactor: str, muestra: str) -> dict:
    cfg = settings()["complementos"]["ardl"]
    d = niveles(deflactor, muestra)
    regs = cfg["regresores"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # avisos de frecuencia inferida y de orden incompleto
        sel = ardl_select_order(d["y"], cfg["max_rezago"], d[regs], cfg["max_rezago"], ic="bic", trend="c",
                                fixed=d[["excluir"]])
        # La forma de corrección de errores necesita al menos un rezago por regresor (el BIC puede elegir 0 o excluirlo)
        orden = {x: max(1, (sel.model.dl_lags or {}).get(x) and max(sel.model.dl_lags[x]) or 1) for x in regs}
        ar = max(1, max(sel.model.ar_lags or [1]))
        uecm = UECM(d["y"], ar, d[regs], orden, trend="c", fixed=d[["excluir"]]).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
        # Caso 3 de Pesaran-Shin-Smith: constante sin restricción, sin tendencia
        bt = uecm.bounds_test(case=3)
    cv = bt.critical_values
    lo, hi = float(cv.loc[95.0, "lower"]), float(cv.loc[95.0, "upper"])
    conclusion = "cointegracion" if bt.statistic > hi else ("sin_cointegracion" if bt.statistic < lo else "inconcluso")
    # Coeficientes de largo plazo: −β_x / α (α = coeficiente del nivel rezagado de y)
    p = uecm.params
    alpha = float(p["y.L1"])
    largo = {x: float(-p[f"{x}.L1"] / alpha) for x in regs}
    return {"deflactor": deflactor, "muestra": muestra, "n": int(uecm.nobs), "rezagos_y": ar, "rezagos_x": orden,
            "F": float(bt.statistic), "pvalor_cota_I1": float(bt.pvalue["upper"]),
            "cv95_inferior_I0": lo, "cv95_superior_I1": hi, "conclusion": conclusion,
            "velocidad_ajuste": alpha, "velocidad_ajuste_p": float(uecm.pvalues["y.L1"]), "largo_plazo": largo}


# --------------------------------------------------------------------------- 2. proyecciones locales

def proyeccion_local(df: pd.DataFrame, shock: str, controles: list[str], horizontes: int, rezagos: int) -> pd.DataFrame:
    """β_h de y_{t+h} − y_{t−1} = a + β_h·shock_t + rezagos de Δy, del shock y de los controles + e.

    Se descartan las filas donde t o t+h caen en la ventana excluida (alivio COVID). Errores HAC(h+1).
    β_h en logit; la respuesta en pp se evalúa en la mora media de la muestra (derivada del logit).
    """
    filas = []
    p_media = float(df["mora"].mean()) / 100
    for h in range(horizontes + 1):
        y = df["y"].shift(-h) - df["y"].shift(1)
        X = pd.DataFrame({shock: df[shock]}, index=df.index)
        for j in range(1, rezagos + 1):
            X[f"dy_l{j}"] = df["dy"].shift(j)
            X[f"{shock}_l{j}"] = df[shock].shift(j)
            for c in controles:
                X[f"{c}_l{j}"] = df[c].shift(j)
        excl = df["excluir"] | df["excluir"].shift(-h, fill_value=False)
        data = pd.concat([y.rename("y"), sm.add_constant(X)], axis=1)[~excl].dropna()
        res = sm.OLS(data["y"], data.drop(columns="y")).fit(cov_type="HAC", cov_kwds={"maxlags": h + 1})
        b, se = float(res.params[shock]), float(res.bse[shock])
        escala = 100 * p_media * (1 - p_media)
        filas.append({"h": h, "beta_logit": b, "se": se, "pvalor": float(res.pvalues[shock]),
                      "respuesta_pp": b * escala, "ic90_inf_pp": (b - 1.645 * se) * escala,
                      "ic90_sup_pp": (b + 1.645 * se) * escala, "n": int(res.nobs)})
    return pd.DataFrame(filas)


def proyecciones_locales(deflactor: str) -> pd.DataFrame:
    cfg = settings()["complementos"]["proyecciones_locales"]
    df = _muestra(deflactor, "limpia")
    tablas = []
    for shock, controles in cfg["shocks"].items():
        lp = proyeccion_local(df, shock, controles, cfg["horizontes"], cfg["rezagos"])
        tablas.append(lp.assign(shock=shock, deflactor=deflactor))
    return pd.concat(tablas, ignore_index=True)


# --------------------------------------------------------------------------- 3. bootstrap de canales

def aportes(params: pd.Series, df: pd.DataFrame, spec, desde, hasta, referencias: dict) -> dict[str, float]:
    """Aporte de cada canal sobre los datos observados con los coeficientes `params`.

    Los residuos se recalculan con esos coeficientes, así la simulación base reproduce la mora observada.
    """
    from mora.canales import simulate

    resid = residuos(params, df, spec)
    base = simulate(params, df, spec, desde, hasta, resid).iloc[-1]
    return {v: float(base - simulate(params, df, spec, desde, hasta, resid, {v: referencias[v]}).iloc[-1])
            for v in spec.lags}


def remuestra(df: pd.DataFrame, res, spec, bloque: int, rng: np.random.Generator) -> pd.DataFrame:
    """Mora sintética: misma dinámica estimada con residuos remuestreados en bloques (moving blocks)."""
    _, X = design(df, spec)
    resid = residuos(res.params, df, spec)
    r = resid.values
    n_bloques = int(np.ceil(len(r) / bloque))
    inicios = rng.integers(0, len(r) - bloque + 1, size=n_bloques)
    nuevos = pd.Series(np.concatenate([r[i:i + bloque] for i in inicios])[: len(r)], index=resid.index)
    out = df.copy()
    p = res.params
    for t in resid.index:  # recursión: los rezagos de Δy son los sintéticos
        dy = p["const"] + nuevos[t]
        for j in range(1, spec.ar + 1):
            dy += p[f"dy_l{j}"] * out["dy"].shift(j).loc[t]
        for var, lag in spec.lags.items():
            dy += p[f"{var}_l{lag}"] * X.loc[t, f"{var}_l{lag}"]
        out.loc[t, "dy"] = dy
    return out


def bootstrap_canales(deflactor: str, variante: str, rng: np.random.Generator) -> pd.DataFrame:
    from mora.canales import CANAL_DE, channel_dataset

    cfg, sat, cb = settings()["canales"], settings()["satelite"], settings()["complementos"]["bootstrap_canales"]
    var = cfg["variantes"][variante]
    df = channel_dataset(deflactor).loc[cfg["inicio"]:]
    expected = {**sat["signos_esperados"], **cfg["signos_esperados"]}
    spec, _ = select_spec(df, var["grilla"], sat["ar_max"], expected)
    res = fit(df, spec)
    desde = df["mora"].loc[cfg["buscar_minimo_desde"]:].idxmin() + pd.DateOffset(months=1)
    hasta = df["dy"].dropna().index.max()
    referencias = {v: (df.loc[: desde - pd.DateOffset(months=1), v].mean() if r == "media_previa" else float(r))
                   for v, r in cfg["referencias"].items() if v in spec.lags}
    puntual = aportes(res.params, df, spec, desde, hasta, referencias)
    sorteos = []
    for _ in range(cb["repeticiones"]):
        sint = remuestra(df, res, spec, cb["bloque_meses"], rng)
        p_b = fit(sint, spec).params  # misma especificación: la incertidumbre de la selección no entra
        sorteos.append(aportes(p_b, df, spec, desde, hasta, referencias))
    s = pd.DataFrame(sorteos)
    return pd.DataFrame([{
        "deflactor": deflactor, "variante": variante, "canal": CANAL_DE[v], "variable": v, "rezago": spec.lags[v],
        "aporte_pp": puntual[v], "boot_p05": float(s[v].quantile(0.05)), "boot_p95": float(s[v].quantile(0.95)),
        "boot_p025": float(s[v].quantile(0.025)), "boot_p975": float(s[v].quantile(0.975)),
        "prob_aporte_positivo": float((s[v] > 0).mean()), "repeticiones": len(s),
    } for v in spec.lags])


# --------------------------------------------------------------------------- orquestación

def main() -> None:
    out = path("outputs") / "complementos"
    out.mkdir(parents=True, exist_ok=True)
    cfg = settings()["complementos"]

    ardl = [bounds(d, m) for m in cfg["ardl"]["muestras"] for d in DEFLACTORES]
    with open(out / "ardl_bounds.json", "w", encoding="utf-8") as fh:
        json.dump(ardl, fh, ensure_ascii=False, indent=2)
    print("complementos: ARDL ok")

    pd.concat([proyecciones_locales(d) for d in DEFLACTORES]).to_csv(out / "proyecciones_locales.csv", index=False)
    print("complementos: proyecciones locales ok")

    rng = np.random.default_rng(cfg["bootstrap_canales"]["semilla"])
    boot = [bootstrap_canales(d, v, rng) for v in cfg["bootstrap_canales"]["variantes"] for d in DEFLACTORES]
    pd.concat(boot).to_csv(out / "bootstrap_canales.csv", index=False)
    print(f"complementos: {out}")


if __name__ == "__main__":
    main()
