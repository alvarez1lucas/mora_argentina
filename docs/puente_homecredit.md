# Puente con homecredit-pd-validation

`python -m mora.puente_homecredit [--actualizar]` (outputs en `outputs/puente_homecredit/`).

[homecredit-pd-validation](https://github.com/alvarez1lucas/homecredit-pd-validation) tiene un modelo de PD individual calibrado (y validado) sobre el dataset público de Home Credit. Este puente toma la distribución de sus PD del set de prueba (61.503 solicitudes; PD media 7,9%, default observado 8,1%) como si fuera la de un modelo de scoring calibrado en un año normal y le aplica la capa macro de la Fase 9.

Se versiona sólo una tabla derivada: 500 tramos con la PD media y el default observado (`data/processed/homecredit_pd_cuantiles.csv`). Con `--actualizar` se regenera desde el repo local (ruta en `config/settings.yaml`).

**Dos reglas de corte**, con la misma tasa de mercado (83,8% TEA), LGD 75% y costo operativo de 12 pp:
- **Sólo pérdida esperada** (la regla para Argentina del proyecto Home Credit): PD\* = r / (r + LGD) = **52,8%**.
- **Con costo de oportunidad** (Fase 9): el préstamo tiene que empatarle a lo que paga el Estado (38,0%) más el costo operativo: PD\* = **21,3%**.

| Escenario (Δ logit) | Aprobación, sólo pérdida esperada | PD media aprobados | Aprobación, con costo de oportunidad | PD media aprobados |
|---|---|---|---|---|
| Año normal (0) | 100% | 7,9% | 93% | 6,4% |
| Hoy (1,26) | 95% | 18,9% | 62% | 11,3% |
| Base (1,51) | 92% | 21,5% | 52% | 12,2% |
| Adverso (1,76) | 88% | 24,1% | 42% | 13,0% |

**Lectura:**
- Con la regla de sólo pérdida esperada casi no cambia nada aunque el riesgo se multiplique, porque el corte (52,8%) queda muy lejos. Pero la cartera aprobada en el escenario base tiene una PD media de 21,5%, por encima del 21,3% en el que prestar empata con el Estado: en promedio, pierde contra el costo de oportunidad.
- Con el costo de oportunidad, en el base se aprueba al 52% de los solicitantes. Es la medida concreta del racionamiento de crédito del sitio.
- **Para el proyecto Home Credit:** su corte para Argentina ignora el costo de oportunidad. Con tasas reales altas y un Estado que paga 38%, la regla r / (r + LGD) aprueba préstamos que no convienen. Es una mejora a incorporar allá (no se modificó ese repo desde acá).

**Límites:** Home Credit no es una cartera argentina; su PD media (7,9%) es mayor que la PD del ciclo de los préstamos personales argentinos (5,5%), así que el nivel de las PD ajustadas es más alto que el de la Fase 9. El ejercicio muestra la forma del efecto, no su nivel exacto.
