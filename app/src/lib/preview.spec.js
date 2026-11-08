import { test, expect, vi } from "vitest";
import { fitTransform, hoopTransform, luminance, isDark, weavePattern, drawHoopOutline, drawGrid, renderRealistic, threadLayers, threadLodLayers, layerSubsetForCount, drawThreads, kindStyle, TRUE_COLOUR_LAYER, THREAD_WIDTH_MM, softShadowFactor } from "./preview.js";
// ONE import line, deliberately. Three had accumulated here -- each bad merge
// of this file stacked another partial copy on top rather than reconciling the
// list, so the same seven names were declared three times over. esbuild
// tolerates that, which is exactly why it survived: the suite stayed green
// while the file quietly recorded a merge nobody had finished.
//
// It came back a FOURTH time: commit 423576a deleted the stale copy, and the
// next merge of main reinstated it, directly under this comment saying not to.
// If you are reconciling this file again, `node --input-type=module --check`
// on it is the check that actually fails -- vitest will not, because esbuild
// dedupes same-module bindings and runs all 42 tests regardless.

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
    setTransform: vi.fn(),
    beginPath: vi.fn(), closePath: vi.fn(),
    moveTo: vi.fn(), lineTo: vi.fn(), arcTo: vi.fn(),
    stroke: vi.fn(), fillRect: vi.fn(),
    clip: vi.fn(),
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

test("a real hoop widens the fit, so a big hoop cannot be drawn off-canvas", () => {
  // Hat front (127 x 57.15 mm) inside a 6x10 hoop (160 x 250) -- the hoop is
  // nearly five times taller than the placement box. Fitting the box alone,
  // which is all this did when its one caller passed a garment and named it a
  // hoop, would put most of that hoop outside the canvas.
  const garment = { widthIn: 5, heightIn: 2.25 };
  const t = hoopTransform(garment, 640, 420, 20, { widthMm: 160, heightMm: 250 });
  expect(t.realWmm).toBe(160);
  expect(t.realHmm).toBe(250);
  // The placement box is still reported, unchanged, under its old name.
  expect(t.hoopWmm).toBeCloseTo(127, 1);
  expect(t.boxWmm).toBeCloseTo(127, 1);
  // Scale now fits 160 x 250: min(600/160, 380/250) = min(3.75, 1.52).
  expect(t.scale).toBeCloseTo(1.52, 2);
  // And the whole hoop lands inside the canvas, which is the point.
  expect(t.oy - (t.realHmm / 2) * t.scale).toBeGreaterThanOrEqual(0);
  expect(t.ox + (t.realWmm / 2) * t.scale).toBeLessThanOrEqual(640);
});

test("a hoop SMALLER than the placement box does not shrink the view", () => {
  // Left chest is 101.6 mm; the 4x4 hoop is 100. The union is the box, so the
  // canvas keeps the scale it had before hoops were drawn at all.
  const garment = { widthIn: 4, heightIn: 4 };
  const withHoop = hoopTransform(garment, 640, 420, 20, { widthMm: 100, heightMm: 100 });
  const without = hoopTransform(garment, 640, 420, 20);
  expect(withHoop.scale).toBeCloseTo(without.scale, 6);
});

test("omitting the hoop reproduces the old transform exactly", () => {
  // The back-compat contract every other caller and spec depends on.
  const garment = { widthIn: 5, heightIn: 2.25 };
  const t = hoopTransform(garment, 640, 420, 20);
  expect(t.realWmm).toBeNull();
  expect(t.realHmm).toBeNull();
  expect(t.scale).toBeCloseTo(4.724, 2);
});

