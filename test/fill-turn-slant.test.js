// Fill rows turn on a slant: `tatamiFill({ turnAlong, minStitch })`, default
// off, and the builder flag that turns it on for a shape's cover fill
// (`buildQualityDesign({ fillTurnSlant })`, built OFF 2026-10-22). The JS twin
// of the Python engine's `cfg.fill_turn_slant` (PR #1036,
// `docs/fill-turn-slant-2026-10-21.md`, `stage6_fill._slant_turns`).
//
// At the end of every row the fill steps straight across to the next row: one
// row spacing, 0.10-0.22 mm at the 0.15 row, the needle landing beside its own
// hole. The pro turns on a slant, `FILL_TURN_ALONG_MM` = 0.7 mm along the row
// (p50 0.71-0.83 across six of his DSTs). Of the two boundary points a turn
// joins, the OUTER one stays on the boundary and the INNER one is pulled in
// until the turn runs that far along the row; the slanted thread lies over the
// corner the pull left bare. Narrowing or square edge: the next row's entry is
// pulled. Widening edge: this row's exit. A column's last near-square turn:
// the exit, so the last row keeps its corner. Preferred row too short to keep
// the shortest stitch: the other end. Left alone: a turn already that far
// along, and one neither row can afford.
const assert = require("node:assert");
const { test } = require("node:test");
const { createHash } = require("node:crypto");
const fill = require("../src/fill.js");
const DG = require("../src/digitize.js");

const P = 4, MIN = 1, PITCH = 0.4, ALONG = 0.7;   // a stitch, the shortest stitch, a row, the turn: think mm
const rect = (x, y, w, h) => [{ x, y }, { x: x + w, y }, { x: x + w, y: y + h }, { x, y: y + h }];
// a parallelogram whose two sides lean `deg` from square to the rows
const para = (w, h, deg) => { const s = h / Math.tan((deg * Math.PI) / 180); return [{ x: 0, y: 0 }, { x: w, y: 0 }, { x: w + s, y: h }, { x: s, y: h }]; };
const ngon = (cx, cy, r, n) => Array.from({ length: n }, (_, i) => { const a = (2 * Math.PI * i) / n; return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) }; });
const md5 = (s) => createHash("md5").update(s).digest("hex");
const ptsFp = (pts) => md5(pts.map((p) => `${p.x},${p.y},${p.travel ? "T" : ""}${p.trim ? "C" : ""}`).join(";"));
const designFp = (d) => md5(d.stitches.map((s) => `${s.x},${s.y},${s.type}`).join(";"));
const turned = (p, deg) => { const t = (deg * Math.PI) / 180, c = Math.cos(t), s = Math.sin(t); return { x: p.x * c - p.y * s, y: p.x * s + p.y * c }; };

const base = (angleDeg, extra) => Object.assign({ rowSpacing: PITCH, angleDeg, maxStitch: P, markConnectors: true, stagger: 4, minStitch: MIN }, extra || {});
const ON = { turnAlong: ALONG };

// Every sewn stitch of a fill (a move into a float's landing is not one) as
// { a, b, d, turn }: `turn` when it joins two rows (the ends differ in height
// in the rows' frame).
function stitches(pts, angleDeg) {
  const out = [];
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i];
    if (b.travel || b.trim) continue;
    const d = Math.hypot(b.x - a.x, b.y - a.y);
    if (d <= 1e-6) continue;
    const ya = turned(a, -angleDeg).y, yb = turned(b, -angleDeg).y;
    out.push({ a, b, d, turn: Math.abs(ya - yb) > 1e-6 });
  }
  return out;
}
const under = (st, lim) => st.filter((s) => s.d < lim - 1e-9);
const median = (xs) => { const s = xs.slice().sort((p, q) => p - q); return s.length ? s[(s.length - 1) >> 1] : NaN; };

// The holes between the ends of each row, keyed by row height, as places along the row.
function holesByRow(pts, angleDeg) {
  const rows = new Map();
  for (const p of pts) {
    if (p.travel || p.trim) continue;
    const q = turned(p, -angleDeg), ky = Math.round(q.y / PITCH * 1e3);
    if (!rows.has(ky)) rows.set(ky, []);
    rows.get(ky).push(Math.round(q.x * 1e6) / 1e6);
  }
  for (const xs of rows.values()) xs.sort((p, q) => p - q);
  return rows;
}

