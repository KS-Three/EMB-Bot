const assert = require("node:assert");
const { test } = require("node:test");
const dst = require("../src/dst.js");
const { decodeDST, decodeDSTStandard, buildImportedDesign, IMPORT_BLOCK_COLORS } = require("../src/dstimport.js");
const fs = require("node:fs");
const path = require("node:path");

// Round-trip fixture: a small hand-built design pushed through our own
// byte-verified encodeDST, then decoded back. Coordinates are chosen already
// centered (bbox midpoint = 0,0) so decode's centering is the identity and
// deepStrictEqual can compare positions directly.
function fixtureDesign() {
  return {
    stitches: [
      { x: -50, y: -20, type: "jump" },   // travel in
      { x: -50, y: -20, type: "stitch" },
      { x: 0, y: -20, type: "stitch" },
      { x: 50, y: -20, type: "stitch" },
      { x: 50, y: 20, type: "trim" },     // trim -> >=3 jumps on the wire
      { x: 50, y: 20, type: "stitch" },
      { x: 0, y: 20, type: "color" },
      { x: 0, y: 20, type: "stitch" },
      { x: -50, y: 20, type: "stitch" },
      { x: -50, y: 20, type: "end" },
    ],
    colors: [{ r: 1, g: 2, b: 3 }, { r: 4, g: 5, b: 6 }],
    label: "RT",
  };
}

test("decodeDST round-trips our own encodeDST output (positions, types, counts)", () => {
  const bytes = dst.encodeDST(fixtureDesign());
  const d = decodeDST(bytes);

  // 6 real stitches, and 6 back. encodeDST stops at the trailing
  // {type:"end"} sentinel as of 2026-09-08, the way exp.js and pes.js always
  // have; before that it wrote the sentinel as a real stitch record and this
  // read back 7.
  assert.strictEqual(d.stitchCount, 6);
  assert.strictEqual(d.colorCount, 2);
  assert.strictEqual(d.trimCount, 1); // the trim survived the jump-run wire format
  assert.strictEqual(d.widthMM, 10);  // 100 units
  assert.strictEqual(d.heightMM, 4);  // 40 units
  assert.strictEqual(d.label, "RT");

  const stitchesOnly = d.stitches.filter((s) => s.type === "stitch");
  assert.deepStrictEqual(
    stitchesOnly.map((s) => [s.x, s.y]),
    // `[-50, 20]` appeared TWICE here until 2026-09-08 -- the design's last
    // stitch, and then the {type:"end"} sentinel written at the same spot as
    // a second, zero-length needle penetration.
    [[-50, -20], [0, -20], [50, -20], [50, 20], [0, 20], [-50, 20]]
  );
  // The trim collapsed to ONE record at the run's landing position.
  const trims = d.stitches.filter((s) => s.type === "trim");
  assert.deepStrictEqual(trims, [{ x: 50, y: 20, type: "trim" }]);
  // The short (single-record) leading jump stayed a jump, not a trim.
  const jumps = d.stitches.filter((s) => s.type === "jump");
  assert.deepStrictEqual(jumps, [{ x: -50, y: -20, type: "jump" }]);
});

test("decodeDST centers an off-origin design on its stitch bbox midpoint", () => {
  const design = {
    stitches: [
      { x: 100, y: 200, type: "stitch" },
      { x: 200, y: 200, type: "stitch" },
      { x: 200, y: 300, type: "stitch" },
      { x: 200, y: 300, type: "end" },
    ],
    colors: [{ r: 0, g: 0, b: 0 }],
  };
  const d = decodeDST(dst.encodeDST(design));
  const xs = d.stitches.filter((s) => s.type === "stitch").map((s) => s.x);
  const ys = d.stitches.filter((s) => s.type === "stitch").map((s) => s.y);
  assert.strictEqual(Math.min(...xs) + Math.max(...xs), 0);
  assert.strictEqual(Math.min(...ys) + Math.max(...ys), 0);
});

