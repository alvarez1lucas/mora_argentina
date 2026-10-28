"""Fase 8: README (inglés y español) e informe de 2 páginas, generados desde outputs/.

`python -m mora.informe` escribe README.md, README_ES.md, site/informe.html y site/en/report.html.
El PDF del informe lo imprime Chrome en el workflow de publicación.

Ningún número está escrito a mano: todo sale de outputs/ (vía mora.sitio.datos), y el workflow
semanal regenera estos archivos junto con los datos.
"""

from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go

from mora.config import ROOT, settings
from mora.sitio import (CSS, JS_TEMA, LIMITACIONES, MEDICIONES, PLOTLY_ES, PLOTLY_JS, SERIES, TINTA, T, _div, _json,
                        datos, fig_canales, fig_escenarios, mes, num)


def pval(p: float, L: str) -> str:
    """'p < 0,001' o 'p = 0,049' según el idioma."""
    return f"p < {num(0.001, L, 3)}" if p < 0.001 else f"p = {num(p, L, 3)}"


def cifras(d: dict, L: str) -> dict:
    """Números clave formateados para el idioma `L`. Cada uno sale de outputs/."""
    desc, aj, rend, esc = d["desc"], d["ajuste"], d["rend"], d["esc"]
    a = d["canales"]
    pp = lambda x, k=1: num(x, L, k)  # noqa: E731

    def canal(v, c, campo="aporte_pp"):
        vals = [float(a[(a["variante"] == v) & (a["deflactor"] == m) & (a["canal"] == c)][campo].iloc[0]) for m in MEDICIONES]
        return min(vals), max(vals)

    oos = d["oos"]
    o12 = oos[(oos["especificacion"] == "base") & (oos["muestra"] == "larga") & (oos["h"] == 12)].set_index("modelo")
    oc12 = d["oos_canales"][d["oos_canales"]["h"] == 12].set_index("modelo")
    sat = {m: esc[f"satelite_{m}"] for m in MEDICIONES}
    k = d["castigos"].iloc[-2:]
    ct = d["castigos_total"].iloc[-1]
    sal = d["cadena"][[f"salario_real_{m}" for m in MEDICIONES]].dropna().iloc[-1]
    feb24 = d["profundidad"].loc["2024-02-01"]
    fe = pd.read_csv(ROOT / "outputs/panel/cosecha_fe.csv").set_index("termino").loc["g_consumo_12_l12"]
    dml = pd.read_csv(ROOT / "outputs/panel_ml/double_ml_cosecha.csv").iloc[0]
    cf = d["panel_ml"]["causal_forest_ate"]
    ew = pd.read_csv(ROOT / "outputs/panel_ml/alerta_temprana_evaluacion.csv").set_index("modelo")
    rc = _json("canales/resumen_canales.json")["base_publico"]
    rango = lambda t: f"{pp(t[0])}–{pp(t[1])}"  # noqa: E731
    return {
        "fecha": mes(desc["ultimo_dato"], L), "mora": pp(desc["mora_familias"]),
        "multiplo": pp(desc["mora_familias"] / aj["mora_familias"]["inicio"]), "mora_ini": pp(aj["mora_familias"]["inicio"]),
        "fecha_ini": mes(aj["ventana"][0], L), "max": pp(desc["maximo_de_la_serie"]), "fecha_max": mes(desc["fecha_maximo"], L),
        "pers": pp(desc["mora_por_linea"]["personales"]), "tarj": pp(desc["mora_por_linea"]["tarjetas_de_credito"]),
        "num": pp(desc["efecto_numerador_12m"]), "den": pp(desc["efecto_denominador_12m"], 2),
        "v_ini": mes(rc["ventana"][0], L), "v_fin": mes(rc["ventana"][1], L),
        "v_mora_ini": pp(rc["mora_inicio"]), "v_mora_fin": pp(rc["mora_fin"]),
        "costo": rango(canal("base", "costo_financiero")), "costo_p": f"{num(canal('base', 'costo_financiero', 'pvalor')[0], L, 3)}–{num(canal('base', 'costo_financiero', 'pvalor')[1], L, 3)}",
        "estado": rango(canal("costo_oportunidad", "rendimiento_estado")),
        "estado_p": f"{num(canal('costo_oportunidad', 'rendimiento_estado', 'pvalor')[0], L, 3)}–{num(canal('costo_oportunidad', 'rendimiento_estado', 'pvalor')[1], L, 3)}",
        "prima": rango(canal("costo_oportunidad", "prima_familias")),
        "poder_pub": pp(float(a[(a["variante"] == "base") & (a["deflactor"] == "publico") & (a["canal"] == "poder_compra")]["aporte_pp"].iloc[0])),
        "poder_sel": pp(float(a[(a["variante"] == "base") & (a["deflactor"] == "seleccionado") & (a["canal"] == "poder_compra")]["aporte_pp"].iloc[0])),
        "poder_pub_p": num(float(a[(a["variante"] == "base") & (a["deflactor"] == "publico") & (a["canal"] == "poder_compra")]["pvalor"].iloc[0]), L, 3),
        "poder_sel_p": num(float(a[(a["variante"] == "base") & (a["deflactor"] == "seleccionado") & (a["canal"] == "poder_compra")]["pvalor"].iloc[0]), L, 3),
        "estado_25": pp(rend["promedios_anuales"]["2025"]["tea_estado_3m"]), "badlar_25": pp(rend["promedios_anuales"]["2025"]["tea_badlar"]),
        "pers_25": pp(rend["promedios_anuales"]["2025"]["tea_personales_nuevos"]),
        "prima_25": pp(rend["promedios_anuales"]["2025"]["prima_personales_sobre_estado_pp"]),
        "estado_badlar_pct": pp(rend["meses_estado_rinde_mas_que_badlar_pct"], 0),
        "exp_feb24": pp(feb24["exposicion_estado_mn_pbi"]), "cred_feb24": pp(feb24["credito_privado_mn_pbi"]),
        "sal_pub": pp(100 - sal["salario_real_publico"]), "sal_mix": pp(100 - sal["salario_real_mix"]),
        "sal_sel": pp(100 - sal["salario_real_seleccionado"]),
        "k_meses": f"{mes(k['fecha'].iloc[0], L)} {'y' if L == 'es' else 'and'} {mes(k['fecha'].iloc[1], L)}",
        "k_obs": f"{pp(k['var_irregular_familias_real'].iloc[0] / 1000, 0)} / {pp(k['var_irregular_familias_real'].iloc[1] / 1000, 0)}",
        "k_cast": f"{pp(k['castigos_familias_estimado_real'].iloc[0] / 1000, 0)} / {pp(k['castigos_familias_estimado_real'].iloc[1] / 1000, 0)}",
        "k_sin": f"{pp(k['irregular_familias_sin_castigos_real'].iloc[0] / 1000, 0)} / {pp(k['irregular_familias_sin_castigos_real'].iloc[1] / 1000, 0)}",
        "ct_fecha": mes(ct["fecha"], L), "ct_aj": pp(ct["ratio_ajustado"]), "ct_of": pp(ct["ratio_oficial"]),
        "rmse_sat": pp(o12.loc["satelite", "rmse"], 2), "rmse_ar": pp(o12.loc["ar1", "rmse"], 2), "rmse_rw": pp(o12.loc["paseo_aleatorio", "rmse"], 2),
        "rmse_can": pp(oc12.loc["satelite", "rmse"], 2), "rmse_can_ar": pp(oc12.loc["ar1", "rmse"], 2),
        "esc_fin": mes(sat["publico"]["fin"], L),
        "esc": {m: {"muestra": sat[m]["muestra"], **{e: pp(sat[m]["mora_fin"][e]["central"]) for e in ("base", "adverso", "favorable")},
                    "p05": pp(sat[m]["mora_fin"]["base"]["p05"]), "p95": pp(sat[m]["mora_fin"]["base"]["p95"]),
                    "niif9": pp(sat[m]["niif9"]["mora_ponderada"]), "prob": pp(100 * sat[m]["prob_mora_fin_supera_origen"]["base"], 0)}
                for m in MEDICIONES},
        "pesos": {e: pp(100 * w, 0) for e, w in sat["publico"]["niif9"]["pesos"].items()},
        "fe": pp(10 * fe["coef"], 2), "fe_p": pval(fe["pvalor"], L), "dml": pp(10 * dml["coef"], 2), "dml_p": pval(dml["pvalor"], L),
        "cf": pp(10 * cf["ate"], 2), "cf_lo": pp(10 * cf["ic95"][0], 2), "cf_hi": pp(10 * cf["ic95"][1], 2),
        "n_ent": d["panel"]["entidades"],
        "ew_lgb": pp(100 * ew.loc["lightgbm", "precision_decil_superior"], 0), "ew_lin": pp(100 * ew.loc["lineal", "precision_decil_superior"], 0),
        "ew_rmse_lin": pp(ew.loc["lineal", "rmse"], 2), "ew_rmse_lgb": pp(ew.loc["lightgbm", "rmse"], 2),
    }


