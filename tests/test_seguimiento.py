import pandas as pd
import pytest

from mora.seguimiento import metricas


def test_metricas_por_horizonte():
    r = pd.DataFrame({
        "h": [3, 3, 12, 12],
        "observada": [5.0, 6.0, 10.0, None],  # la última todavía no se observó
        "error": [1.0, -1.0, -2.0, 0.0],
        "error_ingenuo": [2.0, 2.0, -4.0, 0.0],
        "dentro_banda": [True, False, True, True],
    })
    m = metricas(r, [3, 12]).set_index("h")
    assert m.loc[3, "error_medio"] == pytest.approx(0.0)
    assert m.loc[3, "error_absoluto_medio"] == pytest.approx(1.0)
    assert m.loc[3, "cobertura_banda_90"] == pytest.approx(0.5)
    assert m.loc[12, "n"] == 1
    assert m.loc[12, "error_absoluto_medio_ingenuo"] == pytest.approx(4.0)
