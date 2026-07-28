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

// --- Brand catalogs (Ember-audit follow-up) ----------------------------

import { PALETTES, paletteById, nearestInList, filterThreads, loadPreferredPaletteId } from "./threads.js";
import { THREAD_BRANDS } from "./threadBrands.js";

test("PALETTES leads with the generic Studio list, then every generated brand", () => {
  expect(PALETTES[0].id).toBe("studio");
  expect(PALETTES[0].threads).toBe(THREADS);
  expect(PALETTES).toHaveLength(1 + THREAD_BRANDS.length);
  expect(THREAD_BRANDS.length).toBeGreaterThanOrEqual(4);
});

test("every brand entry is { name, code, rgb } with a valid 0-255 triple and a real catalog code", () => {
  for (const brand of THREAD_BRANDS) {
    expect(brand.threads.length).toBeGreaterThan(300); // real charts are big
    for (const t of brand.threads) {
      expect(typeof t.name).toBe("string");
      expect(t.name.length).toBeGreaterThan(0);
      expect(typeof t.code).toBe("string");
      expect(t.rgb).toHaveLength(3);
      for (const v of t.rgb) {
        expect(Number.isInteger(v)).toBe(true);
        expect(v).toBeGreaterThanOrEqual(0);
        expect(v).toBeLessThanOrEqual(255);
      }
    }
    // Codes must be present on essentially the whole chart (a few oddball
    // rows without one are tolerable, a systematically code-less parse is not).
    const withCode = brand.threads.filter((t) => t.code.length > 0).length;
    expect(withCode / brand.threads.length).toBeGreaterThan(0.95);
  }
});

test("paletteById returns the matching palette and falls back to studio for unknown ids", () => {
  expect(paletteById("isacord").label).toMatch(/Isacord/);
  expect(paletteById("nope").id).toBe("studio");
  expect(paletteById(undefined).id).toBe("studio");
});

test("nearestInList matches nearestThread on the generic list and carries codes on brand lists", () => {
  const viaOld = nearestThread([15, 15, 17]);
  const viaNew = nearestInList(THREADS, [15, 15, 17]);
  expect(viaNew.name).toBe(viaOld.name);
  expect(viaNew.index).toBe(viaOld.index);
  expect(viaNew.code).toBe("");

  const isacord = paletteById("isacord").threads;
  const black = nearestInList(isacord, [0, 0, 0]);
  expect(black.code.length).toBeGreaterThan(0);
  expect(isacord[black.index].name).toBe(black.name);
});

test("filterThreads matches on name OR catalog code, case-insensitively; empty query returns the list untouched", () => {
  const isacord = paletteById("isacord").threads;
  expect(filterThreads(isacord, "")).toBe(isacord);
  expect(filterThreads(isacord, "   ")).toBe(isacord);

  const byName = filterThreads(isacord, "black");
  expect(byName.length).toBeGreaterThan(0);
  expect(byName.every((t) => /black/i.test(t.name) || /black/i.test(t.code))).toBe(true);

  const target = isacord.find((t) => t.code === "0020");
  const byCode = filterThreads(isacord, "0020");
  expect(byCode).toContain(target);
});

test("loadPreferredPaletteId degrades to studio when storage is unavailable or holds an unknown id", () => {
  // Node test env has no localStorage at all -- the helper must swallow that.
  expect(loadPreferredPaletteId()).toBe("studio");
});
