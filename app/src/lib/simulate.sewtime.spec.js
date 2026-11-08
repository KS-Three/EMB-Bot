// The simulator bar's sew-time estimate (lib/simulate.js sewClock /
// sewTimeAt / sewTimeText): positions here, minutes from the engine's own
// sewTimeMin at PLAN_SPM (src/sewtime.js), so the bar's total is the Review
// "Run time" figure in Download.
import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
import { sewClock, sewTimeAt, sewTimeText, simTimeline } from "./simulate.js";

let sewTimeMin, PLAN_SPM, sewFacts;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  // estimate.js imports emb.js, which needs the engine global loaded.
  for (const f of ["units", "sewtime", "garments", "fabrics", "fill", "geometry", "satin",
                   "satinplay", "satinfont", "fontbin", "dst", "fonts", "digitize"])
    require("../../../src/" + f + ".js");
  ({ sewTimeMin, PLAN_SPM } = require("../../../src/sewtime.js"));
  ({ sewFacts } = await import("./estimate.js"));
});

const S = (x, y, type = "stitch") => ({ x, y, type });

// Two threads: a run of 4 stitches (3 strands), a trim, a run of 3 (2
// strands), then trim + colour (ONE stop: the thread was already cut), a run
// of 2 (1 strand), and a colour change with no trim (a stop of its own) into
// a lone stitch, which paints no strand.
//   strands:      0 1 2 | 3 4 | 5 |
//   chain starts: at 0, 3, 5, 6
//   stops:        at 3 (trim), 5 (trim; the colour after it is not one), 6 (colour)
const D = {
  colors: [{ r: 0, g: 0, b: 0 }, { r: 200, g: 0, b: 0 }, { r: 0, g: 0, b: 200 }],
  stitches: [
    S(0, 0), S(10, 0), S(20, 0), S(30, 0),
    S(30, 0, "trim"),
    S(50, 0, "jump"), S(50, 0), S(60, 0), S(70, 0),
    S(70, 0, "trim"), S(70, 0, "color"),
    S(0, 50), S(10, 50),
    S(10, 50, "color"),
    S(90, 90),
    S(0, 0, "end"),
  ],
};

test("the clock's totals are sewFacts's, and its strands are simTimeline's", () => {
  for (const d of [D, { stitches: [] }, { stitches: [S(0, 0, "color"), S(0, 0), S(5, 5)] }]) {
    const c = sewClock(d);
    const f = sewFacts(d);
    expect(c.stitches).toBe(f.stitches);
    expect(c.stops).toBe(f.stops);
    expect(c.total).toBe(simTimeline(d).total);
  }
  const c = sewClock(D);
  expect(c.total).toBe(6);
  expect(c.stitches).toBe(10);
  expect(c.chainStarts.map((e) => e.at)).toEqual([0, 3, 5, 6]);
  expect(c.stopAt.map((e) => e.at)).toEqual([3, 5, 6]);
});

test("the total is exactly sewTimeMin(stitches, stops, PLAN_SPM): the Run time row's figure", () => {
  expect(PLAN_SPM).toBe(650);
  // 6,500 stitches and 10 stops: 10 min of needle + 10 x 120 / 650 = 1.85 min.
  const big = { stitches: [] };
  for (let r = 0; r < 10; r++) {
    for (let i = 0; i < 650; i++) big.stitches.push(S(i, r));
    big.stitches.push(S(0, r, "trim"));
  }
  const c = sewClock(big);
  expect(c.stitches).toBe(6500);
  expect(c.stops).toBe(10);
  const t = sewTimeAt(c, 0, sewTimeMin, PLAN_SPM);
  expect(t).toEqual({ left: 12, total: sewTimeMin(6500, 10, PLAN_SPM) });
  expect(t.total).toBe(12); // 11.85 rounded
  // Half the runs sewn (each run is 649 strands), landed ON the fifth trim,
  // which is still ahead: 3,250 stitches and 6 stops left = 5 + 1.11 -> 6.
  const half = 5 * 649;
  expect(sewTimeAt(c, half, sewTimeMin, PLAN_SPM)).toEqual({ left: 6, total: 12 });
  expect(sewTimeAt(c, half, sewTimeMin, PLAN_SPM).left).toBe(sewTimeMin(3250, 6, PLAN_SPM));
});

test("stitches and stops left, at each position, are what sewTimeMin is charged", () => {
  const c = sewClock(D);
  const seen = [];
  const spy = (st, sp) => { seen.push([st, sp]); return sewTimeMin(st, sp); };
  for (let idx = 0; idx <= c.total; idx++) sewTimeAt(c, idx, spy, PLAN_SPM);
  // [total call, left call] per position; the last position has no left call.
  const left = [];
  for (let i = 0; i < seen.length; i++) if (i % 2 === 1) left.push(seen[i]);
  expect(left).toEqual([
    [10, 3], // idx 0: nothing sewn
    [8, 3],  // idx 1: strand 0 drawn = its two stitches
    [7, 3],
    [6, 3],  // idx 3: landed on the trim; it and the next chain's start are ahead
    [4, 2],  // idx 4: the trim done, the second chain's start and strand 3
    [3, 2],  // idx 5: landed on the trim + colour, still ahead
  ]);
  expect(sewTimeAt(c, c.total, sewTimeMin, PLAN_SPM)).toEqual({ left: 0, total: 1 });
});

test("the estimate never grows as the needle moves, and is total at the start", () => {
  const big = { stitches: [] };
  for (let r = 0; r < 40; r++) {
    for (let i = 0; i < 300; i++) big.stitches.push(S(i, r));
    big.stitches.push(S(0, r, r % 3 ? "trim" : "color"));
  }
  const c = sewClock(big);
  let last = Infinity;
  for (let idx = 0; idx <= c.total; idx += 37) {
    const t = sewTimeAt(c, idx, sewTimeMin, PLAN_SPM);
    expect(t.left).toBeLessThanOrEqual(last);
    expect(t.left).toBeLessThanOrEqual(t.total);
    if (idx === 0) expect(t.left).toBe(t.total);
    last = t.left;
  }
});

test("no figure without the function or with a bad rate; the words say it is an estimate", () => {
  const c = sewClock(D);
  expect(sewTimeAt(c, 0, undefined, PLAN_SPM)).toBeNull();
  expect(sewTimeAt(null, 0, sewTimeMin, PLAN_SPM)).toBeNull();
  expect(sewTimeAt(c, 0, sewTimeMin, 0)).toBeNull();
  expect(sewTimeText(null)).toBe("");
  expect(sewTimeText({ left: 12, total: 18 })).toBe("about 12 min left of 18");
  expect(sewTimeText({ left: 0, total: 18 })).toBe("about 18 min in all");
});
