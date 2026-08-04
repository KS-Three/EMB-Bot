# EMB-Bot — Master Scope

**What this is:** a live status dashboard, not a requirements doc. It exists so
Kent and any Claude session can answer "where do we actually stand?" without
re-deriving it from a dozen spec/plan docs each time. It tracks five product
capability areas on two independent axes — **Status** (is it built) and
**Confidence** (do we trust it) — plus cross-cutting issues that don't respect
area boundaries.

**How it's kept current:** updated proactively after PR-sized work lands, and
on demand via the `/update-master-scope` skill. See "How this document works"
at the bottom for the authority model behind the confidence ratings.

**Last updated:** 2026-08-04, later the same day — docs refresh after PRs
#8–#15 finished merging into `main` (this doc's previous pass, dated below,
was written mid-batch and undercounted what had already landed), touched up
once when **PR #23 (meander tonal tier, row 9) merged mid-refresh**, then
again minutes later when **PR #22 (opaque-alpha fix + `debugviz.
direction_field` restore) also merged**. Both touch-ups were re-verified
directly against the new `main` tip each time, not assumed: combined suite
on current `main` (`c0cb246`) now reads engine `node --test` **266/266**,
Studio `npx vitest run` **331/331** (24 files), digitizer `pytest` **507
passed / 3 failed** — back down to exactly the three long-standing
container-environment golden mismatches cited repeatedly in this project's
PR history (`test_flat_lane_byte_identical`, `test_pushcomp`,
`test_stage2_photo_segment`, all `logo_alpha.png`/`logo_whitebg.png`-towel).

The `test_directionfield::test_drone_render_smoke_and_debug_artifact`
failure this note tracked through two earlier revisions (the direction-field
branch had merged without its `debugviz.direction_field` render function —
an agent lane's uncommitted worktree edit) **is gone, confirmed**: #22
restored the function and is now on `main`. Verified by running the
digitizer suite against a fresh `origin/main` worktree after the merge, not
by assuming the PR description was correct.

Substance changes found on `main` since the prior pass below: the full
`BACKGROUND_ENCLOSED` stack (pipeline + service contract + Studio Layers-panel
restore UI) is now merged — area 1's bullet below was still describing it as
"not built"; the rotation/hoop-fit auto-fit bug flagged as unfixed in area 3
is fixed (`8e668d3`); a Playwright wizard-smoke e2e exists and passes
(1/1, re-run this session); the PDF worksheet export gained dedicated test
coverage (area 4 was still describing zero coverage); direction field (photo
plan row 6), scan-line mono tonal (row 8), and meander tonal (row 9, PR #23)
all landed; the opaque-alpha bug that silently defeated background
detection on every real Studio upload (PR #22) is fixed, so
`BACKGROUND_ENCLOSED` is now genuinely end-to-end, not just unit/service-
tested. Separately, **6 PRs (#16–#21) remain open/draft against `main`,
pending review** — none of that work is described as shipped below, only
flagged per-area with its PR number.

Prior update 2026-08-04 (font-license audit items 4–10 + 12 executed —
full license texts on disk/served/embedded, complete attributions, credits
links; the lawyer consult (item 11) is now the only open compliance gate.
Prior update 2026-08-03: the gradient angle-fragmentation fix landed
that session; `BACKGROUND_ENCLOSED`'s root cause was corrected to
`stage1_prep.py`, still unresolved).

---

## At a glance

| Area | Status | Confidence |
|---|---|---|
| 1. Auto-digitizing quality (image → stitches) | In progress | **Low** beyond flat spot-color art |
| 2. Font library & lettering | Implemented (library + license remediation) | High (tech) / Medium (compliance — one lawyer consult still open, blocking first dollar) |
| 3. Studio app / guided wizard | Implemented | Medium (fabric-preset accuracy: pending sew-out) |
| 4. Export formats | Implemented | Varies by format — see below |
| 5. Stitch-out review & manual editing tools | Implemented (narrow scope) | High |

---

## Cross-cutting issues

Things that don't respect one capability area's boundary. Referenced from the
area they drag down, documented once here.

### DST codec axis bug

EMB-Bot's own browser DST codec (`src/dst.js` / `src/dstimport.js`) is
transposed vs. the Tajima/pyembroidery standard — confirmed, unresolved.
It round-trips correctly against itself but reads a quarter-turn wrong in
third-party software. Full evidence trail: `dst-codec-axis-discrepancy` in
memory, `docs/dst-axis-verdict-2026-07-31.md`, `digitizer/README.md`'s "Open
finding" section.

**A nuance worth flagging, not a fix:** CLAUDE.md says "treat browser DST as
EMB-Bot-internal only," while `digitizer/README.md`/`digitizer_service/formats.py`
say browser DST stays the Studio's *default* encoder "because it is the one
with sewn evidence behind it." These aren't necessarily contradictory — the
first is about trusting browser DST as correct-orientation for arbitrary
third-party software; the second is about which of EMB-Bot's own two encoders
Studio picks internally — but they read differently enough side-by-side that
it's worth Kent confirming the intended reading rather than assuming.

**Resolution path:** a sew-out or third-party read of a browser-encoded DST
(the "third opinion" `digitizer/README.md` calls for). Fixing the codec itself
is explicitly Kent's call — every existing EMB-Bot DST is affected by any fix.

**Independent corroboration exists but is not yet on `main`:** open PR #18
(`pes-crossval`, pending review) adds a browser-encode → pyembroidery-decode
cross-validation harness with DST as the control case — it reproduces the
transposition independently (anti-transpose, rms 0.0), which the PR frames as
validating the harness method itself, not as new information about the bug.
The PR's real news is about the other two encoders, previously unchecked
against an independent implementation: it reports the browser **PES**
encoder as unreadable by standard readers (a 5-byte stitch-stream
mis-framing plus two non-standard fields), worse off than DST since there's
no PES importer to create a migration trap; and **EXP** as geometrically
standard-conformant but truncated by conformant readers at the first trim
(2-byte trim record vs. the standard's 4-byte form). No encoder was changed —
this is a findings-only PR, same Kent's-call posture as the DST bug — and
it is **not merged**, so treat these as reported-not-verified until it lands.

### Font license compliance gap — REMEDIATED 2026-08-04 except the lawyer consult

`docs/font-license-audit-2026-07-31.md` action checklist: **items 1–3 done**
(the 4 flagged fonts pulled, 72 → 68 — see the audit's §7) and **items 4–10 +
12 done** the same day (see its §8): every one of the 68 fonts now has its
full upstream license text on disk (`src/fonts/<key>.LICENSE.txt`), shipped
by `copy-engine.mjs` at `/fonts/<key>.LICENSE.txt`, linked per-font in the
credits dialog, AND embedded verbatim in the `.embf` binary metadata (closes
the bare-download hole); manifest attributions are complete notices
(adapter + upstream copyright + Reserved-Font-Name declarations, emails
stripped); guard tests pin all of it. No Reserved Font Name surfaces as a
primary name anywhere.

**Still open — the one remaining launch gate:** audit item 11, the one-hour
lawyer consult on the CC-BY-SA ShareAlike question (does BY-SA attach to the
14 CC-BY-SA-derived `.embf` binaries and customers' stitch files?). The
ready-to-send brief is `docs/lawyer-brief-cc-by-sa-2026-08-04.md`; booking it
is Kent's real-world action, before first dollar. Worst case per the audit:
relabel 14 binaries + customer note, or pull 14 fonts. Also parked for Kent:
the `satin-fonts.js` legacy-registry residual (audit §7) if `EMB-Bot.html` is
ever distributed, and the bluenesia permission screenshots (audit §8).

**A different resolution to this same gate is drafted but not merged:** open
PR #16 (`sharealike-pull`, pending review) executes a different, already-made
Kent decision — pull all 13 ShareAlike fonts (11 CC-BY-SA-4.0 + 2
CC-BY-SA-2.5) from the shipping library rather than wait on the consult,
taking the library 68 → 55 with zero ShareAlike remaining and, per the PR,
making the lawyer consult non-launch-blocking (the brief stays on file as a
restore path). Stacked on it, PR #17 (`legacy-font-audit`, pending review)
removes the same pulled fonts from the legacy `satin-fonts.js` registry
(21 → 14 entries) that audit §7 flagged as a residual exposure. **Neither PR
is on `main`** — the 68-font count and the open lawyer-consult gate above are
still what's actually shipping; if/when #16 merges this whole subsection
should be rewritten, not just updated.

### No physical sew-out testing has occurred yet

Zero sew-out testing has been done anywhere in this project — confirmed
independently across three separate research passes (auto-digitizing, Studio
fabric presets, export formats). `docs/hardening-closeout-2026-08-02.md`
states it plainly: "Nothing was sewn. Every number above... is geometry."
This is the single biggest confidence ceiling in the project: fabric-preset
accuracy, real stitch quality beyond test-suite geometry checks, and the DST
axis question all wait on this. Four hoopings are already specified in
`docs/hardening-closeout-2026-08-02.md` and would resolve nine currently-open
geometric questions at once — the highest-leverage next action across the
whole project, whenever Kent's ready to schedule it (his explicit call, not
something to push for).

---

## Capability areas

### 1. Auto-digitizing quality (image → stitches)

Covers both implementations that turn an image into stitches: the original
browser JS engine (`src/flatten.js`, `digitize.js`, `geometry.js`, `fill.js`,
`satin.js`) and the Python pipeline (`digitizer/digitizer_core/`) — tracked as
one capability regardless of which implementation is responsible, since
that's how feedback on digitizing quality actually needs to land.

**Status:** In progress. The JS engine is complete but frozen — COOKBOOK.md
notes it was retired in favor of "feed it clean flat art," not because it's
broken. The Python pipeline is the active target: `digitizer/README.md`
states "build steps 1, 3, 4 and 8 of 11" — SAM2 segmentation deferred,
stitch processor / preflight scoring / review-UI polish still to come.
Running in parallel with that step numbering, `docs/photo-digitizing-plan-
2026-07-31.md`'s mono-tonal/portrait technique rows have started landing:
direction field (row 6, structure-tensor + ETF per Kang 2007), scan-line
mono tonal (row 8), and now meander tonal (row 9, **PR #23, merged**) are
all on `main` and counted below. One more sits in open, unmerged PRs:
streamline mono slice (row 10, PR #20), with a multi-color layered-mode
follow-up stacked on top (PR #25) — neither on `main`, neither counted
below.

**Confidence: Low** beyond flat spot-color art. Flat-logo digitizing (both
implementations) is Medium — **266/266** JS tests and **507/510** Python
tests pass (verified this session on `origin/main`; see the "Last updated"
note above — exactly the 3 pre-existing container goldens now, the 4th
regression this note tracked through two revisions is fixed), and the
geometry is internally consistent. `hardening-closeout-2026-08-02.md`
independently re-measured the five newest Python features and found
defects the shipped test suites couldn't see in all five; one of those five
is now fixed (see below), four remain open:

- **Chaining (needle-down travel between shapes) — FIXED 2026-08-03.** Was:
  sews needle-down thread on bare fabric on a stock preset, up to 16.15mm
  exposed, invisible to the shipped test suite because it measured polygon
  cover instead of actual thread position. `_link_cover`
  (`digitizer_core/stage7_sequence.py`) now builds the "already laid" half
  of its cover from the block's own emitted stitch centrelines (buffered to
  real thread width) instead of each shape's sewing polygon. Measured on the
  committed `logo_alpha` fixture: chaining's extra links (10→14) now add
  **zero** bare-fabric exposure — exposed-run count and worst clearance both
  land exactly on the chain-off baseline — while still cutting trims (13→9)
  and stitch count (3012→2992); confirmed independently via the rebuilt
  `tools/chain_probe.py` (which had its own pre-existing bug making its
  before/after comparison a no-op — also fixed). The second precondition —
  an inset on `covered_by`, the half of the cover whose thread doesn't exist
  yet at routing time — closed 2026-08-04: future-colour polygons are eroded
  by `LINK_COVER_INSET_MM` (0.75 mm, derived from the measured per-tier
  shortfall between each tier's real emitted thread and its polygon on both
  committed fixtures — fill 0.023 mm / satin 0.301 mm thread-edge boundary
  shortfall, run-tier honest only at its 0.527/0.539 mm inradius — plus
  `LINK_COVER_TOL_MM`; full table in `machine.py`) before they may bury a
  link, and a link the inset disqualifies becomes a jump, never an exposure.
  Re-measured with chaining on: logo_alpha still links 13→17 / trims 14→10
  with 0.00 mm added bare exposure on both fixtures. `chain_links` **stays
  off by default**: still open is the third precondition, a physical sew-out
  to validate `LINK_COVER_TOL_MM`, which is still a thread spec, not a
  measurement. The other four closeout defects below are unaffected by this
  fix and remain open.
- **Gradient blend tier** — shipped (`stage6_blend.py`), then within one day
  found to fragment into 23 independent-angle regions instead of one shared
  ramp, plus a separate `BACKGROUND_ENCLOSED` defect that silently drops
  enclosed white icon linework as holes
  (`docs/superpowers/plans/2026-08-03-gradient-tier-fragmentation-and-enclosed-white-defects.md`).
  **The angle-fragmentation half is FIXED, same-day follow-up session.**
  Root cause turned out narrower than first diagnosed: all 23 k-means
  fragments were falling to `blend_fill`'s ordinary-tatami fallback (already
  near-uniform post-quantize color, so per-fragment ramp detection almost
  never fires), and that fallback hardcoded `angle_deg=None` — 23
  independent `principal_angle_deg` calls on small, irregular silhouettes,
  the actual "patchwork of differently angled wedges." Fix: one shared
  `design_row_angle_deg` computed per-design (`stage6_blend.
  detect_design_ramp_angle`, fitting L/a/b independently and taking
  whichever channel actually carries the ramp — plain lightness fit misses
  the repro fixture entirely, r2 0.003, because it's a hue rotation not a
  lightness slope; b* carries it at r2 0.45), threaded into both the
  fallback and the true-ramp branch. Verified against the repro fixture end
  to end: every fragment's fill rows now land within 0.55° of each other,
  vs. up to 64° apart before. Fragment COUNT (still 23) and radial-ramp
  angle sharing remain explicit, documented non-goals of this fix. Full
  writeup: the plan doc's "Defect 1 update" section.

  **`BACKGROUND_ENCLOSED` (enclosed-white-icon drop) — the full stack is now
  BUILT and merged to `main`**, closing out the design pass this section
  used to describe as "not built." Root cause was `stage1_prep.py::prep`
  (the no-alpha color-heuristic branch): enclosed pixels used to fold into
  `bg`/get excluded from `fg` before stage 3 or vectorization ever ran, so
  they never became a `Region` with a `shape_id`, which made the warning's
  own "toggle it back on in review" claim false — there was no shape for a
  review edit to reference. All three layers of the fix landed: **pipeline**
  (`c1b9e35` — enclosed pixels join `fg`, `stage4_vectorize.
  tag_enclosed_background` tags `meta["enclosed_background"]`
  post-vectorization, `pipeline.py` resolves a `stitched` shape-override key
  defaulting to "not enclosed," and exclusion happens at `plan_stitches`
  only — never from `PipelineResult.regions`); **service contract**
  (`6651c96`, merged via PR #9 — `digitizer_service/app.py` accepts/
  validates `stitched` as a shape-override key and exposes it per-shape on
  `review.shapes`, with a real end-to-end round trip against the repro
  fixture in `test_service.py`); **Studio UI** (`8e42313`, merged via PR
  #10 — the Layers panel gives an unstitched shape its own dimmed row state
  ("not sewn — enclosed area", distinct from user-deleted), a restore
  action staged through the existing "Apply layer changes" flow, and an
  undo control). All of this is inside the 507/510 Python and 331/331
  Studio counts verified above.

  **The one caveat blocking real end-to-end verification is FIXED, merged
  PR #22:** Studio's actual upload path re-encodes every image through a
  canvas, which manufactures an all-255 opaque alpha channel; `stage1_prep`'s
  alpha branch used to treat *any* alpha channel as ground truth, so a
  fully-opaque one read as "nothing here is background" — background
  detection, and `BACKGROUND_ENCLOSED` with it, silently didn't fire for
  **every real Studio panel upload**, found on a two-squares fixture that
  digitized to 2 shapes as RGB but 3 as RGBA. Fix: an alpha channel with no
  pixel under the detection threshold now carries zero background
  information and is discarded. Same PR restored the `debugviz.
  direction_field` function that had gone missing from `main` (see the
  "Last updated" note above). **Verified post-merge:** POSTed the same
  opaque-RGBA two-squares fixture directly to the live service on current
  `main` — background now detected, 2 shapes, matching the RGB original
  exactly. **Not yet verified:** driving this through the actual Studio
  browser UI end to end (upload → digitize → see the restored shape in the
  Layers panel) — the HTTP-level reproduction above proves the fix, but
  nobody has watched it happen in a real browser session yet.
- **Contour fill** — still off by default, but two of the three 2026-08-02
  defects are fixed (2026-08-04): the widest-inscribed-bare-circle
  instrument (`digitizer_core/barecircle.py`) now exists and *is* the
  `starved` gate (fires past the measured structural centre dot + half a
  ring spacing = 1.07mm; the old area-fraction gate's false alarms and
  blind spots both proven fixed in `tests/test_barecircle.py`), and
  ring-to-ring transition chords are containment-tested (`_link` banks
  instead of stitching outside; 0.3mm-hole regression pinned). Remaining
  and why it stays off: the bare core itself — every healthy shape leaves
  a ~0.86mm bare dot at its centre (~10× tatami's 0.090mm), measured, not
  yet shrunk. One cited figure did not reproduce as written: the star's
  "2.94mm bare disc" is a diameter (radius ≈1.47mm; measured 1.33mm) —
  see `config.py`'s fill_technique block.
- **Satin/fill classifier** — the shipped rule misclassifies compact/noisy
  shapes (a serrated 20mm disc computes as "5.03mm" and gets satin-stitched
  instead of filled). The proposed DT-based replacement (`VP90`) was
  measured and **rejected 2026-08-02** at `SATIN_MAX_WIDTH_MM = 3.0`
  (`main`'s cap at the time) — it scored worse than the shipped rule there,
  and its "pure tightening, cannot get worse" safety claim was proven
  logically inverted (it can only convert true positives into false
  negatives, never the reverse, and FN is the expensive error). **Verdict
  status: STALE, not confirmed or reversed.** An unrelated, later,
  corpus-driven change moved the shipped cap to 5.0 (already on `main`);
  re-running the SAME instrument at the new cap flips the result (`VP90`
  0/21 wrong vs. the shipped rule's 6/21) — but that's the same class of
  small-synthetic-set evidence 2026-08-02's audit already showed can't be
  trusted alone. Needs the 37-file `scratch_corpus/` run at today's cap
  before this verdict can be re-decided either way — see
  `docs/superpowers/plans/2026-08-04-m0-shape-lens-measurement.md`
  ("M0" of the DT-first migration).
- **Fill row spacing (law 19)** — unresolved two-population finding: the
  0.20mm figure is a satin-rail artifact for one file population (refuted)
  but looks like a genuine denser pitch on 43 commissioned cap logos (still
  alive). Shipped `FILL_ROW_MM=0.40` unchanged pending sew-out.

Every claim about visual/sew quality beyond internal geometry checks is
**pending sew-out** — see the cross-cutting item above.

**Next step:** the chaining fix, the gradient angle-fragmentation fix, and
the full `BACKGROUND_ENCLOSED` stack (including the opaque-alpha fix, PR
#22, merged) are all landed. What's left to close this out: watch the
opaque-alpha fix run through the actual Studio browser UI once (verified
so far only at the HTTP level — see the caveat note above), then schedule
the first sew-out session. M0 of the DT-first migration is measured (see
the satin/fill classifier item
above) — corpus leg pending a local run. **M1 (`ShapeField` hoist) is
already merged** (`bc1e59e`, `digitizer_core/shapefield.py` +
`tests/test_shapefield.py` + `tests/test_shapefield_byte_identical.py`, all
present on `origin/main`) — pure infrastructure behind
`cfg.extra["shapefield"]`, off by default, duplicating
`stage6_satin._rasterize`'s rasterization number-for-number rather than
reimplementing it, so the byte-identity test is load-bearing, not
decorative. M2/M3 (the actual classifier change this hoist sets up,
corpus-gated) have not started; a separate, zero-engine-change measurement
pass (open PR #19, `classifier-lens`) instrumented the stage-0 router and
concluded the current thresholds should be left alone, not yet merged.
One more photo-plan technique row sits in an open PR, not yet merged:
streamline (#20) — meander (#23) landed.

---

### 2. Font library & lettering

The 68-font pre-digitized satin library, browser UI, EMBF binary format, the
add-font QC/tier pipeline, and Text mode. Expandable — but every addition is
gated by the license rule below (Kent: don't risk copyright infringement if
this ever sells).

**Status:** Implemented (library/UI/format itself) — license remediation
**done 2026-08-04** (audit items 1–10 + 12; see the cross-cutting item
above), with the lawyer consult (item 11) as the one remaining compliance
gate.

**Confidence:**
- Library/tech: **High.** `src/fontbin.js` (EMBF codec), `manifest.json` +
  55 `.embf` files (72 → 68 after the audit pulls → 55 after the 2026-08-04
  ShareAlike removal), lazy loading,
  `FontBrowser.svelte`/credits UI, and the QC/tier pipeline
  (`tools/qc-font.mjs`, `tools/build-embf.mjs`, `tools/font-license.mjs`,
  `tools/patch-embf-licenses.mjs`) all exist and pass the engine suite.
- License compliance: **High — the open legal question was resolved by
  removal (Kent's call, 2026-08-04).** All 13 ShareAlike fonts pulled
  (audit §9); the remaining 55 are 52 OFL-1.1 + 1 CC-BY-4.0 + 2 CC0, zero
  ShareAlike. Full license texts ship three ways (sidecar file, served
  `/fonts/<key>.LICENSE.txt`, embedded in each binary), attributions are
  complete notices, guard tests pin it. The item-11 lawyer consult is now
  OPTIONAL — kept as the restore path for the 13
  (`docs/lawyer-brief-cc-by-sa-2026-08-04.md`), no longer launch-gating.

**Open issues:** the item-11 consult (above); the `satin-fonts.js` legacy
residual (audit §7). On the tech side: the font-editing round deferred
condensed/expanded width and mixed per-letter size (both risk uneven satin
distortion) — minor, not blocking.

**Next step:** Kent books the lawyer consult (send
`docs/lawyer-brief-cc-by-sa-2026-08-04.md` as-is); font-library expansion is
unblocked otherwise, with the add-font skill's compliance note now backed by
guard tests. Alternatively, open PR #16 (pending review — see the
cross-cutting font-license section above) would resolve this a different
way, by pulling all 13 remaining ShareAlike fonts instead of waiting on the
consult; stacked PR #17 (pending review) closes the related legacy-registry
residual. Neither is merged, so the 68-font count and the open consult gate
above remain what's actually shipping.

---

### 3. Studio app / guided wizard

The Svelte guided flow (garment → content → review → download), saved
projects, the Layers panel entry point — plus fabric & garment presets
(`src/fabrics.js`, `src/garments.js`), folded in here since they're wizard
inputs, not a separate product surface.

**Status:** Implemented. 8 studio slices built and merged, plus two later
feature commits (the auto-digitize review flow, the Layers panel). README
calls it "the primary product."

**Confidence: Medium** for wizard navigability/UI quality. **331/331** Studio
(vitest) tests pass (verified this session), and nearly every
`app/src/lib/*.js` logic module has a paired spec — but that coverage is
still mostly **logic-only**, not UI-behavior. One gap this used to widen is
closed: `app/e2e/wizard-smoke.spec.js` (merged, PR #6) now drives the full
garment→content→review→download path in a real browser and asserts real
cross-step state (garment selection, live stitch count, the review-step
recap reflecting what was actually picked, a real DST file landing on
disk) — re-run this session, **1/1 passing**. It stays a single happy path
(one garment type, text content, one export format) — not broad
component/interaction coverage — so this is left at Medium rather than
bumped a full tier; Kent can override if a single passing e2e path is
enough evidence for him. The previously-documented rotation/hoop-fit bug is
**FIXED** (`8e668d3`, merged): text auto-fit's scale/clamp now computes
against the exact rotated-bbox footprint instead of the unrotated glyph
bbox, with two regression tests reproducing the original overflow on a
non-square hoop across several non-180° angles (267/267 engine, 321/321 app
at that commit).

**Fabric-preset accuracy: pending sew-out** — kept as an explicit separate
note, not blended into the wizard's own score. README says it outright:
"Presets are starting points — stitch a test on your machine and tell me if
a fabric needs tuning." No physical validation has happened yet.

**Next step:** broaden `wizard-smoke.spec.js` beyond its one happy path —
other garment types, the image-content path (not just text), multiple
export formats — before navigability confidence moves past Medium. Open PR
#21 (pending review, stacked on the now-merged PR #10) is relevant to area 5
below, not this one, but adds a second live e2e spec (stale-edit recovery)
worth folding into the same broadening pass once it lands.

---

### 4. Export formats

DST, EXP, PES, SVG, and the PDF worksheet — both the browser JS encoders and
the Python digitizer service's `/export` route (pyembroidery-based).

**Status:** Implemented, all five formats, both paths.

**Confidence — varies by format, not one score:**
- **DST:** split by path. Browser DST is Medium as Studio's sewn-and-shipping
  default; Low if treated as verified-correct-orientation in the abstract —
  see the cross-cutting DST item, this is the same bug. Python `/export` DST
  (pyembroidery, standard-conformant) is Medium-High by spec, not yet
  sew-verified itself.
- **EXP: Medium.** README: "Solid, standard support, incl. trim control."
  4 targeted tests, no known open issues.
- **PES: Medium-Low**, matching README's own "best-effort — reverse-
  engineered" framing. Thinnest coverage of the stitch formats (3 tests).
- **SVG: Medium** — lower stakes (vector proof, not a stitch file), but thin
  coverage (1 test).
- **PDF worksheet: Medium** — was "no dedicated test file exists at all";
  now has one. `app/src/lib/pdfsheet.spec.js` (merged, PR #4) drives
  `src/pdfsheet.js` directly and covers title, the placement line (and its
  omission), the stats block, the thread sequence (incl. its no-name
  fallback), the stitch-sim image embed, `garmentBox` forwarding,
  multi-page pagination, and the zero-design/no-throw path (5 tests, part
  of the 331/331 vitest total verified this session, no flakiness observed
  on a plain default-parallel run). Real gap that remains: assertions are
  on the FakeJsPDF call sequence, not a rendered/pixel-level check of the
  actual PDF output.

**Open issues:** DST axis bug (cross-cutting, see above). PES/EXP now have
independent cross-validation findings — see the DST cross-cutting section
above — but they live in **open PR #18, not yet merged**: PES reportedly
decodes as garbage in standard readers (byte-mis-framed stitch stream), and
EXP reportedly aborts at the first trim in pyembroidery-convention readers
(non-standard 2-byte trim record). Until #18 merges, the confidence bullets
above are the ones actually in effect; the PR's own suggested downgrades
(PES Medium-Low → Low, EXP Medium → Medium-Low) are **not applied here**,
consistent with the doc's own note that MASTER_SCOPE was churning across
parallel lanes when the PR was opened.

**Next step:** same as the DST cross-cutting item — a third-party sew-out/
read settles the axis question, which is the one thing actually blocking a
clean DST confidence rating. Separately, review and merge PR #18 (or verify
its findings independently) before applying its suggested PES/EXP downgrades
here.

---

### 5. Stitch-out review & manual editing tools

The professional-quality refinement toolkit: can a user take auto-digitized
output and manually fix/improve it — delete, recolor, re-tier, adjust angle,
reorder layers — distinct from whether auto-digitizing itself is good
(area 1) or whether the wizard is easy to navigate (area 3).

**Status:** Implemented, narrow scope. Landed 2026-08-02 in two same-day
commits: the review-screen shape-edit plumbing (`c390e9f`) and the Studio
Layers panel UI (`ce8f021`).

**Confidence: High** — unusually, both the wire-protocol plumbing *and* the
user-facing UI are confirmed with matching evidence (not "backend exists, no
UI" or vice versa). The service round-trips `deleted_shape_ids` and
per-shape `shape_overrides` (recolor, tier, fill angle, border, sew layer);
`DigitizePanel.svelte`'s Layers list exposes recolor, tier, fill-angle,
reorder, delete/restore. The landing commit reports live-browser
measurements against the real service confirming all of the above plus
undo/redo and offline-queued edits.

Since this section was last written, the Layers panel gained one more
control of this same kind — restoring a `BACKGROUND_ENCLOSED`-excluded
shape (merged, PR #10) — described under area 1 above rather than
duplicated here, per this doc's own "documented once" convention for
cross-cutting features.

**Open issues (self-flagged in the landing commit, not undocumented gaps):**
- No true shape-recognition re-editing — no reshaping/redrawing outlines,
  no splitting/merging shapes, no manual point editing.
- Per-shape border override is engine-supported but has no UI control.
- Backstitch/underlay adjustment is entirely engine-internal, not exposed
  to the user at all.
- Within-layer sew order is shown, not controllable — it's the machine's
  nearest-neighbor pathing.
- The "stale/unmatched edit" recovery flow was never driven in a live
  browser.

**Next step:** browser-drive the untested stale-edit-recovery flow, and
decide whether per-shape border override deserves a Layers-panel control —
both explicitly flagged as gaps in the landing commit itself. **Open PR #21
(pending review, stacked on the now-merged PR #10) claims to close both**:
a live Playwright spec that spawns the real digitizer service and drives
digitize → edit → id-churn → the stale-edit notice → recovery with no
mocks, plus a Border select per Layers row wired through the same
`setOverride`/"Apply layer changes" path the tier select uses. Not merged —
treat as reported-not-verified until it lands, same posture as the other
open-PR notes in this document. **Open PR #26** (pending review, stacked on
#21) claims the fifth and last self-flagged gap on this list too: a
`sew_order` shape-override key following the same override pattern as
`border`/`tier`, a second ▲/▼ control per Layers row for shapes sharing one
color, and `stage7_sequence.py`'s nearest-neighbor picker forcing pinned
shapes into their slot while unpinned shapes keep competing exactly as
before. Also not merged — same reported-not-verified posture.

---

## How this document works

- **Two independent axes per area:** Status (is it built) and Confidence (do
  we trust it) — kept separate on purpose. Something can be fully
  Implemented and still Low confidence (the DST codec is the standing
  example), or In progress and High confidence (on track, just not done).
- **Confidence authority is hybrid.** Claude proposes a score with cited
  evidence (tests, docs, known defects); Kent has override authority.
  Anything whose real confidence depends on physical machine verification —
  fabric presets, real stitch quality, the DST orientation question — gets
  an explicit **pending sew-out** flag instead of a guessed score, because
  no sew-out testing has happened on this project yet.
- **This document is the source of truth for current status.**
  COOKBOOK.md's former "Known limitations" section pointed here instead of
  maintaining a parallel list, to avoid the two drifting out of sync.
- **Updates:** proactively after PR-sized work changes an area's status or
  confidence, plus on demand via `/update-master-scope` for a checkpoint
  whenever Kent wants a fresh read.