test("with a hoop the canvas draws TWO rectangles, not one", () => {
  // The bug this fixes, stated the way the audit measured it: switching hoops
  // left the rendered canvas byte-identical, because only the placement box
  // was ever drawn. With a hoop there is strictly more ink, and the two rects
  // are told apart by the dash -- the hoop keeps the solid ring and its 3 mm
  // margin, the box becomes dashed with no margin of its own.
  const garment = { widthIn: 4, heightIn: 4 };
  const design = { stitches: [] };

  const bareCtx = makeCtxSpy();
  renderRealistic({ width: 640, height: 420, getContext: () => bareCtx }, design,
                  { hoop: { garment }, fabricRgb: [240, 240, 240] });

  const hoopedCtx = makeCtxSpy();
  renderRealistic({ width: 640, height: 420, getContext: () => hoopedCtx }, design,
                  { hoop: { garment, hoop: { widthMm: 130, heightMm: 180 } },
                    fabricRgb: [240, 240, 240] });

  expect(hoopedCtx.stroke.mock.calls.length)
    .toBeGreaterThan(bareCtx.stroke.mock.calls.length);

  // The box's dash. `setLineDash([5,4])` is the hoop's existing inset margin,
  // so the discriminator is the 7 -- present only once a hoop is known.
  const dashes = (c) => c.setLineDash.mock.calls.map((a) => a[0]).filter(Boolean);
  expect(dashes(hoopedCtx).some((d) => d[0] === 7)).toBe(true);
  expect(dashes(bareCtx).some((d) => d[0] === 7)).toBe(false);
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

// --- renderRealistic: the surround (2026-09-30) ----------------------------

test("renderRealistic: with a surround and a hoop, the canvas is filled with the surround and the fabric is clipped to the hoop", () => {
  const ctx = makeCtxSpy();
  const fills = [];
  ctx.fillRect = vi.fn((x, y, w, h) => fills.push({ style: ctx.fillStyle, x, y, w, h }));
  const canvas = { width: 400, height: 300, getContext: () => ctx };
  const garment = { widthIn: 4, heightIn: 3 };
  renderRealistic(canvas, { stitches: [] }, { hoop: { garment }, fabricRgb: [235, 232, 223], surround: "#22252c" });
  // First fill: the whole canvas, in the surround.
  expect(fills[0]).toMatchObject({ style: "#22252c", x: 0, y: 0, w: 400, h: 300 });
  // Second fill: the fabric, and only the hoop's rectangle of it, under a clip.
  expect(fills[1].style).toBe("rgb(235,232,223)");
  expect(fills[1].w).toBeLessThan(400);
  expect(fills[1].h).toBeLessThan(300);
  expect(ctx.clip).toHaveBeenCalledTimes(1);
  // And it is centred, like the hoop is.
  expect(fills[1].x + fills[1].w / 2).toBeCloseTo(200, 6);
  expect(fills[1].y + fills[1].h / 2).toBeCloseTo(150, 6);
});

test("renderRealistic: the fabric clip is the REAL hoop when one is given, not the placement box", () => {
  const ctx = makeCtxSpy();
  const fills = [];
  ctx.fillRect = vi.fn((x, y, w, h) => fills.push({ x, y, w, h }));
  const canvas = { width: 400, height: 300, getContext: () => ctx };
  // Hat front (5 x 2.25 in) inside a 6x10 hoop: the hoop is the bigger rect.
  const garment = { widthIn: 5, heightIn: 2.25 };
  renderRealistic(canvas, { stitches: [] }, {
    hoop: { garment, hoop: { widthMm: 160, heightMm: 250 } }, fabricRgb: [235, 232, 223], surround: "#22252c",
  });
  const hoopAspect = 160 / 250;
  expect(fills[1].w / fills[1].h).toBeCloseTo(hoopAspect, 3);
});

test("renderRealistic: a surround without a hoop is ignored -- thumbnails and PNG export keep the edge-to-edge fabric", () => {
  const ctx = makeCtxSpy();
  const fills = [];
  ctx.fillRect = vi.fn((x, y, w, h) => fills.push({ style: ctx.fillStyle, x, y, w, h }));
  const canvas = { width: 100, height: 100, getContext: () => ctx };
  renderRealistic(canvas, { stitches: [] }, { fabric: "#ffffff", surround: "#22252c" });
  expect(fills).toHaveLength(1);
  expect(fills[0]).toMatchObject({ style: "#ffffff", w: 100, h: 100 });
  expect(ctx.clip).not.toHaveBeenCalled();
});

test("renderRealistic: omitting the surround is byte-for-byte the old path -- one edge-to-edge fabric fill, no clip", () => {
  const ctx = makeCtxSpy();
  const fills = [];
  ctx.fillRect = vi.fn((x, y, w, h) => fills.push({ style: ctx.fillStyle, x, y, w, h }));
  const canvas = { width: 400, height: 300, getContext: () => ctx };
  const garment = { widthIn: 4, heightIn: 3 };
  renderRealistic(canvas, { stitches: [] }, { hoop: { garment }, fabricRgb: [235, 232, 223] });
  expect(fills).toHaveLength(1);
  expect(fills[0]).toMatchObject({ style: "rgb(235,232,223)", x: 0, y: 0, w: 400, h: 300 });
  expect(ctx.clip).not.toHaveBeenCalled();
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

// --- renderRealistic: devicePixelRatio -------------------------------------

// The field's bitmap is cut at devicePixelRatio so the preview is sharp on a
// HiDPI screen rather than drawn at half resolution and upscaled. The whole
// contract is that NOTHING else has to know: the base transform absorbs the
// ratio, so the geometry a caller gets back is in CSS px at any dpr.
test("renderRealistic at dpr 2 scales the context and keeps the returned transform in CSS px", () => {
  const garment = { widthIn: 4, heightIn: 4 };
  const design = { stitches: [{ x: 0, y: 0, type: "stitch" }, { x: 100, y: 100, type: "stitch" }] };

  const at1 = makeCtxSpy();
  const r1 = renderRealistic(
    { width: 400, height: 300, getContext: () => at1 }, design, { hoop: { garment } });

  // Same CSS box, bitmap cut at 2x — what EmbroideryField does on a Retina
  // screen.
  const at2 = makeCtxSpy();
  const r2 = renderRealistic(
    { width: 800, height: 600, getContext: () => at2 }, design, { hoop: { garment }, dpr: 2 });

  expect(at2.setTransform).toHaveBeenCalledWith(2, 0, 0, 2, 0, 0);
  // Identical geometry: same px-per-mm, same origin. A design 40 mm across
  // still measures 40 mm worth of CSS px, so hit-testing and the overlay need
  // no dpr of their own.
  expect(r2.scale).toBeCloseTo(r1.scale, 6);
  const p1 = r1.toCanvas(10, 10), p2 = r2.toCanvas(10, 10);
  expect(p2.x).toBeCloseTo(p1.x, 6);
  expect(p2.y).toBeCloseTo(p1.y, 6);
  // The fabric fill covers the whole bitmap, expressed in the scaled space.
  expect(at2.fillRect).toHaveBeenCalledWith(0, 0, 400, 300);
});

test("renderRealistic leaves the context transform alone at the default dpr", () => {
  // Every caller but the field passes no dpr, and two of the ctx doubles in
  // this repo have no setTransform at all — so the default path must not
  // touch it.
  const ctx = makeCtxSpy();
  renderRealistic({ width: 400, height: 300, getContext: () => ctx }, { stitches: [] }, {});
  expect(ctx.setTransform).not.toHaveBeenCalled();
  expect(ctx.fillRect).toHaveBeenCalledWith(0, 0, 400, 300);
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
  // The expected width is derived from the LITERAL 0.4, not from the imported
  // THREAD_WIDTH_MM. Deriving it from the constant made this assertion
  // tautological: it moved with the constant, so the whole suite stayed green
  // when the value was changed to 0.9 -- caught by a mutation probe, 2026-08-25.
  const expected = 0.4 * (t.scale * 10);
  expect(expected).toBeGreaterThan(1.2); // guard: this case is above the px floor
  expect(Math.max(...widths)).toBeCloseTo(expected * 1.04, 5); // 1.04 = the shadow pass
  expect(widths).toContain(expected);
});

test("THREAD_WIDTH_MM is 0.4 and MUST NOT be widened — the anti-flattery guard", () => {
  // This is the one assertion standing between the preview and a defect this
  // repo has already reasoned about at length, so it pins a literal rather
  // than anything derived.
  //
  // 0.4 mm is nominal 40wt laid thread. Against the fill row Kent ruled on
  // 2026-09-03 -- 0.15 mm, the professional's measured pitch (machine.py
  // FILL_ROW_MM, PR #339; the browser engine's fillRowMm, PR #341) -- that is
  // coverage 2.67: rows overlap by more than half, as the pro's do. Against
  // the 0.4 mm satin spacing it is exactly 1.0, columns that just touch.
  // Widening it would make an open fill look solid; narrowing it would make
  // the ruled fill look like hatching. Either hides a real density behind
  // the display layer.
  //
  // The density question this test used to guard as "undecided and
  // sew-out-gated" is decided (DOCTRINE, 2026-09-03). The gate that forbids
  // changing a PHYSICAL constant without a sew-out is ROADMAP gate 1, and
  // this constant is one: if a sew-out later establishes a different real
  // laid width, change this number AND the MASTER_SCOPE claim that cites it
  // AND say so out loud -- never quietly because a fill looked gappy or
  // solid.
  expect(THREAD_WIDTH_MM).toBe(0.4);

  const FILL_ROW_MM = 0.15; // digitizer/digitizer_core/machine.py, ruled 2026-09-03
  const SATIN_SPACING_MM = 0.4; // machine.SATIN_SPACING_MM, unchanged by the ruling
  expect(THREAD_WIDTH_MM / FILL_ROW_MM).toBeCloseTo(2.667, 2); // rows overlap, as the pro's do
  expect(THREAD_WIDTH_MM / SATIN_SPACING_MM).toBe(1); // columns just touch
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
  expect(FULL).toEqual([0, 1, 2, 3, 4]);
  // Big design at a comfortable thread width -> cheaper, still shaded.
  expect(threadLodLayers(8, 30000).length).toBeLessThan(FULL.length);
  expect(threadLodLayers(8, 61000).length).toBeLessThan(threadLodLayers(8, 30000).length);
  // Zoomed out far enough that the narrow layers are sub-pixel.
  expect(threadLodLayers(1.3, 500).length).toBeLessThan(FULL.length);
  // Always draws something, and never an out-of-range index.
  for (const [lw, n] of [[1.3, 61000], [1.3, 500], [8, 61000], [8, 500], [2.0, 25000]]) {
    const v = threadLodLayers(lw, n);
    expect(v.length).toBeGreaterThanOrEqual(2);
    expect(v.length).toBeLessThanOrEqual(5);
    for (const i of v) expect(i).toBeGreaterThanOrEqual(0);
    for (const i of v) expect(i).toBeLessThan(5);
  }
});

test("threadLodLayers: EVERY rung paints the thread's true colour — the ladder is a subset, never a prefix", () => {
  // The regression this exists for: the ladder used to return a COUNT, and the
  // cheapest rung took the first two layers — which are the darkened rim and
  // its inboard step. The true colour lives at index 2, so every zoomed-out
  // preview rendered ~15% dark, uniformly, with the whole suite green.
  const rungs = [
    threadLodLayers(8, 500),      // full
    threadLodLayers(8, 30000),    // big design
    threadLodLayers(8, 61000),    // huge design
    threadLodLayers(1.3, 500),    // zoomed out
    threadLodLayers(1.3, 61000),  // both
    threadLodLayers(2.0, 25000),  // the middle rung
  ];
  for (const r of rungs) expect(r).toContain(TRUE_COLOUR_LAYER);

  // And prove index 2 really is the undarkened colour, so the guard above
  // cannot rot if the stack is reordered.
  const rgb = [180, 60, 50];
  const layers = threadLayers(rgb, 0.7, 10);
  expect(layers[TRUE_COLOUR_LAYER].color).toBe(`rgb(${rgb[0]},${rgb[1]},${rgb[2]})`);
});

test("drawThreads draws BLOCK-major: a later colour covers an earlier one, and a recurring colour keeps its own place in sew order", () => {
  // Strand order is sew order. Red, then blue, then red again: the strokes
  // must come out in exactly that order, or an under-colour bleeds through
  // the over-colour's edges where they overlap.
  const RED = [200, 10, 10], BLUE = [10, 10, 200];
  const strands = [
    { x0: 0, y0: 0, x1: 10, y1: 0, rgb: RED, kind: "stitch" },
    { x0: 0, y0: 0, x1: 10, y1: 0, rgb: BLUE, kind: "stitch" },
    { x0: 0, y0: 0, x1: 10, y1: 0, rgb: RED, kind: "stitch" },
  ];
  const ctx = makeCtxSpy();
  drawThreads(ctx, strands, (x) => x, (y) => y, 8, { layers: [2] }); // true colour only
  // Drop the shadow pass's black, keep the thread colours in draw order.
  const painted = ctx.strokeStyleLog.filter((s) => /^rgb\(/.test(s));
  expect(painted).toEqual([
    "rgb(200,10,10)",
    "rgb(10,10,200)",
    "rgb(200,10,10)", // the recurring block paints LAST, not merged into the first
  ]);
});

test("lit view skips a whole off-clip bucket, never part of one -- the on-canvas strokes are untouched", () => {
  // Per-strand culling inside a path that still draws changes Chromium's
  // anti-aliasing of the rest of that path (measured 2026-10-08), so the only
  // pixel-exact skip is a whole stroke() whose every strand is off the clip.
  const RED = [200, 10, 10], BLUE = [10, 10, 200];
  const strands = [
    { x0: 10, y0: 10, x1: 50, y1: 10, rgb: RED, kind: "stitch" },       // on canvas
    { x0: 5000, y0: 10, x1: 5040, y1: 10, rgb: BLUE, kind: "stitch" },  // far right
    { x0: 10, y0: 20, x1: 50, y1: 20, rgb: RED, kind: "stitch" },       // on canvas
    { x0: -900, y0: 20, x1: 60, y1: 20, rgb: RED, kind: "stitch" },     // crosses the edge
  ];
  const clip = { x0: 0, y0: 0, x1: 100, y1: 100 };
  const noClip = makeCtxSpy();
  drawThreads(noClip, strands, (x) => x, (y) => y, 8, { layers: [TRUE_COLOUR_LAYER] });
  const clipped = makeCtxSpy();
  drawThreads(clipped, strands, (x) => x, (y) => y, 8, { layers: [TRUE_COLOUR_LAYER], clip });
  const colours = (c) => c.strokeStyleLog.filter((x) => /^rgb\(/.test(x));
  expect(colours(noClip)).toEqual(["rgb(200,10,10)", "rgb(10,10,200)", "rgb(200,10,10)"]);
  // The blue block is entirely off-clip and goes; both red blocks stay, the
  // edge-crossing strand with them.
  expect(colours(clipped)).toEqual(["rgb(200,10,10)", "rgb(200,10,10)"]);
});

test("FLAT view agrees with the lit view about sew order — a recurring colour is its own block there too", () => {
  // The flat path used to key its buckets by RGB alone, so the third strand
  // below was merged back into the first block and drawn BEFORE the blue it
  // is sewn on top of. Flat is the view you switch to specifically to judge
  // coverage, so it disagreeing with realistic about what covers what was the
  // worst possible place for this bug (found by review 2026-08-26).
  const RED = [200, 10, 10], BLUE = [10, 10, 200];
  const strands = [
    { x0: 0, y0: 0, x1: 10, y1: 0, rgb: RED, kind: "stitch" },
    { x0: 0, y0: 0, x1: 10, y1: 0, rgb: BLUE, kind: "stitch" },
    { x0: 0, y0: 0, x1: 10, y1: 0, rgb: RED, kind: "stitch" },
  ];

  const flatCtx = makeCtxSpy();
  drawThreads(flatCtx, strands, (x) => x, (y) => y, 8, { flat: true });
  const flatOrder = flatCtx.strokeStyleLog.filter((c) => /^rgb\(/.test(c));
  expect(flatOrder).toEqual([
    "rgb(200,10,10)",
    "rgb(10,10,200)",
    "rgb(200,10,10)",
  ]);

  // Stated as an invariant, not two independent expectations: whatever the
  // block sequence is, the two views must produce the SAME one.
  const litCtx = makeCtxSpy();
  drawThreads(litCtx, strands, (x) => x, (y) => y, 8, { layers: [TRUE_COLOUR_LAYER] });
  const litOrder = litCtx.strokeStyleLog.filter((c) => /^rgb\(/.test(c));
  expect(flatOrder).toEqual(litOrder);
});

test("FLAT view still merges nothing it should not: consecutive same-colour strands are ONE stroke pass", () => {
  // The fix must not cost the batching -- one beginPath/stroke per block, not
  // per strand, or a big design pays a path setup for every stitch.
  const RED = [200, 10, 10];
  const strands = Array.from({ length: 50 }, () => (
    { x0: 0, y0: 0, x1: 10, y1: 0, rgb: RED, kind: "stitch" }
  ));
  const ctx = makeCtxSpy();
  drawThreads(ctx, strands, (x) => x, (y) => y, 8, { flat: true });
  expect(ctx.stroke).toHaveBeenCalledTimes(1);
  expect(ctx.strokeStyleLog.filter((c) => /^rgb\(/.test(c))).toEqual(["rgb(200,10,10)"]);
});

test("a layer COUNT paints the true colour too — the same prefix bug, one layer down", () => {
  // renderRealistic's public `threadLayers` option forwards a number straight
  // to drawThreads' `layers`, where it used to mean `slice(0, n)`. Every
  // prefix shorter than 3 excluded index 2, the only undarkened layer, so
  // `{ threadLayers: 2 }` painted rgb(132,7,7) and rgb(170,9,9) for a
  // rgb(200,10,10) thread and never the colour itself. The LOD ladder was
  // fixed for exactly this on 2026-08-25; this caller-facing path kept the
  // bug because the ladder stopped emitting counts while the option went on
  // accepting them.
  for (let n = 1; n <= 5; n++) {
    expect(layerSubsetForCount(n)).toContain(TRUE_COLOUR_LAYER);
    expect(layerSubsetForCount(n).length).toBe(n);
  }
  // Out-of-range clamps rather than throwing or emptying the stack.
  expect(layerSubsetForCount(0)).toContain(TRUE_COLOUR_LAYER);
  expect(layerSubsetForCount(99)).toEqual([0, 1, 2, 3, 4]);

  // And end to end: the narrowest count still puts real thread colour down.
  const RED = [200, 10, 10];
  const strands = [{ x0: 0, y0: 0, x1: 10, y1: 0, rgb: RED, kind: "stitch" }];
  for (const n of [1, 2, 3, 4, 5]) {
    const ctx = makeCtxSpy();
    drawThreads(ctx, strands, (x) => x, (y) => y, 8, { layers: n });
    expect(ctx.strokeStyleLog).toContain("rgb(200,10,10)");
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

// --- renderRealistic: threadStyle "flat" (the realistic-view toggle) --------

test("threadStyle 'flat' drops the lighting entirely — no shadow, no sheen, no dash", () => {
  const design = { stitches: [
    { x: -100, y: 0, type: "stitch" },
    { x: 0, y: 40, type: "stitch" },
    { x: 100, y: 0, type: "stitch" },
  ] };
  const flat = makeCtxSpy();
  renderRealistic({ width: 600, height: 600, getContext: () => flat }, design, { threadStyle: "flat" });
  // The black drop-shadow pass and every lightened specular are gone; what is
  // left is the thread colour itself (plus the fabric fill, which is fillStyle,
  // not strokeStyle).
  expect(flat.strokeStyleLog.some((s) => /^rgba\(0,0,0/.test(s))).toBe(false);
  expect(flat.setLineDash.mock.calls.every((a) => !a[0] || a[0].length === 0)).toBe(true);
  // One stroke per colour, not one per (colour, direction, layer).
  expect(flat.stroke).toHaveBeenCalledTimes(1);
});

test("threadStyle 'flat' keeps PHYSICAL thread width, so switching views never changes the coverage answer", () => {
  const design = { stitches: [
    { x: -100, y: 0, type: "stitch" },
    { x: 100, y: 0, type: "stitch" },
  ] };
  const widthsFor = (style) => {
    const w = [];
    const ctx = makeCtxSpy();
    Object.defineProperty(ctx, "lineWidth", { get() { return this._lw; }, set(v) { this._lw = v; w.push(v); } });
    renderRealistic({ width: 600, height: 600, getContext: () => ctx }, design, { threadStyle: style });
    return w;
  };
  const t = fitTransform(design, 600, 600, 24);
  const expected = THREAD_WIDTH_MM * (t.scale * 10);
  expect(widthsFor("flat")).toContain(expected);
  expect(widthsFor("realistic")).toContain(expected);
});

test("threadStyle: omitting it takes the SAME branch as 'realistic', and a different one from 'flat'", () => {
  // Scope, stated honestly: this pins which BRANCH the default takes. It is
  // not a baseline of what the realistic renderer draws — any change to the
  // shading moves both sides of the omitted-vs-explicit comparison equally, so
  // that pair can only ever catch a flipped default. The title used to claim
  // "exactly today's render", which overstated it (review, 2026-08-25); the
  // flat comparison below is what makes the branch check meaningful at all.
  const design = { stitches: [
    { x: -100, y: 0, type: "stitch" },
    { x: 100, y: 0, type: "stitch" },
  ] };
  const shot = (opts) => {
    const ctx = makeCtxSpy();
    const widths = [];
    Object.defineProperty(ctx, "lineWidth", { get() { return this._lw; }, set(v) { this._lw = v; widths.push(v); } });
    renderRealistic({ width: 600, height: 600, getContext: () => ctx }, design, opts);
    return { strokes: ctx.strokeStyleLog, moves: ctx.moveTo.mock.calls.length, widths };
  };
  const omitted = shot({});
  const explicit = shot({ threadStyle: "realistic" });
  const flat = shot({ threadStyle: "flat" });

  // Default === realistic, on every channel this double can observe.
  expect(omitted.strokes).toEqual(explicit.strokes);
  expect(omitted.moves).toBe(explicit.moves);
  expect(omitted.widths).toEqual(explicit.widths);

  // And that branch is genuinely the lit one: it differs from flat, and it
  // lays down the drop shadow flat has no equivalent of.
  expect(omitted.strokes).not.toEqual(flat.strokes);
  expect(omitted.moves).toBeGreaterThan(flat.moves);
  expect(omitted.strokes.some((s) => /^rgba\(0,0,0/.test(s))).toBe(true);
  expect(flat.strokes.some((s) => /^rgba\(0,0,0/.test(s))).toBe(false);
});

test("threadStyle 'flat' still separates colours — a two-colour design strokes each once", () => {
  const design = {
    stitches: [
      { x: -100, y: 0, type: "stitch" },
      { x: -50, y: 0, type: "stitch" },
      { x: -50, y: 0, type: "color" },
      { x: 50, y: 0, type: "stitch" },
      { x: 100, y: 0, type: "stitch" },
    ],
    colors: [{ r: 200, g: 10, b: 10 }, { r: 10, g: 10, b: 200 }],
  };
  const ctx = makeCtxSpy();
  renderRealistic({ width: 600, height: 600, getContext: () => ctx }, design, { threadStyle: "flat" });
  expect(ctx.strokeStyleLog).toContain("rgb(200,10,10)");
  expect(ctx.strokeStyleLog).toContain("rgb(10,10,200)");
  expect(ctx.stroke).toHaveBeenCalledTimes(2);
});

// --- the render path actually USES each strand's direction --------------------
// Every other sheen assertion calls threadLayers() directly, which pins the
// model but not its wiring: replacing `threadLayers(rgb, angle, lw)` with
// `threadLayers(rgb, 0, lw)` inside drawThreads neuters the whole feature and
// leaves those tests green (confirmed by mutation, 2026-08-25). These close
// that gap by going through drawThreads.

test("drawThreads feeds each strand's OWN direction into the shading — two directions render different colours", () => {
  const rgb = [180, 60, 50];
  const paint = (x1, y1) => {
    const ctx = makeCtxSpy();
    drawThreads(ctx, [{ x0: 0, y0: 0, x1, y1, rgb, kind: "stitch" }], (v) => v, (v) => v, 8, {});
    return ctx.strokeStyleLog.filter((s) => /^rgb\(/.test(s));
  };
  const horizontal = paint(100, 0);
  const diagonal = paint(70, 70);
  expect(horizontal.length).toBeGreaterThan(0);
  expect(horizontal.length).toBe(diagonal.length);
  // Same colour, same width, different heading -> the stroke colours must
  // differ somewhere. If the render path ignored direction they would be
  // identical, which is exactly the mutation this guards.
  expect(horizontal).not.toEqual(diagonal);
});

test("drawThreads: a strand running ACROSS the light paints a brighter specular than one running along it", () => {
  const rgb = [180, 60, 50];
  // preview.js's light, re-derived here so moving the lamp fails loudly.
  const LIGHT_ANGLE = Math.atan2(-0.8321, -0.5547);
  const brightest = (angle) => {
    const ctx = makeCtxSpy();
    const x1 = Math.cos(angle) * 100, y1 = Math.sin(angle) * 100;
    drawThreads(ctx, [{ x0: 0, y0: 0, x1, y1, rgb, kind: "stitch" }], (v) => v, (v) => v, 8, {});
    return Math.max(
      ...ctx.strokeStyleLog
        .filter((s) => /^rgb\(/.test(s))
        .map((s) => luminance(s.match(/\d+/g).map(Number))),
    );
  };
  expect(brightest(LIGHT_ANGLE + Math.PI / 2)).toBeGreaterThan(brightest(LIGHT_ANGLE));
});

test("drawThreads leaves no dash set on the context — the overlays that draw after it must start solid", () => {
  // The rewritten jump/trim test checks only that the [4,3] TRAVEL pattern is
  // absent, which a leaked beaded-specular dash satisfies. This pins the reset
  // itself: drop drawThreads' final setLineDash([]) and the trim markers
  // inherit the thread sheen's dash in a real browser.
  const ctx = makeCtxSpy();
  drawThreads(ctx, [{ x0: 0, y0: 0, x1: 100, y1: 0, rgb: [180, 60, 50], kind: "stitch" }], (v) => v, (v) => v, 8, {});
  const calls = ctx.setLineDash.mock.calls;
  expect(calls.length).toBeGreaterThan(0);
  const last = calls[calls.length - 1][0];
  expect(last).toEqual([]); // solid on exit, whatever it did in between
});

// ---- Stitch KINDS ----------------------------------------------------------
//
// Kent, 2026-09-15: "it's hard to see the satin borders when they are on, off
// or even existent." The shading was never the problem — nothing told the
// renderer which strands were what, so satin, tatami, bean runs, underlay and
// travel were all drawn with one profile. `design.runs` (see strands.js) is
// that missing half, and these tests pin both what each kind now looks like
// and the rule that its absence changes nothing.

// A ctx double that records the ORDER of everything, not just the colours:
// several of the claims below ("underlay sits under", "a border's shadow lands
// on the fill, not beneath it") are claims about draw order, which is only
// visible in the call sequence.
function makeCallLog() {
  const calls = [];
  let _ss, _lw;
  const ctx = {
    save: () => calls.push(["save"]), restore: () => calls.push(["restore"]),
    setTransform: () => {}, closePath: () => {},
    beginPath: () => calls.push(["beginPath"]),
    moveTo: () => {}, lineTo: () => {}, arcTo: () => {},
    stroke: () => calls.push(["stroke", _ss, _lw]),
    fillRect: () => {}, setLineDash: (d) => calls.push(["dash", d && d.slice()]),
    lineCap: "", lineJoin: "", fillStyle: "",
    get strokeStyle() { return _ss; }, set strokeStyle(v) { _ss = v; },
    get lineWidth() { return _lw; }, set lineWidth(v) { _lw = v; },
    calls,
  };
  return ctx;
}
// Every stroke() in order, as {color, width}.
const strokesOf = (ctx) => ctx.calls.filter((c) => c[0] === "stroke").map((c) => ({ color: c[1], width: c[2] }));
const alphaOf = (c) => { const m = /^rgba\(0,0,0,([\d.]+)\)$/.exec(c || ""); return m ? Number(m[1]) : null; };
const firstIndexOf = (list, pred) => list.findIndex(pred);

// A design made of consecutive runs of one colour, one span per run.
function kindedDesign(kinds, rgb) {
  const stitches = [];
  const runs = [];
  kinds.forEach(([kind, role], k) => {
    const i0 = stitches.length;
    for (let i = 0; i < 4; i++) stitches.push({ x: k * 40 + i * 9, y: (i % 2) * 7, type: "stitch" });
    runs.push({ i0, i1: stitches.length - 1, kind, role: role || "", shape: "s" + k, block: 0 });
  });
  stitches.push({ x: 0, y: 0, type: "end" });
  return { stitches, colors: [{ r: rgb[0], g: rgb[1], b: rgb[2] }], runs };
}

test("the kind table cannot flatter coverage: no kind is drawn WIDER than the physical thread, and the two coverage-bearing kinds are exactly 1", () => {
  // THREAD_WIDTH_MM is physical so that preview coverage IS the coverage the
  // machine lays (see the anti-flattery guard above). A kind that inflated
  // itself would reintroduce exactly that defect one level down — an open fill
  // that looks solid — while leaving the constant untouched and the guard
  // green. Kinds may sit UNDER the physical width (a lone running stitch sinks
  // into the weave; an underlay is buried) but never over it.
  for (const kind of ["stitch", "satin", "fill", "run", "underlay", "travel", "nonsense"]) {
    for (const role of ["", "border", "edge_cap"]) {
      expect(kindStyle(kind, role).w).toBeLessThanOrEqual(1);
      expect(kindStyle(kind, role).w).toBeGreaterThan(0);
    }
  }
  expect(kindStyle("satin", "").w).toBe(1);
  expect(kindStyle("fill", "").w).toBe(1);
  expect(kindStyle("satin", "border").w).toBe(1);
  // An unknown kind or role costs distinction, never correctness.
  expect(kindStyle("nonsense", "nonsense")).toMatchObject({ w: 1, tone: 1, sheen: 1, bead: 1, shadow: 1 });
});

test("NO kind marks structure with a colour — every stroke follows the thread, so the canvas can still be judged for thread colour", () => {
  // The honest levers are light and width. A magenta border overlay would be
  // legible and would lie: this canvas is also what Kent picks thread off.
  const design = kindedDesign([["underlay"], ["fill"], ["satin", "border"], ["travel"], ["run"]], [0, 0, 0]);
  const paint = (rgb) => {
    const ctx = makeCallLog();
    renderRealistic({ width: 300, height: 220, getContext: () => ctx }, design, { colorOverride: rgb });
    return strokesOf(ctx).map((s) => s.color);
  };
  const red = paint([200, 10, 10]);
  const blue = paint([10, 120, 220]);
  expect(red.length).toBe(blue.length);
  expect(red.length).toBeGreaterThan(10);
  for (let i = 0; i < red.length; i++) {
    if (alphaOf(red[i]) != null) {
      // The drop shadow is the ONLY thread-independent paint, and it is black.
      expect(red[i]).toBe(blue[i]);
      expect(red[i]).toMatch(/^rgba\(0,0,0,/);
    } else {
      // Everything else moved with the thread — nothing is a fixed hue.
      expect(red[i]).not.toBe(blue[i]);
      expect(red[i]).toMatch(/^rgb\(/);
    }
  }
});

test("satin returns more light than tatami, and tatami's sheen is broken into far shorter beads", () => {
  // The two coverage kinds are the same physical width, so the whole
  // difference has to live in the light: a satin column is long, taut and
  // unbroken (continuous specular); a tatami row is short and ends in a
  // penetration every few millimetres (chopped specular). That contrast is
  // what makes a fill read matte beside a border.
  const rgb = [180, 60, 50], angle = 0.4, lw = 8;
  const satin = threadLayers(rgb, angle, lw, kindStyle("satin", ""));
  const fill = threadLayers(rgb, angle, lw, kindStyle("fill", ""));
  const lum = (css) => { const [r, g, b] = css.match(/\d+/g).map(Number); return luminance([r, g, b]); };
  expect(lum(satin[4].color)).toBeGreaterThan(lum(fill[4].color));
  expect(lum(satin[3].color)).toBeGreaterThan(lum(fill[3].color));
  // Bead length: satin's on-dash is more than twice tatami's.
  expect(satin[4].dash[0]).toBeGreaterThan(fill[4].dash[0] * 2);
  // Both keep the lopsided ~3:1 duty cycle, so each still reads as modulated
  // sheen on a continuous thread rather than as a dashed line.
  expect(satin[4].dash[0] / satin[4].dash[1]).toBeCloseTo(fill[4].dash[0] / fill[4].dash[1], 6);
  // Neither is drawn narrower than the other: this is light, not geometry.
  expect(satin[0].width).toBe(fill[0].width);
});

test("underlay and travel sit UNDER: thinner, dimmer, and drawn before the stitching that covers them", () => {
  const u = kindStyle("underlay", ""), t = kindStyle("travel", ""), s = kindStyle("satin", "");
  expect(u.w).toBeLessThan(s.w);
  expect(t.w).toBeLessThan(u.w);          // travel is the faintest thing on the cloth
  expect(u.tone).toBeLessThan(1);          // in the top layer's shadow
  expect(u.sheen).toBeLessThan(s.sheen);
  expect(u.shadow).toBeLessThan(s.shadow); // sunk into the weave, not proud of it
  expect(u.z).toBeLessThan(s.z);
  expect(t.z).toBeLessThan(u.z);

  // ...and the z rank really is what the renderer draws by. One colour, satin
  // FIRST in sew order, underlay second: without the rank the underlay would
  // paint over the satin.
  const design = kindedDesign([["satin"], ["underlay"]], [200, 10, 10]);
  const ctx = makeCallLog();
  renderRealistic({ width: 300, height: 220, getContext: () => ctx }, design, {});
  const cols = strokesOf(ctx).map((v) => v.color);
  const trueColour = "rgb(200,10,10)";                                   // satin's layer 2
  const underlayTrue = `rgb(${Math.round(200 * u.tone)},${Math.round(10 * u.tone)},${Math.round(10 * u.tone)})`;
  const iUnderlay = firstIndexOf(cols, (c) => c === underlayTrue);
  const iSatin = firstIndexOf(cols, (c) => c === trueColour);
  expect(iUnderlay).toBeGreaterThan(-1);
  expect(iSatin).toBeGreaterThan(-1);
  expect(iUnderlay).toBeLessThan(iSatin);
});

test("a border reads as RAISED: a deeper shadow than plain satin, cast ON the fill it encloses rather than under it", () => {
  // This is the whole answer to "I can't see the satin borders". A border is
  // not a different thread — it is the same thread standing proud of the fill,
  // sewn last and usually over its own underlay. So it gets the cue a raised
  // object gets in any photograph: a longer, darker drop shadow, plus a
  // crisper silhouette. No recolouring anywhere.
  const border = kindStyle("satin", "border");
  expect(border.shadow).toBeGreaterThan(kindStyle("satin", "").shadow);
  expect(border.rim).toBeLessThan(1);           // darker silhouette = crisper edge
  expect(border.z).toBeGreaterThan(kindStyle("satin", "").z); // drawn last in its block
  expect(kindStyle("satin", "edge_cap")).toMatchObject({ shadow: border.shadow, rim: border.rim });

  const design = kindedDesign([["fill"], ["satin", "border"]], [200, 10, 10]);
  const ctx = makeCallLog();
  renderRealistic({ width: 300, height: 220, getContext: () => ctx }, design, {});
  const strokes = strokesOf(ctx);
  const shadows = strokes.map((v) => alphaOf(v.color));
  const iFillPaint = firstIndexOf(strokes, (v) => v.color === "rgb(200,10,10)");
  const iRaisedShadow = firstIndexOf(shadows, (a) => a != null && a > 0.3);
  expect(iFillPaint).toBeGreaterThan(-1);
  // The raised shadow is drawn AFTER the fill: a shadow cast onto a fill has
  // to land on top of it. Left in the global pre-pass it would be painted over
  // by the very thing it is supposed to fall on.
  expect(iRaisedShadow).toBeGreaterThan(iFillPaint);
  // ...and it is deeper than the ordinary one that ran before everything.
  const preAlpha = shadows.find((a) => a != null);
  expect(preAlpha).toBeLessThan(shadows[iRaisedShadow]);
  expect(shadows[iRaisedShadow]).toBeLessThanOrEqual(0.42); // a shadow, never an outline
});

test("a bean run draws as a thin single line — narrower than the column kinds, never wider", () => {
  const run = kindStyle("run", "");
  expect(run.w).toBeLessThan(kindStyle("satin", "").w);
  expect(run.w).toBeLessThan(kindStyle("fill", "").w);
  const ctx = makeCallLog();
  drawThreads(ctx, [{ x0: 0, y0: 0, x1: 20, y1: 0, rgb: [200, 10, 10], kind: "run", role: "", shape: "b" }],
    (x) => x, (y) => y, 8, { layers: [0, 1, 2, 3, 4] });
  const widest = Math.max(...strokesOf(ctx).map((v) => v.width));
  expect(widest).toBeLessThan(8 * 1.04); // the shadow pass is the widest stroke
});

test("NO runs: the render is call-for-call what it was before kinds existed", () => {
  // The hard requirement. Every .embproj saved before 2026-09-15, every
  // imported .dst and the browser's own lettering/manual/shape lanes produce
  // designs with no `runs` at all, and they must render EXACTLY as they did.
  //
  // Byte-identity against the pre-change module was proven out of band over 12
  // renderRealistic configurations and 5 direct drawThreads widths (~380 KB of
  // recorded canvas calls, diffed to zero). What this pins in-suite is the
  // equivalence class around it: absent, empty and malformed `runs` are all
  // the same render, and so is a `runs` that says every stitch is a plain
  // stitch -- plus the two shadow-pass constants that identity rests on.
  const base = { stitches: [
    { x: 0, y: 0, type: "stitch" }, { x: 30, y: 10, type: "stitch" },
    { x: 60, y: -10, type: "stitch" }, { x: 60, y: -10, type: "trim" },
    { x: 90, y: 20, type: "stitch" }, { x: 120, y: 20, type: "stitch" },
  ], colors: [{ r: 200, g: 10, b: 10 }] };
  const render = (d) => {
    const ctx = makeCallLog();
    renderRealistic({ width: 300, height: 220, getContext: () => ctx }, d, {});
    return JSON.stringify(ctx.calls);
  };
  const reference = render(base);
  for (const runs of [undefined, null, [], "junk", [{ i0: NaN, i1: 3, kind: "satin" }]]) {
    expect(render({ ...base, runs })).toBe(reference);
  }
  // A span that says "plain stitch" IS the neutral style, not a near-miss.
  expect(render({ ...base, runs: [{ i0: 0, i1: 5, kind: "stitch", role: "", shape: "", block: 0 }] })).toBe(reference);

  // The single pre-pass those bytes depend on: ONE shadow path, at the
  // original opacity and the original 1.04 width multiple.
  const ctx = makeCallLog();
  renderRealistic({ width: 300, height: 220, getContext: () => ctx }, base, {});
  const strokes = strokesOf(ctx);
  const shadowStrokes = strokes.filter((v) => alphaOf(v.color) != null);
  expect(shadowStrokes.length).toBe(1);
  expect(shadowStrokes[0].color).toBe("rgba(0,0,0,0.22)");
  const lw = Math.max(1.2, 0.4 * (fitTransform(base, 300, 220, 24).scale * 10));
  expect(shadowStrokes[0].width).toBeCloseTo(lw * 1.04, 10);
});

test("FLAT view ignores kinds on purpose — it is the coverage answer, and coverage must not move between views", () => {
  // threadStyle 'flat' exists to answer "is this shape filled", with the
  // lighting gone. Thinning an underlay or a travel there would change the
  // coverage reading, so the flat path is deliberately untouched by kinds.
  const design = kindedDesign([["underlay"], ["fill"], ["satin", "border"]], [200, 10, 10]);
  const kinded = (() => { const c = makeCallLog(); renderRealistic({ width: 300, height: 220, getContext: () => c }, design, { threadStyle: "flat" }); return JSON.stringify(c.calls); })();
  const plain = (() => {
    const c = makeCallLog();
    const { runs, ...noRuns } = design;
    renderRealistic({ width: 300, height: 220, getContext: () => c }, noRuns, { threadStyle: "flat" });
    return JSON.stringify(c.calls);
  })();
  expect(kinded).toBe(plain);
});

test("the planner's OWN kind names are the ones this table answers to — including the three the contract sketch left out", () => {
  // digitizer_core/stitches.py is the vocabulary: underlay, fill, satin,
  // border, bean, run, travel, tie. `border` is a KIND there (a closed outline
  // circuit sewn as a satin column), not only a role, and `bean` is the light
  // outline tier's triple run — so a table that knew only satin/fill/run/
  // underlay/travel would have dropped the border strand to neutral. That
  // strand is the one Kent cannot see; getting it wrong would have been the
  // whole feature missing its target while every test stayed green.
  // Compared on APPEARANCE, not on `key` -- `key` is the draw-group identity,
  // so two kinds that look the same still group separately.
  const look = ({ key, ...rest }) => rest;
  expect(look(kindStyle("border", ""))).toEqual(look(kindStyle("satin", "")));
  expect(look(kindStyle("bean", ""))).toEqual(look(kindStyle("run", "")));
  // A tie is a 2 mm lock the following run sews over — drawn, but quietly.
  expect(kindStyle("tie", "").w).toBeLessThan(kindStyle("run", "").w);
  expect(kindStyle("tie", "").sheen).toBeLessThan(kindStyle("satin", "").sheen);
  // And the narrow-shape border fallback (BORDER -> BEAN, same role) still
  // reads as a border rather than as ordinary outline stitching.
  expect(kindStyle("bean", "border").shadow).toBeGreaterThan(kindStyle("bean", "").shadow);
});

test("a role does NOT raise a run that is underneath by nature — a border's bridge travel stays a connector", () => {
  // stage6_border.border_runs stamps role:"border" on the TRAVEL runs that
  // bridge to the ring, because they belong to that tier. They are still
  // travel: thread the design hides. Lifting them off the cloth with the
  // border's shadow would advertise exactly what should recede.
  const look = ({ key, ...rest }) => rest;
  expect(look(kindStyle("travel", "border"))).toEqual(look(kindStyle("travel", "")));
  expect(look(kindStyle("underlay", "border"))).toEqual(look(kindStyle("underlay", "")));
  expect(look(kindStyle("tie", "edge_cap"))).toEqual(look(kindStyle("tie", "")));
  // ...while the stitching that FORMS the border does stand proud.
  expect(kindStyle("border", "border").raised).toBe(true);
  expect(kindStyle("travel", "border").raised).toBe(false);
});

// ---- Thread appearance, 2026-11-07 ----------------------------------------
//
// Kent: "I want 2 agents working on UI embroidery simulation and appearance."
// Three things read wrong against sewn thread and are pinned here: the lit
// layers ran hole to hole (no crown on a satin column, no visible stagger in a
// tatami fill), a later colour cast no shadow on the colour it lies on, and a
// bean/run line drew nearly as heavy as a satin crossing. All of it is a LOOK;
// none of it claims to match cloth.

// A ctx double that keeps every path command with its coordinates, so the
// crown (where a layer starts and stops along its own strand) is visible.
function makePathLog() {
  const calls = [];
  let _ss, _lw;
  return {
    save() {}, restore() {}, setTransform() {}, closePath() {}, arcTo() {}, fillRect() {}, clip() {},
    setLineDash() {},
    beginPath: () => calls.push(["beginPath"]),
    moveTo: (x, y) => calls.push(["moveTo", x, y]),
    lineTo: (x, y) => calls.push(["lineTo", x, y]),
    stroke: () => calls.push(["stroke", _ss, _lw]),
    get strokeStyle() { return _ss; }, set strokeStyle(v) { _ss = v; },
    get lineWidth() { return _lw; }, set lineWidth(v) { _lw = v; },
    lineCap: "", lineJoin: "", fillStyle: "",
    calls,
  };
}
// The x-extent of each stroke() path, in order: [{ color, width, x0, x1 }].
function pathExtents(calls) {
  const out = [];
  let xs = [];
  for (const c of calls) {
    if (c[0] === "beginPath") xs = [];
    else if (c[0] === "moveTo" || c[0] === "lineTo") xs.push(c[1]);
    else if (c[0] === "stroke") out.push({ color: c[1], width: c[2], x0: Math.min(...xs), x1: Math.max(...xs) });
  }
  return out;
}

test("the crown: the silhouette runs hole to hole, and each lit layer pulls back further from both needle holes", () => {
  const L = threadLayers([200, 10, 10], 0, 10, kindStyle("satin", ""));
  expect(L[0].inset).toBe(0); // coverage is the silhouette's, and it is untouched
  for (let i = 1; i < L.length; i++) expect(L[i].inset).toBeGreaterThan(L[i - 1].inset);
  // the specular never reaches the middle from both sides (it is a crown,
  // not nothing): every layer keeps more than a third of its strand
  expect(L[L.length - 1].inset).toBeLessThan(1 / 3);
  // ...and drawThreads really draws it that way: one 100 px strand, the
  // silhouette spans all of it, the true colour less, the specular least.
  const ctx = makePathLog();
  drawThreads(ctx, [{ x0: 0, y0: 0, x1: 100, y1: 0, rgb: [200, 10, 10], kind: "satin", role: "", shape: "s" }],
    (x) => x, (y) => y, 10, { layers: [0, 1, 2, 3, 4] });
  const paint = pathExtents(ctx.calls).filter((p) => !/^rgba\(0,0,0,/.test(p.color));
  expect(paint.length).toBe(5);
  expect(paint[0].x0).toBe(0);
  expect(paint[0].x1).toBe(100);
  const span = (p) => p.x1 - p.x0;
  expect(span(paint[TRUE_COLOUR_LAYER])).toBeLessThan(100);
  expect(span(paint[TRUE_COLOUR_LAYER])).toBeGreaterThan(70); // the true colour is still most of the thread
  expect(span(paint[4])).toBeLessThan(span(paint[3]));
  expect(span(paint[3])).toBeLessThan(span(paint[TRUE_COLOUR_LAYER]));
  // centred: the crown is symmetric about the strand's middle
  expect((paint[3].x0 + paint[3].x1) / 2).toBeCloseTo(50, 0); // (the lit-side offset moves it a hair)
});

test("the crown is what breaks a tatami row at every penetration: two collinear stitches leave a gap in the highlight, never in the silhouette", () => {
  const ctx = makePathLog();
  const row = [
    { x0: 0, y0: 0, x1: 60, y1: 0, rgb: [200, 10, 10], kind: "fill", role: "", shape: "f" },
    { x0: 60, y0: 0, x1: 120, y1: 0, rgb: [200, 10, 10], kind: "fill", role: "", shape: "f" },
  ];
  drawThreads(ctx, row, (x) => x, (y) => y, 8, { layers: [0, 3] });
  // segments of each path, as [x0, x1] pairs
  const segs = [];
  let cur = null;
  for (const c of ctx.calls) {
    if (c[0] === "beginPath") { cur = []; segs.push(cur); }
    else if (c[0] === "moveTo") cur.push([c[1]]);
    else if (c[0] === "lineTo") cur[cur.length - 1].push(c[1]);
  }
  const [shadow, rim, spec] = segs;
  expect(shadow.length).toBe(2);
  expect(rim.map((s) => s.slice().sort((a, b) => a - b))).toEqual([[0, 60], [60, 120]]); // touch at the hole
  const hi = spec.map((s) => s.slice().sort((a, b) => a - b));
  expect(hi[0][1]).toBeLessThan(60); // the first stitch's highlight stops short of the hole...
  expect(hi[1][0]).toBeGreaterThan(60); // ...and the next one starts past it
});

test("thin and buried kinds crown less than the column kinds; the kindless stitch crowns like a column", () => {
  const c = (k) => kindStyle(k, "").crown;
  expect(c("satin")).toBe(1);
  expect(c("fill")).toBe(1);
  expect(c("stitch")).toBe(1);
  expect(c("run")).toBeLessThan(1);
  expect(c("underlay")).toBeLessThan(1);
  expect(c("travel")).toBeLessThan(c("underlay"));
  for (const k of ["satin", "fill", "run", "bean", "underlay", "tie", "travel", "border", "stitch", "unknown-kind"]) {
    expect(c(k)).toBeGreaterThanOrEqual(0);
    expect(c(k)).toBeLessThanOrEqual(1);
  }
});

test("a bean or run line reads visibly thinner than a satin crossing, not a hair thinner", () => {
  expect(kindStyle("run", "").w).toBeLessThanOrEqual(0.75 * kindStyle("satin", "").w);
  expect(kindStyle("bean", "").w).toBe(kindStyle("run", "").w);
  // and still above the buried kinds, so an outline is not mistaken for underlay
  expect(kindStyle("run", "").w).toBeGreaterThan(kindStyle("underlay", "").w);
});

test("contact shadow: a later colour casts its shadow ON the colour sewn before it, not under it", () => {
  const stitches = [
    { x: 0, y: 0, type: "stitch" }, { x: 40, y: 0, type: "stitch" }, { x: 40, y: 7, type: "stitch" },
    { x: 40, y: 7, type: "color" },
    { x: 10, y: 3, type: "stitch" }, { x: 30, y: 3, type: "stitch" }, { x: 30, y: 10, type: "stitch" },
    { x: 0, y: 0, type: "end" },
  ];
  const design = { stitches, colors: [{ r: 200, g: 10, b: 10 }, { r: 250, g: 250, b: 245 }] };
  const ctx = makeCallLog();
  renderRealistic({ width: 300, height: 220, getContext: () => ctx }, design, {});
  const strokes = strokesOf(ctx);
  const isShadow = (v) => alphaOf(v.color) != null;
  const iRedPaint = firstIndexOf(strokes, (v) => v.color === "rgb(200,10,10)");
  const iWhitePaint = firstIndexOf(strokes, (v) => v.color === "rgb(250,250,245)");
  const shadowIdx = strokes.map((v, i) => (isShadow(v) ? i : -1)).filter((i) => i >= 0);
  // one shadow per colour block, each right before its block
  expect(shadowIdx.length).toBe(2);
  expect(shadowIdx[0]).toBeLessThan(iRedPaint);
  expect(shadowIdx[1]).toBeGreaterThan(iRedPaint); // lands ON the red
  expect(shadowIdx[1]).toBeLessThan(iWhitePaint); // and under the white that casts it
});

test("the block's shadow is ONE path however many kinds the block holds (the measured cost ceiling), plus one per raised group", () => {
  // One path per style group was tried first and cost the mixed fixture +53%
  // at fit zoom: each alpha path is rasterized over its own bounds, and a
  // block's underlay, fill and satin share theirs. This pins the cheaper shape.
  const design = kindedDesign([["travel"], ["underlay"], ["fill"], ["satin"], ["satin", "border"]], [200, 10, 10]);
  const ctx = makeCallLog();
  renderRealistic({ width: 300, height: 220, getContext: () => ctx }, design, {});
  const shadows = strokesOf(ctx).map((v) => alphaOf(v.color)).filter((a) => a != null);
  expect(shadows.length).toBe(2);
  // the ordinary one at the topmost non-raised kind's strength (satin), the
  // raised one deeper
  expect(shadows[0]).toBe(Math.round(0.22 * kindStyle("satin", "").shadow * 1000) / 1000);
  expect(shadows[1]).toBeGreaterThan(shadows[0]);
});

test("buried kinds stay out of the block's shadow: an exposed travel run does not cast at fill strength", () => {
  const s = (x0, x1, kind) => ({ x0, y0: 0, x1, y1: 0, rgb: [200, 10, 10], kind, role: "", shape: "a" });
  const mixedBlock = [s(0, 20, "fill"), s(20, 40, "fill"), s(40, 90, "travel"), s(90, 110, "underlay")];
  const ctx = makePathLog();
  drawThreads(ctx, mixedBlock, (x) => x, (y) => y, 8, { layers: [0, 2] });
  // the shadow path is the first one stroked; count its subpaths
  let n = 0;
  for (const c of ctx.calls) {
    if (c[0] === "moveTo") n++;
    if (c[0] === "stroke") { expect(c[1]).toMatch(/^rgba\(0,0,0,/); break; }
  }
  expect(n).toBe(2); // the two fill strands only
  // ...while a block of buried kinds alone still casts, at its own strength
  const ctx2 = makePathLog();
  drawThreads(ctx2, [s(0, 50, "travel"), s(50, 90, "underlay")], (x) => x, (y) => y, 8, { layers: [0, 2] });
  const first = ctx2.calls.find((c) => c[0] === "stroke");
  expect(first[1]).toBe(`rgba(0,0,0,${Math.round(0.22 * kindStyle("underlay", "").shadow * 1000) / 1000})`);
});


const rec = () => {
  const calls = [];
  const ctx = new Proxy({}, { get: (_, k) => (k === "calls" ? calls : (...a) => { calls.push([k, ...a]); }), set: () => true });
  return { ctx, calls };
};
const g = { minor: "m", major: "M" };

test("draws minor then major lines through the hoop centre", () => {
  const { ctx, calls } = rec();
  drawGrid(ctx, 200, 200, 2, 100, 100, g); // 10 mm = 20 px
  expect(calls.filter((c) => c[0] === "stroke").length).toBe(2);
  expect(calls.some((c) => c[0] === "moveTo" && c[1] === 100.5)).toBe(true);
});

test("drops minor lines when zoomed far out", () => {
  const { ctx, calls } = rec();
  drawGrid(ctx, 200, 200, 0.2, 100, 100, g); // 10 mm = 2 px
  expect(calls.filter((c) => c[0] === "stroke").length).toBe(1);
});

// --- Simulator frames: the completed-block snapshot (2026-11-07) -----------
//
// A fake canvas whose ctx logs every stroke WITH its path, plus the blits,
// and which can make sibling canvases the way a real <canvas> can (through
// its ownerDocument) -- that is what turns the snapshot path on.
function simCanvas(w, h) {
  const made = [];
  const mk = () => {
    const strokes = [];
    const blits = [];
    let path = [], _ss, _lw, fills = 0, dash = [];
    const ctx = {
      save() {}, restore() {}, setTransform() {}, closePath() {}, clip() {}, arcTo() {}, fillText() {},
      beginPath() { path = []; },
      moveTo(x, y) { path.push(["M", x, y]); }, lineTo(x, y) { path.push(["L", x, y]); },
      stroke() { strokes.push({ color: _ss, width: _lw, dash: dash.slice(), path }); },
      fillRect() { fills++; },
      setLineDash(d) { dash = d.slice(); },
      drawImage(src) { blits.push(src); },
      get strokeStyle() { return _ss; }, set strokeStyle(v) { _ss = v; },
      get lineWidth() { return _lw; }, set lineWidth(v) { _lw = v; },
      get fills() { return fills; },
      strokes, blits,
    };
    const c = { width: w, height: h, getContext: () => ctx, ownerDocument: { createElement: () => { const k = mk(); made.push(k); return k; } } };
    return c;
  };
  const canvas = mk();
  canvas.made = made;
  return canvas;
}
// Three colour blocks of 30 stitches each, then a fourth still being sewn.
function blockyDesign() {
  const stitches = [];
  const colors = [];
  for (let b = 0; b < 4; b++) {
    if (b) stitches.push({ x: 0, y: 0, type: "color" });
    colors.push({ r: 40 + b * 50, g: 90, b: 200 - b * 40 });
    for (let i = 0; i < 30; i++) stitches.push({ x: b * 60 + (i % 2) * 40, y: i * 4, type: "stitch" });
  }
  stitches.push({ x: 0, y: 0, type: "end" });
  return { stitches, colors };
}
const SIM_OPTS = { hoop: { garment: { widthIn: 4, heightIn: 4 } }, fabricRgb: [235, 232, 223], view: { zoom: 2, panX: 10, panY: -5 } };

test("simulator frames: a later frame restores the completed blocks and strokes exactly what a fresh render strokes for the open block", () => {
  const design = blockyDesign();
  const live = simCanvas(400, 300);
  // Frame 1 lands in block 4: a full paint, and a snapshot of blocks 1-3.
  renderRealistic(live, design, { ...SIM_OPTS, limitStrands: 95 });
  expect(live.getContext().fills).toBe(1);
  expect(live.made.length).toBe(1);
  expect(live.made[0].getContext().blits).toEqual([live]);
  // Frame 2, one strand on: the snapshot comes back, nothing before the
  // open block is stroked again.
  const ctx = live.getContext();
  ctx.strokes.length = 0;
  renderRealistic(live, design, { ...SIM_OPTS, limitStrands: 100 });
  expect(ctx.fills).toBe(1); // no new fabric fill
  expect(ctx.blits).toEqual([live.made[0]]);
  const fresh = simCanvas(400, 300);
  renderRealistic(fresh, design, { ...SIM_OPTS, limitStrands: 100 });
  const all = fresh.getContext().strokes;
  expect(ctx.strokes.length).toBeGreaterThan(0);
  expect(ctx.strokes.length).toBeLessThan(all.length / 2);
  expect(ctx.strokes).toEqual(all.slice(all.length - ctx.strokes.length));
});

test("simulator frames: a changed view, a scrub back past the snapshot, or an ordinary render paints from the fabric", () => {
  const design = blockyDesign();
  const live = simCanvas(400, 300);
  const ctx = live.getContext();
  renderRealistic(live, design, { ...SIM_OPTS, limitStrands: 95 });
  renderRealistic(live, design, { ...SIM_OPTS, view: { zoom: 3, panX: 0, panY: 0 }, limitStrands: 96 });
  expect(ctx.fills).toBe(2);
  renderRealistic(live, design, { ...SIM_OPTS, view: { zoom: 3, panX: 0, panY: 0 }, limitStrands: 20 });
  expect(ctx.fills).toBe(3);
  expect(ctx.blits).toEqual([]);
  // No limitStrands: the plain path, which never makes a snapshot canvas.
  const plain = simCanvas(400, 300);
  renderRealistic(plain, design, SIM_OPTS);
  renderRealistic(plain, design, SIM_OPTS);
  expect(plain.made.length).toBe(0);
  expect(plain.getContext().fills).toBe(2);
});

// --- Shadows: always solid, soft once the thread is wide (2026-11-07) ------

// A logging ctx with the extras the soft path uses: per-stroke dash, blits,
// and the alpha a blit is drawn at.
function shadowLog() {
  const strokes = [], blits = [];
  let _ss, _lw, dash = [];
  const ctx = {
    save() {}, restore() {}, setTransform() {}, clearRect() {},
    beginPath() {}, moveTo() {}, lineTo() {},
    stroke() { strokes.push({ color: _ss, width: _lw, dash: dash.slice() }); },
    setLineDash(d) { dash = d.slice(); },
    drawImage(src, ...a) { blits.push({ src, alpha: ctx.globalAlpha, args: a }); },
    globalAlpha: 1, lineCap: "", lineJoin: "",
    get strokeStyle() { return _ss; }, set strokeStyle(v) { _ss = v; },
    get lineWidth() { return _lw; }, set lineWidth(v) { _lw = v; },
    strokes, blits,
  };
  return ctx;
}
const isShadow = (s) => /^rgba\(0,0,0,/.test(s.color || "");
const strand = (x0, x1, rgb, kind, role) => ({ x0, y0: 10, x1, y1: 10, rgb, kind: kind || "stitch", ...(role ? { role } : {}) });

test("every shadow is drawn SOLID: a later block's contact shadow no longer inherits the beaded specular's dash", () => {
  const ctx = shadowLog();
  const red = [200, 20, 20], blue = [20, 20, 200];
  drawThreads(ctx, [strand(0, 40, red), strand(5, 45, red), strand(10, 50, blue), strand(20, 60, blue, "satin", "border")],
    (x) => x, (y) => y, 4, { layers: [0, 1, 2, 3, 4] });
  const shadows = ctx.strokes.filter(isShadow);
  expect(shadows.length).toBe(3); // block red, block blue, the raised border
  for (const s of shadows) expect(s.dash).toEqual([]);
  // ...and the beaded layer is still dashed, so the reset is doing work.
  expect(ctx.strokes.some((s) => s.dash.length === 2)).toBe(true);
});

test("softShadowFactor: hard below 6 px of thread, then one step per 3 px, capped", () => {
  expect(softShadowFactor(1.2)).toBe(1);
  expect(softShadowFactor(5.9)).toBe(1);
  expect(softShadowFactor(6)).toBe(2);
  expect(softShadowFactor(9)).toBe(3);
  expect(softShadowFactor(400)).toBe(6);
});

test("soft shadow: wide thread casts through the scratch canvas (no full-res alpha stroke), at the hard shadow's opacity", () => {
  const scratchCtx = shadowLog();
  const scratch = { width: 200, height: 100, getContext: () => scratchCtx };
  const soft = { dpr: 1, cw: 400, ch: 200, scratch: () => scratch };
  const red = [200, 20, 20];
  const ctx = shadowLog();
  drawThreads(ctx, [strand(10, 90, red), strand(20, 120, red)], (x) => x, (y) => y, 9, { layers: [0, 2], softShadow: soft });
  expect(ctx.strokes.filter(isShadow)).toEqual([]);
  expect(ctx.blits.length).toBe(1);
  expect(ctx.blits[0].src).toBe(scratch);
  expect(ctx.blits[0].alpha).toBe(0.22);
  // The shadow path went to the scratch canvas, opaque.
  expect(scratchCtx.strokes.length).toBe(1);
  expect(scratchCtx.strokes[0].color).toBe("#000");
  // Thin thread with the same option: the ordinary hard shadow, unchanged.
  const thin = shadowLog();
  drawThreads(thin, [strand(10, 90, red)], (x) => x, (y) => y, 3, { layers: [0, 2], softShadow: soft });
  expect(thin.blits).toEqual([]);
  expect(thin.strokes.filter(isShadow).map((s) => s.color)).toEqual(["rgba(0,0,0,0.22)"]);
});

test("soft shadow: strands whose shadow lands wholly off the canvas are left out of its path", () => {
  const scratchCtx = shadowLog();
  let moves = 0;
  scratchCtx.moveTo = () => { moves++; };
  const scratch = { width: 200, height: 100, getContext: () => scratchCtx };
  const soft = { dpr: 1, cw: 400, ch: 200, scratch: () => scratch };
  const red = [200, 20, 20];
  drawThreads(shadowLog(), [strand(10, 90, red), strand(5000, 5100, red), strand(-900, -800, red)], (x) => x, (y) => y, 9,
    { layers: [0, 2], softShadow: soft });
  expect(moves).toBe(1);
});

test("satin over its OWN colour's fill casts a shadow onto it -- soft zoom only, so fit zoom keeps one shadow per block", () => {
  const scratch = { width: 200, height: 100, getContext: () => shadowLog() };
  const soft = { dpr: 1, cw: 400, ch: 200, scratch: () => scratch };
  const red = [200, 20, 20];
  const strands = [strand(10, 90, red, "fill"), strand(12, 92, red, "fill"), strand(30, 60, red, "satin"), strand(32, 62, red, "satin")];
  const wide = shadowLog();
  drawThreads(wide, strands, (x) => x, (y) => y, 9, { layers: [0, 2], softShadow: soft });
  expect(wide.blits.length).toBe(2); // the block's, then the satin's onto the fill
  const fit = shadowLog();
  drawThreads(fit, strands, (x) => x, (y) => y, 3, { layers: [0, 2], softShadow: soft });
  expect(fit.blits).toEqual([]);
  expect(fit.strokes.filter(isShadow).length).toBe(1);
  // A fill alone casts no extra shadow at any width.
  const fillOnly = shadowLog();
  drawThreads(fillOnly, strands.slice(0, 2), (x) => x, (y) => y, 9, { layers: [0, 2], softShadow: soft });
  expect(fillOnly.blits.length).toBe(1);
});
