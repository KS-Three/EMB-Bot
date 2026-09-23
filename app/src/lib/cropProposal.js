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

function backgroundRgb({ data, width, height }) {
  // Mean of the frame's 1 px border -- the same premise stage 1's
  // border-flood uses: a real background owns the frame's edge.
  let r = 0, g = 0, b = 0, n = 0;
  const at = (x, y) => (y * width + x) * 4;
  for (let x = 0; x < width; x++) {
    for (const y of [0, height - 1]) {
      const i = at(x, y);
      r += data[i]; g += data[i + 1]; b += data[i + 2]; n++;
    }
  }
  for (let y = 0; y < height; y++) {
    for (const x of [0, width - 1]) {
      const i = at(x, y);
      r += data[i]; g += data[i + 1]; b += data[i + 2]; n++;
    }
  }
  return n ? [r / n, g / n, b / n] : [255, 255, 255];
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
