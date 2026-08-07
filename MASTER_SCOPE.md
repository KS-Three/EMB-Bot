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

**Last updated:** 2026-08-07 — fast follow-up to the `BACKGROUND_ENCLOSED`
bulk-restore banner (area 1, "Auto-digitizing quality" — see that section's
own entry below for the original fix): an adversarial review (`emb-bot-
reviewer`) of the merged diff found the new banner's exclusion of already-
converted text-cluster members (`textConversions`) was correct, but the
pre-existing PER-ROW "Sew it" button sitting right next to it in the same
unstitched-row branch had no such guard — clicking it on a converted
cluster member silently restores stitching for a shape a *different*
feature already replaced with a real text element, with no visual warning
(the "restored" badge only fires off the server's own `stitched` field,
which a cluster conversion's client-only override never touches). Proven
live against the real service, not just reasoned about: converting a
14-member cluster on the `enthusiast_logo.png` benchmark left all 14 with a
fully clickable "Sew it" button and the same misleading "enclosed area"
tooltip. This diff pre-dates the fix, so it never shipped to `main` in the
broken state — caught before merge, not a live regression. Fix:
`DigitizePanel.svelte` gains a shared `isClusterHidden(row, conversions)`
helper, used by both the banner's `unstitchedRows` filter (already correct)
and a new `clusterHidden` per-row const that now gates the per-row "Sew it"
button and label — a cluster-hidden row shows "hidden — converted to text"
pointing at the cluster bar's own Undo control instead. New regression
coverage in `text-cluster-convert.spec.js`: after converting a cluster, the
`Sew it` button count must equal only the pre-conversion baseline (real
enclosed-background rows, if any) and the bulk banner's live count must
exclude the converted members too — verified against the real service,
2/2 relevant e2e specs pass in isolation (the same environmental
worker-contention flake noted in the original entry reproduces when run
back-to-back with other heavy specs and is unrelated to this change).
Studio unit suite 435/435, `vite build` clean. Two smaller review findings
also closed same pass: a stale "not yet verified" sentence directly
contradicting the original fix's own new paragraph (self-resolved once
this branch was restarted from `main`, which already carried that doc fix
separately) and `.dgp-enclosed-banner`'s background swapped from a bare hex
literal to `var(--warn-bg, #fdf6e3)` for consistency with the rest of the
file's color-token convention.

