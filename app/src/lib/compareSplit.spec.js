import { describe, expect, test } from "vitest";
import {
  SPLIT_DEFAULT,
  SPLIT_STEP,
  SPLIT_STEP_COARSE,
  clampSplit,
  splitFromClientX,
  splitKey,
  clipForSplit,
  splitPercent,
  splitValueText,
} from "./compareSplit.js";

describe("clampSplit", () => {
  test("keeps 0..1 and clamps outside it", () => {
    expect(clampSplit(0.3)).toBe(0.3);
    expect(clampSplit(-2)).toBe(0);
    expect(clampSplit(7)).toBe(1);
  });
  test("garbage falls back to the default, never NaN", () => {
    expect(clampSplit(NaN)).toBe(SPLIT_DEFAULT);
    expect(clampSplit(undefined)).toBe(SPLIT_DEFAULT);
    expect(clampSplit("x")).toBe(SPLIT_DEFAULT);
  });
});

describe("splitFromClientX", () => {
  const rect = { left: 100, width: 400 };
  test("maps the pointer onto the overlay's own box", () => {
    expect(splitFromClientX(100, rect)).toBe(0);
    expect(splitFromClientX(300, rect)).toBe(0.5);
    expect(splitFromClientX(500, rect)).toBe(1);
  });
  test("a pointer past either edge pins the split to that edge", () => {
    expect(splitFromClientX(-50, rect)).toBe(0);
    expect(splitFromClientX(900, rect)).toBe(1);
  });
  test("a zero-width box (mid-layout) keeps the default", () => {
    expect(splitFromClientX(300, { left: 0, width: 0 })).toBe(SPLIT_DEFAULT);
    expect(splitFromClientX(300, null)).toBe(SPLIT_DEFAULT);
  });
});

describe("splitKey", () => {
  test("arrows step, Shift steps coarse", () => {
    expect(splitKey(0.5, "ArrowRight")).toBeCloseTo(0.5 + SPLIT_STEP, 9);
    expect(splitKey(0.5, "ArrowLeft")).toBeCloseTo(0.5 - SPLIT_STEP, 9);
    expect(splitKey(0.5, "ArrowRight", true)).toBeCloseTo(0.5 + SPLIT_STEP_COARSE, 9);
    expect(splitKey(0.5, "ArrowLeft", true)).toBeCloseTo(0.5 - SPLIT_STEP_COARSE, 9);
  });
  test("Home and End go to the ends", () => {
    expect(splitKey(0.42, "Home")).toBe(0);
    expect(splitKey(0.42, "End")).toBe(1);
  });
  test("clamped at the ends", () => {
    expect(splitKey(0, "ArrowLeft")).toBe(0);
    expect(splitKey(1, "ArrowRight", true)).toBe(1);
  });
  test("fifty presses land exactly on the end, no float drift", () => {
    let s = 0;
    for (let i = 0; i < 50; i++) s = splitKey(s, "ArrowRight");
    expect(s).toBe(1);
    for (let i = 0; i < 25; i++) s = splitKey(s, "ArrowLeft");
    expect(s).toBe(0.5);
  });
  test("keys the field and the simulator own are not taken", () => {
    for (const k of ["Tab", "[", "]", "<", ">", ",", ".", "Enter", "Escape", "Delete", " "]) {
      expect(splitKey(0.5, k)).toBeNull();
    }
  });
});

describe("clipForSplit", () => {
  test("insets from the right by the stitch side's share", () => {
    expect(clipForSplit(0.5)).toBe("inset(0 50% 0 0)");
    expect(clipForSplit(1)).toBe("inset(0 0% 0 0)");
    expect(clipForSplit(0)).toBe("inset(0 100% 0 0)");
    expect(clipForSplit(0.25)).toBe("inset(0 75% 0 0)");
  });
});

describe("value for assistive tech", () => {
  test("percent is whole, text names both sides", () => {
    expect(splitPercent(0.333)).toBe(33);
    expect(splitValueText(0.3)).toBe("Artwork 30%, stitches 70%");
  });
});
