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
