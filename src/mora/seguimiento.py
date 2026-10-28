"""Seguimiento de pronósticos: ¿acertó el modelo?

`python -m mora.seguimiento` escribe outputs/seguimiento/.

1. Retrospectiva en tiempo pseudo-real. Para cada mes de origen desde `desde`, con los datos
   hasta ese mes: se eligen de nuevo los rezagos (BIC, signos esperados), se reestima el modelo
   satélite y se proyecta el escenario base a 12 meses con los mismos supuestos que hoy (tasas reales
   en su nivel reciente, variaciones interanuales que vuelven a cero). Es más exigente que la
   validación fuera de muestra de la Fase 4, que usaba los regresores observados: acá también los
   supuestos se arman con lo que se sabía en el origen. Limitación: usa la versión actual de los
   datos (no las publicaciones de cada mes, que pueden haberse revisado).
2. Registro de lo publicado. Cada corrida agrega la proyección base vigente (si su origen es nuevo)
   a outputs/seguimiento/registro_pronosticos.csv. Con el tiempo queda el historial real.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from mora.config import path, settings
from mora.escenarios import simular, supuestos
from mora.satelite import build_dataset, fit, select_spec, signs_ok


def _datos(deflactor: str) -> pd.DataFrame:
    """Muestra larga del satélite, como en mora.escenarios.modelo."""
    df = build_dataset(deflactor=deflactor)
    return df.loc[settings()["sample"]["muestras"]["larga"]["inicio"]:]


def proyeccion_en(df: pd.DataFrame, origen: pd.Timestamp, n_sim: int, rng: np.random.Generator) -> pd.DataFrame | None:
    """Proyección base a 12 meses hecha con los datos hasta `origen` (None si no hay especificación válida)."""
    sat, cfg = settings()["satelite"], settings()["escenarios"]
    d = df.loc[:origen]
    grilla, signos = sat["especificaciones"]["base"]["grilla"], sat["signos_esperados"]
    spec, _ = select_spec(d, grilla, sat["ar_max"], signos)
    res = fit(d, spec)
    if not signs_ok(res, spec, signos):
        return None
    fin = origen + pd.DateOffset(months=cfg["horizonte_meses"])
    caminos, _ = supuestos(d, spec, res, fin)
    central = simular(res, d, caminos["base"], spec, origen, fin, 1, None)[0]
    sims = simular(res, d, caminos["base"], spec, origen, fin, n_sim, rng)
    fechas = pd.date_range(origen + pd.offsets.MonthBegin(1), fin, freq="MS")
    return pd.DataFrame({"origen": origen, "fecha": fechas, "h": np.arange(1, len(fechas) + 1),
                         "mora_origen": float(d.loc[origen, "mora"]), "central": central,
                         "p05": np.percentile(sims, 5, axis=0), "p95": np.percentile(sims, 95, axis=0),
                         "especificacion": spec.name()})


def retrospectiva(deflactor: str) -> pd.DataFrame:
    cfg = settings()["seguimiento"]
    df = _datos(deflactor)
    ultimo = df["dy"].dropna().index.max()
    rng = np.random.default_rng(cfg["semilla"])
    tablas = []
    for origen in pd.date_range(cfg["desde"], ultimo - pd.DateOffset(months=1), freq="MS"):
        p = proyeccion_en(df, origen, cfg["simulaciones"], rng)
        if p is not None:
            tablas.append(p)
    out = pd.concat(tablas, ignore_index=True)
    out["observada"] = out["fecha"].map(df["mora"])
    out["error"] = out["central"] - out["observada"]
    out["error_ingenuo"] = out["mora_origen"] - out["observada"]  # sin cambio desde el origen
    out["dentro_banda"] = (out["observada"] >= out["p05"]) & (out["observada"] <= out["p95"])
    return out.assign(deflactor=deflactor)


def metricas(r: pd.DataFrame, horizontes: list[int]) -> pd.DataFrame:
    filas = []
    for h in horizontes:
        x = r[(r["h"] == h) & r["observada"].notna()]
        filas.append({"h": h, "n": int(len(x)), "error_medio": float(x["error"].mean()),
                      "error_absoluto_medio": float(x["error"].abs().mean()),
                      "error_absoluto_medio_ingenuo": float(x["error_ingenuo"].abs().mean()),
                      "cobertura_banda_90": float(x["dentro_banda"].mean())})
    return pd.DataFrame(filas)


def registrar(archivo) -> pd.DataFrame:
    """Agrega la proyección base publicada (mora.escenarios, medición principal) si su origen es nuevo."""
    principal = settings()["deflactores"]["principal"]
    esc = json.load(open(path("outputs") / "escenarios" / "resumen_escenarios.json", encoding="utf-8"))[f"satelite_{principal}"]
    tray = pd.read_csv(path("outputs") / "escenarios" / "trayectorias.csv", parse_dates=["fecha"])
    tray = tray[(tray["modelo"] == "satelite") & (tray["deflactor"] == principal) & (tray["escenario"] == "base")]
    nueva = pd.DataFrame({"origen": pd.Timestamp(esc["origen"]), "fecha": tray["fecha"], "mora_origen": esc["mora_origen"],
                          "central": tray["central"], "p05": tray["p05"], "p95": tray["p95"],
                          "registrado": pd.Timestamp.today().normalize()})
    hist = pd.read_csv(archivo, parse_dates=["origen", "fecha", "registrado"]) if archivo.exists() else None
    if hist is not None and (hist["origen"] == nueva["origen"].iloc[0]).any():
        return hist
    out = pd.concat([hist, nueva], ignore_index=True) if hist is not None else nueva
    out.to_csv(archivo, index=False, date_format="%Y-%m-%d")
    return out


def main() -> None:
    cfg = settings()["seguimiento"]
    out = path("outputs") / "seguimiento"
    out.mkdir(parents=True, exist_ok=True)
    principal = settings()["deflactores"]["principal"]
    r = retrospectiva(principal)
    r.to_csv(out / "retrospectiva.csv", index=False, date_format="%Y-%m-%d")
    m = metricas(r, cfg["horizontes"])
    m.to_csv(out / "metricas_retrospectiva.csv", index=False)
    reg = registrar(out / "registro_pronosticos.csv")
    resumen = {"deflactor": principal, "origenes": [str(r["origen"].min().date()), str(r["origen"].max().date())],
               "n_origenes": int(r["origen"].nunique()), "metricas": m.round(3).to_dict("records"),
               "registro_origenes": sorted({str(pd.Timestamp(x).date()) for x in reg["origen"]})}
    with open(out / "resumen_seguimiento.json", "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, ensure_ascii=False, indent=2)
    print(f"seguimiento: {out}")


if __name__ == "__main__":
    main()
