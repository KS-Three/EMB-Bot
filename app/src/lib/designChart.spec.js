import { test, expect } from "vitest";
import { get } from "svelte/store";
import { chartIdForProject, designChartId } from "./designChart.js";

test("the first element carrying a brand wins", () => {
  expect(chartIdForProject({ elements: [
    { type: "text" },
    { type: "digitized", review: { brandId: "isacord" } },
    { type: "digitized", review: { brandId: "madeira-rayon" } },
  ]})).toBe("isacord");
});

test("a project with no digitized element has no chart, and says so", () => {
  // Lettering only: null, not "studio". The caller decides what a missing
  // chart falls back to; this function does not get to guess.
  expect(chartIdForProject({ elements: [{ type: "text" }] })).toBeNull();
  expect(chartIdForProject({ elements: [{ type: "digitized", review: null }] })).toBeNull();
  expect(chartIdForProject({ elements: [{ type: "digitized", review: { brandId: "" } }] })).toBeNull();
});

test("a missing or malformed project never throws", () => {
  for (const p of [null, undefined, {}, { elements: null }, { elements: [null, undefined] }]) {
    expect(() => chartIdForProject(p)).not.toThrow();
    expect(chartIdForProject(p)).toBeNull();
  }
});

test("the store starts empty so a picker mounted before any project reads null", () => {
  expect(get(designChartId)).toBeNull();
});
