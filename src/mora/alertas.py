"""Alertas tempranas: ¿están volviendo a aparecer las señales que precedieron a las subas de mora?

`python -m mora.alertas` escribe outputs/alertas/.

El modelo de escenarios aprende relaciones promedio y no anticipó el quiebre de 2025
(outputs/seguimiento/). Esto es otra herramienta: el método de señales de Kaminsky y Reinhart
(1999), usado por bancos centrales para alertas de crisis.

- Episodio: en los 12 meses siguientes la mora de familias sube al menos `episodio_pp` puntos.
- Cada indicador tiene una dirección fijada por la teoría (alto o bajo es malo) y "da señal" cuando
  cruza un umbral. El umbral es el percentil que minimiza el cociente ruido/señal:
      NSR = (falsas alarmas / meses sin episodio por delante) / (aciertos / meses con episodio por delante)
  exigiendo que capte al menos `cobertura_minima` de los meses previos a episodios. Un indicador con
  NSR >= 1 no le gana a tirar una moneda y pesa 0.
- Índice compuesto: promedio de las señales encendidas ponderado por 1/NSR (0 a 1), con cuatro
  grados de gravedad (`grados`). Para cada grado se informa con qué frecuencia vino un episodio
  después, en la historia usada para entrenar.
- Se excluye la ventana del alivio COVID (los saltos de la mora por reclasificación no son episodios).

Validación honesta: los umbrales se eligen con lo que se sabía a fines de 2023 (episodios etiquetados
hasta dic-22) y se mira qué decía el índice en 2024, antes de la suba de 2025. La versión vigente usa
toda la historia etiquetada (incluye 2024-25), así aprende del último episodio.
Limitación: en 2011-2026 hay pocos episodios (2018-19 y 2024-25); los umbrales son frágiles.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from mora.config import path, settings
from mora.features import load, precios
from mora.satelite import build_dataset

# indicador: (dirección mala, descripción)
INDICADORES = {
    "sit2": ("alto", "Atrasos de 31 a 90 días (situación 2), % de la cartera de consumo y vivienda"),
    "sit2_d3": ("alto", "Suba de la situación 2 en 3 meses (pp)"),
    "mora_d3": ("alto", "Suba de la mora en 3 meses (pp)"),
    "tasa_real": ("alto", "Tasa real del CFT de préstamos personales (%)"),
    "tasa_real_d12": ("alto", "Suba de la tasa real en 12 meses (pp)"),
    "credito_real_ia": ("alto", "Crecimiento real del crédito al consumo, interanual (%)"),
    "credito_real_ia_l12": ("alto", "Crecimiento real del crédito al consumo de hace 12 meses (efecto cosecha, %)"),
    "tasa_real_l6": ("alto", "Tasa real del CFT de hace 6 meses (%)"),
    "carga": ("alto", "Cuota de préstamos personales sobre la masa salarial (%)"),
    "carga_d12": ("alto", "Suba de la carga de la cuota en 12 meses (pp)"),
    "salario_real_ia": ("bajo", "Salario registrado real, interanual (%)"),
    "emae_ia": ("bajo", "Actividad (EMAE), interanual (%)"),
    "iva_real_ia": ("bajo", "Recaudación real de IVA DGI, interanual (%)"),
    "aportes_real_ia": ("bajo", "Recaudación real de aportes personales, interanual (%)"),
    "debitos_creditos_real_ia": ("bajo", "Recaudación real del impuesto a los débitos y créditos, interanual (%)"),
}


def situacion2() -> pd.DataFrame:
    """Situación 2 y cartera irregular de consumo y vivienda del sistema (panel por entidad, ponderado por saldo)."""
    cols = ["esd_consumo_saldo", "esd_consumo_sit2", "esd_consumo_sit3", "esd_consumo_sit4", "esd_consumo_sit5"]
    p = pd.read_csv(path("processed") / "entidades_panel.csv", usecols=["fecha", *cols], parse_dates=["fecha"]).dropna()
    p = p[(p["esd_consumo_saldo"] > 0) & (p[cols[1:]] <= 100).all(axis=1)]  # porcentajes válidos
    pond = lambda c: (p[c] * p["esd_consumo_saldo"]).groupby(p["fecha"]).sum() / p["esd_consumo_saldo"].groupby(p["fecha"]).sum()  # noqa: E731
    return pd.DataFrame({"sit2": pond("esd_consumo_sit2"),
                         "irregular": pond("esd_consumo_sit3") + pond("esd_consumo_sit4") + pond("esd_consumo_sit5")})


def indicadores() -> pd.DataFrame:
    """Panel mensual de indicadores (medición de precios pública) y mora de familias."""
    df = build_dataset(deflactor="publico")
    macro = load("macro_mensual")
    ipc = precios("publico")["ipc"]
    real_ia = lambda s: 100 * np.log(s / ipc.reindex(s.index)).diff(12)  # noqa: E731
    s2 = situacion2()
    carga = pd.read_csv(path("outputs") / "carga" / "carga_financiera.csv", index_col=0, parse_dates=True)
    c = f"cuota_personales_pct_masa_{settings()['carga']['plazo_central_meses']}m"
    out = pd.DataFrame({
        "mora": df["mora"],
        "sit2": s2["sit2"], "sit2_d3": s2["sit2"].diff(3),
        "mora_d3": df["mora"].diff(3),
        "tasa_real": df["tasa_real_cft"], "tasa_real_d12": df["tasa_real_cft"].diff(12),
        "credito_real_ia": df["credito_real_ia"],
        "credito_real_ia_l12": df["credito_real_ia"].shift(12), "tasa_real_l6": df["tasa_real_cft"].shift(6),
        "carga": carga[c], "carga_d12": carga[c].diff(12),
        "salario_real_ia": df["salario_real_ia"], "emae_ia": df["emae_ia"],
        "iva_real_ia": real_ia(macro["rec_iva_dgi"]), "aportes_real_ia": real_ia(macro["rec_aportes"]),
        "debitos_creditos_real_ia": real_ia(macro["rec_debitos_creditos"]),
    })
    return out.loc[settings()["alertas"]["desde"]:]


def completar_cola(panel: pd.DataFrame, meses: int) -> pd.DataFrame:
    """Extiende hasta `meses` el último dato de cada indicador (sólo al final: los datos se publican con distinto rezago)."""
    out = panel.copy()
    for c in out.columns:
        ultimo = out[c].last_valid_index()
        if ultimo is not None:
            cola = out.loc[ultimo:, c].ffill(limit=meses)
            out.loc[ultimo:, c] = cola
    return out


def episodios(mora: pd.Series, umbral_pp: float, horizonte: int) -> pd.Series:
    """1 si en los próximos `horizonte` meses la mora supera la actual en `umbral_pp` o más (NaN si no se sabe todavía)."""
    adelante = pd.concat([mora.shift(-k) for k in range(1, horizonte + 1)], axis=1)
    maximo = adelante.max(axis=1, skipna=False)
    out = (maximo - mora >= umbral_pp).astype(float)
    out[maximo.isna()] = np.nan
    return out


def excluir_covid(idx: pd.DatetimeIndex) -> np.ndarray:
    a, b = settings()["alertas"]["excluir"]
    return (idx >= a) & (idx <= b)


def umbral_optimo(x: pd.Series, y: pd.Series, direccion: str, cobertura_minima: float) -> dict:
    """Umbral que minimiza el cociente ruido/señal entre percentiles candidatos."""
    ok = x.notna() & y.notna()
    x, y = x[ok], y[ok].astype(bool)
    mejor = {"umbral": np.nan, "nsr": np.inf, "cobertura": 0.0, "prob_episodio_si_senal": np.nan, "n": int(ok.sum())}
    if y.sum() == 0 or (~y).sum() == 0:
        return mejor
    qs = np.arange(0.50, 0.96, 0.025) if direccion == "alto" else np.arange(0.05, 0.51, 0.025)
    for q in qs:
        u = float(x.quantile(q))
        s = x >= u if direccion == "alto" else x <= u
        a, b = int((s & y).sum()), int((s & ~y).sum())
        cobertura = a / int(y.sum())
        if cobertura < cobertura_minima or a == 0:
            continue
        nsr = (b / int((~y).sum())) / cobertura
        if nsr < mejor["nsr"]:
            mejor = {"umbral": u, "nsr": nsr, "cobertura": cobertura, "prob_episodio_si_senal": a / (a + b), "n": int(ok.sum())}
    return mejor


def calibrar(panel: pd.DataFrame, y: pd.Series, hasta: str | None) -> pd.DataFrame:
    cfg = settings()["alertas"]
    m = ~excluir_covid(panel.index) & y.notna()
    if hasta:
        m &= panel.index <= pd.Timestamp(hasta)
    filas = []
    for ind, (direccion, desc) in INDICADORES.items():
        u = umbral_optimo(panel.loc[m, ind], y[m], direccion, cfg["cobertura_minima"])
        # Con pocos episodios, cero falsas alarmas es más suerte que señal: el NSR tiene un piso
        peso = 1 / max(u["nsr"], cfg["nsr_minimo"]) if u["nsr"] < 1 else 0.0
        filas.append({"indicador": ind, "descripcion": desc, "direccion": direccion, **u, "peso": peso})
    return pd.DataFrame(filas).set_index("indicador")


def senales(panel: pd.DataFrame, cal: pd.DataFrame) -> pd.DataFrame:
    s = pd.DataFrame(index=panel.index)
    for ind, r in cal.iterrows():
        if r["peso"] <= 0:
            continue
        x = panel[ind]
        s[ind] = np.where(x.isna(), np.nan, (x >= r["umbral"]) if r["direccion"] == "alto" else (x <= r["umbral"]))
    return s


def indice(s: pd.DataFrame, cal: pd.DataFrame) -> pd.Series:
    """Promedio ponderado de las señales disponibles en cada mes (0 a 1)."""
    w = cal.loc[s.columns, "peso"]
    disponible = s.notna()
    return (s.fillna(0) * w).sum(axis=1) / (disponible * w).sum(axis=1).replace(0, np.nan)


def grado(x: float) -> str:
    for nombre, tope in settings()["alertas"]["grados"].items():
        if x < tope:
            return nombre
    return list(settings()["alertas"]["grados"])[-1]


def frecuencia_por_grado(ind: pd.Series, y: pd.Series) -> pd.DataFrame:
    m = ~excluir_covid(ind.index) & y.notna() & ind.notna()
    g = ind[m].map(grado)
    return pd.DataFrame({"meses": g.value_counts(), "prob_episodio": y[m].groupby(g).mean()}).reindex(list(settings()["alertas"]["grados"]))


def lectura_actual(panel: pd.DataFrame, cal: pd.DataFrame, meses_max: int) -> dict:
    """Último dato de cada indicador (hasta `meses_max` de antigüedad) y el índice con esos datos."""
    ultimo = panel.index.max()
    vals, fechas = {}, {}
    for ind in cal.index:
        x = panel[ind].dropna()
        if len(x) and (ultimo.to_period("M") - x.index.max().to_period("M")).n <= meses_max:
            vals[ind], fechas[ind] = float(x.iloc[-1]), str(x.index.max().date())
    fila = pd.DataFrame([vals], index=[ultimo]).reindex(columns=cal.index)
    s = senales(fila, cal)
    valor = float(indice(s, cal).iloc[0]) if s.shape[1] else float("nan")
    detalle = []
    for ind, r in cal.iterrows():
        detalle.append({"indicador": ind, "descripcion": r["descripcion"], "valor": vals.get(ind), "fecha": fechas.get(ind),
                        "umbral": None if np.isnan(r["umbral"]) else float(r["umbral"]), "direccion": r["direccion"],
                        "peso": float(r["peso"]), "senal": None if ind not in s.columns or pd.isna(s[ind].iloc[0]) else bool(s[ind].iloc[0])})
    return {"fecha": str(ultimo.date()), "indice": valor, "grado": grado(valor), "indicadores": detalle}


def evaluacion_fuera_de_muestra(serie: pd.DataFrame, desde: str, grados: list[str]) -> dict:
    """Meses posteriores al corte con episodio por delante conocido: aciertos y falsas alarmas (grado >= vigilancia)."""
    t = serie.loc[pd.Timestamp(desde) + pd.DateOffset(months=1):].dropna(subset=["episodio_adelante", "grado_validacion"])
    encendida = t["grado_validacion"].isin(grados[1:])
    ep = t["episodio_adelante"].astype(bool)
    return {"meses_evaluados": int(len(t)), "meses_con_episodio": int(ep.sum()),
            "aciertos_pct": float(100 * encendida[ep].mean()) if ep.any() else None,
            "falsas_alarmas_pct": float(100 * encendida[~ep].mean()) if (~ep).any() else None,
            "periodo": [str(t.index.min().date()), str(t.index.max().date())]}


def correlaciones_adelantadas(panel: pd.DataFrame, horizontes: list[int]) -> pd.DataFrame:
    """Correlación de cada indicador hoy con la variación de la mora en los h meses siguientes (sin la ventana COVID)."""
    m = ~excluir_covid(panel.index)
    filas = []
    for ind in INDICADORES:
        fila = {"indicador": ind}
        for h in horizontes:
            y = panel["mora"].shift(-h) - panel["mora"]
            fila[f"corr_h{h}"] = float(panel.loc[m, ind].corr(y[m]))
        filas.append(fila)
    return pd.DataFrame(filas).set_index("indicador")


def main() -> None:
    cfg = settings()["alertas"]
    out = path("outputs") / "alertas"
    out.mkdir(parents=True, exist_ok=True)
    panel = indicadores()
    y = episodios(panel["mora"], cfg["episodio_pp"], cfg["horizonte_meses"])
    y[excluir_covid(y.index)] = np.nan  # los saltos por reclasificación no son episodios

    # 1. Validación: umbrales con lo que se sabía a fines de 2023
    corte = pd.Timestamp(cfg["validacion_hasta"]) - pd.DateOffset(months=cfg["horizonte_meses"])
    cal_v = calibrar(panel, y, str(corte.date()))
    vista = completar_cola(panel.drop(columns="mora"), cfg["antiguedad_maxima_meses"])  # índice mensual con la misma regla que la lectura vigente
    ind_v = indice(senales(vista, cal_v), cal_v)
    # 2. Vigente: toda la historia etiquetada
    cal = calibrar(panel, y, None)
    ind = indice(senales(vista, cal), cal)

    serie = pd.DataFrame({"mora": panel["mora"], "episodio_adelante": y, "indice_vigente": ind,
                          "grado_vigente": ind.map(lambda v: grado(v) if pd.notna(v) else None),
                          "indice_validacion": ind_v, "grado_validacion": ind_v.map(lambda v: grado(v) if pd.notna(v) else None)})
    serie.to_csv(out / "indice_alertas.csv", date_format="%Y-%m-%d")
    cal.to_csv(out / "umbrales_vigentes.csv")
    correlaciones_adelantadas(panel, [3, 6, 12]).to_csv(out / "correlaciones_adelantadas.csv")
    cal_v.to_csv(out / "umbrales_validacion.csv")

    # primera alerta (grado >= 'alerta') en la validación después del corte, antes del episodio de 2025
    grados = list(cfg["grados"])
    fuera = serie.loc[pd.Timestamp(cfg["validacion_hasta"]) + pd.DateOffset(months=1) - pd.DateOffset(years=1):]
    altos = fuera[fuera["grado_validacion"].isin(grados[2:])]
    resumen = {
        "episodio_pp": cfg["episodio_pp"], "horizonte_meses": cfg["horizonte_meses"],
        "meses_con_episodio_adelante": int(y[~excluir_covid(y.index)].sum()),
        "vigente": lectura_actual(panel, cal, cfg["antiguedad_maxima_meses"]),
        "frecuencia_por_grado_vigente": frecuencia_por_grado(ind, y).round(3).reset_index(names="grado").to_dict("records"),
        "validacion": {
            "umbrales_con_datos_hasta": cfg["validacion_hasta"], "episodios_etiquetados_hasta": str(corte.date()),
            "indicadores_con_peso": [i for i, r in cal_v.iterrows() if r["peso"] > 0],
            "primera_alerta_fuera_de_muestra": str(altos.index.min().date()) if len(altos) else None,
            **evaluacion_fuera_de_muestra(serie, cfg["validacion_hasta"], grados),
            "trayectoria_2024_2025": serie.loc["2024-01-01":"2025-12-01", ["mora", "indice_validacion", "grado_validacion"]]
                .reset_index(names="fecha").assign(fecha=lambda t: t["fecha"].dt.strftime("%Y-%m-%d")).round(3).to_dict("records"),
        },
    }
    with open(out / "resumen_alertas.json", "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, ensure_ascii=False, indent=2)
    print(f"alertas: {out}")


if __name__ == "__main__":
    main()
