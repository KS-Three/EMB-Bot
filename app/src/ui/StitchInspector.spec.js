// @vitest-environment jsdom
//
// The stitch inspector's tooltip, and the one promise it makes: a stitch
// reads the same number here as on the simulator's counter. The agreement
// test renders BOTH components from one design and compares their text, on
// three fixtures: a tagged synthetic design (three threads, trims, jumps,
// run spans), a real service result (lib/fixtures/digitized-asym.json) and
// the card v8 sew-out DST (docs/sewout/card-v8-2026-11-01).
import { describe, expect, test, beforeAll } from "vitest";
import { render } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import StitchInspector from "./StitchInspector.svelte";
import SimBar from "./SimBar.svelte";
import { buildStitchIndex, nearestStrand, strandInfo } from "../lib/stitchInspect.js";
import { strandStitchOrdinals, designToStrands } from "../lib/strands.js";
import { simTimeline } from "../lib/simulate.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..", "..", "..");
const S = (x, y, type = "stitch") => ({ x, y, type });

const tagged = {
  colors: [{ r: 200, g: 0, b: 0, name: "Red" }, { r: 0, g: 0, b: 200, name: "Blue" }, { r: 0, g: 150, b: 0, name: "Green" }],
  stitches: [
    S(0, 0), S(2, 0), S(4, 0), S(4, 0, "trim"),
    S(10, 0, "jump"), S(10, 0), S(10, 4), S(11, 0), S(11, 0, "trim"), S(11, 0, "color"),
    S(20, 20, "jump"), S(20, 20), S(23, 20), S(26, 20), S(26, 20, "color"),
    S(0, 30), S(1, 30), S(2, 30), S(2, 30, "end"),
  ],
  runs: [
    { i0: 0, i1: 2, kind: "underlay", shape: "a", role: "" },
    { i0: 5, i1: 7, kind: "satin", shape: "a", role: "" },
    { i0: 11, i1: 13, kind: "fill", shape: "b", role: "" },
    { i0: 15, i1: 17, kind: "bean", shape: "b", role: "border" },
  ],
};

let fixtures;
beforeAll(() => {
  const asym = JSON.parse(readFileSync(join(HERE, "..", "lib", "fixtures", "digitized-asym.json"), "utf8")).design;
  // The engine's own DST decoder (0.1 mm ints), loaded the way emb.spec.js
  // loads it; the file carries no colours, so two are supplied for its one
  // colour change.
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units", "dst", "dstimport"]) require(join(ROOT, "src", f + ".js"));
  const dst = globalThis.EMB.decodeDST(new Uint8Array(readFileSync(join(ROOT, "docs", "sewout", "card-v8-2026-11-01", "card_v8_40wt.dst"))));
  const card = {
    colors: [{ r: 20, g: 20, b: 20, name: "Black" }, { r: 240, g: 240, b: 240, name: "White" }],
    stitches: dst.stitches.map((s) => ({ x: s.x / 10, y: s.y / 10, type: s.type })),
  };
  fixtures = { tagged, asym, card };
});

// The counter and thread readout SimBar shows with `idx` strands drawn.
function simbarAt(design, idx) {
  const tl = simTimeline(design);
  const { container, unmount } = render(SimBar, {
    props: { index: idx, total: tl.total, ordinals: strandStitchOrdinals(design), timeline: tl, names: [] },
  });
  const out = {
    count: container.querySelector(".simcount").textContent.trim(),
    thread: container.querySelector(".simthread-k").textContent.trim(),
  };
  unmount();
  return out;
}

function inspectorAt(ix, j) {
  const { container, unmount } = render(StitchInspector, { props: { info: strandInfo(ix, j), x: 10, y: 10 } });
  const el = container.querySelector("[data-testid=stitch-inspect]");
  const text = el.textContent.replace(/\s+/g, " ").trim();
  unmount();
  return text;
}

describe("agreement with the simulator's counter", () => {
  for (const name of ["tagged", "asym", "card"]) {
    test(`${name}: the stitch under the pointer reads as the counter does once it is drawn`, () => {
      const d = fixtures[name];
      const ix = buildStitchIndex(d);
      const strands = designToStrands(d);
      const n = strands.length;
      expect(n).toBeGreaterThan(5);
      // First, last, every thread change's first strand, and a spread between.
      const tl = simTimeline(d);
      const picks = new Set([0, n - 1, Math.floor(n / 3), Math.floor(n / 2), Math.floor((2 * n) / 3)]);
      for (const b of tl.blocks) if (b.end > b.start) { picks.add(b.start); picks.add(b.end - 1); }
      let checked = 0;
      for (const j0 of picks) {
        // Hover the strand's midpoint and take whatever the lookup returns
        // (a later strand over it wins), so the path is pointer -> number.
        const s = strands[j0];
        const j = nearestStrand(ix, (s.x0 + s.x1) / 2, (s.y0 + s.y1) / 2);
        expect(j).toBeGreaterThanOrEqual(0);
        const tip = inspectorAt(ix, j);
        const bar = simbarAt(d, j + 1);
        const [, num, tot] = bar.count.match(/^([\d,]+) \/ ([\d,]+) stitches$/);
        expect(tip, `${name} strand ${j}`).toContain(`Stitch ${num} of ${tot}`);
        expect(tip, `${name} strand ${j}`).toContain(bar.thread);
        checked++;
      }
      expect(checked).toBeGreaterThanOrEqual(5);
    });
  }
});

describe("the tooltip", () => {
  test("renders nothing without a stitch", () => {
    const { container } = render(StitchInspector, { props: { info: null } });
    expect(container.querySelector("[data-testid=stitch-inspect]")).toBeNull();
  });

  test("says the number, type, length, thread and swatch, and is not a canvas", () => {
    const ix = buildStitchIndex(tagged);
    const info = strandInfo(ix, 2, ["1 Red", "2 Blue", "3 Green"]);
    const { container } = render(StitchInspector, { props: { info, x: 100, y: 80 } });
    const el = container.querySelector("[data-testid=stitch-inspect]");
    expect(el).toHaveAttribute("role", "tooltip");
    expect(el).toHaveAttribute("data-strand", "2");
    expect(el.textContent).toContain("Stitch 5 of 12");
    expect(el.textContent).toContain("Satin · 4.0 mm");
    expect(el.textContent).toContain("Thread 1 of 3");
    expect(el.textContent).toContain("1 Red");
    expect(el.querySelector(".si-swatch").getAttribute("style").replace(/\s/g, "")).toContain("rgb(200,0,0)");
    expect(container.querySelector("canvas")).toBeNull();
    // At the pointer, offset, unflipped away from the window's edges.
    expect(el.getAttribute("style")).toContain("left: 114px");
    expect(el.getAttribute("style")).toContain("top: 94px");
    expect(el.getAttribute("style")).toContain("translate(0, 0)");
  });

  test("flips to the pointer's other side near the window's right and bottom edges", () => {
    const ix = buildStitchIndex(tagged);
    const { container } = render(StitchInspector, {
      props: { info: strandInfo(ix, 0), x: window.innerWidth - 10, y: window.innerHeight - 10 },
    });
    const style = container.querySelector("[data-testid=stitch-inspect]").getAttribute("style");
    expect(style).toContain("translate(-100%, -100%)");
  });
});
