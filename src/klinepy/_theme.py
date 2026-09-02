"""Shared CDN pin + color palettes — single source for widget.py and html.py."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass

_KLINECHARTS_ESM = "https://cdn.jsdelivr.net/npm/klinecharts@10.0.2/+esm"


@dataclass
class Colors:
    """Chart palette. Themes are instances; users may pass one or a partial dict.

    Dicts merge into the active theme (only given keys); a Colors instance
    replaces it (unset fields fall back to these defaults).
    """

    up: str = "#404040"  # dark gray
    down: str = "#a3a3a3"  # light gray
    no_change: str = "#737373"  # mid gray
    accent: str = "#d97706"  # amber — the ONE accent color
    price_line: str = "#737373"  # dashed last-price line + right-edge tag
    background: str = "#ffffff"
    grid: str = "#ececec"
    border: str = "#d4d4d4"
    text: str = "#404040"


# Grayscale + single accent (amber).
_DEFAULTS = Colors()

# Classic pastel green/red.
_CLASSIC = Colors(
    up="#79b473",
    down="#e08276",
    no_change="#a8a8a8",
    accent="#2f6f4f",
    price_line="#6b9c68",
    text="#4a4a4a",
)

# Black/grey mono.
_MONO = Colors(
    up="#1a1a1a",
    down="#9e9e9e",
    no_change="#666666",
    accent="#1a1a1a",
    price_line="#666666",
    text="#333333",
)

_THEMES: dict[str, Colors] = {"default": _DEFAULTS, "classic": _CLASSIC, "mono": _MONO}


def _theme(name: str) -> Colors:
    """Palette by name; raises ValueError for unknown names."""
    try:
        return _THEMES[name]
    except KeyError:
        raise ValueError(f"unknown theme: {name!r} (choose from {sorted(_THEMES)})") from None


def _merge_colors(theme: str, colors: Colors | Mapping[str, str] | None) -> Colors:
    """Theme palette + user overrides (dict keys merge, Colors replaces)."""
    base = _theme(theme)
    if colors is None:
        return base
    if isinstance(colors, Colors):
        return colors
    unknown = set(colors) - {f.name for f in dataclasses.fields(Colors)}
    if unknown:
        raise TypeError(f"unknown color keys: {sorted(unknown)}")
    return dataclasses.replace(base, **colors)
