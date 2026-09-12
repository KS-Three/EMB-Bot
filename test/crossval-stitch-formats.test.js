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

test("crossval control: DST is standard-conformant (FIXED 2026-09-08)", async (t) => {
  await ensureRun();
  const r = skipOrGet(t, "dst.notrim");
  if (!r) return;
  // FIXED 2026-09-08 (was DOCUMENTS KNOWN DEFECT). This asserted
  // "anti-transpose" and its own comment said: 'If this reads "identity", the
  // codec was fixed: update the verdict docs and this pin.' It reads identity
  // now. `dst.js` writes X to the low nibble and Y to the high one,
  // byte-identical to `pystitch.DstWriter.encode_record` across ten deltas, so
  // DST joins PES and EXP as standard-conformant.
  assert.strictEqual(r.fit.transform, "identity");
  assert.ok(r.fit.rms < 0.5, "exact, rms=" + r.fit.rms);
  // FIXED 2026-09-08 (was DOCUMENTS KNOWN DEFECT): the colour change is
  // written 0xC3, so a standard reader sees a real colour stop. It was 0x43,
  // which is not a colour change to anyone but us — pystitch read ZERO colour
  // changes and one spurious sequin-mode toggle, so every multi-colour .dst
  // EMB-Bot wrote sewed straight through on another machine: no stop, no
  // thread change, the whole design in one colour.
  //
  // This is the colour half of docs/dst-axis-verdict-2026-07-31.md's finding.
  // The AXIS half is fixed too, the same day — the identity assertion at the
  // top of this test IS it. The two were filed together but are independent;
  // both are closed now, and neither is Kent's open call any more.
  assert.strictEqual(r.decodedColorChanges, 1, "the colour stop is visible to a standard reader");
  assert.strictEqual(r.decodedSequinToggles, 0, "and is no longer read as a sequin toggle");
  // REGRESSION GUARD (read "DOCUMENTS KNOWN DEFECT" until 2026-09-07). The
  // harness showed this for weeks before anyone asserted it: DST decoded ONE
  // MORE stitch than the design has, because encodeDST fell THROUGH the
  // terminal {type:"end"} sentinel and wrote it as a real stitch record
  // instead of stopping the way exp.js and pes.js both do.
  //
  // The 2026-08-04 verdict deferred it as "one extra phantom stitch", priced
  // on the LETTERING lane where the sentinel sits on the last stitch and the
  // extra record is zero-delta. That price was wrong on every other lane:
  // buildImportedDesign puts the sentinel at the ELEMENT'S OFFSET, so a real
  // 95.7 x 58.3 mm logo ended with a stitch 0.07 mm from the design's centre,
  // 46.4 mm from the previous one — a stray needle penetration mid-design
  // with 46 mm of travel to reach it, on every imported, digitized, shape or
  // manual project. Pure lettering never carried it (buildLetteringDesign
  // appends no sentinel at all).
  //
  // FIXED in 5cb234a (2026-09-07): `if (st.type === "end") break;` in
  // src/dst.js, placed BEFORE the extents update so the sentinel also stopped
  // widening the header's declared bounding box. If this assertion fails the
  // phantom stitch is BACK — fix the codec, do not drop the assertion.
  assert.strictEqual(r.decodedStitches, r.expectedStitches,
    "the design ends where the design ends");
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

// ---- a stitch too long to SEW --------------------------------------------
//
// The `long` fixture puts a 300-unit (30 mm) segment BETWEEN two stitches. A
// DST record reaches +/-121 and an EXP record +/-127, so the FORMAT makes
// both split it — and WHAT the intermediate records are decides whether the
// design is sewn or travelled over. Until 2026-09-07 dst.js emitted JUMPS for
// them (thread silently turned into travel: 3,769 of them on a real Full Back
// monogram) while exp.js emitted stitches. One design, two sew-outs, and
// nothing compared them. These three pins are what compares them.
//
// A PEC record reaches +/-2047 and carried the 30 mm whole until 2026-09-12,
// so PES was the one encoder emitting a move no machine can make. Kent ruled
// that day: split it at 121 — the repo's sewability bar rather than the
// format's reach. All three now agree in kind, and PES and DST agree to the
// unit.

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

test("crossval: PES splits it too, at the imported 121 (FIXED 2026-09-12)", async (t) => {
  await ensureRun();
  const r = skipOrGet(t, "pes.long");
  if (!r) return;
  // FIXED 2026-09-12 (was "PES carries a 30 mm stitch whole (DOCUMENTS KNOWN
  // DEFECT)", asserting decodedStitches === expectedStitches and
  // longestSewnUnits === 300). That test's own comment said: "Whether to
  // split it anyway means importing a limit from another format, which is a
  // machine-behaviour call rather than a spec one; measured and left to
  // Kent. If this assertion starts failing, that call was made." Kent made
  // it: split, at 121 units.
  //
  // PEC's long form still reaches +/-2047, so this split is NOT the format
  // talking — it is the repo's sewability bar, one DST record, the same
  // `max(|dx|,|dy|) > 12.1 mm` test tools/long-stitch-census.mjs counts with
  // and the 2026-09-11 split-satin ruling is stated in. 121 rather than EXP's
  // 127 so that a PES file never carries a sewn move DST would have split.
  assert.ok(r.decodedStitches > r.expectedStitches, "the 300-unit segment must become several records");
  assert.strictEqual(r.longestSewnUnits, 121);
  // And PES now reads EXACTLY like the DST control on this fixture: same
  // count, same longest sewn segment. Three encoders, one sew-out. (EXP
  // differs only by the 6 units of slack its record has — see the test
  // above.) That equality is the whole point of the ruling, so it is
  // asserted rather than left to be noticed.
  const dst = run.results["dst.long"];
  assert.strictEqual(r.decodedStitches, dst.decodedStitches);
  assert.strictEqual(r.longestSewnUnits, dst.longestSewnUnits);
  // The split must lay THREAD, not travel: the 300-unit move happens between
  // two stitches, so the only jump a reader may see is the fixture's own
  // leading travel-in. This is the assertion that would have caught dst.js's
  // pre-2026-09-07 "split everything as jumps" (3,769 of them on a real Full
  // Back monogram).
  assert.strictEqual(r.decodedJumps, 1, "one leading travel-in jump, and no thread turned into travel");
  assert.strictEqual(r.decodedTrims, 0);
});
