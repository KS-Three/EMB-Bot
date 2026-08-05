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
  // moves (e.g. jumps across a full-back panel) are split into intermediate
  // jump hops, mirroring the analogous split in dst.js's encodeDST.
  const PEC_MAX_DELTA = 2047;

  function pecClampStep(delta) {
    if (delta > PEC_MAX_DELTA) return PEC_MAX_DELTA;
    if (delta < -PEC_MAX_DELTA) return -PEC_MAX_DELTA;
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
    let emitted = false;
    for (const st of stitches) {
      const type = st.type || "stitch";
      if (type === "end") break;
      if (type === "color") {
        w.u8(0xfe).u8(0xb0).u8(needleToggle);
        needleToggle = needleToggle === 2 ? 1 : 2;
        continue;
      }
      const sx = st.x | 0;
      const sy = -(st.y | 0); // flip Y to PEC screen convention
      const flag = type === "trim" ? PEC_FLAG_TRIM : type === "jump" ? PEC_FLAG_JUMP : 0;

      let dx = sx - px;
      let dy = sy - py;

      // Emit intermediate jump hops for deltas outside the 12-bit long-form
      // range. These are pure travel moves, so they always carry the jump
      // flag regardless of what the final record's flag will be.
      while (Math.abs(dx) > PEC_MAX_DELTA || Math.abs(dy) > PEC_MAX_DELTA) {
        const stepX = pecClampStep(dx);
        const stepY = pecClampStep(dy);
        pecWriteRecord(w, stepX, stepY, PEC_FLAG_JUMP);
        px += stepX;
        py += stepY;
        dx = sx - px;
        dy = sy - py;
      }

      pecWriteRecord(w, dx, dy, flag);
      px = sx;
      py = sy;
      emitted = true;
    }
    void emitted;
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
