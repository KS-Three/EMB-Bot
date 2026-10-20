// The text lane's two flags (2026-10-20): `dedupeHoles` and `underlayDirection`
// on buildLetteringDesign, both built OFF.
//
// MASTER_SCOPE 25 said lettering "has its own and no flag yet" and 40 that
// buildLetteringDesign "is still not covered". This wires the shape lane's
// two rules through the lettering builder under the same names and values,
// and pins three things:
//
//   1. OFF is main's stream, byte for byte: the md5 of the stitch stream for
//      three library fonts (the Studio's default, the satin font with the
//      most doubled holes at 40 mm, a pixel font) at two sizes, taken on main
//      at 7220f3e.
//   2. `dedupeHoles` ON lays no stitch straight after a stitch on the same
//      point, and the stream is OFF's less exactly those records; a run every
//      record of which repeats the record before it lays nothing and loses
//      its span (apesplit), and no other span moves.
//   3. `underlayDirection` ON turns nothing on these fonts, because this
//      lane's underlay already finishes where its satin starts; it turns a
//      closed ring whose two crosses meet, and nothing else moves.
//
// Everything is asked of the stream in file units (0.1 mm), the way the
// shape lane's tests in test/digitize.test.js ask it.
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const DG = require("../src/digitize.js");
const fb = require("../src/fontbin.js");
const satin = require("../src/satin.js");

const BIN = path.join(__dirname, "..", "src", "fonts", "bin");
const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, underlay: true };
const load = (key) => fb.decodeFontBin(fs.readFileSync(path.join(BIN, key + ".embf")));
// The library is committed; a missing font is a skip locally and a failure on CI,
// as test/run-fonts.test.js has it: a pin nobody ran is not a pin.
function binOrSkip(key) {
  if (fs.existsSync(path.join(BIN, key + ".embf"))) return true;
  if (process.env.CI) throw new Error(`${key}.embf is missing on CI — its pin is unverified, not satisfied`);
  return false;
}
const build = (key, text, widthMm, extra) => DG.buildLetteringDesign(load(key), text, { ...base, targetWidthMm: widthMm, ...(extra || {}) });
const md5 = (d) => crypto.createHash("md5").update(JSON.stringify(d.stitches)).digest("hex");
const records = (d) => d.stitches.map((s) => `${s.x},${s.y},${s.type}`).join(";");
const same = (p, q) => p.x === q.x && p.y === q.y;
const count = (d, type) => d.stitches.filter((s) => s.type === type).length;
// The stitches on a point the stitch before them is on, by the kind of span
// they are in ("none" for a stitch in no span: a cross-stitch font's).
const secondByKind = (d) => {
  const kindAt = [];
  for (const r of d.runs) for (let i = r.i0; i <= r.i1; i++) kindAt[i] = r.kind;
  const out = {};
  for (let i = 1; i < d.stitches.length; i++) {
    if (d.stitches[i].type === "stitch" && d.stitches[i - 1].type === "stitch" && same(d.stitches[i], d.stitches[i - 1])) {
      const k = kindAt[i] || "none";
      out[k] = (out[k] || 0) + 1;
    }
  }
  return out;
};
const seconds = (d) => Object.values(secondByKind(d)).reduce((a, b) => a + b, 0);
// What the flag is to leave of a stream, written out here and not asked of
// the builder: every record but a stitch on the point of the stitch that is
// the record before it. test/digitize.test.js asks the same of the shape lane.
const withoutSecond = (stitches) => {
  const out = [];
  let hole = null;
  for (const s of stitches) {
    if (s.type !== "stitch") hole = null;
    else if (hole && same(hole, s)) continue;
    else hole = s;
    out.push(s);
  }
  return out;
};

// [font, text, width mm, md5 of the OFF stream on main at 7220f3e (2026-10-20),
//  records in it, the doubled holes in it by span kind]
const PINS = [
  ["medium_font", "FRITSCH", 40, "a4e9cff8e793cabe7382408bf66ac465", 590, { underlay: 5 }],
  ["medium_font", "FRITSCH", 100, "a414327a26c87a9b0ae672ec6b7ff6a8", 1291, {}],
  ["mai_en_fleur", "FRITSCH", 40, "96e149414b624ad8f603e9fe8d3f4793", 2039, { underlay: 20, travel: 103, run: 23 }],
  ["mai_en_fleur", "FRITSCH", 100, "6a0322664f1aece2224f1b6a0517579f", 6172, { underlay: 73, travel: 4, satin: 1 }],
  ["pixel10", "FRITSCH", 40, "fd08f0d56f282821dfa08bc76303eae7", 3785, { satin: 10, underlay: 7, travel: 1 }],
  ["pixel10", "FRITSCH", 100, "9152f6f964eba544506510c004b8f993", 6879, {}],
];

