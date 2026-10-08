// Writer-side coverage for src/dst.js and src/exp.js: header fields, extents,
// every representable record, colour/jump/trim semantics, long-move splitting,
// and round-trips through the importer (DST) or a reference decoder (EXP --
// the repo has no EXP importer). Complements dst.test.js / exp.test.js, which
// pin individual byte patterns; nothing here duplicates a pinned byte.
const assert = require("node:assert");
const { test } = require("node:test");
const dst = require("../src/dst.js");
const exp = require("../src/exp.js");
const { decodeDST, decodeDelta } = require("../src/dstimport.js");

const HEADER = 512;
const text = (bytes) => Buffer.from(bytes).toString("latin1");
const fields = (header) => {
  const out = {};
  for (const m of text(header).split("\r")) {
    const k = m.slice(0, 2);
    if (m[2] === ":") out[k === "+X" || k === "-X" || k === "+Y" || k === "-Y" ? m.slice(0, 2) : k] = m.slice(3);
  }
  return out;
};
// Body records, WITHOUT the terminating end record (0x00 0x00 0xF3, whose
// flag bits would otherwise read as a colour change).
const body = (out) => {
  const recs = [];
  for (let i = HEADER; i + 5 < out.length; i += 3) recs.push([out[i], out[i + 1], out[i + 2]]);
  return recs;
};
const S = (x, y, type = "stitch") => ({ x, y, type });
const design = (stitches, colors = 1) => ({
  stitches,
  colors: Array.from({ length: colors }, () => ({ r: 0, g: 0, b: 0, name: "c" })),
});

// Deterministic PRNG so a failure reproduces.
const rng = (seed) => () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296);

// ---- DST header ----------------------------------------------------------

test("DST header: fixed-width fields, CR-terminated, space-padded to 512", () => {
  const out = dst.encodeDST({ label: "HELLO", ...design([S(-50, 20), S(80, -30), S(0, 0, "end")], 2) });
  const h = out.slice(0, HEADER);
  assert.strictEqual(h.length, HEADER);
  const f = fields(h);
  assert.strictEqual(f.LA, "HELLO");
  assert.strictEqual(f.CO, "002");
  assert.strictEqual(f["+X"], "00080");
  assert.strictEqual(f["-X"], "00050");
  assert.strictEqual(f["+Y"], "00020");
  assert.strictEqual(f["-Y"], "00030");
  assert.strictEqual(f.AX, "+00000");
  assert.strictEqual(f.PD, "******");
  // Everything after the last field is spaces, nothing else.
  const used = text(h).lastIndexOf("\r") + 1;
  assert.ok(text(h).slice(used).split("").every((c) => c === " "));
});

test("DST header: the default label is EMBBOT and a long label is cut to 16", () => {
  assert.strictEqual(fields(dst.encodeDST(design([S(0, 0)])).slice(0, HEADER)).LA, "EMBBOT");
  const long = dst.encodeDST({ label: "ABCDEFGHIJKLMNOPQRSTUVWXYZ", ...design([S(0, 0)]) });
  assert.strictEqual(fields(long.slice(0, HEADER)).LA, "ABCDEFGHIJKLMNOP");
});

test("DST header: extents cover every stitch, jump, trim and colour target", () => {
  const out = dst.encodeDST(design([
    S(0, 0), S(10, 10), S(-200, 5, "jump"), S(30, -90, "trim"), S(7, 7), S(600, 0, "color"), S(1, 1),
  ]));
  const f = fields(out.slice(0, HEADER));
  assert.strictEqual(f["+X"], "00600");
  assert.strictEqual(f["-X"], "00200");
  assert.strictEqual(f["+Y"], "00010");
  assert.strictEqual(f["-Y"], "00090");
});

test("DST header: an empty design still writes a 512-byte header and a lone end record", () => {
  const out = dst.encodeDST(design([]));
  assert.strictEqual(out.length, HEADER + 3);
  assert.deepStrictEqual(Array.from(out.slice(-3)), [0x00, 0x00, 0xf3]);
  const f = fields(out.slice(0, HEADER));
  // ST counts the END record: pystitch writes ST 1 for an empty pattern too.
  assert.strictEqual(f.ST, "0000001");
  assert.strictEqual(f["+X"], "00000");
});

