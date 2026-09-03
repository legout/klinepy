"""static-charts-v1: versioned, self-describing per-symbol chart bundles.

One JSON bundle per symbol (``charts/<symbol>.json``), produced entirely by
the caller — charts never fetch or compute data. Bundle fields map onto the
render inputs of html()/fragment(): ``bars`` (OHLCV records), ``rs_line``
(price-pane overlay line), ``blue_dots`` (dot marker overlays), plus
self-describing metadata the chart itself does not draw (``benchmark``,
``fundamentals``).

The ~2y bar window and any indicator math (rs_line, dot conditions) are the
producer's job; this module only validates shape and stamps schema_version.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from klinepy.normalize import _normalize_lines, _to_epoch_ms, normalize_ohlcv
from klinepy.widget import KLineChart

SCHEMA_VERSION = "static-charts-v1"

__all__ = ["SCHEMA_VERSION", "ChartBundle", "emit", "load_bundle", "to_chart"]

_TIME_FIELDS = ("timestamp", "time", "date", "datetime", "session", "day")


def _validate(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a bundle mapping and return it stamped with schema_version.

    Idempotent: an already-emitted bundle (normalized bars, ``blue_dots`` as
    overlay dicts) revalidates unchanged.
    """
    version = bundle.get("schema_version")
    if version is not None and version != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported schema_version: {version!r} (expected {SCHEMA_VERSION!r})"
        )
    if not bundle.get("symbol"):
        raise ValueError("bundle requires a non-empty 'symbol'")
    if "bars" not in bundle:
        raise ValueError("bundle requires 'bars'")
    bars = bundle["bars"]
    if bars and isinstance(bars[0], Mapping) and "time" in bars[0]:
        bars = [dict(b) for b in bars]  # already-emitted records; keep as-is
    else:
        bars = normalize_ohlcv(bars)  # raises on missing time/OHLC columns
    out: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "symbol": str(bundle["symbol"]),
        "bars": bars,
    }
    if bundle.get("rs_line") is not None:
        out["rs_line"] = _normalize_lines({"rs": bundle["rs_line"]}, len(bars))["rs"]
    if bundle.get("blue_dots"):
        out["blue_dots"] = [
            d if d.get("name") == "dot" else _dot_overlay(d) for d in bundle["blue_dots"]
        ]
    if bundle.get("benchmark") is not None:
        out["benchmark"] = str(bundle["benchmark"])
    if bundle.get("fundamentals") is not None:
        if not isinstance(bundle["fundamentals"], Mapping):
            raise ValueError("fundamentals must be a mapping")
        out["fundamentals"] = dict(bundle["fundamentals"])
    return out


def _dot_overlay(dot: Mapping[str, Any]) -> dict[str, Any]:
    """One blue dot {<time field>, value} → klinecharts dot overlay spec."""
    ts = next((dot[k] for k in _TIME_FIELDS if k in dot), None)
    if ts is None or "value" not in dot:
        raise ValueError(
            f"blue dot needs a time field ({'/'.join(_TIME_FIELDS)}) and 'value'; "
            f"got {sorted(dot)}"
        )
    return {
        "name": "dot",
        "points": [{"timestamp": _to_epoch_ms(ts), "value": float(dot["value"])}],
    }


@dataclass
class ChartBundle:
    """Per-symbol chart bundle; ``to_dict()``/``dump()`` emit validated, stamped JSON."""

    symbol: str
    bars: Any = None
    rs_line: Sequence[float | None] | None = None
    blue_dots: Sequence[Mapping[str, Any]] | None = None
    benchmark: str | None = None
    fundamentals: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return _validate(
            {
                "symbol": self.symbol,
                "bars": self.bars,
                "rs_line": self.rs_line,
                "blue_dots": self.blue_dots,
                "benchmark": self.benchmark,
                "fundamentals": self.fundamentals,
            }
        )

    def dump(self, path: str | Path) -> dict[str, Any]:
        """Validate + stamp, write JSON to ``path``, return the stamped dict."""
        return emit(self, path)


def emit(
    bundle: ChartBundle | Mapping[str, Any], path: str | Path | None = None
) -> dict[str, Any]:
    """Validate a ChartBundle or plain mapping, stamp schema_version; optionally write JSON."""
    data = bundle.to_dict() if isinstance(bundle, ChartBundle) else _validate(bundle)
    if path is not None:
        Path(path).write_text(
            json.dumps(data).replace("</", "<\\/"), encoding="utf-8"
        )
    return data


def load_bundle(src: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    """Read a bundle from a dict or JSON file path; validate + return the stamped dict."""
    if isinstance(src, Mapping):
        return _validate(src)
    data = json.loads(Path(src).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise TypeError(f"bundle file must contain a JSON object: {src}")
    return _validate(data)


def to_chart(bundle: Mapping[str, Any] | str | Path) -> KLineChart:
    """Bundle (dict or JSON path) → KLineChart for html()/fragment()."""
    data = load_bundle(bundle)
    return KLineChart(
        data["bars"],
        lines={"rs": data["rs_line"]} if data.get("rs_line") is not None else None,
        overlays=data.get("blue_dots") or None,
        title=data["symbol"],
    )
