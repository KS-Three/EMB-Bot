import { test } from "node:test";
import assert from "node:assert/strict";
import { fileSeconds, median, medianSeconds, renderTable } from "../tools/e2e-spec-times.mjs";

// One test result: starts `at` s after a fixed t0 and lasts `dur` s.
const res = (at, dur) => ({ startTime: new Date(Date.UTC(2026, 10, 7, 0, 0, 0) + at * 1000).toISOString(), duration: dur * 1000 });
const spec = (file, ...results) => ({ file, tests: results.map((r) => ({ results: [r] })) });
const report = (...specs) => ({ suites: [{ file: "x", specs: [], suites: [{ specs }] }] });

test("median: odd, even, unsorted", () => {
  assert.equal(median([30, 10, 20]), 20);
  assert.equal(median([10, 20, 30, 50]), 25);
});

test("serial file = wall span incl. gaps; parallel file = summed durations", () => {
  const rep = report(spec("a.spec.js", res(0, 10), res(15, 5))); // span 20, sum 15
  assert.equal(fileSeconds(rep, true).get("a.spec.js"), 20);
  assert.equal(fileSeconds(rep, false).get("a.spec.js"), 15);
});

test("median over 3 runs is exact, across both steps", () => {
  const run = (serialSecs, parSecs) => [
    { serial: true, report: report(spec("slow.spec.js", res(0, serialSecs))) },
    { serial: false, report: report(spec("fast.spec.js", res(0, parSecs / 2), res(100, parSecs / 2))) },
  ];
  const m = medianSeconds([run(100, 10), run(300, 30), run(200, 20)]);
  assert.equal(m.get("slow.spec.js"), 200);
  assert.equal(m.get("fast.spec.js"), 20);
});

test("a file's reports within one run add; a file absent from a run is medianed over the rest", () => {
  const r1 = [{ serial: false, report: report(spec("a.spec.js", res(0, 4))) }, { serial: false, report: report(spec("a.spec.js", res(0, 6))) }];
  const r2 = [{ serial: false, report: report(spec("a.spec.js", res(0, 20))) }];
  assert.equal(medianSeconds([r1, r2]).get("a.spec.js"), 15);
});

test("renderTable: table shape, sorted, rounded, default flagged", () => {
  const t = renderTable(new Map([["b.spec.js", 12.4], ["a.spec.js", 7.5]]), ["a.spec.js", "b.spec.js", "c.spec.js"], 30);
  assert.deepEqual(t.defaults, ["c.spec.js"]);
  assert.equal(t.covered, 2);
  assert.equal(t.total, 3);
  assert.equal(
    t.text,
    'const SPEC_SECONDS = {\n  "a.spec.js": 8,\n  "b.spec.js": 12,\n  // "c.spec.js": DEFAULT (30 s) -- no run measured it\n};',
  );
});
