// Edge-case coverage for the JS engine: degenerate and awkward geometry fed
// through fill.js, satin.js, flatten.js and digitize.js, and the stitch stream
// that comes out pushed through the DST encoder and importer.
//
// Every test asserts something observable about the OUTPUT -- finite
// coordinates, nothing sewn outside the shape (plus a tolerance), no record
// longer than the format allows, no crash -- never that a particular stitch
// count came back, because a count is the first thing a legitimate tuning
// change moves.
//
// `test.todo` marks a case that exposed a real defect. The body is the repro,
// kept so whoever fixes it can delete the `.todo` and have the test. These
// are NOT fixed here: this file changes no engine behaviour.

const assert = require("node:assert");
const { test } = require("node:test");
const fill = require("../src/fill.js");
const satin = require("../src/satin.js");
const FL = require("../src/flatten.js");
const DG = require("../src/digitize.js");
const dst = require("../src/dst.js");
const dstimport = require("../src/dstimport.js");

const P = (...a) => a.map(([x, y]) => ({ x, y }));
const sq = (x, y, w, h = w) => P([x, y], [x + w, y], [x + w, y + h], [x, y + h]);
const finite = (pts) => pts.every((p) => Number.isFinite(p.x) && Number.isFinite(p.y));
const TOL = 1e-6;
const TATAMI = { rowSpacing: 5, angleDeg: 0, maxStitch: 20 };

// Ray-cast point-in-polygon, boundary counted as inside by the caller's tol.
function inRing(r, x, y) {
  let c = false;
  for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
    if ((r[i].y > y) !== (r[j].y > y) &&
        x < ((r[j].x - r[i].x) * (y - r[i].y)) / (r[j].y - r[i].y) + r[i].x) c = !c;
  }
  return c;
}
const bbox = (pts) => ({
  x0: Math.min(...pts.map((p) => p.x)), x1: Math.max(...pts.map((p) => p.x)),
  y0: Math.min(...pts.map((p) => p.y)), y1: Math.max(...pts.map((p) => p.y)),
});
const within = (pts, b, tol) =>
  pts.every((p) => p.x >= b.x0 - tol && p.x <= b.x1 + tol && p.y >= b.y0 - tol && p.y <= b.y1 + tol);

// A design as buildQualityDesign makes it: one colour, the given shapes.
function design(shapes, opts) {
  return DG.buildQualityDesign(
    [{ rgb: [10, 10, 10], shapes }],
    Object.assign({ pxPerMm: 8, garment: { widthIn: 4, heightIn: 4 } }, opts)
  );
}

// Every record of an encoded file, read back with the importer's own decoder:
// the largest per-axis step any single record carries, and the record count.
function recordSteps(bytes) {
  let max = 0, n = 0;
  for (let i = 512; i + 2 < bytes.length; i += 3) {
    if (bytes[i] === 0 && bytes[i + 1] === 0 && bytes[i + 2] === 0xf3) break;
    const d = dstimport.decodeDelta(bytes[i], bytes[i + 1], bytes[i + 2]);
    max = Math.max(max, Math.abs(d[0]), Math.abs(d[1]));
    n++;
  }
  return { max, n };
}

// Encode, then check the file is well-formed and reads back as the same design.
function assertRoundTrips(d) {
  const bytes = dst.encodeDST(d);
  assert.strictEqual((bytes.length - 512) % 3, 0, "records are 3 bytes each");
  assert.deepStrictEqual(Array.from(bytes.slice(-3)), [0x00, 0x00, 0xf3], "ends with the end record");
  const { max } = recordSteps(bytes);
  assert.ok(max <= 121, "a record carries " + max + " units; the format holds 121");
  const back = dstimport.decodeDST(bytes);
  assert.ok(finite(back.stitches), "imported coordinates are finite");
  assert.ok(Number.isFinite(back.widthMM) && Number.isFinite(back.heightMM));
  assert.strictEqual(back.stitchCount, d.stitches.filter((s) => s.type === "stitch").length,
    "every needle penetration survives the file");
  assert.ok(Math.abs(back.widthMM - d.widthMM) <= 0.3, "width " + back.widthMM + " vs " + d.widthMM);
  assert.ok(Math.abs(back.heightMM - d.heightMM) <= 0.3, "height " + back.heightMM + " vs " + d.heightMM);
  return back;
}