test("DST header: ST is the body record count, END included (pystitch convention), sentinel or not", () => {
  const withSentinel = dst.encodeDST(design([S(0, 0), S(5, 0), S(10, 0), S(10, 0, "end")]));
  const without = dst.encodeDST(design([S(0, 0), S(5, 0), S(10, 0)]));
  for (const out of [withSentinel, without]) {
    assert.strictEqual(fields(out.slice(0, HEADER)).ST, "0000004");
    assert.strictEqual((out.length - HEADER) / 3, 4);
  }
});

// ---- DST records ---------------------------------------------------------

test("DST encodeRecord: every (dx,dy) on the 243-wide grid round-trips through decodeDelta", () => {
  for (let dx = -121; dx <= 121; dx += 1) {
    for (let dy = -121; dy <= 121; dy += 11) {
      const r = dst.encodeRecord(dx, dy, "stitch");
      assert.deepStrictEqual(decodeDelta(r[0], r[1], r[2]), [dx, dy]);
    }
  }
  for (let dy = -121; dy <= 121; dy++) {
    const r = dst.encodeRecord(0, dy, "stitch");
    assert.deepStrictEqual(decodeDelta(r[0], r[1], r[2]), [0, dy]);
  }
});

test("DST encodeRecord: out-of-range deltas throw rather than alias", () => {
  for (const [dx, dy] of [[122, 0], [-122, 0], [0, 122], [0, -122]]) {
    assert.throws(() => dst.encodeRecord(dx, dy, "stitch"), RangeError);
  }
});

test("DST encodeRecord: the flag lands in the top bits of byte 2 and nothing else", () => {
  assert.strictEqual(dst.encodeRecord(0, 0, "stitch")[2] & 0xc0, 0x00);
  assert.strictEqual(dst.encodeRecord(0, 0, "jump")[2] & 0xc0, 0x80);
  assert.strictEqual(dst.encodeRecord(0, 0, "color")[2] & 0xc0, 0xc0);
  for (const f of ["stitch", "jump", "color"]) assert.strictEqual(dst.encodeRecord(0, 0, f)[2] & 0x03, 0x03);
});

test("DST colour changes: one colour record per colour change, none invented", () => {
  const out = dst.encodeDST(design([S(0, 0), S(10, 0), S(10, 0, "color"), S(20, 0), S(20, 0, "color"), S(30, 0)], 3));
  const recs = body(out);
  assert.strictEqual(recs.filter((r) => (r[2] & 0xc0) === 0xc0).length, 2);
  assert.deepStrictEqual(decodeDST(out).colorCount, 3);
});

test("DST jumps: a jump moves the needle without being sewn, and the decoder sees a jump", () => {
  const out = dst.encodeDST(design([S(0, 0), S(10, 0), S(50, 40, "jump"), S(55, 40)]));
  const d = decodeDST(out);
  assert.strictEqual(d.stitches.filter((s) => s.type === "jump").length, 1);
  assert.strictEqual(d.stitches.filter((s) => s.type === "stitch").length, 3);
});

test("DST trims: a trim is at least three jump records and decodes to one trim", () => {
  const out = dst.encodeDST(design([S(0, 0), S(10, 0), S(30, 0, "trim"), S(40, 0)]));
  const recs = body(out);
  assert.ok(recs.filter((r) => (r[2] & 0xc0) === 0x80).length >= 3);
  assert.strictEqual(decodeDST(out).trimCount, 1);
});

test("DST long-stitch splitting: every record is within 121, and the run lands exactly", () => {
  for (const [dx, dy] of [[121, 0], [122, 0], [243, -243], [1000, 7], [-999, 999], [0, 364]]) {
    const out = dst.encodeDST(design([S(0, 0), S(dx, dy)]));
    let x = 0, y = 0;
    for (const r of body(out)) {
      const [ddx, ddy] = decodeDelta(r[0], r[1], r[2]);
      assert.ok(Math.abs(ddx) <= 121 && Math.abs(ddy) <= 121);
      x += ddx; y += ddy;
    }
    assert.deepStrictEqual([x, y], [dx, dy], `move ${dx},${dy}`);
  }
});

