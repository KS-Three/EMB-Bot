import { test, expect } from "vitest";
import { STEPS, canAdvance, nextStep, prevStep } from "./flow.js";
import { defaultProject, update } from "./project.js";

test("steps order", () => { expect(STEPS).toEqual(["garment","content","create","download"]); });

test("create step gates by mode", () => {
  const p = defaultProject(); // mode text, empty text
  expect(canAdvance("create", p)).toBe(false);
  expect(canAdvance("create", update(p, { text: "Hi" }))).toBe(true);
  const pi = update(p, { mode: "image" });
  expect(canAdvance("create", pi)).toBe(false);
  expect(canAdvance("create", update(pi, { _hasImage: true }))).toBe(true);
});

test("content step always advances", () => {
  expect(canAdvance("content", defaultProject())).toBe(true);
});

test("nav", () => {
  expect(nextStep("garment")).toBe("content");
  expect(prevStep("content")).toBe("garment");
  expect(nextStep("download")).toBe(null);
});
