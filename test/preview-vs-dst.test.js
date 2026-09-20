// Pins: the Studio's PREVIEW and the file a customer downloads draw the same
// thread. See tools/preview-vs-dst.mjs for what is measured and why the
// crossval harness next door cannot answer this — it compares coordinates,
// and the defect this file exists for left every coordinate, count and extent
// correct while moving the path between them.
//
// Needs a Python interpreter with pystitch, exactly like
// test/crossval-stitch-formats.test.js: skips on a developer box without one,
// FAILS on CI, where the install step provides it. Same reasoning as that
// file's — a skip nobody notices is not a safe default for a check that is
// the only thing comparing a picture to a file.
const assert = require("node:assert");
const { test } = require("node:test");

let harness = null;
let run = null;
let loadError = null;

async function ensureRun() {
  if (!harness) harness = await import("../tools/preview-vs-dst.mjs");
  if (run || loadError) return;
  const crossval = await import("../tools/crossval-stitch-formats.mjs");
  const python = crossval.resolvePython();
  if (!python) {
    if (process.env.CI) {
      throw new Error(
        "no python with pystitch available, and CI is set. This check must run " +
          "for real in CI -- see .github/workflows for the install step that " +
          "provides it. Do not 'fix' this by allowing the skip."
      );
    }
    loadError = "no python with pystitch available";
    return;
  }
  run = harness.runPreviewVsDst({ python });
}

function skipOrGet(t, key) {
  if (loadError) { t.skip(loadError); return null; }
  const r = run.results[key];
  assert.ok(r && !r.error, key + " decoded without error: " + JSON.stringify(r));
  return r;
}

const FORMATS = ["dst", "exp", "pes"];
const FIXTURES = ["dogleg", "lettering", "resized"];

for (const fixture of FIXTURES) {
  for (const fmt of FORMATS) {
    test(`${fmt}.${fixture}: the file's thread follows the line the preview draws`, async (t) => {
      await ensureRun();
      const r = skipOrGet(t, `${fmt}.${fixture}`);
      if (!r) return;

      // Orientation first: this is the axis question docs/dst-axis-verdict
      // settled on 2026-09-08, asserted here so a picture-level check would
      // catch a codec that ever transposes again.
      assert.strictEqual(r.orientation, "identity", `${fmt}.${fixture} reads as ${r.orientation}`);
      assert.strictEqual(r.orientationFit.identity, 1,
        "every sewn segment in the file lies on a segment the preview drew");

      // Half a unit is 0.05 mm: cumulative rounding in the split is the only
      // thing allowed to move a point off the drawn line. The dogleg put it
      // 14.87 mm off on this same fixture (measured 2026-09-20 against the
      // pre-fix encoders, the run that justified this file existing).
      assert.ok(r.strayMm.fileToPreview <= 0.06,
        `file thread strays ${r.strayMm.fileToPreview} mm from the drawn line`);
      assert.ok(r.strayMm.previewToFile <= 0.06,
        `drawn line strays ${r.strayMm.previewToFile} mm from the file's thread`);

      // A split only ever adds records; it must never drop or demote one.
      assert.ok(r.fileSegments >= r.previewSegments,
        "a split adds sewn segments, it does not remove them");
      // Thread length is the tell for a stitch quietly turned into travel (or
      // the reverse), which no bounding box or stitch count would show.
      assert.ok(Math.abs(r.threadMm.delta) / Math.max(1, r.threadMm.preview) < 0.001,
        `sewn thread differs by ${r.threadMm.delta} mm (${r.threadMm.preview} drawn, ${r.threadMm.file} in the file)`);
    });
  }
}

// The fixtures have to REACH the split, or every assertion above passes
// vacuously. That is not hypothetical: the crossval harness's own long-stitch
// fixture is axis-aligned, which is precisely why it held the dogleg for as
// long as it did — an axis-aligned split is straight however you clamp it.
test("the fixtures actually exercise the split path", async (t) => {
  await ensureRun();
  const dogleg = skipOrGet(t, "dst.dogleg");
  if (!dogleg) return;
  assert.ok(dogleg.previewSegmentsOverOneRecord >= 3,
    "the dogleg fixture must hold several diagonal segments past one record");
  assert.ok(dogleg.fileSegments > dogleg.previewSegments,
    "and the encoder must actually be splitting them");

  const resized = skipOrGet(t, "dst.resized");
  if (!resized) return;
  assert.ok(resized.previewSegmentsOverOneRecord >= 1,
    "the resized-import fixture is the customer path to the split; it must still reach it");
});
