"""Standalone HTML document + embeddable fragment renderers (CDN ESM, no build).

The JS is the same chart bootstrap the anywidget uses, minus the widget
messaging layer: read the trait values into a plain ``cfg`` object, then
``init()`` the chart from klinecharts' pinned CDN ESM build.
"""

from __future__ import annotations

import html as _html
import json
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from klinepy._rrg_js import _RRG_JS
from klinepy._theme import _KLINECHARTS_ESM

if TYPE_CHECKING:
    from klinepy.widget import KLineChart

__all__ = ["fragment", "html"]

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
  // rect (box sugar) → "box" overlay; dot markers get the amber accent.
  const overlaySpec = (o) =>
    o.name === "rect"
      ? { ...o, name: "box", styles: { rect: { style: "stroke", borderColor: accent, borderSize: 1 } } }
      : o.name === "dot"
        ? { ...o, styles: { point: { color: accent, borderColor: accent, borderSize: 6, radius: 3 } } }
        : o;
  const loadBars = (callback) => {
    const bars = toKlineBars();
    callback(bars, false);
    if (!initialScrollDone && bars.length) {
      initialScrollDone = true;
      // Overlays need data-loaded axes; create them once, after first load.
      (cfg.overlays || []).forEach((o) => {
        try {
          chart.createOverlay(overlaySpec(o));
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

_BODY = """
<div id="__ID__"></div>
<script type="module">
  __IMPORT__
  const cfg = __CFG__;
  const el = document.getElementById("__ID__");
  {JS_BODY}
  __CALL__;
</script>
"""


def _body(chart: KLineChart) -> str:
    if chart.rrg:
        # RRG presentation mode: raw Canvas 2D renderer — creates its own
        # canvas and never loads klinecharts (wrong tool for x/y space).
        js, import_line, call = _RRG_JS, "", "renderRRG(el, cfg)"
    else:
        js = _JS
        import_line = (
            "import { init, registerIndicator, registerOverlay } from "
            f'"{_KLINECHARTS_ESM}";'
        )
        call = "render(el, cfg)"
    return (
        _BODY.replace("{JS_BODY}", js)
        .replace("__CALL__", call)
        .replace("__IMPORT__", import_line)
        .replace("__ID__", f"klinepy-chart-{uuid.uuid4().hex[:8]}")
        .replace("__CFG__", _cfg(chart))
    )


def _cfg(chart: KLineChart) -> str:
    """Trait values as a JSON config object for the page script."""
    keys = (
        "bars",
        "lines",
        "panes",
        "overlays",
        "indicators",
        "rrg",
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


def _as_chart(
    chart: KLineChart | Mapping[str, Any] | str | Path,
) -> KLineChart:
    """A static-charts-v1 bundle (dict or JSON path) → chart; a chart passes through."""
    if isinstance(chart, (Mapping, str, Path)):
        from klinepy.bundle import to_chart  # deferred: bundle→widget→html chain

        return to_chart(chart)
    return chart


def fragment(chart: KLineChart | Mapping[str, Any] | str | Path) -> str:
    """Embeddable HTML fragment — no ``<html>``/``<body>`` wrapper.

    ``chart`` is a KLineChart, or a static-charts-v1 bundle (dict or JSON path).
    """
    return _body(_as_chart(chart))


def html(chart: KLineChart | Mapping[str, Any] | str | Path) -> str:
    """Standalone HTML document with CDN ESM import.

    ``chart`` is a KLineChart, or a static-charts-v1 bundle (dict or JSON path).
    """
    chart = _as_chart(chart)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        '<head><meta charset="utf-8"><title>'
        f"{_html.escape(chart.title or 'klinepy')}</title></head>\n"
        f"<body>\n{fragment(chart)}\n</body>\n</html>\n"
    )
