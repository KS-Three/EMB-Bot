const assert = require("node:assert");
const { test } = require("node:test");
const svgpath = require("../src/svgpath.js");

test("parses absolute moveto and lineto", () => {
  const subs = svgpath.parsePathData("M 10 20 L 30 40 L 50 60");
  assert.strictEqual(subs.length, 1);
  assert.strictEqual(subs[0].closed, false);
  assert.deepStrictEqual(subs[0].points, [
    { x: 10, y: 20 }, { x: 30, y: 40 }, { x: 50, y: 60 },
  ]);
});

test("relative commands accumulate from the current point", () => {
  const subs = svgpath.parsePathData("M 10 10 l 5 0 l 0 5");
  assert.deepStrictEqual(subs[0].points, [
    { x: 10, y: 10 }, { x: 15, y: 10 }, { x: 15, y: 15 },
  ]);
});

test("H and V produce horizontal and vertical segments", () => {
  const subs = svgpath.parsePathData("M 0 0 H 10 V 10 h -5 v -5");
  assert.deepStrictEqual(subs[0].points, [
    { x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 },
    { x: 5, y: 10 }, { x: 5, y: 5 },
  ]);
});

test("Z closes the subpath and a following command starts a new one", () => {
  const subs = svgpath.parsePathData("M 0 0 L 10 0 L 10 10 Z M 20 20 L 30 20");
  assert.strictEqual(subs.length, 2);
  assert.strictEqual(subs[0].closed, true);
  assert.strictEqual(subs[0].points.length, 3);
  assert.strictEqual(subs[1].closed, false);
  assert.deepStrictEqual(subs[1].points, [{ x: 20, y: 20 }, { x: 30, y: 20 }]);
});

test("after Z the current point returns to the subpath start", () => {
  const subs = svgpath.parsePathData("M 5 5 L 10 5 Z l 0 10");
  assert.strictEqual(subs.length, 2);
  assert.deepStrictEqual(subs[1].points[0], { x: 5, y: 5 });
  assert.deepStrictEqual(subs[1].points[1], { x: 5, y: 15 });
});

test("implicit repeated coordinates repeat the last command", () => {
  const subs = svgpath.parsePathData("M 0 0 10 10 20 20");
  assert.deepStrictEqual(subs[0].points, [
    { x: 0, y: 0 }, { x: 10, y: 10 }, { x: 20, y: 20 },
  ]);
});

test("comma and negative-sign separated numbers parse", () => {
  const subs = svgpath.parsePathData("M0,0L-5.5,3e1");
  assert.deepStrictEqual(subs[0].points, [{ x: 0, y: 0 }, { x: -5.5, y: 30 }]);
});

test("empty or whitespace path data yields no subpaths", () => {
  assert.deepStrictEqual(svgpath.parsePathData(""), []);
  assert.deepStrictEqual(svgpath.parsePathData("   "), []);
});
