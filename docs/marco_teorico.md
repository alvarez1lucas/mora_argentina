# Marco teórico: por qué se trabó la remonetización vía crédito (2024-2026)

Hipótesis propia del autor, ordenada como una cadena causal. Cada eslabón tiene la evidencia disponible en los datos del proyecto y su estado: **respaldado** (los datos lo muestran), **parcial** (lo muestran con salvedades) o **pendiente** (falta un dato o una prueba). Todos los números salen de `data/processed/`. Las fechas normativas están en `config/eventos_monetarios.yaml`.

## La cadena

```
(1) Remuneración de pasivos      →  (2) Plan: pesos del Tesoro/BCRA      →  (3) Presión cambiaria
    (LELIQ/pases → Lecap)               pasan a crédito privado                 contra el techo de la banda
                                        (multiplicador bancario)                (ancla cambiaria)
                                                                                      │
(6) La mora traba                ←  (5) Cuota cara + salario real   ←  (4) Re-esterilización:
    la remonetización                   en baja → mora                      encajes, tasas, rollover >100%
    (spread, racionamiento)
```

### (1) Remuneración de pasivos e "intereses sobre intereses" — respaldado (BCRA 2018-2023); el costo pasa al Tesoro desde 2024

- Los intereses pagados por el BCRA (pases, LELIQ, remuneración de cuentas corrientes; efecto monetario, id 55) equivalen al 50% de la base monetaria promedio en 2019, al 84% en 2022 y al **261% en 2023**. Es la dinámica de bola de nieve: el BCRA emite para pagar intereses y vuelve a absorber esa emisión con más pasivos remunerados.
- En 2025-2026 ese efecto es **cero en el balance del BCRA**: el pasivo remunerado pasó al Tesoro (LEFI y después Lecaps, que *capitalizan* intereses). La lógica de la bola de nieve sigue, pero ahora es deuda del Tesoro en pesos. El Tesoro licita con rollover >100% (124% en ene-26, 102% en abr-26 y 110% en may-26, según la prensa) a tasas de 28-42% anual con una inflación de ~25-30%: tasa real positiva sobre un stock que se renueva.
- **Pendiente:** el stock de deuda del Tesoro en pesos y sus intereses capitalizados (Secretaría de Finanzas, Boletín de deuda). Sin ese dato no se puede medir la bola de nieve después de 2024.

### (2) El plan: que esos pesos fueran al crédito privado — respaldado

Activo en moneda nacional del sistema (anexo del Informe sobre Bancos):

| % del activo | dic-23 | jun-24 | dic-24 | jun-25 | dic-25 | ago-26 |
|---|---|---|---|---|---|---|
| Títulos públicos | 18,0 | 37,9 | 35,5 | 32,8 | 31,8 | 33,6 |
| Otros créditos por intermediación (pases) | 35,7 | 13,6 | 6,9 | 5,1 | 4,4 | 3,7 |
| Préstamos al sector privado | 27,4 | 26,7 | 37,5 | 42,4 | 44,9 | 44,5 |

El boom de crédito 2024-25 es literalmente esa reasignación del activo. El crédito real al consumo (personales + tarjetas, en pesos de ene-25) pasa de 23,1 billones en oct-24 a 33,4 en nov-25.

### (3) Presión cambiaria contra el ancla — respaldado

Tipo de cambio mayorista como % del techo de la banda (aproximado: 1.400 + 1% mensual desde abr-25, por inflación t-2 desde ene-26): 80% en abr-25, 88% en jul-25 (fin de las LEFI, la liquidez queda libre), **95-96% entre sep-25 y dic-25**. El techo de la banda es el ancla nominal que disciplina los precios de los transables; acercarse al techo pone el ancla en riesgo.
- **Salvedad:** en ese período coinciden las elecciones (26/10/25), la dolarización de carteras y el fin de las LEFI. Los datos no permiten atribuir la presión cambiaria *al crédito* en particular.

### (4) Re-esterilización — respaldado

