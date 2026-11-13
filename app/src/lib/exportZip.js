// "Download all": one zip holding every stitch format the Download step
// offers, the PDF worksheet, a picture of the stitch render and the thread
// list (Kent, 2026-11-05: zip only, no basting frame, no max-stitch split, no
// PES v1/v6 pair).
//
// Nothing here writes a stitch file itself. Each format comes from
// `exportFormat(fmt)` -- DownloadStep passes the SAME exportDesignPreferService
// call its single-format buttons make -- so every file in the zip has been
// through the same read-back (a file that fails it throws and is never handed
// out). Any one failure fails the whole archive with that format's reason and
// nothing is saved, the same rule as the single buttons: a zip holding nine
// good files and a missing tenth reads as complete.
//
// PEC and U01 are not in the zip: the Studio ships neither (Kent's scope call
// of 2026-09-12, exporters.js SERVICE_ONLY_FORMATS), so a zip containing them
// would hand over files the product's own buttons refuse to.
import { zipSync } from "fflate";
import { exportFileName } from "./exporters.js";
import { friendlyError } from "./friendlyError.js";

// The buttons' order: machine formats lead, the proof format follows.
export const ZIP_STITCH_FORMATS = ["dst", "pes", "exp", "jef", "xxx", "vp3", "svg"];

// The file name stem: "fritsch-hat" for the design "Fritsch Hat" (the same slug
// the single-format files use, so the zip's contents sort beside them).
export function zipStem(designName) {
  return exportFileName(designName, "zip").replace(/\.zip$/, "");
}

export function zipEntryNames(designName) {
  const stem = zipStem(designName);
  return [
    ...ZIP_STITCH_FORMATS.map((f) => `${stem}.${f}`),
    `${stem}-worksheet.pdf`,
    `${stem}-preview.png`,
    `${stem}-threads.txt`,
  ];
}

// The thread list in the order it is sewn, one cone per colour block, named from
// the chart the Threads list and the worksheet use. Plain text, the same lines
// the worksheet prints ("1. 1902 Poinsettia") plus the colour's hex.
export function threadListText(colors, chartLabel) {
  const hex = (c) =>
    "#" + [c.r, c.g, c.b].map((v) => Math.max(0, Math.min(255, v | 0)).toString(16).padStart(2, "0")).join("").toUpperCase();
  const head = chartLabel ? `Thread chart: ${chartLabel}\r\n` : "";
  return head + (colors || []).map((c, i) => `${i + 1}. ${c.name || "Color " + (i + 1)} (${hex(c)})`).join("\r\n") + "\r\n";
}

async function bytesOf(data) {
  if (data instanceof Uint8Array) return data;
  if (data instanceof ArrayBuffer) return new Uint8Array(data);
  if (data && typeof data.arrayBuffer === "function") return new Uint8Array(await data.arrayBuffer());
  if (typeof data === "string") return new TextEncoder().encode(data);
  return Uint8Array.from(data);
}

// Runs one step; a failure is reported in the customer's words with the thing
// that failed named, exactly as the single button for it would have.
async function step(what, fn) {
  try {
    return await bytesOf(await fn());
  } catch (e) {
    throw new Error(friendlyError(e, "export", what));
  }
}

// Builds the archive in memory. Throws (and so saves nothing) on the first
// failing file. Returns { bytes, filename, mime, entries } -- the same shape as
// any other export, so it goes through the same save door.
//
// `exportFormat(fmt)` -> { bytes }, `worksheet()` -> PDF bytes, `png()` ->
// PNG bytes/Blob, `threads()` -> the thread list text. All async-friendly.
export async function buildExportZip({ designName, exportFormat, worksheet, png, threads }) {
  const stem = zipStem(designName);
  const files = {};
  const entries = [];
  // Each stitch format's read-back result, in the zip's order, for the "Saved
  // ZIP" line (lib/exportCue.js). Absent = that format was not re-read here.
  const readbacks = [];
  const add = (name, bytes, level) => {
    files[name] = [bytes, { level }];
    entries.push(name);
  };

  for (const fmt of ZIP_STITCH_FORMATS) {
    let readback;
    const out = await step(`${fmt.toUpperCase()} file`, async () => {
      const r = await exportFormat(fmt);
      readback = r.readback;
      return r.bytes;
    });
    readbacks.push({ format: fmt, readback });
    add(`${stem}.${fmt}`, out, 6);
  }
  // Already deflated inside: storing them again costs time and gains nothing.
  add(`${stem}-worksheet.pdf`, await step("PDF worksheet", worksheet), 0);
  add(`${stem}-preview.png`, await step("PNG picture", png), 0);
  add(`${stem}-threads.txt`, await step("thread list", threads), 6);

  return {
    bytes: zipSync(files),
    filename: `${stem}.zip`,
    mime: "application/zip",
    entries,
    readbacks,
  };
}
