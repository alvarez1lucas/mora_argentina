"""Tres mediciones de precios para tres líneas de conclusiones.

- **publico**: IPC oficial del INDEC (canasta ENGHo 2004/05). Antes de dic-2016, la inflación
  mensual de la API del BCRA (empalme, marcado).
- **seleccionado**: las mismas divisiones nacionales del INDEC re-ponderadas con la estructura de
  gasto de la ENGHo 2017/18 (la canasta del índice nuevo que se postergó en feb-2026). Antes de
  dic-2016 se encadena con el IPC de la Ciudad de Buenos Aires (IPCBA), que tiene una metodología
  más actual; antes de jul-2012, con el empalme del BCRA.
- **mix**: promedio geométrico de las variaciones mensuales de publico y seleccionado.

El IPCBA completo (2012-2026) queda como validación externa: es otra medición, de otro organismo,
para otra jurisdicción.

Índice de Laspeyres con base dic-2016: I_t = Σ w_i I_{i,t} / 100, con w_i las participaciones de
gasto llevadas a precios de la base: w_i ∝ s_i / (precio relativo de la división i en el período
de la encuesta respecto de dic-2016).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import nnls

from mora.config import path, settings

DEFLACTORES = ("publico", "seleccionado", "mix")


def _load(name: str) -> pd.DataFrame:
    return pd.read_csv(path("processed") / f"{name}.csv", index_col=0, parse_dates=True)


def chain_backwards(level: pd.Series, monthly_pct: pd.Series) -> pd.Series:
    """Extiende hacia atrás un índice con variaciones mensuales (%) de otra fuente."""
    level = level.dropna()
    base = level.index.min()
    back = monthly_pct[monthly_pct.index <= base].sort_index()
    # P_{t-1} = P_t / (1 + pi_t)
    factor = (1 + back / 100).iloc[::-1].cumprod().iloc[::-1]
    extra = level.loc[base] / factor.shift(-1).fillna(1.0)
    extra = extra[extra.index < base]
    return pd.concat([extra, level]).sort_index()


def splice_ratio(old: pd.Series, new: pd.Series) -> pd.Series:
    """Empalma dos bases de un índice por el cociente en el primer mes común."""
    old, new = old.dropna(), new.dropna()
    common = old.index.intersection(new.index)
    if common.empty:
        raise ValueError("Las series no tienen meses en común para empalmar")
    k = new.loc[common[0]] / old.loc[common[0]]
    return pd.concat([old[old.index < common[0]] * k, new]).sort_index()


def price_updated_weights(shares: dict[str, float], divisions: pd.DataFrame, periodo: tuple[str, str]) -> pd.Series:
    """Participaciones de gasto del período de la encuesta llevadas a precios de la base del índice."""
    s = pd.Series(shares, dtype=float)
    rel = divisions.loc[periodo[0] : periodo[1], s.index].mean() / divisions.iloc[0][s.index]
    w = s / rel
    return w / w.sum()


def laspeyres(divisions: pd.DataFrame, weights: pd.Series) -> pd.Series:
    """Índice agregado (base = 100 en el primer mes) a partir de índices por división base 100."""
    d = divisions[weights.index]
    return (d * weights).sum(axis=1, min_count=len(weights))


def recover_weights(general: pd.Series, divisions: pd.DataFrame) -> tuple[pd.Series, float]:
    """Ponderaciones implícitas del índice oficial por mínimos cuadrados no negativos (validación)."""
    data = pd.concat([general.rename("_g"), divisions], axis=1).dropna()
    w, _ = nnls(data.drop(columns="_g").values, data["_g"].values)
    fitted = data.drop(columns="_g").values @ w
    return pd.Series(w, index=divisions.columns), float(np.abs(fitted / data["_g"].values - 1).max())


def ipcba() -> pd.Series:
    m = _load("macro_mensual")
    return splice_ratio(m["ipcba_general_b2012"], m["ipcba_general_b2021"])


def build() -> pd.DataFrame:
    """Índices de precios mensuales (base dic-2016 = 100 en todas) y validaciones."""
    cfg = settings()["deflactores"]
    reg = cfg["region"]
    div = _load("ipc_divisiones")
    codes = list(cfg["engho_2017_18"])
    divisions = div[[f"{reg}_{c}" for c in codes]].set_axis(codes, axis=1)
    oficial = div[f"{reg}_00"]
    bcra = _load("bcra_mensual")["inflacion_mensual"]

    w_new = price_updated_weights(cfg["engho_2017_18"], divisions, tuple(cfg["engho_periodo"]))
    seleccionado = laspeyres(divisions, w_new)

    caba = ipcba()
    caba_pct = 100 * caba.pct_change()
    publico = chain_backwards(oficial, bcra)
    # antes de dic-2016: IPCBA desde jul-2012; antes, el empalme del BCRA
    seleccionado = chain_backwards(chain_backwards(seleccionado, caba_pct.dropna()), bcra)

    pi_pub = publico.pct_change()
    pi_sel = seleccionado.reindex(publico.index).pct_change()
    pi_mix = np.sqrt((1 + pi_pub) * (1 + pi_sel)) - 1
    mix = (1 + pi_mix.fillna(0)).cumprod()
    mix = mix / mix.loc[oficial.index.min()] * 100

    out = pd.DataFrame(
        {
            "publico": publico,
            "seleccionado": seleccionado.reindex(publico.index),
            "mix": mix.where(publico.notna()),
            "ipcba": (caba / caba.loc[oficial.index.min()] * 100) if oficial.index.min() in caba.index else caba,
        }
    )
    out["empalme_publico"] = out.index < oficial.index.min()
    out["empalme_seleccionado"] = out.index < caba.dropna().index.min()
    return out


def validation_report() -> dict:
    """Chequeos del método, para documentar en el sitio y en el README."""
    cfg = settings()["deflactores"]
    reg = cfg["region"]
    div = _load("ipc_divisiones")
    codes = list(cfg["engho_2017_18"])
    divisions = div[[f"{reg}_{c}" for c in codes]].set_axis(codes, axis=1)
    w_old, err = recover_weights(div[f"{reg}_00"], divisions)
    w_new = price_updated_weights(cfg["engho_2017_18"], divisions, tuple(cfg["engho_periodo"]))
    return {
        "ponderaciones_implicitas_oficial": (100 * w_old).round(2).to_dict(),
        "error_max_reconstruccion_oficial_pct": round(100 * err, 3),
        "ponderaciones_engho_2017_18_a_precios_dic16": (100 * w_new).round(2).to_dict(),
    }


def deflator(nombre: str) -> pd.Series:
    if nombre not in DEFLACTORES:
        raise ValueError(f"Deflactor desconocido: {nombre}")
    return build()[nombre]