// The share of 0.1 mm cells inside `polys` under a thread drawn `width` wide
// along the sewn stitches (a float lays none).
function coverage(pts, polys, width) {
  const CELL = 0.1;
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const ring of polys) for (const p of ring) { x0 = Math.min(x0, p.x); y0 = Math.min(y0, p.y); x1 = Math.max(x1, p.x); y1 = Math.max(y1, p.y); }
  const W = Math.ceil((x1 - x0) / CELL), H = Math.ceil((y1 - y0) / CELL);
  const inside = (x, y) => { let c = false; for (const ring of polys) for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) { const a = ring[i], b = ring[j]; if ((a.y > y) !== (b.y > y) && x < ((b.x - a.x) * (y - a.y)) / (b.y - a.y) + a.x) c = !c; } return c; };
  const hit = new Uint8Array(W * H);
  const r = width / 2, rc = Math.ceil(r / CELL);
  const paint = (a, b) => {
    const n = Math.max(1, Math.ceil(Math.hypot(b.x - a.x, b.y - a.y) / (CELL / 2)));
    for (let s = 0; s <= n; s++) {
      const px = a.x + ((b.x - a.x) * s) / n, py = a.y + ((b.y - a.y) * s) / n;
      const cx = Math.floor((px - x0) / CELL), cy = Math.floor((py - y0) / CELL);
      for (let dy = -rc; dy <= rc; dy++) for (let dx = -rc; dx <= rc; dx++) {
        const gx = cx + dx, gy = cy + dy;
        if (gx < 0 || gy < 0 || gx >= W || gy >= H) continue;
        if (Math.hypot((gx + 0.5) * CELL + x0 - px, (gy + 0.5) * CELL + y0 - py) <= r) hit[gy * W + gx] = 1;
      }
    }
  };
  for (let i = 1; i < pts.length; i++) if (!pts[i].travel && !pts[i].trim) paint(pts[i - 1], pts[i]);
  let inN = 0, cov = 0;
  for (let gy = 0; gy < H; gy++) for (let gx = 0; gx < W; gx++) {
    if (!inside((gx + 0.5) * CELL + x0, (gy + 0.5) * CELL + y0)) continue;
    inN++;
    if (hit[gy * W + gx]) cov++;
  }
  return cov / inN;
}

// ---- OFF: byte-identical to main of 2026-10-22 (03ccab4e) ------------------
// `test/fill-stagger.test.js`'s builder fixture, built with every later flag
// off, and four fills asked of the module directly. Taken before the option
// existed (the scratch script printed them off that tree).
const PINS = {
  design_columnsOff_staggerOff: "d7edc6a658555d3dff9de898f94d7ec2",
  design_columnsOff_staggerOn: "9da3b18a6de700afa9fc9751da488e1a",
  design_columnsOn_staggerOff: "2ace04f12f35d020de7166f4765d16f6",
  design_columnsOn_staggerOn: "6ebf8e9314e27d2fed4b3527765a36e4",
  rect: "27a8750f3b54a3f459a98db4431687c6",
  rectStagger: "01fdc1df8af780235ddec6bb90fec2ba",
  frameColumns: "5f6243b437aca124c2d7a5c1b03f4518",
  disc: "74332f4c3b6a9152385a2f89d2480ab6",
};
const build = (extra) => DG.buildQualityDesign(
  [{ rgb: [10, 10, 10], shapes: [{ outer: rect(0, 0, 400, 200), holes: [], tierOverride: "fill" }, { outer: rect(600, 0, 300, 300), holes: [rect(700, 100, 100, 100)], tierOverride: "fill" }] },
   { rgb: [200, 30, 30], shapes: [{ outer: rect(0, 400, 250, 250), holes: [], tierOverride: "fill" }] }],
  Object.assign({ garment: { widthIn: 6, heightIn: 6 }, pxPerMm: 10, darkOnTop: false, underlay: true, ties: false, dedupeHoles: false }, extra || {}));
function passes(extra) {
  const real = fill.tatamiFill, seen = [];
  fill.tatamiFill = (polys, opts) => { const pts = real(polys, opts); seen.push({ polys, opts, pts }); return pts; };
  try { return { design: build(extra), seen }; } finally { fill.tatamiFill = real; }
}
const count = (d, k) => d.stitches.filter((s) => s.type === k).length;

test("OFF: the builder fixture sews the bytes main sewed, flag absent and flag false", () => {
  for (const fc of [false, true]) for (const fs of [false, true]) {
    const id = `design_columns${fc ? "On" : "Off"}_stagger${fs ? "On" : "Off"}`;
    assert.strictEqual(designFp(build({ fillColumns: fc, fillStagger: fs })), PINS[id], id + " (absent)");
    assert.strictEqual(designFp(build({ fillColumns: fc, fillStagger: fs, fillTurnSlant: false })), PINS[id], id + " (false)");
  }
});

