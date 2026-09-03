"""Python wrapper for KLineCharts.

Three outputs from one chart spec:
  - standalone HTML files (chart.to_html() / klinepy.html(chart))
  - embeddable HTML fragments (chart.fragment() / klinepy.fragment(chart))
  - marimo/Jupyter widgets via anywidget (KLineChart)
"""

from klinepy._theme import Colors
from klinepy.bundle import SCHEMA_VERSION, ChartBundle, emit, load_bundle, to_chart
from klinepy.html import fragment as fragment
from klinepy.html import html as html
from klinepy.normalize import normalize_ohlcv
from klinepy.widget import KLineChart

__version__ = "0.3.0"

__all__ = [
    "SCHEMA_VERSION",
    "ChartBundle",
    "Colors",
    "KLineChart",
    "__version__",
    "emit",
    "fragment",
    "html",
    "load_bundle",
    "normalize_ohlcv",
    "to_chart",
]
