const assert = require("node:assert");
const { test } = require("node:test");
const { parsePathData } = require("../src/svgpath.js");

// Gap coverage for src/svgpath.js beyond test/svgpath.test.js: relative
// curve commands, implicit repetition, arc interactions, malformed input.

const last = (sub) => sub.points[sub.points.length - 1];
const near = (a, b, eps = 1e-9) => Math.abs(a - b) < eps;

// ---- relative commands ----------------------------------------------------

test("a leading relative m is measured from the origin", () => {
  const subs = parsePathData("m 5 6 l 1 1");
  assert.deepStrictEqual(subs[0].points, [{ x: 5, y: 6 }, { x: 6, y: 7 }]);
});

test("extra pairs after a relative m are relative lineto, not moveto", () => {
  const subs = parsePathData("m 10 10 5 0 0 5");
  assert.strictEqual(subs.length, 1);
  assert.deepStrictEqual(subs[0].points, [{ x: 10, y: 10 }, { x: 15, y: 10 }, { x: 15, y: 15 }]);
});

test("relative m after Z is measured from the closed subpath's start", () => {
  const subs = parsePathData("M 10 10 L 20 10 L 20 20 Z m 5 5 l 1 0");
  assert.strictEqual(subs.length, 2);
  assert.deepStrictEqual(subs[1].points, [{ x: 15, y: 15 }, { x: 16, y: 15 }]);
});

test("repeated H and V arguments each move from the previous point", () => {
  const subs = parsePathData("M 0 0 h 1 2 3 v 4 5");
  assert.deepStrictEqual(subs[0].points.slice(1), [
    { x: 1, y: 0 }, { x: 3, y: 0 }, { x: 6, y: 0 }, { x: 6, y: 4 }, { x: 6, y: 9 },
  ]);
});

test("relative c offsets all three points from the segment start and ends exactly", () => {
  const a = parsePathData("M 10 20 C 10 30 30 30 30 20", { tolerance: 0.05 })[0].points;
  const b = parsePathData("M 10 20 c 0 10 20 10 20 0", { tolerance: 0.05 })[0].points;
  assert.deepStrictEqual(b, a);
});

test("relative s resolves its control point relative to the current point", () => {
  const a = parsePathData("M 0 0 C 0 10 10 10 10 0 S 20 -10 20 0", { tolerance: 0.05 })[0].points;
  const b = parsePathData("M 0 0 C 0 10 10 10 10 0 s 10 -10 10 0", { tolerance: 0.05 })[0].points;
  assert.deepStrictEqual(b, a);
});

test("relative q and t match their absolute forms", () => {
  const a = parsePathData("M 0 0 Q 5 10 10 0 T 20 0", { tolerance: 0.05 })[0].points;
  const b = parsePathData("M 0 0 q 5 10 10 0 t 10 0", { tolerance: 0.05 })[0].points;
  assert.deepStrictEqual(b, a);
});

test("chained relative curves accumulate: the second starts where the first ended", () => {
  const pts = parsePathData("M 0 0 c 0 5 5 5 5 0 c 0 5 5 5 5 0", { tolerance: 0.05 })[0].points;
  assert.deepStrictEqual(pts[pts.length - 1], { x: 10, y: 0 });
});

test("implicit repetition of C draws two curves", () => {
  const one = parsePathData("M 0 0 C 0 5 5 5 5 0", { tolerance: 0.05 })[0].points.length;
  const two = parsePathData("M 0 0 C 0 5 5 5 5 0 10 -5 15 -5 15 0", { tolerance: 0.05 })[0].points;
  assert.ok(two.length > one);
  assert.deepStrictEqual(last({ points: two }), { x: 15, y: 0 });
});

test("S after an arc has no reflection (control = current point)", () => {
  // Without a prior curve the first control point is the current point, so
  // S behaves like a C whose first control sits on the start.
  const afterArc = parsePathData("M 0 0 A 5 5 0 0 1 10 0 S 20 10 20 0", { tolerance: 0.05 })[0].points;
  const plain = parsePathData("M 10 0 C 10 0 20 10 20 0", { tolerance: 0.05 })[0].points;
  const tail = afterArc.slice(afterArc.length - plain.length + 1);
  assert.deepStrictEqual(tail, plain.slice(1));
});

test("T after a line has no reflection (control = current point)", () => {
  const pts = parsePathData("M 0 0 L 10 0 T 20 0", { tolerance: 0.05 })[0].points;
  for (const p of pts) assert.ok(near(p.y, 0), "degenerate quadratic should stay on y=0");
});

