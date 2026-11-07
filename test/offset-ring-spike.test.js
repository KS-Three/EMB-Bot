// offsetRing (src/digitize.js) on CONCAVE rings: the wedge-spike class behind
// MASTER_SCOPE defects 54 (fixed 2026-10-03) and 55 (gesture cured 10-03, the
// near repeat dropped 10-08, the offset itself still open).
//
// This file pins what offsetRing does TODAY on three concave rings, each moved
// in and out by 0.3, 1 and 3 mm at the Studio's 10 px per mm. Three measures a
// case must pass, each with a plain assertion where it does:
//
//   - LONGEST EDGE: no output edge longer than twice the input's longest. A
//     spike is an edge far longer than anything in the drawing.
//   - AREA: an inward offset must not grow the ring, an outward must not shrink it.
//   - SELF-CROSSINGS: a ring that was simple must come back simple.
//
// A case that fails is pinned as a KNOWN failure (`skip` carrying the measured
// value), never passed quietly and never with a loosened bound. The last test
// asserts those pinned cases still reproduce, so a change to offsetRing that
// cures one turns it red and says which skips to lift. That is the clipper2-ts
// trigger in `.claude/memory/external-repo-sourcing-2026-11-06.md` ("the next
// offsetRing artefact") measured instead of eyeballed.
//
// Measured 2026-11-07 (this file's own helpers, `node --test`):
//   - crescent OUT 1 mm: longest edge 2.12x the input's; 3 mm: 3.54x. The cusp
//     is pushed the whole mitre clamp (3d) along its bisector.
//   - crescent IN 1 mm and 3 mm: 2 self-crossings each, one per cusp, on a ring
//     10 mm thick at its thinnest. The cusp vertex moves 3d inward and lands
//     past the arc vertex beside it (which moved d), so the edge between them
//     folds back. The fold begins between 0.6 and 0.7 mm on this crescent: terry
//     (0.6) is clear by a hair; a heavier pull compensation is not.
//   - defect 55, the offset half: an anchor dragged 0.6 mm or more past a box
//     corner (so NOT a near repeat: its edge is as long as the offset) keeps the
//     whole clamp. On terry (6 px) the ring reaches 23.8 px out where a clean
//     side is 6 and a clean corner 8.5 -- four times the compensation.
//   - L, star and the crescent at 0.3 mm: every measure passes. The star's
//     tips also take 3d, but its 36-degree point has a true mitre of 3.24d, so
//     that is a mitre, not a spike, and no edge-length or crossing shows it.
//
// The SECOND half of the file runs every case again with `{ bevel: true }`
// (buildQualityDesign's `offsetBevel`, default off), where the pins above are
// lifted: four of the five pass. Measured 2026-11-07:
//   - crescent OUT 1 mm: longest edge 2.12x -> 1.05x; the cusp reaches 3.00d
//     past the drawing -> 1.00d (a bevel, cut square at the offset).
//   - crescent IN 1 mm and 3 mm: 2 self-crossings -> 0 each (the moved edges
//     that ran backward at the cusp are consumed, 4 and 6 corners).
//   - the dragged anchor: 23.8 px out -> 7.2 (6 px slip), 27.7 -> 11.0 (10),
//     37.5 -> 20.8 (20); each within the slip plus the offset.
//   - STILL PINNED, crescent OUT 3 mm: 3.54x -> 2.19x. What is left over 2x is
//     the bevel itself: 1.9d across (57 px at 3 mm) against the drawing's
//     26 px edges. Its reach is 1.00d, so it is no spike, but the edge measure
//     cannot tell a bevel from one and the bound is not loosened for it.
const assert = require("node:assert");
const { test } = require("node:test");
const DG = require("../src/digitize.js");

const PX_PER_MM = 10;                       // the Studio's canvas scale
const OFFSETS_MM = [0.3, 1, 3];
const ring = (pts) => pts.map(([x, y]) => ({ x, y }));