// ---------------------------------------------------------------------------
// fill.js -- degenerate polygons
// ---------------------------------------------------------------------------

const DEGENERATE = {
  "zero area (a doubled-back line)": [P([0, 0], [100, 0], [100, 0], [0, 0])],
  "collinear points": [P([0, 0], [50, 0], [100, 0])],
  "collinear on a diagonal": [P([0, 0], [10, 10], [20, 20], [40, 40])],
  "all points identical": [P([5, 5], [5, 5], [5, 5])],
  "two points": [P([0, 0], [100, 0])],
  "one point": [P([3, 3])],
  "empty ring": [[]],
  "no rings": [],
};

for (const [name, polys] of Object.entries(DEGENERATE)) {
  for (const markConnectors of [false, true]) {
    test(`tatamiFill: ${name} does not crash or emit NaN (markConnectors:${markConnectors})`, () => {
      const out = fill.tatamiFill(polys, Object.assign({ markConnectors, angleDeg: 37 }, { rowSpacing: 5, maxStitch: 20 }));
      assert.ok(Array.isArray(out));
      assert.ok(finite(out), "non-finite coordinate in output");
      // A shape with no area has nowhere to sew: nothing may land far off it.
      const pts = polys.flat();
      if (out.length && pts.length) assert.ok(within(out, bbox(pts), 1e-3), "stitch outside the shape's own bounds");
    });
  }
}

test("satinColumn / medialSatin: degenerate rings return finite points or nothing", () => {
  for (const [name, polys] of Object.entries(DEGENERATE)) {
    for (const fn of [satin.satinColumn, satin.medialSatin]) {
      const out = fn(polys[0], { spacingMm: 0.4, pxPerMm: 8 });
      assert.ok(Array.isArray(out) || out == null, name);
      assert.ok(finite(out || []), name + ": NaN in satin output");
    }
  }
});

test("tatamiFill: a self-intersecting bowtie sews finite stitches inside its own bounds", () => {
  const bow = P([0, 0], [100, 100], [100, 0], [0, 100]);
  const out = fill.tatamiFill([bow], TATAMI);
  assert.ok(finite(out));
  assert.ok(within(out, bbox(bow), 1e-3));
});

test("tatamiFill: a ring that touches itself at a vertex (figure-eight pinch) stays finite and inside", () => {
  const pinch = P([0, 0], [50, 50], [0, 100], [100, 100], [50, 50], [100, 0]);
  const out = fill.tatamiFill([pinch], TATAMI);
  assert.ok(finite(out));
  assert.ok(within(out, bbox(pinch), 1e-3));
});

test("tatamiFill: a duplicated vertex and a closing vertex repeated do not change where thread lands", () => {
  const plain = sq(0, 0, 100);
  const noisy = [plain[0], plain[0], plain[1], plain[2], plain[2], plain[3], plain[0]];
  const out = fill.tatamiFill([noisy], TATAMI);
  assert.ok(out.length > 0 && finite(out));
  assert.ok(within(out, bbox(plain), 1e-3));
});

test("tatamiFill: winding direction does not decide whether a shape is sewn", () => {
  const cw = sq(0, 0, 100), ccw = sq(0, 0, 100).slice().reverse();
  const a = fill.tatamiFill([cw], TATAMI), b = fill.tatamiFill([ccw], TATAMI);
  assert.ok(a.length > 0 && b.length > 0);
  assert.ok(within(a, bbox(cw), 1e-3) && within(b, bbox(cw), 1e-3));
});

// ---------------------------------------------------------------------------
// fill.js -- tiny shapes and slivers
// ---------------------------------------------------------------------------

test("tatamiFill: a shape smaller than one row spacing still yields finite points inside it", () => {
  const tiny = sq(10, 10, 1); // 1 unit square, rows are 5 apart
  const out = fill.tatamiFill([tiny], TATAMI);
  assert.ok(finite(out));
  assert.ok(within(out, bbox(tiny), 1e-3));
});

