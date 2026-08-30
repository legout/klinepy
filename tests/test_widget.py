"""Widget tests (ported from marketdata_screens tests/test_charting.py)."""

from __future__ import annotations

import datetime as dt

import pytest

from klinepy import KLineChart


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


def test_widget_traits_synced(bars):
    w = KLineChart(bars, lines={"SMA 20": [None, 10.5]}, title="TEST", height=123)
    assert w.bars and all(
        {"time", "open", "high", "low", "close"} <= set(r) for r in w.bars
    )
    assert w.lines["SMA 20"] == [None, 10.5]
    assert w.title == "TEST"
    assert w.height == 123
    assert w.accent_color == "#d97706"


def test_lines_padded_to_bar_count(bars):
    w = KLineChart(bars, lines={"x": [1.0]})
    assert w.lines["x"] == [1.0, None]


def test_precision_inference():
    rows = [_row("2026-01-0" + str(d), c=123.4567) for d in range(1, 4)]
    w = KLineChart(rows)
    assert w.precision == 4


def test_nan_line_values_become_none():
    w = KLineChart([_row("2026-01-01")], lines={"sma": [float("nan")]})
    assert w.lines["sma"] == [None]


def test_indicators_trait_synced():
    inds = [
        {"name": "MA", "pane": "candle", "params": [5, 10]},
        {"name": "MACD"},
        {"name": "RSI"},
    ]
    w = KLineChart([_row("2026-01-01")], indicators=inds)
    assert w.indicators == inds
    # empty default
    assert KLineChart([_row("2026-01-01")]).indicators == []
    # ESM wires built-in indicators
    assert 'model.get("indicators")' in KLineChart._esm
    assert "ind_pane_" in KLineChart._esm
