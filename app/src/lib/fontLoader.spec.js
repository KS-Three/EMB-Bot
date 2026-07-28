import { describe, it, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);

beforeAll(() => {
  for (const f of ["units","garments","fabrics","fill","geometry","satin","satinplay","satinfont","fontbin","dst","exp","pes","svgexport","fonts","digitize"])
    require("../../../src/" + f + ".js");
});

describe("fontLoader", () => {
  it("loadManifest returns verified fonts and caches", async () => {
    const { loadManifest } = await import("./fontLoader.js");
    const m1 = await loadManifest();
    // Floor, not exact: QC can demote individual fonts (e.g. ondulamarif_XL
    // dropped for 0-stitch letter glyphs). 60 is far above the pre-Slice-10
    // library of 21 while tolerating a handful of future demotions.
    expect(m1.fonts.length).toBeGreaterThanOrEqual(60);
    expect(m1.fonts.every((f) => f.tier === "verified")).toBe(true);
    expect(await loadManifest()).toBe(m1); // same object -> cached
  });

  it("ensureFont populates EMB.SATIN_FONTS and returns the font", async () => {
    const { ensureFont } = await import("./fontLoader.js");
    const g = globalThis;
    delete (g.EMB.SATIN_FONTS || {}).geneva_simple;
    const font = await ensureFont("geneva_simple");
    expect(font.glyphs).toBeTruthy();
    expect(g.EMB.SATIN_FONTS.geneva_simple).toBe(font);
  });

  it("concurrent ensureFont calls share one load", async () => {
    const { ensureFont } = await import("./fontLoader.js");
    const [a, b] = await Promise.all([ensureFont("cats"), ensureFont("cats")]);
    expect(a).toBe(b);
  });

  it("unknown key rejects with a clear error", async () => {
    const { ensureFont } = await import("./fontLoader.js");
    await expect(ensureFont("nope_font")).rejects.toThrow(/Unknown font: nope_font/);
  });

  it("a newly imported font actually builds lettering", async () => {
    const { ensureFont } = await import("./fontLoader.js");
    const g = globalThis;
    const font = await ensureFont("cats");
    const design = g.EMB.buildLetteringDesign(font, "AB", {
      garment: g.EMB.getGarment("left_chest"), pxPerMm: 8, densityMm: 0.4,
    });
    expect(design.stitchCount).toBeGreaterThan(100);
  });

  it("a failed font load does not poison the cache — retry can succeed", async () => {
    const { ensureFont } = await import("./fontLoader.js");
    // unknown key fails...
    await expect(ensureFont("transient_missing")).rejects.toThrow(/Unknown font/);
    // ...and a subsequent call for a REAL font still works (map not poisoned)
    const font = await ensureFont("geneva_simple");
    expect(font.glyphs).toBeTruthy();
    // and retrying the failed key fails freshly each time rather than returning
    // a stale cached rejection (two calls, two independent rejections)
    await expect(ensureFont("transient_missing")).rejects.toThrow(/Unknown font/);
    await expect(ensureFont("transient_missing")).rejects.toThrow(/Unknown font/);
  });
});
