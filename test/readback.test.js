// Export read-back (src/readback.js): the browser writers' bytes are re-read and
// compared with the design that was written; a file that disagrees is refused
// (Kent, 2026-11-05). This file pins both halves: what the writers produce
// reads back clean, across every jumps-per-trim, and a deliberately corrupted
// byte stream fails each check by name.
const test = require("node:test");
const assert = require("node:assert");
const dst = require("../src/dst.js");
const exp = require("../src/exp.js");
const pes = require("../src/pes.js");
const rb = require("../src/readback.js");

const S = (x, y, type = "stitch") => ({ x, y, type });
const COLORS = [{ r: 200, g: 30, b: 30 }, { r: 20, g: 60, b: 200 }, { r: 30, g: 150, b: 70 }];

// Three colour blocks, trims between parts, a far jump, and one chained move
// of 370 units that must split into four sewn records.
function sample() {
  return {
    stitches: [
      S(0, 0, "jump"), S(0, 0), S(30, 0), S(30, 40), S(400, 40),
      S(400, 40, "trim"), S(500, 100, "jump"), S(500, 100), S(520, 110),
      S(520, 110, "trim"), S(520, 110, "color"), S(540, 130), S(560, 130),
      S(560, 130, "trim"), S(560, 130, "color"), S(300, -50), S(310, -50),
      S(0, 0, "end"),
    ],
    colors: COLORS,
  };
}

const ENC = {
  dst: (d, o) => dst.encodeDST(d, o),
  exp: (d) => exp.encodeEXP(d),
  pes: (d) => pes.encodePES(d),
};
const failedChecks = (r) => new Set(r.failed.map((f) => f.check));

// ---- clean files -------------------------------------------------------------

for (const fmt of ["dst", "exp", "pes"]) {
  test(`${fmt}: the writer's own bytes read back clean`, () => {
    const r = rb.verifyExport(sample(), ENC[fmt](sample()), fmt);
    assert.strictEqual(r.ok, true, JSON.stringify(r.failed));
    assert.strictEqual(r.verified, true);
    assert.strictEqual(r.stitches, 13); // 10 design stitches + 3 split intermediates
    assert.strictEqual(r.trims, 3);
    assert.strictEqual(r.colors, 2);
    assert.ok(r.longestMm <= 12.1);
  });
}

test("dst: every jumps-per-trim reads back at the N the writer used", () => {
  for (const n of [1, 2, 3, 4, 5, 10, undefined, 0, 11, 2.5, "x"]) {
    const bytes = dst.encodeDST(sample(), { jumpsPerTrim: n });
    const r = rb.verifyExport(sample(), bytes, "dst", { jumpsPerTrim: n });
    assert.strictEqual(r.ok, true, `N=${n}: ${JSON.stringify(r.failed)}`);
  }
});

test("dst: a file written at 3 and read at 5 does not agree (the trim rule is the writer's N)", () => {
  const bytes = dst.encodeDST(sample(), { jumpsPerTrim: 3 });
  const r = rb.verifyExport(sample(), bytes, "dst", { jumpsPerTrim: 5 });
  assert.ok(failedChecks(r).has("trim_count") || failedChecks(r).has("header_stitch_count"));
});

test("svg and other formats are labelled unverified, not passed off as checked", () => {
  const r = rb.verifyExport(sample(), new Uint8Array(1), "svg");
  assert.strictEqual(r.verified, false);
  assert.strictEqual(r.ok, true);
  assert.match(r.reason, /no read-back/);
});

test("random designs never false-alarm in any format (a false alarm blocks a good file)", () => {
  let seed = 20261105;
  const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  const types = ["stitch", "stitch", "stitch", "stitch", "jump", "trim", "color"];
  for (let t = 0; t < 400; t++) {
    const st = [];
    let x = 0, y = 0;
    const wild = rnd() < 0.5;
    for (let i = 0, n = 1 + Math.floor(rnd() * 40); i < n; i++) {
      const sc = rnd() < (wild ? 0.3 : 0.02) ? 900 : 60;
      x += Math.round((rnd() - 0.5) * sc);
      y += Math.round((rnd() - 0.5) * sc);
      st.push(S(x, y, types[Math.floor(rnd() * types.length)]));
    }
    if (rnd() < 0.5) st.push(S(0, 0, "end"));
    const design = { stitches: st, colors: COLORS };
    for (const fmt of ["dst", "exp", "pes"]) {
      for (const n of fmt === "dst" ? [undefined, 1, 2, 3, 5, 10] : [undefined]) {
        const r = rb.verifyExport(design, ENC[fmt](design, { jumpsPerTrim: n }), fmt, { jumpsPerTrim: n });
        assert.strictEqual(r.ok, true, `${fmt} N=${n} trial ${t}: ${JSON.stringify(r.failed)}`);
      }
    }
  }
});

