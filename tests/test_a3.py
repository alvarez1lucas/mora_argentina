import pandas as pd

from mora.ingest.a3 import parse


def test_parse_keeps_monthly_futures_only():
    rows = [
        {"dateTime": "2025-09-01T00:00:00.000Z", "symbol": "DLR092025", "settlement": 1419.0, "impliedRate": 43.9,
         "openInterest": 1947549.0, "volume": 1001887, "optionType": None},
        {"dateTime": "2025-09-01T00:00:00.000Z", "symbol": "DLR092025C1500", "settlement": 5.0, "impliedRate": None,
         "openInterest": 10.0, "volume": 1, "optionType": "CALL"},
    ]
    df = parse(rows)
    assert list(df["contrato"]) == ["DLR092025"]
    assert df["vencimiento"].iloc[0] == pd.Timestamp("2025-09-30")
    assert df["fecha"].iloc[0] == pd.Timestamp("2025-09-01")