test("both flags are OFF by default: the stream is main's (md5), and explicit false is byte-identical to omitting them", () => {
  for (const [key, text, w, hash, n] of PINS) {
    if (!binOrSkip(key)) continue;
    const omitted = build(key, text, w);
    assert.strictEqual(md5(omitted), hash, `${key} "${text}" ${w} mm: the OFF stream moved`);
    assert.strictEqual(omitted.stitches.length, n, `${key} "${text}" ${w} mm: records`);
    const off = build(key, text, w, { dedupeHoles: false, underlayDirection: false });
    assert.strictEqual(records(off), records(omitted), `${key} "${text}" ${w} mm: explicit false`);
    assert.deepStrictEqual(off.runs, omitted.runs);
  }
});

test("dedupeHoles: left off, a run's first stitch repeats the point the run before it ended on (the fixtures, by kind)", () => {
  for (const [key, text, w, , , byKind] of PINS) {
    if (!binOrSkip(key)) continue;
    assert.deepStrictEqual(secondByKind(build(key, text, w)), byKind, `${key} "${text}" ${w} mm`);
  }
});

test("dedupeHoles ON: no stitch straight after a stitch on its point, and the stream is OFF's less exactly those records", () => {
  for (const [key, text, w] of PINS) {
    if (!binOrSkip(key)) continue;
    const off = build(key, text, w), on = build(key, text, w, { dedupeHoles: true });
    const label = `${key} "${text}" ${w} mm`;
    assert.strictEqual(seconds(on), 0, label);
    assert.deepStrictEqual(on.stitches, withoutSecond(off.stitches), label);
    assert.strictEqual(on.stitches.length, off.stitches.length - seconds(off), label);
    assert.strictEqual(on.stitchCount, off.stitchCount - seconds(off), label);
    for (const type of ["jump", "trim", "color"]) assert.strictEqual(count(on, type), count(off, type), `${label}: ${type} records`);
    assert.strictEqual(on.widthMM, off.widthMM, label);
    assert.strictEqual(on.heightMM, off.heightMM, label);
    assert.strictEqual(on.colorCount, off.colorCount, label);
    // every span is still a span of stitches, in the same order of kinds:
    // none of the pinned fonts has a run that lays nothing (next test)
    assert.strictEqual(allRepeating(off).length, 0, `${label}: fixture, no run of only repeated records`);
    assert.deepStrictEqual(on.runs.map((r) => r.kind), off.runs.map((r) => r.kind), label);
    spansAreStitches(on, label);
  }
});

// The spans of OFF whose every record sits on the record before it: a run
// that lays nothing under the flag.
const allRepeating = (d) => d.runs.filter((r) => {
  for (let i = r.i0; i <= r.i1; i++) {
    const a = d.stitches[i - 1], b = d.stitches[i];
    if (!(a && a.type === "stitch" && b.type === "stitch" && same(a, b))) return false;
  }
  return true;
});
const spansAreStitches = (d, label) => {
  for (const r of d.runs) {
    assert.ok(r.i0 <= r.i1 && r.i1 < d.stitches.length, `${label}: span ${r.kind} ${r.i0}..${r.i1}`);
    for (let i = r.i0; i <= r.i1; i++) assert.strictEqual(d.stitches[i].type, "stitch", `${label}: span ${r.kind} holds a ${d.stitches[i].type}`);
  }
};

test("dedupeHoles ON: a run every record of which repeats the record before it lays nothing and has no span; every other span stays", () => {
  if (!binOrSkip("apesplit")) return;
  // apesplit at 40 mm: two-point needle-down walks whose both points round
  // onto the stitch they leave from. The shape lane never meets this (pushRun
  // opens every run with a jump); here the span goes with its stitches.
  for (const [text, spansOff, spansOn] of [["FRITSCH", 284, 281], ["Stitches", 324, 316]]) {
    const off = build("apesplit", text, 40), on = build("apesplit", text, 40, { dedupeHoles: true });
    const label = `apesplit "${text}" 40 mm`;
    assert.strictEqual(off.runs.length, spansOff, `${label}: fixture, spans OFF`);
    assert.strictEqual(on.runs.length, spansOn, `${label}: spans ON`);
    const gone = allRepeating(off);
    assert.strictEqual(gone.length, spansOff - spansOn, label);
    for (const r of gone) { assert.strictEqual(r.kind, "travel", label); assert.strictEqual(r.i1 - r.i0 + 1, 2, label); }
    // the spans ON are the spans OFF less exactly those, in order, each of its kind
    assert.deepStrictEqual(on.runs.map((r) => r.kind), off.runs.filter((r) => !gone.includes(r)).map((r) => r.kind), label);
    spansAreStitches(on, label);
    // and the stream is still OFF's less the repeated records
    assert.deepStrictEqual(on.stitches, withoutSecond(off.stitches), label);
    assert.strictEqual(seconds(on), 0, label);
  }
});

