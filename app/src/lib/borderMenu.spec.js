import { describe, expect, test } from "vitest";
import { ADD_TITLE, borderMenuItems, effectiveBorder } from "./borderMenu.js";

describe("effectiveBorder", () => {
  test("no override: the design-wide setting decides, and null means none", () => {
    expect(effectiveBorder(undefined, null)).toEqual({ bordered: false, source: "design" });
    expect(effectiveBorder({}, "off")).toEqual({ bordered: false, source: "design" });
    expect(effectiveBorder(null, "auto")).toEqual({ bordered: true, source: "design" });
    expect(effectiveBorder({ tier: "fill" }, "bean")).toEqual({ bordered: true, source: "design" });
    expect(effectiveBorder({}, "significant")).toEqual({ bordered: true, source: "design" });
  });

  test("an override beats the design setting either way", () => {
    expect(effectiveBorder({ border: "off" }, "auto")).toEqual({ bordered: false, source: "shape" });
    expect(effectiveBorder({ border: "auto" }, "off")).toEqual({ bordered: true, source: "shape" });
    expect(effectiveBorder({ border: "bean" }, null)).toEqual({ bordered: true, source: "shape" });
    // the service lower-cases on the way in; the menu reads the stored spelling the same way
    expect(effectiveBorder({ border: "AUTO" }, null)).toEqual({ bordered: true, source: "shape" });
  });

  test("a non-string override value is not a decision", () => {
    expect(effectiveBorder({ border: true }, null)).toEqual({ bordered: false, source: "design" });
  });
});

describe("borderMenuItems", () => {
  test("a shape with no border offers Add, writing the engine's auto value", () => {
    const items = borderMenuItems(undefined, null);
    expect(items.map((i) => i.id)).toEqual(["add"]);
    expect(items[0]).toMatchObject({ label: "Add border", value: "auto", title: ADD_TITLE });
  });

  test("a shape bordered by the design setting offers Remove only", () => {
    const items = borderMenuItems({}, "auto");
    expect(items.map((i) => i.id)).toEqual(["remove"]);
    expect(items[0]).toMatchObject({ label: "Remove border", value: "off" });
  });

  test("an override adds the way back to the design setting", () => {
    expect(borderMenuItems({ border: "off" }, "auto").map((i) => [i.id, i.value]))
      .toEqual([["add", "auto"], ["design", null]]);
    expect(borderMenuItems({ border: "bean" }, null).map((i) => [i.id, i.value]))
      .toEqual([["remove", "off"], ["design", null]]);
  });

  test("every item carries a title a tooltip can show", () => {
    for (const items of [borderMenuItems({}, null), borderMenuItems({ border: "auto" }, "off")]) {
      for (const it of items) expect(typeof it.title).toBe("string");
    }
  });
});
