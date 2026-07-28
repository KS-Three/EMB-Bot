(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const DST_UNITS_PER_MM = 10;
  const MM_PER_INCH = 25.4;

  // Inverse of dst.js's encodeRecord bit-weight table (same authoritative
  // weights, decode direction). Kept in this module rather than shared so
  // dstimport stays loadable standalone in Node tests.
  function decodeDelta(b0, b1, b2) {
    let x = 0, y = 0;
    if (b0 & 0x80) x += 1;
    if (b0 & 0x40) x -= 1;
    if (b0 & 0x20) x += 9;
    if (b0 & 0x10) x -= 9;
    if (b0 & 0x08) y -= 9;
    if (b0 & 0x04) y += 9;
    if (b0 & 0x02) y -= 1;
    if (b0 & 0x01) y += 1;
    if (b1 & 0x80) x += 3;
    if (b1 & 0x40) x -= 3;
    if (b1 & 0x20) x += 27;
    if (b1 & 0x10) x -= 27;
    if (b1 & 0x08) y -= 27;
    if (b1 & 0x04) y += 27;
    if (b1 & 0x02) y -= 3;
    if (b1 & 0x01) y += 3;
    if (b2 & 0x20) x += 81;
    if (b2 & 0x10) x -= 81;
    if (b2 & 0x08) y -= 81;
    if (b2 & 0x04) y += 81;
    return [x, y];
  }

  // Decodes a Tajima .DST file (Uint8Array) into our internal stitch model:
  // absolute 0.1mm coords, +y up, records typed "stitch" | "jump" | "trim" |
  // "color", CENTERED so the design bbox's midpoint is (0,0) — the same
  // convention buildLetteringDesign/buildQualityDesign output, which is what
  // lets the Studio place/scale/combine an import exactly like a generated
  // element.
  //
  // Jump/trim mapping (lossy in DST itself): the format has no trim opcode —
  // machines read a run of >=3 consecutive jump records as a trim (our own
  // encodeDST emits exactly that, see dst.js splitTrim). So on import, any
  // run of consecutive jumps collapses to ONE record at the run's final
  // position: type "trim" when the run is >=3 records, else "jump". Long
  // moves that were split into >=3 jumps purely for range reasons also read
  // as trims — that ambiguity is inherent to DST and harmless here (a trim
  // before a long travel is what a machine would do anyway).
  //
  // Returns { stitches, stitchCount, jumpCount, trimCount, colorCount,
  // widthMM, heightMM, label }. Throws on anything that can't be a DST.
  function decodeDST(bytes) {
    if (!bytes || bytes.length < 512 + 3) {
      throw new Error("Not a DST file (too small).");
    }
    let label = "";
    // Header is 512 bytes of ASCII "LA:name\r ST:count\r ..." — permissive
    // parse: only used for the label, never trusted for counts/extents.
    for (let i = 0; i < 512 - 3; i++) {
      if (bytes[i] === 0x4c && bytes[i + 1] === 0x41 && bytes[i + 2] === 0x3a) { // "LA:"
        let j = i + 3;
        while (j < 512 && bytes[j] !== 0x0d && bytes[j] !== 0x0a && bytes[j] !== 0x1a) j++;
        label = String.fromCharCode.apply(null, Array.prototype.slice.call(bytes.subarray(i + 3, j))).trim();
        break;
      }
    }

    const stitches = [];
    let x = 0, y = 0;
    let stitchCount = 0, jumpCount = 0, trimCount = 0, colorChanges = 0;
    let pendingJumpRun = 0; // consecutive jump records not yet flushed

    function flushJumpRun() {
      if (!pendingJumpRun) return;
      if (pendingJumpRun >= 3) {
        stitches.push({ x, y, type: "trim" });
        trimCount++;
      } else {
        stitches.push({ x, y, type: "jump" });
        jumpCount++;
      }
      pendingJumpRun = 0;
    }

    for (let i = 512; i + 2 < bytes.length; i += 3) {
      const b0 = bytes[i], b1 = bytes[i + 1], b2 = bytes[i + 2];
      if (b0 === 0 && b1 === 0 && b2 === 0xf3) break; // end record
      const d = decodeDelta(b0, b1, b2);
      x += d[0];
      y += d[1];
      if (b2 & 0x40) { // color change (0xC3 family) — position may move too
        flushJumpRun();
        stitches.push({ x, y, type: "color" });
        colorChanges++;
        continue;
      }
      if (b2 & 0x80) { // jump — accumulate; a run collapses to one jump/trim
        pendingJumpRun++;
        continue;
      }
      flushJumpRun();
      stitches.push({ x, y, type: "stitch" });
      stitchCount++;
    }
    // A trailing jump run (no stitch after it) is dead travel — drop it.
    pendingJumpRun = 0;

    if (!stitchCount) throw new Error("No stitches found — is this really a DST file?");

    // Center: translate so the STITCH bbox midpoint lands on (0,0). Jump/trim
    // positions ride along; they're travel, not ink, so they don't define
    // the bbox (same rule preview.js's designBBoxMm uses).
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const s of stitches) {
      if (s.type !== "stitch") continue;
      if (s.x < minX) minX = s.x;
      if (s.x > maxX) maxX = s.x;
      if (s.y < minY) minY = s.y;
      if (s.y > maxY) maxY = s.y;
    }
    const cx = Math.round((minX + maxX) / 2);
    const cy = Math.round((minY + maxY) / 2);
    for (const s of stitches) { s.x -= cx; s.y -= cy; }

    return {
      stitches,
      stitchCount,
      jumpCount,
      trimCount,
      colorCount: colorChanges + 1,
      widthMM: (maxX - minX) / DST_UNITS_PER_MM,
      heightMM: (maxY - minY) / DST_UNITS_PER_MM,
      label,
    };
  }

  // Default per-block thread colors for imports (DST files carry NO color
  // information — only change markers). Deliberately distinct hues so a
  // multi-block design is readable before the user assigns real threads.
  const IMPORT_BLOCK_COLORS = [
    [40, 40, 45], [220, 45, 45], [40, 110, 210], [240, 180, 40], [50, 160, 80],
    [150, 70, 200], [240, 130, 40], [60, 190, 190], [230, 90, 160], [130, 130, 130],
    [110, 70, 40], [180, 200, 60],
  ];

  // Turns a decodeDST() result into a placeable Design — same output contract
  // as buildLetteringDesign ({ stitches, colors, widthMM, heightMM,
  // stitchCount, colorCount }) so generate.js/combine.js/exporters treat it
  // identically. PRE-DIGITIZED stitches are only ever scaled uniformly
  // (targetWidthMm) and translated (offsetXMm/offsetYMm); nothing is
  // re-digitized — density physically changes with scale, so callers should
  // warn when |scale-1| is large (the returned _debug.scale is for that).
  //
  // opts:
  //   garment        resolved garment (hoop clamp); required.
  //   targetWidthMm  desired width; default = native width, clamped so BOTH
  //                  dims fit the hoop.
  //   offsetXMm/offsetYMm  placement translation, DST-space (+y up), mm.
  //   blockColors    { [blockIndex]: [r,g,b] } overrides; missing blocks get
  //                  IMPORT_BLOCK_COLORS defaults.
  function buildImportedDesign(decoded, opts) {
    const o = opts || {};
    const garment = o.garment;
    if (!garment) throw new Error("buildImportedDesign needs a garment");
    const hoopWmm = garment.widthIn * MM_PER_INCH;
    const hoopHmm = garment.heightIn * MM_PER_INCH;

    const nativeWmm = Math.max(0.1, decoded.widthMM);
    const nativeHmm = Math.max(0.1, decoded.heightMM);

    // Native size unless asked otherwise, then clamp so both dims fit.
    let targetWmm = (typeof o.targetWidthMm === "number" && isFinite(o.targetWidthMm) && o.targetWidthMm > 0)
      ? o.targetWidthMm
      : nativeWmm;
    targetWmm = Math.min(Math.max(targetWmm, 1), hoopWmm);
    let sc = targetWmm / nativeWmm;
    if (nativeHmm * sc > hoopHmm) sc = hoopHmm / nativeHmm; // height clamp

    const offXu = Math.round((o.offsetXMm || 0) * DST_UNITS_PER_MM);
    const offYu = Math.round((o.offsetYMm || 0) * DST_UNITS_PER_MM);

    const stitches = new Array(decoded.stitches.length);
    for (let i = 0; i < decoded.stitches.length; i++) {
      const s = decoded.stitches[i];
      stitches[i] = { x: Math.round(s.x * sc) + offXu, y: Math.round(s.y * sc) + offYu, type: s.type };
    }
    stitches.push({ x: offXu, y: offYu, type: "end" });

    const overrides = o.blockColors || {};
    const colors = [];
    for (let b = 0; b < decoded.colorCount; b++) {
      const rgb = overrides[b] || IMPORT_BLOCK_COLORS[b % IMPORT_BLOCK_COLORS.length];
      colors.push({ r: rgb[0], g: rgb[1], b: rgb[2] });
    }

    return {
      stitches,
      colors,
      widthMM: nativeWmm * sc,
      heightMM: nativeHmm * sc,
      stitchCount: decoded.stitchCount,
      colorCount: colors.length,
      _debug: { scale: sc, jumpCount: decoded.jumpCount, trimCount: decoded.trimCount, label: decoded.label },
    };
  }

  return { decodeDST, buildImportedDesign, IMPORT_BLOCK_COLORS };
});