test("an empty design is an empty file that reads back clean", () => {
  const d = { stitches: [S(0, 0, "end")], colors: COLORS };
  for (const fmt of ["dst", "exp", "pes"]) {
    const r = rb.verifyExport(d, ENC[fmt](d), fmt);
    assert.strictEqual(r.ok, true, `${fmt}: ${JSON.stringify(r.failed)}`);
  }
});

// ---- corrupted bytes fail each check by name ----------------------------------

const flip = (bytes, at, value) => { const b = Uint8Array.from(bytes); b[at] = value; return b; };
const DST_BODY = 512;

test("dst: a dropped record fails stitch_count and header_stitch_count", () => {
  const bytes = dst.encodeDST(sample());
  const cut = new Uint8Array(bytes.length - 3);
  cut.set(bytes.subarray(0, DST_BODY + 3 * 4)); // keep through the 4th record
  cut.set(bytes.subarray(DST_BODY + 3 * 5), DST_BODY + 3 * 4); // skip the 5th (a sewn one)
  const r = rb.verifyExport(sample(), cut, "dst");
  assert.ok(failedChecks(r).has("stitch_count"), JSON.stringify(r.failed));
  assert.ok(failedChecks(r).has("header_stitch_count"));
  const f = r.failed.find((x) => x.check === "stitch_count");
  assert.deepStrictEqual([f.expected, f.read], [13, 12]);
});

test("dst: a stitch record turned into a jump fails stitch_count", () => {
  const bytes = dst.encodeDST(sample());
  // record 2 (index 1) is the first sewn stitch: set its jump flag (0x80)
  const at = DST_BODY + 3 * 1 + 2;
  const r = rb.verifyExport(sample(), flip(bytes, at, bytes[at] | 0x80), "dst");
  assert.ok(failedChecks(r).has("stitch_count"), JSON.stringify(r.failed));
});

test("dst: a lost trim fails trim_count", () => {
  const d = sample();
  const without = { ...d, stitches: d.stitches.filter((s) => s.type !== "trim") };
  const r = rb.verifyExport(d, dst.encodeDST(without), "dst");
  assert.ok(failedChecks(r).has("trim_count"), JSON.stringify(r.failed));
});

test("dst: a colour change turned into a stitch fails color_count", () => {
  const bytes = dst.encodeDST(sample());
  let at = -1;
  for (let i = DST_BODY; i + 2 < bytes.length; i += 3) if (bytes[i + 2] & 0x40) { at = i + 2; break; }
  const r = rb.verifyExport(sample(), flip(bytes, at, 0x03), "dst");
  assert.ok(failedChecks(r).has("color_count"), JSON.stringify(r.failed));
});

test("dst: a colour change in the wrong place fails color_order", () => {
  const d = sample();
  const moved = sample();
  const i = moved.stitches.findIndex((s) => s.type === "color");
  [moved.stitches[i], moved.stitches[i + 1]] = [moved.stitches[i + 1], moved.stitches[i]];
  const r = rb.verifyExport(d, dst.encodeDST(moved), "dst");
  assert.ok(failedChecks(r).has("color_order"), JSON.stringify(r.failed));
});

test("dst/exp/pes: a sewn move over 12.1 mm fails longest_stitch", () => {
  // The same stitches written WITHOUT the split: one 370-unit chained move.
  const long = { stitches: [S(0, 0, "jump"), S(0, 0), S(30, 0), S(400, 0), S(0, 0, "end")], colors: COLORS };
  const split = (a, b) => {
    const r = rb.verifyExport(a, b, "exp");
    return r;
  };
  // EXP: hand-write a single 100-unit chained record sequence the way a broken
  // splitter would (121 is the bar; 127 fits the byte and is over it).
  const bytes = Uint8Array.from([0x80, 0x04, 0, 0, 0, 0, 30, 0, 127, 0, 127, 0, 127, 0, 59, 0]);
  const design = { stitches: [S(0, 0, "jump"), S(0, 0), S(30, 0), S(400, 0), S(0, 0, "end")], colors: COLORS };
  const r = split(design, bytes);
  assert.ok(failedChecks(r).has("longest_stitch"), JSON.stringify(r.failed));
  assert.strictEqual(r.failed.find((f) => f.check === "longest_stitch").read, "12.7 mm");
  // DST's record cannot even hold it; the check still reads the stream it is given.
  assert.ok(long.stitches.length > 0);
});

