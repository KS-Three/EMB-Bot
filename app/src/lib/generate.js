import { EMB } from "./emb.js";
import { flatToRegions } from "./imageRegions.js";

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

export function generateImageDesign(flat, project) {
  const { regions, pxPerMm } = flatToRegions(flat);
  if (!regions.length) throw new Error("No shapes found to stitch — try a simpler image or fewer colors.");
  const garment = EMB.getGarment(project.garmentId);
  const fabric = EMB.getFabric(EMB.fabricForGarment(project.garmentId));
  const design = EMB.buildQualityDesign(regions, {
    garment, fabric, pxPerMm, densityMm: 0.4, satinMaxWidthMm: 3.0, underlay: project.underlay,
  });
  return design;
}
