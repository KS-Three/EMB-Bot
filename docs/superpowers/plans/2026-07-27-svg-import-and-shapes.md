# SVG Vector Import + Shape Elements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parse SVG artwork into stitch regions, so customer vector logos import with exact edges and pictogram packs become clickable shape elements.

**Architecture:** Two new engine modules — `src/svgpath.js` (path data → polylines) and `src/svgimport.js` (document → color regions). Both are pure JS with **no DOM**, so they run in the Node test suite. They produce the exact `{regions, pxPerMm}` contract `app/src/lib/imageRegions.js` already returns, so `buildQualityDesign` is not modified. Shapes reuse that same path: a pictogram pack is pre-parsed offline into stored regions.

**Tech Stack:** Vanilla JS (dual-mode IIFE modules), `node:test` + `node:assert` for engine tests, Svelte 5 + Vitest for the Studio app.

## Global Constraints

- **No DOM in engine modules.** `src/*.js` must run under `node --test`. No `document`, no `DOMParser`, no `getPointAtLength`.
- **No new dependencies.** This project is deliberately zero-dependency in the browser (no OpenCV, no Potrace, no Python). Hand-write the math.
- **Dual-mode module pattern.** Every `src/*.js` file uses the existing IIFE wrapper so it works as both a browser `<script>` (attaching to global `EMB`) and a CommonJS module.
- **Additive and back-compat.** New `opts.*` fields must default to exactly today's output when absent. Existing engine output must stay byte-identical.
- **Points are `{x, y}` objects**, never `[x, y]` arrays. Match `src/geometry.js`.
- **`ENGINE_FILES` is mirrored in three places** and all three must be updated together: `app/scripts/copy-engine.mjs`, `app/src/lib/emb.js` (`ENGINE_KEYS`), and the `<script>` tags in `EMB-Bot.html`.
- **Engine tests:** `node --test` from repo root. **App tests:** `cd app && npm test`. Both must be green before any commit.
- App test files use the `.spec.js` suffix so the repo-root `node --test` ignores them.

## Deviation from the spec

Spec §3.1 lists `parseGlyphLayers(svgText, opts)` as a second export of `src/svgimport.js`. This plan does not build it. Splitting an Ink/Stitch font SVG into per-glyph groups is an **offline import concern**, not a runtime one — the Studio never parses a whole pack in the browser, it consumes per-shape SVGs the importer already extracted. The extraction therefore lives in `tools/build-shapes.mjs` (Task 10) and `tools/try-svg.mjs` (Task 6), keeping the engine module focused on "SVG document → regions."

If a runtime need for glyph-layer splitting appears later, promote it into `svgimport.js` then.

---

### Task 1: Path data tokenizer and line commands

**Files:**
- Create: `src/svgpath.js`
- Test: `test/svgpath.test.js`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: `parsePathData(d, opts)` → `[{ points: [{x,y}], closed: boolean }]`. `opts.tolerance` (number, user units, default `0.2`) controls curve flattening in later tasks; ignored here. Exported on `EMB` as `EMB.parsePathData`.

- [ ] **Step 1: Write the failing test**

Create `test/svgpath.test.js`:

```js
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test test/svgpath.test.js`
Expected: FAIL — `Cannot find module '../src/svgpath.js'`

- [ ] **Step 3: Write minimal implementation**

Create `src/svgpath.js`:

```js
(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  // Splits path data into [{ command: "M", args: [numbers...] }, ...].
  // SVG allows commands to be repeated implicitly by supplying extra
  // coordinate groups (e.g. "M 0 0 10 10" is a moveto then a lineto), which
  // is why args are collected greedily and chunked by the consumer.
  const NUM_RE = /-?\d*\.?\d+(?:[eE][-+]?\d+)?/g;
  const CMD_RE = /[MmLlHhVvCcSsQqTtAaZz]/;

  function tokenize(d) {
    const out = [];
    let i = 0;
    while (i < d.length) {
      const ch = d[i];
      if (CMD_RE.test(ch)) {
        // Collect every number up to the next command letter.
        let j = i + 1;
        while (j < d.length && !CMD_RE.test(d[j])) j++;
        const chunk = d.slice(i + 1, j);
        const args = (chunk.match(NUM_RE) || []).map(Number);
        out.push({ command: ch, args });
        i = j;
      } else {
        i++;
      }
    }
    return out;
  }

  // Number of arguments each command consumes per repetition.
  const ARITY = {
    M: 2, L: 2, H: 1, V: 1, C: 6, S: 4, Q: 4, T: 2, A: 7, Z: 0,
  };

  function parsePathData(d, opts) {
    const tolerance = (opts && opts.tolerance) || 0.2;
    const subpaths = [];
    let current = null;   // { points, closed }
    let cx = 0, cy = 0;   // current point
    let sx = 0, sy = 0;   // start of current subpath

    function startSubpath(x, y) {
      current = { points: [{ x, y }], closed: false };
      subpaths.push(current);
      sx = x; sy = y;
    }
    function lineTo(x, y) {
      if (!current) startSubpath(cx, cy);
      current.points.push({ x, y });
    }

    for (const token of tokenize(String(d || ""))) {
      const upper = token.command.toUpperCase();
      const relative = token.command !== upper;
      const arity = ARITY[upper];

      if (upper === "Z") {
        if (current) current.closed = true;
        cx = sx; cy = sy;
        current = null; // a command after Z begins a new subpath
        continue;
      }

      // Walk the argument list in arity-sized groups (implicit repetition).
      // An M with extra groups becomes M followed by implicit L, per spec.
      let groupIndex = 0;
      for (let a = 0; a + arity <= token.args.length; a += arity, groupIndex++) {
        const g = token.args.slice(a, a + arity);
        let effective = upper;
        if (upper === "M" && groupIndex > 0) effective = "L";

        if (effective === "M") {
          const x = relative ? cx + g[0] : g[0];
          const y = relative ? cy + g[1] : g[1];
          startSubpath(x, y);
          cx = x; cy = y;
        } else if (effective === "L") {
          const x = relative ? cx + g[0] : g[0];
          const y = relative ? cy + g[1] : g[1];
          lineTo(x, y); cx = x; cy = y;
        } else if (effective === "H") {
          const x = relative ? cx + g[0] : g[0];
          lineTo(x, cy); cx = x;
        } else if (effective === "V") {
          const y = relative ? cy + g[0] : g[0];
          lineTo(cx, y); cy = y;
        }
        // C/S/Q/T/A are added in Tasks 2 and 3.
      }
    }
    return subpaths;
  }

  return { parsePathData };
});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test test/svgpath.test.js`
Expected: PASS, 8 tests.

- [ ] **Step 5: Run the full engine suite for regressions**

Run: `node --test`
Expected: PASS. Previous total was 169; expect 177.

- [ ] **Step 6: Commit**

```bash
git add src/svgpath.js test/svgpath.test.js
git commit -m "feat: SVG path tokenizer with moveto/lineto/close commands"
```

---

### Task 2: Bezier commands with adaptive flattening

**Files:**
- Modify: `src/svgpath.js`
- Modify: `test/svgpath.test.js`

**Interfaces:**
- Consumes: `parsePathData(d, opts)` from Task 1.
- Produces: same signature, now handling `C/c/S/s/Q/q/T/t`. `opts.tolerance` becomes meaningful — it is the maximum permitted deviation (in user units) between the true curve and the emitted polyline.

- [ ] **Step 1: Write the failing test**

Append to `test/svgpath.test.js`:

```js
function dist(a, b) { return Math.hypot(a.x - b.x, a.y - b.y); }

// Maximum distance from any emitted point to the true cubic curve,
// sampled densely. Used to assert the flattening tolerance is honored.
function maxDeviationFromCubic(points, p0, p1, p2, p3) {
  const samples = [];
  for (let i = 0; i <= 2000; i++) {
    const t = i / 2000, u = 1 - t;
    samples.push({
      x: u*u*u*p0.x + 3*u*u*t*p1.x + 3*u*t*t*p2.x + t*t*t*p3.x,
      y: u*u*u*p0.y + 3*u*u*t*p1.y + 3*u*t*t*p2.y + t*t*t*p3.y,
    });
  }
  let worst = 0;
  for (const s of samples) {
    let best = Infinity;
    for (const p of points) best = Math.min(best, dist(p, s));
    worst = Math.max(worst, best);
  }
  return worst;
}

test("cubic bezier flattens within tolerance", () => {
  const subs = svgpath.parsePathData("M 0 0 C 0 100 100 100 100 0", { tolerance: 0.5 });
  const pts = subs[0].points;
  assert.ok(pts.length > 4, "expected subdivision, got " + pts.length + " points");
  assert.deepStrictEqual(pts[0], { x: 0, y: 0 });
  assert.deepStrictEqual(pts[pts.length - 1], { x: 100, y: 0 });
  const dev = maxDeviationFromCubic(pts,
    { x: 0, y: 0 }, { x: 0, y: 100 }, { x: 100, y: 100 }, { x: 100, y: 0 });
  assert.ok(dev <= 0.5, "deviation " + dev + " exceeded tolerance 0.5");
});

test("tighter tolerance produces more points", () => {
  const coarse = svgpath.parsePathData("M 0 0 C 0 100 100 100 100 0", { tolerance: 2 });
  const fine = svgpath.parsePathData("M 0 0 C 0 100 100 100 100 0", { tolerance: 0.05 });
  assert.ok(fine[0].points.length > coarse[0].points.length);
});

test("quadratic bezier flattens and ends at its endpoint", () => {
  const subs = svgpath.parsePathData("M 0 0 Q 50 100 100 0", { tolerance: 0.5 });
  const pts = subs[0].points;
  assert.ok(pts.length > 3);
  assert.deepStrictEqual(pts[pts.length - 1], { x: 100, y: 0 });
  // Apex of this symmetric quadratic is at t=0.5 -> (50, 50).
  let closest = Infinity;
  for (const p of pts) closest = Math.min(closest, dist(p, { x: 50, y: 50 }));
  assert.ok(closest < 1, "expected a point near the apex, closest was " + closest);
});

test("S reflects the previous cubic control point", () => {
  // Explicit equivalent of the smooth form: reflection of (0,100) about
  // (100,0) is (200,-100).
  const smooth = svgpath.parsePathData("M 0 0 C 0 100 100 100 100 0 S 200 -100 200 0", { tolerance: 0.25 });
  const explicit = svgpath.parsePathData("M 0 0 C 0 100 100 100 100 0 C 100 -100 200 -100 200 0", { tolerance: 0.25 });
  assert.deepStrictEqual(smooth[0].points, explicit[0].points);
});

test("T reflects the previous quadratic control point", () => {
  const smooth = svgpath.parsePathData("M 0 0 Q 50 100 100 0 T 200 0", { tolerance: 0.25 });
  const explicit = svgpath.parsePathData("M 0 0 Q 50 100 100 0 Q 150 -100 200 0", { tolerance: 0.25 });
  assert.deepStrictEqual(smooth[0].points, explicit[0].points);
});

test("S without a preceding curve uses the current point as control", () => {
  const subs = svgpath.parsePathData("M 10 10 S 20 20 30 10", { tolerance: 0.5 });
  assert.deepStrictEqual(subs[0].points[0], { x: 10, y: 10 });
  assert.deepStrictEqual(subs[0].points[subs[0].points.length - 1], { x: 30, y: 10 });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test test/svgpath.test.js`
