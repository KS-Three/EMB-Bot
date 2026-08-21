// Cross-validation pins: browser PES / EXP / DST encoders vs. pystitch.
//
// These tests PIN CURRENT BEHAVIOR — they are a tripwire, not an endorsement.
// As of 2026-08-05, the PES framing/palette/jump-flag defects and the EXP
// trim-truncation defect the 2026-08-04 verdict memo documented are FIXED
// (see docs/pes-crossval-verdict-2026-08-04.md section 5's recommended fix
// list, and MASTER_SCOPE.md's Export formats section for the harness re-run
// numbers). As of 2026-08-06, EXP's own share of the "end"-record
// extra-stitch quirk is FIXED too (encodeEXP now stops at the terminal
// {type:"end"} sentinel the same way pes.js's encoder already did). The DST
// control assertions still document real, deliberately NOT-fixed defects
// (fixing DST is Kent's call, out of scope here — see
// docs/dst-axis-verdict-2026-07-31.md, including DST's own copy of the same
// end-record quirk) and a PES assertion still pins one remaining,
// explicitly-accepted gap (nearest-chart palette snapping isn't lossless).
// If any assertion here starts failing, the encoder's third-party-visible
// behavior CHANGED — read the docs above before "fixing" anything.
//
// Needs a Python interpreter with pystitch (the digitizer venv, or
// $EMB_CROSSVAL_PYTHON). Skips locally when none is available -- but NEVER
// on CI, where a missing interpreter is a failure.
//
// That asymmetry is the whole point, and it is the same shape as the
// `requires_tesseract` marker in digitizer/tests/conftest.py. These checks
// probed pyembroidery until 2026-08-21; the 2026-08-11 pystitch swap had
// removed it from the venv, so all six skipped and the file reported
// pass 0 / skipped 6 -- green, in a clean checkout and in CI, having
// asserted nothing, while a real PES defect sat behind it. A skip that can
// go unnoticed is not a safe default for the repo's ONLY automated
// third-party format check.

const assert = require("node:assert");
const { test } = require("node:test");

let harness = null;
let run = null;
let loadError = null;

async function ensureRun() {
  if (!harness) {
    harness = await import("../tools/crossval-stitch-formats.mjs");
  }
  if (run || loadError) return;
  const python = harness.resolvePython();
  if (!python) {
    // Fail loud on CI; skip only on a developer box that has no venv yet.
    if (process.env.CI) {
      throw new Error(
        "no python with pystitch available, and CI is set. The cross-validation " +
          "harness must run for real in CI -- see .github/workflows for the " +
          "install step that provides it. Do not 'fix' this by allowing the skip."
      );
    }
    loadError = "no python with pystitch available";
    return;
  }
  run = harness.runCrossval({ python });
}

function skipOrGet(t, key) {
  if (loadError) {
    t.skip(loadError);
    return null;
  }
  const r = run.results[key];
  assert.ok(r && !r.error, key + " decoded without error: " + JSON.stringify(r));
  return r;
}

test("crossval control: DST shows the documented axis transposition", async (t) => {
  await ensureRun();
  const r = skipOrGet(t, "dst.notrim");
  if (!r) return;
  // DOCUMENTS KNOWN DEFECT (docs/dst-axis-verdict-2026-07-31.md): a
  // standard-conformant reader sees the design transposed — decoded point is
  // (y, -x) of the design point instead of (x, -y). If this reads
  // "identity", the codec was fixed: update the verdict docs and this pin.
  // If it reads anything else, the HARNESS is broken.
  assert.strictEqual(r.fit.transform, "anti-transpose");
  assert.ok(r.fit.rms < 0.5, "transposition is exact, rms=" + r.fit.rms);
  // DOCUMENTS KNOWN DEFECT: color change written as 0x43 instead of 0xC3 —
  // third-party readers see a sequin-mode toggle and ZERO color changes.
  assert.strictEqual(r.decodedColorChanges, 0);
  assert.strictEqual(r.decodedSequinToggles, 1);
});

