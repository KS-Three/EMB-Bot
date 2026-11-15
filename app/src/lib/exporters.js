import { EMB } from "./emb.js";
import { renderRealistic } from "./preview.js";
import { exportViaService } from "./digitizer.js";
import { sewFacts, sewSummary } from "./estimate.js";
import { loadQuote, profileById } from "./quote.js";
import { friendlyError } from "./friendlyError.js";

// "Fritsch's Stitches: Hat #2" + "dst" -> "fritsch-s-stitches-hat-2.dst".
// Same slug rule as projectFileName (.embproj backups), so a design's backup
// and its machine file share a stem. An empty name keeps the old "design".
export function exportFileName(name, ext) {
  const base = String(name || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60)
    .replace(/-+$/, "");
  return (base || "design") + "." + ext;
}

// A file that fails its own read-back is broken, not low quality (Kent,
// 2026-11-05), so it is never handed out: the writer's bytes are re-read
// (src/readback.js) and a mismatch throws this, naming the check. The message
// is the customer's sentence; `failed` carries every check with both values.
export class ExportVerifyError extends Error {
  constructor(format, result) {
    const first = result.failed[0];
    super(
      "Export failed: " + CHECK_LABEL[first.check] + " (expected " + first.expected + ", read back " + first.read + ")." +
        (result.failed.length > 1 ? " " + (result.failed.length - 1) + " more check" + (result.failed.length > 2 ? "s" : "") + " failed too." : ""),
    );
    this.name = "ExportVerifyError";
    this.format = format;
    this.check = first.check;
    this.failed = result.failed;
  }
}

const CHECK_LABEL = {
  readable: "the file does not read back",
  stitch_count: "stitch count",
  trim_count: "trim count",
  trim_order: "trim order",
  color_count: "colour block count",
  color_order: "colour block order",
  stitch_positions: "stitch positions",
  longest_stitch: "longest stitch",
  bounding_box: "design size",
  header_bbox: "size in the file header",
  header_stitch_count: "stitch count in the file header",
};

// Reads the bytes just written back with the engine's own readers and throws
// ExportVerifyError if they disagree with `design`. A build whose engine lacks
// readback.js (a spec that loads a subset of the engine) is labelled
// unverified; index.html always loads it, and engineList.spec pins that.
function verified(design, out, format, opts) {
  if (typeof EMB.verifyExport !== "function") {
    return { ...out, readback: { verified: false, reason: "the read-back is not loaded in this build" } };
  }
  const r = EMB.verifyExport(design, out.bytes, format, { jumpsPerTrim: opts.jumpsPerTrim });
  if (!r.ok) throw new ExportVerifyError(format, r);
  return {
    ...out,
    readback: r.verified
      ? { verified: true, stitches: r.stitches, trims: r.trims, colors: r.colors, longestMm: r.longestMm }
      : { verified: false, reason: r.reason },
  };
}

export function exportDesign(design, format, opts = {}) {
  switch (format) {
    case "dst":
      return verified(design, { bytes: EMB.encodeDST(design, { jumpsPerTrim: opts.jumpsPerTrim }), filename: "design.dst", mime: "application/octet-stream" }, "dst", opts);
    case "exp":
      return verified(design, { bytes: EMB.encodeEXP(design), filename: "design.exp", mime: "application/octet-stream" }, "exp", opts);
    case "pes":
      return verified(design, { bytes: EMB.encodePES(design), filename: "design.pes", mime: "application/octet-stream" }, "pes", opts);
    case "svg":
      return { bytes: EMB.designToSVG(design), filename: "design.svg", mime: "image/svg+xml", readback: { verified: false, reason: "SVG is a picture of the design, not a stitch file" } };
    default:
      throw new Error("Unknown format: " + format);
  }
}

// dst/exp/pes CAN prefer the Python digitizer service's pystitch-convention
// encoder — but only when the caller opts in via `preferService`.
//
// This block used to justify that preference by saying the browser's own DST
// encoder "disagrees with the Tajima standard" and that a standard reader sees
// its output "a quarter turn round AND MIRRORED". That was true when written
// (2026-09-07) and FALSE from 2026-09-08, when both halves of the codec were
// fixed to match `pystitch.DstWriter.encode_record` bit-for-bit — yet it stood
// here in the PRESENT TENSE until 2026-09-13, as the stated reason for a
// routing gate. Corrected rather than deleted, because the gate itself is
// still right for a different reason.
//
// The preference is a ROUTING choice now, not a correctness one. That
// gate exists because MASTER_SCOPE.md scopes the service-preference to
// purely-digitized designs only: lettering/manual designs stay on the
// browser's own encoder, the one with actual sew evidence behind it (the
// service's DST has never been sewn by anyone). This function has no
// knowledge of `project`/elements, so it can't tell a digitized design from
// a lettering one itself — that decision is the caller's job; see
// app/src/ui/DownloadStep.svelte's `isPurelyDigitized`, which is what sets
// `preferService`. Falls back to the browser encoder on ANY service failure
// (offline, network error, 4xx/5xx) so Download keeps working exactly as
// it always has when the service isn't running — no visible error, same
// bytes as before this function existed. svg (and any future non-stitch
// format) never touches the service; exportDesign() alone is authoritative
// for those. The returned object is tagged with `via: "service"` or
// `via: "browser"` so callers can tell which encoder actually produced the
// bytes (DownloadStep uses this to label the download).
const SERVICE_EXPORT_FORMATS = new Set(["dst", "exp", "pes"]);

