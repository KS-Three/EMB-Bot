const assert = require("node:assert");
const { test } = require("node:test");
const { designToSVG } = require("../src/svgexport.js");

// Gap coverage for src/svgexport.js beyond test/svgexport.test.js.
// DST units are 0.1 mm, so coordinates are chosen to give exact mm values.

function polylines(svg) {
  return svg.match(/<polyline[^>]*\/>/g) || [];
}
function attr(tag, name) {
  const m = tag.match(new RegExp(name + '="([^"]*)"'));
  return m ? m[1] : null;
}
function pts(tag) {
  return attr(tag, "points").split(" ").map((p) => p.split(",").map(Number));
}
const S = (x, y, type) => (type ? { x, y, type } : { x, y });

test("stitches with no type field are treated as plain stitches", () => {
  const svg = designToSVG({ stitches: [S(0, 0), S(10, 0), S(10, 10)], colors: [{ r: 1, g: 2, b: 3 }] });
  assert.strictEqual(polylines(svg).length, 1);
  assert.strictEqual(pts(polylines(svg)[0]).length, 3);
});

test("color channels are clamped to 0..255 and written as two-digit hex", () => {
  const d = (c) => designToSVG({ stitches: [S(0, 0), S(10, 0)], colors: [c] });
  assert.strictEqual(attr(polylines(d({ r: 300, g: -5, b: 5 }))[0], "stroke"), "#ff0005");
  assert.strictEqual(attr(polylines(d({ r: 0, g: 0, b: 0 }))[0], "stroke"), "#000000");
  assert.strictEqual(attr(polylines(d({ r: 255, g: 255, b: 255 }))[0], "stroke"), "#ffffff");
});

test("fractional color channels truncate toward zero", () => {
  const svg = designToSVG({ stitches: [S(0, 0), S(10, 0)], colors: [{ r: 16.9, g: 0.9, b: 254.9 }] });
  assert.strictEqual(attr(polylines(svg)[0], "stroke"), "#1000fe");
});

test("color changes map runs to colors[1], colors[2]... in order", () => {
  const svg = designToSVG({
    stitches: [S(0, 0), S(10, 0), S(0, 0, "color"), S(0, 10), S(10, 10), S(0, 0, "color"), S(0, 20), S(10, 20)],
    colors: [{ r: 255, g: 0, b: 0 }, { r: 0, g: 255, b: 0 }, { r: 0, g: 0, b: 255 }],
  });
  assert.deepStrictEqual(polylines(svg).map((l) => attr(l, "stroke")), ["#ff0000", "#00ff00", "#0000ff"]);
});

test("more color changes than palette entries falls back to colors[0]", () => {
  const svg = designToSVG({
    stitches: [S(0, 0), S(10, 0), S(0, 0, "color"), S(0, 10), S(10, 10)],
    colors: [{ r: 255, g: 0, b: 0 }],
  });
  assert.deepStrictEqual(polylines(svg).map((l) => attr(l, "stroke")), ["#ff0000", "#ff0000"]);
});

test("back-to-back color changes skip a palette slot without emitting an empty polyline", () => {
  const svg = designToSVG({
    stitches: [S(0, 0), S(10, 0), S(0, 0, "color"), S(0, 0, "color"), S(0, 10), S(10, 10)],
    colors: [{ r: 255, g: 0, b: 0 }, { r: 0, g: 255, b: 0 }, { r: 0, g: 0, b: 255 }],
  });
  assert.deepStrictEqual(polylines(svg).map((l) => attr(l, "stroke")), ["#ff0000", "#0000ff"]);
});

test("an end record breaks the run like a jump", () => {
  const svg = designToSVG({
    stitches: [S(0, 0), S(10, 0), S(0, 0, "end"), S(0, 10), S(10, 10)],
    colors: [{ r: 0, g: 0, b: 0 }],
  });
  assert.strictEqual(polylines(svg).length, 2);
});