test("OFF: four fills asked of the module directly are the bytes main gave, with `turnAlong` absent and 0", () => {
  const plain = (extra) => Object.assign({ rowSpacing: PITCH, angleDeg: 0, maxStitch: P, markConnectors: true }, extra || {});
  const cases = {
    rect: [[rect(0, 0, 40, 20)], plain()],
    rectStagger: [[rect(0, 0, 40, 20)], plain({ stagger: 4, minStitch: MIN })],
    frameColumns: [[rect(0, 0, 60, 60), rect(20, 20, 20, 20)], plain({ angleDeg: 30, columns: true, openTol: PITCH })],
    disc: [[ngon(30, 30, 25, 72)], plain({ angleDeg: 17, centerOut: true })],
  };
  for (const [id, [polys, opts]] of Object.entries(cases)) {
    assert.strictEqual(ptsFp(fill.tatamiFill(polys, opts)), PINS[id], id);
    assert.strictEqual(ptsFp(fill.tatamiFill(polys, Object.assign({ turnAlong: 0 }, opts))), PINS[id], id + " (0)");
  }
});

// ---- the rule, on a column of spans -----------------------------------------
// `slantTurns(seq, along, minStitch)`: `seq` is a column as it is walked,
// [{ y, x0, x1, rev }] with `rev` the rows sewn right to left; -> [[x0, x1]].
const col = (rows) => rows.map(([y, x0, x1], k) => ({ y, x0, x1, rev: k % 2 === 1 }));

test("slantTurns: a square edge pulls the next row's entry 0.7 along, and the exit stays on the boundary", () => {
  // five rows of a box, 10 wide; row 0 sewn left to right, exits at x = 10; row 1 enters at x = 10.
  // (A column's LAST turn is its own case below and reaches the row before it, so the rows read here are the first three.)
  const out = fill.slantTurns(col([[0, 0, 10], [PITCH, 0, 10], [2 * PITCH, 0, 10], [3 * PITCH, 0, 10], [4 * PITCH, 0, 10]]), ALONG, MIN);
  assert.deepStrictEqual(out.slice(0, 3), [[0, 10], [0, 10 - ALONG], [ALONG, 10]]);
});

test("slantTurns: a narrowing edge pulls the entry; a widening edge pulls this row's exit", () => {
  // narrowing on the right: row 1's right end is 0.2 in from row 0's (a third row so this is not the last turn)
  const narrow = fill.slantTurns(col([[0, 0, 10], [PITCH, 0, 9.8], [2 * PITCH, 0, 9.6], [3 * PITCH, 0, 9.4]]), ALONG, MIN);
  assert.deepStrictEqual(narrow.slice(0, 2), [[0, 10], [0, 9.8 - (ALONG - 0.2)]]);
  // widening on the right: row 1's right end is 0.2 out from row 0's, so row 0's exit is pulled
  const wider = fill.slantTurns(col([[0, 0, 10], [PITCH, 0, 10.2], [2 * PITCH, 0, 10.4], [3 * PITCH, 0, 10.6]]), ALONG, MIN);
  assert.deepStrictEqual(wider.slice(0, 2), [[0, 10 - (ALONG - 0.2)], [0, 10.2]]);
  // the same on the left side, where row 1 (right to left) exits and row 2 enters
  const three = fill.slantTurns(col([[0, 0, 10], [PITCH, 0, 10], [2 * PITCH, 0.3, 10], [3 * PITCH, 0.6, 10]]), ALONG, MIN);
  assert.strictEqual(three[2][0], 0.3 + (ALONG - 0.3), "narrowing on the left: row 2's entry pulled (its exit is the last turn's)");
  const wide = fill.slantTurns(col([[0, 0, 10], [PITCH, 0, 10], [2 * PITCH, -0.3, 10]]), ALONG, MIN);
  assert.deepStrictEqual(wide[1], [0 + (ALONG - 0.3), 10 - ALONG], "widening on the left: row 1's exit pulled (and its entry by the turn above)");
});

test("slantTurns: a turn already 0.7 along the row is left alone", () => {
  assert.deepStrictEqual(fill.slantTurns(col([[0, 0, 10], [PITCH, 0, 9.3]]), ALONG, MIN), [[0, 10], [0, 9.3]]);
  assert.deepStrictEqual(fill.slantTurns(col([[0, 0, 10], [PITCH, 0, 10.7]]), ALONG, MIN), [[0, 10], [0, 10.7]]);
});

