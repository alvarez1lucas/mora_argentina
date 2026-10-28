"""Fase 7: sitio estático bilingüe (GitHub Pages) generado desde outputs/.

`python -m mora.sitio` escribe site/index.html (español) y site/en/index.html (inglés).

Todos los números y gráficos salen de outputs/: no hay cifras escritas a mano. Los gráficos son
Plotly (una sola escala por gráfico; las mediciones de precios se eligen con un menú dentro del
gráfico). Colores: paleta categórica de referencia, primeros tres slots (validados en todos los
pares, en modo claro y oscuro); el modo oscuro reasigna los mismos roles a sus pasos oscuros.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from mora.config import ROOT, path, settings

OUT = path("outputs")
PLOTLY_JS = "https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"
PLOTLY_ES = "https://cdn.jsdelivr.net/npm/plotly.js-locales@2.35.2/es.js"  # fechas de los ejes en español

# Roles de color: (claro, oscuro)
SERIES = {"s1": ("#2a78d6", "#3987e5"), "s2": ("#eb6834", "#d95926"), "s3": ("#1baf7a", "#199e70")}
TINTA = {"claro": {"texto": "#0b0b0b", "secundario": "#52514e", "grilla": "#e1e0d9", "eje": "#c3c2b7"},
         "oscuro": {"texto": "#f0efec", "secundario": "#c3c2b7", "grilla": "#2c2c2a", "eje": "#383835"}}
MEDICIONES = ("publico", "mix", "seleccionado")
ROL_MEDICION = {"publico": "s1", "mix": "s2", "seleccionado": "s3"}


# --------------------------------------------------------------------------- textos

T = {
    "es": {
        "lang": "es", "titulo": "Mora de los hogares en Argentina",
        "subtitulo": "Qué explica la suba de la mora de las familias 2024-2026 y qué puede pasar en los próximos 12 meses, con datos públicos y modelos validados fuera de muestra.",
        "otro_idioma": ("English", "en/index.html"),
        "med": {"publico": "Pública (INDEC)", "mix": "Mix", "seleccionado": "Seleccionada (canasta actualizada)"},
        "dec": ",", "mil": ".",
        "meses": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
    },
    "en": {
        "lang": "en", "titulo": "Household loan delinquency in Argentina",
        "subtitulo": "What explains the 2024-2026 rise in household non-performing loans and what may happen over the next 12 months, using public data and out-of-sample validated models.",
        "otro_idioma": ("Español", "../index.html"),
        "med": {"publico": "Official (INDEC)", "mix": "Mix", "seleccionado": "Selected (updated basket)"},
        "dec": ".", "mil": ",",
        "meses": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    },
}


def num(x: float, lang: str, d: int = 1) -> str:
    s = f"{x:,.{d}f}"
    if T[lang]["dec"] == ",":
        s = s.replace(",", "§").replace(".", ",").replace("§", ".")
    return s


def mes(fecha, lang: str) -> str:
    f = pd.Timestamp(fecha)
    return f"{T[lang]['meses'][f.month - 1]}-{str(f.year)[2:]}"


# --------------------------------------------------------------------------- datos

def _json(rel: str) -> dict:
    with open(OUT / rel, encoding="utf-8") as fh:
        return json.load(fh)


def _csv(rel: str, **kw) -> pd.DataFrame:
    return pd.read_csv(OUT / rel, **kw)


def datos() -> dict:
    d = {
        "desc": _json("descriptivo/resumen.json"),
        "ajuste": _json("ajuste/resumen_ajuste.json"),
        "rend": _json("rendimientos/resumen_rendimientos.json"),
        "esc": _json("escenarios/resumen_escenarios.json"),
        "canales": _csv("canales/aportes_por_canal.csv"),
        "familias": _csv("descriptivo/familias_por_linea.csv", parse_dates=["fecha"]),
        "castigos_total": _csv("descriptivo/mora_ajustada_castigos.csv", parse_dates=["fecha"]).dropna(),
        "castigos": _csv("ajuste/castigos_recientes.csv", parse_dates=["fecha"]),
        "cadena": _csv("ajuste/cadena_mensual.csv", index_col=0, parse_dates=True),
        "profundidad": _csv("ajuste/profundidad_credito_pbi.csv", index_col=0, parse_dates=True),
        "tasas": _csv("rendimientos/estado_vs_familias.csv", index_col=0, parse_dates=True),
        "tray": _csv("escenarios/trayectorias.csv", parse_dates=["fecha"]),
        "oos": _csv("modelo/evaluacion_fuera_de_muestra.csv"),
        "oos_canales": _csv("escenarios/validacion_canales.csv"),
        "panel_ml": _json("panel_ml/resumen_panel_ml.json"),
        "panel": _json("panel/resumen_panel.json"),
    }
    return d


# --------------------------------------------------------------------------- gráficos

def _layout(fig: go.Figure, lang: str, y_titulo: str, alto: int = 380) -> go.Figure:
    t = TINTA["claro"]
    fig.update_layout(
        height=alto, margin=dict(l=56, r=16, t=16, b=40), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', size=13, color=t["texto"]),
        hovermode="x unified", legend=dict(orientation="h", y=-0.18, x=0, traceorder="normal", font=dict(color=t["secundario"])),
        separators=T[lang]["dec"] + T[lang]["mil"],
    )
    fig.update_xaxes(showgrid=False, linecolor=t["eje"], tickcolor=t["eje"], tickfont=dict(color=t["secundario"]))
    fig.update_yaxes(gridcolor=t["grilla"], zeroline=False, linecolor=t["eje"], tickfont=dict(color=t["secundario"]),
                     title=dict(text=y_titulo, font=dict(color=t["secundario"], size=12)))
    return fig


def _linea(x, y, nombre: str, rol: str, **kw) -> go.Scatter:
    return go.Scatter(x=x, y=y, name=nombre, mode="lines", line=dict(color=SERIES[rol][0], width=2),
                      meta={"rol": rol}, hovertemplate="%{y:.1f}", **kw)


def _menu(fig: go.Figure, botones: list[tuple[str, list[bool]]]) -> None:
    fig.update_layout(updatemenus=[dict(
        type="dropdown", x=1, y=1.14, xanchor="right", yanchor="top", showactive=True,  # anclado a la derecha: no se sale en celular
        buttons=[dict(label=etq, method="update", args=[{"visible": vis}]) for etq, vis in botones],
    )], margin=dict(t=56))


def fig_mora(d: dict, lang: str) -> go.Figure:
    f = d["familias"]
    nombres = {"es": {"total": "Total familias", "personales": "Préstamos personales", "tarjetas_de_credito": "Tarjetas"},
               "en": {"total": "All household loans", "personales": "Personal loans", "tarjetas_de_credito": "Credit cards"}}[lang]
    fig = go.Figure()
    for linea, rol in (("total", "s1"), ("personales", "s2"), ("tarjetas_de_credito", "s3")):
        s = f[f["linea"] == linea]
        fig.add_trace(_linea(s["fecha"], s["ratio"], nombres[linea], rol))
    return _layout(fig, lang, {"es": "% de la cartera en situación irregular", "en": "% of portfolio non-performing"}[lang])


def fig_tasas(d: dict, lang: str) -> go.Figure:
    desde = settings()["ajuste"]["desde"]
    c, r = d["cadena"].loc[desde:], d["tasas"].loc[desde:]
    n = {"es": ("CFT préstamos personales", "Lo que rinde prestarle al Estado", "BADLAR (fondeo)"),
         "en": ("Personal loan all-in cost (CFT)", "Yield on lending to the State", "BADLAR (funding)")}[lang]
    fig = go.Figure([
        _linea(c.index, c["cft_tea_personales"], n[0], "s2"),
        _linea(r.index, r["tea_estado_3m"], n[1], "s1"),
        _linea(r.index, r["tea_badlar"], n[2], "s3"),
    ])
    return _layout(fig, lang, {"es": "Tasa efectiva anual (%)", "en": "Effective annual rate (%)"}[lang])


def fig_salario(d: dict, lang: str) -> go.Figure:
    c = d["cadena"]
    fig = go.Figure([_linea(c.index, c[f"salario_real_{m}"], T[lang]["med"][m], ROL_MEDICION[m]) for m in MEDICIONES])
    fig.add_hline(y=100, line=dict(color=TINTA["claro"]["eje"], width=1))
    return _layout(fig, lang, {"es": "Salario registrado real (nov-23 = 100)", "en": "Real registered wage (Nov-23 = 100)"}[lang])


ETIQUETA_CANAL = {
    "es": {"costo_financiero": "Costo financiero", "rendimiento_estado": "Lo que paga el Estado<br>(costo de oportunidad)",
           "prima_familias": "Prima de familias<br>sobre el Estado", "poder_compra": "Poder de compra<br>(salario real)",
           "cosecha_dilucion": "Ciclo de crédito", "ancla_cambiaria": "Ancla cambiaria<br>(tipo de cambio real)",
           "esterilizacion": "Absorción directa<br>(títulos + pases)"},
    "en": {"costo_financiero": "Financial cost", "rendimiento_estado": "What the State pays<br>(opportunity cost)",
           "prima_familias": "Household premium<br>over the State", "poder_compra": "Purchasing power<br>(real wage)",
           "cosecha_dilucion": "Credit cycle", "ancla_cambiaria": "FX anchor<br>(real exchange rate)",
           "esterilizacion": "Direct absorption<br>(securities + repos)"},
}


def fig_canales(d: dict, lang: str) -> go.Figure:
    a = d["canales"]
    variantes = {"base": {"es": "Costo total", "en": "Total cost"},
                 "costo_oportunidad": {"es": "Estado + prima", "en": "State + premium"}}
    fig, botones, k = go.Figure(), [], 0
    trazas = []
    for v in variantes:
        for m in MEDICIONES:
            s = a[(a["variante"] == v) & (a["deflactor"] == m)].sort_values("aporte_pp")
            etiquetas = [ETIQUETA_CANAL[lang][c] for c in s["canal"]]
            signif = ["p < 0,05" if p < 0.05 else "n.s." for p in s["pvalor"]] if lang == "es" else \
                     ["p < 0.05" if p < 0.05 else "n.s." for p in s["pvalor"]]
            fig.add_trace(go.Bar(
                x=s["aporte_pp"], y=etiquetas, orientation="h", meta={"rol": "s1"}, name="",
                marker=dict(color=SERIES["s1"][0], line=dict(width=0)), visible=(k == 0),
                error_x=dict(type="data", symmetric=False, array=s["aporte_pp_ic_sup"] - s["aporte_pp"],
                             arrayminus=s["aporte_pp"] - s["aporte_pp_ic_inf"], color=TINTA["claro"]["secundario"], thickness=1),
                customdata=list(zip(s["pvalor"], signif, s["aporte_pp_ic_inf"], s["aporte_pp_ic_sup"])),
                hovertemplate=("%{y}: %{x:+.1f} pp<br>IC 95%: %{customdata[2]:.1f} a %{customdata[3]:.1f}<br>p = %{customdata[0]:.3f} (%{customdata[1]})<extra></extra>"
                               if lang == "es" else
                               "%{y}: %{x:+.1f} pp<br>95% CI: %{customdata[2]:.1f} to %{customdata[3]:.1f}<br>p = %{customdata[0]:.3f} (%{customdata[1]})<extra></extra>"),
            ))
            trazas.append((variantes[v][lang], T[lang]["med"][m]))
            k += 1
    for i, (v, m) in enumerate(trazas):
        botones.append((f"{v} · {m}", [j == i for j in range(len(trazas))]))
    fig.add_vline(x=0, line=dict(color=TINTA["claro"]["eje"], width=1))
    _layout(fig, lang, "", alto=420)
    fig.update_layout(hovermode="closest", showlegend=False, bargap=0.35)
    fig.update_xaxes(title=dict(text={"es": "Aporte (pp de mora)", "en": "Contribution (pp)"}[lang]),
                     showgrid=True, gridcolor=TINTA["claro"]["grilla"])
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", automargin=True)
    _menu(fig, botones)
    return fig


def fig_castigos(d: dict, lang: str) -> go.Figure:
    k = d["castigos"]
    n = {"es": ("Variación observada", "Sin castigos (estimado)"), "en": ("Observed change", "Without write-offs (estimated)")}[lang]
    x = [mes(f, lang) for f in k["fecha"]]
    fig = go.Figure([
        go.Bar(x=x, y=k["var_irregular_familias_real"] / 1000, name=n[0], meta={"rol": "s1"}, marker=dict(color=SERIES["s1"][0]),
               hovertemplate="%{y:,.0f}"),
        go.Bar(x=x, y=k["irregular_familias_sin_castigos_real"] / 1000, name=n[1], meta={"rol": "s2"}, marker=dict(color=SERIES["s2"][0]),
               hovertemplate="%{y:,.0f}"),
    ])
    _layout(fig, lang, {"es": "Miles de millones de pesos constantes", "en": "Billions of constant pesos"}[lang])
    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.08)
    return fig


def fig_profundidad(d: dict, lang: str) -> go.Figure:
    p = d["profundidad"].loc["2016-01-01":]
    n = {"es": ("Crédito al sector privado en pesos", "Exposición de los bancos al Estado (títulos + pases)"),
         "en": ("Peso credit to the private sector", "Bank exposure to the State (securities + repos)")}[lang]
    fig = go.Figure([_linea(p.index, p["credito_privado_mn_pbi"], n[0], "s1"),
                     _linea(p.index, p["exposicion_estado_mn_pbi"], n[1], "s2")])
    return _layout(fig, lang, {"es": "% del PBI", "en": "% of GDP"}[lang])


def fig_escenarios(d: dict, lang: str) -> go.Figure:
    tr = d["tray"][d["tray"]["modelo"] == "satelite"]
    hist = d["familias"][(d["familias"]["linea"] == "total") & (d["familias"]["fecha"] >= settings()["ajuste"]["desde"])]
    n = {"es": {"hist": "Observado", "base": "Base", "adverso": "Adverso", "favorable": "Favorable", "banda": "Base: 90% de las simulaciones"},
         "en": {"hist": "Observed", "base": "Baseline", "adverso": "Adverse", "favorable": "Favorable", "banda": "Baseline: 90% of simulations"}}[lang]
    fig, botones, grupos = go.Figure(), [], []
    for m in MEDICIONES:
        t = tr[tr["deflactor"] == m]
        ini = len(fig.data)
        b = t[t["escenario"] == "base"]
        fig.add_trace(go.Scatter(x=b["fecha"], y=b["p95"], mode="lines", line=dict(width=0), showlegend=False, legendrank=900,
                                 hoverinfo="skip", visible=(m == MEDICIONES[0])))
        fig.add_trace(go.Scatter(x=b["fecha"], y=b["p05"], mode="lines", line=dict(width=0), fill="tonexty",
                                 fillcolor="rgba(42,120,214,0.16)", meta={"rol": "s1", "alfa": 0.16}, name=n["banda"], legendrank=900,
                                 hoverinfo="skip", visible=(m == MEDICIONES[0])))
        fig.add_trace(go.Scatter(x=hist["fecha"], y=hist["ratio"], name=n["hist"], mode="lines", meta={"rol": "tinta"},
                                 line=dict(color=TINTA["claro"]["texto"], width=2), hovertemplate="%{y:.1f}", visible=(m == MEDICIONES[0]),
                                 legendrank=100))
        for e, rol in (("base", "s1"), ("adverso", "s2"), ("favorable", "s3")):
            s = t[t["escenario"] == e]
            x = [hist["fecha"].iloc[-1], *s["fecha"]]
            y = [hist["ratio"].iloc[-1], *s["central"]]
            fig.add_trace(_linea(x, y, n[e], rol, visible=(m == MEDICIONES[0]),
                                 legendrank={"base": 200, "adverso": 300, "favorable": 400}[e]))
        grupos.append((T[lang]["med"][m], range(ini, len(fig.data))))
    total = len(fig.data)
    for etq, rango in grupos:
        botones.append((etq, [i in rango for i in range(total)]))
    _layout(fig, lang, {"es": "Mora de familias (%)", "en": "Household NPL ratio (%)"}[lang], alto=420)
    _menu(fig, botones)
    return fig


# --------------------------------------------------------------------------- página

def _div(fig: go.Figure, id_: str, lang: str) -> str:
    return pio.to_html(fig, include_plotlyjs=False, full_html=False, div_id=id_,
                       config={"displayModeBar": False, "responsive": True, "locale": lang})


def _tile(valor: str, etiqueta: str, nota: str = "") -> str:
    nota_html = f'<div class="tile-nota">{nota}</div>' if nota else ""
    return f'<div class="tile"><div class="tile-valor">{valor}</div><div class="tile-etq">{etiqueta}</div>{nota_html}</div>'


def _tabla(encabezado: list[str], filas: list[list[str]]) -> str:
    th = "".join(f"<th>{h}</th>" for h in encabezado)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in f) + "</tr>" for f in filas)
    return f'<div class="tabla"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def contenido(d: dict, lang: str) -> str:
    """Secciones del sitio. Cada número sale de `d` (outputs/)."""
    L = lang
    desc, aj, rend, esc = d["desc"], d["ajuste"], d["rend"], d["esc"]
    a = d["canales"]
    pp = lambda x, k=1: num(x, L, k)  # noqa: E731

    def aporte(v, m, canal, campo="aporte_pp"):
        return float(a[(a["variante"] == v) & (a["deflactor"] == m) & (a["canal"] == canal)][campo].iloc[0])

    def rango(v, canal):
        vals = [aporte(v, m, canal) for m in MEDICIONES]
        return f"{pp(min(vals))}–{pp(max(vals))}"

    def pv(v, canal):
        vals = [aporte(v, m, canal, "pvalor") for m in MEDICIONES]
        return f"{num(min(vals), L, 3)}–{num(max(vals), L, 3)}"

    sat = {m: esc[f"satelite_{m}"] for m in MEDICIONES}
    s_pub = sat["publico"]
    base_pub = s_pub["mora_fin"]["base"]
    ct = d["castigos_total"].iloc[-1]
    k = d["castigos"].iloc[-2:]
    oos = d["oos"]
    o12 = oos[(oos["especificacion"] == "base") & (oos["muestra"] == "larga") & (oos["h"] == 12)].set_index("modelo")
    oc12 = d["oos_canales"][d["oos_canales"]["h"] == 12].set_index("modelo")
    res_can = _json("canales/resumen_canales.json")["base_publico"]
    sal = d["cadena"][[f"salario_real_{m}" for m in MEDICIONES]].dropna().iloc[-1]
    prof = d["profundidad"]
    feb24 = prof.loc["2024-02-01"]
    r_ini, r_ult = rend["inicio"], rend["ultimo"]
    pr = rend["promedios_anuales"]

    if L == "es":
        hero = (
            _tile(f"{pp(desc['mora_familias'])}%", f"Mora de familias, {mes(desc['ultimo_dato'], L)}",
                  f"Máximo de la serie (desde 2010): {pp(desc['maximo_de_la_serie'])}% en {mes(desc['fecha_maximo'], L)}")
            + _tile(f"{pp(aj['mora_familias']['inicio'])}%", f"Mora de familias, {mes(aj['ventana'][0], L)}", "Antes de la devaluación de dic-23")
            + _tile(f"+{pp(desc['efecto_numerador_12m'])} pp", "Suba en 12 meses explicada por más deuda impaga",
                    f"Efecto del denominador: {pp(desc['efecto_denominador_12m'], 2)} pp")
            + _tile(f"{pp(base_pub['central'])}%", f"Escenario base, {mes(s_pub['fin'], L)}",
                    f"90% de las simulaciones: {pp(base_pub['p05'])}%–{pp(base_pub['p95'])}%")
        )
        secciones = f"""