Expected: FAIL — the cubic test reports 1 point (only the `M`), since `C` is ignored.

- [ ] **Step 3: Write minimal implementation**

In `src/svgpath.js`, insert these helpers inside the factory, above `parsePathData`:

```js
  // Recursive de Casteljau flattening. Emits points for everything AFTER p0
  // (the caller has already emitted the start point). The flatness test is
  // the standard control-point-distance-from-chord measure: when both
  // control points lie within `tolerance` of the chord, the chord is an
  // acceptable approximation of the curve.
  function flattenCubic(p0, p1, p2, p3, tolerance, out, depth) {
    if (depth > 24) { out.push({ x: p3.x, y: p3.y }); return; } // safety floor
    const dx = p3.x - p0.x, dy = p3.y - p0.y;
    const d1 = Math.abs((p1.x - p3.x) * dy - (p1.y - p3.y) * dx);
    const d2 = Math.abs((p2.x - p3.x) * dy - (p2.y - p3.y) * dx);
    const dd = d1 + d2;
    if (dd * dd <= tolerance * tolerance * (dx * dx + dy * dy) * 16) {
      out.push({ x: p3.x, y: p3.y });
      return;
    }
    // Subdivide at t = 0.5.
    const p01 = mid(p0, p1), p12 = mid(p1, p2), p23 = mid(p2, p3);
    const p012 = mid(p01, p12), p123 = mid(p12, p23);
    const m = mid(p012, p123);
    flattenCubic(p0, p01, p012, m, tolerance, out, depth + 1);
    flattenCubic(m, p123, p23, p3, tolerance, out, depth + 1);
  }

  function mid(a, b) { return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }; }

  // A quadratic is exactly representable as a cubic, so degree-elevate and
  // reuse one flattening routine rather than maintaining two.
  function quadToCubic(p0, q, p1) {
    return [
      { x: p0.x + (2 / 3) * (q.x - p0.x), y: p0.y + (2 / 3) * (q.y - p0.y) },
      { x: p1.x + (2 / 3) * (q.x - p1.x), y: p1.y + (2 / 3) * (q.y - p1.y) },
    ];
  }
```

Then, inside `parsePathData`, add tracking of the previous control point immediately after the `let sx = 0, sy = 0;` line:

```js
    // Reflection state for the smooth curve commands S and T. `prevCubicC2`
    // is the second control point of the last C/S; `prevQuadC` is the control
    // point of the last Q/T. Each is null when the previous command was not
    // of the matching curve type, in which case the spec says to use the
    // current point.
    let prevCubicC2 = null;
    let prevQuadC = null;
```

Add a `curveTo` helper next to `lineTo`:

```js
    function curveTo(p1, p2, p3) {
      if (!current) startSubpath(cx, cy);
      flattenCubic({ x: cx, y: cy }, p1, p2, p3, tolerance, current.points, 0);
    }
```

Replace the comment `// C/S/Q/T/A are added in Tasks 2 and 3.` with:

```js
        else if (effective === "C" || effective === "S") {
          let c1, c2, end;
          if (effective === "C") {
            c1 = { x: relative ? cx + g[0] : g[0], y: relative ? cy + g[1] : g[1] };
            c2 = { x: relative ? cx + g[2] : g[2], y: relative ? cy + g[3] : g[3] };
            end = { x: relative ? cx + g[4] : g[4], y: relative ? cy + g[5] : g[5] };
          } else {
            c1 = prevCubicC2
              ? { x: 2 * cx - prevCubicC2.x, y: 2 * cy - prevCubicC2.y }
              : { x: cx, y: cy };
            c2 = { x: relative ? cx + g[0] : g[0], y: relative ? cy + g[1] : g[1] };
            end = { x: relative ? cx + g[2] : g[2], y: relative ? cy + g[3] : g[3] };
          }
          curveTo(c1, c2, end);
          prevCubicC2 = c2; prevQuadC = null;
          cx = end.x; cy = end.y;
        } else if (effective === "Q" || effective === "T") {
          let q, end;
          if (effective === "Q") {
            q = { x: relative ? cx + g[0] : g[0], y: relative ? cy + g[1] : g[1] };
            end = { x: relative ? cx + g[2] : g[2], y: relative ? cy + g[3] : g[3] };
          } else {
            q = prevQuadC
              ? { x: 2 * cx - prevQuadC.x, y: 2 * cy - prevQuadC.y }
              : { x: cx, y: cy };
            end = { x: relative ? cx + g[0] : g[0], y: relative ? cy + g[1] : g[1] };
          }
          const [c1, c2] = quadToCubic({ x: cx, y: cy }, q, end);
          curveTo(c1, c2, end);
          prevQuadC = q; prevCubicC2 = c2;
          cx = end.x; cy = end.y;
        }
```

Finally, clear the reflection state on every non-curve command. Inside the group loop, immediately after `let effective = upper;`, add:

```js
        if (effective === "M" || effective === "L" || effective === "H" || effective === "V") {
          prevCubicC2 = null; prevQuadC = null;
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test test/svgpath.test.js`
Expected: PASS, 14 tests.

- [ ] **Step 5: Run the full engine suite**

Run: `node --test`
Expected: PASS, 183 tests.

- [ ] **Step 6: Commit**

```bash
git add src/svgpath.js test/svgpath.test.js
git commit -m "feat: cubic/quadratic bezier commands with adaptive flattening"
```

---

### Task 3: Elliptical arc command

**Files:**
- Modify: `src/svgpath.js`
- Modify: `test/svgpath.test.js`

**Interfaces:**
- Consumes: `parsePathData` from Task 2.
- Produces: same signature, now handling `A/a`.

**Why sampling rather than bezier conversion:** everything is flattened to polylines anyway, so converting the arc to beziers and then flattening those adds a lossy intermediate step for no benefit. Sample the arc's parametric form directly with a step count derived from the tolerance.

- [ ] **Step 1: Write the failing test**

Append to `test/svgpath.test.js`:

```js
test("arc traces a quarter circle through the expected midpoint", () => {
  // Unit-ish quarter arc from (100,0) to (0,100), r=100, sweep=1 (positive
  // angle direction) puts the midpoint at (100-100/sqrt2, 100/sqrt2) for the
  // large-arc-flag=0 case, i.e. approx (29.29, 70.71).
  const subs = svgpath.parsePathData("M 100 0 A 100 100 0 0 1 0 100", { tolerance: 0.1 });
  const pts = subs[0].points;
  assert.deepStrictEqual(pts[0], { x: 100, y: 0 });
  const last = pts[pts.length - 1];
  assert.ok(Math.abs(last.x - 0) < 1e-6 && Math.abs(last.y - 100) < 1e-6,
    "arc should end at (0,100), got " + JSON.stringify(last));
  // Every point must sit on the circle centered at origin with r=100.
  for (const p of pts) {
    const r = Math.hypot(p.x, p.y);
    assert.ok(Math.abs(r - 100) < 0.5, "point off-circle: r=" + r);
  }
});

test("large-arc-flag selects the long way round", () => {
  const small = svgpath.parsePathData("M 100 0 A 100 100 0 0 1 0 100", { tolerance: 0.5 });
  const large = svgpath.parsePathData("M 100 0 A 100 100 0 1 1 0 100", { tolerance: 0.5 });
  assert.ok(large[0].points.length > small[0].points.length,
    "large arc should need more points than the 90-degree arc");
});

test("degenerate arc with zero radius becomes a straight line", () => {
  const subs = svgpath.parsePathData("M 0 0 A 0 0 0 0 1 50 50");
  assert.deepStrictEqual(subs[0].points, [{ x: 0, y: 0 }, { x: 50, y: 50 }]);
});

test("arc with equal start and end point emits nothing extra", () => {
  const subs = svgpath.parsePathData("M 10 10 A 50 50 0 0 1 10 10");
  assert.deepStrictEqual(subs[0].points, [{ x: 10, y: 10 }]);
});

test("out-of-range radii are scaled up to reach the endpoint", () => {
  // r=10 cannot span a 100-unit chord; the spec says scale radii until it can.
  const subs = svgpath.parsePathData("M 0 0 A 10 10 0 0 1 100 0", { tolerance: 0.5 });
  const pts = subs[0].points;
  const last = pts[pts.length - 1];
  assert.ok(Math.abs(last.x - 100) < 1e-6 && Math.abs(last.y) < 1e-6);
  // Scaled radius is 50, so the arc apex sits 50 below/above the chord.
  let maxAbsY = 0;
  for (const p of pts) maxAbsY = Math.max(maxAbsY, Math.abs(p.y));
  assert.ok(Math.abs(maxAbsY - 50) < 1, "expected apex near 50, got " + maxAbsY);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test test/svgpath.test.js`
Expected: FAIL — arc tests report only the `M` point.

- [ ] **Step 3: Write minimal implementation**

Add this helper inside the factory in `src/svgpath.js`, above `parsePathData`:

