(function (root, factory) {
  const api = factory(root);
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function (root) {
  // Export read-back: after dst.js / exp.js / pes.js write a stitch file, read
  // the BYTES back and refuse to hand the file out if they disagree with the
  // design that was written (Kent, 2026-11-05: block the download; a file that
  // fails its own read-back is broken, not low quality).
  //
  // The expected values come from the in-memory design alone, by arithmetic on
  // its stitches. They do not call the encoders' splitters, so a regression in
  // a splitter, a record packer or a header field shows up as a mismatch rather
  // than agreeing with itself. The readers are the repo's existing ones: the DST
  // record walker (`readDSTRecords`, dstimport.js, on the bit table the
  // 2026-09-08 axis fix made pystitch-exact) and the EXP and PES stream readers
  // lifted from tools/file-cut-census.mjs, the harness the cut census has used
  // since 2026-10-06. Nothing here is a new codec.
  //
  // WHAT THIS IS NOT. It is a same-repo check: a writer and its reader can share
  // a misreading of the format, which is how the DST axis bug lived for months
  // (CLAUDE.md footgun 1). The independent read is the service's: `/export`
  // re-reads with pystitch. This one catches a writer that does not write what
  // it was handed, which is the failure a customer cannot see until the machine.
  //
  // THE CHECKS, per format (units are 0.1 mm; 121 units is 12.1 mm):
  //   stitch_count  sewn records vs the design's stitches plus the intermediates
  //                 a chained move longer than 121 units must split into
  //   trim_count    trims; trim_order: the sewn count each trim follows
  //   color_count   colour-change records; color_order: the sewn count before each
  //   stitch_positions  every design stitch lands where the design put it, in order
  //   longest_stitch  no sewn move that continues a sewn run exceeds 121 units
  //   bounding_box  the sewn stitches' extents equal the design's
  //   dst only: readable (end record, whole records), header_bbox (+X -X +Y -Y),
  //   header_stitch_count (ST)
  // `trim_count` reads a DST by the writer's own jumps-per-trim: a run of N
  // consecutive jump records is a trim, so a file written at 1 or 2 is read at 1
  // or 2. A design `jump` is also one jump record, so at N=1 it reads as a trim
  // on BOTH sides; the check compares the two readings of one rule.
  const MAX_SEWN = 121;
  const DEFAULT_TRIM_JUMPS = 3;
  const FORMATS = ["dst", "exp", "pes"];

  const dstimport = () => {
    if (typeof module !== "undefined" && module.exports) return require("./dstimport.js");
    return root.EMB;
  };

  // Records a move needs at a per-record limit: ceil of the larger axis, never
  // fewer than one. The encoders' splitSteps never needs more (rounding the
  // running total keeps every step within ceil(delta / n)).
  function recordsFor(dx, dy, lim) {
    return Math.max(1, Math.ceil(Math.abs(dx) / lim), Math.ceil(Math.abs(dy) / lim));
  }

  function jumpsPerTrim(n) {
    const v = typeof n === "boolean" ? NaN : Number(n);
    return Number.isInteger(v) && v >= 1 && v <= 10 ? v : DEFAULT_TRIM_JUMPS;
  }

  // Counts what a record stream means. DST has no trim opcode, so there a trim
  // is a run of `n` or more jump records; EXP and PES write the trim itself.
  function counter(explicitTrims, n) {
    let run = 0, sewn = 0, tokens = 0;
    const trimAt = [], colorAt = [];
    return {
      add(kind, count) {
        const c = count || 1;
        tokens += c;
        if (kind === "J") { if (!explicitTrims) run += c; return; }
        if (!explicitTrims && run >= n) trimAt.push(sewn);
        run = 0;
        if (kind === "S") sewn += c;
        else if (kind === "C") colorAt.push(sewn);
        else if (kind === "T") trimAt.push(sewn);
      },
      finish() {
        if (!explicitTrims && run >= n) trimAt.push(sewn);
        run = 0;
        return { stitches: sewn, trimAt, colorAt, tokens };
      },
    };
  }

  function designEvents(design) {
    const out = [];
    const st = (design && design.stitches) || [];
    for (let i = 0; i < st.length; i++) {
      const s = st[i];
      if (s.type === "end") break;
      out.push({
        kind: s.type === "color" ? "C" : s.type === "trim" ? "T" : s.type === "jump" ? "J" : "S",
        x: s.x | 0,
        y: s.y | 0,
      });
    }
    return out;
  }

  // What the file MUST say, from the design alone.
  function expectedExport(design, format, opts) {
    const o = opts || {};
    const explicit = format !== "dst";
    const n = format === "dst" ? jumpsPerTrim(o.jumpsPerTrim) : DEFAULT_TRIM_JUMPS;
    const ev = designEvents(design);
    const cnt = counter(explicit, n);
    let lx = 0, ly = 0, prevS = false;
    let bx0 = Infinity, bx1 = -Infinity, by0 = Infinity, by1 = -Infinity;
    let ex0 = 0, ex1 = 0, ey0 = 0, ey1 = 0;
    const landings = [];
    for (let i = 0; i < ev.length; i++) {
      const e = ev[i];
      if (i === 0) { ex0 = ex1 = e.x; ey0 = ey1 = e.y; }
      else {
        if (e.x < ex0) ex0 = e.x;
        if (e.x > ex1) ex1 = e.x;
        if (e.y < ey0) ey0 = e.y;
        if (e.y > ey1) ey1 = e.y;
      }
      const dx = e.x - lx, dy = e.y - ly;
      const recs = recordsFor(dx, dy, MAX_SEWN);
      if (e.kind === "S") {
        landings.push(e.x, e.y);
        if (e.x < bx0) bx0 = e.x;
        if (e.x > bx1) bx1 = e.x;
        if (e.y < by0) by0 = e.y;
        if (e.y > by1) by1 = e.y;
        if (prevS) cnt.add("S", recs);
        else {
          // travel into a run: every record before the last is a jump
          if (!explicit && recs > 1) cnt.add("J", recs - 1);
          cnt.add("S", 1);
        }
        prevS = true;
        lx = e.x; ly = e.y;
        continue;
      }
      prevS = false;
      if (e.kind === "C") {
        if (explicit) cnt.add("C", 1);
        else {
          if (recs > 1) cnt.add("J", recs - 1);
          cnt.add("C", 1);
          lx = e.x; ly = e.y;
        }
      } else if (e.kind === "T") {
        if (explicit) cnt.add("T", 1);
        else cnt.add("J", Math.max(n, recs));
        lx = e.x; ly = e.y;
      } else { // J
        if (!explicit) cnt.add("J", recs);
        lx = e.x; ly = e.y;
      }
    }
    const done = cnt.finish();
    return {
      format,
      jumpsPerTrim: n,
      stitches: done.stitches,
      trimAt: done.trimAt,
      colorAt: done.colorAt,
      records: done.tokens,
      sewnBox: bx0 === Infinity ? null : [bx0, by0, bx1, by1],
      landings,
      // DST header extents, the writer's convention: every event, absolute values.
      headerBox: [Math.abs(ex1), Math.abs(ex0), Math.abs(ey1), Math.abs(ey0)],
      hasEvents: ev.length > 0,
    };
  }

  // ---- readers ---------------------------------------------------------------
  // Each returns [{ kind: S|J|T|C, dx, dy, x, y }], design frame (+y up),
  // absolute from the file's origin.
  function readEXPRecords(bytes) {
    const out = [];
    const sb = (v) => (v > 127 ? v - 256 : v);
    let x = 0, y = 0;
    let i = 0;
    while (i < bytes.length) {
      if (bytes[i] !== 0x80) {
        if (i + 1 >= bytes.length) throw new Error("EXP ends in the middle of a record");
        const dx = sb(bytes[i]), dy = sb(bytes[i + 1]);
        x += dx; y += dy;
        out.push({ kind: "S", dx, dy, x, y });
        i += 2;
        continue;
      }
      if (i + 3 >= bytes.length) throw new Error("EXP ends in the middle of a control record");
      const code = bytes[i + 1];
      if (code === 0x01) out.push({ kind: "C", dx: 0, dy: 0, x, y });
      else if (code === 0x80) out.push({ kind: "T", dx: 0, dy: 0, x, y });
      else if (code === 0x04) {
        const dx = sb(bytes[i + 2]), dy = sb(bytes[i + 3]);
        x += dx; y += dy;
        out.push({ kind: "J", dx, dy, x, y });
      } else throw new Error("EXP has a control this reader does not know, 0x" + code.toString(16));
      i += 4;
    }
    return out;
  }

  function readPESRecords(bytes) {
    if (!bytes || bytes.length < 12 || String.fromCharCode(bytes[0], bytes[1], bytes[2], bytes[3], bytes[4], bytes[5], bytes[6], bytes[7]) !== "#PES0001") {
      throw new Error("PES is missing its #PES0001 signature");
    }
    const pec = (bytes[8] | (bytes[9] << 8) | (bytes[10] << 16) | (bytes[11] << 24)) >>> 0;
    // past the label, the colours, the block's header and its initial jump
    let i = pec + 532;
    if (i > bytes.length) throw new Error("PES points past its own end");
    const out = [];
    let x = 0, y = 0, ended = false;
    const axis = () => {
      const b = bytes[i++];
      if (!(b & 0x80)) return [b >= 0x40 ? b - 0x80 : b, 0];
      const v = (b << 8) | bytes[i++], d = v & 0x0fff;
      return [d >= 0x800 ? d - 0x1000 : d, v & 0x7000];
    };
    while (i < bytes.length) {
      if (bytes[i] === 0xff) { ended = true; break; }
      if (bytes[i] === 0xfe && bytes[i + 1] === 0xb0) { out.push({ kind: "C", dx: 0, dy: 0, x, y }); i += 3; continue; }
      const [dx, fx] = axis(), [dyRaw, fy] = axis(), f = fx | fy;
      const dy = -dyRaw; // PEC is +y down
      x += dx; y += dy;
      out.push({ kind: f & 0x2000 ? "T" : f & 0x1000 ? "J" : "S", dx, dy, x, y });
    }
    if (!ended) throw new Error("PES stitch stream has no end byte");
    return out;
  }

  function readExport(bytes, format, opts) {
    const o = opts || {};
    if (format === "dst") {
      const r = dstimport().readDSTRecords(bytes);
      return { records: r.records, header: r.header, ended: r.ended, tail: r.tail };
    }
    if (format === "exp") return { records: readEXPRecords(bytes) };
    if (format === "pes") return { records: readPESRecords(bytes) };
    throw new Error("no reader for " + format);
  }

  function readFacts(bytes, format, opts) {
    const o = opts || {};
    const explicit = format !== "dst";
    const n = format === "dst" ? jumpsPerTrim(o.jumpsPerTrim) : DEFAULT_TRIM_JUMPS;
    const r = readExport(bytes, format, o);
    const cnt = counter(explicit, n);
    let longest = 0, prev = null;
    const sewn = [];
    let bx0 = Infinity, bx1 = -Infinity, by0 = Infinity, by1 = -Infinity;
    for (const rec of r.records) {
      cnt.add(rec.kind, 1);
      if (rec.kind === "S") {
        sewn.push(rec.x, rec.y);
        if (rec.x < bx0) bx0 = rec.x;
        if (rec.x > bx1) bx1 = rec.x;
        if (rec.y < by0) by0 = rec.y;
        if (rec.y > by1) by1 = rec.y;
        if (prev === "S") longest = Math.max(longest, Math.abs(rec.dx), Math.abs(rec.dy));
      }
      prev = rec.kind;
    }
    const done = cnt.finish();
    return {
      format,
      jumpsPerTrim: n,
      stitches: done.stitches,
      trimAt: done.trimAt,
      colorAt: done.colorAt,
      records: done.tokens,
      longest,
      sewnBox: bx0 === Infinity ? null : [bx0, by0, bx1, by1],
      sewn,
      header: r.header || null,
      ended: r.ended,
      tail: r.tail,
    };
  }

  // ---- the comparison ----------------------------------------------------------
  const same = (a, b) => a.length === b.length && a.every((v, i) => v === b[i]);
  function firstDiff(a, b) {
    const n = Math.max(a.length, b.length);
    for (let i = 0; i < n; i++) if (a[i] !== b[i]) return i;
    return -1;
  }

  // Verifies `bytes` (what the writer produced) against `design`.
  // -> { ok, verified: true, format, checks: [{ check, expected, read, ok }],
  //      failed: [...], stitches, trims, colors, longestMm }
  // `ok` is false when any check failed; a reader that throws is a failed
  // "readable" check, never an exception out of here.
  function verifyExport(design, bytes, format, opts) {
    if (FORMATS.indexOf(format) === -1) {
      return { ok: true, verified: false, format, reason: "no read-back for " + String(format) + " in the browser", checks: [], failed: [] };
    }
    const exp = expectedExport(design, format, opts);
    let got;
    try {
      got = readFacts(bytes, format, opts);
    } catch (e) {
      const failed = [{ check: "readable", expected: "a file this format's reader accepts", read: String(e && e.message || e), ok: false }];
      return { ok: false, verified: true, format, checks: failed, failed, stitches: exp.stitches, trims: exp.trimAt.length, colors: exp.colorAt.length, longestMm: null };
    }
    const checks = [];
    const add = (check, expected, read, ok) => checks.push({ check, expected, read, ok: ok === undefined ? expected === read : ok });
    if (format === "dst") {
      add("readable", "end record, whole records", got.ended && got.tail === 0 ? "end record, whole records" : (got.ended ? got.tail + " stray bytes after the end record" : "no end record"));
    }
    add("stitch_count", exp.stitches, got.stitches);
    add("trim_count", exp.trimAt.length, got.trimAt.length);
    if (exp.trimAt.length === got.trimAt.length) {
      const d = firstDiff(exp.trimAt, got.trimAt);
      add("trim_order", "each trim after the stitch counts " + exp.trimAt.slice(0, 3).join(","), d < 0 ? "same" : "trim " + (d + 1) + " follows " + got.trimAt[d] + " stitches, not " + exp.trimAt[d], d < 0);
    }
    add("color_count", exp.colorAt.length, got.colorAt.length);
    if (exp.colorAt.length === got.colorAt.length) {
      const d = firstDiff(exp.colorAt, got.colorAt);
      add("color_order", "each colour change after the stitch counts " + exp.colorAt.slice(0, 3).join(","), d < 0 ? "same" : "change " + (d + 1) + " follows " + got.colorAt[d] + " stitches, not " + exp.colorAt[d], d < 0);
    }
    add("longest_stitch", "at most " + MAX_SEWN / 10 + " mm", got.longest / 10 + " mm", got.longest <= MAX_SEWN);
    const eb = exp.sewnBox, gb = got.sewnBox;
    // Every design stitch must land where the design put it, in order (the
    // records between two landings are the splits of a long chained move).
    // Counts and the box alone miss a stitch that moved inside the design.
    let at = 0;
    for (let i = 0; i < got.sewn.length && at < exp.landings.length; i += 2) {
      if (got.sewn[i] === exp.landings[at] && got.sewn[i + 1] === exp.landings[at + 1]) at += 2;
    }
    add("stitch_positions", exp.landings.length / 2 + " stitches where the design puts them", at / 2 + " found in order", at === exp.landings.length);
    add("bounding_box", eb ? eb.join(",") : "none", gb ? gb.join(",") : "none", (!eb && !gb) || (eb && gb && same(eb, gb)));
    if (format === "dst") {
      const h = got.header || {};
      const hb = [h["+X"], h["-X"], h["+Y"], h["-Y"]];
      // the writer keeps the last five digits of each field; a design that reaches
      // past 99999 units is refused before it gets here
      add("header_bbox", exp.headerBox.join(","), hb.join(","), exp.hasEvents ? same(exp.headerBox, hb) : true);
      // the header's own count against the records the file really holds
      add("header_stitch_count", got.records + 1, h.ST, h.ST === got.records + 1);
    }
    const failed = checks.filter((c) => !c.ok);
    return {
      ok: failed.length === 0,
      verified: true,
      format,
      checks,
      failed,
      stitches: got.stitches,
      trims: got.trimAt.length,
      colors: got.colorAt.length,
      longestMm: got.longest / 10,
    };
  }

  return { verifyExport, expectedExport, readExportFacts: readFacts, readEXPRecords, readPESRecords, READBACK_FORMATS: FORMATS, READBACK_MAX_SEWN_UNITS: MAX_SEWN };
});
