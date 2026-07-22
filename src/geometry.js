(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  // 8-connected neighbor offsets used for connected-component labeling.
  const CONN8 = [
    [1, 0], [1, -1], [0, -1], [-1, -1],
    [-1, 0], [-1, 1], [0, 1], [1, 1],
  ];

  // Label connected foreground components with 8-CONNECTIVITY (diagonal
  // touches join components). Returns one entry per blob:
  //   { seed: [x, y], mask: Uint8Array }
  // where `seed` is the top-left-most pixel found during the row-major scan
  // (so the cell directly above it is guaranteed background within the blob)
  // and `mask` is a PER-BLOB mask containing ONLY that blob's pixels.
  //
  // Labeling and tracing MUST agree on connectivity. We label with
  // 8-connectivity here and trace each blob against its own isolated mask, so
  // the edge tracer can never wander onto a different component's pixels
  // (the root cause of the old 4-connected-label / 8-connected-trace bug).
  function labelBlobs(mask, w, h) {
    const visited = new Uint8Array(w * h);
    const blobs = [];
    const stack = [];
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const idx = y * w + x;
        if (mask[idx] !== 1 || visited[idx]) continue;
        // New blob found at its first (top-left-most) pixel.
        const blobMask = new Uint8Array(w * h);
        stack.length = 0;
        stack.push(idx);
        visited[idx] = 1;
        blobMask[idx] = 1;
        while (stack.length) {
          const cur = stack.pop();
          const cx = cur % w;
          const cy = (cur - cx) / w;
          for (const [dx, dy] of CONN8) {
            const nx = cx + dx, ny = cy + dy;
            if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
            const nidx = ny * w + nx;
            if (visited[nidx] || mask[nidx] !== 1) continue;
            visited[nidx] = 1;
            blobMask[nidx] = 1;
            stack.push(nidx);
          }
        }
        blobs.push({ seed: [x, y], mask: blobMask });
      }
    }
    return blobs;
  }

  // Directed-edge headings: 0=E, 1=S, 2=W, 3=N.
  const EDGE_DV = [[1, 0], [0, 1], [-1, 0], [0, -1]];

  function fgAt(mask, w, h, x, y) {
    if (x < 0 || y < 0 || x >= w || y >= h) return 0;
    return mask[y * w + x];
  }

  // For a directed edge leaving vertex (x, y) with heading `d`, return the
  // grid cells immediately to its right and left. Cells are addressed by
  // their top-left corner; the vertex grid runs 0..w, 0..h.
  function edgeCells(x, y, d) {
    switch (d) {
      case 0: return [[x, y], [x, y - 1]];         // E: right below, left above
      case 1: return [[x - 1, y], [x, y]];         // S: right west, left east
      case 2: return [[x - 1, y - 1], [x - 1, y]]; // W: right north, left south
      default: return [[x, y - 1], [x - 1, y - 1]];// N: right east, left west
    }
  }

  // A directed edge is on the clockwise outer boundary when the cell to its
  // right is foreground and the cell to its left is background.
  function isBoundaryEdge(mask, w, h, x, y, d) {
    const [r, l] = edgeCells(x, y, d);
    return fgAt(mask, w, h, r[0], r[1]) === 1 && fgAt(mask, w, h, l[0], l[1]) !== 1;
  }

  // Trace the outer contour of a single blob by following pixel OUTER EDGES
  // (the cracks between foreground and background cells) rather than pixel
  // centers. An n*m solid blob yields a polygon whose `polygonArea` is exactly
  // n*m, so area is strictly monotonic in pixel count and a lone pixel is a
  // unit square (area 1) — no singleton special-case needed.
  //
  // Start at the seed's top-left corner heading east: the seed is
  // top-left-most so its top edge is a boundary edge. At each vertex we prefer
  // to turn LEFT, then go straight, then turn RIGHT, then reverse; preferring
  // left keeps diagonally-adjacent foreground cells connected, matching the
  // 8-connectivity used for labeling.
  //
  // Termination is position-AND-heading: we stop only when we re-enter the
  // start vertex about to repeat the start heading. For this edge tracer the
  // (vertex, heading) state fully determines the next step, so returning to it
  // provably closes exactly one loop — there is no pinch-point ambiguity as
  // there was with the old center tracer, so no separate stopping variable is
  // needed.
  const TURN_PREFERENCE = [3, 0, 1, 2]; // left, straight, right, back (relative)

  function traceBlobEdges(mask, w, h, seedX, seedY) {
    const points = [];
    let x = seedX, y = seedY, d = 0;
    const startX = x, startY = y, startD = d;
    const maxIterations = (w + 1) * (h + 1) * 4 + 16;
    let iterations = 0;

    while (true) {
      points.push({ x, y });
      const [dx, dy] = EDGE_DV[d];
      x += dx; y += dy;

      let nextD = -1;
      for (const rel of TURN_PREFERENCE) {
        const cand = (d + rel) % 4;
        if (isBoundaryEdge(mask, w, h, x, y, cand)) { nextD = cand; break; }
      }
      if (nextD === -1) break; // no continuation (should not happen for a valid blob)
      d = nextD;

      if (x === startX && y === startY && d === startD) break;
      if (++iterations > maxIterations) break; // safety guard
    }

    return points;
  }

  function traceContours(mask, w, h) {
    const blobs = labelBlobs(mask, w, h);
    const contours = [];
    for (const { seed, mask: blobMask } of blobs) {
      contours.push(traceBlobEdges(blobMask, w, h, seed[0], seed[1]));
    }
    return contours;
  }

  // 4-connected neighbor offsets used for BACKGROUND labeling. Holes are found
  // via background connectivity, and 4-connectivity is the correct dual of the
  // 8-connectivity used for foreground blobs: a background region that is only
  // diagonally "pinched" by foreground is still considered enclosed, matching
  // the way the 8-connected foreground closes the loop around it.
  const CONN4 = [[1, 0], [-1, 0], [0, 1], [0, -1]];

  // Hole-aware region tracing. Returns one entry per 8-connected foreground
  // blob: { outer, holes } where `outer` is the blob's outer boundary ring
  // (identical to what traceContours produces) and `holes` is an array of
  // boundary rings, one per background region FULLY ENCLOSED by that blob.
  //
  // A background region is a hole of blob B iff it is 4-connected background,
  // does NOT touch the image border, and is enclosed by B. Enclosure is decided
  // by the foreground pixel directly ABOVE the hole's top-left-most pixel: that
  // pixel is guaranteed to exist (an enclosed region cannot reach row 0) and to
  // be foreground (a background pixel there would be 4-connected into the same
  // region), and it belongs to the enclosing blob's inner boundary.
  //
  // Each hole ring is traced with the SAME crack/edge tracer used for outer
  // boundaries, run on an isolated mask of just that background region, so the
  // hole ring shares the outer ring's coordinate convention and is directly
  // usable by polygonArea and tatamiFill (even-odd fill).
  //
  // Limitation: only the OUTER boundary of each enclosed background region is
  // returned as the hole ring. For deeply nested topology (a blob inside a
  // hole inside a blob) each blob is still traced independently and its own
  // outer ring plus its immediate holes yield a correct even-odd fill; a
  // foreground island sitting inside a hole is reported as its own separate
  // region rather than being subtracted from the hole ring.
  function traceRegions(mask, w, h) {
    const blobs = labelBlobs(mask, w, h);
    const regions = blobs.map(({ seed, mask: blobMask }) => ({
      outer: traceBlobEdges(blobMask, w, h, seed[0], seed[1]),
      holes: [],
    }));

    // Label BACKGROUND pixels with 4-connectivity via flood fill. The first
    // pixel reached for each component (row-major scan) is its top-left-most.
    const bgVisited = new Uint8Array(w * h);
    const stack = [];
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const idx = y * w + x;
        if (mask[idx] === 1 || bgVisited[idx]) continue;

        const seedX = x, seedY = y;
        let touchesBorder = false;
        const pixels = [];
        stack.length = 0;
        stack.push(idx);
        bgVisited[idx] = 1;
        while (stack.length) {
          const cur = stack.pop();
          const cx = cur % w;
          const cy = (cur - cx) / w;
          if (cx === 0 || cy === 0 || cx === w - 1 || cy === h - 1) touchesBorder = true;
          pixels.push(cur);
          for (const [dx, dy] of CONN4) {
            const nx = cx + dx, ny = cy + dy;
            if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
            const nidx = ny * w + nx;
            if (bgVisited[nidx] || mask[nidx] === 1) continue;
            bgVisited[nidx] = 1;
            stack.push(nidx);
          }
        }

        // A background component touching the border is the "outside", not a hole.
        if (touchesBorder) continue;

        // Enclosing blob = owner of the foreground pixel directly above the
        // top-left-most hole pixel. seedY >= 1 here (a row-0 pixel would have
        // set touchesBorder) and that pixel is guaranteed foreground.
        const aboveIdx = (seedY - 1) * w + seedX;
        const blobIndex = blobs.findIndex((b) => b.mask[aboveIdx] === 1);
        if (blobIndex === -1) continue; // defensive; should not happen

        // Trace the hole boundary as the outer edge of an isolated mask of just
        // this background region, reusing the same crack/edge tracer.
        const holeMask = new Uint8Array(w * h);
        for (const p of pixels) holeMask[p] = 1;
        const ring = traceBlobEdges(holeMask, w, h, seedX, seedY);
        if (ring.length >= 4 && polygonArea(ring) > 0) {
          regions[blobIndex].holes.push(ring);
        }
      }
    }

    return regions;
  }

  function perpendicularDistance(pt, a, b) {
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const lenSq = dx * dx + dy * dy;
    if (lenSq === 0) {
      const ddx = pt.x - a.x, ddy = pt.y - a.y;
      return Math.sqrt(ddx * ddx + ddy * ddy);
    }
    const num = Math.abs(dy * pt.x - dx * pt.y + b.x * a.y - b.y * a.x);
    return num / Math.sqrt(lenSq);
  }

  function douglasPeucker(points, tol) {
    if (points.length < 3) return points.slice();
    let maxDist = -1;
    let idx = 0;
    const a = points[0];
    const b = points[points.length - 1];
    for (let i = 1; i < points.length - 1; i++) {
      const d = perpendicularDistance(points[i], a, b);
      if (d > maxDist) { maxDist = d; idx = i; }
    }
    if (maxDist > tol) {
      const left = douglasPeucker(points.slice(0, idx + 1), tol);
      const right = douglasPeucker(points.slice(idx), tol);
      return left.slice(0, -1).concat(right);
    }
    return [a, b];
  }

  function simplify(points, tol) {
    if (!points || points.length < 3) return (points || []).slice();
    return douglasPeucker(points, tol);
  }

  function polygonArea(points) {
    if (!points || points.length < 3) return 0;
    let sum = 0;
    const n = points.length;
    for (let i = 0; i < n; i++) {
      const p1 = points[i];
      const p2 = points[(i + 1) % n];
      sum += p1.x * p2.y - p2.x * p1.y;
    }
    return Math.abs(sum) / 2;
  }

  return {
    traceContours,
    traceRegions,
    simplify,
    polygonArea,
  };
});
