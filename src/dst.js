(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const MAX_DELTA = 121;

  // Signed-weight -> [byteIndex, bitMask], from the authoritative bit-weight table.
  // Byte0: x+1=0x80 x-1=0x40 x+9=0x20 x-9=0x10  y-9=0x08 y+9=0x04 y-1=0x02 y+1=0x01
  // Byte1: x+3=0x80 x-3=0x40 x+27=0x20 x-27=0x10 y-27=0x08 y+27=0x04 y-3=0x02 y+3=0x01
  // Byte2: x+81=0x20 x-81=0x10 y-81=0x08 y+81=0x04
  const X_WEIGHTS = {
    "1":  [0, 0x80], "-1":  [0, 0x40],
    "9":  [0, 0x20], "-9":  [0, 0x10],
    "3":  [1, 0x80], "-3":  [1, 0x40],
    "27": [1, 0x20], "-27": [1, 0x10],
    "81": [2, 0x20], "-81": [2, 0x10],
  };
  const Y_WEIGHTS = {
    "9":  [0, 0x04], "-9":  [0, 0x08],
    "1":  [0, 0x01], "-1":  [0, 0x02],
    "27": [1, 0x04], "-27": [1, 0x08],
    "3":  [1, 0x01], "-3":  [1, 0x02],
    "81": [2, 0x04], "-81": [2, 0x08],
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
    if (flag === "jump") bytes[2] |= 0x80;
    else if (flag === "color") bytes[2] |= 0x40;
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
    let xMin = 0, xMax = 0, yMin = 0, yMax = 0;
    let haveExtents = false;

    for (let i = 0; i < stitches.length; i++) {
      const st = stitches[i];
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
        continue;
      }

      const flag = st.type === "color" ? "color" : st.type === "jump" ? "jump" : "stitch";

      // Emit intermediate jump records for oversized moves.
      let dx = targetX - lastX;
      let dy = targetY - lastY;
      while (Math.abs(dx) > MAX_DELTA || Math.abs(dy) > MAX_DELTA) {
        const stepX = clampStep(dx);
        const stepY = clampStep(dy);
        records.push(encodeRecord(stepX, stepY, "jump"));
        lastX += stepX;
        lastY += stepY;
        dx = targetX - lastX;
        dy = targetY - lastY;
      }

      records.push(encodeRecord(dx, dy, flag));
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
