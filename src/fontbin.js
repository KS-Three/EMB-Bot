// Compact binary font format (.embf) — see docs/superpowers/specs/
// 2026-07-27-font-library-expansion-design.md §4.1a. JSON stores coordinates
// as decimal text; this format quantizes to a Q-grid, delta-encodes each ring,
// and packs Int16 — measured 24.5x smaller than JSON before HTTP compression.
(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const MAGIC = "EMBF";
  const VERSION = 1;

  // A "ring" is a non-empty array whose every element is a [x, y] number pair.
  // This shape-based test (rather than key names like railA/rungs) keeps the
  // codec agnostic to the font schema — cols/rungs/runs.pts all match, and
  // future fields with point data are covered automatically.
  function isRing(v) {
    return Array.isArray(v) && v.length > 0 &&
      v.every((p) => Array.isArray(p) && p.length === 2 &&
        typeof p[0] === "number" && typeof p[1] === "number");
  }

  function quantizeFont(font, Q) {
    const q = Q || 4;
    return walk(font);
    function walk(v) {
      if (isRing(v)) return v.map((p) => [Math.round(p[0] * q) / q, Math.round(p[1] * q) / q]);
      if (Array.isArray(v)) return v.map(walk);
      if (v && typeof v === "object") {
        const o = {};
        for (const k of Object.keys(v)) o[k] = walk(v[k]);
        return o;
      }
      return v;
    }
  }

  function encodeFontBin(font, Q) {
    const q = Q || 4;
    const stream = []; // int16 values, dx dy pairs
    const skeleton = walk(font);
    function walk(v) {
      if (isRing(v)) {
        let px = 0, py = 0;
        for (let i = 0; i < v.length; i++) {
          const x = Math.round(v[i][0] * q), y = Math.round(v[i][1] * q);
          const dx = x - px, dy = y - py;
          if (dx < -32768 || dx > 32767 || dy < -32768 || dy > 32767)
            throw new Error("fontbin: delta overflow — ring jump exceeds Int16 at Q=" + q);
          stream.push(dx, dy);
          px = x; py = y;
        }
        return { __r: v.length };
      }
      if (Array.isArray(v)) return v.map(walk);
      if (v && typeof v === "object") {
        const o = {};
        for (const k of Object.keys(v)) o[k] = walk(v[k]);
        return o;
      }
      return v;
    }

    const metaBytes = utf8Encode(JSON.stringify(skeleton));
    const head = 4 + 1 + 1 + 2 + 4;
    const out = new Uint8Array(head + metaBytes.length + stream.length * 2);
    const dv = new DataView(out.buffer);
    out[0] = 69; out[1] = 77; out[2] = 66; out[3] = 70; // "EMBF"
    out[4] = VERSION;
    out[5] = q;
    dv.setUint32(8, metaBytes.length, true);
    out.set(metaBytes, head);
    let off = head + metaBytes.length;
    for (const v of stream) { dv.setInt16(off, v, true); off += 2; }
    return out;
  }

  function decodeFontBin(bytes) {
    const b = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
    if (b.length < 12 || String.fromCharCode(b[0], b[1], b[2], b[3]) !== MAGIC)
      throw new Error("fontbin: not an EMBF file");
    if (b[4] !== VERSION) throw new Error("fontbin: unsupported EMBF version " + b[4]);
    const q = b[5];
    const dv = new DataView(b.buffer, b.byteOffset, b.byteLength);
    const metaLen = dv.getUint32(8, true);
    const head = 12;
    const skeleton = JSON.parse(utf8Decode(b.subarray(head, head + metaLen)));
    let off = head + metaLen;
    function nextPair() {
      const dx = dv.getInt16(off, true), dy = dv.getInt16(off + 2, true);
      off += 4;
      return [dx, dy];
    }
    return walk(skeleton);
    function walk(v) {
      if (v && typeof v === "object" && !Array.isArray(v) &&
          typeof v.__r === "number" && Object.keys(v).length === 1) {
        const ring = [];
        let px = 0, py = 0;
        for (let i = 0; i < v.__r; i++) {
          const [dx, dy] = nextPair();
          px += dx; py += dy;
          ring.push([px / q, py / q]);
        }
        return ring;
      }
      if (Array.isArray(v)) return v.map(walk);
      if (v && typeof v === "object") {
        const o = {};
        for (const k of Object.keys(v)) o[k] = walk(v[k]);
        return o;
      }
      return v;
    }
  }

  // TextEncoder exists in browsers and Node >= 11; Buffer fallback is for
  // completeness only.
  function utf8Encode(s) {
    if (typeof TextEncoder !== "undefined") return new TextEncoder().encode(s);
    return new Uint8Array(Buffer.from(s, "utf8"));
  }
  function utf8Decode(b) {
    if (typeof TextDecoder !== "undefined") return new TextDecoder().decode(b);
    return Buffer.from(b).toString("utf8");
  }

  return { quantizeFont, encodeFontBin, decodeFontBin };
});
