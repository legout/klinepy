"""RRG renderer JS — shared verbatim by widget.py's _esm and html.py's script.

Leaf module (imports nothing from klinepy): widget.py embeds it in the
anywidget ESM, html.py inlines it in the page script, so it must stay
self-contained (no imports, no top-level state).

Raw Canvas 2D scatter (klinecharts is a time-axis candle engine — wrong tool
for x/y space). Consumes PRECOMPUTED (x, y) weekly points per series; the only
"math" is Catmull-Rom path drawing. Ported from stock-screener rrgTrace.js /
useDragZoom.js (docs/stock-screener-learnings.md items 1-2).
"""

_RRG_JS = """
// Uniform Catmull-Rom path through pts [{x,y}] — interpolates *through* every
// weekly vertex, so the tail passes exactly where the series was each week
// (rrgTrace.js catmullRomPath). Returns a list of cubic-bezier path strings,
// one per segment, so callers can stroke segments with graduated opacity.
function catmullRomSegments(pts) {
  const segs = [];
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] ?? pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] ?? p2;
    const c1x = p1.x + (p2.x - p0.x) / 6, c1y = p1.y + (p2.y - p0.y) / 6;
    const c2x = p2.x - (p3.x - p1.x) / 6, c2y = p2.y - (p3.y - p1.y) / 6;
    segs.push(`M${p1.x},${p1.y} C${c1x},${c1y} ${c2x},${c2y} ${p2.x},${p2.y}`);
  }
  return segs;
}

// RRG presentation mode: precomputed scatter + spline tails + drag-zoom.
// cfg.rrg = [{ name, points: [{date, x, y}] }] oldest -> newest, x/y already
// computed (RS-Ratio / RS-Momentum). Grayscale + single accent.
function renderRRG(el, cfg) {
  // The el arg is the fragment container div; create the canvas inside it.
  const container = document.createElement("canvas");
  container.style.width = "100%";
  container.style.height = cfg.height + "px";
  container.style.background = cfg.background_color;
  el.appendChild(container);

  const series = cfg.rrg || [];
  const ctx = container.getContext("2d");
  const accent = cfg.accent_color, text = cfg.text_color, grid = cfg.grid_color;
  const textDim = text + "99"; // faint text/ticks

  const DETAIL_LIMIT = 20; // tails go line-only above this (RRGChart.jsx)

  // Symmetric axis bounds around the 100/100 cross, padded to the data extent
  // (RRGChart.jsx computeBound).
  let maxAbs = 8;
  for (const s of series) for (const p of s.points)
    maxAbs = Math.max(maxAbs, Math.abs(p.x - 100), Math.abs(p.y - 100));
  const bound = Math.min(20, Math.ceil(maxAbs) + 1);

  let W = 0, H = 0, left = 44, top = 10, plotW = 0, plotH = 0;
  let xr = [100 - bound, 100 + bound], yr = [100 - bound, 100 + bound];
  const xrFull = xr.slice(), yrFull = yr.slice();
  const px = (v) => left + ((v - xr[0]) / (xr[1] - xr[0])) * plotW;
  const py = (v) => top + (1 - (v - yr[0]) / (yr[1] - yr[0])) * plotH;
  const dataAt = (x, y) => ({
    x: xr[0] + ((x - left) / plotW) * (xr[1] - xr[0]),
    y: yr[0] + (1 - (y - top) / plotH) * (yr[1] - yr[0]),
  });
  let dragStart = null, dragRect = null;

  function draw() {
    const dpr = window.devicePixelRatio || 1;
    W = container.clientWidth; H = container.clientHeight;
    container.width = W * dpr; container.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = cfg.background_color;
    ctx.fillRect(0, 0, W, H);
    plotW = W - left - 10; plotH = H - top - 28;
    ctx.font = "10px sans-serif";
    ctx.lineWidth = 1;

    // Grid (5 divisions) + tick labels.
    ctx.strokeStyle = grid;
    for (let i = 0; i <= 5; i++) {
      const t = i / 5;
      const gx = left + t * plotW, gy = top + (1 - t) * plotH;
      ctx.beginPath(); ctx.moveTo(gx, top); ctx.lineTo(gx, top + plotH); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(left, gy); ctx.lineTo(left + plotW, gy); ctx.stroke();
      ctx.fillStyle = textDim;
      ctx.textAlign = "center"; ctx.textBaseline = "top";
      if (i > 0) ctx.fillText((xr[0] + t * (xr[1] - xr[0])).toFixed(1), gx, top + plotH + 4);
      ctx.textAlign = "right";
      ctx.fillText((yr[0] + t * (yr[1] - yr[0])).toFixed(1), left - 5, gy - 5);
    }

    // 100/100 cross (accent) + quadrant labels.
    const cx = px(100), cy = py(100);
    ctx.strokeStyle = accent; ctx.globalAlpha = 0.7;
    ctx.beginPath(); ctx.moveTo(cx, top); ctx.lineTo(cx, top + plotH); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(left, cy); ctx.lineTo(left + plotW, cy); ctx.stroke();
    ctx.globalAlpha = 1;
    ctx.fillStyle = textDim; ctx.textAlign = "left";
    ctx.fillText("Improving", left + 4, top + 4);
    ctx.fillText("Lagging", left + 4, top + plotH - 12);
    ctx.textAlign = "right";
    ctx.fillText("Weakening", left + plotW - 4, top + plotH - 12);
    ctx.fillText("Leading", left + plotW - 4, top + 4);

    const detailed = series.length <= DETAIL_LIMIT;
    for (const s of series) {
      const pts = s.points.map((p) => ({ x: px(p.x), y: py(p.y) }));
      if (!pts.length) continue;
      const segs = catmullRomSegments(pts);
      // Tails: spline through exact weekly vertices, graduated opacity
      // oldest -> newest; line-only (no vertex dots) above DETAIL_LIMIT.
      if (pts.length === 1) {
        ctx.globalAlpha = 1; ctx.fillStyle = accent;
        ctx.beginPath(); ctx.arc(pts[0].x, pts[0].y, 3.5, 0, 6.2832); ctx.fill();
      } else {
        ctx.lineWidth = detailed ? 1.5 : 1.2;
        ctx.strokeStyle = accent;
        const n = segs.length;
        segs.forEach((d, i) => {
          ctx.globalAlpha = detailed ? 0.2 + 0.7 * (i / n) : 0.85;
          ctx.stroke(new Path2D(d));
        });
        ctx.globalAlpha = 1;
        if (detailed) {
          ctx.fillStyle = accent;
          for (let i = 0; i < pts.length - 1; i++) {
            const t = i / Math.max(1, pts.length - 2);
            ctx.globalAlpha = 0.2 + 0.5 * t;
            ctx.beginPath(); ctx.arc(pts[i].x, pts[i].y, 1.5 + 2 * t, 0, 6.2832); ctx.fill();
          }
          ctx.globalAlpha = 1;
        }
      }
      // Head dot + name + direction arrow along the last spline segment.
      const head = pts[pts.length - 1];
      ctx.globalAlpha = 1; ctx.fillStyle = accent;
      ctx.beginPath(); ctx.arc(head.x, head.y, 3.5, 0, 6.2832); ctx.fill();
      ctx.fillStyle = textDim; ctx.font = "600 10px sans-serif"; ctx.textAlign = "left";
      if (s.name) ctx.fillText(s.name, head.x + 7, head.y - 10);
      if (pts.length > 1) {
        const prev = pts[pts.length - 2];
        const ang = Math.atan2(head.y - prev.y, head.x - prev.x);
        // Arrow sits behind the head dot so both stay visible.
        drawArrow(head.x - 6 * Math.cos(ang), head.y - 6 * Math.sin(ang), ang, accent, 5);
      }
    }

    // In-progress zoom selection rectangle.
    if (dragRect) {
      ctx.globalAlpha = 0.08; ctx.fillStyle = text;
      ctx.fillRect(dragRect.x, dragRect.y, dragRect.w, dragRect.h);
      ctx.globalAlpha = 0.6; ctx.strokeStyle = text;
      ctx.strokeRect(dragRect.x, dragRect.y, dragRect.w, dragRect.h);
      ctx.globalAlpha = 1;
    }
  }

  function drawArrow(x, y, ang, color, size) {
    ctx.save(); ctx.translate(x, y); ctx.rotate(ang);
    ctx.globalAlpha = 0.9; ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(-size, -size * 0.6); ctx.lineTo(size, 0); ctx.lineTo(-size, size * 0.6);
    ctx.closePath(); ctx.fill(); ctx.restore();
  }

  // Drag-zoom with an 8px click-vs-drag threshold (useDragZoom.js
  // MIN_DRAG_PX): smaller gestures are clicks and do not zoom.
  const inPlot = (e) => {
    const r = container.getBoundingClientRect();
    const x = e.clientX - r.left, y = e.clientY - r.top;
    return x >= left && x <= left + plotW && y >= top && y <= top + plotH ? { x, y } : null;
  };
  container.style.cursor = "crosshair";
  container.onpointerdown = (e) => {
    const p = inPlot(e);
    if (p) { dragStart = p; e.preventDefault(); }
  };
  container.onpointermove = (e) => {
    const p = inPlot(e);
    if (!dragStart) return;
    if (p) {
      dragRect = { x: Math.min(dragStart.x, p.x), y: Math.min(dragStart.y, p.y),
                   w: Math.abs(p.x - dragStart.x), h: Math.abs(p.y - dragStart.y) };
    } else dragRect = null;
    draw();
  };
  container.onpointerup = (e) => {
    const p = inPlot(e);
    if (dragStart && p && Math.abs(p.x - dragStart.x) >= 8 && Math.abs(p.y - dragStart.y) >= 8) {
      const d1 = dataAt(dragStart.x, dragStart.y), d2 = dataAt(p.x, p.y);
      xr = [Math.min(d1.x, d2.x), Math.max(d1.x, d2.x)];
      yr = [Math.min(d1.y, d2.y), Math.max(d1.y, d2.y)];
    }
    dragStart = null; dragRect = null;
    draw();
  };
  container.onpointerleave = () => { dragStart = null; dragRect = null; draw(); };
  // Double-click resets zoom.
  container.ondblclick = () => { xr = xrFull.slice(); yr = yrFull.slice(); draw(); };
  draw();
}
"""
