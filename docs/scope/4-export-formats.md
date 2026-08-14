# Area 4 — Export formats

**Part of [`MASTER_SCOPE.md`](../../MASTER_SCOPE.md)** — this is the detail
for one capability area. The live one-line verdict (Status / Confidence /
what is next) is in MASTER_SCOPE; this file is the supporting record.

**Claim discipline:** a claim here should carry a `(verb date — source)`
pointer — `confirmed` = checked against code or a passing test, `measured` =
a number was produced, `suspected` = neither. Much of this file predates that
rule and is **not yet annotated**; anything unannotated is unverified until
someone checks it. Test counts, stitch counts and corpus grades written here
were snapshots when written — do not quote one as a current baseline.
Dated narrative belongs in [`../scope-history.md`](../scope-history.md).

---

DST, EXP, PES, SVG, and the PDF worksheet — both the browser JS encoders and
the Python digitizer service's `/export` route (pyembroidery-based).

**Status:** Implemented, all five formats, both paths — with one
reachability caveat: the service `/export` path is only reachable from the
product for purely-digitized designs (`app/src/ui/DownloadStep.svelte`
gates `preferService` on `isPurelyDigitized`); any design containing
lettering or manual shapes downloads through the browser encoders.

**Confidence — varies by format, not one score:**
- **DST:** split by path. Browser DST is Medium as Studio's sewn-and-shipping
  default; Low if treated as verified-correct-orientation in the abstract —
  see the cross-cutting DST item, this is the same bug. Python `/export` DST
  (pyembroidery, standard-conformant) is Medium-High by spec, not yet
  sew-verified itself.
