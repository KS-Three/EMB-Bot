import { EMB } from "./emb.js";

export function generateDesign(project) {
  const text = (project.text || "").trim();
  if (!text) throw new Error("Type some text first.");
  const fontData = (EMB.SATIN_FONTS || {})[project.fontKey];
  if (!fontData) throw new Error("Unknown font: " + project.fontKey);
  const garment = EMB.getGarment(project.garmentId);
  const design = EMB.buildLetteringDesign(fontData, text, {
    garment, pxPerMm: 8, densityMm: 0.4, underlay: project.underlay,
    rgb: project.colorRgb,
  });
  if (!design.stitchCount) throw new Error("No characters in this font yet — try different text.");
  return design;
}
