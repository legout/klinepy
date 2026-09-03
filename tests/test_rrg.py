"""RRG presentation-mode tests: precomputed points in, presentation only."""

from __future__ import annotations

import json

from klinepy import KLineChart

# Data never passes through klinepy: coordinates arrive precomputed.
_WEEKS = ["2026-06-05", "2026-06-12", "2026-06-19", "2026-06-26"]
_SERIES = [
    {"name": "Tech", "points": [{"date": d, "x": 99.0 + i * 0.5, "y": 101.0 - i * 0.25}
                                for i, d in enumerate(_WEEKS)]},
    {"name": "Energy", "points": [{"date": d, "x": 101.5, "y": 98.0} for d in _WEEKS[:2]]},
]


def _rrg_chart(**kw):
    # One dummy bar: RRG mode ignores bars, but KLineChart validates them.
    bar = {"session": "2026-01-02", "open": 10.0, "high": 11.0, "low": 9.0,
           "close": 10.5, "volume": 0}
    return KLineChart([bar], rrg=kw.pop("rrg", _SERIES), **kw)


def test_rrg_points_normalized_and_sorted():
    w = _rrg_chart()
    assert w.rrg[0]["name"] == "Tech"
    pts = w.rrg[0]["points"]
    assert [p["x"] for p in pts] == [99.0, 99.5, 100.0, 100.5]
    dates = [p["date"] for p in pts]
    assert dates == sorted(dates) and all(isinstance(d, int) for d in dates)


def test_rrg_rows_missing_xy_dropped():
    s = [{"name": "G", "points": [{"date": "2026-06-05", "x": 100.0, "y": None},
                                  {"date": "2026-06-12", "x": 101.0, "y": 99.0}]}]
    (pts,) = [s2["points"] for s2 in _rrg_chart(rrg=s).rrg]
    assert len(pts) == 1 and pts[0]["x"] == 101.0


def test_rrg_and_bars_are_independent():
    w = _rrg_chart()
    assert len(w.bars) == 1 and len(w.rrg) == 2


def test_rrg_html_has_canvas_and_data_but_no_kline_math():
    out = _rrg_chart(title="RRG").to_html()
    assert "<canvas" in out and "renderRRG" in out
    assert "klinecharts" not in out  # RRG mode: raw Canvas, no chart lib load
    payload = json.loads(
        "[" + out.split("const cfg = ")[1].split(";\n  const el")[0] + "]"
    )[0]
    assert payload["rrg"][0]["name"] == "Tech"
    assert payload["rrg"][0]["points"][0]["x"] == 99.0


def test_rrg_spline_and_zoom_helpers_present():
    out = _rrg_chart().to_html()
    assert "catmullRomSegments" in out  # spline tails through weekly vertices
    assert "DETAIL_LIMIT" in out  # line-only degradation above 20 series
    assert ">= 8" in out  # 8px click-vs-drag threshold (useDragZoom MIN_DRAG_PX)