// --- the three concave rings (px; all about 40 mm across) --------------------
// An L: a 40 mm box less its top-right 25 mm; one inside corner, all right angles.
const lRing = () => ring([[0, 0], [400, 0], [400, 150], [150, 150], [150, 400], [0, 400]]);
// A crescent with two sharp cusps: outer arc r 200 about (200,200), inner arc
// r 250 about (50,200), both through (200,0) and (200,400). 10 mm thick at the
// middle, 36.9 degrees at each cusp, 48 corners of 19 to 26 px.
const crescentRing = () => {
  const o = [], n = 24;
  for (let i = 0; i <= n; i++) { const a = -Math.PI / 2 + i * Math.PI / n; o.push({ x: 200 + 200 * Math.cos(a), y: 200 + 200 * Math.sin(a) }); }
  const a0 = Math.atan2(200, 150);
  for (let i = 1; i < n; i++) { const a = a0 - 2 * a0 * i / n; o.push({ x: 50 + 250 * Math.cos(a), y: 200 + 250 * Math.sin(a) }); }
  return o;
};
// A five-point star: tips at r 200, inside corners at r 80; 36-degree tips,
// five reflex corners.
const starRing = () => Array.from({ length: 10 }, (_, i) => {
  const a = -Math.PI / 2 + i * Math.PI / 5, r = i % 2 ? 80 : 200;
  return { x: 200 + r * Math.cos(a), y: 200 + r * Math.sin(a) };
});
const SHAPES = { L: lRing, crescent: crescentRing, star: starRing };

// --- the measures ------------------------------------------------------------
const edgeLengths = (p) => p.map((q, i) => { const r = p[(i + 1) % p.length]; return Math.hypot(r.x - q.x, r.y - q.y); });
const longestEdge = (p) => Math.max(...edgeLengths(p));
const cross = (p, q, r) => (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x);
// Proper crossings only: two edges that pass through one another, not a shared corner.
const segmentsCross = (a, b, c, d) => cross(c, d, a) * cross(c, d, b) < 0 && cross(a, b, c) * cross(a, b, d) < 0;
function selfCrossings(p) {
  const n = p.length, hits = [];
  for (let i = 0; i < n; i++) {
    for (let j = i + 2; j < n; j++) {
      if (i === 0 && j === n - 1) continue;             // the closing edge meets the first at a corner
      if (segmentsCross(p[i], p[(i + 1) % n], p[j], p[(j + 1) % n])) hits.push([i, j]);
    }
  }
  return hits;
}
const SPIKE_RATIO = 2;                      // an output edge twice the longest input edge is a spike

function measure(shape, mm, outward, opts) {
  const input = SHAPES[shape](), out = DG.offsetRing(input, mm * PX_PER_MM, outward, opts);
  const a0 = DG.signedArea(input), a1 = DG.signedArea(out);
  return {
    out,
    edgeRatio: longestEdge(out) / longestEdge(input),
    areaRatio: a1 / a0,                                 // same sign while the ring has not inverted
    monotone: Math.sign(a1) === Math.sign(a0) && (outward ? Math.abs(a1) >= Math.abs(a0) : Math.abs(a1) <= Math.abs(a0)),
    crossings: selfCrossings(out),
  };
}

// The pinned failures: measure -> case -> what was measured (2026-11-07).
const KNOWN = {
  edge: {
    "crescent out 1mm": "defect 55: cusp takes the whole 3d clamp; longest edge 2.12x the input's (55.5 px from 26.2)",
    "crescent out 3mm": "defect 55: longest edge 3.54x the input's (92.7 px from 26.2); 12 cusp corners dropped as near repeats",
  },
  cross: {
    "crescent in 1mm": "defect 55: 2 self-crossings (one per cusp) on a ring 10 mm thick; cusp vertex moved 3d past its neighbour's d",
    "crescent in 3mm": "defect 55: 2 self-crossings (one per cusp) on a ring 10 mm thick",
  },
};
const caseName = (shape, mm, outward) => `${shape} ${outward ? "out" : "in"} ${mm}mm`;
const skipIf = (reason) => (reason ? { skip: reason } : {});

