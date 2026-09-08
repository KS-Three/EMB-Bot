(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const MAX_DELTA = 121;

  // Signed-weight -> [byteIndex, bitMask]. X is the LOW nibble of every byte
  // and Y the HIGH nibble, bit-for-bit with `pystitch.DstWriter.encode_record`
  // (and with libembroidery, EduTech and achatina — the four sources
  // docs/dst-axis-verdict-2026-07-31.md cross-checked).
  //
  // Byte0: x+1=0x01 x-1=0x02 x+9=0x04 x-9=0x08   y+1=0x80 y-1=0x40 y+9=0x20 y-9=0x10
  // Byte1: x+3=0x01 x-3=0x02 x+27=0x04 x-27=0x08 y+3=0x80 y-3=0x40 y+27=0x20 y-27=0x10
  // Byte2: x+81=0x04 x-81=0x08                   y+81=0x20 y-81=0x10
  //
  // THESE TWO TABLES WERE SWAPPED until 2026-09-08 -- X in the high nibble,
  // Y in the low one. That is the transposition the 2026-07-31 verdict
  // identified, and it meant EMB-Bot round-tripped only itself: a standard
  // reader saw every design a quarter turn round AND mirrored, letters
  // backwards. Rendered both ways that day through pystitch on a "FRITSCH"
  // lettering export -- the old bytes draw a vertical column of reversed
  // letters, the new ones draw FRITSCH upright at 127.2 x 22.6 mm, the design's
  // own size. `encodeRecord` is now byte-identical to pystitch across ten
  // deltas, and the crossval DST control reads "identity" beside PES and EXP.
  //
  // `dstimport.js`'s `decodeDelta` was swapped in the same commit; the two are
  // one codec and must move together.
  const X_WEIGHTS = {
    "1":  [0, 0x01], "-1":  [0, 0x02],
    "9":  [0, 0x04], "-9":  [0, 0x08],
    "3":  [1, 0x01], "-3":  [1, 0x02],
    "27": [1, 0x04], "-27": [1, 0x08],
    "81": [2, 0x04], "-81": [2, 0x08],
  };
  const Y_WEIGHTS = {
    "1":  [0, 0x80], "-1":  [0, 0x40],
    "9":  [0, 0x20], "-9":  [0, 0x10],
    "3":  [1, 0x80], "-3":  [1, 0x40],
    "27": [1, 0x20], "-27": [1, 0x10],
    "81": [2, 0x20], "-81": [2, 0x10],
  };
  // Weight per balanced-ternary digit position i (3^i), i = 0..4.
  const MAGNITUDES = [1, 3, 9, 27, 81];

  // Balanced-ternary digits of v: digits[i] in {-1,0,1} for weight 3^i (i=0..4).
  function balancedTernaryDigits(v) {
    const digits = [];
    let n = v;
    for (let i = 0; i < 5; i++) {
      let rem = ((n % 3) + 3) % 3; // 0,1,2
      let d;
      if (rem === 0) { d = 0; n = n / 3; }
      else if (rem === 1) { d = 1; n = (n - 1) / 3; }
      else { d = -1; n = (n + 1) / 3; } // rem === 2
      digits.push(d);
      n = Math.trunc(n);
    }
    return digits; // [w1, w3, w9, w27, w81]
  }

  function decompose(value, weights, bytes) {
    const digits = balancedTernaryDigits(value);
    for (let i = 0; i < MAGNITUDES.length; i++) {
      const d = digits[i];
      if (d === 0) continue;
      const [bi, mask] = weights[String(d * MAGNITUDES[i])];
      bytes[bi] |= mask;
    }
  }

  function encodeRecord(dx, dy, flag) {
    if (dx < -MAX_DELTA || dx > MAX_DELTA || dy < -MAX_DELTA || dy > MAX_DELTA) {
      throw new RangeError(
        "DST record delta out of range (-121..121): dx=" + dx + " dy=" + dy
      );
    }
    const bytes = new Uint8Array(3);
    decompose(dx, X_WEIGHTS, bytes);
    decompose(dy, Y_WEIGHTS, bytes);
    // Byte2 low bits 0x03 always set for stitch/jump/color.
    bytes[2] |= 0x03;
    // 0x83 jump, 0xC3 colour change, 0x03 plain stitch. The colour flag is
    // 0xC0 -- BOTH high bits -- not 0x40: a colour change is a jump that also
    // stops the machine, so it carries the jump bit too.
    //
    // This wrote 0x40 (=> 0x43) until 2026-09-08, which is not a colour change
    // in any other reader. Measured that day with pystitch on a two-colour
    // design: 0 COLOR_CHANGE and one spurious SEQUIN_MODE toggle, so every
    // multi-colour .dst EMB-Bot wrote sewed straight through on someone else's
    // machine -- no stop, no thread change, the whole design in one colour.
    // With 0xC3: 1 COLOR_CHANGE, no sequin, stitch count unchanged.
    //
    // Found by docs/dst-axis-verdict-2026-07-31.md as its "bonus finding" and
    // left open since, because it was filed with the axis question. It is NOT
    // the axis question: this changes no geometry, and dstimport.js
    // already reads the standard code (it tests `b2 & 0x40` BEFORE the 0x80
    // jump test, so 0xC3 lands as a colour change), so EMB-Bot's own decode of
    // its own file is byte-identical before and after.
    if (flag === "jump") bytes[2] |= 0x80;
    else if (flag === "color") bytes[2] |= 0xc0;
    return bytes;
  }

  function endRecord() {
    return Uint8Array.from([0x00, 0x00, 0xf3]);
  }

  function field(key, value) {
    return key + ":" + value + "\r";
  }

  function pad(num, width) {
    const s = String(Math.abs(Math.round(num)));
    return s.length >= width ? s.slice(-width) : "0".repeat(width - s.length) + s;
  }

  function signed(num) {
    const n = Math.round(num);
    const sign = n < 0 ? "-" : "+";
    return sign + pad(n, 5);
  }

  function buildHeader(meta) {
    const label = String(meta.label || "").slice(0, 16);
    let s = "";
    s += field("LA", label);
    s += field("ST", pad(meta.stitchCount || 0, 7));
    s += field("CO", pad(meta.colorCount || 0, 3));
    s += field("+X", pad(meta.xMax || 0, 5));
    s += field("-X", pad(meta.xMin || 0, 5));
    s += field("+Y", pad(meta.yMax || 0, 5));
    s += field("-Y", pad(meta.yMin || 0, 5));
    s += field("AX", signed(0));
    s += field("AY", signed(0));
    s += field("MX", signed(0));
    s += field("MY", signed(0));
    s += field("PD", "******");

    const header = new Uint8Array(512).fill(0x20); // space-padded
    for (let i = 0; i < s.length && i < 512; i++) {
      header[i] = s.charCodeAt(i) & 0xff;
    }
    return header;
  }

  function clampStep(delta) {
    if (delta > MAX_DELTA) return MAX_DELTA;
    if (delta < -MAX_DELTA) return -MAX_DELTA;
    return delta;
  }

  // Split a trim's total (dx,dy) into >=3 jump records, each within +/-MAX_DELTA,
  // whose signed deltas sum exactly to (dx,dy). Tajima convention: a machine
  // reads >=3 consecutive jumps as a trim command. Zero delta -> 3 zero jumps.
  function splitTrim(dx, dy) {
    const n = Math.max(
      3,
      Math.ceil(Math.abs(dx) / MAX_DELTA),
      Math.ceil(Math.abs(dy) / MAX_DELTA)
    );
    const steps = [];
    let accX = 0, accY = 0;
    for (let i = 1; i <= n; i++) {
      const sx = Math.round((dx * i) / n) - accX;
      const sy = Math.round((dy * i) / n) - accY;
      steps.push([sx, sy]);
      accX += sx; accY += sy;
    }
    return steps;
  }

  function encodeDST(design) {
    const stitches = (design && design.stitches) || [];
    const colors = (design && design.colors) || [];
    const records = [];

    let lastX = 0;
    let lastY = 0;
    // Whether the previous EMITTED record laid thread — the chain rule the
    // oversized-move split below needs. Starts false: the file's first move is
    // travel to wherever the design begins.
    let lastWasStitch = false;
    let xMin = 0, xMax = 0, yMin = 0, yMax = 0;
    let haveExtents = false;

    for (let i = 0; i < stitches.length; i++) {
      const st = stitches[i];

      // Stop at the terminal sentinel, the way exp.js and pes.js both already
      // do. Without this it fell through to the "stitch" branch and was
      // written as a real needle penetration -- and `endRecord()` below is
      // appended unconditionally anyway, so nothing needs it.
      //
      // The 2026-08-04 verdict deferred this as "one extra phantom stitch",
      // which was true of LETTERING: buildLetteringDesign appends no sentinel
      // at all, and where one exists it sits on the last stitch with a zero
      // delta. buildImportedDesign puts it at the ELEMENT'S OFFSET, so on
      // every imported, digitized, shape or manual project it lands somewhere
      // else entirely. Measured 2026-09-08 on an off-origin bar with the
      // sentinel at (0,0): pystitch read a STITCH at the origin 64.0 mm from
      // the previous one and 51.5 mm from the design's centre, reached by a
      // run of jumps -- a stray penetration with 6 cm of travel to get to it.
      //
      // Placed BEFORE the extents update on purpose: the sentinel was also
      // widening the header's declared bounding box to a corner the design
      // does not occupy.
      if (st.type === "end") break;

      const targetX = st.x | 0;
      const targetY = st.y | 0;

      if (!haveExtents) {
        xMin = xMax = targetX;
        yMin = yMax = targetY;
        haveExtents = true;
      } else {
        if (targetX < xMin) xMin = targetX;
        if (targetX > xMax) xMax = targetX;
        if (targetY < yMin) yMin = targetY;
        if (targetY > yMax) yMax = targetY;
      }

      // Trim: Tajima convention is >=3 consecutive jump records covering the
      // move delta. Always emit at least 3 jumps so the machine reads a trim.
      if (st.type === "trim") {
        for (const [sx, sy] of splitTrim(targetX - lastX, targetY - lastY)) {
          records.push(encodeRecord(sx, sy, "jump"));
        }
        lastX = targetX;
        lastY = targetY;
        lastWasStitch = false; // a trim cuts the chain
        continue;
      }

      const flag = st.type === "color" ? "color" : st.type === "jump" ? "jump" : "stitch";

      // A move too big for one record is split into intermediate ones. What
      // those intermediates ARE is the whole question, and this emitted
      // "jump" for every case until 2026-09-07 — including a STITCH, which
      // silently turned thread the design asked for into travel.
      //
      // exp.js's identical loop has always split a stitch into STITCHES
      // (`isJump ? jumpRecord : stitchRecord`); only this one did not, so one
      // design produced two different sew-outs. Measured that day on a real
      // "AB" monogram at Full Back (304.9 x 146.2 mm, 5,830 stitches), decoded
      // with pystitch:
      //
      //   .dst  5,830 stitches, 3,769 JUMPS, longest sewn segment 16.7 mm
      //   .exp  9,426 stitches,     8 jumps, longest sewn segment 18.0 mm
      //   .pes  5,830 stitches,     3 jumps, longest sewn segment 51.1 mm
      //
      // Three encoders, three answers. This one now matches exp.js: a stitch
      // splits into stitches, a jump into jumps. It is byte-identical for
      // every design whose stitches already fit a record — which is every
      // quick start and every crossval fixture; the split only fires on
      // segments no machine could sew in one go anyway.
      //
      // It splits as stitches only when the move CONTINUES a sewn chain —
      // this record is a stitch AND the last one emitted was too. The move to
      // the FIRST stitch after a jump, a trim, a colour change or the start of
      // the file is TRAVEL: there is nothing to sew between where the needle
      // was and where the design begins, and splitting it into stitches would
      // draw a line across the garment from the origin. (Same chain rule
      // `designToStrands` uses; the old unconditional "jump" was right for
      // this one case by accident, and `test/dstimport.test.js`'s
      // off-origin-centering fixture is exactly it.)
      //
      // A "color" record splits as JUMPS, never as itself: intermediate
      // colour records would insert extra machine stops. In practice colour
      // records carry a zero delta, so that is a guard rather than a path.
      //
      // Whether the ENGINE should emit such segments at all is the bigger
      // question and not this function's: a 17.9 mm satin crossing is
      // unsewable however it is encoded. Measured and recorded for Kent —
      // 18 of 85 shipped fonts produce them at large sizes, and a
      // single-letter monogram at left-chest size gives 278 of 1,607.
      // "end" reaches the "stitch" flag by fallthrough (this encoder has never
      // special-cased it, and combine.js documents why that matters), but it
      // is a terminator, not thread — so it is excluded here even though a
      // real design puts it at the last stitch's own position, delta zero.
      const isStitch = flag === "stitch" && st.type !== "end";
      const splitFlag = isStitch && lastWasStitch ? "stitch" : "jump";
      let dx = targetX - lastX;
      let dy = targetY - lastY;
      while (Math.abs(dx) > MAX_DELTA || Math.abs(dy) > MAX_DELTA) {
        const stepX = clampStep(dx);
        const stepY = clampStep(dy);
        records.push(encodeRecord(stepX, stepY, splitFlag));
        lastX += stepX;
        lastY += stepY;
        dx = targetX - lastX;
        dy = targetY - lastY;
      }

      records.push(encodeRecord(dx, dy, flag));
      lastWasStitch = isStitch;
      lastX = targetX;
      lastY = targetY;
    }

    records.push(endRecord());

    const header = buildHeader({
      label: (design && design.label) || "EMBBOT",
      stitchCount: stitches.length,
      colorCount: colors.length,
      xMin, xMax, yMin, yMax,
    });

    const total = 512 + records.length * 3;
    const out = new Uint8Array(total);
    out.set(header, 0);
    let off = 512;
    for (const r of records) {
      out.set(r, off);
      off += 3;
    }
    return out;
  }

  return {
    encodeRecord,
    endRecord,
    buildHeader,
    encodeDST,
  };
});
