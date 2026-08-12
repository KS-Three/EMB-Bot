import { test, expect } from "vitest";
import { STEPS, canAdvance, nextStep, prevStep } from "./flow.js";
import { defaultProject, addElement, updateElement } from "./project.js";

test("steps order", () => { expect(STEPS).toEqual(["garment","content","create","download"]); });

test("create step gates on at least one ready text element", () => {
  const p = defaultProject(); // one empty text element
  expect(canAdvance("create", p)).toBe(false);
  expect(canAdvance("create", updateElement(p, "e1", { text: "Hi" }))).toBe(true);
});

test("create step gates on at least one ready image element", () => {
  let p = defaultProject();
  p = updateElement(p, "e1", { text: "" });
  p = addElement(p, "image", 100); // e2, image, no _hasImage yet
  expect(canAdvance("create", p)).toBe(false);
  const withImage = updateElement(p, "e2", { _hasImage: true });
  expect(canAdvance("create", withImage)).toBe(true);
});

test("create step advances if ANY element is ready, even if others are not", () => {
  let p = defaultProject(); // e1 text, empty
  p = addElement(p, "image", 100); // e2 image, not ready
  expect(canAdvance("create", p)).toBe(false);
  const ready = updateElement(p, "e1", { text: "Hi" });
  expect(canAdvance("create", ready)).toBe(true);
});

test("content step always advances", () => {
  expect(canAdvance("content", defaultProject())).toBe(true);
});

test("nav", () => {
  expect(nextStep("garment")).toBe("content");
  expect(prevStep("content")).toBe("garment");
  expect(nextStep("download")).toBe(null);
});

test("create step gates a manual element on having at least one valid completed shape", () => {
  let p = defaultProject();
  p = updateElement(p, "e1", { text: "" });
  p = addElement(p, "manual", 100); // e2
  expect(canAdvance("create", p)).toBe(false);

  // A degenerate/collinear "shape" (a mis-click) doesn't count as ready.
  const degenerate = updateElement(p, "e2", {
    shapes: [{ id: "s1", points: [{ x: 0, y: 0 }, { x: 5, y: 0 }, { x: 10, y: 0 }], stitchType: "fill", colorRgb: [1, 1, 1], angleDeg: null }],
  });
  expect(canAdvance("create", degenerate)).toBe(false);

  const ready = updateElement(p, "e2", {
    shapes: [{ id: "s1", points: [{ x: 0, y: 0 }, { x: 20, y: 0 }, { x: 10, y: 20 }], stitchType: "fill", colorRgb: [1, 1, 1], angleDeg: null }],
  });
  expect(canAdvance("create", ready)).toBe(true);
});

test("create step: a preset shape element is ready from birth (kind + params always generate)", () => {
  let p = defaultProject();
  p = updateElement(p, "e1", { text: "" }); // the default text element is NOT ready
  expect(canAdvance("create", p)).toBe(false);
  p = addElement(p, "shape", 100); // e2
  expect(canAdvance("create", p)).toBe(true);
});

test("create step gates design and digitized elements on their baked content, not _hasImage", () => {
  let p = defaultProject();
  p = updateElement(p, "e1", { text: "" });
  p = addElement(p, "design", 100); // e2
  expect(canAdvance("create", p)).toBe(false);
  expect(canAdvance("create", updateElement(p, "e2", { dstBase64: "QQ==" }))).toBe(true);

  let q = defaultProject();
  q = updateElement(q, "e1", { text: "" });
  q = addElement(q, "digitized", 100); // e2
  expect(canAdvance("create", q)).toBe(false);
  const ready = updateElement(q, "e2", { result: { stitches: [], colors: [] } });
  expect(canAdvance("create", ready)).toBe(true);
});
