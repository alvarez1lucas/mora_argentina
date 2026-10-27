"""Ventana del ajuste (nov-2023 → último dato). `python -m mora.ajuste` escribe outputs/ajuste/.

1. Profundidad del crédito: crédito al sector privado (familias, empresas) vs exposición de los
   bancos al sector público y al BCRA, en % del PBI.
2. Cadena causal eslabón por eslabón, mes a mes: ancla cambiaria → esterilización → tasas →
   liquidez y crédito → ingreso → mora.
3. Baja reciente de la mora: cuánto se explica por castigos (créditos pasados a cuentas de orden)
   y cuánto por el resto (curas, refinanciaciones y nuevos atrasos, que con datos públicos no se
   pueden separar).
4. Empresas: mora y crédito.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from mora.config import path, settings
from mora.deflactores import build as build_precios
from mora.features import cft_aproximado, futuro_cercano, tasa_sintetica_usd


def _csv(name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(path("processed") / f"{name}.csv", **kw)


def pbi_anual_mensual() -> pd.DataFrame:
    """PBI nominal anual (promedio de los últimos 4 trimestres a tasa anual), asignado a cada mes.

    Después del último trimestre nominal se extiende con el PBI real y el IPC (marcado como estimado).
    """
    t = _csv("macro_trimestral", index_col=0, parse_dates=True)
    nominal = t["pbi_nominal"].dropna()
    ultimo = nominal.index.max()
    ipc_q = build_precios()["publico"].resample("QS").mean()
    extra = t.loc[t.index > ultimo, "pbi_real"].dropna()
    for q in extra.index:
        prev = q - pd.DateOffset(months=3)
        nominal.loc[q] = nominal.loc[prev] * (t.loc[q, "pbi_real"] / t.loc[prev, "pbi_real"]) * (ipc_q.loc[q] / ipc_q.loc[prev])
    anual = nominal.sort_index().rolling(4).mean()
    meses = pd.date_range(anual.index.min(), anual.index.max() + pd.DateOffset(months=2), freq="MS")
    out = pd.DataFrame({"pbi_anual": anual.reindex(meses, method="ffill")})
    out["pbi_estimado"] = out.index > ultimo + pd.DateOffset(months=2)
    return out


def profundidad() -> pd.DataFrame:
    """Stocks en % del PBI anual. Balance en moneda nacional (anexo) y saldos por sector (todas las monedas)."""
    b = _csv("anexo_balance_por_grupo", parse_dates=["fecha"])
    b = b[b["seccion"] == "Sistema financiero"].pivot_table(index="fecha", columns="concepto", values="valor")
    lin = _csv("anexo_calidad_por_linea", parse_dates=["fecha"])
    saldo = lin[(lin["metrica"] == "Saldo total de financiaciones")
                & (lin["concepto"] == "Cartera total")].pivot_table(index="fecha", columns="seccion", values="valor")
    pbi = pbi_anual_mensual()
    df = pd.DataFrame({
        "credito_privado_mn": b["Sector privado"],
        "titulos_publicos_mn": b["Títulos públicos"],
        "otros_creditos_intermediacion_mn": b["Otros créditos por intermediación financiera"],
        "credito_familias": saldo.get("2. Familias - Total"),
        "credito_empresas": saldo.get("3. Empresas - Total"),
    }).join(pbi, how="inner")
    for c in ("credito_privado_mn", "titulos_publicos_mn", "otros_creditos_intermediacion_mn", "credito_familias", "credito_empresas"):
        df[f"{c}_pbi"] = 100 * df[c] / df["pbi_anual"]
    df["exposicion_estado_mn_pbi"] = df["titulos_publicos_mn_pbi"] + df["otros_creditos_intermediacion_mn_pbi"]
    return df


def cadena(desde: str) -> pd.DataFrame:
    """Indicadores de cada eslabón de la cadena, mensuales, desde `desde`."""
    bcra = _csv("bcra_mensual", index_col=0, parse_dates=True)
    macro = _csv("macro_mensual", index_col=0, parse_dates=True)
    precios = build_precios()
    fam = _csv("familias_por_linea", index_col=0, parse_dates=True)
    lin = _csv("anexo_calidad_por_linea", parse_dates=["fecha"])
    emp = lin[(lin["seccion"] == "3. Empresas - Total") & (lin["metrica"] == "Ratio de irregularidad")
              & (lin["concepto"] == "Cartera irregular total")].set_index("fecha")["valor"]
    fut = _csv("a3_dolar_futuro", parse_dates=["fecha", "vencimiento"])
    cerca = futuro_cercano(fut).resample("MS").mean(numeric_only=True)
    oi = fut.groupby("fecha")["interes_abierto"].sum().resample("MS").last() / 1000  # contratos de USD 1.000 -> millones
    absor = profundidad()
    prof_cols = ["credito_privado_mn_pbi", "exposicion_estado_mn_pbi", "credito_familias_pbi", "credito_empresas_pbi"]
    ipc = precios["publico"]
    r = lambda s: s / ipc * ipc.loc[pd.Timestamp(desde)]  # pesos del mes de inicio

    techo = pd.Series(np.nan, index=bcra.index)
    t = None
    for d in bcra.loc["2025-04-01":].index:  # bandas: 1.400 + 1% mensual desde abr-25; por inflación t-2 desde ene-26
        if t is None:
            t = 1400.0
        elif d >= pd.Timestamp("2026-01-01"):
            t *= 1 + bcra["inflacion_mensual"].shift(2).loc[d] / 100
        else:
            t *= 1.01
        techo[d] = t

    salario = {k: macro["salarios_registrados"] / precios[k] for k in ("publico", "seleccionado", "mix")}
    out = pd.DataFrame({
        # ancla cambiaria
        "tc_mayorista": bcra["tipo_cambio_mayorista"],
        "tc_pct_techo_banda": 100 * bcra["tipo_cambio_mayorista"] / techo,
        "devaluacion_implicita_30d": cerca["tasa_implicita"],
        "interes_abierto_futuros_musd": oi,
        # esterilización
        "absorcion_titulos_pases_pct_activo": 100 * (absor["titulos_publicos_mn"] + absor["otros_creditos_intermediacion_mn"]) / _csv(
            "anexo_balance_por_grupo", parse_dates=["fecha"]).query("seccion == 'Sistema financiero' and concepto == 'Activo'").set_index("fecha")["valor"],
        "depositos_bancos_en_bcra_real": r(bcra["depositos_ef_en_bcra"]),
        "depositos_gobierno_en_bcra_real": r(bcra["depositos_gobierno_en_bcra"]),
        # tasas
        "tamar": bcra["tasa_tamar_privados"],
        "badlar": bcra["tasa_badlar_privados"],
        "pases_1d_max": bcra["tasa_pases_terceros_1d_max"],
        "tna_personales": bcra["tasa_prestamos_personales"],
        "cft_tea_personales": cft_aproximado(bcra["tasa_prestamos_personales"]),
        "spread_personales_tamar": bcra["tasa_prestamos_personales"] - bcra["tasa_tamar_privados"],
        "tasa_sintetica_usd_tamar": tasa_sintetica_usd(bcra["tasa_tamar_privados"], cerca["tasa_implicita"], cerca["dias"]),
        # liquidez y crédito
        "m2_real": r(bcra["m2"]),
        "credito_consumo_real": r(bcra["prestamos_personales"] + bcra["prestamos_tarjetas"]),
        **{c: absor[c] for c in prof_cols},
        # ingreso
        **{f"salario_real_{k}": 100 * v / v.loc[pd.Timestamp(desde)] for k, v in salario.items()},
        "empleo_registrado": macro["empleo_registrado"],
        # mora
        "mora_familias": fam["ratio_cartera_irregular_total"],
        "mora_personales": fam["ratio_personales"],
        "mora_tarjetas": fam["ratio_tarjetas_de_credito"],
        "mora_empresas": emp,
    })
    return out.loc[desde:]


def castigos_recientes(meses: int) -> pd.DataFrame:
    """Variación mensual del stock irregular (total sector privado) frente al flujo de castigos.

    Si el stock irregular baja y hubo castigos, la parte de la baja explicada por castigos es
    castigos / caída. Lo que no explican los castigos es el neto de curas, refinanciaciones y
    nuevos atrasos (no separables con datos públicos). En pesos reales del último mes.
    """
    lin = _csv("anexo_calidad_por_linea", parse_dates=["fecha"])
    tot = lin[lin["seccion"] == "1. Total Sector Privado"]
    ratio = tot[(tot["metrica"] == "Ratio de irregularidad") & (tot["concepto"] == "Cartera irregular total")].set_index("fecha")["valor"]
    cartera = tot[(tot["metrica"] == "Saldo total de financiaciones") & (tot["concepto"] == "Cartera total")].set_index("fecha")["valor"]
    fam = lin[lin["seccion"] == "2. Familias - Total"]
    ratio_f = fam[(fam["metrica"] == "Ratio de irregularidad") & (fam["concepto"] == "Cartera irregular total")].set_index("fecha")["valor"]
    cartera_f = fam[(fam["metrica"] == "Saldo total de financiaciones") & (fam["concepto"] == "Cartera total")].set_index("fecha")["valor"]
    bal = _csv("entidades_balance", dtype={"entidad": str}, parse_dates=["fecha"])
    castigos = bal[~bal["entidad"].str.startswith("AA")].groupby("fecha")["irrecuperables_cuentas_orden"].sum() / 1000  # millones
    ipc = build_precios()["publico"]
    df = pd.DataFrame({"irregular_total": ratio / 100 * cartera, "irregular_familias": ratio_f / 100 * cartera_f,
                       "castigos_stock": castigos}).dropna()
    ult = df.index.max()
    real = df.div(ipc.reindex(df.index), axis=0) * ipc.loc[ult]
    out = pd.DataFrame({
        "mora_total_pct": ratio.reindex(real.index), "mora_familias_pct": ratio_f.reindex(real.index),
        "var_irregular_total_real": real["irregular_total"].diff(),
        "var_irregular_familias_real": real["irregular_familias"].diff(),
        "castigos_flujo_real": real["castigos_stock"].diff().clip(lower=0),
    })
    # parte de los castigos atribuible a familias: proporcional a su peso en el stock irregular (supuesto)
    peso_fam = (df["irregular_familias"] / df["irregular_total"]).reindex(out.index)
    out["castigos_familias_estimado_real"] = out["castigos_flujo_real"] * peso_fam
    out["irregular_familias_sin_castigos_real"] = out["var_irregular_familias_real"] + out["castigos_familias_estimado_real"]
    return out.tail(meses)


def main() -> None:
    cfg = settings()["ajuste"]
    out = path("outputs") / "ajuste"
    out.mkdir(parents=True, exist_ok=True)
    prof = profundidad()
    prof.to_csv(out / "profundidad_credito_pbi.csv", date_format="%Y-%m-%d")
    cad = cadena(cfg["desde"])
    cad.to_csv(out / "cadena_mensual.csv", date_format="%Y-%m-%d")
    cast = castigos_recientes(cfg["meses_castigos"])
    cast.to_csv(out / "castigos_recientes.csv", date_format="%Y-%m-%d")

    def val(s: pd.Series, f: str):
        s = s.dropna()
        return None if s.empty else round(float(s.loc[:f].iloc[-1]), 2)

    d0 = cfg["desde"]
    resumen = {
        "ventana": [d0, str(cad.index.max().date())],
        "credito_privado_pbi": {"inicio": val(prof["credito_privado_mn_pbi"], d0), "ultimo": val(prof["credito_privado_mn_pbi"], "2100-01-01")},
        "exposicion_estado_pbi": {"inicio": val(prof["exposicion_estado_mn_pbi"], d0), "ultimo": val(prof["exposicion_estado_mn_pbi"], "2100-01-01")},
        "credito_familias_pbi": {"inicio": val(prof["credito_familias_pbi"], d0), "ultimo": val(prof["credito_familias_pbi"], "2100-01-01")},
        "credito_empresas_pbi": {"inicio": val(prof["credito_empresas_pbi"], d0), "ultimo": val(prof["credito_empresas_pbi"], "2100-01-01")},
        "mora_familias": {"inicio": val(cad["mora_familias"], d0), "maximo": round(float(cad["mora_familias"].max()), 2),
                          "fecha_maximo": str(cad["mora_familias"].idxmax().date()), "ultimo": val(cad["mora_familias"], "2100-01-01")},
        "mora_empresas": {"inicio": val(cad["mora_empresas"], d0), "ultimo": val(cad["mora_empresas"], "2100-01-01")},
        "castigos_ultimos_meses_real_millones": round(float(cast["castigos_flujo_real"].sum()), 0),
        "pbi_extrapolado_desde": str(prof.index[prof["pbi_estimado"]].min().date()) if prof["pbi_estimado"].any() else None,
    }
    with open(out / "resumen_ajuste.json", "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, ensure_ascii=False, indent=2)
    print(f"ajuste: {out}")


if __name__ == "__main__":
    main()
