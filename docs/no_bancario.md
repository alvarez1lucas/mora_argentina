# Fuera de los bancos: fondos comunes, billeteras y proveedores no financieros

`python -m mora.no_bancario` (outputs en `outputs/no_bancario/`). Los datos los baja la ingesta semanal: `mora.ingest.cafci` y `mora.ingest.pnfc`.

## Fuentes

- **CAFCI, resumen mensual de la industria de FCI** (PDF, desde 2011). Trae la cartera de la industria, de los money market y de los de renta fija por clase de activo. Se lee desde ene-23. En cada tabla la última columna es el mes del informe y las anteriores, el cierre (diciembre) de los años previos. **En 11 de los 45 meses (abr-ago-23, oct-23, feb-mar-24, may-jun-24, sep-24) CAFCI publicó las tablas como imagen y no hay texto que leer:** dic-23 se completa con la columna de cierre de informes posteriores y el resto queda sin dato (no se interpola). Lo leído de cada informe se guarda en `data/processed/cafci_informes.json` para no volver a bajar los PDF.
- **BCRA, Informe de Proveedores No Financieros de Crédito** (semestral, PDF, sin series descargables). Saldo e irregularidad en cinco fechas: dic-23, ago-24, ene-25, jul-25 y feb-26. Cada edición redacta las cifras distinto, así que están transcriptas en `config/settings.yaml` con la cita textual de cada una. `python -m mora.ingest.pnfc --verificar` baja los PDF y comprueba que las citas estén y digan el número cargado. Son datos agregados del BCRA: la Central de Deudores no se consulta por CUIT.

## 1. Exposición al Estado ampliada

A los títulos públicos y pases en pesos de los bancos se les suma la **deuda nacional en cartera de los FCI**.

| % del PBI | dic-23 | dic-24 | dic-25 | jun-26 |
|---|---|---|---|---|
| Bancos (títulos + pases en pesos) | 19,1 | 11,9 | 9,8 | 9,8 |
| FCI, deuda nacional | 2,8 | 2,2 | 1,4 | 2,0 |
| **Total** | **21,9** | **14,1** | **11,2** | **11,7** |
| Crédito bancario al sector privado en pesos | 9,7 | 10,5 | 12,1 | 11,6 |

Contando todos los títulos públicos (también provinciales y extranjeros), los FCI llegan a 3,1% del PBI en dic-23 y 2,2% en jun-26.

**Lo que no se suma, y por qué:**
- **Billeteras virtuales.** Colocan los saldos de sus usuarios en fondos money market, que en jun-26 tenían 70% en plazos fijos y cauciones y sólo 1,4% en títulos públicos. Esa plata vuelve a los bancos como depósitos, y lo que los bancos compran con ella ya está en su exposición: sumarla la contaría dos veces. La exposición de las billeteras al Estado es, sobre todo, indirecta.
- **Brokers y tenencia directa de inversores.** No hay datos públicos de quién tiene los títulos fuera de los fondos (Caja de Valores no publica la tenencia por tipo de inversor).
- **Cartera propia de las fintech.** Tampoco hay datos públicos.

Por eso el total es una **cota inferior**.

**Lectura:** la competencia del Estado por los pesos no pasa sólo por los bancos. En el pico de dic-23, sumando los FCI, la exposición al Estado era más del doble del crédito privado. En 2026 los FCI vuelven a crecer (de 1,1% a 2,0% del PBI entre oct-25 y jun-26), con los fondos de renta fija comprando Lecap.

## 2. Crédito y mora de las familias integrados

| | dic-23 | ago-24 | ene-25 | jul-25 | feb-26 |
|---|---|---|---|---|---|
| Crédito de bancos a familias ($ billones) | 10,0 | 23,1 | 37,0 | 52,1 | 64,0 |
| Crédito de proveedores no financieros ($ billones) | 2,1 | 4,9 | 8,0 | 11,0 | 13,9 |
| Participación no financiera | 17% | 17% | 18% | 17% | 18% |
| Mora de bancos (familias) | 2,8% | 2,7% | 2,7% | 5,7% | 11,2% |
| Mora de proveedores no financieros | 10,6% | 7,6% | 8,6% | 16,2% | 26,9% |
| **Mora integrada** | **4,1%** | **3,5%** | **3,7%** | **7,5%** | **14,0%** |
| Diferencia con la bancaria | +1,4 pp | +0,9 | +1,1 | +1,8 | +2,8 |

**Lectura:**
- Los proveedores no financieros son ~18% del crédito a las familias, una participación estable: crecieron al mismo ritmo que los bancos. Coincide con el 18% que informa el BCRA.
- Su mora se triplicó en un año (de 8,6% a 26,9%) y empezó a subir antes y más fuerte que la bancaria. **Con ellos, la suba de la mora de las familias es de 9,9 pp (de 4,1% a 14,0%), contra 8,4 pp (de 2,8% a 11,2%) si se miran sólo los bancos.**
- Encaja con la cadena del proyecto: sin acceso a los depósitos, estos proveedores se fondean con fideicomisos, obligaciones negociables y bancos a tasas más altas, y prestan a una TNA de 144% en préstamos personales (feb-26), contra 69% de los bancos (TNA de la serie del BCRA).

**Límites:**
- Sólo cinco fechas: no alcanza para estimar un modelo, así que el resto del análisis sigue con la mora bancaria (la única serie mensual).
- El saldo de los proveedores no financieros incluye algo de crédito a empresas (leasing y factoring).
- Muchas personas deben en los dos sectores: de los 12,1 millones de deudores de proveedores no financieros, 6,9 millones también deben a bancos y 5,2 millones deben sólo a no financieros (BCRA, feb-26). La mora integrada pondera saldos, no personas: no hay doble conteo de deuda, pero una misma persona puede estar en mora en los dos lados.
