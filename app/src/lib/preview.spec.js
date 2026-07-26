import { test, expect, vi } from "vitest";
import { fitTransform, hoopTransform, luminance, isDark, weavePattern, drawHoopOutline, renderRealistic } from "./preview.js";

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
