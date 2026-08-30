"""Python wrapper for KLineCharts.

Three outputs from one chart spec:
  - standalone HTML files
  - embeddable HTML fragments for web apps
  - marimo/Jupyter widgets via anywidget
"""

from klinepy.normalize import normalize_ohlcv

__version__ = "0.1.0"

__all__ = ["normalize_ohlcv", "__version__"]
