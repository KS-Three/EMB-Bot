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
  // DOCUMENTS KNOWN DEFECT, and the harness has shown it since the day it was
  // written without anyone asserting it: DST decodes ONE MORE stitch than the
  // design has. encodeDST does not stop at the terminal {type:"end"} sentinel
  // the way exp.js and pes.js both do (one line, `if (st.type === "end")
  // break;`), so it writes it as a real stitch record.
  //
  // The 2026-08-04 verdict deferred this as "one extra phantom stitch",
  // priced on the LETTERING lane where the sentinel sits on the last stitch
  // and the extra record is zero-delta. Measured on the imported/digitized
  // lane 2026-09-07, that price is wrong: buildImportedDesign puts the
  // sentinel at the ELEMENT'S OFFSET, so on a real 95.7 x 58.3 mm logo the DST
  // ends with a stitch **0.07 mm from the design's centre, 46.4 mm from the
  // previous one** — a stray needle penetration in the middle of the design,
  // with 46 mm of travel to reach it. PES and EXP of the same design end where
  // the design ends. Every single-element imported, digitized, shape or manual
  // project carries it; pure lettering does not (buildLetteringDesign appends
  // no sentinel at all).
  //
  // Left in place because the DST codec is Kent's (CLAUDE.md footgun 1). If
  // this starts failing, that call was made — drop this assertion and the
  // MASTER_SCOPE note with it.
  assert.strictEqual(r.decodedStitches, r.expectedStitches + 1);
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

// ---- a stitch too long for one record ------------------------------------
//
// The `long` fixture puts a 300-unit (30 mm) segment BETWEEN two stitches. A
// PEC record reaches +/-2047 units and carries it whole; a DST record reaches
// +/-121 and an EXP record +/-127, so both must split it — and WHAT the
// intermediate records are decides whether the design is sewn or travelled
// over. Until 2026-09-07 dst.js emitted JUMPS for them (thread silently turned
// into travel: 3,769 of them on a real Full Back monogram) while exp.js
// emitted stitches. One design, two sew-outs, and nothing compared them. These
// three pins are what compares them.

test("crossval: a long stitch is SPLIT into stitches by DST", async (t) => {
  await ensureRun();
  const r = skipOrGet(t, "dst.long");
  if (!r) return;
  assert.ok(r.decodedStitches > r.expectedStitches, "the 300-unit segment must become several records");
  // 121 units per axis is the format's own reach, so that is the longest a
  // reader can see sewn. (A diagonal step could reach 121*sqrt(2); this
  // fixture's long segment is axis-aligned.)
  assert.strictEqual(r.longestSewnUnits, 121);
});

test("crossval: EXP splits it the same way, at its own 127", async (t) => {
  await ensureRun();
  const r = skipOrGet(t, "exp.long");
  if (!r) return;
  assert.ok(r.decodedStitches > r.expectedStitches);
  assert.strictEqual(r.longestSewnUnits, 127);
  // The two encoders now agree in kind. They differ only by their formats'
  // reach, which is why the counts are not equal: DST needs three records for
  // 300 units and EXP needs three as well, but the design's own leading
  // zero-delta jump reads differently between the two readers (pystitch
  // reports JUMP 1 for EXP and 0 for DST on an identical zero-length move —
  // observed, not explained, and a no-op either way).
  assert.ok(r.decodedStitches >= 6);
});

test("crossval: PES carries a 30 mm stitch whole (DOCUMENTS KNOWN DEFECT)", async (t) => {
  await ensureRun();
  const r = skipOrGet(t, "pes.long");
  if (!r) return;
  // PEC's long form reaches +/-2047 units, so nothing in the FORMAT forces a
  // split — and pes.js does not impose one. No machine sews a 30 mm stitch.
  // Whether to split it anyway means importing a limit from another format,
  // which is a machine-behaviour call rather than a spec one; measured and
  // left to Kent. If this assertion starts failing, that call was made:
  // update it and the DOCTRINE entry with it.
  assert.strictEqual(r.decodedStitches, r.expectedStitches, "no split");
  assert.strictEqual(r.longestSewnUnits, 300, "30 mm, in one record");
});
