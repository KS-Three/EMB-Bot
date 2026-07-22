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

  function pecWriteRecord(w, dx, dy, isJump) {
    if (!isJump && dx < 64 && dx > -64 && dy < 64 && dy > -64) {
      w.u8(dx & 0x7f);
      w.u8(dy & 0x7f);
    } else {
      let vx = dx & 0x0fff;
      vx |= 0x8000;
      if (isJump) vx |= 0x2000;
      w.u8((vx >> 8) & 0xff).u8(vx & 0xff);
      let vy = dy & 0x0fff;
      vy |= 0x8000;
      if (isJump) vy |= 0x2000;
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
      const isJump = type === "jump" || type === "trim";

      let dx = sx - px;
      let dy = sy - py;

      // Emit intermediate jump hops for deltas outside the 12-bit long-form range.
      while (Math.abs(dx) > PEC_MAX_DELTA || Math.abs(dy) > PEC_MAX_DELTA) {
        const stepX = pecClampStep(dx);
        const stepY = pecClampStep(dy);
        pecWriteRecord(w, stepX, stepY, true);
        px += stepX;
        py += stepY;
        dx = sx - px;
        dy = sy - py;
      }

      pecWriteRecord(w, dx, dy, isJump);
      px = sx;
      py = sy;
      emitted = true;
    }
    void emitted;
    w.u8(0xff); // end of stitch data
  }

  // ---- PEC section ----------------------------------------------------
  function writePEC(w, design) {
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
      // Best-effort Brother palette index; fall back to a mid value.
      const idx = typeof c.paletteIndex === "number" ? c.paletteIndex : (i % 64) + 1;
      w.u8(idx & 0xff);
    }
    // pad colour table region out to the fixed 0x1CF span
    for (let i = 0; i <= 0x1cf - colorCount; i++) w.u8(0x20);

    w.u16le(0x0000);

    // 3-byte little-endian offset to the thumbnail/graphics section (patched later)
    const graphicsOffsetPos = w.tell();
    w.u8(0x00).u8(0x00).u8(0x00);

    w.u8(0x31).u8(0xff).u8(0xf0);

    w.i16le(width);
    w.i16le(height);
    w.i16le(0x01e0); // 480 - nominal design area width
    w.i16le(0x0140); // 320 - nominal design area height
    // start x/y as big-endian, high nibble flag 0x9000 (best-effort)
    w.u16be(0x9000 | 0x0000);
    w.u16be(0x9000 | 0x0000);

    // stitch data
    pecEncodeStitches(w, stitches);

    // patch graphics offset (relative to the offset field location)
    const graphicsStart = w.tell();
    w.patch3le(graphicsOffsetPos, graphicsStart - graphicsOffsetPos + 2);

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
