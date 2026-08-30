# HANDOFF — klinepy (charting split-off)

Origin: `~/projects/marketdata-screens` session 2026-08-30.
Source module to extract: `src/marketdata_screens/charting.py` (511 lines, self-contained, zero repo imports — pure `anywidget`/`traitlets` + klinecharts@10 + lightweight-charts via CDN ESM).

## What this lib is

One normalized OHLCV input → three render targets:

1. **Standalone HTML file** — `klinepy.html(chart) -> str` writing a self-contained document (CDN ESM import, no build step). NEW code — does not exist in marketdata-screens.
2. **HTML fragment** — same chart, no `<html>` wrapper, for embedding in web apps (stario/markup pages). NEW code.
3. **marimo/Jupyter widget** — port of the existing `KLineChart` anywidget from `charting.py:247` (esm from `_KLINECHARTS_ESM = https://cdn.jsdelivr.net/npm/klinecharts@10.0.2/+esm`, canvas init, `timestamp`-ms records, overlay lines via `_normalize_lines`, precision inference via `_infer_precision`).

Also port: `normalize_ohlcv` (charting.py:129) — accepts polars/pandas/arrow/records, output is the klinecharts record shape `{time, open, high, low, close, volume}` epoch-ms. This is the lib's input contract.

`LightweightChart` (TradingView lightweight-charts variant) — decide during extraction: port both or drop. Default lazy call: port `KLineChart` first, lightweight-charts only if a consumer asks.

## Design rules (agreed in session)

- No build step, no bundler: CDN ESM or vendored single-file JS. klinecharts@10 pinned.
- Zero data deps: input is frames/records; klinepy never queries anything.
- `charting.py` normalization helpers are the contract — keep names/behavior, they are covered by marketdata-screens tests (`tests/test_charting*.py` — port those tests).
- py3.11+ (match finvizp floor, widest compat for a rendering lib).

## Consumers

- marketdata-screens web (`views.py` symbol page sparkline/kline usage of `bars_payload`, `views.KLineChart` imports)
- marimo notebooks over the DuckLake (marketdata-marimo-screens skill workflow)

## First tasks

1. Copy `charting.py` → `src/klinepy/` split into `normalize.py` (pure) + `widget.py` (anywidget) + `html.py` (new standalone/fragment renderers); port tests.
2. Decide LightweightChart in/out (default: out until asked).
3. Pre-1.0 API freeze: `KLineChart(bars, lines=..., title=...)`, `to_html()`, `fragment()`.
