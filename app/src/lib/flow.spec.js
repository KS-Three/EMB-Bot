import { test, expect } from "vitest";
import { STEPS, canAdvance, nextStep, prevStep } from "./flow.js";
import { defaultProject, update } from "./project.js";

test("steps order", () => { expect(STEPS).toEqual(["garment","text","preview","download"]); });

test("text step blocks empty text", () => {
  const p = defaultProject();
  expect(canAdvance("text", p)).toBe(false);
  expect(canAdvance("text", update(p, { text: "Hi" }))).toBe(true);
});

test("nav", () => {
  expect(nextStep("garment")).toBe("text");
  expect(prevStep("text")).toBe("garment");
  expect(nextStep("download")).toBe(null);
});
