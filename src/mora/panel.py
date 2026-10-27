"""Fase 5: panel por entidad. `python -m mora.panel` escribe outputs/panel/.

Con efectos fijos de entidad y de mes, la macro común a todos los bancos (tasas, inflación,
ancla cambiaria) queda absorbida: lo que se identifica es la variación ENTRE entidades.

1. Cosecha: ¿las entidades que más crecieron en crédito al consumo tienen más mora 12-24 meses
   después que las que crecieron menos, en el mismo mes?
2. Esterilización (estudio de eventos con exposición continua): ¿las entidades más expuestas al
   sector público y al BCRA (títulos + pases sobre activo) antes del apretón de jul-2025 prestaron
   menos y tuvieron más mora después, relativo a las menos expuestas?
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS

from mora.config import path, settings
from mora.descriptivo import irregular_consumo, normalize_esd_saldo
from mora.features import precios


def build_panel(deflactor: str = "publico") -> pd.DataFrame:
    """Panel entidad x mes con mora de consumo, crédito real, exposición al sector público y controles."""
    cfg = settings()["panel"]
    p = pd.read_csv(path("processed") / "entidades_panel.csv", dtype={"entidad": str}, parse_dates=["fecha"])
    p = normalize_esd_saldo(p)
    p = p[~p["entidad"].str.startswith("AA")]
    b = pd.read_csv(path("processed") / "entidades_balance.csv", dtype={"entidad": str}, parse_dates=["fecha"])
    df = p.merge(b, on=["entidad", "fecha"], how="inner")
    ipc = precios(deflactor)["ipc"]

    df["irr"] = irregular_consumo(df)
    df["consumo"] = df[["prestamos_personales", "prestamos_tarjetas"]].sum(axis=1, min_count=1)
    df["consumo_real"] = df["consumo"] / df["fecha"].map(ipc)
    df["activo_real"] = df["activo_total"] / df["fecha"].map(ipc)
    df["exposicion_sp"] = 100 * (df["titulos_publicos_bcra"].fillna(0) + df["pases_activos"].fillna(0)) / df["activo_total"]
    df["part_tarjetas"] = 100 * df["prestamos_tarjetas"] / df["consumo"]
    df = df.sort_values(["entidad", "fecha"])

    g = df.groupby("entidad")
    df["g_consumo_12"] = 100 * (np.log(df["consumo_real"]) - g["consumo_real"].transform(lambda s: np.log(s).shift(12)))
    df["d12_irr"] = df["irr"] - g["irr"].shift(12)
    df["log_activo_real"] = np.log(df["activo_real"])

    # Entidades con cartera de consumo relevante y suficiente historia
    df = df[(df["consumo"] > 0) & (df["esd_consumo_saldo"] > 0) & df["irr"].notna()]
    meses = df.groupby("entidad")["fecha"].transform("size")
    df = df[meses >= cfg["meses_minimos"]]
    df = df.replace([np.inf, -np.inf], np.nan)
    return df


def _panel_index(df: pd.DataFrame) -> pd.DataFrame:
    return df.set_index(["entidad", "fecha"])


def cosecha_fe(df: pd.DataFrame) -> pd.DataFrame:
    """Δ12 mora_{i,t} sobre el crecimiento del crédito de la entidad 12 y 24 meses antes, con EF de entidad y de mes."""
    d = df.copy().sort_values(["entidad", "fecha"])
    g = d.groupby("entidad")
    d["g_consumo_12_l12"] = g["g_consumo_12"].shift(12)  # crecimiento entre t-24 y t-12
    d["g_consumo_12_l24"] = g["g_consumo_12"].shift(24)  # crecimiento entre t-36 y t-24
    d["exposicion_sp_l12"] = g["exposicion_sp"].shift(12)
    d["part_tarjetas_l12"] = g["part_tarjetas"].shift(12)
    d["log_activo_real_l12"] = g["log_activo_real"].shift(12)
    cols = ["d12_irr", "g_consumo_12_l12", "g_consumo_12_l24", "exposicion_sp_l12", "part_tarjetas_l12", "log_activo_real_l12"]
    data = _panel_index(d)[cols].dropna()
    # recorte de extremos en crecimiento (entidades muy chicas o fusiones)
    lo, hi = settings()["panel"]["recorte_crecimiento"]
    for c in ("g_consumo_12_l12", "g_consumo_12_l24"):
        data = data[data[c].between(lo, hi)]
    res = PanelOLS(data["d12_irr"], data[cols[1:]], entity_effects=True, time_effects=True, drop_absorbed=True).fit(
        cov_type="clustered", cluster_entity=True
    )
    return _tidy(res, "cosecha_fe")


def event_study(df: pd.DataFrame, outcome: str, evento: str, ventana: tuple[int, int], fecha_exposicion: str) -> pd.DataFrame:
    """y_it = a_i + l_t + Σ_k b_k · E_i · 1[t = evento + k] + e_it, con k = -1 como referencia.

    E_i es la exposición al sector público estandarizada, medida antes del evento.
    """
    d = df.copy()
    expo = d[d["fecha"] == pd.Timestamp(fecha_exposicion)].set_index("entidad")["exposicion_sp"]
    expo = (expo - expo.mean()) / expo.std()
    d = d[d["entidad"].isin(expo.index)]
    d["E"] = d["entidad"].map(expo)
    ev = pd.Timestamp(evento)
    d["k"] = (d["fecha"].dt.year - ev.year) * 12 + (d["fecha"].dt.month - ev.month)
    d = d[d["k"].between(*ventana)]
    if outcome == "consumo_real_rel":
        base = d[d["fecha"] == pd.Timestamp(fecha_exposicion)].set_index("entidad")["consumo_real"]
        d["consumo_real_rel"] = 100 * np.log(d["consumo_real"] / d["entidad"].map(base))
    terms = []
    for k in range(ventana[0], ventana[1] + 1):
        if k == -1:
            continue
        name = f"E_x_k{k:+d}"
        d[name] = d["E"] * (d["k"] == k)
        terms.append(name)
    data = _panel_index(d)[[outcome, *terms]].dropna()
    res = PanelOLS(data[outcome], data[terms], entity_effects=True, time_effects=True).fit(cov_type="clustered", cluster_entity=True)
    out = _tidy(res, f"evento_{outcome}")
    out["k"] = out["termino"].str.extract(r"k([+-]\d+)").astype(int)
    out["n_entidades"] = data.index.get_level_values(0).nunique()
    return out


def _tidy(res, modelo: str) -> pd.DataFrame:
    ci = res.conf_int()
    return pd.DataFrame(
        {
            "modelo": modelo,
            "termino": res.params.index,
            "coef": res.params.values,
            "se_cluster": res.std_errors.values,
            "pvalor": res.pvalues.values,
            "ic95_inf": ci["lower"].values,
            "ic95_sup": ci["upper"].values,
            "n": int(res.nobs),
        }
    )


def run(deflactor: str, out) -> dict:
    cfg = settings()["panel"]
    out.mkdir(parents=True, exist_ok=True)
    df = build_panel(deflactor)
    cos = cosecha_fe(df)
    ev = cfg["evento"]
    es = pd.concat(
        [event_study(df, y, ev["fecha"], tuple(ev["ventana"]), ev["fecha_exposicion"]) for y in ("consumo_real_rel", "irr")]
    )
    cos.to_csv(out / "cosecha_fe.csv", index=False)
    es.to_csv(out / "estudio_eventos_exposicion.csv", index=False)
    resumen = {
        "deflactor": deflactor,
        "entidades": int(df["entidad"].nunique()),
        "observaciones": int(len(df)),
        "desde": str(df["fecha"].min().date()),
        "hasta": str(df["fecha"].max().date()),
    }
    with open(out / "resumen_panel.json", "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, ensure_ascii=False, indent=2)
    return {"cosecha": cos, "eventos": es, "resumen": resumen}


def main() -> None:
    run(settings()["deflactores"]["principal"], path("outputs") / "panel")
    print("panel: ok")


if __name__ == "__main__":
    main()