// Formats ONLY the service can write. `preferService` above is a choice
// between two encoders that can both write the same format; this set is a
// different thing entirely — no browser encoder exists for any of these, so
// for them the service is the path or there is no path, and falling through
// to exportDesign() would raise "Unknown format: jef" at a customer.
//
// JEF is Janome, and it is on PRODUCT.md's launch checklist ("PES hardened to
// byte-verified + JEF export", item 1, marked done because
// `digitizer_service/formats.py` has always been able to write it). The
// service could write it; the Studio offered no button, so from the
// customer's seat the feature did not exist and a Janome owner could not use
// the product at all.
//
// Verified 2026-09-07 by decoding what the endpoint actually returns, with
// `pystitch` — the same third-party reader CI cross-validates against. A
// digitized logo the app reported as 80.5 x 16.6 mm, 2 colours, 2459 stitches
// reads back from JEF as 2459 sewn stitches, 80.5 x 16.6 mm, 1 colour change,
// 2 threads in the threadlist. Not an inference from the writer existing.
//
// XXX (Singer) and VP3 (Husqvarna Viking / Pfaff) joined on 2026-09-12 —
// Kent's scope call, which closes MASTER_SCOPE open item 14 for those two and
// leaves PEC and U01 exactly where they were. Same shape as JEF: pyembroidery
// writes them, nothing in the browser does, so for these the service is the
// path or there is no path.
//
// The evidence is `digitizer/tools/format_roundtrip.py --detail` — run it
// rather than re-deriving it. Both read back `identity` through pystitch, the
// same third-party reader CI cross-validates against: 70/70 stitches, 1/1
// colour change, 1725 x 200 units in and out. Both also hand back the
// design's OWN thread RGB (#dc1e28 / #143cc8) where PES, PEC and JEF snap to
// their chart instead, so on colour fidelity these two beat three of the four
// formats that were already shipping.
//
// VP3 has one measured difference, and it is deliberately NOT said to the
// customer (Kent's call, same day). At the THIRD and later colour block the
// read-back is 1 unit narrower: an inserted jump lands one unit short of
// where the design put it and shifts the tail -1 in x. That unit is 0.1 mm —
// one step of the integer 0.1 mm grid the Design contract is already
// quantised to (digitizer_core/adapter.py's `_u`) — and the tool's own
// 1..4-colour sweep shows it pinned there rather than accumulating (0, 0, 1u,
// 1u), as did a 16-block sweep when the call was made. So do not grow a
// button asterisk, a note, or a caveat paragraph out of it. If it ever moves,
// re-run the tool and write about what you measured.
//
// `isServiceOnlyFormat` is exported so the UI can disable the control with a
// reason instead of offering a button that throws.
const SERVICE_ONLY_FORMATS = new Set(["jef", "xxx", "vp3"]);

export function isServiceOnlyFormat(format) {
  return SERVICE_ONLY_FORMATS.has(format);
}

