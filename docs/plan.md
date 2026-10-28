# Plan del proyecto

## Alcance acordado (después de la Fase 1)

- **A. Variable objetivo:** la irregularidad nacional de familias por producto (anexo del Informe sobre Bancos) como serie principal, y el panel por entidad (A16 / ESD de consumo) para robustez y heterogeneidad entre grupos.
- **B. Muestras en paralelo:** cada modelo se estima en una muestra *larga* (2010+, con el deflactor empalmado 2010-2016 y por lo tanto más ruido de medición) y en una *limpia* (2017+, IPC INDEC base dic-2016). La limpia es la principal; si un resultado sólo aparece en una de las dos, se reporta como frágil. La limpia arranca en 2017 y no en 2015 porque INDEC no publicó IPC entre ene y abr de 2016 y el IPC nacional empieza en dic-2016.
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
7. **Sitio web y automatización:** sitio estático (generado con Python + Plotly por `mora.sitio`; se descartó Quarto para no sumar una herramienta externa) publicado en GitHub Pages, bilingüe ES/EN, que lee sólo `data/processed/` y `outputs/`. GitHub Actions corre la ingesta, el modelo y el render, y publica. Reemplaza a Streamlit: carga instantánea sin servidor, se ve como una publicación y no como una demo, y el informe de 2 páginas (PDF, impreso con Chrome en CI) sale de los mismos outputs (`mora.informe`).
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

### Hipótesis de trabajo

**H1 — Tasa fija + desinflación + salario real en baja.** Los préstamos personales se otorgan a tasa fija. Los originados entre mediados de 2024 y 2025 tuvieron una TNA de 65-83% (pico en oct-2025), pero la inflación de los 12 meses siguientes fue de 31-34%: tasa real ex post de 45-54% anual. Desde fines de 2025 el salario real registrado cae (de −0,3% a −4,2% interanual). En 2024 las tasas reales ex post también fueron muy altas y la mora no saltó, porque el stock era chico. Por eso H1 predice una interacción: importa la *carga real ponderada por el stock originado*, no la tasa sola.
- Medición: tasa real ex post por cohorte de originación (tasa de originación contra inflación realizada a 12 meses), tasa real ex ante (inflación esperada del REM), crecimiento real del stock como proxy de la originación, y salario real.
- Implicancia testeable: tarjetas (tasa variable, se reprecian) contra personales (tasa fija): bajo H1, personales debería mostrar más mora rezagada a la desinflación.

**H2 — Absorción del sector público y del BCRA (esterilización).** Los bancos tienen una parte grande del activo en instrumentos remunerados del Tesoro y del BCRA, y eso compite con el crédito privado y sostiene tasas altas. Datos del anexo (activo en moneda nacional, sistema): títulos públicos + otros créditos por intermediación (pases) pasan de ~54% en dic-23 a ~38% en dic-25, mientras el crédito privado sube de 27% a 45%. En 2026 los títulos públicos vuelven a subir (31,1% → 33,6%) y el crédito privado se estanca.
- Medición: participación de títulos públicos, pases y LELIQ en el activo por grupo de entidades; intereses pagados por el BCRA (efecto monetario, id 55); depósitos del gobierno en el BCRA; cronología de encajes verificada (`config/eventos_monetarios.yaml`).
- Identificación: panel por entidad. Las entidades con más exposición al sector público antes del shock de jul-ago 2025 (fin de las LEFI, subas de encajes integrables con títulos) deberían mostrar menos crecimiento del crédito privado y, si el canal opera vía tasa, más mora en sus carteras de consumo. Para esto hace falta la exposición por entidad, que se arma con las cuentas de títulos públicos de `bal_hist`.

**H3 — Cobertura cambiaria subsidiada.** El BCRA vendió dólar futuro (hasta ~83% del interés abierto en sep-2025) para que el sector financiero se quedara en pesos cubierto. Ver el eslabón 3b de `docs/marco_teorico.md`. Medición: devaluación implícita del futuro a ~30 días, tasa sintética en USD e interés abierto (A3 Mercados); pases a 1 día como proxy de la caución.

**Aristas que se suman al análisis:**
- **Cambios en la clasificación de deudores y refinanciaciones:** los bancos pidieron flexibilizar la clasificación (ago-2026) y las familias ya refinanciaron ~$2,6 billones. Si el BCRA lo aprueba, la mora *medida* baja sin que mejore la capacidad de pago: es un quiebre en la variable dependiente. Se sigue en `config/eventos_monetarios.yaml`.
- **Castigos (cuentas de orden):** el ratio subestima el deterioro cuando los bancos pasan créditos a irrecuperables (cuenta 711046 del balance por entidad).
- **Carga financiera de los hogares:** cuotas estimadas (stock × CFT) sobre la masa salarial (SIPA).
- **Expectativas de inflación (REM)**, para tasas reales ex ante.
- **Reservas internacionales y compras de divisas del BCRA en 2026**, como canal de emisión y capacidad de intervención.
- **Empleo registrado (SIPA)**, como canal de ingreso además del salario real.

**Variables candidatas** (las que ya están en la ingesta se marcan ✔):

- Tasas: préstamos personales ✔, BADLAR ✔, TAMAR ✔, política monetaria ✔ (hasta jul-2025). Tasa real ex ante con expectativas del REM (por agregar).
- Liquidez / encajes: depósitos de las entidades en el BCRA ✔ (proxy de integración). Las exigencias de efectivo mínimo se cargan como **eventos normativos fechados**, con la Comunicación "A" de cada cambio, en un archivo versionado.
- Absorción del Tesoro: efectos monetarios de las operaciones con el Tesoro ✔ (compras, adelantos, utilidades, resto). Por agregar: depósitos del Tesoro en el BCRA y rollover de las licitaciones del Tesoro (Secretaría de Finanzas).
- Otras comunes: spread activa-pasiva, carga de servicio de deuda sobre salario, empleo registrado (SIPA), brecha cambiaria, confianza del consumidor (UTDT).

**Riesgos a explicitar:** endogeneidad (una crisis sube la tasa y la mora a la vez), pocos eventos, cambios de régimen superpuestos y muestra corta. Toda conclusión causal se reporta con su supuesto de identificación.
