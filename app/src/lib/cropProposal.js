// Propose a crop rectangle: the DOMINANT INK CLUSTER of the artwork.
//
// Not the bounding box of all non-background ink -- on a phone screenshot
// that spans status bar to home indicator, i.e. the whole screen, which is
// useless on the one case the crop tool exists for.
//
// Worked on a coarse cell grid: cells containing ink are marked, the mark
// mask is DILATED by one cell (a cell is marked if it or any 8-neighbour has
// ink), and connected components are labelled over the dilated mask. That
// merges marks up to ~2 empty cells (~4 mm) apart into one blob, so an icon
// and its wordmark stay together. Each component is ranked by the REAL ink it
// holds, and its rectangle is the bbox of only its cells that actually have
// ink, so the dilation does not inflate the box.
//
// The spec's measurement against the nine REAL_ART logos (2026-09-22: a no-op
// on the four that fill their frame, tight crops on the other five, nothing
// cut on any) was of a PROTOTYPE of this algorithm, taken before the
// transparent-background and one-cell-dilation changes landed. The shipped
// code has not been re-measured against that set; see
// docs/superpowers/specs/2026-09-22-upload-crop-design.md for what was run.
//
// Scale: `widthMm` is the design's TARGET width, and this treats the FULL
// preview width as that width. The service instead fits the artwork's own
// bbox to the target, so the real cell is at least as large as this one
// thinks -- measured in design millimetres, the join distance here is the
// same or larger than intended. That errs toward merging more marks into
// one blob, i.e. toward a looser crop, which is the safe side.
//
// The result is ALWAYS shown to the customer as a draggable suggestion and
// never applied silently. That is what separates it from auto-detection.

// Cells roughly this wide at design scale. The mark mask is dilated by one
// cell before labelling, so two inked cells join when at most two empty cells
// separate them: an effective join distance of ~4-6 mm depending on where the
// marks fall inside their cells.
const CELL_MM = 2.0;
const MARGIN_MM = 2.0;
// How far a channel must sit from the frame's background to count as ink.
const INK_TOLERANCE = 28;
const FULL_FRAME = { x0: 0, y0: 0, x1: 1, y1: 1 };

function backgroundRgb({ data, width, height }) {
  // Mean of the frame's 1 px border -- the same premise stage 1's
  // border-flood uses: a real background owns the frame's edge.
  // Transparent border pixels are skipped (stage 1 treats alpha as
  // background, and getImageData reports them as 0,0,0). Returns null when
  // every border pixel is transparent: ink is then just alpha >= 128.
  let r = 0, g = 0, b = 0, n = 0;
  const at = (x, y) => (y * width + x) * 4;
  const add = (i) => {
    if (data[i + 3] < 128) return;
    r += data[i]; g += data[i + 1]; b += data[i + 2]; n++;
  };
  for (let x = 0; x < width; x++) {
    for (const y of [0, height - 1]) add(at(x, y));
  }
  for (let y = 0; y < height; y++) {
    for (const x of [0, width - 1]) add(at(x, y));
  }
  return n ? [r / n, g / n, b / n] : null;
}

export function proposeCrop(imageData, widthMm) {
  const { data, width, height } = imageData;
  if (!width || !height) return { ...FULL_FRAME };

  const pxPerMm = width / Math.max(widthMm, 1e-6);
  const cellPx = Math.max(1, Math.round(CELL_MM * pxPerMm));
  const cols = Math.ceil(width / cellPx);
  const rows = Math.ceil(height / cellPx);
  const bgRgb = backgroundRgb(imageData);

  // Ink count per cell.
  const ink = new Int32Array(cols * rows);
  let total = 0;
  for (let y = 0; y < height; y++) {
    const cy = (y / cellPx) | 0;
    for (let x = 0; x < width; x++) {
      const i = (y * width + x) * 4;
      if (data[i + 3] < 128) continue; // transparent is not ink
      if (!bgRgb ||
          Math.abs(data[i] - bgRgb[0]) > INK_TOLERANCE ||
          Math.abs(data[i + 1] - bgRgb[1]) > INK_TOLERANCE ||
          Math.abs(data[i + 2] - bgRgb[2]) > INK_TOLERANCE) {
        ink[cy * cols + ((x / cellPx) | 0)]++;
        total++;
      }
    }
  }
  if (!total) return { ...FULL_FRAME };

  // Dilate the mark mask by one cell (8-neighbourhood).
  const mask = new Uint8Array(cols * rows);
  for (let cy = 0; cy < rows; cy++) {
    for (let cx = 0; cx < cols; cx++) {
      if (!ink[cy * cols + cx]) continue;
      for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          const nx = cx + dx, ny = cy + dy;
          if (nx < 0 || ny < 0 || nx >= cols || ny >= rows) continue;
          mask[ny * cols + nx] = 1;
        }
      }
    }
  }

  // Connected components over the dilated mask, 8-connectivity, iterative
  // flood fill (a recursive one blows the stack on a large logo).
  const label = new Int32Array(cols * rows).fill(-1);
  let best = null, bestInk = -1;
  for (let start = 0; start < mask.length; start++) {
    if (!mask[start] || label[start] !== -1) continue;
    const id = start;
    const stack = [start];
    label[start] = id;
    let got = 0;
    let cx0 = cols, cy0 = rows, cx1 = -1, cy1 = -1;
    while (stack.length) {
      const c = stack.pop();
      const cx = c % cols, cy = (c / cols) | 0;
      got += ink[c];
      if (ink[c]) { // bbox over cells with real ink only, not dilation halo
        if (cx < cx0) cx0 = cx;
        if (cy < cy0) cy0 = cy;
        if (cx > cx1) cx1 = cx;
        if (cy > cy1) cy1 = cy;
      }
      for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          const nx = cx + dx, ny = cy + dy;
          if (nx < 0 || ny < 0 || nx >= cols || ny >= rows) continue;
          const n = ny * cols + nx;
          if (mask[n] && label[n] === -1) { label[n] = id; stack.push(n); }
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