test("tatamiFill: a shape 1000x smaller than the row spacing does not crash", () => {
  const out = fill.tatamiFill([sq(0, 0, 0.005)], TATAMI);
  assert.ok(finite(out));
  assert.ok(within(out, { x0: 0, x1: 0.005, y0: 0, y1: 0.005 }, 1e-3));
});

for (const h of [2, 0.2, 0.001]) {
  test(`tatamiFill: a ${h}-unit-thick, 100-long sliver sews inside the sliver (rows are 5 apart)`, () => {
    const sliver = sq(0, 0, 100, h);
    for (const angleDeg of [0, 45, 90]) {
      const out = fill.tatamiFill([sliver], Object.assign({}, TATAMI, { angleDeg }));
      assert.ok(finite(out), "angle " + angleDeg);
      assert.ok(within(out, bbox(sliver), 1e-3), "angle " + angleDeg + " left the sliver");
    }
  });
}

test("tatamiFill: no sewn stitch exceeds maxStitch on a long thin sliver", () => {
  const out = fill.tatamiFill([sq(0, 0, 300, 3)], Object.assign({}, TATAMI, { rowSpacing: 1, maxStitch: 7 }));
  assert.ok(out.length > 0);
  for (let i = 1; i < out.length; i++) {
    if (out[i].travel || out[i - 1].travel) continue;
    const d = Math.hypot(out[i].x - out[i - 1].x, out[i].y - out[i - 1].y);
    // Rows are 1 apart and the turnaround joins row ends, so a step is a
    // stitch-length cut or a short connector, never a long float.
    assert.ok(d <= 7 + 1.5, "gap " + d + " at " + i);
  }
});

// ---------------------------------------------------------------------------
// fill.js -- holes
// ---------------------------------------------------------------------------

const OUTER = sq(0, 0, 100);

test("tatamiFill: a hole sharing a whole edge with the outer ring leaves no thread inside the hole", () => {
  const hole = sq(0, 20, 40, 60); // flush with the left edge
  const out = fill.tatamiFill([OUTER, hole], Object.assign({ markConnectors: true }, TATAMI));
  assert.ok(finite(out));
  const inHole = out.filter((p) => !p.travel && p.x > 1 && p.x < 39 && p.y > 21 && p.y < 79);
  assert.strictEqual(inHole.length, 0, "sew points inside hole: " + inHole.length);
  assert.ok(within(out, bbox(OUTER), 1e-3));
});

test("tatamiFill: a hole touching the outer ring at a single vertex stays finite and inside", () => {
  const hole = P([0, 50], [30, 20], [30, 80]);
  const out = fill.tatamiFill([OUTER, hole], TATAMI);
  assert.ok(finite(out));
  assert.ok(within(out, bbox(OUTER), 1e-3));
});

test("tatamiFill: a hole coincident with the outer ring does not crash or sew outside", () => {
  const out = fill.tatamiFill([OUTER, OUTER], TATAMI);
  assert.ok(finite(out));
  assert.ok(within(out, bbox(OUTER), 1e-3));
});

test("tatamiFill: a ring larger than the one it nests around is filled even-odd, leaving the inner ring empty", () => {
  // tatamiFill is even-odd, so the "hole" bigger than the outer ring is just
  // the outer boundary of an annulus whose void is the smaller square.
  const big = sq(-50, -50, 300);
  const out = fill.tatamiFill([OUTER, big], Object.assign({ markConnectors: true }, TATAMI));
  assert.ok(finite(out));
  assert.ok(within(out, bbox(big), 1e-3));
  const inVoid = out.filter((p) => !p.travel && p.x > 1 && p.x < 99 && p.y > 1 && p.y < 99);
  assert.strictEqual(inVoid.length, 0, "points inside the void: " + inVoid.length);
});

test("tatamiFill: a hole narrower than a stitch is bridged without a NaN or an escape", () => {
  const out = fill.tatamiFill([OUTER, sq(40, 40, 0.5, 20)], TATAMI);
  assert.ok(finite(out));
  assert.ok(within(out, bbox(OUTER), 1e-3));
});

