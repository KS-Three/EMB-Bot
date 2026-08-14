# Research backlog

**Part of [`MASTER_SCOPE.md`](../../MASTER_SCOPE.md).** Competitive and
open-source research that produced backlog items rather than status changes.
Nothing here is a live defect or a commitment — these are catalogued leads.
Each section names its own evidence doc; go there before acting on a line.

**Licensing posture, which governs everything below:** concept-level
clean-room reimplementation only. No literal copying and no near-verbatim
translation of GPL-3.0 source.

---

### Ember Design competitive research — new backlog items, not a status change

Three research passes against `emberdesign.net` (a browser-based embroidery
digitizing competitor), run 2026-08-07: a screenshot UI/UX walkthrough, an
end-to-end Chrome-extension-driven exploration of the live editor, and a
build-artifact fingerprinting pass identifying their actual client-side tech
stack and reverse-engineering their auto-digitize call path. None of it
required bypassing authentication — passes 2 and 3 read client-side
JavaScript Ember's own servers already send to any visitor's browser during
ordinary use, the same thing devtools/View Source does. Full evidence
trail, with exact formulas/library names/bug descriptions:
`docs/emberdesign-competitive-research-2026-08-07.md`.

**Three Ember docs now exist and none indexed the others** (fixed
2026-08-12): the 08-07 research pass above, a manual/pricing teardown
(`docs/ember-competitive-teardown-2026-08-09.md`), and a bundle-level
technical teardown (`docs/ember-technical-teardown-2026-08-08.md`, recovered
from Kent's Desktop and committed 2026-08-12 — it existed nowhere in the
repo). Two items from the technical one are actionable and appear in no
other document:

1. **Ember ships a client-side JS DST *writer*** in the parent app's lazy
   format-codec chunk, with an `EmbThread` class shape mirroring
   pyembroidery's. That is a second reference implementation of the codec
   our own `src/dst.js` disagrees with — and unlike pyembroidery it runs in
   a browser you can step through. Worth using as one more cross-check on
   the axis bug (the verdict is already 5-source settled; this is cheap
   corroboration, not a new gate).
2. **Fill patterns are data, not code** — each pattern is a function
   returning `[{rowOffsetMm, rowPatternMm}, …]`, 13 shipped (6 free / 7
   paid). Our fill-pattern library is the largest named gap vs Ember, and
   this is the shape that makes new patterns table entries instead of new
   algorithms. Also worth copying: `underlays[]` as an array from day one
   (they had to migrate to it) and their versioned-document migration chain
   (our `.embproj` additive migrations already work this way).

Their monetization split is relevant to the tabled billing decision: all
*manual* tooling free and unlimited, money charged for **automation** —
auto-digitize, click-to-stitch, extra fill patterns, unlimited storage
($9.99/mo). And their auto fill-angle is a one-line bounding-box aspect
check (`90 * (h >= w)`), which is the entire "intelligence" behind it — our
per-shape PCA principal axis is already ahead of the benchmark on that axis.

**The prioritization decision matters more than the findings themselves.**
Resolved via a pressure-tested discussion, not assumed: feature-parity work
is real and belongs on the roadmap, but under a **standing priority rule,
not a one-time gate** — it only gets picked up when nothing trust/quality-
related is currently open and actionable. A one-time gate was explicitly
rejected because two of the three originally-proposed gating conditions
(the sew-out session above; open-ended "continued core-quality work") are
externally-scheduled or inherently ongoing and would never crisply resolve
— parity work would never start under a literal gate. The practical
consequence: an idea only earns priority *within* the backlog if it maps to
something already independently flagged as a gap, not merely because a
competitor has it.

