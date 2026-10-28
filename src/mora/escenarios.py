"""Fase 6: escenarios de mora de familias a 12 meses (base, adverso, favorable) y ponderación NIIF 9.

`python -m mora.escenarios` escribe outputs/escenarios/.

Modelos:
- satelite (principal): especificación base en la muestra larga, la única que le gana al AR(1)
  fuera de muestra en todos los horizontes (outputs/modelo/evaluacion_fuera_de_muestra.csv).
- canales (referencia): la ecuación de canales (salario real, costo financiero, esterilización,
  tipo de cambio real, crédito) en la muestra limpia. Sirve para explicar, no para proyectar:
  fuera de muestra no le gana al AR(1) (outputs/escenarios/validacion_canales.csv).
Cada uno con las tres mediciones de precios.

Supuestos, calibrados con la historia de cada variable (no elegidos a mano):
- base: las tasas reales se quedan en el promedio de sus últimos 3 meses; las variaciones
  interanuales convergen linealmente a cero en `meses_convergencia`.
- adverso / favorable: base + un shock igual al percentil `cuantil_shock` (o 1 − cuantil) de los
  cambios a 12 meses observados de la variable, en la dirección que sube (baja) la mora según el
  coeficiente estimado. Entra de forma gradual en `meses_rampa`.
Los shocks arrancan después del último dato observado de cada variable: con rezagos de 6 a 18
meses, buena parte del horizonte ya está determinada por datos observados.

Incertidumbre: simulaciones con coeficientes sorteados de su distribución (covarianza HAC) y
shocks remuestreados de los residuos. NIIF 9: promedio de los escenarios con `pesos_niif9`.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from mora.config import path, settings
from mora.deflactores import DEFLACTORES
from mora.satelite import Spec, build_dataset, design, evaluate_oos, fit, inv_logit, oos_summary, select_spec, signs_ok

ESCENARIOS = ("base", "adverso", "favorable")


def modelo(nombre: str, deflactor: str) -> tuple[pd.DataFrame, Spec, object, str]:
    """Dataset, especificación elegida por BIC, ajuste y muestra del modelo de escenarios.

    Sólo se proyecta con un modelo que respeta los signos esperados. Si en la muestra larga ninguna
    combinación de rezagos los respeta (pasa con la medición seleccionada: su inflación 2010-2016
    vuelve muy negativas las tasas reales de esos años), se usa la muestra limpia.
    """
    sat = settings()["satelite"]
    if nombre == "satelite":
        grilla, signos = sat["especificaciones"]["base"]["grilla"], sat["signos_esperados"]
        for muestra in ("larga", "limpia"):
            df = build_dataset(deflactor=deflactor)
            if muestra == "limpia":
                df.loc[df["ipc_empalmado"], ["tasa_real_cft", "credito_real_ia", "salario_real_ia"]] = np.nan
            df = df.loc[settings()["sample"]["muestras"][muestra]["inicio"]:]
            spec, _ = select_spec(df, grilla, sat["ar_max"], signos)
            res = fit(df, spec)
            if signs_ok(res, spec, signos):
                return df, spec, res, muestra
        raise ValueError(f"satélite sin especificación con los signos esperados ({deflactor})")
    if nombre == "canales":
        from mora.canales import channel_dataset

        cfg = settings()["canales"]
        df = channel_dataset(deflactor).loc[cfg["inicio"]:]
        grilla = cfg["variantes"]["base"]["grilla"]
        signos = {**sat["signos_esperados"], **cfg["signos_esperados"]}
        spec, _ = select_spec(df, grilla, sat["ar_max"], signos)
        return df, spec, fit(df, spec), "limpia"
    raise ValueError(nombre)


def trayectoria_base(s: pd.Series, fechas: pd.DatetimeIndex, nivel: bool, meses_convergencia: int) -> pd.Series:
    """Camino base después del último dato: nivel = promedio de 3 meses; variación = converge a 0."""
    obs = s.dropna()
    futuro = fechas[fechas > obs.index.max()]
    if nivel:
        return pd.Series(obs.iloc[-3:].mean(), index=futuro)
    m = np.arange(1, len(futuro) + 1)
    return pd.Series(obs.iloc[-1] * np.clip(1 - m / meses_convergencia, 0, None), index=futuro)


def shock(s: pd.Series, coef: float, cuantil: float) -> dict[str, float]:
    """Shock adverso y favorable: cuantiles de los cambios a 12 meses, según el signo del coeficiente."""
    d12 = s.dropna().diff(12).dropna()
    alto, bajo = float(d12.quantile(cuantil)), float(d12.quantile(1 - cuantil))
    return {"adverso": alto if coef > 0 else bajo, "favorable": bajo if coef > 0 else alto}


def supuestos(df: pd.DataFrame, spec: Spec, res, fin: pd.Timestamp) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Regresores extendidos hasta `fin` en cada escenario y tabla de supuestos."""
    cfg = settings()["escenarios"]
    fechas = pd.date_range(df.index.min(), fin, freq="MS")
    caminos = {e: pd.DataFrame(index=fechas) for e in ESCENARIOS}
    filas = []
    for var, lag in spec.lags.items():
        s = df[var]
        ult = s.dropna().index.max()
        base = trayectoria_base(s, fechas, var in cfg["variables_nivel"], cfg["meses_convergencia"])
        sh = shock(s, float(res.params[f"{var}_l{lag}"]), cfg["cuantil_shock"])
        rampa = np.clip(np.arange(1, len(base) + 1) / cfg["meses_rampa"], 0, 1)
        for e in ESCENARIOS:
            futuro = base + (sh[e] * rampa if e != "base" else 0.0)
            caminos[e][var] = pd.concat([s.loc[:ult], futuro]).reindex(fechas)
            filas.append({"variable": var, "rezago": lag, "escenario": e, "ultimo_dato": str(ult.date()),
                          "valor_ultimo_dato": float(s.loc[ult]), "shock": 0.0 if e == "base" else sh[e],
                          "valor_fin_horizonte": float(futuro.iloc[-1]) if len(futuro) else float(s.loc[ult])})
    return caminos, pd.DataFrame(filas)


