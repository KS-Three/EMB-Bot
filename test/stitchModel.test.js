const assert = require("node:assert");
const { test } = require("node:test");
const m = require("../src/stitchModel.js");

const two = [
  { rgb:[255,0,0], polygons:[[{x:0,y:0},{x:100,y:0},{x:100,y:100},{x:0,y:100}]] },
  { rgb:[0,0,255], polygons:[[{x:120,y:0},{x:200,y:0},{x:200,y:80},{x:120,y:80}]] },
];

test("builds a design with 2 colors and one color change", () => {
  const d = m.buildDesign(two, { garment:{widthIn:4,heightIn:4}, densityMm:0.5, outline:false, pxPerMm:10 });
  assert.strictEqual(d.colorCount, 2);
  assert.strictEqual(d.colors.length, 2);
  assert.strictEqual(d.stitches.filter(s=>s.type==="color").length, 1);
  assert.strictEqual(d.stitches[d.stitches.length-1].type, "end");
  assert.ok(d.stitchCount > 0);
});
test("design fits inside garment box", () => {
  const d = m.buildDesign(two, { garment:{widthIn:4,heightIn:4}, densityMm:0.5, outline:false, pxPerMm:10 });
  assert.ok(d.widthMM <= 4*25.4 + 1e-6 && d.heightMM <= 4*25.4 + 1e-6);
});
test("coordinates centered near origin", () => {
  const d = m.buildDesign(two, { garment:{widthIn:12,heightIn:12}, densityMm:0.5, outline:false, pxPerMm:10 });
  const xs = d.stitches.filter(s=>s.type==="stitch").map(s=>s.x);
  const mid = (Math.max(...xs)+Math.min(...xs))/2;
  assert.ok(Math.abs(mid) < 30); // roughly centered (DST units)
});
test("max stitch length honored in final physical mm regardless of fit scale", () => {
  // Small 20x20 px square (pxPerMm:10 => 2mm) scaled UP into a 4in garment (fit.scale ~= 5x).
  const small = [
    { rgb:[0,0,0], polygons:[[{x:0,y:0},{x:20,y:0},{x:20,y:20},{x:0,y:20}]] },
  ];
  const d = m.buildDesign(small, { garment:{widthIn:4,heightIn:4}, densityMm:0.5, maxStitchMm:4.0, outline:false, pxPerMm:10 });
  // maxStitch honored in FINAL space within 5% tolerance (DST units = 0.1mm).
  const limit = 4.0 * 10 * 1.05;
  const s = d.stitches;
  for (let i = 1; i < s.length; i++) {
    const a = s[i-1], b = s[i];
    // Only consecutive real stitches; skip color/jump/end and pairs spanning a jump.
    if (a.type !== "stitch" || b.type !== "stitch") continue;
    const gap = Math.hypot(b.x - a.x, b.y - a.y);
    assert.ok(gap <= limit, `gap ${gap.toFixed(1)} DST exceeds ${limit.toFixed(1)}`);
  }
  // Design still fits the garment box (unchanged).
  assert.ok(d.widthMM <= 4*25.4 + 1e-6 && d.heightMM <= 4*25.4 + 1e-6);
});

// ---- edge cases: empty design, empty regions, colour changes, huge counts ----

const base = { garment: { widthIn: 4, heightIn: 4 }, densityMm: 0.5, outline: false, pxPerMm: 10 };
const sq = (x, y, s) => [{ x, y }, { x: x + s, y }, { x: x + s, y: y + s }, { x, y: y + s }];

test("empty design (no regions) yields just an end marker", () => {
  const d = m.buildDesign([], base);
  assert.deepStrictEqual(d.stitches, [{ x: 0, y: 0, type: "end" }]);
  assert.strictEqual(d.stitchCount, 0);
  assert.strictEqual(d.colorCount, 0);
  assert.deepStrictEqual(d.colors, []);
  assert.ok(Number.isFinite(d.widthMM) && Number.isFinite(d.heightMM));
});

test("regions with no geometry still count as colours but emit no stitches or colour change", () => {
  const regions = [
    { rgb: [1, 2, 3], polygons: [] },
    { rgb: [4, 5, 6] },
    { rgb: [7, 8, 9], polygons: [[{ x: 0, y: 0 }]] }, // 1-point polygon: no geometry
  ];
  const d = m.buildDesign(regions, base);
  assert.strictEqual(d.colorCount, 3);
  assert.strictEqual(d.colors.length, 3);
  assert.deepStrictEqual(d.stitches, [{ x: 0, y: 0, type: "end" }]);
  assert.strictEqual(d.stitchCount, 0);
});

test("colour names and rgb default sensibly", () => {
  const d = m.buildDesign([{ polygons: [sq(0, 0, 100)] }, { rgb: [9, 8, 7], polygons: [] }], base);
  assert.deepStrictEqual(d.colors[0], { r: 0, g: 0, b: 0, name: "Color 1" });
  assert.deepStrictEqual(d.colors[1], { r: 9, g: 8, b: 7, name: "Color 2" });
});

