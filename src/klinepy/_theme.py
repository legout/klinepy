"""Shared CDN pin + palettes — single source for widget.py and html.py."""

_KLINECHARTS_ESM = "https://cdn.jsdelivr.net/npm/klinecharts@10.0.2/+esm"

# Default: grayscale + single accent (amber).
_DEFAULTS = {
    "up": "#404040",  # dark gray
    "down": "#a3a3a3",  # light gray
    "no_change": "#737373",  # mid gray
    "accent": "#d97706",  # amber — the ONE accent color
    "grid": "#ececec",
    "border": "#d4d4d4",
    "text": "#404040",
}

# Classic pastel green/red.
_CLASSIC = {
    "up": "#79b473",  # pastel green
    "down": "#e08276",  # pastel red
    "no_change": "#a8a8a8",
    "accent": "#2f6f4f",  # deep green accent
    "grid": "#ececec",
    "border": "#d4d4d4",
    "text": "#4a4a4a",
}

# Black/grey mono — candles solid black up, outlined grey down.
_MONO = {
    "up": "#1a1a1a",  # black
    "down": "#9e9e9e",  # grey
    "no_change": "#666666",
    "accent": "#1a1a1a",  # black accent — overlays stay monochrome
    "black_grey": True,
    "grid": "#ececec",
    "border": "#d4d4d4",
    "text": "#333333",
}

_THEMES = {"default": _DEFAULTS, "classic": _CLASSIC, "mono": _MONO}


def _theme(name: str) -> dict:
    """Palette by name; raises ValueError for unknown names."""
    try:
        return _THEMES[name]
    except KeyError:
        raise ValueError(f"unknown theme: {name!r} (choose from {sorted(_THEMES)})") from None
