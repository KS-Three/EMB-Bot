import { test, expect } from "vitest";
import { BASE_SPS, SPEEDS, advanceIndex, clampIndex, nextSpeed } from "./simulate.js";

// --- advanceIndex -----------------------------------------------------------

test("advanceIndex moves BASE_SPS strands in exactly one second at 1x", () => {
  expect(advanceIndex(0, 1000, 1, 100000)).toBeCloseTo(BASE_SPS, 6);
});

test("advanceIndex scales linearly with speed", () => {
  const at1x = advanceIndex(0, 200, 1, 100000);
  const at4x = advanceIndex(0, 200, 4, 100000);
  expect(at4x).toBeCloseTo(at1x * 4, 6);
});

test("advanceIndex accumulates fractional progress across small frames (no stall at slow speeds)", () => {
  // 60fps frames at 1x: each frame adds BASE_SPS/60 ≈ 4.17 -- but even a
  // 1ms frame must add SOMETHING, carried as a float.
  let idx = 0;
  for (let i = 0; i < 10; i++) idx = advanceIndex(idx, 1, 1, 100000);
  expect(idx).toBeCloseTo((10 / 1000) * BASE_SPS, 6);
  expect(idx).toBeGreaterThan(0);
});

test("advanceIndex clamps at total and never goes below 0", () => {
  expect(advanceIndex(95, 60000, 8, 100)).toBe(100);
  expect(advanceIndex(0, -50, 1, 100)).toBe(0); // negative dt (clock skew) is treated as 0
  expect(advanceIndex(0, NaN, 1, 100)).toBe(0);
});

// --- clampIndex -------------------------------------------------------------

test("clampIndex floors and clamps scrub input to [0, total]", () => {
  expect(clampIndex("42.9", 100)).toBe(42);
  expect(clampIndex(-5, 100)).toBe(0);
  expect(clampIndex(250, 100)).toBe(100);
  expect(clampIndex("not a number", 100)).toBe(0);
});

// --- nextSpeed --------------------------------------------------------------

test("nextSpeed cycles through every option and wraps back to the first", () => {
  let s = SPEEDS[0];
  const seen = [s];
  for (let i = 1; i < SPEEDS.length; i++) {
    s = nextSpeed(s);
    seen.push(s);
  }
  expect(seen).toEqual(SPEEDS);
  expect(nextSpeed(s)).toBe(SPEEDS[0]);
});

test("nextSpeed recovers from an unknown speed by returning the first option", () => {
  expect(nextSpeed(3)).toBe(SPEEDS[0]);
});
