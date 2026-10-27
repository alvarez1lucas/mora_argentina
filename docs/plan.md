# Plan del proyecto

## Alcance acordado (después de la Fase 1)

- **A. Variable objetivo:** la irregularidad nacional de familias por producto (anexo del Informe sobre Bancos) como serie principal, y el panel por entidad (A16 / ESD de consumo) para robustez y heterogeneidad entre grupos.
- **B. Muestra:** estimación principal desde 2017-01 (IPC INDEC base dic-2016). 2010-2016 sólo como descriptivo, con el deflactor empalmado y marcado.
- **C. PNFC/fintech:** fuera del modelo, sólo como contexto. Bancos vs EFNB sí entra (EFNB ≠ fintech).
- **D. Desempleo:** trimestral. Va a un modelo auxiliar trimestral y no como regresor mensual.
- **E. Datos:** se versionan las series procesadas chicas (`data/processed/`). Los 7z y `balhist.txt` no se versionan.

## Fases

1. **Relevamiento de datos** — hecho (`docs/relevamiento_datos.md`).
2. **Ingesta reproducible** — `python -m mora.ingest`.
3. **Descriptivo:** mora por producto y por grupo; descomposición numerador/denominador del ratio; indicador ajustado por castigos, (irregular + irrecuperables en cuentas de orden) / (cartera + irrecuperables en cuentas de orden); fechado de quiebres.
4. **Modelo satélite:** tests de raíz unitaria (ADF/KPSS, Zivot-Andrews con quiebre), ARDL / modelo de corrección de errores si hay cointegración y modelo en diferencias si no la hay; rezagos por criterio de información con un tope justificado; crecimiento previo del crédito como proxy del efecto cosecha; validación expanding-window fuera de muestra contra benchmarks ingenuos (random walk, AR).
5. **Canales monetarios y financieros (fase causal, separada del satélite).** Ver abajo.
6. **Escenarios:** base, adverso y favorable, con intervalos de confianza (lógica forward-looking de NIIF 9 y stress test).
7. **Dashboard y automatización:** Streamlit bilingüe que lee sólo `data/processed/` y `outputs/`; GitHub Actions mensual.
8. **Informe de 2 páginas y README (EN + ES).**

## Fase 5: canales monetarios y financieros

**Pregunta:** ¿cuánto del salto de la mora 2025-26 se explica por el endurecimiento monetario y de liquidez (tasas, encajes, absorción del Tesoro) y cuánto por ingreso real y efecto cosecha?

**Principio:** separar *precedencia predictiva* de *causalidad*. Granger y VAR van como descriptivos. Para afirmar algo causal hace falta una fuente de variación que no esté contaminada por el mismo shock macro que mueve la mora. Si no hay una creíble, el resultado se reporta como asociación.

| Herramienta | Qué responde | Límite |
|---|---|---|
| Granger / VAR reducido | ¿La tasa anticipa a la mora? | No es causalidad: un tercer factor puede mover las dos |
| Proyecciones locales (Jordà) | Respuesta de la mora a h meses de un shock de tasa | Requiere identificar el shock |
| Estudio de eventos sobre cambios de régimen (fin de las LEFI en jul-2025, subas de encajes, salida del cepo) | Dinámica alrededor de quiebres fechados con su fuente normativa | Pocos eventos, que suelen coincidir con otros shocks |
| **Panel por entidad con exposición diferencial** | ¿Las entidades más expuestas al shock (más tarjetas, a tasa variable, o más crecimiento de crédito previo) sufrieron más mora? | Es la identificación más defendible con estos datos; la exposición tiene que medirse antes del shock |
| Heterogeneidad por línea | Si el canal tasa importa, tarjetas (tasa variable) debería reaccionar antes que personales (tasa fija al originar) | Implicancia testeable, no una prueba |

**Variables candidatas** (las que ya están en la ingesta se marcan ✔):

- Tasas: préstamos personales ✔, BADLAR ✔, TAMAR ✔, política monetaria ✔ (hasta jul-2025). Tasa real ex ante con expectativas del REM (por agregar).
- Liquidez / encajes: depósitos de las entidades en el BCRA ✔ (proxy de integración). Las exigencias de efectivo mínimo se cargan como **eventos normativos fechados**, con la Comunicación "A" de cada cambio, en un archivo versionado.
- Absorción del Tesoro: efectos monetarios de las operaciones con el Tesoro ✔ (compras, adelantos, utilidades, resto). Por agregar: depósitos del Tesoro en el BCRA y rollover de las licitaciones del Tesoro (Secretaría de Finanzas).
- Otras comunes: spread activa-pasiva, carga de servicio de deuda sobre salario, empleo registrado (SIPA), brecha cambiaria, confianza del consumidor (UTDT).

**Riesgos a explicitar:** endogeneidad (una crisis sube la tasa y la mora a la vez), pocos eventos, cambios de régimen superpuestos y muestra corta. Toda conclusión causal se reporta con su supuesto de identificación.
