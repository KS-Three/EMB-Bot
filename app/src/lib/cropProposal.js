// Propose a crop rectangle: the DOMINANT INK CLUSTER of the artwork.
//
// Not the bounding box of all non-background ink -- on a phone screenshot
// that spans status bar to home indicator, i.e. the whole screen, which is
// useless on the one case the crop tool exists for.
//
// Worked on a coarse cell grid instead of a morphological dilation: marking
// cells that contain ink and joining neighbouring marked cells is the same
// operation at grid resolution, and far less code to get right in the
// browser. Measured against the nine REAL_ART logos 2026-09-22 -- no-op on
// the four that fill their frame, correct tight crops on the other five,
// nothing cut on any.
//
// The result is ALWAYS shown to the customer as a draggable suggestion and
// never applied silently. That is what separates it from auto-detection.

// Cells roughly this wide at design scale. Half the 4 mm merge distance, so
// two marks within ~4 mm land in the same or adjacent cells and join.
const CELL_MM = 2.0;
const MARGIN_MM = 2.0;
// How far a channel must sit from the frame's background to count as ink.
const INK_TOLERANCE = 28;
const FULL_FRAME = { x0: 0, y0: 0, x1: 1, y1: 1 };

function median(values) {
  const s = [...values].sort((a, b) => a - b);
  const mid = s.length >> 1;
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

function backgroundRgb({ data, width, height }) {
  // Per-channel MEDIAN over the frame's 1 px border, opaque pixels only --
  // the same premise stage 1's border-flood uses (a real background owns
  // the frame's edge), sharpened twice over a plain mean:
  //
  // - Opaque-only matches the ink loop's own alpha rule (data[i+3] < 128 is
  //   not ink). A transparent border sampled unconditionally would pull in
  //   whatever RGB sits under the transparency -- becker_marine_logo.png is
  //   one colour everywhere with the shape entirely in alpha, so its
  //   under-transparency RGB (near-black) would invert ink detection across
  //   the whole image if the mean counted it.
  // - Median is close to immune to a minority of border-touching ink, where
  //   a mean can be skewed past INK_TOLERANCE by a single large mark that
  //   reaches the edge. Also matches digitizer_core/stage1_prep.py's
  //   `_dominant_border_color`, a dominant colour rather than an average --
  //   this proposal should not be less robust than the pipeline it feeds.
  const rs = [], gs = [], bs = [];
  const at = (x, y) => (y * width + x) * 4;
  const sample = (x, y) => {
    const i = at(x, y);
    if (data[i + 3] < 128) return; // transparent border pixels don't count
    rs.push(data[i]); gs.push(data[i + 1]); bs.push(data[i + 2]);
  };
  // Top and bottom rows, every column (corners included here).
  for (let x = 0; x < width; x++) {
    sample(x, 0);
    sample(x, height - 1);
  }
  // Left and right columns, excluding the two rows already sampled above so
  // the four corner pixels are each counted once, not twice.
  for (let y = 1; y < height - 1; y++) {
    sample(0, y);
    sample(width - 1, y);
  }
  // No opaque border pixels at all -- a fully transparent frame -- means
  // everything visible is ink; white is the correct backdrop assumption for
  // artwork composited for display.
  if (!rs.length) return [255, 255, 255];
  return [median(rs), median(gs), median(bs)];
}

export function proposeCrop(imageData, widthMm) {
  const { data, width, height } = imageData;
  if (!width || !height) return { ...FULL_FRAME };

  const pxPerMm = width / Math.max(widthMm, 1e-6);
  const cellPx = Math.max(1, Math.round(CELL_MM * pxPerMm));
  const cols = Math.ceil(width / cellPx);
  const rows = Math.ceil(height / cellPx);
  const [br, bg, bb] = backgroundRgb(imageData);

  // Ink count per cell.
  const ink = new Int32Array(cols * rows);
  let total = 0;
  for (let y = 0; y < height; y++) {
    const cy = (y / cellPx) | 0;
    for (let x = 0; x < width; x++) {
      const i = (y * width + x) * 4;
      if (data[i + 3] < 128) continue; // transparent is not ink
      if (Math.abs(data[i] - br) > INK_TOLERANCE ||
          Math.abs(data[i + 1] - bg) > INK_TOLERANCE ||
          Math.abs(data[i + 2] - bb) > INK_TOLERANCE) {
        ink[cy * cols + ((x / cellPx) | 0)]++;
        total++;
      }
    }
  }
  if (!total) return { ...FULL_FRAME };

  // Connected components over marked cells, 8-connectivity, iterative flood
  // fill (a recursive one blows the stack on a large logo).
  const label = new Int32Array(cols * rows).fill(-1);
  let best = null, bestInk = -1;
  for (let start = 0; start < ink.length; start++) {
    if (!ink[start] || label[start] !== -1) continue;
    const id = start;
    const stack = [start];
    label[start] = id;
    let got = 0;
    let cx0 = cols, cy0 = rows, cx1 = -1, cy1 = -1;
    while (stack.length) {
      const c = stack.pop();
      const cx = c % cols, cy = (c / cols) | 0;
      got += ink[c];
      if (cx < cx0) cx0 = cx;
      if (cy < cy0) cy0 = cy;
      if (cx > cx1) cx1 = cx;
      if (cy > cy1) cy1 = cy;
      for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          const nx = cx + dx, ny = cy + dy;
          if (nx < 0 || ny < 0 || nx >= cols || ny >= rows) continue;
          const n = ny * cols + nx;
          if (ink[n] && label[n] === -1) { label[n] = id; stack.push(n); }
        }
      }
    }
    // Rank by the REAL ink a blob holds, not its cell count: a scatter of
    // specks covers more cells than a solid mark of the same weight.
    if (got > bestInk) { bestInk = got; best = [cx0, cy0, cx1, cy1]; }
  }
  if (!best) return { ...FULL_FRAME };

  const margin = MARGIN_MM * pxPerMm;
  const [cx0, cy0, cx1, cy1] = best;
  const clamp = (v) => Math.min(Math.max(v, 0), 1);
  return {
    x0: clamp((cx0 * cellPx - margin) / width),
    y0: clamp((cy0 * cellPx - margin) / height),
    x1: clamp(((cx1 + 1) * cellPx + margin) / width),
    y1: clamp(((cy1 + 1) * cellPx + margin) / height),
  };
}
