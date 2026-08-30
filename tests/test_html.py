"""HTML output tests: standalone document vs embeddable fragment."""

from __future__ import annotations

import datetime as dt

from klinepy import KLineChart, fragment, html


def _bars():
    return [
        {
            "session": dt.date.fromisoformat(d),
            "open": 10.0,
            "high": 11.0,
            "low": 9.0,
            "close": 10.5,
            "volume": 1000,
        }
        for d in ("2026-01-01", "2026-01-02")
    ]


def test_html_document_contains_cdn_and_bars():
    doc = KLineChart(_bars(), title="AAPL").to_html()
    assert "<html" in doc
    assert "klinecharts@10.0.2" in doc
    assert '"close": 10.5' in doc


def test_fragment_has_no_html_wrapper():
    frag = KLineChart(_bars()).fragment()
    assert "<html" not in frag
    assert "klinecharts@10.0.2" in frag
    assert '"close": 10.5' in frag


def test_module_level_wrappers():
    chart = KLineChart(_bars())
    assert html(chart) == chart.to_html()
    assert fragment(chart) == chart.fragment()
