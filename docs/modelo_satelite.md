# Modelo satélite (Fase 4): decisiones y resultados

Código: `src/mora/satelite.py`. Outputs: `outputs/modelo/`. Todos los números de este documento salen de esos archivos (corrida del 27/10/2026).

## Especificación

Δ logit(mora familias)_t = c + φ₁Δy_{t-1} + φ₂Δy_{t-2} + Σ_k β_k x_{k,t-L_k} + e_t, con errores HAC (Newey-West).

| Decisión | Justificación |
|---|---|
| Mora en logit y primera diferencia | El logit acota el ratio. En nivel es I(1): ADF p = 0,80 y KPSS p = 0,017; en diferencia, estacionaria. Zivot-Andrews (con un quiebre endógeno) tampoco rechaza la raíz unitaria (p = 0,11) y ubica el quiebre en dic-2023. |
| Regresores en variación interanual | Estacionarios (tasa real y crédito, según ADF y KPSS) o con KPSS que no rechaza estacionariedad (salario, empleo, EMAE). Regresión balanceada: no hay correlación espuria entre tendencias. |
| Un rezago por regresor, grilla acotada | La mora es atraso de más de 90 días: nada actúa antes de 3 meses. Grilla de 3-12 meses para tasa e ingreso y de 12-18 para crédito. Dentro de la grilla se elige por BIC, con todas las combinaciones estimadas en la misma muestra. |
| Tasa real = CFT aproximado (TNA + IVA) deflactado por la inflación de 3 meses anualizada | Con la inflación de 12 meses previa, la tasa real de 2024 daba −40% cuando era muy positiva (la desinflación fue brusca). Se reemplaza por el REM cuando esté ingresado. |
| Ventana COVID excluida (alivio de clasificación + 6 meses) | A 6938 / A 7245: la mora medida bajó artificialmente. Con la ventana adentro, el salto al desarmarse el alivio se propagaba por los términos AR y los pronósticos de mediados de 2021 explotaban (errores de 40-50 pp a 12 meses). |
| Signos esperados | Tasa real +; salario, empleo y EMAE −. Se elige el menor BIC entre las especificaciones con esos signos (práctica estándar en stress testing). |
| Crédito previo sin restricción de signo | Tiene dos efectos opuestos: dilución del denominador (−) y cosecha (+). Con la ecuación base, el coeficiente es + a 6 meses (p = 0,10), − entre 12 y 21 meses (p < 0,01), ≈ 0 a 24 y + no significativo a 27-30. A nivel nacional domina la dilución; la cosecha se busca en el panel por entidad (Fase 5). |

## Resultados

Especificaciones elegidas:
- base / larga (2013-2026, n = 140): tasa real (t−6), empleo (t−3), EMAE (t−3), crédito (t−15), AR(2). R² ajustado 0,53.
- base / limpia (2018-2026, n = 80): tasa real (t−6), empleo (t−6), EMAE (t−3), crédito (t−15), AR(2). R² ajustado 0,58.
- completa / limpia (n = 77): tasa real (t−6), salario real (t−6), EMAE (t−9), crédito (t−18), AR(2). R² ajustado 0,57.

**Hallazgo robusto:** la tasa real (CFT) rezagada 6 meses es positiva y significativa en las dos muestras de la especificación base (p = 0,012 y 0,015). El salario real, el empleo y el EMAE no resultan significativos al 5%.

**Evaluación fuera de muestra** (ventana expansiva; en cada origen se re-eligen los rezagos sólo con datos hasta ese mes). RMSE en puntos porcentuales de mora:

| Muestra | h | Satélite | AR(1) | Paseo aleatorio |
|---|---|---|---|---|
| larga | 3 | **0,42** | 0,56 | 0,86 |
| larga | 6 | **0,88** | 1,31 | 1,69 |
| larga | 12 | **2,25** | 2,92 | 3,12 |
| limpia | 3 | 0,67 | 0,65 | 1,08 |
| limpia | 12 | 3,76 | 3,43 | 3,85 |

En la muestra larga el satélite le gana a los dos benchmarks en todos los horizontes. En la limpia, con 80 observaciones, empata con el AR(1) hasta 6 meses y pierde a 12. **Lectura honesta:** la ventaja del modelo depende de tener la historia larga; con la muestra limpia sola, la macro no agrega poder predictivo por sobre la inercia a 12 meses. Para escenarios condicionales (Fase 6) se usa la base / larga, y la limpia queda como chequeo de robustez de los signos.

## Limitaciones

- Un solo episodio de suba grande (2025-26): los coeficientes los identifica sobre todo ese episodio.
- El CFT es una cota inferior (sin seguros ni gastos) y la expectativa de inflación es adaptativa hasta tener el REM.
- La ventana COVID excluida saca 21 meses de datos.
- Los errores de pronóstico a 12 meses son grandes en cualquier modelo (2-4 pp): la incertidumbre de los escenarios tiene que mostrarse.

## Robustez de medición: tres mediciones de precios

`python -m mora.robustez` corre el modelo completo con cada deflactor (ver `src/mora/deflactores.py`). Outputs en `outputs/robustez/`; comparación lado a lado en `comparacion.csv`.

Inflación acumulada por etapa (`inflacion_por_periodo.csv`):

| Etapa | Pública | Seleccionada (ENGHo 2017/18) | Mix | IPCBA |
|---|---|---|---|---|
| INDEC intervenido (jul-12 → dic-16) | 125,7% | 238,4% | 176,4% | 243,1% |
| Tarifas congeladas (dic-16 → nov-23) | 2.716% | 2.637% | 2.676% | 2.463% |
| Ajuste (nov-23 → sep-26) | 344,4% | 360,2% | 352,2% | 367,2% |

Resultados del modelo con cada medición:

- **Tasa real (CFT):** positiva y significativa en 8 de 9 corridas (p entre 0,001 y 0,015). La excepción es la muestra larga con la medición seleccionada: ahí el coeficiente cambia de signo y no hay especificación que cumpla los signos esperados. El tramo 2012-2016 con inflación IPCBA (mucho más alta que la oficial) produce tasas reales muy negativas en un período de mora estable. **Conclusión: el canal tasa es robusto a la medición en la muestra limpia y en la larga con las mediciones pública y mix; en la larga con la seleccionada no lo es.**
- **Salario real:** no significativo con ninguna medición (p entre 0,67 y 0,87). La hipótesis de que una medición más realista de precios haría aparecer el canal ingreso **no se confirma en este modelo nacional**. Salvedades: el índice de salarios es de asalariados registrados (no capta a los informales) y la diferencia agregada entre mediciones en la etapa de ajuste es de ~3,5% en el nivel de precios.
- **Crédito previo (dilución):** negativo y significativo en 8 de 9 corridas.
- **Fuera de muestra:** en la muestra larga el satélite le gana al AR(1) con las tres mediciones (RMSE relativo a 6 meses de 0,67 a 0,82); en la limpia no, con ninguna.
