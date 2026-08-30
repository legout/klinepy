"""Tests for klinepy.normalize (data normalization only — no widget)."""

from __future__ import annotations

import datetime as dt

import pytest

from klinepy.normalize import normalize_ohlcv


def _row(date: str, o=10.0, h=11.0, l=9.0, c=10.5, v=1_000):
    return {
        "session": dt.date.fromisoformat(date),
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": v,
    }


@pytest.fixture()
def bars():
    # deliberately unsorted + one row missing close
    return [
        _row("2026-01-02"),
        {
            "session": dt.date(2026, 1, 3),
            "open": 10.0,
            "high": 11.0,
            "low": 9.0,
            "close": None,
            "volume": 500,
        },
        _row("2026-01-01"),
    ]


def test_normalize_sorts_and_drops_incomplete(bars):
    out = normalize_ohlcv(bars)
    assert len(out) == 2
    assert [r["time"] for r in out] == sorted(r["time"] for r in out)
    assert out[0]["time"] == int(
        dt.datetime(2026, 1, 1, tzinfo=dt.UTC).timestamp() * 1000
    )
    assert out[0]["volume"] == 1_000.0


def test_normalize_epoch_seconds_and_ms_passthrough():
    rows = [
        {"time": 1767225600, "open": 1, "high": 2, "low": 0.5, "close": 1.5},  # seconds
        {"time": 1767225600_000, "open": 1, "high": 2, "low": 0.5, "close": 1.5},  # ms
    ]
    out = normalize_ohlcv(rows)
    assert out[0]["time"] == out[1]["time"] == 1767225600_000


def test_normalize_iso_string_dates():
    out = normalize_ohlcv(
        [{"date": "2026-01-05", "open": 1, "high": 2, "low": 0.5, "close": 1.5}]
    )
    assert out[0]["time"] == int(
        dt.datetime(2026, 1, 5, tzinfo=dt.UTC).timestamp() * 1000
    )


def test_normalize_rejects_missing_ohlc():
    with pytest.raises(ValueError, match="OHLC"):
        normalize_ohlcv([{"time": 1767225600, "open": 1, "high": 2, "low": 0.5}])


def test_polars_frame_input():
    pl = pytest.importorskip("polars")
    frame = pl.DataFrame(
        {
            "session": [dt.date(2026, 1, 1), dt.date(2026, 1, 2)],
            "open": [10.0, 10.5],
            "high": [11.0, 11.5],
            "low": [9.0, 9.5],
            "close": [10.5, 11.0],
            "volume": [1000, 1100],
        }
    )
    out = normalize_ohlcv(frame)
    assert len(out) == 2
    assert out[1]["close"] == 11.0