export async function exportDesignPreferService(design, format, opts = {}) {
  const { label = "EMBBOT", exportViaServiceFn = exportViaService, fetchFn, preferService = false, jumpsPerTrim } = opts;
  if (SERVICE_ONLY_FORMATS.has(format)) {
    // No browser fallback exists, so a failure here is the end of the road and
    // has to say so in words a customer can act on. The service's own message
    // rides along: it names the actual cause (down, 4xx, timeout) and this
    // wrapper would otherwise swallow it.
    try {
      const out = await exportViaServiceFn(design, format, label, fetchFn);
      return { ...out, via: "service" };
    } catch (e) {
      // Keep the cause when the service gave one in words; never paste raw
      // transport text ("Failed to fetch") after the sentence.
      throw new Error(friendlyError(e, "export", `${format.toUpperCase()} file`));
    }
  }
  if (preferService && SERVICE_EXPORT_FORMATS.has(format)) {
    try {
      const out = await exportViaServiceFn(design, format, label, fetchFn, jumpsPerTrim);
      return { ...out, via: "service" };
    } catch (e) {
      // service down or erroring -- fall through to the browser encoder.
      // A service that REFUSED its own file (read-back mismatch) falls through
      // too: the browser's bytes go through the same read-back before they
      // leave, so nothing unverified is handed out, and if the browser file
      // fails as well the customer gets that failure and no file. The refusal
      // is kept on the result for the console, not shown (no-warnings ruling).
      if (e && e.readbackFailed) {
        const out = exportDesign(design, format, { jumpsPerTrim });
        console.warn("The digitizer service refused its own " + format.toUpperCase() + " file: " + e.message);
        return { ...out, via: "browser", serviceRefused: e.message };
      }
    }
  }
  return { ...exportDesign(design, format, { jumpsPerTrim }), via: "browser" };
}

// Builds and saves a PDF worksheet (title, stitch-simulation render, stats,
// thread sequence). jsPDF is loaded lazily so it never bloats the initial
// bundle — this is the only place that touches it. `hoop` (optional, a
// garments.js HOOPS preset) puts the chosen hoop on the sheet next to the
// placement — worksheets printed before the hoop picker existed simply
// omitted the line, and a missing hoop still does.
//
// `asBytes` (Download all): build the sheet but do not save it, and return its
// bytes as a Uint8Array for the zip. Without it the sheet saves, as always.
export async function exportWorksheetPDF(design, garment, hoop, chartLabel, hoopNote, { asBytes = false } = {}) {
  const mod = await import("jspdf");
  window.jspdf = window.jspdf || { jsPDF: mod.jsPDF };
  // Trims and thread metres, computed by the same walk the Review step uses
  // so the printed sheet and the screen cannot disagree. Computed HERE and
  // passed through `meta` rather than inside pdfsheet.js: the engine copy
  // takes no Studio imports (it is loaded as a plain script by
  // `app/public/engine/`), and duplicating the walk is how two numbers for
  // one design start to drift.
  const facts = sewFacts(design);
  // The operator's quote inputs, read from the same storage the Download
  // sheet edits, so the sheet on paper quotes what the screen just did. The
  // dollar lines are the screen's own rows, reworded only by a colon.
  const quote = loadQuote();
  const profile = profileById(quote.profileId);
  const quoteLines = sewSummary(design, quote)
    .filter((r) => r.label === "Thread cost" || r.label === "Machine time")
    .map((r) => r.label + ": " + r.value);
  const doc = EMB.buildWorksheetPDF(design, {
    ...(asBytes ? { save: false } : {}),
    quoteLines,
    garmentLabel: garment.label || "",
    // The id as well as the label: the sheet resolves the fabric preset from
    // it to state the backing class and whether the goods want a topper. A
    // label is for the reader, an id is for the lookup, and passing only the
    // first is what left the sheet guessing stabilizer from a stitch count.
    garmentId: garment.id || "",
    hoop: hoop ? { label: hoop.label, widthMm: hoop.widthMm, heightMm: hoop.heightMm } : null,
    sew: {
      trims: facts.trims,
      threadM: facts.threadM,
      stops: facts.stops,
      spm: quote.spm,
      machineLabel: profile ? profile.label : "",
    },
    // Whose thread numbering the sheet's codes belong to. The caller has
    // already snapped every colour to this chart's nearest cone, so the
    // label and the codes come from one palette object and cannot name
    // different charts.
    chartLabel: chartLabel || "",
    // Whether the design fits the hoop named above. Passed in, not
    // re-derived: DownloadStep already computes this for its export gate,
    // and a second computation is how one document starts disagreeing with
    // the other about the same design.
    hoopNote: hoopNote || "",
    fileName: "embbot-worksheet.pdf",
    // the box the field draws and clamps to: the hat front's PLACEMENTS box where
    // the garment carries `clampBox` (Kent 2026-11-14), else the inch pair
    garmentBox: garment.clampBox
      ? { widthMM: garment.clampBox.w, heightMM: garment.clampBox.h }
      : { widthMM: garment.widthIn * 25.4, heightMM: garment.heightIn * 25.4 },
  });
  return asBytes ? new Uint8Array(doc.output("arraybuffer")) : undefined;
}

// ---- True-size PNG --------------------------------------------------------
// The approval PNG used to be "1200 px on the long side", so a print of it came
// out at whatever size the viewer chose. It is now drawn at a stated scale and
// says so in a pHYs chunk (pixels per metre), so a print or a layout tool lands
// at the sewn size. PNG_PX_PER_MM = 12 is 304.8 dpi. The 40 px pad is unchanged
// and is NOT part of the stated size: printable width = (pixels - 2 pad) / ppm.
export const PNG_PX_PER_MM = 12;
export const PNG_PAD_PX = 40;
const PNG_MAX_SIDE = 6000; // canvas budget; a huge design lowers the scale, pHYs follows

