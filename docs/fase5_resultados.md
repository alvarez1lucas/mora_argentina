# Fase 5: canales, panel y ML causal

Hipótesis del autor: la suba de la mora de familias 2024-26 es un problema **macro** con cinco canales que actúan juntos: (1) caída del poder de compra mayor que la que muestran las estadísticas oficiales, (2) alto costo financiero, (3) tasas altas, (4) esterilización y absorción de pesos por el Estado, (5) ancla cambiaria con intervención. El objetivo de esta fase es ponderar el peso de cada uno.

Todos los números salen de `outputs/canales/`, `outputs/panel/` y `outputs/panel_ml/`.

## 1. Ponderación de canales (nacional)

Modelo: Δ logit de la mora con un regresor por canal y rezagos elegidos por BIC dentro de grillas económicas (`src/mora/canales.py`). Muestra limpia (2018-2026, n = 77), la única con salario real. Descomposición histórica por simulación contrafáctica: aporte de cada canal = mora simulada con datos reales − mora simulada con ese canal neutral. La simulación con datos reales reproduce exactamente la mora observada.

Ventana: del mínimo de 2024 (oct-24, 2,49%) al último dato (ago-26, 12,81%): **+10,3 pp**.

| Canal | Pública | Mix | Seleccionada | Lectura |
|---|---|---|---|---|
| Costo financiero (tasa real del CFT, t−6) | +8,2 pp | +8,3 | +8,2 | El mayor aporte. Significativo con las tres mediciones (p de 0,02 a 0,05). Banda muy amplia (de ~0 a 34-41 pp): el coeficiente se estima con poca precisión y el contrafáctico extrapola lejos |
| Ciclo de crédito (t−18) | +3,6 | +3,5 | +3,3 | Significativo. A nivel nacional el coeficiente es negativo: la contracción real del crédito 18 meses antes (2023-24) achica el denominador y empuja el ratio |
| Poder de compra (salario real, t−6) | +1,0 | +1,8 | +2,6 | **Significativo sólo con las mediciones mix (p = 0,03) y seleccionada (p = 0,006)**. Con la oficial, no (p = 0,10) |
| Ancla cambiaria (tipo de cambio real, t−9) | +1,4 | +1,9 | +2,5 | No significativo (p de 0,08 a 0,30) |
| Esterilización (Δ títulos + pases / activo, t−12) | −3,3 | −3,1 | −2,9 | No significativo (banda de −10 a +9 pp). En la ventana la absorción bajó (la plata pasó al crédito) |

Los aportes no suman exactamente 10,3 pp: el logit no es lineal y los canales interactúan.

**Lecturas:**
1. **El costo financiero es el canal dominante en las tres mediciones.** Explica alrededor de la mitad de los aportes positivos.
2. **La hipótesis de la medición se confirma en este modelo.** Con la canasta actualizada (o el mix), el poder de compra pasa a ser un canal significativo y su aporte se duplica o más (de 1,0 a 1,8-2,6 pp). La estadística oficial subestima el canal ingreso.
3. **La esterilización no aparece como canal propio, pero eso no la descarta.** Opera a través de las tasas: el encaje integrable con títulos y la absorción del Tesoro sostienen el costo del crédito, cuyo efecto ya está dentro del canal costo financiero. Separar "tasa alta por política" de "tasa alta por riesgo" requiere un modelo de mediación (pendiente).
4. **Ancla cambiaria:** aporte positivo con las tres mediciones, pero sin significancia. Con un solo episodio de apreciación con intervención, los datos no alcanzan para afirmarlo.

## 2. Panel por entidad (66 entidades, 2011-2026)

Efectos fijos de entidad y de mes: la macro común queda absorbida.

- **La cosecha existe a nivel banco.** 10 pp más de crecimiento real del crédito al consumo entre t−24 y t−12 → +0,35 pp de variación interanual de la mora (p < 0,001). A nivel nacional la dilución la tapa; entre bancos aparece.
- **La exposición al sector público no tiene efecto diferencial.** En el estudio de eventos del apretón de jul-2025, las entidades más expuestas a títulos y pases no prestaron menos ni tuvieron más mora: ningún coeficiente es significativo al 5%, y a 12 meses tienen algo menos de mora (p = 0,08). La esterilización es un shock común a todo el sistema: el diseño entre bancos no la puede ver, y por eso su peso se mide en la ecuación nacional.

## 3. ML causal y alerta temprana

