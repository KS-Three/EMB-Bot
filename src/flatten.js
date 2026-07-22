(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const TRANSPARENT_INDEX = 255;

  // One 3x3 majority pass. Reads from `src`, writes a fresh array. Transparent
  // (255) centers are copied through untouched; transparent neighbors never
  // vote. A non-transparent center takes the most common non-transparent index
  // in its (clipped) 3x3 neighborhood, itself included; ties keep the center.
  function modePass(src, w, h) {
    const out = new Uint8Array(src.length);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const i = y * w + x;
        const center = src[i];
        if (center === TRANSPARENT_INDEX) {
          out[i] = TRANSPARENT_INDEX;
          continue;
        }
        const counts = new Map();
        for (let dy = -1; dy <= 1; dy++) {
          const ny = y + dy;
          if (ny < 0 || ny >= h) continue;
          for (let dx = -1; dx <= 1; dx++) {
            const nx = x + dx;
            if (nx < 0 || nx >= w) continue;
            const v = src[ny * w + nx];
            if (v === TRANSPARENT_INDEX) continue;
            counts.set(v, (counts.get(v) || 0) + 1);
          }
        }
        // Pick the max count; if two or more values share the max, keep center.
        // The center itself is always counted (>=1), so counts is never empty.
        let winner = center;
        let winCount = -1;
        let tiedAtMax = false;
        for (const [v, c] of counts) {
          if (c > winCount) {
            winCount = c;
            winner = v;
            tiedAtMax = false;
          } else if (c === winCount) {
            tiedAtMax = true;
          }
        }
        out[i] = tiedAtMax ? center : winner;
      }
    }
    return out;
  }

  function modeFilter(indices, w, h, opts) {
    const iterations = opts && opts.iterations != null ? opts.iterations : 1;
    let cur = Uint8Array.from(indices);
    for (let it = 0; it < iterations; it++) {
      cur = modePass(cur, w, h);
    }
    return cur;
  }

  // Label 4-connected components of equal index (transparent excluded) via an
  // iterative flood fill. Returns { label:Int32Array(-1 for transparent),
  // sizes:number[], count:number }.
  function labelComponents(grid, w, h) {
    const n = w * h;
    const label = new Int32Array(n).fill(-1);
    const sizes = [];
    const stack = [];
    let count = 0;
    for (let start = 0; start < n; start++) {
      if (grid[start] === TRANSPARENT_INDEX || label[start] !== -1) continue;
      const val = grid[start];
      const id = count++;
      label[start] = id;
      stack.length = 0;
      stack.push(start);
      let size = 0;
      while (stack.length) {
        const p = stack.pop();
        size++;
        const px = p % w;
        const py = (p / w) | 0;
        if (px > 0 && label[p - 1] === -1 && grid[p - 1] === val) { label[p - 1] = id; stack.push(p - 1); }
        if (px < w - 1 && label[p + 1] === -1 && grid[p + 1] === val) { label[p + 1] = id; stack.push(p + 1); }
        if (py > 0 && label[p - w] === -1 && grid[p - w] === val) { label[p - w] = id; stack.push(p - w); }
        if (py < h - 1 && label[p + w] === -1 && grid[p + w] === val) { label[p + w] = id; stack.push(p + w); }
      }
      sizes.push(size);
    }
    return { label, sizes, count };
  }

  // Most common non-transparent index among the 4-neighbors that lie OUTSIDE the
  // given component. Ties resolve to the lowest index. Returns -1 when the
  // component has no valid neighbor (fully surrounded by transparent/border).
  function majorityNeighbor(grid, label, comp, w, h) {
    const n = w * h;
    const votes = new Map();
    for (let i = 0; i < n; i++) {
      if (label[i] !== comp) continue;
      const px = i % w;
      const py = (i / w) | 0;
      const check = (q) => {
        if (label[q] === comp) return; // inside the component
        const v = grid[q];
        if (v === TRANSPARENT_INDEX) return;
        votes.set(v, (votes.get(v) || 0) + 1);
      };
      if (px > 0) check(i - 1);
      if (px < w - 1) check(i + 1);
      if (py > 0) check(i - w);
      if (py < h - 1) check(i + w);
    }
    let best = -1;
    let bestCount = -1;
    for (const [v, c] of votes) {
      if (c > bestCount || (c === bestCount && v < best)) {
        bestCount = c;
        best = v;
      }
    }
    return best;
  }

  // Repeatedly absorb the smallest sub-threshold component into its majority
  // neighboring index. Re-labels after each absorb so a just-absorbed speck can
  // join and grow a neighbor for a later, bigger absorb. Terminates: every
  // absorb merges a component into an existing neighboring component, strictly
  // reducing the total component count, and stuck components (only
  // transparent/border neighbors) are skipped rather than retried forever.
  function absorbSmallRegions(indices, w, h, minPx) {
    const cur = Uint8Array.from(indices);
    for (;;) {
      const { label, sizes, count } = labelComponents(cur, w, h);
      // Candidate components under the threshold, smallest first.
      const candidates = [];
      for (let c = 0; c < count; c++) if (sizes[c] < minPx) candidates.push(c);
      candidates.sort((a, b) => sizes[a] - sizes[b]);

      let chosen = -1;
      let target = -1;
      for (const c of candidates) {
        const maj = majorityNeighbor(cur, label, c, w, h);
        if (maj !== -1) { chosen = c; target = maj; break; }
      }
      if (chosen === -1) break; // nothing absorbable remains

      for (let i = 0; i < cur.length; i++) if (label[i] === chosen) cur[i] = target;
    }
    return cur;
  }

  // Merge the palette entries in idxList into one population-weighted color.
  // The merged color lands at the lowest index in idxList; the higher merged
  // entries are removed and every index remapped compactly (255 preserved).
  function mergeColors(palette, indices, idxList) {
    const L = palette.length;
    const uniq = Array.from(new Set(idxList)).sort((a, b) => a - b);

    if (uniq.length < 2) {
      return { palette: palette.map((c) => c.slice()), indices: Uint8Array.from(indices) };
    }

    const mergedTo = uniq[0];
    const removed = new Set(uniq.slice(1));

    // Population weights = pixel counts per index in `indices`.
    const counts = new Array(L).fill(0);
    for (let i = 0; i < indices.length; i++) {
      const v = indices[i];
      if (v !== TRANSPARENT_INDEX && v < L) counts[v]++;
    }

    let wSum = 0;
    let r = 0, g = 0, b = 0;
    for (const idx of uniq) {
      const wt = counts[idx];
      wSum += wt;
      r += palette[idx][0] * wt;
      g += palette[idx][1] * wt;
      b += palette[idx][2] * wt;
    }
    let merged;
    if (wSum === 0) {
      let ra = 0, ga = 0, ba = 0;
      for (const idx of uniq) { ra += palette[idx][0]; ga += palette[idx][1]; ba += palette[idx][2]; }
      merged = [Math.round(ra / uniq.length), Math.round(ga / uniq.length), Math.round(ba / uniq.length)];
    } else {
      merged = [Math.round(r / wSum), Math.round(g / wSum), Math.round(b / wSum)];
    }

    // Build the compacted palette and an old->new position map.
    const newPalette = [];
    const newPos = new Array(L).fill(-1);
    for (let i = 0; i < L; i++) {
      if (removed.has(i)) continue;
      newPos[i] = newPalette.length;
      newPalette.push(i === mergedTo ? merged.slice() : palette[i].slice());
    }
    const mergedNewPos = newPos[mergedTo];

    const oldToNew = new Array(L);
    for (let i = 0; i < L; i++) {
      oldToNew[i] = (i === mergedTo || removed.has(i)) ? mergedNewPos : newPos[i];
    }

    const newIndices = Uint8Array.from(indices, (v) =>
      v === TRANSPARENT_INDEX ? TRANSPARENT_INDEX : (v < L ? oldToNew[v] : v)
    );

    return { palette: newPalette, indices: newIndices };
  }

  function indicesToRGBA(indices, palette, w, h) {
    const n = w * h;
    const out = new Uint8ClampedArray(n * 4);
    for (let i = 0; i < n; i++) {
      const o = i * 4;
      const v = indices[i];
      if (v === TRANSPARENT_INDEX) continue; // leave as [0,0,0,0]
      const c = palette[v] || [0, 0, 0];
      out[o] = c[0];
      out[o + 1] = c[1];
      out[o + 2] = c[2];
      out[o + 3] = 255;
    }
    return out;
  }

  // Fraction of opaque (non-transparent) pixels assigned to each palette index.
  // Sums to ~1 when any opaque pixels exist; all zeros when there are none.
  function paletteShares(indices, paletteLen) {
    const counts = new Array(paletteLen).fill(0);
    let total = 0;
    for (let i = 0; i < indices.length; i++) {
      const v = indices[i];
      if (v === TRANSPARENT_INDEX) continue;
      total++;
      if (v < paletteLen) counts[v]++;
    }
    const shares = new Array(paletteLen).fill(0);
    if (total === 0) return shares;
    for (let k = 0; k < paletteLen; k++) shares[k] = counts[k] / total;
    return shares;
  }

  return {
    modeFilter,
    absorbSmallRegions,
    mergeColors,
    indicesToRGBA,
    paletteShares,
  };
});
