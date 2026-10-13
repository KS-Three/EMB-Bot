// Cross-stitch arm split at the machine limit (2026-10-13, Kent: "Split at machine
// limit"; docs/crossstitch-arm-census-2026-10-13.md fix A). An arm whose per-axis
// delta exceeds one DST record is emitted as ceil(needed) collinear sub-segments.
// Nothing below the record changes, and 5.0 mm / 12.1 mm-as-length are NOT split
// points: how long an arm may float on cloth is a fabric constant (ROADMAP gate 1).
const assert = require("node:assert");
const { test } = require("node:test");
const crypto = require("node:crypto");
const CF = require("../src/crossfill.js");
const DST = require("../src/dst.js");

const SQUARE = [[0, 0], [40, 0], [40, 40], [0, 40], [0, 0]].map((p) => ({ x: p[0], y: p[1] }));
const LAT = { step: 10, offX: 0, offY: 0 };

test("crossFill: arms within maxSegPx are untouched, longer arms split collinearly with fixed ends", () => {
  const plain = CF.crossFill([SQUARE], LAT, {});
  const same = CF.crossFill([SQUARE], LAT, { maxSegPx: 10 });
  assert.deepStrictEqual(same, plain, "arm axis delta 10 is not past a limit of 10");
  const split = CF.crossFill([SQUARE], LAT, { maxSegPx: 4 });
  assert.strictEqual(split.length, plain.length);
  split.forEach((r, i) => {
    const p = plain[i].pts, q = r.pts;
    assert.deepStrictEqual([q[0], q[q.length - 1]], p, "endpoints unchanged");
    assert.strictEqual(r.jump, plain[i].jump);
    assert.strictEqual(q.length - 1, Math.ceil(Math.max(Math.abs(p[1].x - p[0].x), Math.abs(p[1].y - p[0].y)) / 4));
    for (let k = 1; k < q.length; k++) {
      assert.ok(Math.max(Math.abs(q[k].x - q[k - 1].x), Math.abs(q[k].y - q[k - 1].y)) <= 4 + 1e-9);
      const cross = (q[k].x - q[0].x) * (p[1].y - p[0].y) - (q[k].y - q[0].y) * (p[1].x - p[0].x);
      assert.ok(Math.abs(cross) < 1e-9, "collinear");
    }
  });
});

// --- design level ---------------------------------------------------------
global.window = global;
const DG = require("../src/digitize.js");
const garments = require("../src/garments.js");


const FONTS = ["egyptian", "egyptian_small", "eloquent", "eloquent_small", "heavenly",
  "heavenly_small", "jaquarda_bastarda_9", "jersey_15", "noble"];
// sha256(JSON.stringify(design.stitches)).slice(0,16) captured on main BEFORE the
// split landed (7c38818e): the split must not move a single byte at these sizes.
const BEFORE = {
  "egyptian@25": "3f4baf56b47024b3",
  "egyptian@60": "1c149457b7277c41",
  "egyptian_small@25": "3f4baf56b47024b3",
  "egyptian_small@60": "1c149457b7277c41",
  "eloquent@25": "2b27a3977a452a77",
  "eloquent@60": "c33c51161e57d049",
  "eloquent_small@25": "2b27a3977a452a77",
  "eloquent_small@60": "c33c51161e57d049",
  "heavenly@25": "00a72722bdaa6dba",
  "heavenly@60": "c7336ffdcda17878",
  "heavenly_small@25": "00a72722bdaa6dba",
  "heavenly_small@60": "c7336ffdcda17878",
  "jaquarda_bastarda_9@25": "5a535ea7e9e1c4e8",
  "jaquarda_bastarda_9@60": "cb4e4635e847acdf",
  "jersey_15@25": "3dc2cb26d0699f22",
  "jersey_15@60": "137ea9a1349a65bc",
  "noble@25": "a2dca4e8060d8ea5",
  "noble@60": "100b85f0207798cf"
};