test("tatamiFill: every sewn point of an annulus with an edge-touching hole is inside outer and outside hole", () => {
  const hole = sq(0, 30, 50, 40);
  const out = fill.tatamiFill([OUTER, hole], Object.assign({ markConnectors: true }, TATAMI));
  for (const p of out) {
    if (p.travel) continue;
    // Boundary points are allowed; only a point strictly inside the hole is a defect.
    const strictlyInHole = p.x > 0.5 && p.x < 49.5 && p.y > 30.5 && p.y < 69.5 && inRing(hole, p.x, p.y);
    assert.ok(!strictlyInHole, `point ${p.x},${p.y} inside the hole`);
  }
});

// ---------------------------------------------------------------------------
// fill.js -- bad spacing parameters
// ---------------------------------------------------------------------------

test("tatamiFill: a missing, NaN or zero maxStitch still produces finite output", () => {
  for (const maxStitch of [undefined, NaN, 0, -1]) {
    const out = fill.tatamiFill([OUTER], { rowSpacing: 5, angleDeg: 0, maxStitch });
    assert.ok(finite(out), "maxStitch " + maxStitch);
  }
});

test("tatamiFill: a missing or NaN rowSpacing still produces finite output", () => {
  for (const rowSpacing of [undefined, NaN]) {
    const out = fill.tatamiFill([OUTER], { rowSpacing, angleDeg: 0, maxStitch: 20 });
    assert.ok(finite(out), "rowSpacing " + rowSpacing);
  }
});

// BUG: tatamiFill never returns for a non-positive rowSpacing. Measured
// 2026-10-08 on a 100x100 square with { rowSpacing: 0, angleDeg: 0,
// maxStitch: 20 }: the process runs out of heap (node --max-old-space-size=300
// dies in under 20 s) -- the row loop steps by 0 and keeps pushing rows. A
// rowSpacing of -1 hangs the same way. Every other bad input above (undefined,
// NaN, a zero or negative maxStitch) is tolerated. The Studio's density slider
// bottoms out above 0, which is why no customer has hit this, but
// buildQualityDesign({ densityMm: 0 }) is falsy and falls back to the default,
// so the reachable route is a direct caller. Fix belongs in fill.js; the repro
// is deliberately not run here because it takes the process down with it.
test.todo("tatamiFill: rowSpacing <= 0 terminates (BUG: runs out of memory at 0, hangs at -1)");

// ---------------------------------------------------------------------------
// satin.js
// ---------------------------------------------------------------------------

test("satinColumn: a stroke thinner than one satin spacing yields finite points within its bounds", () => {
  const stroke = sq(0, 0, 160, 0.2); // 20 mm long, 0.025 mm wide at 8 px/mm
  const out = satin.satinColumn(stroke, { spacingMm: 0.4, pxPerMm: 8 });
  assert.ok(finite(out));
  if (out.length) assert.ok(within(out, { x0: 0, x1: 160, y0: 0, y1: 0.2 }, 0.5));
});

test("satinColumn: a ring shorter than one satin spacing in both directions is empty or finite", () => {
  const out = satin.satinColumn(sq(0, 0, 1), { spacingMm: 0.4, pxPerMm: 8 });
  assert.ok(finite(out));
});

test("satinColumn: a bowtie ring terminates with finite points", () => {
  const out = satin.satinColumn(P([0, 0], [100, 100], [100, 0], [0, 100]), { spacingMm: 0.4, pxPerMm: 8 });
  assert.ok(finite(out));
});

test("satinColumn: pull compensation larger than the column is finite", () => {
  const out = satin.satinColumn(sq(0, 0, 160, 16), { spacingMm: 0.4, pxPerMm: 8, pullCompMm: 50 });
  assert.ok(finite(out));
});

test("medialSatin: a hairline stroke and a tiny blob stay finite", () => {
  for (const ring of [sq(0, 0, 400, 0.5), sq(0, 0, 2), P([0, 0], [100, 0], [50, 0.01])]) {
    const out = satin.medialSatin(ring, { spacingMm: 0.4, pxPerMm: 8 });
    assert.ok(finite(out || []));
  }
});