<section><h2>1. Qué pasó</h2>
<p>La mora de las familias (cartera en situación 3, 4 y 5 sobre el total, Informe sobre Bancos del BCRA) pasó de {pp(aj['mora_familias']['inicio'])}% en {mes(aj['ventana'][0], L)} a {pp(desc['mora_familias'])}% en {mes(desc['ultimo_dato'], L)}. En préstamos personales es {pp(desc['mora_por_linea']['personales'])}% y en tarjetas {pp(desc['mora_por_linea']['tarjetas_de_credito'])}%.</p>
{_div(fig_mora(d, L), 'g-mora', L)}
<p><strong>No es un efecto de que se achicó la cartera.</strong> De la suba de los últimos 12 meses, +{pp(desc['efecto_numerador_12m'])} pp se explican porque creció la deuda impaga en términos reales y {pp(desc['efecto_denominador_12m'], 2)} pp por el cambio del stock de préstamos.</p>
</section>

<section><h2>2. La cadena: de la política monetaria a la cuota</h2>
<p>Para bajar la inflación, el programa ancló el dólar y absorbió pesos con tasas altas. Los bancos encontraron más rentable prestarle al Estado que a las familias: en {mes(feb24.name, L)} su exposición al Estado era {pp(feb24['exposicion_estado_mn_pbi'])}% del PBI, contra {pp(feb24['credito_privado_mn_pbi'])}% de crédito al sector privado.</p>
{_div(fig_profundidad(d, L), 'g-prof', L)}
<p>Cuando el crédito se reactivó, las familias tomaron deuda a tasas altas justo cuando el salario real no se recuperaba. El salario registrado real está {pp(100 - sal['salario_real_publico'])}% abajo de nov-23 con la medición oficial, {pp(100 - sal['salario_real_mix'])}% con la mix y {pp(100 - sal['salario_real_seleccionado'])}% con la canasta actualizada (ponderadores ENGHo 2017/18).</p>
{_div(fig_salario(d, L), 'g-salario', L)}
<p><strong>Lo que rinde prestarle al Estado pone un piso a la tasa de las familias.</strong> Como no hay una serie pública de rendimientos de Lecap, se calcula lo que los bancos efectivamente ganaron con títulos públicos y pases en pesos (cuentas de resultados de cada entidad, reexpresadas por inflación). En 2025 el Estado les rindió en promedio {pp(pr['2025']['tea_estado_3m'])}% anual, por encima de la BADLAR ({pp(pr['2025']['tea_badlar'])}%). Y la tasa de préstamos personales nuevos se quedó en {pp(pr['2025']['tea_personales_nuevos'])}%: una prima de {pp(pr['2025']['prima_personales_sobre_estado_pp'])} pp sobre el Estado.</p>
{_div(fig_tasas(d, L), 'g-tasas', L)}
</section>