| Método | Efecto cosecha (pp de mora por 10 pp de crecimiento) |
|---|---|
| Panel con efectos fijos | 0,35 (p < 0,001) |
| Double ML (LightGBM, 5 folds, 3 repeticiones, clusters por entidad) | 0,14 (p = 0,049) |
| Causal Forest (ATE) | 0,20 (IC 95%: 0,03 a 0,37) |

**Heterogeneidad (Causal Forest):** el efecto es mayor en entidades con más tarjetas (0,27 en el cuartil superior contra 0,05 en el inferior), más grandes y más expuestas al sector público, y desde dic-2023 (0,26 contra 0,19).

**Alerta temprana** (pronóstico de la suba de mora de cada entidad a 12 meses; entrenamiento con datos anteriores a 2023, evaluación 2024-2025):

| Modelo | RMSE | Precisión en el decil de mayor riesgo |
|---|---|---|
| Sin cambio (ingenuo) | 9,17 | — |
| Lineal | **7,97** | 30% |
| LightGBM | 8,28 | **46%** |

El lineal pronostica mejor el nivel; LightGBM identifica mejor a las entidades que más se deterioran (46% de acierto contra 10% al azar). SHAP: crecimiento del crédito, mora actual, empleo y tasa real.

## Pendiente

- Modelo de mediación: cuánto del costo financiero se explica por política monetaria (encajes, absorción, TAMAR) y cuánto por riesgo.
- Carga financiera de los hogares (cuota / ingreso), para verificar la afirmación de ~25% del salario.
- REM como expectativa de inflación.
- Ponderación de canales con bootstrap en vez de bandas por IC del coeficiente.

## 4. Mediación: ¿el costo financiero viene del fondeo o del spread?

Variante `costo_dividido` de `mora.canales`: la tasa real del CFT se reemplaza por dos regresores, la tasa real de fondeo (BADLAR, la tasa que mueve la política monetaria) y el spread de la tasa de préstamos personales sobre la BADLAR. Ventana: oct-24 → ago-26.

| Componente | Pública | Mix | Seleccionada |
|---|---|---|---|
| Spread personales − BADLAR (t−12) | +8,3 pp (p < 0,001) | +8,2 pp (p < 0,001) | +7,5 pp (p < 0,001) |
| Tasa real de fondeo (t−6) | +0,4 (p = 0,73) | +0,5 (p = 0,70) | +1,1 (p = 0,21) |

**Lectura:** el efecto del costo financiero sobre la mora pasa por el spread, no por la tasa de fondeo. Entre jun-25 y ago-26 la TAMAR fue de 22% a 53% y volvió, pero la tasa a familias se quedó en 65-83%: el spread pasó de 21 pp (ago-25) a 41-44 pp.

**Salvedades:**
- Parte del spread es *consecuencia* de la mora (los bancos cobran el riesgo). El rezago de 12 meses mitiga la causalidad inversa, pero no la elimina.
- Con datos públicos el spread no se puede separar en riesgo, costos y **costo de oportunidad de prestarle al Estado**. Si una Lecap rinde 28-42% sin riesgo, ese rendimiento pone un piso a la tasa de un préstamo a familias. Esa es la vía por la que la esterilización encarecería el crédito sin pasar por la BADLAR. Para medirla hace falta la serie de rendimientos de Lecap/Boncap (pendiente: resultados de licitaciones de la Secretaría de Finanzas).

## 5. Ventana del ajuste (nov-23 → hoy)

`python -m mora.ajuste` (outputs en `outputs/ajuste/`).

- Crédito privado en pesos: 9,3% del PBI en nov-23, 11,7% en nov-25 y 11,1% al último dato. En feb-24 la exposición de los bancos al Estado (títulos + pases, moneda nacional) era 18,8% del PBI, contra 8,4% de crédito privado.
- Salario real contra nov-23: −8,7% con la medición pública, −10,2% con la mix y −11,6% con la seleccionada.
- **Castigos y el freno reciente de la mora:** en jun-26 y jul-26 el stock irregular de familias creció $59 y $22 mil millones reales, mientras se castigaban unos $238 y $189 mil millones atribuibles a familias (estimado: castigos totales × participación de las familias en el stock irregular). Sin castigos, el stock habría crecido unos $298 y $211 mil millones. El freno de la mora es, en buena parte, contable.
- Empresas: la mora bajó de 2,7% a 0,7% (nov-24) con el boom de crédito y volvió a 3,8%. Embargos de ARCA y cheques rechazados: sin series públicas (contexto de prensa).
