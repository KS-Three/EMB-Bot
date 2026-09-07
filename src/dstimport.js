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
  // A DST's first 512 bytes are an ASCII header of CR-terminated "XX:value"
  // fields. Nothing downstream trusts their VALUES — the counts and extents
  // are recomputed from the record stream — but their PRESENCE is what says
  // this is a DST at all, and until 2026-09-07 nothing checked it.
  //
  // What that cost: the size check below is the only thing that stood between
  // a customer and a decode of arbitrary bytes, so ANY file over 515 bytes
  // decoded. Feeding the panel a Brother .pes produced no error and a design
  // reading **3736 x 7624 mm with 10,878 colour blocks** — the panel then
  // rendered a thread picker for every one of them. Measured through the
  // shipped UI.
  //
  // The signal is decisive. Measured over every DST in the repo — five
  // commissioned professional files, one written by pystitch, two by
  // EMB-Bot's own encoder, i.e. three unrelated writers — ALL twelve tags are
  // present in all eight. Every negative tried (PES, JEF, EXP, SVG, PNG, two
  // blocks of random bytes, a JSON project file) scores ZERO, and a file
  // hand-built to contain sixty "ST:" lines scores one. The floor of three is
  // set well under twelve so a sparse writer is not rejected, and well over
  // one so a coincidence is not admitted.
  const DST_HEADER_TAGS = ["LA", "ST", "CO", "+X", "-X", "+Y", "-Y", "AX", "AY", "MX", "MY", "PD"];
  const DST_HEADER_TAGS_MIN = 3;

  function dstHeaderTagCount(bytes) {
    let text = "";
    for (let i = 0; i < 512 && i < bytes.length; i++) text += String.fromCharCode(bytes[i]);
    const seen = {};
    let n = 0;
    // Tags are matched at the START of a delimited line, not anywhere in the
    // block: "ST:" inside a filename or a comment is not a header field.
    for (const line of text.split(/[\r\n\x1a]/)) {
      const tag = line.replace(/^\s+/, "").slice(0, 2);
      if (line.replace(/^\s+/, "").charAt(2) !== ":") continue;
      if (DST_HEADER_TAGS.indexOf(tag) === -1 || seen[tag]) continue;
      seen[tag] = true;
      n++;
    }
    return n;
  }

  function decodeDST(bytes) {
    if (!bytes || bytes.length < 512 + 3) {
      throw new Error("Not a DST file (too small).");
    }
    if (dstHeaderTagCount(bytes) < DST_HEADER_TAGS_MIN) {
      throw new Error(
        "Not a DST file \u2014 no Tajima header fields in the first 512 bytes. " +
        "If this is a .pes, .jef or .exp, look for the .dst download of the same " +
        "design: DST is the only stitch format EMB-Bot can read."
      );
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

  // The SAME file, read the way a Tajima/pyembroidery writer meant it.
  //
  // `decodeDST` above reads a DST in EMB-Bot's OWN convention — the one
  // `dst.js` writes — so the two round-trip against each other exactly and
  // `test/dstimport.test.js` pins that. Third-party files are not written in
  // that convention, and the import lane exists for third-party files.
  //
  // What the difference LOOKS like, measured 2026-09-07 and worth stating
  // precisely because the repo had it recorded wrong since August:
  //
  //   * against pystitch's own coordinates, `decodeDST` is an exact 90 deg
  //     CCW rotation: (px, py) -> (-py, px), rms 0 over all five committed pro
  //     reference DSTs and over test/fixtures/standard-tajima.dst.
  //   * but the model's +y points UP and a raster frame's +y points DOWN, so
  //     ON SCREEN that rotation composes with the flip into a REFLECTION. An
  //     imported logo does not arrive on its side; it arrives BACKWARDS, and
  //     no amount of rotation repairs it. (The Studio told customers to use
  //     Rotate until this was looked at rather than measured — a bbox swap is
  //     equally consistent with a turn and a mirror, and only a picture tells
  //     them apart. docs/scope-history.md 2026-09-07 carries the numbers.)
  //
  // The correction is therefore a plain transpose of the decoded points,
  // which is its own inverse and leaves the bbox-centered contract intact:
  // the result's model point is exactly (px, -py) of what pystitch reads,
  // which is the same mapping tools/crossval-stitch-formats.mjs calls
  // "identity" in the export direction.
  //
  // Deliberately a SECOND entry point rather than a change to `decodeDST`:
  // `dst.js`'s writer is unchanged and still speaks EMB-Bot's convention, so
  // the reader that pairs with it has to stay as it is. When the codec itself
  // is put right (Kent's call — it re-orients every DST EMB-Bot has written)
  // these two collapse into one and this function is deleted.
  function decodeDSTStandard(bytes) {
    const d = decodeDST(bytes);
    return Object.assign({}, d, {
      stitches: d.stitches.map((s) => ({ x: s.y, y: s.x, type: s.type })),
      widthMM: d.heightMM,
      heightMM: d.widthMM,
    });
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
  //   targetWidthMm  desired width AFTER rotation; default = native width,
  //                  clamped so BOTH dims fit the hoop.
  //   rotationDeg    rotation about the design's own center (CCW in +y-up
  //                  space, same convention as the lettering engine's
  //                  rotationDeg). Applied BEFORE the scale/clamp math, so
  //                  targetWidthMm and the hoop clamps always speak about
  //                  the dimensions the user actually sees — a landscape
  //                  design rotated 90 clamps by its new (portrait) extents.
  //   offsetXMm/offsetYMm  placement translation, DST-space (+y up), mm.
  //   blockColors    { [blockIndex]: [r,g,b] } overrides; missing blocks get
  //                  IMPORT_BLOCK_COLORS defaults.
  function buildImportedDesign(decoded, opts) {
    const o = opts || {};
    const garment = o.garment;
    if (!garment) throw new Error("buildImportedDesign needs a garment");
    const hoopWmm = garment.widthIn * MM_PER_INCH;
    const hoopHmm = garment.heightIn * MM_PER_INCH;

    // Rotation happens in decoded (unscaled, centered) space, in floats —
    // rounding waits for the single scale-time round below so a rotated
    // design doesn't accumulate two quantization passes. The rot === 0 path
    // must stay byte-identical to the pre-rotation code: source points and
    // native dims pass through untouched.
    const rot = (((o.rotationDeg || 0) % 360) + 360) % 360;
    let srcPoints = decoded.stitches;
    let srcWmm = decoded.widthMM;
    let srcHmm = decoded.heightMM;
    if (rot !== 0) {
      // Exact values for quadrant angles: Math.sin(Math.PI) leaves ~1e-16
      // of noise that would otherwise leak into widthMM/heightMM (and the
      // SizePanel display) every time someone uses the flip-180 shortcut.
      const QUAD = { 0: [1, 0], 90: [0, 1], 180: [-1, 0], 270: [0, -1] };
      const rad = (rot * Math.PI) / 180;
      const cos = QUAD[rot] ? QUAD[rot][0] : Math.cos(rad);
      const sin = QUAD[rot] ? QUAD[rot][1] : Math.sin(rad);
      srcPoints = decoded.stitches.map((s) => ({
        x: s.x * cos - s.y * sin,
        y: s.x * sin + s.y * cos,
        type: s.type,
      }));
      // Re-center on the ROTATED stitch bbox midpoint: rotating a point
      // cloud about the old bbox center does not generally leave the new
      // bbox centered (only a perfect rectangle would), and every consumer
      // (placement offsets, hoop clamps, the field's selection box) assumes
      // bbox-centered output — the same contract decodeDST establishes.
      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      for (const s of srcPoints) {
        if (s.type !== "stitch") continue;
        if (s.x < minX) minX = s.x;
        if (s.x > maxX) maxX = s.x;
        if (s.y < minY) minY = s.y;
        if (s.y > maxY) maxY = s.y;
      }
      const cx = (minX + maxX) / 2;
      const cy = (minY + maxY) / 2;
      for (const s of srcPoints) { s.x -= cx; s.y -= cy; }
      srcWmm = (maxX - minX) / DST_UNITS_PER_MM;
      srcHmm = (maxY - minY) / DST_UNITS_PER_MM;
    }

    const nativeWmm = Math.max(0.1, srcWmm);
    const nativeHmm = Math.max(0.1, srcHmm);

    // Native size unless asked otherwise, then clamp so both dims fit.
    let targetWmm = (typeof o.targetWidthMm === "number" && isFinite(o.targetWidthMm) && o.targetWidthMm > 0)
      ? o.targetWidthMm
      : nativeWmm;
    targetWmm = Math.min(Math.max(targetWmm, 1), hoopWmm);
    let sc = targetWmm / nativeWmm;
    if (nativeHmm * sc > hoopHmm) sc = hoopHmm / nativeHmm; // height clamp

    const offXu = Math.round((o.offsetXMm || 0) * DST_UNITS_PER_MM);
    const offYu = Math.round((o.offsetYMm || 0) * DST_UNITS_PER_MM);

    const stitches = new Array(srcPoints.length);
    for (let i = 0; i < srcPoints.length; i++) {
      const s = srcPoints[i];
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

  return { decodeDST, decodeDSTStandard, buildImportedDesign, IMPORT_BLOCK_COLORS };
});