<section><h2>3. Cuánto pesó cada canal</h2>
<p>Ecuación de la variación mensual de la mora (logit) con un regresor por canal, rezagos elegidos por BIC y descomposición histórica contrafáctica: el aporte de cada canal es la mora simulada con los datos reales menos la simulada con ese canal en un valor neutral. Ventana: del mínimo de {mes(res_can['ventana'][0], L)} ({pp(res_can['mora_inicio'])}%) a {mes(res_can['ventana'][1], L)} ({pp(res_can['mora_fin'])}%). Las barras muestran el intervalo del 95%. Usá el menú para cambiar la medición de precios y la forma de medir el costo financiero.</p>
{_div(fig_canales(d, L), 'g-canales', L)}
<ul>
<li><strong>El costo financiero es el canal dominante</strong> en las tres mediciones: +{rango('base', 'costo_financiero')} pp (p = {pv('base', 'costo_financiero')}).</li>
<li>Al separarlo, <strong>lo que paga el Estado aporta +{rango('costo_oportunidad', 'rendimiento_estado')} pp y es significativo</strong> (p = {pv('costo_oportunidad', 'rendimiento_estado')}). La prima propia de las familias suma +{rango('costo_oportunidad', 'prima_familias')} pp, pero no es significativa. La esterilización actúa por el piso que pone a las tasas, no por la BADLAR.</li>
<li><strong>El poder de compra pesa más cuanto más realista es la medición de precios</strong>: en la ecuación base aporta +{pp(aporte('base', 'publico', 'poder_compra'))} pp con la oficial (p = {num(aporte('base', 'publico', 'poder_compra', 'pvalor'), L, 3)}) y +{pp(aporte('base', 'seleccionado', 'poder_compra'))} pp con la canasta actualizada (p = {num(aporte('base', 'seleccionado', 'poder_compra', 'pvalor'), L, 3)}).</li>
<li>Ancla cambiaria y absorción directa: sin significancia estable entre especificaciones.</li>
</ul>
</section>

