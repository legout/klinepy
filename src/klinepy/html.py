"""Standalone HTML document + embeddable fragment renderers (CDN ESM, no build).

The JS is the same chart bootstrap the anywidget uses, minus the widget
messaging layer: read the trait values into a plain ``cfg`` object, then
``init()`` the chart from klinecharts' pinned CDN ESM build.
"""

from __future__ import annotations

import html as _html
import json
import uuid
from typing import TYPE_CHECKING

from klinepy._theme import _KLINECHARTS_ESM

if TYPE_CHECKING:
    from klinepy.widget import KLineChart

__all__ = ["fragment", "html"]


def _cfg(chart: KLineChart) -> str:
    """Trait values as a JSON config object for the page script."""
    keys = (
        "bars",
        "lines",
        "panes",
        "indicators",
        "title",
        "height",
        "precision",
        "up_color",
        "down_color",
        "accent_color",
        "grid_color",
        "border_color",
        "text_color",
    )
    return json.dumps({k: getattr(chart, k) for k in keys}).replace("</", "<\\/")


_JS = """
let _seriesSeq = 0;

// Plot Python-supplied values as a custom indicator line.
function addSeries(chart, name, values, paneId, accent, series) {
  const key = "klinepy_series_" + (_seriesSeq++);
  registerIndicator({
    name: key,
    shortName: name,
    series,
    precision: 2,
    figures: [{ key: "v", title: name + ": ", type: "line", styles: () => ({ color: accent, size: 1.5 }) }],
    calc: (dataList, indicator) => dataList.map((d, i) => ({ v: values[i] ?? null })),
  });
  return chart.createIndicator({ name: key, paneId }, paneId === "candle_pane");
}

async function render(el, cfg) {
  const container = document.createElement("div");
  container.style.width = "100%";
  container.style.height = cfg.height + "px";
  el.appendChild(container);

  const lines = cfg.lines || {};
  const overlayNames = Object.keys(lines);

  const styles = {
    grid: {
      horizontal: { color: cfg.grid_color },
      vertical: { color: cfg.grid_color },
    },
    candle: {
      bar: {
        upColor: cfg.up_color,
        downColor: cfg.down_color,
        noChangeColor: cfg.down_color,
        upBorderColor: cfg.up_color,
        downBorderColor: cfg.down_color,
        noChangeBorderColor: cfg.down_color,
        upWickColor: cfg.up_color,
        downWickColor: cfg.down_color,
        noChangeWickColor: cfg.down_color,
      },
    },
    indicator: {
      bars: [{
        upColor: cfg.up_color,
        downColor: cfg.down_color,
        noChangeColor: cfg.down_color,
      }],
    },
    xAxis: {
      axisLine: { color: cfg.border_color },
      tickLine: { color: cfg.border_color },
      tickText: { color: cfg.text_color },
    },
    yAxis: {
      axisLine: { color: cfg.border_color },
      tickLine: { color: cfg.border_color },
      tickText: { color: cfg.text_color },
    },
    separator: { color: cfg.border_color },
  };

  const chart = init(container, {
    styles,
    locale: "en-US",
    timezone: "UTC",
    layout: { yAxis: { position: "right" } },
  });
  chart.setSymbol({ ticker: cfg.title || "—", pricePrecision: cfg.precision });
  chart.setPeriod({ span: 1, type: "day" });

  const toKlineBars = () =>
    (cfg.bars || []).map((b) => ({
      timestamp: b.time,
      open: b.open,
      high: b.high,
      low: b.low,
      close: b.close,
      volume: b.volume ?? 0,
    }));

  let initialScrollDone = false;
  const loadBars = (callback) => {
    const bars = toKlineBars();
    callback(bars, false);
    if (!initialScrollDone && bars.length) {
      initialScrollDone = true;
      try {
        chart.scrollToDataIndex(Math.max(0, bars.length - 120));
      } catch (e) { /* older API */ }
    }
  };
  chart.setDataLoader({ getBars: ({ callback }) => loadBars(callback) });

  chart.createIndicator({ name: "VOL", paneId: "candle_pane_vol" });
  chart.setPaneOptions({ id: "candle_pane_vol", height: 90 });
  // Overlay lines: plot the synced Python values, amber accent, on the price pane.
  const accent = cfg.accent_color;
  overlayNames.forEach((n) => addSeries(chart, n, lines[n], "candle_pane", accent, "price"));
  // Own-pane series (e.g. rel vol): one sub-pane per named series.
  const panes = cfg.panes || {};
  let paneCount = 0;
  Object.keys(panes).forEach((n) => {
    const paneId = "pane_line_" + (paneCount++);
    addSeries(chart, n, panes[n], paneId, accent, "normal");
    chart.setPaneOptions({ id: paneId, height: 90 });
  });

  const inds = cfg.indicators || [];
  let subCount = 0;
  inds.forEach((spec) => {
    try {
      const entry = { name: spec.name };
      if (spec.params) entry.calcParams = spec.params;
      if (spec.pane === "candle") {
        entry.paneId = "candle_pane";
        chart.createIndicator(entry, true);
      } else {
        const paneId = "ind_pane_" + (subCount++);
        entry.paneId = paneId;
        chart.createIndicator(entry);
        chart.setPaneOptions({ id: paneId, height: spec.height || 90 });
      }
    } catch (e) {
      console.warn("indicator failed:", spec.name, e);
    }
  });
}
"""

_BODY = f"""
<div id="__ID__"></div>
<script type="module">
  import {{ init, registerIndicator }} from "{_KLINECHARTS_ESM}";
  const cfg = __CFG__;
  const el = document.getElementById("__ID__");
  {_JS}
  render(el, cfg);
</script>
"""


def fragment(chart: KLineChart) -> str:
    """Embeddable HTML fragment — no ``<html>``/``<body>`` wrapper."""
    dom_id = f"klinepy-chart-{uuid.uuid4().hex[:8]}"
    return _BODY.replace("__ID__", dom_id).replace("__CFG__", _cfg(chart))


def html(chart: KLineChart) -> str:
    """Standalone HTML document with CDN ESM import."""
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        '<head><meta charset="utf-8"><title>'
        f"{_html.escape(chart.title or 'klinepy')}</title></head>\n"
        f"<body>\n{fragment(chart)}\n</body>\n</html>\n"
    )
