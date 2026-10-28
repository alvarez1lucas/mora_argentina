"""Fase 4: modelo satélite de la mora de familias. `python -m mora.satelite` escribe outputs/modelo/.

Especificación
--------------
    Δ logit(mora_t) = c + Σ_j φ_j Δ logit(mora_{t-j}) + Σ_k β_k x_{k, t-L_k} + γ·covid_t + e_t

- La mora entra en logit (acota el ratio a 0-100%) y en primera diferencia: el nivel es I(1)
  (ver tests de raíz unitaria en outputs/modelo/estacionariedad.csv).
- Los regresores entran en variación interanual (estacionarios): regresión balanceada, sin
  riesgo de correlación espuria entre tendencias.
- Cada regresor entra con un único rezago L_k, elegido por BIC dentro de una grilla acotada por
  criterio económico: la mora es atraso de más de 90 días (nada actúa antes de 3 meses) y el
  efecto cosecha del crédito tarda 12-18 meses.
- El alivio de clasificación de deudores (A 6938 / A 7245) y los meses en que se normaliza quedan
  fuera de la estimación y de la evaluación: bajaron la mora medida y su reversión contamina los AR.
- Signos esperados: entre las especificaciones con el signo que predice la teoría para cada
  regresor, se elige la de menor BIC (práctica estándar en modelos satélite de stress testing).
- Errores estándar HAC (Newey-West).
- Dos especificaciones: "base" (disponible en las dos muestras) y "completa" (agrega salario real,
  que existe desde 2017 con IPC limpio). La comparación larga vs limpia se hace con la base.
"""

from __future__ import annotations

import itertools
import json
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
import yaml
from statsmodels.tools.sm_exceptions import InterpolationWarning
from statsmodels.tsa.stattools import adfuller, kpss, zivot_andrews

from mora.config import ROOT, path, settings
from mora.features import cft_aproximado, inflacion_esperada, load, precios


# --------------------------------------------------------------------------- datos

def logit(p_pct: pd.Series) -> pd.Series:
    p = p_pct / 100
    return np.log(p / (1 - p))


def inv_logit(z: pd.Series | np.ndarray) -> np.ndarray:
    return 100 / (1 + np.exp(-np.asarray(z)))


def regime_dummy(index: pd.DatetimeIndex, regime_id: str) -> pd.Series:
    with open(ROOT / "config" / "regimenes.yaml", encoding="utf-8") as fh:
        reg = {r["id"]: r for r in yaml.safe_load(fh)["regimenes"]}[regime_id]
    desde = pd.Timestamp(reg["desde"]).to_period("M").to_timestamp()
    hasta = pd.Timestamp(reg["hasta"]) if reg["hasta"] else index.max()
    return pd.Series(((index >= desde) & (index <= hasta)).astype(float), index=index)


