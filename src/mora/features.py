"""Construcción de variables de análisis a partir de data/processed.

- Deflactor: IPC INDEC (base dic-2016) y, hacia atrás, encadenado con la inflación mensual
  de la API del BCRA. El tramo empalmado (antes de 2016-12) se marca y se usa sólo como
  descriptivo: la API no documenta la fuente de esa serie antes de 2017.
- Descomposición exacta del cambio del ratio de irregularidad en efecto numerador
  (cambio del saldo irregular) y efecto denominador (cambio del saldo total).
"""

from __future__ import annotations

import pandas as pd

from mora.config import path, settings


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(path("processed") / f"{name}.csv", index_col=0, parse_dates=True)


def price_index(ipc_indec: pd.Series, inflacion_mensual: pd.Series) -> pd.DataFrame:
    """Índice de precios (base: primer dato de INDEC = valor INDEC) con flag de empalme."""
    ipc = ipc_indec.dropna()
    base_date = ipc.index.min()
    back = inflacion_mensual[inflacion_mensual.index <= base_date].sort_index()
    # P_{t-1} = P_t / (1 + pi_t): se encadena hacia atrás desde la base
    factors = (1 + back / 100).iloc[::-1].cumprod().iloc[::-1]
    back_level = ipc.loc[base_date] / factors.shift(-1).fillna(1.0)
    back_level = back_level[back_level.index < base_date]
    level = pd.concat([back_level, ipc]).sort_index()
    return pd.DataFrame({"ipc": level, "ipc_empalmado": level.index < base_date})


def decompose_ratio_change(numerador: pd.Series, denominador: pd.Series, h: int = 12) -> pd.DataFrame:
    """Descomposición exacta de R_t - R_{t-h}, con R = 100 * N / D (en puntos porcentuales).

    R_t - R_{t-h} = 100 * (N_t - N_{t-h}) / D_t            (efecto numerador)
                  + 100 * N_{t-h} * (1/D_t - 1/D_{t-h})     (efecto denominador)

    El ratio no depende de la unidad, pero la partición sí: con N y D en pesos corrientes la
    inflación infla los dos efectos. Por eso se aplica sobre saldos reales; así el efecto
    denominador mide cuánto cambió el ratio sólo porque creció o cayó la cartera real.
    """
    n, d = numerador, denominador
    efecto_num = 100 * (n - n.shift(h)) / d
    efecto_den = 100 * n.shift(h) * (1 / d - 1 / d.shift(h))
    ratio = 100 * n / d
    return pd.DataFrame(
        {
            "ratio": ratio,
            "cambio_ratio": ratio - ratio.shift(h),
            "efecto_numerador": efecto_num,
            "efecto_denominador": efecto_den,
        }
    )


def tasas_reales(tna: pd.Series, inflacion_mensual: pd.Series, h: int = 12) -> pd.DataFrame:
    """Tasa real anual de un préstamo originado en t a tasa fija (TNA en %, capitalización mensual).

    - `tea`: tasa efectiva anual.
    - `real_ex_ante_ingenua`: contra la inflación de los h meses previos (expectativa adaptativa).
    - `real_ex_post`: contra la inflación realizada en los h meses siguientes (lo que terminó pagando
      el deudor en términos reales). Queda vacía para las cohortes cuyos h meses todavía no pasaron.
    """
    tea = (1 + tna / 100 / 12) ** 12 - 1
    factor = 1 + inflacion_mensual / 100
    infl_previa = factor.rolling(h).apply(lambda x: x.prod(), raw=True) - 1
    infl_siguiente = infl_previa.shift(-h)
    return pd.DataFrame(
        {
            "tea": 100 * tea,
            "inflacion_previa": 100 * infl_previa,
            "inflacion_siguiente": 100 * infl_siguiente,
            "real_ex_ante_ingenua": 100 * ((1 + tea) / (1 + infl_previa) - 1),
            "real_ex_post": 100 * ((1 + tea) / (1 + infl_siguiente) - 1),
        }
    )


def inflacion_esperada(deflactor: str, idx: pd.DatetimeIndex) -> pd.Series:
    """Inflación esperada a 12 meses (fracción) para pasar tasas a reales.

    Con `satelite.expectativa_inflacion` = "previa": la inflación de los últimos w meses anualizada,
    con la medición de precios `deflactor`. Con 12 meses la medida falla en las desinflaciones bruscas
    (en 2024 daba tasas reales de -40% con tasas muy positivas). Con "rem": la mediana del REM
    del BCRA, que es sobre el IPC oficial, cualquiera sea el deflactor.
    """
    cfg = settings()["satelite"]
    if cfg.get("expectativa_inflacion", "previa") == "rem":
        return (load("bcra_mensual")["inflacion_esperada_rem"] / 100).reindex(idx)
    ipc = precios(deflactor)["ipc"]
    w = cfg["ventana_expectativa_inflacion"]
    return ((ipc / ipc.shift(w)) ** (12 / w) - 1).reindex(idx)


