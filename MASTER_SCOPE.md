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

**Last updated:** 2026-08-05 — corpus laws 23 and 26 landed for real this
pass, closing out the reverted attempt this doc has carried since the last
entry (see that entry's UPDATE note, area 1, for the historical account of
why the first attempt was backed out). Law 26: `fabrics.py`'s `pique_knit`/
`jersey_tee` `fill_underlay` moves `edge_lattice` -> `edge_run`, dropping
the crosshatch pass a fill doesn't need (corpus: 7/507 fills carry a
lattice underlay). Law 23: satin's own zigzag underlay pitch is no longer
implicitly shared with fill's — a new `machine.SATIN_ZIGZAG_PITCH_MM = 1.45`
constant (fill's lattice underlay keeps reading the old `UNDERLAY_ZIGZAG_MM
= 2.0`), wired into `stage6_satin.py`'s `_stroke_underlay()`, plus that
function's rail-narrowing factor `0.3 -> 0.09` (each zigzag leg now spans
0.82x the column width, corpus-measured, not the old 0.4x). The blocker the
first attempt hit — landing either law moves `machine.py`'s coverage-budget
thresholds' own self-fit ground truth — is resolved by recalibrating
`COVERAGE_WARN_UNITS`'s *methodology*, not its value: the old derivation
comment said "checked against what our own output actually produces" (self-
fit, circular); the new one re-derives 2.5 two ways that don't depend on
prior engine output — law 27's own prose figure for a safe classic stack,
cross-checked against law 28's underlay-cost figure (~0.1-0.2 units) computed
from the corrected engine's real underlay geometry (fill's generic zigzag
underlay prices at 0.4mm-thread/2.0mm-pitch = 0.208 units; satin's new
pitch at 0.4/1.45 = 0.283) — a classic stack lands at 2.21-2.28 units either
way, comfortably under 2.5 with headroom, not against it. The number did not
move; only its provenance did. `COVERAGE_BLOCK_UNITS` (3.5) is untouched on
purpose — the playbook tags it sew-out-gated, not desk-safe, still pending
Kent's physical stacked-fill-ladder test (`EMBBOT_SEWOUT_CARD.dst` block 2).
`STITCHES_CUTAWAY_MIN` (25,000) is also untouched — externally sourced
(OESD), independent of engine output, correct as-is — but the fixture that
exercises it (`test_a_heavy_design_prescribes_cutaway_stabilizer`, a solid
square) had to grow from 160 mm (26.7k stitches) to 180 mm (28.4k) because
law 26 alone drops the old fixture to 22.5k, legitimately under the
threshold now that the fill underlay is lighter; the STOP CONDITION for
leaving the threshold itself alone was never hit — 180 mm is still an
ordinary garment-sized design, not a contrived one. Sample measurements
(`whitebg` @ `left_chest`, pique_knit): `coverage_p50` 1.19 -> 1.00,
`stitch_count` 2469 -> 2165. Landing both laws moved geometry in more places
than the two explicitly-scoped preflight assertions — regenerated
deliberately, not defensively, and each is commented with why: `test_
preflight.py`'s `coverage_p50` and `link_thread_mm` goldens (travel-graph
routing shifted, 109.0 -> 87.8 mm on the fixture logo);
`test_flat_lane_byte_identical.py`'s `flat_lane_golden.json` (regenerated via
its own `tools/capture_flat_lane_golden.py`, all 4 fixtures move, all use
the default pique_knit fabric); `test_pushcomp.py`'s `GOLDEN_FLAG_OFF` table
(all 4 entries move — two via law 26's fabric change, two via law 23's
fabric-independent width gate, spelled out entry-by-entry in that table's
own comment); `test_stage2_photo_segment.py` needed no changes of its own,
it reuses `test_flat_lane_byte_identical.py`'s golden. One more collision
neither this doc's prior entry nor the task brief anticipated: `test_
chaining.py`'s two "bend into cover" tests pinned a specific band polygon
that landed on a knife-edge of the (inherently discrete, budget-gated) link-
routing search once law 26 thinned `pique_knit`'s underlay — non-monotonic
under small perturbations either direction, confirmed by sweeping dozens of
band placements post-landing rather than hand-fitting one value; the chosen
replacement band was checked robust to +-0.4 mm on both edges (47/49
perturbations still route as a bend). Full suite `cd digitizer && .venv/
bin/python -m pytest tests/ -q`, run to completion in the foreground:
**771 passed, 3 skipped, 0 failed** (794s) — every one of the 3 known
container-environment goldens this doc has cited every pass since
2026-08-03 (`test_flat_lane_byte_identical[logo_alpha.png]`, `test_pushcomp
[logo_whitebg.png-towel]`, `test_stage2_photo_segment[logo_alpha.png]`)
happened to pass clean in this environment on this run too — allowed to
fail per this pass's own task brief, not required to, and their passing
here isn't claimed as a fix, just an honest report of what the run showed;
engine `node --test` **272/272** and Studio `npx vitest run` **381/381** (26 files)
both re-run this pass as a sanity check even though neither `src/` nor
`app/` changed a byte — confirmed by `git status` before running. This work
was done in an isolated worktree per its own task brief and is committed
locally only — not pushed, no PR opened, merge is the coordinator's call.

**Same-day follow-up, still 2026-08-05: an independent stitch-geometry audit
caught a real peak/hotspot regression the above validation missed.** The
landing above validated `whitebg`/synthetic-square fixtures at p50/typical
behaviour only, never `logo_alpha.png`'s peak/hotspot behaviour — and
`logo_alpha` carries `Sf5200f3f`, a multi-stroke glyph classified satin on
its per-shape MEAN width (~5.0mm, right at `SATIN_MAX_WIDTH_MM`) while one
skeleton stroke's own LOCAL corridor runs 0.33-10.33mm, well past where the
corpus ever validated a satin zigzag underlay at all. `DENSITY_STACKED`
flipped `warn` -> `block` there (`coverage_max` 13.11 -> 16.69). Root cause
confirmed by isolation: the satin crosses themselves already self-overlap
on this shape in the UNMODIFIED engine (`coverage_max` 13.11 pre-law-23
too, a real, separate, pre-existing defect this fix does not touch), sitting
just under `_COVERAGE_MIN_PATCH_MM2`'s 25mm2 connected-patch gate; law 23's
denser/wider zigzag underlay supplied just enough extra thread to bridge
that pre-existing near-miss over the gate. Fix: `stage6_satin.py::
_stroke_underlay` now skips the zigzag pass entirely for a stroke whose
local width anywhere exceeds `SATIN_MAX_WIDTH_MM` (falling back to the
center-run walk only) — the corpus gives no guidance for that regime under
either the old or the new numbers, so omitting the guess beats
extrapolating either one. Reuses `SATIN_MAX_WIDTH_MM`, the same ceiling
`SPLIT_SATIN_ABOVE_MM` already gates on, not a new constant. Regression-
pinned (`test_a_wide_oversize_satin_stroke_does_not_block_on_underlay_
glue`, `test_preflight.py`); `flat_lane_golden.json` regenerated a second
time (`logo_alpha.png`/`photo/enthusiast_logo.png` entries move — both
carry oversize local strokes). Full suite re-run to completion in the
foreground: **772 passed, 3 skipped, 0 failed** (811s), 0 failures this
time (the 3 known-flaky goldens passed clean again). The pre-existing satin
self-overlap defect on `Sf5200f3f` itself (peak 13.11, unrelated to either
law) is NOT fixed by this pass and remains open — currently invisible to
`DENSITY_STACKED` because it never reaches the connected-patch gate alone,
which is arguably its own gap in the coverage instrument's peak-detection
sensitivity, flagged here rather than chased further.

**Also flagged by the same audit, lower priority, not yet acted on:**
`pique_knit`/`jersey_tee`'s new `edge_run` fill underlay (this pass, above)
leaves large fill interiors up to 13mm from the nearest underlay stitch (vs
1.6-1.8mm under the old `edge_lattice`), and `jersey_tee`'s own preset note
("needs solid underlay") arguably now reads in tension with `edge_run`;
`center_run` might be more defensible per the corpus data than `edge_run`
for that one preset specifically. Not investigated this pass — a candidate
for a focused follow-up, not a blocker on what shipped here.

**Follow-up correction, 2026-08-05 (same day): the whole-stroke skip above
is the final state — a same-day per-station narrowing attempt was tried and
then dropped, not shipped.** An independent audit briefly proposed
narrowing the skip from per-stroke to per-station, reasoning that a
whole-stroke skip could over-silence a large organic photo-tier shape
(`testdata/photo/drone_render.png`) that was mostly ordinary-width with
only a small oversize fraction. That narrowing was implemented, then
reverted before landing: a separate, independent verification (real
`run_preflight` calls, not either side's own claims) found PR #60
(`satin-classifier-organic-shapes`, `digitizer_core.stage6_satin.
is_satin_candidate`'s `design_class`-scoped DT check) already resolves
`drone_render.png` completely at the classification stage — with laws
23/26 and PR #60 both applied, `drone_render.png @ 80mm/left_chest` reads
byte-identical preflight numbers (`coverage_max` 5.26, `over_warn_mm2`
68.0, severity `warn`) whether the per-station narrowing is applied on top
or not. The narrowing's entire reason for existing was moot before it ever
needed to ship, so it was dropped in favor of the simpler, already-verified
whole-stroke skip. `logo_alpha.png`'s own fix is unaffected either way —
`Sf5200f3f` is `design_class="flat"`, on which PR #60's fix is a
byte-for-byte no-op, so laws 23/26 plus the whole-stroke skip remain fully
necessary and are not superseded by anything on `main`. `drone_render.png`,
`region_blobs.png` and `summit_badge.png` are consequently out of scope
for this entry entirely — not fixed here and not flagged here as gaps,
since PR #60 already owns them at the classifier level (see that entry
below for its own numbers). Full suite re-run to completion in the
foreground: **828 passed, 3 skipped, 0 failed** (708s).

Prior update below, 2026-08-05, still earlier the same day — the
boundary-editor slice landed: area 5's
last self-flagged gap ("no reshaping/redrawing outlines... no manual point
editing") is now half-closed. A new `boundary_override` shape_overrides key
(contract v1.4) lets a review-screen edit replace a shape's exterior ring
with a hand-drawn polygon, following the exact override pattern the rest of
this area already uses: service-side validation (`digitizer_service/
app.py`, point count 3..500, finite numbers, shell validity, and the
sewability floor — a fast 400 on the common mistakes), core-side defense in
depth plus hole-containment checking (`digitizer_core/regions.py::
apply_shape_edits` — the one check that can only run here, since it alone
sees the shape's own existing holes; a rejected edit is always a clean
`ValueError`, never a crash or silently repaired geometry), `match_shape_
ids` carry-forward alongside the other five override keys, and a Studio
Layers-panel "Edit shape boundary" (✎) control (`DigitizePanel.svelte`) — a
small SVG editor with draggable vertex handles, click-a-midpoint-to-add,
right-click/Delete-to-remove, full keyboard equivalents (arrow-key nudge,
Enter/Space to add), and live client-side validation (`digitizer.js`'s
`boundaryIssues`, mirroring the server's own checks) that disables Save
before an invalid edit ever reaches the wire. On save the new polygon rides
through the SAME `setOverride` -> `shapeOverrides` -> "Apply layer changes"
flow every other override in this area already uses — no new save/apply
path invented. Verified live against the real service via Playwright MCP
(a full click-through including the invalid self-intersecting-shape
rejection path, screenshotted) and a new Playwright e2e spec
(`app/e2e/digitize-boundary-edit.spec.js`: drag a vertex, save, apply,
confirm the design actually reshapes and resews, Reset to auto undoes it).
Splitting/merging shapes — the other half of the original shape-
recognition gap — is explicitly untouched this pass; see area 5 below for
the honest scope line. Full suite re-run this pass: digitizer **708 passed
/ 3 failed / 3 skipped** (`digitizer/` commit `298eae0`) — the 3 failures
are the same long-standing container-environment golden mismatches this
doc has cited every pass since 2026-08-03
(`test_flat_lane_byte_identical[logo_alpha.png]`,
`test_pushcomp[logo_whitebg.png-towel]`,
`test_stage2_photo_segment[logo_alpha.png]`), not new regressions; Studio
`npx vitest run` **354/354** (25 files, up from 348 — 8 new unit tests for
the boundary-edit contract plus `outlineFull`/`boundaryIssues` coverage),
`app/` commit `ac11163`. Engine `node --test` untouched by this slice, not
re-run.

Prior update below, 2026-08-04, latest still — three more PRs landed on top of
the prior entry's CI + photo-plan-closeout wave, closing the last open
photo-plan row and fixing a real region-fragmentation defect on busy gradient
art. **PR #43** (`background-removal-rembg`, merged `7d07aea`) wires
`remove_background_seam` for real: it shells out to an isolated venv
(`digitizer/rembg_isolated/`, not committed — see its own README) running
`digitizer_core/rembg_worker.py` as a standalone subprocess, sidestepping the
`numba`-vs-`numpy==2.5.1` conflict the prior pass's probe doc flagged rather
than touching the shared venv's pin. Gated behind a new
`cfg.photo_prep_background_removal` flag layered on top of the existing
`photo_prep` gate; missing venv, worker crash, timeout, or bad output all
degrade to the documented no-op (`PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE`),
mirroring the YuNet face-priors fallback pattern. Verified end-to-end in that
PR's own worktree: a real isolated venv built from
`digitizer/rembg_isolated/requirements.txt`, a real cutout on
`skimage.data.astronaut()` through the actual subprocess, and the graceful
fallback in both its environment and runtime failure forms (`tests/
test_background_removal.py`, 350 lines). **This closes photo plan row 1, the
last row this doc was still tracking as open — rows 0–15 are now all built.**
**PR #44** (`delete-standalone-html`, merged `ad4bf52`) deleted
`EMB-Bot-standalone.html` (6,339 lines) and updated every live doc that
pointed at it (COOKBOOK.md, README.md, this file, `.claude/skills/
run-emb-bot/SKILL.md`, `.claude/agents/emb-bot-reviewer.md`); `tools/
bundle.mjs` is fully dead code now, left in place but not wired to anything.
Re-checked this pass: no live doc still references the file — the only
remaining mentions are in dated planning/spec/audit docs
(`docs/superpowers/plans/2026-07-22-emb-bot.md`,
`docs/superpowers/plans/2026-07-27-font-editing-abilities.md`,
`docs/superpowers/specs/2026-07-27-font-library-expansion-design.md`,
`docs/font-license-audit-2026-07-31.md`) describing the state at the time
they were written, which is the same "kept as written for the historical
record" convention `docs/font-license-audit-2026-07-31.md` itself already
uses elsewhere — not a gap. **PR #45** (`gradient-fragmentation-fix`, merged
`fc40d53`, 4 commits) fixes a real region-COUNT fragmentation defect distinct
from the angle-fragmentation one closed 2026-08-03 (below): busy gradient art
was fragmenting into ~10x the photo plan's own 20–80-region accept band under
plain k-means (`drone_render.png` measured ~208 final regions). Fix:
`gradient`-classified designs now dispatch through `stage2_photo_segment`
(SLIC+RAG) instead of `stage2_quantize`, same as the photo classes, plus
`MERGE_DELTAE00_THRESH` retuned `10.0` → `20.0` (with `FACE_MERGE_FACTOR`
`0.5` → `0.25` in the same commit so the face-local absolute merge tolerance
stays decoupled from the retune). Landing this exposed two more real bugs,
both fixed same-PR: `stage2_photo_segment` didn't separate
`BACKGROUND_ENCLOSED` pixels from the main population the way
`stage2_quantize` always has (measured: 0 of 3 enclosed regions survived
their own tag on `repro_gradient_white_icon.png` before the fix), and the
`PHOTO_SEGMENT_REGION_COUNT` warning was reporting thread-colour count under
a message claiming region count. A new `CLASS_OVERRIDE_TECHNIQUE_MISMATCH`
preflight guard and a `stage6_blend` follow-up (widening `blend_fill`'s
shared-angle preference to fragments whose own fit reads "radial" by chance,
an interaction the routing switch exposed) round out the 4-commit PR.
**Region-count honesty note, checked directly against the regression tests'
own docstrings rather than taken from the commit message alone
(`tests/test_stage2_photo_segment.py`):** the 20–80 accept-band claim is
validated on exactly **two** real busy fixtures, `drone_render.png` (→65
regions) and a newly-built `summit_badge.png` (→30) — not a broader corpus
sweep. That is real, independently-checked evidence, not nothing, but it is
narrower than "fixed, full stop" would imply; re-verified this pass that a
third fixture, `repro_gradient_white_icon.png` (the *angle*-fragmentation
fix's own repro case), still produces exactly 23 regions after PR #45's
routing switch — same count as before, now via SLIC+RAG instead of k-means,
which is expected (that fixture's own fragmentation was never the
region-count defect PR #45 targets) but is worth stating plainly rather than
implying the routing change uniformly shrinks region counts everywhere.
Fragment count and radial-ramp angle sharing remain non-goals of the
*angle*-fragmentation fix specifically, unchanged from the entry below.

Fresh full suite run this pass (this worktree, HEAD `fc40d53`): digitizer
`cd digitizer && .venv/bin/python -m pytest tests/ -q` — **688 passed / 3
failed / 3 skipped** — the same three long-standing container-environment
goldens this doc has cited every pass since 2026-08-03
(`test_flat_lane_byte_identical[logo_alpha.png]`,
`test_pushcomp[logo_whitebg.png-towel]`,
`test_stage2_photo_segment[logo_alpha.png]`), not new regressions; engine
`node --test` re-run this pass too — **267/267**, unaffected (no `src/`
change survived this pass — see below). Studio (`vitest`) was **not**
re-run this pass, since nothing in `app/` changed across PRs #43–45; carrying
forward the prior entry's **348/348** (25 files) rather than re-asserting an
unverified number.

**UPDATE 2026-08-05: both laws below landed for real — see the top-of-doc
entry for the corrected coverage-budget recalibration that made it possible.
The account below of the reverted attempt is kept as the historical record
of why it needed care, not as current status.**

**Two corpus-law fixes evaluated this pass and reverted, not landed —
recorded here because they touched code before being backed out, not just
considered.** `docs/corpus-laws-round3-2026-08-01.md` law 26 (fabric preset
`fill_underlay` `edge_lattice` → `edge_run` for `pique_knit`/`jersey_tee`)
and law 23 (satin structural zigzag underlay pitch/width correction) are
both tagged "desk-safe" in that doc, and the corpus evidence behind each
looks solid on its own terms. But actually applying either one and running
the suite (not just reading the doc) showed a materially bigger blast radius
than "desk-safe" implies here: `pique_knit` is the default fabric for
untagged designs and for `left_chest`, so changing its fill underlay moved
**8 of the digitizer's hard byte-identical golden assertions across three
test files** (`test_flat_lane_byte_identical.py`, `test_stage2_photo_
segment.py`, `test_pushcomp.py`) that explicitly instruct "if this test ever
goes red, the change under review is wrong — not this test," and — more
consequentially — dropped `test_preflight.py`'s measured `coverage_p50` from
1.2 to 1.0 on the benchmark logo and silenced the `STABILIZER_CUTAWAY`
finding entirely on the constructed 26.7k-stitch heavy-design case: a real
behaviour change in a customer-facing warning, not a cosmetic hash diff. Law
23's zigzag correction, even scoped to a brand-new satin-only constant to
avoid also perturbing fill's unrelated crosshatch-lattice underlay style,
still auto-applies to every satin column over `SATIN_ZIGZAG_ABOVE_MM` via
`stage6_satin`'s existing width-based zigzag-promotion rule regardless of
fabric — so it moved the same preflight coverage/stabilizer numbers again,
independently confirmed by reverting law 26 alone and re-running. Both
changes were fully reverted (verified back to the exact 3-known-failure
baseline via a clean pytest run) rather than landed with a "fix the
preflight calibration too" scope-creep, since that calibration is itself
descriptively tuned to today's shipped geometry (`machine.py`'s coverage-
budget comments: "checked against what our own output actually produces")
and re-deriving it is its own project, not a desk-safe follow-on to a fabric
tweak. Two smaller items from the same review pass — law 19's stale
interleave-hedge comment on `machine.FILL_ROW_MM` and law 40's stale
"UNMEASURED" comment on `machine.BORDER_SEAM_OFFSET_MM` — WERE comment-only
and are landed (`digitizer_core/machine.py`, `digitizer_core/
stage6_border.py`); no constant moved, verified by the same clean pytest run
before and after.

Prior update below, 2026-08-04, still earlier the same day — a large batch
landed: **CI now exists** (Kent added a stock GitHub Actions conda
workflow, first run failed on wrong Python/no environment.yml; rewritten in
**PR #37** to run this repo's real suites — engine `node --test`, Studio
`vitest`, digitizer `pytest` with the 3 known container goldens deselected —
and every PR from here on is gated on its Actions run going green before
merge, not just local suite passes). On top of that, photo plan rows 11
(FDoG detail layer), 12 (sketch tier), 14 (depth-sorted sequencing), and a
15-guard subset (preflight) landed, plus the last two step-3 dependency
gaps closed: **PR #38** shipped the zero-dep photo-prep slice (CLAHE tone +
texture kill) with a full dependency probe (`docs/photo-prep-deps-probe-
2026-08-04.md`) establishing rembg/YuNet/contrib-opencv were all installable
but not yet wired; **PR #39** applied the probe-verified opencv-contrib
swap (`opencv-contrib-python-headless` replaces plain `opencv-python-
headless` in `requirements.txt`/`pyproject.toml`, same cv2 build plus
`cv2.ximgproc`), which lights up `rolling_guidance`'s real texture-kill path
instead of its bilateral fallback — golden-safe, re-verified in a fresh
throwaway venv both before and after landing; **PR #41** wired real YuNet
face detection into the face-priors seam PR #38 had landed as a documented
no-op — `cv2.FaceDetectorYN` on the committed, sha-pinned model
(`digitizer_core/model_data/face_detection_yunet_2023mar.onnx`), true-
positive detection proven on `skimage.data.astronaut()` (a rights-safe
public-domain photo shipped inside the scikit-image wheel, not a committed
photograph), wired into the face-local merge-threshold drop, region-class
mapping, and a new `FACE_TOO_SMALL` preflight guard. **This closes the
caveat this doc has carried since the palette-k-medoids pass** — the
eyes/skin class multipliers that used to run at a flat 1.0 "until step 3's
face priors exist" now receive real face regions. An independent geometry
audit (fresh measurement from raw output, not the shipped tests' own
assertions) confirmed all of PR #41's claims and caught one real defect
before merge: `FACE_BLOCK_HOOP_MM` used a rounded 100.0mm instead of this
codebase's own literal-inch hoop convention (`src/units.js`: `inch × 25.4`,
already used by the guard's sibling `FACE_MIN_HOOP_MM`), leaving a ~1.6mm
dead band where a design that still needed a real 4×4in hoop got no
warning — fixed to 101.6mm same-PR, with a boundary regression test. A
parallel geometry audit of PR #40 (sketch tier — `fill_technique="sketch"`,
a config preset over rows 10/11 with zero new algorithms, `stage6_streamline`
gaining an additive `darkness_scale` kwarg) independently re-derived its
seed-spacing and highlight-cutoff numbers from raw emitted stitch
coordinates and bit-exact-diffed the default-kwarg path against the
pre-change parent commit across 7 scenarios — full confirmation, no defects
found. Photo plan status: **rows 0, 2–15 are now all built** (row 1,
background removal via rembg, remains the one open row — installable per
the probe doc but blocked on a `numba` vs. this repo's `numpy==2.5.1` pin;
documented as a seam, `remove_background_seam`, not attempted this pass).
Combined suite on the final composed `main` (`354f075`): engine **267/267**,
Studio **348/348** (25 files), digitizer **654 passed / 3 failed / 1
skipped** — the 3 failures are the same long-standing container-environment
goldens this doc has cited every pass since 2026-08-03. Main-branch CI run
green on all 3 jobs.

Prior update below, 2026-08-04, later still — verification pass confirming
**all 11 PRs from the prior pass's "#16–#21 pending review" list, plus #22
though #28, are now merged to `main`** (`4cf8760`, the `backstitch-
underlay-control` merge; every PR number from #16 through #28 shows a
"Merge pull request" commit in `git log origin/main`, checked directly, not
inferred from titles), rebased and re-verified once more when **two more
PRs landed on top mid-pass — #29 (wizard-smoke e2e broadened along three
axes: garment type, image-content path, export formats) and #30 (a
real-jsPDF byte/text-extraction test tier for the worksheet export,
replacing "call-sequence-only" as the PDF coverage's honest description)**.
Fresh suite run against the final tip (`8544713`): engine `node --test`
**267/267**; Studio `cd app && npx vitest run` **347/347** (25 files, up
from 24 — #30's new spec file); digitizer `.venv/bin/python -m pytest
tests/ -q` **564 passed / 3 failed** — still exactly the same three
long-standing
container-environment golden mismatches this doc has cited every pass since
2026-08-03 (`test_flat_lane_byte_identical[logo_alpha.png]`,
`test_pushcomp[logo_whitebg.png-towel]`,
`test_stage2_photo_segment[logo_alpha.png]`), not new regressions.

What actually changed in the code, verified against source rather than PR
titles: the 13-font ShareAlike pull (**PR #16**, `src/fonts/manifest.json`
recounted directly at **55** entries, license breakdown 52 OFL-1.1 + 2 CC0 +
1 CC-BY-4.0, zero ShareAlike) and its legacy-registry follow-up (**PR #17**,
`satin-fonts.js` diff-verified 21 → 14 entries) together retire the
lawyer-consult gate as launch-blocking (area 2, and the cross-cutting
font-license section below, both rewritten this pass — they'd drifted out
of sync with each other, one already describing the post-pull state and one
still describing it as an unmerged proposal); the PES/EXP pyembroidery
cross-validation (**PR #18**, `docs/pes-crossval-verdict-2026-08-04.md`) —
mis-framed PES stitch stream, EXP's fatal-on-first-trim record — is now
corroborated evidence on `main`, not a pending finding (area 4,
cross-cutting DST section); the classifier-lens measurement (**PR #19**)
confirming the shipped stage-0 four-way router's thresholds should be left
alone is merged (area 1); the streamline thread-paint tier's mono slice
(**PR #20**) and its layered multi-colour follow-up (**PR #25**) are both
merged (photo plan row 10, area 1 — both slices now built, not one); the
stale-edit e2e spec and per-shape border-override UI (**PR #21**) closed
area 5's first two self-flagged gaps; the within-layer sew-order control
(**PR #26**) closed its third; the contour bare-core shrink (**PR #27**,
confirmed directly in `digitizer_core/config.py`'s `fill_technique` comment
block — all three of the 2026-08-02 audit's defects now read "FIXED
2026-08-04", including the bare-core dot this doc previously described as
"measured, not yet shrunk") closed the one remaining defect keeping contour
fill's quality bar down (area 1); and the per-shape underlay-style override
(**PR #28**, `digitizer_service/app.py`'s `_OVERRIDE_KEYS` re-read directly:
`{thread_index, fill_angle_deg, tier, border, layer, sew_order, stitched,
underlay_style}`) closed area 5's fourth. Every "open PR #N, pending
review" callout this doc was carrying for that range is folded into its
area's prose below and removed, per this doc's own convention for landed
work (see how #9/#10/#25's/#26's/#27's own predecessors were folded rather
than kept as standing callouts). One thing this pass did NOT find any new
evidence for: physical sew-out testing — still zero, see the cross-cutting
item below, unchanged.

Prior update 2026-08-04, earlier the same day: docs refresh once PRs #8–#15
had finished merging (written mid-batch, so it undercounted at first),
touched up twice more that pass as #23 (meander tonal tier) then #22
(opaque-alpha fix + `debugviz.direction_field` restore) landed mid-refresh.
Combined suite at that point: engine 266/266, Studio 331/331 (24 files),
digitizer 507/510 (same 3 known container goldens). Substance folded in
then: the full `BACKGROUND_ENCLOSED` stack (pipeline + service contract +
Studio Layers-panel restore UI), the rotation/hoop-fit auto-fit fix
(`8e668d3`), a passing Playwright wizard-smoke e2e, and PDF-worksheet test
coverage. Prior update 2026-08-04 (font-license audit items 4–10 + 12
executed — full license texts on disk/served/embedded, complete
attributions, credits links). Prior update 2026-08-03: the gradient
angle-fragmentation fix landed that session; `BACKGROUND_ENCLOSED`'s root
cause was corrected to `stage1_prep.py`, still unresolved at that time.

---

## At a glance

| Area | Status | Confidence |
|---|---|---|
| 1. Auto-digitizing quality (image → stitches) | In progress | **Low** beyond flat spot-color art |
| 2. Font library & lettering | Implemented (library + license remediation) | High (tech) / High (compliance — resolved 2026-08-04 by removal, lawyer consult now an optional restore path) |
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

**Independent corroboration, merged 2026-08-04 (PR #18, `pes-crossval`):** a
browser-encode → pyembroidery-decode cross-validation harness
(`tools/crossval-stitch-formats.mjs` + `tools/crossval_decode.py`, pinned by
`test/crossval-stitch-formats.test.js`, part of the 267/267 engine count
above) with DST as the control case reproduces the transposition
independently (anti-transpose, rms 0.0) — the PR frames this as validating
the harness method itself, not as new information about the DST bug. The
harness's real news was about the other two encoders, previously unchecked
against an independent implementation, and is now **FIXED, not just
documented — merged 2026-08-05 (**PR #58**, `pes-exp-byte-framing-fix`):** the browser
**PES** encoder's 5-byte stitch-stream mis-framing (one extra header pad
byte plus two non-standard `0x9000` fields) is deleted and the
graphics-offset field re-derived against the standard's PEC-relative-512
baseline, its jump/trim PEC flags are no longer aliased to the same code,
and it now maps design RGB to the nearest Brother PEC chart index instead of
always falling back to sequential chart indices; the browser **EXP**
encoder's 2-byte `0x80 0x03` trim record (which aborted pyembroidery-
convention readers at the first trim) is replaced with the 4-byte Melco form
readers expect. Harness re-run: PES now decodes identity/rms 0/15 stitches
(was 354 phantom stitches, rms 234.6, transform "transpose"); EXP with a
trim now decodes the whole design incl. the second colour block (was
truncated at 11 of 15 stitches). DST is untouched and still reproduces its
documented transposition, confirming the fix didn't touch it. Full writeup
and before/after: `docs/pes-crossval-verdict-2026-08-04.md` (root-cause
memo) and this file's "Last updated" entry above (fix + re-run numbers). Both
encoders had no browser-side importer to create a migration trap, so — per
the memo's section 5 — this fix carried none of the DST codec's migration
risk and didn't need to wait on Kent's sign-off the way that fix would;
Export-formats confidence below is upgraded accordingly.

### Font license compliance gap — RESOLVED 2026-08-04 by removal

`docs/font-license-audit-2026-07-31.md` action checklist: **items 1–3 done**
(the 4 flagged fonts pulled, 72 → 68 — see the audit's §7) and **items 4–10 +
12 done** the same day (see its §8): every surviving font had its full
upstream license text on disk (`src/fonts/<key>.LICENSE.txt`), shipped
by `copy-engine.mjs` at `/fonts/<key>.LICENSE.txt`, linked per-font in the
credits dialog, AND embedded verbatim in the `.embf` binary metadata (closes
the bare-download hole); manifest attributions are complete notices
(adapter + upstream copyright + Reserved-Font-Name declarations, emails
stripped); guard tests pin all of it.

**The one-hour lawyer consult this gap used to gate on (audit item 11) is
now optional, not launch-blocking — merged 2026-08-04 (PR #16,
`sharealike-pull`):** rather than wait on the consult, Kent's call was to
pull all 13 ShareAlike fonts (11 CC-BY-SA-4.0 + 2 CC-BY-SA-2.5) from the
shipping library outright. Recounted directly from `src/fonts/manifest.json`
this pass: **55 entries**, license breakdown 52 OFL-1.1 + 2 CC0 + 1
CC-BY-4.0 — zero ShareAlike remaining, zero Reserved Font Name as a primary
name anywhere. The ready-to-send brief,
`docs/lawyer-brief-cc-by-sa-2026-08-04.md`, stays on file as the restore
path if Kent ever wants those 13 fonts back, but booking the consult is no
longer something first dollar waits on. Stacked on it, **PR #17
(`legacy-font-audit`), merged same day,** removes the same 7 pulled fonts
(the original 2 + the 5 ShareAlike) from the legacy `satin-fonts.js`
registry — diff-verified this pass at 21 → 14 entries — so `EMB-Bot.html`
carries nothing pulled either. `EMB-Bot-standalone.html` (the only place
that still embedded a pre-audit inlined copy) is **deleted, 2026-08-04,
Kent's call** — no pre-audit font list ships anywhere. Still parked for
Kent: the bluenesia permission screenshots (audit §8).

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
mono tonal (row 8), meander tonal (row 9), and now streamline thread-paint
(row 10) are all on `main` and counted below — **streamline landed in two
merged slices, both on `main` as of this pass:** the mono slice (PR #20,
Jobard-Lefer evenly-spaced streamlines traced in the row-6 direction field)
and its multi-colour layered follow-up (PR #25, decomposes a region into
3–5 chart shades via `stage6_blend`'s own shade-selection machinery and
traces one streamline set per shade, dark-to-light). Row 10 was the last
one this doc was still tracking as open; all of rows 6/8/9/10 are now
built. Row 13 (chart-restricted weighted k-medoids palette selection,
build-order step 7) landed after that pass on the `palette-kmedoids`
branch: `digitizer_core/palette.py` replaces the photo path's per-region
nearest-thread snap (`stage2_photo_segment` step 6) with a deterministic
PAM selection over the config's thread chart, ΔE00 objective, region
weight = area × class multiplier — measured on the committed `fur_ramp.png`
fixture: 8 ramp regions that nearest-snap scattered across 7 near-duplicate
spools now resolve to 5 one-family browns, max excess 2.34 ΔE00. The
eyes/skin/subject/background multipliers are wired and test-proven — **all
four classes are now real, none is a flat-1.0 placeholder**: PR #41 wired
real face priors, so a detected face's eye/skin regions receive their
documented class multipliers; the `palette-subject-background-wiring`
branch (commit `7f82511`, see the "Last updated" note above) closed the
remaining gap by threading PR #43's `remove_background_seam` mask one hop
further downstream into `stage2_photo_segment._region_classes`, so a
non-face region now classes "subject"/"background" from a REAL rembg mask
too, honestly degrading to `None`/plain-area whenever rembg didn't actually
run. Flat/gradient lanes untouched (byte-identical goldens re-verified).
Row 14 (sequencing + underlay
deltas) landed the same pass: photo-classified designs (or
`cfg.extra["photo_sequencing"]` opt-in) sew depth-sorted —
background-tagged layers first, then dark→light by thread luminance,
explicit detail-tier layers last (`stage7_sequence.depth_sort_layers`,
called from `run_stages` after `compact_layers` so stage 5's underlap
model follows the same order, and BEFORE `apply_layer_overrides`/
`sew_order` so both review-screen overrides still win) — plus the underlay
split (light-mesh fill underlay, spine-run satin underlay, tonal tiers
bare by construction; per-shape `underlay_style` still beats the class
default both ways). Flat and gradient lanes are byte-identical by
construction and by the committed goldens. TRUE instance-level depth
(subject vs. mid-ground) needs step 3's segmentation and is documented as
a seam in `depth_sort_layers`' docstring, not faked
(`tests/test_photo_sequencing.py`).

Row 11 (FDoG detail layer, `stage6_detail.py`) landed in a later pass: Kang
2007's coherent-line-drawing edges (the same machinery row 6's direction
field reimplements from) drive bean-run detail strokes over the fill,
appended last so they never merge into fill quantization; `SourcePixels.
gradient_class` was fixed the same pass (`gradient_class` gates blend
routing, a separate concern from `design_class` gating photo sequencing/
underlay — the two were composing incorrectly before). Row 12 (sketch tier,
`stage6_sketch.py`) landed this pass, closing photo plan **law 10** — the
corpus-measured target (corgi/snowman/rose: ~6 runs, 12k stitches, 1 trim)
the plan doc predicted would fall out of rows 8–11 "nearly free, a config
preset, not a new engine": `fill_technique="sketch"` reads row 10's
darkness field at half strength (`SKETCH_DARKNESS_SCALE=0.5`) via a new
additive `darkness_scale` kwarg on `stage6_streamline.streamline_fill`
(default `1.0`, bit-exact identical to every existing caller — independently
re-verified across 7 scenarios, parent commit vs. this one), and appends
row 11's detail block. Row 15 (preflight guardrails) grew a `FACE_TOO_SMALL`
guard this pass (a detected face in a design that only fits a 4×4in hoop
blocks with a size-up-to-5×7 suggestion) alongside the guards already
landed in the prior preflight pass (low px/mm, low subject/background
contrast, heavy stabilizer estimate, many color stops). **Photo plan status
as of this pass: rows 0–15 are all built** — row 1 (rembg background
removal), the last one this doc was tracking as open, closed via PR #43 (see
the "Last updated" note above for the isolated-venv mechanism; its own
follow-on noted at the time, the palette subject/background class-weight
seam, is ALSO now closed — see this file's newest "Last updated" entry at
the top, `palette-subject-background-wiring` commit `7f82511`).

**Confidence: Low** beyond flat spot-color art. Flat-logo digitizing (both
implementations) is Medium — **267/267** JS tests and **688/694** Python
tests pass (fresh run this pass at HEAD `fc40d53`; see the "Last updated"
note above — the 3 failures are the same long-standing container-environment
goldens this doc has cited every pass since 2026-08-03, not new regressions;
the 3 skips are pre-existing, not new), and the geometry is internally
consistent — independent geometry/behavior audits (fresh measurement from
raw pipeline output, not the shipped tests' own assertions) have now run
against the sketch tier and the face-priors wiring specifically, on top of
the standing per-PR verification practice. `hardening-closeout-2026-08-02.md`
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
  vs. up to 64° apart before. Fragment COUNT (still 23 on this specific
  repro fixture, `repro_gradient_white_icon.png`) and radial-ramp angle
  sharing were explicit, documented non-goals of THIS fix specifically. Full
  writeup: the plan doc's "Defect 1 update" section.

  **A separate, more severe region-COUNT fragmentation defect on busy
  gradient art — FIXED, PR #45 (`gradient-fragmentation-fix`, merged
  `fc40d53`).** Distinct from the angle defect above: plain k-means was
  fragmenting busy multi-region gradient art (`drone_render.png`) into
  ~208 final regions, ~10x the photo plan's own 20–80-region accept band.
  Fix: `gradient`-classified designs now dispatch through
  `stage2_photo_segment` (SLIC+RAG) instead of `stage2_quantize`, same as
  the photo classes, plus `MERGE_DELTAE00_THRESH` retuned `10.0` → `20.0`.
  Landing it exposed and fixed two more bugs same-PR: `stage2_photo_segment`
  wasn't separating `BACKGROUND_ENCLOSED` pixels from the main population
  the way `stage2_quantize` always has (0 of 3 enclosed regions survived
  their own tag on `repro_gradient_white_icon.png` before the fix — now
  fixed by giving `segment` the same population split `quantize` uses), and
  the `PHOTO_SEGMENT_REGION_COUNT` warning was reporting thread-colour count
  under a message claiming region count. **Validation caveat, worth stating
  plainly rather than calling this unconditionally clean:** the 20–80
  accept-band claim rests on exactly two real busy fixtures,
  `drone_render.png` (→65 regions) and a newly-built `summit_badge.png`
  (→30) — real, independently-checked evidence, but not a corpus sweep.
  Confirmed this pass that `repro_gradient_white_icon.png` (the angle-fix's
  own repro case, noted above) still lands at 23 regions after this
  routing change — an unaffected case, not a counterexample, but a reminder
  the fix's real-world coverage is two fixtures deep, not universal. See
  the "Last updated" note above for the full commit breakdown.

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
  undo control). All of this is inside the digitizer and Studio test counts
  cited in the "Last updated" note above (both grown further since).

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
- **Contour fill** — **all three of the 2026-08-02 audit's defects are now
  fixed, confirmed 2026-08-04 (PR #27, `contour-bare-core-shrink`, merged);
  it still ships off by default, but no longer because of any open defect
  in this list.** The widest-inscribed-bare-circle instrument
  (`digitizer_core/barecircle.py`) exists and *is* the `starved` gate (the
  old area-fraction gate's false alarms and blind spots both proven fixed
  in `tests/test_barecircle.py`), ring-to-ring transition chords are
  containment-tested (`_link` banks instead of stitching outside;
  0.3mm-hole regression pinned), and **the bare core itself — the item this
  doc previously described as "measured, not yet shrunk" — is shrunk**:
  `_refine_terminal_generation` bisects the last ring onto the true
  sewability floor instead of wherever the fixed spacing grid landed, and a
  finishing pass patches whatever `barecircle.widest_bare_circle` still
  calls the worst remaining bare spot with an ordinary tatami patch.
  Re-measured directly from `digitizer_core/config.py`'s `fill_technique`
  comment block this pass: discs and the dumbbell fixture went **0.863mm →
  0.067–0.13mm**; `machine.CONTOUR_BARE_CORE_MM` was recalibrated
  0.87 → 0.13 to match, and `starved_threshold_mm` re-derives to 0.33mm at
  shipped spacing (was 1.07mm). The 10-point star — a different, more
  severe failure mode (its mitred-offset annihilates most of the interior)
  — shrinks too (1.33mm → 0.441mm) but correctly stays `starved`, which is
  the right outcome for a shape this poorly suited to contour, not a
  regression to chase. One cited figure never reproduced as written across
  either pass: the star's "2.94mm bare disc" is a diameter, not a radius
  (radius ≈1.47mm; measured 1.28–1.43mm depending on reconstruction).
  Flipping the tier's own default is still explicitly Kent's call, not a
  geometry question — `fill_technique` stays `"tatami"` for byte-identical
  compatibility with the engine that has always shipped, same posture as
  every other opt-in tier here.
- **Satin/fill classifier** — the shipped rule misclassifies compact/noisy
  shapes (a serrated 20mm disc computes as "5.03mm" and gets satin-stitched
  instead of filled). The proposed DT-based replacement (`VP90`) was
  measured and **rejected 2026-08-02** at `SATIN_MAX_WIDTH_MM = 3.0`
  (`main`'s cap at the time) — it scored worse than the shipped rule there,
  and its "pure tightening, cannot get worse" safety claim was proven
  logically inverted (it can only convert true positives into false
  negatives, never the reverse, and FN is the expensive error). A later,
  unrelated, corpus-driven change moved the shipped cap to 5.0 (already on
  `main`); re-running the SAME instrument at the new cap flips the result
  (`VP90` 0/21 wrong vs. the shipped rule's 6/21) — but that alone stayed
  the same class of small-synthetic-set evidence 2026-08-02's audit already
  showed can't be trusted alone, so a wholesale swap remained blocked on the
  37-file `scratch_corpus/` run (gitignored, empty in every checkout) that
  no session has had access to (`docs/superpowers/plans/
  2026-08-04-m0-shape-lens-measurement.md`, "M0" of the DT-first migration).

  **A narrower, evidence-scoped slice of this landed instead
  (`satin-classifier-organic-shapes` branch), not a wholesale swap:**
  `is_satin_candidate` (`digitizer_core/stage6_satin.py`) gained a
  `design_class` keyword. For `"flat"` (the default, and every pre-existing
  caller that doesn't pass one) it is byte-for-byte the original rule —
  zero behaviour change, so every byte-identical golden
  (`test_flat_lane_byte_identical.py`'s 4 fixtures, all flat-classified) is
  untouched by construction, not just by re-verification. For the other
  three classes (`gradient`, `photo_subject`, `photo_scene` — where
  segmentation-derived boundary noise, not clean vector art, is what
  actually produces the misclassification) a second, independent opinion
  now runs: `_dt_regular_and_within_cap` reads the exact distance transform
  at the shape's own medial axis (`build_shape_field`, already-merged M1
  infrastructure) and ANDs two terms — `2*sigma < mu` (uniform thickness)
  and the 90th-percentile radius under the cap — exactly the spike's own
  recommended `VP90` arm, a pure tightening (only ever turns a satin call
  into a fill call, never the reverse). Both call sites that decide the
  tier (`stage7_sequence.py`'s `sequence`, `stage5_overlap.py`'s
  `_comp_axis` for the directional-pull-comp path) now thread `design_class`
  through so the two agree, preserving the existing "compensation must not
  flip a shape's tier" invariant.

  **Measured, not assumed:** this repo's own two named organic-photo
  fixtures, run through the real pipeline
  (`PipelineConfig(target_width_mm=60.0, garment_id="left_chest")`, the
  preflight `DENSITY_STACKED` repro) — before the fix, `region_blobs.png`
  **blocked** (`peak_units` 10.02, `over_block_mm2` 76.0) and
  `summit_badge.png` **warned** (`over_warn_mm2` 247.0); after, **neither
  raises the finding at all**, not just a severity step down. Confirmed
  stable across `target_width_mm` 60/80 and `garment_id` left_chest/hat_front
  (6 combinations, all clear). The specific shapes that flip: `region_blobs.
  png`'s `Sd12bfc9e`/`S94f29987` (bbox aspect ~1.08/1.09 — near-square, not a
  ribbon by any honest reading) and `summit_badge.png`'s `Sed818ef7`/
  `S00d736bf`/`S6096e7a9`, all correctly satin before the fix under
  `ribbon_width_mm` alone and correctly fill after. As a bonus check (not a
  target fixture named in this PR, but the same root cause, cross-referenced
  from the unmerged `digitizer-satin-underlay-cap-fix` branch's own
  commit messages): `drone_render.png @ 80mm/left_chest`, independently
  confirmed blocking on this exact unmodified checkout (`peak_units` 17.12,
  `over_block_mm2` 275.0 — matching that branch's own cited numbers exactly),
  also clears to no finding at all under this fix — a full resolution where
  that branch's narrower underlay-pitch mitigation only got it down to a
  reduced block.

  Full digitizer suite before/after (this exact worktree, not a cited
  number from elsewhere): **773 passed / 3 failed / 3 skipped** both before
  and after — the 3 failures are the same long-standing container-
  environment goldens this doc has cited every pass since 2026-08-03
  (`test_flat_lane_byte_identical.py[logo_alpha.png]`, `test_pushcomp.py
  [logo_whitebg.png-towel]`, `test_stage2_photo_segment.py[logo_alpha.png]`),
  present identically before this change and unrelated to it (a 1-stitch-
  count drift, not a classification difference). One REAL regression turned
  up mid-verification and was fixed in the same PR, not silently patched
  around: `test_photo_sequencing.py::test_flat_and_gradient_classes_are_
  inert_in_sequence` used a 10x10 square sitting exactly on
  `SATIN_MAX_WIDTH_MM`'s cap as its "gradient lane is inert" fixture — the
  DT check correctly reclassifies that shape for `"gradient"` now (the same
  archetype as `test_satin.py`'s `SQUARE 8x8`), so the test's OWN fixture
  was silently exercising the exact bug this PR fixes. Rewritten to use
  shapes unambiguous under both rules, isolating the sequencing-machinery
  invariant it actually exists to pin from the satin/fill call it no longer
  should assume is class-independent. New regression coverage:
  `test_satin.py` (a serrated-disc fixture matching this bullet's own
  20mm-disc example, swept at three tooth depths, `design_class="flat"`
  pinned unchanged, four letterform archetypes pinned unaffected) and
  `test_preflight.py` (`region_blobs.png`/`summit_badge.png` no longer
  raise `DENSITY_STACKED`, read from the real pipeline, not a mock).

  **What this does NOT resolve:** the DT-first migration's M2/M3 (a full
  classifier swap, corpus-gated) is untouched and still blocked on the same
  37-file `scratch_corpus/` run — this PR is deliberately narrower, scoped
  to the one slice (non-flat design classes only) where the evidence is
  strong enough to land without that corpus: zero flat-lane byte-identical
  risk by construction, a pure-tightening DT term identical to the spike's
  own vetted recommendation, and direct measurement against this repo's own
  committed fixtures rather than a synthetic population alone.
- **Fill row spacing (law 19)** — unresolved two-population finding: the
  0.20mm figure is a satin-rail artifact for one file population (refuted)
  but looks like a genuine denser pitch on 43 commissioned cap logos (still
  alive). Shipped `FILL_ROW_MM=0.40` unchanged pending sew-out.

Every claim about visual/sew quality beyond internal geometry checks is
**pending sew-out** — see the cross-cutting item above.

**Next step:** the chaining fix, the gradient angle-fragmentation fix, the
gradient region-count fragmentation fix (PR #45, above — two-fixture
validation caveat noted there), the full `BACKGROUND_ENCLOSED` stack
(including the opaque-alpha fix, PR #22), and the contour bare-core shrink
(PR #27) are all landed. What's left to close this out: watch the
opaque-alpha fix run through the actual Studio browser UI once (verified so
far only at the HTTP level — see the caveat note above), then schedule the
first sew-out session. M0 of the DT-first
migration is measured (see the satin/fill classifier item above) — corpus
leg still pending a local run (`scratch_corpus/` is gitignored and
confirmed empty in this checkout). **M1 (`ShapeField` hoist) is already
merged** (`bc1e59e`, `digitizer_core/shapefield.py` +
`tests/test_shapefield.py` + `tests/test_shapefield_byte_identical.py`, all
present on `origin/main`) — pure infrastructure behind
`cfg.extra["shapefield"]`, off by default, duplicating
`stage6_satin._rasterize`'s rasterization number-for-number rather than
reimplementing it, so the byte-identity test is load-bearing, not
decorative. M2/M3 (the actual classifier change this hoist sets up,
corpus-gated) have not started. A separate, zero-engine-change measurement
pass — **merged 2026-08-04, PR #19, `classifier-lens`** — instrumented
`stage0_classify.py`'s four-way router (`flat`/`gradient`/`photo_subject`/
`photo_scene`, a different classifier from the satin-vs-fill one M0/M1
target) and concluded no threshold move is needed: 12/12 fixtures agree
with adjudicated truth, and every ±50% sweep of the 7 documented constants
only creates misroutes, never fixes one (`docs/classifier-lens-2026-08-04.md`).
All four photo-plan technique rows queued as of the prior pass (direction
field row 6, scan-line row 8, meander row 9, streamline row 10 in both its
mono and layered slices) are now merged — none remain open. Since then,
rows 11 (FDoG detail), 12 (sketch tier), 13 (palette), 14 (depth sequencing),
a 15 subset (preflight guards), and the face-priors half of row 2 (YuNet)
have all landed too, and **row 1 (rembg background removal), the row this
doc tracked longest as open, closed via PR #43** — exactly the
isolated-subprocess-harness path this paragraph used to propose as the
natural next step: a throwaway venv (`digitizer/rembg_isolated/`, not
committed) pinned to a compatible numpy, invoked as a subprocess from the
main pipeline, sidestepping the `numba`-vs-`numpy==2.5.1` conflict rather
than touching the shared venv's pin. **All 16 photo-plan rows (0–15) are now
built.** The palette subject/background class-weight seam this closure did
NOT itself resolve is noted above, where it's discussed — and is now ALSO
closed, per this file's newest "Last updated" entry. CI now gates
every merge (`.github/workflows/python-package-conda.yml`, PR #37) — three
jobs (engine/studio/digitizer), the digitizer job deselecting the same 3
known container goldens this doc has always excluded from its own counts.

---

### 2. Font library & lettering

The 55-font pre-digitized satin library, browser UI, EMBF binary format, the
add-font QC/tier pipeline, and Text mode. Expandable — but every addition is
gated by the license rule below (Kent: don't risk copyright infringement if
this ever sells).

**Status:** Implemented (library/UI/format itself) — license remediation
**resolved 2026-08-04** (audit items 1–10 + 12, plus items 1–3's pulls
followed by the full 13-font ShareAlike removal, PR #16; see the
cross-cutting item above). The item-11 lawyer consult is no longer a
launch gate — it's an optional restore path now.

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

**Open issues:** the item-11 consult is optional now, not blocking (above).
`EMB-Bot-standalone.html` (which embedded a pre-audit inlined font registry)
is **deleted, 2026-08-04, Kent's call** — the live `satin-fonts.js` residual
was already closed the same day (audit §10), so no pre-audit font list
ships anywhere now. On
the tech side: the font-editing round deferred condensed/expanded width and
mixed per-letter size (both risk uneven satin distortion) — minor, not
blocking.

**Next step:** font-library expansion is unblocked — the license gate is
resolved by removal (PR #16 + #17, both merged), and the add-font skill's
compliance note is backed by guard tests. Booking the lawyer consult (send
`docs/lawyer-brief-cc-by-sa-2026-08-04.md` as-is) is now purely optional,
Kent's call, only relevant if he wants the 13 pulled ShareAlike fonts back.

---

### 3. Studio app / guided wizard

The Svelte guided flow (garment → content → review → download), saved
projects, the Layers panel entry point — plus fabric & garment presets
(`src/fabrics.js`, `src/garments.js`), folded in here since they're wizard
inputs, not a separate product surface.

**Status:** Implemented. 8 studio slices built and merged, plus two later
feature commits (the auto-digitize review flow, the Layers panel). README
calls it "the primary product."

**Confidence: Medium**, with the one gap that was holding it there now
closed. **347/347** Studio (vitest) tests pass (fresh run this session, 25
files), and nearly every `app/src/lib/*.js` logic module has a paired spec
— that coverage is still mostly **logic-only**, not UI-behavior, but the
live-browser e2e side grew real breadth this pass: `app/e2e/wizard-smoke
.spec.js` (merged, PR #6) drives the full garment→content→review→download
path in a real browser and asserts real cross-step state, and the
broadening this doc used to list as the open next step — **merged, PR #29**
— covers all three named axes: two more garment types (Hat Front, Full
Back, each confirmed the review recap reflects the actual pick), the
image-content path (`ImagePanel`'s client-side canvas flatten, previously
untested — confirms the review step's image branch and a real download),
and two more export formats beyond DST (PES verified by its `#PES0001`
magic header, EXP by real stitch-record byte size, plus the PDF worksheet
as a fourth format via a distinct code path). A second live e2e spec exists
alongside it — `app/e2e/digitize-stale-edits.spec.js` (merged, PR #21) —
covering the stale-edit-recovery path; see area 5 below, since that's the
gap it was built to close. The previously-documented rotation/hoop-fit bug
is **FIXED** (`8e668d3`, merged): text auto-fit's scale/clamp now computes
against the exact rotated-bbox footprint instead of the unrotated glyph
bbox, with two regression tests reproducing the original overflow on a
non-square hoop across several non-180° angles (267/267 engine, 321/321 app
at that historical commit — not today's totals, which have since grown
further).

**Fabric-preset accuracy: pending sew-out** — kept as an explicit separate
note, not blended into the wizard's own score. README says it outright:
"Presets are starting points — stitch a test on your machine and tell me if
a fabric needs tuning." No physical validation has happened yet.

**Next step:** with the three-axis e2e broadening landed, the wizard-flow
gap this doc tracked longest is closed; whether that alone earns a bump to
High or Medium stays right pending real UI-behavior (not just logic) specs
is Kent's call, not this pass's to decide unilaterally — left at Medium
here. Fabric-preset accuracy remains sew-out-gated, unchanged.

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
cross-validation, not just pyembroidery agreement.

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

**Open issues:** of the five gaps the landing commit self-flagged, **four are
now closed** (all merged 2026-08-04, all confirmed against source this
pass — `digitizer_service/app.py`'s `_OVERRIDE_KEYS` now reads
`{thread_index, fill_angle_deg, tier, border, layer, sew_order, stitched,
underlay_style}`):
- ~~Per-shape border override is engine-supported but has no UI
  control.~~ **Closed, PR #21** — a Border select per Layers row.
- ~~The "stale/unmatched edit" recovery flow was never driven in a live
  browser.~~ **Closed, PR #21** — `app/e2e/digitize-stale-edits.spec.js`
  drives the real digitizer service through the real `DigitizePanel` in a
  real browser (Playwright), forces an edit stale via a width change, and
  asserts the unmatched-edit notice, clear, and re-apply all work.
- ~~Within-layer sew order is shown, not controllable.~~ **Closed, PR
  #26** — a `sew_order` shape-override key plus a second ▲/▼ control per
  Layers row for shapes sharing one color layer.
- ~~Backstitch/underlay adjustment is entirely engine-internal.~~
  **Closed, PR #28** — the fill/contour underlay-style knob
  (`PipelineConfig.underlay_style`, seven named styles) is now a per-shape
  override, following the border/tier/fill_angle_deg pattern exactly:
  validated at the service, applied in `regions.apply_shape_edits`, carried
  across re-digitize via `match_shape_ids`, resolved per-shape in
  `stage7_sequence.sequence` ahead of both the tatami and contour emitters,
  and a Layers-panel dropdown next to the fill-angle control (shown only
  when a shape's tier is "fill", since satin ignores it). Deliberately does
  NOT touch satin's own underlay (`fabric.satin_underlay`) — a materially
  narrower, effectively-binary knob (spine run, or zigzag above
  `machine.SATIN_ZIGZAG_ABOVE_MM`) versus fill's seven styles, so it stays
  engine-internal on purpose. Backed by Python tests asserting the override
  actually changes emitted underlay stitch geometry (not just a config
  round-trip) and Studio vitest coverage of the wire contract, but — unlike
  the border control it was modeled on, which PR #21's e2e spec now drives
  live — this one has no live-browser coverage yet: the Layers-panel
  dropdown itself has no automated coverage (no svelte-component test
  harness exists in this repo yet, matching tier/border/fill-angle's own
  testing gap).

**Boundary reshaping — CLOSED 2026-08-05** (worktree `agent-
a28de220d2af7ede5`, commits `298eae0` digitizer / `ac11163` studio): the
"no reshaping/redrawing outlines... no manual point editing" half of the
one gap above is closed, following the override-pattern playbook exactly —
new contract key, service validation, core application + carry-forward,
Layers-panel control, tests at every layer.

- **Contract key: `boundary_override`** (shape_overrides, v1.4) — a list of
  `[x, y]` mm points (design-center origin, y-down, the same space
  `outline_mm` already reports) replacing a shape's EXTERIOR ring only;
  holes ride forward unchanged from the shape's current geometry.
  `digitizer_service/app.py`'s `_canonicalize_shape_edits` validates point
  count (3..500, mirrored in `digitizer_core.regions`'s own copy),
  finiteness, and — the shell alone, since a request never carries the
  shape's holes — polygon validity plus the same sewability floor stage 4's
  own run-tier rescue already holds auto-digitized regions to
  (`machine.RUN_MIN_AREA_MM2` / `RUN_MIN_LOOP_MM`): a fast 400 on a
  self-intersecting drag or a pinched-shut shape. `digitizer_core/
  regions.py::apply_shape_edits` re-validates independently (defense in
  depth, same posture as every other key here) and ALSO checks hole
  containment against the shape's real polygon — the one check that can
  only run there. A rejected edit is always a clean `ValueError` (a 400 at
  submit, or a job-level error for the hole-containment case specifically,
  since that one needs the shape's real geometry to catch) — never a crash,
  never silently repaired geometry. `area_mm2` is recomputed on a
  successful edit; the key was added to `match_shape_ids`' carry-forward
  list alongside `border`/`tier`/`fill_angle_deg`/`sew_order`/
  `underlay_style`.
- **Studio UI:** `DigitizePanel.svelte` gained an "Edit shape boundary" (✎)
  control per Layers row (shown wherever the other per-shape controls
  already are — not for hidden or not-sewn rows). It opens a small SVG
  editor in place of the layer list: draggable vertex handles, small
  midpoint dots that add a vertex on click/Enter, right-click or Delete to
  remove one (floor of 3, matching the server), arrow keys to nudge a
  focused point. `digitizer.js` gained the client-side mirror of the
  server's geometry checks (`boundaryIssues`/`ringArea`/`dedupeRing`) so an
  invalid shape shows its problem and disables Save immediately, before a
  wire round trip — the server stays the actual authority. `reviewFromJob`
  gained `outlineFull` (deduped, capped at the server's own 500-point
  ceiling) distinct from the thumbnail's hard-decimated `outline`, so
  opening the editor never silently reshapes a shape before a single drag
  happens. Save merges the result into `shapeOverrides` via the existing
  `setOverride` call — the identical "Apply layer changes" flow every
  other override here already uses; no new save/apply path.
- **Verification:** `digitizer/tests/test_shape_overrides.py` (core-level:
  valid reshape + recomputed area, hole preservation, an awkward-but-valid
  hand edit run through real stage5/stage7 with no degenerate stitches,
  rejection of a bowtie/sliver/too-few-points with a clear error, dedup of
  a closed ring, carry-forward via `match_shape_ids`, a stateless
  re-digitize round trip proving the override survives on the SAME stable
  id) and `digitizer/tests/test_service.py` (HTTP-level: the round trip,
  cache-key participation, bad-geometry 400s, and the one check that can
  only fail at job-run time — a shrunk shell that pokes a real hole
  outside it). Studio: `digitizer.spec.js` unit coverage for the new pure
  helpers and wire contract, plus a new Playwright e2e spec
  (`app/e2e/digitize-boundary-edit.spec.js`) driving the real digitizer
  service end to end. Also manually verified live via Playwright MCP
  against the real service — drag-to-move, click-to-add, right-click-to-
  remove, and the invalid-shape (self-intersecting) rejection path all
  confirmed working, screenshotted.

**Shape splitting and merging — CLOSED 2026-08-05** (worktree
`agent-a095c5eea8b6320fb`, branch `shape-split-merge`): the "other half of
the original shape-recognition gap" this doc tracked as fully open is now
built, following the same override-pattern playbook `boundary_override`
established — new contract keys, service validation, core application, a
Layers-panel control, tests at every layer — with one structural difference
called out up front because it drives every design choice below: merge and
split change the SET of shapes, not one shape's geometry, so neither rides
`shape_overrides` (which is keyed to ONE existing shape_id that survives the
edit) — both are new top-level config keys, siblings of `deleted_shape_ids`.

- **Contract keys (v1.5): `merge_shape_ids` / `split_shapes`.**
  `merge_shape_ids: [[shape_id, shape_id, ...], ...]` — each inner list at
  least 2 distinct ids to union into one new shape. `split_shapes:
  {shape_id: [[x0,y0],[x1,y1]]}` — a straight cut line (extended internally
  past the shape's own bounding box, so the caller sends only the two
  dragged endpoints) dividing one shape into exactly two. Both are validated
  service-side for shape/type (`digitizer_service/app.py`'s
  `_canonicalize_shape_edits`, mirrored bounds in
  `digitizer_core.regions`'s own copy) and re-validated independently at the
  core layer (`regions.apply_shape_merges` / `apply_shape_splits`, called
  from `pipeline.run_stages` BEFORE `apply_shape_edits` — ids are minted
  against the full stage-4 generation before deletions/overrides consume
  any of them, the same ordering reasoning `apply_shape_edits` already
  documents for itself). A stale/unknown id is a warning and that one
  merge/split is skipped (`SHAPE_EDIT_UNKNOWN_ID`, same posture
  `deleted_shape_ids` already has); a geometrically bad request (mixed
  threads, a present hole, a non-adjacent merge, a line that doesn't cross
  cleanly or crosses a hole, a piece under the sewability floor) is a clean
  `ValueError` — a 400 at submit for what the service can shallow-check, a
  failed job for what only the core's real Region geometry can (mirroring
  `boundary_override`'s own hole-containment asymmetry exactly).
- **`shape_id` allocation: brand new, deterministic ids hashed from the
  OPERATION's own inputs, never geometry.** Confirmed before relying on it:
  `match_shape_ids` is not wired into `pipeline.run_stages` at all today —
  it exists for a future segmenter (SAM2) that would move centroids/areas
  slightly on a re-digitize of the SAME image, a different problem from a
  user *deliberately* replacing a shape's identity. So merge/split mint new
  ids instead of trying to carry one forward: `_merge_shape_id` hashes the
  sorted source ids ("SM" + blake2s), `_split_shape_id` hashes the source id
  + the cut line's own (canonicalized-order) endpoints + which of the two
  pieces ("SP" + blake2s, piece order fixed by centroid, never shapely's
  internal `split()` ordering). Both prefixes can never collide with an
  `assign_shape_ids` output (always `"S" + hex`). Being pure functions of
  the request rather than geometry means an identical resubmit is one
  stable cache key/one stable pair of new ids, and — as a documented but
  not yet UI-wired bonus — a caller that computes the same hash could layer
  a `shape_overrides` entry onto a shape a merge/split mints in the SAME
  request; the shipped Studio UI does not do this, it always waits for the
  fresh review payload before adding further overrides (two-step, not
  one-shot).
- **v1 scope, deliberately narrow — the honest trade-offs, not silently
  missing:**
  - **Merge requires the union to reduce to ONE polygon** (source shapes
    must already touch or overlap) — a hard architectural fact, not a
    style choice: `Region.polygon` is a single `shapely.Polygon` everywhere
    in stages 5-7, so a merge that can't produce one polygon has no legal
    result. **Worth stating plainly:** stage 3's connected-component
    labeling (`connectivity=8`) already fuses any two genuinely-touching
    same-color regions into one shape_id before assign_shape_ids ever
    runs, so in practice this restricts merge's usefulness on the flat/
    gradient lanes to shapes a SLIC/RAG photo-segment pass left adjacent
    but unmerged, or a future hand-authored/manual-digitizing workflow —
    not "any two same-color shapes a user points at," which would need a
    bridging/convex-hull strategy this pass does not build. Documented as
    a real, known narrowing, not glossed over.
  - **Merge requires every source shape to share one thread_number** (no
    cross-color merge — which color would the result take? a real product
    question, deferred) **and none of them may have a hole** (shapely's own
    union handles holes correctly; the deferral is which shape's hole
    semantics should win when two different shapes' holes overlap or one
    sits over the other's fill — genuinely ambiguous, sidestepped for v1
    rather than guessed at).
  - **Split is a single straight cut line, not an arbitrary polyline** —
    extended internally so the caller need only send the two dragged
    endpoints, producing exactly two pieces. A cut crossing one of the
    shape's own holes is rejected rather than silently turning the hole
    into a notch on both halves (shapely itself handles this case without
    erroring, so the rejection is a deliberate product choice, verified
    against real shapely behavior before writing the guard, not a
    limitation of the library).
  - Per-shape styling (`border`/`tier`/`fill_angle_deg`/`sew_order`/
    `underlay_style`) is seeded onto the result from the largest source
    shape (merge) or onto BOTH new pieces (split); `boundary_override` is
    never carried forward either way — it describes a hand-edited shell for
    a polygon that no longer exists once the identity changes.
- **Studio UI (`DigitizePanel.svelte`):** a merge-selection checkbox per
  Layers row (stitched, non-hidden shapes only) plus a "Merge N shapes" bar
  that live-validates the selection (`digitizer.js`'s `mergeGroupIssues` —
  at least 2 shapes, one thread) and disables the button until it passes; a
  "Split shape" (✂) control opening a small SVG editor sharing the boundary
  editor's scaffolding — a draggable 2-point cut line (defaulting to a
  horizontal line through the shape's own centroid, already valid for a
  convex shape) with live validation (`splitLineIssues`, counting crossings
  against the shape's own outline) disabling Save until the line crosses
  cleanly. Both save through the SAME `setOverride`-adjacent →
  `mergeGroups`/`splitLines` element fields → "Apply layer changes" flow
  every other override here uses; `canonicalShapeEdits`/`editsKey` fold both
  new fields into the existing pending-edit diff, so no new Apply-button
  wiring was needed. A merged/split result row's provenance (and its
  Undo-merge/Undo-split action) is read off the LAST APPLIED job's own
  `SHAPES_MERGED_BY_USER`/`SHAPE_SPLIT_BY_USER` warnings — the server
  already computed which source ids produced which result id, so the
  client never re-derives the hash.
- **Verification:** core-level (`digitizer/tests/test_shape_identity.py`,
  24 tests — the merge/split happy paths on synthetic adjacent Regions, every
  v1 guardrail as a real `ValueError`, the warn-vs-skip stale-id path, id
  determinism/stability regardless of argument or endpoint order, and two
  tests proving `cfg.merge_shape_ids`/`cfg.split_shapes` reach
  `apply_shape_merges`/`apply_shape_splits` from a REAL `digitize()` call
  against the same `logo_whitebg.png` fixture `test_shape_overrides.py`
  uses — the merge case using that fixture's own two real, non-adjacent
  "1305" regions to prove the adjacency guardrail fires on real geometry,
  not just synthetic squares) and service-level
  (`digitizer/tests/test_service.py` — parse/canonicalization including
  point/endpoint-order normalization for a stable cache key, 13 new bad-
  request 400 cases, the manual-digitizing field exclusion extended to both
  new keys, an HTTP round trip that actually cuts the fixture's real purple
  rectangle into two new shapes with the design's stitch count changing,
  and the merge-rejection round trip against the real orange pair). Studio:
  `digitizer.spec.js` gained unit coverage for the new canonicalization and
  the two pure validation helpers (7 tests); a new Playwright e2e spec
  (`app/e2e/digitize-shape-identity.spec.js`) drives the REAL digitizer
  service end to end for split (open the editor, save the default cut,
  Apply, confirm the one original row became two rows sharing its thread
  with a "split shape" badge and the design's stats changed, then Undo
  split restores the single shape) — **run live against the real service
  this pass, both tests green.**
  **One thing this pass deliberately did NOT verify live:** a full
  browser round trip of a SUCCESSFUL merge (select → Merge → Apply →
  one combined row). The reason is the same architectural fact above, not
  an oversight: `two-squares.png` (this repo's existing digitize-e2e
  fixture) has exactly two shapes, differently colored, so a live merge
  attempt on it can only ever demonstrate the SAME-COLOR validation
  rejecting a mixed selection (which the e2e spec does verify live,
  including the merge bar disabling itself) — not a genuine successful
  union, which needs two REAL same-thread, already-touching regions that,
  per the connected-component fact above, essentially never reach the
  review screen as two separate shapes in the first place. The successful-
  union code path itself is proven, just at the core level on synthetic
  Regions and the service level via the real-but-rejected orange pair, not
  through this particular browser harness.

**Next step:** the underlay-style dropdown (PR #28) still has no live-
browser check of its own. A live-browser proof of a genuinely SUCCESSFUL
merge (not just the rejection path) needs either a purpose-built fixture
image engineered to survive stage 3's connected-component fusion as two
separate same-thread regions, or a bridging/convex-hull merge strategy for
non-adjacent shapes — neither attempted this pass; both are candidates if
this area's merge feature gets picked up again.

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
