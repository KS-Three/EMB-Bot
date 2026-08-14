# Area 1 — Auto-digitizing quality (image → stitches)

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

Covers both implementations that turn an image into stitches: the original
browser JS engine (`src/flatten.js`, `digitize.js`, `geometry.js`, `fill.js`,
`satin.js`) and the Python pipeline (`digitizer/digitizer_core/`) — tracked as
one capability regardless of which implementation is responsible, since
that's how feedback on digitizing quality actually needs to land.

**Status:** In progress. The JS engine is complete but frozen — COOKBOOK.md
notes it was retired in favor of "feed it clean flat art," not because it's
broken. The Python pipeline is the active target: stages 1–7, fill + satin,
the service, preflight scoring (`digitizer_core/preflight.py` — the same
scorer the corpus scorecard and this doc's fix-grading program run on), and
the review UI are all built (this entry used to quote a stale
`digitizer/README.md` line calling preflight "still to come"; that README
line has itself been corrected). SAM2 segmentation (an optional
alternative region former for photo-classified designs) is built, merged,
and now reachable from Studio via the `embstudio:sam2` dev seam, still
gated behind `cfg.photo_segment_sam2` (default `False`).

**Satin-vs-fill routing is the named next work (Kent, 2026-08-14), and the
measurement that picked it says the defect is misrouting, not a threshold.**
A stitch-type confusion matrix over the pro-parity corpus — 15,953 shared
2 mm cells across 23 professional designs, using the scorecard's own
`cell_stats` classifier and registration so it is the same comparison the
score reports — reads:

| pro \ ours | run | satin | fill | share of ground |
|---|---|---|---|---|
| run | 0 | 15 | 32 | 0.3% |
| satin | 324 | 5,241 | 2,991 | 53.6% |
| fill | 294 | 2,348 | 4,708 | 46.1% |
| **ours** | 3.9% | 47.7% | 48.5% | |

The two marginals nearly agree — pro 53.6% satin / 46.1% fill against our
47.7% / 48.5% — while per-place agreement is 0.624 raw against a 0.479 chance
floor, i.e. **0.278 corrected**. That combination is the whole finding: the
engine sews about the right *amount* of satin, in substantially the wrong
*places*. 35.0% of the pro's satin ground is sewn as fill and 31.9% of its
fill ground is sewn as satin, so the two errors nearly cancel in the mix and
hide from any metric that looks at totals. **Retuning `satin_max` cannot fix
this** — a wider cap buys satin in the places already over-satinned, and a
narrower one gives up the satin that is currently right.

Spread per design is wide enough to be diagnostic rather than uniform noise:
`mfab_hat` catches 92.4% of the pro's satin (corrected 0.542), proving the
classifier does work on some geometry; `becker_chest_small` catches 62.0%
while satinning 73% of the pro's fill (corrected 0.000, raw 0.435 against a
0.497 floor — worse than guessing); and `tires_hat_3d`, which the pro sews
98.3% satin, is sewn 81.5% fill (corrected 0.000). Those three are the
obvious first fixtures to reason against.

**Where to look first:** `is_satin_candidate` (`stage6_satin.py:185`) is
three consecutive *rejection* gates — a `2·area/perimeter` width cap, a
`length_est < 3·w` aspect test, and `_dt_regular_and_within_cap`, which its
own docstring describes as "a pure TIGHTENING, it can only turn a satin call
into a fill call, never the reverse". There is no path that promotes a shape
the width/aspect test rejected. So every pro-satin-sewn-as-fill cell is one
of those three gates firing, and the reverse errors are shapes that passed
all three and should not have. *(measured 2026-08-14 — confusion matrix over
the pro-parity corpus; numbers and method in
[`docs/scope-history.md`](../scope-history.md), 2026-08-14 entry)*

**Its "tie, not a win" verdict is SUPERSEDED as of 2026-08-11 — and the
hedge attached to that verdict turned out to be the right one.** The
2026-08-10 measurement (`digitizer/docs/sam2-segmentation-live-acceptance-
2026-08-10.md`) found SAM2 a tie with the classical SLIC+RAG segmenter at
a real ~40s/job CPU cost, but said in the same breath that the corpus
"lacks real complex-photo fixtures (faces, jackets, smoothly-varying
subjects) to properly exercise what SAM2 is actually for, so the tie is a
statement about corpus coverage, not SAM2's ceiling." That is exactly what
it was: Kent ran a real photo through it on 2026-08-11 and reported SAM2
"drastically better at the photo recognition portion," and decided to keep
it. The committed corpus still cannot show this — the only two
`photo_subject`/`photo_scene` fixtures are synthetic stubs — so **the
corpus remains unable to defend or refute SAM2's quality, and a real-photo
fixture is the missing piece.** Cost after tuning: ~1.03 GB footprint and
roughly +15 to +30s per photo (see the "Last updated" entry at the top for
the `points_per_side` 16→12 change, the rejected `max_side_px` change, and
the two open risks on this lane).
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
built.

