"""Pure OHLCV input normalization (no widget, no HTML).

The input contract for every render target: accepts a polars/pandas frame or
an iterable of mappings and returns klinecharts record shape
``{"time": <epoch ms>, "open", "high", "low", "close", "volume"?}`` sorted by
time, with rows missing any OHLC price dropped.

Zero data deps: frames are duck-typed, polars/pandas are optional.
"""

from __future__ import annotations

import datetime as _dt
import math
from collections.abc import Mapping, Sequence
from typing import Any

__all__ = ["normalize_ohlcv"]

_TIME_KEYS = ("timestamp", "time", "date", "datetime", "session", "day")
_PRICE_KEYS = ("open", "high", "low", "close")
_VOLUME_KEYS = ("volume", "vol")


def _to_epoch_ms(value: Any) -> int:
    """Normalize a time-like value to epoch milliseconds (UTC for dates)."""
    if isinstance(value, _dt.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=_dt.UTC)
        return int(value.timestamp() * 1000)
    if isinstance(value, _dt.date):
        return int(
            _dt.datetime(value.year, value.month, value.day, tzinfo=_dt.UTC).timestamp()
            * 1000
        )
    if isinstance(value, str):
        parsed = _dt.date.fromisoformat(value[:10])
        return _to_epoch_ms(parsed)
    if isinstance(value, bool):
        raise ValueError(f"invalid time value: {value!r}")
    if isinstance(value, (int, float)):
        ms = int(value)
        if ms < 10_000_000_000:  # seconds, not milliseconds
            ms *= 1000
        return ms
    raise ValueError(f"cannot normalize time value: {value!r}")


def _columns_of(frame: Any) -> list[str]:
    cols = getattr(frame, "columns", None)
    if cols is None:
        return []
    return [str(c) for c in cols]


def _pick_column(columns: Sequence[str], candidates: Sequence[str]) -> str | None:
    lowered = {c.lower(): c for c in columns}
    for key in candidates:
        if key in lowered:
            return lowered[key]
    return None


def _frame_rows(frame: Any) -> list[dict[str, Any]]:
    """Rows of a polars/pandas frame as plain dicts."""
    try:
        import polars as pl

        if isinstance(frame, pl.DataFrame):
            return frame.to_dicts()
    except ImportError:  # pragma: no cover - polars is a notebook extra
        pass
    try:
        import pandas as pd

        if isinstance(frame, pd.DataFrame):
            return frame.to_dict(orient="records")  # type: ignore[return-value]
    except ImportError:  # pragma: no cover - pandas is a main dep
        pass
    raise TypeError(
        f"unsupported bars type: {type(frame)!r}; expected polars/pandas DataFrame"
    )


def normalize_ohlcv(bars: Any) -> list[dict[str, Any]]:
    """Normalize OHLCV input to kline/lightweight records.

    Returns a list of ``{"time": <epoch ms>, "open": ..., "high": ...,
    "low": ..., "close": ..., "volume": ...}`` dicts sorted by time, with
    rows missing any OHLC price dropped.
    """
    rows: list[dict[str, Any]]
    if isinstance(bars, Sequence) and bars and isinstance(bars[0], Mapping):
        rows = list(bars)  # type: ignore[arg-type]
    else:
        rows = _frame_rows(bars)

    if not rows:
        return []

    columns = list(rows[0].keys())
    time_col = _pick_column(columns, _TIME_KEYS)
    price_cols = {k: _pick_column(columns, (k,)) for k in _PRICE_KEYS}
    volume_col = _pick_column(columns, _VOLUME_KEYS)
    if time_col is None or any(v is None for v in price_cols.values()):
        raise ValueError(
            f"bars must contain time ({'/'.join(_TIME_KEYS)}) and OHLC columns; got {columns}"
        )

    records: list[dict[str, Any]] = []
    for row in rows:
        o, h, l, c = (row[price_cols[k]] for k in _PRICE_KEYS)  # type: ignore[index]
        if o is None or h is None or l is None or c is None:
            continue
        rec = {
            "time": _to_epoch_ms(row[time_col]),  # type: ignore[index]
            "open": float(o),
            "high": float(h),
            "low": float(l),
            "close": float(c),
        }
        if volume_col is not None:
            vol = row[volume_col]  # type: ignore[index]
            rec["volume"] = None if vol is None else float(vol)
        records.append(rec)

    records.sort(key=lambda r: r["time"])
    return records


def _normalize_lines(
    lines: Mapping[str, Sequence[float | None]] | None, n_bars: int
) -> dict[str, list[float | None]]:
    """Align overlay line values to the bar count (pad/truncate with None)."""
    out: dict[str, list[float | None]] = {}
    for name, values in (lines or {}).items():
        vals = [
            None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)
            for v in values
        ]
        if len(vals) < n_bars:
            vals = vals + [None] * (n_bars - len(vals))
        out[str(name)] = vals[:n_bars]
    return out


def _normalize_rrg(
    series: Sequence[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Precomputed RRG series pass-through: ``{"name", "points": [{"date", "x", "y"}]}``.

    Coordinates arrive precomputed (x = RS-Ratio, y = RS-Momentum) — pure
    presentation, no math here. Points missing x/y are dropped, points are
    sorted oldest → newest, dates go through :func:`_to_epoch_ms`.
    """
    out: list[dict[str, Any]] = []
    for s in series or []:
        s = dict(s)
        pts: list[dict[str, Any]] = []
        for p in s.get("points") or []:
            p = dict(p)
            if p.get("x") is None or p.get("y") is None:
                continue
            raw_date = p.get("date", p.get("time"))
            pts.append(
                {
                    "date": _to_epoch_ms(raw_date) if raw_date is not None else None,
                    "x": float(p["x"]),
                    "y": float(p["y"]),
                }
            )
        pts.sort(key=lambda p: (p["date"] is None, p["date"] or 0))
        out.append({"name": str(s.get("name", "")), "points": pts})
    return out


def _normalize_overlays(
    overlays: Sequence[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Box sugar → klinecharts rect; full overlay specs pass through."""
    out: list[dict[str, Any]] = []
    for o in overlays or []:
        o = dict(o)
        if "start" in o:  # box: {start, end, top, bottom} → rect overlay
            o = {
                "name": "rect",
                "points": [
                    {"timestamp": _to_epoch_ms(o["start"]), "value": float(o["top"])},
                    {"timestamp": _to_epoch_ms(o["end"]), "value": float(o["bottom"])},
                ],
            }
        out.append(o)
    return out


def _infer_precision(records: Sequence[Mapping[str, Any]]) -> int:
    """Max decimal places seen in closes, clamped to [2, 4] (fallback 2)."""
    decimals = 2
    for rec in records[:200]:
        text = repr(float(rec["close"]))
        if "e" not in text and "." in text:
            decimals = max(decimals, min(4, len(text.split(".")[1].rstrip("0")) or 2))
    return decimals
