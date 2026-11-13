// Download all: the zip assembly (lib/exportZip.js).
//
// The writers are injected, so these tests pin what the ARCHIVE does: which
// entries it holds and what they are called, that each file's bytes are the
// single-format export's bytes untouched, and that one failing file fails the
// whole archive (nothing returned, so nothing to save).
import { expect, test, vi } from "vitest";
import { unzipSync } from "fflate";

// exportZip.js imports the real exporters.js for the file-name slug only;
// stub the heavy parts it drags in.
vi.mock("./preview.js", () => ({ renderRealistic: () => {} }));
vi.mock("./digitizer.js", () => ({ exportViaService: async () => ({}) }));
vi.mock("./emb.js", () => ({ EMB: {} }));

import { buildExportZip, threadListText, zipEntryNames, zipStem, ZIP_STITCH_FORMATS } from "./exportZip.js";

// Distinct, non-compressible-looking bytes per format so a swapped entry shows.
const fileFor = (fmt) => Uint8Array.from({ length: 300 }, (_, i) => (i * 31 + fmt.charCodeAt(0) * 7 + fmt.length) & 255);
const PDF = Uint8Array.from([0x25, 0x50, 0x44, 0x46, 1, 2, 3]);
const PNG = Uint8Array.from([0x89, 0x50, 0x4e, 0x47, 9, 8, 7]);

function parts(over = {}) {
  return {
    designName: "Fritsch Hat #2",
    exportFormat: async (fmt) => ({ bytes: fileFor(fmt), filename: "design." + fmt, mime: "x", via: "service" }),
    worksheet: async () => PDF,
    png: async () => new Blob([PNG], { type: "image/png" }),
    threads: async () => "1. Black (#000000)\r\n",
    ...over,
  };
}

test("the entries are <name>.<ext> per format, plus worksheet, preview and threads", async () => {
  const zip = await buildExportZip(parts());
  const stem = "fritsch-hat-2";
  expect(zip.filename).toBe(stem + ".zip");
  expect(zip.mime).toBe("application/zip");
  expect(zip.entries).toEqual([
    ...ZIP_STITCH_FORMATS.map((f) => `${stem}.${f}`),
    `${stem}-worksheet.pdf`,
    `${stem}-preview.png`,
    `${stem}-threads.txt`,
  ]);
  expect(zip.entries).toEqual(zipEntryNames("Fritsch Hat #2"));
  const files = unzipSync(zip.bytes);
  expect(Object.keys(files).sort()).toEqual([...zip.entries].sort());
  expect(Object.keys(files)).toHaveLength(10);
});

test("the stitch formats are the Download step's seven: DST PES EXP JEF XXX VP3 SVG", () => {
  expect(ZIP_STITCH_FORMATS).toEqual(["dst", "pes", "exp", "jef", "xxx", "vp3", "svg"]);
});

test("every file's bytes equal the single-format export's bytes", async () => {
  const zip = await buildExportZip(parts());
  const files = unzipSync(zip.bytes);
  for (const f of ZIP_STITCH_FORMATS) expect(Array.from(files[`fritsch-hat-2.${f}`]), f).toEqual(Array.from(fileFor(f)));
  expect(Array.from(files["fritsch-hat-2-worksheet.pdf"])).toEqual(Array.from(PDF));
  expect(Array.from(files["fritsch-hat-2-preview.png"])).toEqual(Array.from(PNG));
  expect(new TextDecoder().decode(files["fritsch-hat-2-threads.txt"])).toBe("1. Black (#000000)\r\n");
});

test("an empty name falls back to design, like the single files", async () => {
  const zip = await buildExportZip(parts({ designName: "" }));
  expect(zip.filename).toBe("design.zip");
  expect(zip.entries[0]).toBe("design.dst");
  expect(zipStem("")).toBe("design");
});

