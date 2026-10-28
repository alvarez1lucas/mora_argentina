# Seguimiento de pronósticos

`python -m mora.seguimiento` (outputs en `outputs/seguimiento/`). Corre en la actualización semanal.

## Retrospectiva en tiempo pseudo-real

Para cada mes de origen desde ene-23: con los datos hasta ese mes se eligen de nuevo los rezagos (BIC con signos esperados), se reestima el modelo satélite (muestra 2010+, medición pública) y se proyecta el escenario base a 12 meses con los mismos supuestos que hoy, armados con los datos de ese momento. Es más exigente que la validación fuera de muestra de la Fase 4, que usa los regresores observados. En oct-24 ninguna especificación respetaba los signos esperados y ese origen queda afuera.

| Horizonte | Error medio absoluto | Sin cambio desde el origen | Sesgo | Dentro de la banda del 90% | n |
|---|---|---|---|---|---|
| 3 meses | 0,34 pp | 0,85 | −0,10 | 85% | 40 |
| 6 meses | 0,72 pp | 1,70 | −0,30 | 81% | 37 |
| 12 meses | 2,13 pp | 3,19 | −1,55 | 71% | 31 |

**Lectura:**
- Le gana a suponer que nada cambia en todos los horizontes.
- **No anticipó el quiebre de 2025.** Las proyecciones hechas durante 2024 esperaban una mora de 2-3%; fue de 5% a 10,6% un año después, fuera de la banda. Desde feb-25 las proyecciones a 12 meses vuelven a quedar dentro de la banda. Hipótesis: hasta 2024 casi no había episodios de tasa real alta con crecimiento rápido del crédito, y el modelo tenía poco de dónde aprender el golpe.
- La banda del 90% cubre el 71% a 12 meses y el sesgo es negativo (subestima): las bandas de los escenarios son un piso de la incertidumbre, porque no incluyen el riesgo de cambio de régimen.

**Límite:** se usa la versión actual de los datos, no la que estaba publicada en cada mes.

## Registro de lo publicado

Cada corrida agrega la proyección base vigente a `outputs/seguimiento/registro_pronosticos.csv` si su origen es nuevo, con la fecha de registro. El primer registro es el de origen ago-26. Con el tiempo, ese archivo es el historial real de aciertos del sitio.