for (const shape of Object.keys(SHAPES)) {
  test(`${shape}: the input ring is simple and concave`, () => {
    const r = SHAPES[shape]();
    assert.strictEqual(selfCrossings(r).length, 0, "the drawing crosses itself");
    let turns = 0;
    for (let i = 0; i < r.length; i++) turns += cross(r[i], r[(i + 1) % r.length], r[(i + 2) % r.length]) < 0 ? 1 : 0;
    assert.ok(turns > 0 && turns < r.length, "a concave ring turns both ways: " + turns + " of " + r.length);
  });
  for (const outward of [true, false]) for (const mm of OFFSETS_MM) {
    const name = caseName(shape, mm, outward);
    test(`${name}: no output edge over ${SPIKE_RATIO}x the longest input edge`, skipIf(KNOWN.edge[name]), () => {
      const m = measure(shape, mm, outward);
      assert.ok(m.edgeRatio <= SPIKE_RATIO, `longest edge ${m.edgeRatio.toFixed(3)}x the input's`);
    });
    test(`${name}: ${outward ? "grows" : "shrinks"} the area and does not invert`, () => {
      const m = measure(shape, mm, outward);
      assert.ok(m.monotone, `area x${m.areaRatio.toFixed(3)}`);
    });
    test(`${name}: comes back without self-crossings`, skipIf(KNOWN.cross[name]), () => {
      const m = measure(shape, mm, outward);
      assert.strictEqual(m.crossings.length, 0, "crossings at edge pairs " + JSON.stringify(m.crossings));
    });
  }
}

// --- defect 55's own case: a box whose last anchor is beside its last corner --
const boxRing = () => ring([[0, 0], [400, 0], [400, 400], [0, 400]]);
const TERRY_PX = 6;                          // terry's 0.6 mm pull compensation
// How far out of the drawn box the moved ring reaches, in px (a clean side: 6).
const reachPast = (moved) => Math.max(...moved.map((p) => Math.max(-p.x, -p.y, p.x - 400, p.y - 400)));

test("defect 55, cured half: the census' 1 px slip is dropped and the box moved as drawn", () => {
  // tools/closed-ring-census.mjs table 4: second click of a double-click 1 px
  // from the last anchor. Dropped as a near repeat since 2026-10-08.
  const moved = DG.offsetRing(boxRing().concat([{ x: -0.2, y: 400.98 }]), TERRY_PX, true);
  assert.deepStrictEqual(moved, ring([[-6, -6], [406, -6], [406, 406], [-6, 406]]));
});

test("defect 55, open half: an anchor dragged 0.6 mm past the corner sews no further out than a clean corner",
  { skip: "defect 55: 23.8 px out for a 6 px offset (clean side 6, clean corner 8.5): the edge is as long as the offset, so it is no near repeat, and the sharp corner takes the whole 3d clamp" }, () => {
    for (const slipPx of [6, 10, 20]) {
      const moved = DG.offsetRing(boxRing().concat([{ x: -slipPx * 0.2, y: 400 + slipPx * 0.98 }]), TERRY_PX, true);
      // a bevelled or rounded corner would reach the slip itself plus the offset, no more
      assert.ok(reachPast(moved) <= slipPx + TERRY_PX + 1e-9, `${slipPx} px slip: ${reachPast(moved).toFixed(1)} px out`);
    }
  });

