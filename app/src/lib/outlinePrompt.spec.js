import { describe, it, expect } from "vitest";
import {
  outlineRows, undecidedOutlineIds, removedOutlineIds,
  keepPatch, removePatch, putBackPatch, throbAt, THROB_MS,
} from "./outlinePrompt.js";
import { canonicalShapeEdits, editsKey, reviewFromJob } from "./digitizer.js";

const el = (over = {}) => ({
  type: "digitized",
  review: {
    shapes: [
      { id: "Sword", stitched: true, hairlineOutline: false },
      { id: "Skey1", stitched: true, hairlineOutline: true },
      { id: "Skey2", stitched: true, hairlineOutline: true },
    ],
  },
  shapeOverrides: {},
  deletedShapeIds: [],
  keptOutlineIds: [],
  ...over,
});

describe("the thin-outline prompt", () => {
  it("reads the digitizer's mark off the wire, and only a true one", () => {
    const review = reviewFromJob({
      shapes: [
        { shape_id: "Sa", thread_index: 0, outline_mm: [[0, 0], [1, 0], [1, 1]], hairline_outline: true },
        { shape_id: "Sb", thread_index: 0, outline_mm: [[0, 0], [1, 0], [1, 1]] },
      ],
      palette: [{ rgb: [1, 2, 3] }],
    });
    expect(review.shapes.map((r) => r.hairlineOutline)).toEqual([true, false]);
  });

  it("asks about every marked shape that is still sewn and unanswered", () => {
    expect(outlineRows(el()).map((r) => r.id)).toEqual(["Skey1", "Skey2"]);
    expect(undecidedOutlineIds(el())).toEqual(["Skey1", "Skey2"]);
    expect(undecidedOutlineIds(el({ review: null }))).toEqual([]);
    expect(undecidedOutlineIds({})).toEqual([]);
  });

  it("does not ask about a shape that is not sewn", () => {
    expect(undecidedOutlineIds(el({ shapeOverrides: { Skey1: { stitched: false } } }))).toEqual(["Skey2"]);
  });

  it("Keep remembers the answer and is not a shape edit", () => {
    const before = el();
    const after = { ...before, ...keepPatch(before) };
    expect(after.keptOutlineIds).toEqual(["Skey1", "Skey2"]);
    expect(undecidedOutlineIds(after)).toEqual([]);
    // nothing about the stitches changed, so the design must not read stale
    expect(editsKey(canonicalShapeEdits(after))).toBe(editsKey(canonicalShapeEdits(before)));
  });

  it("Remove hides every undecided outline in one patch, restorably", () => {
    const before = el({ deletedShapeIds: ["Sold"] });
    const after = { ...before, ...removePatch(before) };
    expect(after.deletedShapeIds).toEqual(["Sold", "Skey1", "Skey2"]);
    expect(undecidedOutlineIds(after)).toEqual([]);
    expect(removedOutlineIds(after)).toEqual(["Skey1", "Skey2"]);
    // a real edit: the design waits on Auto Digitize
    expect(editsKey(canonicalShapeEdits(after))).not.toBe(editsKey(canonicalShapeEdits(before)));
  });

  it("Put back un-hides them, leaves other hidden shapes hidden, and does not ask again", () => {
    const removed = { ...el({ deletedShapeIds: ["Sold"] }) };
    Object.assign(removed, removePatch(removed));
    const back = { ...removed, ...putBackPatch(removed) };
    expect(back.deletedShapeIds).toEqual(["Sold"]);
    expect(removedOutlineIds(back)).toEqual([]);
    expect(undecidedOutlineIds(back)).toEqual([]);
  });

  it("a new outline after a re-digitize is asked about even when older ones were kept", () => {
    const kept = el({ keptOutlineIds: ["Skey1"] });
    expect(undecidedOutlineIds(kept)).toEqual(["Skey2"]);
  });

  it("throbs between 0 and 1, one breath per period", () => {
    expect(throbAt(0)).toBeCloseTo(0);
    expect(throbAt(THROB_MS / 2)).toBeCloseTo(1);
    expect(throbAt(THROB_MS)).toBeCloseTo(0);
    for (let t = 0; t < THROB_MS; t += 37) {
      expect(throbAt(t)).toBeGreaterThanOrEqual(0);
      expect(throbAt(t)).toBeLessThanOrEqual(1);
    }
  });
});
