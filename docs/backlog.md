# Backlog

Todo lo propuesto durante el proyecto, clasificado. Estados: **hecho**, **ahora** (cambia la medición o el modelo), **en su fase**, **contexto** (va al sitio o al informe, sin modelo), **fuera de alcance** (con el motivo).

## Medición de precios (Fase 4b)

| Ítem | Estado | Notas |
|---|---|---|
| Tres líneas de conclusiones: pública, seleccionada (canasta ENGHo 2017/18), mix | hecho | `mora.deflactores`, `mora.robustez` |
| IPC por división del INDEC | hecho | `ipc_divisiones.csv` |
| IPCBA (CABA) 2012-2026 como validación externa y para el tramo 2012-2016 | hecho | Empalme base 2011-12 / base 2021 en feb-2022 |
| Validar la reconstrucción del oficial | hecho | Ponderaciones implícitas por mínimos cuadrados no negativos; error máximo 0,22% (nacional), 0,0% (GBA) |
| Tarifas puntuales desde dic-2023 (colectivo AMBA +1.513%, gas +1.391%, agua +573%, prepaga +417%, nafta +417%, luz +387%, IPC +348%) | contexto | Gráfico aportado por el autor, fuente no identificada. Contraste con subíndices oficiales del INDEC (GBA, nov-23 → sep-26): electricidad, gas y otros combustibles +896%, transporte público +730%, alquiler +774%, prepagas +500%, combustibles +501%, nivel general +353% |
| Apertura de regulados del IPCBA 2012-2022 | fuera de alcance | La serie figura en datos.gob.ar pero la API la devuelve vacía |

## Datos pendientes

| Ítem | Estado | Notas |
|---|---|---|
| Expectativas de inflación (REM, BCRA) | hecho (chequeo) | `mora.expectativas`: refuerza la conclusión; destapó el error del traspaso en reales (docs/expectativas.md) |
| Carga financiera de los hogares (cuotas / masa salarial) | hecho | `mora.carga`: agregada; no verifica el "~25% del salario" de los endeudados (docs/carga.md) |
| Stock de deuda del Tesoro en pesos e intereses capitalizados | hecho | `mora.deuda` con el boletín mensual de Finanzas (docs/deuda.md) |
| Licitaciones del Tesoro (rollover, tasas) y emisión dollar-linked | hecho (rollover mensual agregado) | Desde los flujos del boletín; los resultados por licitación no tienen serie descargable |
| Mercado de trabajo informal (EPH) | descartado | Agrega ruido: los informales casi no tienen acceso al crédito bancario |
| Posición oficial del BCRA en futuros | fuera de alcance por ahora | No se encontró el archivo fuente; se usan puntos de control de prensa |
| Cheques rechazados | fuera de alcance por ahora | No está en la API del BCRA |
| Mora de PNFC/fintech | hecho | Cinco fechas de los informes semestrales del BCRA, con citas verificables (docs/no_bancario.md) |

## Fases

| Fase | Estado |
|---|---|
| 1 Relevamiento | hecho |
| 2 Ingesta | hecho |
| 3 Descriptivo | hecho |
| 4 Modelo satélite | hecho |
| 4b Robustez de medición | hecho |
| 5 Causal y panel (DiD con exposición, Double ML, Causal Forest, LightGBM + SHAP, mediación, costo de oportunidad) | hecho; proyecciones locales, ARDL/bounds y bootstrap de canales en `mora.complementos` (no integrados al sitio ni al workflow; ver docs/complementos.md) |
| 6 Escenarios | hecho |
| 7 Sitio web (Python + Plotly, selector de medición) | hecho; falta publicar |
| 8 Informe y README | hecho; falta publicar |
| 9 Capa de decisión (PD por escenario, tasa mínima de originación) | hecho; en el sitio (sección 7), con el puente a homecredit-pd-validation |
| 10 Seguimiento de pronósticos (retrospectiva y registro) | hecho (`mora.seguimiento`, docs/seguimiento.md) |
| 11 Fuera de los bancos (FCI, billeteras, PNFC) | hecho (`mora.no_bancario`, docs/no_bancario.md) |
| 12 Alertas tempranas (método de señales, con situación 2 y recaudación) | hecho (`mora.alertas`, docs/alertas.md) |
