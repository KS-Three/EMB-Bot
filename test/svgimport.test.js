const assert = require("node:assert");
const { test } = require("node:test");
require("../src/svgpath.js");
const svg = require("../src/svgimport.js");

function approx(a, b, eps) { return Math.abs(a - b) < (eps === undefined ? 1e-9 : eps); }

// ---------------------------------------------------------------------
// Transforms
// ---------------------------------------------------------------------

test("parses translate, scale and rotate into matrices", () => {
  assert.deepStrictEqual(svg.parseTransform("translate(10 20)"), [1, 0, 0, 1, 10, 20]);
  assert.deepStrictEqual(svg.parseTransform("translate(10)"), [1, 0, 0, 1, 10, 0]);
  assert.deepStrictEqual(svg.parseTransform("scale(2 3)"), [2, 0, 0, 3, 0, 0]);
  assert.deepStrictEqual(svg.parseTransform("scale(2)"), [2, 0, 0, 2, 0, 0]);
  assert.deepStrictEqual(svg.parseTransform("matrix(1 2 3 4 5 6)"), [1, 2, 3, 4, 5, 6]);
  const r = svg.parseTransform("rotate(90)");
  assert.ok(approx(r[0], 0) && approx(r[1], 1) && approx(r[2], -1) && approx(r[3], 0));
});

test("unknown or empty transform is the identity", () => {
  assert.deepStrictEqual(svg.parseTransform(""), [1, 0, 0, 1, 0, 0]);
  assert.deepStrictEqual(svg.parseTransform("wobble(3)"), [1, 0, 0, 1, 0, 0]);
});

test("multiple transforms compose left to right", () => {
  // translate then scale: the scale applies in the translated frame.
  const m = svg.parseTransform("translate(10 0) scale(2)");
  assert.deepStrictEqual(svg.applyMatrix(m, { x: 5, y: 0 }), { x: 20, y: 0 });
});

test("rotate with a center rotates about that point", () => {
  const m = svg.parseTransform("rotate(90 10 10)");
  const p = svg.applyMatrix(m, { x: 10, y: 10 });
  assert.ok(approx(p.x, 10, 1e-9) && approx(p.y, 10, 1e-9));
});

test("skewX shears along x", () => {
  const m = svg.parseTransform("skewX(45)");
  const p = svg.applyMatrix(m, { x: 0, y: 1 });
  assert.ok(approx(p.x, 1, 1e-9) && approx(p.y, 1, 1e-9));
});

// ---------------------------------------------------------------------
// Shape primitives
// ---------------------------------------------------------------------

test("rect primitive becomes a closed four point subpath", () => {
  const subs = svg.primitiveToSubpaths("rect", { x: "1", y: "2", width: "10", height: "5" }, {});
  assert.strictEqual(subs.length, 1);
  assert.strictEqual(subs[0].closed, true);
  assert.deepStrictEqual(subs[0].points, [
    { x: 1, y: 2 }, { x: 11, y: 2 }, { x: 11, y: 7 }, { x: 1, y: 7 },
  ]);
});

test("rect with rx produces rounded corners", () => {
  const subs = svg.primitiveToSubpaths("rect",
    { x: "0", y: "0", width: "20", height: "10", rx: "3" }, { tolerance: 0.1 });
  assert.strictEqual(subs[0].closed, true);
  assert.ok(subs[0].points.length > 8, "expected corner arcs to add points");
  for (const p of subs[0].points) {
    assert.ok(p.x >= -1e-9 && p.x <= 20 + 1e-9 && p.y >= -1e-9 && p.y <= 10 + 1e-9);
  }
});

test("circle primitive lies on its radius", () => {
  const subs = svg.primitiveToSubpaths("circle", { cx: "5", cy: "5", r: "4" }, { tolerance: 0.05 });
  assert.strictEqual(subs[0].closed, true);
  for (const p of subs[0].points) {
    assert.ok(Math.abs(Math.hypot(p.x - 5, p.y - 5) - 4) < 0.2);
  }
});

