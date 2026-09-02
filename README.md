# klinepy

Python wrapper for KLineCharts (klinecharts@10) — one chart spec, three outputs:
standalone HTML, embeddable fragment, marimo/anywidget widget.

Three built-in themes — grayscale + amber (default), pastel green/red, black/grey —
plus fully custom colors:

| `theme="default"` | `theme="classic"` | `theme="mono"` |
|---|---|---|
| ![default](docs/images/default.png) | ![classic](docs/images/classic.png) | ![mono](docs/images/mono.png) |

```python
KLineChart(bars, theme="classic")   # preset; explicit *_color kwargs still override
```

Custom palettes via a dict (merges into the theme) or the `Colors` dataclass
(replaces it) — both accept the same keys: `up`, `down`, `no_change`, `accent`,
`price_line` (dashed last-price line + tag), `background`, `grid`, `border`, `text`.

```python
from klinepy import KLineChart, Colors

# tweak one key of a preset
KLineChart(bars, theme="classic", colors={"accent": "#b91c1c"})

# full custom, e.g. dark
KLineChart(bars, colors=Colors(
    up="#4ade80", down="#f87171", accent="#fbbf24", price_line="#fbbf24",
    background="#0f172a", grid="#1e293b", border="#334155", text="#94a3b8",
))
```

![dark](docs/images/dark.png)

Precedence: `*_color` kwargs > `colors` > `theme` > defaults.

Grayscale theme with a single amber accent (`#d97706`). The JS side loads the
klinecharts ESM build from jsDelivr (needs internet in the browser); the
Python side is pure data (polars/pandas frames or dicts — no data deps).

## Usage

```python
from klinepy import KLineChart, html, fragment

chart = KLineChart(
    bars,                      # polars/pandas DataFrame or list of dicts
    lines={"SMA 20": sma},     # overlay lines on the price pane, aligned/padded to bar count
    panes={"rel vol": rv},     # own-pane series (one sub-pane per named series)
    overlays=[boxes],          # boxes / klinecharts overlay specs, see below
    title="AAPL",
    indicators=[{"name": "MACD"}}],  # optional built-in klinecharts indicators
    height=460,
)

# 1. marimo / Jupyter widget
mo.ui.anywidget(chart)

# 2. standalone HTML document (CDN ESM, no build step)
open("aapl.html", "w").write(chart.to_html())   # or: html(chart)

# 3. embeddable fragment for web apps (no <html> wrapper)
page += chart.fragment()                        # or: fragment(chart)
```

### Overlays

`lines` and `panes` plot the values you pass (amber accent). For boxes — e.g.
Darvas:

```python
chart = KLineChart(bars, overlays=[
    {"start": dt.date(2026, 1, 5), "end": dt.date(2026, 1, 25),
     "top": 103.0, "bottom": 97.0},          # rendered as an amber rect
])
```

![boxes](docs/images/boxes.png)

Full [klinecharts overlay specs](https://klinecharts.com/en-US/guide/overlay)
(`priceLine`, `segment`, `simpleTag`, …) pass through unchanged:

```python
overlays=[{"name": "priceLine", "points": [{"timestamp": ts_ms, "value": 99.5}]}]
```

## Development

```bash
uv sync
uv run pytest
```