```js
  // Endpoint -> center parameterization, per SVG 1.1 appendix F.6.5, then
  // direct parametric sampling. `out` receives every point after the start.
  function flattenArc(x1, y1, rx, ry, xAxisRotDeg, largeArc, sweep, x2, y2, tolerance, out) {
    if (x1 === x2 && y1 === y2) return;            // spec: arc is skipped entirely
    if (rx === 0 || ry === 0) { out.push({ x: x2, y: y2 }); return; } // treated as a line

    rx = Math.abs(rx); ry = Math.abs(ry);
    const phi = (xAxisRotDeg * Math.PI) / 180;
    const cosPhi = Math.cos(phi), sinPhi = Math.sin(phi);

    // Step 1: translate so the midpoint is the origin, and rotate by -phi.
    const dx2 = (x1 - x2) / 2, dy2 = (y1 - y2) / 2;
    const x1p = cosPhi * dx2 + sinPhi * dy2;
    const y1p = -sinPhi * dx2 + cosPhi * dy2;

    // Step 2: correct out-of-range radii (F.6.6).
    const lambda = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry);
    if (lambda > 1) { const s = Math.sqrt(lambda); rx *= s; ry *= s; }

    // Step 3: compute the center in the rotated frame.
    const rx2 = rx * rx, ry2 = ry * ry;
    const num = rx2 * ry2 - rx2 * y1p * y1p - ry2 * x1p * x1p;
    const den = rx2 * y1p * y1p + ry2 * x1p * x1p;
    let coef = den === 0 ? 0 : Math.sqrt(Math.max(0, num / den));
    if (largeArc === sweep) coef = -coef;
    const cxp = coef * ((rx * y1p) / ry);
    const cyp = coef * (-(ry * x1p) / rx);

    // Step 4: rotate the center back and undo the translation.
    const cx = cosPhi * cxp - sinPhi * cyp + (x1 + x2) / 2;
    const cy = sinPhi * cxp + cosPhi * cyp + (y1 + y2) / 2;

    // Step 5: start angle and sweep angle.
    const ux = (x1p - cxp) / rx, uy = (y1p - cyp) / ry;
    const vx = (-x1p - cxp) / rx, vy = (-y1p - cyp) / ry;
    let theta1 = Math.atan2(uy, ux);
    let dTheta = Math.atan2(ux * vy - uy * vx, ux * vx + uy * vy);
    if (!sweep && dTheta > 0) dTheta -= 2 * Math.PI;
    if (sweep && dTheta < 0) dTheta += 2 * Math.PI;

    // Step count from the tolerance: for a circular arc of radius r, the
    // sagitta of a step of angle a is r*(1-cos(a/2)), so bound that by the
    // tolerance and solve for a.
    const rMax = Math.max(rx, ry);
    let stepAngle = 2 * Math.acos(Math.max(-1, Math.min(1, 1 - tolerance / rMax)));
    if (!isFinite(stepAngle) || stepAngle <= 1e-6) stepAngle = Math.PI / 180;
    const steps = Math.max(2, Math.ceil(Math.abs(dTheta) / stepAngle));

    for (let i = 1; i <= steps; i++) {
      const t = theta1 + (dTheta * i) / steps;
      const ex = rx * Math.cos(t), ey = ry * Math.sin(t);
      out.push({
        x: cosPhi * ex - sinPhi * ey + cx,
        y: sinPhi * ex + cosPhi * ey + cy,
      });
    }
    // Force the exact endpoint so float drift never leaves a gap that the
    // hole/containment logic in Task 5 would misread as an open ring.
    const last = out[out.length - 1];
    if (last) { last.x = x2; last.y = y2; }
  }
```

Then add the `A` branch inside the group loop, after the `Q`/`T` branch:

```js
        else if (effective === "A") {
          const endX = relative ? cx + g[5] : g[5];
          const endY = relative ? cy + g[6] : g[6];
          if (!current) startSubpath(cx, cy);
          flattenArc(cx, cy, g[0], g[1], g[2], g[3] !== 0, g[4] !== 0,
            endX, endY, tolerance, current.points);
          prevCubicC2 = null; prevQuadC = null;
          cx = endX; cy = endY;
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test test/svgpath.test.js`
Expected: PASS, 19 tests.

- [ ] **Step 5: Run the full engine suite**

Run: `node --test`
Expected: PASS, 188 tests.

- [ ] **Step 6: Commit**

```bash
git add src/svgpath.js test/svgpath.test.js
git commit -m "feat: elliptical arc command via endpoint parameterization"
```

---

### Task 4: Transforms and shape primitives

**Files:**
- Create: `src/svgimport.js`
- Test: `test/svgimport.test.js`

**Interfaces:**
- Consumes: `EMB.parsePathData(d, opts)` from Task 3.
- Produces:
  - `parseTransform(str)` → `[a, b, c, d, e, f]` (an SVG matrix; identity is `[1,0,0,1,0,0]`).
  - `multiplyMatrix(m1, m2)` → `[a,b,c,d,e,f]` (applies `m2` then `m1`).
  - `applyMatrix(m, pt)` → `{x, y}`.
  - `primitiveToSubpaths(tagName, attrs, opts)` → `[{points, closed}]` for `rect`, `circle`, `ellipse`, `line`, `polyline`, `polygon`; `[]` for anything else.

- [ ] **Step 1: Write the failing test**

Create `test/svgimport.test.js`:

```js
const assert = require("node:assert");
const { test } = require("node:test");
require("../src/svgpath.js");
const svg = require("../src/svgimport.js");

function approx(a, b, eps) { return Math.abs(a - b) < (eps === undefined ? 1e-9 : eps); }

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test test/svgimport.test.js`
Expected: FAIL — `Cannot find module '../src/svgimport.js'`

- [ ] **Step 3: Write minimal implementation**

Create `src/svgimport.js`:

```js
(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const IDENTITY = [1, 0, 0, 1, 0, 0];
  const NUM_RE = /-?\d*\.?\d+(?:[eE][-+]?\d+)?/g;

  // SVG matrices are [a,b,c,d,e,f] meaning
  //   x' = a*x + c*y + e
  //   y' = b*x + d*y + f
  function multiplyMatrix(m1, m2) {
    return [
      m1[0] * m2[0] + m1[2] * m2[1],
      m1[1] * m2[0] + m1[3] * m2[1],
      m1[0] * m2[2] + m1[2] * m2[3],
      m1[1] * m2[2] + m1[3] * m2[3],
      m1[0] * m2[4] + m1[2] * m2[5] + m1[4],
      m1[1] * m2[4] + m1[3] * m2[5] + m1[5],
    ];
  }

  function applyMatrix(m, pt) {
    return {
      x: m[0] * pt.x + m[2] * pt.y + m[4],
      y: m[1] * pt.x + m[3] * pt.y + m[5],
    };
  }

  // Parses a transform LIST. Per spec the list applies left to right, which
  // means the leftmost is the outermost — so they compose by successive
  // right-multiplication.
  function parseTransform(str) {
    let m = IDENTITY.slice();
    const re = /([a-zA-Z]+)\s*\(([^)]*)\)/g;
    let match;
    while ((match = re.exec(String(str || "")))) {
      const name = match[1];
      const a = (match[2].match(NUM_RE) || []).map(Number);
      let t = null;
      if (name === "translate") t = [1, 0, 0, 1, a[0] || 0, a.length > 1 ? a[1] : 0];
      else if (name === "scale") t = [a[0] || 0, 0, 0, a.length > 1 ? a[1] : a[0] || 0, 0, 0];
      else if (name === "matrix" && a.length >= 6) t = a.slice(0, 6);
      else if (name === "rotate") {
        const rad = ((a[0] || 0) * Math.PI) / 180;
        const cos = Math.cos(rad), sin = Math.sin(rad);
        const rot = [cos, sin, -sin, cos, 0, 0];
        if (a.length >= 3) {
          // rotate(angle cx cy) == translate(cx,cy) rotate(angle) translate(-cx,-cy)
          t = multiplyMatrix([1, 0, 0, 1, a[1], a[2]], rot);
          t = multiplyMatrix(t, [1, 0, 0, 1, -a[1], -a[2]]);
        } else t = rot;
      } else if (name === "skewX") t = [1, 0, Math.tan(((a[0] || 0) * Math.PI) / 180), 1, 0, 0];
      else if (name === "skewY") t = [1, Math.tan(((a[0] || 0) * Math.PI) / 180), 0, 1, 0, 0];
      if (t) m = multiplyMatrix(m, t);
    }
    return m;
  }

  function num(attrs, name, fallback) {
    const v = parseFloat(attrs[name]);
    return isFinite(v) ? v : fallback;
  }

  // Builds a rounded-rectangle or plain-rectangle outline. Corner arcs reuse
  // the path parser so arc flattening logic exists in exactly one place.
  function rectSubpath(attrs, opts) {
    const x = num(attrs, "x", 0), y = num(attrs, "y", 0);
    const w = num(attrs, "width", 0), h = num(attrs, "height", 0);
    if (w <= 0 || h <= 0) return [];
    let rx = num(attrs, "rx", NaN), ry = num(attrs, "ry", NaN);
    if (!isFinite(rx) && !isFinite(ry)) {
      return [{ points: [
        { x, y }, { x: x + w, y }, { x: x + w, y: y + h }, { x, y: y + h },
      ], closed: true }];
    }
    if (!isFinite(rx)) rx = ry;
    if (!isFinite(ry)) ry = rx;
    rx = Math.min(rx, w / 2); ry = Math.min(ry, h / 2);
    const d = [
      "M", x + rx, y,
      "H", x + w - rx,
      "A", rx, ry, 0, 0, 1, x + w, y + ry,
      "V", y + h - ry,
      "A", rx, ry, 0, 0, 1, x + w - rx, y + h,
      "H", x + rx,
      "A", rx, ry, 0, 0, 1, x, y + h - ry,
      "V", y + ry,
      "A", rx, ry, 0, 0, 1, x + rx, y,
      "Z",
    ].join(" ");
    const subs = root.EMB.parsePathData(d, opts);
    for (const s of subs) s.closed = true;
    return subs;
  }

  function ellipseSubpath(cx, cy, rx, ry, opts) {
    if (rx <= 0 || ry <= 0) return [];
    // Two half arcs, because a single arc from a point back to itself is
    // skipped per the SVG spec.
    const d = [
      "M", cx - rx, cy,
      "A", rx, ry, 0, 0, 1, cx + rx, cy,
      "A", rx, ry, 0, 0, 1, cx - rx, cy,
      "Z",
    ].join(" ");
    const subs = root.EMB.parsePathData(d, opts);
    for (const s of subs) s.closed = true;
    return subs;
  }

  function pointsList(str) {
    const a = (String(str || "").match(NUM_RE) || []).map(Number);
    const pts = [];
    for (let i = 0; i + 1 < a.length; i += 2) pts.push({ x: a[i], y: a[i + 1] });
    return pts;
  }

  function primitiveToSubpaths(tagName, attrs, opts) {
    const o = opts || {};
    switch (tagName) {
      case "rect": return rectSubpath(attrs, o);
      case "circle": {
        const r = num(attrs, "r", 0);
        return ellipseSubpath(num(attrs, "cx", 0), num(attrs, "cy", 0), r, r, o);
      }
      case "ellipse":
        return ellipseSubpath(num(attrs, "cx", 0), num(attrs, "cy", 0),
          num(attrs, "rx", 0), num(attrs, "ry", 0), o);
      case "line":
        return [{ points: [
          { x: num(attrs, "x1", 0), y: num(attrs, "y1", 0) },
          { x: num(attrs, "x2", 0), y: num(attrs, "y2", 0) },
        ], closed: false }];
      case "polygon": {
        const pts = pointsList(attrs.points);
        return pts.length ? [{ points: pts, closed: true }] : [];
      }
      case "polyline": {
        const pts = pointsList(attrs.points);
        return pts.length ? [{ points: pts, closed: false }] : [];
      }
      case "path": {
        const subs = root.EMB.parsePathData(attrs.d || "", o);
        return subs;
      }
      default: return [];
    }
  }

  return { parseTransform, multiplyMatrix, applyMatrix, primitiveToSubpaths };
});
```