Prior update below, still 2026-08-07: `stage2_photo_segment`'s superpixel
oversegmentation step (photo plan step 1, every photo/gradient-classified
design's segmentation entry point) swaps `skimage.segmentation.slic` for
`cv2.ximgproc.createSuperpixelSEEDS` (branch `seeds-superpixel-swap`, draft
PR against `main`, **not merged — do not treat this as shipped**). Motivated
by a standalone benchmark (superpixel algorithm isolated as the only
variable, every downstream step — RAG construction, area-ratio protection,
merge, CC split, min-area floor — held byte-identical) that measured SEEDS
producing 2-4x tighter boundaries than SLIC at matched region counts on the
two real busy fixtures this module's own test suite already tracks.

Real before/after, full pipeline (`run_stages`, `len(PipelineResult.
regions)`, the same F4 metric this module's threshold retunes have always
been measured against):

| fixture | SLIC (old, thresh=20.0) | SEEDS (new, thresh=26.0) |
|---|---|---|
| `drone_render.png` | 65 | 74 |
| `summit_badge.png` | 30 | 39 |
| `gradient_ramp_linear.png` | 2 | 2 |
| `gradient_ramp_radial.png` | 2 | 2 |

Both busy fixtures land inside the 20-80 accept band with real headroom;
visually inspected via `debugviz.stage2_photo_merged` on both, boundaries
read clean (drone_render's lettering/foliage/fuselage edges are crisp, no
speckle). The flagged risk going into this pass — SEEDS' extra boundary
sensitivity over-segmenting a smooth gradient ramp — was checked directly,
not assumed, and did NOT materialize: both ramps hold at their SLIC-era
counts across the whole threshold sweep tried (18.0-35.0), never exceeding
2 regions. `MERGE_DELTAE00_THRESH` moved 20.0 -> 26.0 (SEEDS' raw output
fragments WORSE than SLIC's at the OLD threshold — 106 vs 65 regions on
drone_render at 20.0 — the opposite of the benchmark's own framing that
SEEDS would need a less-aggressive merge; measured directly via a real
two-fixture sweep that the threshold had to move UP, not down).
`FACE_MERGE_FACTOR` re-derived as `5.0 / MERGE_DELTAE00_THRESH` (was a
hand-typed `0.25`) so the face-local absolute merge tolerance stays pinned
at 5.0 dE00 regardless of the base threshold, the same decoupling
`AREA_RATIO_PROTECT_THRESH` already established as precedent one retune
ago; `test_face_local_threshold_splits_shades_that_merge_outside_a_face`
confirms the absolute number held.

**KNOWN, MEASURED, UNRESOLVED REGRESSION — why this ships as a draft PR
and should NOT be merged as-is.** `summit_badge.png`'s black ring/inner-
circle/crosshair complex — real design content a prior PR (`AREA_RATIO_
PROTECT_THRESH`) fixed from ~1% to 83.7% area recovery — regresses hard
under SEEDS, to ~9-11% recovery, confirmed both numerically (`dark_area_mm2`
vs. source blackish-pixel area) and visually (`debugviz.stage2_photo_
merged`: the ring's own black stroke is almost entirely absent, only a
short arc and the crosshair needle survive dark). Root cause, measured not
guessed: under SLIC the complex consolidated into ONE large coherent RAG
node before ever facing the background — a clean big-vs-big size mismatch,
exactly what `AREA_RATIO_PROTECT_THRESH` guards. Under SEEDS the same
complex starts fragmented into ~150-260 much smaller (~750-800px)
superpixels, and the hierarchical merge walks a graduated CHAIN of small,
comparable-size, progressively-diluted edges from black to background —
never presenting the one large-ratio edge area-ratio protection is built to
catch. Every re-derivation attempted this pass — lowering `AREA_RATIO_MIN_
SMALL_PX` alone (200-1000, recovery stayed flat at ~9-10%); lowering it
together with `AREA_RATIO_PROTECT_THRESH` and a much more aggressive
`AREA_RATIO_MERGE_FACTOR` (recovery DID recover, to ~99-107%, but at the
cost of pushing `drone_render.png` to 122 regions — through the 80-region
ceiling `MERGE_DELTAE00_THRESH` was tuned against — and `gradient_ramp_
radial.png` to 8, toward the over-segmentation risk this same pass ruled
out elsewhere) — either failed to move recovery or fixed it by breaking
other already-validated behavior. No combination found cleanly decoupled
"protect this one real complex" from "keep allowing legitimate small-into-
large absorption broadly" the way the original SLIC-era tuning did.
`AREA_RATIO_PROTECT_THRESH`/`AREA_RATIO_MERGE_FACTOR`/`AREA_RATIO_MIN_
SMALL_PX` therefore ship UNCHANGED (18.0/0.6/1000) — the full investigation
trail lives in that constant's own docstring in `stage2_photo_segment.py`.
`test_summit_badge_black_complex_survives_full_pipeline` is marked
`xfail(strict=True)` (not deleted, not weakened, not silently lowered) so
this stays a live, visible regression marker — a future fix that resolves
it will flip the test to an unexpected pass, which pytest reports loudly.

**Confidence: LOW for this specific change, unresolved.** The core
algorithm swap measurably helps general busy-photo fragmentation
(`drone_render.png`) and does not regress gradient-ramp behavior — real,
validated wins. It is NOT safe to treat as a drop-in SLIC replacement across
all photo/gradient content: specifically, thin/high-contrast detail sitting
on a large similar-toned background (`summit_badge.png`'s own failure
shape) loses real design content that a previous fix restored. Full
targeted suite green otherwise: `test_stage2_photo_segment.py` (35 passed,
1 xfailed — the known regression above), `test_face_priors.py` (folded into
the same run), `test_flat_lane_byte_identical.py` + `test_palette.py` +
`test_pipeline.py` (30/30, confirming the flat/gradient golden lane and
unrelated pipeline stages are untouched), `test_background_removal.py` +
`test_stage6_blend.py` (both touch this module, both green). Do not raise
this rating, and do not merge the branch, until the `summit_badge.png`
regression above is actually resolved with real numbers behind the fix —
not just re-flagged as acceptable.

Prior update below, still 2026-08-07 — `regularize_text_clusters` gains a third,
**Last updated:** 2026-08-07 — Kent's own real-world upload of the
Instagram icon (gradient rounded-square background, white camera-glyph
linework) still showed "white space, not clean crisp edges" even after the
`BACKGROUND_ENCLOSED` restore mechanism verified directly below. Not a new
geometry defect: investigated first via `digitizing-quality-auditor` to
check Kent's own diagnosis (adjust overlap/pull-comp/density/underlay,
standard commercial-digitizing knobs) against the codebase's own history —
all four are already tuned for this art class (Laws 22/23/26/27-29,
appliqué cover pull-comp #72, border seam-sharing #73) and untouched by
this complaint. Root cause confirmed by direct reproduction against HEAD
(`stage1_prep.py::prep` on `testdata/photo/repro_gradient_white_icon.png`,
essentially this fixture): the white camera-glyph lines are the same white
as the page background, so `tag_enclosed_background` correctly flags them
`enclosed_background` (the same logic that correctly leaves an "O"'s
counter unstitched) and `pipeline.py` holds them unstitched by default —
real, deliberate behavior (see the `BACKGROUND_ENCLOSED` bullet in area 1
below), but the only way to fix it was clicking "Sew it" once per shape on
a dimmed list row, easy to miss entirely.

Asked Kent directly (a real product tradeoff, not a mechanical call):
auto-restore large enclosed areas by default (zero clicks here, but risks
silently filling a genuinely-intended hole on some future design) vs. keep
today's safe per-shape default and make restoring fast/obvious instead. He
picked the latter. `DigitizePanel.svelte` gains a loud `.dgp-enclosed-banner`
(replacing the old plain-text warning bullet) showing a live count plus a
"Sew all N" bulk action (`restoreAllUnstitched`) — one merged
`shapeOverrides` patch, not a loop (looping would clobber itself against
the same stale `element` prop across iterations, the pitfall
`undoTextConversion` already documents and works around). Deliberately
excludes any row belonging to a cluster already converted to text via
`textConversions` — that row's `stitched:false` is a permanent hide from
the text-cluster feature, not a default this banner should ever offer to
undo. Per-shape default behavior is otherwise byte-for-byte unchanged: a
genuine small enclosed hole still holds out by default exactly as before.

Verified against the real digitizer service + browser, not just unit-level:
`app/e2e/digitize-background-enclosed.spec.js` gained a second test driving
the bulk path end to end (banner shows the live count, "Sew all N" restores
every enclosed region on the repro fixture in one click, Apply re-stitches
all of them through the real service) and the existing single-row test's
assertions were updated for the new banner; both pass
(`npx playwright test e2e/digitize-background-enclosed.spec.js`, 2/2, plus
the sibling `digitize-boundary-edit`/`digitize-shape-identity`/
`digitize-stale-edits`/`text-cluster-convert` specs re-run clean to confirm
no shared-component regression). Studio unit suite: `npx vitest run`
435/435 (28 files). `npx vite build` clean. Engine and digitizer suites
untouched by this pass (pure Studio UI change, no `src/` or
`digitizer_core/` edits) and not re-run.
**Last updated:** 2026-08-07 — `stage6_satin.py`'s "E missing its
bottom-left corner" defect (root-caused, deliberately left open by PR #77 —
see this doc's own 2026-08-06 entry below) is now root-caused for real and
FIXED. Re-verified fresh before touching anything: rendered `photo/
enthusiast_logo.png` at 90mm via `debugviz.stage6`, confirmed by direct
render inspection that the defect is still present on current `main`
(PRs #77-#80 all merged, none touched this) — a visible gray gap between
the satin and the underlay's own boundary trace at the glyph's flush
corner. Also re-checked the "N" PR #77 flagged as possibly-short: its satin
coverage bounds now match its polygon bounds to within 0.008mm on every
side — **not present**, confirming the earlier independent re-measurement
this doc already noted.

**Real root cause, and it is NOT what PR #77's own investigation
suspected.** The junction machinery it named (`_extend_to_cap`,
`_retract_cap_corner`, `_merge_through_junctions`) is innocent: traced
directly, the stem's own medial axis welds through all three of the E's
T-junctions into one both-ends-free stroke exactly as designed, and
`_extend_to_cap` lands each of its two caps within 0.15mm of the glyph's
real corner. The actual bug is one step later, in `_short_stitch_guard`
(same file): the cross one station in from a cap is a real, keepable
stitch on its own (measured 0.57-0.60mm, comfortably over
`SATIN_MIN_CROSS_MM`'s 0.5mm floor) — but that station's same-rail step off
the cap is short enough to trip the guard, whose pull-toward-middle is
sized for a WIDE curve (35%, capped at an absolute 0.6mm — fine when a
cross is several mm) and, applied to an already-narrow cross, pulls it
under the floor. `satin_stroke`'s degenerate-cross filter then drops it a
few lines later for a reason that has nothing to do with why that filter
exists (an actual same-point pinch) — and the corner sews as bare fabric
even though the cap machinery it was blamed for did its job correctly.
Confirmed by direct instrumentation of the real code path (not a
reimplementation) on both the real fixture and an isolated synthetic
"E"-shaped polygon carrying the identical multi-junction topology, before
and after.

**Fix:** `_pull_short` (called from `_short_stitch_guard`) now bounds its
pull so it can never take a cross under `SATIN_MIN_CROSS_MM` itself — a
pull that would have landed the result below the floor lands AT the floor
(with a 1% margin so float rounding in the two `dist()` calls along the
way can't undershoot it) instead of past it. This is a general fix, not a
per-letter patch: it changes one shared helper every satin column's
short-stitch guard already goes through, for the specific case (a
near-floor cross whose same-rail step is short) that is possible at ANY
cap zone, corner, or tight curve — not gated on being near a junction or a
specific shape. Blast radius acknowledged honestly: this touches the
short-stitch guard's behavior for every satin shape in the app, satin
being `stage6_satin.py`'s whole reason for existing. What kept the change
narrow in practice: the new bound only ever binds when a pull would
otherwise cross the floor — a curve with real room to spare (the guard's
normal case, crosses several mm wide) never reaches it, so it is a no-op
there by construction, not by luck.

Visual re-verification, same method as the reproduction: the fixture's
"E" now shows a stitch landing 0.32mm from its flush corner (was 0.59mm) —
closer to the true vertex, not a residual gap eliminated to zero (a
mathematical corner is a zero-width point; no satin cross can land exactly
on it without becoming the same kind of degenerate stitch the guard
exists to prevent). Before/after crops of the corner, rendered directly
from the real polygon and the real `satin_shape` output (not the
composite debug render, for a distraction-free comparison), confirm the
gray gap visibly closes. The glyph's OTHER flush corner (bottom bar) was
already inside the floor before this fix (0.36mm both before and after —
a different station's parity happened not to trigger the guard there) and
is unchanged, not a follow-up gap: a pre-existing non-issue this pass
confirmed rather than assumed. One labeling caveat, stated plainly rather
than glossed over: "top"/"bottom" here is this pass's own render
convention (y-down, verified against a labeled direct render of the
glyph, not assumed) — which of the E's two flush corners Kent's own eyes
called "bottom-left" when he first reported this cannot be cross-verified
without his original screenshot. What IS verified: a genuine,
reproducible flush-corner coverage gap, with the exact symptom described
(bare fabric against the underlay's own boundary trace) and the exact
geometry described (a stem crossing multiple T-junctions), was found and
fixed on this glyph.

New regression tests, `tests/test_satin.py`: a synthetic `E_LETTERFORM`
polygon (proportions taken directly from the real fixture's own vectorized
"E", translated to the origin) plus `test_a_stem_crossing_three_junctions_
welds_into_one_stroke` (confirms the fixture actually exercises the
multi-junction topology before trusting the second test) and
`test_stem_free_end_reaches_its_own_flush_corner` (the coverage
regression; fails on pre-fix code at 0.59mm, passes post-fix at 0.32mm —
verified failing on the reverted code, not just passing on the fixed one).
Targeted suites green: `test_satin.py` **51/51** (49 existing + 2 new),
`test_flat_lane_byte_identical.py` **6/6**, `test_preflight.py`/
`test_stages.py`/`test_pushcomp.py`/`test_chaining.py` **169/169**
combined. Golden impact, checked by diff rather than assumed: only
`photo/enthusiast_logo.png`'s entry in `flat_lane_golden.json` moved
(regenerated the same way the doc's own prior precedent did — one key,
not a full re-run); `logo_whitebg.png`/`logo_alpha.png`/`ribbon_curve.png`
came back byte-identical. On the moved entry, `shape_ids`/`areas_mm2`/
`warnings`/`stitch_count` are all unchanged (2363 both before and after)
— only `stitch_coords` moved, and by a wide margin (1983 of 2363 entries),
which measured out as a benign downstream cascade rather than a new
defect: re-ran `preflight.run_preflight` on the same fixture before/after
and got the same score (88/B), the same single finding
(`TRIM_HEAVY`, essentially unchanged), and near-identical coverage metrics
(`coverage_max` 4.45 both, `coverage_area_mm2` 630→631) — consistent with
a few points' worth of real change early in one shape's sew order
cascading through Laws 27-29's structural entry-point selection for every
shape sewn after it, not with anything escaping its shape or overlapping
wrong. Three other fixtures (`logo_alpha.png`, `logo_whitebg.png`,
`ribbon_curve.png`) re-rendered and visually inspected: clean, no
starburst, no new gaps — `ribbon_curve.png` in particular is the fixture
`test_a_satin_free_end_does_not_fan_into_a_starburst` pins in detail for
exactly this guard's earlier, unrelated fix, and it still passes. Full
digitizer suite **not** re-run locally per this environment's own standing
caution (COOKBOOK.md); CI runs it on the PR.

**Last updated:** 2026-08-07 — closed the one remaining verification gap on
the `BACKGROUND_ENCLOSED` / opaque-alpha fix (area 1, "Auto-digitizing
quality"): watched it run through the real Studio browser UI via Playwright
MCP, not just the HTTP-level check PR #22 already had. Uploaded
`repro_gradient_white_icon.png` through the actual `+ Auto-digitize` file
input (the same canvas-re-encode path the opaque-alpha bug lived in),
digitized it against the real service, and confirmed visually: 4 enclosed
icon-linework regions held out by default as dimmed "not sewn — enclosed
area" rows (not dropped, not merged into neighbors), the canvas preview
showing them as literal unfilled gaps; clicked "Sew it" on one, applied, and
watched the real service re-stitch it (10,916 → 11,114 stitches, gap now
solid fill) while the other three stayed correctly held out. Screenshots
under `.playwright-mcp/background-enclosed-*.png`. No code change needed —
the fix already worked; see area 1's `BACKGROUND_ENCLOSED` write-up below
for the full account. Doc-only change, committed directly (see that
section's "CLOSED 2026-08-07" note for detail).

Prior update below, still 2026-08-07: `regularize_text_clusters` gains a third,
independent safety layer on top of the selective-regularization fix directly
below (PR #77, `fix-lettering-defects-hole-and-regularization`, still open/
draft, not yet merged to `main` — this work stacks on that branch; see "Not
yet merged" at the end of this entry): an OCR-confidence quality gate. The
two existing checks (`_REGULARIZE_SKIP_TOLERANCE`, hole-preservation) are
geometric PROXIES for "would this redraw read worse" — this measures it
directly. For every cluster member that clears both existing checks and is
about to be buffered, Tesseract (Apache-2.0; new `tesseract-ocr` system
package + `pytesseract` wrapper) scores the member's own rasterized crop
before and after the proposed skeleton-buffer redraw (`--psm 10`,
single-character mode); if confidence drops by >=20.0 points
(`_OCR_CONFIDENCE_DROP_THRESHOLD`), the buffer is discarded and the member
falls back to its original polygon — the same fail-open contract
`buffer_failed` already uses. Only a confidence NUMBER is ever read:
`pytesseract`'s decoded-text field (`data["text"]`) is never accessed
anywhere in this module — verified both by code inspection and by a
regression test that makes the decoded-text field raise `AssertionError` if
anything ever touches it (`tests/test_ocr_gate.py::
test_ocr_confidence_never_reads_the_decoded_text_field`).

Threshold calibrated on real measurements, not assumed. On the real
benchmark fixture (`enthusiast_logo.png`'s 14-member subline, 90mm), the ONE
member PR #77's existing checks let through to the buffer (the +30%-off
"I") drops from 77.0 to 0.0 confidence — Tesseract finds no text at all in
the buffered crop, a 77-point loss this gate now catches and blocks. A
broader real calibration set (font-rendered glyphs E/F/H/I/L/N/S/T/Z, DejaVu
Sans Bold, individually perturbed in stroke width so each clears
`_REGULARIZE_SKIP_TOLERANCE` on its own) measured six more real buffered
examples: three clearly damaging (-49, -27, -26 points), one borderline
(-20), one mild/still-fine (-5), one genuine improvement (+11, correctly NOT
blocked). 20.0 sits between the largest real "still fine" delta (-5) and the
smallest real "genuinely damaged" one (-20). Full evidence trail, both
calibration sets, and every constant's reasoning: `digitizer_core/
textcluster.py`'s "OCR-confidence quality gate" module-docstring section.

New tests, real Tesseract, no system-font dependency (letters are hand-built
5x7 dot-matrix block glyphs — deterministic across machines/CI runners, not
a font file that may or may not be installed): `tests/test_ocr_gate.py` (6
new — a real "fine" case, 93.0->92.0, gate does not fire; a real "damaging"
case, 92.0->0.0, gate fires and falls back to the original polygon; OCR
unavailable fails open; exact threshold boundary pinned with mocked values;
two tests proving the decoded text is never touched). Two of PR #77's own
tests now correctly isolate this new layer via the same no-op-patch pattern
`test_pipeline.py` already used to isolate `regularize_text_clusters`
itself: `test_textcluster.py`'s two bare-rectangle variance/area tests
(rectangles carry no real letterform content for Tesseract to read, before
or after) and `test_pipeline.py`'s full-pipeline variance test (whose real-
fixture "after" run now patches past the gate for the same real member the
gate legitimately blocks — that block is `test_ocr_gate.py`'s job to cover
directly, not this test's). Targeted suites green: `test_ocr_gate.py`
(6/6), `test_textcluster.py` (15/15), `test_pipeline.py` (12/12),
`test_stages.py` (15/15), `test_satin.py` (49/49), `test_service.py -k
text_cluster` (1/1). Full digitizer suite not re-run locally (this
environment's own standing caution, see COOKBOOK.md); CI runs it on the PR.

No isolation needed (unlike `rembg_isolated/`): `pytesseract`'s only deps
are `packaging`/`Pillow`, both already present in `requirements.txt` — no
numpy/numba conflict, confirmed via `pip show pytesseract` before adding it
to the shared venv. System `tesseract-ocr` install step added to CI's
`digitizer` job; documented in `digitizer/README.md`'s "Setup" alongside
`rembg_isolated/`'s own system-dependency note.

**Not yet merged:** this lands on branch `text-cluster-ocr-confidence-gate`,
stacked on PR #77's own branch (`fix-lettering-defects-hole-and-
regularization`) since the `_REGULARIZE_SKIP_TOLERANCE`/hole-preservation
mechanism this extends is not on `main` yet. Opened as a draft PR against
`main`; its diff will show both PRs' changes combined until #77 merges
first, at which point it collapses down to just this one.

Prior update below, still 2026-08-06: Kent looked at a real rendered
stitch-out of the benchmark fixture (`enthusiast_logo.png` at 90mm) and
reported 5 concrete
letterform-fidelity defects. All 5 were reproduced first (`debugviz.stage6`
render, visually inspected, not inferred from stats) before touching any
code — the working hypothesis going in (all 5 traced to `textcluster.py`'s
regularization) turned out to be **half right**: the investigation found
THREE separate root causes, not one, and this pass fixes two of them, leaving
the third open and documented rather than rushing a wide-blast-radius patch.

- **Subline "ENTERPRISES INC" garbled/illegible — FIXED.** Root cause really
  was `textcluster.regularize_text_clusters`, but not the mechanism assumed:
  it redrew EVERY tagged cluster member's polygon as a skeleton-buffer,
  unconditionally, even members whose own geometry was already fine.
  Measured on the real 14-member subline cluster: 13 of 14 members' own
  pre-regularization stroke half-width already sat within +-11% of the
  cluster's shared target (only one real outlier, at +30%) — the
  unconditional buffer was replacing already-good vectorized letterforms
  with a cruder approximation for zero consistency gain, and a skeleton-LINE
  buffer structurally cannot reproduce a real interior hole (3 of the 14
  members — R/P-style counters — lost theirs). Fix: `regularize_text_
  clusters` now skips a member (leaves its polygon untouched) when its own
  measured stroke half-width is within 15% of the cluster's target
  (`_REGULARIZE_SKIP_TOLERANCE`), or unconditionally when its original
  polygon already carries a real interior ring — a line buffer is never the
  right primitive for a hole it never measured. A genuine outlier still
  regularizes exactly as before (proven both on the real fixture and a new
  synthetic unit test). Full evidence and the module's new "Selective
  regularization" section: `digitizer_core/textcluster.py`.
- **"A" missing its triangular counter — FIXED, and NOT a text-cluster bug.**
  Direct measurement showed the main wordmark's letters (including the "A")
  carry neither `rescued_small_shape` nor `text_candidate` — they never go
  through `textcluster.py` at all, which falsified half of the working
  hypothesis immediately. Real root cause: `stage3_segment.
  resolve_small_regions` treated a small but completely real enclosed hole
  — already correctly found by `Prep.enclosed_mask` at stage 1
  (2.08mm², comfortably above the sewable floor) — as ordinary segmentation
  noise and absorbed it into the "A" glyph's own ink (its only possible
  neighbor, since an enclosed hole's neighbor is always the shape enclosing
  it), erasing it before `stage4_vectorize.tag_enclosed_background`'s
  already-correct machinery ever got the chance to tag it as its own Region.
  Fix: `resolve_small_regions` takes an optional `enclosed_mask` (wired from
  `Prep.enclosed_mask` in `pipeline.py`) and protects any small region
  >=60% covered by it from absorption/drop — it still has to clear stage 4's
  own real-geometry floor to survive, same as any other kept mask. Confirmed
  interacting CORRECTLY, not colliding, with the separate same-day
  `satin-classifier-organic-shapes` DT-tightening fix (area 1 below): the
  "A" used to flip satin->fill specifically because it read as a solid,
  holeless, organic blob (exactly what that fix's DT check exists to catch)
  — restoring the hole makes it measure as the well-proportioned ribbon
  letterform it always was, and it correctly flips back to satin
  (`tests/test_satin.py` updated with the real evidence for both directions;
  visual re-render confirms clean parallel satin, not a starburst).
- **"E" missing its bottom-left corner / "N" reading short — ROOT-CAUSED,
  left OPEN. CLOSED 2026-08-07** — see this doc's newest entry at the top:
  the actual mechanism was not the junction/cap-extension machinery this
  entry's own investigation suspected (that traced out innocent), but
  `_short_stitch_guard`'s pull-toward-middle taking an already-adequate
  near-corner cross under `SATIN_MIN_CROSS_MM`. The "N" symptom is
  confirmed NOT present (coverage bounds match its polygon to 0.008mm).
  Original write-up kept below for the investigation trail. Confirmed real
  via direct render crops (bare unstitched
  fabric exactly where the underlay's own boundary trace shows the true
  polygon corner). Confirmed NOT a text-cluster or enclosed-hole defect —
  the wordmark's satin letters go through the ordinary `stage6_satin.py`
  column-generation path (`extract_strokes`/`satin_stroke`/`_rail_points`),
  which is used by every satin shape in the app, not this feature. This is a
  real, pre-existing gap in how a letterform stroke that passes through
  MULTIPLE T-junctions along its own length (the E's vertical stem meets 3
  horizontal bars) gets its rail/cap geometry built — evidence points at the
  interaction between free-end cap extension (`_extend_to_cap`/
  `_retract_cap_corner`) and the per-station width cap in `_rail_points`,
  but was not narrowed further. Deliberately NOT fixed in this pass:
  `stage6_satin.py` is the single largest, most heavily-tuned, most
  fixture-sensitive file in the codebase (1750 lines, referenced by every
  satin golden in the suite, several hard-won fixes already on record in
  this doc's own history), and a change there needs its own dedicated
  investigation and review pass, not a patch bundled into an unrelated
  feature's bugfix. Flagged here as a real, separate, still-open defect.

New regression tests: `tests/test_textcluster.py` (2 new + 1 rewritten to
match the corrected selective behavior — the old one asserted "every member
regularizes," which was the bug), `tests/test_stages.py` (1 new, the
enclosed-hole-survives-absorption case), `tests/test_satin.py` (1 rewritten
— the "A"'s satin/fill call flips as a correct consequence of the hole fix,
not a break). Targeted suites green: `test_textcluster.py` (15/15),
`test_stages.py` (15/15), `test_pipeline.py` (12/12, including both existing
text-cluster wiring tests), `test_satin.py` (49/49). **Not verified locally:**
`test_flat_lane_byte_identical.py` — `testdata/flat_lane_golden.json` is
pre-existing corrupted JSON at HEAD (confirmed via `git status`/`git log`
showing zero local diff on that file; unrelated to this pass, already
tracked by a separate in-progress fix per `git worktree list`), so it cannot
even be collected here, let alone regenerated. This pass's geometry changes
(the "A"'s hole, several subline members' polygons) almost certainly move
`photo/enthusiast_logo.png`'s golden entry once that file is fixed — flagged
explicitly rather than silently left for CI to discover. Full digitizer
suite NOT re-run locally per this task's own instruction (proven unreliable
in this environment); CI runs it on the PR.

Prior update below, still 2026-08-06: satin entry/exit point selection now follows
**Last updated:** 2026-08-07 — `digitizer_core/textcluster.py`'s text-cluster
detector gains three classical-CV strengthening passes, all measured against
the real `enthusiast_logo.png` benchmark rather than assumed (area 1's
"Text-cluster detection" entry below has the full writeup): (1) three new
candidate filters — stroke-width coefficient of variation, aspect-ratio
bounds, and bbox-nesting exclusion — tightening `_candidates()`, which
previously compared only each shape's MEAN stroke half-width; (2) a Shape
Context descriptor (Belongie/Malik/Puzicha 2002, new module
`digitizer_core/shapecontext.py`, ~150 lines, no new dependency) wired into
`regularize_text_clusters` as a before/after glyph-plausibility gate — a
cluster member whose regularized redraw structurally diverges too far from
its own original shape (a corner blown out, a hole filled) is now skipped
instead of silently applied, same fail-open discipline as every other guard
in that function; (3) MSER (`cv2.MSER_create()`) was investigated as a
companion signal and deliberately NOT built — measured directly against both
the raw and prepped benchmark image, it returns zero regions everywhere,
because this module's whole domain (flat-lane, few-solid-color vector art)
structurally lacks the multi-level intensity gradient MSER's threshold-sweep
stability check requires; full reasoning in `textcluster.py`'s own "MSER"
docstring section. All three additions land on the SAME real benchmark
fixture's golden output byte-identical (`test_flat_lane_byte_identical.py`
still green) — none of the fixture's 14 real letters or its regularization
were false-positived by the new filters; the filters instead removed a class
of failure the fixture doesn't happen to trigger today (confirmed via direct
measurement on the fixture's own non-member fragments, not inferred). 30 new
tests (`tests/test_shapecontext.py`, new; `tests/test_textcluster.py`
additions), 222 total across the touched suites passing.

Prior update below, still 2026-08-06 — satin entry/exit point selection now follows
corpus laws 27-29 instead of pure nearest-point, closing the highest-value
item a `digitizing-quality-auditor` health check surfaced this session (Kent
picked it explicitly over two alternatives it also proposed: border
seam-sharing, which needs a design sign-off on which shape wins a shared
edge before it can be built, and appliqué cover pull-comp, both still open).
Scored on 291 real professional decisions, `docs/corpus-laws-round3-
2026-08-01.md` found pros enter a satin stroke at its FREE end (the open
cap) 85.2% of the time, not whichever end is merely nearest the needle
(42.3% for that rule) — and will pay up to ~10mm of extra travel to reach
it (law 29), not more. `digitizer_core/stage6_satin.py` gains one new
helper, `_choose_stroke_entry(cur, a, free_a, b, free_b)`: when a stroke has
exactly one free end (the other welded into a junction by the existing
skeleton-weld machinery), entry prefers the free end unless the extra
travel over the nearer end exceeds the new `machine.
STRUCTURAL_ENTRY_BUDGET_MM = 10.0` (law 29's own measured cutoff), in which
case it falls back to nearest — unchanged from before. When both ends are
free (an isolated stroke) or both are junction-welded, there is no
structural signal to prefer and proximity alone decides, byte-identical to
the old rule — this is why the change's reach is narrower than "every
satin stroke": only strokes with exactly one free end are affected. Wired
into two call sites — `_order_strokes` (the sequencing simulation) and
`satin_shape`'s per-run reversal loop — but the reversal loop applies the
new rule ONLY to the visible satin column (`StitchRun` kind `SATIN`);
underlay runs keep pure-nearest orientation, since the corpus law was read
off real stitch files' visible satin entries, not hidden underlay, and
underlay orientation is already separately tuned to minimize inter-stroke
hops. **Not implemented:** law 28's finer end-CLASS ordering (cap > tee >
corner ~= butt) among junction ends specifically — that needs classifying
each junction end's own arm count/angle, which `Stroke` does not currently
carry (only the binary free/not-free distinction `extract_strokes` already
computes). Left as an explicit follow-up rather than guessed at.

Six new tests in `tests/test_satin.py`: four direct unit tests of
`_choose_stroke_entry` (prefers the cap within budget, exact-10mm boundary,
falls back past the budget, and both tie cases — both-free and
both-junction — fall back to pure proximity), plus two end-to-end tests via
`satin_shape` on synthetic T-junction polygons (a new short-stem
`T_SHORT_STEM` fixture proving the cap wins within budget; the existing
`T_SHAPE` fixture's 17mm stem proving the budget fallback still holds for a
real over-budget case). Golden impact, checked by diff rather than assumed:
`flat_lane_golden.json`'s `logo_alpha.png` and `photo/enthusiast_logo.png`
entries moved (both carry real lettering with free/junction-asymmetric
strokes) and were regenerated — deliberately, only those two keys, via the
same `snapshot()` function `tools/capture_flat_lane_golden.py` uses, not a
full re-run of that script — while `logo_whitebg.png` and `ribbon_curve.png`
came back byte-identical and were left untouched, matching the fact that
neither fixture has a qualifying stroke. `shape_ids`/`areas_mm2`/`warnings`
are identical before/after on both regenerated fixtures; only
`stitch_coords` moved (plus `stitch_count` on `enthusiast_logo.png`, 2431 ->
2454 — expected, since a different entry point reshapes travel-graph
routing between strokes). Full digitizer suite re-run to completion in the
foreground after the golden update: **867 passed, 3 skipped, 0 failed**
(1228s) — the 3 skips are the same standing container-environment goldens
this doc has tracked since 2026-08-03, deselected the same way CI does, not
new failures. Engine `node --test` re-run too: **283/283** (this doc's
267/267 figure was stale going in — more engine tests landed since it was
last written; not a regression, just catching the count up). `app/`
untouched by this change (confirmed via `git status`) and not re-run in
this environment (Studio's `node_modules` isn't installed here); carrying
forward the doc's last-verified Studio count rather than asserting an
unverified new one. Done directly on the session's own working branch, not
an isolated worktree — a solo, contained fix.

Prior update below, still 2026-08-06: the "jersey_tee fill underlay" follow-up this
doc flagged as a low-priority candidate (area 1, below) is investigated and
**closed as declined, not a code change**: a direct measurement (synthetic
fill polygons at realistic sizes — 60x40mm, 100x70mm, 20x15mm — run through
`digitizer_core.stage6_fill._underlay_paths`, computing the real max distance
from any interior point to the nearest underlay stitch) shows `center_run`
does NOT close the 13mm interior gap the prior audit measured — it's
statistically identical to `edge_run` (60x40mm: 19.04mm vs 19.02mm; 100x70mm:
34.02mm vs 34.01mm; 20x15mm: 6.58mm vs 6.11mm, `center_run` actually
*slightly worse* on the small shape). A single line through the shape's
principal axis is exactly as far from off-axis interior points as a
perimeter walk is; only a full grid/lattice pass (`edge_lattice`/
**Last updated:** 2026-08-06 — the satin/fill classifier's DT-tightening fix
(`satin-classifier-organic-shapes`, area 1 below), previously scoped to
`gradient`/`photo_subject`/`photo_scene` only on the premise that flat art's
boundaries are clean, is **extended to `design_class="flat"` too**: that
premise was empirically false, proven on this repo's own committed
`testdata/photo/enthusiast_logo.png` benchmark, where the flat-exempted rule
satin-stitched two real shapes into a literal starburst (confirmed by
rendering their actual pre-fix stitch coordinates). `is_satin_candidate`'s
`design_class == "flat": return True` early return is deleted; the DT check
(`_dt_regular_and_within_cap`, itself untouched) now runs unconditionally.
`flat_lane_golden.json` regenerated and structurally diffed — exactly the 2
predicted entries move (`logo_alpha.png`, `photo/enthusiast_logo.png`),
`logo_whitebg.png`/`ribbon_curve.png` stay byte-identical. Full detail,
exact measurements, and the pure-tightening safety re-proof (four
letterform archetypes still satin under `"flat"`) in area 1's "Satin/fill
classifier" bullet below.

Prior update below, still 2026-08-06: the "jersey_tee fill underlay"
follow-up this doc flagged as a low-priority candidate (area 1, below) is
investigated and **closed as declined, not a code change**: a direct
measurement (synthetic fill polygons at realistic sizes — 60x40mm, 100x70mm,
20x15mm — run through `digitizer_core.stage6_fill._underlay_paths`,
computing the real max distance from any interior point to the nearest
underlay stitch) shows `center_run` does NOT close the 13mm interior gap the
prior audit measured — it's statistically identical to `edge_run` (60x40mm:
19.04mm vs 19.02mm; 100x70mm: 34.02mm vs 34.01mm; 20x15mm: 6.58mm vs 6.11mm,
`center_run` actually *slightly worse* on the small shape). A single line
through the shape's principal axis is exactly as far from off-axis interior
points as a perimeter walk is; only a full grid/lattice pass (`edge_lattice`/
`edge_zigzag`) actually closes it, to 1.6-1.8mm regardless of shape size.
Even combining `edge_run`+`center_run` (a real corpus recipe, "Rg.Re") only
halves the gap on large shapes (9-17mm) — nowhere near lattice coverage. So
the flagged fix candidate would have been a no-op dressed up as a fix:
`jersey_tee` stays on `edge_run`, unchanged. The real closer (a lattice
pass) is exactly what corpus law 26 already found professional digitizers
rarely use under fills (7/507) and was the explicit reason `edge_lattice`
was removed as this fabric's default in the first place
(`docs/corpus-laws-round3-2026-08-01.md`) — so the 13mm gap reads as a
structural property of sparse running-line underlay on a large fill shape,
not a `jersey_tee`-specific misconfiguration, and law 26's own choice is
reaffirmed rather than second-guessed. Measurement script was a throwaway
scratchpad check, not committed — a one-off geometric verification, not
ongoing test coverage. No source file changed this pass.

Prior update below, still 2026-08-06: the "Evaluation corpus & harness"
cross-cutting gap (below) gets its harness half built: `digitizer/tools/
corpus_scorecard.py`, a `capture`/`diff` CLI that runs the digitizer's 14
committed `testdata/` fixtures through the already-existing
`preflight.run_preflight` scorer at two garment configs and remembers/diffs
the result — a standing, automated answer to "did this change make the
output better or worse" that this doc has flagged as missing since the
corpus-laws-23/26 pass. Shipped as a reporting tool, not a CI gate, on
purpose; the corpus half (`scratch_corpus/`) remains inaccessible and
untouched. Full detail in the cross-cutting section itself, not duplicated
here.

Prior update below, still 2026-08-05: the satin self-overlap defect this doc
has carried as an open callout since the corpus-laws-23/26 pass (area 1
below) is **FIXED**: `stage6_satin.py::_rail_points` now caps every satin cross's
per-station width to `machine.SATIN_MAX_WIDTH_MM / 2`, on top of the
existing local-corridor cap. Root cause, confirmed by direct spine
inspection (not assumed): `logo_alpha.png`'s `Sf5200f3f` carries a stroke
with BOTH ends free — no skeleton junction node on it at all — whose
half-width profiles as a smooth, single-peaked taper across all 36 of its
own stations (0.17mm at each tip, ramping continuously to 4.67mm at the
apex and back down). That is the shape's real medial-axis width, not a
measurement artifact; an initial "junction merged-footprint DT" hypothesis,
and a local-neighbourhood-outlier cap built on it, were both tried and
disproven (the outlier cap made zero difference, since a genuine continuous
taper has no isolated station to detect against). The fix instead reuses
`SATIN_MAX_WIDTH_MM` as a flat per-station ceiling — the same
corpus-validated cap the satin/fill classifier and `_stroke_underlay`'s
oversize skip (prior update below) already gate on, not a new number, so no
classifier-eligible column should need a wider cross regardless of why one
station reads wide. Measured on `Sf5200f3f`: eliminates all 2580
non-adjacent self-crossing rail-to-rail segment pairs and drops the shape's
own isolated coverage peak from 9.57 to 3.41 layers (design `coverage_max`
13.11 -> 3.24 at `target_width_mm=80`/`left_chest`). One real, minor
collision found and resolved: a synthetic `tests/test_pushcomp.py` fixture
(a 45x4.5mm bar) legitimately grows to 5.1mm under directional pull comp
(Law 22) and lost ~0.02mm of `rail_overhang` to the new cap — not a bug the
push-comp test exists to catch, so its fixture height moved 4.5 -> 4.0mm
with an inline comment explaining why, rather than loosening the cap to
route around an incidental collision. `flat_lane_golden.json` regenerated;
confirmed by structural diff that only the `logo_alpha.png` entry moved
(`logo_whitebg.png`/`ribbon_curve.png`/`photo/enthusiast_logo.png`
byte-identical). New regression coverage: `tests/test_satin.py::
test_satin_crosses_do_not_self_overlap_across_a_wide_junction` (direct
geometry, not just the aggregate coverage number) and `tests/
test_preflight.py::test_a_wide_oversize_satin_stroke_does_not_block_on_
underlay_glue`'s old `coverage_max > 10.0` floor — which existed
specifically to pin this defect as NOT yet fixed — is now inverted to a
`< 5.0` ceiling. Full digitizer suite re-run to completion in the
foreground: **852 passed, 3 skipped, 0 failed** (1136s) — 0 failures this
run, including the 3 container-environment goldens this doc usually
caveats as known-flaky, which passed clean here too. Engine/Studio
untouched by this pass (`git status` confirmed no `src/`/`app/` changes) and
not re-run, carrying forward their last-verified counts below rather than
re-asserting unverified numbers.

Prior update below, still 2026-08-05 — text-cluster detection + a regularized
lettering fallback landed across two PRs, #63 (merged: `textcluster.py`'s
geometry-only detection of text-like clusters among rescued small shapes,
pipeline wiring, the service's read-only `text_candidate`/`text_cluster_id`
review fields, geometric regularization via a skeleton-buffer redraw at each
cluster's shared median stroke width, and the Studio side — a "looks like
text" badge, a per-cluster "Convert to text" action, and undo) and #64
(open at time of writing: a real Playwright e2e run against the live
service, which caught and fixed a genuine bug, not a test mistake —
`ContentStep.svelte` forwarded `DigitizePanel`'s `converttotext` event up to
`App.svelte` but never wired the same forwarding for `removeelement`, so
undo silently never removed the created text element; fixed with the
missing one-line forward). No OCR anywhere in this slice — detection is
pure geometry (proximity, bbox-height and stroke-width similarity via the
same `ShapeField`/EDT machinery `stage6_satin` already uses), and nothing is
ever auto-substituted: converting a detected cluster creates a real,
**empty** text element with no font pre-picked, so a user always supplies
the actual word and typeface themselves. Full detail in areas 1 and 5 below,
and spec/plan at `docs/superpowers/specs/2026-08-05-text-cluster-detection-
design.md` / `docs/superpowers/plans/2026-08-05-text-cluster-detection.md`.
Verified per-step (not just at the end): digitizer full suite **851 passed,
3 skipped, 0 failed** (unaffected by the e2e-only PR #64 step, which touches
no Python source), Studio `vitest` **426/426**, and the new
`app/e2e/text-cluster-convert.spec.js` passing for real against the live
service and browser after the `removeelement` fix above. Also verified live
in a running Studio dev session against the real benchmark fixture
(`enthusiast_logo.png` at 90mm): the badge/action bar appears over the
14-shape subline cluster exactly as the Python-side pipeline tests predict.

**Also this pass: the cross-cutting "Evaluation corpus & harness" gap below
is newly tracked** (not a new capability area — this doc considered and
explicitly rejected splitting area 1 into separate "image analysis"/"stitch
planning" areas this same session, since they're pipeline stages of one
system, not separately shippable products) — see that section for why, and
for a correction to an external review's claims that this pass's own
research found inaccurate.

Prior update below, still 2026-08-05: corpus laws 23 and 26 landed for real
this pass, closing out the reverted attempt this doc has carried since the
last entry (see that entry's UPDATE note, area 1, for the historical account
of why the first attempt was backed out). Law 26: `fabrics.py`'s `pique_knit`/
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
law) was NOT fixed by this pass and was left open — currently invisible to
`DENSITY_STACKED` because it never reaches the connected-patch gate alone,
which is arguably its own gap in the coverage instrument's peak-detection
sensitivity, flagged here rather than chased further. **FIXED, separate
same-day pass — see the top-of-doc "Last updated" entry; this paragraph is
kept as the historical record of the defect, not current status.**

**Also flagged by the same audit: `pique_knit`/`jersey_tee`'s new `edge_run`
fill underlay leaves large fill interiors up to 13mm from the nearest
underlay stitch (vs 1.6-1.8mm under the old `edge_lattice`) — investigated
and CLOSED as declined, 2026-08-06, see the top-of-doc "Last updated"
entry.** The candidate fix floated here (`center_run` in place of
`edge_run` for `jersey_tee`) was measured directly and does not work: a
single center line sits exactly as far from off-axis interior points as a
perimeter walk does (measured statistically identical max-gap across three
realistic fill sizes), so it would not have addressed the tension with
`jersey_tee`'s "needs solid underlay" note it was floated to fix. The only
style that actually closes the gap is a lattice pass, which corpus law 26
already found rare in real fills (7/507) and was the reason `edge_lattice`
was removed as this fabric's default to begin with — so `edge_run` stays,
and the 13mm figure is read as inherent to sparse running-line underlay on
a large shape, not a preset defect. This paragraph is kept as the
historical record of the flagged concern, not current status.

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

### Evaluation corpus & harness — real gap, newly tracked here

**Newly named as its own cross-cutting item this pass, not a newly-discovered
problem** — every piece of it was already visible, scattered across area 1's
history as a recurring blocker with no single name: the DT-first satin/fill
classifier's M2/M3 has been blocked since 2026-08-01 on a 37-file
`scratch_corpus/` run that no session has ever had local access to
(gitignored, confirmed empty in every checkout); several corpus-law
recalibrations (`docs/corpus-laws-round3-2026-08-01.md`) needed careful,
one-off validation against golden fixtures specifically because there is no
standing, automated way to score "did this change make the output better or
worse" outside of manually re-running the digitizer suite and eyeballing a
handful of fixtures; and the fundamental confidence ceiling this doc has
always cited — zero physical sew-out testing — is the same root cause
wearing a different hat: no repeatable, automated quality signal, so every
serious quality question queues behind either a corpus nobody has, or a
sew-out that hasn't been scheduled. This is a real, distinct capability gap
— a labeled corpus plus a scoring harness — not merely a rhetorical
reframing of the sew-out gap above; landing it would let future classifier/
quality changes be judged against *something* before either the corpus or a
sew-out session is available, not instead of them.

**The harness half is now BUILT, same-day follow-up: `digitizer/tools/
corpus_scorecard.py`.** The corpus half is untouched — the 37-file
`scratch_corpus/` M2/M3 needs is still inaccessible, gitignored and empty in
every checkout, same as above. What this pass adds is the "remember and
diff" machinery that was missing: `capture` runs every one of the
digitizer's 14 committed `testdata/` fixtures (top-level and `photo/`)
through `digitize()` + the already-existing `digitizer_core.preflight.
run_preflight` — which already computed a 0-100 score, letter grade, typed
findings and ~20 metrics per design; this pass aggregates that existing
signal across the corpus rather than inventing a new metric — at two
configs (80mm width x `left_chest`/`hat_front`, two distinct fabric
presets) and writes `testdata/corpus_scorecard_baseline.json`. `diff`
re-runs the same matrix and reports score deltas, findings that appeared/
resolved by code, and metric drift past a 5% noise threshold against that
baseline. Shipped deliberately as a REPORTING tool, not a CI gate — the
script's own docstring cites this doc's corpus-laws-23/26 history (a
"desk-safe" threshold picked without real validation, later reverted) as
the reason not to invent pass/fail numbers yet; the one exception treated
as a hard signal is a brand-new "block"-severity finding, which does flip
the `diff` command's exit code, since that's the one low-noise, high-
confidence case. Verified working, not just written: a real captured
baseline (all 14 fixtures x 2 configs, grades spanning A to F — the F/0
scores on `drone_render.png`, `repro_gradient_white_icon.png` and
`summit_badge.png` are real, already-documented rough edges in those
photo-tier stress fixtures, not a harness bug, exactly the kind of honest
signal this tool exists to surface rather than hide), then an immediate
re-`diff` with zero code changes reporting "no drift against the baseline"
at exit 0 — proving the underlying pipeline is deterministic and the
harness doesn't false-positive on its own output. No dedicated test file:
matches this repo's own convention that no `tools/*.py` script (including
the same-pattern `capture_flat_lane_golden.py`) has one, and a full capture
run touches several photo/SLIC fixtures, too slow for the regular suite.
**Next step for this gap:** use the tool by hand against a few real future
corpus-law/classifier changes to learn what a genuine regression looks like
here before deciding on hard CI thresholds; the labeled-corpus half stays
blocked on `scratch_corpus/` access, unchanged by this pass.

**Not promoted to a sixth top-level capability area.** This session
evaluated and explicitly rejected splitting area 1 ("auto-digitizing
quality") into separate "image analysis" (raster → regions/colors) and
"stitch planning" (regions → technique/stitches) areas, which an external
review of this doc proposed alongside naming this gap. Reasoning: those are
tightly-coupled pipeline STAGES of one system (`stage0_classify` →
`stage1_prep`/`stage1_photo_prep` → `stage2_quantize`/`stage2_photo_segment`
→ `stage3_segment` → `stage4_vectorize` → stages 5–7), not two separately
shippable products — nearly every feature this doc tracks under area 1
(this pass's own text-cluster detection included) touches both halves, so
splitting the tracking would recreate, at the doc level, the exact
"handoff nobody owns" problem that review raised as a reason to name this
gap in the first place. A future session should feel free to promote this
from a cross-cutting note to its own capability area once real work
actually lands against it (a labeled fixture set, a scoring script/metric),
per this doc's own convention of tracking status, not aspiration.

**Correcting the record on that same external review, so a future session
isn't misled by it:** it also claimed color quantization/palette reduction,
segmentation & vectorization, background removal, and small-detail/minimum-
feature culling had "no owner" in this project. Checked directly against
source this pass — all four already exist and are already documented above:
quantization is `stage2_quantize.py` (k-means + CIEDE2000 thread snapping)
and `palette.py` (weighted k-medoids chart selection); segmentation/
vectorization is `stage2_photo_segment.py` (SLIC+RAG)/`stage3_segment.py`/
`stage4_vectorize.py` — the literal subject of the `BACKGROUND_ENCLOSED` and
gradient-fragmentation sagas already detailed at length above; background
removal is `stage1_photo_prep.py`'s `remove_background_seam` (rembg,
isolated venv, PR #43); small-detail culling is `stage3_segment.py`'s
`small_shape_rescue` path (rescues a shape as a run stitch instead of
dropping it — the exact mechanism this pass's own text-cluster detection
builds on top of). The review's two accurate points — text detection in
logos being a real gap, and this evaluation-corpus/harness gap — are exactly
the two reflected in this update: the first is now closed by this pass's own
feature, the second is captured here.

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

  **Demonstration fixture moved off `logo_alpha.png`, 2026-08-06 — the
  chaining mechanism itself is unaffected, only which committed image proves
  it.** The satin/fill classifier's flat-lane DT-tightening fix (below)
  correctly reclassified two of `logo_alpha.png`'s shapes from satin to
  fill, which — as an incidental side effect, not a chaining defect —
  eliminated the specific narrow gap chaining used to bridge on that one
  fixture: measured directly, `chain_links` on vs. off became byte-identical
  output there (6 links either way, 0 exposure either way, 0 trims removed).
  Every synthetic-geometry chaining test in `test_chaining.py` (the ones
  that construct their own controlled gaps rather than reading a real image)
  stayed green throughout, confirming the mechanism itself never broke.
  `tests/test_chaining.py::test_chaining_cuts_the_benchmark_fixtures_trim_rate`
  and `..._adds_no_bare_fabric_exposure_on_the_committed_fixture` now run
  against `photo/enthusiast_logo.png` @ 82mm instead (this repo's own
  primary real-art benchmark, not a new synthetic construction) — swept
  across widths first to confirm 82mm isn't cherry-picked to the edge of the
  4.1 trims/1k corpus ceiling (it lands at 3.41/1k with real margin). The
  new numbers are a stronger demonstration than the old ones: links 2→17,
  trims 21→9, and bare-fabric exposure is exactly 0.0 mm both with and
  without chaining (cleaner than `logo_alpha`'s old 0.3011 mm/0.2057 mm
  floor, not a regression from it).
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
  exactly.

  **CLOSED 2026-08-07 — verified live via Playwright MCP through the actual
  Studio browser UI.** Drove the real `+ Auto-digitize` flow end to end
  against `repro_gradient_white_icon.png` (the camera-glyph gradient badge
  used by `test_enclosed_background.py`'s `REPRO` fixture): chose Tote →
  Content → Auto-digitize, uploaded the fixture through the real file input
  (the same canvas-re-encode upload path the opaque-alpha bug lived in),
  clicked Digitize, and let the real service (127.0.0.1:8721) run it.
  Confirmed everything the design promises, visually, not just via network
  inspection: the warnings list showed "Enclosed background-colored areas
  were left open, like the hole in an O. Find them in the Layers list,
  marked 'not sewn — enclosed area,' to sew them"; the Layers panel listed
  4 separate `#2521`-colored rows (860/125/132/132 mm² — the icon's square
  frame, ring, and dot linework) each tagged "not sewn — enclosed area"
  with its own "Sew it" control — not silently absent, not merged into a
  neighboring shape; and the live canvas preview showed those exact
  shapes rendered as unfilled gaps against the stitched gradient fill,
  matching "left open" literally. Clicked "Sew it" on the 860 mm² row: it
  moved into the normal editable Layers list with a "restored" badge and a
  live "NOT SEWN" pill, the other three stayed exactly as they were.
  Clicked "Apply layer changes" and waited on the real service round trip
  (`Digitizing…` → button hidden): stitch count moved 10,916 → 11,114, a
  new "2521 Fuchsia" thread-per-color entry appeared, and the canvas
  preview's square-frame gap was now solid stitched fill instead of a hole
  — the enclosed region became a real, sewable element on command, exactly
  as the fix's own description promises, while the three still-unreviewed
  regions kept their dimmed "not sewn — enclosed area" rows the whole time.
  Screenshots: `.playwright-mcp/background-enclosed-unstitched-rows.png`
  (post-digitize, all 4 held out), `.playwright-mcp/background-enclosed-
  sew-it-clicked.png` (one restored locally, badge + pill visible),
  `.playwright-mcp/background-enclosed-applied-final.png` (post-Apply:
  11,114 stitches, restored shape now solid-filled in the preview, the
  other three still correctly held out). This was the one remaining gap in
  this section — the HTTP-level check above proved the fix; this proves it
  survives the real upload path, the real Layers-panel UI, and a real
  restore-and-resew round trip, watched directly in the browser.

  **UX follow-up, 2026-08-07 — the restore mechanism was real but too easy
  to miss.** Kent's own real-world upload of this exact problem class (the
  Instagram icon) reported "still white gaps" even after live-browser
  verification of the mechanism above — not a geometry regression, a
  discoverability one: the per-shape "Sew it" control lived as a dimmed
  list line, and restoring N enclosed regions took N separate clicks. Full
  investigation and fix in this file's newest "Last updated" entry at the
  top; summary: the per-shape default is unchanged (a small enclosed hole
  still holds out by default), but `DigitizePanel.svelte` now surfaces a
  loud `.dgp-enclosed-banner` with a live count and a one-click "Sew all N"
  bulk restore, deliberately excluding text-cluster-converted rows. Verified
  end to end against the real service + browser
  (`app/e2e/digitize-background-enclosed.spec.js`, 2/2).

  **Follow-up caught pre-merge by adversarial review, same day: the
  per-row "Sew it" button needed the same text-cluster guard the banner
  already had.** Full detail in this file's newest "Last updated" entry at
  the top; summary: a converted cluster member could still be individually
  "restored" via the row-level button next to the banner, silently
  un-hiding a shape a different feature had already replaced with a text
  element. Fixed with a shared `isClusterHidden` check gating both the
  label and the button; new coverage in `text-cluster-convert.spec.js`
  proves a converted member never shows "Sew it" and is excluded from the
  banner's live count.

  **Band/part transition jump flags — FIXED, 2026-08-06.** `blend_fill`
  stitches each shade band (and, when `_band_clip` returns more than one
  disconnected polygon for a band, each part within it) as its own
  independent `stitch_shape` call, and every one of those calls' first run
  starts with `jump=False` in isolation — correct on its own, wrong once
  spliced back-to-back with whatever came before it, which used to leave a
  bare straight stitch across the real physical gap between two shade bands
  or two disjoint parts of one band. Both transitions now get an explicit
  `jump=True` with `trim` set from the actual measured gap, mirroring
  `stage6_fill.stitch_shape`'s own `emit()` convention for a travel move —
  deliberately without attempting `emit()`'s `travel_path` bridge first,
  since a bridge here would route the wrong shade's thread across the seam
  (see the code comments at both sites in `stage6_blend.py` for the full
  reasoning). Regression-tested in `test_stage6_blend.py`: one test drives
  the real linear-ramp fixture end to end and checks every band boundary,
  the other monkeypatches `_band_clip` to force a same-band, two-part split
  (no committed fixture has that topology naturally) and checks the seam
  between parts. `digitizer/tests` run clean with the fix in.
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

  **2026-08-06 update: the flat-lane exemption is gone — it was an unproven
  premise, not a proven-safe default, and it was wrong.** The scoping above
  reasoned that `"flat"` art's clean, spot-colour, vector-like boundaries
  don't carry the segmentation-derived noise the DT check exists to catch,
  so `is_satin_candidate` special-cased `design_class == "flat": return
  True` and skipped `_dt_regular_and_within_cap` entirely for it. A fresh
  audit against this repo's own committed, flat-classified benchmark
  fixture — `testdata/photo/enthusiast_logo.png`, picked in the first place
  because it "reproduces almost nothing [Kent] complains about" (COOKBOOK.md
  "Hard-won lessons") — disproved that premise directly: at
  `target_width_mm=90`, the DT check correctly rejects `Scd89ad66` (the
  wordmark's "A", `ribbon_width_mm` 2.386mm, area 33.837mm2) and `Sff37b029`
  (the emblem's 4-point star, `ribbon_width_mm` 1.287mm, area 17.624mm2) —
  both of which the flat-exempted rule satin-stitched into a literal
  **starburst** (crosses fanning from a single point), confirmed by
  rendering the actual pre-fix emitted stitch coordinates, not inferred from
  the classifier's numbers alone. That is exactly the defect COOKBOOK.md's
  "Hard-won lessons" section names by name ("Green tests are not evidence of
  quality... the engine produced starbursts") — invisible to the shipped
  test suite and to `preflight`/`corpus_scorecard.py` because neither
  measures cross-fan coherence, only mechanical properties (determinism, no
  phantom loops, nothing outside the artwork).

  Fix: the `design_class == "flat": return True` early return in
  `is_satin_candidate` (`digitizer_core/stage6_satin.py`) is deleted. The DT
  check now runs unconditionally — `design_class` is kept as a parameter
  (every existing caller still passes one) but no longer changes the
  verdict. This is a pure widening of an already-proven-correct check, not a
  new rule: `_dt_regular_and_within_cap` itself is untouched, byte for byte.

  **Measured, not assumed, on both configs that matter:** at the golden
  capture width (`target_width_mm=80`, `tools/capture_flat_lane_golden.py`'s
  own config), `enthusiast_logo.png`'s `Scd87e08f` (`ribbon_width_mm`
  2.121mm, area 26.735mm2) and `S919bee11` (1.144mm, area 13.925mm2) flip;
  at `target_width_mm=90` (the audit's cited config) it's `Scd89ad66`/
  `Sff37b029` above — different shape-id hashes because the raster scale
  differs, same underlying defect. `logo_alpha.png` also moves at 80mm:
  `Sb253ebba` and `Sf5200f3f` (both `ribbon_width_mm` 4.997mm — sitting
  right at the 5.0mm cap — and identical area, 100.241mm2, being mirrored
  halves of one glyph). `Sf5200f3f` is not a new finding — it's the
  "multi-stroke glyph" the 2026-08-05 self-overlap fix (`_rail_points`'
  `SATIN_MAX_WIDTH_MM / 2` per-station cap, prior update above) already
  named and partially mitigated without being able to fix outright, because
  that fix ran before this one and `design_class="flat"` still exempted the
  shape from ever being told it wasn't a ribbon. Rendering `Sf5200f3f`'s and
  `Sb253ebba`'s pre-fix stitches confirms the same starburst defect on this
  fixture too (a converging fan and an X-cross pattern respectively) — this
  fix is the fuller resolution the self-overlap cap could only patch around.
  Post-fix, all six flipped shapes sew as `stage6_fill.stitch_shape`'s
  ordinary parallel fill rows.

  `flat_lane_golden.json` regenerated via the repo's own
  `tools/capture_flat_lane_golden.py`, then structurally diffed key by key
  against the pre-change file (not blind-accepted): exactly the 2 predicted
  entries move — `logo_alpha.png` (`stitch_count` 2089 -> 2072) and
  `photo/enthusiast_logo.png` (`stitch_count` 2431 -> 2331), both only in
  `stitch_count`/`stitch_coords`; `shape_ids`/`areas_mm2`/`warnings` are
  identical on every one of the 4 fixtures, confirming no shape appeared,
  disappeared, or moved — only how the same shapes sew. `logo_whitebg.png`
  and `ribbon_curve.png` are byte-identical, exactly as predicted (neither
  fixture contains a shape the DT check disagrees with the old rule on).

  **Safety invariant re-proven for the flat lane specifically, the same way
  it was already proven for the other 3 classes:** this is satin->fill only,
  never the reverse. All four letterform archetypes (`BAR`, `O_RING`,
  `C_STROKE`, `T_SHAPE`) keep their satin call under `design_class="flat"`
  (`tests/test_satin.py::
  test_the_dt_check_does_not_cost_real_ribbons_their_satin_call_when_flat`).
  `tests/test_satin.py::test_satin_crosses_do_not_self_overlap_across_a_wide_
  junction` (the 2026-08-05 regression pin for `Sf5200f3f`'s rail-geometry
  cap) now calls `satin_shape` directly on the shape's real geometry,
  decoupled from `is_satin_candidate`, so the cap's own regression coverage
  survives the shape no longer reaching satin through the classifier; a
  companion test pins the classifier side directly
  (`test_sf5200f3f_no_longer_reaches_satin_in_the_real_pipeline`).
  `tests/test_preflight.py::test_a_wide_oversize_satin_stroke_does_not_
  block_on_underlay_glue` still passes unchanged (`coverage_max` stays well
  under its `< 5.0` ceiling now that the shape fills instead of satins).
  Superseded: `test_flat_design_class_keeps_the_old_verdict_on_purpose`,
  whose own premise (flat keeps the old verdict on purpose) this fix
  disproves — replaced by `test_flat_design_class_now_gets_the_dt_check_too`
  and `test_flat_lane_starburst_shapes_correctly_flip_to_fill`.

  Verified targeted, not a local full-suite run this pass (CI —
  `.github/workflows/python-package-conda.yml` — is the full-suite gate on
  the PR itself): `tests/test_satin.py` **43/43**, `tests/test_preflight.py`
  **56/56**, `tests/test_flat_lane_byte_identical.py` + `tests/
  test_photo_sequencing.py` + `tests/test_pushcomp.py` together **46/46** —
  every file this change touches or that reads `is_satin_candidate`/
  `Sf5200f3f`/the flat-lane goldens directly, all green, 0 failures. Engine
  `node --test` re-verified unaffected: **283/283**, confirming this pass is
  Python-only (`git status` shows no `src/`/`app/` changes).
- **Fill row spacing (law 19)** — unresolved two-population finding: the
  0.20mm figure is a satin-rail artifact for one file population (refuted)
  but looks like a genuine denser pitch on 43 commissioned cap logos (still
  alive). Shipped `FILL_ROW_MM=0.40` unchanged pending sew-out.
- **Border tier seam-sharing — REAL FIX landed (was KNOWN LIMITATION,
  mitigated-not-fixed as of PR #67).** `stage6_border.py`'s module docstring
  used to document an unresolved defect: under `border="auto"` (or any
  per-shape border override), two different-colour shapes that abut get
  coincident outline rails, because stage 5's overlap resolution makes both
  shapes' visible edges the same line — each shape's own circuit then rides
  that line at full density, sewing a double-thick bar in two threads. PR #67
  shipped detection only (`BORDER_SEAM_SHARED`, unconditional on every
  qualifying pair); this pass adds the seam-aware suppression that PR
  explicitly scoped out, in `stage7_sequence._yield_frontage`.

  **The fix and its tie-break.** `sequence()` already commits shapes to the
  fabric in a fixed, deterministic order (nearest-neighbour within each
  colour/step group, groups in `sew_index` order) and already tracks, as it
  goes, the true visible geometry of every shape whose border tier put a
  real circuit down (`border_geom_by_id`, pre-existing from PR #67). The tie-
  break is SEW ORDER: whichever shape's border commits first keeps the seam
  at full density; before a later shape traces its own circuit,
  `_yield_frontage` checks it against every already-committed border, and for
  any shared run past the same `2 * BORDER_WIDTH_MM` threshold PR #67's
  warning used, differences a buffered band (`BORDER_WIDTH_MM +
  BORDER_HOST_MARGIN_MM`, 1.6mm at the shipped column) around the coincident
  curve out of that shape's border INPUT geometry before handing it to
  `border_runs` — "inset its border circuit locally", one of the two options
  the old docstring named. This needed no lookahead or second pass: by
  causal construction, every shape a given shape could contend a seam with
  has, by the time it sews, either already committed a real border (and sits
  in `border_geom_by_id` to yield to) or has not (nothing to yield to,
  nothing changes) — so no pair can end up with both circuits riding the
  line, or with neither covering it. `border_geom_by_id` always stores the
  TRUE unmodified visible geometry regardless of whether a shape yielded, so
  a third shape sharing a seam with an already-yielded shape still yields
  against that shape's real edge, not its already-inset one.

  **Measured before/after** (`tests/test_border.py`'s existing two abutting
  10x10mm bordered rectangles, sharing the edge x=10 the full 10mm — the PR
  #67 fixture): pre-fix, both shapes' own outer rails independently produce
  13 penetrations apiece sitting on the x=10 line — the double bar, real on
  actual stitch output, not just geometry. Post-fix, run through the real
  `sequence()`: the earlier-sewn shape (layer 0) still has all 13 on the
  line, untouched; the later-sewn shape (layer 1) has ZERO — its whole
  border retreated to x >= 11.6mm, comfortably clear of the seam — and
  `BORDER_SEAM_SHARED` no longer fires for this pair, because the pair is no
  longer wrong.

  **What is not resolved, and why the warning still exists for it.** A
  shape whose entire frontage IS a shared seam — hemmed in by an
  already-bordered neighbour on more than one side, e.g. a shape sitting in
  a hole/slot fully cut out of an earlier-sewn shape — has nowhere to
  retreat to; `_yield_frontage` falls back to the untouched geometry rather
  than deleting the shape's border outright (same "a real border beats none"
  call `stage6_border.round_inward` already makes when its own corner
  relaxation eats a shape whole), and `BORDER_SEAM_SHARED` now fires only
  for these residual, genuinely-unresolved pairs — reworded from "turn
  border off on one side" staying literally true (still the only escape for
  this case) rather than reporting a defect that no longer exists on every
  other pair. Verified end-to-end on a constructed fixture (a 2x15mm slot
  cut clean through a much larger, earlier-sewn bordered shape, sharing all
  four of its sides): the slot's raw geometry does hold a real bean-tier
  border on its own, but a 2mm-wide shape cannot survive retreating ~1.6mm
  off both long edges at once, so the fallback engages, the slot still sews
  its (un-suppressed) bean border, and `BORDER_SEAM_SHARED` correctly names
  the pair. This case was deliberately chosen to be reachable in practice —
  a simple two-rectangle abutment, checked exhaustively, turns out to be
  impossible to fully erase given how `BORDER_WIDTH_MM`/`BORDER_HOST_MARGIN_MM`
  and the "would this shape have lightened to bean anyway" threshold happen
  to be calibrated (both come out to the same 1.6mm number), so the residual
  case is real but structurally rare — a shape has to be hemmed in from more
  than one direction to hit it, not merely adjacent to one neighbour.

  Tie-break reasoning: sew order (not shape_id or area) was chosen because
  it is the only option requiring no lookahead or duplicated fill/border
  computation to implement correctly — `border_geom_by_id`'s existing,
  already-causal accumulation makes "yield to whatever is already on the
  fabric" fall out of the pipeline's own structure rather than being a
  policy bolted on top, and it composes correctly with N-way seams (a middle
  shape in a row of three yields only to whichever of its neighbours sewed
  first, never both, and never zero).

  Regression coverage, `tests/test_border.py` (17 → 22 tests): the PR #67
  fixture rewritten to measure real stitch penetrations before/after instead
  of only checking the warning
  (`test_seam_sharing_is_resolved_automatically_not_just_warned`); the
  hemmed-in-slot fallback, end-to-end
  (`test_border_seam_shared_still_fires_when_a_shape_is_hemmed_in_on_every_side`);
  `_yield_frontage` unit-tested directly for the resolved, no-shared-edge,
  and fallback cases; `_border_seam_warning` unit-tested for its
  pairs/count/message construction. The negative case from PR #67 (a 6mm gap,
  and border off) is unchanged and still passes.

  Targeted verification: `tests/test_border.py` (22/22) plus every other
  test file that imports `stage7_sequence`
  (`test_chaining.py`, `test_planning.py`, `test_pushcomp.py`,
  `test_run_tier.py`, `test_shape_overrides.py`, `test_stage6_detail.py`,
  `test_stage6_sketch.py`, `test_stage6_streamline.py`,
  `test_photo_sequencing.py`, `test_stages.py`) plus both byte-identical
  golden suites (`test_flat_lane_byte_identical.py`,
  `test_shapefield_byte_identical.py`) — 233 tests, 0 failed, run directly
  rather than assumed from a full-suite pass. A design with no seam-sharing
  bordered pair takes the identical `_yield_frontage(geom, {}, ...) ->
  (geom, [])` no-op path every existing border call already took, so this
  change carries no byte-identity risk for the common case by construction.
- **Appliqué tier (`stage6_applique.py`, 4-layer placement/cutting/tackdown/
  cover, wired into `stage7_sequence` and reachable through the service with
  no gating) — audited for the first time this pass; had never appeared in
  this doc despite being fully shipped and reachable.** Followed this file's
  standing hardening methodology (`docs/hardening-closeout-2026-08-02.md`):
  re-derive the module's own geometric claims from real fixtures and
  synthetic constructions, adversarially, rather than trust the shipped
  suite's own 44 assertions. Two real, confirmed defects found; both fixed,
  with new regression tests (44 → 49 in `test_applique.py`, all measured off
  emitted stitch points, house convention).

  **Fixed — the scissors-fit / hole-trim gates were blind to bottlenecked
  shapes.** `min_inscribed_diameter` (`polylabel`'s single largest inscribed
  circle) fed both `APPLIQUE_CUTTING_LINE_SUPPRESSED` ("scissors don't fit
  under 12mm") and `APPLIQUE_FORCED_PRE_CUT` (a hole's own trim floor). That
  measure answers "how big is the best spot in this shape", not "can
  scissors get all the way around it" — the two coincide only on the
  convex/star-shaped fixtures the shipped tests use (a plain disc, a
  centred-hole donut). Constructed a synthetic "dog bone" — two 20mm circles
  joined by a 3mm neck, a realistic silhouette for a real logo (barbell,
  bone, wrench, any letterform with a narrow waist) — and measured
  `min_inscribed_diameter` reporting **19.94mm** (one lobe's own circle),
  with the scissors gate never firing, even though nothing wider than 3mm
  can actually pass through the neck. Same failure independently confirmed
  on an off-centre ring (hole not centred in its outer boundary): the ring's
  thin side is 5mm, `min_inscribed_diameter` reports **24.99mm** because
  `polylabel`'s one point lands on the ring's fat side. Fix: a new
  `narrowest_passage_diameter` bisects the erosion radius at which the shape
  first changes topology (a new exterior piece appears, or an interior ring
  merges into the exterior) — the standard morphological bottleneck
  definition — and now feeds both gates. Verified it is a strict refinement,
  not a behavior change on ordinary shapes: matches `min_inscribed_diameter`
  exactly (± 0.01mm) on a plain square and the existing `SMALL_DISC`/donut
  fixtures the shipped tests already pin, so both pre-existing tests pass
  unchanged. New tests: the dog-bone and off-centre-ring reproductions
  above, plus an explicit "must not move the number on ordinary shapes"
  regression.

  **Fixed — pre-cut's default tackdown silently sewed as a zero-width run,
  not the documented zigzag/E column.** §2.7 gives zigzag/E tackdowns a real
  WIDTH ("positioned by column width, centered on the line") — a straddling
  column that compresses the fabric, distinct from run/double-run's single
  line, and the spec singles out knit/jersey as needing it because "a run
  lets the knit roll." `tackdown="zigzag"` is the pre-cut MODE'S OWN DEFAULT
  (`applique_steps` resolves `tackdown=None` to `"zigzag"` whenever
  `mode=="pre_cut"`), so this was hit on every pre-cut design nobody
  overrode the tackdown type on — not an edge case. Measured directly:
  before the fix, every tackdown point for a pre-cut piece landed within
  1.5e-15mm of `s_tack` (a hairline, i.e. a plain running stitch); after,
  the points spread over 2.01mm, matching `min(APPLIQUE_TACK_WIDTH_MM,
  W_cover - 2*m_bury)` — §2.7's own hard vendor constraint — exactly.
  `machine.APPLIQUE_TACK_WIDTH_MM` existed as a constant and was read by no
  code path before this. Root cause: `applique_steps` called `_run_layer`
  unconditionally for every tackdown type, and the only branch inside it was
  the pass count (2 for `"double_run"`, else 1) — so `"zigzag"` fell through
  identically to `"run"`. Fix: a new `_zigzag_tack_layer` (built on the same
  `_rail_column` column emitter `_cover_layer` was refactored onto, so the
  cover's own proven geometry — rail alternation, corner filleting, closure
  overlap — is reused rather than duplicated) is dispatched for
  `tackdown in ("zigzag", "e_stitch")`; run/double-run are unchanged and
  pinned by a new regression to stay a single line. New tests:
  `test_pre_cut_tackdown_is_a_real_column_not_a_zero_width_run`,
  `test_run_and_double_run_tackdowns_stay_a_single_line`.

  **Confirmed correct, independently re-derived (not just re-read from the
  shipped tests):** the tolerance-stack algebra in `solve_cover_width`/
  `cover_rails` (hand-recomputed for tight/normal/loose against §2.3's
  published validation table, matches to the number); overlap detection
  still fires `APPLIQUE_PIECES_OVERLAP` even when one of the two pieces
  falls through `APPLIQUE_NO_FABRIC_VISIBLE` (built a standalone two-
  `PlannedRegion` harness — a 40mm square overlapping a 2.5mm ribbon — since
  this exact "goes silent on the case that matters" defect is what a prior,
  differently-numbered commit of this same tier was found to have in
  `hardening-closeout-2026-08-02.md`; it does **not** reproduce on this
  repo's actual `stage6_applique.py`/`stage7_sequence.py` history, a
  different lineage than that doc audited); thread-contiguity and the "does
  applique ever no-op on real art" claims from that same prior doc, spot-
  checked on this repo's 3 real appliqué-eligible fixtures
  (`logo_whitebg.png`, `logo_alpha.png`, `ribbon_curve.png`) × 3 garments —
  all 9 combinations produce output that differs from `applique=False`
  (i.e. the tier is never a silent no-op here) and none show the "thread
  abandoned then picked up again" fragmentation that doc described for its
  own commit.

  **Follow-up, 2026-08-06: two of the three "confirmed but not fixed" gaps
  below are now fixed, the third stays open by design.** Same standing
  discipline as the first pass — real geometry measured before/after on
  `SHIELD` (a concave shield polygon), `BIG_SQUARE`, and a plain circle,
  not trust that tests pass. New regression tests, 49 → 54 in
  `test_applique.py`.

  **Fixed — `APPLIQUE_COVER_PULL_COMP_MM` (0.20mm, §2.8) now compensates
  the cover satin; it was defined and applied by no code path.** The same
  effect `Fabric.pull_comp_mm` compensates for on an ordinary satin column
  (Law 24: thread tension pulls each cross's two penetrations together, so
  a column sews narrower than digitized) was uncompensated on the one
  column type that deliberately does NOT go through stage 5's fabric pull
  comp — `applique_pass` passes the raw artwork polygon on purpose, because
  B has to stay the exact tolerance-stack reference point, not something a
  fabric preset already grew. Fix: `_cover_layer` now widens the column it
  actually stitches — `c_in -= pull`, `c_out += pull` — the same direction
  stage 5's `poly.buffer(pull)` widens an ordinary satin ribbon (confirmed
  against `Fabric` "pique_knit", pull_comp_mm 0.3: a 4.5mm bar sews at
  5.1mm, `tests/test_pushcomp.py`). Measured on `SHIELD` at the trim-in-place
  default: cover rails moved from (-1.50, +1.50) to (-1.70, +1.70) — exactly
  `g.c_in - 0.20` / `g.c_out + 0.20` — a 3.00mm design now sewing a 3.40mm
  column. `AppliqueGeometry.c_in`/`c_out`/`width_mm` are deliberately left
  at the solved, uncompensated values, because every gate
  (`edge_headroom_mm`, `bury_mm`, §2.12's checks) and every other test in
  the file measures against the DESIGNED width, not the sewn one — and it
  is cover-only: pre-cut's zigzag tackdown shares `_rail_column` with the
  cover but §2.8's row is specific to layer 4, so the tackdown's own width
  (`min(APPLIQUE_TACK_WIDTH_MM, W_cover - 2*m_bury)`, still 2.00mm at the
  default) is unchanged and pinned by a new regression. New tests:
  `test_cover_pull_comp_leaves_the_solved_geometry_and_the_tackdown_alone`,
  and `test_cover_straddles_the_edge_and_buries_the_tackdown` updated (its
  old assertion, `min(cover) == g.c_in`, is exactly the uncompensated
  number pull comp now moves past).

  **Fixed — `_cover_layer`'s closure overlap now reads
  `APPLIQUE_CLOSURE_OVERLAP_STITCHES` (6) instead of inheriting
  `BORDER_CLOSURE_OVERLAP_MM` (1.40mm) from the border module.**
  Investigated first, because at the 0.40mm cover spacing the two numbers
  were already close — 1.40mm / 0.20mm-per-station rounds to 7 stitches,
  one more than the appliqué constant, and both sit inside Stahls'
  published 4–8 stitch window, so the substitution was never a visible
  defect. Fixed anyway: it was a coincidence resting on
  `APPLIQUE_COVER_SPACING_MM` staying 0.40mm (nothing enforced that), not a
  read of the appliqué tier's own §2.8 number, and the fix sidesteps a
  second, independent imprecision — `_loop_stations` divided the mm
  distance by a per-ring arc-length step that varies with ring geometry,
  so the exact stitch count could drift shape to shape even at a fixed
  spacing. `stage6_border._loop_stations`/`_satin_loop` gained an
  `overlap_stitches` param (an exact station count, bypassing the
  mm-divided-by-step path) that `_cover_layer` now passes; every other
  caller (border's own outline, the pre-cut zigzag tackdown) leaves it
  `None` and is provably unchanged (`tests/test_border.py`,
  `test_run_and_double_run_tackdowns_stay_a_single_line`,
  `test_pre_cut_tackdown_is_a_real_column_not_a_zero_width_run` all still
  pass byte-for-byte). Measured on a plain 20mm-radius circle: the
  appliqué-specific overlap emits exactly one fewer cross than the
  border-inherited one it replaced (688 vs. 689). New test:
  `test_cover_closure_overlap_reads_the_appliqué_specific_stitch_count`
  (monkeypatches the constant and confirms the emitted cross count moves
  with it exactly — a proof the old code, which read nothing, could not
  have passed).
  `APPLIQUE_OVERLAP_ALLOWANCE_FRAC` (0.5) is a **different, unrelated**
  constant despite the similar name and was investigated separately: it is
  §2.11's Wilcom number ("cutting overlap = half the cover width") for
  Mode B multi-piece batching — how one piece's cutting boundary dilates
  into a neighbour it overlaps — not how a single piece's own cover
  circuit overlaps its own start. Mode B is explicitly not built
  (`applique_pass`'s own docstring: "Mode B batching... is NOT built");
  `APPLIQUE_OVERLAP_ALLOWANCE_FRAC` correctly stays unread until it is, and
  wiring it into `_cover_layer` would have been the wrong fix for the wrong
  gap. Left alone, now documented in `machine.py` next to the constant.

  **Fixed — `max_cover_width`'s 5.0mm clamp (and the 2.5mm floor) no longer
  silent.** `solve_cover_width`'s own `"clamped"` field has always recorded
  whether the width it returned is the tolerance stack's own request or one
  of the two hard bounds; no caller read it. New code
  `APPLIQUE_COVER_WIDTH_CLAMPED` (`warnings_codes.py`), fired by
  `check_gates` and aggregated by `applique_pass` exactly like the other
  four appliqué gates, reporting which bound (`"floor"` or `"ceiling"`)
  fired. Also fixed in the same pass: `solve_geometry`'s override branch
  (`width_mm=...`, `PipelineConfig.applique_cover_width_mm`) was carrying
  the PRE-override `"clamped"` verdict forward unchanged, so a caller
  override that itself blew past the ceiling — config.py's own documented
  "escape hatch... still clamped to [2.5, 5.0]" — was invisible to the new
  code too; `"clamped"` is now recomputed against the actual requested
  override. This override path is the practically reachable one: the
  solver's own W_req never reaches either bound at any published trim
  discipline (§2.3's table tops out at 4.0mm, loose), confirmed directly —
  `solve_cover_width(m_edge=3.0)` is the one way found to make the solver
  itself clamp (W_req 7.7mm → 5.0mm). New tests:
  `test_solve_cover_width_can_clamp_from_the_tolerance_stack_itself`,
  `test_a_clamped_cover_width_is_warned_not_silent`,
  `test_a_forced_cover_width_override_warns_end_to_end` (through
  `applique_pass` on the benchmark logo at `applique_cover_width_mm=8.0`).

  **Fixed, 2026-08-07: §2.12's pre-cut `min_inscribed_diameter >= 8mm` gate
  (scissors/placement floor) is now checked — it was never checked before,
  only the 12mm trim-in-place floor was.** Same shape of change as the
  `max_cover_width` clamp fix directly above: a geometric measurement, the
  pre-existing threshold constant (`APPLIQUE_MIN_INSCRIBED_PRECUT_MM`, 8.0,
  `machine.py` — already there, read by no code path), a new warning code
  (`APPLIQUE_PRECUT_TOO_NARROW`, `warnings_codes.py`), wired into
  `check_gates` and aggregated by `applique_pass` exactly like the other five
  appliqué gates. Fed by `narrowest_passage_diameter`, not
  `min_inscribed_diameter` — the same choice the trim-in-place gate already
  made and for the same reason (a dog-bone-shaped piece has one lobe's own
  huge inscribed circle and a neck `min_inscribed_diameter` never has to
  visit). Scoped strictly to `geom.mode == PRE_CUT`, mirroring the existing
  `geom.mode == TRIM_IN_PLACE` gate immediately above it in `check_gates` —
  confirmed mutually exclusive, not merely both-correct-in-isolation: a
  synthetic dog-bone with a 6mm neck (under pre-cut's 8mm floor AND
  trim-in-place's 12mm floor) fires `APPLIQUE_PRECUT_TOO_NARROW` and NOT
  `APPLIQUE_CUTTING_LINE_SUPPRESSED` under `mode=PRE_CUT`, and the reverse
  under `mode=TRIM_IN_PLACE` (`test_precut_and_trim_in_place_scissors_
  floors_never_both_fire`). No real fixture needed for the end-to-end proof
  either: the benchmark logo already has the 1.0mm² / 1.07mm-inscribed
  region `test_pre_cut_costs_one_fewer_stop_per_piece` documents, so
  `applique_mode="pre_cut"` on real artwork fires the new code with no
  construction (`test_a_precut_design_warns_when_a_piece_is_too_narrow_to_
  hand_cut`), and the same artwork under `trim_in_place` never fires it.
  New tests: `test_a_precut_piece_clears_the_scissors_floor_by_default`,
  `test_a_narrow_precut_piece_is_warned_not_silent`,
  `test_precut_and_trim_in_place_scissors_floors_never_both_fire`,
  `test_a_precut_design_warns_when_a_piece_is_too_narrow_to_hand_cut` (54 →
  58 in `test_applique.py`, all passing, targeted run not assumed from a
  full-suite pass). The physical rationale for the specific 8mm number is
  still not traced to a stated vendor constraint anywhere this audit found
  (unlike the tackdown-width fix's `W_tack <= W_cover - 2*m_bury`) — that
  gap is in the *number*, not in whether the gate fires; the constant itself
  was untouched, only its being read.

  **Still confirmed but NOT fixed — genuinely out of scope, unchanged from
  the first pass:**
  - `applique_cover="zigzag"` and `"e_stitch"` are accepted config values
    but produce **byte-identical stitch geometry** to `"satin"` — re-verified
    directly this pass (same point-for-point equality on `SHIELD`, unaffected
    by the pull-comp/closure-overlap fixes above, which apply uniformly
    regardless of `cover`). `cover` still only changes the printed worksheet
    label. §2.8 calls zigzag cover "a genuinely different aesthetic, not a
    cheap satin" at a different spacing, and E-stitch a different stitch
    ORDER (a comb pattern) — neither is built. Still not fixed because the
    spec itself gives two different candidate zigzag spacings (1.69mm SPI
    vs. Melco's 3.0mm preset) as alternatives with no stated tie-break, and
    E-stitch's comb order is a real algorithm with no spec to follow here.

  **Caveat, stated plainly:** this is 3 real fixtures and a handful of
  targeted synthetic constructions (dog-bone, off-centre ring, two-piece
  overlap harness, a plain circle for the closure-overlap count), not a
  corpus sweep, and it covers the geometry/gate layer only — no sew-out,
  same standing caveat as every other tier in this doc. `trim_discipline`/
  `material`/`placement` combinations were exercised through the existing
  shipped tests' parametrization, not independently re-swept by either
  pass.

Every claim about visual/sew quality beyond internal geometry checks is
**pending sew-out** — see the cross-cutting item above.

**Next step:** the chaining fix, the gradient angle-fragmentation fix, the
gradient region-count fragmentation fix (PR #45, above — two-fixture
validation caveat noted there), the full `BACKGROUND_ENCLOSED` stack
(including the opaque-alpha fix, PR #22), and the contour bare-core shrink
(PR #27) are all landed. The opaque-alpha fix has now been watched running
through the actual Studio browser UI (2026-08-07, live via Playwright MCP —
see the caveat note above, now closed); what's left to close this out is
scheduling the first sew-out session. M0 of the DT-first
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

**Text-cluster detection + regularized lettering fallback — merged 2026-08-05
(PR #63, Steps 0–6; PR #64, Step 7).** A real, cited gap the small-shape
rescue path (above) always had: `stage3_segment.py`'s `small_shape_rescue`
stops a logo's small lettering (the benchmark subline) from being dropped,
but treats every glyph as an independent noisy blob — nothing distinguished
"this is a word" from "this is nine unrelated small shapes," and nothing
made a detected word's letters share one visual weight. Three new pieces,
all geometry-only, no OCR — **still true of detection and of what
regularization decides to redraw**; a later, additive safety layer (below,
2026-08-07) reads an OCR CONFIDENCE NUMBER to sanity-check regularization's
own output, never a decoded character, so the "no OCR" design principle this
feature was built on (`textcluster.py`'s own top-of-file docstring) still
holds in the sense that mattered when it was written — no text is ever
recognized, read, or auto-filled:

- **Detection** (`digitizer_core/textcluster.py`, new module):
  `detect_text_clusters`, a post-vectorization pass (wired into
  `pipeline.py` right after `tag_enclosed_background`, same "computed fact,
  before shape edits" ordering) that groups `rescued_small_shape`-flagged
  Regions (a new `Region.meta` marker this feature added) by proximity,
  bbox-height similarity, and stroke-width similarity — the last measured
  via `shapefield.build_shape_field`, a third independent consumer of that
  module alongside `stage6_satin` and the `shape_lens.py` instrument. A
  qualifying group (>=3 members; letters come in groups, and this doc's own
  research found 1–2 similarly-sized nearby shapes far too common a
  coincidence — e.g. a belt buckle's two rivets — to read as text alone)
  gets tagged `text_candidate`/`text_cluster_id`/`text_cluster_stroke_mm` in
  `Region.meta`; an ambiguous group is left untagged entirely (fails open,
  same "uncertainty resolves to no behavior change" discipline
  `tag_enclosed_background` already established). Exposed read-only over
  HTTP (`digitizer_service/app.py`'s `_review_payload`, no `_OVERRIDE_KEYS`
  entry — same category as `layer`/`enclosed_background`, never
  client-submitted). Verified against the real benchmark fixture, not just
  synthetic ones: `enthusiast_logo.png`'s subline at 90mm tags >=10 of its
  own rescued shape_ids into one cluster.
- **Regularization** (`textcluster.regularize_text_clusters`, same module,
  wired immediately after detection): redraws a tagged member's polygon as a
  fixed-radius buffer around its own skeleton, sized to the cluster's shared
  median stroke half-width, so a detected-but-unconverted word reads as one
  consistent line weight instead of independently-noisy glyphs. A genuine
  geometry change (unlike detection's pure tagging), so it fails open onto
  the ORIGINAL untouched polygon (`text_cluster_regularize_skipped`)
  whenever the buffered result can't be trusted — too small to sew, an
  invalid buffer, a degenerate skeleton. **Correction made mid-build, worth
  recording:** the first design draft assumed a per-shape stitch-width
  parameter existed to feed a cluster median into; a spike found the run
  tier's actual generator (`stage6_border.run_outline`) has no such
  parameter at all — it traces each shape's own polygon ring exactly at
  fixed global stitch spacing — so the real lever had to be geometric
  (the skeleton-buffer redraw actually shipped), not a stitch-generation
  tweak. Branching glyph skeletons (a letter like "E"/"T"/"R" does not
  reduce to one path) are handled by reusing `stage6_satin`'s own tested
  skeleton-decomposition machinery (`_skeleton_edges`/
  `_merge_through_junctions`/`_prune_spurs`, the same tool `extract_strokes`
  already uses) rather than a narrower non-branching-only scope — verified
  on the real fixture: 10 of the subline's 14 members have branching
  skeletons, and all 14 buffer into single valid, sewable polygons.
  **No longer unconditional, fixed 2026-08-06** (this doc's top entry has the
  full evidence): the buffer is now selective, not the default-always-on
  treatment for every member. A member already within 15% of the cluster's
  target stroke half-width, or one whose own polygon already has a real
  interior ring, is left completely untouched instead of being replaced by
  a cruder buffered approximation — a real render (`debugviz.stage6`) showed
  the old unconditional version was making an already-clean subline read
  LESS legibly, not more consistently, and could never represent a real
  letter counter (an "R"/"P" bowl) at all. `flat_lane_golden.json` moves for
  exactly that one fixture — this specific slice's original claim, "the
  other 3 entries are byte-identical," still holds; the 2026-08-06 fix could
  not be verified against that golden locally (see this doc's top entry: the
  file is separately, pre-existingly corrupted in this checkout).
  **Additional safety layer, 2026-08-07** (this doc's top entry has the full
  evidence): an OCR-confidence quality gate now sits on top of the
  selective checks above. Both are geometric proxies for "would this redraw
  read worse" — this measures it directly, scoring the member's own
  rasterized crop with Tesseract before and after the proposed buffer and
  discarding the buffer if confidence drops >=20 points. Only a confidence
  NUMBER is read, never decoded text (`data["text"]` is never accessed,
  code-inspected and regression-tested). On the real benchmark fixture this
  catches the one case the checks above still let through: the +30%-off "I"
  the prior fix's own docstring cites drops from 77.0 to 0.0 OCR confidence
  when buffered — Tesseract finds no text at all in the result — and this
  gate now blocks it, falling back to the original polygon.
- **Studio side (area 5 has the full detail):** a "looks like text" badge
  and a per-cluster "Convert to text" action that creates a real, empty
  text element — the user types the actual word and picks a font, nothing
  is ever auto-filled that could be silently wrong.

Photo/gradient design classes are untouched by construction (this feature
only acts on `rescued_small_shape`-flagged Regions, a flat-lane-only
concept); every existing byte-identical golden not involving
`enthusiast_logo.png` is unaffected. Out of scope, on purpose: general
shape-primitive recognition (classifying arbitrary shapes as circle/
rounded-rect/star, for a manual-edit "snap to clean shape" assist or to
strengthen the satin/fill classifier) — that's the separate, already-
tracked DT-first classifier thread above (M0/M1 landed, M2/M3 blocked on
the corpus), not duplicated here. Full detail, including the corrected
design history: `docs/superpowers/specs/2026-08-05-text-cluster-detection-
design.md` and `docs/superpowers/plans/2026-08-05-text-cluster-detection.md`.

**Classical-CV strengthening pass, 2026-08-07 (three tracks scoped, two
built, one investigated and declined — all measured, not assumed):**

- **Candidate filters** (`_candidates`, in `textcluster.py`): previously
  compared only each shape's MEAN stroke half-width for cross-shape
  similarity, discarding the per-pixel distribution `shapefield.
  build_shape_field` already computes. Three more filters now tighten the
  same function, each calibrated against `enthusiast_logo.png` @ 90mm
  PRE-regularization (the actual geometry `_candidates` sees — read fresh
  via `run_stages` with `regularize_text_clusters` patched to a no-op, not
  the pipeline's final, already-regularized output, which would have hidden
  the real per-glyph variance): **stroke-width coefficient of variation**
  (`STROKE_CV_MAX = 0.32`) — the fixture's 14 real letters measure CV
  0.027-0.235, three sibling rescued-but-not-word fragments measure
  0.401-0.461, a clean gap; **aspect-ratio bounds** (`ASPECT_RATIO_MIN/MAX
  = 0.05/1.4`) — the same 14 letters are portrait 0.107-0.964, the same 3
  fragments landscape 1.778-2.125; **bbox-nesting exclusion**
  (`_drop_nested`) — the same 3 fragments each sit bbox-nested inside one of
  the 14 real letters, a third, independent confirmation they're
  segmentation artifacts. On this fixture the three fragments were already
  excluded from the tagged cluster by the pre-existing height-similarity
  gate (so this pass doesn't move `enthusiast_logo.png`'s own golden output
  — confirmed, `test_flat_lane_byte_identical.py` stayed green) — the new
  filters are defense-in-depth against a case that DOES independently
  confirm on real evidence rather than a fix for an observed false positive
  on this one fixture. One real finding worth flagging: this repo's own
  existing synthetic test fixtures (plain axis-aligned rectangles) measure
  WORSE on stroke-width CV than genuine font glyphs of similar proportions —
  a solid rectangle's medial axis is one straight segment, so end-taper
  (universal to any stroke's free tip) is a much larger fraction of its
  total skeleton length than a real letter's more complex one. The original
  0.9mm-wide test rectangles (CV 0.458) were thinned to ~0.15-0.35mm (CV
  0.21-0.29) so they clear the new, real-measured threshold — full reasoning
  in `textcluster.py`'s own module docstring and `test_textcluster.py`'s.
- **Shape Context glyph-plausibility gate** (new module
  `digitizer_core/shapecontext.py`, ~150 lines, zero new dependency —
  `scipy.optimize.linear_sum_assignment` is already in the tree): a
  from-scratch implementation of Belongie/Malik/Puzicha 2002's Shape Context
  descriptor (sample boundary points incl. holes, log-polar relative-
  position histograms, Hungarian-algorithm point correspondence, chi-squared
  cost). Wired into `regularize_text_clusters` as a SECOND guard after the
  existing sewability/validity check: a buffered replacement can be
  perfectly valid and sewable while still being structurally wrong (a target
  radius mismatched from a member's own true stroke — already possible
  within the pre-existing `SIMILARITY_RATIO=0.5` floor's own looseness —
  inflates or blows out real structure). `SHAPE_CONTEXT_MAX_DIST = 0.25`,
  calibrated against the real fixture's 14 members (which all regularize
  cleanly today, distance 0.033-0.106) plus synthetic matched-vs-mismatched
  sweeps on a branching ("L") letterform (a correctly-matched radius scores
  0.173; a 2x-mismatched one — realistic given `SIMILARITY_RATIO`'s own
  floor — scores 0.285 with 2.4x area bloat). A gated skip sets a new,
  distinct `text_cluster_regularize_shape_changed` flag (alongside the
  pre-existing `text_cluster_regularize_skipped`) and the measured distance
  is recorded either way (`text_cluster_shape_context_dist`) for
  diagnostics. On `enthusiast_logo.png` itself none of the 14 real members
  trip the gate — golden output unchanged, confirmed.
- **MSER — investigated, deliberately NOT built.** Considered both upstream
  (`stage3_segment.resolve_small_regions`, to catch lettering absorbed into
  a bigger neighbor before ever becoming its own `rescued_small_shape`) and
  as a direct per-shape signal in `textcluster.py` (`detect_text_clusters`
  already receives `p: Prep`, whose `p.rgb` is the real prepped raster —
  unused plumbing that would have made this cheap to wire). Measured
  directly, not assumed: `cv2.MSER_create().detectRegions()` returns ZERO
  regions on `enthusiast_logo.png`, both the raw source file and the
  pipeline-prepped raster, at default params and swept down to 1px
  `min_area`/`delta`. Root cause is structural, not a fixture accident: the
  raw source has exactly 3 unique grayscale values total (2 in the subline
  text region specifically — pure foreground/background, no antialiasing).
  MSER's mechanism needs a multi-level intensity landscape to sweep
  thresholds across; a 2-3-value hard-edged image gives its own internal
  stability check nothing to measure. This isn't one unlucky fixture: this
  module's own scope is flat-lane art by construction ("this feature only
  acts on `rescued_small_shape`-flagged Regions, a flat-lane-only concept,"
  per this entry's own text above) — hard vector-style edges are the norm
  here, not the exception, and MSER's real strength (photographs, lighting
  gradients, JPEG blur) is the opposite domain. Full reasoning in
  `textcluster.py`'s own "MSER" docstring section.

Tests: `tests/test_shapecontext.py` (new, 8 tests — translation/scale
invariance, deliberate non-rotation-invariance, minor-vs-major structural
change discrimination, hole-appearing sensitivity, degenerate-input
handling); `tests/test_textcluster.py` gains 6 (3 candidate-filter isolation
tests, a nesting-tie test, the shape-context gate's matched/mismatched
integration test) plus its existing 13 re-validated against the thinned
fixture geometry. 222 tests total passing across
`test_textcluster.py`/`test_shapecontext.py`/`test_pipeline.py`/
`test_flat_lane_byte_identical.py`/`test_shapefield_byte_identical.py`/
`test_satin.py`/`test_service.py`.
**OCR-suggested text (2026-08-07, not yet merged — branch TBD, opened as a
draft PR against `main`).** Kent's explicit call: "do not set OCR aside...
this should become a focus." Everything above this paragraph is geometry-
only detection, deliberately OCR-free — that is unchanged; this adds a
strictly LATER, read-only, additive pass, not a relaxation of it.
`textcluster.ocr_suggest_text` (new function, same module, wired into
`pipeline.py` immediately after `regularize_text_clusters` so it reads
whichever polygon the design will actually sew/export) runs Tesseract
(`--psm 10`, single-character mode — same tool, same PSM choice, as the
independent, not-yet-merged `text-cluster-ocr-confidence-gate` branch's
regularization-safety gate, which this reuses the RASTERIZE-AND-SCORE
TECHNIQUE from but not any call path — that gate's job is a boolean "would
this redraw read worse," `data["text"]` never read; this pass's job is
"what does this glyph probably say," both text and confidence surfaced) on
each ALREADY-tagged member's own rasterized crop, and stamps
`Region.meta["ocr_char"]`/`["ocr_confidence"]` — a single best-guess
character plus Tesseract's own 0-100 confidence, or `None`/`None` when the
measurement itself fails (missing binary, degenerate crop). Exposed
read-only over HTTP (`_review_payload`'s `ocr_char`/`ocr_confidence`, same
`_OVERRIDE_KEYS`-free category as `text_candidate`). The service takes NO
position on "good enough" — it reports a raw per-member measurement; the
confidence GATE is entirely Studio's call (area 5 below has the full UX
detail: `OCR_SUGGESTION_MIN_CONFIDENCE`, the badge, the `textSource`
provenance flag). New system dependency: `tesseract-ocr` (Apache-2.0,
`pytesseract` wrapper), added to `requirements.txt`/`pyproject.toml`/CI's
digitizer job/`README.md` "Setup" — missing it fails open (every OCR field
reads `None`, Studio's gate then behaves exactly like a below-threshold
read, i.e. exactly like before this feature existed). New tests:
`tests/test_ocr_suggest.py` (8, hand-built dot-matrix block letters — no
system-font dependency, same technique `test_ocr_gate.py` on the sibling
branch uses), plus wiring tests in `test_pipeline.py` (real benchmark
fixture, full pipeline) and `test_service.py` (real HTTP seam). Full
digitizer suite run locally against this change: **893 passed, 3 skipped**
(the same 3 pre-existing container-environment goldens COOKBOOK.md's
"Running things" already flags — the pass count grew organically past that
doc's last-recorded 654/658 snapshot from other, already-merged work
between then and now, not from this PR alone; re-verify rather than diffing
against that stale number directly). **A real, measured cost worth flagging
plainly, not burying:** this same local run took ~20 minutes, roughly double
COOKBOOK.md's documented 7-11 minute baseline — `ocr_suggest_text` runs
unconditionally on every tagged cluster member across every pipeline
invocation the suite makes (Tesseract's Python binding shells out per crop),
and several existing tests reuse the same text-cluster-tagging real-image
fixtures many times over. No test failed; this is a suite-runtime cost, not
a correctness one, but a follow-up should watch whether it's worth gating
behind a `cfg.extra[...]` opt-in flag (the pattern `shapefield`/`photo_prep`
already established for costly additive work) if a future single-`/digitize`
request's added latency — not measured here, only the test suite's
cumulative cost was — turns out to matter in practice. Out of scope,
unchanged from the text-cluster-detection entry above: `fontKey` is NEVER
auto-picked by anything downstream of this — OCR gives characters, never a
typeface match, regardless of confidence.

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

**The underlay-style dropdown's live-browser check — CLOSED 2026-08-06.**
Verified live via Playwright MCP against a real running Studio + digitizer
service: an already-digitized `enthusiast_logo.png` project had two
fill-tier shapes carrying the "Underlay style" control this section used to
flag as unchecked. Set one (33.7 mm², `#0134`) from "Auto underlay" to
"None" and clicked "Apply layer changes" — the design's total stitch count
dropped 2,650 -> 2,016 (a real, substantial re-stitch through the actual
service, not a stale UI value), confirming the control's whole round trip:
dropdown -> `shape_overrides.underlay_style` -> real `/digitize` call ->
updated stitch plan -> updated Studio state. Screenshot on file
(`.playwright-mcp/underlay-style-applied.png` in that session's worktree).
This was the last of area 5's four `_OVERRIDE_KEYS` controls without its
own live-browser proof; border/tier/fill-angle/boundary/merge-selection/
split were already covered by e2e specs or prior live sessions.

**A genuinely SUCCESSFUL merge's live-browser proof remains open, and is
harder than this doc previously scoped it** — re-investigated 2026-08-06,
source-level, not by assumption. Two candidate fixes this doc floated
("a purpose-built fixture image" or "a bridging/convex-hull merge
strategy") were checked against the real code before attempting either:

- **The "just recolor one shape to match, then merge" shortcut does NOT
  work**, and is worth ruling out explicitly so a future pass doesn't
  re-try it: `pipeline.run_stages` calls `apply_shape_merges` BEFORE
  `apply_shape_edits` on every single pass, so a merge always validates
  against each shape's ORIGINAL `thread_number` from stage 4, never a
  `shape_overrides` recolor — recoloring first and merging second (even as
  two separate Apply steps) never changes what the merge check sees, since
  each fresh `digitize()` call re-derives colors from scratch before any
  override is applied within that same call.
- **The deeper reason a "purpose-built fixture" is hard, confirmed by
  reading `stage3_segment.py` directly:** its connected-component pass runs
  PER FINAL THREAD LAYER (`for layer in range(len(quant.thread_indices))`),
  after any SLIC/RAG merging in `stage2_photo_segment.py` has already
  happened — so two regions reaching that stage with the SAME final thread
  assignment are fused if they're pixel-adjacent, regardless of whether the
  photo segmenter's own ΔE00 merge threshold (`MERGE_DELTAE00_THRESH`)
  considered them "different clusters" upstream. This is not lane-specific
  (the doc's prior phrasing implied only the flat lane was affected) — it's
  the same connected-component step either way. The only geometrically
  possible opening left is a pair of regions that are NOT pixel-adjacent at
  stage 3 (so they survive as separate shapes) whose VECTORIZED polygons
  (stage 4) happen to end up touching or overlapping anyway — a subtle,
  not-yet-attempted fixture-engineering target, not a quick win.
- **The fixture WAS attempted, same day, follow-up — and empirically
  falsified with real numbers, not just theory.** A gradient-classified
  probe image (two identical bright-green squares on a smooth ramp, forcing
  the SLIC+RAG lane) swept the gap between the squares from 0 to 40px
  (0-2.4mm at the probe's 16.67 px/mm) and measured the resulting regions
  directly via `digitizer_core.run_stages` + shapely, not through the
  browser. Result: **there is no gap value that produces two separate
  same-thread shapes close enough to plausibly vectorize-touch.** Below
  ~10px (~0.5mm) the two squares fuse into ONE region every time (SLIC's
  own superpixel averaging blends them before RAG ever runs — the
  superpixel diameter at `SLIC_N_SEGMENTS=1200` over a 1000x650px image is
  ~23px, comparable to or larger than the probe's own square size at small
  gaps). At >=12px (~0.7mm) they separate into two same-thread regions —
  but the measured shapely distance between them is **already 0.71-0.73mm
  at the very first gap where separation happens at all**, roughly
  constant across a wide range of further gap increases (SLIC's boundary
  quantizes to its own superpixel grid, so several different raw pixel
  gaps alias to byte-identical vectorized output) before finally growing
  with gap size at 40px (1.37mm). There is no intermediate regime: it's
  "one fused shape" or "two shapes >=0.7mm apart," never "two shapes
  touching." That floor is roughly three orders of magnitude past
  `simplify_tol_mm`'s ~0.03-0.12mm-scale vectorization tolerance (the
  mechanism a 2026-08-06 pass earlier speculated MIGHT close a small gap),
  so no fixture built from ordinary artwork through the normal SLIC/RAG
  pipeline can reach the "touching" state `apply_shape_merges` requires.
  This is now a settled, evidence-backed conclusion for this codebase's
  CURRENT segmentation parameters (`SLIC_N_SEGMENTS`, `MERGE_DELTAE00_
  THRESH`, `simplify_tol_mm`) — not "not yet tried."
- **What's left is genuinely a product decision, not more fixture-hunting:**
  a bridging/convex-hull merge strategy for non-adjacent shapes (changing
  `apply_shape_merges`'s own semantics to connect two shapes that don't
  touch, not just union ones that already do) is the only path left to a
  live successful-merge proof, and it changes what "merge" means for every
  user, not just this test case — Kent's call on whether it's wanted at
  all, not something to build unilaterally to satisfy a test-coverage gap.
  Not attempted this pass.

**Convert-to-text (text-cluster detection) — merged 2026-08-05** (PR #63
Steps 6a/6b, PR #64 Step 7 e2e): a new kind of manual-editing action,
distinct from every prior one in this area — instead of editing a shape's
own geometry/style, it REPLACES a whole detected cluster of shapes with a
different kind of project element entirely (area 1 above has the detection/
regularization side).

- **`DigitizePanel.svelte`:** a "looks like text" badge per candidate row
  (honest tooltip: "no character recognition — it can be wrong"), and a
  per-CLUSTER action bar (one per unique `text_cluster_id` visible, reusing
  the merge-selection bar's `.dgp-mergebar` markup) rather than a per-row
  control — deliberately, since a converted cluster's member rows move into
  this file's existing `unstitched` row branch, which renders no per-row
  badges or buttons at all; a per-row button would vanish exactly when Undo
  needs to be reachable.
- **New coordination logic with no prior precedent in this codebase:**
  every other override here (`tier`/`border`/`underlay_style`/
  `boundary_override`/merge/split) edits or replaces state on ONE existing
  element. "Convert to text" instead creates a brand-new `type: "text"`
  project element (via a new `addSeededTextElement`, sibling to `addElement`
  in `project.js`, seeded from the cluster's bbox/color — deliberately with
  an EMPTY `text` and `fontKey: null`, so nothing is ever auto-filled that
  could be silently wrong) AND, in the same user action, patches the
  ORIGINATING digitized element (`stitched: false` per member shape via the
  existing override plumbing, plus a new `textConversions` map recording
  which cluster produced which text element — pure Studio-side provenance,
  never sent to the server, unlike the wire-bound `mergeGroups`/
  `splitLines`). `App.svelte`'s new `onConvertClusterToText` is the
  coordination point; a new `converttotext` event carries the seed up from
  `DigitizePanel` through `ContentStep`, mirroring the existing `addelement`
  event's bubbling exactly.
- **Undo** mirrors `undoMerge`/`undoSplit`'s button-swap, with one real
  difference: merge/split provenance is re-derived from the last APPLIED
  job's own warnings (because the SERVER executed those edits); a text
  conversion's provenance lives entirely in `element.textConversions`
  already, since nothing about it was ever server-executed — no round trip
  needed to know what to undo.
- **A real bug the e2e test caught, not a test-authoring mistake:**
  `ContentStep.svelte` forwarded `DigitizePanel`'s `converttotext` event up
  to `App.svelte` but never wired the same forwarding for `removeelement`
  — Svelte component events don't bubble automatically, each parent must
  forward explicitly. `undoTextConversion` dispatches `removeelement` from
  inside `DigitizePanel`; with no forward, that event had nowhere to go, so
  undo silently never removed the created text element (no crash, no
  error — just a dropped event). Fixed with the missing one-line forward;
  the real e2e run (against the live service and browser, not a mock)
  failed before the fix and passed after.
- **Verification:** `project.spec.js` (3 new tests for the seed-element
  function), `digitizer.spec.js` (5 new tests for the wire-field mapping and
  the cluster/seed pure helpers), full Studio suite 426/426 (421 pre-existing
  + 5 new, baseline re-verified via `git stash` before trusting the delta).
  `app/e2e/text-cluster-convert.spec.js` (new, sibling to
  `digitize-boundary-edit.spec.js`) drives the real service end to end:
  upload the real benchmark fixture → badge appears on >=10 shapes →
  Convert to text → lands in an empty `TextStep` with no font picked → type
  real text, pick a font → navigate back → Undo → original shapes resume
  stitching, text element gone — **run for real, 1 passed**, after the
  `removeelement` fix above. Also manually verified live via Playwright MCP
  against a running dev session on the real benchmark fixture, screenshotted.
- **Out of scope, on purpose, AS OF THE 2026-08-05 MERGE:** real character
  recognition. **Superseded 2026-08-07 by the OCR-suggested-text entry
  immediately below** — this bullet is kept, not deleted, as an honest
  record of what shipped at the time; it no longer describes current
  behavior. Auto font selection/matching to the source typeface and any
  change to the satin/fill classifier remain out of scope, unchanged.

**OCR-suggested text (2026-08-07, not yet merged — draft PR against
`main`).** UX-safety-critical, not a convenience shortcut: automation-bias
research on prefilled-vs-empty form fields found people catch errors in a
confident-looking WRONG suggestion only ~30% of the time, vs. ~75% when the
system visibly hedges — so "Convert to text" prefilling an OCR guess is only
safe if it (a) is gated on real confidence and (b) never looks like
user-authored text until a human has actually looked at it. Both are now
true:

- **The gate** (`digitizer.js`'s new `textClusterSeed` logic,
  `OCR_SUGGESTION_MIN_CONFIDENCE = 55`, Studio-side — the service reports a
  raw per-member confidence and takes no position on "good enough," see area
  1 above): the cluster's suggested text is the MINIMUM confidence across
  its own members, not a mean (a word is only as trustworthy as its worst-
  read letter; a mean would let one badly-misread character hide inside an
  otherwise-confident average — verified by a dedicated test using real
  numbers where mean and min disagree). Threshold calibrated on real
  Tesseract measurements, not assumed: every genuinely-wrong real/synthetic
  cluster measured had a MIN confidence <=7.0 (the real benchmark fixture's
  own "ENTERPRISES INC." subline, which has two real misreads, measures
  0.0); every genuinely-correct synthetic control word measured had a MIN
  >=70.0. 55 sits centered in that gap. Below the floor — including a
  pre-OCR service sending neither field at all — behavior is byte-identical
  to before this feature existed: `text: ""`, `fontKey: null`.
  `fontKey` is NEVER auto-picked regardless of confidence — OCR gives
  characters, never a typeface match, exactly as the superseded bullet
  above already established, just no longer contingent on OCR being absent
  entirely.
- **Provenance + the "unconfirmed suggestion" treatment:** a gated seed also
  carries `textSource: "ocr-suggested"` through to the new text element.
  `TextStep.svelte` renders one small, non-blocking advisory badge ("Suggested
  from image — verify before saving") above the textarea while that flag is
  set, reusing `DigitizePanel.svelte`'s existing "looks like text" badge's
  visual convention (`.dgp-lbadge`'s pill shape) plus the `--warn-text` color
  this codebase already uses elsewhere for "needs a look" states — not new
  styling invented for this one badge. The flag (and badge) clear the
  instant the user edits the textarea, in the SAME patch as the edit itself
  (`text`/`textSource` set together, one dispatch) — an unconfirmed guess
  stops being unconfirmed the moment a human has touched it, whatever they
  changed it to.
- **Verification:** `digitizer.spec.js` (new tests for the wire-field
  mapping and the gate — fills/clears at the exact threshold boundary,
  min-not-mean aggregation, missing-data-is-no-signal, left-to-right
  ordering by bbox), `test_ocr_suggest.py`/pipeline/service tests on the
  Python side (area 1). First Svelte component spec for a NON-canvas panel
  (`ManualPanel.spec.js` was the only precedent, canvas-only): a new
  `TextStep.spec.js` + `TextStep.testHarness.svelte` (same "wrap in a real
  parent to observe Svelte 5's un-exposed component-event dispatch" pattern
  ManualPanel's own harness established) covers the badge appearing,
  disappearing on edit, and never appearing for ordinary user-typed text.
  Full Studio suite green (see "Running things" for the count this pass
  observed).

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