test("slantTurns: the column's last turn pulls the exit when the edge is near square, so the last row keeps its corner", () => {
  const out = fill.slantTurns(col([[0, 0, 10], [PITCH, 0, 10], [2 * PITCH, 0, 10]]), ALONG, MIN);
  assert.deepStrictEqual(out, [[0, 10], [ALONG, 10 - ALONG], [0, 10]]);
  // but a last turn on an edge sloped past the row spacing is an ordinary narrowing turn: the entry is pulled
  const sloped = fill.slantTurns(col([[0, 0, 10], [PITCH, 0, 10], [2 * PITCH, 0.5, 10]]), ALONG, MIN);
  assert.deepStrictEqual(sloped[2], [0.5 + (ALONG - 0.5), 10]);
});

test("slantTurns: a row too short to keep the shortest stitch gives the pull to the turn's other end, and a turn neither can afford is left alone", () => {
  // row 1 is 1.5 long: 1.5 - 0.7 = 0.8 < MIN, so row 0's exit is pulled instead
  assert.deepStrictEqual(fill.slantTurns(col([[0, 0, 10], [PITCH, 8.5, 10]]), ALONG, MIN), [[0, 10 - ALONG], [8.5, 10]]);
  // both rows 1.5 long: nothing moves
  assert.deepStrictEqual(fill.slantTurns(col([[0, 8.5, 10], [PITCH, 8.5, 10]]), ALONG, MIN), [[8.5, 10], [8.5, 10]]);
  // a row pulled from both its turns is counted twice: a 2.3 long middle row takes the first pull
  // (1.6 left) and cannot take the last turn's exit pull too (0.9 < MIN), so that one goes to the last row's entry
  const twice = fill.slantTurns(col([[0, 7.7, 10], [PITCH, 7.7, 10], [2 * PITCH, 7.7, 10]]), ALONG, MIN);
  assert.deepStrictEqual(twice, [[7.7, 10], [7.7, 10 - ALONG], [7.7 + ALONG, 10]]);
});

// ---- ON: no fill turn under half a millimetre, the rows' grid and cover kept ----
const SHAPES = {
  box: { polys: [rect(0, 0, 40, 20)], angle: 0 },
  boxAcross: { polys: [rect(0, 0, 40, 20)], angle: 90 },
  disc: { polys: [ngon(30, 30, 25, 72)], angle: 17 },
  strip: { polys: [rect(0, 0, 30, 2.5)], angle: 90 },       // rows 2.5 long, across the strip
  para20: { polys: [para(30, 15, 20)], angle: 0 },
  para45: { polys: [para(30, 15, 45)], angle: 0 },
  para60: { polys: [para(30, 15, 60)], angle: 0 },
  para75: { polys: [para(30, 15, 75)], angle: 0 },
};
const both = (id, extra) => {
  const s = SHAPES[id];
  return { s, off: fill.tatamiFill(s.polys, base(s.angle, extra)), on: fill.tatamiFill(s.polys, base(s.angle, Object.assign({}, ON, extra))) };
};

// Where the straight step is under 0.5 mm, flag off: every edge square to the
// rows, and a sloped edge whose step along the row per row is short enough
// (hypot(0.4, 0.4 / tan 60) = 0.46; at 45 degrees it is already 0.57, and at
// 20 degrees 1.17, further along than the rule asks, so those are left alone).
const DEFECT = ["box", "boxAcross", "disc", "strip", "para60", "para75"];

test("ON: the straight step across is the defect, and no turn is under 0.5 mm after it", () => {
  for (const id of Object.keys(SHAPES)) {
    const { s, off, on } = both(id);
    const offTurns = under(stitches(off, s.angle).filter((t) => t.turn), 0.5), onTurns = under(stitches(on, s.angle).filter((t) => t.turn), 0.5);
    if (DEFECT.includes(id)) assert.ok(offTurns.length >= 10, id + ": the defect, flag off: " + offTurns.length + " turns under 0.5");
    else assert.strictEqual(offTurns.length, 0, id + ": a shallow slope's turns are already long, flag off");
    assert.strictEqual(onTurns.length, 0, id + ": turns under 0.5 with the flag on: " + onTurns.map((t) => t.d.toFixed(3)).join(" "));
  }
});

