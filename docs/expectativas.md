# Chequeo: inflación esperada del REM

`python -m mora.expectativas` (outputs en `outputs/expectativas/`). Corre en la actualización semanal.

En todo el proyecto la tasa real se calcula con la inflación de los últimos 3 meses anualizada (`mora.features.inflacion_esperada`). La alternativa es la mediana del Relevamiento de Expectativas de Mercado (REM) del BCRA a 12 meses (API del BCRA, variable 29). El REM es sobre el IPC oficial, así que se compara sólo con la medición pública. Las dos medidas difieren mucho en la desinflación: en ene-24 la retrospectiva anualizada daba 749% y el REM 183%.

| Medida de inflación esperada | Inflación reciente (principal) | REM |
|---|---|---|
| Satélite 2017+: coeficiente de la tasa real (logit, por pp) | 0,00035 (p = 0,015) | 0,00050 (p = 0,030) |
| Satélite 2017+: signos esperados en todas las variables | sí | no (otro regresor) |
| Cadena, etapa 2: aporte de la tasa a la suba de la mora | +8,3 pp (p = 0,026) | +9,7 pp (p = 0,001) |
| Cadena, etapa 1: tasa real del CFT, antes → ventana | 25% → 62% | 38% → 85% |
| Cadena, etapa 1: peso de lo que paga el Estado (contable) | 41% | 30% |

**Lectura:**
- **La conclusión central se refuerza con el REM:** la tasa real pesa más en la suba de la mora y con más precisión.
- El peso contable de lo que paga el Estado baja de 41% a 30%. Coincide con el reparto que tiene en cuenta el traspaso estimado en tasas nominales (0,75), que con la medida principal da 30-31%. Las dos vías llevan a ~30%, que es el número más defendible. El 41% es una cota superior.
- Este chequeo fue el que destapó un error: el traspaso medido en tasas reales daba 1,05-1,08 porque las dos tasas comparten la inflación esperada que se les resta. Ahora se mide en nominales (ver `docs/fase5_resultados.md`, sección 7).
