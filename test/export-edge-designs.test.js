// Edge DESIGNS through the three browser writers (src/dst.js, exp.js, pes.js):
// empty, a single stitch, 200 colour changes, and coordinates at the extremes
// of what each format can carry. export-writers.test.js pins header fields,
// record semantics and the empty DST/EXP file; this file adds what it does
// not: PES at the edges, and every writer at one stitch / 200 colours / the
// coordinate limits. Units are 0.1 mm.
const assert = require("node:assert");
const { test } = require("node:test");
const dst = require("../src/dst.js");
const exp = require("../src/exp.js");
const pes = require("../src/pes.js");
const { decodeDST } = require("../src/dstimport.js");

const S = (x, y, type = "stitch") => ({ x, y, type });
const colours = (n) =>
  Array.from({ length: n }, (_, i) => ({ r: (i * 37) % 256, g: (i * 91) % 256, b: (i * 17) % 256, name: "c" + i }));
const design = (stitches, n = 1) => ({ stitches, colors: colours(n) });
const header = (out) => Buffer.from(out.slice(0, 512)).toString("latin1");
const hfield = (out, key) => new RegExp(key + ":\\s*([-+]?\\d+)").exec(header(out))[1];

// 200 colour changes, two stitches in each of the 201 blocks.
function manyColours(changes) {
  const st = [S(0, 0), S(5, 3)];
  for (let i = 1; i <= changes; i++) st.push(S(5, 3, "color"), S(5 + i, 3), S(8 + i, 6));
  return design(st, changes + 1);
}

// PEC reader (the stitch block only): each record as {dx, dy, kind}, in PEC
// screen space (+Y down). records[0] is the writer's initial positioning jump.
function pecRecords(out) {
  const pecStart = new DataView(out.buffer, out.byteOffset, out.byteLength).getUint32(8, true);
  let i = pecStart;
  while (!(out[i] === 0x31 && out[i + 1] === 0xff && out[i + 2] === 0xf0)) i++;
  i += 11;
  const recs = [];
  const axis = () => {
    const b = out[i];
    if (b & 0x80) {
      let v = ((b << 8) | out[i + 1]) & 0x0fff;
      if (v & 0x800) v -= 0x1000;
      const f = b & 0x30;
      i += 2;
      return [v, f];
    }
    let v = b & 0x7f;
    if (v & 0x40) v -= 0x80;
    i += 1;
    return [v, 0];
  };
  while (out[i] !== 0xff) {
    if (out[i] === 0xfe) { recs.push({ dx: 0, dy: 0, kind: "color" }); i += 3; continue; }
    const [dx, fx] = axis();
    const [dy, fy] = axis();
    const f = fx | fy;
    recs.push({ dx, dy, kind: f & 0x10 ? "jump" : f & 0x20 ? "trim" : "stitch" });
  }
  return recs;
}
const pecPath = (out) => {
  let x = 0, y = 0;
  return pecRecords(out).slice(1).filter((r) => r.kind !== "color").map((r) => ({ x: (x += r.dx) + 0, y: 0 - (y += r.dy), kind: r.kind }));
};

// EXP reader: 2-byte moves; 4-byte 0x80 controls (0x01 colour, 0x80 trim, 0x04 jump).
function expEvents(out) {
  const ev = [];
  let x = 0, y = 0;
  const s8 = (b) => (b > 127 ? b - 256 : b);
  for (let i = 0; i < out.length; ) {
    if (out[i] === 0x80) {
      const c = out[i + 1];
      if (c === 0x01) ev.push({ kind: "color" });
      else if (c === 0x80) ev.push({ kind: "trim" });
      else {
        assert.strictEqual(c, 0x04, "unknown EXP control");
        x += s8(out[i + 2]); y += s8(out[i + 3]);
        ev.push({ kind: "jump", x, y });
      }
      i += 4;
    } else {
      x += s8(out[i]); y += s8(out[i + 1]);
      ev.push({ kind: "stitch", x, y });
      i += 2;
    }
  }
  return ev;
}

// ---- empty ---------------------------------------------------------------

test("empty design: PES is a valid container with no stitch records, not a throw", () => {
  for (const d of [design([]), design([S(0, 0, "end")]), { stitches: [], colors: [] }, undefined, {}]) {
    const out = pes.encodePES(d);
    assert.strictEqual(Buffer.from(out.slice(0, 8)).toString("latin1"), "#PES0001");
    assert.deepStrictEqual(pecPath(out), []);
    // The PEC pointer lands inside the file.
    assert.ok(new DataView(out.buffer, out.byteOffset).getUint32(8, true) < out.length);
  }
});

test("empty design: an undefined or stitchless design never throws in DST or EXP", () => {
  for (const d of [undefined, {}, { stitches: [] }]) {
    assert.strictEqual(exp.encodeEXP(d).length, 0);
    assert.strictEqual(dst.encodeDST(d).length, 512 + 3);
  }
});