test("decodeDST rejects non-DST inputs", () => {
  assert.throws(() => decodeDST(new Uint8Array(10)), /too small/);
  // A REAL header (three Tajima fields, the floor the guard added 2026-09-07
  // wants) plus nothing but the end record -> no stitches. The header used to
  // be 512 zero bytes here, which now fails the earlier "is it a DST at all"
  // check and would have tested that instead of this.
  const empty = new Uint8Array(512 + 3).fill(0x20, 0, 512);
  const head = "LA:EMPTY\rST:     0\rCO:  1\r";
  for (let i = 0; i < head.length; i++) empty[i] = head.charCodeAt(i);
  empty[512] = 0; empty[513] = 0; empty[514] = 0xf3;
  assert.throws(() => decodeDST(empty), /No stitches/);
});

const GARMENT = { widthIn: 4, heightIn: 4 }; // 101.6 x 101.6 mm hoop

test("buildImportedDesign defaults to native size and matches the lettering Design contract", () => {
  const d = decodeDST(dst.encodeDST(fixtureDesign()));
  const design = buildImportedDesign(d, { garment: GARMENT });
  assert.strictEqual(design.widthMM, 10);
  assert.strictEqual(design.heightMM, 4);
  assert.strictEqual(design.stitchCount, 6);  // 6 real; the end sentinel is no longer written as a stitch
  assert.strictEqual(design.colorCount, 2);
  assert.strictEqual(design.colors.length, 2);
  assert.strictEqual(design.stitches[design.stitches.length - 1].type, "end");
  assert.strictEqual(design._debug.scale, 1);
});

test("buildImportedDesign scales stitches uniformly to targetWidthMm and applies offsets", () => {
  const d = decodeDST(dst.encodeDST(fixtureDesign()));
  const design = buildImportedDesign(d, {
    garment: GARMENT, targetWidthMm: 20, offsetXMm: 5, offsetYMm: -3,
  });
  assert.strictEqual(design.widthMM, 20);
  assert.strictEqual(design.heightMM, 8);
  assert.strictEqual(design._debug.scale, 2);
  const first = design.stitches.find((s) => s.type === "stitch");
  // (-50,-20) * 2 + (50,-30) offset units
  assert.deepStrictEqual([first.x, first.y], [-100 + 50, -40 - 30]);
});

test("buildImportedDesign clamps to the hoop on BOTH dims (a tall design can't overflow via width-only clamp)", () => {
  const tall = {
    stitches: [
      { x: 0, y: -1000, type: "stitch" }, // 200mm tall, 2mm wide
      { x: 20, y: 1000, type: "stitch" },
      { x: 20, y: 1000, type: "end" },
    ],
    colors: [{ r: 0, g: 0, b: 0 }],
  };
  const d = decodeDST(dst.encodeDST(tall));
  const design = buildImportedDesign(d, { garment: GARMENT }); // hoop 101.6mm
  assert.ok(design.heightMM <= 101.6 + 1e-9);
  assert.ok(design._debug.scale < 1);
});

test("rotationDeg 0 (and absent) is byte-identical to the pre-rotation path", () => {
  const d = decodeDST(dst.encodeDST(fixtureDesign()));
  const plain = buildImportedDesign(d, { garment: GARMENT });
  const rot0 = buildImportedDesign(d, { garment: GARMENT, rotationDeg: 0 });
  const rot360 = buildImportedDesign(d, { garment: GARMENT, rotationDeg: 360 });
  assert.deepStrictEqual(rot0, plain);
  assert.deepStrictEqual(rot360, plain);
});

test("rotationDeg 90 swaps the design's reported and actual extents", () => {
  const d = decodeDST(dst.encodeDST(fixtureDesign())); // 10 x 4 mm
  const design = buildImportedDesign(d, { garment: GARMENT, rotationDeg: 90 });
  assert.ok(Math.abs(design.widthMM - 4) < 0.05, `widthMM ${design.widthMM}`);
  assert.ok(Math.abs(design.heightMM - 10) < 0.05, `heightMM ${design.heightMM}`);
  assert.strictEqual(design.stitchCount, 6);  // 6 real; the end sentinel is no longer written as a stitch
  // (x, y) -> (-y, x): the first real stitch (-50,-20) lands at (20,-50).
  const first = design.stitches.find((s) => s.type === "stitch");
  assert.deepStrictEqual([first.x, first.y], [20, -50]);
});

