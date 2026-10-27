import numpy as np
import pandas as pd
import pytest

from mora.config import settings
from mora.ingest.bcra_api import AGGS, parse_detalle, to_monthly


def test_config_aggs_are_valid():
    for name, spec in settings()["bcra_api"]["series"].items():
        assert spec["agg"] in AGGS, name


def test_parse_detalle_sorts_and_drops_duplicates():
    rows = [
        {"fecha": "2026-01-03", "valor": 3.0},
        {"fecha": "2026-01-01", "valor": 1.0},
        {"fecha": "2026-01-01", "valor": 9.0},
    ]
    s = parse_detalle(rows, name="x")
    assert list(s.index.strftime("%Y-%m-%d")) == ["2026-01-01", "2026-01-03"]
    assert s.iloc[0] == 1.0


def _daily(start, end, value=1.0):
    idx = pd.date_range(start, end, freq="D")
    return pd.Series(value, index=idx)


def test_to_monthly_mean_and_last():
    s = pd.Series([1.0, 3.0, 10.0], index=pd.to_datetime(["2026-01-05", "2026-01-31", "2026-02-27"]))
    s = pd.concat([_daily("2025-12-01", "2025-12-31", 5.0), s])
    assert to_monthly(s, "mean").loc["2026-01-01"] == pytest.approx(2.0)
    assert to_monthly(s, "last").loc["2026-01-01"] == 3.0


def test_to_monthly_sum_marks_empty_months_as_missing():
    s = pd.concat([_daily("2026-01-01", "2026-01-31", 1.0), _daily("2026-03-01", "2026-03-31", 2.0)])
    m = to_monthly(s, "sum")
    assert m.loc["2026-01-01"] == 31
    assert np.isnan(m.loc["2026-02-01"])
    assert m.loc["2026-03-01"] == 62


def test_to_monthly_drops_incomplete_last_month_for_daily_series():
    s = _daily("2026-08-01", "2026-10-15")
    m = to_monthly(s, "mean")
    assert m.index.max() == pd.Timestamp("2026-09-01")


def test_to_monthly_keeps_last_month_for_monthly_series():
    s = pd.Series([1.0, 2.0, 3.0], index=pd.to_datetime(["2026-06-30", "2026-07-31", "2026-08-31"]))
    assert to_monthly(s, "last").index.max() == pd.Timestamp("2026-08-01")


def test_to_monthly_rejects_unknown_agg():
    with pytest.raises(ValueError):
        to_monthly(_daily("2026-01-01", "2026-01-31"), "median")
