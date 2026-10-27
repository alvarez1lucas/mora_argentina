"""Robustez de medición: el modelo satélite con las tres mediciones de precios.

`python -m mora.robustez` escribe outputs/robustez/:
- indices_precios.csv: las tres mediciones más el IPCBA (base dic-2016 = 100).
- inflacion_por_periodo.csv: inflación acumulada por etapa con cada medición.
- validacion.json: ponderaciones implícitas del oficial y error de reconstrucción.
- <deflactor>/: los outputs completos del modelo con cada deflactor.
- comparacion.csv: coeficientes clave y error fuera de muestra lado a lado.
"""

from __future__ import annotations

import json

import pandas as pd

from mora.config import path, settings
from mora.deflactores import DEFLACTORES, build, validation_report
from mora.satelite import run_all

# Etapas para comparar las mediciones (desde, hasta)
ETAPAS = {
    "indec_intervenido_2012_2016": ("2012-07-01", "2016-12-01"),
    "tarifas_congeladas_2016_2023": ("2016-12-01", "2023-11-01"),
    "ajuste_2023_hoy": ("2023-11-01", None),
}


def inflation_by_period(indices: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for etapa, (desde, hasta) in ETAPAS.items():
        d = indices.loc[desde:hasta].dropna()
        rows.append({"etapa": etapa, "desde": str(d.index[0].date()), "hasta": str(d.index[-1].date()),
                     **(100 * (d.iloc[-1] / d.iloc[0] - 1)).round(1).to_dict()})
    return pd.DataFrame(rows)


def comparison(corridas_por_deflactor: dict[str, list[dict]]) -> pd.DataFrame:
    rows = []
    for deflactor, corridas in corridas_por_deflactor.items():
        for c in corridas:
            coefs = c["coeficientes"].set_index("termino")
            oos = c["oos"]
            sat = oos[oos["modelo"] == "satelite"].set_index("h")
            ar = oos[oos["modelo"] == "ar1"].set_index("h")
            row = {"deflactor": deflactor, "corrida": c["tag"].rsplit("_", 1)[0], "especificacion": c["meta"]["especificacion"],
                   "n": c["meta"]["n"], "r2_ajustado": round(c["meta"]["r2_ajustado"], 3), "signos_ok": c["meta"]["signos_ok"]}
            for var in ("tasa_real_cft", "salario_real_ia", "empleo_ia", "emae_ia", "credito_real_ia"):
                term = next((t for t in coefs.index if t.startswith(f"{var}_l")), None)
                row[f"{var}_coef"] = coefs.loc[term, "coef"] if term else None
                row[f"{var}_pvalor"] = coefs.loc[term, "pvalor"] if term else None
            for h in (6, 12):
                row[f"rmse_h{h}"] = sat.loc[h, "rmse"] if h in sat.index else None
                row[f"rmse_h{h}_vs_ar1"] = sat.loc[h, "rmse"] / ar.loc[h, "rmse"] if h in sat.index else None
            rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    out = path("outputs") / "robustez"
    out.mkdir(parents=True, exist_ok=True)
    indices = build()
    cols = ["publico", "seleccionado", "mix", "ipcba"]
    indices.to_csv(out / "indices_precios.csv", date_format="%Y-%m-%d")
    inflation_by_period(indices[cols].astype(float)).to_csv(out / "inflacion_por_periodo.csv", index=False)
    with open(out / "validacion.json", "w", encoding="utf-8") as fh:
        json.dump(validation_report(), fh, ensure_ascii=False, indent=2)

    corridas = {d: run_all(d, out / d) for d in DEFLACTORES}
    comparison(corridas).to_csv(out / "comparacion.csv", index=False)
    print(f"robustez: {out} (principal: {settings()['deflactores']['principal']})")


if __name__ == "__main__":
    main()
