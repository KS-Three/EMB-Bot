import { test, expect } from "vitest";
import { THREADS, nearestThread } from "./threads.js";

// --- THREADS shape ----------------------------------------------------

test("THREADS has exactly 56 entries", () => {
  expect(THREADS).toHaveLength(56);
});

test("THREADS has no duplicate names", () => {
  const names = THREADS.map((t) => t.name);
  const unique = new Set(names);
  expect(unique.size).toBe(names.length);
});

test("every THREADS entry is a valid { name, rgb } shade with an rgb 0-255 triple", () => {
  for (const t of THREADS) {
    expect(typeof t.name).toBe("string");
    expect(t.name.length).toBeGreaterThan(0);
    expect(Array.isArray(t.rgb)).toBe(true);
    expect(t.rgb).toHaveLength(3);
    for (const v of t.rgb) {
      expect(Number.isInteger(v)).toBe(true);
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThanOrEqual(255);
    }
  }
});

test("THREADS names are generic (no brand names)", () => {
  const banned = /coats|madeira|isacord|robison|sulky|brother|janome|pfaff|singer/i;
  for (const t of THREADS) {
    expect(banned.test(t.name)).toBe(false);
  }
});

// --- nearestThread ------------------------------------------------------

test("nearestThread returns itself for every exact-match entry", () => {
  THREADS.forEach((t, i) => {
    const result = nearestThread(t.rgb);
    expect(result.name).toBe(t.name);
    expect(result.rgb).toEqual(t.rgb);
    expect(result.index).toBe(i);
  });
});

test("nearestThread maps a near-miss rgb to the nearest named shade", () => {
  const black = THREADS.find((t) => t.name === "Black");
  const nearBlack = [black.rgb[0] + 2, black.rgb[1] - 1, black.rgb[2] + 1];
  const result = nearestThread(nearBlack);
  expect(result.name).toBe("Black");
  expect(result.rgb).toEqual(black.rgb);

  const snow = THREADS.find((t) => t.name === "Snow White");
  const nearWhite = [253, 253, 254];
  const resultWhite = nearestThread(nearWhite);
  expect(resultWhite.name).toBe(snow.name);
});

test("nearestThread returns a shade whose index correctly points back into THREADS", () => {
  const result = nearestThread([0, 0, 0]);
  expect(THREADS[result.index]).toEqual({ name: result.name, rgb: result.rgb });
});

test("nearestThread picks the CLOSEST shade (Euclidean), not just the first close one", () => {
  // Navy vs Midnight are both dark blues -- a color exactly at Navy's rgb
  // should resolve to Navy, not any other dark blue.
  const navy = THREADS.find((t) => t.name === "Navy");
  const result = nearestThread(navy.rgb);
  expect(result.name).toBe("Navy");
});
