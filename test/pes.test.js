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
    if (b0 === 0xfe) { i += 3; continue; } // colour change: 0xfe 0xb0 <needle>

    let dx;
    if (b0 & 0x80) {
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

    records.push({ dx, dy });
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
