import pandas as pd

from mora.ingest.finanzas import _fecha, es_mercado_pesos


def test_instrumentos_de_mercado_en_pesos():
    assert es_mercado_pesos("LECAP - $")
    assert es_mercado_pesos("BONCAP/$/15-01-2027")
    assert es_mercado_pesos("BONCER/$/0%+CER/30-06-2027")
    assert es_mercado_pesos("LETRA - U$S - Pagan en pesos")  # dollar-linked: se suscribe y paga en pesos
    assert not es_mercado_pesos("LETES - U$S")                # 'U$S' no es pesos
    assert not es_mercado_pesos("LETRA ANSES - $")            # intra sector público
    assert not es_mercado_pesos("LETRA FGS - $")
    assert not es_mercado_pesos("Adelantos Transitorios BCRA")


def test_fechas_del_encabezado():
    assert _fecha(pd.Timestamp("2019-01-15")) == pd.Timestamp("2019-01-01")
    assert _fecha("sep-26 (*)") == pd.Timestamp("2026-09-01")
    assert _fecha("en %") is None
