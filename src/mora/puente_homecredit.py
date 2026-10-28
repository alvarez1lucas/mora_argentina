"""Puente con homecredit-pd-validation: el ajuste macro aplicado a un modelo de scoring real.

`python -m mora.puente_homecredit [--actualizar]` escribe outputs/puente_homecredit/.

El proyecto homecredit-pd-validation (github.com/alvarez1lucas/homecredit-pd-validation) tiene un
modelo de PD individual calibrado sobre el dataset público de Home Credit (Kaggle). Acá se toma la
distribución de sus PD del set de prueba como si fuera la de un modelo de scoring calibrado en un año
normal (TTC) y se le aplica la capa macro de la Fase 9:

1. Ajuste por escenario: PD_momento = inv_logit(logit(PD) + Δ), con el Δ de préstamos personales de
   mora.decision (hoy, base, adverso).
2. Dos reglas de corte:
   - la del proyecto Home Credit para Argentina, PD* = r / (r + LGD): un préstamo a un año que sólo
     tiene que cubrir la pérdida esperada;
   - la de la Fase 9, que además exige empatarle a lo que paga el Estado más el costo operativo:
     PD* = [(1 + r) − (1 + r_Estado + costo)] / [(1 + r) − (1 − LGD)].
   Con la misma tasa de mercado y la misma LGD en las dos.

Se versiona sólo una tabla derivada (cuantiles de la PD y tasa de default observada por cuantil),
no los datos del otro proyecto. Con --actualizar se regenera desde el repo local, si existe.
Limitación: Home Credit no es una cartera argentina; la distribución sirve como forma realista de
un modelo calibrado, no como nivel de riesgo argentino.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from mora.config import path, settings
from mora.decision import inv_logit, logit, pd_equilibrio

ESCENARIOS = ("ttc", "hoy", "base", "adverso")


def actualizar_cuantiles(origen: Path, n: int) -> pd.DataFrame:
    """Cuantiles de la PD calibrada del set de prueba de Home Credit y default observado en cada tramo."""
    p = pd.read_parquet(origen, columns=["pd", "default"])
    p["tramo"] = pd.qcut(p["pd"].rank(method="first"), n, labels=False)
    t = p.groupby("tramo").agg(pd_media=("pd", "mean"), default_obs=("default", "mean"), n=("pd", "size")).reset_index()
    return t


def desplazamientos() -> dict[str, float]:
    """Δ logit de préstamos personales (medición pública) por escenario respecto del promedio del ciclo."""
    p = pd.read_csv(path("outputs") / "decision" / "pd_por_escenario.csv")
    p = p[(p["deflactor"] == "publico") & (p["linea"] == "personales")].set_index("escenario")
    hoy = float(logit(p["pd_hoy_pct"].iloc[0] / 100) - logit(p["pd_ttc_pct"].iloc[0] / 100))
    return {"ttc": 0.0, "hoy": hoy, "base": float(p.loc["base", "delta_logit_vs_ttc"]),
            "adverso": float(p.loc["adverso", "delta_logit_vs_ttc"])}


def evaluar(tramos: pd.DataFrame, deltas: dict[str, float], cortes: dict[str, float]) -> pd.DataFrame:
    """Aprobación, PD media de los aprobados y pérdida esperada, por escenario y regla de corte."""
    w = tramos["n"] / tramos["n"].sum()
    filas = []
    for e in ESCENARIOS:
        pd_e = inv_logit(logit(tramos["pd_media"].clip(1e-6, 1 - 1e-6)) + deltas[e])
        for regla, corte in cortes.items():
            aprob = pd_e < corte
            share = float(w[aprob].sum())
            filas.append({"escenario": e, "regla": regla, "corte_pd_pct": 100 * corte,
                          "pd_media_cartera_pct": 100 * float((w * pd_e).sum()),
                          "aprobacion_pct": 100 * share,
                          "pd_media_aprobados_pct": 100 * float((w[aprob] * pd_e[aprob]).sum() / share) if share else np.nan})
    return pd.DataFrame(filas)


def main(argv: list[str] | None = None) -> None:
    cfg = settings()["puente_homecredit"]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actualizar", action="store_true", help="regenerar los cuantiles desde el repo local de Home Credit")
    args = parser.parse_args(argv)
    archivo = path("processed") / "homecredit_pd_cuantiles.csv"
    if args.actualizar:
        actualizar_cuantiles(Path(cfg["predicciones"]), cfg["cuantiles"]).to_csv(archivo, index=False)
    tramos = pd.read_csv(archivo)

    dec = json.load(open(path("outputs") / "decision" / "resumen_decision.json", encoding="utf-8"))
    r = dec["tea_personales_mercado_pct"] / 100
    r_e = dec["tea_estado_pct"] / 100
    lgd, costo = dec["lgd_central"], dec["costo_central_pp"] / 100
    cortes = {"solo_perdida_esperada": r / (r + lgd), "con_costo_de_oportunidad": pd_equilibrio(r, r_e, costo, lgd)}
    deltas = desplazamientos()
    res = evaluar(tramos, deltas, cortes)

    out = path("outputs") / "puente_homecredit"
    out.mkdir(parents=True, exist_ok=True)
    res.to_csv(out / "aprobacion_por_escenario.csv", index=False)
    resumen = {"tea_mercado_pct": 100 * r, "tea_estado_pct": 100 * r_e, "lgd": lgd, "costo_operativo_pp": 100 * costo,
               "cortes_pd_pct": {k: round(100 * v, 2) for k, v in cortes.items()},
               "delta_logit": {k: round(v, 3) for k, v in deltas.items()},
               "pd_media_homecredit_pct": round(100 * float((tramos["pd_media"] * tramos["n"]).sum() / tramos["n"].sum()), 2),
               "default_observado_homecredit_pct": round(100 * float((tramos["default_obs"] * tramos["n"]).sum() / tramos["n"].sum()), 2),
               "n_solicitudes": int(tramos["n"].sum()),
               "tabla": res.round(2).to_dict("records")}
    with open(out / "resumen_puente.json", "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, ensure_ascii=False, indent=2)
    print(f"puente homecredit: {out}")


if __name__ == "__main__":
    main()
