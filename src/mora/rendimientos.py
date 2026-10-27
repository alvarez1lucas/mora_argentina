"""Rendimientos implícitos del balance de los bancos: cuánto rinde prestarle al Estado y cuánto a las familias.

`python -m mora.rendimientos` escribe outputs/rendimientos/.

No hay una serie pública de rendimientos de Lecap/Boncap. En su lugar se usan las cuentas de
resultados de `bal_hist` (Información de Entidades Financieras): lo que el sistema efectivamente
ganó con títulos públicos y pases con el BCRA, sobre el stock de esos activos. Es el costo de
oportunidad de prestarle a una familia: si el Estado paga X sin riesgo de crédito, ningún banco
presta a familias por debajo de X más la pérdida esperada.

Tratamiento contable:
- Las cuentas de resultados vienen acumuladas en el ejercicio (se reinician en enero) y los ingresos
  con signo negativo. El flujo del mes es la diferencia con el acumulado del mes anterior.
- Desde enero de 2020 (NIC 29, Com. A 6651) los balances se presentan reexpresados: el acumulado
  del mes anterior está en moneda de ese mes y se lleva a moneda del mes con el IPC oficial (el que
  usan los bancos). Sin esta corrección los rendimientos de dic-23 dan miles por ciento.
- Rendimiento de títulos = intereses + ajuste CER + resultado por medición (retorno total). Incluye
  ganancias de valuación, por eso la serie mensual es ruidosa; los modelos usan el promedio de 3 meses.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from mora.config import path, settings
from mora.features import precios

# Componentes: (cuenta de resultado, stocks que la generan)
COMPONENTES = {
    "estado": (["res_titulos_publicos_mn", "res_pases_bcra_mn"], ["titulos_publicos_mn", "pases_activos_mn"]),
    "titulos": (["res_titulos_publicos_mn"], ["titulos_publicos_mn"]),
    "pases_bcra": (["res_pases_bcra_mn"], ["pases_activos_mn"]),
    "personales": (["res_prestamos_personales"], ["prestamos_personales", "prestamos_personales_monto_reducido"]),
    "tarjetas": (["res_tarjetas"], ["prestamos_tarjetas"]),
    "depositos": (["costo_depositos_mn"], ["depositos_mn"]),
}


def factor_reexpresion(ipc: pd.Series, desde: str) -> pd.Series:
    """Factor que lleva valores del mes anterior a moneda del mes (1 antes de `desde`)."""
    f = (ipc / ipc.shift(1)).fillna(1.0)
    f[f.index < pd.Timestamp(desde)] = 1.0
    return f


def flujo_mensual(acumulado: pd.Series, factor: pd.Series) -> pd.Series:
    """Resultado del mes a partir del acumulado del ejercicio (que se reinicia en enero)."""
    idx = pd.date_range(acumulado.index.min(), acumulado.index.max(), freq="MS")
    a = acumulado.reindex(idx)
    out = a - a.shift(1) * factor.reindex(idx)
    enero = idx.month == 1
    out[enero] = a[enero]
    return out


def tasa_efectiva_anual(flujo: pd.Series, stock: pd.Series, factor: pd.Series) -> pd.Series:
    """TEA (%) = (1 + flujo / stock promedio del mes)^12 − 1; el stock previo llevado a moneda del mes."""
    s = stock.reindex(flujo.index)
    promedio = (s + s.shift(1) * factor.reindex(flujo.index)) / 2
    return 100 * ((1 + flujo / promedio) ** 12 - 1)


def sistema() -> pd.DataFrame:
    """Rendimientos implícitos del sistema (TEA, %) por componente, con flujos y stocks en millones."""
    cfg = settings()["rendimientos"]
    bal = pd.read_csv(path("processed") / "entidades_balance.csv", parse_dates=["fecha"], dtype={"entidad": str})
    tot = bal.drop(columns="entidad").groupby("fecha").sum(min_count=1).loc[cfg["desde"]:]
    factor = factor_reexpresion(precios("publico")["ipc"], cfg["reexpresion_desde"])
    out = {}
    for nombre, (resultados, stocks) in COMPONENTES.items():
        # ingresos con signo negativo; el costo de los depósitos con signo positivo y el stock pasivo negativo
        acum = tot[resultados].sum(axis=1, min_count=1).abs()
        stock = tot[stocks].sum(axis=1, min_count=1).abs()
        flujo = flujo_mensual(acum, factor)
        out[f"tea_{nombre}"] = tasa_efectiva_anual(flujo, stock, factor)
        out[f"stock_{nombre}_millones"] = stock.reindex(flujo.index) / 1000
    df = pd.DataFrame(out)
    df["tea_estado_3m"] = df["tea_estado"].rolling(3).mean()
    return df


def comparacion(df: pd.DataFrame) -> pd.DataFrame:
    """Rendimiento del Estado contra la tasa de los préstamos nuevos (BCRA) y la BADLAR, en TEA."""
    bcra = pd.read_csv(path("processed") / "bcra_mensual.csv", index_col=0, parse_dates=True)

    def tea_desde_tna(tna: pd.Series) -> pd.Series:
        return 100 * ((1 + tna / 100 / 12) ** 12 - 1)

    out = df[["tea_estado", "tea_estado_3m", "tea_personales", "tea_tarjetas", "tea_depositos"]].copy()
    out["tea_personales_nuevos"] = tea_desde_tna(bcra["tasa_prestamos_personales"]).reindex(out.index)
    out["tea_badlar"] = tea_desde_tna(bcra["tasa_badlar_privados"]).reindex(out.index)
    # Prima que cobra el banco a una familia por encima de lo que le paga el Estado
    out["prima_personales_sobre_estado_pp"] = out["tea_personales_nuevos"] - out["tea_estado_3m"]
    out["estado_sobre_badlar_pp"] = out["tea_estado_3m"] - out["tea_badlar"]
    return out


def resumen(comp: pd.DataFrame, desde: str) -> dict:
    v = comp.loc[desde:].dropna(subset=["tea_estado_3m"])
    ult = v.index.max()

    def fila(t):
        return {k: round(float(v.loc[t, k]), 1) for k in
                ["tea_estado_3m", "tea_personales_nuevos", "tea_badlar", "prima_personales_sobre_estado_pp"]}

    anual = v.groupby(v.index.year)[["tea_estado_3m", "tea_personales_nuevos", "tea_badlar",
                                     "prima_personales_sobre_estado_pp"]].mean().round(1)
    return {
        "inicio": {"fecha": str(v.index.min().date()), **fila(v.index.min())},
        "ultimo": {"fecha": str(ult.date()), **fila(ult)},
        "promedios_anuales": {str(a): r.to_dict() for a, r in anual.iterrows()},
        "meses_estado_rinde_mas_que_badlar_pct": round(100 * float((v["estado_sobre_badlar_pp"] > 0).mean()), 1),
    }


def main() -> None:
    out = path("outputs") / "rendimientos"
    out.mkdir(parents=True, exist_ok=True)
    df = sistema()
    comp = comparacion(df)
    df.to_csv(out / "rendimientos_sistema.csv", index_label="fecha")
    comp.to_csv(out / "estado_vs_familias.csv", index_label="fecha")
    with open(out / "resumen_rendimientos.json", "w", encoding="utf-8") as fh:
        json.dump(resumen(comp, settings()["ajuste"]["desde"]), fh, ensure_ascii=False, indent=2)
    print(f"rendimientos: {out}")


if __name__ == "__main__":
    main()