- **EXP: Medium-High**, upgraded from Medium-Low this pass. The PR #18
  cross-validation (see the cross-cutting DST section above) had found the
  browser encoder's geometry/color/jump encoding genuinely
  standard-conformant but its 2-byte trim record fatal to pyembroidery-
  convention readers at the first trim — **fixed 2026-08-05**
  (PR #58, `pes-exp-byte-framing-fix`): `trimRecord()` now writes the 4-byte Melco
  form. Harness re-run: a trimmed design now decodes whole (identity
  transform, rms 0, colour change and second colour block both present),
  where it used to truncate at 11 of 15 stitches. **Also fixed, 2026-08-06:**
  the "end"-record extra-stitch quirk this entry used to flag as out of
  scope — `encodeEXP` fell through to the generic stitch path for the
  terminal `{type:"end"}` sentinel `stitchModel.js` always appends, writing
  it as one real zero-delta stitch that standard readers decoded as an extra
  phantom stitch beyond the design's true count (16 of 15). `pes.js`'s own
  encoder already stopped at `"end"` the same way; `encodeEXP` now does too
  (`if (st.type === "end") break;`, matching `pes.js`'s exact pattern).
  Harness re-run: `exp.notrim`/`exp.full` both now read `expected 15, decoded
  15` (was `decoded 16`). DST carries the identical underlying gap and is
  deliberately left alone (Kent's call, migration risk — see the cross-
  cutting section) — EXP has no importer anywhere in this codebase, so
  fixing it here carries none of that risk, same low-risk read the original
  PES/EXP fix got. Not raised all the way to High since this is
  cross-validated against pyembroidery, not a real machine/software sew or
  open. The Python `/export` path was never affected (different writer).
- **PES: Medium-High**, upgraded from Low this pass. README's own
  "best-effort — reverse-engineered" framing still applies to the format's
  general maturity, but the specific defects PR #18 found — the 5-byte
  stitch-stream mis-framing, jump records flagged as trims, palette indices
  never set — are **fixed 2026-08-05** (PR #58, `pes-exp-byte-framing-fix`): the
  extra header pad byte and the two non-standard `0x9000` fields are
  deleted, the graphics-offset field is re-derived against the standard's
  PEC-relative-512 baseline, jump records use PEC flag `0x1000` (was
  incorrectly sharing trim's `0x2000`), and a nearest-Brother-chart-index
  colour mapping (`BROTHER_PEC_CHART`/`nearestPecIndex` in `src/pes.js`,
  sourced from pyembroidery's `EmbThreadPec.get_thread_set()`) now sets
  `paletteIndex` from design RGB. Harness re-run: 15/15 stitches, identity
  transform, rms 0, colour change present, threads nearest-chart-matched to
  the fixture's actual red/blue (was 354 phantom stitches from a mis-framed
  stream, 0 colour changes, wrong/arbitrary sequential-fallback threads).
  Not raised to High: nearest-chart colour mapping is inherently lossy (PEC
  has only 64 fixed chart colors, so this is a snap-to-nearest, not an exact
  round-trip), and this is pyembroidery cross-validation, not a verified
  Brother-machine load or PE-Design open — the verdict memo's own closing
  line still calls for that as the last mile. Coverage: the original 3
  targeted tests (updated for the new byte layout) plus the crossval
  harness's PES-specific pins, which do now cross-validate against an
  independent decoder.
- **SVG: Medium-High**, upgraded from Medium (2026-08-06) — still lower
  stakes than a real stitch format (vector proof only), but the "thin
  coverage (1 test)" gap this doc used to flag is closed: `test/svgexport
  .test.js` grew to 10 tests, reading a close pass of `src/svgexport.js`
  rather than guessing at edge cases -- real extents recomputed from stitch
  coordinates (not trusted from the design's own possibly-stale
  `widthMM`/`heightMM` fields), the DST-up-to-SVG-down Y flip, one
  `<polyline>` per color run, both jumps and trims correctly breaking a path
  without drawing a travel line across the gap, a missing color falling
  back to black rather than throwing, and a null/undefined/empty design
  producing a minimal valid SVG rather than crashing. One documented-not-
  fixed behavior worth knowing about, not treated as a bug: a lone stitch
  sitting between two jumps renders nothing (`designToSVG`'s `run.length >=
  2` gate can't turn a single point into a `<polyline>`) — real designs
  essentially never produce an isolated single-stitch run (satin/fill always
  emit many), so this was left as a pinned, conscious simplification rather
  than a speculative fix. No production code changed; the pass through
  `src/svgexport.js` while writing these tests found the existing logic
  correct on every dimension checked. Full engine suite: `node --test` —
  **283/283 passed, 0 failed** (274 baseline, this pass's own EXP fix
  included, + 9 new SVG tests replacing the old 1).
- **PDF worksheet: Medium-High** — was "no dedicated test file exists at
  all," then gained call-sequence coverage, and this pass closes the
  remaining gap. `app/src/lib/pdfsheet.spec.js` (merged, PR #4) drives
  `src/pdfsheet.js` against a `FakeJsPDF` recorder — title, the placement
  line (and its omission), the stats block, the thread sequence (incl. its
  no-name fallback), the stitch-sim image embed, `garmentBox` forwarding,
  multi-page pagination, and the zero-design/no-throw path. **Merged, PR
  #30** adds the second tier this doc used to flag as missing: `app/src/lib
  /pdfsheet.realpdf.spec.js` runs the same builder against the REAL `jspdf`
  package (no fake) and inspects the actual generated PDF bytes — page
  count cross-checked three independent ways (jsPDF's own count, raw
  `/Type /Page` object count, the Pages tree's declared `/Count`), byte
  size, and extractable text (a regex pulls real `Tj` text-show operators
  out of jsPDF's uncompressed content stream) confirming the title, stats,
  and thread-sequence lines are genuinely present in the output, not just
  called-for. The PR's own verification independently reproduced the
  regression-catching claim: breaking a real line of `pdfsheet.js` failed
  both tiers, for independently-derived reasons. Left at Medium-High, not
  High, since this is still automated-inspection rather than a human/visual
  check of the rendered page.

**Open issues:** DST axis bug (cross-cutting, see above) — unchanged, still
Kent's call, `src/dst.js` deliberately untouched by the PES/EXP fix below.
PES/EXP's own cross-validation findings (PR #18) are **fixed as of
2026-08-05** (PR #58, `pes-exp-byte-framing-fix` — see the cross-cutting section
above and this file's "Last updated" entry for the full before/after): PES
no longer decodes as garbage in standard readers, and EXP no longer aborts
at the first trim. The "end"-record extra-stitch quirk EXP used to share
with DST is **also fixed as of 2026-08-06** — see the EXP bullet above;
DST keeps its own copy of the same gap, deliberately, Kent's call.
Remaining, explicitly-accepted gaps: nearest-chart colour mapping isn't a
lossless round-trip (64 fixed PEC chart colors); and no real Brother-machine
load or PE-Design open has happened yet — only pyembroidery
cross-validation.

**Next step:** for DST, same as the cross-cutting item — a third-party
sew-out/read settles the axis question. For PES/EXP, the verdict memo's own
closing line: a real Brother-machine load (or PE-Design open) of a
harness-clean PES file, to confirm machine behavior matches the
cross-validation, not just pyembroidery agreement. Separately, not
sew-out-gated: `pystitch` (Ink/Stitch's MIT-licensed pyembroidery
fork — see the cross-cutting "Ink/Stitch research" section above) as a
replacement for this area's `pyembroidery` dependency is now evaluated —
`docs/pystitch-evaluation-2026-08-11.md`, verdict **Adopt**, checked
against `digitizer_service/formats.py` and the other call sites — with
adoption in progress in a parallel lane as of 2026-08-11.
