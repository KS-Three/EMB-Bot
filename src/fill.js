(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const EPS = 1e-9;

  function rotate(p, cos, sin) {
    return { x: p.x * cos - p.y * sin, y: p.x * sin + p.y * cos };
  }

  // Tatami scan-line fill across one or more polygons.
  // polygons: Array<Array<{x,y}>>; even-odd parity across ALL polygons (holes respected).
  // opts: { rowSpacing, angleDeg=0, maxStitch }
  function tatamiFill(polygons, opts) {
    const rowSpacing = opts.rowSpacing;
    const angleDeg = opts.angleDeg || 0;
    const maxStitch = opts.maxStitch;
    const theta = (angleDeg * Math.PI) / 180;

    // Rotate all points by -angleDeg about the origin so scanlines are horizontal.
    const cosN = Math.cos(-theta);
    const sinN = Math.sin(-theta);
    // Rotate back by +angleDeg.
    const cosP = Math.cos(theta);
    const sinP = Math.sin(theta);

    // Collect rotated edges and compute bbox.
    const edges = [];
    let minY = Infinity;
    let maxY = -Infinity;
    for (const poly of polygons) {
      const n = poly.length;
      if (n < 2) continue;
      const rp = poly.map((p) => rotate(p, cosN, sinN));
      for (const p of rp) {
        if (p.y < minY) minY = p.y;
        if (p.y > maxY) maxY = p.y;
      }
      for (let i = 0; i < n; i++) {
        const a = rp[i];
        const b = rp[(i + 1) % n];
        edges.push([a, b]);
      }
    }

    if (!isFinite(minY) || !isFinite(maxY)) return [];

    // Collect ordered span endpoints (in rotated space) following the
    // boustrophedon path across all rows.
    const key = [];
    let rowIndex = 0;
    for (let y = minY; y <= maxY + EPS; y += rowSpacing) {
      // Gather x-intersections with all edges using the half-open rule.
      const xs = [];
      for (const [a, b] of edges) {
        const y0 = a.y;
        const y1 = b.y;
        if (y0 === y1) continue; // horizontal edge: skip (parity preserved)
        // Half-open: count edge if min(y0,y1) <= y < max(y0,y1).
        const lo = Math.min(y0, y1);
        const hi = Math.max(y0, y1);
        if (y >= lo && y < hi) {
          const t = (y - y0) / (y1 - y0);
          xs.push(a.x + t * (b.x - a.x));
        }
      }
      if (xs.length >= 2) {
        xs.sort((p, q) => p - q);
        // Pair spans (even-odd).
        const spans = [];
        for (let i = 0; i + 1 < xs.length; i += 2) {
          spans.push([xs[i], xs[i + 1]]);
        }
        // Boustrophedon: reverse span order and endpoints on odd rows.
        const rev = rowIndex % 2 === 1;
        const ordered = rev ? spans.slice().reverse() : spans;
        for (const span of ordered) {
          const start = rev ? span[1] : span[0];
          const end = rev ? span[0] : span[1];
          key.push({ x: start, y });
          key.push({ x: end, y });
        }
      }
      rowIndex++;
    }

    // Densify: ensure no two consecutive points exceed maxStitch (this also
    // splits the inter-row travel stitches). Then rotate back by +angleDeg.
    const out = [];
    if (key.length === 0) return out;
    out.push(rotate(key[0], cosP, sinP));
    for (let i = 1; i < key.length; i++) {
      const a = key[i - 1];
      const b = key[i];
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.hypot(dx, dy);
      if (maxStitch && maxStitch > 0 && dist > maxStitch) {
        const steps = Math.ceil(dist / maxStitch);
        for (let s = 1; s < steps; s++) {
          const t = s / steps;
          out.push(rotate({ x: a.x + dx * t, y: a.y + dy * t }, cosP, sinP));
        }
      }
      out.push(rotate(b, cosP, sinP));
    }
    return out;
  }

  // Walk the polygon perimeter emitting a point every stitchLen of arc length.
  function runningOutline(polygon, opts) {
    const stitchLen = opts.stitchLen;
    const out = [];
    const n = polygon.length;
    if (n === 0) return out;
    if (n === 1) return [{ x: polygon[0].x, y: polygon[0].y }];

    out.push({ x: polygon[0].x, y: polygon[0].y });
    let carry = 0; // distance accumulated since last emitted point

    for (let i = 0; i < n; i++) {
      const a = polygon[i];
      const b = polygon[(i + 1) % n]; // closed loop back to start
      const segDx = b.x - a.x;
      const segDy = b.y - a.y;
      const segLen = Math.hypot(segDx, segDy);
      if (segLen <= EPS) continue;
      const ux = segDx / segLen;
      const uy = segDy / segLen;
      // Position along this segment (from a) of the next point to emit.
      let dist = stitchLen - carry;
      while (dist <= segLen + EPS) {
        const d = Math.min(dist, segLen);
        out.push({ x: a.x + ux * d, y: a.y + uy * d });
        dist += stitchLen;
      }
      carry = segLen - (dist - stitchLen);
    }
    return out;
  }

  return {
    tatamiFill,
    runningOutline,
  };
});
