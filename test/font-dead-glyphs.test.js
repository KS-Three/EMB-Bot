// Glyphs that are PRESENT in a shipped font and sew nothing (2026-08-22).
//
// Different from a stunted glyph, which sews a stub, and different from a
// character the font simply lacks. This one is in the font, takes its advance,
// looks selectable in every UI — and puts no thread down. Type "2024" in
// western_light and the 4 is a gap.
//
// The engine reports these at layout time now (`unsupported`, and the Studio
// shows "This font can't stitch …"), so the user is told at the moment it
// matters. This file is the other half: a census, so a NEW one is caught on
// the way in rather than discovered by a customer.
//
// qc-font cannot cover it. Its stitchability check is scoped to LETTERS by
// design — that is what the sellable/personal tier decision turns on — so a
// dead digit or a dead hyphen has never been in its field of view.
//
// The list is a debt register, not a suppression list. It fails in BOTH
// directions: a new dead glyph fails, and an entry that is no longer dead
// fails too. Nothing here is fixable from this repo — the geometry is
// upstream's — so the register is the honest form. Do not "fix" a failure by
// widening it; work out which font changed and why.
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const fb = require("../src/fontbin.js");

const BIN = path.join(__dirname, "..", "src", "fonts", "bin");

// Exactly the rule the stitch path uses — routeGlyph / routeRuns / crossFill,
// mirrored in satinfont.js `sewsSomething` and qc-font's `stitchable`. A run
// without an authored stitch length is never sewn (ROADMAP gate 1 bars this
// project from inventing one), and a cross-stitch region needs the font's
// measured grid to fill it.
function sews(font, g) {
  if ((g.cols || []).length) return true;
  if (font.crossGrid && (g.runs || []).some((r) => r && r.fill === "cross" && r.pts)) return true;
  return (g.runs || []).some((r) => r && r.pts && r.lenMm > 0);
}

// key -> the single characters that are present and sew nothing.
// Measured 2026-08-22 over all 85 shipped fonts: 26 glyphs in 6 fonts.
//
// A MECHANISM that would produce exactly this, worth stating because it is
// proven even where the instances are not: build-font's stripRunParamsIfSatin
// is FONT-WIDE. If any glyph in the font has satin columns, every glyph's run
// parameters are stripped — including a glyph with NO columns, whose runs are
// the entire character. That is the shape of roaring_twenties_KOR's ten dead
// symbols: "-" is one 2-point run, "=" six runs, and the font's letters are
// satin. The strip exists for a good reason (honouring authored run params on
// satin fonts would add construction stitches to every already-shipped satin
// font — Kent's call, deliberately deferred), but its blast radius includes
// glyphs where the run is not construction, it is the glyph.
//
// NOT confirmed for these fonts, and do not write it up as confirmed: whether
// upstream authored a stitch length that was stripped, or never authored one,
// is indistinguishable from the built JSON — both produce a bare point array.
// It needs the Ink/Stitch SVG sources in scratch_ink/, which exist on Kent's
// machine and not in a cloud checkout.
const KNOWN_DEAD = {
  ondulamarif_Medium: ["'"],
  ondulamarif_S: ["'"],
  ondulamarif_XL: [":", "º"],
  roaring_twenties_KOR: ["+", "-", "/", "<", "=", ">", "\\", "_", "¯", "°"],
  roaring_twenties_KOR_small: ["+", "-", "/", "<", "=", ">", "\\", "_", "¯", "°"],
  western_light: ["4", "ç"],
};

function deadGlyphs(font) {
  return Object.keys(font.glyphs)
    .filter((k) => [...k].length === 1 && k !== " ")
    .filter((k) => !sews(font, font.glyphs[k]))
    .sort();
}

function loadAll() {
  // src/fonts/bin/ is COMMITTED. On CI a missing library means the build did
  // not run — not that there is nothing to check — and a test that returns
  // early asserts nothing while reporting green.
  if (!fs.existsSync(BIN)) {
    if (process.env.CI) throw new Error("src/fonts/bin missing on CI — the font library did not build");
    return null;
  }
  const files = fs.readdirSync(BIN).filter((f) => f.endsWith(".embf"));
  assert.ok(files.length > 50, `only ${files.length} .embf files — the library did not build`);
  return files.map((f) => [f.replace(/\.embf$/, ""), fb.decodeFontBin(fs.readFileSync(path.join(BIN, f)))]);
}

test("no shipped font has an unrecorded glyph that sews nothing", () => {
  const all = loadAll();
  if (!all) return;
  const surprises = [];
  for (const [key, font] of all) {
    const allowed = new Set(KNOWN_DEAD[key] || []);
    const fresh = deadGlyphs(font).filter((c) => !allowed.has(c));
    if (fresh.length) surprises.push(`${key}: ${fresh.map((c) => JSON.stringify(c)).join(", ")}`);
  }
  assert.deepStrictEqual(surprises, [],
    "these glyphs exist in the font, take their advance, and put no thread down — " +
    "a user typing them gets a silent gap. Work out whether the font should ship " +
    "before adding it to KNOWN_DEAD.");
});

test("the register is real — a glyph that started stitching must come off the list", () => {
  const all = loadAll();
  if (!all) return;
  const byKey = new Map(all);
  const stale = [];
  for (const [key, chars] of Object.entries(KNOWN_DEAD)) {
    const font = byKey.get(key);
    if (!font) continue; // font pulled from the library; nothing to check
    const dead = new Set(deadGlyphs(font));
    const revived = chars.filter((c) => !dead.has(c));
    if (revived.length) stale.push(`${key}: ${revived.map((c) => JSON.stringify(c)).join(", ")}`);
  }
  assert.deepStrictEqual(stale, [],
    "these now stitch — drop them from KNOWN_DEAD so the register keeps meaning something");
});

test("the engine REPORTS them, which is the half the user actually sees", () => {
  const all = loadAll();
  if (!all) return;
  for (const m of ["units", "garments", "fabrics", "fill", "geometry", "satin",
                   "satinplay", "satinfont", "fontbin", "dst", "fonts", "digitize"])
    require("../src/" + m + ".js");
  const EMB = globalThis.EMB;
  const byKey = new Map(all);
  // A census that nobody surfaces is just a list. Pin the actual user-visible
  // behaviour for one case from each class — a digit, a letter, punctuation.
  for (const [key, text, want] of [
    ["western_light", "2024", ["4"]],
    ["western_light", "façade", ["ç"]],
    ["roaring_twenties_KOR", "A-B", ["-"]],
  ]) {
    const font = byKey.get(key);
    if (!font) continue;
    assert.deepStrictEqual(
      EMB.layoutText(font, text, { emMm: 20, pxPerMm: 8 }).unsupported, want,
      `${key} typing ${JSON.stringify(text)} must report ${JSON.stringify(want)}`);
  }
});
