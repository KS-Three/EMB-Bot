import { EMB } from "./emb.js";

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
