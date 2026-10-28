"""Chequeo: ¿cambian las conclusiones si la inflación esperada sale del REM?

`python -m mora.expectativas` escribe outputs/expectativas/.

En todo el proyecto la tasa real se calcula con la inflación de los últimos 3 meses anualizada
(mora.features.inflacion_esperada). La alternativa natural es la mediana del Relevamiento de
Expectativas de Mercado (REM) del BCRA a 12 meses. Se repiten, con las dos medidas y la medición de
precios pública, las piezas que dependen de la tasa real:

- modelo satélite en la muestra limpia (2017+, donde hay REM todos los meses): coeficiente de la
  tasa real, su p-valor y el ajuste;
- cadena en dos etapas (mora.cadena): aporte de la tasa a la suba de la mora, su p-valor, el peso de
  lo que paga el Estado en la suba de la tasa y el traspaso.

El REM es sobre el IPC oficial, por eso sólo se compara con la medición pública.
"""

from __future__ import annotations

import json
from contextlib import contextmanager

import numpy as np
import pandas as pd

from mora import cadena
from mora.config import path, settings
from mora.features import inflacion_esperada, precios
from mora.satelite import build_dataset, fit, select_spec, signs_ok

MEDIDAS = ("previa", "rem")


@contextmanager
def medida(nombre: str):
    """Cambia la medida de inflación esperada mientras dura el bloque (settings() está en caché)."""
    cfg = settings()["satelite"]
    anterior = cfg.get("expectativa_inflacion", "previa")
    cfg["expectativa_inflacion"] = nombre
    try:
        yield
    finally:
        cfg["expectativa_inflacion"] = anterior


def satelite_limpia(deflactor: str) -> dict:
    sat = settings()["satelite"]
    df = build_dataset(deflactor=deflactor)
    df.loc[df["ipc_empalmado"], ["tasa_real_cft", "credito_real_ia", "salario_real_ia"]] = np.nan
    df = df.loc[settings()["sample"]["muestras"]["limpia"]["inicio"]:]
    grilla, signos = sat["especificaciones"]["base"]["grilla"], sat["signos_esperados"]
    spec, _ = select_spec(df, grilla, sat["ar_max"], signos)
    res = fit(df, spec)
    k = f"tasa_real_cft_l{spec.lags['tasa_real_cft']}" if "tasa_real_cft" in spec.lags else None
    return {"especificacion": spec.name(), "signos_ok": bool(signs_ok(res, spec, signos)), "n": int(res.nobs),
            "r2_ajustado": float(res.rsquared_adj),
            "coef_tasa": float(res.params[k]) if k else None, "p_tasa": float(res.pvalues[k]) if k else None}


def comparar(deflactor: str = "publico") -> tuple[pd.DataFrame, pd.DataFrame]:
    filas = []
    for m in MEDIDAS:
        with medida(m):
            s = satelite_limpia(deflactor)
            c = cadena.run(deflactor)
        e1 = c["etapa1"].set_index("parte")
        meta = c["meta"]
        filas.append({
            "medida": m, "sat_especificacion": s["especificacion"], "sat_signos_ok": s["signos_ok"], "sat_n": s["n"],
            "sat_r2_ajustado": s["r2_ajustado"], "sat_coef_tasa": s["coef_tasa"], "sat_p_tasa": s["p_tasa"],
            "cadena_especificacion": meta["especificacion"], "cadena_aporte_tasa_pp": meta["aporte_tasa_pp"],
            "cadena_p_tasa": meta["p_tasa"], "cadena_tasa_previa_pp": meta["tasa_real_previa_pp"],
            "cadena_tasa_ventana_pp": meta["tasa_real_ventana_pp"],
            "cadena_peso_estado_pct": float(e1.loc["estado", "peso_en_suba_tasa_pct"]),
            "cadena_traspaso": meta["traspaso"]["beta_estado"],
        })
    # Las dos medidas de inflación esperada, mes a mes
    idx = pd.date_range("2017-01-01", precios(deflactor).index.max(), freq="MS")
    series = {}
    for m in MEDIDAS:
        with medida(m):
            series[m] = 100 * inflacion_esperada(deflactor, idx)
    return pd.DataFrame(filas), pd.DataFrame(series).rename_axis("fecha")


def main() -> None:
    out = path("outputs") / "expectativas"
    out.mkdir(parents=True, exist_ok=True)
    tabla, series = comparar("publico")
    tabla.to_csv(out / "comparacion.csv", index=False)
    series.to_csv(out / "inflacion_esperada.csv", date_format="%Y-%m-%d")
    with open(out / "resumen_expectativas.json", "w", encoding="utf-8") as fh:
        json.dump(tabla.round(4).to_dict("records"), fh, ensure_ascii=False, indent=2)
    print(f"expectativas: {out}")


if __name__ == "__main__":
    main()