<section><h2>4. La baja reciente es, en buena parte, contable</h2>
<p>En {mes(k['fecha'].iloc[0], L)} y {mes(k['fecha'].iloc[1], L)} la deuda irregular de las familias casi no creció ({pp(k['var_irregular_familias_real'].iloc[0] / 1000, 0)} y {pp(k['var_irregular_familias_real'].iloc[1] / 1000, 0)} mil millones de pesos constantes). Pero en esos meses los bancos castigaron (pasaron a pérdida) unos {pp(k['castigos_familias_estimado_real'].iloc[0] / 1000, 0)} y {pp(k['castigos_familias_estimado_real'].iloc[1] / 1000, 0)} mil millones atribuibles a familias. Sin castigos, la deuda irregular habría crecido {pp(k['irregular_familias_sin_castigos_real'].iloc[0] / 1000, 0)} y {pp(k['irregular_familias_sin_castigos_real'].iloc[1] / 1000, 0)} mil millones.</p>
{_div(fig_castigos(d, L), 'g-castigos', L)}
<p>Para el sector privado total, sumando los castigos de los últimos meses al numerador, la mora de {mes(ct['fecha'], L)} sería {pp(ct['ratio_ajustado'])}% en lugar de {pp(ct['ratio_oficial'])}%. Los castigos de familias se estiman con la participación de las familias en la deuda irregular, porque el dato publicado es del total. Las refinanciaciones no se pueden separar con datos públicos.</p>
</section>