test("reflection state is cleared by an intervening L", () => {
  const a = parsePathData("M 0 0 C 0 10 10 10 10 0 L 10 0 S 20 -10 20 0", { tolerance: 0.05 })[0].points;
  const b = parsePathData("M 0 0 C 0 10 10 10 10 0 L 10 0 C 10 0 20 -10 20 0", { tolerance: 0.05 })[0].points;
  assert.deepStrictEqual(a, b);
});

// ---- arcs -----------------------------------------------------------------

test("relative arc after Z offsets from the subpath start", () => {
  const subs = parsePathData("M 10 10 L 20 10 L 20 20 Z a 5 5 0 0 1 10 0", { tolerance: 0.1 });
  assert.strictEqual(subs.length, 2);
  assert.deepStrictEqual(subs[1].points[0], { x: 10, y: 10 });
  assert.deepStrictEqual(last(subs[1]), { x: 20, y: 10 });
});

test("an arc with no preceding M starts at the origin", () => {
  const subs = parsePathData("A 5 5 0 0 1 10 0", { tolerance: 0.1 });
  assert.strictEqual(subs.length, 1);
  assert.deepStrictEqual(subs[0].points[0], { x: 0, y: 0 });
  assert.deepStrictEqual(last(subs[0]), { x: 10, y: 0 });
});

test("negative radii use their absolute value", () => {
  const pos = parsePathData("M 0 0 A 50 50 0 0 1 100 0", { tolerance: 0.2 })[0].points;
  const neg = parsePathData("M 0 0 A -50 -50 0 0 1 100 0", { tolerance: 0.2 })[0].points;
  assert.deepStrictEqual(neg, pos);
});

test("a rotation of 360 degrees gives the same arc as 0", () => {
  const a = parsePathData("M 0 0 A 30 20 0 0 1 40 10", { tolerance: 0.1 })[0].points;
  const b = parsePathData("M 0 0 A 30 20 360 0 1 40 10", { tolerance: 0.1 })[0].points;
  assert.strictEqual(a.length, b.length);
  a.forEach((p, i) => { assert.ok(near(p.x, b[i].x, 1e-6) && near(p.y, b[i].y, 1e-6)); });
});

test("a half-circle arc with exact-diameter radii lands exactly on the endpoint", () => {
  const pts = parsePathData("M 0 0 A 50 50 0 0 1 100 0", { tolerance: 0.1 })[0].points;
  assert.deepStrictEqual(last({ points: pts }), { x: 100, y: 0 });
});

test("one zero radius collapses the arc to a line even when the other is non-zero", () => {
  const pts = parsePathData("M 0 0 A 0 25 0 0 1 30 40")[0].points;
  assert.deepStrictEqual(pts, [{ x: 0, y: 0 }, { x: 30, y: 40 }]);
  const pts2 = parsePathData("M 0 0 A 25 0 0 0 1 30 40")[0].points;
  assert.deepStrictEqual(pts2, [{ x: 0, y: 0 }, { x: 30, y: 40 }]);
});

test("a very large tolerance still produces at least a mid point and the endpoint", () => {
  const pts = parsePathData("M 0 0 A 50 50 0 0 1 100 0", { tolerance: 1000 })[0].points;
  assert.ok(pts.length >= 3);
  assert.deepStrictEqual(pts[pts.length - 1], { x: 100, y: 0 });
});

test("implicit repetition of A draws a second arc", () => {
  const subs = parsePathData("M 0 0 A 5 5 0 0 1 10 0 5 5 0 0 1 20 0", { tolerance: 0.1 });
  assert.deepStrictEqual(last(subs[0]), { x: 20, y: 0 });
  assert.ok(subs[0].points.some((p) => near(p.x, 10) && near(p.y, 0, 1e-6)));
});

test("arc flags separated only by commas or only by nothing both lex", () => {
  const a = parsePathData("M0 0A5 5 0 0,1 10,0", { tolerance: 0.1 })[0].points;
  const b = parsePathData("M0 0A5 5 0 01 10 0", { tolerance: 0.1 })[0].points;
  assert.deepStrictEqual(last({ points: a }), { x: 10, y: 0 });
  assert.deepStrictEqual(b, a);
});

test("a flag that is not 0 or 1 truncates the arc's arguments, so the arc is dropped", () => {
  const subs = parsePathData("M 0 0 A 5 5 0 2 1 10 0 L 3 3");
  // the A has only 3 usable args (< arity 7) so nothing is drawn for it
  assert.deepStrictEqual(subs[0].points, [{ x: 0, y: 0 }, { x: 3, y: 3 }]);
});

// ---- malformed input ------------------------------------------------------