test("ellipse honors separate radii", () => {
  const subs = svg.primitiveToSubpaths("ellipse", { cx: "0", cy: "0", rx: "10", ry: "5" }, { tolerance: 0.05 });
  let maxX = 0, maxY = 0;
  for (const p of subs[0].points) { maxX = Math.max(maxX, Math.abs(p.x)); maxY = Math.max(maxY, Math.abs(p.y)); }
  assert.ok(Math.abs(maxX - 10) < 0.2 && Math.abs(maxY - 5) < 0.2);
});

test("polygon closes but polyline does not", () => {
  const poly = svg.primitiveToSubpaths("polygon", { points: "0,0 10,0 10,10" }, {});
  const line = svg.primitiveToSubpaths("polyline", { points: "0,0 10,0 10,10" }, {});
  assert.strictEqual(poly[0].closed, true);
  assert.strictEqual(line[0].closed, false);
  assert.deepStrictEqual(poly[0].points, [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }]);
});

test("line primitive yields two points", () => {
  const subs = svg.primitiveToSubpaths("line", { x1: "0", y1: "0", x2: "3", y2: "4" }, {});
  assert.deepStrictEqual(subs[0].points, [{ x: 0, y: 0 }, { x: 3, y: 4 }]);
});

test("unknown tag yields no subpaths", () => {
  assert.deepStrictEqual(svg.primitiveToSubpaths("marker", {}, {}), []);
});

// ---------------------------------------------------------------------
// Document parsing
// ---------------------------------------------------------------------

function svgDoc(inner, attrs) {
  return '<svg xmlns="http://www.w3.org/2000/svg" ' + (attrs || 'viewBox="0 0 100 100"') + '>' + inner + '</svg>';
}

test("parses a single filled rect into one region", () => {
  const out = svg.parseSVG(svgDoc('<rect x="10" y="10" width="80" height="80" fill="#ff0000"/>'));
  assert.strictEqual(out.regions.length, 1);
  assert.deepStrictEqual(out.regions[0].rgb, [255, 0, 0]);
  assert.strictEqual(out.regions[0].shapes.length, 1);
  assert.strictEqual(out.regions[0].shapes[0].holes.length, 0);
});

test("identical fills across elements merge into one region", () => {
  const out = svg.parseSVG(svgDoc(
    '<rect x="0" y="0" width="10" height="10" fill="#00ff00"/>' +
    '<rect x="50" y="50" width="10" height="10" fill="#00ff00"/>'));
  assert.strictEqual(out.regions.length, 1, "same color should be one region");
  assert.strictEqual(out.regions[0].shapes.length, 2);
});

test("different fills produce separate regions", () => {
  const out = svg.parseSVG(svgDoc(
    '<rect x="0" y="0" width="10" height="10" fill="#00ff00"/>' +
    '<rect x="50" y="50" width="10" height="10" fill="#0000ff"/>'));
  assert.strictEqual(out.regions.length, 2);
});

test("resolves fill from hex shorthand, rgb() and named colors", () => {
  const hex3 = svg.parseSVG(svgDoc('<rect width="10" height="10" fill="#f00"/>'));
  assert.deepStrictEqual(hex3.regions[0].rgb, [255, 0, 0]);
  const rgb = svg.parseSVG(svgDoc('<rect width="10" height="10" fill="rgb(0, 128, 255)"/>'));
  assert.deepStrictEqual(rgb.regions[0].rgb, [0, 128, 255]);
  const named = svg.parseSVG(svgDoc('<rect width="10" height="10" fill="black"/>'));
  assert.deepStrictEqual(named.regions[0].rgb, [0, 0, 0]);
});

test("inline style fill beats the presentation attribute", () => {
  const out = svg.parseSVG(svgDoc('<rect width="10" height="10" fill="#ff0000" style="fill:#0000ff"/>'));
  assert.deepStrictEqual(out.regions[0].rgb, [0, 0, 255]);
});

test("fill is inherited from an ancestor group", () => {
  const out = svg.parseSVG(svgDoc('<g fill="#123456"><rect width="10" height="10"/></g>'));
  assert.deepStrictEqual(out.regions[0].rgb, [0x12, 0x34, 0x56]);
});