<section><h2>5. Los próximos 12 meses</h2>
<p>Proyección con el modelo satélite (muestra 2010+), que fuera de muestra le gana al paseo aleatorio y al AR(1): a 12 meses su error cuadrático medio es {pp(o12.loc['satelite', 'rmse'], 2)} pp, contra {pp(o12.loc['ar1', 'rmse'], 2)} del AR(1) y {pp(o12.loc['paseo_aleatorio', 'rmse'], 2)} del paseo aleatorio. Los supuestos salen de la historia de cada variable: en el base las tasas reales se mantienen y las variaciones interanuales vuelven a cero; en el adverso y el favorable se aplica el cambio a 12 meses del peor y del mejor 10% de los años desde 2010.</p>
{_div(fig_escenarios(d, L), 'g-esc', L)}
{_tabla(['Medición', 'Muestra', 'Base', 'Adverso', 'Favorable', 'Ponderado NIIF 9', 'Prob. de superar el nivel actual (base)'],
        [[T[L]['med'][m], {'larga': '2010+', 'limpia': '2017+'}[sat[m]['muestra']],
          f"{pp(sat[m]['mora_fin']['base']['central'])}%", f"{pp(sat[m]['mora_fin']['adverso']['central'])}%",
          f"{pp(sat[m]['mora_fin']['favorable']['central'])}%", f"{pp(sat[m]['niif9']['mora_ponderada'])}%",
          f"{pp(100 * sat[m]['prob_mora_fin_supera_origen']['base'], 0)}%"] for m in MEDICIONES])}