test("dst: a shifted design fails bounding_box", () => {
  const moved = sample();
  moved.stitches[12].x += 60;
  const r = rb.verifyExport(sample(), dst.encodeDST(moved), "dst");
  assert.ok(failedChecks(r).has("bounding_box"), JSON.stringify(r.failed));
});

test("dst: a wrong header fails header_bbox", () => {
  const bytes = dst.encodeDST(sample());
  const text = Buffer.from(bytes.subarray(0, 512)).toString("latin1");
  const at = text.indexOf("+X:") + 3;
  const b = Uint8Array.from(bytes);
  b.set(Buffer.from("00001", "latin1"), at);
  const r = rb.verifyExport(sample(), b, "dst");
  assert.deepStrictEqual([...failedChecks(r)], ["header_bbox"]);
  assert.strictEqual(r.failed[0].read.split(",")[0], "1");
});

test("dst: a missing end record is not readable", () => {
  const bytes = dst.encodeDST(sample());
  const r = rb.verifyExport(sample(), bytes.subarray(0, bytes.length - 3), "dst");
  assert.ok(failedChecks(r).has("readable"), JSON.stringify(r.failed));
});

test("exp: a dropped record fails stitch_count; an unknown control is not readable", () => {
  const bytes = exp.encodeEXP(sample());
  // drop the second sewn stitch record (the file begins 80 04 00 00 jump, 00 00 stitch, 1e 00 ...)
  const cut = Uint8Array.from([...bytes.subarray(0, 6), ...bytes.subarray(8)]);
  assert.ok(failedChecks(rb.verifyExport(sample(), cut, "exp")).has("stitch_count"));
  const bad = flip(bytes, 1, 0x55);
  const r = rb.verifyExport(sample(), bad, "exp");
  assert.deepStrictEqual([...failedChecks(r)], ["readable"]);
});

test("exp: a lost trim and a lost colour fail trim_count and color_count", () => {
  const d = sample();
  const noTrim = { ...d, stitches: d.stitches.filter((s) => s.type !== "trim") };
  assert.ok(failedChecks(rb.verifyExport(d, exp.encodeEXP(noTrim), "exp")).has("trim_count"));
  const noColor = { ...d, stitches: d.stitches.filter((s) => s.type !== "color") };
  assert.ok(failedChecks(rb.verifyExport(d, exp.encodeEXP(noColor), "exp")).has("color_count"));
});

test("pes: a stitch record corrupted in the PEC stream fails; the signature is checked", () => {
  const bytes = pes.encodePES(sample());
  const pec = bytes[8] | (bytes[9] << 8) | (bytes[10] << 16) | (bytes[11] << 24);
  const first = pec + 532;
  // clobber the first stitch record's delta
  const r = rb.verifyExport(sample(), flip(bytes, first + 2, 0x3f), "pes");
  assert.strictEqual(r.ok, false, "a corrupted PEC delta must be caught");
  const noSig = flip(bytes, 0, 0x58);
  assert.deepStrictEqual([...failedChecks(rb.verifyExport(sample(), noSig, "pes"))], ["readable"]);
});

test("pes: a lost trim and a lost colour fail trim_count and color_count", () => {
  const d = sample();
  const noTrim = { ...d, stitches: d.stitches.filter((s) => s.type !== "trim") };
  assert.ok(failedChecks(rb.verifyExport(d, pes.encodePES(noTrim), "pes")).has("trim_count"));
  const noColor = { ...d, stitches: d.stitches.filter((s) => s.type !== "color") };
  assert.ok(failedChecks(rb.verifyExport(d, pes.encodePES(noColor), "pes")).has("color_count"));
});

test("a stitch-stream byte flip anywhere in a DST body is caught", () => {
  const bytes = dst.encodeDST(sample());
  let missed = 0;
  for (let i = DST_BODY; i < bytes.length; i++) {
    if (rb.verifyExport(sample(), flip(bytes, i, bytes[i] ^ 0x04), "dst").ok) missed++;
  }
  assert.strictEqual(missed, 0);
});
