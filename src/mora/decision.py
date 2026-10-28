"""Fase 9: capa de decisión para el otorgamiento de crédito a familias.

`python -m mora.decision` escribe outputs/decision/.

Traduce los escenarios (mora.escenarios) y el costo de oportunidad (mora.rendimientos) en dos insumos
para la política de crédito, por línea (préstamos personales y tarjetas):

1. Ajuste de PD por escenario. La mora de cada línea se proyecta desde la mora total del escenario
   con la sensibilidad histórica de la línea a la total (Δ12 del logit, muestra limpia). Con la mora
   de la línea como proxy de la PD a 12 meses, el ajuste es un desplazamiento en el logit:
   PD_escenario = inv_logit(logit(PD_modelo) + Δ). Con Δ respecto del promedio del ciclo (TTC), un
   modelo de scoring calibrado TTC que aprueba con PD < c debe aprobar con PD < inv_logit(logit(c) − Δ)
   para mantener el mismo riesgo efectivo.
2. Tasa mínima de originación. Un préstamo a un año rinde (1 + r) si paga y recupera (1 − LGD) del
   capital si no paga. Para empatar lo que rinde prestarle al Estado más los costos operativos:
       r_min = [(1 + r_Estado + costo) − PD·(1 − LGD)] / (1 − PD) − 1
   y la PD de equilibrio a la tasa vigente: PD* = [(1 + r) − (1 + r_Estado + costo)] / [(1 + r) − (1 − LGD)].
   El CFT que paga la familia suma el IVA sobre los intereses (mora.features.cft_aproximado).

Supuestos que no salen de datos públicos (LGD y costo operativo) van con tabla de sensibilidad.
La mora de la línea es una proxy de la PD promedio de la cartera, no de la PD marginal de un solicitante.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import statsmodels.api as sm

from mora.config import path, settings
from mora.deflactores import DEFLACTORES
from mora.satelite import logit as logit_pct

# En este módulo las probabilidades van en fracción (0-1); mora.satelite.logit/inv_logit trabajan en %.


def logit(p):
    p = np.asarray(p, dtype=float)
    return np.log(p / (1 - p))


def inv_logit(z):
    return 1 / (1 + np.exp(-np.asarray(z, dtype=float)))

ESCENARIOS = ("base", "adverso", "favorable")


def _lineas() -> pd.DataFrame:
    f = pd.read_csv(path("outputs") / "descriptivo" / "familias_por_linea.csv", parse_dates=["fecha"])
    return f.pivot(index="fecha", columns="linea", values="ratio")


def sensibilidad_linea(m: pd.DataFrame, linea: str, desde: str) -> dict:
    """β de Δ12 logit(línea) sobre Δ12 logit(total), con errores HAC."""
    d = m.loc[desde:]
    y = logit_pct(d[linea]).diff(12)
    x = logit_pct(d["total"]).diff(12)
    data = pd.concat([y.rename("y"), x.rename("x")], axis=1).dropna()
    res = sm.OLS(data["y"], sm.add_constant(data["x"])).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
    return {"beta": float(res.params["x"]), "se": float(res.bse["x"]), "r2": float(res.rsquared), "n": int(res.nobs)}


def pd_por_escenario(deflactor: str) -> pd.DataFrame:
    """Mora proyectada por línea a fin del horizonte (proxy de PD a 12 meses) y su desplazamiento logit."""
    cfg = settings()["decision"]
    esc = json.load(open(path("outputs") / "escenarios" / "resumen_escenarios.json", encoding="utf-8"))[f"satelite_{deflactor}"]
    m = _lineas()
    origen = pd.Timestamp(esc["origen"])
    total_hoy = float(m.loc[origen, "total"]) / 100
    filas = []
    for linea in cfg["lineas"]:
        s = sensibilidad_linea(m, linea, cfg["ttc_desde"])
        hoy = float(m.loc[origen, linea]) / 100
        ttc = float(m.loc[cfg["ttc_desde"]:, linea].mean()) / 100
        casos = {e: esc["mora_fin"][e]["central"] for e in ESCENARIOS}
        casos["adverso_p95"] = esc["mora_fin"]["adverso"]["p95"]
        casos["niif9_ponderado"] = esc["niif9"]["mora_ponderada"]
        for caso, total_fin in casos.items():
            mover = s["beta"] * (logit(total_fin / 100) - logit(total_hoy))
            pd_fin = float(inv_logit(logit(hoy) + mover))
            filas.append({
                "deflactor": deflactor, "linea": linea, "escenario": caso, "fecha": esc["fin"],
                "mora_total_fin_pct": total_fin, "pd_12m_pct": 100 * pd_fin, "pd_hoy_pct": 100 * hoy, "pd_ttc_pct": 100 * ttc,
                "beta_linea": s["beta"], "beta_se": s["se"],
                "delta_logit_vs_ttc": float(logit(pd_fin) - logit(ttc)), "delta_logit_vs_hoy": float(logit(pd_fin) - logit(hoy)),
                "multiplicador_vs_ttc": pd_fin / ttc, "multiplicador_vs_hoy": pd_fin / hoy,
            })
    return pd.DataFrame(filas)


def cortes(pds: pd.DataFrame, cortes_ttc: list[float]) -> pd.DataFrame:
    """Punto de corte equivalente sobre la PD de un modelo calibrado TTC, por escenario."""
    filas = []
    for _, r in pds.iterrows():
        for c in cortes_ttc:
            filas.append({"deflactor": r["deflactor"], "linea": r["linea"], "escenario": r["escenario"],
                          "corte_ttc_pct": 100 * c,
                          "corte_equivalente_pct": 100 * float(inv_logit(logit(c) - r["delta_logit_vs_ttc"]))})
    return pd.DataFrame(filas)


def tasa_minima(pd_: float, r_estado: float, costo: float, lgd: float) -> float:
    """TEA mínima (fracción) para empatar al Estado + costos, con default al año y recupero 1 − LGD."""
    return ((1 + r_estado + costo) - pd_ * (1 - lgd)) / (1 - pd_) - 1


def pd_equilibrio(r: float, r_estado: float, costo: float, lgd: float) -> float:
    """PD máxima a la que la tasa r todavía empata al Estado + costos."""
    return ((1 + r) - (1 + r_estado + costo)) / ((1 + r) - (1 - lgd))


def cft_desde_tea(tea: float, iva: float = 0.21) -> float:
    """CFT anual (fracción) que paga la familia: IVA sobre los intereses mensuales."""
    tem = (1 + tea) ** (1 / 12) - 1
    return (1 + tem * (1 + iva)) ** 12 - 1


def tasas(pds: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    cfg = settings()["decision"]
    rend = pd.read_csv(path("outputs") / "rendimientos" / "estado_vs_familias.csv", index_col=0, parse_dates=True)
    r_estado = float(rend["tea_estado_3m"].dropna().iloc[-1]) / 100
    fecha_estado = str(rend["tea_estado_3m"].dropna().index[-1].date())
    bcra = pd.read_csv(path("processed") / "bcra_mensual.csv", index_col=0, parse_dates=True)
    tna = bcra["tasa_prestamos_personales"].dropna()
    tea_mercado = (1 + float(tna.iloc[-1]) / 100 / 12) ** 12 - 1
    filas = []
    for _, r in pds.iterrows():
        for lgd in cfg["lgd"]:
            for costo in cfg["costo_operativo_pp"]:
                c = costo / 100
                rmin = tasa_minima(r["pd_12m_pct"] / 100, r_estado, c, lgd)
                fila = {"deflactor": r["deflactor"], "linea": r["linea"], "escenario": r["escenario"],
                        "pd_12m_pct": r["pd_12m_pct"], "lgd": lgd, "costo_operativo_pp": costo,
                        "tea_estado_pct": 100 * r_estado, "tea_minima_pct": 100 * rmin, "cft_minimo_pct": 100 * cft_desde_tea(rmin)}
                if r["linea"] == "personales":  # única línea con tasa de mercado en la API del BCRA
                    fila.update({"tea_mercado_pct": 100 * tea_mercado, "colchon_pp": 100 * (tea_mercado - rmin),
                                 "pd_equilibrio_pct": 100 * pd_equilibrio(tea_mercado, r_estado, c, lgd)})
                filas.append(fila)
    meta = {"tea_estado_pct": 100 * r_estado, "fecha_tea_estado": fecha_estado,
            "tna_personales_mercado_pct": float(tna.iloc[-1]), "fecha_tna": str(tna.index[-1].date()),
            "tea_personales_mercado_pct": 100 * tea_mercado}
    return pd.DataFrame(filas), meta


def main() -> None:
    cfg = settings()["decision"]
    out = path("outputs") / "decision"
    out.mkdir(parents=True, exist_ok=True)
    pds = pd.concat([pd_por_escenario(d) for d in DEFLACTORES], ignore_index=True)
    pds.to_csv(out / "pd_por_escenario.csv", index=False)
    cortes(pds, cfg["cortes_ttc"]).to_csv(out / "cortes_aprobacion.csv", index=False)
    t, meta = tasas(pds)
    t.to_csv(out / "tasa_minima_originacion.csv", index=False)
    ref = t[(t["lgd"] == cfg["lgd_central"]) & (t["costo_operativo_pp"] == cfg["costo_central_pp"])]
    resumen = {
        **meta, "lgd_central": cfg["lgd_central"], "costo_central_pp": cfg["costo_central_pp"],
        "pd_publico": pds[pds["deflactor"] == "publico"].set_index(["linea", "escenario"])[
            ["pd_12m_pct", "pd_ttc_pct", "pd_hoy_pct", "multiplicador_vs_ttc", "delta_logit_vs_ttc"]].round(3)
            .reset_index().to_dict("records"),
        "tasa_minima_publico_central": ref[ref["deflactor"] == "publico"][
            ["linea", "escenario", "pd_12m_pct", "tea_minima_pct", "cft_minimo_pct", "colchon_pp", "pd_equilibrio_pct"]]
            .round(2).replace({np.nan: None}).to_dict("records"),
    }
    with open(out / "resumen_decision.json", "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, ensure_ascii=False, indent=2)
    print(f"decisión: {out}")


if __name__ == "__main__":
    main()