Note the `root.EMB.parsePathData` calls: `src/svgpath.js` must load before `src/svgimport.js`, which the ENGINE_FILES ordering in Task 7 enforces.

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test test/svgimport.test.js`
Expected: PASS, 12 tests.

- [ ] **Step 5: Run the full engine suite**

Run: `node --test`
Expected: PASS, 200 tests.

- [ ] **Step 6: Commit**

```bash
git add src/svgimport.js test/svgimport.test.js
git commit -m "feat: SVG transform parsing and shape primitives"
```

---

### Task 5: Document parsing — fills, holes, and region assembly

**Files:**
- Modify: `src/svgimport.js`
- Modify: `test/svgimport.test.js`

**Interfaces:**
- Consumes: everything from Task 4.
- Produces: `parseSVG(svgText, opts)` → `{ regions, pxPerMm, warnings }` where `regions` is `[{ rgb: [r,g,b], shapes: [{ outer: [{x,y}], holes: [[{x,y}]] }] }]` — the exact contract `flatToRegions` in `app/src/lib/imageRegions.js` returns. `opts.targetLongMm` (number, default `50`) sets the physical size the artwork's long side maps to, which is what makes the flattening tolerance resolve in final mm rather than source units. `warnings` is `string[]`.

- [ ] **Step 1: Write the failing test**

Append to `test/svgimport.test.js`:

```js
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

test("a subpath inside another becomes a hole", () => {
  // Outer square with an inner square, one path, evenodd.
  const d = "M 0 0 H 100 V 100 H 0 Z M 25 25 H 75 V 75 H 25 Z";
  const out = svg.parseSVG(svgDoc('<path d="' + d + '" fill="#000" fill-rule="evenodd"/>'));
  assert.strictEqual(out.regions[0].shapes.length, 1);
  assert.strictEqual(out.regions[0].shapes[0].holes.length, 1);
});

