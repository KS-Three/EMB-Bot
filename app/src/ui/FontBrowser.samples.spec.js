// @vitest-environment jsdom
//
// The stitched-sample queue fetches a font binary ONLY for tiles in the
// window. A tile that a search or group filter removes must leave the queue
// with it: IntersectionObserver.unobserve() fires no callback, so without an
// explicit unwant() in the action's destroy(), every filtered-out tile that
// was still waiting got fetched and decoded ahead of the tiles the customer
// was now looking at (post-merge review of #1348, 2026-11-07).
import { beforeAll, expect, test, vi } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import { createRequire } from "node:module";

const SANS = ["s0", "s1", "s2", "s3", "s4", "s5"];
const SCRIPT = ["c0", "c1"];

// Every ensureFont() call, in order. The first two (the queue's concurrency)
// hang until the spec releases them, so the rest of the window is still
// queued when the filter changes; later loads settle at once.
const calls = [];
const held = [];
vi.mock("../lib/fontLoader.js", () => ({
  loadCoverage: () => Promise.resolve(null),
  loadManifest: () => Promise.resolve({
    fonts: [
      ...SANS.map((k) => ({ key: k, name: "Sans " + k, group: "Sans" })),
      ...SCRIPT.map((k) => ({ key: k, name: "Script " + k, group: "Script" })),
    ],
  }),
  loadFontStyles: () => Promise.resolve(null),
  loadOutlineRows: () => Promise.resolve({ rows: [], coverage: {} }),
  ensureFont: (key) => {
    calls.push(key);
    if (calls.length <= 2) return new Promise((resolve) => held.push(() => resolve(null)));
    return Promise.resolve(null);
  },
}));

// jsdom has no IntersectionObserver. This one does what the real one does
// for the case under test: observe() adds a target, unobserve() removes it
// SILENTLY (no callback), and the spec decides when targets intersect.
let io = null;
class FakeIO {
  constructor(cb) { this.cb = cb; this.targets = new Set(); io = this; }
  observe(el) { this.targets.add(el); }
  unobserve(el) { this.targets.delete(el); }
  disconnect() { this.targets.clear(); }
  fire(els) { this.cb(els.map((target) => ({ target, isIntersecting: true }))); }
}

let FontBrowser;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  require("../../../src/units.js");
  globalThis.EMB.buildLetteringDesign =
    globalThis.EMB.buildLetteringDesign || (() => { throw new Error("not used by this spec"); });
  globalThis.EMB.SATIN_FONTS = globalThis.EMB.SATIN_FONTS || {};
  globalThis.fetch = () => Promise.reject(new Error("no network in tests"));
  globalThis.IntersectionObserver = FakeIO;
  ({ default: FontBrowser } = await import("./FontBrowser.svelte"));
});

const tick = () => new Promise((r) => setTimeout(r, 0));
const tileOf = (container, key) => container.querySelector('.fb-tile[data-key="' + key + '"]');

test("a tile a group filter removes is taken off the sample queue", async () => {
  const { container } = render(FontBrowser, { props: { selected: null, currentText: "" } });
  await tick();
  expect(io, "the browser should start an observer on its body").toBeTruthy();

  // The window: every Sans tile. Two start loading, four wait in the queue.
  io.fire(SANS.map((k) => tileOf(container, k)));
  await tick();
  expect(calls).toEqual(["s0", "s1"]);

  // The customer clicks Script before those load. The Sans tiles leave the
  // grid; the Script tiles are what is now in view.
  const chip = [...container.querySelectorAll(".fb-chip")].find((b) => b.textContent.trim() === "Script");
  await fireEvent.click(chip);
  await tick();
  expect(tileOf(container, "s2"), "the Sans tiles should be gone").toBeNull();
  io.fire(SCRIPT.map((k) => tileOf(container, k)));
  await tick();

  // The two in-flight loads finish; the queue drains.
  for (const release of held.splice(0)) release();
  for (let i = 0; i < 10; i++) await tick();

  const after = calls.slice(2);
  expect(after.filter((k) => SANS.includes(k)),
    "no binary may be fetched for a tile that is no longer on screen").toEqual([]);
  expect(after.sort()).toEqual([...SCRIPT].sort());
});
