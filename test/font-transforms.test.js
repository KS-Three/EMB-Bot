// SVG transforms in font glyphs (2026-08-22).
//
// build-font.mjs had TWO path walks: a transform-aware one, and a simpler one
// that read each path's `d` and ignored transforms entirely. The simple one was
// used for every font in the standard single-`ltr.svg` layout — i.e. most of
// the library.
//
// That is harmless for a glyph whose coordinates are baked into its `d`, and
// destroys a glyph that places repeated geometry BY transform. mimosa_large is
// a dot-matrix face that does both: its "A" carries 38 distinct `d` values and
// no transforms and imported perfectly, while its "D" carries ONE `d` — a
// single dot — repeated 38 times with 38 different transforms. Dropping those
// stacked all 38 dots on one point, so "D" sewed 6,193 stitches into
// 40.0 x 0.0 mm against a healthy glyph's 996 in 40.0 x 60.1 mm: a needle
// hammering one line thousands of times, and it shipped.
//
// Three other fonts were hit the same way (mimosa_medium, apesplit,
// initials_medium). Fixing the root cause fixed all four at once.
//
// The fixture is built so the bug cannot hide: glyph A is placed ENTIRELY by
// transform and glyph B is the identical shape with baked coordinates, so the
// assertion is that the two agree. A test that only checked A's bounding box
// against a constant would still pass if transforms were applied twice.
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const ROOT = path.join(__dirname, "..");
const FIXTURE = path.join(__dirname, "fixtures", "fonts", "transforms");

function importFixture() {
  const out = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "embfont-")), "out.json");
  execFileSync(process.execPath, [path.join(ROOT, "tools", "build-font.mjs"), FIXTURE, out], { stdio: "ignore" });
  return JSON.parse(fs.readFileSync(out, "utf8"));
}

const pointsOf = (g) => (g.runs || []).flatMap((r) => r.pts || r);
const boxOf = (g) => {
  const p = pointsOf(g);
  const xs = p.map((q) => q[0]), ys = p.map((q) => q[1]);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
};

test("a glyph placed by transform matches the same glyph with baked coordinates", () => {
  const font = importFixture();
  // A: one 10x10 square reused 4 times, positioned only by transform (one of
  // them on a parent <g>, so nesting is exercised too).
  // B: the same four squares written out at their final coordinates.
  assert.deepStrictEqual(boxOf(font.glyphs["A"]), boxOf(font.glyphs["B"]),
    "transform-placed glyph does not agree with the baked-coordinate one — " +
    "transforms are being dropped, double-applied, or mis-composed");
  assert.deepStrictEqual(boxOf(font.glyphs["A"]), [0, 0, 40, 40]);
});

test("dropping transforms would collapse the glyph — the failure this guards", () => {
  const font = importFixture();
  // All four of A's squares share one `d` at the origin. If transforms were
  // ignored, every square would land on 0,0..10,10 and the glyph would be a
  // tenth of its true size — exactly mimosa_large's "D".
  const [x0, y0, x1, y1] = boxOf(font.glyphs["A"]);
  assert.ok(x1 - x0 > 10 && y1 - y0 > 10,
    `glyph A collapsed to ${x1 - x0}x${y1 - y0} — its four squares stacked on one spot`);
  assert.strictEqual((font.glyphs["A"].runs || []).length, 4, "expected four separate squares");
});

test("rotate(deg,cx,cy) is applied about its stated centre", () => {
  const font = importFixture();
  // C is the unit square at the origin under rotate(-90,20,20). By hand:
  // (0,0) -> (0,40) and (10,10) -> (10,30), so the box is 0,30..10,40.
  // A rotate applied about the ORIGIN instead would put it at 0,-10..10,0.
  assert.deepStrictEqual(boxOf(font.glyphs["C"]), [0, 30, 10, 40]);
});

test("a non-self-closed </path> does not pop the transform stack", () => {
  const font = importFixture();
  // Glyph D is two squares inside <g transform="translate(0,50)">, the FIRST
  // written as <path ...></path> rather than self-closed. The walk popped on
  // any closing tag while only <g> ever pushed, so that </path> discarded the
  // group's frame and every following sibling lost the parent transform —
  // here the second square would fall back to y 0..10.
  //
  // Dormant across the whole upstream library (every file self-closes its
  // paths), which is exactly why it needs a test rather than a comment: the
  // day a font does this, nothing else would catch it.
  const pts = pointsOf(font.glyphs["D"]);
  const ys = pts.map((p) => p[1]);
  assert.strictEqual((font.glyphs["D"].runs || []).length, 2, "expected both squares");
  assert.ok(Math.min(...ys) === 50 && Math.max(...ys) === 60,
    `both squares must sit at y 50..60; got ${Math.min(...ys)}..${Math.max(...ys)} — ` +
    `the </path> popped the group transform off the stack`);
});

test("the licence file is found whether it is LICENSE or license", () => {
  // 141 of 142 upstream fonts name it LICENSE; fold_inkstitch names it
  // "license". build-font looked for the uppercase spelling only, which
  // resolves fine on Kent's case-insensitive Windows filesystem and silently
  // read NOTHING on Linux — every cloud session. The font then imported with an
  // empty licence, and licenseId("") returns SEE-LICENSE-FILE, which sits
  // outside ALLOWED_LICENSES: fold_inkstitch was excluded from the sellable
  // library for two weeks by a filename, not by its licence, which is in fact
  // OFL-1.1.
  //
  // It failed SAFE, but by luck rather than design — the identical silence
  // excludes a legitimately-licensed font and would let a badly-licensed one
  // through if the default ever flipped. Exercised by copying the fixture and
  // renaming its licence, so no second committed fixture is needed.
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "embfont-lic-"));
  for (const f of fs.readdirSync(FIXTURE)) {
    const dest = f === "LICENSE" ? "license" : f;
    fs.copyFileSync(path.join(FIXTURE, f), path.join(tmp, dest));
  }
  assert.ok(!fs.existsSync(path.join(tmp, "LICENSE")), "fixture copy must have only the lowercase name");
  const out = path.join(tmp, "out.json");
  execFileSync(process.execPath, [path.join(ROOT, "tools", "build-font.mjs"), tmp, out], { stdio: "ignore" });
  const font = JSON.parse(fs.readFileSync(out, "utf8"));
  assert.ok(/Open Font License/i.test(font.license || ""),
    "licence text was not picked up from a lowercase 'license' file — the font " +
    "would import with an empty licence and be silently excluded from the build");
});
