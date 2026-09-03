"""static-charts-v1 bundle: validation, stamping, emit/load, round-trip."""

from __future__ import annotations

import datetime as dt
import json

import pytest

from klinepy import ChartBundle, emit, fragment, html, load_bundle, to_chart

_BARS = [
    {
        "session": dt.date.fromisoformat(d),
        "open": 10.0,
        "high": 11.0,
        "low": 9.0,
        "close": 10.5,
        "volume": 1000,
    }
    for d in ("2026-01-01", "2026-01-02", "2026-01-03")
]


def test_emit_stamps_schema_version_and_normalizes():
    data = emit({"symbol": "AAPL", "bars": _BARS, "benchmark": "SPY"})
    assert data["schema_version"] == "static-charts-v1"
    assert data["bars"][0] == {
        "time": 1767225600000,
        "open": 10.0,
        "high": 11.0,
        "low": 9.0,
        "close": 10.5,
        "volume": 1000.0,
    }
    assert data["benchmark"] == "SPY"


def test_bundle_dataclass_and_emit_roundtrip(tmp_path):
    path = tmp_path / "AAPL.json"
    data = ChartBundle(symbol="AAPL", bars=_BARS, benchmark="SPY").dump(path)
    assert path.exists()
    assert json.loads(path.read_text()) == data
    assert load_bundle(path) == data


def test_rejects_wrong_schema_version():
    with pytest.raises(ValueError, match="unsupported schema_version"):
        emit({"schema_version": "static-charts-v2", "symbol": "A", "bars": _BARS})


def test_rejects_missing_symbol_or_bars():
    with pytest.raises(ValueError, match="symbol"):
        emit({"bars": _BARS})
    with pytest.raises(ValueError, match="bars"):
        emit({"symbol": "A"})


def test_rejects_bad_bars():
    with pytest.raises(ValueError, match="time"):
        emit({"symbol": "A", "bars": [{"open": 1.0}]})


def test_rs_line_padded_to_bars():
    data = emit({"symbol": "A", "bars": _BARS, "rs_line": [1.0, 2.0]})
    assert data["rs_line"] == [1.0, 2.0, None]


def test_blue_dots_become_overlays():
    data = emit(
        {
            "symbol": "A",
            "bars": _BARS,
            "blue_dots": [{"session": "2026-01-02", "value": 11.0}],
        }
    )
    assert data["blue_dots"] == [
        {"name": "dot", "points": [{"timestamp": 1767312000000, "value": 11.0}]}
    ]


def test_rejects_bad_blue_dot():
    with pytest.raises(ValueError, match="blue dot"):
        emit({"symbol": "A", "bars": _BARS, "blue_dots": [{"value": 1.0}]})


def test_fundamentals_pass_through():
    data = emit(
        {"symbol": "A", "bars": _BARS, "fundamentals": {"market_cap": 1e12}}
    )
    assert data["fundamentals"] == {"market_cap": 1e12}


def test_to_chart_renders_bundle():
    data = emit(
        {
            "symbol": "AAPL",
            "bars": _BARS,
            "rs_line": [1.0, 1.1, None],
            "blue_dots": [{"session": "2026-01-02", "value": 11.0}],
            "benchmark": "SPY",
            "fundamentals": {"pe": 30},
        }
    )
    doc = to_chart(data).to_html()
    assert "AAPL" in doc
    assert '"rs": [1.0, 1.1, null]' in doc
    assert '"name": "dot"' in doc


def test_emit_is_idempotent_on_emitted_bundle():
    data = emit(
        {
            "symbol": "A",
            "bars": _BARS,
            "rs_line": [1.0, 1.1, None],
            "blue_dots": [{"session": "2026-01-02", "value": 11.0}],
        }
    )
    assert emit(dict(data)) == data


def test_html_and_fragment_accept_bundles_directly(tmp_path):
    path = tmp_path / "A.json"
    data = emit({"symbol": "A", "bars": _BARS, "rs_line": [1.0, 1.1, None]}, path)
    for out in (html(data), fragment(data), html(path), fragment(path)):
        assert '"rs": [1.0, 1.1, null]' in out
        assert "klinecharts@10.0.2" in out
    assert "<html" in html(path) and "<html" not in fragment(path)


def test_to_chart_from_path(tmp_path):
    path = tmp_path / "A.json"
    emit({"symbol": "A", "bars": _BARS}, path)
    assert "A" in to_chart(path).to_html()
