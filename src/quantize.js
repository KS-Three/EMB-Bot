(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const TRANSPARENT_INDEX = 255;
  const KMEANS_ITERATIONS = 10;
  const MERGE_DIST = 16; // Euclidean RGB distance below which palette entries merge.

  // Build a box (list of pixel positions + cached channel ranges) from an array of
  // {r,g,b} opaque pixel samples referenced by index into `pixels`.
  function makeBox(pixelIdxs, pixels) {
    let rMin = 255, rMax = 0, gMin = 255, gMax = 0, bMin = 255, bMax = 0;
    for (const idx of pixelIdxs) {
      const p = pixels[idx];
      if (p.r < rMin) rMin = p.r;
      if (p.r > rMax) rMax = p.r;
      if (p.g < gMin) gMin = p.g;
      if (p.g > gMax) gMax = p.g;
      if (p.b < bMin) bMin = p.b;
      if (p.b > bMax) bMax = p.b;
    }
    return { idxs: pixelIdxs, rMin, rMax, gMin, gMax, bMin, bMax };
  }

  function widestChannel(box) {
    const rRange = box.rMax - box.rMin;
    const gRange = box.gMax - box.gMin;
    const bRange = box.bMax - box.bMin;
    if (rRange >= gRange && rRange >= bRange) return "r";
    if (gRange >= rRange && gRange >= bRange) return "g";
    return "b";
  }

  function splitBox(box, pixels) {
    const channel = widestChannel(box);
    const sorted = box.idxs.slice().sort((a, b) => pixels[a][channel] - pixels[b][channel]);
    const mid = Math.floor(sorted.length / 2);
    const left = sorted.slice(0, mid);
    const right = sorted.slice(mid);
    return [makeBox(left, pixels), makeBox(right, pixels)];
  }

  function boxRange(box) {
    return Math.max(box.rMax - box.rMin, box.gMax - box.gMin, box.bMax - box.bMin);
  }

  function averageColor(box, pixels) {
    let rSum = 0, gSum = 0, bSum = 0;
    for (const idx of box.idxs) {
      const p = pixels[idx];
      rSum += p.r; gSum += p.g; bSum += p.b;
    }
    const count = box.idxs.length;
    return [
      Math.round(rSum / count),
      Math.round(gSum / count),
      Math.round(bSum / count),
    ];
  }

  // Lloyd's k-means refinement of an initial palette against the opaque pixel
  // set. Assigns each pixel to its nearest centroid (squared-Euclidean RGB),
  // recomputes each centroid as the mean of its assigned pixels, and drops any
  // centroid that ends an iteration with zero assigned pixels (no phantom
  // entries). Returns { centroids: [[r,g,b],...], counts: [...] } where counts
  // is the population assigned to each surviving centroid.
  function refineKMeans(seed, pixels, iterations) {
    let centroids = seed.map((c) => c.slice());
    const assign = new Int32Array(pixels.length).fill(-1);
    let counts = new Array(centroids.length).fill(0);

    for (let iter = 0; iter < iterations; iter++) {
      let changed = false;

      // Assignment step.
      for (let j = 0; j < pixels.length; j++) {
        const p = pixels[j];
        let best = 0, bestDist = Infinity;
        for (let k = 0; k < centroids.length; k++) {
          const c = centroids[k];
          const dr = p.r - c[0], dg = p.g - c[1], db = p.b - c[2];
          const d = dr * dr + dg * dg + db * db;
          if (d < bestDist) { bestDist = d; best = k; }
        }
        if (assign[j] !== best) { assign[j] = best; changed = true; }
      }

      // Update step: mean of assigned pixels; drop empty clusters.
      const sums = centroids.map(() => [0, 0, 0]);
      counts = new Array(centroids.length).fill(0);
      for (let j = 0; j < pixels.length; j++) {
        const k = assign[j];
        const p = pixels[j];
        sums[k][0] += p.r; sums[k][1] += p.g; sums[k][2] += p.b;
        counts[k]++;
      }
      const nextCentroids = [];
      const nextCounts = [];
      const remap = new Array(centroids.length).fill(-1);
      for (let k = 0; k < centroids.length; k++) {
        if (counts[k] === 0) continue; // drop phantom cluster
        remap[k] = nextCentroids.length;
        nextCentroids.push([
          Math.round(sums[k][0] / counts[k]),
          Math.round(sums[k][1] / counts[k]),
          Math.round(sums[k][2] / counts[k]),
        ]);
        nextCounts.push(counts[k]);
      }
      if (nextCentroids.length !== centroids.length) {
        // Cluster indices shifted; remap assignments so the next iteration's
        // change-detection compares against valid indices.
        for (let j = 0; j < pixels.length; j++) assign[j] = remap[assign[j]];
        changed = true;
      }
      centroids = nextCentroids;
      counts = nextCounts;

      if (!changed) break; // converged
    }

    return { centroids, counts };
  }

  // Repeatedly merge the closest pair of centroids whose Euclidean RGB distance
  // is < MERGE_DIST into their population-weighted average, until no pair
  // remains within MERGE_DIST. Collapses duplicate entries that appear when
  // there are fewer true colors than requested.
  function mergeNearDuplicates(centroids, counts) {
    const cents = centroids.map((c) => c.slice());
    const wts = counts.slice();
    for (;;) {
      let bestI = -1, bestJ = -1, bestDist = Infinity;
      for (let i = 0; i < cents.length; i++) {
        for (let j = i + 1; j < cents.length; j++) {
          const dr = cents[i][0] - cents[j][0];
          const dg = cents[i][1] - cents[j][1];
          const db = cents[i][2] - cents[j][2];
          const d = Math.sqrt(dr * dr + dg * dg + db * db);
          if (d < bestDist) { bestDist = d; bestI = i; bestJ = j; }
        }
      }
      if (bestI === -1 || bestDist >= MERGE_DIST) break;
      const wi = wts[bestI], wj = wts[bestJ];
      const w = wi + wj || 1;
      cents[bestI] = [
        Math.round((cents[bestI][0] * wi + cents[bestJ][0] * wj) / w),
        Math.round((cents[bestI][1] * wi + cents[bestJ][1] * wj) / w),
        Math.round((cents[bestI][2] * wi + cents[bestJ][2] * wj) / w),
      ];
      wts[bestI] = w;
      cents.splice(bestJ, 1);
      wts.splice(bestJ, 1);
    }
    return cents;
  }

  function medianCut(rgba, n) {
    const count = Math.floor(rgba.length / 4);
    const indices = new Uint8Array(count).fill(TRANSPARENT_INDEX);

    // Collect opaque pixels (with their original pixel index) as {r,g,b}.
    const pixels = []; // pixels[j] = {r,g,b}, parallel array; opaqueIdxs[j] = original pixel index
    const opaqueOrigIdx = [];
    for (let i = 0; i < count; i++) {
      const off = i * 4;
      const a = rgba[off + 3];
      if (a === 0) continue;
      pixels.push({ r: rgba[off], g: rgba[off + 1], b: rgba[off + 2] });
      opaqueOrigIdx.push(i);
    }

    if (pixels.length === 0) {
      return { palette: [], indices };
    }

    const allIdxs = pixels.map((_, j) => j);
    let boxes = [makeBox(allIdxs, pixels)];

    while (boxes.length < n) {
      // Find the box with the greatest channel range that can still be split
      // (needs at least 2 distinct pixels to split meaningfully).
      let bestIdx = -1;
      let bestRange = -1;
      for (let i = 0; i < boxes.length; i++) {
        const box = boxes[i];
        if (box.idxs.length < 2) continue;
        const range = boxRange(box);
        if (range > bestRange) {
          bestRange = range;
          bestIdx = i;
        }
      }
      if (bestIdx === -1 || bestRange <= 0) break; // nothing left worth splitting

      const box = boxes[bestIdx];
      const [left, right] = splitBox(box, pixels);
      if (left.idxs.length === 0 || right.idxs.length === 0) break;
      boxes.splice(bestIdx, 1, left, right);
    }

    // Median cut only seeds the palette (it balances pixel population rather
    // than separating colors). Refine with k-means so flat, few-color art
    // resolves to its true colors, then merge near-duplicate entries.
    const seed = boxes.map((box) => averageColor(box, pixels));
    const { centroids, counts } = refineKMeans(seed, pixels, KMEANS_ITERATIONS);
    const palette = mergeNearDuplicates(centroids, counts);

    // Assign each opaque pixel to nearest FINAL palette color (Euclidean in RGB).
    for (let j = 0; j < pixels.length; j++) {
      const p = pixels[j];
      let bestPal = 0;
      let bestDist = Infinity;
      for (let k = 0; k < palette.length; k++) {
        const [pr, pg, pb] = palette[k];
        const dr = p.r - pr, dg = p.g - pg, db = p.b - pb;
        const dist = dr * dr + dg * dg + db * db;
        if (dist < bestDist) {
          bestDist = dist;
          bestPal = k;
        }
      }
      indices[opaqueOrigIdx[j]] = bestPal;
    }

    return { palette, indices };
  }

  function knockoutBackground(rgba, w, h, opts) {
    const options = opts || {};
    const tolerance = options.tolerance === undefined ? 24 : options.tolerance;
    const sampleCorner = options.sampleCorner === undefined ? true : options.sampleCorner;

    const out = new Uint8ClampedArray(rgba.length);
    out.set(rgba);

    const count = w * h;
    const whiteThreshold = 255 - tolerance;

    let cornerR = 0, cornerG = 0, cornerB = 0;
    if (sampleCorner && count > 0) {
      cornerR = rgba[0];
      cornerG = rgba[1];
      cornerB = rgba[2];
    }

    for (let i = 0; i < count; i++) {
      const off = i * 4;
      const r = rgba[off], g = rgba[off + 1], b = rgba[off + 2];

      const isNearWhite = r >= whiteThreshold && g >= whiteThreshold && b >= whiteThreshold;

      let isNearCorner = false;
      if (sampleCorner) {
        isNearCorner =
          Math.abs(r - cornerR) <= tolerance &&
          Math.abs(g - cornerG) <= tolerance &&
          Math.abs(b - cornerB) <= tolerance;
      }

      if (isNearWhite || isNearCorner) {
        out[off + 3] = 0;
      }
    }

    return out;
  }

  return {
    medianCut,
    knockoutBackground,
  };
});
