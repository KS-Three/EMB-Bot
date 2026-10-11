// Colour-change economy for the JS engine: a colour change is a machine stop,
// so the engine must not add one where the thread does not change.
//   1. same-colour regions that are ADJACENT in sew order share one thread
//   2. the colour count equals the distinct colours actually sewn
// The passing tests pin what holds today; the `todo` ones are real gaps found
// while writing this file (listed in the PR body).
const assert = require("node:assert");
const { test } = require("node:test");
const DG = require("../src/digitize.js");

const sq = (x0, y0, s) => [{ x: x0, y: y0 }, { x: x0 + s, y: y0 }, { x: x0 + s, y: y0 + s }, { x: x0, y: y0 + s }];
const region = (rgb, x0) => ({ rgb, shapes: [{ outer: sq(x0, 0, 60), holes: [] }] });
const BASE = { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 4, densityMm: 0.5, underlay: false, satinMaxWidthMm: 0.05 };
const A = [50, 50, 50], B = [200, 10, 10], C = [10, 10, 200], D = [240, 240, 240];

const nChanges = (d) => d.stitches.filter((s) => s.type === "color").length;
const key = (c) => `${c.r},${c.g},${c.b}`;
const distinct = (d) => new Set(d.colors.map(key)).size;

// Invariants every design must satisfy regardless of options.
function checkStructure(d, label) {
  assert.strictEqual(nChanges(d), Math.max(0, d.colorCount - 1), `${label}: one colour record between each pair of threads`);
  assert.strictEqual(d.colorCount, d.colors.length, `${label}: colorCount matches colors[]`);
  const types = d.stitches.map((s) => s.type);
  for (let i = 1; i < types.length; i++) {
    assert.ok(!(types[i] === "color" && types[i - 1] === "color"), `${label}: two colour records back to back at ${i}`);
  }
}

test("colour order: a design with no repeated colour has one change per extra colour", () => {
  const d = DG.buildQualityDesign([region(A, 0), region(B, 200), region(C, 400)], BASE);
  checkStructure(d, "ABC");
  assert.strictEqual(d.colorCount, 3);
  assert.strictEqual(distinct(d), 3);
  assert.strictEqual(nChanges(d), 2);
});

test("colour order: minimizeColorChanges folds adjacent AND revisited same-colour regions", () => {
  const on = Object.assign({ minimizeColorChanges: true }, BASE);
  const aab = DG.buildQualityDesign([region(A, 0), region(A, 200), region(B, 400)], on);
  checkStructure(aab, "AAB min");
  assert.strictEqual(aab.colorCount, 2);
  assert.strictEqual(distinct(aab), 2, "colour count equals distinct colours used");
  const aba = DG.buildQualityDesign([region(A, 0), region(B, 200), region(A, 400)], on);
  checkStructure(aba, "ABA min");
  assert.strictEqual(aba.colorCount, distinct(aba));
  assert.strictEqual(aba.colorCount, 2);
});

test("colour order: with minimizeColorChanges no two neighbouring threads are the same colour", () => {
  const regs = [region(A, 0), region(B, 100), region(A, 200), region(D, 300), region(D, 400), region(A, 500), region(B, 600)];
  const d = DG.buildQualityDesign(regs, Object.assign({ minimizeColorChanges: true }, BASE));
  checkStructure(d, "mixed min");
  for (let i = 1; i < d.colors.length; i++) {
    assert.notStrictEqual(key(d.colors[i]), key(d.colors[i - 1]), `threads ${i - 1} and ${i} are the same colour`);
  }
  assert.strictEqual(d.colorCount, distinct(d), "every thread is a distinct colour");
  assert.strictEqual(d.colorCount, 3);
});

test("colour order: the default path never adds a change between different-colour neighbours beyond the pair", () => {
  const d = DG.buildQualityDesign([region(A, 0), region(B, 200), region(A, 400)], BASE);
  checkStructure(d, "ABA default");
  assert.strictEqual(d.colorCount, 3, "default sews the revisit as its own thread (documented: minimize is opt-in)");
});

test("colour order: lettering with no colorRanges is one thread, no change", () => {
  const d = DG.buildQualityDesign([region(A, 0)], BASE);
  checkStructure(d, "single");
  assert.strictEqual(d.colorCount, 1);
  assert.strictEqual(nChanges(d), 0);
});

// ---- Real gaps (todo: reported, not failing the suite) ----

test("colour order: adjacent same-colour regions share one thread by default", { todo: "engine default emits a needless colour change between adjacent same-rgb regions; minimizeColorChanges is opt-in and no caller (app/src, src/) sets it" }, () => {
  const d = DG.buildQualityDesign([region(A, 0), region(A, 200), region(B, 400)], BASE);
  assert.strictEqual(d.colorCount, 2);
  assert.strictEqual(nChanges(d), 1);
});

test("colour order: default colour count equals distinct colours used", { todo: "default path: A,B,A sews three threads for two colours" }, () => {
  const d = DG.buildQualityDesign([region(A, 0), region(B, 200), region(A, 400)], BASE);
  assert.strictEqual(d.colorCount, distinct(d));
});

test("colour order: minimizeColorChanges groups same-colour regions even when different colours tie on brightness", { todo: "B (200,10,10) and C (10,10,200) tie on brightness, the sort interleaves them, B,C,B,C sews 4 threads for 2 colours (the sort needs an rgb tiebreak)" }, () => {
  const d = DG.buildQualityDesign([region(B, 0), region(C, 100), region(B, 200), region(C, 300)], Object.assign({ minimizeColorChanges: true }, BASE));
  assert.strictEqual(d.colorCount, distinct(d));
});