test("fill none is skipped entirely", () => {
  const out = svg.parseSVG(svgDoc('<rect width="10" height="10" fill="none"/>'));
  assert.strictEqual(out.regions.length, 0);
});

test("missing fill defaults to black per the SVG spec", () => {
  const out = svg.parseSVG(svgDoc('<rect width="10" height="10"/>'));
  assert.deepStrictEqual(out.regions[0].rgb, [0, 0, 0]);
});

test("group transforms apply to child geometry", () => {
  const out = svg.parseSVG(svgDoc('<g transform="translate(100 0)"><rect width="10" height="10" fill="#fff"/></g>'));
  const pts = out.regions[0].shapes[0].outer;
  for (const p of pts) assert.ok(p.x >= 100 - 1e-6);
});

test("nested group transforms compose", () => {
  const out = svg.parseSVG(svgDoc(
    '<g transform="translate(10 0)"><g transform="scale(2)">' +
    '<rect width="10" height="10" fill="#fff"/></g></g>'));
  let maxX = -Infinity;
  for (const p of out.regions[0].shapes[0].outer) maxX = Math.max(maxX, p.x);
  assert.ok(Math.abs(maxX - 30) < 1e-6, "expected 10 + 10*2 = 30, got " + maxX);
});

test("elements with explicit closing tags keep the state stack balanced", () => {
  // <rect></rect> is legal SVG; its closing tag must pop the rect's own
  // frame, not the enclosing group's. If the stack goes unbalanced the
  // second rect loses the red group fill.
  const out = svg.parseSVG(svgDoc(
    '<g fill="#ff0000"><rect width="10" height="10"></rect>' +
    '<rect x="20" width="10" height="10"></rect></g>'));
  assert.strictEqual(out.regions.length, 1);
  assert.deepStrictEqual(out.regions[0].rgb, [255, 0, 0]);
  assert.strictEqual(out.regions[0].shapes.length, 2);
});

test("geometry inside defs, clipPath or gradients does not render", () => {
  const out = svg.parseSVG(svgDoc(
    '<defs><rect width="50" height="50" fill="#ff0000"/></defs>' +
    '<clipPath id="c"><circle cx="5" cy="5" r="5" fill="#00ff00"/></clipPath>' +
    '<rect width="10" height="10" fill="#0000ff"/>'));
  assert.strictEqual(out.regions.length, 1, "only the visible rect should import");
  assert.deepStrictEqual(out.regions[0].rgb, [0, 0, 255]);
});

test("use instances a defs element at its x/y offset", () => {
  const out = svg.parseSVG(svgDoc(
    '<defs><rect id="r" width="10" height="10" fill="#f00"/></defs>' +
    '<use href="#r" x="20"/>'));
  assert.strictEqual(out.regions.length, 1);
  const xs = out.regions[0].shapes[0].outer.map((p) => p.x);
  assert.strictEqual(Math.min(...xs), 20);
  assert.strictEqual(Math.max(...xs), 30);
});

test("unresolvable use references warn and are skipped", () => {
  const out = svg.parseSVG(svgDoc('<use href="other.svg#r" x="20"/><use href="#missing"/>'));
  assert.strictEqual(out.regions.length, 0);
  assert.ok(out.warnings.some((w) => /use/i.test(w)));
});

// ---------------------------------------------------------------------
// Exporter-style documents (synthetic, written to mimic each app's output)
// ---------------------------------------------------------------------

function bbox(shape) {
  const xs = shape.outer.map((p) => p.x), ys = shape.outer.map((p) => p.y);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)].map((v) => Math.round(v * 1000) / 1000);
}

