import re

import pytest

from mora.sitio import datos, mes, num, pagina
from mora.config import path


def test_formato_numeros_por_idioma():
    assert num(1234.567, "es", 1) == "1.234,6"
    assert num(1234.567, "en", 1) == "1,234.6"
    assert num(-0.03, "es", 2) == "-0,03"


def test_mes_abreviado():
    assert mes("2026-08-01", "es") == "ago-26"
    assert mes("2026-08-01", "en") == "Aug-26"


@pytest.mark.skipif(not (path("outputs") / "escenarios" / "resumen_escenarios.json").exists(),
                    reason="requiere los outputs del pipeline")
@pytest.mark.parametrize("lang", ["es", "en"])
def test_pagina_sin_valores_faltantes(lang):
    html = pagina(datos(), lang)
    texto = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    assert not re.search(r"\bnan\b|\bNaN\b|\binf\b", texto)
    assert html.count("plotly-graph-div") >= 7
