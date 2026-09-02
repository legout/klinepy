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
        "overlays",
        "indicators",
        "title",
        "height",
        "precision",
        "up_color",
        "down_color",
        "no_change_color",
        "accent_color",
        "price_line_color",
        "background_color",
        "grid_color",
        "border_color",
        "text_color",
    )
    return json.dumps({k: getattr(chart, k) for k in keys}).replace("</", "<\\/")


_JS = """
let _seriesSeq = 0;

// Box overlay (e.g. Darvas): rect figure from two corner points.
// Border color comes from the per-overlay styles override at create time.
registerOverlay({
  name: "box",
  totalStep: 2,
  needDefaultPointFigure: true,
  needDefaultXAxisFigure: true,
  needDefaultYAxisFigure: true,
  createPointFigures: ({ coordinates }) =>
    coordinates.length === 2
      ? [{
          type: "rect",
          attrs: {
            x: Math.min(coordinates[0].x, coordinates[1].x),
            y: Math.min(coordinates[0].y, coordinates[1].y),
            width: Math.abs(coordinates[1].x - coordinates[0].x),
            height: Math.abs(coordinates[1].y - coordinates[0].y),
          },
        }]
      : [],
});

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
  container.style.background = cfg.background_color;
  el.appendChild(container);

  const lines = cfg.lines || {};
  const overlayNames = Object.keys(lines);
  const accent = cfg.accent_color;

  const styles = {
    grid: {
      horizontal: { color: cfg.grid_color },
      vertical: { color: cfg.grid_color },
    },
    candle: {
      bar: {
        upColor: cfg.up_color,
        downColor: cfg.down_color,
        noChangeColor: cfg.no_change_color,
        upBorderColor: cfg.up_color,
        downBorderColor: cfg.down_color,
        noChangeBorderColor: cfg.no_change_color,
        upWickColor: cfg.up_color,
        downWickColor: cfg.down_color,
        noChangeWickColor: cfg.no_change_color,
      },
      priceMark: {
        high: { color: cfg.text_color },
        low: { color: cfg.text_color },
        last: {
          upColor: cfg.price_line_color,
          downColor: cfg.price_line_color,
          noChangeColor: cfg.price_line_color,
        },
      },
    },
    indicator: {
      bars: [{
        upColor: cfg.up_color,
        downColor: cfg.down_color,
        noChangeColor: cfg.no_change_color,
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
      // Overlays need data-loaded axes; create them once, after first load.
      (cfg.overlays || []).forEach((o) => {
        try {
          chart.createOverlay(
            o.name === "rect"
              ? { ...o, name: "box", styles: { rect: { style: "stroke", borderColor: accent, borderSize: 1 } } }
              : o
          );
        } catch (e) {
          console.warn("overlay failed:", o.name, e);
        }
      });
      // scrollToDataIndex here breaks overlay rendering in 10.0.2;
      // offset 0 shows the latest bars instead.
      try {
        chart.setOffsetRightDistance(0);
      } catch (e) { /* older API */ }
    }
  };
  chart.setDataLoader({ getBars: ({ callback }) => loadBars(callback) });

  chart.createIndicator({ name: "VOL", paneId: "candle_pane_vol" });
  chart.setPaneOptions({ id: "candle_pane_vol", height: 90 });
  // Overlay lines: plot the synced Python values, amber accent, on the price pane.
  overlayNames.forEach((n) => addSeries(chart, n, lines[n], "candle_pane", accent, "price"));
  // Own-pane series (e.g. rel vol): one sub-pane per named series.
  const panes = cfg.panes || {};
  let paneCount = 0;
  Object.keys(panes).forEach((n) => {
    const paneId = "pane_line_" + (paneCount++);
    addSeries(chart, n, panes[n], paneId, accent, "normal");
    chart.setPaneOptions({ id: paneId, height: 90 });
  });
  // Overlays (boxes, lines, tags): created inside loadBars after first data.

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
  import {{ init, registerIndicator, registerOverlay }} from "{_KLINECHARTS_ESM}";
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
