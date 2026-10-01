const assert = require("node:assert");
const fs = require("node:fs");
const { test } = require("node:test");
const sewtime = require("../src/sewtime.js");

// How long the machine is busy, for the worksheet and the review screen.
//
// The number this produces is a PLANNING figure, not a measurement, and the
// tests below are written to keep it honest in the two ways it could quietly
// stop being one: by dropping the trim term (the whole reason a 12-stop logo
// is not just its stitch count divided by a speed), and by drifting from the
// Python constants it is hand-ported from.

test("run time is stitches over the plan rate when nothing is cut", () => {
  // 6,500 stitches at 650 spm is exactly ten minutes of needle time.
  assert.strictEqual(sewtime.sewTimeMin(6500, 0), 10);
});

test("every trim costs its stitch-equivalents", () => {
  // 10 trims at 120 stitch-equivalents each is 1,200 on top of 6,500,
  // i.e. 7,700 / 650 = 11.84... minutes, reported to the minute.
  assert.strictEqual(sewtime.sewTimeMin(6500, 10), 12);
});

test("the trim term is load-bearing, not decoration", () => {
  // If this ever reads equal, the "(incl. trims)" the sheet prints beside the
  // figure has become a lie and the estimate under-quotes every stop-heavy
  // design — which is exactly the class of job the operator most wants warned
  // about (machine-physics playbook law 36: trims and stops are unbilled
  // margin loss).
  assert.notStrictEqual(sewtime.sewTimeMin(6500, 10), sewtime.sewTimeMin(6500, 0));
});

test("a design with no stitches takes no time", () => {
  assert.strictEqual(sewtime.sewTimeMin(0, 0), 0);
});

test("it never reports zero minutes for work that exists", () => {
  // A 200-stitch monogram is 18 seconds of needle time. Rounding that to "0
  // min" on a worksheet reads as "nothing to do" rather than "under a
  // minute", so the floor is one minute once there is any work at all.
  assert.strictEqual(sewtime.sewTimeMin(200, 0), 1);
});

test("bad inputs produce null, never a plausible wrong number", () => {
  // Same posture as `estimate.js`'s thread metres: a missing input drops the
  // row rather than quoting a figure derived from a default.
  assert.strictEqual(sewtime.sewTimeMin(null, 0), null);
  assert.strictEqual(sewtime.sewTimeMin(6500, null), null);
  assert.strictEqual(sewtime.sewTimeMin(-1, 0), null);
  assert.strictEqual(sewtime.sewTimeMin(6500, -2), null);
});

test("the constants are the ones the sheet claims", () => {
  // The sheet prints "at 650 spm (incl. trims)". If either constant moves,
  // that sentence has to move with it.
  assert.strictEqual(sewtime.PLAN_SPM, 650);
  assert.strictEqual(sewtime.TRIM_COST_STITCHES, 120);
});

// Read a constant straight out of the Python engine's machine.py — the same
// helper test/digitize.test.js uses for THREAD_LENGTH_FACTOR.
function machinePy(name) {
  const src = fs.readFileSync(__dirname + "/../digitizer/digitizer_core/machine.py", "utf8");
  const m = src.match(new RegExp("^" + name + "\\s*=\\s*([0-9.]+)", "m"));
  assert.ok(m, name + " not found in digitizer/digitizer_core/machine.py");
  return +m[1];
}

test("engine parity: the two time constants equal machine.py's", () => {
  // Both files have called each other "twin" since 2026-09-20 and nothing
  // held them together: the test above pins the JS side to literals, and no
  // test read the Python side at all (found 2026-10-01).
  assert.strictEqual(sewtime.PLAN_SPM, machinePy("PLAN_SPM"));
  assert.strictEqual(sewtime.TRIM_COST_STITCHES, machinePy("TRIM_COST_STITCHES"));
});

// --- the operator's own speed (2026-10-01) ----------------------------------

test("a typed running speed moves the needle time and leaves the stops alone", () => {
  // 13,000 stitches: 20 min at 650, 10 min at 1,300.
  assert.strictEqual(sewtime.sewTimeMin(13000, 0, 1300), 10);
  // A trim is a fixed stretch of clock (trimmer, reposition): ~11 s, which is
  // what 120 stitch-equivalents means AT the plan rate. Run the head twice as
  // fast and the trimmer is no quicker. 60 stops x 120 / 650 = 11.08 min on
  // top of the 10, not 5.54.
  assert.strictEqual(sewtime.sewTimeMin(13000, 60, 1300), 21);
});

test("at the plan rate the speed argument changes nothing", () => {
  assert.strictEqual(sewtime.sewTimeMin(6500, 10, 650), sewtime.sewTimeMin(6500, 10));
});

test("a speed that is not a positive number is no basis for a figure", () => {
  assert.strictEqual(sewtime.sewTimeMin(6500, 0, 0), null);
  assert.strictEqual(sewtime.sewTimeMin(6500, 0, -850), null);
  assert.strictEqual(sewtime.sewTimeMin(6500, 0, NaN), null);
  assert.strictEqual(sewtime.sewTimeMin(6500, 0, "850"), null);
});

// --- bobbin thread ------------------------------------------------------------

test("bobbin metres are a share of the top thread, never more than it", () => {
  // Madeira's pair: ~3 m of underthread to ~5 m of top, per 1,000 stitches.
  assert.strictEqual(sewtime.BOBBIN_SHARE_OF_TOP, 3 / 5);
  assert.ok(Math.abs(sewtime.bobbinM(2.5) - 1.5) < 1e-9);
  assert.strictEqual(sewtime.bobbinM(0), 0);
  // The property the per-1,000-stitches rule broke on short satin stitches.
  for (const m of [0.1, 2.5, 40, 900]) assert.ok(sewtime.bobbinM(m) < m);
});

test("bobbin metres are null on a count that cannot support a figure", () => {
  assert.strictEqual(sewtime.bobbinM(null), null);
  assert.strictEqual(sewtime.bobbinM(-5), null);
  assert.strictEqual(sewtime.bobbinM(NaN), null);
});
