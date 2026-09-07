// Which shipped fonts can stitch a given set of characters.
//
// The gap this closes: typing a Russian, Greek or Hebrew name in the default
// font produces "This font can’t stitch «Р», «у», «с». Try a different font,
// or different text." — true, actionable only by opening up to 85 fonts by
// hand. Three shipped fonts cover Cyrillic, three cover Greek, two cover
// Hebrew, and NONE covers Japanese, Korean or Arabic — which is a different
// answer the customer also deserves, because "try a different font" is advice
// to keep looking for something that is not there.
//
// The index is `src/fonts/manifest-coverage.json`, built from the shipped .embf
// binaries by tools/build-font-coverage.mjs and guarded by
// test/font-coverage.test.js. This module is PURE — fontLoader.js owns
// fetching it (it already owns "read a file out of the fonts directory", and
// that reader is the one that works in both Node and the browser), and it is
// fetched LAZILY, only once there is actually an unsupported character, so the
// common case pays nothing for it.

// Ranges are `cp | [lo, hi]`, sorted ascending — a binary search would be
// tidier, but the longest list is 137 entries (egyptian) and this runs once
// per unsupported-character event, not per frame.
function rangesCover(ranges, cp) {
  for (const r of ranges) {
    if (typeof r === "number") { if (r === cp) return true; if (r > cp) return false; continue; }
    if (cp < r[0]) return false;
    if (cp <= r[1]) return true;
  }
  return false;
}

// Every font whose coverage includes EVERY character of `text`.
//
// The WHOLE text, not just the characters that failed — that distinction is
// the difference between advice and a new dead end. `hebrew_font_large` holds
// 29 glyphs and no ASCII at all, so on "Shalom שלום" it covers exactly the
// characters that failed and none of the ones that worked; suggesting it would
// move the problem rather than fix it.
//
// Whitespace is skipped: a font is not disqualified for having no space glyph
// (the layout engine advances instead of looking one up), and requiring one
// would rule out every font on any multi-word name.
export function fontsCovering(text, coverage) {
  const fonts = (coverage && coverage.fonts) || null;
  if (!fonts || typeof text !== "string") return [];
  const cps = [...new Set([...text].filter((c) => !/\s/.test(c)).map((c) => c.codePointAt(0)))];
  if (!cps.length) return [];
  return Object.keys(fonts)
    .filter((key) => cps.every((cp) => rangesCover(fonts[key], cp)))
    .sort();
}

// The WHOLE "this font can't stitch X" message, so one place decides the
// wording. It used to be assembled at four call sites from a shared prefix
// plus a suffix, which read as two sentences arguing with each other once the
// "no font can" case existed:
//
//   This font can’t stitch “日”, “本” and “語” — No font in this library can
//   stitch those characters — try different text.
//
// Three outcomes, deliberately worded apart:
//   - fonts found         -> name them, capped, because a list of 70 is not advice
//   - none in the library -> lead with that; the current font is not the problem
//   - no index            -> the generic advice, unchanged from before this existed
//
// `charsText` is the already-formatted character list (generate.js's
// `charList`, which caps at six and says "and N more"). `text` is the WHOLE
// text the element is trying to set — see fontsCovering. `nameFor` maps a font
// key to its display name (the manifest's `name`), falling back to the key so
// a missing manifest degrades to something readable.
export function unsupportedMessage(charsText, text, coverage, nameFor = (k) => k, max = 3) {
  const cant = `This font can\u2019t stitch ${charsText}`;
  if (!coverage) return `${cant}. Try a different font, or different text.`;
  const keys = fontsCovering(text, coverage);
  if (!keys.length) {
    return `No font in this library can stitch ${charsText} \u2014 try different text.`;
  }
  const names = keys.slice(0, max).map(nameFor);
  const rest = keys.length - names.length;
  const list = names.length === 1
    ? names[0]
    : names.slice(0, -1).join(", ") + " and " + names[names.length - 1];
  const more = rest > 0 ? ` (${rest} more too)` : "";
  return `${cant} \u2014 ${list}${more} can. Switch fonts and it will stitch.`;
}
