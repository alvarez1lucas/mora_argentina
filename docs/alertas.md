# Alertas tempranas y recaudación

`python -m mora.alertas` (outputs en `outputs/alertas/`). Corre en la actualización semanal.

## Por qué

El modelo de escenarios aprende relaciones promedio y no anticipó el quiebre de 2025 (`docs/seguimiento.md`). Las alertas son otra herramienta: miran si vuelven a aparecer las señales que precedieron a subas de la mora, para que si el patrón de 2024-25 se repite (por ejemplo, en 2027) se encienda antes.

## Método

Método de señales de Kaminsky y Reinhart (1999).
- **Episodio:** la mora de familias sube al menos 1 punto en los 12 meses siguientes. Se excluye la ventana del alivio COVID (mar-20 a dic-21), cuyos saltos son por reclasificación.
- **Indicadores**, con la dirección que fija la teoría:
  - atrasos de 31 a 90 días (situación 2, consumo y vivienda, ponderada por saldo desde el panel por entidad) y su suba en 3 meses;
  - suba de la mora en 3 meses;
  - tasa real del CFT y su suba en 12 meses;
  - crecimiento real del crédito (también con 12 meses de rezago);
  - carga de la cuota y su suba en 12 meses;
  - salario real, actividad (EMAE);
  - recaudación real de IVA, aportes y débitos/créditos.
- **Umbral:** el percentil que minimiza el cociente ruido/señal (falsas alarmas sobre aciertos), exigiendo que capte al menos 25% de los meses previos a episodios.
- **Peso:** 1/NSR, con un piso de NSR de 0,1. Si NSR ≥ 1, el indicador pesa 0.
- **Índice:** promedio ponderado de las señales encendidas (0 a 1). En el último mes, cada indicador usa su último dato con hasta 3 meses de antigüedad.
- **Grados:** sin alerta (< 0,25), vigilancia (< 0,5), alerta (< 0,75), alerta grave.

## Validación fuera de muestra

Umbrales elegidos con lo que se sabía a fines de 2023 (episodios etiquetados hasta dic-22: sólo el de 2018-19).

- Ene-24 a ago-25: en los 17 meses con una suba por delante, el índice estuvo en vigilancia o más en el **76%**. Los 3 meses sin suba por delante (ene-mar 24) también estuvieron encendidos: son muy pocos para medir falsas alarmas.
- Trayectoria:
  - vigilancia en ene-24 y alerta en mar-24, por la caída del salario y la actividad;
  - **sin alerta entre ago-24 y nov-24, justo antes de la suba**;
  - vigilancia desde dic-24, con la mora en 2,55%;
  - alerta en oct-25.
- **Nunca llegó a alerta grave.** El episodio de 2018-19 fue un golpe al ingreso; el de 2025, un boom de crédito con tasa real alta. Con un solo episodio previo, el sistema no podía aprender el segundo patrón.

## Versión vigente

Entrenada con toda la historia etiquetada (incluye 2024-25). En sep-26 marca **vigilancia** (índice 0,26), con tres indicadores encendidos:
- situación 2 en 3,8% (umbral 2,6%);
- tasa real en 72% (umbral 62%);
- actividad en −1,3% (umbral −1,2%).

Algunos umbrales vigentes están calibrados casi exclusivamente con 2024-25, como la tasa real ≥ 62% o el crédito real ≥ 51%. Son exigentes y frágiles.

## Qué anticipa la mora (correlación con la variación de los 6 meses siguientes, sin COVID)

| Indicador | h = 3 | h = 6 | h = 12 |
|---|---|---|---|
| Suba de la carga de la cuota en 12 meses | 0,88 | 0,91 | 0,78 |
| Situación 2 (nivel) | 0,81 | 0,75 | 0,53 |
| Suba de la mora en 3 meses | 0,82 | 0,76 | 0,55 |
| Crecimiento real del crédito | 0,55 | 0,65 | 0,66 |
| Tasa real del CFT | 0,55 | 0,59 | 0,39 |
| Salario real (interanual) | 0,23 | 0,30 | 0,31 |
| Recaudación real de aportes | 0,07 | 0,17 | 0,27 |
| Recaudación real de IVA DGI | −0,06 | −0,05 | −0,02 |
| Recaudación real de débitos y créditos | −0,05 | −0,02 | 0,01 |

## Recaudación

Serie mensual de ARCA por tributo (datos.gob.ar, dataset 142.3): IVA DGI, débitos y créditos bancarios, internos, aportes, contribuciones y total. "Facilidades de pago" está en 0 desde 2023 (discontinuada) y no se usa.

- **Ventaja: velocidad.** Llega a sep-26 cuando el EMAE llega a jul-26. El IVA real interanual es negativo en 9 de los 11 meses entre nov-25 y sep-26: la actividad se desacelera.
- **Pero casi no anticipa la mora** (tabla). Entra al índice con peso bajo.
- Salario, actividad y aportes en alza anticipan *más* mora, no menos. Es el efecto cosecha: en Argentina, los buenos momentos traen boom de crédito y la mora llega después.

**Límite central:** en 2011-2026 hay dos episodios. Los umbrales y las frecuencias por grado son muy inciertos; el índice sirve para ordenar la atención, no como probabilidad.
