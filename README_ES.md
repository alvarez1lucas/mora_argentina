# Mora de los hogares en Argentina

**[Sitio](https://alvarez1lucas.github.io/mora-hogares-argentina/)** · **[Informe de 2 páginas (PDF)](https://alvarez1lucas.github.io/mora-hogares-argentina/informe.pdf)** · [English version](README.md)

¿Qué explica la suba de la mora de las familias en Argentina entre 2024 y 2026, y qué puede pasar en los próximos 12 meses? El proyecto responde sólo con datos públicos (BCRA, INDEC, IPCBA, A3 Mercados), econometría de series de tiempo y de panel, ML causal y validación fuera de muestra. Todos los números de este archivo los genera `python -m mora.informe` desde `outputs/`; el pipeline se actualiza todas las semanas con GitHub Actions.

## Resultados (datos a ago-26)

- **La mora se multiplicó por 4,7.** La mora de familias (situación 3 a 5, BCRA) pasó de 2,7% en nov-23 a 12,8% en ago-26, el máximo desde que empieza la serie en 2010 (pico de 12,9% en jul-26). Préstamos personales: 17,0%; tarjetas: 12,2%.
- **Es deuda impaga, no una cartera que se achica.** De la suba de 12 meses, +6,2 pp son del numerador (crecimiento real de la deuda irregular) y -0,03 pp del denominador.
- **Alertas tempranas.** Un índice por el método de señales (Kaminsky-Reinhart) con atrasos tempranos (31-90 días), carga de la cuota, tasa real, crecimiento del crédito, actividad y recaudación marca **vigilancia** en sep-26. Entrenado sólo con datos hasta 2023, estuvo en vigilancia o más en el 76% de los meses previos a la suba de 2025, pero se apagó entre ago-24 y nov-24, justo antes. La recaudación llega rápido pero casi no anticipa la mora.
- **Más allá de los bancos.** Los proveedores no financieros de crédito (fintech, billeteras, emisoras de tarjetas no bancarias) tienen el 18% del crédito a las familias, con una cartera irregular de 26,9% en feb-26 (informes semestrales del BCRA); sumando los dos sectores, la mora de las familias era 14,0% y no el 11,2% de los bancos. Del lado del fondeo, los fondos comunes tenían deuda nacional por 2,0% del PBI en jun-26 (máximo de 2,8% en dic-23, CAFCI), lo que lleva la exposición al Estado de 9,8% (bancos) a 11,7% del PBI. Los money market, donde las billeteras colocan los saldos de sus usuarios, tienen sólo 1,4% en títulos públicos: esa plata llega al Estado vía los bancos y no se suma dos veces.
- **Cadena en dos etapas: la esterilización sube la tasa y la tasa sube la mora.** La esterilización y la tasa no compiten como canales, así que se ponderan en secuencia. *Etapa 1:* la tasa real del CFT de préstamos personales subió 35–36 pp (de 25–26% a 61–62% en los meses que mueven la ventana); lo que el Estado les paga a los bancos por títulos y pases en pesos (cuentas de resultados reexpresadas por inflación) explica entre el 30–31% y el 39–41% de esa suba: cada punto que sube, la tasa de los préstamos sube 0,75 puntos (tasas nominales, p < 0,001). En 2025 promedió 46,4%, por encima de la BADLAR (41,7%), y le ganó a la BADLAR en el 85% de los meses desde nov-23. *Etapa 2:* en la descomposición histórica contrafáctica de la suba de oct-24 (2,5%) a ago-26 (12,8%), la tasa real es el canal dominante, +8,3 pp (p = 0,007–0,026): entre +2,6–2,8 y +3,5–3,7 pp por lo que paga el Estado (con el traspaso estimado y en la cuenta contable), el resto por la prima del banco y +1,5 pp por el IVA. Con un coeficiente propio para lo que paga el Estado, su aporte es +5,0–5,6 pp (p = 0,021–0,023).
- **El poder de compra pesa más con mediciones de precios realistas.** El salario registrado real está 7,9% abajo de nov-23 con el IPC oficial, 9,4% con el mix y 11,0% con la canasta actualizada. Su aporte pasa de +0,7 pp (p = 0,148) a +2,1 pp (p = 0,009).
- **El freno reciente es, en buena parte, castigos.** En jun-26 y jul-26 la deuda irregular de familias creció 59 / 22 mil millones de pesos constantes, mientras se castigaban unos 238 / 189 mil millones; sin castigos habría crecido 298 / 211 mil millones. Para el sector privado total, la mora de jul-26 sería 9,4% en lugar de 7,7%.
- **Efecto cosecha a nivel banco.** En 66 entidades con efectos fijos de entidad y mes, 10 pp más de crecimiento real del crédito al consumo 12-24 meses antes suman 0,35 pp a la variación interanual de la mora (p < 0,001); Double ML: 0,14 pp (p = 0,049); Causal Forest (ATE): 0,20 pp (IC 95%: 0,03 a 0,37).

### Escenarios a ago-27 (mora de familias, hoy 12,8%)

| Medición | Muestra | Base | Banda 90% | Adverso | Favorable | Ponderado NIIF 9 |
|---|---|---|---|---|---|---|
| Pública (INDEC) | 2010+ | 15,9% | 10,4–22,0% | 19,7% | 13,3% | 16,5% |
| Mix | 2010+ | 15,7% | 10,0–22,1% | 19,2% | 13,3% | 16,3% |
| Seleccionada (canasta actualizada) | 2017+ | 13,9% | 7,4–20,5% | 16,2% | 12,2% | 14,2% |

El modelo satélite le gana al AR(1) y al paseo aleatorio fuera de muestra (RMSE a 12 meses: 2,25 pp contra 2,92 y 3,12). Pesos NIIF 9: 60% base, 25% adverso, 15% favorable. **En el base la mora sigue subiendo**, porque la tasa real queda cerca de máximos históricos; sólo baja si baja la tasa real.

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
- Panel por banco: efectos fijos dobles (errores por cluster), estudio de eventos del apretón de jul-25, Double ML y Causal Forest (EconML), alerta temprana con LightGBM + SHAP (lineal: RMSE 7,97, precisión en el decil superior 30%; LightGBM: 8,28, 46%).
- Los tests de Granger, donde se usan, son sólo descriptivos.

## Limitaciones

- Son datos agregados: no se observa a cada deudor. La Central de Deudores no se usa, por privacidad.
- La mora del sector informal y de las plataformas no bancarias (Mercado Pago, Ualá) no está en estos datos; sus tasas sí aparecen en el relevamiento de transparencia.
- Las relaciones estimadas no son causales en sentido estricto. El rezago de los regresores mitiga, pero no elimina, la causalidad inversa (por ejemplo, el spread también sube porque sube la mora).
- Hay un solo ciclo de ajuste con estas características y la muestra limpia tiene 77 meses: las bandas son anchas y se reportan siempre.
- Los castigos de familias y el PBI de los últimos trimestres son estimaciones (están marcadas en los datos).
- La medición seleccionada es una propuesta propia: cambia los ponderadores del índice (ENGHo 2017/18), no la medición de precios del INDEC.
- No hay series públicas de cheques rechazados recientes, embargos de ARCA ni stock de refinanciaciones.
- El modelo de canales explica pero no pronostica: su RMSE a 12 meses (3,80 pp) es peor que el de un AR(1) (3,43).
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
