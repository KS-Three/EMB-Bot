// The ONE way a .dst file's bytes become a design element's fields. Two doors
// lead here: DesignPanel's "Choose a .dst file…" and the starter pack
// (lib/starterPack.js). Both hand over raw bytes and get back the same patch,
// so a starter design IS an ordinary import: generate.js decodes it, the
// engine sizes and clamps it, and save/load carries it as base64 like any
// other .dst.
import { EMB } from "./emb.js";

export function bytesToBase64(bytes) {
  // btoa needs a binary string; build it in chunks so a large-ish file
  // can't blow the argument-count limit of String.fromCharCode.apply.
  let bin = "";
  const CHUNK = 0x8000;
  for (let i = 0; i < bytes.length; i += CHUNK) {
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
  }
  return btoa(bin);
}

// Throws (EMB.decodeDSTStandard's own message) on anything that is not a DST:
// validated BEFORE storing, so a bad file never lands on an element.
// `sizeMm: null` is the file's native size, clamped to the placement by the
// engine (buildImportedDesign).
export function designFilePatch(bytes, name) {
  EMB.decodeDSTStandard(bytes);
  return { dstBase64: bytesToBase64(bytes), name, blockColors: {}, sizeMm: null };
}
