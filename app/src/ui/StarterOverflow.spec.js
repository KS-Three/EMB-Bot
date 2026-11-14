// @vitest-environment jsdom
//
// What a customer sees when a starter does not fit the placement it is dropped
// on (Kent 2026-11-14, "Stop at 75%, say so"): the Bur oak leaf on the hat front
// is 67.9 mm tall at 75% in a 64 mm box (the hat front's PLACEMENTS box, Kent's
// ruling the same day; the Shamrock used to overflow the old 57.15 mm one and
// now fits at 81%), so auto-fit stops at 75% and the design panel says the file
// does not fit. Real pack file, real engine, real panel.
import { beforeAll, expect, test } from "vitest";
import { render } from "@testing-library/svelte";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import "@testing-library/jest-dom/vitest";

const HERE = dirname(fileURLToPath(import.meta.url));
let EMB, generate, designImport, DesignPanel;

beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units", "garments", "fabrics", "fill", "geometry", "quantize", "flatten", "satin", "satinplay", "satinfont", "fontbin", "dst", "dstimport", "exp", "digitize"]) {
    require("../../../src/" + f + ".js");
  }
  ({ EMB } = await import("../lib/emb.js"));
  generate = await import("../lib/generate.js");
  designImport = await import("../lib/designImport.js");
  DesignPanel = (await import("./DesignPanel.svelte")).default;
});

function starterOn(file, name, garmentId) {
  const bytes = new Uint8Array(readFileSync(join(HERE, "..", "..", "public", "starter", file)));
  const el = { id: "e1", type: "design", rotationDeg: 0, offsetXMm: 0, offsetYMm: 0, blockColors: {}, ...designImport.designFilePatch(bytes, name) };
  const built = generate.generateElement(el, EMB.getGarment(garmentId), {});
  // the field's report of the drawn size (EmbroideryField emitSelectedDims)
  return { el, built, dims: { widthMM: built.widthMM, heightMM: built.heightMM } };
}

const shamrockOn = (garmentId) => starterOn("shamrock.dst", "Shamrock", garmentId);

test("Bur oak leaf on the hat front: 75% limit, the does-not-fit line, still sewable", () => {
  const { el, built, dims } = starterOn("bur-oak-leaf.dst", "Bur oak leaf", "hat_front");
  expect(built._debug.scale).toBeCloseTo(0.75, 9);
  expect(built.heightMM).toBeGreaterThan(64); // overflows the 64 mm box
  expect(built.stitchCount).toBeGreaterThan(0);
  expect(built.stitches[built.stitches.length - 1].type).toBe("end"); // a complete file, exportable
  const { container } = render(DesignPanel, { props: { element: el, designDims: dims } });
  expect(container.textContent).toMatch(/Resized to 75%/);
  expect(container.textContent).toMatch(/Auto-fit stopped\s+at the 75% limit/);
  expect(container.textContent).toMatch(/does\s+not fit the placement/);
});

test("Shamrock on the hat front now fits its 64 mm box: 81%, no limit line (Kent 2026-11-14)", () => {
  const { built } = shamrockOn("hat_front");
  expect(built._debug.scale).toBeGreaterThan(0.8);
  expect(built._debug.scale).toBeLessThan(0.82);
  expect(built.heightMM).toBeLessThanOrEqual(64 + 0.05);
});

test("Shamrock where it fits (full back): native size, the 'sews exactly as digitized' line", () => {
  const { el, built, dims } = shamrockOn("full_back");
  expect(built._debug.scale).toBe(1);
  const { container } = render(DesignPanel, { props: { element: el, designDims: dims } });
  expect(container.textContent).toMatch(/sews exactly as digitized/);
  expect(container.textContent).not.toMatch(/Resized to/);
});
