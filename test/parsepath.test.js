// SVG scientific notation in path data (2026-08-21).
//
// build-font.mjs decided "is this token a command?" with an UNANCHORED
// /[a-zA-Z]/. SVG numbers may be written in scientific notation — Inkscape
// emits "5.2e-4" routinely for sub-micron offsets — and those contain an "e",
// so such a number was taken as a command letter. Nothing below matches a
// command named "5.2e-4", and because every following token is a plain number
// nothing ever reassigns cmd, so the parser walked the rest of the path
// emitting no points: every path was silently TRUNCATED at its first
// scientific-notation number.
//
// 119 of 132 upstream fonts contain such numbers, and 63 of the 70 shipped
// ones. It went unnoticed for so long because satin rails carry large
// coordinates where the truncation lands late — montecarlo lost 95 of 195,997
// rail points, about 0.05%, which looks fine. It was only unmissable on
// cross-stitch fonts, whose pixel-art outlines are almost entirely
// scientific-notation offsets: their glyphs decoded as unrecognisable
// fragments rather than letters.
//
// This runs the real importer over a committed fixture, so it exercises the
// actual tokenizer rather than a copy of it.
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const ROOT = path.join(__dirname, "..");
const FIXTURE = path.join(__dirname, "fixtures", "fonts", "scinotation");

function importFixture() {
  const out = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "embfont-")), "out.json");
  execFileSync(process.execPath, [path.join(ROOT, "tools", "build-font.mjs"), FIXTURE, out], { stdio: "ignore" });
  return JSON.parse(fs.readFileSync(out, "utf8"));
}

test("a path written with scientific notation is not truncated", () => {
  const font = importFixture();
  // The fixture draws one square per glyph as "m 0,0 5e-4,40 h 40 l -3e-4,-40 z".
  // Truncating at "5e-4" leaves a single moveto point, which parsePath drops
  // (subpaths need >= 2 points) — so the glyph disappears entirely.
  assert.ok(font.glyphs["A"], "glyph A vanished — the path truncated at the first 5e-4");
  const g = font.glyphs["A"];
  const ring = (g.runs[0] && g.runs[0].pts) || g.runs[0];
  assert.ok(Array.isArray(ring), "expected a run of points");
  assert.strictEqual(ring.length, 5, `expected a closed 5-point square, got ${ring.length} points`);
});

test("the scientific-notation square has the right corners and closes", () => {
  const font = importFixture();
  const ring = (font.glyphs["A"].runs[0] && font.glyphs["A"].runs[0].pts) || font.glyphs["A"].runs[0];
  // 5e-4 and -3e-4 are sub-unit, so after rounding this is an exact square.
  assert.deepStrictEqual(ring, [[0, 0], [0, 40], [40, 40], [40, 0], [0, 0]]);
  assert.deepStrictEqual(ring[0], ring[ring.length - 1], "ring must close for fill to work");
});

test("every glyph in the fixture survives the import", () => {
  const font = importFixture();
  assert.deepStrictEqual(Object.keys(font.glyphs).sort(), ["A", "B"]);
});
