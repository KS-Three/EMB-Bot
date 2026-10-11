import { beforeAll, expect, test } from "vitest";
import { createRequire } from "node:module";

// The hooping card's rows. The advice is the engine's (test/fabrics.test.js
// pins it); these pin the adapter's own contract — which design field it
// reads, and that it says nothing when there is nothing to stand on.

let hoopingRows;
let EMB;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  require("../../../src/fabrics.js");
  EMB = globalThis.EMB;
  // lib/emb.js refuses to load without the lettering engine; this spec needs
  // only fabrics.js (same stub DownloadSheet.spec.js uses).
  EMB.buildLetteringDesign =
    EMB.buildLetteringDesign || (() => { throw new Error("not used by this spec"); });
  ({ hoopingRows } = await import("./hooping.js"));
});

const design = (stitchCount) => ({ widthMM: 80, heightMM: 40, stitchCount, stitches: [] });

test("states stabilizer, topper and needle for a garment we ship", () => {
  expect(hoopingRows("left_chest", design(4321))).toEqual([
    { label: "Stabilizer", value: "cutaway", note: "" },
    { label: "Topper", value: "no", note: "" },
    { label: "Needle", value: "75/11 ballpoint", note: "standard for 40wt thread" },
  ]);
  expect(hoopingRows("towel", design(4321))[1].value).toBe("yes");
  expect(hoopingRows("tote", design(4321))[2].value).toBe("75/11 sharp");
});

test("the rows are the worksheet's lines, word for word", () => {
  // One function behind both documents is the point of the card; this is the
  // assertion that would fail if someone gave the screen its own wording.
  const rows = hoopingRows("tote", design(26676));
  expect(rows.map(EMB.hoopingLine)).toEqual([
    "Stabilizer: cutaway (escalated - 26,676 stitches; tear-away releases under this much thread)",
    "Topper: no",
    "Needle: 75/11 sharp (standard for 40wt thread)",
  ]);
  // Exactly at the threshold is not "over".
  expect(hoopingRows("tote", design(25000))[0]).toEqual({ label: "Stabilizer", value: "tearaway", note: "" });
});

test("says nothing without a design, without stitches, or for an unknown garment", () => {
  expect(hoopingRows("left_chest", null)).toEqual([]);
  expect(hoopingRows("left_chest", design(0))).toEqual([]);
  expect(hoopingRows("no_such_garment", design(4321))).toEqual([]);
  expect(hoopingRows("", design(4321))).toEqual([]);
});
