const assert = require("node:assert");
const { test } = require("node:test");
const { designToSVG } = require("../src/svgexport.js");

// DST units are 0.1mm (UNITS_PER_MM = 10 in src/svgexport.js) -- every
// coordinate below is chosen so the mm math comes out exact, so assertions
// can compare real numbers, not just substring presence.

function polylines(svg) {
  const out = [];
  const re = /<polyline[^>]*\/>/g;
  let m;
  while ((m = re.exec(svg))) out.push(m[0]);
  return out;
}
function attr(tag, name) {
  const m = tag.match(new RegExp(name + '="([^"]*)"'));
  return m ? m[1] : null;
}

const design = { stitches:[{x:-50,y:50,type:"stitch"},{x:50,y:50,type:"stitch"},{x:50,y:-50,type:"stitch"},{x:0,y:0,type:"end"}], colors:[{r:200,g:0,b:0,name:"Color 1"}], widthMM:10, heightMM:10, stitchCount:3, colorCount:1 };

test("SVG has svg root and a stroke color", () => {
  const s = designToSVG(design);
  assert.ok(s.startsWith("<svg"));
  assert.ok(s.includes("stroke"));
  assert.ok(s.includes("viewBox"));
});

test("viewBox/width/height reflect the real extents in mm, not the design's own (possibly stale) widthMM/heightMM fields", () => {
  const d = {
    stitches: [
      { x: 0, y: 0, type: "stitch" },
      { x: 300, y: 0, type: "stitch" }, // 30mm wide
      { x: 300, y: 200, type: "stitch" }, // 20mm tall
    ],
    colors: [{ r: 0, g: 0, b: 0 }],
    widthMM: 999, heightMM: 999, // intentionally wrong -- must be ignored
  };
  const s = designToSVG(d);
  const svgTag = s.match(/<svg[^>]*>/)[0];
  assert.strictEqual(attr(svgTag, "viewBox"), "0 0 30 20");
  assert.strictEqual(attr(svgTag, "width"), "30mm");
  assert.strictEqual(attr(svgTag, "height"), "20mm");
});

test("Y axis is flipped: DST +Y (up) becomes SVG +Y (down) with the top of the design at y=0", () => {
  const d = {
    stitches: [
      { x: 0, y: 100, type: "stitch" }, // DST-up-most point -> SVG top (y=0)
      { x: 0, y: -100, type: "stitch" }, // DST-down-most point -> SVG bottom
    ],
    colors: [{ r: 0, g: 0, b: 0 }],
  };
  const s = designToSVG(d);
  const [line] = polylines(s);
  const pts = attr(line, "points").split(" ").map((p) => p.split(",").map(Number));
  assert.deepStrictEqual(pts[0], [0, 0]);
  assert.deepStrictEqual(pts[1], [0, 20]); // 200 units of travel = 20mm
});

test("a color change splits the run into separate polylines, each in its own color", () => {
  const d = {
    stitches: [
      { x: 0, y: 0, type: "stitch" },
      { x: 10, y: 0, type: "stitch" },
      { x: 10, y: 0, type: "color" },
      { x: 10, y: 10, type: "stitch" },
      { x: 20, y: 10, type: "stitch" },
    ],
    colors: [{ r: 255, g: 0, b: 0 }, { r: 0, g: 255, b: 0 }],
  };
  const s = designToSVG(d);
  const lines = polylines(s);
  assert.strictEqual(lines.length, 2, "one polyline per color run");
  assert.strictEqual(attr(lines[0], "stroke"), "#ff0000");
  assert.strictEqual(attr(lines[1], "stroke"), "#00ff00");
});

test("a jump breaks the path without drawing a line across the travel gap", () => {
  const d = {
    stitches: [
      { x: 0, y: 0, type: "stitch" },
      { x: 10, y: 0, type: "stitch" },
      { x: 100, y: 100, type: "jump" }, // travels far away
      { x: 100, y: 100, type: "stitch" },
      { x: 110, y: 100, type: "stitch" },
    ],
    colors: [{ r: 0, g: 0, b: 0 }],
  };
  const s = designToSVG(d);
  const lines = polylines(s);
  assert.strictEqual(lines.length, 2, "the jump must start a new polyline, not extend the old one");
  assert.strictEqual(attr(lines[0], "points").split(" ").length, 2);
  assert.strictEqual(attr(lines[1], "points").split(" ").length, 2);
});

test("a trim breaks the path the same way a jump does", () => {
  const d = {
    stitches: [
      { x: 0, y: 0, type: "stitch" },
      { x: 10, y: 0, type: "stitch" },
      { x: 50, y: 50, type: "trim" },
      { x: 50, y: 50, type: "stitch" },
      { x: 60, y: 50, type: "stitch" },
    ],
    colors: [{ r: 0, g: 0, b: 0 }],
  };
  const s = designToSVG(d);
  assert.strictEqual(polylines(s).length, 2);
});

test("a run of a single stitch (surrounded by jumps) is dropped -- a lone point can't form a <polyline>", () => {
  // Documents current behavior, not a claim this is ideal: `run.length >= 2`
  // gates every push in designToSVG, so an isolated stitch between two jumps
  // renders nothing. Real designs essentially never produce a true
  // single-stitch run in isolation (satin/fill always emit runs of many),
  // so this is a low-stakes, deliberate simplification -- pinned here so a
  // future change to it is a conscious decision, not an accidental one.
  const d = {
    stitches: [
      { x: 0, y: 0, type: "jump" },
      { x: 10, y: 0, type: "stitch" }, // lone stitch, no line to draw
      { x: 20, y: 0, type: "jump" },
      { x: 30, y: 0, type: "stitch" },
      { x: 40, y: 0, type: "stitch" },
    ],
    colors: [{ r: 0, g: 0, b: 0 }],
  };
  const s = designToSVG(d);
  assert.strictEqual(polylines(s).length, 1, "only the 2-point run survives");
});

test("missing/undefined color falls back to black, not a crash", () => {
  const d = {
    stitches: [
      { x: 0, y: 0, type: "stitch" },
      { x: 10, y: 0, type: "stitch" },
    ],
    colors: [], // no color entry at all
  };
  const s = designToSVG(d);
  const [line] = polylines(s);
  assert.strictEqual(attr(line, "stroke"), "#000000");
});

test("an empty design (no stitches) produces a minimal valid, non-crashing SVG", () => {
  const s = designToSVG({ stitches: [], colors: [] });
  assert.ok(s.startsWith("<svg"));
  assert.ok(s.endsWith("</svg>"));
  assert.strictEqual(polylines(s).length, 0);
  const svgTag = s.match(/<svg[^>]*>/)[0];
  // Zero-extent design falls back to a 1x1mm viewBox rather than a
  // degenerate "0 0 0 0" one no viewer could render sensibly.
  assert.strictEqual(attr(svgTag, "viewBox"), "0 0 1 1");
});

test("designToSVG tolerates a null/undefined design entirely", () => {
  assert.doesNotThrow(() => designToSVG(undefined));
  assert.doesNotThrow(() => designToSVG(null));
  assert.doesNotThrow(() => designToSVG({}));
});