test("dedupeHoles ON: the stitch after a jump, a trim or a colour change is laid, even on the point the needle is on", () => {
  if (!binOrSkip("mai_en_fleur")) return;
  // Two colours put a trim and a colour change in the middle of the word, and
  // the next glyph's run then opens with a jump onto the point it starts from.
  const two = { colorRanges: [{ startIdx: 0, endIdx: 3, colorRgb: [200, 0, 0] }] };
  const off = build("mai_en_fleur", "FRITSCH", 40, two), on = build("mai_en_fleur", "FRITSCH", 40, { ...two, dedupeHoles: true });
  assert.ok(count(off, "color") >= 1, "fixture: a colour change");
  assert.deepStrictEqual(on.stitches, withoutSecond(off.stitches));
  // after every record that is not a stitch, ON lays the same stitch OFF does
  const after = (d) => { const out = []; for (let i = 1; i < d.stitches.length; i++) if (d.stitches[i - 1].type !== "stitch") out.push(`${d.stitches[i - 1].type}>${d.stitches[i].x},${d.stitches[i].y},${d.stitches[i].type}`); return out; };
  assert.deepStrictEqual(after(on), after(off));
  assert.ok(after(on).length > 10, "fixture: jumps in the word");
});

test("dedupeHoles ON with ties: every lock is laid and none of them doubles a hole", () => {
  if (!binOrSkip("mai_en_fleur")) return;
  const tied = build("mai_en_fleur", "FRITSCH", 40, { ties: true });
  const both = build("mai_en_fleur", "FRITSCH", 40, { ties: true, dedupeHoles: true });
  assert.ok(tied._debug.nTies > 0, "fixture: ties");
  assert.strictEqual(both._debug.nTies, tied._debug.nTies);
  assert.strictEqual(seconds(both), 0);
});

test("dedupeHoles ON: a cross-stitch font's leg ends, laid twice in one hole, are laid once", () => {
  if (!binOrSkip("noble")) return;
  const off = build("noble", "FRITSCH", 40), on = build("noble", "FRITSCH", 40, { dedupeHoles: true });
  assert.deepStrictEqual(secondByKind(off), { none: 17 }, "fixture: noble's crosses lie in no span");
  assert.strictEqual(seconds(on), 0);
  assert.deepStrictEqual(on.stitches, withoutSecond(off.stitches));
});

// --- underlayDirection --------------------------------------------------------

// For every satin span entered needle-down from its own underlay: the
// underlay's last stitch, and the midpoints of the column's first and last
// crosses (file units).
const columnsAfterUnderlay = (d) => {
  const st = d.stitches, spans = d.runs, out = [];
  for (let k = 1; k < spans.length; k++) {
    const s = spans[k];
    if (s.kind !== "satin") continue;
    let j = k - 1;
    if (spans[j].kind === "travel") j--;
    if (j < 0 || spans[j].kind !== "underlay" || spans[j].shape !== s.shape) continue;
    let jumped = false;
    for (let i = spans[j].i1 + 1; i < s.i0; i++) if (st[i].type !== "stitch") jumped = true;
    if (jumped) continue;
    const mid = (p, q) => ({ x: (p.x + q.x) / 2, y: (p.y + q.y) / 2 });
    out.push({ shape: s.shape, from: st[spans[j].i1], first: mid(st[s.i0], st[s.i0 + 1]), last: mid(st[s.i1], st[s.i1 - 1]) });
  }
  return out;
};
const dist = (p, q) => Math.hypot(p.x - q.x, p.y - q.y);