let _crcTable = null;
function crc32(bytes) {
  if (!_crcTable) {
    _crcTable = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
      _crcTable[n] = c >>> 0;
    }
  }
  let c = 0xffffffff;
  for (let i = 0; i < bytes.length; i++) c = _crcTable[(c ^ bytes[i]) & 255] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

// Returns a copy of `png` (Uint8Array) with a pHYs chunk (metre unit) placed
// right after IHDR, replacing any existing one. Not a PNG: returned unchanged.
export function setPngPhys(png, pxPerMetre) {
  const sig = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
  if (png.length < 33 || sig.some((b, i) => png[i] !== b)) return png;
  const dv = new DataView(png.buffer, png.byteOffset, png.byteLength);
  const ppm = Math.round(pxPerMetre);
  const chunk = new Uint8Array(21);
  const cv = new DataView(chunk.buffer);
  cv.setUint32(0, 9);
  chunk.set([0x70, 0x48, 0x59, 0x73], 4); // "pHYs"
  cv.setUint32(8, ppm);
  cv.setUint32(12, ppm);
  chunk[16] = 1; // unit: metre
  cv.setUint32(17, crc32(chunk.subarray(4, 17)));
  // Walk chunks after IHDR (8 sig + 25 IHDR), dropping any old pHYs.
  const parts = [png.subarray(0, 33), chunk];
  let off = 33;
  while (off + 12 <= png.length) {
    const len = dv.getUint32(off);
    const type = String.fromCharCode(png[off + 4], png[off + 5], png[off + 6], png[off + 7]);
    const end = off + 12 + len;
    if (type !== "pHYs") parts.push(png.subarray(off, Math.min(end, png.length)));
    off = end;
  }
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let o = 0;
  for (const p of parts) { out.set(p, o); o += p.length; }
  return out;
}

async function blobBytes(blob) {
  if (typeof blob.arrayBuffer === "function") return new Uint8Array(await blob.arrayBuffer());
  return new Uint8Array(await new Response(blob).arrayBuffer());
}

// Design extent in mm: the stitch bounding box (what renderRealistic's fit
// uses), falling back to the declared size when there are no stitches.
function designExtentMM(design) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const s of design.stitches || []) {
    if (s.type === "color" || s.type === "end") continue;
    if (s.x < minX) minX = s.x; if (s.x > maxX) maxX = s.x;
    if (s.y < minY) minY = s.y; if (s.y > maxY) maxY = s.y;
  }
  if (maxX >= minX && maxY >= minY) {
    return { w: Math.max(0.1, (maxX - minX) / 10), h: Math.max(0.1, (maxY - minY) / 10) };
  }
  return { w: design.widthMM || 1, h: design.heightMM || 1 };
}

// Renders design to a PNG preview image at PNG_PX_PER_MM (pad excluded) and
// stamps that scale into the file as pHYs. Uses renderRealistic with
// design-fit (no hoop); the canvas is sized so the fit's scale is that px/mm.
export async function exportPNG(design) {
  const ext = designExtentMM(design);
  let pxMm = PNG_PX_PER_MM;
  const pad = PNG_PAD_PX;
  const longMm = Math.max(ext.w, ext.h);
  if (longMm * pxMm + 2 * pad > PNG_MAX_SIDE) pxMm = (PNG_MAX_SIDE - 2 * pad) / longMm;

  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(ext.w * pxMm) + 2 * pad);
  canvas.height = Math.max(1, Math.round(ext.h * pxMm) + 2 * pad);

  renderRealistic(canvas, design, { pad });

  let blob = await new Promise((resolve, reject) => {
    canvas.toBlob((b) => {
      if (b === null) {
        reject(new Error("Failed to generate PNG: canvas.toBlob returned null"));
      } else {
        resolve(b);
      }
    }, "image/png");
  });

  // A blob we cannot read back (test doubles) is returned as drawn.
  if (blob && (typeof blob.arrayBuffer === "function" || typeof Response !== "undefined") && blob.type !== undefined) {
    try {
      const bytes = await blobBytes(blob);
      const stamped = setPngPhys(bytes, pxMm * 1000);
      if (stamped !== bytes) blob = new Blob([stamped], { type: "image/png" });
    } catch { /* keep the unstamped PNG */ }
  }

  return { blob, filename: "design.png", mime: "image/png", pxPerMm: pxMm };
}