test("an empty region between two real ones adds no extra colour change", () => {
  const regions = [
    { rgb: [255, 0, 0], polygons: [sq(0, 0, 100)] },
    { rgb: [0, 255, 0], polygons: [] },
    { rgb: [0, 0, 255], polygons: [sq(150, 0, 100)] },
  ];
  const d = m.buildDesign(regions, base);
  assert.strictEqual(d.colorCount, 3);
  assert.strictEqual(d.stitches.filter((s) => s.type === "color").length, 1);
});

test("a leading empty region does not make the first real region emit a colour change", () => {
  const d = m.buildDesign(
    [{ rgb: [0, 0, 0], polygons: [] }, { rgb: [255, 0, 0], polygons: [sq(0, 0, 100)] }],
    base
  );
  assert.strictEqual(d.stitches.filter((s) => s.type === "color").length, 0);
  assert.strictEqual(d.colorCount, 2);
});

test("N real regions give N-1 colour changes, each at the next region's first stitch", () => {
  const n = 6;
  const regions = Array.from({ length: n }, (_, i) => ({
    rgb: [i * 10, 0, 0],
    polygons: [sq(i * 150, 0, 100)],
  }));
  const d = m.buildDesign(regions, base);
  const s = d.stitches;
  const idx = s.map((p, i) => (p.type === "color" ? i : -1)).filter((i) => i >= 0);
  assert.strictEqual(idx.length, n - 1);
  for (const i of idx) {
    assert.ok(i > 0 && i < s.length - 1);
    // marker sits on the point that follows it
    assert.strictEqual(s[i].x, s[i + 1].x);
    assert.strictEqual(s[i].y, s[i + 1].y);
  }
});

test("end marker repeats the last position; stitchCount counts only type stitch", () => {
  const d = m.buildDesign(two, base);
  const s = d.stitches;
  const last = s[s.length - 2];
  assert.deepStrictEqual(s[s.length - 1], { x: last.x, y: last.y, type: "end" });
  assert.strictEqual(d.stitchCount, s.filter((p) => p.type === "stitch").length);
  assert.strictEqual(s.filter((p) => p.type === "end").length, 1);
});

test("a far-apart region is reached by a colour marker, not a jump (jump detection is per region)", () => {
  const d = m.buildDesign(
    [{ rgb: [0, 0, 0], polygons: [sq(0, 0, 50)] }, { rgb: [1, 1, 1], polygons: [sq(2000, 0, 50)] }],
    { ...base, garment: { widthIn: 12, heightIn: 12 } }
  );
  assert.strictEqual(d.stitches.filter((p) => p.type === "color").length, 1);
  assert.ok(!d.stitches.some((p) => p.type === "jump"));
});

test("outline adds stitches without adding colour changes", () => {
  const plain = m.buildDesign(two, base);
  const out = m.buildDesign(two, { ...base, outline: true });
  assert.ok(out.stitchCount > plain.stitchCount);
  assert.strictEqual(out.stitches.filter((s) => s.type === "color").length, 1);
});

test("degenerate zero-area geometry (a point, a vertical line) does not throw or yield NaN", () => {
  for (const polys of [[[{ x: 5, y: 5 }, { x: 5, y: 5 }]], [[{ x: 5, y: 0 }, { x: 5, y: 80 }]]]) {
    const d = m.buildDesign([{ rgb: [0, 0, 0], polygons: polys }], base);
    for (const s of d.stitches) assert.ok(Number.isFinite(s.x) && Number.isFinite(s.y));
    assert.strictEqual(d.stitches[d.stitches.length - 1].type, "end");
  }
});

test("huge artwork is scaled down to the garment box with finite coordinates", () => {
  const d = m.buildDesign(
    [{ rgb: [0, 0, 0], polygons: [sq(0, 0, 1e6)] }],
    { ...base, densityMm: 2, maxStitchMm: 4, pxPerMm: 1e4 }
  );
  assert.ok(d.widthMM <= 4 * 25.4 + 1e-6 && d.heightMM <= 4 * 25.4 + 1e-6);
  for (const s of d.stitches) assert.ok(Number.isFinite(s.x) && Number.isFinite(s.y));
  assert.ok(d.stitchCount > 0);
});

test("many regions (200) keep one colour entry each and N-1 changes", () => {
  const regions = Array.from({ length: 200 }, (_, i) => ({
    rgb: [i % 256, 0, 0],
    polygons: [sq((i % 20) * 120, Math.floor(i / 20) * 120, 100)],
  }));
  const d = m.buildDesign(regions, { ...base, garment: { widthIn: 12, heightIn: 12 }, densityMm: 1 });
  assert.strictEqual(d.colors.length, 200);
  assert.strictEqual(d.colorCount, 200);
  assert.strictEqual(d.stitches.filter((s) => s.type === "color").length, 199);
});