test("ON: a slanted turn is sqrt(0.7^2 + row^2) long on a square edge, and never over a stitch", () => {
  const { s, on } = both("box");
  const turns = stitches(on, s.angle).filter((t) => t.turn).map((t) => t.d);
  const want = Math.hypot(ALONG, PITCH);
  assert.ok(Math.abs(median(turns) - want) < 1e-6, "p50 " + median(turns) + " against " + want);
  assert.ok(Math.max(...turns) <= P + 1e-9, "a turn over a stitch: " + Math.max(...turns));
});

test("ON: without the stagger too (the Python engine has no such pairing), and the floor is kept by `minStitch` alone", () => {
  for (const id of ["box", "para60", "strip"]) {
    const { s, off, on } = both(id, { stagger: 0 });
    assert.ok(under(stitches(off, s.angle).filter((t) => t.turn), 0.5).length >= 10, id + ": the defect, flag off");
    assert.strictEqual(under(stitches(on, s.angle).filter((t) => t.turn), 0.5).length, 0, id);
    for (const t of stitches(on, s.angle)) if (!t.turn) assert.ok(t.d >= MIN - 1e-9 || t.d >= P / 2 - 1e-9, id + ": a row stitch of " + t.d);
  }
});

test("ON: every row is still sewn, at its own height, and the holes between its ends are the grid's", () => {
  for (const id of Object.keys(SHAPES)) {
    const { s, off, on } = both(id);
    const hOff = holesByRow(off, s.angle), hOn = holesByRow(on, s.angle);
    assert.deepStrictEqual([...hOn.keys()].sort(), [...hOff.keys()].sort(), id + ": the rows");
    let kept = 0, all = 0;
    for (const [ky, xsOff] of hOff) {
      const xsOn = hOn.get(ky), lo = xsOff[0], hi = xsOff[xsOff.length - 1];
      // the ends may move in by the pull, and the stagger's own end rule (a grid point under
      // the shortest stitch from an end is dropped and the long step halved) reaches a stitch
      // and a shortest stitch in from there; every hole beyond that is where it was
      const inner = xsOff.filter((x) => x > lo + ALONG + P + MIN + 1e-6 && x < hi - ALONG - P - MIN - 1e-6);
      for (const x of inner) { all++; if (xsOn.some((y) => Math.abs(y - x) < 1e-6)) kept++; }
      // no end moved out, or in by more than the pull (the row before a column's last
      // may be pulled at both ends: the turn above's entry and the last turn's exit)
      assert.ok(xsOn[0] >= lo - 1e-6 && xsOn[0] <= lo + ALONG + 1e-6, id + ": row " + ky + " low end " + lo + " -> " + xsOn[0]);
      assert.ok(xsOn[xsOn.length - 1] <= hi + 1e-6 && xsOn[xsOn.length - 1] >= hi - ALONG - 1e-6, id + ": row " + ky + " high end " + hi + " -> " + xsOn[xsOn.length - 1]);
    }
    if (id !== "strip") assert.ok(all > 50, id + ": fixture, interior holes " + all);   // a 2.5 mm row has none that far from its ends
    assert.strictEqual(kept, all, id + ": interior holes moved: " + (all - kept) + " of " + all);
  }
});

test("ON: at the 0.15 mm row, under a 0.4 mm thread, the shape is covered as it was; the pull's corner lies under the slanted thread", () => {
  // The builder's row (`FILL_ROW_MM`), not this file's 0.4: the bare corner is a
  // right triangle 0.7 along by one row across, and its far corner is
  // 0.7 * row / hypot(0.7, row) from the slanted thread -- 0.15 mm at the 0.15
  // row (under the thread's 0.2 half-width), 0.35 at a 0.4 row (not). The
  // Python lane measured 0.000-0.002 mm^2 bare at 0.15; thread width decides
  // it, which is why the flip is a sew-out's.
  for (const id of ["box", "disc", "para20", "para60", "strip"]) {
    const { s } = both(id);
    const off = fill.tatamiFill(s.polys, base(s.angle, { rowSpacing: 0.15 })), on = fill.tatamiFill(s.polys, base(s.angle, Object.assign({ rowSpacing: 0.15 }, ON)));
    const cOff = coverage(off, s.polys, 0.4), cOn = coverage(on, s.polys, 0.4);
    assert.ok(cOff > 0.95, id + ": fixture, off " + cOff);
    assert.ok(cOn >= cOff - 0.002, id + ": coverage " + cOff.toFixed(4) + " -> " + cOn.toFixed(4));
  }
});