test("rotationDeg 180 preserves extents and negates stitch positions", () => {
  const d = decodeDST(dst.encodeDST(fixtureDesign()));
  const plain = buildImportedDesign(d, { garment: GARMENT });
  const design = buildImportedDesign(d, { garment: GARMENT, rotationDeg: 180 });
  assert.strictEqual(design.widthMM, plain.widthMM);
  assert.strictEqual(design.heightMM, plain.heightMM);
  const first = design.stitches.find((s) => s.type === "stitch");
  const firstPlain = plain.stitches.find((s) => s.type === "stitch");
  assert.deepStrictEqual([first.x, first.y], [-firstPlain.x, -firstPlain.y]);
});

test("targetWidthMm means POST-rotation width, and the hoop clamps by rotated extents", () => {
  const d = decodeDST(dst.encodeDST(fixtureDesign())); // 10 x 4 mm native
  // Rotated 90 the design is 4mm wide; asking for 8mm wide = scale 2.
  const design = buildImportedDesign(d, { garment: GARMENT, rotationDeg: 90, targetWidthMm: 8 });
  assert.ok(Math.abs(design.widthMM - 8) < 0.1, `widthMM ${design.widthMM}`);
  assert.ok(Math.abs(design._debug.scale - 2) < 0.05);

  // A 2x200mm design rotated 90 becomes 200mm WIDE — the width clamp (not
  // the height clamp) must now be the one that catches it in a 101.6mm hoop.
  const tall = {
    stitches: [
      { x: 0, y: -1000, type: "stitch" },
      { x: 20, y: 1000, type: "stitch" },
      { x: 20, y: 1000, type: "end" },
    ],
    colors: [{ r: 0, g: 0, b: 0 }],
  };
  const dt = decodeDST(dst.encodeDST(tall));
  const rotated = buildImportedDesign(dt, { garment: GARMENT, rotationDeg: 90, targetWidthMm: 500 });
  assert.ok(rotated.widthMM <= 101.6 + 1e-9, `widthMM ${rotated.widthMM}`);
});

test("rotation re-centers on the rotated stitch bbox (asymmetric cloud stays bbox-centered)", () => {
  // An L-shaped cloud: rotating about the old center shifts the new bbox,
  // so the builder must re-center before scaling/placing.
  const ell = {
    stitches: [
      { x: -100, y: -50, type: "stitch" },
      { x: 100, y: -50, type: "stitch" },
      { x: 100, y: 50, type: "stitch" },
      { x: 100, y: 50, type: "end" },
    ],
    colors: [{ r: 0, g: 0, b: 0 }],
  };
  const d = decodeDST(dst.encodeDST(ell));
  const design = buildImportedDesign(d, { garment: GARMENT, rotationDeg: 45 });
  const pts = design.stitches.filter((s) => s.type === "stitch");
  const xs = pts.map((s) => s.x);
  const ys = pts.map((s) => s.y);
  assert.ok(Math.abs(Math.min(...xs) + Math.max(...xs)) <= 1, "x bbox centered");
  assert.ok(Math.abs(Math.min(...ys) + Math.max(...ys)) <= 1, "y bbox centered");
});

test("buildImportedDesign honors per-block color overrides and falls back to distinct defaults", () => {
  const d = decodeDST(dst.encodeDST(fixtureDesign()));
  const design = buildImportedDesign(d, {
    garment: GARMENT, blockColors: { 1: [9, 8, 7] },
  });
  assert.deepStrictEqual(design.colors[1], { r: 9, g: 8, b: 7 });
  const def = IMPORT_BLOCK_COLORS[0];
  assert.deepStrictEqual(design.colors[0], { r: def[0], g: def[1], b: def[2] });
});

