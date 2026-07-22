(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const TRANSPARENT_INDEX = 255;

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

    const palette = boxes.map((box) => averageColor(box, pixels));

    // Assign each opaque pixel to nearest palette color (Euclidean in RGB).
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
