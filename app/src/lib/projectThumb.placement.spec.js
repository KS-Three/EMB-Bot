// @vitest-environment jsdom
//
// The thumbnail of a project with SEVERAL digitized elements must show them
// where and how big the customer put them -- the same scale, offset and sew
// order generateAll gives the Studio -- not each service result stacked on
// one origin at its native size (#1344 post-merge review).
import { beforeAll, expect, test } from "vitest";
import { createRequire } from "node:module";

let projectDesign;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units", "garments", "fabrics", "fill", "geometry", "dst", "dstimport"]) require("../../../src/" + f + ".js");
  globalThis.EMB.buildLetteringDesign =
    globalThis.EMB.buildLetteringDesign || (() => { throw new Error("not used by this spec"); });
  ({ projectDesign } = await import("./projectThumb.js"));
});

// A filled square `side` units across in its own service frame, centred on
// (0, 0) like every service result, one colour.
function square(side, rgb) {
  const h = side / 2;
  const stitches = [];
  for (let y = -h; y <= h; y += side / 10) {
    stitches.push({ x: -h, y, type: "stitch" }, { x: h, y, type: "stitch" });
  }
  stitches.push({ x: h, y: h, type: "end" });
  return { stitches, colors: [{ r: rgb[0], g: rgb[1], b: rgb[2] }], widthMM: side / 10, heightMM: side / 10 };
}

// x/y extent (0.1 mm units) of the sewn stitches in colour block k.
function blockBox(design, k) {
  let block = 0, x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const s of design.stitches) {
    if (s.type === "color") { block++; continue; }
    if (s.type !== "stitch" || block !== k) continue;
    x0 = Math.min(x0, s.x); x1 = Math.max(x1, s.x);
    y0 = Math.min(y0, s.y); y1 = Math.max(y1, s.y);
  }
  return { w: x1 - x0, h: y1 - y0, cx: (x0 + x1) / 2, cy: (y0 + y1) / 2 };
}

test("two digitized elements sit side by side at the sizes the customer chose", () => {
  // Both service results came back 50 mm wide; the customer sized the badge
  // to 30 mm at x -40 and the wordmark to 100 mm at x +20.
  const project = {
    garmentId: "full_back",
    elements: [
      { id: "badge", type: "digitized", result: square(500, [200, 0, 0]), sizeMm: 30, offsetXMm: -40, offsetYMm: 0 },
      { id: "word", type: "digitized", result: square(500, [0, 0, 200]), sizeMm: 100, offsetXMm: 20, offsetYMm: 0 },
    ],
  };
  const d = projectDesign(project);
  const a = blockBox(d, 0), b = blockBox(d, 1);
  expect(a.w).toBeCloseTo(300, -1);
  expect(b.w).toBeCloseTo(1000, -1);
  expect(b.cx - a.cx).toBeCloseTo(600, -1); // 20 - (-40) = 60 mm apart
});

test("on a cap the thumbnail sews bottom-up like generateAll", () => {
  // listed top piece first; a cap sews the LOWER one first (+y is up)
  const project = {
    garmentId: "hat_front",
    elements: [
      { id: "top", type: "digitized", result: square(200, [200, 0, 0]), sizeMm: 20, offsetXMm: 0, offsetYMm: 15 },
      { id: "low", type: "digitized", result: square(200, [0, 0, 200]), sizeMm: 20, offsetXMm: 0, offsetYMm: -15 },
    ],
  };
  const d = projectDesign(project);
  expect(blockBox(d, 0).cy).toBeLessThan(blockBox(d, 1).cy);
});
