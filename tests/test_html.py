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
    import re

    chart = KLineChart(_bars())
    strip = lambda s: re.sub(r"klinepy-chart-\w+", "ID", s)
    assert strip(html(chart)) == strip(chart.to_html())
    assert strip(fragment(chart)) == strip(chart.fragment())


def test_fragments_have_unique_container_ids():
    a, b = fragment(KLineChart(_bars())), fragment(KLineChart(_bars()))
    id_a = a.split('id="')[1].split('"')[0]
    assert f'id="{id_a}"' in a and f'getElementById("{id_a}")' in a
    assert f'id="{id_a}"' not in b  # different id per fragment


def test_script_and_title_escaped():
    doc = KLineChart(_bars(), title="</script><b>x").to_html()
    assert "</script><b>" not in doc
    raw = '{"close": "</script>"}'
    assert raw not in doc