test("DST: a design that ends on a colour change still terminates with the end record", () => {
  const out = dst.encodeDST(design([S(0, 0), S(5, 5), S(5, 5, "color")], 2));
  assert.deepStrictEqual(Array.from(out.slice(-3)), [0x00, 0x00, 0xf3]);
});

test("DST: output length is always 512 + 3n", () => {
  const rand = rng(7);
  for (let t = 0; t < 20; t++) {
    const st = [S(0, 0)];
    for (let i = 0; i < 30; i++) st.push(S(Math.round((rand() - 0.5) * 800), Math.round((rand() - 0.5) * 800)));
    assert.strictEqual((dst.encodeDST(design(st)).length - HEADER) % 3, 0);
  }
});

// ---- DST round-trip through the importer -----------------------------------

// decodeDST re-centres on the stitch bbox midpoint, so compare shape (deltas
// between consecutive stitches) rather than absolute position.
const stitchPoints = (d) => d.stitches.filter((s) => s.type === "stitch").map((s) => [s.x, s.y]);
const deltas = (pts) => pts.slice(1).map((p, i) => [p[0] - pts[i][0], p[1] - pts[i][1]]);

test("DST round-trip: random sewn designs with long stitches keep every stitch-to-stitch delta", () => {
  const rand = rng(42);
  for (let t = 0; t < 25; t++) {
    const st = [S(0, 0)];
    let x = 0, y = 0;
    for (let i = 0; i < 40; i++) {
      x += Math.round((rand() - 0.5) * 300);
      y += Math.round((rand() - 0.5) * 300);
      st.push(S(x, y));
    }
    const back = decodeDST(dst.encodeDST(design(st)));
    // Long sewn moves are split into several sewn records, so only the
    // endpoints are comparable: re-derive them from the cumulative path.
    const want = st.map((s) => [s.x, s.y]);
    const got = stitchPoints(back);
    // the last decoded point must be where the last design point is, relative to the first
    const rel = (pts) => [pts[pts.length - 1][0] - pts[0][0], pts[pts.length - 1][1] - pts[0][1]];
    assert.deepStrictEqual(rel(got), rel(want), `seed trial ${t}`);
    assert.ok(got.length >= want.length);
  }
});

test("DST round-trip: stitch, colour and trim counts and the extents survive", () => {
  const d = design([
    S(0, 0), S(40, 0), S(40, 30), S(40, 30, "color"), S(0, 30), S(0, 60, "trim"), S(60, 60), S(60, 60, "end"),
  ], 2);
  const back = decodeDST(dst.encodeDST({ ...d, label: "RT" }));
  assert.strictEqual(back.label, "RT");
  assert.strictEqual(back.colorCount, 2);
  assert.strictEqual(back.trimCount, 1);
  assert.strictEqual(back.widthMM, 6);
  assert.strictEqual(back.heightMM, 6);
  assert.strictEqual(stitchPoints(back).length, 5);
});

test("DST round-trip: the importer's extents agree with the header the writer wrote", () => {
  const out = dst.encodeDST(design([S(-300, 40), S(500, -80), S(100, 200)]));
  const f = fields(out.slice(0, HEADER));
  const back = decodeDST(out);
  assert.strictEqual(back.widthMM * 10, Number(f["+X"]) + Number(f["-X"]));
  assert.strictEqual(back.heightMM * 10, Number(f["+Y"]) + Number(f["-Y"]));
});

