from datetime import date

import pandas as pd

from mora.ingest.transparencia import summarize


def _row(codigo, tea, cft, fecha="2026-09-01", moneda="Pesos", tipo="Fija"):
    return {"codigoEntidad": codigo, "descripcionEntidad": f"E{codigo}", "denominacion": moneda, "tipoTasa": tipo,
            "tasaEfectivaAnualMaxima": tea, "costoFinancieroEfectivoTotalMaximo": cft, "fechaInformacion": fecha}


def test_summarize_filters_and_classifies():
    raw = pd.DataFrame([
        _row(7, 100, 130), _row(7, 120, 150),
        _row(7, 999, 999, fecha="2022-03-07"),       # vieja: se descarta
        _row(7, 50, 60, moneda="Dólares"),           # otra moneda: se descarta
        _row(55123, 200, 280),
    ])
    out = summarize(raw, "Personales", date(2026, 10, 27), antiguedad_max_dias=180).set_index("codigo_entidad")
    assert out.loc[7, "tea_mediana"] == 110
    assert out.loc[7, "n_productos"] == 2
    assert out.loc[7, "tipo"] == "entidad_financiera"
    assert out.loc[55123, "tipo"] == "pnfc"