// ---- one stitch ----------------------------------------------------------

test("one stitch: DST writes one record plus END and the importer reads one sewn stitch", () => {
  const out = dst.encodeDST(design([S(40, -25)]));
  assert.strictEqual((out.length - 512) / 3, 2, "one stitch record plus END");
  assert.strictEqual(hfield(out, "ST"), "0000002");
  // The importer centres on the first sewn point, so one stitch reads as (0,0).
  const sewn = decodeDST(out).stitches.filter((s) => s.type === "stitch");
  assert.deepStrictEqual(sewn.map((s) => [s.x, s.y]), [[0, 0]]);
  assert.deepStrictEqual(Array.from(out.slice(512, 518)), [69, 149, 3, 0, 0, 243], "the record is the (40,-25) move");
});

test("one stitch: a lone stitch at the origin writes one zero-delta record, not nothing", () => {
  const out = dst.encodeDST(design([S(0, 0)]));
  assert.strictEqual((out.length - 512) / 3, 2);
  assert.deepStrictEqual(Array.from(out.slice(512, 515)), [0, 0, 3]);
});

test("one stitch: EXP writes a 2-byte record and PES decodes to the same point", () => {
  assert.deepStrictEqual(expEvents(exp.encodeEXP(design([S(40, -25)]))).filter((e) => e.kind === "stitch").map((e) => [e.x, e.y]), [[40, -25]]);
  assert.deepStrictEqual(pecPath(pes.encodePES(design([S(40, -25)]))).map((p) => [p.x, p.y]), [[40, -25]]);
});

// ---- 200 colour changes --------------------------------------------------

test("200 colour changes: DST header CO is the 201 colours defined, and 200 colour records are written", () => {
  const out = dst.encodeDST(manyColours(200));
  // CO is colors.length (export-writers.test.js pins 2 colours -> "002").
  assert.strictEqual(hfield(out, "CO"), "201");
  const colourRecs = [];
  for (let i = 512; i + 5 < out.length; i += 3) if ((out[i + 2] & 0xc3) === 0xc3) colourRecs.push(i);
  assert.strictEqual(colourRecs.length, 200);
});

test("200 colour changes: DST round-trips every stitch, in order, with 200 colour records", () => {
  const d = manyColours(200);
  const back = decodeDST(dst.encodeDST(d)).stitches;
  assert.strictEqual(back.filter((s) => s.type === "color").length, 200);
  // The importer rebases on the first sewn point, so compare relative moves.
  const rel = (pts) => pts.map(([x, y]) => [x - pts[0][0], y - pts[0][1]]);
  const want = rel(d.stitches.filter((s) => s.type === "stitch").map((s) => [s.x, s.y]));
  assert.deepStrictEqual(rel(back.filter((s) => s.type === "stitch").map((s) => [s.x, s.y])), want);
});

test("200 colour changes: EXP carries 200 colour controls and the same sewn points", () => {
  const d = manyColours(200);
  const ev = expEvents(exp.encodeEXP(d));
  assert.strictEqual(ev.filter((e) => e.kind === "color").length, 200);
  assert.deepStrictEqual(ev.filter((e) => e.kind === "stitch").map((e) => [e.x, e.y]), d.stitches.filter((s) => s.type === "stitch").map((s) => [s.x, s.y]));
});

test("200 colour changes: PES writes 200 colour records, a 201-entry colour table and the same sewn points", () => {
  const d = manyColours(200);
  const out = pes.encodePES(d);
  assert.strictEqual(pecRecords(out).filter((r) => r.kind === "color").length, 200);
  const pecStart = new DataView(out.buffer, out.byteOffset).getUint32(8, true);
  assert.strictEqual(out[pecStart + 48], 200, "PEC stores colours minus one");
  assert.deepStrictEqual(pecPath(out).map((p) => [p.x, p.y]), d.stitches.filter((s) => s.type === "stitch").map((s) => [s.x, s.y]));
});

test("200 colour changes: the PEC needle toggle alternates 2,1,2,1 so no two colour records repeat", () => {
  const out = pes.encodePES(manyColours(200));
  const pecStart = new DataView(out.buffer, out.byteOffset).getUint32(8, true);
  const toggles = [];
  for (let i = pecStart + 512; i < out.length - 2; i++) if (out[i] === 0xfe && out[i + 1] === 0xb0) toggles.push(out[i + 2]);
  assert.ok(toggles.length >= 200);
  toggles.slice(0, 200).forEach((t, k) => assert.strictEqual(t, k % 2 === 0 ? 2 : 1));
});

test("200 colour changes with only one colour defined: no writer throws", () => {
  const d = { ...manyColours(200), colors: colours(1) };
  assert.doesNotThrow(() => dst.encodeDST(d));
  assert.doesNotThrow(() => exp.encodeEXP(d));
  assert.doesNotThrow(() => pes.encodePES(d));
});