test("non-string path data does not throw", () => {
  assert.deepStrictEqual(parsePathData(null), []);
  assert.deepStrictEqual(parsePathData(undefined), []);
  assert.deepStrictEqual(parsePathData(), []);
  assert.deepStrictEqual(parsePathData(0), []);
});

test("a command with too few arguments is ignored", () => {
  const subs = parsePathData("M 0 0 L 10");
  assert.deepStrictEqual(subs[0].points, [{ x: 0, y: 0 }]);
});

test("a trailing partial coordinate group is dropped, complete groups kept", () => {
  const subs = parsePathData("M 0 0 L 10 10 20");
  assert.deepStrictEqual(subs[0].points, [{ x: 0, y: 0 }, { x: 10, y: 10 }]);
});

test("a truncated curve draws nothing", () => {
  const subs = parsePathData("M 0 0 C 1 2 3 4 5");
  assert.deepStrictEqual(subs[0].points, [{ x: 0, y: 0 }]);
});

test("a path that does not start with M starts at the origin", () => {
  const subs = parsePathData("L 10 10 L 20 0");
  assert.strictEqual(subs.length, 1);
  assert.deepStrictEqual(subs[0].points, [{ x: 0, y: 0 }, { x: 10, y: 10 }, { x: 20, y: 0 }]);
});

test("numbers with no command before them are ignored", () => {
  const subs = parsePathData("10 20 M 1 1 L 2 2");
  assert.deepStrictEqual(subs[0].points, [{ x: 1, y: 1 }, { x: 2, y: 2 }]);
});

test("unknown command letters are skipped as stray text", () => {
  // 'X' is not a command, so it neither starts a command nor consumes args:
  // its characters are absorbed by the preceding command's argument scan.
  const subs = parsePathData("M 0 0 L 5 5 X 9 9");
  assert.deepStrictEqual(subs[0].points.slice(0, 2), [{ x: 0, y: 0 }, { x: 5, y: 5 }]);
});

test("stray punctuation between numbers is skipped", () => {
  const subs = parsePathData("M 0 0 L 1 ; 2");
  assert.deepStrictEqual(subs[0].points, [{ x: 0, y: 0 }, { x: 1, y: 2 }]);
});

test("Z with no open subpath is harmless", () => {
  assert.deepStrictEqual(parsePathData("Z"), []);
  const subs = parsePathData("M 0 0 L 5 0 Z Z L 2 2");
  assert.strictEqual(subs[0].closed, true);
});

test("a lone M yields a single-point open subpath", () => {
  const subs = parsePathData("M 3 4");
  assert.strictEqual(subs.length, 1);
  assert.deepStrictEqual(subs[0], { points: [{ x: 3, y: 4 }], closed: false });
});

test("consecutive M commands each start a subpath", () => {
  const subs = parsePathData("M 0 0 M 5 5 M 9 9 L 10 10");
  assert.strictEqual(subs.length, 3);
  assert.deepStrictEqual(subs[2].points, [{ x: 9, y: 9 }, { x: 10, y: 10 }]);
});

test("number forms: leading dot, trailing dot, exponents, explicit plus", () => {
  const subs = parsePathData("M .5 .5 L 1. 2.e0 L +3 4E-0");
  assert.deepStrictEqual(subs[0].points, [
    { x: 0.5, y: 0.5 }, { x: 1, y: 2 }, { x: 3, y: 4 },
  ]);
});

test("adjacent numbers split on a second decimal point or a sign", () => {
  const subs = parsePathData("M 0 0 L 1.5.5-2");
  // "1.5" "." "5"... -> 1.5, .5, -2 => one full pair then a partial group
  assert.deepStrictEqual(subs[0].points, [{ x: 0, y: 0 }, { x: 1.5, y: 0.5 }]);
});

test("command letters are case-sensitive for relativity and need no whitespace", () => {
  const subs = parsePathData("M1 1l1 1L5 5");
  assert.deepStrictEqual(subs[0].points, [{ x: 1, y: 1 }, { x: 2, y: 2 }, { x: 5, y: 5 }]);
});

test("a huge coordinate count does not blow the stack", () => {
  let d = "M 0 0";
  for (let i = 1; i <= 20000; i++) d += " L " + i + " " + (i % 7);
  const subs = parsePathData(d);
  assert.strictEqual(subs[0].points.length, 20001);
});

test("NaN-producing geometry from a degenerate curve still terminates", () => {
  const pts = parsePathData("M 0 0 C 1e308 1e308 -1e308 1e308 0 0", { tolerance: 0.1 })[0].points;
  assert.ok(pts.length >= 2 && pts.length <= 65537 * 2);
});
