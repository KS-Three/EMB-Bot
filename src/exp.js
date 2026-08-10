(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const MAX_DELTA = 127;

  // Two's-complement signed byte.
  const sb = (v) => (v < 0 ? v + 256 : v);

  function clampStep(delta) {
    if (delta > MAX_DELTA) return MAX_DELTA;
    if (delta < -MAX_DELTA) return -MAX_DELTA;
    return delta;
  }

  function colorRecord() {
    return Uint8Array.from([0x80, 0x01, 0x00, 0x00]);
  }

  function jumpRecord(dx, dy) {
    return Uint8Array.from([0x80, 0x04, sb(dx), sb(dy)]);
  }

  function trimRecord() {
    // Melco-convention 4-byte control record (0x80-prefixed controls are
    // fixed 4 bytes: 0x80, code, then 2 payload bytes). The previous 2-byte
    // form (0x80, 0x03) isn't a control code pyembroidery-convention readers
    // know; they consume 2 bytes of the following record as this one's
    // payload and abort the rest of the file. See
    // docs/pes-crossval-verdict-2026-08-04.md section 4.
    return Uint8Array.from([0x80, 0x80, 0x07, 0x00]);
  }

  function stitchRecord(dx, dy) {
    return Uint8Array.from([sb(dx), sb(dy)]);
  }

  function encodeEXP(design) {
    const stitches = (design && design.stitches) || [];
    const records = [];

    let lastX = 0;
    let lastY = 0;

    for (let i = 0; i < stitches.length; i++) {
      const st = stitches[i];

      // The terminal `{type:"end"}` sentinel `stitchModel.js` always appends
      // is a design-list marker, not a real stitch -- pes.js's own encoder
      // already stops here the same way (src/pes.js, both its CSewSeg and
      // decoder loops). Without this, it fell through to the generic path
      // below and got written as a real zero-delta stitch record, which
      // standard EXP readers then decode as one extra phantom stitch beyond
      // the design's real count. See docs/pes-crossval-verdict-2026-08-04.md
      // section 4's "shared quirk with DST" note -- DST has the same gap but
      // is deliberately left alone (Kent's call, every existing EMB-Bot DST
      // is affected); EXP has no importer in this codebase, so fixing it
      // here carries none of that migration risk.
      if (st.type === "end") break;

      const targetX = st.x | 0;
      const targetY = st.y | 0;

      if (st.type === "color") {
        records.push(colorRecord());
        // Color-change control record carries no positional delta.
        continue;
      }

      // Trim: emit the Melco trim control, then any positional delta as
      // jump record(s). Separate the trim command from the travel move.
      if (st.type === "trim") {
        records.push(trimRecord());
        let dx = targetX - lastX;
        let dy = targetY - lastY;
        while (Math.abs(dx) > MAX_DELTA || Math.abs(dy) > MAX_DELTA) {
          const stepX = clampStep(dx);
          const stepY = clampStep(dy);
          records.push(jumpRecord(stepX, stepY));
          lastX += stepX;
          lastY += stepY;
          dx = targetX - lastX;
          dy = targetY - lastY;
        }
        if (dx !== 0 || dy !== 0) records.push(jumpRecord(dx, dy));
        lastX = targetX;
        lastY = targetY;
        continue;
      }

      const isJump = st.type === "jump";

      let dx = targetX - lastX;
      let dy = targetY - lastY;

      // Split any move with |delta|>127 into multiple records stepping toward the target.
      while (Math.abs(dx) > MAX_DELTA || Math.abs(dy) > MAX_DELTA) {
        const stepX = clampStep(dx);
        const stepY = clampStep(dy);
        records.push(isJump ? jumpRecord(stepX, stepY) : stitchRecord(stepX, stepY));
        lastX += stepX;
        lastY += stepY;
        dx = targetX - lastX;
        dy = targetY - lastY;
      }

      records.push(isJump ? jumpRecord(dx, dy) : stitchRecord(dx, dy));
      lastX = targetX;
      lastY = targetY;
    }

    let total = 0;
    for (const r of records) total += r.length;
    const out = new Uint8Array(total);
    let off = 0;
    for (const r of records) {
      out.set(r, off);
      off += r.length;
    }
    return out;
  }

  return {
    encodeEXP,
  };
});