**Stage 4 was discarding whole regions, and calling them "details" — found
and fixed 2026-08-13.** Kent: *"we still have the space in the lower portion
of the owl that gets dropped."* It was one root cause with two effects, both
in `stage4_vectorize.vectorize`'s handling of a repaired outline.

`approxPolyDP` can make a traced boundary cross itself, and `make_valid`
repairs it — but the repair's TYPE varies with the geometry. A simple
figure-eight comes back as a bare `MultiPolygon` whose members are polygons.
One that also sheds a dangling edge comes back as a `GeometryCollection`
holding a `MultiPolygon` **and** a `LineString`, so the polygons sit one level
deeper. The old code scanned only the top level for `Polygon`, then kept the
single largest match:

- **A `GeometryCollection` scanned as "no polygons at all" and the entire
  region was dropped.** On `owl_kent.jpg` that is **944 mm² and 718 mm²** —
  20% and 15% of the design — which also took their thread colours out of the
  palette (`EMPTY_THREAD_LAYER`, and Kent's panel showing 9 colours where the
  palette had picked 12). On `summit_badge.png` it is a single **2,787 mm²**
  drop: the whole badge body.
- **Keeping only the largest part threw away the others.** That is Kent's
  actual bare patch — a 30 mm² piece of the owl's body region that the repair
  separated and that then lost the size contest. Nothing ever sewed there.

Both are fixed: polygons are collected recursively at any depth, and every
part clearing the same sewable floor a whole region must clear is kept as its
own region. Measured across the fixture set — **7 of 10 unchanged, byte for
byte**, including every flat/line-art fixture and the `enthusiast_logo`
benchmark (they produce no invalid polygons, so the path never runs):

| fixture | regions | colours | stitches | dropped by stage 4 |
|---|---|---|---|---|
| `owl_kent.jpg` | 25 → **35** | 12 → **14** | 7,725 → **11,307** | 1,662 mm² → **0** |
| `summit_badge.png` | 37 → **43** | 11 → **12** | 3,843 → **8,263** | 2,794 mm² → **5.3 mm²** |
| `drone_render.png` | 72 → **74** | 17 → 17 | 9,161 → **9,239** | 4.0 mm² → **1.2 mm²** |
| the other 7 | unchanged | unchanged | unchanged | unchanged |

What remains dropped is now genuinely sub-sewable: 131 slivers totalling
5.3 mm² on `summit_badge`, none bigger than 0.3 mm².

**The warning is why this survived so long, so it changed too.**
`DROPPED_SMALL_SHAPES` described every one of these as a detail "too small or
thin to hold a stitch" — a 2,787 mm² region included. Nobody investigates a
lost speck. The engine now sends `largest_mm2` and `all_small`, and when a
drop is an order of magnitude past detail scale both the engine message and
the Studio panel name it as a shape that could not be turned into a sewable
outline, with its size, and point at the preview. **Generalises past this
bug: a warning that makes a large loss sound routine is a defect in its own
right.**

**Fix #6.3 landed, 2026-08-11 (evening) — post-vectorization thread
re-validation (`stage4_vectorize.revalidate_threads`, called from
`pipeline.run_stages` right after `tag_enclosed_background`).** A thread is
chosen at stage 2 from the pixels a region occupied THEN; stage 4's
`simplify_tol_mm=0.2mm` then moves the outline, which is a rounding error on a
20mm shape and a large fraction of a 1.3mm-wide one. Nothing downstream ever
re-asked. It now does: each shape is re-scored against the pixels its FINAL
polygon covers and re-snapped when a meaningfully better spool exists, with a
new `THREAD_RESNAPPED_AFTER_DRIFT` warning. **Threads only — never geometry**
(the simplified outline is the one that sews well). Gated on
`THREAD_REVALIDATE_MIN_PX=200` and `THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00=3.0`
so ordinary sub-unit wobble cannot churn assignments or goldens.

