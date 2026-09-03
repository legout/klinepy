#!/usr/bin/env python3
"""Write the dark-tour HTML scenes (docs/tour/) that capture-tour.mjs drives.

Run: uv run python scripts/emit-tour-html.py
Deterministic synthetic bars — no network, no data deps. No build step: the
capture script loads these standalone-HTML files directly in a browser.
"""

from __future__ import annotations

import datetime as dt
import math
from pathlib import Path

from klinepy import ChartBundle, Colors, KLineChart, to_chart

OUT = Path(__file__).resolve().parent.parent / "docs" / "tour"

# The README "full custom dark" palette.
DARK = Colors(
    up="#4ade80",
    down="#f87171",
    accent="#fbbf24",
    price_line="#fbbf24",
    background="#0f172a",
    grid="#1e293b",
    border="#334155",
    text="#94a3b8",
)


def _bars(n: int = 150) -> list[dict]:
    """Deterministic synthetic daily bars (weekdays only)."""
    out: list[dict] = []
    price, d0 = 100.0, dt.date(2026, 1, 5)
    for i in range(n):
        d = d0 + dt.timedelta(days=i)
        if d.weekday() >= 5:
            continue
        o = price
        price = round(100 + 1.8 * math.sin(i / 9) + 3.5 * math.sin(i / 31) + (i % 7 - 3) * 0.4, 2)
        out.append(
            {
                "session": d,
                "open": o,
                "close": price,
                "high": round(max(o, price) + 0.9, 2),
                "low": round(min(o, price) - 0.9, 2),
                "volume": 800_000 + (i * 37_000) % 900_000,
            }
        )
    return out


def _sma(bars: list[dict], n: int = 20) -> list[float]:
    out = []
    for i in range(len(bars)):
        w = bars[max(0, i - n + 1) : i + 1]
        out.append(round(sum(b["close"] for b in w) / len(w), 2))
    return out


def _rrg_series() -> list[dict]:
    week0 = dt.date(2026, 3, 6)  # a Friday
    series = []
    for j, name in enumerate(("Tech", "Energy", "Finance")):
        pts = [
            {
                "date": (week0 + dt.timedelta(weeks=i)).isoformat(),
                "x": round(100 + 4.5 * math.sin(t * 2.8 + j * 1.1) + j * 1.3, 2),
                "y": round(100 + 5.0 * math.cos(t * 3.7 + j * 0.8) - j * 0.9, 2),
            }
            for i in range(26)
            for t in (i / 25,)
        ]
        series.append({"name": name, "points": pts})
    return series


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    bars = _bars()

    (OUT / "dark.html").write_text(
        KLineChart(bars, lines={"SMA 20": _sma(bars)}, title="AAPL", colors=DARK).to_html()
    )

    win = bars[-24:]
    (OUT / "boxes.html").write_text(
        KLineChart(
            bars,
            overlays=[
                {
                    "start": win[0]["session"],
                    "end": win[-1]["session"],
                    "top": max(b["high"] for b in win),
                    "bottom": min(b["low"] for b in win),
                }
            ],
            title="AAPL + Darvas",
            colors=DARK,
        ).to_html()
    )

    # static-charts-v1: emit the bundle JSON, then render it via the loader path.
    data = ChartBundle(
        symbol="AAPL",
        bars=bars,
        rs_line=[round(b["close"] * 0.9, 2) for b in bars],  # price-scale: rides below candles
        blue_dots=[{"session": b["session"], "value": b["high"]} for b in bars[20:150:30]],
        benchmark="SPY",
        fundamentals={"market_cap": 3.4e12},
    ).dump(OUT / "AAPL.json")
    loaded = to_chart(OUT / "AAPL.json")
    (OUT / "bundle.html").write_text(
        KLineChart(
            loaded.bars,
            lines=dict(loaded.lines),
            overlays=list(loaded.overlays),
            title=loaded.title,
            colors=DARK,
        ).to_html()
    )
    del data  # emitted above; keeps the emit() round-trip explicit

    # RRG presentation mode: bars are ignored, points precomputed.
    bar = {"session": "2026-01-02", "open": 10.0, "high": 11.0, "low": 9.0,
           "close": 10.5, "volume": 0}
    (OUT / "rrg.html").write_text(
        KLineChart([bar], rrg=_rrg_series(), title="Relative Rotation", colors=DARK).to_html()
    )

    print(f"wrote {sorted(p.name for p in OUT.iterdir())} in {OUT}")


if __name__ == "__main__":
    main()
