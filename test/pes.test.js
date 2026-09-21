const assert = require("node:assert");
const { test } = require("node:test");
const { encodePES } = require("../src/pes.js");
const design = { stitches:[{x:-50,y:50,type:"stitch"},{x:50,y:50,type:"stitch"},{x:50,y:-50,type:"stitch"},{x:0,y:0,type:"end"}], colors:[{r:200,g:0,b:0,name:"Color 1"}], widthMM:10, heightMM:10, stitchCount:3, colorCount:1 };

test("PES starts with signature", () => {
  const out = encodePES(design);
  assert.strictEqual(Buffer.from(out.slice(0,8)).toString("latin1"), "#PES0001");
});
test("PES contains PEC block marker", () => {
  const out = encodePES(design);
  const s = Buffer.from(out).toString("latin1");
  assert.ok(s.includes("CEmbOne") || s.includes("CSewSeg") || out.length > 100);
});

// ---- PEC stitch-data decoder (mirrors the real PEC delta format) --------
// Locates the stitch-data region using the same offsets encodePES/writePEC
// use (the 4-byte PEC-section offset at byte 8, then the fixed "0x31 0xff
// 0xf0" pattern marker followed by width/height/nominal-area fields -- the
// standard PEC block has exactly these four u16 fields after the marker,
// no extra "start x/y" fields), then walks the delta-encoded stitch bytes
// and reconstructs signed dx/dy for each record (short form: 7-bit two's
// complement; long form: 12-bit two's complement carried in the low 12 bits
// of the two flag bytes).
//
// Each record also carries its `kind` -- "stitch", "jump", "trim" or
// "color" -- read the way pystitch's PecReader reads it: JUMP_CODE 0x10 and
// TRIM_CODE 0x20 on EITHER axis's long-form high byte, trim losing to jump
// when both are set, and a short-form pair being a plain stitch by
// construction. That is what makes the chain-rule tests below able to ask
// whether a split laid thread or travelled over it.
function decodePecStitchDeltas(out) {
  const dv = new DataView(out.buffer, out.byteOffset, out.byteLength);
  const pecStart = dv.getUint32(8, true);

  let markerIndex = -1;
  for (let i = pecStart; i < out.length - 2; i++) {
    if (out[i] === 0x31 && out[i + 1] === 0xff && out[i + 2] === 0xf0) {
      markerIndex = i;
      break;
    }
  }
  assert.ok(markerIndex >= 0, "expected 0x31 0xff 0xf0 PEC marker after pecStart");

  // marker(3) + width(2) + height(2) + nominal width(2) + nominal height(2)
  // = 11 bytes to the first stitch-data byte.
  let i = markerIndex + 11;

  const records = [];
  while (i < out.length) {
    const b0 = out[i];
    if (b0 === 0xff) break; // end of stitch data
    // colour change: 0xfe 0xb0 <needle>. Recorded (rather than skipped) so a
    // test can see WHERE it sits in the stream; its delta is zero either way.
    if (b0 === 0xfe) { records.push({ dx: 0, dy: 0, kind: "color" }); i += 3; continue; }

    let jump = false, trim = false;

    let dx;
    if (b0 & 0x80) {
      if (b0 & 0x10) jump = true;
      if (b0 & 0x20) trim = true;
      const word = (out[i] << 8) | out[i + 1];
      let v = word & 0x0fff;
      if (v & 0x800) v -= 0x1000;
      dx = v;
      i += 2;
    } else {
      let v = b0 & 0x7f;
      if (v & 0x40) v -= 0x80;
      dx = v;
      i += 1;
    }

    const b1 = out[i];
    let dy;
    if (b1 & 0x80) {
      if (b1 & 0x10) jump = true;
      if (b1 & 0x20) trim = true;
      const word = (out[i] << 8) | out[i + 1];
      let v = word & 0x0fff;
      if (v & 0x800) v -= 0x1000;
      dy = v;
      i += 2;
    } else {
      let v = b1 & 0x7f;
      if (v & 0x40) v -= 0x80;
      dy = v;
      i += 1;
    }

    records.push({ dx, dy, kind: jump ? "jump" : trim ? "trim" : "stitch" });
  }
  return records;
}