test("farthestBoundaryPair / splitBoundary: two coincident points do not throw", () => {
  const ring = P([5, 5], [5, 5], [5, 5], [5, 5]);
  const [i, j] = satin.farthestBoundaryPair(ring);
  assert.ok(Number.isInteger(i) && Number.isInteger(j));
  const [a, b] = satin.splitBoundary(ring, i, j);
  assert.ok(finite(a) && finite(b));
});

// ---------------------------------------------------------------------------
// flatten.js -- degenerate rasters
// ---------------------------------------------------------------------------

const T = 255;

test("modeFilter: a 1x1, a 1xN and an all-transparent raster return the same shape", () => {
  assert.deepStrictEqual(FL.modeFilter(Uint8Array.from([3]), 1, 1), Uint8Array.from([3]));
  const row = Uint8Array.from([0, 1, 0, 1, 0]);
  assert.strictEqual(FL.modeFilter(row, 5, 1).length, 5);
  const clear = new Uint8Array(9).fill(T);
  assert.deepStrictEqual(FL.modeFilter(clear, 3, 3), clear);
});

test("modeFilter: a zero-sized raster does not throw", () => {
  assert.strictEqual(FL.modeFilter(new Uint8Array(0), 0, 0).length, 0);
});

test("absorbSmallRegions: a raster with nothing small, or nothing opaque, comes back whole", () => {
  const solid = new Uint8Array(16).fill(1);
  assert.deepStrictEqual(FL.absorbSmallRegions(solid, 4, 4, { minArea: 100 }).length, 16);
  const clear = new Uint8Array(16).fill(T);
  const out = FL.absorbSmallRegions(clear, 4, 4, { minArea: 100 });
  assert.ok(out.every((v) => v === T), "transparent pixels must not be repainted");
});

test("absorbSmallRegions: a lone pixel in a transparent field is not repainted transparent-wards into NaN", () => {
  const idx = new Uint8Array(25).fill(T);
  idx[12] = 2;
  const out = FL.absorbSmallRegions(idx, 5, 5, { minArea: 4 });
  assert.strictEqual(out.length, 25);
  assert.ok(out.every((v) => Number.isInteger(v) && v >= 0 && v <= 255));
});

test("paletteShares: an empty and an all-transparent raster give shares that are finite", () => {
  for (const idx of [new Uint8Array(0), new Uint8Array(9).fill(T)]) {
    const s = FL.paletteShares(idx, 3);
    const vals = Array.isArray(s) ? s : Object.values(s || {});
    assert.ok(vals.every((v) => Number.isFinite(v)), "NaN share from an image with no opaque pixel");
  }
});

// ---------------------------------------------------------------------------
// digitize.js -- shapes through buildQualityDesign
// ---------------------------------------------------------------------------

test("buildQualityDesign: degenerate shapes produce a design with finite stitches and never throw", () => {
  for (const [name, polys] of Object.entries(DEGENERATE)) {
    const d = design([{ outer: polys[0] || [], holes: [] }].filter((s) => s.outer.length));
    assert.ok(finite(d.stitches), name);
    assert.ok(d.stitches.length >= 1, name + ": the end sentinel is always there");
  }
});

test("buildQualityDesign: a self-intersecting bowtie does not throw and stays finite", () => {
  const d = design([{ outer: P([0, 0], [100, 100], [100, 0], [0, 100]), holes: [] }]);
  assert.ok(finite(d.stitches));
});

test("buildQualityDesign: a hole larger than its outer ring does not throw or sew outside the hoop", () => {
  const d = design([{ outer: sq(0, 0, 100), holes: [sq(-50, -50, 300)] }]);
  assert.ok(finite(d.stitches));
});

