const assert = require("node:assert");
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
