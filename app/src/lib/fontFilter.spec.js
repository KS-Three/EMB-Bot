import { describe, it, expect } from "vitest";
import { filterFonts, sizeBand } from "./fontFilter.js";

const FONTS = [
  { key: "geneva_simple", name: "Geneva Simple", group: "Sans" },
  { key: "aventurina", name: "Aventurina", group: "Script" },
  { key: "cats", name: "Cats", group: "Display" },
  { key: "small_font", name: "Small Font", group: "Small" },
];

describe("filterFonts", () => {
  it("no query, group All returns everything", () => {
    expect(filterFonts(FONTS, "", "All")).toHaveLength(4);
  });
  it("group filter narrows", () => {
    expect(filterFonts(FONTS, "", "Script").map((f) => f.key)).toEqual(["aventurina"]);
  });
  it("query matches name case-insensitively", () => {
    expect(filterFonts(FONTS, "gen", "All").map((f) => f.key)).toEqual(["geneva_simple"]);
  });
  it("query matches key too", () => {
    expect(filterFonts(FONTS, "small_f", "All")).toHaveLength(1);
  });
  it("query and group compose", () => {
    expect(filterFonts(FONTS, "a", "Display").map((f) => f.key)).toEqual(["cats"]);
  });
  it("no match returns empty, never throws", () => {
    expect(filterFonts(FONTS, "zzz", "All")).toEqual([]);
    expect(filterFonts([], "x", "Sans")).toEqual([]);
  });

  // Key-matching stopped being a convenience on 2026-08-22 and became the only
  // route to three shipped fonts. The library now carries names written in
  // their own scripts — "חוכמה Large", "Кирилиця" — which a customer on a
  // Latin keyboard cannot type. If this search ever narrowed to `name`, those
  // fonts would still be in the manifest, still render, and be unreachable
  // from the browser, with nothing failing anywhere.
  //
  // Asserted against the REAL manifest rather than a fixture, because the
  // property is about the fonts that actually ship.
  it("every shipped font is reachable from a Latin keyboard", async () => {
    const { createRequire } = await import("node:module");
    const require = createRequire(import.meta.url);
    const man = require("../../../src/fonts/manifest.json");
    expect(man.fonts.length).toBeGreaterThan(50); // an empty list would assert nothing
    const unreachable = man.fonts
      .filter((f) => !filterFonts(man.fonts, f.key, "All").some((x) => x.key === f.key))
      .map((f) => f.key);
    expect(unreachable).toEqual([]);
  });

  it("finds the non-Latin-named fonts by the script they are FOR", async () => {
    const { createRequire } = await import("node:module");
    const require = createRequire(import.meta.url);
    const man = require("../../../src/fonts/manifest.json");
    const keys = (q) => filterFonts(man.fonts, q, "All").map((f) => f.key).sort();
    // A customer looking for Hebrew types "hebrew", not "חוכמה".
    expect(keys("hebrew")).toEqual(["hebrew_font_large", "hebrew_font_medium"]);
    expect(keys("cyrillic")).toEqual(["cyrillic"]);
    // ...and someone who CAN type the name still finds it.
    expect(keys("חוכמה")).toEqual(["hebrew_font_large", "hebrew_font_medium"]);
  });
});

describe("sizeBand", () => {
  it("derives 0.75x-2x from authored size", () => {
    expect(sizeBand(20)).toEqual({ min: 15, max: 40 });
  });
  it("null on missing size", () => {
    expect(sizeBand(undefined)).toBeNull();
    expect(sizeBand(0)).toBeNull();
  });
});
