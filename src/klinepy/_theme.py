"""Shared CDN pin + palette — single source for widget.py and html.py."""

_KLINECHARTS_ESM = "https://cdn.jsdelivr.net/npm/klinecharts@10.0.2/+esm"

# Grayscale + single accent (amber) palette.
_DEFAULTS = {
    "up": "#404040",  # dark gray
    "down": "#a3a3a3",  # light gray
    "no_change": "#737373",  # mid gray
    "accent": "#d97706",  # amber — the ONE accent color
    "grid": "#ececec",
    "border": "#d4d4d4",
    "text": "#404040",
}
