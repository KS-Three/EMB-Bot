// Export read-back in the Studio (src/readback.js behind lib/exporters.js).
//
// Kent, 2026-11-05: a stitch file whose bytes do not read back as the design
// that was written is broken, not low quality, so it is never handed out. The
// browser writers' bytes are re-read inside exportDesign(); a mismatch throws
// ExportVerifyError, whose message is the customer's sentence ("Export failed:
// <check> ..."), and nothing reaches triggerDownload.
import { test, expect, beforeAll, beforeEach, afterEach, vi } from "vitest";
import { createRequire } from "node:module";

vi.mock("jspdf", () => ({ jsPDF: class FakeJsPDF {} }));
vi.mock("./preview.js", () => ({ renderRealistic: vi.fn() }));

const S = (x, y, type = "stitch") => ({ x, y, type });
const design = {
  stitches: [
    S(0, 0, "jump"), S(0, 0), S(30, 0), S(30, 40), S(400, 40),
    S(400, 40, "trim"), S(500, 100, "jump"), S(500, 100), S(520, 110),
    S(520, 110, "trim"), S(520, 110, "color"), S(540, 130), S(560, 130),
    S(0, 0, "end"),
  ],
  colors: [{ r: 200, g: 30, b: 30 }, { r: 20, g: 60, b: 200 }],
};

let exporters;
let EMB;
const real = {};

beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units", "garments", "fabrics", "fill", "geometry", "satin", "satinplay", "satinfont", "fontbin", "dst", "dstimport", "exp", "pes", "readback", "svgexport", "digitize"]) {
    require("../../../src/" + f + ".js");
  }
  ({ EMB } = await import("./emb.js"));
  exporters = await import("./exporters.js");
  for (const k of ["encodeDST", "encodeEXP", "encodePES"]) real[k] = EMB[k];
});

afterEach(() => {
  Object.assign(EMB, real); // undo any corrupted encoder
});

// A writer that loses one sewn record: the file is whole, the design is not in it.
function dropOneStitch(bytes, format) {
  if (format === "dst") {
    const out = new Uint8Array(bytes.length - 3);
    out.set(bytes.subarray(0, 512 + 3 * 4));
    out.set(bytes.subarray(512 + 3 * 5), 512 + 3 * 4);
    return out;
  }
  if (format === "exp") return Uint8Array.from([...bytes.subarray(0, 6), ...bytes.subarray(8)]);
  const pec = bytes[8] | (bytes[9] << 8) | (bytes[10] << 16) | (bytes[11] << 24);
  const first = pec + 532;
  const out = Uint8Array.from(bytes);
  out[first + 2] = 0x3f; // a stitch delta the design never had
  return out;
}

const ENCODER = { dst: "encodeDST", exp: "encodeEXP", pes: "encodePES" };

for (const format of ["dst", "exp", "pes"]) {
  test(`${format}: a clean file is returned with its read-back counts`, () => {
    const out = exporters.exportDesign(design, format);
    expect(out.bytes.length).toBeGreaterThan(10);
    expect(out.readback.verified).toBe(true);
    expect(out.readback.stitches).toBeGreaterThan(8);
    expect(out.readback.colors).toBe(1);
  });

  test(`${format}: a file that does not read back as the design is refused, with the check named`, () => {
    EMB[ENCODER[format]] = (d, o) => dropOneStitch(real[ENCODER[format]](d, o), format);
    let err;
    try { exporters.exportDesign(design, format); } catch (e) { err = e; }
    expect(err).toBeInstanceOf(exporters.ExportVerifyError);
    expect(err.message).toMatch(/^Export failed: /);
    expect(err.format).toBe(format);
    expect(err.failed.length).toBeGreaterThan(0);
    expect(err.check).toBe(err.failed[0].check);
  });
}

test("the refusal names the check and both numbers", () => {
  EMB.encodeDST = (d, o) => dropOneStitch(real.encodeDST(d, o), "dst");
  expect(() => exporters.exportDesign(design, "dst")).toThrow(/^Export failed: stitch count \(expected 11, read back 10\)/);
});