**The estimator is the fix, and the first build got it wrong** — worth
knowing because the same trap has now caught this codebase twice. Scoring a
region by MEAN Lab put the traced sliver at dE00 **5.54**, i.e. reported the
defect as absent. That shape is bimodal: 59.5% of its 2,333 px are near-white,
per-pixel dE00 to its assigned `2560 Azalea Pink` runs 23.9 at p10/p50 and
25.2 at p90, and the mean lands on a colour almost no pixel carries — exactly
the criticism `docs/photo-quality-root-cause-2026-08-11.md` already makes of
`preflight._artwork_colors_by_thread`'s pooled per-channel medians. Scoring
the MEDIAN OF THE PER-PIXEL dE00 reproduces the doc's original 23.87 and
re-snaps it to 0.00. Per-region worst dE00: `repro_gradient_white_icon`
23.87 → 0.00, `drone_render` 20.99 → 10.64, `summit_badge` mean 3.76 → 3.52.
`digitizer/tests/test_thread_revalidate.py` (7 tests) pins the mean-vs-
per-pixel gap so a refactor cannot quietly reintroduce the blind estimator.
**CORRECTED, 2026-08-11 (late) — this entry originally said "#6.3 does not
move the corpus scorecard grade, do not tune against it." That was measured
against the OLD pooled instrument and is WRONG now.** `619e9ad` ("score
THREAD_MATCH_POOR per region, not per pooled thread median") landed the
prerequisite this entry called for, and re-measuring the same three fixtures
at the same two configs against the new instrument gives:

| fixture | #6.3 off | #6.3 on |
|---|---|---|
| `repro_gradient_white_icon` (both configs) | **F, 0** — worst dE 28.3 | **B, 76** — worst dE 6.8 |
| `drone_render` (both configs) | F, 0 — worst dE 36.0 | F, 0 — worst dE **14.1** |
| `summit_badge` (both configs) | F, 0 — worst dE 10.3 | F, 0 — worst dE 10.2 |

The fixture this fix was built for goes from the corpus's worst grade to a B.
Note the OFF baseline moved too (`repro` was D/58 under the pooled instrument,
F/0 under the per-region one) — that is the new instrument finally seeing the
23.9 dE drift the pooled median was averaging away. **The instrument and the
fix now agree, which is the real result: the corpus harness is trustworthy on
thread matching for the first time.** `drone_render` stays F/0 because other
findings dominate its score, but its thread error falls 61%.

**Fix #6.2 REFUTED, 2026-08-11 (evening) — built, swept, and reverted; do not
rebuild it from the root-cause doc's recommendation.** Capping the RAG
hierarchical merge on region-internal Lab spread cannot work: (a) a tightening
factor only defers a merge in `merge_hierarchical`'s global heap and the
substituted merges were worse (`drone_render` worst region RMS 35.88 → 62.97);
(b) with a hard refusal instead, the ceiling turns out to be SEEDS granularity,
not the merge — `drone_render`'s worst RAW superpixel is already RMS 70.00 and
its worst final region is 70.00 at every cap, and tripling
`SEEDS_TARGET_FG_SUPERPIXELS` moves it to 35.61 from 35.88 because the merge
threshold re-merges the finer pieces; (c) the usable window is empty — below
cap ~14 `drone_render` goes 21 → 170 regions at 90mm (through the 20-80 accept
band, undoing PR #45), above ~18 the rule does nothing, and the one survivor
(16.0) leaves both target fixtures' grades unchanged while costing
`repro_gradient_white_icon` 12 points (58 → 46). Full measurement in the
follow-up section of `docs/photo-quality-root-cause-2026-08-11.md`.
**What #6.2 actually needs** is either splitting regions by colour AFTER the
merge (downstream of the accept band) or accepting wide-spread regions and
letting the tonal tiers sew them — which is what `source_pixels` and the
blend/streamline tiers already exist for.

**Fix #6.1 landed, 2026-08-11 — `drone_render.png`'s `max_colors` floor-aware
overflow (`digitizer_core/palette.py::select_palette`).** Traced in
`docs/photo-quality-root-cause-2026-08-11.md`: `drone_render.png` (and two
siblings, `summit_badge.png`/`repro_gradient_white_icon.png` — see that doc)
scored F/0 on `digitizer/tools/corpus_scorecard.py` at both `80mm/left_chest`
and `80mm/hat_front`. Root cause specific to `drone_render.png`:
`select_palette`'s BUILD loop hit `max_colors=12` before its own excess-ΔE
target was satisfied, force-merging two regions with excellent available
chart matches (floor 1.98/1.51 ΔE00 — e.g. Isacord "Silver") onto a bad
spool ("Armour", ΔE 9.10–9.18) purely because the cap bound first.

**Fix:** BUILD's stop rule now allows growth up to `hard_cap = max_k +
PALETTE_OVERFLOW_K` past the soft `max_colors` cap, but ONLY to rescue a
region whose own floor is already excellent (`floor <= excess_deltae * 0.5`)
— never to pad the palette for a region no thread actually matches well.
Landed on branch `fix-6-1-palette-overflow` (commits `e5b4969` design spec,
`8270dde` red unit test, `e6aef9c` green fix, `78ba1d7`
`photo_lane_segment_golden.json` recapture, `818f19a`/`074e515` docstring
cleanup).

**Verified correct at the algorithm level, not just unit-tested:** a direct
trace against the real `photo/drone_render.png` fixture (not the synthetic
Task-1 test scenario) confirms both target regions get correctly rescued —
assigned to Titanium/White chart spools, present after SWAP — and
`select_palette`'s own internal metric improves exactly as designed:
`max_excess_de00` 7.599 → 1.969. A separate golden fixture,
`digitizer/testdata/photo_lane_segment_golden.json`, was deliberately
recaptured for the same reason (`drone_render.png` 12→14 threads).

**Does NOT move `drone_render.png`'s corpus-scorecard grade.** Recaptured
`testdata/corpus_scorecard_baseline.json` post-fix (commit `821d066`) shows,
at both configs: score/grade unchanged 0/F → 0/F; `color_changes` 14→16;
`THREAD_MATCH_POOR` findings 5→6 (up, not down); `thread_worst_delta_e`
unchanged at 9.2.

**Correction: three other fixtures did move in this recapture — not noise,
and not from this fix.** `region_blobs.png` (`stitch_count` 1081→1079,
`coverage_area_mm2` 1141→1142, both configs), `gradient_ramp_linear.png`
(`stitch_count` 712→708, both configs) and `enthusiast_logo.png`
(`coverage_area_mm2` 667→666, `hat_front` only) all shifted — sub-1%-scale,
no score/grade/finding change on any of the three, but real movement this
fix did not cause. `enthusiast_logo.png` classifies `flat`; `pipeline.py`
routes `flat` designs through `stage2_quantize.quantize()`, which never
calls `select_palette` — the only function this fix touches, so it cannot
be the cause, full stop. `region_blobs.png` and `gradient_ramp_linear.png`
classify `gradient` and do reach `select_palette`, but measured directly
(instrumented run against today's code): 4 and 2 medoids selected
respectively, nowhere near `max_colors=12`'s soft cap — BUILD exits via the
pre-existing excess-satisfied check before this fix's new code path is ever
reached, so old and new code execute identically for both. The stage-2
golden in `photo_lane_segment_golden.json` also pins `region_blobs.png`
byte-identical, and that test currently passes. The real cause of the
drift: the corpus baseline was last captured 2026-08-08 (commit
`e455b6c`) and sat unrefreshed through roughly 15 unrelated digitizer
commits landed since (the SAM2 lane routing, the `kept_masks_to_quant`
refactor, three new fill techniques, among others) — `821d066` is the
first recapture since, so it folded that pre-existing, never-diagnosed
drift into the new baseline alongside fix #6.1's real change, and this
doc originally misattributed all of it to noise. Not chased further
here — a stale-baseline habit gap, not a code defect, out of scope for
#6.1.

Separately, root cause of `drone_render.png`'s own scorecard disconnect,
confirmed by direct trace, not guessed: `preflight.py`'s
`THREAD_MATCH_POOR` finding measures a POOLED per-thread median artwork
color across every region assigned to a given spool, not this fix's
per-region excess-over-floor target. The two rescued regions leave Armour's
other, unrelated pooled regions untouched, and the newly-promoted Titanium
spool has its own mediocre pooled match (~7.8), so the pooled signal
doesn't move even though the per-region fix worked exactly as designed.
This is the same pooled-vs-per-region measurement gap the root-cause doc
already flags as a contributing factor for `summit_badge.png` (see below) —
a real, understood preflight-methodology gap worth a future look, not
chased further here (out of scope for #6.1).

**This fix is grade-flat-or-negative by construction on the current
scorecard.** `preflight.py` deducts 12 points per `THREAD_MATCH_POOR:warn`
finding (30 if severity escalates to `:block`) and adds a
`COLOR_STOPS_HEAVY` finding once `color_changes` exceeds
`COLOR_STOPS_MAX` (10) — both keyed off pooled, per-thread signals, not
per-region ones. Every spool this fix's overflow mechanism adds is one
more chance at a new `THREAD_MATCH_POOR` finding on that added thread
(exactly what happened here: 5→6) and pushes `color_changes` a step
closer to the `COLOR_STOPS_HEAVY` threshold. So on the CURRENT scorecard
this fix can only hold a design's grade flat or lower it — even when it
genuinely improves per-region color fidelity — because the scorecard
measures pooled per-thread match quality, not this fix's per-region
excess-over-floor target. `drone_render.png` was already floored at
0/F, so the new finding was invisible here; a design sitting at, say, a
B grade going in could plausibly drop a full letter grade or more if
this fires on it. `drone_render.png`'s result (grade unchanged,
poor-match count up) is the expected general behavior of this fix on
the current scorecard, not a fixture-specific anomaly.

**Measured at Studio's real `max_colors` defaults before merge, not just at
the digitizer's 12.** The whole corpus_scorecard run above uses
`PipelineConfig.max_colors=12`, but Studio ships `max_colors: 6`
(`app/src/lib/project.js`'s `DEFAULT_DIGITIZE_PARAMS`) and its slider goes
down to 2 (`DigitizePanel.svelte`) — so `PALETTE_OVERFLOW_K`'s flat +3
allowance is a 50% overshoot at the real default and 150% at the minimum,
and nothing had ever exercised either. Measured directly (all 14 fixtures ×
2 configs, run twice each with `PALETTE_OVERFLOW_K` patched to 0 vs 3, 56
digitize runs):

* **`max_colors=6`:** only `drone_render.png` changes at all — 2 of 28
  combos; every other fixture is identical with the overflow on or off.
  On it: `color_changes` 9→12, score/grade unchanged 0/F, `THREAD_MATCH_POOR`
  unchanged at 7, `thread_worst_delta_e` unchanged at 9.5 — but a NEW
  `COLOR_STOPS_HEAVY` finding appears (0→1), because 9 stops sat just under
  `COLOR_STOPS_MAX=10` and 12 clears it. That is the paragraph above's
  −12 exposure showing up concretely; invisible here only because this
  fixture is already floored at 0.
* **`max_colors=2`:** again only `drone_render.png` moves (2 of 28).
  `color_changes` 1→2 — **+1, not the 150% blowup the flat allowance
  suggests** — no `COLOR_STOPS_HEAVY`, and `thread_worst_delta_e` actually
  IMPROVES 16.9→11.4. The floor gate self-limits: it only keeps growing
  while a rescuable low-floor region is the worst offender, and a 2-color
  palette runs out of those immediately.

So the flat `+3` allowance does not misbehave at small `max_colors` the way
its arithmetic implies — the gate, not the constant, is what bounds it in
practice. The one real measured cost is the `COLOR_STOPS_HEAVY` trip at
`max_colors=6`. **Caveat on how much this proves:** exactly one fixture in
the 14-fixture corpus exercises the overflow path at any `max_colors`
setting, so "nothing else is affected" is real evidence but thin evidence —
a customer photo with a different region/floor landscape could behave
differently, and no fixture here would catch it.

**Still open from the same root-cause doc, untouched by this fix:** #6.2
`summit_badge.png` (F/0 left_chest, F/10 hat_front — a segmentation-merge
chaining issue in `stage2_photo_segment.py`'s hierarchical RAG merge, NOT a
`palette.py` bug) and #6.3 `repro_gradient_white_icon.png` (D/58 both
configs — a post-vectorization color/geometry desync on thin/hairline
shapes, needs its own design pass). Ranked by leverage in the root-cause
doc: #6.1 was the cheapest, most contained fix; #6.2 and #6.3 remain
genuinely open work.

**Streamline fill grew a per-shape form, 2026-08-07** (branch
`streamline-fill-flat-lane-override`) — a competitor-research prompt (Ember
Design ships an equivalent "Streamlines" fill as a generic, per-shape
pattern choice, not photo-only; see `docs/emberdesign-competitive-research-
2026-08-07.md` §"Pass 3" if that doc has landed on `main` by the time you
read this — as of THIS pass it still lives on an unmerged
`docs-emberdesign-competitive-research` branch/worktree, so this entry is
self-contained rather than assuming a cross-cutting backlog row already
exists to close out). **Before:** `stage6_streamline.streamline_fill` was
reachable only design-wide (`cfg.fill_technique == "streamline"` — which,
worth stating precisely, was already NOT gated to photo-classified designs
anywhere in `stage7_sequence.py`; `test_stage6_sketch.py::
test_sketch_technique_implies_the_detail_block` already ran it against
`forced_class="flat"`). There was no way to force streamline fill on ONE
shape inside an otherwise-tatami design the way `tier == "sketch"` (and
`"satin"`/`"fill"`/`"run"`) already could. **After:** `shape_overrides[sid].
tier == "streamline"` works exactly like `tier == "sketch"` does — the
identical shape-layers per-shape-override mechanism (contract v1.6, not a
parallel one): `regions._TIER_VALUES` grew the value, `pipeline.run_stages`'
per-shape source-pixel opt-in scan now also matches `tier == "streamline"`,
and `stage7_sequence.stitch_one`'s streamline branch
(`(streamline or tier == "streamline") and source_pixels is not None`)
moved ahead of scanline/meander in the elif chain — mirroring where the
sketch check already sits — so a per-shape override correctly beats a
different design-wide tonal technique. The three other closed-set mirrors
of the tier vocabulary (`digitizer_service/app.py`'s own `_TIER_VALUES`,
the Studio's `app/src/lib/digitizer.js` `SHAPE_TIERS`, and the Layers-panel
tier `<select>` in `DigitizePanel.svelte`) all grew the value too — this is
backend-**and**-Studio-UI-complete for the specific ask, a one-line
`<option>` addition matching the exact, already-shipped Sketch pattern, not
a guessed UI.

**The direction-field question — the actual design decision, not a wiring
detail.** Investigated three options for what a streamline fill's tangent
field should be for a manually-selected shape with no source-photo texture:
(1) a field derived from the shape's own geometry (medial-axis/skeleton,
the way `stage6_satin`'s rails work), (2) a plain user-specified angle, (3)
a hybrid. Chose (3) — but by **reusing the existing raster/structure-tensor
direction field (`directionfield.py`) completely unchanged, zero new
algorithm**, rather than building anything new: it already reads this
design's own prepped raster (`SourcePixels.rgb` — whatever art the job was
given, a photo or a flat logo alike) and follows real local structure where
the raster has any (antialiasing, subtle shading, texture inside a
"flat"-classified logo), and where a region's raster is genuinely
flat/textureless, the field's own already-shipped, already-tested coherence
gate (`RegionDirection.use_house_angle`) falls back automatically to
parallel lines at the shape's `fill_angle_deg` override — the same per-shape
angle knob ordinary tatami fill already exposes — or the house angle.
Rejected building a shape-geometry/medial-axis-derived tangent field:
that's a materially different, unbuilt algorithm (not a wiring change), and
this codebase has no medial-axis-to-smooth-vector-field machinery to reuse
for it (`shapefield.py`'s `medial_axis` is a skeleton graph for satin rails,
not a per-pixel tangent field) — flagged as a distinct, larger, un-started
feature if wanted later, not attempted here. Also explicitly decided
**against** extending `digitizer_core/manual.py` (the separate,
genuinely raster-less "no image at all" manual-shape-authoring path —
`PipelineResult.source_pixels`/`px_per_mm` are unconditionally `None`
there) to allow `"streamline"` as a technique: `streamline_fill` has no
raster-free mode — darkness/d_sep/the highlight cutoff/the field itself are
all read off `SourcePixels.rgb`, not optional inputs — so exposing it there
would either crash or always silently no-op to tatami, worse than not
offering it. `manual.py`'s own `VALID_TECHNIQUES` stays
`{"satin", "fill", "run"}`, now pinned by an added regression test.

Regression tests added (`tests/test_stage6_streamline.py`): a forced-tier
test proving genuine direction-following on a manually-classified
(`forced_class="flat"`, non-photo) shape measured against a known
stripe-angle fixture (the file's existing analytic-truth discipline, not a
"didn't crash" smoke test), a forced-tier spacing test proving genuine
evenly-spaced J–L placement (median line gap matches the analytic d_sep
formula, not tatami rows), a pipeline source-pixel-plumbing test for the
per-shape override, a no-source-pixels-falls-back-to-tatami-exactly test,
and core-layer + service-layer tier-vocabulary validation tests — 8 new
tests total, mirroring `test_stage6_sketch.py`'s equivalent "sketch" tests
one-for-one. Plus one added case in `test_manual.py`'s existing
bad-technique parametrize list, and one added Studio-side vitest case in
`app/src/lib/digitizer.spec.js` mirroring its existing "sketch" `SHAPE_TIERS`
regression test (that file's own comment records a near-miss where the
dropdown once shipped a tier option before `SHAPE_TIERS` recognized it —
the exact failure this new test, like the sketch one beside it, exists to
catch).

**Verified unaffected, full targeted runs, all green:**
`test_stage6_streamline.py` (28/28, 8 new), `test_stage6_sketch.py`,
`test_manual.py`, `test_pipeline.py`, `test_service.py`,
`test_flat_lane_byte_identical.py`, `test_directionfield.py`,
`test_stage6_scanline.py`, `test_stage6_meander.py`, `test_stage6_blend.py`,
`test_border.py`, `test_fill.py`, `test_satin.py`, `test_preflight.py` —
228 tests across the first seven files alone, no new failures — confirming
the photo-pipeline's existing streamline behavior and every other tier are
untouched byte-for-byte. Studio `app` vitest suite: 413/413 real tests
green (2 suite-load failures traced to that 2026-08-07 session's own ad-hoc
node_modules symlink, not a code issue — independently confirmed passing
23/23 against a real, non-symlinked `node_modules`).

**Cross-hatch fill added, 2026-08-09** (branch `crosshatch-fill-pattern`) —
the first of a planned small family of new named fill patterns for flat/
spot-color art, picked as the lowest-risk starting point because the
codebase already does the core trick: `stage6_fill.py`'s `double_lattice`
underlay style has always called `_fill_paths` twice at +-45deg and
concatenated the results for its own 3-pass underlay. The new
`_crosshatch_fill_paths` does the same thing to the VISIBLE fill instead —
one tatami pass at the shape's fill angle, one at angle+90, each pass
individually spaced `machine.CROSSHATCH_ROW_SCALE_FACTOR` (2.0, a starting
reasoned value, un-sew-out-gated but lower-stakes than the pending-sew-out
density constants since this ships opt-in only) times wider than a normal
single pass, so the two passes together land near a single pass's stitch
density instead of roughly doubling it. No new travel-planning logic:
`stitch_shape`'s existing `emit()` closure bridges between the two passes
the same generic way it already bridges between any list of paths (proven
by a dedicated test asserting exactly one travel run appears between pass 1
and pass 2, the same mechanism `double_lattice` has always relied on for
its own multi-pass underlay).

Wired in exactly like `tier: "streamline"`'s per-shape precedent (verified
against the current code, not assumed): both a design-wide
`fill_technique == "crosshatch"` value and a per-shape
`shape_overrides[sid].tier == "crosshatch"` override, reaching the same
`stitch_shape` call stage 7's plain-tatami fallback already makes, just
with `technique="crosshatch"`. Positioned in `stitch_one`'s elif chain
alongside sketch/streamline (ahead of scanline/meander/gradient/contour) so
a forced per-shape tier wins the same precedence fight those two already
do — but unlike them, crosshatch needs no source pixels (it's geometric,
not tonal), so it carries none of their raster-plumbing opt-in cost, proven
by a dedicated test. All three closed-set mirrors of the tier vocabulary
(`digitizer_core/regions.py`'s `_TIER_VALUES`, `digitizer_service/app.py`'s
own copy, and the Studio's `app/src/lib/digitizer.js` `SHAPE_TIERS`) grew
the value, plus the Layers-panel tier `<select>` in `DigitizePanel.svelte`
gained a Cross-hatch option — the same 5-file pattern the streamline entry
above documents.

Strictly additive: every existing `fill_technique` value's output is
pinned byte-identical (`test_crosshatch.py::
test_the_crosshatch_flag_off_changes_nothing`, plus the untouched golden
suites — `test_flat_lane_byte_identical.py`, `test_pushcomp.py`,
`test_contour.py`, `test_stage6_streamline.py`, `test_stage6_sketch.py`,
`test_shape_overrides.py`, `test_service.py` — all re-run green, 182+119
tests, no changes needed to any of them). 13 new tests added (4 in
`tests/test_fill.py` covering `_crosshatch_fill_paths` directly — two
angularly-distinct passes measured from emitted geometry, per-pass spacing
matching `row_mm * CROSSHATCH_ROW_SCALE_FACTOR`, the pass-2-chains-off-
pass-1 handoff, and degrading sensibly on a too-thin shape; 9 in the new
`tests/test_crosshatch.py` covering both wiring paths end-to-end on the
real `logo_whitebg.png` fixture and the per-shape override's isolation from
its neighbour, plus the two closed-set validation layers). Full digitizer
suite: 942 -> 955 passed, 3 skipped, 0 failed (was 654/658 as of this
doc's last full-suite count on 2026-08-04; the gap is five days of
unrelated growth, re-measured fresh this pass, not this change's doing).
Studio `app` vitest suite: 593 -> 594 passed, 0 failed (the one new
`digitizer.spec.js` case mirroring its existing streamline/sketch
`SHAPE_TIERS` regression test).

**Wave, chevron and brick fills added, 2026-08-10** (branch
`wave-chevron-brick-fill-patterns`) — three more purely-geometric fill
variants, the next slice of the family crosshatch opened, batched together
because all three share one architectural change: `stage6_fill.py` gained
`_wave_row_points`, `_chevron_row_points` and `_brick_row_points`, each
built ON `_row_points` (a shared `_row_points_at_phase` helper now carries
the boundary/`MIN_STITCH_MM`/`TINY_STITCH_MM` handling both `_row_points`
and `_brick_row_points` need) rather than three parallel reimplementations.
Unlike crosshatch — a whole second angled tatami pass — none of the three
needs new travel-planning logic: each only changes how ONE row's own
interior points are placed, so `_fill_paths` picks the row-point function
via a new `technique` parameter (`_ROW_POINT_FNS`, unlisted names including
"tatami" keep `_row_points`, byte-identical) and its column-walking,
ordering and travel logic is untouched.

- **wave** perturbs every interior point's y by `machine.WAVE_AMPLITUDE_MM`
  (0.35 mm) `* sin(2*pi*x/machine.WAVE_LENGTH_MM + phase)` (`WAVE_LENGTH_MM`
  4.0 mm), phase alternating 0/pi by row parity — the simplest rule that
  puts adjacent rows' waves in opposite motion at any given x, which is what
  stops the wobble from stacking into a corrugated-cardboard ridge instead
  of reading as texture.
- **chevron** alternates every interior point +-`machine.
  CHEVRON_AMPLITUDE_MM` (0.45 mm), sign flipping every single interior
  stitch (period two stitches, ~6 mm at the default 3.0 mm stitch length) —
  a deliberately simplified TEXTURAL herringbone impression at one fill
  angle, not a full multi-angle banded herringbone (that would need new
  column/travel logic, out of scope for this family).
- **brick** swaps the van der Corput anti-moire stagger (`_stagger_phase`)
  for a strict period-2 "running bond": even rows' interior grid at phase 0,
  odd rows at `stitch_mm / 2`. No new constant — the phase IS `stitch_mm /
  2`, already a known quantity.

Both new `machine.py` constants are starting, reasoned values — not
sew-out-validated, same caveat every tuning constant in that file carries —
and lower-stakes than the pending-sew-out density constants for the
identical reason `CROSSHATCH_ROW_SCALE_FACTOR`'s own comment gives: every
one of these three ships OPT-IN only (per-shape `tier` or per-design
`fill_technique`), so nobody's existing output moves.

Wired through the identical five-file pattern the crosshatch entry above
documents (`config.py`'s `fill_technique` docstring, `regions.py`'s
`_TIER_VALUES`, `digitizer_service/app.py`'s own copy, `app/src/lib/
digitizer.js`'s `SHAPE_TIERS`, and three new options — Wave/Chevron/Brick —
in `DigitizePanel.svelte`'s Layers-panel tier dropdown), each positioned in
`stitch_one`'s elif chain immediately after crosshatch's own branch, same
precedence slot (ahead of scanline/meander/gradient/contour), same
no-source-pixels-needed reasoning (purely geometric, not tonal).

Strictly additive: every existing `fill_technique` value's output, crosshatch
included, is unchanged. Proved three ways — a parametrized `test_the_flag_
off_changes_nothing` in the new `tests/test_wave_chevron_brick.py`; a clean
pre-change baseline captured by stashing this branch's diff and re-running
the suite (955 passed, 3 skipped, 0 failed) against the post-change run
below; and every golden-bearing file re-run explicitly green with this
branch's changes applied (`test_fill.py`, `test_crosshatch.py`,
`test_contour.py`, `test_stage6_streamline.py`, `test_stage6_sketch.py`,
`test_stage6_scanline.py`, `test_stage6_meander.py`, `test_pushcomp.py`,
`test_shape_overrides.py`, `test_service.py` — 309 passed together, 0
failed). 16 new tests in `test_fill.py` (wave's amplitude/phase measured
both by exact formula match on every emitted interior point and by
independent peak-spacing measurement over a densely-sampled row, plus the
opposite-motion adjacent-row claim isolated with `staggers=1`; chevron's
exact +-amplitude alternation and its every-stitch period; brick's exact
period-2 phase measured against `_row_points_at_phase` directly, and shown
to diverge from the van der Corput pattern at row 2 where the two rules
provably disagree; a `_fill_paths`-level wiring check per technique proving
row ends stay on the boundary while interior points move) and 22
parametrized cases in the new `tests/test_wave_chevron_brick.py` (design-
wide flag reachability and off-changes-nothing, per-shape tier isolation
compared as coordinate SETS — robust to a sibling shape's own entry point
shifting for unrelated reasons — no-source-pixels, and both closed-set
validation layers; mirrors `test_crosshatch.py`'s own structure).

Full digitizer suite: 955 -> 993 passed, 3 skipped, 0 failed (clean
pre-change baseline captured via `git stash`, not the doc's last recorded
count, which predates several days of unrelated growth). Studio `app`
vitest suite: 594 -> 595 passed, 0 failed (one new parametrized
`digitizer.spec.js` case covering all three tiers at once, mirroring
crosshatch's own single-case regression test).

Row 13 (chart-restricted weighted k-medoids palette selection,
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
implementations) is Medium — JS: 283 tests, **281/283** at the 2026-08-11
audit (2 embf-guard failures, fix in progress); Python: **688/694** at HEAD
`fc40d53` (a 2026-08-04 run — the 3 failures are the same long-standing
container-environment goldens this doc has cited every pass since
2026-08-03, not new regressions; the 3 skips are pre-existing, not new),
and the geometry is internally
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

**Fixed, 2026-08-08 (PR #97) — appliqué's configured cover style
(`cfg.applique_cover`) was silently ignored; every cover sewed byte-
identical satin geometry regardless.** `applique_steps` threaded the
setting down to `_cover_layer`'s call site, but `_cover_layer` never
accepted or read it. `_cover_layer` now takes a `cover` param: `"zigzag"`
drives the same `_rail_column` emitter with a new
`APPLIQUE_ZIGZAG_COVER_SPACING_MM` (3.0mm, Melco's preset pitch — picked
for consistency with this file's other Melco-sourced defaults, **not**
validated by sew-out) instead of `geom.spacing_mm`; `"satin"` (default)
and `"e_stitch"` (no algorithm/spec exists to build one against, left as a
documented fallthrough) keep `geom.spacing_mm` and stay byte-identical to
before. New regression tests pin satin's unchanged geometry and confirm
zigzag produces genuinely sparser stitch geometry that moves with the
constant (`test_applique.py`: 58 → 63). Full digitizer suite unaffected
(942 passed, 3 skipped). Doesn't move this area's Status/Confidence verdict
— a real config-wiring bugfix on an already-built feature, not new
capability, and still sew-out-unvalidated like the rest of appliqué.

