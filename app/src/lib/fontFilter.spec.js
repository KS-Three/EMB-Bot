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
