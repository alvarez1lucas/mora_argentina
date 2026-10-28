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
PLOTLY_ES = "https://cdn.jsdelivr.net/npm/plotly.js@2.35.2/dist/plotly-locale-es.js"  # fechas de los ejes en español

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
        "cadena_e1": _csv("cadena/etapa1_tasa.csv"),
        "cadena_e2": _csv("cadena/etapa2_mora.csv"),
        "cadena_partes": _csv("cadena/etapa2_partes_de_la_tasa.csv"),
        "cadena_res": _json("cadena/resumen_cadena.json"),
        "nb_exp": _csv("no_bancario/exposicion_estado_ampliada.csv", index_col=0, parse_dates=True),
        "nb": _json("no_bancario/resumen_no_bancario.json"),
        "dec": _json("decision/resumen_decision.json"),
        "cortes": _csv("decision/cortes_aprobacion.csv"),
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
    kw.setdefault("mode", "lines")
    return go.Scatter(x=x, y=y, name=nombre, line=dict(color=SERIES[rol][0], width=2),
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


ETIQUETA = {
    "es": {"estado": "Lo que paga el Estado<br>(piso: esterilización)", "prima": "Prima del banco<br>sobre el Estado",
           "impuestos": "IVA sobre<br>los intereses", "poder_compra": "Poder de compra<br>(salario real)",
           "cosecha_dilucion": "Ciclo de crédito", "ancla_cambiaria": "Ancla cambiaria<br>(tipo de cambio real)"},
    "en": {"estado": "What the State pays<br>(floor: sterilization)", "prima": "Bank premium<br>over the State",
           "impuestos": "VAT on<br>interest", "poder_compra": "Purchasing power<br>(real wage)",
           "cosecha_dilucion": "Credit cycle", "ancla_cambiaria": "FX anchor<br>(real exchange rate)"},
}
PARTES = ("estado", "prima", "impuestos")


def _barras_h(fig: go.Figure, lang: str, x_titulo: str, alto: int) -> None:
    fig.add_vline(x=0, line=dict(color=TINTA["claro"]["eje"], width=1))
    _layout(fig, lang, "", alto=alto)
    fig.update_layout(hovermode="closest", bargap=0.35, margin=dict(b=110), legend=dict(y=-0.3, yanchor="top"))
    fig.update_xaxes(title=dict(text=x_titulo), showgrid=True, gridcolor=TINTA["claro"]["grilla"])
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", automargin=True, autorange="reversed")


def fig_etapa1(d: dict, lang: str) -> go.Figure:
    """Etapa 1: cuánto subió cada parte de la tasa real del CFT sobre su promedio previo."""
    e1 = d["cadena_e1"]
    fig, botones = go.Figure(), []
    for i, m in enumerate(MEDICIONES):
        s = e1[e1["deflactor"] == m].set_index("parte").loc[list(PARTES)]
        fig.add_trace(go.Bar(
            x=s["exceso_pp"], y=[ETIQUETA[lang][p] for p in PARTES], orientation="h", name="", meta={"rol": "s1"},
            marker=dict(color=SERIES["s1"][0], line=dict(width=0)), visible=(i == 0),
            customdata=list(zip(s["promedio_previo_pp"], s["promedio_ventana_pp"], s["peso_en_suba_tasa_pct"])),
            hovertemplate=("%{y}: %{x:+.1f} pp de tasa real<br>Antes: %{customdata[0]:.1f} · en la ventana: %{customdata[1]:.1f}<br>%{customdata[2]:.0f}% de la suba de la tasa<extra></extra>"
                           if lang == "es" else
                           "%{y}: %{x:+.1f} pp of real rate<br>Before: %{customdata[0]:.1f} · in the window: %{customdata[1]:.1f}<br>%{customdata[2]:.0f}% of the rate increase<extra></extra>"),
        ))
        botones.append((T[lang]["med"][m], [j == i for j in range(len(MEDICIONES))]))
    _barras_h(fig, lang, {"es": "Suba sobre el promedio previo<br>(pp de tasa real anual)",
                          "en": "Rise over the prior average<br>(pp of real annual rate)"}[lang], 300)
    fig.update_layout(showlegend=False)
    _menu(fig, botones)
    return fig


def fig_etapa2(d: dict, lang: str) -> go.Figure:
    """Etapa 2: aporte a la suba de la mora; la tasa aparece repartida entre sus partes."""
    e2, partes = d["cadena_e2"], d["cadena_partes"]
    grupos = {"es": ("Tasa, por parte (etapa 1)", "Otros canales"), "en": ("Rate, by part (stage 1)", "Other channels")}[lang]
    hov = ("%{y}: %{x:+.1f} pp<br>IC 95%: %{customdata[0]:.1f} a %{customdata[1]:.1f}<br>%{customdata[2]}<extra></extra>"
           if lang == "es" else "%{y}: %{x:+.1f} pp<br>95% CI: %{customdata[0]:.1f} to %{customdata[1]:.1f}<br>%{customdata[2]}<extra></extra>")
    fig, botones, n = go.Figure(), [], 2
    for i, m in enumerate(MEDICIONES):
        t = partes[partes["deflactor"] == m].set_index("parte").loc[list(PARTES)]
        p_tasa = float(e2[(e2["deflactor"] == m) & (e2["canal"] == "costo_financiero")]["pvalor"].iloc[0])
        o = e2[(e2["deflactor"] == m) & (e2["canal"] != "costo_financiero")].sort_values("aporte_pp", ascending=False)
        nota_t = [f"{num(x, lang, 0)}% del aporte de la tasa · p de la tasa = {num(p_tasa, lang, 3)}" if lang == "es" else
                  f"{num(x, lang, 0)}% of the rate contribution · rate p = {num(p_tasa, lang, 3)}" for x in t["peso_en_aporte_tasa_pct"]]
        nota_o = [f"p = {num(p, lang, 3)}" for p in o["pvalor"]]
        for (y, x, lo, hi, notas), rol, nombre in (
                (([ETIQUETA[lang][p] for p in PARTES], t["aporte_pp"], t["aporte_pp_ic_inf"], t["aporte_pp_ic_sup"], nota_t), "s1", grupos[0]),
                (([ETIQUETA[lang][c] for c in o["canal"]], o["aporte_pp"], o["aporte_pp_ic_inf"], o["aporte_pp_ic_sup"], nota_o), "s2", grupos[1])):
            fig.add_trace(go.Bar(
                x=x, y=y, orientation="h", name=nombre, meta={"rol": rol}, visible=(i == 0), legendrank=1 if rol == "s1" else 2,
                marker=dict(color=SERIES[rol][0], line=dict(width=0)),
                error_x=dict(type="data", symmetric=False, array=hi - x, arrayminus=x - lo,
                             color=TINTA["claro"]["secundario"], thickness=1),
                customdata=list(zip(lo, hi, notas)), hovertemplate=hov,
            ))
        botones.append((T[lang]["med"][m], [j // n == i for j in range(n * len(MEDICIONES))]))
    _barras_h(fig, lang, {"es": "Aporte a la suba<br>de la mora (pp)", "en": "Contribution to<br>the NPL rise (pp)"}[lang], 420)
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
    e = d["nb_exp"]["total_pbi"].loc["2023-01-01":]  # con huecos: meses en que CAFCI publicó la cartera como imagen
    n = {"es": ("Crédito al sector privado en pesos", "Exposición de los bancos al Estado (títulos + pases)",
                "Bancos + fondos comunes (deuda nacional)"),
         "en": ("Peso credit to the private sector", "Bank exposure to the State (securities + repos)",
                "Banks + mutual funds (national debt)")}[lang]
    fig = go.Figure([_linea(p.index, p["credito_privado_mn_pbi"], n[0], "s1"),
                     _linea(p.index, p["exposicion_estado_mn_pbi"], n[1], "s2"),
                     _linea(e.index, e, n[2], "s2", mode="lines+markers")])
    fig.data[2].update(line=dict(dash="dot", width=2), marker=dict(size=8, color=SERIES["s2"][0]))
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


def cadena_cifras(d: dict, L: str) -> dict:
    """Cifras de la ponderación en dos etapas (outputs/cadena/), como rangos entre las tres mediciones."""
    e1, e2, pa, res = d["cadena_e1"], d["cadena_e2"], d["cadena_partes"], d["cadena_res"]
    a = d["canales"]

    def rg(vals, k=1):
        lo, hi = min(vals), max(vals)
        return num(lo, L, k) if round(lo, k) == round(hi, k) else f"{num(lo, L, k)}–{num(hi, L, k)}"

    def de(tabla, col, valor, campo):
        return [float(tabla[(tabla["deflactor"] == m) & (tabla[col] == valor)][campo].iloc[0]) for m in MEDICIONES]

    def oport(campo):
        return [float(a[(a["variante"] == "costo_oportunidad") & (a["deflactor"] == m) & (a["canal"] == "rendimiento_estado")][campo].iloc[0])
                for m in MEDICIONES]

    r = [res[m] for m in MEDICIONES]
    pub = res["publico"]
    out = {
        "meses_tasa": (mes(pub["meses_tasa"][0], L), mes(pub["meses_tasa"][1], L)), "rezago": pub["rezago_tasa"],
        "ventana": (mes(pub["ventana"][0], L), mes(pub["ventana"][1], L)),
        "mora_ini": num(pub["mora_inicio"], L), "mora_fin": num(pub["mora_fin"], L),
        "tasa_prev": rg([x["tasa_real_previa_pp"] for x in r], 0), "tasa_vent": rg([x["tasa_real_ventana_pp"] for x in r], 0),
        "tasa_suba": rg([x["tasa_real_ventana_pp"] - x["tasa_real_previa_pp"] for x in r], 0),
        "beta": rg([x["traspaso"]["beta_estado"] for x in r], 2),
        "p_mora_previa": num(min(x["traspaso"]["p_mora_previa"] for x in r), L, 2),
        "tasa": rg(de(e2, "canal", "costo_financiero", "aporte_pp")),
        "tasa_p": rg(de(e2, "canal", "costo_financiero", "pvalor"), 3),
        "rob": rg(oport("aporte_pp")), "rob_p": rg(oport("pvalor"), 3),
    }
    for x in PARTES:
        out[f"exc_{x}"] = rg(de(e1, "parte", x, "exceso_pp"))
        out[f"peso_{x}"] = rg(de(e1, "parte", x, "peso_en_suba_tasa_pct"), 0)
        out[f"mora_{x}"] = rg(de(pa, "parte", x, "aporte_pp"))
    for c in ("poder_compra", "ancla_cambiaria", "cosecha_dilucion"):
        out[c] = {m: num(v, L) for m, v in zip(MEDICIONES, de(e2, "canal", c, "aporte_pp"))}
        out[f"{c}_p"] = {m: num(v, L, 3) for m, v in zip(MEDICIONES, de(e2, "canal", c, "pvalor"))}
        out[f"{c}_rg"] = rg(de(e2, "canal", c, "aporte_pp"))
    return out


def conclusiones(d: dict, L: str) -> str:
    """Bloque "En síntesis": cinco conclusiones en lenguaje llano, cada número desde outputs/."""
    pp = lambda x, k=1: num(x, L, k)  # noqa: E731
    desc, aj, esc = d["desc"], d["ajuste"], d["esc"]["satelite_publico"]
    cad, cr = cadena_cifras(d, L), d["cadena_res"]["publico"]
    nbc = d["nb"]["credito_integrado"]
    nb_ult = max(nbc)
    k = d["castigos"].iloc[-2:]
    cast = k["castigos_familias_estimado_real"].sum() / 1000
    sin = k["irregular_familias_sin_castigos_real"].sum() / 1000
    tm = {r["escenario"]: r for r in d["dec"]["tasa_minima_publico_central"] if r["linea"] == "personales"}
    margen = tm["base"]["colchon_pp"]
    c = d["cortes"]
    corte = float(c[(c["deflactor"] == "publico") & (c["linea"] == "personales") & (c["escenario"] == "base")
                    & (c["corte_ttc_pct"].round(6) == 10)]["corte_equivalente_pct"].iloc[0])
    suba = cr["mora_fin"] - cr["mora_inicio"]
    e1 = d["cadena_e1"]
    peso_estado = pp(float(e1[(e1["deflactor"] == "publico") & (e1["parte"] == "estado")]["peso_en_suba_tasa_pct"].iloc[0]), 0)
    multiplo = desc["mora_familias"] / aj["mora_familias"]["inicio"]
    if L == "es":
        vs_estado = ("apenas empata con" if abs(margen) < 2 else "le gana a" if margen > 0 else "pierde contra")
        items = [
            f"<strong>La mora de las familias se multiplicó por {pp(multiplo)}:</strong> de {pp(aj['mora_familias']['inicio'])}% en {mes(aj['ventana'][0], L)} a {pp(desc['mora_familias'])}% en {mes(desc['ultimo_dato'], L)}, el máximo desde 2010. Contando fintech y billeteras, era {pp(nbc[nb_ult]['mora_integrada_pct'])}% en {mes(nb_ult, L)}.",
            f"<strong>La causa principal es lo caro del crédito.</strong> La tasa real que pagan las familias explica {cad['tasa']} de los {pp(suba)} puntos que subió la mora desde el mínimo de {cad['ventana'][0]}. La caída del salario real y el atraso cambiario suman, pero bastante menos.",
            f"<strong>La tasa está alta en buena parte porque el Estado compite por los pesos.</strong> Lo que el Estado les paga a los bancos explica cerca del {peso_estado}% de la suba de la tasa y se traslada completo. Con ese piso, a la tasa de mercado prestarle a una familia {vs_estado} prestarle al Estado (margen de {'+' if margen >= 0 else ''}{pp(margen)} puntos en el escenario base).",
            f"<strong>El freno reciente de la mora es, en buena parte, contable.</strong> En {mes(k['fecha'].iloc[0], L)} y {mes(k['fecha'].iloc[1], L)} los bancos pasaron a pérdida unos {pp(cast, 0)} mil millones de pesos de deuda de familias; sin eso, la deuda impaga habría crecido {pp(sin, 0)} mil millones.",
            f"<strong>Hacia adelante, la mora sigue subiendo si la tasa real no baja:</strong> {pp(esc['mora_fin']['base']['central'])}% en {mes(esc['fin'], L)} en el escenario base. Para un banco, eso implica aprobar mucho menos: quien hoy aprueba hasta un riesgo de 10% calibrado en un año normal debería aprobar sólo hasta {pp(corte)}%.",
        ]
        titulo = "En síntesis"
    else:
        vs_estado = ("barely breaks even with" if abs(margen) < 2 else "beats" if margen > 0 else "loses to")
        items = [
            f"<strong>Household delinquency multiplied by {pp(multiplo)}:</strong> from {pp(aj['mora_familias']['inicio'])}% in {mes(aj['ventana'][0], L)} to {pp(desc['mora_familias'])}% in {mes(desc['ultimo_dato'], L)}, the highest since 2010. Including fintechs and digital wallets, it was {pp(nbc[nb_ult]['mora_integrada_pct'])}% in {mes(nb_ult, L)}.",
            f"<strong>The main cause is expensive credit.</strong> The real rate households pay explains {cad['tasa']} of the {pp(suba)} points delinquency rose since the {cad['ventana'][0]} low. Falling real wages and the strong peso add, but much less.",
            f"<strong>Rates are high largely because the State competes for pesos.</strong> What the State pays banks explains about {peso_estado}% of the rise in the rate and passes through in full. With that floor, at the market rate lending to a household {vs_estado} lending to the State (margin of {'+' if margen >= 0 else ''}{pp(margen)} points in the baseline).",
            f"<strong>The recent leveling-off is largely an accounting effect.</strong> In {mes(k['fecha'].iloc[0], L)} and {mes(k['fecha'].iloc[1], L)} banks wrote off about {pp(cast, 0)} billion pesos of household debt; without that, unpaid debt would have grown {pp(sin, 0)} billion.",
            f"<strong>Going forward, delinquency keeps rising unless real rates fall:</strong> {pp(esc['mora_fin']['base']['central'])}% by {mes(esc['fin'], L)} in the baseline. For a bank, that means approving far less: a lender approving up to a 10% risk calibrated on a normal year should now approve only up to {pp(corte)}%.",
        ]
        titulo = "In short"
    return f'<section class="sintesis"><h2>{titulo}</h2><ol>{"".join(f"<li>{x}</li>" for x in items)}</ol></section>'


def contenido(d: dict, lang: str) -> str:
    """Secciones del sitio. Cada número sale de `d` (outputs/)."""
    L = lang
    desc, aj, rend, esc = d["desc"], d["ajuste"], d["rend"], d["esc"]
    pp = lambda x, k=1: num(x, L, k)  # noqa: E731

    cad = cadena_cifras(d, L)
    nbe = d["nb"]["exposicion"]
    nbc = d["nb"]["credito_integrado"]
    nb_ult, nb_ini = max(nbc), min(nbc)
    sat = {m: esc[f"satelite_{m}"] for m in MEDICIONES}
    s_pub = sat["publico"]
    base_pub = s_pub["mora_fin"]["base"]
    ct = d["castigos_total"].iloc[-1]
    k = d["castigos"].iloc[-2:]
    oos = d["oos"]
    o12 = oos[(oos["especificacion"] == "base") & (oos["muestra"] == "larga") & (oos["h"] == 12)].set_index("modelo")
    oc12 = d["oos_canales"][d["oos_canales"]["h"] == 12].set_index("modelo")
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
<p><strong>Con fintech y billeteras, la mora es más alta.</strong> Los proveedores no financieros de crédito (fintech, billeteras, emisoras de tarjetas no bancarias, mutuales) son {pp(nbc[nb_ult]['participacion_pnfc_pct'], 0)}% del crédito a las familias y su cartera irregular llegó a {pp(nbc[nb_ult]['mora_pnfc_pct'])}% en {mes(nb_ult, L)} (informes semestrales del BCRA). Sumando los dos sectores, la mora de las familias era {pp(nbc[nb_ult]['mora_integrada_pct'])}% y no {pp(nbc[nb_ult]['mora_bancos_pct'])}%: {pp(nbc[nb_ult]['diferencia_pp'])} pp más. En {mes(nb_ini, L)} la diferencia era {pp(nbc[nb_ini]['diferencia_pp'])} pp. El resto del análisis usa la mora bancaria, que es la única serie mensual.</p>
</section>

<section><h2>2. La cadena: de la política monetaria a la cuota</h2>
<p>Para bajar la inflación, el programa ancló el dólar y absorbió pesos con tasas altas. Los bancos encontraron más rentable prestarle al Estado que a las familias: en {mes(feb24.name, L)} su exposición al Estado era {pp(feb24['exposicion_estado_mn_pbi'])}% del PBI, contra {pp(feb24['credito_privado_mn_pbi'])}% de crédito al sector privado.</p>
{_div(fig_profundidad(d, L), 'g-prof', L)}
<p><strong>Fuera de los bancos también se le presta al Estado.</strong> Los fondos comunes de inversión tenían deuda nacional por {pp(nbe['fci_deuda_nacional_pbi'])}% del PBI en {mes(nbe['ultimo'], L)} (máximo: {pp(nbe['maximo_fci_deuda_nacional_pbi'])}% en {mes(nbe['fecha_maximo_fci'], L)}; datos de la CAFCI). Sumados a los bancos, la exposición al Estado llega a {pp(nbe['total_pbi'])}% del PBI, contra {pp(nbe['credito_privado_bancos_pbi'])}% de crédito bancario al sector privado. Los fondos money market, donde las billeteras virtuales colocan el saldo de sus usuarios, tienen sólo {pp(nbe['fci_money_market_titulos_pct'])}% en títulos públicos y {pp(nbe['fci_money_market_plazo_pct'], 0)}% en plazos fijos y cauciones: esa plata vuelve a los bancos, y lo que los bancos compran con ella ya está en su exposición. Por eso no se suma, para no contarla dos veces. No hay datos públicos de la tenencia directa por medio de brokers ni de la cartera propia de las fintech.</p>
<p>Cuando el crédito se reactivó, las familias tomaron deuda a tasas altas justo cuando el salario real no se recuperaba. El salario registrado real está {pp(100 - sal['salario_real_publico'])}% abajo de nov-23 con la medición oficial, {pp(100 - sal['salario_real_mix'])}% con la mix y {pp(100 - sal['salario_real_seleccionado'])}% con la canasta actualizada (ponderadores ENGHo 2017/18).</p>
{_div(fig_salario(d, L), 'g-salario', L)}
<p><strong>Lo que rinde prestarle al Estado pone un piso a la tasa de las familias.</strong> Como no hay una serie pública de rendimientos de Lecap, se calcula lo que los bancos efectivamente ganaron con títulos públicos y pases en pesos (cuentas de resultados de cada entidad, reexpresadas por inflación). En 2025 el Estado les rindió en promedio {pp(pr['2025']['tea_estado_3m'])}% anual, por encima de la BADLAR ({pp(pr['2025']['tea_badlar'])}%). Y la tasa de préstamos personales nuevos se quedó en {pp(pr['2025']['tea_personales_nuevos'])}%: una prima de {pp(pr['2025']['prima_personales_sobre_estado_pp'])} pp sobre el Estado.</p>
{_div(fig_tasas(d, L), 'g-tasas', L)}
</section>

<section><h2>3. Cuánto pesó cada canal: la cadena en dos etapas</h2>
<p><strong>La esterilización y la tasa no son canales paralelos: una causa la otra.</strong> Para absorber pesos, el BCRA y el Tesoro les pagan a los bancos una tasa que los convenza de comprar sus títulos o hacer pases (Leliq, pases, LEFI, Lecap). Cada peso que un banco le presta a una familia es un peso que deja de ganar esa tasa sin riesgo: lo que paga el Estado es el piso de la tasa a familias. Si la esterilización y la tasa entran juntas en la ecuación de la mora, el efecto que pasa por la tasa queda contado en la tasa y a la esterilización le queda sólo el resto, que es casi nada. Por eso la ponderación se hace en dos pasos: primero qué subió la tasa, después qué subió la mora.</p>

<h3>Etapa 1: qué subió la tasa</h3>
<p>La tasa real del CFT de préstamos personales se descompone de forma exacta en tres partes: lo que paga el Estado (en términos reales), la prima que el banco cobra por encima del Estado y el IVA sobre los intereses. Entre {cad['meses_tasa'][0]} y {cad['meses_tasa'][1]} (los meses que, con el rezago de {cad['rezago']} meses de la etapa 2, mueven la mora de la ventana) la tasa real promedió {cad['tasa_vent']}%, contra {cad['tasa_prev']}% antes: <strong>+{cad['tasa_suba']} pp</strong>.</p>
{_div(fig_etapa1(d, L), 'g-etapa1', L)}
<ul>
<li><strong>Lo que paga el Estado explica el {cad['peso_estado']}% de la suba de la tasa</strong> (+{cad['exc_estado']} pp). La prima del banco, el {cad['peso_prima']}% (+{cad['exc_prima']} pp), y el IVA, el {cad['peso_impuestos']}% (+{cad['exc_impuestos']} pp): crece solo, porque se cobra sobre una tasa más alta.</li>
<li><strong>El piso se traslada completo.</strong> Cada punto más que paga el Estado sube {cad['beta']} puntos la tasa real de los préstamos (variaciones interanuales desde 2018, p &lt; 0,001), controlando por la mora previa. La mora previa no explica la tasa (p &gt; {cad['p_mora_previa']}): la prima no subió por el riesgo pasado.</li>
</ul>

<h3>Etapa 2: qué subió la mora</h3>
<p>Ecuación de la variación mensual de la mora (logit) con la tasa real del CFT, el salario real, el tipo de cambio real y el crédito real, con rezagos elegidos por BIC. El aporte de cada canal es la mora simulada con los datos reales menos la simulada con ese canal en un valor neutral. El aporte de la tasa se reparte entre sus partes de la etapa 1, poniendo cada parte en su promedio previo. Ventana: del mínimo de {cad['ventana'][0]} ({cad['mora_ini']}%) a {cad['ventana'][1]} ({cad['mora_fin']}%). Las barras muestran el intervalo del 95%.</p>
{_div(fig_etapa2(d, L), 'g-etapa2', L)}
<ul>
<li><strong>La tasa es el canal dominante:</strong> +{cad['tasa']} pp (p = {cad['tasa_p']}). De eso, <strong>lo que paga el Estado aporta +{cad['mora_estado']} pp</strong>, la prima del banco +{cad['mora_prima']} pp y el IVA +{cad['mora_impuestos']} pp.</li>
<li>Robustez: si a lo que paga el Estado se le estima un coeficiente propio en vez de repartir el de la tasa, su aporte es +{cad['rob']} pp (p = {cad['rob_p']}).</li>
<li><strong>El poder de compra pesa más cuanto más realista es la medición de precios:</strong> +{cad['poder_compra']['publico']} pp con la oficial (p = {cad['poder_compra_p']['publico']}) y +{cad['poder_compra']['seleccionado']} pp con la canasta actualizada (p = {cad['poder_compra_p']['seleccionado']}).</li>
<li>Ancla cambiaria: +{cad['ancla_cambiaria_rg']} pp, significativa sólo con la canasta actualizada (p = {cad['ancla_cambiaria_p']['seleccionado']}). Ciclo de crédito: +{cad['cosecha_dilucion_rg']} pp.</li>
</ul>
<p class="nota">La cantidad absorbida (stock de títulos y pases) no entra en la etapa 2 porque actúa a través del precio: en una ecuación única con la tasa adentro, su aporte directo no se distingue de cero. Los intervalos de las partes de la tasa se mueven con el coeficiente de la tasa y son amplios. Lo que paga el Estado también refleja las expectativas de inflación y el riesgo soberano, no sólo la decisión de esterilizar.</p>
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
<p><strong>Including fintechs and digital wallets, delinquency is higher.</strong> Non-bank credit providers (fintechs, wallets, non-bank card issuers, mutual associations) account for {pp(nbc[nb_ult]['participacion_pnfc_pct'], 0)}% of household credit, and their non-performing ratio reached {pp(nbc[nb_ult]['mora_pnfc_pct'])}% in {mes(nb_ult, L)} (BCRA semiannual reports). Combining both sectors, household delinquency was {pp(nbc[nb_ult]['mora_integrada_pct'])}% rather than {pp(nbc[nb_ult]['mora_bancos_pct'])}%: {pp(nbc[nb_ult]['diferencia_pp'])} pp higher. In {mes(nb_ini, L)} the gap was {pp(nbc[nb_ini]['diferencia_pp'])} pp. The rest of the analysis uses bank delinquency, the only monthly series.</p>
</section>

<section><h2>2. The chain: from monetary policy to the monthly payment</h2>
<p>To bring inflation down, the program anchored the exchange rate and absorbed pesos with high rates. Banks found it more profitable to lend to the State than to households: in {mes(feb24.name, L)} their exposure to the State was {pp(feb24['exposicion_estado_mn_pbi'])}% of GDP, against {pp(feb24['credito_privado_mn_pbi'])}% for private credit.</p>
{_div(fig_profundidad(d, L), 'g-prof', L)}
<p><strong>Lending to the State also happens outside banks.</strong> Mutual funds held national government debt worth {pp(nbe['fci_deuda_nacional_pbi'])}% of GDP in {mes(nbe['ultimo'], L)} (peak: {pp(nbe['maximo_fci_deuda_nacional_pbi'])}% in {mes(nbe['fecha_maximo_fci'], L)}; CAFCI data). Added to banks, exposure to the State reaches {pp(nbe['total_pbi'])}% of GDP, against {pp(nbe['credito_privado_bancos_pbi'])}% for bank credit to the private sector. Money market funds, where digital wallets park their users' balances, hold only {pp(nbe['fci_money_market_titulos_pct'])}% in government securities and {pp(nbe['fci_money_market_plazo_pct'], 0)}% in time deposits and repos: that money goes back to banks, and what banks buy with it is already in their exposure, so it is not added again. There is no public data on direct holdings through brokers or on fintechs' own portfolios.</p>
<p>When credit came back, households borrowed at high rates just as real wages failed to recover. The real registered wage is {pp(100 - sal['salario_real_publico'])}% below Nov-23 with the official measure, {pp(100 - sal['salario_real_mix'])}% with the mix and {pp(100 - sal['salario_real_seleccionado'])}% with the updated basket (ENGHo 2017/18 weights).</p>
{_div(fig_salario(d, L), 'g-salario', L)}
<p><strong>What lending to the State pays sets a floor for household rates.</strong> With no public series of Treasury bill (Lecap) yields, the measure is what banks actually earned on peso government securities and repos (income accounts of each bank, restated for inflation). In 2025 the State paid them {pp(pr['2025']['tea_estado_3m'])}% a year on average, above BADLAR ({pp(pr['2025']['tea_badlar'])}%). New personal loans stayed at {pp(pr['2025']['tea_personales_nuevos'])}%, a {pp(pr['2025']['prima_personales_sobre_estado_pp'])} pp premium over the State.</p>
{_div(fig_tasas(d, L), 'g-tasas', L)}
</section>

<section><h2>3. How much each channel weighed: the two-stage chain</h2>
<p><strong>Sterilization and the loan rate are not parallel channels: one causes the other.</strong> To absorb pesos, the central bank and the Treasury pay banks a rate high enough for them to buy their paper or do repos (Leliq, repos, LEFI, Lecap). Every peso a bank lends to a household is a peso that stops earning that risk-free rate, so what the State pays is the floor of household rates. If sterilization and the rate enter the delinquency equation together, the effect that runs through the rate is counted in the rate and sterilization keeps only the remainder, which is close to nothing. So the weighting is done in two steps: first what raised the rate, then what raised delinquency.</p>

<h3>Stage 1: what raised the rate</h3>
<p>The real all-in cost (CFT) of personal loans splits exactly into three parts: what the State pays (in real terms), the premium banks charge over the State, and VAT on interest. Between {cad['meses_tasa'][0]} and {cad['meses_tasa'][1]} (the months that, with stage 2's {cad['rezago']}-month lag, drive delinquency in the window) the real rate averaged {cad['tasa_vent']}%, against {cad['tasa_prev']}% before: <strong>+{cad['tasa_suba']} pp</strong>.</p>
{_div(fig_etapa1(d, L), 'g-etapa1', L)}
<ul>
<li><strong>What the State pays explains {cad['peso_estado']}% of the rise in the rate</strong> (+{cad['exc_estado']} pp). The bank premium explains {cad['peso_prima']}% (+{cad['exc_prima']} pp) and VAT {cad['peso_impuestos']}% (+{cad['exc_impuestos']} pp), which grows on its own because it is charged on a higher rate.</li>
<li><strong>The floor passes through in full.</strong> Each extra point the State pays raises the real loan rate by {cad['beta']} points (year-on-year changes since 2018, p &lt; 0.001), controlling for past delinquency. Past delinquency does not explain the rate (p &gt; {cad['p_mora_previa']}): the premium did not rise because of past risk.</li>
</ul>

<h3>Stage 2: what raised delinquency</h3>
<p>Equation for the monthly change in the (logit) NPL ratio with the real CFT, the real wage, the real exchange rate and real credit, with BIC-selected lags. Each channel's contribution is simulated delinquency with actual data minus simulated delinquency with that channel held neutral. The rate's contribution is split among its stage-1 parts by setting each part to its prior average. Window: from the {cad['ventana'][0]} low ({cad['mora_ini']}%) to {cad['ventana'][1]} ({cad['mora_fin']}%). Bars show the 95% interval.</p>
{_div(fig_etapa2(d, L), 'g-etapa2', L)}
<ul>
<li><strong>The rate is the dominant channel:</strong> +{cad['tasa']} pp (p = {cad['tasa_p']}). Of that, <strong>what the State pays contributes +{cad['mora_estado']} pp</strong>, the bank premium +{cad['mora_prima']} pp and VAT +{cad['mora_impuestos']} pp.</li>
<li>Robustness: estimating a separate coefficient for what the State pays, instead of splitting the rate's, gives +{cad['rob']} pp (p = {cad['rob_p']}).</li>
<li><strong>Purchasing power weighs more the more realistic the price measure:</strong> +{cad['poder_compra']['publico']} pp with the official index (p = {cad['poder_compra_p']['publico']}) and +{cad['poder_compra']['seleccionado']} pp with the updated basket (p = {cad['poder_compra_p']['seleccionado']}).</li>
<li>FX anchor: +{cad['ancla_cambiaria_rg']} pp, significant only with the updated basket (p = {cad['ancla_cambiaria_p']['seleccionado']}). Credit cycle: +{cad['cosecha_dilucion_rg']} pp.</li>
</ul>
<p class="nota">The quantity absorbed (stock of securities and repos) is left out of stage 2 because it works through the price: in a single equation with the rate included, its direct contribution is indistinguishable from zero. Intervals for the rate's parts move with the rate coefficient and are wide. What the State pays also reflects inflation expectations and sovereign risk, not only the decision to sterilize.</p>
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
:root{color-scheme:light;--bg:#f9f9f7;--surface:#fcfcfb;--text:#0b0b0b;--text2:#52514e;--muted:#898781;--line:#e1e0d9;--accent:#2a78d6;--lado1:rgba(42,120,214,.075);--lado2:rgba(235,104,52,.055)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#0d0d0d;--surface:#1a1a19;--text:#f0efec;--text2:#c3c2b7;--muted:#898781;--line:#2c2c2a;--accent:#3987e5;--lado1:rgba(57,135,229,.10);--lado2:rgba(217,89,38,.07)}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#0d0d0d;--surface:#1a1a19;--text:#f0efec;--text2:#c3c2b7;--muted:#898781;--line:#2c2c2a;--accent:#3987e5;--lado1:rgba(57,135,229,.10);--lado2:rgba(217,89,38,.07)}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:920px;margin:0 auto;padding:24px 16px 64px}
/* Color tenue en los márgenes (sólo pantallas anchas): los dos colores principales de los gráficos */
@media screen and (min-width:1000px){body::before{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;
background:radial-gradient(50% 85% at 0% 25%,var(--lado1),transparent 72%),radial-gradient(50% 85% at 100% 75%,var(--lado2),transparent 72%)}}
header{display:flex;justify-content:space-between;align-items:baseline;gap:16px;flex-wrap:wrap}
h1{font-size:2rem;line-height:1.2;margin:8px 0}
h2{font-size:1.35rem;margin:48px 0 8px}
h3{font-size:1.1rem;margin:28px 0 6px}
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
.sintesis{background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:8px;padding:4px 20px 8px;margin-top:28px}
.sintesis h2{margin:16px 0 4px}
.sintesis ol{padding-left:20px;margin:8px 0}
.sintesis li{margin:10px 0}
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
{conclusiones(d, lang)}
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