def build_dataset(linea: str = "total", deflactor: str = "publico") -> pd.DataFrame:
    """Dataset mensual: mora (logit y Δ) y regresores en variación interanual (%).

    `deflactor` elige la medición de precios (ver mora.deflactores) para todas las variables reales.
    """
    fam = load("familias_por_linea")
    bcra, macro = load("bcra_mensual"), load("macro_mensual")
    col = "ratio_cartera_irregular_total" if linea == "total" else f"ratio_{linea}"
    idx = fam.index
    p = precios(deflactor)
    ipc = p["ipc"].reindex(idx)
    infl_previa = inflacion_esperada(deflactor, idx)  # ver mora.features.inflacion_esperada
    cft = cft_aproximado(bcra["tasa_prestamos_personales"]).reindex(idx) / 100
    credito_real = (bcra["prestamos_personales"] + bcra["prestamos_tarjetas"]).reindex(idx) / ipc
    salario_real = macro["salarios_registrados"].reindex(idx) / ipc

    def ia(s: pd.Series) -> pd.Series:
        return 100 * np.log(s).diff(12)

    df = pd.DataFrame(
        {
            "mora": fam[col],
            "y": logit(fam[col]),
            "tasa_real_cft": 100 * ((1 + cft) / (1 + infl_previa) - 1),
            "salario_real_ia": ia(salario_real),
            "empleo_ia": ia(macro["empleo_registrado"].reindex(idx)),
            "emae_ia": ia(macro["emae_desest"].reindex(idx)),
            "credito_real_ia": ia(credito_real),
            "ipc_empalmado": p["ipc_empalmado"].reindex(idx).fillna(True).astype(bool),
        },
        index=idx,
    )
    df["dy"] = df["y"].diff()
    df["covid"] = regime_dummy(idx, "alivio_clasificacion_covid")
    # Ventana excluida de la estimación: el alivio y los meses en que se normaliza la clasificación
    # (la mora salta al desarmarse el alivio y ese salto contamina los términos AR).
    meses_extra = settings()["satelite"]["meses_post_covid_excluidos"]
    fin = df.index[df["covid"] == 1].max()
    df["excluir"] = (df["covid"] == 1) | ((df.index > fin) & (df.index <= fin + pd.DateOffset(months=meses_extra)))
    return df


# --------------------------------------------------------------------------- estacionariedad