// --- the trigger: the pins above still describe offsetRing -------------------
// When this goes red offsetRing has changed. Re-measure, lift the skips that
// now pass, and say so in the PR body: it is the clipper2-ts decision's input.
test("the pinned failures still reproduce (lift their skips when this turns red)", () => {
  const still = [];
  for (const name of Object.keys(KNOWN.edge)) {
    const [shape, dir, mm] = name.split(" ");
    const m = measure(shape, parseFloat(mm), dir === "out");
    if (m.edgeRatio > SPIKE_RATIO) still.push(name); else assert.fail(`${name}: longest edge now ${m.edgeRatio.toFixed(3)}x, under ${SPIKE_RATIO}: lift its skip`);
  }
  for (const name of Object.keys(KNOWN.cross)) {
    const [shape, dir, mm] = name.split(" ");
    const m = measure(shape, parseFloat(mm), dir === "out");
    if (m.crossings.length > 0) still.push(name); else assert.fail(`${name}: no self-crossing now: lift its skip`);
  }
  const dragged = DG.offsetRing(boxRing().concat([{ x: -1.2, y: 405.88 }]), TERRY_PX, true);
  assert.ok(reachPast(dragged) > 6 + TERRY_PX, "the dragged anchor no longer spikes (" + reachPast(dragged).toFixed(1) + " px out): lift its skip");
  assert.ok(Math.abs(reachPast(dragged) - 23.8) < 0.1, "the dragged anchor's reach has moved from 23.8 px: " + reachPast(dragged).toFixed(2));
  assert.strictEqual(still.length, 4);
});

// =============================================================================
// The same cases with `{ bevel: true }` (buildQualityDesign's `offsetBevel`).
// The pins above are lifted here; what still fails is pinned again, with its
// own measured value, under the same rule: skip, never a looser bound.
// =============================================================================
const BEVEL = { bevel: true };
const KNOWN_BEVEL = {
  edge: {
    "crescent out 3mm": "bevel: longest edge 2.19x the input's (57.4 px from 26.2) -- the bevel chord itself, 1.9d across; it reaches 1.00d past the drawing, so no spike",
  },
  cross: {},
};
// how far the furthest point lies from the ring as drawn, in units of the offset
const segDist = (p, a, b) => {
  const dx = b.x - a.x, dy = b.y - a.y, l2 = dx * dx + dy * dy;
  const t = l2 ? Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / l2)) : 0;
  return Math.hypot(p.x - a.x - t * dx, p.y - a.y - t * dy);
};
const reachOf = (input, out, d) => Math.max(...out.map((p) => Math.min(...input.map((a, i) => segDist(p, a, input[(i + 1) % input.length]))))) / d;

for (const shape of Object.keys(SHAPES)) {
  for (const outward of [true, false]) for (const mm of OFFSETS_MM) {
    const name = caseName(shape, mm, outward);
    test(`bevel, ${name}: no output edge over ${SPIKE_RATIO}x the longest input edge`, skipIf(KNOWN_BEVEL.edge[name]), () => {
      const m = measure(shape, mm, outward, BEVEL);
      assert.ok(m.edgeRatio <= SPIKE_RATIO, `longest edge ${m.edgeRatio.toFixed(3)}x the input's`);
    });
    test(`bevel, ${name}: ${outward ? "grows" : "shrinks"} the area and does not invert`, () => {
      const m = measure(shape, mm, outward, BEVEL);
      assert.ok(m.monotone, `area x${m.areaRatio.toFixed(3)}`);
    });
    test(`bevel, ${name}: comes back without self-crossings`, skipIf(KNOWN_BEVEL.cross[name]), () => {
      const m = measure(shape, mm, outward, BEVEL);
      assert.strictEqual(m.crossings.length, 0, "crossings at edge pairs " + JSON.stringify(m.crossings));
    });
  }
}

// (1.01d, not 1: the crescent's arc corners turn 7.5 degrees and mitre to
// d / cos 3.75 = 1.002d, a true mitre, which the bevel rightly leaves alone.)
test("bevel: the crescent's and the star's sharp points reach no further than the offset (3d without it)", () => {
  for (const shape of ["crescent", "star"]) for (const mm of OFFSETS_MM) {
    const input = SHAPES[shape](), d = mm * PX_PER_MM;
    const on = reachOf(input, DG.offsetRing(input, d, true, BEVEL), d);
    assert.ok(on <= 1.01, `${shape} out ${mm} mm: reaches ${on.toFixed(3)}d`);
  }
  // and without the option the crescent's cusp takes the whole clamp, as pinned above
  const input = crescentRing();
  assert.ok(Math.abs(reachOf(input, DG.offsetRing(input, 10, true), 10) - 3) < 1e-9);
});

