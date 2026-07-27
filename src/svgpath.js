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