test("crossval control: DST trim-as-3-jumps IS read back as a trim", async (t) => {
  await ensureRun();
  const r = skipOrGet(t, "dst.full");
  if (!r) return;
  assert.strictEqual(r.decodedTrims, 1);
});

test("crossval: EXP geometry and color changes are standard-conformant (no trims)", async (t) => {
  await ensureRun();
  const r = skipOrGet(t, "exp.notrim");
  if (!r) return;
  assert.strictEqual(r.fit.transform, "identity");
  assert.ok(r.fit.rms < 0.5, "exact geometry, rms=" + r.fit.rms);
  assert.deepStrictEqual(r.fit.offset, [0, 0]);
  assert.strictEqual(r.decodedColorChanges, 1);
  // FIXED 2026-08-06 (was: +1, the shared end-record quirk below) --
  // encodeEXP now stops at the terminal {type:"end"} sentinel the same way
  // pes.js's encoder already did, instead of falling through and writing it
  // as one extra zero-delta plain stitch.
  assert.strictEqual(r.decodedStitches, r.expectedStitches);
});

test("crossval: EXP trim record survives for standard readers (FIXED 2026-08-05)", async (t) => {
  await ensureRun();
  const r = skipOrGet(t, "exp.full");
  if (!r) return;
  // FIXED (was DOCUMENTS KNOWN DEFECT): trimRecord() now writes the
  // Melco-convention 4-byte control (0x80 0x80 0x07 0x00) instead of the
  // 2-byte 0x80 0x03 that made pyembroidery-convention readers abort the
  // rest of the file at the first trim. All 15 design stitches now survive
  // exactly (see the no-trim test above for the end-record fix), along with
  // the trim and the second color block's color change.
  assert.strictEqual(r.decodedStitches, r.expectedStitches);
  assert.strictEqual(r.fit.transform, "identity");
  assert.ok(r.fit.rms < 0.5, "exact geometry, rms=" + r.fit.rms);
  assert.strictEqual(r.decodedColorChanges, 1, "color change after the trim now survives");
  assert.strictEqual(r.decodedTrims, 1);
});

test("crossval: PES stitch stream decodes cleanly for standard readers (FIXED 2026-08-05)", async (t) => {
  await ensureRun();
  const r = skipOrGet(t, "pes.notrim");
  if (!r) return;
  // FIXED (was DOCUMENTS KNOWN DEFECT): the PEC block layout was 5 bytes off
  // the standard (1 extra header pad byte + two non-standard u16 "start x/y"
  // fields); deleting those 5 bytes and re-deriving the graphics-offset
  // field against the standard's PEC-relative-512 baseline puts the stitch
  // stream back in frame. A standard reader now decodes the exact stitch
  // count with identity transform and rms 0.
  assert.strictEqual(r.decodedStitches, r.expectedStitches);
  assert.strictEqual(r.fit.transform, "identity");
  assert.ok(r.fit.rms < 0.5, "exact geometry, rms=" + r.fit.rms);
  assert.strictEqual(r.decodedColorChanges, 1, "color change now survives the framing fix");
});

test("crossval: PES thread palette maps design colors to nearest Brother chart entry (FIXED 2026-08-05)", async (t) => {
  await ensureRun();
  const r = skipOrGet(t, "pes.notrim");
  if (!r) return;
  // FIXED (was DOCUMENTS KNOWN DEFECT): pes.js now maps each design color's
  // RGB to the nearest Brother PEC chart index (see BROTHER_PEC_CHART /
  // nearestPecIndex in src/pes.js) instead of leaving paletteIndex unset and
  // falling back to sequential chart indices 1,2,3... Palette identity is
  // still not perfectly lossless (PEC only has 64 fixed chart colors, so an
  // arbitrary design RGB snaps to its nearest chart neighbor rather than
  // round-tripping exactly) -- that's the expected, remaining gap of a
  // nearest-match scheme, not a bug. The fixture's red (200,30,30) and blue
  // (30,60,200) now decode as the Brother chart's nearest actual Red/Blue
  // entries instead of two unrelated dark blues.
  assert.strictEqual(r.threads.length, 2);
  assert.deepStrictEqual(r.threads, ["#ed171f", "#0a55a3"]);
});
