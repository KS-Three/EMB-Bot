import { test, expect } from "vitest";
import { HELP, HELP_KEYS, helpText } from "./settingHelp.js";

// The copy is data Kent edits by hand, so the shape is what a test can hold:
// three sentences per entry, none empty, none a wall, and every key that a
// component asks for present. The wording itself is his.

test("every entry has a title and the three sentences, and none is empty", () => {
  expect(HELP_KEYS.length).toBeGreaterThanOrEqual(24);
  for (const key of HELP_KEYS) {
    const h = HELP[key];
    for (const part of ["title", "what", "changes", "when"]) {
      expect(typeof h[part], `${key}.${part}`).toBe("string");
      expect(h[part].trim().length, `${key}.${part} is empty`).toBeGreaterThan(0);
    }
    expect(Object.keys(h).sort()).toEqual(["changes", "title", "what", "when"]);
  }
});

test("an entry fits a popover: no sentence over 320 characters, the three together under 700", () => {
  for (const key of HELP_KEYS) {
    const h = HELP[key];
    for (const part of ["what", "changes", "when"]) {
      expect(h[part].length, `${key}.${part} runs long`).toBeLessThanOrEqual(320);
    }
    expect(h.what.length + h.changes.length + h.when.length, `${key} runs long`).toBeLessThanOrEqual(700);
  }
});

test("the sentences end as sentences, so the plain-text form reads", () => {
  for (const key of HELP_KEYS) {
    const h = HELP[key];
    for (const part of ["what", "changes", "when"]) {
      expect(/[.!?°]$/.test(h[part].trim()), `${key}.${part} lacks a full stop`).toBe(true);
    }
  }
});

test("helpText joins the parts in order and labels the middle two; an unknown key is empty", () => {
  const t = helpText("fillAngle");
  expect(t.startsWith("Fill angle. The direction")).toBe(true);
  expect(t).toMatch(/ Changes: .* When: /);
  expect(helpText("nope")).toBe("");
});

test("the keys the components attach exist", () => {
  const wanted = [
    "designWidth", "colors", "satinThin", "evenWidths", "fillAngle", "border", "designEdge", "photoReading",
    "shapeTier", "shapeAngle", "shapeUnderlay", "shapeBorder", "stitchWidth", "wholeWord",
    "fitToHoop", "autoSnap", "outlines", "jumps", "trims", "realistic", "simulator",
    "letterSpacing", "curve", "rotation",
  ];
  for (const k of wanted) expect(HELP[k], k).toBeTruthy();
});
