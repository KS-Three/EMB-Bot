import { EMB } from "./emb.js";
import { renderRealistic } from "./preview.js";
import { exportViaService } from "./digitizer.js";

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
// encoder is confirmed transposed a quarter-turn against the Tajima
// standard) — but only when the caller opts in via `preferService`. That
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

export async function exportDesignPreferService(design, format, opts = {}) {
  const { label = "EMBBOT", exportViaServiceFn = exportViaService, fetchFn, preferService = false } = opts;
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
// bundle — this is the only place that touches it.
export async function exportWorksheetPDF(design, garment) {
  const mod = await import("jspdf");
  window.jspdf = window.jspdf || { jsPDF: mod.jsPDF };
  EMB.buildWorksheetPDF(design, {
    garmentLabel: garment.label || "",
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
