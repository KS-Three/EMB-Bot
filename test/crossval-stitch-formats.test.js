// Cross-validation pins: browser PES / EXP / DST encoders vs. pyembroidery.
//
// These tests PIN CURRENT BEHAVIOR, including known defects — they are a
// tripwire, not an endorsement. Several assertions document defects that are
// deliberately NOT fixed here (files in the wild; changing the encoders is
// Kent's call, exactly like the DST axis bug). If one of these "documents
// known defect" assertions starts failing, the encoder's third-party-visible
// behavior CHANGED — read docs/pes-crossval-verdict-2026-08-04.md and
// docs/dst-axis-verdict-2026-07-31.md before "fixing" anything.
//
// Needs a Python interpreter with pyembroidery (the digitizer venv, or
// $EMB_CROSSVAL_PYTHON). Skips cleanly when none is available.

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
    loadError = "no python with pyembroidery available";
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
  // Encoder quirk (shared with DST): the terminal {type:"end"} design record
  // is emitted as one extra zero-delta plain stitch.
  assert.strictEqual(r.decodedStitches, r.expectedStitches + 1);
});

test("crossval: EXP trim record truncates the file for standard readers", async (t) => {
  await ensureRun();
  const r = skipOrGet(t, "exp.full");
  if (!r) return;
  // DOCUMENTS KNOWN DEFECT (docs/pes-crossval-verdict-2026-08-04.md): the
  // 2-byte trim record 0x80 0x03 is not a control code pyembroidery knows;
  // its reader aborts there, silently dropping every stitch after the first
  // trim (here: 4 of 15 stitches, the color change, and the whole second
  // color block).
  assert.strictEqual(r.decodedStitches, 11, "decode stops at the trim");
  assert.strictEqual(r.decodedColorChanges, 0, "color change after trim is lost");
});

test("crossval: PES stitch stream is mis-framed for standard readers", async (t) => {
  await ensureRun();
  const r = skipOrGet(t, "pes.notrim");
  if (!r) return;
  // DOCUMENTS KNOWN DEFECT (docs/pes-crossval-verdict-2026-08-04.md): the
  // PEC block layout is 5 bytes off the standard (1 extra header pad byte +
  // two non-standard u16 "start x/y" fields), so a standard reader decodes
  // the stitch stream out of frame: phantom moves, one-byte phase shift,
  // then it walks the blank-thumbnail region as hundreds of (0,0) stitches.
  // If these start reading CLEANLY, the encoder changed: update the verdict
  // doc and pin the new behavior.
  assert.notStrictEqual(r.decodedStitches, r.expectedStitches);
  assert.ok(
    r.decodedStitches > 5 * r.expectedStitches,
    "phantom stitches from the thumbnail region (got " + r.decodedStitches + ")"
  );
  assert.notStrictEqual(r.fit.transform, "identity");
  assert.strictEqual(r.decodedColorChanges, 0, "color change is lost in the mis-framed stream");
});

test("crossval: PES thread palette ignores design colors", async (t) => {
  await ensureRun();
  const r = skipOrGet(t, "pes.notrim");
  if (!r) return;
  // Color COUNT survives (2 threads listed), but identity does not: no code
  // path sets paletteIndex, so the PEC palette is always sequential chart
  // indices 1,2,3... — fixture red/blue decode as Brother chart entries
  // (dark blues), regardless of the design's actual colors.
  assert.strictEqual(r.threads.length, 2);
  assert.deepStrictEqual(r.threads, ["#0e1f7c", "#0a55a3"]);
});
