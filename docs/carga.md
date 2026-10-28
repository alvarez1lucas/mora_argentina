# Carga financiera de las familias

`python -m mora.carga` (outputs en `outputs/carga/`). Corre en la actualización semanal.

**Medida:** cuota de los préstamos personales sobre la masa salarial registrada.
- Cuota mensual = stock de préstamos personales (BCRA) × (TNA / 12 + 1 / plazo). El plazo promedio no es público: central de 24 meses y sensibilidad con 18 y 36.
- Masa salarial = remuneración promedio de los asalariados privados (SIPA, serie 153.1_RNERACIDIO_2009_M_21, sin el medio aguinaldo de junio y diciembre y con el aguinaldo prorrateado ×13/12) × trabajadores registrados (SIPA). Aplica la remuneración privada a todo el empleo registrado.
- Las tarjetas no entran en la cuota: no se sabe qué parte del saldo se financia. Se informa su saldo en meses de masa salarial (0,9 en jun-26).

| | nov-23 | jun-26 | Promedio 2017-2023 | Máximo (oct-18) |
|---|---|---|---|---|
| Cuota de personales / masa salarial (24 meses) | 3,9% | **7,0%** | 5,4% | 9,0% |
| Con plazo de 18 / 36 meses (jun-26) | | 8,0% / 6,0% | | |
| Sólo intereses (jun-26) | | 4,0% | | |

**Lectura:** la carga casi se duplicó desde nov-23 (×1,8), por el boom de crédito con tasas reales altas. El máximo de la serie fue en oct-18, en plena suba anterior de la mora (de 3,0% a 4,8% entre ene-18 y jul-19).

**Lo que no permite decir:** como divide por todos los trabajadores registrados, tengan deuda o no, no verifica la cifra de "~25% del salario" que circula para los hogares endeudados. Para eso hacen falta datos por deudor (la Central de Deudores no se usa, por privacidad) o encuestas como la de Finanzas de los Hogares, que no tienen una edición reciente.