test("two disjoint subpaths are two shapes, not a hole", () => {
  const d = "M 0 0 H 10 V 10 H 0 Z M 50 50 H 60 V 60 H 50 Z";
  const out = svg.parseSVG(svgDoc('<path d="' + d + '" fill="#000"/>'));
  assert.strictEqual(out.regions[0].shapes.length, 2);
  assert.strictEqual(out.regions[0].shapes[0].holes.length, 0);
});

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test test/svgimport.test.js`
Expected: FAIL — `svg.parseSVG is not a function`

- [ ] **Step 3: Write minimal implementation**

Add to `src/svgimport.js`, inside the factory before the `return`:

```js
  // Minimal element scanner. A real XML parser is unnecessary and would be a
  // dependency: Ink/Stitch SVGs and exported vector art are well-formed, and
  // all this needs is tag name, attributes, and nesting depth for transform
  // and fill inheritance.
  const TAG_RE = /<\s*(\/?)\s*([a-zA-Z][\w:-]*)((?:\s+[\w:-]+\s*=\s*(?:"[^"]*"|'[^']*'))*)\s*(\/?)\s*>/g;
  const ATTR_RE = /([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/g;

  const NAMED_COLORS = {
    black: [0, 0, 0], white: [255, 255, 255], red: [255, 0, 0],
    green: [0, 128, 0], lime: [0, 255, 0], blue: [0, 0, 255],
    yellow: [255, 255, 0], cyan: [0, 255, 255], aqua: [0, 255, 255],
    magenta: [255, 0, 255], fuchsia: [255, 0, 255], gray: [128, 128, 128],
    grey: [128, 128, 128], silver: [192, 192, 192], maroon: [128, 0, 0],
    olive: [128, 128, 0], navy: [0, 0, 128], purple: [128, 0, 128],
    teal: [0, 128, 128], orange: [255, 165, 0], pink: [255, 192, 203],
    brown: [165, 42, 42], gold: [255, 215, 0], beige: [245, 245, 220],
  };

  function parseAttrs(raw) {
    const attrs = {};
    let m;
    ATTR_RE.lastIndex = 0;
    while ((m = ATTR_RE.exec(raw || ""))) attrs[m[1]] = m[2] !== undefined ? m[2] : m[3];
    return attrs;
  }

  // Reads a property from the inline style attribute, which per CSS cascade
  // outranks the equivalent presentation attribute.
  function styleProp(styleStr, prop) {
    if (!styleStr) return null;
    const re = new RegExp("(?:^|;)\\s*" + prop + "\\s*:\\s*([^;]+)", "i");
    const m = re.exec(styleStr);
    return m ? m[1].trim() : null;
  }

  function parseColor(value) {
    if (!value) return null;
    const v = String(value).trim().toLowerCase();
    if (v === "none" || v === "transparent") return null;
    if (v[0] === "#") {
      const hex = v.slice(1);
      if (hex.length === 3) {
        return [parseInt(hex[0] + hex[0], 16), parseInt(hex[1] + hex[1], 16), parseInt(hex[2] + hex[2], 16)];
      }
      if (hex.length === 6) {
        return [parseInt(hex.slice(0, 2), 16), parseInt(hex.slice(2, 4), 16), parseInt(hex.slice(4, 6), 16)];
      }
      return null;
    }
    if (v.startsWith("rgb")) {
      const a = (v.match(NUM_RE) || []).map(Number);
      if (a.length >= 3) return [Math.round(a[0]), Math.round(a[1]), Math.round(a[2])];
      return null;
    }
    if (Object.prototype.hasOwnProperty.call(NAMED_COLORS, v)) return NAMED_COLORS[v].slice();
    return null; // url(#gradient) and anything else unsupported
  }

  function signedArea(pts) {
    let a = 0;
    for (let i = 0, n = pts.length; i < n; i++) {
      const p = pts[i], q = pts[(i + 1) % n];
      a += p.x * q.y - q.x * p.y;
    }
    return a / 2;
  }

  function bboxOf(pts) {
    let minx = Infinity, miny = Infinity, maxx = -Infinity, maxy = -Infinity;
    for (const p of pts) {
      if (p.x < minx) minx = p.x; if (p.x > maxx) maxx = p.x;
      if (p.y < miny) miny = p.y; if (p.y > maxy) maxy = p.y;
    }
    return { minx, miny, maxx, maxy };
  }

  function pointInPolygon(pt, poly) {
    let inside = false;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      const a = poly[i], b = poly[j];
      if ((a.y > pt.y) !== (b.y > pt.y) &&
          pt.x < ((b.x - a.x) * (pt.y - a.y)) / (b.y - a.y) + a.x) inside = !inside;
    }
    return inside;
  }

  // Groups a flat subpath list into {outer, holes}. A subpath nested inside
  // an odd number of others is a hole; nested inside an even number, a new
  // outer. This matches even-odd exactly and matches non-zero for the
  // overwhelmingly common case of correctly-wound artwork.
  function groupIntoShapes(rings) {
    const usable = rings.filter((r) => r.length >= 3);
    const withMeta = usable.map((pts) => ({ pts, box: bboxOf(pts), area: Math.abs(signedArea(pts)) }));
    withMeta.sort((a, b) => b.area - a.area); // outers before their holes
    const depth = new Array(withMeta.length).fill(0);
    for (let i = 0; i < withMeta.length; i++) {
      for (let j = 0; j < withMeta.length; j++) {
        if (i === j) continue;
        const inner = withMeta[i], outer = withMeta[j];
        if (outer.area <= inner.area) continue;
        if (inner.box.minx < outer.box.minx || inner.box.maxx > outer.box.maxx ||
            inner.box.miny < outer.box.miny || inner.box.maxy > outer.box.maxy) continue;
        if (pointInPolygon(inner.pts[0], outer.pts)) depth[i]++;
      }
    }
    const shapes = [];
    const outerIndexByDepthPath = [];
    for (let i = 0; i < withMeta.length; i++) {
      if (depth[i] % 2 === 0) {
        shapes.push({ outer: withMeta[i].pts, holes: [] });
        outerIndexByDepthPath[i] = shapes.length - 1;
      }
    }
    for (let i = 0; i < withMeta.length; i++) {
      if (depth[i] % 2 === 0) continue;
      // Attach to the smallest enclosing even-depth ring.
      let bestIdx = -1, bestArea = Infinity;
      for (let j = 0; j < withMeta.length; j++) {
        if (depth[j] % 2 !== 0 || j === i) continue;
        if (withMeta[j].area <= withMeta[i].area) continue;
        if (!pointInPolygon(withMeta[i].pts[0], withMeta[j].pts)) continue;
        if (withMeta[j].area < bestArea) { bestArea = withMeta[j].area; bestIdx = j; }
      }
      if (bestIdx >= 0) shapes[outerIndexByDepthPath[bestIdx]].holes.push(withMeta[i].pts);
    }
    return shapes;
  }

  function parseSVG(svgText, opts) {
    const o = opts || {};
    const targetLongMm = o.targetLongMm || 50;
    const warnings = [];
    const text = String(svgText || "");

    // Root sizing: viewBox is authoritative; width/height is the fallback.
    let vbW = 0, vbH = 0;
    const rootMatch = /<\s*svg\b([^>]*)>/i.exec(text);
    const rootAttrs = rootMatch ? parseAttrs(rootMatch[1]) : {};
    if (rootAttrs.viewBox) {
      const a = (rootAttrs.viewBox.match(NUM_RE) || []).map(Number);
      if (a.length >= 4) { vbW = a[2]; vbH = a[3]; }
    }
    if (!vbW || !vbH) {
      vbW = parseFloat(rootAttrs.width) || 0;
      vbH = parseFloat(rootAttrs.height) || 0;
      if (vbW && vbH) warnings.push("No viewBox found; using the width/height attributes for scale.");
    }
    if (!vbW || !vbH) {
      vbW = 100; vbH = 100;
      warnings.push("No viewBox, width or height found; assuming a 100x100 coordinate space.");
    }

    // Flattening tolerance resolves in FINAL MM, not source units: a fixed
    // source-unit tolerance silently coarsens as a design scales up. This is
    // the same class of bug as the 2026-07-27 density-floor regression.
    const unitsPerMm = Math.max(vbW, vbH) / targetLongMm;
    const TOLERANCE_MM = 0.05;
    const tolerance = TOLERANCE_MM * unitsPerMm;

    // Stack of inherited state, one frame per open element.
    const stack = [{ matrix: IDENTITY.slice(), fill: null, fillRule: "nonzero" }];
    const byColor = new Map();
    let sawText = false, sawStrokeOnly = false;

    let m;
    TAG_RE.lastIndex = 0;
    while ((m = TAG_RE.exec(text))) {
      const closing = m[1] === "/";
      const tag = m[2].toLowerCase().replace(/^.*:/, ""); // strip any namespace
      const selfClosing = m[4] === "/";
      if (closing) { if (stack.length > 1) stack.pop(); continue; }

      const attrs = parseAttrs(m[3]);
      const parent = stack[stack.length - 1];

      let matrix = parent.matrix;
      if (attrs.transform) matrix = multiplyMatrix(matrix, parseTransform(attrs.transform));

      const styleFill = styleProp(attrs.style, "fill");
      const rawFill = styleFill !== null ? styleFill : attrs.fill;
      const fill = rawFill !== undefined && rawFill !== null
        ? { value: rawFill, rgb: parseColor(rawFill) }
        : parent.fill;
      const fillRule = styleProp(attrs.style, "fill-rule") || attrs["fill-rule"] || parent.fillRule;
      const frame = { matrix, fill, fillRule };

      if (tag === "text" || tag === "tspan") sawText = true;

      if (tag === "svg" || tag === "g" || tag === "defs" || tag === "symbol") {
        if (!selfClosing) stack.push(frame);
        continue;
      }

      const subs = primitiveToSubpaths(tag, attrs, { tolerance });
      if (subs.length) {
        // An explicit fill of "none" means no fill; an ABSENT fill anywhere in
        // the ancestor chain means black, per the SVG initial value.
        const explicitNone = fill && fill.rgb === null;
        const rgb = fill && fill.rgb ? fill.rgb : (explicitNone ? null : [0, 0, 0]);
        if (rgb === null) {
          const strokeVal = styleProp(attrs.style, "stroke") || attrs.stroke;
          if (strokeVal && strokeVal !== "none") sawStrokeOnly = true;
        } else {
          const rings = subs.map((s) => s.points.map((p) => applyMatrix(matrix, p)));
          const key = rgb.join(",");
          if (!byColor.has(key)) byColor.set(key, { rgb, rings: [] });
          for (const r of rings) byColor.get(key).rings.push(r);
        }
      }
      if (!selfClosing && subs.length === 0 && tag !== "path") stack.push(frame);
    }

    if (sawText) {
      warnings.push("This file contains live text. Convert text to outlines in your design app, or it will not stitch.");
    }
    if (sawStrokeOnly && byColor.size === 0) {
      warnings.push("This artwork is made of strokes with no fills. Stroke conversion is not supported yet — add fills, or expand the strokes to outlines.");
    }

    const regions = [];
    for (const { rgb, rings } of byColor.values()) {
      const shapes = groupIntoShapes(rings);
      if (shapes.length) regions.push({ rgb, shapes });
    }

    return { regions, pxPerMm: unitsPerMm, warnings };
  }
```

Add `parseSVG` to the returned object:

```js
  return { parseTransform, multiplyMatrix, applyMatrix, primitiveToSubpaths, parseSVG };
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test test/svgimport.test.js`
Expected: PASS, 30 tests.

- [ ] **Step 5: Run the full engine suite**

Run: `node --test`
Expected: PASS, 218 tests.

- [ ] **Step 6: Commit**

```bash
git add src/svgimport.js test/svgimport.test.js
git commit -m "feat: parse SVG documents into color regions with hole detection"
```

---

### Task 6: Verify real shape packs render — RISK GATE

**Files:**
- Create: `tools/try-svg.mjs`
- Create: `docs/superpowers/notes/2026-07-27-shape-pack-findings.md`

**Interfaces:**
- Consumes: `EMB.parseSVG` from Task 5, `EMB.buildQualityDesign` from `src/digitize.js`, `renderDesignPNG` from the existing `tools/render-dst.mjs` harness.
- Produces: no code other tasks depend on. This task exists to answer a question before Tasks 8–10 build a UI on top of an assumption.

**Why this task is here:** the shape grid's entire value rests on pictogram packs stitching acceptably. The 2026-07-27 investigation established they are fill-based SVG artwork, but **not** that they produce good stitches through `buildQualityDesign`. Several use `cross_stitch_method` and `pattern_size_mm`, which this engine does not implement — those will come out as plain tatami fill, visibly different from the `preview.png` upstream ships. Find out now, not after building a grid.

- [ ] **Step 1: Write the harness**

Create `tools/try-svg.mjs`:

```js
// Parses an SVG file (or one GlyphLayer from an Ink/Stitch font SVG) through
// the vector importer and renders the resulting stitches to a PNG, so shape
// packs can be eyeballed without a browser.
//
// Usage:
//   node tools/try-svg.mjs <file.svg> [outPrefix] [glyphLabel]
import { readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);

require("../src/units.js");
require("../src/garments.js");
require("../src/fabrics.js");
require("../src/fill.js");
require("../src/geometry.js");
require("../src/satin.js");
require("../src/satinplay.js");
require("../src/satinfont.js");
require("../src/svgpath.js");
require("../src/svgimport.js");
require("../src/digitize.js");
const EMB = globalThis.EMB;

const [file, outPrefix = "scratch_svgtry", glyphLabel] = process.argv.slice(2);
if (!file) { console.error("usage: node tools/try-svg.mjs <file.svg> [outPrefix] [glyphLabel]"); process.exit(1); }

let svgText = readFileSync(file, "utf8");

// Ink/Stitch font SVGs hold one <g inkscape:label="GlyphLayer-X"> per glyph.
// Extract just the requested layer so a single shape can be inspected.
if (glyphLabel) {
  const re = new RegExp('<g[^>]*inkscape:label\\s*=\\s*"GlyphLayer-' + glyphLabel + '"[\\s\\S]*?</g>', "i");
  const m = re.exec(svgText);
  if (!m) { console.error("glyph layer not found: " + glyphLabel); process.exit(1); }
  svgText = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000">' + m[0] + "</svg>";
}

const parsed = EMB.parseSVG(svgText, { targetLongMm: 60 });
console.log("regions:", parsed.regions.length);
for (const [i, r] of parsed.regions.entries()) {
  const shapeCount = r.shapes.length;
  const holeCount = r.shapes.reduce((n, s) => n + s.holes.length, 0);
  console.log("  region " + i + " rgb=" + r.rgb.join(",") + " shapes=" + shapeCount + " holes=" + holeCount);
}
for (const w of parsed.warnings) console.log("warning:", w);

if (!parsed.regions.length) { console.log("no regions — nothing to stitch"); process.exit(0); }

const garment = EMB.getGarment("patch");
const design = EMB.buildQualityDesign(parsed.regions, {
  garment,
  fabric: EMB.getFabric(EMB.fabricForGarment("patch")),
  pxPerMm: parsed.pxPerMm,
  densityMm: 0.4,
  satinMaxWidthMm: 3.0,
  underlay: true,
});
console.log("stitches:", design.stitchCount, "colors:", design.colorCount,
  "size:", Math.round(design.widthMM) + "x" + Math.round(design.heightMM) + "mm");

writeFileSync(outPrefix + ".json", JSON.stringify({
  regions: parsed.regions.length,
  warnings: parsed.warnings,
  stitchCount: design.stitchCount,
  colorCount: design.colorCount,
  widthMM: design.widthMM,
  heightMM: design.heightMM,
}, null, 2));
console.log("wrote " + outPrefix + ".json");
```

- [ ] **Step 2: Download two packs and run the harness**

The 2026-07-27 investigation left downloaded copies in `scratch_packs/` (gitignored). If absent, re-fetch:

```bash
curl -sL -o scratch_packs/nautical.ltr.svg https://raw.githubusercontent.com/inkstitch/embroidery-fonts/main/src/nautical/ltr.svg
curl -sL -o scratch_packs/flowery_crosses.ltr.svg https://raw.githubusercontent.com/inkstitch/embroidery-fonts/main/src/flowery_crosses/ltr.svg
```

Run against a whole pack and a single glyph:

```bash
node tools/try-svg.mjs scratch_packs/nautical.ltr.svg scratch_packs/naut_all
node tools/try-svg.mjs scratch_packs/nautical.ltr.svg scratch_packs/naut_A A
node tools/try-svg.mjs scratch_packs/flowery_crosses.ltr.svg scratch_packs/flow_A A
```

Expected: non-zero `regions`, non-zero `stitchCount`, and a plausible size. A region count in the hundreds for a whole-pack run is normal (every glyph at once).

- [ ] **Step 3: Render a PNG and look at it**

Use the existing DST render harness to produce an image, following the pattern in `tools/render-dst.mjs`. Export the design to DST first, then render:

```bash
node tools/render-dst.mjs scratch_packs/naut_A.dst scratch_packs/naut_A.png
```

If `try-svg.mjs` does not yet write a DST, add that (mirroring how `tools/run-digitize.mjs` writes one via `EMB.encodeDST`) before rendering.

- [ ] **Step 4: Record the findings**

Create `docs/superpowers/notes/2026-07-27-shape-pack-findings.md` documenting, per pack tested:
- region count, stitch count, and output size
- whether the rendered PNG resembles the pack's upstream `preview.png`
- any warnings emitted
- a verdict: **usable**, **usable with caveats**, or **exclude**

- [ ] **Step 5: STOP and report to the user**

This is a decision gate, not a step to push through. Report:
- If packs render acceptably: proceed to Task 7.
- If cross-stitch/pattern packs look materially worse than their previews: report which packs are affected and recommend excluding them, per spec §5 — *do not ship a pack that looks nothing like its own preview image*.
- If nothing renders usefully: **stop.** Tasks 8–10 (shape element, shape grid) lose their basis, and the slice should be re-scoped to vector logo import only. That is a real possible outcome and it is better found here than after building a picker.

- [ ] **Step 6: Commit**

```bash
git add tools/try-svg.mjs docs/superpowers/notes/2026-07-27-shape-pack-findings.md
git commit -m "test: vector import harness and shape pack verification findings"
```

---

### Task 7: Wire the engine modules into both front-ends

**Files:**
- Modify: `app/scripts/copy-engine.mjs:8-14`
- Modify: `app/src/lib/emb.js:12-18`
- Modify: `EMB-Bot.html` (the `<script src="src/...">` block)
- Test: `app/src/lib/emb.spec.js` (create if absent)

**Interfaces:**
- Consumes: `src/svgpath.js`, `src/svgimport.js`.
- Produces: `EMB.parseSVG` available in the browser. `ENGINE_KEYS` and `ENGINE_FILES` both include `svgpath.js` and `svgimport.js`, in that order, before `digitize.js`.

**Ordering constraint:** `svgimport.js` calls `root.EMB.parsePathData` at runtime, so `svgpath.js` must load first. Both must load before anything that calls `parseSVG`.

- [ ] **Step 1: Write the failing test**

Create `app/src/lib/emb.spec.js`:

```js
import { describe, it, expect } from "vitest";
import { ENGINE_KEYS } from "./emb.js";
import { ENGINE_FILES } from "../../scripts/copy-engine.mjs";

describe("engine file lists", () => {
  it("ENGINE_KEYS and ENGINE_FILES are identical", () => {
    expect(ENGINE_KEYS).toEqual(ENGINE_FILES);
  });

  it("includes the SVG import modules", () => {
    expect(ENGINE_KEYS).toContain("svgpath.js");
    expect(ENGINE_KEYS).toContain("svgimport.js");
  });

  it("loads svgpath before svgimport", () => {
    expect(ENGINE_KEYS.indexOf("svgpath.js")).toBeLessThan(ENGINE_KEYS.indexOf("svgimport.js"));
  });
});
```

Note: `app/src/lib/emb.js` throws at import time when the engine global is absent. If this test fails for that reason rather than on the assertion, move `ENGINE_KEYS` into its own module (`app/src/lib/engineFiles.js`) that both `emb.js` and this test import, and update `emb.js` to re-export it. Keep the single-source-of-truth property either way.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && npx vitest run src/lib/emb.spec.js`
Expected: FAIL — `svgpath.js` not in the list.

- [ ] **Step 3: Update all three lists**

In `app/scripts/copy-engine.mjs`, change `ENGINE_FILES` to:

```js
export const ENGINE_FILES = [
  "units.js", "garments.js", "fabrics.js", "fill.js", "geometry.js",
  "quantize.js", "flatten.js", "satin.js", "satinplay.js", "satinfont.js",
  "svgpath.js", "svgimport.js",
  "dst.js", "exp.js", "pes.js", "svgexport.js", "stitchModel.js",
  "fonts.js", "digitize.js", "render.js", "pdfsheet.js",
  "fonts/satin-fonts.js",
];
```

Apply the identical array to `ENGINE_KEYS` in `app/src/lib/emb.js`.

In `EMB-Bot.html`, add these two tags immediately after the `satinfont.js` tag and before `dst.js`:

```html
    <script src="src/svgpath.js"></script>
    <script src="src/svgimport.js"></script>
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd app && npx vitest run src/lib/emb.spec.js
```
Expected: PASS, 3 tests.

```bash
cd app && npm test
```
Expected: PASS. Previous total was 182; expect 185.

- [ ] **Step 5: Verify the engine copy step works**

Run: `cd app && node scripts/copy-engine.mjs`
Expected: `copied 22 engine files to ...` and no "missing engine file" error.

- [ ] **Step 6: Commit**

```bash
git add app/scripts/copy-engine.mjs app/src/lib/emb.js app/src/lib/emb.spec.js EMB-Bot.html
git commit -m "feat: load svgpath and svgimport in both front-ends"
```

---

### Task 8: SVG upload path in the Studio

**Files:**
- Create: `app/src/lib/svgRegions.js`
- Create: `app/src/lib/svgRegions.spec.js`
- Modify: `app/src/lib/generate.js:15-34`
- Modify: `app/src/ui/ImagePanel.svelte`

**Interfaces:**
- Consumes: `EMB.parseSVG` from Task 7.
- Produces:
  - `svgToRegions(svgText, opts)` → `{ regions, pxPerMm, warnings }`, applying `opts.threadRgb` (`{ [regionIndex]: [r,g,b] }`) overrides exactly as `flatToRegions` does.
  - `generateElement` handles image elements whose `runtime.svgs[element.id]` holds SVG text, taking the vector path instead of the flatten path.

- [ ] **Step 1: Write the failing test**

Create `app/src/lib/svgRegions.spec.js`:

```js
import { describe, it, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);

beforeAll(() => {
  for (const f of ["units", "garments", "fabrics", "fill", "geometry", "satin",
                   "satinplay", "satinfont", "svgpath", "svgimport", "digitize"]) {
    require("../../../src/" + f + ".js");
  }
});

const DOC = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">' +
  '<rect x="0" y="0" width="40" height="40" fill="#ff0000"/>' +
  '<rect x="50" y="50" width="40" height="40" fill="#0000ff"/></svg>';

describe("svgToRegions", () => {
  it("returns the region contract with two colors", async () => {
    const { svgToRegions } = await import("./svgRegions.js");
    const out = svgToRegions(DOC);
    expect(out.regions).toHaveLength(2);
    expect(out.pxPerMm).toBeGreaterThan(0);
    expect(Array.isArray(out.warnings)).toBe(true);
    expect(out.regions[0].shapes[0].outer.length).toBeGreaterThanOrEqual(3);
  });

  it("applies thread color overrides by region index", async () => {
    const { svgToRegions } = await import("./svgRegions.js");
    const out = svgToRegions(DOC, { threadRgb: { 0: [10, 20, 30] } });
    expect(out.regions[0].rgb).toEqual([10, 20, 30]);
    expect(out.regions[1].rgb).not.toEqual([10, 20, 30]);
  });

  it("surfaces warnings from the parser", async () => {
    const { svgToRegions } = await import("./svgRegions.js");
    const out = svgToRegions('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">' +
      '<text x="0" y="5">hi</text><rect width="4" height="4" fill="#000"/></svg>');
    expect(out.warnings.some((w) => /outline/i.test(w))).toBe(true);
  });

  it("throws a clear error when no fillable geometry exists", async () => {
    const { svgToRegions } = await import("./svgRegions.js");
    expect(() => svgToRegions('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"></svg>'))
      .toThrow(/no filled shapes/i);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && npx vitest run src/lib/svgRegions.spec.js`
Expected: FAIL — cannot resolve `./svgRegions.js`.

- [ ] **Step 3: Write the adapter**

Create `app/src/lib/svgRegions.js`:

```js
import { EMB } from "./emb.js";

// Physical size the artwork's long side maps to before hoop fitting, matching
// imageRegions.js's NOMINAL_LONG_MM so vector and raster art land at a
// comparable pre-fit scale.
const NOMINAL_LONG_MM = 50;

// Parses SVG text into the ColorRegion[] contract buildQualityDesign expects —
// the same shape flatToRegions returns for raster art, so downstream code
// (generate.js, combine.js, the field renderer) needs no vector-specific path.
//
// opts.threadRgb: { [regionIndex]: [r,g,b] } overrides, keyed by the index of
// the region in the returned array — the same convention flatToRegions uses
// for palette indices.
export function svgToRegions(svgText, opts) {
  const threadRgb = (opts && opts.threadRgb) || {};
  const parsed = EMB.parseSVG(svgText, {
    targetLongMm: (opts && opts.targetLongMm) || NOMINAL_LONG_MM,
  });
  if (!parsed.regions.length) {
    const hint = parsed.warnings.length ? " " + parsed.warnings[0] : "";
    throw new Error("This SVG has no filled shapes to stitch." + hint);
  }
  const regions = parsed.regions.map((r, i) => ({
    rgb: i in threadRgb ? [...threadRgb[i]] : r.rgb,
    shapes: r.shapes,
  }));
  return { regions, pxPerMm: parsed.pxPerMm, warnings: parsed.warnings };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app && npx vitest run src/lib/svgRegions.spec.js`
Expected: PASS, 4 tests.

- [ ] **Step 5: Route image elements through the vector path**

In `app/src/lib/generate.js`, add the import at the top:

```js
import { svgToRegions } from "./svgRegions.js";
```

Replace the image branch of `generateElement` (currently lines 18-34) with:

```js
  if (element.type === "image") {
    const fabric = EMB.getFabric(EMB.fabricForGarment(garment.id));
    const common = {
      garment, fabric, densityMm: 0.4, satinMaxWidthMm: 3.0,
      underlay: element.underlay,
      targetWidthMm: element.sizeMm || undefined,
      offsetXMm: element.offsetXMm || 0,
      offsetYMm: element.offsetYMm || 0,
    };

    // Vector path: runtime.svgs[id] holds the uploaded SVG source text. Takes
    // precedence over the raster path because an SVG never needs flattening —
    // it already states its colors exactly.
    const svgs = (runtime && runtime.svgs) || {};
    const svgText = svgs[element.id];
    if (svgText) {
      const { regions, pxPerMm } = svgToRegions(svgText, { threadRgb: element.threadRgb });
      return EMB.buildQualityDesign(regions, { ...common, pxPerMm });
    }

    const flats = (runtime && runtime.flats) || {};
    const flat = flats[element.id];
    if (!flat) return null;
    const { regions, pxPerMm } = flatToRegions(flat, { threadRgb: element.threadRgb });
    return EMB.buildQualityDesign(regions, { ...common, pxPerMm });
  }
```

- [ ] **Step 6: Accept .svg in the upload control**

`app/src/ui/ImagePanel.svelte` currently declares props at lines 14-24 (`element`, `workImage`, `flat`) and has its file input at line 249. Add a third owned-by-App prop next to `flat`:

```js
  // svgText: raw SVG source when the uploaded file was a vector. Owned by
  // App for the same reason workImage/flat are — it must survive this panel
  // being destroyed on step navigation. Non-null means the vector path is
  // active and every flatten control is irrelevant.
  export let svgText = null;
```

Change the file input at line 249 to accept vectors:

```svelte
  <input type="file" accept="image/*,.svg,image/svg+xml" on:change={onFileChange} />
```

In `onFileChange` (around line 118), branch before `loadImage`. Insert at the top of the `try` block:

```js
      // Vector branch: an SVG states its colors exactly, so it skips
      // prepRGBA/flattenRGBA entirely — no rasterizing, no median-cut.
      if (file.type === "image/svg+xml" || /\.svg$/i.test(file.name)) {
        const text = await file.text();
        fileName = file.name;
        d("svg", text);       // App stores this in runtime.svgs[element.id]
        d("flat", null);      // clear any raster state from a previous upload
        busy = false;
        return;
      }
```

Wrap every flatten control in the template so it only renders for raster input. Find the Colors slider, remove-background checkbox, flattened-art preview, and the Merge selected / Reset colors swatch bar, and guard the whole block:

```svelte
{#if !svgText}
  <!-- existing colors slider, remove-bg, flatten preview, merge/reset bar -->
{:else}
  <p class="vectorbadge">Vector — exact edges, no flattening needed.</p>
  {#each vectorWarnings as w}
    <p class="hint">{w}</p>
  {/each}
{/if}
```

Derive `vectorWarnings` reactively so parse problems surface without blocking:

```js
  $: vectorWarnings = (() => {
    if (!svgText) return [];
    try { return svgToRegions(svgText).warnings; } catch (e) { return [e.message]; }
  })();
```

Import it at the top of the component: `import { svgToRegions } from "../lib/svgRegions.js";`

In `App.svelte`, add a `svgs` map beside the existing `flats` map, handle the new `svg` event by writing `svgs[element.id] = text`, pass `svgText={svgs[el.id] ?? null}` down through `ContentStep` to `ImagePanel`, and include `svgs` in the `runtime` object handed to `generateAll`. Reset it at boot exactly as `_hasImage` is reset — an uploaded file cannot survive a page reload.

**Do not put `svgs` inside `ImagePanel`.** Slice 2's review found panel-local working state dies on step navigation; the same trap applies here.

- [ ] **Step 7: Run all tests**

```bash
cd app && npm test
```
Expected: PASS, 189 tests.

```bash
node --test
```
Expected: PASS, 218 tests.

- [ ] **Step 8: Verify in the browser**

Start the Studio, upload a simple two-color SVG, confirm: the flatten controls are hidden, the swatches show the file's actual colors, Generate produces stitches, and the DST downloads.

- [ ] **Step 9: Commit**

```bash
git add app/src/lib/svgRegions.js app/src/lib/svgRegions.spec.js app/src/lib/generate.js app/src/ui/ImagePanel.svelte
git commit -m "feat: SVG upload path with exact-edge vector import"
```

---

### Task 9: Shape element type and project model v3

**Files:**
- Modify: `app/src/lib/project.js:1-38, 108-157`
- Modify: `app/src/lib/project.spec.js`
- Modify: `app/src/lib/generate.js`
- Create: `app/src/lib/shapes.js`

**Interfaces:**
- Consumes: `svgToRegions` from Task 8.
- Produces:
  - `defaultShapeElement(id)` → `{ id, type: "shape", packId, shapeId, colorRgb, underlay, sizeMm, offsetXMm, offsetYMm }`.
  - `migrateProject` accepts v2 input and returns `{ version: 3, ... }`.
  - `getShapeSVG(packId, shapeId)` → SVG text, from `shapes.js`.
  - `addElement(project, "shape", hoopWmm)` works.

**Prerequisite:** Task 6 must have concluded that packs are usable. If it did not, stop — this task and Task 10 have no basis.

- [ ] **Step 1: Write the failing test**

Append to `app/src/lib/project.spec.js`:

```js
import { defaultShapeElement, defaultProject, migrateProject, addElement } from "./project.js";

describe("shape elements (v3)", () => {
  it("defaultShapeElement has the expected shape", () => {
    const el = defaultShapeElement("e9");
    expect(el).toMatchObject({
      id: "e9", type: "shape", packId: null, shapeId: null,
      underlay: true, sizeMm: null, offsetXMm: 0, offsetYMm: 0,
    });
    expect(Array.isArray(el.colorRgb)).toBe(true);
  });

  it("a new project is version 3", () => {
    expect(defaultProject().version).toBe(3);
  });

  it("addElement supports the shape type", () => {
    const p = addElement(defaultProject(), "shape", 100);
    const added = p.elements[p.elements.length - 1];
    expect(added.type).toBe("shape");
    expect(p.selectedId).toBe(added.id);
  });

  it("migrates a v2 project to v3 without altering its elements", () => {
    const v2 = {
      version: 2, garmentId: "hat_front", selectedId: "e1",
      elements: [{ id: "e1", type: "text", text: "Kent", fontKey: "geneva_simple" }],
      fabricRgb: [10, 20, 30],
    };
    const out = migrateProject(v2);
    expect(out.version).toBe(3);
    expect(out.garmentId).toBe("hat_front");
    expect(out.elements).toHaveLength(1);
    expect(out.elements[0].text).toBe("Kent");
    expect(out.fabricRgb).toEqual([10, 20, 30]);
  });

  it("still migrates a v1 project all the way to v3", () => {
    const out = migrateProject({ mode: "text", text: "Hi", fontKey: "geneva_simple" });
    expect(out.version).toBe(3);
    expect(out.elements[0].text).toBe("Hi");
  });

  it("a v3 project round-trips unchanged", () => {
    const p = defaultProject();
    expect(migrateProject(p)).toEqual(p);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && npx vitest run src/lib/project.spec.js`
Expected: FAIL — `defaultShapeElement is not exported`.

- [ ] **Step 3: Implement the model change**

In `app/src/lib/project.js`, add after `defaultImageElement`:

```js
export function defaultShapeElement(id) {
  return {
    id,
    type: "shape",
    packId: null,     // set when the user picks from the shape grid
    shapeId: null,
    colorRgb: [20, 20, 20],
    underlay: true,
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
  };
}
```

Change `defaultProject`'s `version: 2` to `version: 3`.

In `addElement`, replace the factory selection line with:

```js
  const factory = type === "image" ? defaultImageElement
    : type === "shape" ? defaultShapeElement
    : defaultTextElement;
```

In `migrateV1`, change the returned `version: 2` to `version: 3`.

Replace `migrateProject` with:

```js
// Normalizes any input (a v3 project, a v2 project, a v1 project, or garbage)
// into a valid v3 project. v2 -> v3 is purely a version bump: the shape
// element type is additive, so no existing element needs rewriting.
export function migrateProject(input) {
  if (!input || typeof input !== "object") return defaultProject();

  if (input.version === 3 || input.version === 2) {
    const base = defaultProject();
    const merged = { ...base, ...input, version: 3 };
    if (!Array.isArray(merged.elements) || merged.elements.length === 0) {
      merged.elements = base.elements;
    }
    return merged;
  }

  const looksLikeV1 = "mode" in input || "text" in input || "fontKey" in input;
  if (looksLikeV1) return { ...defaultProject(), ...migrateV1(input) };

  return defaultProject();
}
```

- [ ] **Step 4: Add the shape registry**

Create `app/src/lib/shapes.js`:

```js
// Shape pack registry. Each pack is a set of named shapes, every shape stored
// as SVG source text that svgToRegions() parses at generate time — the same
// path an uploaded vector logo takes, so shapes need no dedicated engine code.
//
// Packs are produced offline by tools/build-shapes.mjs from Ink/Stitch
// pictogram fonts. Task 6's findings determine which packs are included:
// packs relying on cross-stitch or pattern fills are excluded, because this
// engine renders them as plain tatami and they would not resemble their own
// preview images.
//
// Shape labels are authored during import and are the ONLY thing surfaced to
// users. The underlying glyph letter is never shown — nobody should have to
// know a star lives under "k".
export const SHAPE_PACKS = {};

export function listPacks() {
  return Object.values(SHAPE_PACKS).map((p) => ({
    id: p.id, name: p.name, license: p.license, count: p.shapes.length,
  }));
}

export function listShapes(packId) {
  const pack = SHAPE_PACKS[packId];
  return pack ? pack.shapes.map((s) => ({ id: s.id, label: s.label, preview: s.preview })) : [];
}

export function getShapeSVG(packId, shapeId) {
  const pack = SHAPE_PACKS[packId];
  if (!pack) throw new Error("Unknown shape pack: " + packId);
  const shape = pack.shapes.find((s) => s.id === shapeId);
  if (!shape) throw new Error("Unknown shape: " + packId + "/" + shapeId);
  return shape.svg;
}
```

- [ ] **Step 5: Generate shape elements**

In `app/src/lib/generate.js`, add the import:

```js
import { getShapeSVG } from "./shapes.js";
```

Add this branch in `generateElement`, before the text handling:

```js
  if (element.type === "shape") {
    if (!element.packId || !element.shapeId) return null; // nothing picked yet
    const svgText = getShapeSVG(element.packId, element.shapeId);
    const { regions, pxPerMm } = svgToRegions(svgText, { threadRgb: { 0: element.colorRgb } });
    return EMB.buildQualityDesign(regions, {
      garment,
      fabric: EMB.getFabric(EMB.fabricForGarment(garment.id)),
      pxPerMm,
      densityMm: 0.4,
      satinMaxWidthMm: 3.0,
      underlay: element.underlay,
      targetWidthMm: element.sizeMm || undefined,
      offsetXMm: element.offsetXMm || 0,
      offsetYMm: element.offsetYMm || 0,
    });
  }
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd app && npm test
```
Expected: PASS, 195 tests.

- [ ] **Step 7: Verify saved projects still load**

Open the Studio, load a project saved before this change, and confirm it opens with its elements intact and its version reported as 3. Storage integrity rules from Slice 7 apply: a corrupt record must return null rather than being overwritten with a blank project.

- [ ] **Step 8: Commit**

```bash
git add app/src/lib/project.js app/src/lib/project.spec.js app/src/lib/shapes.js app/src/lib/generate.js
git commit -m "feat: shape element type and project model v3"
```

---

### Task 10: Shape pack importer and the shape grid UI

**Files:**
- Create: `tools/build-shapes.mjs`
- Create: `app/src/ui/ShapePicker.svelte`
- Modify: `app/src/ui/ContentStep.svelte`
- Modify: `app/src/lib/shapes.js` (populate `SHAPE_PACKS`)
- Modify: `README.md`
- Modify: `COOKBOOK.md`

**Interfaces:**
- Consumes: `listPacks`, `listShapes`, `getShapeSVG` from Task 9; `defaultShapeElement` and `addElement` from Task 9.
- Produces: a `+ Shape` action in ContentStep that inserts a configured shape element.

- [ ] **Step 1: Write the importer**

Create `tools/build-shapes.mjs`. It must:

- Read an Ink/Stitch pictogram font directory (`ltr.svg`, or an `ltr/` directory of per-glyph files — `mai_en_fleur` uses the latter, so **fail loudly on an unrecognised layout rather than skipping silently**).
- Split into `<g inkscape:label="GlyphLayer-X">` groups, one per shape.
- Wrap each glyph group in a standalone `<svg>` with a `viewBox` derived from the glyph's own geometry bounds.
- Emit `{ id, name, license, shapes: [{ id, label, svg, preview }] }` per pack.
- Read the pack's `LICENSE` file and carry it into the pack record — the credits obligation from the licensing decision applies to shapes too.
- Require a human-authored label map, since upstream glyph layers are named by letter, not by content. Store labels in `tools/shape-labels.json` keyed `packId/glyphLetter`. A glyph with no label is **excluded**, not shipped as "k".

- [ ] **Step 2: Import the packs Task 6 approved**

```bash
node tools/build-shapes.mjs scratch_packs/nautical nautical
node tools/build-shapes.mjs scratch_packs/mai_en_fleur mai_en_fleur
```

Import only packs Task 6 marked **usable** or **usable with caveats**. Excluded packs stay out entirely.

- [ ] **Step 3: Build the picker**

Create `app/src/ui/ShapePicker.svelte`:

```svelte
<script>
  import { createEventDispatcher } from "svelte";
  import { listPacks, listShapes } from "../lib/shapes.js";

  // Element-scoped shape chooser. Same patch convention as TextStep and
  // ImagePanel: selections dispatch upward, this component owns no project
  // state of its own.
  export let element;
  const d = createEventDispatcher();

  let query = "";

  // Flatten every pack's shapes into one searchable list. Labels are authored
  // at import time; the underlying glyph letter is never shown, because
  // nobody should have to learn that a star lives under "k".
  $: allShapes = listPacks().flatMap((pack) =>
    listShapes(pack.id).map((s) => ({ ...s, packId: pack.id, packName: pack.name }))
  );

  $: filtered = query.trim()
    ? allShapes.filter((s) => {
        const q = query.trim().toLowerCase();
        return s.label.toLowerCase().includes(q) || s.packName.toLowerCase().includes(q);
      })
    : allShapes;

  function pick(s) {
    d("elupdate", { id: element.id, patch: { packId: s.packId, shapeId: s.id } });
  }
</script>

<label class="fieldlabel" for="shapesearch">Find a shape</label>
<input id="shapesearch" class="search" type="search" bind:value={query} placeholder="star, flower, anchor…" />

{#if filtered.length === 0}
  <p class="hint">No shapes match “{query}”.</p>
{:else}
  <div class="shapegrid">
    {#each filtered as s (s.packId + "/" + s.id)}
      <button
        type="button"
        class="shapetile"
        class:selected={element.packId === s.packId && element.shapeId === s.id}
        title={s.label + " · " + s.packName}
        on:click={() => pick(s)}
      >
        <img src={s.preview} alt="" width="48" height="48" />
        <span class="shapelabel">{s.label}</span>
      </button>
    {/each}
  </div>
{/if}

<style>
  /* In-flow, NOT a popover: Slices 7 and 8 both hit popovers clipping inside
     the scrollable .panel-body. Do not reintroduce that. */
  .search {
    width: 100%;
    padding: 0.5rem 0.6rem;
    border: 1px solid var(--line);
    border-radius: var(--radius-s);
    background: var(--surface);
    color: var(--ink);
    font-size: var(--fs-s);
  }
  .shapegrid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(72px, 1fr));
    gap: 0.5rem;
    margin-top: 0.6rem;
  }
  .shapetile {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
    padding: 0.4rem 0.2rem;
    border: 1px solid var(--line);
    border-radius: var(--radius-s);
    background: var(--surface);
    color: var(--ink);
    cursor: pointer;
  }
  .shapetile.selected {
    border-color: var(--accent);
    box-shadow: 0 0 0 1px var(--accent);
  }
  .shapelabel {
    font-size: var(--fs-xs);
    text-align: center;
    line-height: 1.2;
  }
</style>
```

Do **not** add `outline: none` anywhere. Slice 8 removed every such rule and a follow-up review round still caught one that survived the first pass; the global `:focus-visible` in `theme.css` must keep working.

- [ ] **Step 4: Add the entry point**

`app/src/ui/ContentStep.svelte` has its add-element buttons at lines 113-116 and its selected-element switch at line 124. Add the third button:

```svelte
<div class="eladd-row">
  <button type="button" class="eladd" on:click={() => d("addelement", "text")}>+ Text</button>
  <button type="button" class="eladd" on:click={() => d("addelement", "image")}>+ Image</button>
  <button type="button" class="eladd" on:click={() => d("addelement", "shape")}>+ Shape</button>
</div>
```

Extend `summarize` (line 44) so shape rows read sensibly in the element list:

```js
  function summarize(element) {
    if (element.type === "text") {
      const t = (element.text || "").trim();
      return t ? `"${truncate(t, 18)}"` : "Text · empty";
    }
    if (element.type === "shape") {
      return element.shapeId ? "Shape · " + element.shapeId : "Shape · none picked";
    }
    const n = element.nColors || 0;
    // ...existing image summary unchanged
  }
```

Add the shape branch to the keyed selection block at line 124, before the image branch:

```svelte
{#key el.id}
  {#if el.type === "shape"}
    <ShapePicker element={el} on:elupdate />
  {:else if el.type === "image"}
    <!-- existing ImagePanel usage unchanged -->
```

Import it alongside the other panels: `import ShapePicker from "./ShapePicker.svelte";`

The existing `SizePanel` and thread-color controls already key off the selected element, so shape sizing and recoloring work without further change.

- [ ] **Step 5: Run all tests**

```bash
node --test && cd app && npm test
```
Expected: both green.

- [ ] **Step 6: Verify end to end in the browser**

Confirm: `+ Shape` inserts an element; the grid shows labelled thumbnails with no glyph letters visible; picking a shape generates stitches; the shape drags, resizes, and recolors like any other element; a DST downloads and decodes.

- [ ] **Step 7: Update the docs**

- `README.md` — document SVG upload and the shape picker; note that stroke-only SVGs and live text are not supported, and that cross-stitch and pattern fills do not reproduce.
- `COOKBOOK.md` — record that `svgpath.js`/`svgimport.js` are the vector path, that the pictogram investigation found packs are fill-based (with the numbers), and that `ENGINE_FILES` lives in three places that must stay in sync.

- [ ] **Step 8: Commit**

```bash
git add tools/build-shapes.mjs tools/shape-labels.json app/src/ui/ShapePicker.svelte app/src/ui/ContentStep.svelte app/src/lib/shapes.js README.md COOKBOOK.md
git commit -m "feat: shape pack importer and shape picker UI"
```

---

## Definition of done

- [ ] `node --test` green (expect ~218).
- [ ] `cd app && npm test` green (expect ~195).
- [ ] A customer vector logo imports with exact edges and no flatten step.
- [ ] Shape packs render acceptably, or are excluded with the reason recorded in Task 6's findings note.
- [ ] `+ Shape` inserts a shape that drags, resizes, recolors and exports.
- [ ] Live text, stroke-only art, and missing viewBox all produce clear messages rather than silent empty designs.
- [ ] Existing font and image output is unchanged — no stitch-math edits are in scope, so any diff is a regression.
- [ ] Shape pack licenses are carried into the pack records, per the licensing decision.
