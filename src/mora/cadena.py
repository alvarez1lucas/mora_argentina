"""Ponderación en dos etapas: esterilización → tasa → mora.

`python -m mora.cadena` escribe outputs/cadena/.

La esterilización no compite con la tasa en la ecuación de la mora: es una causa de la tasa. Si se
ponen las dos en la misma ecuación, el efecto de la esterilización que pasa por la tasa queda
contado en la tasa y a la esterilización sólo le queda el resto ("absorción directa", ~0). Por eso
la ponderación se hace en dos pasos:

Etapa 1 (qué explica la tasa). La tasa real del CFT de préstamos personales se descompone de forma
exacta (identidad contable, con la misma expectativa de inflación π):
    tasa_real_cft = (CFT − π)/(1 + π)
                  = (r_Estado − π)/(1 + π)      lo que paga el Estado: el piso que pone la esterilización
                  + (TEA − r_Estado)/(1 + π)    prima del banco sobre el Estado (riesgo, costos, margen)
                  + (CFT − TEA)/(1 + π)         cuña del IVA sobre los intereses
r_Estado es el rendimiento implícito de títulos + pases en pesos del balance (mora.rendimientos). Se
mide cuánto subió cada parte sobre su promedio previo en los meses que, con el rezago de la etapa 2,
mueven la mora de la ventana. Además se estima el traspaso: Δ12 de la tasa real de los préstamos
contra Δ12 de lo que paga el Estado, controlando por la mora previa (riesgo). Con traspaso 1 el
reparto contable es exacto; con traspaso < 1, parte de lo que paga el Estado no llega a la tasa.

Etapa 2 (qué explica la mora). La ecuación de canales sin la absorción (salario real, tasa real del
CFT, tipo de cambio real, crédito real). El aporte de la tasa se reparte entre sus partes con
contrafácticos: cada parte de la tasa en su promedio previo. El reparto se hace en el logit, donde la
ecuación es lineal y las partes suman exactamente el aporte de la tasa; después se pasa a pp en la
misma proporción.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import statsmodels.api as sm

from mora.canales import CANAL_DE, channel_dataset, historical_decomposition, simulate
from mora.config import path, settings
from mora.deflactores import DEFLACTORES
from mora.features import cft_aproximado, precios
from mora.rendimientos import comparacion, sistema
from mora.satelite import fit, residuos, select_spec, signs_ok
from mora.satelite import logit as logit_pct

COMPONENTES = ("estado", "prima", "impuestos")


def componentes_tasa(deflactor: str, idx: pd.DatetimeIndex, rend: pd.DataFrame) -> pd.DataFrame:
    """Tasa real del CFT y sus tres partes (pp de tasa real anual). Suman exactamente la tasa."""
    bcra = pd.read_csv(path("processed") / "bcra_mensual.csv", index_col=0, parse_dates=True)
    ipc = precios(deflactor)["ipc"]
    w = settings()["satelite"]["ventana_expectativa_inflacion"]
    pi = ((ipc / ipc.shift(w)) ** (12 / w) - 1).reindex(idx)
    return partes_tasa(bcra["tasa_prestamos_personales"].reindex(idx), rend["tea_estado_3m"].reindex(idx), pi)


def partes_tasa(tna: pd.Series, tea_estado: pd.Series, pi: pd.Series) -> pd.DataFrame:
    """Identidad contable: TNA de préstamos (%), TEA del Estado (%) e inflación esperada (fracción)."""
    tea = (1 + tna / 100 / 12) ** 12 - 1
    cft = cft_aproximado(tna) / 100
    r_e = tea_estado / 100
    out = pd.DataFrame({
        "estado": 100 * (r_e - pi) / (1 + pi),
        "prima": 100 * (tea - r_e) / (1 + pi),
        "impuestos": 100 * (cft - tea) / (1 + pi),
    }, index=tna.index)
    out["tasa_real_cft"] = out[list(COMPONENTES)].sum(axis=1, min_count=len(COMPONENTES))
    return out


def traspaso(comp: pd.DataFrame, mora: pd.Series, rezago_mora: int = 3) -> dict:
    """β de Δ12 (tasa real de los préstamos sin IVA) sobre Δ12 (lo que paga el Estado), con la mora previa."""
    tasa_prestamo = comp["estado"] + comp["prima"]
    data = pd.DataFrame({
        "y": tasa_prestamo.diff(12),
        "estado": comp["estado"].diff(12),
        "mora_previa": mora.diff(12).shift(rezago_mora),
    }).dropna()
    res = sm.OLS(data["y"], sm.add_constant(data[["estado", "mora_previa"]])).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
    return {"beta_estado": float(res.params["estado"]), "se_estado": float(res.bse["estado"]),
            "p_estado": float(res.pvalues["estado"]), "beta_mora_previa": float(res.params["mora_previa"]),
            "p_mora_previa": float(res.pvalues["mora_previa"]), "r2": float(res.rsquared), "n": int(res.nobs),
            "desde": str(data.index.min().date()), "hasta": str(data.index.max().date())}


def run(deflactor: str) -> dict:
    cfg, can, sat = settings()["cadena"], settings()["canales"], settings()["satelite"]
    df = channel_dataset(deflactor).loc[can["inicio"]:]
    comp = componentes_tasa(deflactor, df.index, comparacion(sistema()))
    # la identidad reproduce la tasa del modelo (misma TNA, mismo IVA, misma π)
    dif = (comp["tasa_real_cft"] - df["tasa_real_cft"]).abs().max()
    assert dif < 1e-8, f"la descomposición no reproduce la tasa real del CFT ({dif})"

    # ---- etapa 2: mora sin la esterilización como canal propio
    expected = {**sat["signos_esperados"], **can["signos_esperados"]}
    spec, _ = select_spec(df, cfg["grilla_mora"], sat["ar_max"], expected)
    res = fit(df, spec)
    desde = df["mora"].loc[can["buscar_minimo_desde"]:].idxmin()
    hasta = df["dy"].dropna().index.max()
    previo = comp.loc[:desde].dropna()  # promedios previos sobre los mismos meses para todas las partes
    ref_comp = previo[list(COMPONENTES)].mean()
    referencias = {"tasa_real_cft": float(ref_comp.sum())}
    referencias.update({v: 0.0 for v in spec.lags if v != "tasa_real_cft"})
    inicio = desde + pd.DateOffset(months=1)
    contrib = historical_decomposition(res, df, spec, inicio, hasta, referencias)

    lag = spec.lags["tasa_real_cft"]
    k = f"tasa_real_cft_l{lag}"
    resid = residuos(res.params, df, spec)
    ci = res.conf_int()

    def reparto(params: pd.Series) -> dict[str, float]:
        """Aporte de la tasa (pp) repartido entre sus partes según su aporte en el logit.

        En el logit la ecuación es lineal: los aportes de las partes suman exactamente el de la tasa.
        La no linealidad aparece recién al pasar a pp, así que se reparte en proporción al logit.
        """
        base = simulate(params, df, spec, inicio, hasta, resid).iloc[-1]
        cf_tasa = simulate(params, df, spec, inicio, hasta, resid, {"tasa_real_cft": referencias["tasa_real_cft"]}).iloc[-1]
        dz = {}
        for parte in COMPONENTES:
            cf = (df["tasa_real_cft"] - (comp[parte] - ref_comp[parte])).fillna(df["tasa_real_cft"])
            dz[parte] = float(logit_pct(base) - logit_pct(simulate(params, df, spec, inicio, hasta, resid,
                                                                   {"tasa_real_cft": cf}).iloc[-1]))
        total_pp = float(base - cf_tasa)
        return {parte: total_pp * dz[parte] / sum(dz.values()) for parte in COMPONENTES} | {"_dz": dz}

    centro = reparto(res.params)
    bandas = []
    for b in (ci.loc[k, 0], ci.loc[k, 1]):
        p = res.params.copy()
        p[k] = b
        bandas.append(reparto(p))
    partes = pd.DataFrame([{
        "parte": parte, "aporte_pp": centro[parte], "aporte_logit": centro["_dz"][parte],
        "aporte_pp_ic_inf": min(b[parte] for b in bandas), "aporte_pp_ic_sup": max(b[parte] for b in bandas),
    } for parte in COMPONENTES])
    aporte_tasa = float(contrib.loc[contrib["variable"] == "tasa_real_cft", "aporte_pp"].iloc[0])
    partes["peso_en_aporte_tasa_pct"] = 100 * partes["aporte_pp"] / aporte_tasa

    # ---- etapa 1: cuánto subió cada parte de la tasa en los meses que mueven la mora de la ventana
    meses_tasa = comp.loc[inicio - pd.DateOffset(months=lag): hasta - pd.DateOffset(months=lag)]
    exceso = (meses_tasa[list(COMPONENTES)].mean() - ref_comp)
    etapa1 = pd.DataFrame({
        "parte": list(COMPONENTES), "promedio_previo_pp": ref_comp.values,
        "promedio_ventana_pp": meses_tasa[list(COMPONENTES)].mean().values, "exceso_pp": exceso.values,
    })
    etapa1["peso_en_suba_tasa_pct"] = 100 * etapa1["exceso_pp"] / etapa1["exceso_pp"].sum()
    tr = traspaso(comp, df["mora"])
    # Reparto con el traspaso estimado: lo que no pasa del Estado a la tasa queda en la prima
    beta = min(max(tr["beta_estado"], 0.0), 1.0)
    pesos_traspaso = {"estado": beta * exceso["estado"],
                      "prima": exceso["prima"] + (1 - beta) * exceso["estado"],
                      "impuestos": exceso["impuestos"]}
    etapa1["exceso_con_traspaso_pp"] = etapa1["parte"].map(pesos_traspaso)

    tags = {"deflactor": deflactor}
    meta = {
        "deflactor": deflactor, "especificacion": spec.name(), "signos_ok": bool(signs_ok(res, spec, expected)),
        "n": int(res.nobs), "r2_ajustado": float(res.rsquared_adj), "ventana": [str(desde.date()), str(hasta.date())],
        "mora_inicio": float(df.loc[desde, "mora"]), "mora_fin": float(df.loc[hasta, "mora"]),
        "rezago_tasa": lag, "meses_tasa": [str(meses_tasa.index.min().date()), str(meses_tasa.index.max().date())],
        "tasa_real_previa_pp": float(ref_comp.sum()), "tasa_real_ventana_pp": float(meses_tasa["tasa_real_cft"].mean()),
        "aporte_tasa_pp": aporte_tasa,
        "coef_tasa": float(res.params[k]), "p_tasa": float(res.pvalues[k]), "traspaso": tr,
    }
    return {"etapa1": etapa1.assign(**tags), "etapa2": contrib.assign(**tags), "partes": partes.assign(**tags),
            "componentes": comp.assign(**tags), "meta": meta}


def main() -> None:
    out = path("outputs") / "cadena"
    out.mkdir(parents=True, exist_ok=True)
    corridas = {d: run(d) for d in DEFLACTORES}
    for nombre, archivo in (("etapa1", "etapa1_tasa.csv"), ("etapa2", "etapa2_mora.csv"),
                            ("partes", "etapa2_partes_de_la_tasa.csv")):
        pd.concat([c[nombre] for c in corridas.values()]).to_csv(out / archivo, index=False)
    pd.concat([c["componentes"] for c in corridas.values()]).rename_axis("fecha").to_csv(out / "componentes_tasa.csv")
    with open(out / "resumen_cadena.json", "w", encoding="utf-8") as fh:
        json.dump({d: c["meta"] for d, c in corridas.items()}, fh, ensure_ascii=False, indent=2)
    print(f"cadena: {out}")


if __name__ == "__main__":
    main()