test("Illustrator style: CSS class fills in a <style> block", () => {
  const doc = '<?xml version="1.0" encoding="utf-8"?>\n' +
    '<!-- Generator: Adobe Illustrator 28.0.0, SVG Export Plug-In . SVG Version: 6.00 Build 0)  -->\n' +
    '<svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"\n' +
    '\t viewBox="0 0 100 100" style="enable-background:new 0 0 100 100;" xml:space="preserve">\n' +
    '<style type="text/css">\n\t.st0{fill:#E30613;}\n\t.st1{fill:none;stroke:#000000;stroke-miterlimit:10;}\n\t.st2,.st3{fill:#1D71B8;}\n</style>\n' +
    '<rect x="10" y="10" class="st0" width="20" height="20"/>\n' +
    '<circle class="st1" cx="50" cy="50" r="10"/>\n' +
    '<polygon class="st3" points="60,60 90,60 90,90 "/>\n' +
    '</svg>';
  const out = svg.parseSVG(doc);
  const colors = out.regions.map((r) => r.rgb.join(",")).sort();
  assert.deepStrictEqual(colors, ["227,6,19", "29,113,184"]);
});

test("inline style beats a class rule, which beats the attribute", () => {
  const out = svg.parseSVG(svgDoc(
    '<style>.a{fill:#00ff00}</style>' +
    '<rect class="a" fill="#ff0000" width="10" height="10"/>' +
    '<rect class="a" style="fill:#0000ff" x="20" width="10" height="10"/>'));
  const colors = out.regions.map((r) => r.rgb.join(",")).sort();
  assert.deepStrictEqual(colors, ["0,0,255", "0,255,0"]);
});

test("Inkscape style: CDATA style, nested layer transforms, xlink:href clones", () => {
  const doc = '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" ' +
    'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="100mm" height="100mm" viewBox="0 0 100 100">' +
    '<defs id="defs2"><style id="s1"><![CDATA[ .ink { fill: #ff6600 } ]]></style></defs>' +
    '<g inkscape:label="Layer 1" inkscape:groupmode="layer" id="layer1" transform="translate(10,0)">' +
    '<g id="g5" transform="scale(2)">' +
    '<path id="p1" class="ink" d="m 0,0 h 5 v 5 h -5 z"/>' +
    '</g>' +
    '<use xlink:href="#p1" id="use1" transform="translate(40,0)"/>' +
    '</g></svg>';
  const out = svg.parseSVG(doc);
  assert.strictEqual(out.regions.length, 1);
  const boxes = out.regions[0].shapes.map(bbox).sort((a, b) => a[0] - b[0]);
  // Original: layer translate(10) * scale(2). Clone: layer translate(10) *
  // translate(40) and NOT the g5 scale, since use references the raw path.
  assert.deepStrictEqual(boxes, [[10, 0, 20, 10], [50, 0, 55, 5]]);
});

test("Figma style: clip-path group with defs clipPath imports unclipped and warns", () => {
  const doc = '<svg width="100" height="100" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">' +
    '<g clip-path="url(#clip0_1_2)">' +
    '<path fill-rule="evenodd" clip-rule="evenodd" d="M10 10H90V90H10V10ZM30 30V70H70V30H30Z" fill="#111111"/>' +
    '</g>' +
    '<defs><clipPath id="clip0_1_2"><rect width="100" height="100" fill="white"/></clipPath></defs>' +
    '</svg>';
  const out = svg.parseSVG(doc);
  assert.strictEqual(out.regions.length, 1); // the white clip rect never renders
  assert.deepStrictEqual(out.regions[0].rgb, [17, 17, 17]);
  assert.strictEqual(out.regions[0].shapes.length, 1);
  assert.strictEqual(out.regions[0].shapes[0].holes.length, 1);
  assert.ok(out.warnings.some((w) => /clip/i.test(w)));
});

test("root fill=none (Figma) does not hide children that set their own fill", () => {
  const out = svg.parseSVG('<svg viewBox="0 0 10 10" fill="none" xmlns="http://www.w3.org/2000/svg">' +
    '<rect width="5" height="5" fill="#123456"/><rect x="6" width="2" height="2"/></svg>');
  assert.strictEqual(out.regions.length, 1);
  assert.deepStrictEqual(out.regions[0].rgb, [18, 52, 86]);
});