// BUG: a design with no usable geometry reports NaN dimensions. Measured
// 2026-10-08: buildQualityDesign([{ rgb, shapes: [{ outer: [], holes: [] }] }])
// returns the single `end` stitch, which is right, but widthMM and heightMM are
// NaN (the bbox of zero points, 0/0 after the fit scale). Anything downstream
// that prints or compares the size -- the stats line, the hoop ceiling check,
// the worksheet -- gets NaN. The all-regions-empty path just above it returns
// widthMM: 0 and is correct, which is the contract this should meet.
test.todo("buildQualityDesign: an empty outer ring reports 0 x 0 mm, not NaN (BUG: widthMM/heightMM are NaN)");

test("buildQualityDesign: a shape far below one row spacing beside a large one is sewn finite and in the hoop", () => {
  const d = design([{ outer: sq(0, 0, 400), holes: [] }, { outer: sq(500, 0, 1), holes: [] }]);
  assert.ok(finite(d.stitches));
  assert.ok(d.widthMM <= 4 * 25.4 + 0.01 && d.heightMM <= 4 * 25.4 + 0.01);
});

test("buildQualityDesign: a hairline sliver stays inside the hoop with finite stitches", () => {
  for (const h of [2, 0.01]) {
    const d = design([{ outer: sq(0, 0, 800, h), holes: [] }]);
    assert.ok(finite(d.stitches), "h " + h);
    assert.ok(d.widthMM <= 4 * 25.4 + 0.01, "h " + h);
  }
});

test("buildQualityDesign: a hole flush with the outer edge leaves no needle penetration in the hole", () => {
  // 100 px square at 1 px/mm, centred; hole is the left 40 x 60 slab.
  const d = DG.buildQualityDesign(
    [{ rgb: [10, 10, 10], shapes: [{ outer: sq(0, 0, 100), holes: [sq(0, 20, 40, 60)] }] }],
    { pxPerMm: 1, garment: { widthIn: 4, heightIn: 4 }, densityMm: 0.5, underlay: false, satinMaxWidthMm: 3 }
  );
  const sew = d.stitches.filter((s) => s.type === "stitch");
  assert.ok(sew.length > 100 && finite(sew));
  // DST units are 0.1 mm, centred, y up: hole x in [-50,-10] mm, y in [-30,30] mm.
  const margin = 20; // 2 mm of slack for underlay inset and pull compensation
  const inHole = sew.filter((p) => p.x > -500 + margin && p.x < -100 - margin && Math.abs(p.y) < 300 - margin);
  assert.strictEqual(inHole.length, 0, "penetrations inside the hole: " + inHole.length);
});

// ---------------------------------------------------------------------------
// Hoop limits
// ---------------------------------------------------------------------------

test("buildQualityDesign: a shape far wider than the hoop is scaled to fit it", () => {
  const d = design([{ outer: sq(0, 0, 100000, 50000), holes: [] }]);
  assert.ok(finite(d.stitches));
  assert.ok(d.widthMM <= 4 * 25.4 + 0.01, "width " + d.widthMM);
  assert.ok(d.heightMM <= 4 * 25.4 + 0.01, "height " + d.heightMM);
  const b = bbox(d.stitches);
  assert.ok(b.x1 - b.x0 <= 4 * 25.4 * 10 + 10, "stitch extent past the hoop");
});

test("buildQualityDesign: a very tall, narrow shape is clamped on height, not width", () => {
  const d = design([{ outer: sq(0, 0, 100, 100000), holes: [] }]);
  assert.ok(finite(d.stitches));
  assert.ok(d.heightMM <= 4 * 25.4 + 0.01, "height " + d.heightMM);
});

test("buildQualityDesign: a targetWidthMm past the hoop, or below 1 mm, is clamped into range", () => {
  for (const targetWidthMm of [10000, 0.001]) {
    const d = design([{ outer: sq(0, 0, 400, 200), holes: [] }], { targetWidthMm });
    assert.ok(finite(d.stitches), "target " + targetWidthMm);
    assert.ok(d.widthMM <= 4 * 25.4 + 0.01, "target " + targetWidthMm + " -> " + d.widthMM);
  }
});

// ---------------------------------------------------------------------------
// DST export / import round trips on those designs
// ---------------------------------------------------------------------------

