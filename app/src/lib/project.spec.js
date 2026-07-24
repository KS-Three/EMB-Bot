import { test, expect } from "vitest";
import { defaultProject, update } from "./project.js";
test("defaultProject has sane beginner defaults", () => {
  const p = defaultProject();
  expect(p.garmentId).toBe("left_chest");
  expect(p.text).toBe("");
  expect(p.fontKey).toBe("geneva_simple");
  expect(p.colorRgb).toEqual([20, 20, 20]);
  expect(p.underlay).toBe(true);
});
test("defaults include image-mode fields", () => {
  const p = defaultProject();
  expect(p.mode).toBe("text");
  expect(p.nColors).toBe(4);
  expect(p.removeBg).toBe(true);
});
test("update returns a new object and merges", () => {
  const p = defaultProject();
  const q = update(p, { text: "Kent" });
  expect(q.text).toBe("Kent");
  expect(p.text).toBe(""); // original untouched
});