test("symbol instanced by use renders with the use's inherited fill", () => {
  const out = svg.parseSVG(svgDoc(
    '<defs><symbol id="sym"><rect width="10" height="10"/></symbol></defs>' +
    '<use href="#sym" fill="#00ff00" x="5" y="5"/>'));
  assert.strictEqual(out.regions.length, 1);
  assert.deepStrictEqual(out.regions[0].rgb, [0, 255, 0]);
  assert.deepStrictEqual(bbox(out.regions[0].shapes[0]), [5, 5, 15, 15]);
});

test("commented-out markup is ignored", () => {
  const out = svg.parseSVG(svgDoc('<!-- <rect width="10" height="10" fill="#f00"/> --><rect width="3" height="3" fill="#00f"/>'));
  assert.strictEqual(out.regions.length, 1);
  assert.deepStrictEqual(out.regions[0].rgb, [0, 0, 255]);
});

test("self-referencing use does not recurse forever", () => {
  const out = svg.parseSVG(svgDoc('<g id="loop"><rect width="2" height="2"/><use href="#loop" x="3"/></g>'));
  assert.strictEqual(out.regions.length, 1);
});

test("strokes-only Inkscape art via class still warns about strokes", () => {
  const out = svg.parseSVG(svgDoc('<style>.s{fill:none;stroke:#000;stroke-width:2}</style><path class="s" d="M0 0 L50 50"/>'));
  assert.strictEqual(out.regions.length, 0);
  assert.ok(out.warnings.some((w) => /stroke/i.test(w)));
});

test("gradient fills warn and skip the element", () => {
  const out = svg.parseSVG(svgDoc('<rect width="10" height="10" fill="url(#grad)"/>'));
  assert.strictEqual(out.regions.length, 0);
  assert.ok(out.warnings.some((w) => /gradient|pattern/i.test(w)));
});

// ---------------------------------------------------------------------
// Fill rules and holes
// ---------------------------------------------------------------------

test("a subpath inside another becomes a hole under evenodd", () => {
  // Outer square with an inner square wound the SAME direction, one path.
  const d = "M 0 0 H 100 V 100 H 0 Z M 25 25 H 75 V 75 H 25 Z";
  const out = svg.parseSVG(svgDoc('<path d="' + d + '" fill="#000" fill-rule="evenodd"/>'));
  assert.strictEqual(out.regions[0].shapes.length, 1);
  assert.strictEqual(out.regions[0].shapes[0].holes.length, 1);
});

test("nonzero keeps a same-direction nested ring filled (no hole)", () => {
  // Same geometry as the evenodd test, default fill-rule (nonzero): both
  // rings wind the same way, so the winding number inside the inner ring is
  // 2 — still filled. The inner ring is invisible and must NOT punch a hole.
  const d = "M 0 0 H 100 V 100 H 0 Z M 25 25 H 75 V 75 H 25 Z";
  const out = svg.parseSVG(svgDoc('<path d="' + d + '" fill="#000"/>'));
  assert.strictEqual(out.regions[0].shapes.length, 1);
  assert.strictEqual(out.regions[0].shapes[0].holes.length, 0);
});

test("nonzero makes an opposite-direction nested ring a hole", () => {
  // Inner ring reversed: winding inside it is 1 - 1 = 0, so it is a hole
  // under nonzero too (this is how design tools export donuts).
  const d = "M 0 0 H 100 V 100 H 0 Z M 25 25 V 75 H 75 V 25 Z";
  const out = svg.parseSVG(svgDoc('<path d="' + d + '" fill="#000"/>'));
  assert.strictEqual(out.regions[0].shapes.length, 1);
  assert.strictEqual(out.regions[0].shapes[0].holes.length, 1);
});

test("two disjoint subpaths are two shapes, not a hole", () => {
  const d = "M 0 0 H 10 V 10 H 0 Z M 50 50 H 60 V 60 H 50 Z";
  const out = svg.parseSVG(svgDoc('<path d="' + d + '" fill="#000"/>'));
  assert.strictEqual(out.regions[0].shapes.length, 2);
  assert.strictEqual(out.regions[0].shapes[0].holes.length, 0);
});

