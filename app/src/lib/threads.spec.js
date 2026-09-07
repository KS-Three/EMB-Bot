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

import {
  PALETTE_INDEX,
  STUDIO_PALETTE,
  getCachedPalette,
  loadPalette,
  nearestInList,
  filterThreads,
  loadPreferredPaletteId,
} from "./threads.js";
import { THREAD_BRAND_INDEX } from "./threadBrandsIndex.js";
import { THREAD_BRANDS } from "./threadBrandsData.js";

test("PALETTE_INDEX leads with the generic Studio list, then every generated brand", () => {
  expect(PALETTE_INDEX[0].id).toBe("studio");
  expect(PALETTE_INDEX[0].count).toBe(THREADS.length);
  expect(PALETTE_INDEX).toHaveLength(1 + THREAD_BRAND_INDEX.length);
  // The full Ink/Stitch sweep minus the software-company policy exclusions
  // (Brother x2, Janome, Viking, Floriani, Hemingworth — see
  // tools/build-threads.mjs POLICY_EXCLUDED). Grows only via new imports
  // from pure thread manufacturers.
  expect(THREAD_BRAND_INDEX.length).toBeGreaterThanOrEqual(68);
  for (const banned of ["brother-country", "brother-embroidery", "janome", "viking-palette", "floriani-polyester", "hemingworth"]) {
    expect(THREAD_BRAND_INDEX.some((e) => e.id === banned)).toBe(false);
  }
});

test("the static index and the lazy data module agree brand-for-brand", () => {
  expect(THREAD_BRAND_INDEX.length).toBe(THREAD_BRANDS.length);
  THREAD_BRAND_INDEX.forEach((entry, i) => {
    const brand = THREAD_BRANDS[i];
    expect(entry.id).toBe(brand.id);
    expect(entry.label).toBe(brand.label);
    expect(entry.count).toBe(brand.threads.length);
  });
  // The four pre-sweep charts keep their original ids so the stored
  // embstudio:threadPalette preference of an existing user still resolves.
  for (const legacy of ["isacord", "polyneon", "madeira-rayon", "robison-anton"]) {
    expect(THREAD_BRAND_INDEX.some((e) => e.id === legacy)).toBe(true);
  }
});

test("every brand entry is { name, code, rgb } with a valid 0-255 triple and a real catalog code", () => {
  // Plain-JS validation with aggregate assertions: ~20k entries x 8
  // expect() calls each blows straight through vitest's 5s test timeout,
  // so collect violations and assert once (the violation list names the
  // offenders on failure, which is better diagnostics anyway).
  const badEntries = [];
  const undersized = [];
  const codePoor = [];
  let total = 0;
  for (const brand of THREAD_BRANDS) {
    // Smallest legitimate chart is 15 colors (Simthread Glow In The Dark).
    if (brand.threads.length < 10) undersized.push(brand.id);
    total += brand.threads.length;
    let withCode = 0;
    for (const t of brand.threads) {
      const rgbOk =
        Array.isArray(t.rgb) &&
        t.rgb.length === 3 &&
        t.rgb.every((v) => Number.isInteger(v) && v >= 0 && v <= 255);
      if (typeof t.name !== "string" || t.name.length === 0 || typeof t.code !== "string" || !rgbOk) {
        badEntries.push(brand.id + ":" + JSON.stringify(t));
      }
      if (t.code.length > 0) withCode++;
    }
    // Codes must be present on essentially the whole chart (a few oddball
    // rows without one are tolerable, a systematically code-less parse is not).
    if (withCode / brand.threads.length <= 0.95) codePoor.push(brand.id);
  }
  expect(undersized).toEqual([]);
  expect(badEntries.slice(0, 5)).toEqual([]);
  expect(codePoor).toEqual([]);
  expect(total).toBeGreaterThan(15000); // the whole sweep, not a subset
});

test("loadPalette resolves brands lazily, caches them, and falls back to studio for unknown ids", async () => {
  const isacord = await loadPalette("isacord");
  expect(isacord.label).toMatch(/Isacord/);
  expect(isacord.threads.length).toBeGreaterThan(300);
  // After one successful load every brand is a synchronous cache hit
  // (the data module ships all brands in one chunk).
  expect(getCachedPalette("isacord")).toBe(isacord);
  expect(getCachedPalette("sulky-rayon")).not.toBeNull();
  expect((await loadPalette("nope")).id).toBe("studio");
  expect((await loadPalette(undefined)).id).toBe("studio");
  expect(getCachedPalette("studio")).toBe(STUDIO_PALETTE);
});

test("nearestInList matches nearestThread on the generic list and carries codes on brand lists", () => {
  const viaOld = nearestThread([15, 15, 17]);
  const viaNew = nearestInList(THREADS, [15, 15, 17]);
  expect(viaNew.name).toBe(viaOld.name);
  expect(viaNew.index).toBe(viaOld.index);
  expect(viaNew.code).toBe("");

  const isacord = THREAD_BRANDS.find((b) => b.id === "isacord").threads;
  const black = nearestInList(isacord, [0, 0, 0]);
  expect(black.code.length).toBeGreaterThan(0);
  expect(isacord[black.index].name).toBe(black.name);
});

test("filterThreads matches on name OR catalog code, case-insensitively; empty query returns the list untouched", () => {
  const isacord = THREAD_BRANDS.find((b) => b.id === "isacord").threads;
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

// --- The shopping list must name the cones the design actually sews --------
//
// Measured 2026-09-07 driving the real Download step: it defaulted to Studio's
// 56 generic shades on a design whose cones the engine had picked out of a
// 398-colour catalog. On `logo_bridge_bar` at 80 mm that collapsed 13 distinct
// cones to 9 names — 0501 Sun, 0713 Lemon and 6031 Limelight all printing
// "Lemon" — so a customer buys nine spools for a thirteen-cone design. And the
// names are not merely coarse: on `logo_golden_tee` the engine's `0670 Cream`
// printed as "Natural White" while `0630 Buttercup` printed as "Cream".
//
// This env has no localStorage (see the test above), so these exercise the
// no-stored-preference path — which is the one every first-time customer is
// on, and the only one that changed.

test("a design's own chart becomes the default when nothing is stored", () => {
  expect(loadPreferredPaletteId("isacord")).toBe("isacord");
  expect(loadPreferredPaletteId("madeira-rayon")).toBe("madeira-rayon");
});

test("a lettering-only project, with no design chart, keeps generic names", () => {
  expect(loadPreferredPaletteId()).toBe("studio");
  expect(loadPreferredPaletteId(null)).toBe("studio");
  expect(loadPreferredPaletteId("")).toBe("studio");
});

test("a chart id this build cannot load is never selected", () => {
  // The service knows 69 brands; a build that shipped before one of them must
  // not select a chart it cannot fetch — the summary would render no cones.
  expect(loadPreferredPaletteId("brand-from-the-future")).toBe("studio");
});

test("a stored preference still wins over the design's chart", () => {
  // The one case this env cannot reach on its own: someone who deliberately
  // picked "Studio basics" keeps it, and the selector is right there anyway.
  const saved = globalThis.localStorage;
  globalThis.localStorage = { getItem: () => "studio", setItem: () => {} };
  try {
    expect(loadPreferredPaletteId("isacord")).toBe("studio");
  } finally {
    if (saved === undefined) delete globalThis.localStorage;
    else globalThis.localStorage = saved;
  }
});