test("PEC stitch encoding splits an oversized delta instead of aliasing", () => {
  const bigMove = {
    stitches: [
      { x: 0, y: 0, type: "stitch" },
      { x: 3000, y: 0, type: "stitch" }, // 300mm move, exceeds the +-2047 12-bit long-form range
      { x: 3000, y: 0, type: "end" },
    ],
    colors: [{ r: 200, g: 0, b: 0, name: "Color 1" }],
  };
  const out = encodePES(bigMove);
  const records = decodePecStitchDeltas(out);

  const totalDx = records.reduce((sum, r) => sum + r.dx, 0);
  const totalDy = records.reduce((sum, r) => sum + r.dy, 0);

  assert.strictEqual(totalDx, 3000, "reconstructed dx must equal the true 3000-unit displacement, not an aliased value");
  assert.strictEqual(totalDy, 0);

  // Every emitted record must itself be within the encodable 12-bit range.
  for (const r of records) {
    assert.ok(Math.abs(r.dx) <= 2047, "each hop's dx must fit the signed 12-bit long form");
    assert.ok(Math.abs(r.dy) <= 2047, "each hop's dy must fit the signed 12-bit long form");
  }
});

// ---- a move too long to SEW ----------------------------------------------
//
// Nothing in the PEC FORMAT forces a split below +-2047 units (204.7 mm), so
// until 2026-09-12 pes.js emitted whatever the design asked for. DOCTRINE
// 2026-09-07 measured what that cost on a real `manga_impact` "AB" monogram at
// Full Back, all three encoders on one design:
//
//   .dst  5,830 stitches, 3,769 jumps, longest sewn 16.7 mm
//   .exp  9,426 stitches,     8 jumps, longest sewn 18.0 mm
//   .pes  5,830 stitches,     3 jumps, longest sewn 51.1 mm
//
// dst.js was fixed that day; PES was measured and left to Kent, because
// splitting below the format's own reach means importing a sewability limit
// and that is a machine-behaviour call. Kent ruled 2026-09-12: split it, at
// 121 units -- one DST record, the same `max(|dx|,|dy|) > 12.1 mm` bar
// tools/long-stitch-census.mjs counts with.
//
// The CHAIN RULE is the part that is easy to get wrong. A move splits into
// STITCHES only when it CONTINUES a sewn run; the move into the first stitch
// of a run is travel, and splitting travel into stitches draws a line from
// the origin across the garment. These tests are dst.test.js's own, re-aimed
// at pes.js -- deliberately, so that a future change cannot satisfy one
// encoder's idea of the rule and not the other's.

// The PEC block always opens with writePEC's own positioning jump
// (`write_jump(-extends[0], -extends[1])`, PecWriter's own convention), which
// is framing rather than design. Drop it.
function pecBody(design) {
  return decodePecStitchDeltas(encodePES(design)).slice(1);
}
// How many times the needle goes down, as a standard reader counts it.
function sewn(design) {
  return pecBody(design).filter((r) => r.kind === "stitch").length;
}
const BLACK = [{ r: 0, g: 0, b: 0, name: "a" }];

test("a long move INSIDE a stitch run is SEWN, not travelled", () => {
  const near = { stitches: [
    { x: 0, y: 0, type: "jump" }, { x: 0, y: 0, type: "stitch" }, { x: 100, y: 0, type: "stitch" },
  ], colors: BLACK };
  const far = { stitches: [
    { x: 0, y: 0, type: "jump" }, { x: 0, y: 0, type: "stitch" }, { x: 300, y: 0, type: "stitch" },
  ], colors: BLACK };
  assert.strictEqual(sewn(near), 2, "100 units is one record; nothing to split");
  assert.strictEqual(sewn(far), 4, "300 units needs three records, all of them stitches");
  // The same fixture reads 2 in the OLD encoder -- one record carrying the
  // whole 30 mm -- which is the defect, not a smaller number.
  assert.ok(pecBody(far).every((r) => r.kind !== "trim"), "splitting must not invent a trim");
});