<p class="nota">Ponderado NIIF 9: {pp(100 * s_pub['niif9']['pesos']['base'], 0)}% base, {pp(100 * s_pub['niif9']['pesos']['adverso'], 0)}% adverso, {pp(100 * s_pub['niif9']['pesos']['favorable'], 0)}% favorable, promediando las simulaciones. Con la medición seleccionada, ninguna especificación de la muestra larga respeta los signos esperados (su inflación 2010-2016 vuelve muy negativas las tasas reales de esos años), así que se proyecta con la muestra 2017+, que fuera de muestra no le gana al AR(1). El modelo de canales sirve para explicar, no para proyectar: a 12 meses su error es {pp(oc12.loc['satelite', 'rmse'], 2)} pp, contra {pp(oc12.loc['ar1', 'rmse'], 2)} del AR(1).</p>
</section>
"""
    else:
        hero = (
            _tile(f"{pp(desc['mora_familias'])}%", f"Household NPL ratio, {mes(desc['ultimo_dato'], L)}",
                  f"Series high (since 2010): {pp(desc['maximo_de_la_serie'])}% in {mes(desc['fecha_maximo'], L)}")
            + _tile(f"{pp(aj['mora_familias']['inicio'])}%", f"Household NPL ratio, {mes(aj['ventana'][0], L)}", "Before the Dec-23 devaluation")
            + _tile(f"+{pp(desc['efecto_numerador_12m'])} pp", "12-month rise explained by more unpaid debt",
                    f"Denominator effect: {pp(desc['efecto_denominador_12m'], 2)} pp")
            + _tile(f"{pp(base_pub['central'])}%", f"Baseline scenario, {mes(s_pub['fin'], L)}",
                    f"90% of simulations: {pp(base_pub['p05'])}%–{pp(base_pub['p95'])}%")
        )
        secciones = f"""
<section><h2>1. What happened</h2>
<p>The household non-performing loan ratio (situations 3, 4 and 5 over total, BCRA banking report) rose from {pp(aj['mora_familias']['inicio'])}% in {mes(aj['ventana'][0], L)} to {pp(desc['mora_familias'])}% in {mes(desc['ultimo_dato'], L)}. It is {pp(desc['mora_por_linea']['personales'])}% for personal loans and {pp(desc['mora_por_linea']['tarjetas_de_credito'])}% for credit cards.</p>
{_div(fig_mora(d, L), 'g-mora', L)}
<p><strong>It is not a shrinking-portfolio effect.</strong> Of the 12-month rise, +{pp(desc['efecto_numerador_12m'])} pp comes from real growth in unpaid debt and {pp(desc['efecto_denominador_12m'], 2)} pp from the change in the loan stock.</p>
</section>

<section><h2>2. The chain: from monetary policy to the monthly payment</h2>
<p>To bring inflation down, the program anchored the exchange rate and absorbed pesos with high rates. Banks found it more profitable to lend to the State than to households: in {mes(feb24.name, L)} their exposure to the State was {pp(feb24['exposicion_estado_mn_pbi'])}% of GDP, against {pp(feb24['credito_privado_mn_pbi'])}% for private credit.</p>
{_div(fig_profundidad(d, L), 'g-prof', L)}
<p>When credit came back, households borrowed at high rates just as real wages failed to recover. The real registered wage is {pp(100 - sal['salario_real_publico'])}% below Nov-23 with the official measure, {pp(100 - sal['salario_real_mix'])}% with the mix and {pp(100 - sal['salario_real_seleccionado'])}% with the updated basket (ENGHo 2017/18 weights).</p>
{_div(fig_salario(d, L), 'g-salario', L)}
<p><strong>What lending to the State pays sets a floor for household rates.</strong> With no public series of Treasury bill (Lecap) yields, the measure is what banks actually earned on peso government securities and repos (income accounts of each bank, restated for inflation). In 2025 the State paid them {pp(pr['2025']['tea_estado_3m'])}% a year on average, above BADLAR ({pp(pr['2025']['tea_badlar'])}%). New personal loans stayed at {pp(pr['2025']['tea_personales_nuevos'])}%, a {pp(pr['2025']['prima_personales_sobre_estado_pp'])} pp premium over the State.</p>
{_div(fig_tasas(d, L), 'g-tasas', L)}
</section>

<section><h2>3. How much each channel weighed</h2>
<p>Equation for the monthly change in the (logit) NPL ratio with one regressor per channel, BIC-selected lags, and a counterfactual historical decomposition: each channel's contribution is simulated delinquency with actual data minus simulated delinquency with that channel held neutral. Window: from the {mes(res_can['ventana'][0], L)} low ({pp(res_can['mora_inicio'])}%) to {mes(res_can['ventana'][1], L)} ({pp(res_can['mora_fin'])}%). Bars show the 95% interval. Use the menu to switch the price measure and how the financial cost is measured.</p>
{_div(fig_canales(d, L), 'g-canales', L)}
<ul>
<li><strong>Financial cost is the dominant channel</strong> under all three measures: +{rango('base', 'costo_financiero')} pp (p = {pv('base', 'costo_financiero')}).</li>
<li>Split in two, <strong>what the State pays contributes +{rango('costo_oportunidad', 'rendimiento_estado')} pp and is significant</strong> (p = {pv('costo_oportunidad', 'rendimiento_estado')}). The household-specific premium adds +{rango('costo_oportunidad', 'prima_familias')} pp but is not significant. Sterilization works through the floor it sets on rates, not through BADLAR.</li>
<li><strong>Purchasing power weighs more the more realistic the price measure</strong>: in the base equation it contributes +{pp(aporte('base', 'publico', 'poder_compra'))} pp with the official index (p = {num(aporte('base', 'publico', 'poder_compra', 'pvalor'), L, 3)}) and +{pp(aporte('base', 'seleccionado', 'poder_compra'))} pp with the updated basket (p = {num(aporte('base', 'seleccionado', 'poder_compra', 'pvalor'), L, 3)}).</li>
<li>FX anchor and direct absorption: no stable significance across specifications.</li>
</ul>
</section>