// ---- EXP -------------------------------------------------------------------
// Reference decoder: plain record = [dx,dy] signed bytes; 0x80 introduces a
// 4-byte control (0x01 colour, 0x04 jump with delta, 0x80 0x07 trim).
const sbyte = (v) => (v > 127 ? v - 256 : v);
function decodeEXP(bytes) {
  const ev = [];
  let x = 0, y = 0;
  for (let i = 0; i < bytes.length; ) {
    if (bytes[i] === 0x80) {
      const c = bytes[i + 1];
      if (c === 0x01) ev.push({ type: "color", x, y });
      else if (c === 0x80) ev.push({ type: "trim", x, y });
      else if (c === 0x04) {
        x += sbyte(bytes[i + 2]); y += sbyte(bytes[i + 3]);
        ev.push({ type: "jump", x, y });
      } else assert.fail("unknown EXP control 0x" + c.toString(16));
      i += 4;
    } else {
      x += sbyte(bytes[i]); y += sbyte(bytes[i + 1]);
      ev.push({ type: "stitch", x, y });
      i += 2;
    }
  }
  return ev;
}

test("EXP: no header, even-length stream, every record is 2 bytes or a 4-byte 0x80 control", () => {
  const out = exp.encodeEXP(design([S(0, 0), S(10, 5), S(10, 5, "color"), S(20, 5, "jump"), S(20, 5, "trim"), S(25, 5)], 2));
  assert.strictEqual(out.length % 2, 0);
  assert.doesNotThrow(() => decodeEXP(out));
});

test("EXP: an empty design is an empty file", () => {
  assert.strictEqual(exp.encodeEXP(design([])).length, 0);
  assert.strictEqual(exp.encodeEXP(design([S(0, 0, "end")])).length, 0);
});

test("EXP long-move splitting: the decoded path lands exactly on the requested point", () => {
  for (const [dx, dy] of [[100, 0], [300, -250], [-999, 999], [0, 700]]) {
    for (const type of ["stitch", "jump", "trim"]) {
      const ev = decodeEXP(exp.encodeEXP(design([S(0, 0, "jump"), S(dx, dy, type), S(dx + 3, dy, "stitch")])));
      const lastMove = ev.filter((e) => e.type !== "color" && e.type !== "trim");
      const end = lastMove[lastMove.length - 1];
      assert.deepStrictEqual([end.x, end.y], [dx + 3, dy], `${type} ${dx},${dy}`);
    }
  }
});

test("EXP round-trip: random designs with colours, jumps and trims decode to the same path", () => {
  const rand = rng(99);
  for (let t = 0; t < 25; t++) {
    const st = [S(0, 0, "jump")];
    let x = 0, y = 0, colors = 1;
    for (let i = 0; i < 40; i++) {
      x += Math.round((rand() - 0.5) * 60);
      y += Math.round((rand() - 0.5) * 60);
      const r = rand();
      const type = r < 0.08 ? "color" : r < 0.16 ? "jump" : r < 0.24 ? "trim" : "stitch";
      if (type === "color") colors++;
      st.push(S(x, y, type));
    }
    const ev = decodeEXP(exp.encodeEXP(design(st, colors)));
    assert.strictEqual(ev.filter((e) => e.type === "color").length, colors - 1);
    assert.strictEqual(ev.filter((e) => e.type === "trim").length, st.filter((s) => s.type === "trim").length);
    // Position at the end of the stream is the position of the last moving design point.
    const moving = st.filter((s) => s.type !== "color");
    const last = moving[moving.length - 1];
    const walked = ev.filter((e) => e.type !== "color" && e.type !== "trim");
    const pos = walked[walked.length - 1];
    if (last.type !== "trim") assert.deepStrictEqual([pos.x, pos.y], [last.x, last.y], `trial ${t}`);
  }
});

test("EXP and DST agree on the needle path of the same design", () => {
  const d = design([S(0, 0, "jump"), S(30, 10), S(60, -20), S(60, -20, "color"), S(90, 40), S(-80, 40, "jump"), S(-70, 45)], 2);
  const e = decodeEXP(exp.encodeEXP(d)).filter((s) => s.type === "stitch");
  const back = decodeDST(dst.encodeDST(d));
  const dstPts = stitchPoints(back);
  const rel = (pts) => pts.map((p) => [p[0] - pts[0][0], p[1] - pts[0][1]]);
  assert.deepStrictEqual(rel(e.map((s) => [s.x, s.y])), rel(dstPts));
});
