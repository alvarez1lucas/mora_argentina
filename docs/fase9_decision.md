# Fase 9: capa de decisión para el otorgamiento

`python -m mora.decision` (outputs en `outputs/decision/`). Convierte las conclusiones del proyecto en dos insumos de política de crédito, por línea:

1. **Ajuste de la PD por escenario:** cuánto mover el punto de corte de aprobación.
2. **Tasa mínima de originación:** a qué tasa conviene prestarle a una familia en lugar de prestarle al Estado.

Todas las cifras salen de `resumen_decision.json`, `pd_por_escenario.csv`, `cortes_aprobacion.csv` y `tasa_minima_originacion.csv`. Las de este documento corresponden a la medición pública.

## Qué no es

No es un modelo de scoring: no hay datos por solicitante, y la Central de Deudores no se usa, por privacidad. Es la **capa macro** que en la práctica bancaria se aplica encima del scoring individual (ajuste point-in-time de la PD, pricing por riesgo). La PD que usa es la **mora de la línea** (stock irregular sobre cartera), una proxy de la PD *promedio* de la cartera, no de la PD marginal de un solicitante. Como incluye deuda en situación 5 que todavía no se castigó, **probablemente sobrestima la PD a 12 meses**, y por lo tanto también la tasa mínima.

## 1. PD por escenario y punto de corte

La mora de cada línea se proyecta desde la mora total del escenario con su sensibilidad histórica: Δ12 del logit de la línea contra el de la total, 2017+. Personales: β = 0,98 (error estándar 0,02). Tarjetas: β = 1,24 (0,05).

| Línea | Promedio del ciclo (TTC) | Hoy | Base | Adverso | Favorable | NIIF 9 |
|---|---|---|---|---|---|---|
| Personales | 5,5% | 17,0% | 20,8% | 25,3% | 17,6% | 21,6% |
| Tarjetas | 3,6% | 12,2% | 16,0% | 20,8% | 12,8% | 16,7% |

Con la medición seleccionada la PD base es más baja (personales 18,3%, tarjetas 13,5%), porque su escenario base también lo es.

**Punto de corte equivalente.** Un modelo de scoring calibrado sobre el promedio del ciclo (TTC) que aprueba a quien tenga PD < c tiene que aprobar con PD < c' para mantener el mismo riesgo efectivo. El ajuste es un desplazamiento en el logit, de 1,5 en personales y 1,6 en tarjetas en el base:

| Corte TTC | Personales: base | Personales: adverso | Tarjetas: base | Tarjetas: adverso |
|---|---|---|---|---|
| 10% | 2,4% | 1,9% | 2,1% | 1,6% |
| 20% | 5,3% | 4,1% | 4,7% | 3,4% |

**Lectura:** un modelo que en un año normal aprobaba al 10% más riesgoso hoy sólo debería aprobar a quien en un año normal habría tenido 2,4% de PD. Eso es **racionamiento de crédito**, y explica por qué el crédito real al consumo cae aunque los bancos tengan fondeo: el riesgo efectivo de cada perfil se multiplicó por ~4.

## 2. Tasa mínima de originación (préstamos personales)

Un préstamo a un año rinde (1 + r) si se paga y recupera (1 − LGD) del capital si no. Tasa mínima para empatar lo que rinde el Estado (títulos + pases en pesos: **38,0% TEA**, jul-26) más el costo operativo:

r_min = [(1 + r_Estado + costo) − PD·(1 − LGD)] / (1 − PD) − 1

Supuestos centrales: LGD 75%, costo operativo 12 pp. Tasa de mercado de préstamos personales (BCRA, sep-26): 62,4% TNA = **83,8% TEA**.

| Escenario | PD 12 m | TEA mínima | CFT mínimo (con IVA) | Margen sobre el mercado |
|---|---|---|---|---|
| Favorable | 17,6% | 76,8% | 98,6% | +7,0 pp |
| Base | 20,8% | 82,9% | 106,9% | **+0,9 pp** |
| NIIF 9 ponderado | 21,6% | 84,4% | 108,8% | −0,6 pp |
| Adverso | 25,3% | 92,4% | 119,7% | −8,6 pp |
| Adverso (percentil 95) | 34,9% | 117,1% | 153,9% | −33,3 pp |

**PD de equilibrio** a la tasa de mercado: 21,3% (supuestos centrales); de 17,1% a 26,3% según LGD y costo.

**Sensibilidad del margen en el escenario base (pp):**

| LGD \ costo operativo | 8 pp | 12 pp | 16 pp |
|---|---|---|---|
| 60% | +9,9 | +4,8 | −0,2 |
| 75% | +5,9 | +0,9 | −4,2 |
| 90% | +2,0 | −3,1 | −8,1 |

**Lectura:**
- **A la tasa promedio de mercado, prestarle a una familia empata con prestarle al Estado en el escenario base, y pierde en el adverso.** Con lo que paga el Estado como piso, el riesgo actual no deja margen. Es la traducción operativa del hallazgo de la Fase 5: la esterilización pone un piso a la tasa, y con la mora en 13% ese piso se come el margen.
- Por eso los bancos **racionan** (suben el corte) y **segmentan**. En transparencia, la mediana del CFT de préstamos personales de 42 bancos es 147,8%, muy por encima del CFT mínimo del base (106,9%). El 24% ofrece por debajo: son sobre todo bancos con clientes de haberes, cuya PD es menor que la promedio.
- La tasa promedio del BCRA está sesgada hacia los préstamos a clientes de haberes y de menor riesgo, y por eso el margen promedio parece chico. El margen sobre el resto de la cartera depende del segmento.

Para tarjetas se calcula la tasa mínima (CFT mínimo del base: 94,6%), pero no hay una serie de tasa de mercado contra la cual compararla.

## Cómo se usaría en un banco

1. El modelo de scoring individual da una PD calibrada al promedio del ciclo.
2. Se le suma el desplazamiento logit del escenario elegido (o del ponderado NIIF 9) → PD del momento.
3. Se aprueba si la tasa que el cliente acepta supera la tasa mínima con *su* PD (no la promedio), con la tasa del Estado del mes como piso.
4. Si cambia el escenario macro o lo que paga el Estado, se recalculan los cortes y las tasas sin reentrenar el scoring.

## Límites

- La PD es una proxy agregada (stock irregular), probablemente sobrestimada; no hay PD marginal por solicitante.
- La LGD y el costo operativo son supuestos, no datos: por eso la tabla de sensibilidad.
- El modelo es a un año, sin capital regulatorio, sin impuestos además del IVA (por ejemplo, ingresos brutos) y sin el valor de la relación con el cliente (venta cruzada, acreditación de haberes), que en la práctica justifica prestar con margen negativo a algunos segmentos.
