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

  function parsePathData(d, opts) {
    const tolerance = (opts && opts.tolerance != null) ? opts.tolerance : 0.2;
    const subpaths = [];
    let current = null;   // { points, closed }
    let cx = 0, cy = 0;   // current point
    let sx = 0, sy = 0;   // start of current subpath

    // Reflection state for the smooth curve commands S and T. `prevCubicC2`
    // is the second control point of the last C/S; `prevQuadC` is the control
    // point of the last Q/T. Each is null when the previous command was not
    // of the matching curve type, in which case the spec says to use the
    // current point.
    let prevCubicC2 = null;
    let prevQuadC = null;

    function startSubpath(x, y) {
      current = { points: [{ x, y }], closed: false };
      subpaths.push(current);
      sx = x; sy = y;
    }
    function lineTo(x, y) {
      if (!current) startSubpath(cx, cy);
      current.points.push({ x, y });
    }
    function curveTo(p1, p2, p3) {
      if (!current) startSubpath(cx, cy);
      flattenCubic({ x: cx, y: cy }, p1, p2, p3, tolerance, current.points, 0);
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

        if (effective === "M" || effective === "L" || effective === "H" || effective === "V") {
          prevCubicC2 = null; prevQuadC = null;
        }

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
        } else if (effective === "C" || effective === "S") {
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
        // A is added in Task 3.
      }
    }
    return subpaths;
  }

  return { parsePathData };
});
