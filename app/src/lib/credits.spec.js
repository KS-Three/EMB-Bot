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
});
