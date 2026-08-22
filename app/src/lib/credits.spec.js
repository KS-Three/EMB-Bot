import { describe, it, expect } from "vitest";
import { creditLines, MODIFICATION_NOTE } from "./credits.js";

const FONTS = [
  { key: "b_font", name: "Bravo", licenseId: "CC-BY-SA-4.0", attribution: "Adapted by X", source: "Ink/Stitch" },
  { key: "a_font", name: "Alpha", licenseId: "OFL-1.1", attribution: "Adapted by Y", source: "Ink/Stitch" },
];

describe("creditLines", () => {
  it("sorts by display name and carries license fields through", () => {
    const lines = creditLines(FONTS);
    expect(lines.map((l) => l.name)).toEqual(["Alpha", "Bravo"]);
    expect(lines[0]).toMatchObject({ licenseId: "OFL-1.1", attribution: "Adapted by Y", source: "Ink/Stitch", binHref: "/fonts/bin/a_font.embf" });
  });
  it("tolerates missing attribution without throwing", () => {
    const lines = creditLines([{ key: "x", name: "X", licenseId: "CC0" }]);
    expect(lines[0].attribution).toBe("");
  });
  it("links each font's local full license text and carries the modification note", () => {
    // font-license-audit-2026-07-31.md item 7: author/copyright line
    // (attribution, covered above), modification note (CC §3(a)(1)(B)),
    // and a link to the LOCAL LICENSE.txt shipped by copy-engine.mjs.
    const lines = creditLines(FONTS);
    expect(lines[0].licenseHref).toBe("/fonts/a_font.LICENSE.txt");
    expect(lines[1].licenseHref).toBe("/fonts/b_font.LICENSE.txt");
    expect(lines[0].modificationNote).toBe(MODIFICATION_NOTE);
    expect(MODIFICATION_NOTE).toMatch(/[Mm]odified/);
  });

  // The credits dialog is where the OFL's "this licence must accompany every
  // copy" obligation is actually discharged, and a broken link there fails
  // silently — a 404 in a dialog nobody opens twice. So pin it against the
  // REAL manifest rather than a fixture: every shipped font gets a line, and
  // every line's licence href names a file that exists.
  //
  // credits.js builds "/fonts/<key>.LICENSE.txt" and copy-engine copies
  // src/fonts/<key>.LICENSE.txt to that path; this holds the two ends of that
  // convention together. Verified 2026-08-22 — 85 of 85, no gaps.
  it("every shipped font gets a complete credit line with a real licence file", async () => {
    const { createRequire } = await import("node:module");
    const require = createRequire(import.meta.url);
    const fs = require("node:fs");
    const path = require("node:path");
    const man = require("../../../src/fonts/manifest.json");
    expect(man.fonts.length).toBeGreaterThan(50); // an empty manifest asserts nothing

    const lines = creditLines(man.fonts);
    expect(lines).toHaveLength(man.fonts.length);

    const FONT_DIR = path.join(__dirname, "..", "..", "..", "src", "fonts");
    const broken = lines
      .filter((l) => !fs.existsSync(path.join(FONT_DIR, l.licenseHref.split("/").pop())))
      .map((l) => l.licenseHref);
    expect(broken).toEqual([]);

    const incomplete = lines
      .filter((l) => !l.attribution || !l.licenseId || !l.source)
      .map((l) => l.name);
    expect(incomplete).toEqual([]);
  });
});