// ---- reading a file EMB-Bot did NOT write --------------------------------
//
// Every test above encodes with `dst.js` and decodes with `decodeDST`, so a
// symmetric error in the pair cancels and is invisible to all of them. That
// is not a hypothetical: the pair IS symmetrically wrong, and the import lane
// exists for files written by other software.
//
// `test/fixtures/standard-tajima.dst` is written by pystitch — an independent
// Tajima/pyembroidery-convention implementation — via
// digitizer/tools/make_standard_dst_fixture.py. 40 x 10 mm, deliberately
// asymmetric under all eight dihedral transforms: one long arm along +x, ONE
// short arm at ONE end, and a second colour block in ONE corner. A bbox
// comparison cannot tell a rotation from a mirror; these points can.
const STANDARD_DST = path.join(__dirname, "fixtures", "standard-tajima.dst");
function standardBytes() {
  return new Uint8Array(fs.readFileSync(STANDARD_DST));
}

// pystitch reads this file as 40.0 x 10.0 mm. The model's +y points UP where
// pystitch's points down, so the model point for a pystitch point (px, py) is
// (px, -py) — the same mapping tools/crossval-stitch-formats.mjs calls
// "identity" going the other way.
const EXPECTED_STANDARD = [
  { x: -200, y: -50, type: "stitch" }, { x: -100, y: -50, type: "stitch" },
  { x: 0, y: -50, type: "stitch" }, { x: 100, y: -50, type: "stitch" },
  { x: 200, y: -50, type: "stitch" },
  { x: 200, y: 0, type: "stitch" }, { x: 200, y: 50, type: "stitch" },
  { x: 200, y: 50, type: "trim" }, { x: 200, y: 50, type: "color" },
  { x: -200, y: 50, type: "trim" },
  { x: -200, y: 50, type: "stitch" }, { x: -150, y: 50, type: "stitch" },
  { x: -200, y: 10, type: "stitch" },
];

test("decodeDSTStandard reads a third-party DST as its writer meant it", () => {
  const d = decodeDSTStandard(standardBytes());
  assert.strictEqual(d.widthMM, 40, "pystitch reads this file as 40.0 mm wide");
  assert.strictEqual(d.heightMM, 10);
  assert.deepStrictEqual(d.stitches, EXPECTED_STANDARD);
});

test("decodeDST reads a third-party DST correctly — it IS the standard reader now", () => {
  // This asserted the DEFECT until 2026-09-08 (10 x 40, width and height
  // swapped), and its own comment said what to do when it stopped failing:
  // "the codec was fixed — delete decodeDSTStandard and point the import lane
  // back at decodeDST". That is what happened. `decodeDelta` now reads X from
  // the low nibble and Y from the high one, bit-for-bit with pystitch.
  const d = decodeDST(standardBytes());
  assert.strictEqual(d.widthMM, 40, "pystitch reads this file as 40.0 mm wide");
  assert.strictEqual(d.heightMM, 10);
  assert.deepStrictEqual(d.stitches, EXPECTED_STANDARD);
});

test("decodeDSTStandard is an ALIAS now, not a second reader", () => {
  // Two entry points existed only while the writer spoke a private dialect.
  // With one correct codec, a wrapper that transposes on top of it would be a
  // second wrong turn — so this pins the collapse rather than the wrapper.
  assert.strictEqual(decodeDSTStandard, decodeDST,
    "decodeDSTStandard must stay the same function, not a re-added correction");
});

test("a transpose on top of the corrected read would MIRROR the design", () => {
  // The whole reason this fixture is asymmetric. Until 2026-09-07 the repo
  // recorded the import defect as "a quarter turn" and the Studio told
  // customers to use Rotate — advice that cannot work, because rotation
  // preserves orientation and a transpose does not. The bbox swap that was
  // measured is equally consistent with both; the SIGNED AREA of three
  // non-collinear points is what separates them.
  //
  // Kept and repointed. The intuitive "repair" for any future orientation
  // report is to transpose the decode; this shows what that costs — the
  // design comes back mirrored, letters backwards — so the next person
  // reaches for a measurement instead of a transpose.
  const good = decodeDST(standardBytes()).stitches;
  const transposed = good.map((s) => ({ x: s.y, y: s.x, type: s.type }));
  const cross = (p, q, r) => (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x);
  const [i, j, k] = [0, 4, 6]; // start of the long arm, its far end, tip of the short arm
  const sa = cross(good[i], good[j], good[k]);
  const sb = cross(transposed[i], transposed[j], transposed[k]);
  assert.notStrictEqual(sa, 0, "the three sample points must not be collinear");
  assert.ok(sa * sb < 0, `signed area keeps its sign (${sa} vs ${sb}) — that would be a rotation, not a mirror`);
  assert.strictEqual(Math.abs(sa), Math.abs(sb), "same triangle, opposite handedness");
});

