# klinepy

Python wrapper for KLineCharts (klinecharts@10) — one chart spec, three outputs:
standalone HTML, embeddable fragment, marimo/anywidget widget.

Grayscale theme with a single amber accent (`#d97706`). The JS side loads the
klinecharts ESM build from jsDelivr (needs internet in the browser); the
Python side is pure data (polars/pandas frames or dicts — no data deps).

## Usage

```python
from klinepy import KLineChart, html, fragment

chart = KLineChart(
    bars,                      # polars/pandas DataFrame or list of dicts
    lines={"SMA 20": sma},     # optional overlay values, aligned/padded to bar count
    title="AAPL",
    indicators=[{"name": "MACD"}],  # optional built-in klinecharts indicators
    height=460,
)

# 1. marimo / Jupyter widget
mo.ui.anywidget(chart)

# 2. standalone HTML document (CDN ESM, no build step)
open("aapl.html", "w").write(chart.to_html())   # or: html(chart)

# 3. embeddable fragment for web apps (no <html> wrapper)
page += chart.fragment()                        # or: fragment(chart)
```

## Development

```bash
uv sync
uv run pytest
```
