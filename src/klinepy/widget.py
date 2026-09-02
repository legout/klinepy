"""KLineChart anywidget (klinecharts v10): candle pane + volume pane + overlay lines.

Uses the v10 data-loader API (``setDataLoader`` → ``getBars``), renders
overlay lines as custom indicators, and keeps all styling grayscale with
the single amber accent.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import anywidget
import traitlets

from klinepy._theme import _DEFAULTS, _KLINECHARTS_ESM, Colors, _merge_colors
from klinepy.normalize import (
    _infer_precision,
    _normalize_lines,
    _normalize_overlays,
    normalize_ohlcv,
)

__all__ = ["KLineChart"]


class KLineChart(anywidget.AnyWidget):
    """klinecharts v10 widget: candle pane + volume pane + overlay lines."""

    _esm = f"""
    import {{ init, dispose, registerIndicator, registerOverlay }} from "{_KLINECHARTS_ESM}";

    let _seriesSeq = 0;

    // Box overlay (e.g. Darvas): rect figure from two corner points.
    // Border color comes from the per-overlay styles override at create time.
    registerOverlay({{
      name: "box",
      totalStep: 2,
      needDefaultPointFigure: true,
      needDefaultXAxisFigure: true,
      needDefaultYAxisFigure: true,
      createPointFigures: ({{ coordinates }}) =>
        coordinates.length === 2
          ? [{{
              type: "rect",
              attrs: {{
                x: Math.min(coordinates[0].x, coordinates[1].x),
                y: Math.min(coordinates[0].y, coordinates[1].y),
                width: Math.abs(coordinates[1].x - coordinates[0].x),
                height: Math.abs(coordinates[1].y - coordinates[0].y),
              }},
            }}]
          : [],
    }});

    // Plot Python-supplied values as a custom indicator line.
    function addSeries(chart, name, values, paneId, accent, series) {{
      const key = "klinepy_series_" + (_seriesSeq++);
      registerIndicator({{
        name: key,
        shortName: name,
        series,
        precision: 2,
        figures: [{{ key: "v", title: name + ": ", type: "line", styles: () => ({{ color: accent, size: 1.5 }}) }}],
        calc: (dataList, indicator) => dataList.map((d, i) => ({{ v: values[i] ?? null }})),
      }});
      return chart.createIndicator({{ name: key, paneId }}, paneId === "candle_pane");
    }}

    async function render({{ model, el }}) {{
      const container = document.createElement("div");
      container.style.width = "100%";
      container.style.height = model.get("height") + "px";
      container.style.background = model.get("background_color");
      el.appendChild(container);

      const lines = model.get("lines") || {{}};
      const overlayNames = Object.keys(lines);
      const accent = model.get("accent_color");

      const styles = {{
        grid: {{
          horizontal: {{ color: model.get("grid_color") }},
          vertical: {{ color: model.get("grid_color") }},
        }},
        candle: {{
          bar: {{
            upColor: model.get("up_color"),
            downColor: model.get("down_color"),
            noChangeColor: model.get("no_change_color"),
            upBorderColor: model.get("up_color"),
            downBorderColor: model.get("down_color"),
            noChangeBorderColor: model.get("no_change_color"),
            upWickColor: model.get("up_color"),
            downWickColor: model.get("down_color"),
            noChangeWickColor: model.get("no_change_color"),
          }},
          priceMark: {{
            high: {{ color: model.get("text_color") }},
            low: {{ color: model.get("text_color") }},
            last: {{
              upColor: model.get("price_line_color"),
              downColor: model.get("price_line_color"),
              noChangeColor: model.get("price_line_color"),
            }},
          }},
        }},
        indicator: {{
          bars: [{{
            upColor: model.get("up_color"),
            downColor: model.get("down_color"),
            noChangeColor: model.get("no_change_color"),
          }}],
        }},
        xAxis: {{
          axisLine: {{ color: model.get("border_color") }},
          tickLine: {{ color: model.get("border_color") }},
          tickText: {{ color: model.get("text_color") }},
        }},
        yAxis: {{
          axisLine: {{ color: model.get("border_color") }},
          tickLine: {{ color: model.get("border_color") }},
          tickText: {{ color: model.get("text_color") }},
        }},
        separator: {{ color: model.get("border_color") }},
      }};

      const chart = init(container, {{
        styles,
        locale: "en-US",
        timezone: "UTC",
        layout: {{ yAxis: {{ position: "right" }} }},
      }});
      chart.setSymbol({{ ticker: model.get("title") || "—", pricePrecision: model.get("precision") }});
      chart.setPeriod({{ span: 1, type: "day" }});

      // klinecharts KLineData uses `timestamp` (ms); our records use `time`.
      const toKlineBars = () =>
        (model.get("bars") || []).map((b) => ({{
          timestamp: b.time,
          open: b.open,
          high: b.high,
          low: b.low,
          close: b.close,
          volume: b.volume ?? 0,
        }}));

      // After the first data load, scroll the viewport to the most recent
      // bars: a full-history view crushes the base of parabolic movers.
      let initialScrollDone = false;
      const loadBars = (callback) => {{
        const bars = toKlineBars();
        callback(bars, false);
        if (!initialScrollDone && bars.length) {{
          initialScrollDone = true;
          // Overlays need data-loaded axes; create them once, after first load.
          (model.get("overlays") || []).forEach((o) => {{
            try {{
              chart.createOverlay(
                o.name === "rect"
                  ? {{ ...o, name: "box", styles: {{ rect: {{ style: "stroke", borderColor: accent, borderSize: 1 }} }} }}
                  : o
              );
            }} catch (e) {{
              console.warn("overlay failed:", o.name, e);
            }}
          }});
          // scrollToDataIndex here breaks overlay rendering in 10.0.2;
          // offset 0 shows the latest bars instead.
          try {{
            chart.setOffsetRightDistance(0);
          }} catch (e) {{ /* older API */ }}
        }}
      }};
      chart.setDataLoader({{ getBars: ({{ callback }}) => loadBars(callback) }});

      chart.createIndicator({{ name: "VOL", paneId: "candle_pane_vol" }});
      chart.setPaneOptions({{ id: "candle_pane_vol", height: 90 }});
      // Overlay lines: plot the synced Python values, amber accent, on the price pane.
      overlayNames.forEach((n) => addSeries(chart, n, lines[n], "candle_pane", accent, "price"));
      // Own-pane series (e.g. rel vol): one sub-pane per named series.
      const panes = model.get("panes") || {{}};
      let paneCount = 0;
      Object.keys(panes).forEach((n) => {{
        const paneId = "pane_line_" + (paneCount++);
        addSeries(chart, n, panes[n], paneId, accent, "normal");
        chart.setPaneOptions({{ id: paneId, height: 90 }});
      }});
      // Built-in indicators: pane="candle" stacks on the price pane,
      // pane="sub" (default) gets its own sub-pane below volume.
      const inds = model.get("indicators") || [];
      let subCount = 0;
      inds.forEach((spec) => {{
        try {{
          const entry = {{ name: spec.name }};
          if (spec.params) entry.calcParams = spec.params;
          if (spec.pane === "candle") {{
            entry.paneId = "candle_pane";
            chart.createIndicator(entry, true);
          }} else {{
            const paneId = "ind_pane_" + (subCount++);
            entry.paneId = paneId;
            chart.createIndicator(entry);
            chart.setPaneOptions({{ id: paneId, height: spec.height || 90 }});
          }}
        }} catch (e) {{
          console.warn("indicator failed:", spec.name, e);
        }}
      }});

      const onBarsChange = () => chart.resetData();
      model.on("change:bars", onBarsChange);

      const observer = new ResizeObserver(() => {{
        chart.resize(container.clientWidth, model.get("height"));
      }});
      observer.observe(container);

      model.on("destroy", () => {{
        observer.disconnect();
        try {{ dispose(container); }} catch (e) {{ /* already gone */ }}
      }});
    }}

    export default {{ render }};
    """

    bars = traitlets.List(trait=traitlets.Dict(traits=None)).tag(sync=True)
    lines = traitlets.Dict().tag(sync=True)
    panes = traitlets.Dict().tag(sync=True)
    overlays = traitlets.List(trait=traitlets.Dict(traits=None)).tag(sync=True)
    indicators = traitlets.List(trait=traitlets.Dict(traits=None)).tag(sync=True)
    title = traitlets.Unicode("").tag(sync=True)
    height = traitlets.Int(460).tag(sync=True)
    precision = traitlets.Int(2).tag(sync=True)
    up_color = traitlets.Unicode(_DEFAULTS.up).tag(sync=True)
    down_color = traitlets.Unicode(_DEFAULTS.down).tag(sync=True)
    no_change_color = traitlets.Unicode(_DEFAULTS.no_change).tag(sync=True)
    accent_color = traitlets.Unicode(_DEFAULTS.accent).tag(sync=True)
    price_line_color = traitlets.Unicode(_DEFAULTS.price_line).tag(sync=True)
    background_color = traitlets.Unicode(_DEFAULTS.background).tag(sync=True)
    grid_color = traitlets.Unicode(_DEFAULTS.grid).tag(sync=True)
    border_color = traitlets.Unicode(_DEFAULTS.border).tag(sync=True)
    text_color = traitlets.Unicode(_DEFAULTS.text).tag(sync=True)

    def __init__(
        self,
        bars: Any,
        *,
        lines: Mapping[str, Sequence[float | None]] | None = None,
        panes: Mapping[str, Sequence[float | None]] | None = None,
        overlays: Sequence[Mapping[str, Any]] | None = None,
        indicators: Sequence[Mapping[str, Any]] | None = None,
        theme: str = "default",
        colors: Colors | Mapping[str, str] | None = None,
        title: str = "",
        height: int = 460,
        precision: int | None = None,
        up_color: str | None = None,
        down_color: str | None = None,
        no_change_color: str | None = None,
        accent_color: str | None = None,
        price_line_color: str | None = None,
        background_color: str | None = None,
        grid_color: str | None = None,
        border_color: str | None = None,
        text_color: str | None = None,
    ) -> None:
        # precedence: explicit *_color kwargs > colors (dict merges into theme,
        # Colors replaces) > theme > defaults
        t = _merge_colors(theme, colors)
        records = normalize_ohlcv(bars)
        super().__init__(
            bars=records,
            lines=_normalize_lines(lines, len(records)),
            panes=_normalize_lines(panes, len(records)),
            overlays=_normalize_overlays(overlays),
            indicators=[dict(ind) for ind in (indicators or [])],
            title=title,
            height=height,
            precision=precision if precision is not None else _infer_precision(records),
            up_color=up_color if up_color is not None else t.up,
            down_color=down_color if down_color is not None else t.down,
            no_change_color=no_change_color if no_change_color is not None else t.no_change,
            accent_color=accent_color if accent_color is not None else t.accent,
            price_line_color=price_line_color if price_line_color is not None else t.price_line,
            background_color=background_color if background_color is not None else t.background,
            grid_color=grid_color if grid_color is not None else t.grid,
            border_color=border_color if border_color is not None else t.border,
            text_color=text_color if text_color is not None else t.text,
        )

    def to_html(self) -> str:
        """Standalone HTML document (CDN ESM, no build step)."""
        from klinepy.html import html

        return html(self)

    def fragment(self) -> str:
        """Embeddable HTML fragment (no <html> wrapper)."""
        from klinepy.html import fragment

        return fragment(self)
