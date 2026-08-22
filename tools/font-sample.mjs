// Which characters a preview tile should set for a given font.
//
// Extracted from tools/build-previews.mjs 2026-08-22 so it can be TESTED. The
// grid of tiles is the only thing a customer sees before choosing a font, and
// when this picks badly nothing fails — the tile just quietly says less. That
// is exactly what happened to three fonts (see the fallback chain below), so
// the rule now lives where a test can reach it. Same reason
// tools/font-license.mjs is shared rather than duplicated.

// Sample: the font's own name where its glyphs allow, else uppercase, else
// the first few of the glyphs it actually has (pictogram packs show symbols
// — that IS their honest preview).
export function sampleFor(font) {
  const has = (ch) => ch === " " || !!(font.glyphs && font.glyphs[ch]);
  const name = String(font.name || "Sample");
  if ([...name].every(has)) return name;
  const caseFixed = name.replace(/[a-z]/g, (c) => c.toUpperCase());
  if ([...caseFixed].every(has)) return caseFixed;
  // ONE unrenderable character in the name should not cost the whole name
  // (2026-08-22). Three fonts were losing it over exactly that, and the tiles
  // they fell through to were worse in every case:
  //   fold_inkstitch  "Fold Ink/Stitch" — no "/" glyph — tile read "012345"
  //   hebrew_font_*   "חוכמה Large"     — no Latin     — tile read "אבגדה"
  // Dropping just the characters the font cannot set gives "FOLD INKSTITCH"
  // and "חוכמה" — the font's own name, which is what a browsing tile is for.
  //
  // Take whichever of the two spellings survives better rather than picking
  // one: stripping the ORIGINAL "Fold Ink/Stitch" in a caps-only font leaves
  // "FIS", while stripping the case-fixed spelling keeps all but the slash.
  // For Hebrew the two are identical, since case-fixing does nothing to it.
  const strip = (t) => [...t].filter(has).join("").replace(/\s+/g, " ").trim();
  const partial = [strip(name), strip(caseFixed)].sort((a, b) => b.length - a.length)[0];
  if (partial.length >= 3) return partial;
  // LETTERS BEFORE DIGITS, explicitly. Object.keys puts integer-like keys
  // first whatever the insertion order, so a bare key order hands back "0123"
  // before it hands back "ABCD" — for every font, not just unlucky ones. That
  // is why fold_inkstitch's tile read "012345" and not "ABCDEF", and a tile of
  // digits says almost nothing about a typeface. Found 2026-08-22 by a test
  // asserting the wrong expectation and being right anyway.
  const alnum = Object.keys(font.glyphs || {}).filter((k) => /^[A-Za-z0-9]$/.test(k));
  const own = alnum.filter((k) => /[A-Za-z]/.test(k)).concat(alnum.filter((k) => /[0-9]/.test(k)))
    .slice(0, 6).join("");
  if (own) return own;
  // Non-Latin fonts (Hebrew, 2026-08-22). Every fallback above assumes Latin
  // glyph names, so a Hebrew font fell through to "?" — which it does not
  // contain either — and rendered ZERO stitches. Both Hebrew faces shipped with
  // no preview tile at all, and the guard test caught it. Take the font's own
  // first few single-character glyphs whatever the script; layoutText handles
  // RTL ordering from font.dir, so the tile reads correctly.
  const any = Object.keys(font.glyphs || {})
    .filter((k) => [...k].length === 1 && k !== " " && k !== ".notdef")
    .slice(0, 5).join("");
  return any || "?";
}
