import { test, expect, vi } from "vitest";
import { fitTransform, hoopTransform, luminance, isDark, weavePattern, drawHoopOutline, renderRealistic, threadLayers, threadLodLayers, THREAD_WIDTH_MM } from "./preview.js";

// A ctx double that tracks strokeStyle assignments (a plain property can't
// record its own write history) alongside vi.fn() spies for every 2D-context
// method preview.js's draw helpers call. No real canvas needed (node env has
// no canvas 2D context) -- this is the same node-test-environment workaround
// exporters.spec.js already documents for renderRealistic.
function makeCtxSpy() {
  const strokeStyleLog = [];
  let _strokeStyle;
  return {
    save: vi.fn(), restore: vi.fn(),
    beginPath: vi.fn(), closePath: vi.fn(),
    moveTo: vi.fn(), lineTo: vi.fn(), arcTo: vi.fn(),
    stroke: vi.fn(), fillRect: vi.fn(),
    setLineDash: vi.fn(),
    lineWidth: 0,
    lineCap: "",
    fillStyle: "",
    get strokeStyle() { return _strokeStyle; },
    set strokeStyle(v) { _strokeStyle = v; strokeStyleLog.push(v); },
    strokeStyleLog,
  };
}
test("fitTransform centers and scales design into canvas with padding", () => {
  const design = { stitches: [ { x: -100, y: -50, type: "stitch" }, { x: 100, y: 50, type: "stitch" } ] };
  const t = fitTransform(design, 400, 300, 20);
  // design is 200 wide, 100 tall; canvas usable 360x260 -> scale limited by width 360/200=1.8
  expect(t.scale).toBeCloseTo(1.8, 1);
  // centered: midpoint (0,0) maps to canvas center (200,150)
  expect(t.ox).toBeCloseTo(200, 0);
  expect(t.oy).toBeCloseTo(150, 0);
});

test("Y axis flips: DST y-up must map to canvas y-down (no mirrored letters)", () => {
  // DST units: +y is UP. A stitch at the design TOP (+y) must land at a
  // SMALLER canvas y than one at the design bottom (-y).
  const design = { stitches: [ { x: 0, y: -50, type: "stitch" }, { x: 0, y: 50, type: "stitch" } ] };
  const t = fitTransform(design, 400, 300, 20);
  const canvasYTop = t.oy - 50 * t.scale;    // design top (+50)
  const canvasYBottom = t.oy - (-50) * t.scale; // design bottom (-50)
  expect(canvasYTop).toBeLessThan(canvasYBottom);
  // and the pair stays centered: midpoint maps to canvas center
  expect((canvasYTop + canvasYBottom) / 2).toBeCloseTo(150, 0);
});

test("hoopTransform fits the full hoop (not the design) into the canvas, +y up", () => {
  // 5in x 2.25in garment (hat front) on a 640x420 canvas, 20px pad.
  const garment = { widthIn: 5, heightIn: 2.25 };
  const t = hoopTransform(garment, 640, 420, 20);
  expect(t.hoopWmm).toBeCloseTo(127, 1);      // 5 * 25.4
  expect(t.hoopHmm).toBeCloseTo(57.15, 1);    // 2.25 * 25.4
  // scale limited by width: min(600/127, 380/57.15) = min(4.724, 6.649)
  expect(t.scale).toBeCloseTo(4.724, 2);
  // origin is the canvas center (hoop-space origin = hoop center)
  expect(t.ox).toBeCloseTo(320, 0);
  expect(t.oy).toBeCloseTo(210, 0);
  // +y is UP in hoop space: a positive-y point must land ABOVE center (smaller canvas y)
  expect(t.oy - 10 * t.scale).toBeLessThan(t.oy);
});

// --- luminance / isDark (Slice 8 Task 2, B7) -------------------------------

test("luminance: black is 0, white is 1", () => {
  expect(luminance([0, 0, 0])).toBeCloseTo(0, 6);
  expect(luminance([255, 255, 255])).toBeCloseTo(1, 6);
});

