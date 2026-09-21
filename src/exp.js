(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  // The RECORD limit: an EXP delta is one signed byte per axis, so a single
  // record cannot carry more than ±127 units. This bounds TRAVEL, and only
  // travel.
  const MAX_DELTA = 127;

  // The SEWABILITY ceiling, and the last encoder to get one.
  //
  // Nothing in the EXP format forces a split below its own ±127 (12.7 mm), so
  // until 2026-09-13 this file used MAX_DELTA for both jobs and emitted sewn
  // moves up to 12.7 mm — past `machine.MAX_STITCH_MM` (12.1), which is what
  // the machine can actually pull. `dst.js` has always split sewn moves at its
  // record's own ±121, and `pes.js` got `PEC_MAX_SEWN_DELTA = 121` on
  // 2026-09-12 (#465) for exactly this reason. EXP was the odd one out, and
  // that fix's own comment named it: *"121 rather than EXP's 127 so that a PES
  // file never carries a sewn move DST would have split."*
  //
  // Measured 2026-09-13 — one design, a 6-step sewn chain of 12.5 mm axis
  // moves, encoded in all three and decoded with pystitch:
  //   dst  12 sewn, worst axis 12.1 mm
  //   pes  12 sewn, worst axis 12.1 mm
  //   exp   6 sewn, worst axis 12.5 mm   <- over the ceiling
  // One design, three sew-outs, and only EXP's carried a move no machine can
  // pull — the same sentence pes.js records about PES before it was fixed.
  //
  // Kent's ruling 2026-09-13, the same call he made for PES the day before:
  // split at 121. Not a new physical constant (ROADMAP gate 1): 121 units is
  // `machine.MAX_STITCH_MM` 12.1, already shipped, and already what the other
  // two encoders enforce — this makes EXP agree with them rather than
  // inventing a number. `digitizer/tests/test_machine_wire.py` asserts all
  // three, and `test/crossval-stitch-formats.test.js` pins the behaviour.
  const EXP_MAX_SEWN_DELTA = 121;

  // Two's-complement signed byte.
  const sb = (v) => (v < 0 ? v + 256 : v);

  // Split (dx,dy) into steps of at most `limit` per axis that sum EXACTLY to
  // (dx,dy) and whose landing points follow the straight line between the two
  // ends. See src/dst.js's copy for why this exists: all three encoders
  // clamped the axes independently until 2026-09-20, which walks an L and puts
  // the file's thread off the line the Studio drew, with every count, extent
  // and endpoint still matching.
  //
  // Always returns at least one step: a NaN delta or a missing limit used to
  // make `n` NaN, skip the loop and hand the caller an empty array to
  // dereference. Identical to dst.js's copy on purpose —
  // test/encoder-split.test.js drives all three through one set of cases.
  function splitSteps(dx, dy, limit, minSteps) {
    const lim = limit || MAX_DELTA;
    const need = Math.max(Math.ceil(Math.abs(dx) / lim), Math.ceil(Math.abs(dy) / lim));
    let n = Math.max(minSteps || 1, 1, Number.isFinite(need) ? need : 1);
    for (;;) {
      const steps = [];
      let accX = 0, accY = 0, ok = true;
      for (let i = 1; i <= n; i++) {
        const sx = Math.round((dx * i) / n) - accX;
        const sy = Math.round((dy * i) / n) - accY;
        if (Math.abs(sx) > lim || Math.abs(sy) > lim) { ok = false; break; }
        steps.push([sx, sy]);
        accX += sx; accY += sy;
      }
      if (ok) return steps;
      n++;
    }
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
        const dx = targetX - lastX;
        const dy = targetY - lastY;
        // A zero-delta trim still writes no jump at all, exactly as before.
        if (dx !== 0 || dy !== 0) {
          for (const [sx, sy] of splitSteps(dx, dy, MAX_DELTA, 1)) {
            records.push(jumpRecord(sx, sy));
          }
        }
        lastX = targetX;
        lastY = targetY;
        continue;
      }

      const isJump = st.type === "jump";

      const dx = targetX - lastX;
      const dy = targetY - lastY;

      // Travel splits at the RECORD limit; a sewn move splits at the
      // SEWABILITY ceiling, which is lower. Same shape as pes.js's
      // `chained ? PEC_MAX_SEWN_DELTA : PEC_MAX_DELTA`.
      const limit = isJump ? MAX_DELTA : EXP_MAX_SEWN_DELTA;
      for (const [sx, sy] of splitSteps(dx, dy, limit, 1)) {
        records.push(isJump ? jumpRecord(sx, sy) : stitchRecord(sx, sy));
      }
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
    // Exported for test/encoder-split.test.js — see the note on dst.js's copy.
    splitSteps,
  };
});
