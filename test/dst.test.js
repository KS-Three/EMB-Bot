const assert = require("node:assert");
const { test } = require("node:test");
const dst = require("../src/dst.js");
const b = (...xs) => Uint8Array.from(xs);

test("zero stitch record", () => assert.deepStrictEqual(dst.encodeRecord(0,0,"stitch"), b(0x00,0x00,0x03)));
test("color change record", () => assert.deepStrictEqual(dst.encodeRecord(0,0,"color"), b(0x00,0x00,0x43)));
test("jump record", () => assert.deepStrictEqual(dst.encodeRecord(0,0,"jump"), b(0x00,0x00,0x83)));
test("dx=1", () => assert.deepStrictEqual(dst.encodeRecord(1,0,"stitch"), b(0x80,0x00,0x03)));
test("dx=-1", () => assert.deepStrictEqual(dst.encodeRecord(-1,0,"stitch"), b(0x40,0x00,0x03)));
test("dy=1", () => assert.deepStrictEqual(dst.encodeRecord(0,1,"stitch"), b(0x01,0x00,0x03)));
test("dx=9", () => assert.deepStrictEqual(dst.encodeRecord(9,0,"stitch"), b(0x20,0x00,0x03)));
test("dx=13 = 9+3+1", () => assert.deepStrictEqual(dst.encodeRecord(13,0,"stitch"), b(0xA0,0x80,0x03)));
test("dx=121 max", () => assert.deepStrictEqual(dst.encodeRecord(121,0,"stitch"), b(0xA0,0xA0,0x23)));
test("dx=2 = +3-1", () => assert.deepStrictEqual(dst.encodeRecord(2,0,"stitch"), b(0x40,0x80,0x03)));
test("dx=5 = +9-3-1", () => assert.deepStrictEqual(dst.encodeRecord(5,0,"stitch"), b(0x60,0x40,0x03)));
test("dy=2 = +3-1", () => assert.deepStrictEqual(dst.encodeRecord(0,2,"stitch"), b(0x02,0x01,0x03)));
test("end record", () => assert.deepStrictEqual(dst.endRecord(), b(0x00,0x00,0xF3)));
test("header is 512 bytes and contains ST field", () => {
  const h = dst.buildHeader({ label:"TEST", stitchCount:5, colorCount:1, xMin:-10,xMax:10,yMin:-5,yMax:5 });
  assert.strictEqual(h.length, 512);
  const s = Buffer.from(h).toString("latin1");
  assert.ok(s.includes("LA:TEST"));
  assert.ok(s.includes("ST:0000005"));
  assert.ok(s.includes("CO:001"));
});
test("encodeDST splits large jump >121", () => {
  const design = { stitches:[{x:0,y:0,type:"stitch"},{x:300,y:0,type:"stitch"}], colors:[{r:0,g:0,b:0,name:"a"}] };
  const out = dst.encodeDST(design);
  // 512 header + N*3 + end(3); N includes split intermediate records
  assert.strictEqual((out.length - 512) % 3, 0);
  assert.deepStrictEqual(out.slice(-3), b(0x00,0x00,0xF3));
});
// Inverse of the authoritative X weight table: [byteIndex] -> {mask: signedWeight}
const X_DECODE = [
  { 0x80: 1, 0x40: -1, 0x20: 9, 0x10: -9 }, // byte0
  { 0x80: 3, 0x40: -3, 0x20: 27, 0x10: -27 }, // byte1
  { 0x20: 81, 0x10: -81 }, // byte2
];
const Y_DECODE = [
  { 0x01: 1, 0x02: -1, 0x04: 9, 0x08: -9 }, // byte0
  { 0x01: 3, 0x02: -3, 0x04: 27, 0x08: -27 }, // byte1
  { 0x04: 81, 0x08: -81 }, // byte2
];
const decodeAxis = (rec, TABLE) => {
  let v = 0;
  for (let bi = 0; bi < 3; bi++) {
    for (const maskStr of Object.keys(TABLE[bi])) {
      const mask = Number(maskStr);
      if (rec[bi] & mask) v += TABLE[bi][mask];
    }
  }
  return v;
};
// Iterate 3-byte body records (skip 512 header, stop at end record 0xF3).
const bodyRecords = (out) => {
  const recs = [];
  for (let off = 512; off + 3 <= out.length; off += 3) {
    const rec = out.slice(off, off + 3);
    if (rec[0] === 0x00 && rec[1] === 0x00 && rec[2] === 0xF3) break;
    recs.push(rec);
  }
  return recs;
};

test("encodeDST records sum to correct total displacement (x=300)", () => {
  const design = { stitches:[{x:0,y:0,type:"stitch"},{x:300,y:0,type:"stitch"}], colors:[{r:0,g:0,b:0,name:"a"}] };
  const out = dst.encodeDST(design);
  let totalDx = 0;
  for (const rec of bodyRecords(out)) totalDx += decodeAxis(rec, X_DECODE);
  assert.strictEqual(totalDx, 300);
});

test("trim zero-delta emits exactly 3 jump records [0x00,0x00,0x83]", () => {
  const design = { stitches:[{x:0,y:0,type:"stitch"},{x:0,y:0,type:"trim"}], colors:[{r:0,g:0,b:0,name:"a"}] };
  const recs = bodyRecords(dst.encodeDST(design));
  // record 0 is the initial stitch (0,0); the trim (same position) yields 3 jumps
  const trimRecs = recs.slice(1);
  assert.strictEqual(trimRecs.length, 3, "trim should emit exactly 3 jump records");
  for (const r of trimRecs) assert.deepStrictEqual(Array.from(r), [0x00, 0x00, 0x83]);
});

test("trim small delta emits 3 jump records whose deltas sum to the move", () => {
  const design = { stitches:[{x:0,y:0,type:"stitch"},{x:30,y:-18,type:"trim"}], colors:[{r:0,g:0,b:0,name:"a"}] };
  const recs = bodyRecords(dst.encodeDST(design));
  const trimRecs = recs.slice(1);
  assert.strictEqual(trimRecs.length, 3, "small-delta trim should emit exactly 3 jump records");
  let sx = 0, sy = 0;
  for (const r of trimRecs) {
    assert.ok(r[2] & 0x80, "each trim record must be jump-flagged");
    sx += decodeAxis(r, X_DECODE); sy += decodeAxis(r, Y_DECODE);
  }
  assert.strictEqual(sx, 30);
  assert.strictEqual(sy, -18);
});

test("trim huge delta (>363) emits >=3 jump records, all jump-flagged, sum correct", () => {
  const design = { stitches:[{x:0,y:0,type:"stitch"},{x:900,y:-500,type:"trim"}], colors:[{r:0,g:0,b:0,name:"a"}] };
  const recs = bodyRecords(dst.encodeDST(design));
  const trimRecs = recs.slice(1);
  assert.ok(trimRecs.length >= 3, "huge-delta trim needs >=3 records, got " + trimRecs.length);
  let sx = 0, sy = 0;
  for (const r of trimRecs) {
    assert.ok(r[2] & 0x80, "each trim record must be jump-flagged");
    const dx = decodeAxis(r, X_DECODE), dy = decodeAxis(r, Y_DECODE);
    assert.ok(Math.abs(dx) <= 121 && Math.abs(dy) <= 121, "each delta within +/-121");
    sx += dx; sy += dy;
  }
  assert.strictEqual(sx, 900);
  assert.strictEqual(sy, -500);
});
