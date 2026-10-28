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
| Expectativas de inflación (REM, BCRA) | en su fase (5) | Reemplaza la inflación de 3 meses anualizada como expectativa |
| Carga financiera de los hogares (cuotas / masa salarial) | en su fase (5) | Stock × CFT sobre masa salarial SIPA |
| Stock de deuda del Tesoro en pesos e intereses capitalizados | en su fase (5) | Secretaría de Finanzas, Boletín de deuda |
| Licitaciones del Tesoro (rollover, tasas) y emisión dollar-linked | en su fase (5) | La prensa indica que el dollar-linked reemplazó a los futuros en 2026 |
| Mercado de trabajo informal (EPH) | en su fase (5) | El salario registrado no capta a los deudores informales |
| Posición oficial del BCRA en futuros | fuera de alcance por ahora | No se encontró el archivo fuente; se usan puntos de control de prensa |
| Cheques rechazados | fuera de alcance por ahora | No está en la API del BCRA |
| Mora de PNFC/fintech | contexto | Sin serie primaria; sólo la foto de CFT del régimen de transparencia |

## Fases

| Fase | Estado |
|---|---|
| 1 Relevamiento | hecho |
| 2 Ingesta | hecho |
| 3 Descriptivo | hecho |
| 4 Modelo satélite | hecho |
| 4b Robustez de medición | hecho |
| 5 Causal y panel (DiD con exposición, Double ML, Causal Forest, LightGBM + SHAP, mediación, costo de oportunidad) | hecho; pendientes opcionales: proyecciones locales, ARDL/bounds, bandas por bootstrap |
| 6 Escenarios | hecho |
| 7 Sitio web (Python + Plotly, selector de medición) | hecho; falta publicar |
| 8 Informe y README | hecho; falta publicar |
