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


def test_output_contains_line_and_pane_values():
    chart = KLineChart(_bars(), lines={"SMA 20": [10.0, 10.5]}, panes={"rel vol": [1.2, 0.8]})
    for out in (chart.to_html(), chart.fragment()):
        assert '"SMA 20": [10.0, 10.5]' in out
        assert '"rel vol": [1.2, 0.8]' in out
        assert "pane_line_" in out  # own-pane series wired


def test_output_contains_overlays():
    box = {"start": 1767225600000, "end": 1767312000000, "top": 11.5, "bottom": 9.0}
    doc = KLineChart(_bars(), overlays=[box]).to_html()
    assert '"name": "rect"' in doc
    assert '"value": 11.5' in doc
    assert "createOverlay" in doc


def test_dot_overlay_registered_in_both_embeds():
    # bundle blue_dots emit name:"dot"; klinecharts has no built-in dot,
    # so both embeds must register the circle-figure overlay.
    for embed in (KLineChart._esm, KLineChart(_bars()).to_html()):
        assert 'name: "dot"' in embed
        assert 'type: "circle"' in embed


def test_standalone_body_uses_chart_background():
    doc = KLineChart(_bars(), colors={"background": "#0f172a"}).to_html()
    assert '<body style="margin:0;background:#0f172a">' in doc
