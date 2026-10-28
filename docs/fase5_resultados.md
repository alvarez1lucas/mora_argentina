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
3. **La esterilización no aparece como canal propio, pero eso no la descarta** (ver la sección 7, que reemplaza esta ponderación por una en dos etapas). Opera a través de las tasas: el encaje integrable con títulos y la absorción del Tesoro sostienen el costo del crédito, cuyo efecto ya está dentro del canal costo financiero. Separar "tasa alta por política" de "tasa alta por riesgo" requiere un modelo de mediación (pendiente).
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

## 6. Costo de oportunidad: cuánto rinde prestarle al Estado

`python -m mora.rendimientos` (outputs en `outputs/rendimientos/`).

No hay una serie pública de rendimientos de Lecap/Boncap. Se reemplaza por algo más directo: **lo que los bancos efectivamente ganaron** con títulos públicos y pases con el BCRA en pesos (cuentas de resultados del balance de cada entidad), dividido por el stock de esos activos. Es el costo de oportunidad de prestarle a una familia.

Tratamiento contable: las cuentas de resultados vienen acumuladas en el año y, desde 2020, reexpresadas por inflación (NIC 29). El flujo de cada mes se obtiene llevando el acumulado del mes anterior a moneda del mes. Sin esa corrección dic-23 da rendimientos de miles por ciento; con ella, 213% (Leliq al 133% TNA) y ~35% en jul-25 (LEFI/Lecap ~2,7% mensual).

| Promedio anual (TEA, %) | Estado (títulos + pases, 3 meses) | Préstamos personales nuevos | BADLAR | Prima de familias sobre el Estado |
|---|---|---|---|---|
| 2024 | 138,6 | 136,3 | 77,4 | −2,2 pp |
| 2025 | 46,4 | 104,3 | 41,7 | +57,9 pp |
| 2026 | 41,8 | 92,7 | 28,2 | +50,8 pp |

**Lecturas:**
- Desde nov-23, en el 85% de los meses **el Estado le pagó a los bancos más que la BADLAR**. En 2026 la diferencia es de 5 a 21 pp. La tasa de fondeo subestima el costo de oportunidad, y por eso la mediación con la BADLAR (sección 4) no encontraba el canal.
- En la variante `costo_oportunidad` de la ponderación de canales, la tasa a familias se separa en *lo que rinde el Estado* y *la prima sobre el Estado*:

| Componente (oct-24 → ago-26) | Pública | Mix | Seleccionada |
|---|---|---|---|
| Rendimiento real del Estado (t−6) | +5,6 pp (p = 0,023) | +5,3 pp (p = 0,021) | +5,0 pp (p = 0,021) |
| Prima de familias sobre el Estado (t−3) | +5,2 (p = 0,18) | +5,3 (p = 0,15) | +5,2 (p = 0,13) |

**Conclusión:** la esterilización sí aparece, pero no por la BADLAR, sino por el **piso que pone lo que paga el Estado**. Es significativa con las tres mediciones y explica cerca de la mitad de la suba de la mora en la ventana. La prima propia del riesgo de familias suma otro tanto, pero no es significativa.

**Salvedades:** el rendimiento incluye ganancias de valuación de los bonos (ruidoso: se usa el promedio de 3 meses); son 77 observaciones; y el rendimiento del Estado y la prima están correlacionados entre sí, por lo que la división entre ambos es menos precisa que su suma.

## 7. Ponderación en dos etapas: esterilización → tasa → mora

`python -m mora.cadena` (outputs en `outputs/cadena/`). **Reemplaza a la sección 1 como ponderación principal** (es la que muestran el sitio, el README y el informe).

**Por qué.** La esterilización y la tasa no son canales paralelos: la esterilización es causa de la tasa. Para absorber pesos, el BCRA y el Tesoro les pagan a los bancos una tasa que los convenza de comprar títulos o hacer pases; cada peso prestado a una familia deja de ganar esa tasa sin riesgo, así que lo que paga el Estado es el piso de la tasa a familias. En la sección 1 la absorción (cantidad) y la tasa entraban juntas en la ecuación de la mora: el efecto de la esterilización que pasa por la tasa quedaba contado en la tasa y a la absorción le quedaba sólo el efecto directo, que no se distingue de cero (−3,1 pp). Eso subestimaba la esterilización por diseño, no por los datos.

