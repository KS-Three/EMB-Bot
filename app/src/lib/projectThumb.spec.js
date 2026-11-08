// @vitest-environment jsdom
//
// projectThumb: stitches -> 96 px data URL, cached by saved revision.
// The speed test drives the REAL renderRealistic against a no-op 2D context
// (jsdom has no canvas), so it prices the renderer's own per-stitch work --
// not the browser rasteriser, which the e2e/browser measurement in the PR
// covers.
import { beforeEach, expect, test, vi } from "vitest";
import { getThumb, projectDesign, drawThumb, thinForThumb, clearThumbCache, thumbKey, THUMB_PX } from "./projectThumb.js";

// A context that accepts any call or assignment and answers with itself.
function nullCtx() {
  const fn = function () { return proxy; };
  const store = {};
  const proxy = new Proxy(fn, {
    get: (_t, k) => (k in store ? store[k] : k === Symbol.toPrimitive ? () => 0 : proxy),
    set: (_t, k, v) => { store[k] = v; return true; },
    apply: () => proxy,
  });
  return proxy;
}

let drawn;
beforeEach(() => {
  clearThumbCache();
  drawn = 0;
  HTMLCanvasElement.prototype.getContext = function () { return nullCtx(); };
  HTMLCanvasElement.prototype.toDataURL = () => { drawn++; return "data:image/png;base64,AAAA"; };
});

// n sewn stitches along a wobbly spiral, two colour blocks, 0.1 mm units.
function bigDesign(n) {
  const stitches = [];
  for (let i = 0; i < n; i++) {
    if (i === Math.floor(n / 2)) stitches.push({ x: 0, y: 0, type: "color" });
    const a = i * 0.05;
    const r = 5 + i * 0.008;
    stitches.push({ x: Math.round(Math.cos(a) * r), y: Math.round(Math.sin(a) * r), type: "stitch" });
  }
  return { stitches, colors: [{ rgb: [200, 30, 30] }, { rgb: [30, 30, 200] }], widthMM: 40, heightMM: 40 };
}
const projectWith = (result) => ({ elements: [{ id: "e1", type: "digitized", result }] });

test("a project with no baked stitches has no design, so no draw", () => {
  expect(projectDesign({ elements: [{ id: "e1", type: "text" }] })).toBeNull();
  expect(projectDesign(projectWith({ stitches: [{ x: 0, y: 0, type: "trim" }] }))).toBeNull();
  expect(projectDesign(null)).toBeNull();
  const url = getThumb({ id: "p", updatedAt: 1 }, () => ({ elements: [] }));
  expect(url).toBeNull();
  expect(drawn).toBe(0);
});

test("the thumbnail is cached by saved revision: same revision draws once, a new one redraws", () => {
  const load = vi.fn(() => projectWith(bigDesign(200)));
  const a1 = getThumb({ id: "p", updatedAt: 5 }, load);
  const a2 = getThumb({ id: "p", updatedAt: 5 }, load);
  expect(a1).toMatch(/^data:image\/png/);
  expect(a2).toBe(a1);
  expect(drawn).toBe(1);
  expect(load).toHaveBeenCalledTimes(1);
  getThumb({ id: "p", updatedAt: 6 }, load);
  expect(drawn).toBe(2);
  expect(thumbKey("p", 6)).toBe("p:6");
});

test("a 20k-stitch project thumbnail builds in <= 120 ms", () => {
  const project = projectWith(bigDesign(20000));
  drawThumb(projectDesign(project)); // warm the JIT like a second drawer row would
  clearThumbCache();
  const load = () => project;
  const t0 = performance.now();
  const url = getThumb({ id: "big", updatedAt: 1 }, load);
  const ms = performance.now() - t0;
  console.log(`20k-stitch thumbnail build: ${ms.toFixed(1)} ms`);
  expect(url).toMatch(/^data:image\/png/);
  expect(ms).toBeLessThanOrEqual(120);
  expect(THUMB_PX).toBe(96);
});

test("thinning drops sub-pixel stitches but keeps colour/trim records, run ends and the bbox", () => {
  // 12k stitches drifting slowly across a 20 mm box (200 units): sub-pixel steps.
  const stitches = [{ x: 0, y: 0, type: "stitch" }];
  for (let i = 1; i < 12000; i++) {
    if (i === 6000) { stitches.push({ x: 0, y: 0, type: "trim" }, { x: 0, y: 0, type: "color" }); }
    stitches.push({ x: Math.round(100 + 100 * Math.sin(i / 3000)), y: Math.round(100 + 100 * Math.cos(i / 3700)), type: "stitch" });
  }
  stitches.push({ x: 200, y: 200, type: "stitch" });
  const design = { stitches, colors: [{}, {}], runs: [{ i0: 0, i1: 5 }] };
  const thin = thinForThumb(design);
  expect(thin.stitches.length).toBeLessThan(stitches.length);
  expect(thin.runs).toBeUndefined();
  expect(thin.stitches.filter((s) => s.type === "color").length).toBe(1);
  expect(thin.stitches.filter((s) => s.type === "trim").length).toBe(1);
  expect(thin.stitches[thin.stitches.length - 1]).toEqual({ x: 200, y: 200, type: "stitch" });
  // small designs pass through untouched
  const small = { stitches: stitches.slice(0, 50), colors: [{}] };
  expect(thinForThumb(small)).toBe(small);
});
