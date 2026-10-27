# Relevamiento de datos (Fase 1)

Verificado contra las fuentes el 26/10/2026. Los ids y URLs viven en `config/settings.yaml`.

## Variable objetivo

| Serie | Fuente | Frec. | Rango | Descarga | Limitaciones |
|---|---|---|---|---|---|
| Irregularidad y saldo de financiaciones a **familias** por línea (personales, tarjetas, hipotecarios, prendarios, otros) y apertura UVA | Anexo del Informe sobre Bancos (`informe-bancos-anexo.xlsx`) | M | 2010-01 → último mes (UVA desde 2018) | Excel con URL fija, se pisa cada mes | Sólo total del sistema. Irregular = situación 3 a 5 (>90 días) |
| Irregularidad al sector privado por grupo (públicos, privados nacionales/extranjeros, EFNB) | Mismo anexo, hoja "Calidad de Cartera" | M | 2010-01 → (anual 2002-2009) | Ídem | No separa familias de empresas por grupo. **EFNB ≠ fintech** |
| Panel por entidad: A16 (irregularidad consumo), A9, A11, A13, A14, A17 y ESD de consumo (situación 1-5) | BCRA, Información de Entidades Financieras | M | 2011-01 → último mes | Un 7z por mes. La 5ta columna numérica es el mes del archivo | "Consumo" ≈ familias, pero no es idéntico. Altas y bajas de entidades. **El saldo de ESD cambia de unidad (miles → millones de $) en algún punto de la serie**: usar sólo ratios o normalizar |
| Balance histórico por entidad: cuenta 711046 "Créditos clasificados irrecuperables" (cuentas de orden) y préstamos por línea | `bal_hist/balhist.txt`, dentro del 7z más reciente | M | 1994-11 → último mes (se conserva desde 2011) | 300 MB descomprimido | Moneda homogénea desde 2020 (NIC 29). La 711046 no abre por línea |

## Crédito, precios, tasas y liquidez (API BCRA v4.0)

Stocks de préstamos personales y tarjetas (diarios, 2002+); hipotecarios y prendarios a personas humanas en moneda local (mensual, 1999+); inflación mensual; tasas de préstamos personales (2010-07+), BADLAR, TAMAR (2024-10+), tasa de política monetaria (2015-12 → **discontinuada jul-2025**); tipo de cambio mayorista; base monetaria, M2, depósitos de las entidades en el BCRA (proxy de integración de encajes); y factores de explicación de la base monetaria (operaciones con el Tesoro, pases, LELIQ). La API v3.0 está dada de baja (HTTP 410).

## INDEC (datos.gob.ar)

IPC nacional base dic-2016 (2016-12+), índice de salarios registrados (2015-10+), EMAE desestacionalizado (2004+) y desocupación de la EPH (trimestral, 2003+).

## Fuera de alcance

- **Mora de PNFC/fintech:** no hay serie primaria pública. Las cifras de prensa (>30%) son estimaciones de consultoras (1816, CEPA, U. Austral) armadas con la Central de Deudores por CUIT.
- **Central de Deudores:** excluida por privacidad.
- **RIPTE:** figura en el catálogo de datos.gob.ar (`158.1_REPTE_0_0_5`), pero la API lo devuelve vacío (oct-2026). Lo reemplaza el índice de salarios de INDEC.

## Contraste con la prensa

| Dato | Prensa | Anexo BCRA |
|---|---|---|
| Familias jul-26 | ~12,9% | 12,94% |
| Familias jul-25 | ~5,6% | 5,65% |
| Personales jul-26 | "cerca del 15%" | 16,71% |
| Familias ago-26 | — | 12,81% |

## Problemas técnicos encontrados

- **TLS:** un antivirus que inspecciona TLS (Avast) reemplaza la cadena de certificados. La ingesta valida contra el almacén del sistema operativo (`truststore`) y no desactiva la verificación.
