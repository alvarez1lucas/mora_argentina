import numpy as np

from mora.ingest.datos_gob import parse_payload


def test_parse_payload_sorts_and_coerces():
    payload = {"data": [["2026-02-01", 2.5], ["2026-01-01", None], ["2026-03-01", "3"]]}
    s = parse_payload(payload, name="x")
    assert list(s.index.strftime("%Y-%m")) == ["2026-01", "2026-02", "2026-03"]
    assert np.isnan(s.iloc[0])
    assert s.iloc[2] == 3.0


def test_parse_payload_empty():
    assert parse_payload({"data": []}, name="x").empty


def test_frequency_classification():
    import pandas as pd

    from mora.ingest.datos_gob import frequency

    assert frequency(pd.Series(1.0, index=pd.date_range("2025-01-01", periods=10, freq="B"))) == "diaria"
    assert frequency(pd.Series(1.0, index=pd.date_range("2025-01-01", periods=10, freq="MS"))) == "mensual"
    assert frequency(pd.Series(1.0, index=pd.date_range("2025-01-01", periods=10, freq="QS"))) == "trimestral"
