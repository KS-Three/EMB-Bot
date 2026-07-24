import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
let design;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","satin","satinplay","satinfont","dst","exp","pes","svgexport","fonts","digitize"]) require("../../../src/" + f + ".js");
  new Function(require("node:fs").readFileSync(require("node:path").join(__dirname, "../../../src/fonts/satin-fonts.js"), "utf8"))();
  const { generateDesign } = await import("./generate.js");
  const { defaultProject, update } = await import("./project.js");
  design = generateDesign(update(defaultProject(), { text: "AB" }));
});
test("DST export yields bytes and a .dst filename", async () => {
  const { exportDesign } = await import("./exporters.js");
  const out = exportDesign(design, "dst");
  expect(out.filename.endsWith(".dst")).toBe(true);
  expect(out.bytes.length).toBeGreaterThan(100);
});
test("EXP export yields bytes and a .exp filename", async () => {
  const { exportDesign } = await import("./exporters.js");
  const out = exportDesign(design, "exp");
  expect(out.filename.endsWith(".exp")).toBe(true);
  expect(out.bytes.length).toBeGreaterThan(50);
});
test("PES export yields bytes and a .pes filename", async () => {
  const { exportDesign } = await import("./exporters.js");
  const out = exportDesign(design, "pes");
  expect(out.filename.endsWith(".pes")).toBe(true);
  expect(out.bytes.length).toBeGreaterThan(50);
});
test("SVG export yields an <svg> string and a .svg filename", async () => {
  const { exportDesign } = await import("./exporters.js");
  const out = exportDesign(design, "svg");
  expect(out.filename.endsWith(".svg")).toBe(true);
  expect(String(out.bytes)).toContain("<svg");
});
test("unknown format throws", async () => {
  const { exportDesign } = await import("./exporters.js");
  expect(() => exportDesign(design, "zzz")).toThrow();
});
