"""Más allá de los bancos: fondos comunes, billeteras y proveedores no financieros de crédito.

`python -m mora.no_bancario` escribe outputs/no_bancario/.

1. Exposición al Estado ampliada. A los títulos públicos + pases en pesos de los bancos se les suma
   la deuda nacional en cartera de los fondos comunes de inversión (CAFCI). No se suma lo que los
   FCI tienen en plazos fijos y cauciones: es fondeo de bancos, y lo que los bancos compran con eso
   ya está en su balance (se contaría dos veces). Los fondos money market, donde las billeteras
   virtuales colocan los saldos de sus usuarios, tienen ~1% en títulos públicos: la exposición de
   las billeteras al Estado es, sobre todo, indirecta, vía bancos. No hay datos públicos de la
   tenencia directa de inversores minoristas por medio de brokers ni de la cartera propia de las
   fintech.
2. Crédito y mora de las familias integrados. Al crédito bancario a familias se le suma el de los
   proveedores no financieros (PNFC: fintech, billeteras, emisoras de tarjetas no bancarias,
   mutuales, etc.), con la irregularidad de los informes semestrales del BCRA. La mora integrada
   pondera la de cada sector por su saldo. Sólo en las fechas de esos informes.
"""

from __future__ import annotations

import json

import pandas as pd

from mora.ajuste import pbi_anual_mensual, profundidad
from mora.config import path


def exposicion_estado() -> pd.DataFrame:
    """Exposición al Estado en pesos (% del PBI): bancos, FCI y total. Sólo meses con PBI."""
    prof = profundidad()
    fci = pd.read_csv(path("processed") / "cafci_carteras.csv", index_col="fecha", parse_dates=True)
    pbi = pbi_anual_mensual()["pbi_anual"]
    df = pd.DataFrame({
        "bancos_pbi": prof["exposicion_estado_mn_pbi"],
        "fci_deuda_nacional_pbi": 100 * fci["industria_deuda_nacional"] / pbi,
        "fci_titulos_publicos_pbi": 100 * fci["industria_titulos_publicos"] / pbi,
        "fci_money_market_titulos_pct": 100 * fci["money_market_titulos_publicos"] / fci["money_market_patrimonio"],
        "fci_money_market_plazo_pct": 100 * fci["money_market_operaciones_plazo"] / fci["money_market_patrimonio"],
        "credito_privado_bancos_pbi": prof["credito_privado_mn_pbi"],
    }).dropna(subset=["bancos_pbi"])
    df["total_pbi"] = df["bancos_pbi"] + df["fci_deuda_nacional_pbi"]
    return df


def credito_integrado() -> pd.DataFrame:
    """Crédito y mora de familias, bancos + PNFC, en las fechas de los informes del BCRA."""
    pnfc = pd.read_csv(path("processed") / "pnfc_informes.csv", index_col="fecha", parse_dates=True)
    prof = profundidad()
    fam = pd.read_csv(path("processed") / "familias_por_linea.csv", index_col=0, parse_dates=True)
    out = pd.DataFrame({
        "credito_bancos": prof["credito_familias"].reindex(pnfc.index) / 1e6,  # billones de pesos
        "mora_bancos_pct": fam["ratio_cartera_irregular_total"].reindex(pnfc.index),
        "credito_pnfc": pnfc["saldo_billones"],
        "mora_pnfc_pct": pnfc["irregularidad_pct"],
        "pbi_anual": pbi_anual_mensual()["pbi_anual"].reindex(pnfc.index) / 1e6,
    })
    out["participacion_pnfc_pct"] = 100 * out["credito_pnfc"] / (out["credito_bancos"] + out["credito_pnfc"])
    irregular = out["credito_bancos"] * out["mora_bancos_pct"] + out["credito_pnfc"] * out["mora_pnfc_pct"]
    out["mora_integrada_pct"] = irregular / (out["credito_bancos"] + out["credito_pnfc"])
    out["diferencia_pp"] = out["mora_integrada_pct"] - out["mora_bancos_pct"]
    out["credito_bancos_pbi"] = 100 * out["credito_bancos"] / out["pbi_anual"]
    out["credito_pnfc_pbi"] = 100 * out["credito_pnfc"] / out["pbi_anual"]
    return out


def main() -> None:
    out = path("outputs") / "no_bancario"
    out.mkdir(parents=True, exist_ok=True)
    exp = exposicion_estado()
    exp.to_csv(out / "exposicion_estado_ampliada.csv", date_format="%Y-%m-%d")
    cred = credito_integrado()
    cred.to_csv(out / "credito_mora_integrados.csv", date_format="%Y-%m-%d")
    ult = exp.dropna(subset=["fci_deuda_nacional_pbi"]).index.max()
    fila = lambda df, t, cols: {c: round(float(df.loc[t, c]), 2) for c in cols}  # noqa: E731
    cols_exp = ["bancos_pbi", "fci_deuda_nacional_pbi", "fci_titulos_publicos_pbi", "total_pbi",
                "fci_money_market_titulos_pct", "fci_money_market_plazo_pct", "credito_privado_bancos_pbi"]
    resumen = {
        "exposicion": {"ultimo": str(ult.date()), **fila(exp, ult, cols_exp),
                       "maximo_fci_deuda_nacional_pbi": round(float(exp["fci_deuda_nacional_pbi"].max()), 2),
                       "fecha_maximo_fci": str(exp["fci_deuda_nacional_pbi"].idxmax().date())},
        "credito_integrado": {str(t.date()): fila(cred, t, cred.columns) for t in cred.index},
    }
    with open(out / "resumen_no_bancario.json", "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, ensure_ascii=False, indent=2)
    print(f"no bancario: {out}")


if __name__ == "__main__":
    main()