let census;
async function tools() {
  if (!census) census = await import("../tools/small-cap-census.mjs");
  return census;
}
function build(font, text, garment, targetWidthMm) {
  return DG.buildLetteringDesign(font, text, {
    garment: garments.getGarment(garment), pxPerMm: 8, rgb: [20, 20, 20],
    weightPreset: "normal", targetWidthMm,
  });
}
function maxAxisMm(design) {
  let prev = null, was = false, m = 0;
  for (const s of design.stitches) {
    if (s.type === "end") break;
    if (s.type === "stitch") {
      if (prev && was) m = Math.max(m, Math.abs(s.x - prev.x) / 10, Math.abs(s.y - prev.y) / 10);
      prev = s; was = true;
    } else { if (s.type !== "color") prev = s; was = false; }
  }
  return m;
}

test("the satinfont limit is the encoder's record", () => {
  assert.strictEqual(DST.DST_MAX_DELTA / 10, 12.1);
});

test("byte-identical to pre-split main for the 9 fonts at 25 and 60 mm cap", async () => {
  const { loadFont, calibrate } = await tools();
  for (const name of FONTS) {
    const font = loadFont(name), cal = calibrate(font, "AB");
    for (const cap of [25, 60]) {
      const d = build(font, "AB", "full_back", cal.trialWidth * cap / cal.trialCap);
      const h = crypto.createHash("sha256").update(JSON.stringify(d.stitches)).digest("hex").slice(0, 16);
      assert.strictEqual(h, BEFORE[name + "@" + cap], name + " @ " + cap + " mm moved");
    }
  }
});

function hoop(font, text, garment) {
  return DG.buildLetteringDesign(font, text, {
    garment: garments.getGarment(garment), pxPerMm: 8, emMm: 18,
    rgb: [20, 20, 20], weightPreset: "normal", targetWidthMm: 1e4,
  });
}

test("hoop-size cap (full_back 'AB' egyptian ~250 mm): nothing past a record, X endpoints unchanged", async () => {
  const { loadFont } = await tools();
  const font = loadFont("egyptian");
  const split = hoop(font, "AB", "full_back");
  assert.ok(split.lettering.capMm > 200, "hoop-filling cap " + split.lettering.capMm);
  assert.ok(maxAxisMm(split) <= 12.1 + 1e-9, "max axis " + maxAxisMm(split));

  // Same build with the split switched off (the engine calls crossFill through the module).
  const orig = CF.crossFill;
  CF.crossFill = (r, l, o) => orig(r, l, Object.assign({}, o, { maxSegPx: 0 }));
  let plain;
  try { plain = hoop(font, "AB", "full_back"); } finally { CF.crossFill = orig; }
  assert.ok(maxAxisMm(plain) > 12.1, "the unsplit build does exceed a record");
  assert.ok(split.stitches.length > plain.stitches.length, "extra penetrations were added");

  // Every unsplit stitch survives in order; every added one lies on the segment
  // between its neighbours (0.1 mm DST rounding allowed).
  const U = plain.stitches.filter((s) => s.type !== "end"), S = split.stitches.filter((s) => s.type !== "end");
  let j = 0;
  for (let i = 0; i < S.length; i++) {
    const u = U[j];
    if (u && S[i].type === u.type && S[i].x === u.x && S[i].y === u.y) { j++; continue; }
    assert.ok(j > 0 && j < U.length, "added stitch inside the stream");
    const a = U[j - 1], b = U[j], len = Math.hypot(b.x - a.x, b.y - a.y);
    const off = Math.abs((b.x - a.x) * (S[i].y - a.y) - (b.y - a.y) * (S[i].x - a.x)) / len;
    assert.ok(off <= 1.5, "added stitch off the arm by " + off + " units");
  }
  assert.strictEqual(j, U.length, "all unsplit stitches kept, in order");
});