test("svg is returned and labelled unverified, never as checked", () => {
  const out = exporters.exportDesign(design, "svg");
  expect(out.readback.verified).toBe(false);
  expect(out.readback.reason).toMatch(/not a stitch file/);
});

test("jumpsPerTrim rides to the read-back: a file written at 1 or 2 still verifies", () => {
  for (const n of [1, 2, 3, 6, 10]) {
    const out = exporters.exportDesign(design, "dst", { jumpsPerTrim: n });
    expect(out.readback.verified, `N=${n}`).toBe(true);
  }
});

test("exportDesignPreferService: the browser path refuses a bad file and returns nothing", async () => {
  EMB.encodePES = (d) => dropOneStitch(real.encodePES(d), "pes");
  await expect(exporters.exportDesignPreferService(design, "pes")).rejects.toThrow(/^Export failed: /);
});

test("exportDesignPreferService: a service that refused its own file falls back to a browser file that verifies", async () => {
  const refusal = Object.assign(new Error("Export failed: stitch count (expected 11, read back 10)."), { status: 500, readbackFailed: true });
  const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
  const out = await exporters.exportDesignPreferService(design, "dst", {
    preferService: true,
    exportViaServiceFn: async () => { throw refusal; },
  });
  expect(out.via).toBe("browser");
  expect(out.readback.verified).toBe(true);
  expect(out.serviceRefused).toMatch(/Export failed/);
  expect(warn).toHaveBeenCalled();
  warn.mockRestore();
});

test("exportDesignPreferService: if the browser file fails as well, nothing is returned", async () => {
  const refusal = Object.assign(new Error("Export failed: stitch count (expected 11, read back 10)."), { status: 500, readbackFailed: true });
  vi.spyOn(console, "warn").mockImplementation(() => {});
  EMB.encodeDST = (d, o) => dropOneStitch(real.encodeDST(d, o), "dst");
  await expect(exporters.exportDesignPreferService(design, "dst", {
    preferService: true,
    exportViaServiceFn: async () => { throw refusal; },
  })).rejects.toBeInstanceOf(exporters.ExportVerifyError);
});

test("a service-only format (JEF) that the service refuses fails with the service's sentence", async () => {
  const refusal = Object.assign(new Error("Export failed: trim count (expected 2, read back 0)."), { status: 500, readbackFailed: true });
  await expect(exporters.exportDesignPreferService(design, "jef", {
    exportViaServiceFn: async () => { throw refusal; },
  })).rejects.toThrow(/^Export failed: trim count \(expected 2, read back 0\)/);
});

test("exportViaService flags the service's read-back refusal and passes its verified headers through", async () => {
  const { exportViaService } = await import("./digitizer.js");
  const refused = {
    ok: false, status: 500,
    json: async () => ({ detail: "Export failed: stitch count (expected 13, read back 12).", readback: { verified: false } }),
  };
  const err = await exportViaService(design, "dst", "x", async () => refused).catch((e) => e);
  expect(err.readbackFailed).toBe(true);
  expect(err.message).toMatch(/^Export failed: stitch count/);
  // an ordinary 500 is NOT a refusal
  const plain500 = { ok: false, status: 500, json: async () => ({ detail: "Something went wrong on our side." }) };
  const e2 = await exportViaService(design, "dst", "x", async () => plain500).catch((e) => e);
  expect(e2.readbackFailed).toBeUndefined();

  const headers = new Map([["X-Export-Verified", "true"], ["X-Export-Readback", '{"stitches":13,"trims":2,"colors":2,"longest_mm":12}'], ["Content-Type", "application/octet-stream"]]);
  const ok = { ok: true, status: 200, blob: async () => new Blob(["x"]), headers: { get: (k) => headers.get(k) || null } };
  const out = await exportViaService(design, "dst", "x", async () => ok);
  expect(out.readback).toEqual({ verified: true, stitches: 13, trims: 2, colors: 2, longest_mm: 12 });
  const unknown = { ...ok, headers: { get: () => null } };
  expect((await exportViaService(design, "dst", "x", async () => unknown)).readback).toBeUndefined();
});