def cft_aproximado(tna: pd.Series, iva: float = 0.21) -> pd.Series:
    """CFT efectivo anual (%) aproximado: tasa mensual de la TNA más IVA sobre intereses.

    Es una cota inferior: no incluye seguros de vida ni gastos de otorgamiento. La serie de tasas
    del BCRA es una TNA sin IVA; en la foto del régimen de transparencia (2026) la mediana de
    CFT mensual / TEM es 1,21, exactamente el IVA.
    """
    tem_con_iva = tna / 100 / 12 * (1 + iva)
    return 100 * ((1 + tem_con_iva) ** 12 - 1)


def sorpresa_carga_cuota(inflacion_mensual: pd.Series, salario_nominal: pd.Series, h: int = 12) -> pd.Series:
    """Cuánto más pesa una cuota fija sobre el salario a h meses de lo que el deudor podía esperar.

    Expectativa ingenua: el salario nominal sube como la inflación de los h meses previos.
    >1 significa que la cuota quedó más pesada que lo esperado (la desinflación no la licuó).
    Con expectativas adaptativas sobreestima la sorpresa en las desinflaciones bruscas (2024);
    la versión con expectativas del REM queda para la Fase 5.
    """
    factor = 1 + inflacion_mensual / 100
    esperado = factor.rolling(h).apply(lambda x: x.prod(), raw=True)
    realizado = salario_nominal.shift(-h) / salario_nominal
    return esperado / realizado


def futuro_cercano(futuros: pd.DataFrame, plazo_objetivo: int = 30, plazo_minimo: int = 7) -> pd.DataFrame:
    """Por día, el contrato de dólar futuro con plazo más cercano a `plazo_objetivo` días.

    Se descartan los contratos a menos de `plazo_minimo` días (la tasa implícita anualizada de
    un contrato por vencer es muy ruidosa).
    """
    f = futuros.copy()
    f["dias"] = (f["vencimiento"] - f["fecha"]).dt.days
    f = f[f["dias"] >= plazo_minimo]
    f["_dist"] = (f["dias"] - plazo_objetivo).abs()
    return f.sort_values(["fecha", "_dist"]).groupby("fecha").first().drop(columns="_dist")


def tasa_sintetica_usd(tasa_pesos: pd.Series, devaluacion_implicita: pd.Series, dias: pd.Series) -> pd.Series:
    """Rendimiento en dólares (TNA %) de colocar pesos a `tasa_pesos` y cubrirse con el futuro.

    Ambas tasas son TNA en %, al plazo `dias`. Una tasa sintética alta y positiva indica que el
    futuro estaba "barato" respecto de la tasa en pesos: cobertura cambiaria subsidiada.
    """
    bruto = (1 + tasa_pesos / 100 * dias / 365) / (1 + devaluacion_implicita / 100 * dias / 365)
    return (bruto - 1) * 365 / dias * 100


def precios(deflactor: str = "publico") -> pd.DataFrame:
    """Índice de precios (`ipc`) y marca de empalme (`ipc_empalmado`) según la medición elegida."""
    from mora.deflactores import build

    d = build()
    # mix y seleccionado comparten el tramo empalmado (antes del IPCBA)
    marca = "empalme_publico" if deflactor == "publico" else "empalme_seleccionado"
    return pd.DataFrame({"ipc": d[deflactor], "ipc_empalmado": d[marca]})


def familias(h: int = 12, deflactor: str = "publico") -> pd.DataFrame:
    """Dataset de familias por línea: ratios, saldos, saldo irregular nominal y real, y descomposición."""
    fam = load("familias_por_linea")
    p = precios(deflactor).reindex(fam.index)
    out = fam.copy()
    out[["ipc", "ipc_empalmado"]] = p
    # El anexo llama "Cartera irregular total" al ratio y "Cartera total" al saldo: ambos son la línea "total"
    out = out.rename(columns={"ratio_cartera_irregular_total": "ratio_total", "saldo_cartera_total": "saldo_total"})
    lineas = [c.removeprefix("ratio_") for c in out.columns if c.startswith("ratio_")]
    for linea in lineas:
        saldo_col = f"saldo_{linea}"
        irregular = out[f"ratio_{linea}"] / 100 * out[saldo_col]
        out[f"irregular_{linea}"] = irregular
        out[f"irregular_real_{linea}"] = irregular / out["ipc"] * 100
        out[f"saldo_real_{linea}"] = out[saldo_col] / out["ipc"] * 100
        dec = decompose_ratio_change(out[f"irregular_real_{linea}"], out[f"saldo_real_{linea}"], h=h)
        out[f"efecto_num_{linea}"] = dec["efecto_numerador"]
        out[f"efecto_den_{linea}"] = dec["efecto_denominador"]
    return out
