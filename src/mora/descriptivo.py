"""Fase 3: análisis descriptivo. `python -m mora.descriptivo` escribe outputs/descriptivo/.

Todas las tablas salen de data/processed: nada hardcodeado. El sitio web lee sólo estos outputs.
"""

from __future__ import annotations

import json

import pandas as pd

from mora.config import path, settings
from mora.features import familias

_SIT_IRREGULAR = ["esd_consumo_sit3", "esd_consumo_sit4", "esd_consumo_sit5"]


def _processed(name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(path("processed") / f"{name}.csv", **kw)


def familias_tidy() -> pd.DataFrame:
    """Familias por línea en formato largo: ratio, saldos reales y descomposición interanual."""
    f = familias()
    lineas = [c.removeprefix("ratio_") for c in f.columns if c.startswith("ratio_")]
    frames = []
    for linea in lineas:
        frames.append(
            pd.DataFrame(
                {
                    "fecha": f.index,
                    "linea": linea,
                    "ratio": f[f"ratio_{linea}"].values,
                    "saldo_real": f[f"saldo_real_{linea}"].values,
                    "irregular_real": f[f"irregular_real_{linea}"].values,
                    "efecto_numerador": f[f"efecto_num_{linea}"].values,
                    "efecto_denominador": f[f"efecto_den_{linea}"].values,
                    "ipc_empalmado": f["ipc_empalmado"].values,
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def normalize_esd_saldo(panel: pd.DataFrame, sistema: str = "AA000") -> pd.DataFrame:
    """Lleva el saldo de ESD a millones de pesos en toda la serie.

    El BCRA pasó de miles a millones en algún mes; se detecta como una caída de más de 100 veces
    del saldo del sistema entre dos meses consecutivos y se divide por 1.000 todo lo anterior.
    """
    p = panel.copy()
    s = p[p["entidad"] == sistema].set_index("fecha")["esd_consumo_saldo"].sort_index()
    salto = s[(s / s.shift(1)) < 0.01]
    if not salto.empty:
        corte = salto.index[0]
        p.loc[p["fecha"] < corte, "esd_consumo_saldo"] /= 1000
    return p


def irregular_consumo(panel: pd.DataFrame) -> pd.Series:
    """Irregularidad de la cartera de consumo o vivienda (%): situación 3 + 4 + 5 del ESD."""
    return panel[_SIT_IRREGULAR].sum(axis=1, min_count=len(_SIT_IRREGULAR))


def consumo_por_grupo() -> pd.DataFrame:
    """Irregularidad de consumo por agrupamiento institucional (archivos AA del BCRA)."""
    grupos = settings()["descriptivo"]["grupos"]
    p = _processed("entidades_panel", dtype={"entidad": str}, parse_dates=["fecha"])
    p = p[p["entidad"].isin(grupos)]
    out = p.assign(grupo=p["entidad"].map(grupos), irregular_consumo=irregular_consumo(p))
    return out[["fecha", "grupo", "irregular_consumo"]].sort_values(["fecha", "grupo"])


def distribucion_entidades(cuantiles=(0.1, 0.25, 0.5, 0.75, 0.9)) -> pd.DataFrame:
    """Cuantiles de la irregularidad de consumo entre entidades (sin agregados), por mes."""
    p = _processed("entidades_panel", dtype={"entidad": str}, parse_dates=["fecha"])
    p = p[~p["entidad"].str.startswith("AA") & (p["esd_consumo_saldo"] > 0)]
    p = p.assign(irr=irregular_consumo(p)).dropna(subset=["irr"])
    q = p.groupby("fecha")["irr"].quantile(list(cuantiles)).unstack()
    q.columns = [f"p{int(c * 100)}" for c in q.columns]
    q["n_entidades"] = p.groupby("fecha").size()
    return q.reset_index()


def ajuste_por_castigos(irregular: pd.Series, cartera: pd.Series, castigos_stock: pd.Series, h: int = 12) -> pd.DataFrame:
    """Ratio de irregularidad oficial y ajustado por los créditos pasados a cuentas de orden.

    Los castigos sacan deuda impaga del balance: bajan el numerador y el denominador. El ajuste
    suma el flujo de castigos de los últimos h meses a ambos (flujos negativos, por bajas
    definitivas de la cuenta de orden, se toman como cero). Todo en la misma unidad monetaria.
    """
    flujo = (castigos_stock - castigos_stock.shift(h)).clip(lower=0)
    return pd.DataFrame(
        {
            "ratio_oficial": 100 * irregular / cartera,
            "castigos_flujo": flujo,
            "ratio_ajustado": 100 * (irregular + flujo) / (cartera + flujo),
        }
    )


def mora_ajustada_sector_privado() -> pd.DataFrame:
    """Total sector privado (no hay apertura de castigos por línea): oficial contra ajustado."""
    a = _processed("anexo_calidad_por_linea", parse_dates=["fecha"])
    a = a[(a["seccion"] == "1. Total Sector Privado")]
    ratio = a[(a["metrica"] == "Ratio de irregularidad") & (a["concepto"] == "Cartera irregular total")].set_index("fecha")["valor"]
    cartera = a[(a["metrica"] == "Saldo total de financiaciones") & (a["concepto"] == "Cartera total")].set_index("fecha")["valor"]
    irregular = ratio / 100 * cartera  # millones de $
    b = _processed("entidades_balance", dtype={"entidad": str}, parse_dates=["fecha"])
    b = b[~b["entidad"].str.startswith("AA")]
    castigos = b.groupby("fecha")["irrecuperables_cuentas_orden"].sum() / 1000  # miles -> millones de $
    df = ajuste_por_castigos(irregular, cartera, castigos.reindex(cartera.index))
    return df.reset_index().rename(columns={"index": "fecha"})


def resumen(fam: pd.DataFrame) -> dict:
    """Indicadores para el encabezado del sitio, todos calculados de los outputs."""
    tot = fam[fam["linea"] == "total"].set_index("fecha").sort_index()
    ult = tot["ratio"].last_valid_index()
    hace12 = ult - pd.DateOffset(months=12)
    lineas = fam[fam["fecha"] == ult].set_index("linea")["ratio"].round(2).to_dict()
    return {
        "ultimo_dato": str(ult.date()),
        "mora_familias": round(float(tot.loc[ult, "ratio"]), 2),
        "mora_familias_hace_12m": round(float(tot.loc[hace12, "ratio"]), 2),
        "efecto_numerador_12m": round(float(tot.loc[ult, "efecto_numerador"]), 2),
        "efecto_denominador_12m": round(float(tot.loc[ult, "efecto_denominador"]), 2),
        "serie_desde": str(tot["ratio"].first_valid_index().date()),
        "maximo_de_la_serie": round(float(tot["ratio"].max()), 2),
        "fecha_maximo": str(tot["ratio"].idxmax().date()),
        "mora_por_linea": lineas,
    }


def main() -> None:
    out = path("outputs") / "descriptivo"
    out.mkdir(parents=True, exist_ok=True)
    fam = familias_tidy()
    fam.to_csv(out / "familias_por_linea.csv", index=False, date_format="%Y-%m-%d")
    consumo_por_grupo().to_csv(out / "consumo_por_grupo.csv", index=False, date_format="%Y-%m-%d")
    distribucion_entidades().to_csv(out / "distribucion_entidades.csv", index=False, date_format="%Y-%m-%d")
    mora_ajustada_sector_privado().to_csv(out / "mora_ajustada_castigos.csv", index=False, date_format="%Y-%m-%d")
    with open(out / "resumen.json", "w", encoding="utf-8") as fh:
        json.dump(resumen(fam), fh, ensure_ascii=False, indent=2)
    print(f"descriptivo: {out}")


if __name__ == "__main__":
    main()
