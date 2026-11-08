// One rate for every sew-time figure (#1334's Decision 1, Kent's pick (b),
// 2026-11-07): estimate.js `runSpm(quote)` is the operator's Quote speed when
// one is set, else the engine's PLAN_SPM. Download's "Run time" row
// (`sewSummary`) and the simulator bar (`sewTimeAt` at runSpm's rate) both
// read it, so the bar's total is the row's minutes with or without a quote.
import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
import { sewClock, sewTimeAt } from "./simulate.js";

let EMB, runSpm, sewSummary, cleanQuote;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units", "sewtime", "garments", "fabrics", "fill", "geometry", "satin",
                   "satinplay", "satinfont", "fontbin", "dst", "fonts", "digitize"])
    require("../../../src/" + f + ".js");
  ({ EMB } = await import("./emb.js"));
  ({ runSpm, sewSummary } = await import("./estimate.js"));
  ({ cleanQuote } = await import("./quote.js"));
});

// 13,000 sewn stitches in two colours, trim before the change (one stop).
function twoColour() {
  const stitches = [];
  for (let i = 0; i < 6500; i++) stitches.push({ x: i, y: 0, type: "stitch" });
  stitches.push({ x: 0, y: 0, type: "trim" });
  stitches.push({ x: 0, y: 0, type: "color" });
  for (let i = 0; i < 6500; i++) stitches.push({ x: i, y: 10, type: "stitch" });
  stitches.push({ x: 0, y: 0, type: "end" });
  return { widthMM: 100, heightMM: 50, stitches };
}

test("no quote speed: the engine's planning rate, marked as not quoted", () => {
  expect(EMB.PLAN_SPM).toBe(650);
  for (const q of [undefined, null, {}, cleanQuote({}), cleanQuote({ profileId: "smartstitch_s1501" }),
                   { spm: null }, { spm: 0 }, { spm: -5 }, { spm: NaN }, { spm: "900" }])
    expect(runSpm(q)).toEqual({ spm: EMB.PLAN_SPM, quoted: false });
});

test("a quote speed: that speed, marked as quoted", () => {
  expect(runSpm(cleanQuote({ spm: "1000" }))).toEqual({ spm: 1000, quoted: true });
  expect(runSpm({ spm: 650 })).toEqual({ spm: 650, quoted: true }); // typed 650 is still theirs
  // cleanQuote's nameplate ceiling is applied before runSpm sees it.
  expect(runSpm(cleanQuote({ profileId: "smartstitch_s1501", spm: 5000 }))).toEqual({ spm: 1200, quoted: true });
});

test("the bar's total is the Run time row's minutes, at the same rate, with and without a quote", () => {
  const d = twoColour();
  const clock = sewClock(d);
  for (const q of [null, cleanQuote({ spm: 1000 }), cleanQuote({ profileId: "smartstitch_s1501", spm: 1200 }), cleanQuote({ spm: 300 })]) {
    const { spm } = runSpm(q);
    const row = sewSummary(d, q).find((r) => r.label === "Run time").value;
    const m = row.match(/^~(\d+) min.* at ([\d,]+) spm$/);
    expect(m, row).not.toBeNull();
    expect(Number(m[2].replace(/,/g, ""))).toBe(spm);
    const bar = sewTimeAt(clock, 0, EMB.sewTimeMin, spm);
    expect(bar.total).toBe(Number(m[1]));
    expect(bar.left).toBe(bar.total);
  }
  // And the rate moves the figure: 1,000 spm is shorter than 650.
  const plan = sewTimeAt(clock, 0, EMB.sewTimeMin, runSpm(null).spm).total;
  const fast = sewTimeAt(clock, 0, EMB.sewTimeMin, runSpm({ spm: 1000 }).spm).total;
  expect(fast).toBeLessThan(plan);
});
