import { EMB } from "./emb.js";
import { renderRealistic } from "./preview.js";

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