**Etapa 1: qué subió la tasa.** Identidad exacta de la tasa real del CFT de préstamos personales (misma inflación esperada π que el modelo):

tasa real CFT = (r_Estado − π)/(1 + π) + (TEA − r_Estado)/(1 + π) + (CFT − TEA)/(1 + π)

lo que paga el Estado (real) + prima del banco sobre el Estado + IVA sobre los intereses. Suba de cada parte sobre su promedio previo (2017 → oct-24) en los meses que, con el rezago de 6 meses de la etapa 2, mueven la mora de la ventana (may-24 → feb-26). La tasa real pasó de ~25% a ~61-62%:

| Parte | Pública | Mix | Seleccionada | Peso en la suba de la tasa |
|---|---|---|---|---|
| Lo que paga el Estado | +14,9 pp | +14,4 | +13,8 | 39-41% |
| Prima del banco sobre el Estado | +15,1 | +15,0 | +14,9 | 41-43% |
| IVA sobre los intereses | +6,4 | +6,3 | +6,2 | 18% |

**Traspaso.** Δ12 de la tasa real de los préstamos (sin IVA) contra Δ12 de lo que paga el Estado, controlando por la Δ12 de la mora 3 meses antes, HAC(12), 2018-2026 (n = 100): β = 1,05-1,08 (error estándar ~0,11, p < 0,001). La mora previa no es significativa (p > 0,8). **El piso se traslada uno a uno**, y la prima no subió como reacción al riesgo pasado.

**Etapa 2: qué subió la mora.** La ecuación de canales sin la absorción: salario real (t−6), tasa real del CFT (t−6), tipo de cambio real (t−9), crédito real (t−15), AR(2); signos correctos, R² ajustado 0,58-0,59, n = 77. El aporte de la tasa se reparte entre sus partes poniendo cada una en su promedio previo. El reparto se hace en el logit, donde la ecuación es lineal y las partes suman exacto, y se pasa a pp en la misma proporción. Ventana oct-24 (2,49%) → ago-26 (12,81%):

| Canal | Pública | Mix | Seleccionada |
|---|---|---|---|
| **Tasa real del CFT** | **+8,3 pp (p = 0,026)** | **+8,3 (p = 0,014)** | **+8,3 (p = 0,007)** |
| · lo que paga el Estado | +3,7 | +3,6 | +3,5 |
| · prima del banco | +3,1 | +3,2 | +3,3 |
| · IVA | +1,5 | +1,5 | +1,5 |
| Ancla cambiaria | +1,4 (p = 0,24) | +1,9 (p = 0,11) | +2,4 (p = 0,04) |
| Poder de compra | +0,7 (p = 0,15) | +1,4 (p = 0,05) | +2,1 (p = 0,009) |
| Ciclo de crédito | +0,5 (p = 0,004) | +0,5 (p = 0,003) | +0,4 (p = 0,002) |

**Lectura:**
- La cadena se sostiene en los dos eslabones: lo que paga el Estado explica ~40% de la suba de la tasa y se traslada completo, y la tasa es el canal dominante de la mora. Por la vía de la tasa, la esterilización aporta ~3,5-3,7 pp de los 10,3 pp de suba de la mora.
- Robustez: con un coeficiente propio para lo que paga el Estado (variante `costo_oportunidad`, sección 6) el aporte es +5,0-5,6 pp. El reparto proporcional es la cota conservadora: supone que un punto de tasa pesa lo mismo venga de donde venga.
- La prima del banco pesa casi lo mismo que el piso del Estado. Con datos públicos no se puede separar en riesgo, costos y margen; que no responda a la mora previa sugiere que no es sólo riesgo.

**Límites:** los intervalos de las partes se mueven con el coeficiente de la tasa (IC 95% de 0,1 a 16 pp para lo que paga el Estado) y son amplios. Lo que paga el Estado también incorpora expectativas de inflación y riesgo soberano, no sólo la decisión de esterilizar. El IVA crece mecánicamente con la tasa: parte de su aporte es amplificación de las otras dos partes.