- La tasa "endógena" duró poco: la TAMAR pasa de 34% (jul-25) a 53% (ago-25) y queda en ~50% hasta oct-25.
- Encajes: A 8281 y A 8289 (+10 pp y +10 pp en FCI money market, pases y cauciones, desde 01/08/25), A 8302 (integración diaria desde 18/08/25), **A 8306 (+3,5 pp en todas las obligaciones en pesos, integrables con títulos públicos de licitación primaria)**. Los depósitos de las entidades en el BCRA, en términos reales, pasan de 12,2 a 16,9 billones entre jul-25 y ago-25.
- La A 8306 es el mecanismo que describe la hipótesis: el encaje se usa para que los bancos financien al Tesoro en vez de prestarle al sector privado.

### (5) Cuota cara y salario real en baja → mora — respaldado

- **La TNA subestima la carga.** La serie de tasas del BCRA es una TNA sin IVA. En el régimen de transparencia (2026) la mediana de CFT mensual / TEM es **1,21: el IVA sobre intereses**, sin contar seguros ni gastos. Mediana de los préstamos personales en 2026: bancos, TEA 117% y CFT 148%; PNFC, TEA 343% y CFT 411%.
- **CFT aproximado sobre la tasa promedio del BCRA** (TNA + IVA): 123-132% de TEA en 2025, con picos de 158% (sep-25) y 147% (nov-25).
- **Tasa real ex post con CFT** para las cohortes otorgadas entre 2024 y 2025: **53% a 75% anual**; la cohorte de sep-25 da 94%. El salario nominal registrado sube ~28-30% en los 12 meses siguientes, así que la cuota fija no se licúa.
- **Salario real registrado** (índice ene-25 = 100): 100,8 en ago-25 y **96,1 en mar-26** (−4,7%). La inflación rebota a 2,9-3,4% mensual en ene-mar 26 después de la presión cambiaria.
- Mora de familias: 5,6% en jul-25 → 12,9% en jul-26. Personales: 7,2% → 16,7%.
- **Sorpresa de carga de la cuota** (salario esperado, con expectativa ingenua, contra salario realizado a 12 meses): 1,05-1,2 para las cohortes de 2025. Para las de 2024 da 2-2,6, pero ese número exagera porque nadie esperaba que la inflación de 2023 se repitiera; falta la versión con expectativas del REM.

### (6) La mora traba la remonetización — parcial

- **Spread personales − TAMAR:** 32 pp (nov-24) → 36-38 pp (2025) → **43-44 pp (nov-25 y may-26)**. El costo de fondeo baja (TAMAR de 51% a 22%) pero la tasa a familias apenas se mueve (de 83% a 62-65%): los bancos cobran el riesgo de crédito y racionan.
- Crédito real al consumo: 33,4 billones (nov-25) → 30,7 (ago-26), **−8%**. M2 real: 67,3 (jul-25) → 55,8 (abr-26), **−17%**, con recuperación parcial a 58,5 en ago-26.
- **Salvedad:** el estancamiento del crédito puede venir de la oferta (bancos que racionan por la mora) o de la demanda (familias sobreendeudadas que no quieren tomar más deuda). Las dos versiones son compatibles con la hipótesis, pero tienen implicancias distintas. Para separarlas: panel por entidad, comparando las entidades con más mora previa contra las demás en el crecimiento posterior del crédito.

## Qué falta para pasar de narrativa a evidencia

1. **Identificación.** Entre jul-25 y dic-25 todo ocurre a la vez (fin de las LEFI, encajes, elecciones, presión cambiaria). Una serie nacional no puede separar los eslabones. El panel por entidad sí: exposición previa a títulos públicos, mora previa y mezcla de productos como fuentes de variación entre entidades.
2. **Expectativas de inflación del REM** (BCRA), para la tasa real ex ante y la sorpresa de carga.
3. **Stock de deuda del Tesoro en pesos** (Secretaría de Finanzas), para medir la bola de nieve después de 2024.
4. **Historia del CFT:** la API de transparencia sólo da la foto vigente. El pipeline guarda una foto por mes desde oct-2026 (`transparencia_entidades.csv`). Para el pasado se usa el CFT aproximado (TNA + IVA, cota inferior).
5. **Contrafáctico:** ¿qué habría pasado con la mora sin la re-esterilización? Es la pregunta de los escenarios (Fase 6).
