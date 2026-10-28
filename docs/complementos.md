# Análisis complementarios

`python -m mora.complementos` (outputs en `outputs/complementos/`). Son chequeos de robustez del modelo principal. **No están integrados** al sitio, al README ni al workflow semanal: se corren a mano. El bootstrap tarda ~10 minutos.

## 1. ARDL con bounds test: ¿hay relación de largo plazo?

Pesaran, Shin y Smith (2001), caso 3 (constante sin restricción). Variables en niveles: logit de la mora, tasa real del CFT, log del salario real registrado y log del crédito real al consumo. La ventana del alivio COVID entra como regresor fijo. Los rezagos se eligen por BIC (hasta 6), con mínimo 1 por regresor para la forma de corrección de errores. El test es válido con regresores I(0) o I(1). Output: `ardl_bounds.json`.

| Muestra | Medición | n | F | Cota I(1) al 5% | Resultado | Velocidad de ajuste (por mes) |
|---|---|---|---|---|---|---|
| Larga | Pública | 125 | 5,65 | 4,01 | Cointegración | −0,084 |
| Larga | Mix | 126 | 11,12 | 4,01 | Cointegración | −0,165 |
| Larga | Seleccionada | 126 | 10,66 | 4,01 | Cointegración | −0,167 |
| Limpia | Pública | 111 | 10,70 | 4,01 | Cointegración | −0,169 |
| Limpia | Mix | 111 | 10,38 | 4,01 | Cointegración | −0,171 |
| Limpia | Seleccionada | 111 | 10,00 | 4,01 | Cointegración | −0,172 |

**Coeficientes de largo plazo (logit)** muy estables entre las 6 corridas: salario real −4,82 a −4,95, crédito real +1,74 a +1,83, tasa real +0,0012 a +0,0032 por pp.

**Lectura:**
- **La relación en niveles no es espuria.** Mora, tasa, salario y crédito comparten una tendencia de largo plazo con las tres mediciones y en las dos muestras. Es el respaldo formal de que modelar en diferencias no tiraba información de largo plazo.
- **En el largo plazo, el salario real es la variable de mayor peso.** Con la mora actual (12,8%), 1% más de salario real equivale a ~0,5 pp menos de mora (−4,9 × 0,01 × p(1−p)). La tasa real pesa en el corto plazo: 10 pp más de tasa equivalen a ~0,2 pp en el largo plazo. Encaja con la lectura de los canales: el costo financiero dispara la mora y el ingreso define dónde se estabiliza.
- Más crédito real, más mora en el largo plazo: el efecto cosecha.
- La mora corrige entre el 8% y el 17% del desvío por mes, una vida media de 4 a 8 meses.

**Límites:** la "larga" arranca de hecho cuando empieza la serie de salarios, por eso tiene casi las mismas observaciones que la limpia. El bounds test no contempla quiebres estructurales más allá de la ventana COVID.

## 2. Proyecciones locales (Jordà)

Una regresión por horizonte h = 0…18: y(t+h) − y(t−1) contra el regresor en t, controlando por 3 rezagos de Δy, del propio regresor y de los controles (salario real o tasa real, según el caso, y actividad). Muestra limpia, sin las filas en que t o t+h caen en la ventana COVID, con errores HAC(h+1). Respuesta en pp de mora a la mora media de la muestra, por 1 pp del regresor. Output: `proyecciones_locales.csv`.

| Shock (1 pp) | h = 6 | h = 9 | h = 12 | h = 18 |
|---|---|---|---|---|
| Tasa real del CFT, pública | +0,016 (p = 0,24) | +0,027 (p = 0,12) | +0,023 (p = 0,10) | +0,017 (p = 0,46) |
| Salario real, pública | +0,020 (p = 0,71) | +0,024 (p = 0,66) | −0,010 (p = 0,71) | −0,116 (p < 0,001) |

**Lectura:** la forma coincide con la del modelo satélite: la tasa real pega con un pico a los 9-12 meses, y el salario pega más tarde y de manera más persistente. Pero **con proyecciones locales el efecto de la tasa no llega a ser significativo** (p de 0,10 a 0,15 en las tres mediciones). Las proyecciones locales son menos eficientes que un modelo dinámico, porque estiman una regresión por horizonte con cada vez menos datos (56 observaciones a h = 18). Es una advertencia honesta: la evidencia del canal tasa descansa en la estructura del modelo dinámico.

## 3. Bootstrap por bloques de la ponderación de canales

300 repeticiones por medición y variante. Se remuestrean los residuos en bloques de 12 meses, se reconstruye la mora con la dinámica estimada, se reestima la misma especificación y se recalcula el aporte de cada canal sobre los datos observados. Output: `bootstrap_canales.csv`.

Comparación con las bandas publicadas, que mueven un coeficiente por vez (medición mix):

| Canal | Aporte | Bootstrap 95% | Banda por IC del coeficiente | P(aporte > 0) |
|---|---|---|---|---|
| Costo financiero | +8,3 pp | 3,0 a 10,4 | 0,2 a 37,7 | 100% |
| Lo que paga el Estado (variante costo de oportunidad) | +5,3 | −0,1 a 7,5 | 0,7 a 11,2 | 97% |
| Prima de familias | +5,3 | −2,2 a 8,2 | −0,7 a 25,2 | 90% |
| Poder de compra (base) | +1,8 | 0,1 a 2,7 | 0,1 a 3,7 | 98% |
| Ciclo de crédito (base) | +3,5 | −0,4 a 5,6 | 0,1 a 7,8 | 95% |
| Ancla cambiaria (base) | +1,9 | −1,0 a 3,7 | −0,7 a 5,1 | 91% |
| Absorción directa (base) | −3,1 | −8,8 a 3,0 | −9,7 a 8,6 | 24% |

**Lectura:**
- **El bootstrap confirma el orden de los canales y acota mucho las bandas de arriba.** La banda por IC del coeficiente llegaba a 38-41 pp para el costo financiero porque extrapola el logit lejos; con el bootstrap el aporte queda entre 2 y 10 pp, siempre positivo.
- **Lo que paga el Estado** sale positivo en el 97-98% de las repeticiones, con el límite inferior pegado a cero. Es robusto, pero no holgado.
- **Poder de compra:** positivo en el 94% de las repeticiones con la medición pública y en el 99-100% con la seleccionada. Se sostiene la lectura de que la medición oficial subestima este canal.
- Absorción directa: no se puede distinguir de cero (24-51%), como en la estimación principal.

**Límite:** la especificación (los rezagos) queda fija, así que la incertidumbre de elegirla no entra en las bandas.
