import { test, expect } from "vitest";
import { pickScaleBar } from "./scalebar.js";

test("picks the longest round length that fits the budget", () => {
  // 5.4 px/mm is the Left-chest template at fit zoom on a 1440x900 field:
  // 20 mm = 108 px fits a 120 px budget, 25 mm = 135 px does not.
  expect(pickScaleBar(5.4)).toEqual({ mm: 20, px: 108, label: "20 mm" });
});

test("zooming in shortens the length, never the bar past its budget", () => {
  // Same field at 4x: 21.6 px/mm. 5 mm = 108 px fits, 10 mm = 216 does not.
  const bar = pickScaleBar(5.4 * 4);
  expect(bar.mm).toBe(5);
  expect(bar.px).toBeLessThanOrEqual(120);
});

test("the ends of the ladder: a tiny scale takes the longest step, an absurd zoom falls back to the shortest", () => {
  expect(pickScaleBar(0.1).mm).toBe(200); // 200 mm is a 20 px bar; nothing longer is offered
  const bar = pickScaleBar(500); // 1 mm is already 500 px -- over budget, but there is no shorter step
  expect(bar.mm).toBe(1);
  expect(bar.px).toBe(500);
});

test("no scale, no bar", () => {
  expect(pickScaleBar(0)).toBeNull();
  expect(pickScaleBar(undefined)).toBeNull();
  expect(pickScaleBar(NaN)).toBeNull();
});

test("the budget is a parameter, so a narrower bar picks a shorter step", () => {
  expect(pickScaleBar(5.4, 60).mm).toBe(10); // 10 mm = 54 px fits 60; 20 mm = 108 does not
});
