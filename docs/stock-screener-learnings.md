# stock-screener (xang1234) learnings for klinepy

Full analysis: ~/projects/marketdata-screens/research/stock-screener-analysis.md (2026-09-02).

## Adopt (evidence paths under the repo root)

1. **RRG as pure presentation** — RS-Ratio/RS-Momentum coordinates precomputed server-side (`services/rrg_service.py` + `analysis/rrg_weekly.py`), chart component only draws (`frontend/src/components/Charts/RRGChart.jsx`). Tails = Catmull-Rom splines through exact weekly vertices with graduated opacity (`rrgTrace.js`), degrade to line-only above 20 visible series, drag-zoom with 8px click-vs-drag threshold (`useDragZoom.js`). Port the math if RRG ever lands in marketdata-screens — ECharts scatter can consume the same precomputed points.
2. **Temporal z-score, not double-percentile** — because RS ratings are already cross-sectional percentiles, they z-score each group against its OWN trailing history (26-week z re-centered at 100, scale 5, clamp [80,120]; momentum = 4w ROC → EMA3 → 13w z). Avoids double-normalization. `analysis/rrg_weekly.py`.
3. **Static chart bundle format** — `charts/<symbol>.json`, schema `static-charts-v1`: 2y OHLCV bars, rs_line, blue_dots markers, benchmark symbol, fundamentals (top-200 symbols). `static_site_export_service.py`. This is the model for klinepy's standalone-HTML data contract — one versioned JSON per symbol, self-describing.
4. **Playwright README tour** — scripted dark-mode GIF/WebM capture of the live app (`frontend/scripts/capture-static-site-tour.mjs`, `capture-scan-workflow.mjs`). Keeps docs honest; trivially reusable for marketdata-screens.

## Avoid

- Their chart stack weight (recharts ~400KB + lightweight-charts, MUI theming) — klinepy stays CDN-ESM KLineCharts, no build step.
- Chart components fetching their own data — precompute and pass data in (their pattern, keep it).