def meses_determinados(df: pd.DataFrame, spec: Spec, origen: pd.Timestamp) -> int:
    """Meses del horizonte en que todos los regresores (rezagados) ya son datos observados."""
    holgura = [lag - (origen.to_period("M") - df[v].dropna().index.max().to_period("M")).n for v, lag in spec.lags.items()]
    return max(0, min(holgura))


def simular(res, df: pd.DataFrame, regresores: pd.DataFrame, spec: Spec, origen: pd.Timestamp,
            fin: pd.Timestamp, n: int, rng: np.random.Generator | None) -> np.ndarray:
    """Trayectorias de mora (%) de origen+1 a fin. Con rng=None: camino central (coeficientes puntuales, sin shocks)."""
    fechas = pd.date_range(origen + pd.offsets.MonthBegin(1), fin, freq="MS")
    work = df.reindex(regresores.index).copy()
    work[list(spec.lags)] = regresores[list(spec.lags)]
    _, X = design(work.assign(excluir=False), spec)
    nombres = list(res.params.index)
    if rng is None:
        params, eps, n = res.params.values[None, :], np.zeros((1, len(fechas))), 1
    else:
        params = rng.multivariate_normal(res.params.values, res.cov_params().values, size=n)
        y_obs, X_obs = design(df, spec)
        resid = (y_obs - X_obs[nombres].mul(res.params).sum(axis=1)).dropna().values
        eps = rng.choice(resid, size=(n, len(fechas)))
    dy_hist = df["dy"].loc[:origen].values
    lags_dy = np.tile(dy_hist[::-1][: spec.ar], (n, 1))  # columnas: dy_{t-1}, dy_{t-2}, ...
    y = np.full(n, float(df.loc[origen, "y"]))
    out = np.empty((n, len(fechas)))
    for i, t in enumerate(fechas):
        dy = params[:, nombres.index("const")] + eps[:, i]
        for j in range(1, spec.ar + 1):
            dy += params[:, nombres.index(f"dy_l{j}")] * lags_dy[:, j - 1]
        for var, lag in spec.lags.items():
            k = f"{var}_l{lag}"
            dy += params[:, nombres.index(k)] * float(X.loc[t, k])
        lags_dy = np.column_stack([dy, lags_dy[:, :-1]]) if spec.ar > 1 else dy[:, None]
        y = y + dy
        out[:, i] = inv_logit(y)
    return out


