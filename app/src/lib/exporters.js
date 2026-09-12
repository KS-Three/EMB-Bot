import { EMB } from "./emb.js";
import { renderRealistic } from "./preview.js";
import { exportViaService } from "./digitizer.js";
import { sewFacts } from "./estimate.js";

export function exportDesign(design, format) {
  switch (format) {
    case "dst":
      return { bytes: EMB.encodeDST(design), filename: "design.dst", mime: "application/octet-stream" };
    case "exp":
      return { bytes: EMB.encodeEXP(design), filename: "design.exp", mime: "application/octet-stream" };
    case "pes":
      return { bytes: EMB.encodePES(design), filename: "design.pes", mime: "application/octet-stream" };
    case "svg":
      return { bytes: EMB.designToSVG(design), filename: "design.svg", mime: "image/svg+xml" };
    default:
      throw new Error("Unknown format: " + format);
  }
}

// dst/exp/pes CAN prefer the Python digitizer service's pyembroidery-
// convention encoder (the trustworthy path for third-party software — see
// MASTER_SCOPE.md's DST codec axis bug section: the browser's own DST
// encoder disagrees with the Tajima standard, and rendered 2026-09-07 a
// standard reader sees its output a quarter turn round AND MIRRORED, which
// is why "transposed" and "a quarter turn" were both understatements —
// rotating the file back elsewhere cannot repair it) — but only when the
// caller opts in via `preferService`. That
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
  const { label = "EMBBOT", exportViaServiceFn = exportViaService, fetchFn, preferService = false } = opts;
  if (SERVICE_ONLY_FORMATS.has(format)) {
    // No browser fallback exists, so a failure here is the end of the road and
    // has to say so in words a customer can act on. The service's own message
    // rides along: it names the actual cause (down, 4xx, timeout) and this
    // wrapper would otherwise swallow it.
    try {
      const out = await exportViaServiceFn(design, format, label, fetchFn);
      return { ...out, via: "service" };
    } catch (e) {
      throw new Error(`${format.toUpperCase()} is written by the digitizer service, which isn\u2019t answering — start it and try again. (${e.message})`);
    }
  }
  if (preferService && SERVICE_EXPORT_FORMATS.has(format)) {
    try {
      const out = await exportViaServiceFn(design, format, label, fetchFn);
      return { ...out, via: "service" };
    } catch (e) {
      // service down or erroring -- fall through to the browser encoder.
    }
  }
  return { ...exportDesign(design, format), via: "browser" };
}

// Builds and saves a PDF worksheet (title, stitch-simulation render, stats,
// thread sequence). jsPDF is loaded lazily so it never bloats the initial
// bundle — this is the only place that touches it. `hoop` (optional, a
// garments.js HOOPS preset) puts the chosen hoop on the sheet next to the
// placement — worksheets printed before the hoop picker existed simply
// omitted the line, and a missing hoop still does.
export async function exportWorksheetPDF(design, garment, hoop, chartLabel, hoopNote) {
  const mod = await import("jspdf");
  window.jspdf = window.jspdf || { jsPDF: mod.jsPDF };
  // Trims and thread metres, computed by the same walk the Review step uses
  // so the printed sheet and the screen cannot disagree. Computed HERE and
  // passed through `meta` rather than inside pdfsheet.js: the engine copy
  // takes no Studio imports (it is loaded as a plain script by
  // `app/public/engine/`), and duplicating the walk is how two numbers for
  // one design start to drift.
  const facts = sewFacts(design);
  EMB.buildWorksheetPDF(design, {
    garmentLabel: garment.label || "",
    hoop: hoop ? { label: hoop.label, widthMm: hoop.widthMm, heightMm: hoop.heightMm } : null,
    sew: { trims: facts.trims, threadM: facts.threadM },
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
    garmentBox: { widthMM: garment.widthIn * 25.4, heightMM: garment.heightIn * 25.4 },
  });
}

// Renders design to a PNG preview image. Long side is 1200px, other side
// scaled to preserve the design's aspect ratio (widthMM/heightMM). Uses
// renderRealistic with design-fit (no hoop).
export async function exportPNG(design) {
  const aspectW = design.widthMM || 1;
  const aspectH = design.heightMM || 1;
  // Guard against zero: if either is 0 or missing, use 1:1 aspect.
  const aspect = (aspectH !== 0) ? (aspectW / aspectH) : 1;

  let w, h;
  if (aspect >= 1) {
    w = 1200;
    h = Math.round(1200 / aspect);
  } else {
    h = 1200;
    w = Math.round(1200 * aspect);
  }

  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;

  renderRealistic(canvas, design, { pad: 40 });

  const blob = await new Promise((resolve, reject) => {
    canvas.toBlob((b) => {
      if (b === null) {
        reject(new Error("Failed to generate PNG: canvas.toBlob returned null"));
      } else {
        resolve(b);
      }
    }, "image/png");
  });

  return { blob, filename: "design.png", mime: "image/png" };
}
