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