test("isDark classifies the Garment step's 8 fabric swatches the way the field's contrast logic expects", () => {
  expect(isDark([255, 255, 255])).toBe(false); // White
  expect(isDark([235, 232, 223])).toBe(false); // Natural
  expect(isDark([214, 199, 175])).toBe(false); // Sand
  expect(isDark([179, 35, 45])).toBe(true); // Red
  expect(isDark([32, 64, 150])).toBe(true); // Royal
  expect(isDark([25, 34, 60])).toBe(true); // Navy
  expect(isDark([30, 79, 52])).toBe(true); // Forest
  expect(isDark([20, 20, 22])).toBe(true); // Black
});

// --- weavePattern -----------------------------------------------------------

test("weavePattern draws a crosshatch of darkened, low-alpha lines every ~3px, both directions", () => {
  const ctx = makeCtxSpy();
  weavePattern(ctx, 9, 6, [235, 232, 223], 2);
  expect(ctx.strokeStyleLog[0]).toBe("rgba(205,202,193,0.08)");
  // x: 0,3,6,9 (4) + y: 0,3,6 (3) = 7 line segments, one stroke() batching all of them
  expect(ctx.moveTo).toHaveBeenCalledTimes(7);
  expect(ctx.lineTo).toHaveBeenCalledTimes(7);
  expect(ctx.stroke).toHaveBeenCalledTimes(1);
});

test("weavePattern skips drawing when zoomed out past the noise threshold (< 1.5 px/mm)", () => {
  const ctx = makeCtxSpy();
  weavePattern(ctx, 100, 100, [235, 232, 223], 1.2);
  expect(ctx.stroke).not.toHaveBeenCalled();
  expect(ctx.moveTo).not.toHaveBeenCalled();
});

test("weavePattern clamps the darkened tone at 0 instead of going negative on already-dark fabric", () => {
  const ctx = makeCtxSpy();
  weavePattern(ctx, 3, 3, [10, 5, 2], 2);
  expect(ctx.strokeStyleLog[0]).toBe("rgba(0,0,0,0.08)");
});

// --- drawHoopOutline luminance-aware chrome (B7) ---------------------------

test("drawHoopOutline: dark fabric gets a light outline/inset variant, light fabric keeps the original dark variant", () => {
  const t = { hoopWmm: 100, hoopHmm: 80, scale: 2, ox: 100, oy: 80 };
  const onWhite = makeCtxSpy();
  drawHoopOutline(onWhite, t, [255, 255, 255]);
  expect(onWhite.strokeStyleLog).toContain("rgba(60,50,40,0.35)");
  expect(onWhite.strokeStyleLog).toContain("rgba(60,50,40,0.28)");

  const onBlack = makeCtxSpy();
  drawHoopOutline(onBlack, t, [20, 20, 22]);
  expect(onBlack.strokeStyleLog).toContain("rgba(255,255,255,0.45)");
  expect(onBlack.strokeStyleLog).toContain("rgba(255,255,255,0.35)");
});

test("drawHoopOutline defaults to the original light-fabric (dark chrome) variant when no fabricRgb is given (back-compat)", () => {
  const t = { hoopWmm: 100, hoopHmm: 80, scale: 2, ox: 100, oy: 80 };
  const ctx = makeCtxSpy();
  drawHoopOutline(ctx, t);
  expect(ctx.strokeStyleLog[0]).toBe("rgba(60,50,40,0.35)");
});

// --- renderRealistic: fabricRgb precedence (B5) ----------------------------

test("renderRealistic: fabricRgb wins over the fabric CSS string when both are given (B5)", () => {
  const ctx = makeCtxSpy();
  const canvas = { width: 100, height: 100, getContext: () => ctx };
  renderRealistic(canvas, { stitches: [] }, { fabric: "#ffffff", fabricRgb: [25, 34, 60] });
  expect(ctx.fillStyle).toBe("rgb(25,34,60)");
});

