// Access the engine global loaded by the <script> tags in index.html.
// The engine modules (dual-mode IIFEs) assign onto globalThis.EMB.
const g = typeof window !== "undefined" ? window : globalThis;
if (!g.EMB || typeof g.EMB.buildLetteringDesign !== "function") {
  throw new Error("Engine not loaded — check the <script src=\"/engine/...\"> tags in index.html and that scripts/copy-engine.mjs ran.");
}
export const EMB = g.EMB;

// Ordered list of engine script filenames, in dependency order.
// MUST stay in sync with scripts/copy-engine.mjs's ENGINE_FILES and the
// <script src="/engine/..."> order in index.html.
export const ENGINE_KEYS = [
  "units.js", "garments.js", "fabrics.js", "fill.js", "geometry.js",
  "quantize.js", "flatten.js", "satin.js", "satinplay.js", "crossfill.js", "satinfont.js",
  "fontbin.js",
  "svgpath.js", "svgimport.js",
  "dst.js", "dstimport.js", "exp.js", "pes.js", "svgexport.js", "stitchModel.js",
  // "fonts.js" is deliberately NOT here. It is 137 Google-Fonts CDN URLs
  // whose loader needs a global `opentype` that the Studio never loads, so
  // every one of its entry points throws if called — and nothing in app/src
  // calls them (FONTS, loadFont, textToRegions, textToLetters, pathToPolygons:
  // zero references). The Studio's lettering runs on local .embf files via
  // lib/fontLoader.js instead. The FILE stays: five tools/ scripts still use
  // it from Node, where `opentype` can be required. Removing it from this list
  // is what makes "the Studio has no CDN runtime dependencies" true rather
  // than nearly true. If outline-text ever returns to the browser, use fontkit
  // (maintained) rather than opentype.js 1.3.4 (dormant since 2020).
  "digitize.js", "render.js", "pdfsheet.js",
];
