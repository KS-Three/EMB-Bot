const assert = require("node:assert");
const { test } = require("node:test");
const dst = require("../src/dst.js");
const { decodeDST, buildImportedDesign, IMPORT_BLOCK_COLORS } = require("../src/dstimport.js");

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

  // 6 real stitches + 1: encodeDST writes the design's trailing {type:"end"}
  // marker as a zero-delta stitch record before the true DST end record, so
  // it decodes back as one extra (zero-length, harmless) stitch.
  assert.strictEqual(d.stitchCount, 7);
  assert.strictEqual(d.colorCount, 2);
  assert.strictEqual(d.trimCount, 1); // the trim survived the jump-run wire format
  assert.strictEqual(d.widthMM, 10);  // 100 units
  assert.strictEqual(d.heightMM, 4);  // 40 units
  assert.strictEqual(d.label, "RT");

  const stitchesOnly = d.stitches.filter((s) => s.type === "stitch");
  assert.deepStrictEqual(
    stitchesOnly.map((s) => [s.x, s.y]),
    [[-50, -20], [0, -20], [50, -20], [50, 20], [0, 20], [-50, 20], [-50, 20]]
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
  // 512-byte header + only jump records -> no stitches
  const empty = new Uint8Array(512 + 3);
  empty[512] = 0; empty[513] = 0; empty[514] = 0xf3;
  assert.throws(() => decodeDST(empty), /No stitches/);
});

const GARMENT = { widthIn: 4, heightIn: 4 }; // 101.6 x 101.6 mm hoop

test("buildImportedDesign defaults to native size and matches the lettering Design contract", () => {
  const d = decodeDST(dst.encodeDST(fixtureDesign()));
  const design = buildImportedDesign(d, { garment: GARMENT });
  assert.strictEqual(design.widthMM, 10);
  assert.strictEqual(design.heightMM, 4);
  assert.strictEqual(design.stitchCount, 7);
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

test("buildImportedDesign honors per-block color overrides and falls back to distinct defaults", () => {
  const d = decodeDST(dst.encodeDST(fixtureDesign()));
  const design = buildImportedDesign(d, {
    garment: GARMENT, blockColors: { 1: [9, 8, 7] },
  });
  assert.deepStrictEqual(design.colors[1], { r: 9, g: 8, b: 7 });
  const def = IMPORT_BLOCK_COLORS[0];
  assert.deepStrictEqual(design.colors[0], { r: def[0], g: def[1], b: def[2] });
});