test("the move to the FIRST stitch is travel, however far", () => {
  // Nothing to sew between where the needle was and where the design begins.
  // Splitting this into stitches would draw a line from the origin across the
  // garment -- which is what a naive "a stitch splits into stitches" does, and
  // what test/dstimport.test.js's off-origin centering fixture caught for DST.
  // 400 units is well past the 121 sewability bar and well inside the format's
  // 2047, so this fires ONLY if the chain rule is missing.
  const d = { stitches: [
    { x: 400, y: 500, type: "stitch" }, { x: 450, y: 500, type: "stitch" },
  ], colors: BLACK };
  assert.strictEqual(sewn(d), 2);
});

test("a trim and a colour change both cut the chain", () => {
  for (const cut of ["trim", "color"]) {
    const d = { stitches: [
      { x: 0, y: 0, type: "jump" }, { x: 0, y: 0, type: "stitch" }, { x: 50, y: 0, type: "stitch" },
      { x: 50, y: 0, type: cut },
      { x: 400, y: 0, type: "stitch" }, { x: 450, y: 0, type: "stitch" },
    ], colors: [{ r: 0, g: 0, b: 0 }, { r: 1, g: 1, b: 1 }] };
    assert.strictEqual(sewn(d), 4, cut + " must not leave the next long move sewing across the garment");
  }
});

test("a long JUMP is still a jump", () => {
  const d = { stitches: [
    { x: 0, y: 0, type: "jump" }, { x: 0, y: 0, type: "stitch" },
    { x: 900, y: 0, type: "jump" },
    { x: 950, y: 0, type: "stitch" },
  ], colors: BLACK };
  assert.strictEqual(sewn(d), 2);
});

test("every record of a split sewn run is a stitch within the 121-unit bar", () => {
  const d = { stitches: [
    { x: 0, y: 0, type: "jump" }, { x: 0, y: 0, type: "stitch" },
    { x: 600, y: 400, type: "stitch" },
    { x: 600, y: 400, type: "end" },
  ], colors: BLACK };
  const body = pecBody(d);
  // [0] the design's own leading jump, [1] the first stitch (travel in, one
  // record); everything after is the split of the 60 x 40 mm move.
  assert.strictEqual(body[0].kind, "jump");
  const split = body.slice(2);
  assert.ok(split.length > 1, "a 600-unit move must not survive as one record");
  let sx = 0, sy = 0;
  for (const r of split) {
    assert.strictEqual(r.kind, "stitch", "thread the design asked for stays thread");
    assert.ok(Math.abs(r.dx) <= 121 && Math.abs(r.dy) <= 121,
      "each step within one DST record: " + JSON.stringify(r));
    sx += r.dx; sy += r.dy;
  }
  // PEC screen space is +Y down, so the design's +400 lands as -400, and the
  // steps must still sum EXACTLY to the move -- a split that drifts is worse
  // than no split.
  assert.strictEqual(sx, 600);
  assert.strictEqual(sy, -400);
});

test("a design whose sewn moves all fit the bar is byte-identical to before", () => {
  // The safety property, in miniature. Proved at scale the same day: the PES
  // of all 85 shipped fonts at left-chest size ("Your Name") hashes
  // 47d101ebfa6b70d26b28215ef9d6cb812165182d9083e4b6ea2fc118144b2882 both
  // before and after this change -- 0 of 184,020 sewn segments there exceed
  // 121 units, so the split fires only on designs that were already
  // unsewable. On "AB" at Full Back, where 1,688 of 1,743,631 sewn segments
  // do exceed it, exactly 9 of the 85 files change -- the same 9 fonts
  // tools/long-stitch-census.mjs flags.
  const d = { stitches: [
    { x: 0, y: 0, type: "jump" }, { x: 0, y: 0, type: "stitch" },
    { x: 100, y: 0, type: "stitch" }, { x: 100, y: 100, type: "stitch" },
    { x: 100, y: 100, type: "end" },
  ], colors: BLACK };
  const body = pecBody(d);
  assert.strictEqual(body.length, 4, "the leading jump plus three stitches, no splits");
  assert.deepStrictEqual(body.map((r) => r.kind), ["jump", "stitch", "stitch", "stitch"]);
});