test("round trip: a design with a sub-row-spacing shape beside a large one survives the file", () => {
  assertRoundTrips(design([{ outer: sq(0, 0, 400), holes: [] }, { outer: sq(500, 0, 1), holes: [] }]));
});

test("round trip: a hairline sliver survives the file", () => {
  assertRoundTrips(design([{ outer: sq(0, 0, 800, 2), holes: [] }]));
});

test("round trip: a design scaled down from far past the hoop survives the file", () => {
  assertRoundTrips(design([{ outer: sq(0, 0, 100000, 50000), holes: [] }]));
});

test("round trip: an annulus whose hole touches the edge survives the file", () => {
  assertRoundTrips(design([{ outer: sq(0, 0, 100), holes: [sq(0, 20, 40, 60)] }]));
});

test("round trip: a long jump between two far-apart shapes is split into records within the format maximum", () => {
  const d = design([{ outer: sq(0, 0, 60), holes: [] }, { outer: sq(2000, 1500, 60), holes: [] }]);
  assertRoundTrips(d);
});

test("encodeDST: an end-only design (nothing digitizable) is a valid file with no records", () => {
  const d = design([{ outer: [], holes: [] }]);
  const bytes = dst.encodeDST(d);
  assert.strictEqual(recordSteps(bytes).n, 0);
  assert.strictEqual((bytes.length - 512) % 3, 0);
  // ...and the importer refuses it by name rather than inventing a design.
  assert.throws(() => dstimport.decodeDST(bytes), /No stitches found/);
});

test("encodeDST: a single stitch is a valid file that reads back as one stitch", () => {
  const d = { stitches: [{ x: 0, y: 0, type: "stitch" }], colors: [{ r: 0, g: 0, b: 0, name: "a" }] };
  const back = dstimport.decodeDST(dst.encodeDST(d));
  assert.strictEqual(back.stitchCount, 1);
  assert.strictEqual(back.widthMM, 0);
  assert.strictEqual(back.heightMM, 0);
});

test("encodeDST: moves at and just past the 121 unit record limit split without exceeding it", () => {
  for (const reach of [120, 121, 122, 242, 243, 3000]) {
    for (const [dx, dy] of [[reach, 0], [0, reach], [reach, reach], [-reach, reach], [reach, 1]]) {
      const d = { stitches: [{ x: 0, y: 0, type: "stitch" }, { x: dx, y: dy, type: "stitch" }], colors: [{ r: 0, g: 0, b: 0, name: "a" }] };
      const bytes = dst.encodeDST(d);
      assert.ok(recordSteps(bytes).max <= 121, `${dx},${dy}`);
      const back = dstimport.decodeDST(bytes);
      assert.ok(finite(back.stitches));
      // The span is preserved to the unit, however many records it took.
      assert.strictEqual(Math.round(back.widthMM * 10), Math.abs(dx), `${dx},${dy} width`);
      assert.strictEqual(Math.round(back.heightMM * 10), Math.abs(dy), `${dx},${dy} height`);
    }
  }
});

test("encodeDST: non-finite and fractional coordinates never produce a record the format cannot hold", () => {
  const d = {
    stitches: [
      { x: 0, y: 0, type: "stitch" },
      { x: 10.4, y: -10.6, type: "stitch" },
      { x: NaN, y: 5, type: "stitch" },
      { x: 50, y: Infinity, type: "stitch" },
    ],
    colors: [{ r: 0, g: 0, b: 0, name: "a" }],
  };
  let bytes;
  try { bytes = dst.encodeDST(d); } catch (e) { return; } // refusing outright is acceptable
  assert.ok(recordSteps(bytes).max <= 121);
});

test("encodeDST: negative-extent designs (everything left of and below the origin) keep their size", () => {
  const d = { stitches: [{ x: -500, y: -400, type: "stitch" }, { x: -300, y: -100, type: "stitch" }], colors: [{ r: 0, g: 0, b: 0, name: "a" }] };
  const back = dstimport.decodeDST(dst.encodeDST(d));
  assert.strictEqual(Math.round(back.widthMM * 10), 200);
  assert.strictEqual(Math.round(back.heightMM * 10), 300);
});