test("ON: a shape with a hole, sewn by the column walk, gets the same turn and not one more cut", () => {
  const polys = [rect(0, 0, 60, 60), rect(20, 20, 20, 20)], angle = 30;
  const off = fill.tatamiFill(polys, base(angle, { columns: true, openTol: PITCH }));
  const on = fill.tatamiFill(polys, base(angle, Object.assign({ columns: true, openTol: PITCH }, ON)));
  assert.ok(on.columnWalk && off.columnWalk, "fixture: the column walk");
  const cuts = (pts) => pts.filter((p) => p.trim).length;
  assert.strictEqual(cuts(on), cuts(off));
  const offTurns = under(stitches(off, angle).filter((t) => t.turn), 0.5).length, onTurns = under(stitches(on, angle).filter((t) => t.turn), 0.5).length;
  assert.ok(offTurns >= 100, "the defect, flag off: " + offTurns);
  assert.ok(onTurns <= 2, "turns under 0.5 with the flag on: " + onTurns + " (a column's one row that no pull can afford is allowed)");
  assert.ok(coverage(on, polys, 0.4) >= coverage(off, polys, 0.4) - 0.002);
});

// ---- the builder flag -------------------------------------------------------
test("fillTurnSlant (shapes): ON reaches every cover pass with the Python engine's constant, and never the underlay", () => {
  const { seen } = passes({ fillTurnSlant: true });
  const cover = seen.filter((p) => p.opts.turnAlong);
  assert.strictEqual(cover.length, 3, "fixture: three fill shapes, one cover pass each");
  for (const p of cover) {
    assert.ok(Math.abs(p.opts.turnAlong / p.opts.minStitch - 0.7) < 1e-12, "machine.FILL_TURN_ALONG_MM against MIN_STITCH_MM, in the fill's own units: " + p.opts.turnAlong + " / " + p.opts.minStitch);
    assert.ok(Math.abs(p.opts.turnAlong / p.opts.maxStitch - 0.7 / 4) < 1e-12, "0.7 mm against the 4 mm stitch");
  }
  const under_ = seen.filter((p) => !p.opts.turnAlong);
  assert.ok(under_.length >= 3, "fixture: underlay passes, " + under_.length);
  const offUnder = passes({ fillTurnSlant: false }).seen.filter((p) => p.opts.rowSpacing !== cover[0].opts.rowSpacing);
  assert.deepStrictEqual(under_.map((p) => p.pts), offUnder.map((p) => p.pts), "every underlay pass is the one sewn with the flag off");
});

test("fillTurnSlant (shapes): the constant is declared once in digitize.js as 0.7, the Python engine's", () => {
  const src = require("node:fs").readFileSync(require("node:path").join(__dirname, "..", "src", "digitize.js"), "utf8");
  const m = /\bconst FILL_TURN_ALONG_MM\s*=\s*([0-9.]+)/.exec(src);
  assert.ok(m, "no FILL_TURN_ALONG_MM in digitize.js");
  assert.strictEqual(Number(m[1]), 0.7);
});

test("fillTurnSlant (shapes): the design keeps its size, its colours, its cuts and its runs, and sheds its short turns", () => {
  for (const fc of [false, true]) {
    const off = build({ fillColumns: fc }), on = build({ fillColumns: fc, fillTurnSlant: true });
    assert.notStrictEqual(designFp(on), designFp(off), "the flag does something");
    assert.strictEqual(on.widthMM, off.widthMM);
    assert.strictEqual(on.heightMM, off.heightMM);
    for (const k of ["trim", "color", "jump", "end"]) assert.strictEqual(count(on, k), count(off, k), k + " records");
    assert.deepStrictEqual(on.runs.map((r) => r.kind + "/" + r.shape + "/" + r.block), off.runs.map((r) => r.kind + "/" + r.shape + "/" + r.block));
    const more = on.stitchCount / off.stitchCount - 1;
    assert.ok(more > -0.05 && more < 0.02, "stitches: " + off.stitchCount + " -> " + on.stitchCount);
    // the design's units are 0.1 mm: a stitch under 0.5 mm is under 5
    const short = (d) => { let n = 0; for (let i = 1; i < d.stitches.length; i++) if (d.stitches[i].type === "stitch" && d.stitches[i - 1].type === "stitch" && Math.hypot(d.stitches[i].x - d.stitches[i - 1].x, d.stitches[i].y - d.stitches[i - 1].y) < 5) n++; return n; };
    assert.ok(short(on) < 0.3 * short(off), "stitches under 0.5 mm: " + short(off) + " -> " + short(on));
  }
});
