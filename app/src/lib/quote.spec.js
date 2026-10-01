// @vitest-environment jsdom
import { test, expect, beforeEach } from "vitest";
import {
  MACHINE_PROFILES, QUOTE_KEY, profileById, cleanQuote, loadQuote, saveQuote,
  money, threadCost, machineCost,
} from "./quote.js";

beforeEach(() => {
  localStorage.clear();
});

test("every profile figure is a number or an honest null, and names where it was read", () => {
  const ids = new Set();
  for (const p of MACHINE_PROFILES) {
    expect(ids.has(p.id), `duplicate id ${p.id}`).toBe(false);
    ids.add(p.id);
    expect(p.label.length).toBeGreaterThan(0);
    expect(p.source).toMatch(/^https:\/\//);
    for (const k of ["needles", "maxSpm", "maxSpmCaps", "maxStitchMm"]) {
      expect(p[k] === null || (typeof p[k] === "number" && p[k] > 0), `${p.id}.${k}`).toBe(true);
    }
  }
  const s = profileById("smartstitch_s1501");
  expect(s.needles).toBe(15);
  expect(s.maxSpm).toBe(1200);
  // Nobody publishes it, so it is not stated.
  expect(s.maxStitchMm).toBeNull();
});

test("nothing entered is nothing stored, and reads back as all-null", () => {
  expect(loadQuote()).toEqual({ profileId: null, spm: null, conePrice: null, coneM: null, hourRate: null });
  saveQuote({});
  expect(localStorage.getItem(QUOTE_KEY)).toBeNull();
});

test("form strings round-trip as numbers", () => {
  saveQuote({ profileId: "smartstitch_s1501", spm: "850", conePrice: "7.5", coneM: "5000", hourRate: "40" });
  expect(loadQuote()).toEqual({ profileId: "smartstitch_s1501", spm: 850, conePrice: 7.5, coneM: 5000, hourRate: 40 });
});

test("junk is null, never a number", () => {
  const q = cleanQuote({ profileId: "no_such", spm: "fast", conePrice: -3, coneM: 0, hourRate: "" });
  expect(q).toEqual({ profileId: null, spm: null, conePrice: null, coneM: null, hourRate: null });
  localStorage.setItem(QUOTE_KEY, "{not json");
  expect(loadQuote().spm).toBeNull();
});

test("a typed speed cannot exceed the chosen machine's nameplate", () => {
  expect(cleanQuote({ profileId: "smartstitch_s1501", spm: 2000 }).spm).toBe(1200);
  // With no profile there is no ceiling to apply.
  expect(cleanQuote({ spm: 2000 }).spm).toBe(2000);
});

test("thread cost is the share of a cone, and needs BOTH cone inputs", () => {
  expect(threadCost(50, { conePrice: 10, coneM: 5000 })).toBeCloseTo(0.1, 9);
  expect(threadCost(50, { conePrice: 10, coneM: null })).toBeNull();
  expect(threadCost(50, { conePrice: null, coneM: 5000 })).toBeNull();
  expect(threadCost(null, { conePrice: 10, coneM: 5000 })).toBeNull();
  expect(threadCost(50, null)).toBeNull();
});

test("machine cost is minutes at the hourly rate, or nothing", () => {
  expect(machineCost(12, { hourRate: 40 })).toBeCloseTo(8, 9);
  expect(machineCost(12, { hourRate: null })).toBeNull();
  expect(machineCost(null, { hourRate: 40 })).toBeNull();
});

test("money never rounds a real cost to free", () => {
  expect(money(8)).toBe("$8.00");
  expect(money(0.105)).toBe("$0.10");
  expect(money(0.004)).toBe("under $0.01");
  expect(money(0)).toBe("$0.00");
  expect(money(NaN)).toBeNull();
});