test("extents span every record including jumps, so a far jump widens the viewBox", () => {
  // Documents current behaviour (the box is not limited to drawn stitches).
  const svg = designToSVG({
    stitches: [S(0, 0), S(10, 0), S(1000, 0, "jump")],
    colors: [{ r: 0, g: 0, b: 0 }],
  });
  assert.strictEqual(attr(svg.match(/<svg[^>]*>/)[0], "viewBox"), "0 0 100 1");
});

test("coordinates are origin-shifted so the min corner sits at 0,0", () => {
  const svg = designToSVG({ stitches: [S(-200, -100), S(-100, 0)], colors: [{ r: 0, g: 0, b: 0 }] });
  // x: (-200..-100) -> 0..10mm; y flipped: yMax=0 -> -100 maps to 10, 0 maps to 0
  assert.deepStrictEqual(pts(polylines(svg)[0]), [[0, 10], [10, 0]]);
  assert.strictEqual(attr(svg.match(/<svg[^>]*>/)[0], "viewBox"), "0 0 10 10");
});

test("fractional stitch coordinates truncate to integer DST units", () => {
  const svg = designToSVG({ stitches: [S(0.9, 0.9), S(10.9, 0.9)], colors: [{ r: 0, g: 0, b: 0 }] });
  assert.deepStrictEqual(pts(polylines(svg)[0]), [[0, 0], [1, 0]]);
});

test("a zero-height design gets a 1mm viewBox height so the SVG stays valid", () => {
  const svg = designToSVG({ stitches: [S(0, 0), S(100, 0)], colors: [{ r: 0, g: 0, b: 0 }] });
  const tag = svg.match(/<svg[^>]*>/)[0];
  assert.strictEqual(attr(tag, "viewBox"), "0 0 10 1");
  assert.strictEqual(attr(tag, "height"), "1mm");
});

test("a zero-width design gets a 1mm viewBox width", () => {
  const svg = designToSVG({ stitches: [S(0, 0), S(0, 100)], colors: [{ r: 0, g: 0, b: 0 }] });
  assert.strictEqual(attr(svg.match(/<svg[^>]*>/)[0], "viewBox"), "0 0 1 10");
});

test("point coordinates are rounded to 3 decimals", () => {
  const svg = designToSVG({ stitches: [S(0, 0), S(1, 0), S(3, 0)], colors: [{ r: 0, g: 0, b: 0 }] });
  assert.deepStrictEqual(pts(polylines(svg)[0]), [[0, 0], [0.1, 0], [0.3, 0]]);
});

test("polyline draws at the 0.4mm display thread width with round joins and caps", () => {
  const svg = designToSVG({ stitches: [S(0, 0), S(10, 0)], colors: [{ r: 0, g: 0, b: 0 }] });
  const l = polylines(svg)[0];
  assert.strictEqual(attr(l, "stroke-width"), "0.4");
  assert.strictEqual(attr(l, "fill"), "none");
  assert.strictEqual(attr(l, "stroke-linejoin"), "round");
  assert.strictEqual(attr(l, "stroke-linecap"), "round");
});

test("output is a well-formed single svg element with the SVG namespace", () => {
  const svg = designToSVG({ stitches: [S(0, 0), S(10, 0)], colors: [] });
  assert.ok(svg.startsWith('<svg xmlns="http://www.w3.org/2000/svg"'));
  assert.ok(svg.endsWith("</svg>"));
  assert.strictEqual((svg.match(/<svg/g) || []).length, 1);
});

test("design with stitches but no colors array still renders black", () => {
  const svg = designToSVG({ stitches: [S(0, 0), S(10, 0)] });
  assert.strictEqual(attr(polylines(svg)[0], "stroke"), "#000000");
});

test("empty design viewBox is the 1x1mm fallback", () => {
  const svg = designToSVG({ stitches: [], colors: [] });
  assert.strictEqual(attr(svg.match(/<svg[^>]*>/)[0], "viewBox"), "0 0 1 1");
  assert.strictEqual(polylines(svg).length, 0);
});
