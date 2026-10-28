"""Deuda del Tesoro en pesos: cuánto le debe el Estado al mercado, cuánto renueva y cuánto capitaliza.

`python -m mora.deuda` escribe outputs/deuda/.

Complementa la cadena esterilización → tasa → mora del lado del Tesoro (mora.ingest.finanzas):
- stock de deuda en moneda local (CER y no CER) en % del PBI, junto a la exposición de los bancos;
- rollover del mercado en pesos: colocado / vencido en los instrumentos que se licitan. Con rollover
  < 100% el Tesoro devuelve pesos al mercado (inyecta liquidez); con > 100% los absorbe;
- capitalización de intereses: intereses que no se pagan sino que se suman al capital (LECAP,
  BONCAP), en % del PBI anualizado;
- relación entre el rollover y las tasas de los meses siguientes (lo que paga el Estado y la tasa
  de los préstamos personales).

Las cifras del boletín están en dólares: los stocks se pasan a pesos con el tipo de cambio mayorista
del último día del mes y los flujos con el promedio del mes. Para el rollover la moneda no importa.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from mora.ajuste import pbi_anual_mensual, profundidad
from mora.config import path, settings
from mora.features import load
from mora.rendimientos import comparacion, sistema


def serie() -> pd.DataFrame:
    d = pd.read_csv(path("processed") / "deuda_tesoro.csv", index_col="fecha", parse_dates=True)
    bcra = load("bcra_mensual")
    tc_fin, tc_medio = bcra["tipo_cambio_mayorista_fin"].reindex(d.index), bcra["tipo_cambio_mayorista"].reindex(d.index)
    pbi = pbi_anual_mensual()["pbi_anual"].reindex(d.index)
    prof = profundidad()
    out = pd.DataFrame(index=d.index)
    for c in ("deuda_moneda_local", "deuda_no_cer", "deuda_cer"):
        out[f"{c}_pbi"] = 100 * d[f"{c}_usd"] * tc_fin / pbi
    out["deuda_moneda_local_pct_total"] = 100 * d["deuda_moneda_local_usd"] / d["deuda_total_pago_normal_usd"]
    emis, amort = d["emisiones_mercado_pesos_usd"], d["amortizaciones_mercado_pesos_usd"]
    out["rollover_pct"] = 100 * emis / amort.replace(0, np.nan)
    out["rollover_3m_pct"] = 100 * emis.rolling(3).sum() / amort.rolling(3).sum()
    out["financiamiento_neto_pbi"] = 100 * (emis - amort) * tc_medio * 12 / pbi  # anualizado
    out["capitalizacion_pbi"] = 100 * d["capitalizacion_usd"] * tc_medio * 12 / pbi  # anualizado
    out["bancos_exposicion_estado_pbi"] = prof["exposicion_estado_mn_pbi"].reindex(d.index)
    out["bancos_titulos_mn_pbi"] = prof["titulos_publicos_mn_pbi"].reindex(d.index)
    return out


def rollover_y_tasas(s: pd.DataFrame, horizontes: list[int]) -> pd.DataFrame:
    """Correlación del rollover de 3 meses con la variación posterior de lo que paga el Estado y de la tasa de préstamos."""
    rend = comparacion(sistema()).reindex(s.index)
    filas = []
    for h in horizontes:
        fila = {"h": h, "n": int(s["rollover_3m_pct"].notna().sum())}
        for nombre, serie_tasa in (("tea_estado", rend["tea_estado_3m"]), ("tea_prestamos", rend["tea_personales_nuevos"])):
            futuro = serie_tasa.shift(-h) - serie_tasa
            fila[f"corr_{nombre}"] = float(s["rollover_3m_pct"].corr(futuro))
        filas.append(fila)
    return pd.DataFrame(filas)


def main() -> None:
    cfg = settings()["deuda"]
    out = path("outputs") / "deuda"
    out.mkdir(parents=True, exist_ok=True)
    s = serie()
    s.to_csv(out / "deuda_tesoro_pesos.csv", date_format="%Y-%m-%d")
    corr = rollover_y_tasas(s, cfg["horizontes"])
    corr.to_csv(out / "rollover_y_tasas.csv", index=False)
    ult = s["deuda_moneda_local_pbi"].dropna().index.max()
    fila = lambda t, cols: {c: round(float(s.loc[t, c]), 2) for c in cols if pd.notna(s.loc[t, c])}  # noqa: E731
    cols = ["deuda_moneda_local_pbi", "deuda_cer_pbi", "deuda_no_cer_pbi", "deuda_moneda_local_pct_total",
            "bancos_exposicion_estado_pbi", "bancos_titulos_mn_pbi"]
    anual = s.loc["2024-01-01":].groupby(s.loc["2024-01-01":].index.year).agg(
        rollover_pct=("rollover_pct", "median"), capitalizacion_pbi=("capitalizacion_pbi", "mean"),
        financiamiento_neto_pbi=("financiamiento_neto_pbi", "mean"))
    resumen = {
        "ultimo": str(ult.date()), "ultimo_valores": fila(ult, cols), "nov23": fila(pd.Timestamp("2023-11-01"), cols),
        "ultimo_flujos": str(s["rollover_pct"].dropna().index.max().date()),
        "rollover_ultimos_6m": {str(t.date()): round(float(v), 1) for t, v in s["rollover_pct"].dropna().iloc[-6:].items()},
        "anual_desde_2024": {str(k): {c: round(float(v), 2) for c, v in r.items()} for k, r in anual.iterrows()},
        "rollover_y_tasas": corr.round(3).to_dict("records"),
    }
    with open(out / "resumen_deuda.json", "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, ensure_ascii=False, indent=2)
    print(f"deuda: {out}")


if __name__ == "__main__":
    main()
