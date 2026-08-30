"""Python wrapper for KLineCharts.

Three outputs from one chart spec:
  - standalone HTML files (chart.to_html() / klinepy.html(chart))
  - embeddable HTML fragments (chart.fragment() / klinepy.fragment(chart))
  - marimo/Jupyter widgets via anywidget (KLineChart)
"""

from klinepy.html import fragment as fragment
from klinepy.html import html as html
from klinepy.normalize import normalize_ohlcv
from klinepy.widget import KLineChart

__version__ = "0.1.0"

__all__ = ["KLineChart", "__version__", "fragment", "html", "normalize_ohlcv"]
