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
test("encodeDST records sum to correct total displacement (x=300)", () => {
  const design = { stitches:[{x:0,y:0,type:"stitch"},{x:300,y:0,type:"stitch"}], colors:[{r:0,g:0,b:0,name:"a"}] };
  const out = dst.encodeDST(design);
  // Inverse of the authoritative X weight table: [byteIndex] -> {mask: signedWeight}
  const X_DECODE = [
    { 0x80: 1, 0x40: -1, 0x20: 9, 0x10: -9 }, // byte0
    { 0x80: 3, 0x40: -3, 0x20: 27, 0x10: -27 }, // byte1
    { 0x20: 81, 0x10: -81 }, // byte2
  ];
  const decodeDx = (rec) => {
    let dx = 0;
    for (let bi = 0; bi < 3; bi++) {
      for (const maskStr of Object.keys(X_DECODE[bi])) {
        const mask = Number(maskStr);
        if (rec[bi] & mask) dx += X_DECODE[bi][mask];
      }
    }
    return dx;
  };
  let totalDx = 0;
  // Iterate 3-byte records, skipping header (512) and stopping before end record 0xF3.
  for (let off = 512; off + 3 <= out.length; off += 3) {
    const rec = out.slice(off, off + 3);
    if (rec[0] === 0x00 && rec[1] === 0x00 && rec[2] === 0xF3) break; // end record
    totalDx += decodeDx(rec);
  }
  assert.strictEqual(totalDx, 300);
});
