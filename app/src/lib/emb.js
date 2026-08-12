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
  "quantize.js", "flatten.js", "satin.js", "satinplay.js", "satinfont.js",
  "fontbin.js",
  "svgpath.js", "svgimport.js",
  "dst.js", "dstimport.js", "exp.js", "pes.js", "svgexport.js", "stitchModel.js",
  "fonts.js", "digitize.js", "render.js", "pdfsheet.js",
];
