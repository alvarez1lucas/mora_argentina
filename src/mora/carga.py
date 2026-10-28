"""Carga financiera de las familias: cuánto del ingreso se va en la cuota.

`python -m mora.carga` escribe outputs/carga/.

Medida agregada (no por hogar endeudado): cuota de los préstamos personales sobre la masa salarial
registrada.
- Cuota mensual = stock de préstamos personales × (TNA/12 + 1/plazo): intereses más una amortización
  lineal. El plazo promedio no es público: se usa un valor central y una sensibilidad.
- Masa salarial mensual = remuneración promedio de los asalariados privados (SIPA, sin el aguinaldo
  de junio y diciembre y con el aguinaldo prorrateado) × trabajadores registrados (SIPA). Es una
  aproximación: aplica la remuneración privada a todo el empleo registrado.
- Tarjetas: se informa el saldo en meses de masa salarial, no una cuota, porque no hay datos de qué
  parte se financia y qué parte se paga completa a fin de mes.

Como divide por todos los trabajadores registrados (con y sin deuda), no sirve para verificar la
cifra de "~25% del salario" que circula, que se refiere a los hogares endeudados: esa necesita
datos por deudor. Sirve para ver cómo se movió la carga en el tiempo.
"""

from __future__ import annotations

import json

import pandas as pd

from mora.config import path, settings
from mora.features import load


def carga() -> pd.DataFrame:
    cfg = settings()["carga"]
    bcra, macro = load("bcra_mensual"), load("macro_mensual")
    rem = macro["remuneracion_privada"].copy()
    # Junio y diciembre incluyen medio aguinaldo: se saca y se reparte en los 12 meses (×13/12).
    # Un promedio de 12 meses haría lo mismo, pero con inflación alta se atrasa varios meses.
    rem[rem.index.month.isin([6, 12])] /= 1.5
    rem = rem * 13 / 12
    masa = rem * macro["empleo_registrado"] * 1000 / 1e6  # millones de pesos; empleo en miles
    out = pd.DataFrame({"masa_salarial": masa, "prestamos_personales": bcra["prestamos_personales"],
                        "prestamos_tarjetas": bcra["prestamos_tarjetas"],
                        "tna_personales": bcra["tasa_prestamos_personales"]}).dropna()
    for plazo in cfg["plazos_meses"]:
        cuota = out["prestamos_personales"] * (out["tna_personales"] / 100 / 12 + 1 / plazo)
        out[f"cuota_personales_pct_masa_{plazo}m"] = 100 * cuota / out["masa_salarial"]
    out["intereses_personales_pct_masa"] = 100 * out["prestamos_personales"] * out["tna_personales"] / 100 / 12 / out["masa_salarial"]
    out["tarjetas_meses_de_masa"] = out["prestamos_tarjetas"] / out["masa_salarial"]
    out["personales_meses_de_masa"] = out["prestamos_personales"] / out["masa_salarial"]
    return out.loc[cfg["desde"]:]


def main() -> None:
    cfg = settings()["carga"]
    out = path("outputs") / "carga"
    out.mkdir(parents=True, exist_ok=True)
    c = carga()
    c.to_csv(out / "carga_financiera.csv", date_format="%Y-%m-%d")
    col = f"cuota_personales_pct_masa_{cfg['plazo_central_meses']}m"
    ult = c.index.max()
    fila = lambda t: {k: round(float(c.loc[t, k]), 2) for k in c.columns if k.endswith(("pct_masa", "m", "de_masa"))}  # noqa: E731
    resumen = {
        "plazo_central_meses": cfg["plazo_central_meses"], "ultimo": str(ult.date()), "valores_ultimo": fila(ult),
        "promedio_2017_2023": round(float(c.loc["2017-01-01":"2023-12-01", col].mean()), 2),
        "nov23": fila(pd.Timestamp("2023-11-01")),
        "maximo": {"fecha": str(c[col].idxmax().date()), "valor": round(float(c[col].max()), 2)},
    }
    with open(out / "resumen_carga.json", "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, ensure_ascii=False, indent=2)
    print(f"carga: {out}")


if __name__ == "__main__":
    main()