Under that filter, from the three passes:
- **Promoted, real independent justification:**
  - Evenly-spaced streamline fill — Ember ships this as a paid "Streamlines"
    fill pattern (`ess`, evenly-spaced streamlines of a 2D vector field).
    EMB-Bot already has the same algorithm built
    (`digitizer_core/stage6_streamline.py`, a clean-room Jobard & Lefer
    implementation, deliberately not adapted from the license-unverified
    `embroidery-streamlines` reference repo), but scoped today to the
    photo-classification auto-pipeline only ("technique row 10"). The open
    item is exposing existing capability as a general, manually-selectable
    fill type — not building the algorithm, which already exists and is
    tested.
  - Boustrophedon polygon decomposition at an arbitrary sweep angle
    (Ember's `bcd`) — relevant to this doc's own long-standing fill-angle-
    selection research (the Goldman-patent "test 16 candidate angles"
    finding).
  - A color-block sequencer UI view (Ember's "Sequencer: Colors" panel —
    collapses shapes into color blocks with thread name/brand/shape count/
    stitch-index range per block) — addresses a gap already found
    independently in the 2026-08-07 research pass: cross-color sequencing today has zero
    geometric-adjacency signal (see area 1's sequencing-research notes).
- **One concrete, low-risk, testable idea, not yet a backlog promotion
  pending a real test:** Ember's raster-input simplification tolerance
  scales with design size (`tolerance = min(2.5, max(0.32, 0.0028 *
  size))`); EMB-Bot's `simplify_tol_mm` (`digitizer_core/config.py`) is a
  fixed 0.2mm regardless of design size. Pairs with the already-backlogged
  Visvalingam-Whyatt simplification-algorithm research as a second,
  independent angle on the same vectorization step.
- **Recorded as existing, explicitly not queued — much larger scope than
  the above:** `ember-bridge`, a separate Tauri desktop app that terminates
  Brother machines' own TLS protocol locally for direct-to-machine design
  transfer, bypassing manual file export. A real, distinct product
  capability EMB-Bot has no equivalent of; not comparable in scope or risk
  to the items above.
- **Two of EMB-Bot's own architecture choices validated, not changed, by
  what was found:** server-side auto-digitizing (Ember's client bundles
  were probed for every common ML-inference surface — ONNX, TensorFlow.js,
  transformers.js, WebGPU/WebNN — and any LLM API reference — OpenAI,
  Anthropic, Replicate, Bedrock, SageMaker — and none were found anywhere;
  their `/api/vectorize` is architecturally server-side and, from the
  client's own vantage point, indistinguishable from a classical
  raster-to-SVG tracer, the same shape as EMB-Bot's own `digitizer_service`
  split); and depending on a mature format library (`pyembroidery`) rather
  than hand-rolling PES/DST/EXP/etc. readers/writers from scratch the way
  Ember's own `/convert` module apparently does (no WASM, no third-party
  format library found in that module at all).

**One direct process lesson, not a feature idea:** Ember's own user manual
documents keyboard shortcuts (`3 = circle, 4 = rectangle, 5 = pen, 6 =
satin blocks`) that no longer match the shipped toolbar (`3 = satin
blocks, 4 = pen`, circle/rectangle moved into a shapes flyout, and Text —
not documented at all — added as a real toolbar entry). Real evidence that
doc drift actively misleads users, not just a hygiene nitpick — consistent
with, not a new argument for, this project's own existing discipline around
keeping `MASTER_SCOPE.md`/`COOKBOOK.md` matched to shipped reality.

---

### `simplify_tol_mm` design-size scaling — measured 2026-08-07, no change justified

One concrete backlog item the 2026-08-07 Ember Design competitive research
pass adopted (that research itself is `docs/emberdesign-competitive-
research-2026-08-07.md`, open as PR #89 at the time of this entry, not yet
merged — see that PR/doc for the full competitive writeup; this entry is
the follow-up that closes out its one `digitizer_core`-side action item):
Ember's equivalent vectorization tolerance scales linearly with design size,
clamped `[0.32, 2.5]`, while `digitizer_core/config.py`'s `simplify_tol_mm`
is a fixed 0.2 mm constant regardless of `target_width_mm` — flagged as
"could plausibly benefit from size-proportional scaling the way Ember's
does."

**Checked directly, not assumed, and the fixed constant is correct as-is —
no change made.** Two things, measured independently:

1. **The two are not a like-for-like comparison.** Ember's `/api/vectorize`
   traces a raw uploaded image with no physical-size input at that layer at
   all (their editor sets physical size later); their "size" is the traced
   raster shape's own pixel dimensions — a proxy for "how much raw contour
   noise this image probably has," not a physical output measurement.
   EMB-Bot already has an explicit mm scale at this point (`px_per_mm`,
   derived from `target_width_mm` in stage 1) and applies `simplify_tol_mm`
   AFTER that conversion specifically so it measures real millimetres
   independent of source resolution — a more direct solve to the problem
   Ember's heuristic approximates without one. Their own floor (0.32 mm) is
   already coarser than EMB-Bot's entire current default (0.2 mm), so
   copying their formula/clamp would be a strictly coarser, unjustified
   behavior change, not a calibration match.
2. **Direct measurement confirms the fixed constant already behaves as a
   genuine, scale-invariant physical-mm tolerance.** Held one synthetic
   wavy contour's pixel geometry fixed and swept `px_per_mm` 3.0-40.0 (the
   range this app's real 40-180 mm `target_width_mm` bound produces —
   measured 4.0-34.1 px/mm running the full pipeline on every flat- and
   photo-lane testdata fixture at 40/60/80/90/120/150/180 mm): the Hausdorff
   deviation between the simplified and unsimplified contour stayed
   0.185-0.200 mm across the ENTIRE swept range, while vertex count varied
   26-226 exactly as it should (a design built from the same source pixels
   genuinely has less raw detail to preserve at a smaller physical size, not
   more error at a bigger one). Full end-to-end runs on the flat-lane
   fixtures (`logo_whitebg.png`, `logo_alpha.png`, `ribbon_curve.png` —
   immune to the photo lane's own segmenter-resolution confounds) showed the
   same thing: smooth, sub-linear vertex growth with `target_width_mm` (62
   vertices at 40 mm -> 101 at 90 mm -> 125 at 150 mm on `logo_whitebg.png`),
   no blocky under-detail at the small end, no runaway blowup at the large
   end. The one fixture that DID show a dramatic vertex swing at small sizes
   (`photo/summit_badge.png`: 1654 vertices at 40 mm collapsing to 627 at
   80 mm) traced entirely to a DIFFERENT, already-documented mechanism — the
   sub-detail rescue path's own fixed 0.5 px floor (`stage4_vectorize.py`,
   a few lines from `simplify_tol_mm`'s own use), confirmed via a
   per-region breakdown: 1263 of those 1654 vertices came from `rescued_
   small_shape=True` regions, which bypass `simplify_tol_mm` entirely — not
   this constant, and out of this pass's scope to touch.

Regression tests pinning both measurements: `tests/test_run_tier.py::
test_simplify_tol_mm_realized_deviation_is_px_per_mm_invariant` (the
isolated Hausdorff sweep) and `tests/test_pipeline.py::
test_simplify_tol_mm_stays_fine_across_the_real_target_width_range` (the
end-to-end vertex-count bounds on a real fixture). `simplify_tol_mm`'s own
docstring in `config.py` carries the full writeup so a future pass doesn't
re-litigate this from scratch without evidence. The flat-lane byte-identical
golden (`testdata/flat_lane_golden.json`, pinned by `tests/
test_flat_lane_byte_identical.py`) is untouched, as expected — this was a
measurement-only pass, no pipeline behavior changed.

---

### Ink/Stitch research — new backlog items, not a status change

A full capability sweep of Ink/Stitch (the open-source Inkscape embroidery
extension) against EMB-Bot's current state, run 2026-08-10: fill algorithms,
satin column variants, DST/machine-format read-write, chaining/routing,
lettering, and more, checked against live GitHub source and docs (not
training-data memory) — `docs/inkstitch-research-2026-08-10.md` (948 lines,
full citation trail per finding). **Licensing posture sets the terms for
everything below (the doc's own §0):** Ink/Stitch's code is GPL-3.0 — no
literal copying, no near-verbatim translation, concept-level clean-room
reimplementation only, the same posture EMB-Bot's `fill-techniques-2026-08
-01.md` and `lettering-mastery-2026-08-01.md` already established for
`cross_stitch.py`/`contour_fill.py`. The one exception: Ink/Stitch's DST/
format library, `pystitch`, is MIT-licensed and usable as a real runtime
dependency, not just a concept source (see below and the cross-cutting DST
section above).

**`pystitch` as a `pyembroidery` replacement — evaluation complete,
adoption in progress 2026-08-11.** Ink/Stitch depends on `pystitch`
(github.com/inkstitch/pystitch), not upstream pyembroidery — its own
MIT-licensed fork, hosted under the `inkstitch` org, claiming broader format
read coverage (46 formats vs. pyembroidery's smaller list) and active
maintenance. `digitizer/`'s current format read/write
(`digitizer_service/formats.py` and equivalent call sites) depends on
upstream `pyembroidery` today. The API-compatibility diff this entry used
to queue as "not done" is DONE: `docs/pystitch-evaluation-2026-08-11.md`
checked `pystitch`'s public API against EMB-Bot's actual `pyembroidery`
call sites and its verdict is **Adopt**; the swap itself is in progress in
a parallel lane as of 2026-08-11.

**A gap the 2026-08-10 pass confirmed directly against EMB-Bot's own code, going
beyond what the research doc itself could verify.** The research doc could
only flag satin underlay as an open verification item (§2: Ink/Stitch ships
three variants — center-walk, contour, zigzag — but could not confirm from
docs alone whether EMB-Bot's own satin underlay implements a matching
three-way split). Checked directly this pass: `digitizer_core/fabrics.py`'s
`Fabric.satin_underlay` field only ever takes `"center_run"` or `"zigzag"`
across every fabric preset, and `digitizer_core/stage6_satin.py`'s
`_stroke_underlay()` (the function that actually builds it) only ever emits
a center-spine run plus an optional zigzag pass — grepped for `"contour"` as
a satin underlay value anywhere in `digitizer_core/`, zero hits. Ink/Stitch's
third style (`do_contour_underlay()`: runs up one rail, crosses, returns
down the opposite rail) is structurally distinct from a straight center-spine
walk, not a naming gap. Confirmed absent, not merely unverified — a real,
scoped gap, cheap to add once satin's medial-axis rail extraction exists
(the same rails the center-walk/zigzag passes already use).

**Real capability gaps confirmed absent from EMB-Bot, concept-level porting
only (GPL-3.0 blocks literal code):** meander/stipple fill, tartan/plaid
fill, ripple stitch, circular fill + Fermat spiral, satin e-stitch/s-stitch
point-selection variants, and bean stitch's per-position variable-repeat
pattern (Ink/Stitch's `bean_stitch(repeats=[0,1,3])` — worth checking
whether EMB-Bot's own bean stitch, if it has one, is flatter than this).
Full tiered priority ranking (concrete/low-risk vs. real-gap vs.
lower-priority vs. already-matched vs. legally-off-limits): research doc
§10, not re-derived here.

**EMB-Bot confirmed already ahead of Ink/Stitch in some areas — recorded so
this doesn't get re-litigated later against Ink/Stitch as if it were an
authority to defer to.** EMB-Bot's corpus-derived chaining laws (Laws
59–62, coverage-routed link decisions — a link is legal where something
will sew over it later) are more sophisticated than either of Ink/Stitch's
own routing modules, both flat distance-threshold trim logic (`auto_run.py`'s
0.75mm jump-trim threshold; `auto_satin.py`'s source-overlap-only
`should_trim()`), neither coverage-aware (research doc §3, §5). EMB-Bot's
planned linear-gradient fill scheduler (largest-remainder/highest-averages,
proven `|count_c(n) − Σα_c| < 1` error bound) is more rigorous than
Ink/Stitch's shipped square-root mirrored row subdivision, which states no
error bound (§1.7). EMB-Bot's planned guided/flow-following fill
(`stage6_curved.py`'s parametric-map/Wilcom-UT-transform approach) is
architecturally more sound than Ink/Stitch's shipped guided-fill strategies
(Copy/Offset/Buffer — all normal-offset), on EMB-Bot's own already-documented
reasoning that normal-offset "destroys" the penetration lattice and "fails
at cusps/swallowtails" (§1.6). None of these are new findings that change
anything — they're confirmations that EMB-Bot's own prior research already
out-designed the shipped reference in these three areas.

**Contour fill provenance flag — open question, not a resolved finding.**
The research doc confirms EMB-Bot's own `fill-techniques-2026-08-01.md`
`stage6_contour.py` plan correctly cites Ink/Stitch's contour-fill approach
and its documented limitation (contour underlay doesn't follow the contour,
only the fill angle — EMB-Bot's plan to beat that is a real, verified
differentiator, not an assumed one). But the research doc also noticed
EMB-Bot's own `CONTOUR_ENTRY_SOFT = 1.5` / `CONTOUR_ENTRY_HARD = 2.05`
constants (`digitizer_core/machine.py`, confirmed at lines 144–145 this
pass) exactly match Ink/Stitch's own entry-point buffer thresholds
(1.5x/2.05x offset spacing, `contour_fill.py`), and the plan doc doesn't
cite a source for those two specific numbers. Flagged as an open provenance
question — were they independently corpus-measured, or did they end up
matching because Ink/Stitch's docs were open while picking them — worth a
quick check by whoever builds `stage6_contour.py`, not resolved either way
here.