# --------------------------------------------------------------------------- README

def readme(d: dict, L: str) -> str:
    c = cifras(d, L)
    cfg = settings()["sitio"]
    url, repo = cfg["url"], cfg["repo_url"]
    med = T[L]["med"]
    lim = "\n".join(f"- {x}" for x in LIMITACIONES[L])
    filas_esc = "\n".join(
        f"| {med[m]} | {'2010+' if c['esc'][m]['muestra'] == 'larga' else '2017+'} | {c['esc'][m]['base']}% | {c['esc'][m]['p05']}–{c['esc'][m]['p95']}% | "
        f"{c['esc'][m]['adverso']}% | {c['esc'][m]['favorable']}% | {c['esc'][m]['niif9']}% |" for m in MEDICIONES)
    if L == "en":
        return f"""# Household loan delinquency in Argentina

**[Live site]({url})** · **[2-page report (PDF)]({url}informe-en.pdf)** · [Versión en español](README_ES.md)

What explains the 2024-2026 surge in household non-performing loans in Argentina, and what may happen over the next 12 months? This project answers with public data only (BCRA, INDEC, Buenos Aires City statistics, A3 Mercados), time-series and panel econometrics, causal ML, and out-of-sample validation. Every number below is generated from `outputs/` by `python -m mora.informe`; the pipeline refreshes weekly via GitHub Actions.

## Key results (data as of {c['fecha']})

- **Delinquency multiplied by {c['multiplo']}.** The household NPL ratio (BCRA situations 3-5) rose from {c['mora_ini']}% in {c['fecha_ini']} to {c['mora']}% in {c['fecha']}, the highest since the series starts in 2010 (peak {c['max']}% in {c['fecha_max']}). Personal loans: {c['pers']}%; credit cards: {c['tarj']}%.
- **It is unpaid debt, not a shrinking portfolio.** Of the 12-month rise, +{c['num']} pp is the numerator (real growth in non-performing debt) and {c['den']} pp the denominator.
- **Financial cost is the dominant channel.** In a counterfactual historical decomposition of the rise from {c['v_ini']} ({c['v_mora_ini']}%) to {c['v_fin']} ({c['v_mora_fin']}%), the real all-in cost of personal loans contributes +{c['costo']} pp (p = {c['costo_p']}) under all three price measures.
- **Sterilization works through the floor it sets on lending rates.** Banks' implied yield on peso government securities and central-bank repos (from their income statements, restated for inflation) averaged {c['estado_25']}% in 2025, above BADLAR ({c['badlar_25']}%); it beat BADLAR in {c['estado_badlar_pct']}% of months since Nov-23. Splitting the loan rate into *what the State pays* and *the household premium*, the former contributes +{c['estado']} pp and is significant (p = {c['estado_p']}); the premium adds +{c['prima']} pp but is not significant.
- **Purchasing power matters more under realistic price measures.** The real registered wage is {c['sal_pub']}% below Nov-23 with the official CPI, {c['sal_mix']}% with the mix and {c['sal_sel']}% with an updated-weights basket. Its contribution goes from +{c['poder_pub']} pp (p = {c['poder_pub_p']}) to +{c['poder_sel']} pp (p = {c['poder_sel_p']}).
- **The recent leveling-off is largely write-offs.** In {c['k_meses']} household non-performing debt grew {c['k_obs']} billion constant pesos while about {c['k_cast']} billion were written off; without write-offs it would have grown {c['k_sin']} billion. For the total private sector, the {c['ct_fecha']} ratio would be {c['ct_aj']}% instead of {c['ct_of']}%.
- **Vintage (cosecha) effect at bank level.** Across {c['n_ent']} banks with entity and month fixed effects, 10 pp more real consumer-credit growth 12-24 months earlier adds {c['fe']} pp to the annual change in NPLs ({c['fe_p']}); Double ML: {c['dml']} pp ({c['dml_p']}); causal forest ATE: {c['cf']} pp (95% CI {c['cf_lo']} to {c['cf_hi']}).

### Scenarios to {c['esc_fin']} (household NPL ratio, currently {c['mora']}%)

| Price measure | Sample | Baseline | 90% band | Adverse | Favorable | IFRS 9 weighted |
|---|---|---|---|---|---|---|
{filas_esc}

The satellite model beats the AR(1) and the random walk out of sample (12-month RMSE {c['rmse_sat']} pp vs {c['rmse_ar']} and {c['rmse_rw']}). IFRS 9 weights: {c['pesos']['base']}% baseline, {c['pesos']['adverso']}% adverse, {c['pesos']['favorable']}% favorable. **In the baseline, delinquency keeps rising** because the real loan rate stays near historical highs; it only falls if real rates fall.

## Approach

| Phase | What | Module | Output |
|---|---|---|---|
| 1-2 | Data survey and reproducible ingestion (BCRA APIs and files, INDEC, datos.gob.ar, A3) | `mora.ingest` | `data/processed/` |
| 3 | Descriptive: lines, bank groups, numerator vs denominator, write-off-adjusted ratio | `mora.descriptivo` | `outputs/descriptivo/` |
| 4 | Satellite model with out-of-sample validation, long (2010+) and clean (2017+) samples | `mora.satelite` | `outputs/modelo/` |
| 4b | Three price measures: official, updated-weights basket, mix | `mora.deflactores`, `mora.robustez` | `outputs/robustez/` |
| 5 | Channel weighting, mediation, opportunity cost, bank panel, causal ML, early warning | `mora.canales`, `mora.rendimientos`, `mora.panel`, `mora.panel_ml`, `mora.ajuste` | `outputs/canales/`, ... |
| 6 | Scenarios with simulation bands and IFRS 9 weighting | `mora.escenarios` | `outputs/escenarios/` |
| 7-8 | Website, report and this README, generated from outputs | `mora.sitio`, `mora.informe` | `site/`, `README*.md` |

## Methods

- Target: logit of the NPL ratio; unit-root tests (ADF, KPSS, Zivot-Andrews) → the model is in differences (no spurious levels regression).
- Lags chosen by BIC inside economically bounded grids, with expected-sign restrictions; HAC standard errors.
- COVID-era classification relief (BCRA A6938/A7245) and its unwinding are excluded from estimation.
- Expanding-window out-of-sample evaluation with re-selection at each origin, against a random walk and an AR(1).
- Counterfactual historical decomposition with coefficient-CI bands; mediation by splitting the loan rate.
- Bank panel: two-way fixed effects (clustered), event study around the Jul-25 tightening, Double ML and causal forest (EconML), LightGBM + SHAP early warning (linear: RMSE {c['ew_rmse_lin']}, top-decile precision {c['ew_lin']}%; LightGBM: {c['ew_rmse_lgb']}, {c['ew_lgb']}%).
- Granger tests, where used, are descriptive only.

## Limitations

{lim}
- The channel model explains but does not forecast: its 12-month RMSE ({c['rmse_can']} pp) is worse than an AR(1) ({c['rmse_can_ar']}).
- With the updated-weights basket, no long-sample specification has the expected signs (its 2010-2016 inflation makes real rates deeply negative), so that scenario uses the 2017+ sample. The long model depends on how inflation during the statistical blackout is measured.

## Reproduce

```bash
pip install -r requirements.txt && pip install -e .
python -m mora.ingest          # downloads and processes public data (bank files: ~2.7 GB, kept out of git)
python -m mora.descriptivo && python -m mora.satelite && python -m mora.robustez
python -m mora.panel && python -m mora.panel_ml && python -m mora.rendimientos && python -m mora.canales
python -m mora.ajuste && python -m mora.escenarios
python -m mora.sitio && python -m mora.informe
pytest
```

Configuration lives in `config/` (`settings.yaml`, regimes, monetary events). Methodological notes: `docs/`.

## Data

BCRA (banking report annex, financial institutions monthly files, statistics API v4, transparency regime), INDEC (CPI by division, wages, employment, EMAE, GDP), Buenos Aires City statistics (IPCBA), datos.gob.ar, A3 Mercados (dollar futures). The credit bureau (Central de Deudores) is deliberately not used, for privacy.

Author: Lucas Alvarez · [GitHub](https://github.com/alvarez1lucas)
"""
    return f"""# Mora de los hogares en Argentina

**[Sitio]({url})** · **[Informe de 2 páginas (PDF)]({url}informe.pdf)** · [English version](README.md)

¿Qué explica la suba de la mora de las familias en Argentina entre 2024 y 2026, y qué puede pasar en los próximos 12 meses? El proyecto responde sólo con datos públicos (BCRA, INDEC, IPCBA, A3 Mercados), econometría de series de tiempo y de panel, ML causal y validación fuera de muestra. Todos los números de este archivo los genera `python -m mora.informe` desde `outputs/`; el pipeline se actualiza todas las semanas con GitHub Actions.

## Resultados (datos a {c['fecha']})

- **La mora se multiplicó por {c['multiplo']}.** La mora de familias (situación 3 a 5, BCRA) pasó de {c['mora_ini']}% en {c['fecha_ini']} a {c['mora']}% en {c['fecha']}, el máximo desde que empieza la serie en 2010 (pico de {c['max']}% en {c['fecha_max']}). Préstamos personales: {c['pers']}%; tarjetas: {c['tarj']}%.
- **Es deuda impaga, no una cartera que se achica.** De la suba de 12 meses, +{c['num']} pp son del numerador (crecimiento real de la deuda irregular) y {c['den']} pp del denominador.
- **El costo financiero es el canal dominante.** En la descomposición histórica contrafáctica de la suba de {c['v_ini']} ({c['v_mora_ini']}%) a {c['v_fin']} ({c['v_mora_fin']}%), el costo real de los préstamos personales aporta +{c['costo']} pp (p = {c['costo_p']}) con las tres mediciones de precios.
- **La esterilización actúa por el piso que pone a la tasa.** Lo que los bancos ganaron con títulos públicos y pases con el BCRA en pesos (cuentas de resultados reexpresadas por inflación) promedió {c['estado_25']}% en 2025, por encima de la BADLAR ({c['badlar_25']}%), y le ganó a la BADLAR en el {c['estado_badlar_pct']}% de los meses desde nov-23. Separando la tasa a familias en *lo que paga el Estado* y *la prima de familias*, lo primero aporta +{c['estado']} pp y es significativo (p = {c['estado_p']}); la prima suma +{c['prima']} pp sin ser significativa.
- **El poder de compra pesa más con mediciones de precios realistas.** El salario registrado real está {c['sal_pub']}% abajo de nov-23 con el IPC oficial, {c['sal_mix']}% con el mix y {c['sal_sel']}% con la canasta actualizada. Su aporte pasa de +{c['poder_pub']} pp (p = {c['poder_pub_p']}) a +{c['poder_sel']} pp (p = {c['poder_sel_p']}).
- **El freno reciente es, en buena parte, castigos.** En {c['k_meses']} la deuda irregular de familias creció {c['k_obs']} mil millones de pesos constantes, mientras se castigaban unos {c['k_cast']} mil millones; sin castigos habría crecido {c['k_sin']} mil millones. Para el sector privado total, la mora de {c['ct_fecha']} sería {c['ct_aj']}% en lugar de {c['ct_of']}%.
- **Efecto cosecha a nivel banco.** En {c['n_ent']} entidades con efectos fijos de entidad y mes, 10 pp más de crecimiento real del crédito al consumo 12-24 meses antes suman {c['fe']} pp a la variación interanual de la mora ({c['fe_p']}); Double ML: {c['dml']} pp ({c['dml_p']}); Causal Forest (ATE): {c['cf']} pp (IC 95%: {c['cf_lo']} a {c['cf_hi']}).

### Escenarios a {c['esc_fin']} (mora de familias, hoy {c['mora']}%)

| Medición | Muestra | Base | Banda 90% | Adverso | Favorable | Ponderado NIIF 9 |
|---|---|---|---|---|---|---|
{filas_esc}

El modelo satélite le gana al AR(1) y al paseo aleatorio fuera de muestra (RMSE a 12 meses: {c['rmse_sat']} pp contra {c['rmse_ar']} y {c['rmse_rw']}). Pesos NIIF 9: {c['pesos']['base']}% base, {c['pesos']['adverso']}% adverso, {c['pesos']['favorable']}% favorable. **En el base la mora sigue subiendo**, porque la tasa real queda cerca de máximos históricos; sólo baja si baja la tasa real.

## Enfoque

| Fase | Qué | Módulo | Output |
|---|---|---|---|
| 1-2 | Relevamiento e ingesta reproducible (APIs y archivos del BCRA, INDEC, datos.gob.ar, A3) | `mora.ingest` | `data/processed/` |
| 3 | Descriptivo: líneas, grupos de bancos, numerador vs denominador, mora ajustada por castigos | `mora.descriptivo` | `outputs/descriptivo/` |
| 4 | Modelo satélite con validación fuera de muestra, muestra larga (2010+) y limpia (2017+) | `mora.satelite` | `outputs/modelo/` |
| 4b | Tres mediciones de precios: oficial, canasta actualizada y mix | `mora.deflactores`, `mora.robustez` | `outputs/robustez/` |
| 5 | Ponderación de canales, mediación, costo de oportunidad, panel por banco, ML causal, alerta temprana | `mora.canales`, `mora.rendimientos`, `mora.panel`, `mora.panel_ml`, `mora.ajuste` | `outputs/canales/`, ... |
| 6 | Escenarios con bandas por simulación y ponderación NIIF 9 | `mora.escenarios` | `outputs/escenarios/` |
| 7-8 | Sitio, informe y este README, generados desde outputs | `mora.sitio`, `mora.informe` | `site/`, `README*.md` |

## Métodos

- Variable: logit de la mora; tests de raíz unitaria (ADF, KPSS, Zivot-Andrews) → el modelo va en diferencias (sin regresión espuria en niveles).
- Rezagos por BIC dentro de grillas acotadas por criterio económico, con restricción de signos; errores HAC.
- El alivio de clasificación de la pandemia (A6938/A7245) y su desarme quedan fuera de la estimación.
- Evaluación fuera de muestra con ventana expansiva y re-selección en cada origen, contra paseo aleatorio y AR(1).
- Descomposición histórica contrafáctica con bandas por IC de los coeficientes; mediación separando la tasa.
- Panel por banco: efectos fijos dobles (errores por cluster), estudio de eventos del apretón de jul-25, Double ML y Causal Forest (EconML), alerta temprana con LightGBM + SHAP (lineal: RMSE {c['ew_rmse_lin']}, precisión en el decil superior {c['ew_lin']}%; LightGBM: {c['ew_rmse_lgb']}, {c['ew_lgb']}%).
- Los tests de Granger, donde se usan, son sólo descriptivos.

## Limitaciones

{lim}
- El modelo de canales explica pero no pronostica: su RMSE a 12 meses ({c['rmse_can']} pp) es peor que el de un AR(1) ({c['rmse_can_ar']}).
- Con la canasta actualizada, ninguna especificación de la muestra larga respeta los signos esperados (su inflación 2010-2016 vuelve muy negativas las tasas reales), así que ese escenario usa la muestra 2017+. El modelo largo depende de cómo se mida la inflación del apagón estadístico.

## Reproducir

```bash
pip install -r requirements.txt && pip install -e .
python -m mora.ingest          # baja y procesa los datos públicos (archivos de entidades: ~2,7 GB, fuera de git)
python -m mora.descriptivo && python -m mora.satelite && python -m mora.robustez
python -m mora.panel && python -m mora.panel_ml && python -m mora.rendimientos && python -m mora.canales
python -m mora.ajuste && python -m mora.escenarios
python -m mora.sitio && python -m mora.informe
pytest
```

La configuración está en `config/` (`settings.yaml`, regímenes, eventos monetarios). Notas metodológicas: `docs/`.

## Datos

BCRA (anexo del Informe sobre Bancos, Información de Entidades Financieras, API de estadísticas v4, régimen de transparencia), INDEC (IPC por división, salarios, empleo, EMAE, PBI), IPCBA (GCBA), datos.gob.ar, A3 Mercados (dólar futuro). La Central de Deudores no se usa, por privacidad.

Autor: Lucas Alvarez · [GitHub](https://github.com/alvarez1lucas)
"""