test("bevel, defect 55 open half: an anchor dragged 0.6 mm past the corner sews no further out than the slip plus the offset", () => {
  for (const slipPx of [6, 10, 20]) {
    const moved = DG.offsetRing(boxRing().concat([{ x: -slipPx * 0.2, y: 400 + slipPx * 0.98 }]), TERRY_PX, true, BEVEL);
    assert.ok(reachPast(moved) <= slipPx + TERRY_PX + 1e-9, `${slipPx} px slip: ${reachPast(moved).toFixed(1)} px out`);
  }
});

test("bevel, defect 55 cured half: the 1 px slip, no longer dropped, still reaches no further than the slip plus the offset", () => {
  const moved = DG.offsetRing(boxRing().concat([{ x: -0.2, y: 400.98 }]), TERRY_PX, true, BEVEL);
  assert.ok(reachPast(moved) <= 1 + TERRY_PX, `${reachPast(moved).toFixed(2)} px out`);
  assert.strictEqual(selfCrossings(moved).length, 0);
});

test("bevel: a ring with no corner past the clamp and nothing to consume comes back bit for bit as without it", () => {
  for (const mm of OFFSETS_MM) for (const outward of [true, false]) {
    assert.deepStrictEqual(DG.offsetRing(lRing(), mm * PX_PER_MM, outward, BEVEL), DG.offsetRing(lRing(), mm * PX_PER_MM, outward), `L ${outward ? "out" : "in"} ${mm} mm`);
  }
  assert.deepStrictEqual(DG.offsetRing(boxRing(), TERRY_PX, true, BEVEL), DG.offsetRing(boxRing(), TERRY_PX, true));
});

test("off is off: no options, {} and { bevel: false } are one ring", () => {
  for (const shape of Object.keys(SHAPES)) for (const mm of OFFSETS_MM) for (const outward of [true, false]) {
    const base = DG.offsetRing(SHAPES[shape](), mm * PX_PER_MM, outward);
    assert.deepStrictEqual(DG.offsetRing(SHAPES[shape](), mm * PX_PER_MM, outward, {}), base);
    assert.deepStrictEqual(DG.offsetRing(SHAPES[shape](), mm * PX_PER_MM, outward, { bevel: false }), base);
  }
});

test("buildQualityDesign: offsetBevel absent and false sew one design; true reaches the fill rings", () => {
  const FABRICS = require("../src/fabrics.js");
  const make = (extra) => DG.buildQualityDesign([{ rgb: [27, 58, 92], shapes: [{ outer: crescentRing(), holes: [], tierOverride: "fill", angleOverride: 0 }] }],
    Object.assign({ garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 10, targetWidthMm: 40, darkOnTop: false, underlay: true, fabric: FABRICS.getFabric("terry_towel") }, extra));
  const base = make({});
  assert.deepStrictEqual(make({ offsetBevel: false }).stitches, base.stitches);
  const on = make({ offsetBevel: true });
  assert.ok(on.stitchCount > 0);
  assert.notDeepStrictEqual(on.stitches, base.stitches, "the option did not reach the pull-compensated rings");
});

// When this goes red the bevelled offset has changed: re-measure and lift.
test("bevel: the pinned failure still reproduces (lift its skip when this turns red)", () => {
  const m = measure("crescent", 3, true, BEVEL);
  assert.ok(m.edgeRatio > SPIKE_RATIO, `crescent out 3mm: longest edge now ${m.edgeRatio.toFixed(3)}x: lift its skip`);
  assert.ok(Math.abs(m.edgeRatio - 2.19) < 0.01, `crescent out 3mm: ${m.edgeRatio.toFixed(3)}x, pinned at 2.19`);
});
