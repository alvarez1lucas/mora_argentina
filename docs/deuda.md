# Deuda del Tesoro en pesos y licitaciones

`python -m mora.deuda` (outputs en `outputs/deuda/`). La ingesta (`mora.ingest.finanzas`) baja cada semana el boletín mensual de la deuda bruta de la Administración Central (Secretaría de Finanzas, Excel desde ene-19, en millones de dólares). La URL del Excel cambia cada mes y se toma de la página de datos.

## Qué se mide

- **Stock en moneda local** (hoja A.3), CER y no CER. Se pasa a pesos con el tipo de cambio mayorista de fin de mes y se expresa en % del PBI.
- **Rollover del mercado en pesos** (hoja A.4): colocaciones / vencimientos de los instrumentos que se licitan. Entran LECAP, LEFI, BONCAP, BONCER, BONTE, BONAR en pesos, TAMAR, duales y letras dollar-linked que se pagan en pesos. Quedan afuera las letras entre organismos públicos (ANSES, FGS, AFIP, fondos fiduciarios), los adelantos del BCRA y los pagarés. Incluye canjes, que inflan las dos puntas. Es una medida mensual agregada: no reemplaza el resultado de cada licitación, que se publica como comunicado de prensa sin serie descargable.
- **Intereses capitalizados** (hoja A.4): intereses que se suman al capital en vez de pagarse, en % del PBI anualizado. La fuente los informa en 0 entre 2021 y 2023.

## Resultados

| | nov-23 | jun-26 |
|---|---|---|
| Deuda del Tesoro en moneda local (% PBI) | 29,5 | 32,9 (pico 45,4 en jun-24) |
| · ajustable por CER | 17,3 | 18,5 |
| · no ajustable | 12,3 | 14,4 |
| Moneda local / deuda total | 37,5% | 47,7% (49,3% en sep-26) |
| Exposición de los bancos al Estado (títulos + pases, % PBI) | 12,8 | 9,8 |

| Año | Rollover mediano | Intereses capitalizados (% PBI, anualizado) | Financiamiento neto del mercado (% PBI, anualizado) |
|---|---|---|---|
| 2024 | 120% | 2,9 | +16,1 |
| 2025 | 84% | 10,7 | −5,9 |
| 2026 (ene-sep) | 100% | 5,0 | +0,5 |

**Lectura:**
- **La esterilización pasó del BCRA al Tesoro.** Leliq → pases del BCRA (dic-23) → LEFI del Tesoro (jul-24) → LECAP (jul-25). La deuda en pesos del Tesoro creció y ganó peso en el total, mientras la exposición de los bancos al Estado bajaba.
- **Los intereses se capitalizan.** En 2025 los intereses capitalizados equivalieron a 10,7% del PBI anual. El Estado sostiene tasas altas, que son el piso de la tasa a familias, sin pagar los intereses en efectivo mientras la deuda se renueva.
- **2024 absorbió y 2025 devolvió.** En 2024 el Tesoro colocó más de lo que vencía (absorbió pesos); en 2025, menos (los devolvió, sobre todo al desarmarse las LEFI en jul-25).
- **Rollover y tasas.** Con un rollover de 3 meses alto, lo que paga el Estado tiende a bajar después: correlación de −0,28 a −0,30 a 1, 3 y 6 meses; con la tasa de préstamos, de −0,11 a −0,18. Refleja la demanda por los títulos (cuando el mercado los pide, el Tesoro coloca más y más barato), no un efecto causal del rollover sobre la tasa.

**Límites:**
- Los flujos incluyen canjes.
- El tipo de cambio de conversión de los flujos es el promedio del mes, no el del día de cada operación.
- La tenencia por tipo de inversor (bancos, FCI, BCRA, FGS) no está en el boletín.
