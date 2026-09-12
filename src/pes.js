(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  // Both PES/PEC coordinates use 0.1mm units, same as the Design (DST) model.
  // DST origin is centre with +Y up; PEC screen convention is +Y down, so Y is
  // flipped when emitting PEC/PES stitch coordinates.

  // ---- little byte-buffer helper --------------------------------------
  function Writer() {
    this.bytes = [];
  }
  Writer.prototype.u8 = function (v) { this.bytes.push(v & 0xff); return this; };
  Writer.prototype.u16le = function (v) { this.u8(v); this.u8(v >> 8); return this; };
  Writer.prototype.u16be = function (v) { this.u8(v >> 8); this.u8(v); return this; };
  Writer.prototype.i16le = function (v) { return this.u16le(v & 0xffff); };
  Writer.prototype.u32le = function (v) {
    this.u8(v); this.u8(v >> 8); this.u8(v >> 16); this.u8(v >> 24); return this;
  };
  Writer.prototype.f32le = function (v) {
    const b = new Uint8Array(4);
    new DataView(b.buffer).setFloat32(0, v, true);
    for (let i = 0; i < 4; i++) this.u8(b[i]);
    return this;
  };
  Writer.prototype.str = function (s) {
    for (let i = 0; i < s.length; i++) this.u8(s.charCodeAt(i) & 0xff);
    return this;
  };
  Writer.prototype.lenStr = function (s) { this.u16le(s.length); return this.str(s); };
  Writer.prototype.tell = function () { return this.bytes.length; };
  Writer.prototype.patch3le = function (pos, v) {
    this.bytes[pos] = v & 0xff;
    this.bytes[pos + 1] = (v >> 8) & 0xff;
    this.bytes[pos + 2] = (v >> 16) & 0xff;
  };
  Writer.prototype.patch4le = function (pos, v) {
    this.bytes[pos] = v & 0xff;
    this.bytes[pos + 1] = (v >> 8) & 0xff;
    this.bytes[pos + 2] = (v >> 16) & 0xff;
    this.bytes[pos + 3] = (v >> 24) & 0xff;
  };

  function extents(stitches) {
    let xMin = 0, xMax = 0, yMin = 0, yMax = 0, have = false;
    for (const st of stitches) {
      const x = st.x | 0, y = st.y | 0;
      if (!have) { xMin = xMax = x; yMin = yMax = y; have = true; }
      else {
        if (x < xMin) xMin = x;
        if (x > xMax) xMax = x;
        if (y < yMin) yMin = y;
        if (y > yMax) yMax = y;
      }
    }
    return { xMin, xMax, yMin, yMax, have };
  }

  // ---- PEC delta stitch encoding --------------------------------------
  // Short form: one signed 7-bit byte per axis when |delta| <= 63.
  // Long form:  two bytes per axis, 0x80 flag + 12-bit value; 0x20 flag = jump/trim.
  // Colour change: 0xFE 0xB0 <needle>. End: 0xFF.
  // Long-form field is a signed 12-bit two's complement value, so a single
  // record can only carry a delta in [-PEC_MAX_DELTA, PEC_MAX_DELTA]. Larger
  // TRAVEL moves (e.g. a jump across a full-back panel) are split into
  // intermediate jump hops. Sewn moves are split far earlier, at
  // PEC_MAX_SEWN_DELTA below.
  const PEC_MAX_DELTA = 2047;

  // The SEWABILITY ceiling, and the reason this file needed a ruling.
  //
  // Nothing in the PEC format forces a split below 2047 units (204.7 mm), so
  // until 2026-09-12 pes.js carried whatever the design asked for: the
  // crossval `long` fixture's 300-unit segment came out as ONE record, and a
  // real `manga_impact` "AB" monogram at Full Back emitted a 51.1 mm stitch
  // (DOCTRINE 2026-09-07's three-encoder table) — a move no machine can sew.
  // DST split the same design at its record's own ±121 and EXP at ±127, so
  // one design produced three different sew-outs and only PES's was
  // unsewable.
  //
  // Kent's ruling 2026-09-12: split it. 121 units is not PEC's limit — it is
  // THE REPO'S sewability bar, `max(|dx|,|dy|) > 12.1 mm`, one DST record.
  // That is the same test `tools/long-stitch-census.mjs` counts with and the
  // same one DOCTRINE's "18 fonts produce stitches over one DST record" and
  // the 2026-09-11 split-satin ruling are stated in. Picking DST's 121 over
  // EXP's 127 means a PES file never contains a sewn move that DST would have
  // had to split: the three encoders agree on what is sewable, and differ
  // only in the 6 units of slack EXP's record happens to have.
  //
  // Travel is NOT subject to this — a jump, a trim, and the move into the
  // first stitch of a run all keep the format's full 2047 reach, because
  // splitting travel finer only writes more records for the same needle-up
  // move. See the chain rule in pecEncodeStitches.
  const PEC_MAX_SEWN_DELTA = 121;

  function pecClampStep(delta, limit) {
    const lim = limit || PEC_MAX_DELTA;
    if (delta > lim) return lim;
    if (delta < -lim) return -lim;
    return delta;
  }

  // Long-form flag: 0 = plain stitch, PEC_FLAG_JUMP = jump, PEC_FLAG_TRIM =
  // trim. Matches pyembroidery's PecWriter/PecReader (JUMP_CODE=0x10,
  // TRIM_CODE=0x20, shifted into the high byte of the 16-bit long-form
  // record, i.e. 0x1000/0x2000). Jumps and trims previously shared the
  // 0x2000 (TRIM) code, so every jump decoded as a trim in standard readers.
  const PEC_FLAG_JUMP = 0x1000;
  const PEC_FLAG_TRIM = 0x2000;

  function pecWriteRecord(w, dx, dy, flag) {
    if (!flag && dx < 64 && dx > -64 && dy < 64 && dy > -64) {
      w.u8(dx & 0x7f);
      w.u8(dy & 0x7f);
    } else {
      let vx = dx & 0x0fff;
      vx |= 0x8000;
      if (flag) vx |= flag;
      w.u8((vx >> 8) & 0xff).u8(vx & 0xff);
      let vy = dy & 0x0fff;
      vy |= 0x8000;
      if (flag) vy |= flag;
      w.u8((vy >> 8) & 0xff).u8(vy & 0xff);
    }
  }

  function pecEncodeStitches(w, stitches) {
    let px = 0, py = 0; // previous position in PEC screen space (0.1mm, +Y down)
    let needleToggle = 2;
    // Whether the previous EMITTED record laid thread — the chain rule the
    // oversized-move split below needs, identical to encodeDST's. Starts
    // false: the file's first move is travel to wherever the design begins.
    let lastWasStitch = false;
    for (const st of stitches) {
      const type = st.type || "stitch";
      if (type === "end") break;
      if (type === "color") {
        w.u8(0xfe).u8(0xb0).u8(needleToggle);
        needleToggle = needleToggle === 2 ? 1 : 2;
        lastWasStitch = false; // a colour change cuts the chain
        continue;
      }
      const sx = st.x | 0;
      const sy = -(st.y | 0); // flip Y to PEC screen convention
      const flag = type === "trim" ? PEC_FLAG_TRIM : type === "jump" ? PEC_FLAG_JUMP : 0;
      const isStitch = flag === 0;

      // THE CHAIN RULE (dst.js's encodeDST, same words, same reason). A move
      // splits into STITCHES only when it CONTINUES a sewn run: this record
      // is a stitch AND the last emitted one was. The move to the FIRST
      // stitch after a jump, a trim, a colour change or the start of the file
      // is TRAVEL — there is nothing to sew between where the needle was and
      // where the design begins, and splitting it into stitches would draw a
      // line from the origin across the garment.
      //
      // So a chained stitch is split at the sewability bar, as stitches; a
      // jump, a trim and travel into a run are split at the format's own
      // reach, as jumps. `test/dstimport.test.js`'s off-origin-centering
      // fixture is exactly the case that punishes getting this wrong.
      const chained = isStitch && lastWasStitch;
      const limit = chained ? PEC_MAX_SEWN_DELTA : PEC_MAX_DELTA;
      const splitFlag = chained ? 0 : PEC_FLAG_JUMP;

      let dx = sx - px;
      let dy = sy - py;

      while (Math.abs(dx) > limit || Math.abs(dy) > limit) {
        const stepX = pecClampStep(dx, limit);
        const stepY = pecClampStep(dy, limit);
        pecWriteRecord(w, stepX, stepY, splitFlag);
        px += stepX;
        py += stepY;
        dx = sx - px;
        dy = sy - py;
      }

      pecWriteRecord(w, dx, dy, flag);
      px = sx;
      py = sy;
      lastWasStitch = isStitch;
    }
    w.u8(0xff); // end of stitch data
  }

  // ---- Brother PEC thread chart (indices 1-64) -------------------------
  // RGB values per the standard Brother PEC palette, sourced from
  // pyembroidery's EmbThreadPec.get_thread_set() (installed at
  // digitizer/.venv/lib/python*/site-packages/pyembroidery/EmbThreadPec.py)
  // -- the same reference chart the Python digitizer's pyembroidery-backed
  // /export route and this repo's cross-validation harness
  // (tools/crossval-stitch-formats.mjs) already treat as ground truth.
  // Index 0 is unused (PEC has no "index 0" thread).
  const BROTHER_PEC_CHART = [
    null,
    [14, 31, 124], [10, 85, 163], [0, 135, 119], [75, 107, 175],
    [237, 23, 31], [209, 92, 0], [145, 54, 151], [228, 154, 203],
    [145, 95, 172], [158, 214, 125], [232, 169, 0], [254, 186, 53],
    [255, 255, 0], [112, 188, 31], [186, 152, 0], [168, 168, 168],
    [125, 111, 0], [255, 255, 179], [79, 85, 86], [0, 0, 0],
    [11, 61, 145], [119, 1, 118], [41, 49, 51], [42, 19, 1],
    [246, 74, 138], [178, 118, 36], [252, 187, 197], [254, 55, 15],
    [240, 240, 240], [106, 28, 138], [168, 221, 196], [37, 132, 187],
    [254, 179, 67], [255, 243, 107], [208, 166, 96], [209, 84, 0],
    [102, 186, 73], [19, 74, 70], [135, 135, 135], [216, 204, 198],
    [67, 86, 7], [253, 217, 222], [249, 147, 188], [0, 56, 34],
    [178, 175, 212], [104, 106, 176], [239, 227, 185], [247, 56, 102],
    [181, 75, 100], [19, 43, 26], [199, 1, 86], [254, 158, 50],
    [168, 222, 235], [0, 103, 62], [78, 41, 144], [47, 126, 32],
    [255, 204, 204], [255, 217, 17], [9, 91, 166], [240, 249, 112],
    [227, 243, 91], [255, 153, 0], [255, 240, 141], [255, 200, 200],
  ];

  function nearestPecIndex(r, g, b) {
    let bestIdx = 1;
    let bestDist = Infinity;
    for (let i = 1; i < BROTHER_PEC_CHART.length; i++) {
      const entry = BROTHER_PEC_CHART[i];
      const dr = r - entry[0], dg = g - entry[1], db = b - entry[2];
      const dist = dr * dr + dg * dg + db * db;
      if (dist < bestDist) { bestDist = dist; bestIdx = i; }
    }
    return bestIdx;
  }

  // ---- PEC section ----------------------------------------------------
  function writePEC(w, design) {
    const pecStart = w.tell(); // PEC-relative 0 for this section
    const stitches = (design && design.stitches) || [];
    const colors = (design && design.colors) || [];
    const colorCount = Math.max(1, colors.length);
    const ext = extents(stitches);
    const width = ext.xMax - ext.xMin;
    const height = ext.yMax - ext.yMin;

    const label = String((design && design.label) || "EMBBOT").slice(0, 16);

    w.str("LA:");
    w.str(label);
    for (let i = label.length; i < 16; i++) w.u8(0x20); // pad to 16
    w.u8(0x0d);
    for (let i = 0; i < 12; i++) w.u8(0x20);
    w.u8(0xff).u8(0x00).u8(0x06).u8(0x26);
    for (let i = 0; i < 12; i++) w.u8(0x20);

    // colour count (stored as count-1) and palette index list
    w.u8((colorCount - 1) & 0xff);
    for (let i = 0; i < colorCount; i++) {
      const c = colors[i] || {};
      // Explicit paletteIndex wins; otherwise map the design RGB to the
      // nearest Brother chart entry; otherwise fall back to a sequential
      // index (matches prior behaviour when no colour info exists at all).
      let idx;
      if (typeof c.paletteIndex === "number") {
        idx = c.paletteIndex;
      } else if (
        typeof c.r === "number" &&
        typeof c.g === "number" &&
        typeof c.b === "number"
      ) {
        idx = nearestPecIndex(c.r, c.g, c.b);
      } else {
        idx = (i % 64) + 1;
      }
      w.u8(idx & 0xff);
    }
    // pad colour table region out to the fixed 0x1CF span
    for (let i = 0; i < 0x1cf - colorCount; i++) w.u8(0x20);

    w.u16le(0x0000);

    // 3-byte little-endian offset to the thumbnail/graphics section (patched later)
    const graphicsOffsetPos = w.tell();
    w.u8(0x00).u8(0x00).u8(0x00);

    w.u8(0x31).u8(0xff).u8(0xf0);

    w.i16le(width);
    w.i16le(height);
    w.i16le(0x01e0); // 480 - nominal design area width
    w.i16le(0x01b0); // 432 - nominal design area height (standard value; was 0x0140/320)

    // Initial positioning jump. This is NOT optional padding: a standard
    // reader treats the PEC stitch block as a fixed 15-byte header —
    // 3 marker bytes + 4 shorts + this 4-byte long-form jump — and skips
    // all 15 before it starts decoding deltas (PecReader.read_pec's
    // `f.seek(0x0F, 1)`). Omitting it left the header 4 bytes short, so the
    // reader consumed the first two stitch records as header and decoded
    // every remaining point shifted by the delta it had eaten.
    // Value matches PecWriter.write_pec_block's
    // `write_jump(-extends[0], -extends[1])`, in PEC screen space (+Y down,
    // so the design's yMax is the screen-space yMin).
    pecWriteRecord(w, -ext.xMin, ext.yMax, PEC_FLAG_JUMP);

    // stitch data
    pecEncodeStitches(w, stitches);

    // Patch the graphics offset: standard semantics are the stitch-block
    // LENGTH measured from PEC-relative 512 (the byte right after the
    // fixed-size PEC header), not "relative to the field's own position".
    // Matches pyembroidery's PecWriter.write_pec_block (stitch_block_length
    // = f.tell() - stitch_block_start_position, where
    // stitch_block_start_position == PEC-relative 512) and PecReader.read_pec
    // (stitch_block_end = read_int_24le(f) - 5 + f.tell()).
    const graphicsStart = w.tell();
    const pecBaseline = pecStart + 512;
    w.patch3le(graphicsOffsetPos, graphicsStart - pecBaseline);

    // blank thumbnails: 48x38, 1bpp => 6 bytes/row * 38 = 228 bytes each.
    // One master image plus one per colour. Blank (all zero) is acceptable.
    const bytesPerImage = 6 * 38;
    const imageCount = colorCount + 1;
    for (let n = 0; n < imageCount; n++) {
      for (let b = 0; b < bytesPerImage; b++) w.u8(0x00);
    }
  }

  // ---- PES v1 container -----------------------------------------------
  function encodePES(design) {
    const stitches = (design && design.stitches) || [];
    const colors = (design && design.colors) || [];
    const colorCount = Math.max(1, colors.length);
    const ext = extents(stitches);
    const width = ext.xMax - ext.xMin;
    const height = ext.yMax - ext.yMin;

    const w = new Writer();
    w.str("#PES0001");

    // 4-byte offset to the PEC section (patched after the header body).
    const pecStartPos = w.tell();
    w.u32le(0x00000000);

    // minimal v1 header body
    w.u16le(0x0001); // scale to fit page (nominal)
    w.u16le(0x0001); // hoop code (nominal)
    w.u16le(0xffff);
    w.u16le(0x0000);

    // --- CEmbOne section (design container / transform) ---
    w.lenStr("CEmbOne");
    // bounding rectangle (twice: extents + clip), in 0.1mm
    w.i16le(0).i16le(0).i16le(width).i16le(height);
    w.i16le(0).i16le(0).i16le(width).i16le(height);
    // affine transform: identity rotation/scale, translate to a nominal origin
    w.f32le(1).f32le(0);
    w.f32le(0).f32le(1);
    w.f32le(50).f32le(50);
    w.i16le(1);
    w.i16le(0).i16le(0);
    w.i16le(width).i16le(height);
    for (let i = 0; i < 8; i++) w.i16le(0);

    // --- CSewSeg section (stitch/colour block list) ---
    //
    // This carries the design's OWN points, unsplit — the sewability split
    // added 2026-09-12 lives in the PEC block only, deliberately. PEC is the
    // stream a machine sews and the one every standard reader decodes
    // (pystitch's PesReader ignores the PES header entirely and jumps to the
    // PEC block; so does pyembroidery's), which is why "longest sewn" is
    // measurable there and not here. Splitting CSewSeg as well would be an
    // unmeasurable change to a section nothing in this repo — or in the
    // cross-validation harness — reads back. It is not an oversight: if a
    // PE-Design-class editor that DOES read CSewSeg ever becomes part of the
    // evidence, split it there too and measure it.
    w.u16le(0xffff);
    w.u16le(0x0000);
    w.lenStr("CSewSeg");

    // group consecutive same-kind runs into segments, colour changes split blocks
    const segments = [];
    let colorIndex = 0;
    let run = null;
    for (const st of stitches) {
      const type = st.type || "stitch";
      if (type === "end") break;
      if (type === "color") { colorIndex++; run = null; continue; }
      const isJump = type === "jump" || type === "trim";
      const kind = isJump ? 1 : 0;
      if (!run || run.kind !== kind || run.colorIndex !== colorIndex) {
        run = { kind, colorIndex, points: [] };
        segments.push(run);
      }
      run.points.push([st.x | 0, -(st.y | 0)]);
    }

    w.u16le(colorCount);              // colour count
    w.u16le(segments.length & 0xffff); // block count
    for (const seg of segments) {
      w.u16le(seg.kind);                 // 0 = normal, 1 = jump
      w.u16le(seg.colorIndex & 0xffff);  // thread index
      w.u16le(seg.points.length & 0xffff);
      for (const p of seg.points) {
        w.i16le(p[0]);
        w.i16le(p[1]);
      }
    }
    w.u16le(0x0000);

    // --- PEC section ---
    const pecStart = w.tell();
    w.patch4le(pecStartPos, pecStart);
    writePEC(w, design);

    return Uint8Array.from(w.bytes);
  }

  return { encodePES, writePEC };
});
