import { test, expect } from "vitest";
import { THREAD_BRANDS } from "./threadBrandsData.js";
import { THREAD_BRAND_INDEX } from "./threadBrandsIndex.js";

// Integrity of the generated manufacturer charts (tools/build-threads.mjs).
// The data comes from upstream Ink/Stitch palette files, so these pin what a
// customer would notice: a swatch that renders wrong, a row that names no
// thread, one code that shows two different colours.

const rows = THREAD_BRANDS.flatMap((b) => b.threads.map((t) => ({ brand: b.id, ...t })));

// Same code, visibly different colour. All are upstream conflicts we cannot
// settle without the manufacturer's printed card -- see the PR body. This list
// may only shrink: a NEW conflict fails the test below.
const KNOWN_CODE_CONFLICTS = new Set([
  "dmc:0000", "anchor:164", "anchor:218", "anchor:306",
  "embroidex:2106", "emmel:ML1338", "sigma:ST448",
  "sulky-polyester:1001", "sulky-polyester:304",
  "royal-polyester:P152", "royal-polyester:P153", "royal-polyester:P196",
  "royal-polyester:P232", "royal-polyester:P239",
  "royal-polyester:P311", "royal-polyester:P7188",
]);

test("brand index matches the data module (ids, order, counts)", () => {
  expect(THREAD_BRAND_INDEX.map((b) => [b.id, b.label, b.count])).toEqual(
    THREAD_BRANDS.map((b) => [b.id, b.label, b.threads.length]),
  );
});

test("every thread has a non-empty trimmed name and an RGB triple of integers 0-255", () => {
  // ~20k rows: a vitest expect() per field costs seconds, so test in plain
  // code and assert once on the list of offenders.
  const bad = [];
  for (const t of rows) {
    const ok =
      typeof t.name === "string" && t.name.length > 0 && t.name === t.name.trim() &&
      Array.isArray(t.rgb) && t.rgb.length === 3 &&
      t.rgb.every((v) => Number.isInteger(v) && v >= 0 && v <= 255);
    if (!ok) bad.push(`${t.brand} ${t.code} ${t.name} ${t.rgb}`);
  }
  expect(bad).toEqual([]);
});

test("no name carries runs of spaces", () => {
  expect(rows.filter((t) => /\s{2,}/.test(t.name)).map((t) => `${t.brand} ${t.code}`)).toEqual([]);
});

test("no brand repeats a name+code+colour row", () => {
  for (const b of THREAD_BRANDS) {
    const keys = b.threads.map((t) => `${t.name}|${t.code}|${t.rgb}`);
    expect(new Set(keys).size, b.id).toBe(keys.length);
  }
});

test("a code never shows two visibly different colours, bar the known upstream conflicts", () => {
  const found = new Set();
  for (const b of THREAD_BRANDS) {
    const byCode = new Map();
    for (const t of b.threads) {
      if (!t.code) continue;
      const prev = byCode.get(t.code);
      if (prev && prev.rgb.some((v, i) => Math.abs(v - t.rgb[i]) > 2)) found.add(`${b.id}:${t.code}`);
      byCode.set(t.code, prev || t);
    }
  }
  expect([...found].filter((k) => !KNOWN_CODE_CONFLICTS.has(k))).toEqual([]);
  // keep the allowlist honest: a fixed conflict must be removed from it
  expect([...KNOWN_CODE_CONFLICTS].filter((k) => !found.has(k))).toEqual([]);
});

test("names that state black or white have a colour to match", () => {
  const lum = ([r, g, b]) => 0.2126 * r + 0.7152 * g + 0.0722 * b;
  const bad = [];
  for (const t of rows) {
    if (/^(black|jet black)$/i.test(t.name) && !(lum(t.rgb) < 130)) bad.push(`${t.brand} ${t.code} ${t.rgb}`);
    if (/^(white|snow white|bright white)$/i.test(t.name) && !(lum(t.rgb) > 170)) bad.push(`${t.brand} ${t.code} ${t.rgb}`);
  }
  expect(bad).toEqual([]);
});