def unit_root_table(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """ADF (H0: raíz unitaria) y KPSS (H0: estacionaria) en nivel y en primera diferencia."""
    rows = []
    for c in cols:
        for forma, s in (("nivel", df[c]), ("diferencia", df[c].diff())):
            s = s.dropna()
            adf_p = adfuller(s, autolag="AIC")[1]
            with warnings.catch_warnings():
                # KPSS acota el p-valor a [0,01; 0,10] (tabla de valores críticos): se reporta el borde
                warnings.simplefilter("ignore", InterpolationWarning)
                kpss_p = kpss(s, regression="c", nlags="auto")[1]
            rows.append({"variable": c, "forma": forma, "n": len(s), "adf_pvalor": adf_p, "kpss_pvalor": kpss_p,
                         "conclusion": _ur_verdict(adf_p, kpss_p)})
    return pd.DataFrame(rows)


def _ur_verdict(adf_p: float, kpss_p: float, alpha: float = 0.05) -> str:
    if adf_p < alpha and kpss_p >= alpha:
        return "estacionaria"
    if adf_p >= alpha and kpss_p < alpha:
        return "raiz_unitaria"
    return "ambigua"


def zivot_andrews_test(s: pd.Series) -> dict:
    """Raíz unitaria con un quiebre endógeno (en nivel y tendencia)."""
    s = s.dropna()
    stat, pval, _, _, bp = zivot_andrews(s, regression="ct", autolag="AIC")
    return {"estadistico": stat, "pvalor": pval, "fecha_quiebre": str(s.index[bp].date())}


# --------------------------------------------------------------------------- especificación

@dataclass
class Spec:
    lags: dict[str, int]
    ar: int

    def name(self) -> str:
        return ", ".join(f"{k}(t-{v})" for k, v in self.lags.items()) + f" | AR({self.ar})"


def design(df: pd.DataFrame, spec: Spec) -> tuple[pd.Series, pd.DataFrame]:
    """y y X de la regresión. Las filas de la ventana COVID quedan con y = NaN (fuera de la estimación)."""
    X = pd.DataFrame(index=df.index)
    for j in range(1, spec.ar + 1):
        X[f"dy_l{j}"] = df["dy"].shift(j)
    for var, lag in spec.lags.items():
        X[f"{var}_l{lag}"] = df[var].shift(lag)
    y = df["dy"].where(~df["excluir"]) if "excluir" in df else df["dy"]
    return y, sm.add_constant(X)


def residuos(params: pd.Series, df: pd.DataFrame, spec: Spec) -> pd.Series:
    """Residuos y − X·β sólo en las filas con todos los regresores (sum() trataría los faltantes como cero)."""
    y, X = design(df, spec)
    X = X[params.index]
    return (y - X.mul(params).sum(axis=1))[X.notna().all(axis=1) & y.notna()]


def signs_ok(res, spec: Spec, expected: dict[str, int]) -> bool:
    return all(np.sign(res.params[f"{v}_l{l}"]) == expected[v] for v, l in spec.lags.items() if expected.get(v, 0) != 0)


def candidate_specs(grid: dict[str, list[int]], ar_max: int) -> list[Spec]:
    names = list(grid)
    return [Spec(dict(zip(names, combo)), ar) for combo in itertools.product(*grid.values()) for ar in range(1, ar_max + 1)]


def select_spec(
    df: pd.DataFrame, grid: dict[str, list[int]], ar_max: int, expected: dict[str, int] | None = None
) -> tuple[Spec, pd.DataFrame]:
    """Elige la combinación de rezagos con menor BIC entre las que tienen los signos esperados.

    Todas se estiman en la misma muestra para que el BIC sea comparable. Si ninguna cumple los
    signos, se toma la de menor BIC y queda marcada (`signos_ok` = False) en la tabla.
    """
    specs = candidate_specs(grid, ar_max)
    max_lag = max(max(v) for v in grid.values())
    common = df.index[max(max_lag, ar_max) + 1 :]
    rows = []
    for spec in specs:
        y, X = design(df, spec)
        data = pd.concat([y.rename("dy"), X], axis=1).loc[common].dropna()
        if len(data) < X.shape[1] + 10:
            continue
        res = sm.OLS(data["dy"], data.drop(columns="dy")).fit()
        rows.append({"spec": spec, "bic": res.bic, "n": int(res.nobs), "signos_ok": signs_ok(res, spec, expected or {})})
    if not rows:
        raise ValueError("Sin observaciones suficientes para estimar")
    tabla = pd.DataFrame(rows)
    tabla = tabla[tabla["n"] == tabla["n"].max()].sort_values(["signos_ok", "bic"], ascending=[False, True])
    return tabla.iloc[0]["spec"], tabla.assign(spec=tabla["spec"].map(Spec.name))


def fit(df: pd.DataFrame, spec: Spec):
    y, X = design(df, spec)
    data = pd.concat([y.rename("dy"), X], axis=1).dropna()
    return sm.OLS(data["dy"], data.drop(columns="dy")).fit(cov_type="HAC", cov_kwds={"maxlags": 12})


# --------------------------------------------------------------------------- pronóstico y evaluación

def forecast_path(res, df: pd.DataFrame, spec: Spec, origin: pd.Timestamp, h: int) -> pd.Series:
    """Pronóstico recursivo del nivel de mora (%) h meses adelante desde `origin`.

    Condicional a los regresores observados (los rezagos >= 3 meses hacen que los primeros
    meses sean pronóstico puro; más allá equivale a un escenario con la macro realizada).
    """
    fechas = pd.date_range(origin + pd.offsets.MonthBegin(1), periods=h, freq="MS")
    work = df.copy()
    y_level = work.loc[origin, "y"]
    out = {}
    params = res.params
    for t in fechas:
        if t not in work.index:
            break
        row = {"const": 1.0}
        for j in range(1, spec.ar + 1):
            row[f"dy_l{j}"] = work["dy"].shift(j).loc[t]
        for var, lag in spec.lags.items():
            row[f"{var}_l{lag}"] = work[var].shift(lag).loc[t]
        dy_hat = sum(params[k] * row[k] for k in params.index)
        if np.isnan(dy_hat):
            break
        work.loc[t, "dy"] = dy_hat
        y_level += dy_hat
        out[t] = float(inv_logit(y_level))
    return pd.Series(out)


def ar_benchmark_path(df: pd.DataFrame, origin: pd.Timestamp, h: int) -> pd.Series:
    hist = df.loc[:origin, "dy"]
    pares = pd.concat([hist.where(~df.loc[:origin, "excluir"]), hist.shift(1)], axis=1).dropna()
    res = sm.OLS(pares.iloc[:, 0].values, sm.add_constant(pares.iloc[:, 1].values)).fit()
    c, phi = res.params
    y, dy, out = df.loc[origin, "y"], hist.dropna().iloc[-1], {}
    for t in pd.date_range(origin + pd.offsets.MonthBegin(1), periods=h, freq="MS"):
        dy = c + phi * dy
        y += dy
        out[t] = float(inv_logit(y))
    return pd.Series(out)


def evaluate_oos(
    df: pd.DataFrame, grid: dict[str, list[int]], ar_max: int, min_train: int, horizons: list[int],
    expected: dict[str, int] | None = None,
) -> pd.DataFrame:
    """Ventana expansiva: en cada origen se re-elige la especificación sólo con datos hasta ese mes.

    No se evalúan orígenes ni meses objetivo dentro de la ventana COVID excluida.
    """
    usable = df.dropna(subset=list(grid) + ["dy"]).index
    origins = [o for o in usable[min_train:] if not df.loc[o, "excluir"]]
    hmax = max(horizons)
    rows = []
    for origin in origins:
        train = df.loc[:origin]
        try:
            spec, _ = select_spec(train, grid, ar_max, expected)
            res = fit(train, spec)
        except ValueError:
            continue
        paths = {
            "satelite": forecast_path(res, df, spec, origin, hmax),
            "paseo_aleatorio": pd.Series(df.loc[origin, "mora"], index=pd.date_range(origin + pd.offsets.MonthBegin(1), periods=hmax, freq="MS")),
            "ar1": ar_benchmark_path(train, origin, hmax),
        }
        for h in horizons:
            t = origin + pd.DateOffset(months=h)
            if t not in df.index or np.isnan(df.loc[t, "mora"]) or df.loc[t, "excluir"]:
                continue
            for modelo, path_ in paths.items():
                if t in path_.index:
                    rows.append({"origen": origin, "h": h, "modelo": modelo, "pronostico": path_[t], "real": df.loc[t, "mora"]})
    e = pd.DataFrame(rows)
    e["error"] = e["pronostico"] - e["real"]
    return e


def oos_summary(errors: pd.DataFrame) -> pd.DataFrame:
    g = errors.groupby(["h", "modelo"])["error"]
    s = pd.DataFrame({"rmse": g.apply(lambda x: float(np.sqrt((x**2).mean()))), "mae": g.apply(lambda x: float(x.abs().mean())), "n": g.size()}).reset_index()
    rw = s[s["modelo"] == "paseo_aleatorio"].set_index("h")["rmse"]
    s["rmse_relativo_paseo_aleatorio"] = s.apply(lambda r: r["rmse"] / rw[r["h"]], axis=1)
    return s


# --------------------------------------------------------------------------- contribuciones

def contributions(res, df: pd.DataFrame, spec: Spec, desde: pd.Timestamp, hasta: pd.Timestamp) -> pd.DataFrame:
    """Aporte de cada regresor al cambio acumulado del logit de la mora entre `desde` y `hasta`.

    Aporte_k = β_k · Σ_t (x_{k,t-L} − media muestral de x_k). La suma de aportes más la inercia
    (términos AR), la constante y el residuo reproduce el cambio observado.
    """
    _, X = design(df, spec)
    X = X.loc[desde:hasta].dropna()
    mean = design(df, spec)[1].dropna().mean()
    rows = []
    for var, lag in spec.lags.items():
        k = f"{var}_l{lag}"
        rows.append({"factor": var, "rezago": lag, "aporte_logit": float(res.params[k] * (X[k] - mean[k]).sum())})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- orquestación

def run_sample(name: str, spec_name: str, grid: dict[str, list[int]], cfg: dict, deflactor: str = "publico") -> dict:
    df = build_dataset(deflactor=deflactor)
    inicio = pd.Timestamp(settings()["sample"]["muestras"][name]["inicio"])
    if name == "limpia":
        df.loc[df["ipc_empalmado"], ["tasa_real_cft", "credito_real_ia", "salario_real_ia"]] = np.nan
    df = df.loc[inicio:]
    expected = cfg["signos_esperados"]
    spec, ranking = select_spec(df, grid, cfg["ar_max"], expected)
    res = fit(df, spec)
    errors = evaluate_oos(df, grid, cfg["ar_max"], cfg["min_train"], cfg["horizontes"], expected)
    ult = df["dy"].dropna().index.max()
    contrib = contributions(res, df, spec, ult - pd.DateOffset(months=11), ult)
    tag = f"{spec_name}_{name}_{deflactor}"
    coefs = pd.DataFrame({"coef": res.params, "se_hac": res.bse, "pvalor": res.pvalues, "ic95_inf": res.conf_int()[0], "ic95_sup": res.conf_int()[1]})
    return {
        "tag": tag,
        "spec": spec,
        "coeficientes": coefs.rename_axis("termino").reset_index(),
        "ranking": ranking.head(10),
        "oos": oos_summary(errors).assign(especificacion=spec_name, muestra=name, deflactor=deflactor),
        "contribuciones": contrib.assign(especificacion=spec_name, muestra=name, deflactor=deflactor, desde=str((ult - pd.DateOffset(months=11)).date()), hasta=str(ult.date())),
        "meta": {"especificacion": spec.name(), "signos_ok": bool(signs_ok(res, spec, expected)), "n": int(res.nobs), "r2_ajustado": float(res.rsquared_adj),
                 "desde": str(res.model.data.row_labels[0].date()), "hasta": str(res.model.data.row_labels[-1].date())},
    }


def run_all(deflactor: str, out) -> list[dict]:
    """Todas las especificaciones y muestras configuradas con un deflactor; escribe los outputs en `out`."""
    cfg = settings()["satelite"]
    out.mkdir(parents=True, exist_ok=True)
    df = build_dataset(deflactor=deflactor)
    vars_ = ["y", "tasa_real_cft", "salario_real_ia", "empleo_ia", "emae_ia", "credito_real_ia"]
    unit_root_table(df.loc["2011-01-01":], vars_).to_csv(out / "estacionariedad.csv", index=False)
    za = zivot_andrews_test(df["y"])

    corridas = []
    for spec_name, spec_cfg in cfg["especificaciones"].items():
        for muestra in spec_cfg["muestras"]:
            corridas.append(run_sample(muestra, spec_name, spec_cfg["grilla"], cfg, deflactor))
            print(f"satélite {spec_name}/{muestra}/{deflactor}: ok")

    pd.concat([c["coeficientes"].assign(corrida=c["tag"]) for c in corridas]).to_csv(out / "coeficientes.csv", index=False)
    pd.concat([c["ranking"].assign(corrida=c["tag"]) for c in corridas]).to_csv(out / "seleccion_rezagos.csv", index=False)
    pd.concat([c["oos"] for c in corridas]).to_csv(out / "evaluacion_fuera_de_muestra.csv", index=False)
    pd.concat([c["contribuciones"] for c in corridas]).to_csv(out / "contribuciones_12m.csv", index=False)
    with open(out / "resumen_modelo.json", "w", encoding="utf-8") as fh:
        json.dump({"deflactor": deflactor, "zivot_andrews_logit_mora": za, "corridas": {c["tag"]: c["meta"] for c in corridas}}, fh, ensure_ascii=False, indent=2)
    print(f"satélite: {out}")
    return corridas


def main() -> None:
    run_all(settings()["deflactores"]["principal"], path("outputs") / "modelo")


if __name__ == "__main__":
    main()