<section><h2>4. The recent leveling-off is largely an accounting effect</h2>
<p>In {mes(k['fecha'].iloc[0], L)} and {mes(k['fecha'].iloc[1], L)} household non-performing debt barely grew ({pp(k['var_irregular_familias_real'].iloc[0] / 1000, 0)} and {pp(k['var_irregular_familias_real'].iloc[1] / 1000, 0)} billion constant pesos). But in those months banks wrote off about {pp(k['castigos_familias_estimado_real'].iloc[0] / 1000, 0)} and {pp(k['castigos_familias_estimado_real'].iloc[1] / 1000, 0)} billion attributable to households. Without write-offs, non-performing debt would have grown {pp(k['irregular_familias_sin_castigos_real'].iloc[0] / 1000, 0)} and {pp(k['irregular_familias_sin_castigos_real'].iloc[1] / 1000, 0)} billion.</p>
{_div(fig_castigos(d, L), 'g-castigos', L)}
<p>For the total private sector, adding recent write-offs back to the numerator, the {mes(ct['fecha'], L)} ratio would be {pp(ct['ratio_ajustado'])}% instead of {pp(ct['ratio_oficial'])}%. Household write-offs are estimated using households' share of non-performing debt, since the published figure is for the total. Refinancings cannot be separated with public data.</p>
</section>

<section><h2>5. The next 12 months</h2>
<p>Projection with the satellite model (2010+ sample), which beats both a random walk and an AR(1) out of sample: at 12 months its root mean squared error is {pp(o12.loc['satelite', 'rmse'], 2)} pp, against {pp(o12.loc['ar1', 'rmse'], 2)} for the AR(1) and {pp(o12.loc['paseo_aleatorio', 'rmse'], 2)} for the random walk. Assumptions come from each variable's history: in the baseline, real rates stay put and year-on-year changes fade to zero; the adverse and favorable cases apply the 12-month change of the worst and best 10% of years since 2010.</p>
{_div(fig_escenarios(d, L), 'g-esc', L)}
{_tabla(['Price measure', 'Sample', 'Baseline', 'Adverse', 'Favorable', 'IFRS 9 weighted', 'Prob. of exceeding current level (baseline)'],
        [[T[L]['med'][m], {'larga': '2010+', 'limpia': '2017+'}[sat[m]['muestra']],
          f"{pp(sat[m]['mora_fin']['base']['central'])}%", f"{pp(sat[m]['mora_fin']['adverso']['central'])}%",
          f"{pp(sat[m]['mora_fin']['favorable']['central'])}%", f"{pp(sat[m]['niif9']['mora_ponderada'])}%",
          f"{pp(100 * sat[m]['prob_mora_fin_supera_origen']['base'], 0)}%"] for m in MEDICIONES])}