# --------------------------------------------------------------------------- informe de 2 páginas

CSS_INFORME = """
@page{size:A4;margin:12mm 14mm}
body{font-size:10pt;line-height:1.42;background:#fff;color:#0b0b0b}
main{max-width:none;padding:0}
h1{font-size:17pt;margin:0 0 2px}
h2{font-size:11.5pt;margin:12px 0 4px;break-after:avoid}
.tabla{break-inside:avoid}
.sub{font-size:9.5pt;margin:0 0 8px}
.tiles{grid-template-columns:repeat(4,1fr);gap:6px}
.tile{padding:7px 9px}
.tile-valor{font-size:15pt}
.tile-etq,.tile-nota{font-size:8pt;margin-top:2px}
p,li{margin:3px 0}
ul{padding-left:16px;margin:4px 0}
.fig{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.fig .plotly-graph-div{margin:4px 0;border:1px solid #e1e0d9;border-radius:6px}
table{font-size:8.5pt}
th,td{padding:3px 6px}
.salto{break-before:page}
.nota{font-size:8.5pt}
footer{margin-top:10px;padding-top:6px;font-size:8pt}
"""


def _figs_informe(d: dict, L: str) -> tuple[go.Figure, go.Figure]:
    esc = fig_escenarios(d, L)
    can = fig_canales(d, L)
    # Versión estática: sin menú; escenarios con la medición pública, canales con Estado + prima (mix)
    n_can = len(can.data)
    elegido = 3 + MEDICIONES.index("mix")  # orden de trazas: base × 3 mediciones, costo_oportunidad × 3
    for i, tr in enumerate(can.data):
        tr.visible = i == elegido
    # Ancho fijo: en la impresión el autoajuste de Plotly no ve el ancho de la columna
    for f in (esc, can):
        f.layout.updatemenus = ()
        f.update_layout(height=250, width=335, autosize=False, margin=dict(l=44, r=10, t=8, b=36),
                        font=dict(size=10), legend=dict(y=-0.25, font=dict(size=9)))
    can.update_layout(margin=dict(l=8, r=10, t=8, b=36))
    esc.update_yaxes(title_text="%")
    assert n_can == 6
    return esc, can