test("a same-colored element on top of another does not punch a hole", () => {
  // Two separate ELEMENTS: SVG paints each independently, so a small square
  // over a big same-colored square is just paint on paint — unlike two
  // subpaths of one evenodd path.
  const out = svg.parseSVG(svgDoc(
    '<rect width="100" height="100" fill="#000" fill-rule="evenodd"/>' +
    '<rect x="25" y="25" width="50" height="50" fill="#000" fill-rule="evenodd"/>'));
  assert.strictEqual(out.regions.length, 1);
  assert.strictEqual(out.regions[0].shapes.length, 2);
  assert.strictEqual(out.regions[0].shapes[0].holes.length, 0);
  assert.strictEqual(out.regions[0].shapes[1].holes.length, 0);
});

test("island inside a hole becomes its own shape", () => {
  // Ring 1 (fill) > ring 2 (hole) > ring 3 (fill again), evenodd.
  const d = "M 0 0 H 100 V 100 H 0 Z" +
    " M 20 20 H 80 V 80 H 20 Z" +
    " M 40 40 H 60 V 60 H 40 Z";
  const out = svg.parseSVG(svgDoc('<path d="' + d + '" fill="#000" fill-rule="evenodd"/>'));
  assert.strictEqual(out.regions[0].shapes.length, 2);
  const big = out.regions[0].shapes.find((s) => s.holes.length === 1);
  const island = out.regions[0].shapes.find((s) => s.holes.length === 0);
  assert.ok(big, "expected the outer shape to carry the hole");
  assert.ok(island, "expected the innermost ring to become its own shape");
});

// ---------------------------------------------------------------------
// Sizing, warnings, degenerate input
// ---------------------------------------------------------------------

test("pxPerMm maps the viewBox long side to targetLongMm", () => {
  const out = svg.parseSVG(svgDoc('<rect width="10" height="10" fill="#000"/>', 'viewBox="0 0 200 100"'), { targetLongMm: 50 });
  // 200 user units across 50mm -> 4 units per mm.
  assert.ok(Math.abs(out.pxPerMm - 4) < 1e-9, "got " + out.pxPerMm);
});

test("missing viewBox falls back to width/height and warns", () => {
  const out = svg.parseSVG(svgDoc('<rect width="10" height="10" fill="#000"/>', 'width="300" height="150"'));
  assert.ok(out.pxPerMm > 0);
  assert.ok(out.warnings.some((w) => /viewBox/i.test(w)));
});

test("text elements produce a warning about converting to outlines", () => {
  const out = svg.parseSVG(svgDoc('<text x="0" y="10">Hello</text><rect width="5" height="5" fill="#000"/>'));
  assert.ok(out.warnings.some((w) => /outline/i.test(w)));
});

test("stroke-only art yields no regions and warns about strokes", () => {
  const out = svg.parseSVG(svgDoc('<path d="M 0 0 L 50 50" fill="none" stroke="#000" stroke-width="2"/>'));
  assert.strictEqual(out.regions.length, 0);
  assert.ok(out.warnings.some((w) => /stroke/i.test(w)));
});

test("open subpaths are closed implicitly for filling", () => {
  // SVG fills an unclosed subpath as though it were closed.
  const out = svg.parseSVG(svgDoc('<path d="M 0 0 L 50 0 L 50 50" fill="#000"/>'));
  assert.strictEqual(out.regions.length, 1);
  assert.strictEqual(out.regions[0].shapes[0].outer.length, 3);
});

test("degenerate subpaths with under three points are dropped", () => {
  const out = svg.parseSVG(svgDoc('<path d="M 0 0 L 10 0" fill="#000"/>'));
  assert.strictEqual(out.regions.length, 0);
});

test("empty or garbage input yields no regions and does not throw", () => {
  assert.deepStrictEqual(svg.parseSVG("").regions, []);
  assert.deepStrictEqual(svg.parseSVG("not svg at all").regions, []);
  assert.deepStrictEqual(svg.parseSVG(null).regions, []);
});
