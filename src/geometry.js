(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  // 8-connected (Moore) neighbor offsets, starting from "east" and going
  // counter-clockwise: E, NE, N, NW, W, SW, S, SE.
  const NEIGHBORS = [
    [1, 0], [1, -1], [0, -1], [-1, -1],
    [-1, 0], [-1, 1], [0, 1], [1, 1],
  ];

  function at(mask, w, h, x, y) {
    if (x < 0 || y < 0 || x >= w || y >= h) return 0;
    return mask[y * w + x];
  }

  // Find connected foreground components via 4-connected flood fill and
  // return, for each, one interior pixel (the top-left-most pixel found
  // during the row-major scan, which is guaranteed to be a boundary pixel
  // with no foreground neighbor above or to its left within the blob).
  function findBlobSeeds(mask, w, h) {
    const visited = new Uint8Array(w * h);
    const seeds = [];
    const stack = [];
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const idx = y * w + x;
        if (mask[idx] !== 1 || visited[idx]) continue;
        // New blob found at its first (top-left-most) pixel.
        seeds.push([x, y]);
        stack.length = 0;
        stack.push(idx);
        visited[idx] = 1;
        while (stack.length) {
          const cur = stack.pop();
          const cx = cur % w;
          const cy = (cur - cx) / w;
          const dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]];
          for (const [dx, dy] of dirs) {
            const nx = cx + dx, ny = cy + dy;
            if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
            const nidx = ny * w + nx;
            if (visited[nidx] || mask[nidx] !== 1) continue;
            visited[nidx] = 1;
            stack.push(nidx);
          }
        }
      }
    }
    return seeds;
  }

  // Moore-neighbor boundary tracing (Suzuki/Abe-style single-blob variant)
  // starting from a known top-left-most boundary pixel of the blob.
  function traceBoundary(mask, w, h, startX, startY) {
    const points = [{ x: startX, y: startY }];

    // The seed is top-left-most, so the pixel to its "west" (index 4 in
    // NEIGHBORS, offset (-1,0)) is guaranteed background. Begin the search
    // for the next boundary pixel from that direction.
    let curX = startX, curY = startY;
    let backtrackDir = 4; // direction pointing to a known background pixel

    // Special case: isolated single pixel with no foreground neighbors at
    // all — return a degenerate closed "polygon" around it so callers get
    // a valid (if minimal) contour rather than looping forever.
    let hasNeighbor = false;
    for (const [dx, dy] of NEIGHBORS) {
      if (at(mask, w, h, curX + dx, curY + dy) === 1) { hasNeighbor = true; break; }
    }
    if (!hasNeighbor) {
      return [
        { x: startX, y: startY },
        { x: startX + 1, y: startY },
        { x: startX + 1, y: startY + 1 },
        { x: startX, y: startY + 1 },
      ];
    }

    const maxIterations = w * h * 8 + 64;
    let iterations = 0;
    const firstX = startX, firstY = startY;
    let firstStepBackDir = -1;

    while (iterations++ < maxIterations) {
      let found = false;
      let nextDir = -1, nextX = 0, nextY = 0;
      // Search neighbors starting just after the backtrack direction,
      // going clockwise in our (counter-clockwise-indexed) array, i.e.
      // decrementing index, wrapping mod 8.
      for (let k = 1; k <= 8; k++) {
        const dir = (backtrackDir + k) % 8;
        const [dx, dy] = NEIGHBORS[dir];
        const nx = curX + dx, ny = curY + dy;
        if (at(mask, w, h, nx, ny) === 1) {
          nextDir = dir; nextX = nx; nextY = ny; found = true;
          break;
        }
      }

      if (!found) {
        // Fully isolated pixel (shouldn't happen given hasNeighbor check,
        // but guard against it anyway).
        break;
      }

      if (iterations === 1) {
        firstStepBackDir = (nextDir + 4) % 8;
      }

      // Stop condition: we've returned to the starting pixel via the same
      // entry direction as the very first step (standard Moore tracing
      // termination, Jacob's stopping criterion).
      if (nextX === firstX && nextY === firstY) {
        break;
      }

      points.push({ x: nextX, y: nextY });
      curX = nextX; curY = nextY;
      // New backtrack direction: direction we came from, relative to the
      // new current pixel.
      backtrackDir = (nextDir + 4) % 8;

      if (curX === firstX && curY === firstY) break;
    }

    return points;
  }

  function traceContours(mask, w, h) {
    const seeds = findBlobSeeds(mask, w, h);
    const contours = [];
    for (const [sx, sy] of seeds) {
      contours.push(traceBoundary(mask, w, h, sx, sy));
    }
    return contours;
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
    simplify,
    polygonArea,
  };
});