test("each format is asked for once, in the buttons' order", async () => {
  const asked = [];
  await buildExportZip(parts({ exportFormat: async (fmt) => { asked.push(fmt); return { bytes: fileFor(fmt) }; } }));
  expect(asked).toEqual(ZIP_STITCH_FORMATS);
});

test("one format failing read-back fails the whole zip with that format's reason", async () => {
  const reason = "Export failed: stitch count (expected 20, read back 19).";
  const worksheet = vi.fn(async () => PDF);
  const png = vi.fn(async () => PNG);
  const exportFormat = async (fmt) => {
    if (fmt === "pes") throw new Error(reason);
    return { bytes: fileFor(fmt) };
  };
  // Nothing is returned, so there is nothing to hand to the save door.
  await expect(buildExportZip(parts({ exportFormat, worksheet, png }))).rejects.toThrow(reason);
  // ...and it stopped at the failing file instead of building the rest.
  expect(worksheet).not.toHaveBeenCalled();
  expect(png).not.toHaveBeenCalled();
});

test("each stitch format's read-back result rides out on the archive, in the zip's order", async () => {
  const rb = (fmt) => (fmt === "svg" ? { verified: false, reason: "picture" } : { verified: true, stitches: 20, colors: 2 });
  const zip = await buildExportZip(parts({ exportFormat: async (fmt) => ({ bytes: fileFor(fmt), readback: rb(fmt) }) }));
  expect(zip.readbacks.map((r) => r.format)).toEqual(ZIP_STITCH_FORMATS);
  expect(zip.readbacks.find((r) => r.format === "dst").readback).toEqual({ verified: true, stitches: 20, colors: 2 });
  expect(zip.readbacks.find((r) => r.format === "svg").readback.verified).toBe(false);
  // a format that reported nothing is carried as nothing, not as verified
  const bare = await buildExportZip(parts());
  expect(bare.readbacks.every((r) => r.readback === undefined)).toBe(true);
});

test("a mismatch in the LAST stitch file still returns nothing: no archive, no partial entries", async () => {
  const exportFormat = async (fmt) => {
    if (fmt === "svg") throw new Error("Export failed: design size (expected 1,2, read back 1,3).");
    return { bytes: fileFor(fmt), readback: { verified: true } };
  };
  const result = await buildExportZip(parts({ exportFormat })).then((z) => ({ z }), (e) => ({ e }));
  expect(result.z).toBeUndefined();
  expect(result.e.message).toBe("Export failed: design size (expected 1,2, read back 1,3).");
});

test("a failing worksheet, picture or thread list fails it too, in plain words", async () => {
  await expect(buildExportZip(parts({ worksheet: async () => { throw new Error("boom"); } }))).rejects.toThrow(/PDF worksheet/);
  await expect(buildExportZip(parts({ png: async () => { throw new Error("boom"); } }))).rejects.toThrow(/PNG picture/);
  await expect(buildExportZip(parts({ threads: async () => { throw new Error("boom"); } }))).rejects.toThrow(/thread list/);
});

test("an unreachable service reads as the service not answering, naming the format", async () => {
  const exportFormat = async (fmt) => {
    if (fmt === "jef") throw Object.assign(new TypeError("Failed to fetch"), { kind: "unreachable" });
    return { bytes: fileFor(fmt) };
  };
  await expect(buildExportZip(parts({ exportFormat }))).rejects.toThrow(/JEF file.*digitizer service/s);
});

test("the thread list is the sewn order, one cone per block, named from the chart", () => {
  const colors = [
    { r: 200, g: 30, b: 40, name: "1902 Poinsettia" },
    { r: 0, g: 0, b: 0, name: "1000 Black" },
    { r: 255, g: 255, b: 255 },
  ];
  expect(threadListText(colors, "Madeira Polyneon")).toBe(
    "Thread chart: Madeira Polyneon\r\n1. 1902 Poinsettia (#C81E28)\r\n2. 1000 Black (#000000)\r\n3. Color 3 (#FFFFFF)\r\n",
  );
  expect(threadListText([], "")).toBe("\r\n");
});
