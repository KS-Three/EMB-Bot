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