def informe_html(d: dict, L: str) -> str:
    c = cifras(d, L)
    esc_fig, can_fig = _figs_informe(d, L)
    med = T[L]["med"]
    tabla = "".join(
        f"<tr><td>{med[m]}</td><td>{'2010+' if c['esc'][m]['muestra'] == 'larga' else '2017+'}</td><td>{c['esc'][m]['base']}%</td>"
        f"<td>{c['esc'][m]['p05']}–{c['esc'][m]['p95']}%</td><td>{c['esc'][m]['adverso']}%</td><td>{c['esc'][m]['favorable']}%</td>"
        f"<td>{c['esc'][m]['niif9']}%</td></tr>" for m in MEDICIONES)
    url = settings()["sitio"]["url"]
    if L == "es":
        enc = ["Medición", "Muestra", "Base", "Banda 90%", "Adverso", "Favorable", "NIIF 9"]
        cuerpo = f"""
<h1>Mora de los hogares en Argentina</h1>
<p class="sub">Informe con datos a {c['fecha']}. Sólo datos públicos; todos los números se generan desde el código del proyecto. Versión interactiva: <a href="{url}">{url}</a></p>
<div class="tiles">
<div class="tile"><div class="tile-valor">{c['mora']}%</div><div class="tile-etq">Mora de familias, {c['fecha']}</div><div class="tile-nota">{c['mora_ini']}% en {c['fecha_ini']}</div></div>
<div class="tile"><div class="tile-valor">+{c['num']} pp</div><div class="tile-etq">Suba de 12 meses por más deuda impaga</div><div class="tile-nota">Denominador: {c['den']} pp</div></div>
<div class="tile"><div class="tile-valor">+{c['estado']} pp</div><div class="tile-etq">Aporte de lo que paga el Estado</div><div class="tile-nota">p = {c['estado_p']}</div></div>
<div class="tile"><div class="tile-valor">{c['esc']['publico']['base']}%</div><div class="tile-etq">Escenario base, {c['esc_fin']}</div><div class="tile-nota">Banda 90%: {c['esc']['publico']['p05']}–{c['esc']['publico']['p95']}%</div></div>
</div>
<h2>Qué pasó</h2>
<p>La mora de las familias (situación 3 a 5) es la más alta desde que empieza la serie en 2010: {c['mora']}% ({c['pers']}% en préstamos personales, {c['tarj']}% en tarjetas). No es un efecto de que se achicó la cartera: de la suba de 12 meses, +{c['num']} pp se explican por el crecimiento real de la deuda impaga.</p>
<h2>Por qué: la cadena</h2>
<ul>
<li><strong>Los bancos le prestaban al Estado.</strong> En feb-24 su exposición al Estado era {c['exp_feb24']}% del PBI, contra {c['cred_feb24']}% de crédito privado.</li>
<li><strong>Lo que paga el Estado pone el piso de la tasa.</strong> En 2025 los títulos y pases en pesos rindieron a los bancos {c['estado_25']}% anual, más que la BADLAR ({c['badlar_25']}%). Los préstamos personales nuevos se quedaron en {c['pers_25']}%: una prima de {c['prima_25']} pp.</li>
<li><strong>El salario no acompañó.</strong> El salario registrado real está {c['sal_pub']}% abajo de nov-23 con el IPC oficial y {c['sal_sel']}% con la canasta actualizada.</li>
</ul>
<div class="fig">{_div(can_fig, 'i-can', L)}{_div(esc_fig, 'i-esc', L)}</div>
<p class="nota">Izquierda: aporte de cada canal a la suba de la mora entre {c['v_ini']} y {c['v_fin']} (medición mix; barras: IC 95%). Derecha: escenarios con la medición pública (banda: 90% de las simulaciones del base).</p>
<h2>Cuánto pesó cada canal</h2>
<ul>
<li><strong>Costo financiero:</strong> +{c['costo']} pp (p = {c['costo_p']}), el canal dominante con las tres mediciones de precios.</li>
<li><strong>Separado:</strong> lo que paga el Estado aporta +{c['estado']} pp (p = {c['estado_p']}); la prima propia de las familias, +{c['prima']} pp (no significativa). La esterilización encarece el crédito por el piso que pone a la tasa, no por la BADLAR.</li>
<li><strong>Poder de compra:</strong> +{c['poder_pub']} pp con el IPC oficial (p = {c['poder_pub_p']}) y +{c['poder_sel']} pp con la canasta actualizada (p = {c['poder_sel_p']}). La estadística oficial subestima este canal.</li>
<li><strong>Cosecha (panel de {c['n_ent']} bancos):</strong> 10 pp más de crecimiento del crédito 12-24 meses antes suman {c['fe']} pp de mora (efectos fijos, {c['fe_p']}); {c['dml']} pp con Double ML y {c['cf']} pp con Causal Forest.</li>
</ul>
<h2>La baja reciente es contable</h2>
<p>En {c['k_meses']} la deuda irregular de familias creció {c['k_obs']} mil millones de pesos constantes, mientras se castigaban unos {c['k_cast']} mil millones. Sin castigos habría crecido {c['k_sin']} mil millones. Para el sector privado total, la mora de {c['ct_fecha']} sería {c['ct_aj']}% y no {c['ct_of']}%.</p>
<h2>Próximos 12 meses</h2>
<div class="tabla"><table><thead><tr>{''.join(f'<th>{h}</th>' for h in enc)}</tr></thead><tbody>{tabla}</tbody></table></div>
<p>El modelo satélite le gana fuera de muestra al AR(1) y al paseo aleatorio (error a 12 meses: {c['rmse_sat']} pp contra {c['rmse_ar']} y {c['rmse_rw']}). <strong>En el base la mora sigue subiendo</strong>, porque la tasa real queda cerca de máximos históricos: para que baje tiene que bajar la tasa real, no alcanza con que la actividad se estabilice. NIIF 9: {c['pesos']['base']}% base, {c['pesos']['adverso']}% adverso, {c['pesos']['favorable']}% favorable.</p>
<h2>Límites</h2>
<ul>
<li>Datos agregados (no se usa la Central de Deudores); sin datos del sector informal ni de la mora de plataformas no bancarias.</li>
<li>Relaciones estimadas con rezagos, no causalidad estricta; un solo ciclo de este tipo: bandas anchas.</li>
<li>El modelo de canales explica pero no pronostica (error a 12 meses {c['rmse_can']} pp contra {c['rmse_can_ar']} del AR(1)). El modelo largo depende de cómo se mida la inflación 2010-2016.</li>
</ul>
"""
    else:
        enc = ["Price measure", "Sample", "Baseline", "90% band", "Adverse", "Favorable", "IFRS 9"]
        cuerpo = f"""
<h1>Household loan delinquency in Argentina</h1>
<p class="sub">Report with data as of {c['fecha']}. Public data only; every number is generated by the project's code. Interactive version: <a href="{url}en/">{url}en/</a></p>
<div class="tiles">
<div class="tile"><div class="tile-valor">{c['mora']}%</div><div class="tile-etq">Household NPL ratio, {c['fecha']}</div><div class="tile-nota">{c['mora_ini']}% in {c['fecha_ini']}</div></div>
<div class="tile"><div class="tile-valor">+{c['num']} pp</div><div class="tile-etq">12-month rise from more unpaid debt</div><div class="tile-nota">Denominator: {c['den']} pp</div></div>
<div class="tile"><div class="tile-valor">+{c['estado']} pp</div><div class="tile-etq">Contribution of what the State pays</div><div class="tile-nota">p = {c['estado_p']}</div></div>
<div class="tile"><div class="tile-valor">{c['esc']['publico']['base']}%</div><div class="tile-etq">Baseline scenario, {c['esc_fin']}</div><div class="tile-nota">90% band: {c['esc']['publico']['p05']}–{c['esc']['publico']['p95']}%</div></div>
</div>
<h2>What happened</h2>
<p>The household NPL ratio (situations 3 to 5) is the highest since the series starts in 2010: {c['mora']}% ({c['pers']}% for personal loans, {c['tarj']}% for credit cards). It is not a shrinking-portfolio effect: +{c['num']} pp of the 12-month rise comes from real growth in unpaid debt.</p>
<h2>Why: the chain</h2>
<ul>
<li><strong>Banks were lending to the State.</strong> In Feb-24 their exposure to the State was {c['exp_feb24']}% of GDP, against {c['cred_feb24']}% for private credit.</li>
<li><strong>What the State pays sets the floor for loan rates.</strong> In 2025 peso securities and repos paid banks {c['estado_25']}% a year, more than BADLAR ({c['badlar_25']}%). New personal loans stayed at {c['pers_25']}%: a {c['prima_25']} pp premium.</li>
<li><strong>Wages did not keep up.</strong> The real registered wage is {c['sal_pub']}% below Nov-23 with the official CPI and {c['sal_sel']}% with the updated basket.</li>
</ul>
<div class="fig">{_div(can_fig, 'i-can', L)}{_div(esc_fig, 'i-esc', L)}</div>
<p class="nota">Left: each channel's contribution to the rise between {c['v_ini']} and {c['v_fin']} (mix measure; bars: 95% CI). Right: scenarios with the official measure (band: 90% of baseline simulations).</p>
<h2>How much each channel weighed</h2>
<ul>
<li><strong>Financial cost:</strong> +{c['costo']} pp (p = {c['costo_p']}), the dominant channel under all three price measures.</li>
<li><strong>Split:</strong> what the State pays contributes +{c['estado']} pp (p = {c['estado_p']}); the household-specific premium +{c['prima']} pp (not significant). Sterilization makes credit dearer through the floor it sets on rates, not through BADLAR.</li>
<li><strong>Purchasing power:</strong> +{c['poder_pub']} pp with the official CPI (p = {c['poder_pub_p']}) and +{c['poder_sel']} pp with the updated basket (p = {c['poder_sel_p']}). Official statistics understate this channel.</li>
<li><strong>Vintage effect ({c['n_ent']}-bank panel):</strong> 10 pp more credit growth 12-24 months earlier adds {c['fe']} pp of NPLs (fixed effects, {c['fe_p']}); {c['dml']} pp with Double ML and {c['cf']} pp with a causal forest.</li>
</ul>
<h2>The recent leveling-off is an accounting effect</h2>
<p>In {c['k_meses']} household non-performing debt grew {c['k_obs']} billion constant pesos while about {c['k_cast']} billion were written off. Without write-offs it would have grown {c['k_sin']} billion. For the total private sector, the {c['ct_fecha']} ratio would be {c['ct_aj']}% rather than {c['ct_of']}%.</p>
<h2>Next 12 months</h2>
<div class="tabla"><table><thead><tr>{''.join(f'<th>{h}</th>' for h in enc)}</tr></thead><tbody>{tabla}</tbody></table></div>
<p>The satellite model beats the AR(1) and the random walk out of sample (12-month error {c['rmse_sat']} pp vs {c['rmse_ar']} and {c['rmse_rw']}). <strong>In the baseline, delinquency keeps rising</strong> because the real loan rate stays near historical highs: it only falls if real rates fall, not merely if activity stabilizes. IFRS 9: {c['pesos']['base']}% baseline, {c['pesos']['adverso']}% adverse, {c['pesos']['favorable']}% favorable.</p>
<h2>Limits</h2>
<ul>
<li>Aggregate data (the credit bureau is not used); no data on informal-sector or non-bank-platform delinquency.</li>
<li>Lagged relationships, not strict causality; a single cycle of this kind: wide bands.</li>
<li>The channel model explains but does not forecast (12-month error {c['rmse_can']} pp vs {c['rmse_can_ar']} for an AR(1)). The long model depends on how 2010-2016 inflation is measured.</li>
</ul>
"""
    pie = {"es": f"Fuentes: BCRA, INDEC, IPCBA (GCBA), A3 Mercados. Código y metodología: {settings()['sitio']['repo_url']}",
           "en": f"Sources: BCRA, INDEC, IPCBA (Buenos Aires City), A3 Mercados. Code and methodology: {settings()['sitio']['repo_url']}"}[L]
    js = JS_TEMA % (json.dumps({k: list(v) for k, v in SERIES.items()}), json.dumps(TINTA))
    loc = f'<script src="{PLOTLY_ES}"></script>' if L == "es" else ""
    titulo = {"es": "Informe: mora de los hogares en Argentina", "en": "Report: household loan delinquency in Argentina"}[L]
    return f"""<!doctype html>
<html lang="{L}" data-theme="light">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<style>{CSS}{CSS_INFORME}</style>
<script src="{PLOTLY_JS}"></script>{loc}
</head>
<body><main>{cuerpo}<footer>{pie}</footer></main><script>{js}</script></body>
</html>
"""


def main() -> None:
    d = datos()
    (ROOT / "README.md").write_text(readme(d, "en"), encoding="utf-8")
    (ROOT / "README_ES.md").write_text(readme(d, "es"), encoding="utf-8")
    destino = ROOT / settings()["sitio"]["destino"]
    for L, rel in (("es", "informe.html"), ("en", "en/report.html")):
        f = destino / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(informe_html(d, L), encoding="utf-8")
    print(f"informe: README.md, README_ES.md, {destino}")


if __name__ == "__main__":
    main()