test("underlayDirection: OFF by default here, and ON is byte-identical to OFF on these fonts — the underlay already ends where the satin starts", () => {
  for (const [key, text, w] of PINS) {
    if (!binOrSkip(key)) continue;
    const off = build(key, text, w), on = build(key, text, w, { underlayDirection: true });
    const label = `${key} "${text}" ${w} mm`;
    assert.strictEqual(records(on), records(off), label);
    assert.deepStrictEqual(on.runs, off.runs, label);
    const cols = columnsAfterUnderlay(on);
    if (w === 40 && key === "medium_font") assert.ok(cols.length >= 15, `${label}: fixture, columns after an underlay (${cols.length})`);
    // the heading, under the flag: no column starts at the cross farther from its underlay's end
    for (const c of cols) assert.ok(dist(c.from, c.first) <= dist(c.from, c.last), `${label} ${c.shape}: starts ${dist(c.from, c.first) / 10} mm from the thread, the other end ${dist(c.from, c.last) / 10} mm`);
  }
});

test("underlayDirection ON turns a closed ring whose two crosses meet, and nothing else moves", () => {
  if (!binOrSkip("colorful")) return;
  const off = build("colorful", "Stitches", 100), on = build("colorful", "Stitches", 100, { underlayDirection: true });
  assert.notStrictEqual(records(on), records(off), "fixture: colorful's rings turn");
  assert.strictEqual(on.stitches.length, off.stitches.length);
  assert.strictEqual(on.stitchCount, off.stitchCount);
  assert.deepStrictEqual(on.runs, off.runs, "the same spans at the same indices");
  // the same stitches, some of them the other way round
  const sorted = (d) => d.stitches.filter((s) => s.type === "stitch").map((s) => `${s.x},${s.y}`).sort();
  assert.deepStrictEqual(sorted(on), sorted(off));
  // as many trims and jumps; a trim sits on the last sewn point, so a turned
  // ring's trim moves to the ring's other end with it
  for (const type of ["jump", "trim", "color"]) assert.strictEqual(count(on, type), count(off, type), `${type} records`);
  for (const d of [off, on]) for (let i = 1; i < d.stitches.length; i++) if (d.stitches[i].type === "trim") assert.ok(same(d.stitches[i], d.stitches[i - 1]), "a trim is where the thread is");
  let turned = 0;
  for (let k = 0; k < off.runs.length; k++) {
    const r = off.runs[k], a = off.stitches.slice(r.i0, r.i1 + 1), b = on.stitches.slice(r.i0, r.i1 + 1);
    if (JSON.stringify(a) === JSON.stringify(b)) continue;
    assert.strictEqual(r.kind, "satin", `only a satin span turns (${r.kind})`);
    assert.deepStrictEqual(b, a.slice().reverse(), `span ${k}: the same stitches, reversed`);
    // a ring: its two crosses within half a millimetre of each other (measured 0 to 0.3 mm)
    const mid = (p, q) => ({ x: (p.x + q.x) / 2, y: (p.y + q.y) / 2 });
    const gap = dist(mid(a[0], a[1]), mid(a[a.length - 1], a[a.length - 2]));
    assert.ok(gap <= 5, `span ${k}: a ring (its ends ${gap / 10} mm apart)`);
    turned++;
  }
  assert.strictEqual(turned, 6, "the six rings of Stitches");
  // no travel added: the connectors are the same length
  const travel = (d) => d.runs.filter((r) => r.kind === "travel").map((r) => r.i1 - r.i0 + 1);
  assert.deepStrictEqual(travel(on), travel(off));
});

test("startNear's ends: a column wider than it is long is not turned when its first cross is at the thread, and is when its last cross is", () => {
  // one cross wide (4), one spacing long (1); the first stitch is on rail A, the last on rail B
  const pts = [{ x: 0, y: 0 }, { x: 4, y: 0 }, { x: 0, y: 1 }, { x: 4, y: 1 }];
  const ends = { a: { x: 2, y: 0 }, b: { x: 2, y: 1 } };
  // the thread at the first cross: measured by the first and last STITCHES it is nearer the last
  const atFirst = { x: 3, y: -0.2 };
  assert.notStrictEqual(satin.startNear(pts, atFirst), pts, "by its stitches the column would turn");
  assert.strictEqual(satin.startNear(pts, atFirst, ends), pts, "by its crosses it stays");
  // the thread at the last cross: turned either way, and the turn is the same
  const atLast = { x: 2, y: 1.2 };
  assert.deepStrictEqual(satin.startNear(pts, atLast, ends), pts.slice().reverse());
  assert.deepStrictEqual(satin.startNear(pts, atLast), pts.slice().reverse());
  // ends left out, or given empty, are the first and last stitches, as before
  assert.deepStrictEqual(satin.startNear(pts, atFirst, {}), satin.startNear(pts, atFirst));
  assert.deepStrictEqual(satin.startNear(pts, atLast, {}), satin.startNear(pts, atLast));
});
