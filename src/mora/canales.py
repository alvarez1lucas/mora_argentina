"""Ponderación de canales: cuánto aportó cada canal macro a la suba de la mora de familias.

`python -m mora.canales` escribe outputs/canales/.

Canales (uno por variable, para que la atribución sea interpretable):
- poder_compra:       salario real registrado (variación interanual), con cada medición de precios
- costo_financiero:   tasa real del CFT de préstamos personales
- esterilizacion:     Δ12 de (títulos públicos + otros créditos por intermediación, que incluye los
                      pases con el BCRA) sobre el activo en pesos del sistema
- ancla_cambiaria:    tipo de cambio real (mayorista / precios), variación interanual
- cosecha_dilucion:   crédito real al consumo, variación interanual

Se estima la misma ecuación que el satélite (Δ logit de la mora, rezagos por BIC dentro de grillas
acotadas, signos esperados donde la teoría los fija) en la muestra limpia, que es la única con
salario real.

Descomposición histórica: se simula la mora con el modelo y los residuos observados (reproduce la
mora real) y, para cada canal, la misma simulación con ese canal en un valor neutral (variaciones
en cero; tasa real en su promedio previo a la ventana). La diferencia es el aporte del canal en
puntos porcentuales de mora, con la inercia incluida. Bandas: coeficiente en los extremos del IC 95%.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from mora.config import path, settings
from mora.deflactores import DEFLACTORES
from mora.features import inflacion_esperada, precios
from mora.rendimientos import comparacion, sistema
from mora.satelite import build_dataset, design, fit, inv_logit, residuos, select_spec, signs_ok

CANAL_DE = {
    "salario_real_ia": "poder_compra",
    "tasa_real_cft": "costo_financiero",
    "absorcion_d12": "esterilizacion",
    "tcr_ia": "ancla_cambiaria",
    "credito_real_ia": "cosecha_dilucion",
    # variante costo_dividido: el costo financiero separado en fondeo (política monetaria) y spread (riesgo)
    "tasa_real_fondeo": "tasa_fondeo_politica",
    "spread_personales": "spread_riesgo",
    # variante costo_oportunidad: la tasa a familias separada en lo que paga el Estado y la prima sobre eso
    "tasa_real_estado": "rendimiento_estado",
    "prima_sobre_estado": "prima_familias",
}


def absorcion_sistema() -> pd.Series:
    """(Títulos públicos + otros créditos por intermediación) / activo, sistema financiero, moneda nacional (%)."""
    a = pd.read_csv(path("processed") / "anexo_balance_por_grupo.csv", parse_dates=["fecha"])
    a = a[a["seccion"] == "Sistema financiero"].pivot_table(index="fecha", columns="concepto", values="valor")
    return 100 * (a["Títulos públicos"] + a["Otros créditos por intermediación financiera"]) / a["Activo"]


def channel_dataset(deflactor: str) -> pd.DataFrame:
    df = build_dataset(deflactor=deflactor)
    bcra = pd.read_csv(path("processed") / "bcra_mensual.csv", index_col=0, parse_dates=True)
    ipc = precios(deflactor)["ipc"]
    tcr = (bcra["tipo_cambio_mayorista"] / ipc).reindex(df.index)
    df["tcr_ia"] = 100 * np.log(tcr).diff(12)
    df["absorcion_d12"] = absorcion_sistema().reindex(df.index).diff(12)
    # Fondeo: BADLAR (plazo fijo mayorista) real con la misma expectativa de inflación que el CFT
    infl_exp = inflacion_esperada(deflactor, df.index)
    badlar_tea = ((1 + bcra["tasa_badlar_privados"] / 100 / 12) ** 12 - 1).reindex(df.index)
    df["tasa_real_fondeo"] = 100 * ((1 + badlar_tea) / (1 + infl_exp) - 1)
    df["spread_personales"] = (bcra["tasa_prestamos_personales"] - bcra["tasa_badlar_privados"]).reindex(df.index)
    # Costo de oportunidad: rendimiento implícito de títulos + pases en pesos del balance (mora.rendimientos)
    rend = comparacion(sistema()).reindex(df.index)
    df["tasa_real_estado"] = 100 * ((1 + rend["tea_estado_3m"] / 100) / (1 + infl_exp) - 1)
    df["prima_sobre_estado"] = rend["prima_personales_sobre_estado_pp"]
    return df


def simulate(params: pd.Series, df: pd.DataFrame, spec, desde: pd.Timestamp, hasta: pd.Timestamp,
             resid: pd.Series, override: dict[str, float] | None = None) -> pd.Series:
    """Simula la mora (%) entre desde y hasta sumando los residuos observados.

    Con `override` = {variable: valor de referencia}, ese canal queda fijo en la referencia
    (contrafáctico). Sin override, la simulación reproduce exactamente la mora observada.
    """
    work = df.copy()
    for var, ref in (override or {}).items():
        work[var] = ref
    _, X = design(work, spec)
    y = float(df.loc[desde - pd.DateOffset(months=1), "y"])
    dys = df["dy"].copy()
    out = {}
    for t in pd.date_range(desde, hasta, freq="MS"):
        dy = params["const"] + resid.get(t, 0.0)
        for j in range(1, spec.ar + 1):
            dy += params[f"dy_l{j}"] * dys.shift(j).loc[t]
        for var, lag in spec.lags.items():
            dy += params[f"{var}_l{lag}"] * X.loc[t, f"{var}_l{lag}"]
        dys.loc[t] = dy
        y += dy
        out[t] = float(inv_logit(y))
    return pd.Series(out)


def historical_decomposition(res, df: pd.DataFrame, spec, desde: pd.Timestamp, hasta: pd.Timestamp,
                             referencias: dict[str, float]) -> pd.DataFrame:
    """Aporte de cada canal = mora simulada con datos reales − mora simulada con el canal neutral.

    Las filas de la ventana que quedaron fuera de la estimación no tienen residuo: se toma cero.
    Bandas: el mismo contrafáctico con el coeficiente del canal en los extremos de su IC 95%.
    """
    resid = residuos(res.params, df, spec)
    base = simulate(res.params, df, spec, desde, hasta, resid)
    ci = res.conf_int()
    rows = []
    for var, lag in spec.lags.items():
        k = f"{var}_l{lag}"
        cf = simulate(res.params, df, spec, desde, hasta, resid, {var: referencias[var]})
        aportes = []
        for b in (ci.loc[k, 0], ci.loc[k, 1]):
            p = res.params.copy()
            p[k] = b
            aportes.append(simulate(p, df, spec, desde, hasta, resid).iloc[-1]
                           - simulate(p, df, spec, desde, hasta, resid, {var: referencias[var]}).iloc[-1])
        rows.append({
            "canal": CANAL_DE[var], "variable": var, "rezago": lag, "referencia": referencias[var],
            "coef": float(res.params[k]), "pvalor": float(res.pvalues[k]),
            "aporte_pp": float(base.iloc[-1] - cf.iloc[-1]),
            "aporte_pp_ic_inf": float(min(aportes)), "aporte_pp_ic_sup": float(max(aportes)),
        })
    out = pd.DataFrame(rows)
    pos = out["aporte_pp"].clip(lower=0).sum()
    out["peso_sobre_aportes_positivos_pct"] = 100 * out["aporte_pp"].clip(lower=0) / pos if pos > 0 else np.nan
    out.attrs["mora_simulada_fin"] = float(base.iloc[-1])
    return out


def run(deflactor: str, variante: str = "base") -> dict:
    cfg = settings()["canales"]
    var = cfg["variantes"][variante]
    sat = settings()["satelite"]
    df = channel_dataset(deflactor).loc[cfg["inicio"]:]
    expected = {**sat["signos_esperados"], **cfg["signos_esperados"]}
    spec, ranking = select_spec(df, var["grilla"], sat["ar_max"], expected)
    res = fit(df, spec)
    mora = df["mora"]
    desde = mora.loc[cfg["buscar_minimo_desde"]:].idxmin()
    hasta = df["dy"].dropna().index.max()
    referencias = {v: (df.loc[: desde, v].mean() if r == "media_previa" else float(r))
                   for v, r in cfg["referencias"].items() if v in var["grilla"]}
    contrib = historical_decomposition(res, df, spec, desde + pd.DateOffset(months=1), hasta, referencias)
    meta = {
        "deflactor": deflactor, "variante": variante, "especificacion": spec.name(), "signos_ok": bool(signs_ok(res, spec, expected)),
        "n": int(res.nobs), "r2_ajustado": float(res.rsquared_adj),
        "ventana": [str(desde.date()), str(hasta.date())],
        "mora_inicio": float(mora.loc[desde]), "mora_fin": float(mora.loc[hasta]),
        "cambio_observado_pp": float(mora.loc[hasta] - mora.loc[desde]),
        "suma_aportes_canales_pp": float(contrib["aporte_pp"].sum()),
        "mora_simulada_fin": contrib.attrs["mora_simulada_fin"],
        "referencias": {k: float(v) for k, v in referencias.items()},
    }
    coefs = pd.DataFrame({"coef": res.params, "pvalor": res.pvalues}).rename_axis("termino").reset_index()
    tags = {"deflactor": deflactor, "variante": variante}
    return {"contribuciones": contrib.assign(**tags), "meta": meta, "coeficientes": coefs.assign(**tags),
            "ranking": ranking.head(10).assign(**tags)}


def main() -> None:
    out = path("outputs") / "canales"
    out.mkdir(parents=True, exist_ok=True)
    corridas = {(d, v): run(d, v) for v in settings()["canales"]["variantes"] for d in DEFLACTORES}
    pd.concat([c["contribuciones"] for c in corridas.values()]).to_csv(out / "aportes_por_canal.csv", index=False)
    pd.concat([c["coeficientes"] for c in corridas.values()]).to_csv(out / "coeficientes.csv", index=False)
    pd.concat([c["ranking"] for c in corridas.values()]).to_csv(out / "seleccion_rezagos.csv", index=False)
    with open(out / "resumen_canales.json", "w", encoding="utf-8") as fh:
        json.dump({f"{v}_{d}": c["meta"] for (d, v), c in corridas.items()}, fh, ensure_ascii=False, indent=2)
    print(f"canales: {out}")


if __name__ == "__main__":
    main()
