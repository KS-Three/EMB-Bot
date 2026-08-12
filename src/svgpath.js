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
  const NUM_STICKY_RE = /[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?/y;
  const CMD_RE = /[MmLlHhVvCcSsQqTtAaZz]/;

  // Lexes the argument run following one command letter. Arc commands need
  // their own scanner because the two flag arguments are single characters
  // that minifiers write with no separator before the next number
  // ("a1.5 1.5 0 011.06.44" is rx ry rot 0 1 1.06 .44) — a greedy number
  // regex would read "011.06" as one number and shift every later argument.
  function lexArgs(chunk, isArc) {
    const out = [];
    let i = 0;
    while (i < chunk.length) {
      const ch = chunk[i];
      if (ch === " " || ch === "," || ch === "\t" || ch === "\n" || ch === "\r") { i++; continue; }
      if (isArc && (out.length % 7 === 3 || out.length % 7 === 4)) {
        if (ch === "0" || ch === "1") { out.push(Number(ch)); i++; continue; }
        break; // malformed flag; stop consuming this chunk
      }
      NUM_STICKY_RE.lastIndex = i;
      const m = NUM_STICKY_RE.exec(chunk);
      if (!m) { i++; continue; } // stray character; skip it
      out.push(Number(m[0]));
      i = NUM_STICKY_RE.lastIndex;
    }
    return out;
  }

  function tokenize(d) {
    const out = [];
    let i = 0;
    while (i < d.length) {
      const ch = d[i];
      if (CMD_RE.test(ch)) {
        // Collect every argument up to the next command letter.
        let j = i + 1;
        while (j < d.length && !CMD_RE.test(d[j])) j++;
        const chunk = d.slice(i + 1, j);
        const args = lexArgs(chunk, ch === "A" || ch === "a");
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

  // Hard ceiling on the adaptive subdivision. Flatness converges long before
  // this for any sane tolerance; the cap is what keeps tolerance -> 0 (or
  // garbage geometry) degrading gracefully instead of exploding: one curve
  // can never emit more than 2^MAX_DEPTH segments (~65k).
  const MAX_DEPTH = 16;

  // Recursive de Casteljau flattening. Emits points for everything AFTER p0
  // (the caller has already emitted the start point).
  //
  // Flatness test: let L(t) = (1-t)p0 + t*p3 be the chord parameterized
  // linearly. Subtracting it from the Bezier collapses to
  //   B(t) - L(t) = 3u²t·e1 + 3ut²·e2,   u = 1-t,
  //   e1 = p1 - (2p0+p3)/3,  e2 = p2 - (p0+2p3)/3
  // (e1/e2 are how far each control point sits from where it would sit if
  // the curve were exactly the chord). Since 3u²t + 3ut² = 3ut ≤ 3/4 on
  // [0,1], the deviation is bounded by (3/4)·max(|e1|,|e2|); requiring that
  // to be ≤ tolerance GUARANTEES the emitted polyline stays within tolerance
  // of the true curve. Using 3e1/3e2 avoids the divisions, so the test is
  // max(|3e1|²,|3e2|²) ≤ 16·tolerance².
  //
  // This replaces the earlier perpendicular-distance-to-chord test, which
  // had three holes: an extra ×16 borrowed from THIS criterion made it 4×
  // looser than intended (real deviation up to 3× tolerance); measuring only
  // the perpendicular component accepted control points collinear with but
  // beyond the chord (overshoot never subdivided); and a degenerate chord
  // (p0 == p3, a loop) zeroed both sides so any loop passed at depth 0. The
  // full 2D offset norm has none of those blind spots.
  function flattenCubic(p0, p1, p2, p3, tolerance, out, depth) {
    const e1x = 3 * p1.x - 2 * p0.x - p3.x, e1y = 3 * p1.y - 2 * p0.y - p3.y;
    const e2x = 3 * p2.x - p0.x - 2 * p3.x, e2y = 3 * p2.y - p0.y - 2 * p3.y;
    const err = Math.max(e1x * e1x + e1y * e1y, e2x * e2x + e2y * e2y);
    if (err <= 16 * tolerance * tolerance || depth >= MAX_DEPTH) {
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

  // Endpoint -> center parameterization, per SVG 1.1 appendix F.6.5 (with
  // the F.6.6 out-of-range radius correction), then direct parametric
  // sampling. `out` receives every point after the start point.
  //
  // Step-size guarantee: the ellipse is the unit circle scaled by
  // diag(rx, ry) then rotated; a linear map scales every distance by at most
  // its largest singular value, max(rx, ry). The sagitta of a unit-circle
  // arc spanning angle a is 1 - cos(a/2), so a parameter step of angle a
  // keeps the chord within max(rx, ry) * (1 - cos(a/2)) of the ellipse —
  // bound that by the tolerance and solve for a. Tolerance 0 (or below the
  // fallback) degrades to fixed 1-degree steps rather than diverging.
  function flattenArc(x1, y1, rx, ry, xAxisRotDeg, largeArc, sweep, x2, y2, tolerance, out) {
    if (x1 === x2 && y1 === y2) return;            // spec: arc is skipped entirely
    if (rx === 0 || ry === 0) { out.push({ x: x2, y: y2 }); return; } // spec: treat as lineto

    rx = Math.abs(rx); ry = Math.abs(ry);
    const phi = (xAxisRotDeg * Math.PI) / 180;
    const cosPhi = Math.cos(phi), sinPhi = Math.sin(phi);

    // Step 1: translate so the chord midpoint is the origin, rotate by -phi.
    const dx2 = (x1 - x2) / 2, dy2 = (y1 - y2) / 2;
    const x1p = cosPhi * dx2 + sinPhi * dy2;
    const y1p = -sinPhi * dx2 + cosPhi * dy2;

    // Step 2: scale up out-of-range radii until the endpoints fit (F.6.6).
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

    // Step 5: start angle and sweep angle (F.6.5.5 / F.6.5.6).
    const ux = (x1p - cxp) / rx, uy = (y1p - cyp) / ry;
    const vx = (-x1p - cxp) / rx, vy = (-y1p - cyp) / ry;
    const theta1 = Math.atan2(uy, ux);
    let dTheta = Math.atan2(ux * vy - uy * vx, ux * vx + uy * vy);
    if (!sweep && dTheta > 0) dTheta -= 2 * Math.PI;
    if (sweep && dTheta < 0) dTheta += 2 * Math.PI;

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
    // hole/containment grouping downstream would misread as an open ring.
    const last = out[out.length - 1];
    if (last) { last.x = x2; last.y = y2; }
  }

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
        } else if (effective === "A") {
          const endX = relative ? cx + g[5] : g[5];
          const endY = relative ? cy + g[6] : g[6];
          if (!current) startSubpath(cx, cy);
          flattenArc(cx, cy, g[0], g[1], g[2], g[3] !== 0, g[4] !== 0,
            endX, endY, tolerance, current.points);
          prevCubicC2 = null; prevQuadC = null;
          cx = endX; cy = endY;
        }
      }
    }
    return subpaths;
  }

  return { parsePathData };
});
