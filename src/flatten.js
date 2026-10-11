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
  // sizes:number[], count:number }. One walk over the whole image, counted in
  // `stats.imageWalks` when a caller hands `stats` over.
  function labelComponents(grid, w, h, stats) {
    if (stats) stats.imageWalks += 1;
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

  // Repeatedly absorb the smallest sub-threshold component into its majority
  // neighboring index: the most common non-transparent index among the
  // 4-neighbors outside it, ties to the lowest index. Smallest first, and of
  // two the same size the one a raster scan meets first, so a just-absorbed
  // speck can join and grow a neighbor for a later, bigger absorb. A component
  // with only transparent/border neighbors stays as it is. Terminates: every
  // absorb merges a component into an existing neighboring component, strictly
  // reducing the total component count.
  //
  // The image is labelled ONCE. After that each component keeps its own pixels
  // (a linked list), its size and its first pixel; an absorb joins the lists
  // of the components it merges, and a heap hands over the smallest. The rule
  // above used to be run by labelling the whole image again after every
  // absorb; `test/flatten.test.js` keeps that version word for word and holds
  // this one to its output.
  //
  // `opts.stats`, when given as { absorbed: 0, imageWalks: 0 }, is counted
  // into: components absorbed, and walks over the whole image. It changes
  // nothing that is returned.
  function absorbSmallRegions(indices, w, h, minPx, opts) {
    const stats = (opts && opts.stats) || null;
    const cur = Uint8Array.from(indices);
    const n = w * h;
    const { label, sizes, count } = labelComponents(cur, w, h, stats);

    // Each component's pixels as a linked list in raster order, so a list
    // starts at its component's first pixel.
    const next = new Int32Array(n).fill(-1);
    const head = new Int32Array(count).fill(-1);
    const tail = new Int32Array(count);
    if (stats) stats.imageWalks += 1;
    for (let p = 0; p < n; p++) {
      const c = label[p];
      if (c === -1) continue;
      if (head[c] === -1) head[c] = p;
      else next[tail[c]] = p;
      tail[c] = p;
    }
    const size = Int32Array.from(sizes);
    const first = Int32Array.from(head);

    // `label` is never rewritten. A component taken into another points at it
    // through `parent`, and is itself only while it is its own parent.
    const parent = new Int32Array(count);
    for (let c = 0; c < count; c++) parent[c] = c;
    const rootOf = (c) => {
      while (parent[c] !== c) { parent[c] = parent[parent[c]]; c = parent[c]; }
      return c;
    };

    // The candidates in a min-heap: smallest first, of two the same size the
    // one whose first pixel comes first, which is the order a fresh labelling
    // would number them in. Only the component just taken out ever grows, so
    // nothing changes rank while it waits, and no component waits twice.
    const heap = new Int32Array(count);
    let waiting = 0;
    const ahead = (a, b) => size[a] < size[b] || (size[a] === size[b] && first[a] < first[b]);
    const put = (c) => {
      let i = waiting++;
      while (i > 0) {
        const up = (i - 1) >> 1;
        if (!ahead(c, heap[up])) break;
        heap[i] = heap[up];
        i = up;
      }
      heap[i] = c;
    };
    const take = () => {
      const top = heap[0];
      const c = heap[--waiting];
      let i = 0;
      for (;;) {
        let kid = 2 * i + 1;
        if (kid >= waiting) break;
        if (kid + 1 < waiting && ahead(heap[kid + 1], heap[kid])) kid++;
        if (!ahead(heap[kid], c)) break;
        heap[i] = heap[kid];
        i = kid;
      }
      heap[i] = c;
      return top;
    };
    for (let c = 0; c < count; c++) if (size[c] < minPx) put(c);

    const votes = new Int32Array(256);
    const voted = [];
    let self = -1; // the component in hand
    let own = 0; // its index
    let target = -1; // the index it is absorbed into
    const vote = (q) => {
      const v = cur[q];
      // A neighbor of its own index is inside it: components are maximal.
      if (v === own || v === TRANSPARENT_INDEX) return;
      if (votes[v]++ === 0) voted.push(v);
    };
    const join = (q) => {
      if (cur[q] !== target) return;
      const other = rootOf(label[q]);
      if (other === self) return;
      parent[other] = self;
      size[self] += size[other];
      if (first[other] < first[self]) first[self] = first[other];
      next[tail[self]] = head[other];
      tail[self] = tail[other];
    };
    const around = (p, visit) => {
      const px = p % w;
      const py = (p / w) | 0;
      if (px > 0) visit(p - 1);
      if (px < w - 1) visit(p + 1);
      if (py > 0) visit(p - w);
      if (py < h - 1) visit(p + w);
    };

    while (waiting > 0) {
      self = take();
      if (parent[self] !== self) continue; // taken into a neighbor while it waited

      own = cur[head[self]];
      for (let p = head[self]; p !== -1; p = next[p]) around(p, vote);
      target = -1;
      let most = 0;
      for (const v of voted) {
        if (votes[v] > most || (votes[v] === most && v < target)) { most = votes[v]; target = v; }
        votes[v] = 0;
      }
      voted.length = 0;
      // Only transparent/border beside it. Nothing can ever arrive there, so
      // it is not asked again.
      if (target === -1) continue;

      // Repaint it and take in every neighboring component of its new index.
      // Their pixels join the list after `last`, where this walk stops.
      const last = tail[self];
      for (let p = head[self]; ; p = next[p]) {
        cur[p] = target;
        around(p, join);
        if (p === last) break;
      }
      if (stats) stats.absorbed += 1;
      if (size[self] < minPx) put(self);
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