def run(nombre: str, deflactor: str) -> dict:
    cfg = settings()["escenarios"]
    df, spec, res, muestra = modelo(nombre, deflactor)
    origen = df["dy"].dropna().index.max()
    fin = origen + pd.DateOffset(months=cfg["horizonte_meses"])
    caminos, tabla = supuestos(df, spec, res, fin)
    rng = np.random.default_rng(cfg["semilla"])
    fechas = pd.date_range(origen + pd.offsets.MonthBegin(1), fin, freq="MS")
    filas, finales = [], {}
    for e in ESCENARIOS:
        central = simular(res, df, caminos[e], spec, origen, fin, 1, None)[0]
        sims = simular(res, df, caminos[e], spec, origen, fin, cfg["simulaciones"], rng)
        finales[e] = sims[:, -1]
        for i, t in enumerate(fechas):
            filas.append({"fecha": t, "escenario": e, "central": central[i], "media": sims[:, i].mean(),
                          "p05": np.percentile(sims[:, i], 5), "p50": np.percentile(sims[:, i], 50),
                          "p95": np.percentile(sims[:, i], 95)})
    tray = pd.DataFrame(filas)
    pesos = cfg["pesos_niif9"]
    fin_df = tray[tray["fecha"] == fin].set_index("escenario")
    ponderada = sum(pesos[e] * fin_df.loc[e, "media"] for e in ESCENARIOS)
    # Distribución ponderada: mezcla de las simulaciones de los tres escenarios según los pesos
    mezcla = np.concatenate([rng.choice(finales[e], int(round(pesos[e] * cfg["simulaciones"]))) for e in ESCENARIOS])
    meta = {
        "modelo": nombre, "deflactor": deflactor, "muestra": muestra, "especificacion": spec.name(), "n": int(res.nobs),
        "origen": str(origen.date()), "fin": str(fin.date()), "mora_origen": float(df.loc[origen, "mora"]),
        "meses_determinados_por_datos_observados": meses_determinados(df, spec, origen),
        "mora_fin": {e: {k: float(fin_df.loc[e, k]) for k in ["central", "media", "p05", "p50", "p95"]} for e in ESCENARIOS},
        "prob_mora_fin_supera_origen": {e: float((finales[e] > df.loc[origen, "mora"]).mean()) for e in ESCENARIOS},
        "niif9": {"pesos": pesos, "mora_ponderada": float(ponderada),
                  "p05": float(np.percentile(mezcla, 5)), "p95": float(np.percentile(mezcla, 95)),
                  # >1: los escenarios malos pesan más que los buenos (asimetría del logit y de los shocks)
                  "ajuste_forward_looking": float(ponderada / fin_df.loc["base", "media"])},
    }
    tags = {"modelo": nombre, "deflactor": deflactor, "muestra": muestra}
    return {"trayectorias": tray.assign(**tags), "supuestos": tabla.assign(**tags), "meta": meta}


def validacion_canales(deflactor: str) -> pd.DataFrame:
    """Evaluación fuera de muestra del modelo de canales (la del satélite está en outputs/modelo/)."""
    cfg, sat = settings()["canales"], settings()["satelite"]
    from mora.canales import channel_dataset

    df = channel_dataset(deflactor).loc[cfg["inicio"]:]
    errores = evaluate_oos(df, cfg["variantes"]["base"]["grilla"], sat["ar_max"], sat["min_train"], sat["horizontes"],
                           {**sat["signos_esperados"], **cfg["signos_esperados"]})
    return oos_summary(errores).assign(modelo_evaluado="canales", deflactor=deflactor)


def main() -> None:
    out = path("outputs") / "escenarios"
    out.mkdir(parents=True, exist_ok=True)
    validacion_canales(settings()["deflactores"]["principal"]).to_csv(out / "validacion_canales.csv", index=False)
    corridas = {(m, d): run(m, d) for m in settings()["escenarios"]["modelos"] for d in DEFLACTORES}
    pd.concat([c["trayectorias"] for c in corridas.values()]).to_csv(out / "trayectorias.csv", index=False, date_format="%Y-%m-%d")
    pd.concat([c["supuestos"] for c in corridas.values()]).to_csv(out / "supuestos.csv", index=False)
    with open(out / "resumen_escenarios.json", "w", encoding="utf-8") as fh:
        json.dump({f"{m}_{d}": c["meta"] for (m, d), c in corridas.items()}, fh, ensure_ascii=False, indent=2)
    print(f"escenarios: {out}")


if __name__ == "__main__":
    main()
