// @vitest-environment jsdom
//
// What a customer sees when a starter does not fit the placement it is dropped
// on (Kent 2026-11-14, "Stop at 75%, say so"): the Shamrock on the hat front is
// 58.95 mm tall in a 57.2 mm box, so auto-fit stops at 75% and the design panel
// says the file does not fit. Real pack file, real engine, real panel.
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

function shamrockOn(garmentId) {
  const bytes = new Uint8Array(readFileSync(join(HERE, "..", "..", "public", "starter", "shamrock.dst")));
  const el = { id: "e1", type: "design", rotationDeg: 0, offsetXMm: 0, offsetYMm: 0, blockColors: {}, ...designImport.designFilePatch(bytes, "Shamrock") };
  const built = generate.generateElement(el, EMB.getGarment(garmentId), {});
  // the field's report of the drawn size (EmbroideryField emitSelectedDims)
  return { el, built, dims: { widthMM: built.widthMM, heightMM: built.heightMM } };
}

test("Shamrock on the hat front: 75% limit, the does-not-fit line, still sewable", () => {
  const { el, built, dims } = shamrockOn("hat_front");
  expect(built._debug.scale).toBeCloseTo(0.75, 9);
  expect(built.heightMM).toBeGreaterThan(57.2); // overflows the 57.2 mm box
  expect(built.stitchCount).toBeGreaterThan(0);
  expect(built.stitches[built.stitches.length - 1].type).toBe("end"); // a complete file, exportable
  const { container } = render(DesignPanel, { props: { element: el, designDims: dims } });
  expect(container.textContent).toMatch(/Resized to 75%/);
  expect(container.textContent).toMatch(/Auto-fit stopped\s+at the 75% limit/);
  expect(container.textContent).toMatch(/does\s+not fit the placement/);
});

test("Shamrock where it fits (full back): native size, the 'sews exactly as digitized' line", () => {
  const { el, built, dims } = shamrockOn("full_back");
  expect(built._debug.scale).toBe(1);
  const { container } = render(DesignPanel, { props: { element: el, designDims: dims } });
  expect(container.textContent).toMatch(/sews exactly as digitized/);
  expect(container.textContent).not.toMatch(/Resized to/);
});