test("a standard file keeps its blocks, trims and label through the corrected read", () => {
  const d = decodeDSTStandard(standardBytes());
  assert.strictEqual(d.colorCount, 2);
  assert.strictEqual(d.stitchCount, 10);
  assert.strictEqual(d.trimCount, 2);
});

// ---- is it even a DST? ---------------------------------------------------
//
// The only gate used to be `length >= 515`, so any file bigger than that
// decoded into "a design". Measured through the shipped UI 2026-09-07: a
// Brother .pes fed to the import lane raised no error and reported
// **3736 x 7624 mm with 10,878 colour blocks**, and the panel rendered a
// thread picker for every one of them.

// Swap a synthetic 512-byte header onto a real DST's record stream, so these
// tests vary ONLY the header and the body stays a stream that is known to
// decode.
function withHeader(lines) {
  const body = standardBytes().subarray(512);
  const head = new Uint8Array(512).fill(0x20);
  const text = lines.map((l) => l + "\r").join("");
  for (let i = 0; i < text.length && i < 512; i++) head[i] = text.charCodeAt(i) & 0xff;
  const out = new Uint8Array(512 + body.length);
  out.set(head, 0);
  out.set(body, 512);
  return out;
}

test("a file with no Tajima header is refused, and the message names the way out", () => {
  // 4 KB of nothing — stands in for every non-DST tried: PES, JEF, EXP, SVG,
  // PNG, random bytes and a JSON project file all score zero header tags.
  const notADst = new Uint8Array(4096);
  assert.throws(() => decodeDST(notADst), (e) => {
    assert.match(e.message, /Not a DST file/);
    // A dead end would be "invalid file". The formats a customer is most
    // likely holding are named, with what to do about them.
    assert.match(e.message, /\.pes/);
    assert.match(e.message, /\.dst download/);
    return true;
  });
});

test("three header fields are enough, two are not", () => {
  // The floor is deliberately well under the twelve every real writer emits
  // (a sparse writer must not be rejected) and well over the one a file
  // hand-built out of "ST:" lines can reach by coincidence.
  assert.throws(() => decodeDST(withHeader(["LA:X", "ST:  10"])), /Not a DST file/);
  const ok = decodeDST(withHeader(["LA:X", "ST:  10", "CO:  2"]));
  assert.strictEqual(ok.stitchCount, 10);
});

test("only the twelve real tags count, and only at the start of a line", () => {
  // "ST:" inside a label is not a header field. Three junk tags plus a label
  // that contains one must still fail.
  assert.throws(() => decodeDST(withHeader(["ZZ:1", "QQ:2", "WW:3", "LA:my ST:file"])), /Not a DST file/);
});

test("every DST in the repo still decodes", () => {
  // The guard's job is to reject what is not a DST, and its risk is rejecting
  // one that is. These come from three unrelated writers — a commissioned
  // professional file, pystitch, and EMB-Bot's own encoder.
  const dir = path.join(__dirname, "..", "digitizer", "testdata", "reference");
  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".dst"));
  assert.ok(files.length >= 5, "expected the committed reference DSTs to be present");
  for (const f of files) {
    const d = decodeDST(new Uint8Array(fs.readFileSync(path.join(dir, f))));
    assert.ok(d.stitchCount > 0, f);
  }
  assert.ok(decodeDST(standardBytes()).stitchCount > 0, "pystitch fixture");
  assert.ok(decodeDST(dst.encodeDST(fixtureDesign())).stitchCount > 0, "EMB-Bot's own encoder");
});
