# Fase 6: escenarios a 12 meses

`python -m mora.escenarios` (outputs en `outputs/escenarios/`). Todos los números de este documento salen de `resumen_escenarios.json`, `supuestos.csv` y `validacion_canales.csv`.

## Qué modelo proyecta y por qué

| Modelo | Error a 12 meses (RMSE, pp) | AR(1) | Paseo aleatorio | Uso |
|---|---|---|---|---|
| Satélite, muestra 2010+ | 2,25 | 2,92 | 3,12 | **Proyección** |
| Canales, muestra 2017+ | 3,80 | 3,43 | 3,85 | Explicación (no le gana al AR(1)) |

El satélite (tasa real del CFT, empleo, actividad y crédito real) es el único que le gana al AR(1) fuera de muestra en todos los horizontes. El modelo de canales sirve para atribuir la suba pasada, no para proyectar.

**Regla de signos.** Sólo se proyecta con un modelo que respete los signos esperados. Con la medición seleccionada, ninguna especificación de la muestra larga los respeta: su inflación 2010-2016, casi el doble de la oficial intervenida, vuelve muy negativas las tasas reales de una etapa con mora baja y estable, y la tasa aparece restando mora. En ese caso se proyecta con la muestra 2017+. Es una fragilidad que hay que decir: **el modelo largo depende de cómo se mida la inflación del apagón estadístico.**

## Supuestos (calibrados con la historia, no elegidos a mano)

- **Base:** la tasa real del CFT se queda en el promedio de sus últimos 3 meses (~69% real con la medición pública, un nivel históricamente extremo); empleo, actividad y crédito real vuelven a variación interanual cero en 12 meses.
- **Adverso / favorable:** al base se le suma el cambio a 12 meses del percentil 90 / 10 de la historia de cada variable desde 2010, en la dirección que sube / baja la mora según el coeficiente estimado, con entrada gradual en 6 meses. Ejemplo (medición pública): tasa real +33,8 pp / −22,7 pp; actividad −9,1% / +9,3%; crédito real −30,4% / +24,9%.
- **Incertidumbre:** 2.000 simulaciones por escenario con coeficientes sorteados de su distribución (covarianza HAC) y shocks remuestreados de los residuos (sólo de los meses con todos los regresores observados).
- Con rezagos de 3 a 15 meses, el primer o los dos primeros meses ya están determinados por datos observados.

## Resultados (mora de familias en ago-27; hoy 12,81%)

| Medición | Muestra | Base | Adverso | Favorable | 90% de las simulaciones (base) | Ponderado NIIF 9 | P(supera el nivel actual), base |
|---|---|---|---|---|---|---|---|
| Pública | 2010+ | 15,9% | 19,7% | 13,3% | 10,4–22,0% | 16,5% | 81% |
| Mix | 2010+ | 15,7% | 19,2% | 13,3% | 10,0–22,1% | 16,3% | 79% |
| Seleccionada | 2017+ | 13,9% | 16,2% | 12,2% | 7,4–20,5% | 14,2% | 61% |

Ponderación NIIF 9: 60% base, 25% adverso, 15% favorable (configurable). El ajuste forward-looking (ponderado / base) es 1,02-1,03: los escenarios malos pesan más que los buenos por la asimetría de los shocks y del logit.

## Lectura

1. **En el escenario base la mora no baja: sigue subiendo, más despacio.** El motivo es la tasa real: con un CFT real de ~70%, el modelo sigue empujando la mora hacia arriba aunque la actividad y el empleo se estabilicen. Para que la mora baje hace falta que la tasa real baje (escenario favorable), no sólo que la economía deje de caer.
2. **Las bandas son anchas** (de 10 a 22% en el base). Es honesto: hay un solo episodio de este tipo en la muestra, y el error histórico del modelo a 12 meses es de 2,25 pp.
3. **El freno contable de jun-jul 2026 (castigos) no cambia la proyección**: el modelo trabaja con la variación del ratio, y los castigos pueden seguir moderándolo sin que cambie la capacidad de pago.
4. El modelo de canales (referencia) da un base más bajo (10,9–12,2% central), pero pronostica peor que un AR(1): no se usa para proyectar.

## Limitaciones

- Los escenarios son condicionales: no son pronósticos de la tasa, el salario ni la actividad.
- No incluyen cambios regulatorios (por ejemplo, flexibilización de la clasificación de deudores), que pueden mover el ratio sin cambiar la capacidad de pago.
- Los pesos NIIF 9 son una convención de la práctica bancaria, no una estimación.
