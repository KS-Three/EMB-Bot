// Pure font-list filtering for the browser dialog. Kept out of the component
// so it's unit-testable without DOM.
//
// `styles` is the optional {key: [tag, ...]} map from src/fonts/manifest-styles.json
// (tools/tag-font-styles.mjs). With it, a query also matches a font by its
// STYLE: every word of the query must hit the name, the key, a tag, or a
// synonym of a tag, so "bold script" narrows to bold script fonts. Without it
// (older build, fetch failed) behaviour is exactly the old name/key substring
// match — the whole query is always still tried as one substring first, so
// multi-word names like "Geneva Simple" keep working.
const SYNONYMS = {
  cursive: ["script", "handwritten"],
  handwriting: ["handwritten"],
  calligraphy: ["script", "elegant"],
  fancy: ["decorative", "ornate"],
  ornamental: ["ornate"],
  old: ["vintage", "retro"],
  oldfashioned: ["vintage"],
  antique: ["vintage"],
  cowboy: ["western"],
  wild: ["western"],
  comic: ["playful"],
  fun: ["playful"],
  cute: ["playful", "rounded"],
  thick: ["bold"],
  heavy: ["bold"],
  fat: ["bold"],
  thin: ["light", "narrow-stroke"],
  skinny: ["light", "condensed"],
  tall: ["condensed"],
  narrow: ["condensed"],
  wedding: ["elegant", "script"],
  classy: ["elegant", "formal"],
  fancyscript: ["script", "ornate"],
  varsity: ["block", "bold"],
  college: ["block"],
  army: ["military", "stencil"],
  tiny: ["small"],
  gothic: ["gothic", "blackletter"],
  oldenglish: ["blackletter"],
  initials: ["monogram"],
  sans: ["sans"],
  "sans-serif": ["sans"],
};

function tokens(q) {
  return q.split(/[\s,]+/).filter(Boolean);
}

function tokenMatches(tok, f, tags) {
  if (f.name.toLowerCase().includes(tok) || f.key.toLowerCase().includes(tok)) return true;
  if (!tags.length) return false;
  if (tags.some((t) => t === tok || (tok.length >= 3 && t.startsWith(tok)))) return true;
  return (SYNONYMS[tok] || []).some((s) => tags.includes(s));
}

export function filterFonts(fonts, query, group, styles) {
  const q = (query || "").trim().toLowerCase();
  const toks = tokens(q);
  return (fonts || []).filter((f) => {
    if (group && group !== "All" && f.group !== group) return false;
    if (!q) return true;
    if (f.name.toLowerCase().includes(q) || f.key.toLowerCase().includes(q)) return true;
    if (!styles || toks.length === 0) return false;
    const tags = (styles[f.key] || []).map((t) => t.toLowerCase());
    return toks.every((tok) => tokenMatches(tok, f, tags));
  });
}

// Recommended size band from the authored size. Multipliers are a starting
// point per the spec — validate against real stitch-outs before trusting.
export function sizeBand(sizeMm) {
  if (!(sizeMm > 0)) return null;
  return { min: Math.round(sizeMm * 0.75), max: Math.round(sizeMm * 2.0) };
}