// ---- coordinates at the extremes -----------------------------------------

// 4000 units = 400 mm, a large commercial hoop's reach.
test("±hoop extent (±400 mm): DST header extents and every stitch survive", () => {
  const M = 4000;
  const out = dst.encodeDST(design([S(-M, -M), S(M, M), S(-M, M), S(M, -M)]));
  for (const k of ["+X", "-X", "+Y", "-Y"]) assert.strictEqual(hfield(out, "\\" + k), String(M).padStart(5, "0"));
  // Long chained moves are split into <=121 stitches, so check the swept box
  // and the end point (the importer rebases on the first sewn point).
  const pts = decodeDST(out).stitches.filter((s) => s.type === "stitch");
  const xs = pts.map((s) => s.x), ys = pts.map((s) => s.y);
  assert.strictEqual(Math.max(...xs) - Math.min(...xs), 2 * M);
  assert.strictEqual(Math.max(...ys) - Math.min(...ys), 2 * M);
  assert.deepStrictEqual([pts.at(-1).x - pts[0].x, pts.at(-1).y - pts[0].y], [2 * M, 0]);
});

test("±hoop extent (±400 mm): EXP and PES land on the same points", () => {
  const M = 4000;
  const pts = [[-M, -M], [M, M], [-M, M], [M, -M]];
  const d = design(pts.map(([x, y]) => S(x, y)));
  assert.deepStrictEqual(expEvents(exp.encodeEXP(d)).filter((e) => e.kind === "stitch").length > 4, true, "long moves are split");
  const lastExp = expEvents(exp.encodeEXP(d)).filter((e) => e.kind !== "color").pop();
  assert.deepStrictEqual([lastExp.x, lastExp.y], [M, -M]);
  const path = pecPath(pes.encodePES(d));
  assert.deepStrictEqual([path.at(-1).x, path.at(-1).y], [M, -M]);
});

test("±hoop extent: no split step in any writer exceeds its format's record range", () => {
  const M = 4000;
  const d = design([S(-M, -M), S(M, M), S(-M, M)]);
  const dstOut = dst.encodeDST(d);
  for (let i = 512; i + 5 < dstOut.length; i += 3) {
    const { decodeDelta } = require("../src/dstimport.js");
    const [dx, dy] = decodeDelta(dstOut[i], dstOut[i + 1], dstOut[i + 2]);
    assert.ok(Math.abs(dx) <= 121 && Math.abs(dy) <= 121);
  }
  for (const r of pecRecords(pes.encodePES(d))) assert.ok(Math.abs(r.dx) <= 2047 && Math.abs(r.dy) <= 2047);
  for (const e of expEvents(exp.encodeEXP(d))) assert.ok(e.kind === "color" || e.kind === "trim" || Number.isFinite(e.x));
});

test("coordinates at the PEC int16 limit (±32767 = 3.27 m) still encode the right width and path", () => {
  const M = 32767;
  const out = pes.encodePES(design([S(0, 0), S(M, 0)]));
  const path = pecPath(out);
  assert.deepStrictEqual([path.at(-1).x, path.at(-1).y], [M, 0]);
  const pecStart = new DataView(out.buffer, out.byteOffset).getUint32(8, true);
  let i = pecStart;
  while (!(out[i] === 0x31 && out[i + 1] === 0xff && out[i + 2] === 0xf0)) i++;
  assert.strictEqual(new DataView(out.buffer, out.byteOffset).getInt16(i + 3, true), M);
});

test("extreme negative coordinates: DST header minus-extents are positive magnitudes", () => {
  const out = dst.encodeDST(design([S(0, 0), S(-3000, -2000)]));
  assert.strictEqual(hfield(out, "\\-X"), "03000");
  assert.strictEqual(hfield(out, "\\-Y"), "02000");
  assert.strictEqual(hfield(out, "\\+X"), "00000");
});

test("fractional coordinates do not corrupt the stream length parity", () => {
  const d = design([S(0.4, 0.6), S(10.7, -3.2), S(20.5, 7.5)]);
  assert.strictEqual(exp.encodeEXP(d).length % 2, 0);
  assert.strictEqual((dst.encodeDST(d).length - 512) % 3, 0);
  assert.doesNotThrow(() => pes.encodePES(d));
});

// ---- BUGS found by this file (todo until fixed) --------------------------

test.todo("DST header: a design wider than 99999 units (10 m) wraps the 5-digit +X/-X field (writes 00001 for 100001) instead of clamping or refusing");
test.todo("PES/PEC: a design wider than 32767 units (3.27 m) overflows the int16 width/height and CSewSeg points silently instead of throwing or clamping");
test.todo("PES: 257 or more colours wraps the PEC colour-count byte to 0 (colorCount-1 & 0xff), and the 0x1cf-wide colour table is overrun past 463 colours");