test("renderRealistic: the existing fabric CSS string alone still works (B5 back-compat -- FontSelect/exportPNG)", () => {
  const ctx = makeCtxSpy();
  const canvas = { width: 100, height: 100, getContext: () => ctx };
  renderRealistic(canvas, { stitches: [] }, { fabric: "#ffffff" });
  expect(ctx.fillStyle).toBe("#ffffff");
});

test("renderRealistic: falls back to the original hardcoded fabric when neither fabric nor fabricRgb is given", () => {
  const ctx = makeCtxSpy();
  const canvas = { width: 100, height: 100, getContext: () => ctx };
  renderRealistic(canvas, { stitches: [] }, {});
  expect(ctx.fillStyle).toBe("#e9e6df");
});

test("renderRealistic renders a luminance-aware hoop outline even for an empty design -- the empty-state and populated-state paths share one fabric/contrast/view helper (B4)", () => {
  const ctx = makeCtxSpy();
  const canvas = { width: 400, height: 300, getContext: () => ctx };
  const garment = { widthIn: 4, heightIn: 3 };
  const result = renderRealistic(canvas, { stitches: [] }, { hoop: { garment }, fabricRgb: [20, 20, 22] });
  expect(result).toBeTruthy();
  expect(ctx.strokeStyleLog.some((s) => /^rgba\(255,255,255/.test(s))).toBe(true);
});

// --- renderRealistic view contract (B1, BLOCKING) --------------------------

test("renderRealistic view contract (B1): view defaults to identity -- omitting it matches passing zoom:1/pan:0 exactly (FontSelect/exportPNG unaffected)", () => {
  const canvas = { width: 400, height: 300, getContext: () => makeCtxSpy() };
  const design = { stitches: [] };
  const garment = { widthIn: 4, heightIn: 3 };
  const withView = renderRealistic(canvas, design, { hoop: { garment }, view: { zoom: 1, panX: 0, panY: 0 } });
  const withoutView = renderRealistic(canvas, design, { hoop: { garment } });
  expect(withoutView.scale).toBeCloseTo(withView.scale, 6);
  const p1 = withView.toCanvas(3, 4);
  const p2 = withoutView.toCanvas(3, 4);
  expect(p2.x).toBeCloseTo(p1.x, 6);
  expect(p2.y).toBeCloseTo(p1.y, 6);
});

test("renderRealistic view contract (B1): zoom:2 doubles the returned scale (scale = base.scale * view.zoom)", () => {
  const canvas = { width: 400, height: 300, getContext: () => makeCtxSpy() };
  const design = { stitches: [] };
  const garment = { widthIn: 4, heightIn: 3 };
  const r1 = renderRealistic(canvas, design, { hoop: { garment } });
  const r2 = renderRealistic(canvas, design, { hoop: { garment }, view: { zoom: 2, panX: 0, panY: 0 } });
  expect(r2.scale).toBeCloseTo(r1.scale * 2, 6);
});

test("renderRealistic view contract (B1): the pan that keeps an arbitrary cursor mm-point fixed can be solved and reused across a zoom change (wheel-zoom-around-cursor invariant)", () => {
  const canvas = { width: 400, height: 300, getContext: () => makeCtxSpy() };
  const design = { stitches: [] };
  const garment = { widthIn: 4, heightIn: 3 };
  const r1 = renderRealistic(canvas, design, { hoop: { garment }, view: { zoom: 1, panX: 5, panY: -3 } });
  const anchorMm = { x: 10, y: 6 };
  const p1 = r1.toCanvas(anchorMm.x, anchorMm.y); // the canvas point currently "under the cursor"

  // Same recurrence a wheel handler would use to solve for the new pan that
  // keeps p1 fixed while zooming 1 -> 2 about the canvas center:
  //   panX' = (p.x - cx) * (1 - k) + panX * k   where k = newZoom / oldZoom
  const cx = canvas.width / 2, cy = canvas.height / 2, k = 2 / 1;
  const panX2 = (p1.x - cx) * (1 - k) + 5 * k;
  const panY2 = (p1.y - cy) * (1 - k) + -3 * k;

  const r2 = renderRealistic(canvas, design, { hoop: { garment }, view: { zoom: 2, panX: panX2, panY: panY2 } });
  const p2 = r2.toCanvas(anchorMm.x, anchorMm.y);
  expect(p2.x).toBeCloseTo(p1.x, 6);
  expect(p2.y).toBeCloseTo(p1.y, 6);
});

// --- renderRealistic: limitStrands (stitch simulator) ----------------------

test("renderRealistic limitStrands draws only the first N strands; omitting it draws everything (simulator contract)", () => {
  // 4 chained stitches = 3 strands. No hoop and no weave, so strands are the
  // ONLY moveTo source in this render — which makes moveTo a clean proxy for
  // "how many strands got drawn".
  //
  // The per-strand pass count is DERIVED from the single-strand render rather
  // than hardcoded. What this test owns is the simulator contract (N strands
  // in -> N strands' worth of drawing out, 0 -> nothing at all); how many
  // passes drawThreads spends per strand is its business and changes with the
  // LOD ladder, so pinning a literal here only ever produces a false failure.
  const design = { stitches: [
    { x: 0, y: 0, type: "stitch" },
    { x: 10, y: 0, type: "stitch" },
    { x: 20, y: 0, type: "stitch" },
    { x: 30, y: 0, type: "stitch" },
  ] };
  const limited = makeCtxSpy();
  renderRealistic({ width: 100, height: 100, getContext: () => limited }, design, { limitStrands: 1 });
  const perStrand = limited.moveTo.mock.calls.length;
  expect(perStrand).toBeGreaterThan(0);

  const full = makeCtxSpy();
  renderRealistic({ width: 100, height: 100, getContext: () => full }, design, {});
  expect(full.moveTo).toHaveBeenCalledTimes(perStrand * 3);

  const zero = makeCtxSpy();
  renderRealistic({ width: 100, height: 100, getContext: () => zero }, design, { limitStrands: 0 });
  expect(zero.moveTo).toHaveBeenCalledTimes(0);
});

test("renderRealistic limitStrands past the end is a plain full render (clamps, never throws)", () => {
  const design = { stitches: [
    { x: 0, y: 0, type: "stitch" },
    { x: 10, y: 0, type: "stitch" },
  ] };
  const clamped = makeCtxSpy();
  renderRealistic({ width: 100, height: 100, getContext: () => clamped }, design, { limitStrands: 999 });
  // Identical to asking for exactly the one strand this design has.
  const exact = makeCtxSpy();
  renderRealistic({ width: 100, height: 100, getContext: () => exact }, design, { limitStrands: 1 });
  expect(clamped.moveTo.mock.calls.length).toBe(exact.moveTo.mock.calls.length);
  expect(clamped.moveTo.mock.calls.length).toBeGreaterThan(0);
});

// --- renderRealistic: jump/trim overlays -----------------------------------

test("renderRealistic showJumps draws dashed travel lines; showTrims draws X markers; both off draws neither", () => {
  const design = { stitches: [
    { x: 0, y: 0, type: "stitch" },
    { x: 10, y: 0, type: "stitch" },
    { x: 50, y: 50, type: "jump" },
    { x: 60, y: 50, type: "stitch" },
    { x: 60, y: 50, type: "trim" },
  ] };
  // The TRAVEL-LINE dash is [4,3] specifically. drawThreads also sets a dash
  // (the beaded thread specular), so "was setLineDash called at all" no longer
  // isolates the overlay — assert on the overlay's own pattern instead.
  const dashes = (c) => c.setLineDash.mock.calls.map((a) => JSON.stringify(a[0]));
  const TRAVEL = JSON.stringify([4, 3]);

  const off = makeCtxSpy();
  renderRealistic({ width: 100, height: 100, getContext: () => off }, design, {});
  expect(dashes(off)).not.toContain(TRAVEL);

  const jumps = makeCtxSpy();
  renderRealistic({ width: 100, height: 100, getContext: () => jumps }, design, { showJumps: true });
  // dash pattern set, then cleared
  expect(jumps.setLineDash).toHaveBeenCalledWith([4, 3]);
  expect(jumps.setLineDash).toHaveBeenCalledWith([]);
  expect(jumps.strokeStyleLog).toContain("rgba(37,99,235,0.8)");

  const trims = makeCtxSpy();
  renderRealistic({ width: 100, height: 100, getContext: () => trims }, design, { showTrims: true });
  expect(trims.strokeStyleLog).toContain("rgba(220,38,38,0.9)");
  expect(dashes(trims)).not.toContain(TRAVEL); // trim markers are solid
});

// --- threadLayers: the lit-cylinder model ----------------------------------
// These own the CLAIM the realistic render rests on — that a thread is shaded
// like a cylinder and that its sheen depends on which way it runs relative to
// the light. Asserted on the pure function, so no canvas is involved and a
// regression names itself instead of showing up as "the preview looks off".

// The light direction baked into preview.js, re-derived here rather than
// imported: if someone moves the lamp, these tests should fail loudly rather
// than silently follow it.
const LIGHT_ANGLE = Math.atan2(-0.8321, -0.5547);

function brightnessOf(cssRgb) {
  const [r, g, b] = cssRgb.match(/\d+/g).map(Number);
  return luminance([r, g, b]);
}

test("threadLayers: sheen is DIRECTIONAL — a thread running across the light is brighter than one running along it", () => {
  const rgb = [180, 60, 50];
  const along = threadLayers(rgb, LIGHT_ANGLE, 8);
  const across = threadLayers(rgb, LIGHT_ANGLE + Math.PI / 2, 8);
  const specular = (ls) => brightnessOf(ls[ls.length - 1].color);
  // This is the whole visual signature of embroidery: one thread colour reads
  // as two different colours when the stitch direction changes.
  expect(specular(across)).toBeGreaterThan(specular(along));
  // ...and by a margin big enough for a human to see, not float noise.
  expect(specular(across) - specular(along)).toBeGreaterThan(0.15);
});

test("threadLayers: layers run widest to narrowest, so painting them in order builds a cylinder instead of erasing it", () => {
  const ls = threadLayers([120, 140, 200], 0.7, 10);
  for (let i = 1; i < ls.length; i++) {
    expect(ls[i].width).toBeLessThan(ls[i - 1].width);
  }
  expect(ls[0].width).toBe(10); // the widest layer IS the thread's full width
});

test("threadLayers: the dark edge is darker than the base and the specular is lighter — a cross-section, not a flat stroke", () => {
  const rgb = [120, 140, 200];
  const ls = threadLayers(rgb, Math.PI / 2, 10);
  const base = luminance(rgb);
  expect(brightnessOf(ls[0].color)).toBeLessThan(base); // dark rim
  expect(brightnessOf(ls[ls.length - 1].color)).toBeGreaterThan(base); // specular
});

test("threadLayers: the specular sits off-centre, toward the lit side, and stays inboard of the silhouette", () => {
  const ls = threadLayers([200, 200, 200], LIGHT_ANGLE + Math.PI / 2, 10);
  const hi = ls[ls.length - 1].offset;
  expect(Math.abs(hi)).toBeGreaterThan(0.5); // genuinely displaced, not centred
  // A real cylinder's highlight never reaches its own outline.
  expect(Math.abs(hi)).toBeLessThan(10 / 2);
});

test("threadLayers: only the narrowest specular is dashed (plied-thread sheen beads; the body does not)", () => {
  const ls = threadLayers([200, 60, 60], 1.1, 9);
  expect(ls[ls.length - 1].dash).not.toBeNull();
  for (let i = 0; i < ls.length - 1; i++) expect(ls[i].dash).toBeNull();
});

// --- renderRealistic: physical thread width + LOD --------------------------

test("renderRealistic: thread width is PHYSICAL — the widest stroke tracks THREAD_WIDTH_MM x pxPerMm, so preview coverage is the coverage the machine lays", () => {
  const widths = [];
  const ctx = makeCtxSpy();
  Object.defineProperty(ctx, "lineWidth", {
    get() { return this._lw; },
    set(v) { this._lw = v; widths.push(v); },
  });
  // design-fit path: pxPerMm = t.scale * 10, and t.scale is set by the design
  // spanning 200 DST units across a 100px canvas with pad 24.
  const design = { stitches: [
    { x: -100, y: 0, type: "stitch" },
    { x: 100, y: 0, type: "stitch" },
  ] };
  // A canvas big enough that the physical width clears the 1.2px visibility
  // floor -- otherwise the floor, not THREAD_WIDTH_MM, is what is under test.
  renderRealistic({ width: 600, height: 600, getContext: () => ctx }, design, { pad: 24 });
  const t = fitTransform(design, 600, 600, 24);
  const expected = THREAD_WIDTH_MM * (t.scale * 10);
  expect(expected).toBeGreaterThan(1.2); // guard: this case is above the px floor
  expect(Math.max(...widths)).toBeCloseTo(expected * 1.04, 5); // 1.04 = the shadow pass
  expect(widths).toContain(expected);
});

test("renderRealistic: threadWidthMm is overridable, and a wider thread strokes wider", () => {
  const widthsFor = (mm) => {
    const w = [];
    const ctx = makeCtxSpy();
    Object.defineProperty(ctx, "lineWidth", { get() { return this._lw; }, set(v) { this._lw = v; w.push(v); } });
    renderRealistic({ width: 200, height: 200, getContext: () => ctx },
      { stitches: [{ x: -100, y: 0, type: "stitch" }, { x: 100, y: 0, type: "stitch" }] },
      { threadWidthMm: mm });
    return Math.max(...w);
  };
  expect(widthsFor(0.8)).toBeGreaterThan(widthsFor(0.4));
});

test("threadLodLayers: a big design or a thin thread sheds layers, and never sheds all of them", () => {
  const FULL = threadLodLayers(8, 500);
  expect(FULL).toBe(5);
  // Big design at a comfortable thread width -> cheaper, still shaded.
  expect(threadLodLayers(8, 30000)).toBeLessThan(FULL);
  expect(threadLodLayers(8, 61000)).toBeLessThan(threadLodLayers(8, 30000));
  // Zoomed out far enough that the narrow layers are sub-pixel.
  expect(threadLodLayers(1.3, 500)).toBeLessThan(FULL);
  // Monotonic in both inputs, and always draws something.
  for (const [lw, n] of [[1.3, 61000], [1.3, 500], [8, 61000], [8, 500], [2.0, 25000]]) {
    const v = threadLodLayers(lw, n);
    expect(v).toBeGreaterThanOrEqual(2);
    expect(v).toBeLessThanOrEqual(5);
  }
});

test("renderRealistic: threadLayers overrides the LOD ladder (the escape hatch a caller can force)", () => {
  const design = { stitches: [
    { x: -100, y: 0, type: "stitch" },
    { x: 100, y: 0, type: "stitch" },
  ] };
  const two = makeCtxSpy();
  renderRealistic({ width: 600, height: 600, getContext: () => two }, design, { threadLayers: 2 });
  const five = makeCtxSpy();
  renderRealistic({ width: 600, height: 600, getContext: () => five }, design, { threadLayers: 5 });
  expect(five.moveTo.mock.calls.length).toBeGreaterThan(two.moveTo.mock.calls.length);
});