<p class="nota">IFRS 9 weighting: {pp(100 * s_pub['niif9']['pesos']['base'], 0)}% baseline, {pp(100 * s_pub['niif9']['pesos']['adverso'], 0)}% adverse, {pp(100 * s_pub['niif9']['pesos']['favorable'], 0)}% favorable, averaging the simulations. With the selected measure no long-sample specification has the expected signs (its 2010-2016 inflation makes real rates in those years deeply negative), so the projection uses the 2017+ sample, which does not beat the AR(1) out of sample. The channel model explains rather than forecasts: its 12-month error is {pp(oc12.loc['satelite', 'rmse'], 2)} pp against {pp(oc12.loc['ar1', 'rmse'], 2)} for the AR(1).</p>
</section>
"""
    return hero, secciones


LIMITACIONES = {
    "es": [
        "Son datos agregados: no se observa a cada deudor. La Central de Deudores no se usa, por privacidad.",
        "La mora del sector informal y de las plataformas no bancarias (Mercado Pago, Ualá) no está en estos datos; sus tasas sí aparecen en el relevamiento de transparencia.",
        "Las relaciones estimadas no son causales en sentido estricto. El rezago de los regresores mitiga, pero no elimina, la causalidad inversa (por ejemplo, el spread también sube porque sube la mora).",
        "Hay un solo ciclo de ajuste con estas características y la muestra limpia tiene 77 meses: las bandas son anchas y se reportan siempre.",
        "Los castigos de familias y el PBI de los últimos trimestres son estimaciones (están marcadas en los datos).",
        "La medición seleccionada es una propuesta propia: cambia los ponderadores del índice (ENGHo 2017/18), no la medición de precios del INDEC.",
        "No hay series públicas de cheques rechazados recientes, embargos de ARCA ni stock de refinanciaciones.",
    ],
    "en": [
        "Data are aggregates: individual borrowers are not observed. The credit bureau (Central de Deudores) is not used, for privacy reasons.",
        "Delinquency in the informal sector and on non-bank platforms (Mercado Pago, Ualá) is not in these data; their rates do appear in the transparency survey.",
        "Estimated relationships are not strictly causal. Lagged regressors mitigate but do not remove reverse causality (e.g., spreads also rise because delinquency rises).",
        "There is a single adjustment cycle of this kind and the clean sample has 77 months: bands are wide and always reported.",
        "Household write-offs and GDP for the latest quarters are estimates (flagged in the data).",
        "The selected price measure is our own proposal: it changes the index weights (ENGHo 2017/18), not INDEC's price collection.",
        "There are no recent public series for bounced checks, tax-agency (ARCA) garnishments or the stock of refinanced loans.",
    ],
}

CSS = """
:root{color-scheme:light;--bg:#f9f9f7;--surface:#fcfcfb;--text:#0b0b0b;--text2:#52514e;--muted:#898781;--line:#e1e0d9;--accent:#2a78d6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#0d0d0d;--surface:#1a1a19;--text:#f0efec;--text2:#c3c2b7;--muted:#898781;--line:#2c2c2a;--accent:#3987e5}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#0d0d0d;--surface:#1a1a19;--text:#f0efec;--text2:#c3c2b7;--muted:#898781;--line:#2c2c2a;--accent:#3987e5}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:920px;margin:0 auto;padding:24px 16px 64px}
header{display:flex;justify-content:space-between;align-items:baseline;gap:16px;flex-wrap:wrap}
h1{font-size:2rem;line-height:1.2;margin:8px 0}
h2{font-size:1.35rem;margin:48px 0 8px}
.sub{color:var(--text2);max-width:720px;margin:0 0 24px}
a{color:var(--accent)}
.idioma{font-size:.9rem}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:16px}
.tile-valor{font-size:1.9rem;font-weight:600;line-height:1.1}
.tile-etq{color:var(--text2);font-size:.92rem;margin-top:6px}
.tile-nota{color:var(--muted);font-size:.82rem;margin-top:6px}
section .js-plotly-plot,section .plotly-graph-div{background:var(--surface);border:1px solid var(--line);border-radius:8px;margin:12px 0}
.tabla{overflow-x:auto;margin:12px 0}
table{border-collapse:collapse;width:100%;font-size:.92rem;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line)}
th{color:var(--text2);font-weight:600}
.nota{color:var(--text2);font-size:.9rem}
footer{color:var(--muted);font-size:.85rem;margin-top:48px;border-top:1px solid var(--line);padding-top:16px}
"""

# Reasigna los roles de color de Plotly al tema activo (claro u oscuro)
JS_TEMA = """
const SERIES=%s, TINTA=%s;
function hexA(h,a){const n=parseInt(h.slice(1),16);return `rgba(${n>>16&255},${n>>8&255},${n&255},${a})`}
function aplicarTema(){
  const t=document.documentElement.dataset.theme, osc=t?t==='dark':matchMedia('(prefers-color-scheme: dark)').matches;
  const k=osc?1:0, ink=TINTA[osc?'oscuro':'claro'];
  document.querySelectorAll('.js-plotly-plot').forEach(g=>{
    const idx=[],line=[],marker=[],fill=[];
    g.data.forEach((tr,i)=>{const r=tr.meta&&tr.meta.rol;if(!r)return;
      const c=r==='tinta'?ink.texto:SERIES[r][k];idx.push(i);line.push(c);marker.push(c);
      fill.push(tr.meta.alfa?hexA(c,tr.meta.alfa):tr.fillcolor||null)});
    if(idx.length)Plotly.restyle(g,{'line.color':line,'marker.color':marker,'fillcolor':fill},idx);
    Plotly.relayout(g,{'font.color':ink.texto,'legend.font.color':ink.secundario,
      'xaxis.tickfont.color':ink.secundario,'yaxis.tickfont.color':ink.secundario,
      'yaxis.title.font.color':ink.secundario,'xaxis.title.font.color':ink.secundario,
      'yaxis.gridcolor':ink.grilla,'xaxis.linecolor':ink.eje,'yaxis.linecolor':ink.eje});
  });
}
window.addEventListener('load',aplicarTema);
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',aplicarTema);
"""


def pagina(d: dict, lang: str) -> str:
    t = T[lang]
    hero, secciones = contenido(d, lang)
    repo = settings()["sitio"]["repo_url"]
    lim = "".join(f"<li>{x}</li>" for x in LIMITACIONES[lang])
    fecha = mes(d["desc"]["ultimo_dato"], lang)
    tit_lim = {"es": "Lo que estos datos no permiten afirmar", "en": "What these data cannot tell us"}[lang]
    pie = {"es": f"Datos al {fecha}. Fuentes: BCRA (Informe sobre Bancos, Información de Entidades Financieras, API de estadísticas), INDEC, GCBA (IPCBA), A3 Mercados. Código, metodología y datos procesados: <a href=\"{repo}\">{repo}</a>. Se actualiza todas las semanas con GitHub Actions.",
           "en": f"Data as of {fecha}. Sources: BCRA (banking report, financial institutions data, statistics API), INDEC, Buenos Aires City (IPCBA), A3 Mercados. Code, methodology and processed data: <a href=\"{repo}\">{repo}</a>. Updated weekly with GitHub Actions."}[lang]
    js = JS_TEMA % (json.dumps({k: list(v) for k, v in SERIES.items()}), json.dumps(TINTA))
    return f"""<!doctype html>
<html lang="{t['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t['titulo']}</title>
<meta name="description" content="{t['subtitulo']}">
<style>{CSS}</style>
<script src="{PLOTLY_JS}"></script>
{f'<script src="{PLOTLY_ES}"></script>' if lang == "es" else ""}
</head>
<body>
<main>
<header><h1>{t['titulo']}</h1><a class="idioma" href="{t['otro_idioma'][1]}">{t['otro_idioma'][0]}</a></header>
<p class="sub">{t['subtitulo']}</p>
<div class="tiles">{hero}</div>
{secciones}
<section><h2>{tit_lim}</h2><ul>{lim}</ul></section>
<footer>{pie}</footer>
</main>
<script>{js}</script>
</body>
</html>
"""


def main() -> None:
    d = datos()
    destino = ROOT / settings()["sitio"]["destino"]
    for lang, rel in (("es", "index.html"), ("en", "en/index.html")):
        f = destino / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(pagina(d, lang), encoding="utf-8")
    print(f"sitio: {destino}")


if __name__ == "__main__":
    main()
