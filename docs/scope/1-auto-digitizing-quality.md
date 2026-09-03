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

**Update 2026-08-17: the pooled-vs-per-region gap described above is
CLOSED.** `619e9ad` (2026-08-11) rescored `THREAD_MATCH_POOR` per region —
each thread is judged by its WORST region's per-pixel CIEDE2000 median,
never a pooled per-thread median (`preflight.py`, `_thread_match_findings`;
both measured pooling failures are documented on `_region_color_errors`).
The corpus baseline was recaptured under the per-region yardstick in
`307e69d`. Current baseline reads for the two designs this section
discusses: `drone_render.png` (both configs) — grade F, 16
`THREAD_MATCH_POOR` findings (4 block, 12 warn), worst dE 14.1;
`summit_badge.png` (both configs) — grade F, 7 `THREAD_MATCH_POOR` findings
(1 block, 6 warn), worst dE 10.2. The paragraphs above stand as the record
of why the change was needed.

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

**Update 2026-08-17: the "pooled, per-thread signals" premise above is
CLOSED, same as above.** `619e9ad` (2026-08-11) made `THREAD_MATCH_POOR`
per-region, not pooled-per-thread — `COLOR_STOPS_HEAVY` is unaffected (it
keys off `color_changes`, not thread-colour matching). The qualitative
argument (more spools from the overflow mechanism means more chances at a
`THREAD_MATCH_POOR` finding) was not re-measured against the per-region
instrument here; treat the paragraph above as the record of the reasoning
at the time, not a current description of the scorecard's mechanism.

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
`summit_badge.png` (a segmentation-merge chaining issue in
`stage2_photo_segment.py`'s hierarchical RAG merge, NOT a `palette.py` bug)
and #6.3 `repro_gradient_white_icon.png` (a post-vectorization
color/geometry desync on thin/hairline shapes, needs its own design pass).
Ranked by leverage in the root-cause doc: #6.1 was the cheapest, most
contained fix.

> **Read the paragraph above as of 2026-08-11 morning, not as live status.**
> #6.3 was fixed that same evening — `stage4_vectorize.revalidate_threads`,
> table below — and the grades quoted here have both moved since. Re-measured
> at HEAD: `repro_gradient_white_icon` **B/76 at both configs** (worst dE00
> 6.8, was D/58 under the pooled instrument and F/0 under the per-region one);
> `summit_badge` **F/0 at both configs** (worst dE00 10.2, was quoted F/10 at
> `hat_front`). #6.2 alone is still open, and its grade is saturated — judge
> any fix on `thread_worst_delta_e`, never on score.
> *(measured 2026-08-21 — `corpus_scorecard._score_one`, both MATRIX configs)*

**Streamline fill grew a per-shape form, 2026-08-07** (branch
`streamline-fill-flat-lane-override`) — a competitor-research prompt (Ember
Design ships an equivalent "Streamlines" fill as a generic, per-shape
pattern choice, not photo-only; see `docs/emberdesign-competitive-research-
2026-08-07.md` §"Pass 3"). **That doc is on `main`.** This entry used to
hedge — "if that doc has landed by the time you read this; as of THIS pass
it still lives on an unmerged `docs-emberdesign-competitive-research`
branch/worktree" — and that condition is now resolved: the doc landed and
the branch is gone. The entry stays self-contained anyway. *(confirmed
2026-08-21 — `git log origin/main -- docs/emberdesign-competitive-research-2026-08-07.md`)*
**Before:** `stage6_streamline.streamline_fill` was
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


**Open defect, found 2026-08-20 (this session, Kent reporting by eye) —
satin-tier shapes silently drop extremity features: `enthusiast_logo.png`'s
emblem loses 11.5% of its artwork area to unstitched spurs, with correct
outlines and `stitched: true`.** Kent spotted two holes in a live render —
"it lost the left arm of the logo (that heads in the direction of the star)"
and "the logo lost the bottom right corner". Both are real, and they are the
**#1 and #3 largest missing regions in the whole design**
*(measured 2026-08-20 — overlay diff of `app/e2e/fixtures/enthusiast_logo.png`
against its own stitch output, decoded with pystitch)*:

| missing area | centroid (mm) | what it is |
|---|---|---|
| 11.62 mm² | (6.5, 14.3) | left bracket's inward tab, pointing at the star |
| 6.15 mm² | (1.7, 4.7) | left bracket, outer edge |
| 5.32 mm² | (25.8, 22.6) | **bottom-right corner** |
| 4.01 mm² | (0.7, 21.8) | left bracket, lower outer edge |

97.1 mm² of 1372.2 mm² artwork is unstitched overall (7.1%); within the
emblem alone it is **11.5%**. Method: render the design's own exported DST at
0.4 mm stroke width (nominal 40wt laid width), scale-match to the source
artwork's ink mask, and difference. Reproduce at `target_width_mm=150`,
`max_colors=6` against a running service.

**What it is not** — three candidate causes were tested and each is excluded:

1. **Not shape formation.** The emblem's two shield brackets are formed
   *correctly and symmetrically*, tabs included: `S041897f7` (left,
   165.4 mm², 14 pts) and `S0406e2a0` (right, 165.6 mm², 14 pts), both
   `tier: satin`, both `stitched: true`, both with the inward tab present in
   `outline_mm`. Plotting the review payload's outlines shows a clean,
   mirror-symmetric emblem. The geometry is right; the stitches are missing.
2. **Not background intrusion**, despite the job raising
   `BACKGROUND_UNCERTAIN` ("Background detection reached deep inside a
   shape"). `bg_tolerance_lab` 6.0 → 3.0 → 1.5 and `bg_intrusion_min_mm`
   2.0 → 0.5 all produce **byte-identical** output (4759 stitches, 4 emblem
   shapes, 383.4 mm² emblem area, warning still raised). The warning is
   firing on something that is not driving this loss — worth its own look,
   since a warning that cannot be silenced by its own knobs is misleading.
3. **Not the starburst regression** (`stage6_satin.is_satin_candidate`'s
   deleted `design_class == "flat"` early return). That fix is present and
   the DT check runs unconditionally *(confirmed 2026-08-20 — read at
   `digitizer_core/stage6_satin.py:185`)*.

So the loss is in **satin rail generation on a bracket-with-spur outline**:
the ribbon spine covers the main limb and the spur is dropped. It is
asymmetric — the left bracket loses its inward tab while its mirror twin
covers the same feature, and the right bracket instead loses its bottom
corner — which points at a traversal-order or spine-endpoint effect rather
than a threshold. Not yet root-caused to a function.

**Why this matters more than the corpus score suggests:** `preflight` and
`corpus_scorecard.py` measure mechanical properties and per-cell stitch-type
agreement, neither of which notices that an 11.6 mm² limb of a logo is simply
absent. This is the same blind spot COOKBOOK.md's "Hard-won lessons" names —
a green suite over a design a customer would reject on sight. A coverage
check (artwork ink vs stitched ink, per shape) would catch it and does not
exist today.

**Size is a separate, confirmed axis — and it is not this bug.** The same
fixture at `target_width_mm` 80 / 120 / 150 shows the *wordmark* recovering
monotonically with size *(measured 2026-08-20)*: the "N" is a fused blob with
pinched counters at 80 mm, opens at 120 mm, and is clean satin at 150 mm;
`SAME_THREAD_SHAPES_MERGED` falls 9 pairs → 2 → 2 and `SMALL_SHAPES_AS_RUN`
14 → 14 → 4 shapes. At 80 mm the caps are ~5.5 mm tall with ~1.5 mm strokes,
so pull compensation grows neighbouring strokes into each other and the merge
pass fuses them. That is a legibility floor, not a defect — but the product
needs left-chest logos at 80–100 mm, so the actionable gap is an **honest
warning** ("this wordmark reads better at ≥120 mm"), which is geometry/UX
work and not sew-out-gated. Where the floor actually sits *is* gate 1
territory and stays unanswered until fabric says so.

**Not fixed here.** Filed with the reproduction, the exclusions, and the
measurement so the next session starts from evidence rather than a screenshot.

**Fixed (instrument), 2026-08-20 — `preflight` gained a coverage check:
`ARTWORK_UNCOVERED` fires when a sewn shape's own claimed artwork gets no
thread.** Direct follow-on to the extremity-drop defect above — the blind
spot that let it score clean is now closed. `digitizer_core/preflight.py`'s
`_uncovered_findings`, wired into `run_preflight` alongside the other
artwork-dependent checks (skipped, metrics `None`, when called without an
image — same contract as the thread-match check).

**Ground truth is `polygon ∩ ink`, and both halves are load-bearing** — each
alone produces a false-positive class the other kills, both found by testing
against `becker_marine_logo.png` before trusting either:

- *Polygon alone* claims a letter's open counter (e.g. the "C" in BECKER) as
  area belonging to that shape, so a correctly-bare counter reads as 62 mm²
  missing.
- *Ink alone* (`~bg_mask`) counts every enclosed white counter as artwork
  needing thread, so the same fixture reads 42.3% "missing" while sewing
  exactly as designed.
- A third class, independent of both: `cv2.erode`'s default border does not
  erode artwork touching the image edge, so a full-bleed design
  (`logo_gaulke_roofing`) read a permanent 37.5 mm² strip down its border at
  every erosion width tried, until the erode call got an explicit zero
  border.

**Verified against the shape Kent named.** `enthusiast_logo.png` at 150 mm:
`ARTWORK_UNCOVERED`, 7.8 mm² worst patch, names `S041897f7` — the exact left
bracket from the finding above. Six other fixtures (`logo_whitebg`,
`logo_alpha`, `ribbon_curve`, `logo_gaulke_roofing`,
`logo_drone_thermal_badge`, `logo_script_tires`) stay silent, score
unaffected. Full digitizer suite: 1222 passed (was 1218 — 4 new tests), 8
skipped, 8 xfailed, the same 3 pre-existing golden mismatches COOKBOOK.md
already names (`test_flat_lane_byte_identical`, `test_pushcomp`,
`test_stage2_photo_segment`, all container-environment, none touching this
change) — no regression.

**The threshold is explicitly flagged provisional in the code
(`_UNCOVERED_MIN_PATCH_MM2 = 5.0`).** The clean population sits at 0.00-0.25
mm² and the two adjudicated problem cases at 7.75 and 44.50, but two
fixtures in the middle — `logo_script_tires` (4.50) and
`logo_drone_thermal_badge` (3.25) — are unadjudicated: nobody has looked at
whether those are real drops or acceptable. 5.0 clears both and catches both
known problems, but the margin to 4.50 is 10%, nothing like
`_COVERAGE_MIN_PATCH_MM2`'s two-orders-of-magnitude separation. **Do not
treat 5.0 as settled** — widen the fixture set and adjudicate the middle
before leaning on it.

**Not done:** the satin rail generation bug itself (still open, per the
entry above) and `becker_marine_logo.png` was excluded from calibration —
its artwork is 146×91 px for a 90 mm design (1.6 px/mm, far under
`PHOTO_MIN_PX_PER_MM=10.0`), so it is a garbage-in case unrelated to this
check's accuracy.

**Found 2026-08-20 (this session, Kent reporting by eye on a pro-parity chart)
— `logo_hotel_fremont.webp` at 92.5mm/patch: two real, root-caused defects
and two refuted misreads, none of them the `enthusiast_logo` coverage-drop
mechanism.** Kent flagged five things off a rendered comparison chart
(`digitizer_core, 92.5mm, patch`, 10,319 stitches vs. the professional
Wilcom file's 15,589 — decoded with pystitch, matching the chart's own
count). Investigated each against the actual segmentation/plan data, not
the render:

1. **"THE" incomplete / missing EAT\|STAY\|PLAY — real, but not a coverage
   drop.** The letter shapes exist and `stitched: true` (confirmed directly:
   `S42e426b8`, `S3ddcec6c`, `S666da526` for "THE"; `Sbe6c9978`, `Sac264dc6`
   for the tagline). They're 2-5 mm² at 0.53-0.98mm column width —
   `preflight` already names this class: `LETTERING_TOO_SMALL` (38 shapes at
   this config) and `STITCHES_TOO_SHORT` (65% of satin stitches under the
   1mm needle minimum, "thread breaks are likely"). Too small to read, and
   likely too small to sew reliably — not dropped. This is a genuine
   physical-scale limitation the instrumentation already surfaces; nothing
   new to build.
2. **Satin border not clean — real, newly root-caused.** The rope-twist
   border should be one continuous stroke. It sews as **~21 disconnected
   satin fragments** (2-20 mm² each, all thread 0862), each with its own
   start/stop. Directly explains `TRIM_HEAVY` (13.0 trims/1000 here vs. the
   professional file's 21 trims over 15,589 stitches — roughly an order of
   magnitude fewer per stitch). Not filed as a fix — root cause (why the
   segmenter fragments a thin continuous rope motif into ~21 islands instead
   of joining them) is not found, same evidentiary standard as the
   `enthusiast_logo` bracket entry above.
3. **`CLASSIFIED_GRADIENT` on genuinely flat vector art — confirmed
   misclassification, but NOT the fix.** The rope's diagonal light/dark
   banding is almost certainly what trips stage 0's classifier on artwork
   the chart's own caption calls "flat vector-style badge art, 4 colors."
   Tested directly: `forced_class="flat"` on the same job produces **worse**
   output — 2 colors instead of 5, no letter counters at all, a solid
   crushed mass (screenshots in chat, not committed — the `hf-flat-mono.png`
   render). So this is not a one-flag fix; neither route currently has a
   good answer for fine serif text or a twisted-rope motif at this scale.
   Worth recording so nobody re-tries `forced_class=flat` as the fix here.
4. **"Missing backfill stitching for support" — refuted.** Underlay is
   present: 78 underlay runs across the plan, confirmed directly present
   under 5 of 6 sampled small letter shapes (`plan.iter_runs()`, `kind ==
   "underlay"`). Same render-fidelity class as the earlier `render-dst.mjs`
   white-gaps misread — thin zigzag underlay doesn't visually register as
   "backing" in a stitch-path line render even when it is really there, and
   the chart itself is captioned "not thread-realistic."

Method: `digitize()` + `plan.iter_runs()` directly in Python, not the
service HTTP layer, to get per-run `kind` (`satin`/`fill`/`underlay`/`run`/
`travel`) that the exported design JSON doesn't carry. `ARTWORK_UNCOVERED`
(the check filed above) stayed silent on this job (`worst_mm2: 0.2`,
`total_mm2: 0.0`) — correctly, since nothing here is a coverage drop; this
was the first real-world use of that check on a fixture it wasn't built
against, and it didn't false-positive on a design with five other genuine
problems, which is itself a useful data point for its 5.0mm² threshold.

**Not done:** no fix attempted for the border fragmentation or the
tiny-lettering legibility floor — both are physical/segmentation-scale
questions (gate 1 territory for the latter), filed with reproduction only.

---

## Why this area is not split in two

*Moved verbatim from `MASTER_SCOPE.md` on 2026-08-21 under that file's rule 5
("overflow goes to `docs/scope/`, never to the bin") during a trim pass back
under its 800-line budget. It is a standing argument about how this area is
TRACKED, not a status claim — which is why it left the dashboard. The
undated "this session"/"this pass" deixis below refers to the 2026-08-14
session that wrote it.*

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
vectorization is `stage2_photo_segment.py` (SLIC+RAG; SEEDS since 2026-08-07 — stage2_photo_segment.py:11-27, internal names still slic_*)/`stage3_segment.py`/
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

## The satin extremity drop — ROOT-CAUSED AND FIXED 2026-08-21

The defect filed above (`enthusiast_logo.png`, the emblem bracket losing its
inward tab and a corner, 7.8 mm² reported by `ARTWORK_UNCOVERED`, D/52) is
closed. **The filed hypothesis — "asymmetric between mirror twins, a
traversal-order smell, not a threshold" — was wrong on both halves.**

**Mechanism.** `stage6_satin._prune_spurs` erases short dead-end skeleton twigs
and repeats up to 4 times so a twig hidden behind a twig still goes. Erasing a
spur leaves its branch node standing; a node left holding one arm turns that arm
into a dead end through no thinning of its own; pass 2 measures that stem against
the same bar and deletes real limb. Traced pass by pass on the polygon stage 7
actually satins:

| twin | pass 1 | pass 2 (the stem) | bar | outcome |
|---|---|---|---|---|
| left `S041897f7` | both tab twigs, 17.142 px | **19.000 px → pruned** | 19.4770 px | 1 stroke, tab has no spine |
| right `S0406e2a0` | both tab twigs, 16.728 px | 20.000 px → kept | 19.1152 px | 3 strokes incl. the 3.33 mm tab |

**One raster pixel — 0.167 mm at `_RASTER_PX_PER_MM` 6.0 — decides a 3.3 mm
tab, between two shapes whose sewn areas differ by 0.06%** (194.530 vs 194.653
mm²). The left is doubly penalised: shorter stem *and* a 1.9% higher bar from
its own mean DT. That is why it looks like an asymmetry bug and is not one.

**Fix:** a dead end `_prune_spurs` itself exposed is remembered and never
counted as a spur tip. Narrow by construction — a node going 3 arms → 2 welds
its survivors into one longer edge whose free end is elsewhere, and that edge
stays prunable on its own length. Left bracket now sews a 3.17 mm tab against
its twin's 3.33 mm; `ARTWORK_UNCOVERED` silent; score 52 → 64, D → C.

**Measured and REFUTED — do not rebuild:**
- *Retuning the 1.6 multiplier.* Fixes 2 fixtures, breaks 2, 7 test failures.
  The decision margin is ±0.4% against 3.5% noise in its own input, and 8.2% of
  all spur decisions across 9 fixtures sit within ±5% of the bar. **No threshold
  value is correct when the margin is smaller than the noise** — every candidate
  only moves which shape sits on the knife edge.
- *A grid-independent normalizer* (median/p75 DT, `ribbon_width_mm`). Correct at
  shape level, but the twins' skeletons genuinely branch differently, so no
  length statistic separates them.
- *Reunifying co-linear twigs before pruning.* The twigs form a ~105° V, not two
  co-linear halves, the identical V exists on the healthy twin, and it would not
  save the stem, which dies a pass later in its own right.
- *Moving `_corner_forks` ahead of `_prune_spurs`.* `_corner_forks` returns the
  empty set for both twins at the shipped threshold; it is inert here.

**Blast radius** (guard on vs off, 90 mm, `max_colors=6`): `logo_alpha.png` and
`logo_whitebg.png` **byte-identical** — the genuine-regression canary and the
pushcomp golden fixture are untouched, so both pre-existing golden failures are
unrelated. `logo_gaulke_roofing.png` identical. Eight fixtures move, all in one
direction (satin runs +1 to +3): enthusiast_logo, owl_kent, drone_render,
hotel_fremont, drone_thermal_badge, repro_gradient_white_icon, becker_marine,
bridge_bar, golden_tee. **`test_flat_lane_byte_identical[photo/enthusiast_logo.png]`
legitimately moves** — it was already in the expected-failure matrix on this
platform and was NOT recaptured here, per COOKBOOK's diff-then-capture rule: a
recapture on a run where the golden already fails for an unrelated platform
reason would fold that divergence in.

**The trap that cost the first investigation its whole result, recorded so
nobody repeats it:** it measured `region.polygon` (165.41 mm²). Stage 7 satins
the pull-compensated `p.polygon` (194.53 mm², +0.3 mm outward, 17% different
`half_mm`) — `stage7_sequence.py`'s own comment says so. Every spur length, flip
point and stroke list was therefore off-pipeline, and the "topology fork"
conclusion drawn from them was an artifact. Intercept `satin_shape` to get the
operative polygon; `region.polygon` is only what `is_satin_candidate` classifies
on. *(measured 2026-08-21 — reproduced independently three times)*

### The same fix closed a second defect, in text-cluster regularization

`_prune_spurs` is shared with `textcluster.py` (imported at :341, called at
:676 at the identical `max(3.0, half_px * 1.6)`), and the same cascade was
mangling letters there. `regularize_text_clusters` redraws a cluster member by
buffering its skeleton to the cluster's shared stroke width; on a block-letter
"I" the prune pass erased the two serif caps, then erased the stem those caps
had left dead-ended, and the redraw came back as a bare fragment:

| | area (orig 1.1120 mm²) | shape-context dist | OCR confidence |
|---|---|---|---|
| before the guard | 0.7214 mm² — 35% of the letter gone | 0.1834 | 92.0 → **0.0** |
| after the guard | 0.8793 mm² | 0.0999 | 92.0 → **95.0** |

Tesseract found no text at all in the pre-fix redraw. After the guard the
regularized letter reads *better* than the original.

**This is how the defect was found: the fix made a test fail.**
`test_ocr_gate.py::test_regularization_damaging_gate_falls_back_to_original`
asserted the OCR damage-gate FIRES on that "I" — and with no damage left to
catch, it correctly stopped firing. The test's own module docstring had
described the cause as a property of the letter ("buffering an 'I' this way
collapses the vertical bar's two serif caps into the stem") rather than as a
bug. **A test that pins a defect's symptom as expected behaviour reads as a
regression when the defect is fixed** — the docstring now says so.

The gate keeps its positive case, re-based onto the risk its own docstring
names instead of onto a fixed bug: a target radius mismatched from the
member's true stroke width. At radius 0.60 against the member's own 0.1542 the
buffer balloons the letter to 3.9601 mm² and OCR goes 92.0 → 0.0 — the same
signature, from a cause the gate actually defends against.

**Process note worth more than the fix:** the full local suite was green
(same failure set as baseline, `logo_alpha` canary clean) and CI still went
red, because all five `requires_tesseract` tests SKIP without the binary and
one of them was the only coverage of the shared caller. Installing tesseract
locally takes about a minute; see COOKBOOK "Running things", failure class 2.
*(measured 2026-08-21 — reproduced locally with tesseract 5.3.4 after CI
surfaced it)*

**Measured 2026-08-21 — "enlarge the design" is not a reliably actionable
instruction, and `LETTERING_TOO_SMALL` no longer implies it is.** Follow-up
on Hotel Fremont defect 1 (tiny lettering) from the entry above. The obvious
improvement looked like answering the "enlarge to what?" the warning invites
— the arithmetic is trivial (`MIN_COLUMN_MM` / measured column × current
width). Built it, measured it, and **threw it away**: the number it produces
is not real.

Sweep on `photo/logo_hotel_fremont.webp`, `max_colors=6`, `garment_id=patch`:

| width | flagged / satin total | worst column | median flagged column | derived "needed" width |
|---|---|---|---|---|
| 92.5 mm | 38 / 46 | 0.56 mm | 0.80 mm | 258 mm |
| 120 mm | 27 / 47 | 0.62 mm | 0.80 mm | 367 mm |
| 165 mm | 25 / 56 | 0.52 mm | 0.94 mm | **697 mm** |
| 220 mm | 13 / 63 | 0.66 mm | 0.79 mm | 397 mm |

The flagged **count** falls honestly (38 → 13). Everything a size
recommendation would rest on does not: the worst column has no trend, and
**the median flagged column is flat near 0.8 mm at every size.** Satin shapes
rise 46 → 63 across the same range — segmentation keeps generating
sub-millimetre shapes as the design grows, so the failing tail refills itself
and never empties. A worst-shape-driven target therefore swings
258 → 697 → 397 mm, dominated by whichever sliver landed on the knife edge.
Same instability class as the spur-prune multiplier (`±0.4%` decision margin
against `3.5%` input noise) recorded in
`.claude/memory/satin-extremity-drop-and-coverage-check.md`.

**Consequence for the earlier claim in this file that the wordmark "recovers
monotonically with size."** That still holds for what it measured —
`SAME_THREAD_SHAPES_MERGED`, `SMALL_SHAPES_AS_RUN` and the visible letterform
on `enthusiast_logo` — and the flagged count here agrees. But it should not
be read as "there is a size at which lettering comes clean." On this fixture
there is not; 2.4× the width still leaves 13 shapes under the needle minimum.

**What shipped instead:** the finding now reports `n of total` rather than a
bare `n`, and says plainly that enlarging helps without fully clearing it.
"38 satin shapes are too small" reads like specks to trim; "38 of 46" says
the wordmark itself does not fit — a different decision. The denominator is
the only summary in this check that survives rescaling. A regression test
asserts the *absence* of a suggested width, so a future edit cannot add one
back without a measurement that is stable under rescaling.

**Also re-measured (2026-08-21):** PR #186's `_prune_spurs` fix does **not**
move this fixture — 10,319 → 10,294 stitches, still 38 flagged shapes, still
64/C. That fix closed the serif-cap collapse in `textcluster.py`; Hotel
Fremont's small lettering is a separate, unrelated mechanism. Worth stating
because the two look superficially alike (both "serif details disappearing").

---

## Junction-free DT width — MEASURED NEGATIVE, do not rebuild (PR #152)

Recorded here 2026-08-21, as PR #152 was closed. The branch was left open
since 2026-08-14 purely to keep this result reviewable, and it turned out
to be written down **nowhere else**: PR #192's body claimed it was "durably
recorded" in MASTER_SCOPE, `.claude/memory/`, and `docs/scope-history.md:401`,
but all three of those cite the *2026-08-11 DT-first architecture swap* — a
different experiment with a different conclusion. Closing the PR without this
entry would have lost it.

**The diagnosis, which still stands.** `_dt_regular_and_within_cap`'s `p90`
term rejects shapes for being **branchy**, not for being **wide**. `p90`
strips a junction's inflated inscribed circle (a serif crossbar runs √2 times
its stroke) for *one* junction; it does not hold at branch density, where tens
of branch points inflate well over a tenth of the skeletal pixels. Over the
pro-parity corpus this term is the dominant satin→fill misroute: **11 of 14 DT
rejections**, on shapes the perimeter-based cap gate had just passed. The two
gates disagree by construction — `p90` runs **1.2–1.45×** `ribbon_width_mm` on
the same shape while both are compared against the same `max_width_mm`:

| shape | `ribbon_width_mm` (cap gate) | `p90` (DT gate) | verdict |
|---|---|---|---|
| tires `S396ab4ae` | 4.88 ✓ | 5.83 ✗ | fill |
| becker `Sb92e681c` | 4.21 ✓ | 6.12 ✗ | fill |
| mfab `Sfb63bcf2` | 4.63 ✓ | 6.33 ✗ | fill |

**Why relaxing it still failed.** It does not put satin where the pro puts it;
it puts **more** satin everywhere, and more lands wrong than right. Corpus mean
**54.76 → 54.60**, mean `sttype` **0.217 → 0.198** — the metric it was built to
move, moving backwards. 9 designs better, **12 worse**, 2 flat. The designs
that regressed hardest were the ones already working: `mfab_hat` 63.8 → 60.6
(`sttype` 0.54 → 0.40), `toat_beanie` 56.3 → 53.2 (0.46 → 0.37),
`becker_hat_large` 53.2 → 51.7 (0.11 → **0.00**). `tires_hat_3d`, the design it
was built for, gained +0.8 with `sttype` still 0.00.

**The durable result — this is the part that governs live defect 5.** The
corpus satin/fill *mix* is already nearly correct (pro 53.6/46.1, ours
47.7/48.5), so any change that only shifts a threshold in one direction must
move a mix that was already right. **No one-directional adjustment of the
satin/fill gate — cap, `p90`, aspect, or regularity — can fix this.** Only
something that moves satin *from* the wrong shapes *to* the right ones can:
better discrimination, not a looser or tighter gate. That rules out a whole
class of cheap fixes, and it is consistent with the later oracle measurement
(2026-08-17: an oracle knowing the pro's per-shape answer scores 76.6% against
our 55.4%, i.e. the remaining gap is segmentation, not gate tuning).

*(measured 2026-08-14 — PR #152 over the pro-parity corpus; scores are on the
pre-2026-08-14 scale for `sttype`'s chance correction, so do not compare these
absolute numbers to post-PR-151 ones — the direction and the ruling-out are
what carry.)*

## Chained small-region rescue — LANDED 2026-08-21, gated to the non-photo lane

`resolve_small_regions` size-tested every region against the ~2.25 mm² floor
**individually** and was blind to the union. When quantisation shatters one
structure into sub-floor pieces, each piece's best halo-share neighbour is the
large BACKGROUND region it sits on rather than the neighbouring fragment — so
the whole structure was absorbed into the background one piece at a time.
Measured: an 84-segment ring, 172 mm² and 40 mm across, **digitised to zero
sewn regions**, with only an advisory `ABSORBED_SMALL_SHAPES` to show for it.

**Fix:** `_chained_small_regions` size-tests connected chains of sub-floor
regions against the same `cfg.min_detail_mm`-derived floor; a chain that clears
it is kept, members rescued individually with their colours intact. No new
threshold — the same bar, applied to the structure instead of each crumb.
*(fixed 2026-08-17, landed 2026-08-21 — `stage3_segment._chained_small_regions`,
PR #188; detail in `docs/shape-fidelity-findings-2026-08-17.md`)*

**The lane gate, and why it exists.** The full digitizer suite had never
completed against this fix (started 2026-08-17, starved by a concurrent corpus
prep, killed unfinished). Run to completion 2026-08-21 it produced **two
failures beyond baseline**, both attributable to this one function:
`photo/summit_badge.png`'s stage-2 golden (**34 regions/12 threads → 46/15**,
`max_excess_de00` **2.453 → 7.763**) and the full-bleed preflight guard on
`logo_gaulke_roofing.png` (0.2 mm² that a neighbour used to cover became
covered by nobody — under the 5.0 mm² reporting floor, no finding fired).

Cause: the fix's evidence — 15 pro-parity designs, 13 byte-identical — is
**entirely non-photo-lane**. Photo quantisation makes sub-floor fragments
mutually adjacent everywhere, the exact condition the rescue fires on, so it
stops discriminating there. `tires_hat_3d`'s reassuring "791 sub-floor regions,
0 rescued" is flat-ish art and is not evidence about photos.

So `resolve_small_regions` now takes `chain_rescue: bool = True` and both photo
segmenters pass `False`; the main pipeline call keeps it, which is where the
ring defect lives. Both failures resolve with **no golden re-captured and no
assertion relaxed**. *(measured + gated 2026-08-21 — Kent's call; guard is
`test_ring_absorb.py::test_chain_rescue_is_gated_per_lane`)*

**Do not "simplify" the gate away.** Whether 46 regions beats 34 on
`summit_badge` is unmeasured, and a raw region count is not a quality claim.
Re-opening the photo lane needs a measurement, not a flag flip.

**Worth on the corpus** (measured 2026-08-17, non-photo lane): `bridge_hat`
+156 stitches, `precision_drone` +29, the other 13 byte-identical. Insurance
against silent structural loss on fragmented artwork, not a general quality win.

## Trim attribution on the 46-hole white field — the cut rule, measured (2026-08-21)

First measurements against the target Kent ruled first for live defect 6.
Reproduce with `digitizer/tools/trim_attribution_probe.py`; the tool's own
docstring carries these numbers and the caveat below.

`logo_hotel_fremont.webp`, 92.5 mm / patch, `max_colors=6`. Shape
**`S78e6cd01`** — 2095.8 mm², **46 holes**, **280 fill runs** + 63 travel —
carries **57 of the design's 132 trims, 43%**, inside a single shape. (Recorded
previously as 56 of 135; same shape, same magnitude, small drift.)

**The cut rule is a step function with nothing else in play.** Every run-to-run
boundary in that shape, split by whether it cut:

| | gaps that did NOT cut | gaps that DID cut |
|---|---|---|
| n | 286 | 56 |
| range | 0.30 – **2.92 mm** | **3.02** – 31.28 mm |
| median | 1.35 mm | 5.96 mm |

That is `trim_at_mm = 3.0` and only that — no distance-band logic, no
cover test, no travel attempt recorded at the boundary. **48 of 56 cuts (86%)
are moves under 11.8 mm**, the floor
`docs/fragmentation-attribution-2026-08-18.md` measured the professional as
never cutting below. `trim_at_mm` is gate-1 territory and the sew-out is
accepted as-is, so this is **not retunable** — it is the diagnosis, not a fix.

### Ordering is NOT the gap — a first read of this said it was

The probe's `reorder` pass greedily re-sequences the same fill runs
(nearest endpoint, flipping allowed) and scores them by the same 3.0 mm rule:
**100 → 44** boundaries, inter-run travel **904 → 510 mm**. A first pass read
that as a 56% cut reduction available from ordering alone. **It is not, twice
over:**

1. The pass compares fill-run endpoints only, skipping the **63 travel runs**
   the planner interleaves. Its "as shipped" 100 is not the plan's 57 trims,
   so the two numbers are not commensurable and the ratio between them means
   nothing.
2. `_fill_paths` **already** orders columns greedily nearest-first, considering
   both traversal directions (`stage6_fill.py:594-676`). The probe ran the same
   algorithm, so a real 56% gap between them was never plausible — the gap was
   the measurement, not the planner.

**Do not re-propose "add nearest-neighbour fill ordering."** It is already
there. The pass is kept because it bounds what pure ordering can do, not as a
claim about trims.

### What that leaves gate-clear

Travel **coverage**, not ordering and not the threshold: every 3–11.8 mm gap a
travel run could bridge is a cut removed without touching a constant. 63 travel
runs already bridge boundaries on this shape; the 56 that cut did not get one.
That points at `_graph_travel` never returning a path — a defect no test in the
repo exercises. **Not measured here**, and it needs a planner re-run scored on
real trims, not on filtered endpoint gaps, which is the trap above.

### Travel coverage sized, and it is NOT the lever either (2026-08-21)

Kent's call was to size the recovery before building it, per
`docs/fragmentation-attribution-2026-08-18.md`'s own instruction. Sized:
**the ceiling is 4 of 56 cuts, 7%.** Do not build a travel-side fix for this
shape. Reproduce with `trim_attribution_probe.py --pass travel`.

**The mechanism is exact.** `stage6_fill.py:877` cuts *only* when `travel_path`
returns `None` **and** the gap exceeds `trim_at_mm`:

```python
bridge = travel_path(poly, ring, runs[-1].points[-1], pts[0], slack)
if bridge is None:
    trim = d > trim_at_mm
```

So every one of `S78e6cd01`'s 56 cuts is a **travel failure**, and
`trim_at_mm` only decides whether a failed travel becomes a cut or a silent
jump. A successful travel never cuts, at any distance.

Replaying those 56 pairs against every one of the shape's 20 ring fragments,
with the candidate cap and the detour budget both removed:

| | count |
|---|---|
| **no route stays inside the shape, at any length** | **52** |
| routable, length the only objection | 4 |

Recovering all 4 costs 216 mm of extra travel (~86 stitches), 54 mm per cut.
That is the whole prize. With 46 holes and only 20 inset-ring fragments, the
shape genuinely disconnects its own fill rows — there is no path to find.

**Two knobs ruled out on the way, both gate-clear and both worthless here:**

- `_TRAVEL_RING_CANDIDATES = 3` (a pure performance cap) recovers **0 of 56**.
  The right ring being outside the top 3 is not what is happening.
- `_TRAVEL_DETOUR_FACTOR = 4.0` recovers at most those same 4, and raising it
  past ~16 buys nothing further.

**A correction this entry has to carry, because a first diagnostic got it
wrong.** An earlier pass reported "55 of 56 blocked by the detour budget",
which pointed at the budget as the lever. It was an artifact: that check
flagged `over-budget` as soon as *any* candidate exceeded the budget, before
testing whether *any* candidate was covered at all. Test containment first,
then length — otherwise unroutable pairs masquerade as merely-too-long ones
and the wrong knob looks like the fix.

**Two stale claims corrected:**

1. `_graph_travel` is **satin-side** (`stage6_satin.py:2159`). A fill shape's
   travel is `travel_path` (`stage6_fill.py:523`). Pointing at `_graph_travel`
   for this white field — as an earlier note in this file did — is a category
   error; they are different code paths.
2. The attribution doc's "no test references `_graph_travel` or
   `_build_travel_graph`" is **out of date**: `tests/test_travel_graph.py`
   exists with 7 tests. The doc was written 2026-08-18; the test landed after.

**Where that leaves live defect 6.** On this shape, under gate 1, the gate-clear
levers are exhausted: ordering was already correct, travel tops out at 7%, and
the two mechanisms that would actually move it — `chain_links` and
`trim_at_mm` — are frozen. The remaining idea is upstream of stitching
entirely: stop handing a 46-hole, 2,095 mm² perforated region to the filler as
one shape. That is a stage-2/segmentation question, not a stage-6 one, and it
has not been sized.

### CORRECTION — the 7% ceiling was measured with the ORDER HELD FIXED (2026-08-21)

**The entry immediately above concluded "do not build a travel-side fix." That
conclusion is wrong, and this entry supersedes it.** The 7% number itself is
correct but answers a narrower question than it appeared to: *given the
boundaries the planner already chose*, only 4 of 56 were routable. It never
asked whether a different choice of next run would have been.

It would have been. Reproduce with `trim_attribution_probe.py --pass routable`:

| ordering | cuts | travel |
|---|---|---|
| shipped (nearest by distance) | **57** | 188 mm |
| routable-first (nearest **among reachable**) | **24** | 941 mm |

**33 of 57 cuts — 58% — removed by ordering alone, no constant touched.** This
is constructive, not a bound: it is an ordering that achieves 24, not an
estimate of what one might.

**The mechanism.** `_fill_paths` picks the nearest next column by straight-line
distance. On a 46-hole shape the nearest column is frequently *across a hole*,
where `travel_path` cannot route, so `stage6_fill.py:877` cuts. A farther column
in the same travel-connected island would have cost a few more millimetres and
no cut at all. **The cut is manufactured by the choice, not forced by the
geometry.** Supporting measurement: the 280 fill runs form only **17
travel-connected components**, 195 of them in one and 64 in another, so the
connectivity floor is 16 cuts — the constructive ordering reaches 24.

**Cost.** +752 mm of travel = **+301 stitches on a 10,291-stitch design
(+2.9%)**, or 22.8 mm per cut removed. That travel stays **inside** the shape —
`travel_path` requires `cover.covers(route)` — so unlike `chain_links` it is
not thread on bare fabric, and it is not the gate-1 question `chain_links` is.
Whether 2.9% more stitches is worth 58% fewer trims is a production judgement,
not a geometric one.

**Why this was missed twice.** Both earlier readings held something fixed and
reported the result as a property of the defect:

1. The `reorder` pass compared fill endpoints while ignoring interleaved travel,
   making ordering look like a 56% win it had not earned.
2. The `travel` pass held the planner's ordering fixed, making travel look
   exhausted at 7%.

Each was true of what it measured and false as a claim about the defect. **The
lever is the interaction between the two** — ordering *by reachability* — which
neither pass could see alone. Before concluding a lever is dead here, check what
your measurement is holding constant.

**Status: not implemented.** This is a sizing, on one shape, of a change to
`_fill_paths`' ordering loop (`stage6_fill.py:594-676`). It would move
`test_flat_lane_byte_identical` and stroke goldens on every fixture with a
holed fill, so it needs the corpus run and the same-failure-set discipline —
golden re-capture on Linux CI is pre-authorized (standing rulings). Nothing
above is evidence about any shape but this one.

### Routable-first ordering across the corpus — it generalises, but is NOT a drop-in (2026-08-21)

The 58% figure above is one shape. Swept every committed photo fixture, scoring
cuts by the same `stage6_fill.py:877` rule, on every shape with at least one
hole and ≥15 fill runs. **Note the config differs from the single-shape entry
above:** this sweep runs `PipelineConfig(max_colors=6)` at the DEFAULT
`target_width_mm=80.0`, not 92.5 mm/patch, so its `logo_hotel_fremont` row
(44 holes, 247 runs, 46→14) is a different geometry from that entry's
(46 holes, 280 runs, 57→24). Do not quote them as the same measurement.

**17 shapes across 12 fixtures: 290 cuts → 163, 44% removed.**

**But 13 improved and 4 REGRESSED.** A naive swap of the ordering rule would
make those four worse:

| fixture | shape | holes | runs | shipped | routable | delta |
|---|---|---|---|---|---|---|
| `photo_chrome_specular.png` | `S75b4b6e6` | 2 | 74 | 8 | 15 | **+7** |
| `tight_crop_pale_subject.png` | `Sddefb246` | 9 | 22 | 12 | 17 | **+5** |
| `photo_dof_meadow.png` | `Sf0dc3da8` | 3 | 30 | 7 | 10 | **+3** |
| `photo_scene_stub.png` | `S8c97b2f3` | 1 | 15 | 3 | 6 | **+3** |

Biggest wins, for contrast: `logo_hotel_fremont` 46→14, `logo_gaulke_roofing`
(40 holes) 28→12, `drone_render` (13 holes) 21→6,
`screenshot_phone_ui_golke` (26 holes) 18→4.

**All four regressions used LESS travel, not more** (−1401, −686, −627,
−194 mm). That is the tell: on a shape whose boundaries are naturally
sub-`trim_at_mm`, the shipped nearest-distance walk keeps hops short enough that
a failed travel becomes a silent jump rather than a cut. Routable-first chases
reachability instead, and lands in positions where the next run is both far
*and* unroutable — manufacturing cuts the distance-greedy walk avoided by
accident. The wins cluster on high-hole-count shapes (13–44 holes); the losses
on shapes with few holes or few runs.

**So the rule is conditional, not universal.** The obvious form of the fix is
not "replace the ordering" but **score both and keep the better** — both walks
are cheap and the cut count is exactly computable before emitting, so a
per-shape choice is non-regressing by construction. That is a design sketch,
not a measurement; it has not been built or tested.

**Still not implemented, and the honest ceiling is lower than 44%.** These are
per-shape numbers on shapes chosen for having holes; they are not a design-level
or corpus-level trim reduction, and nothing here has been through the corpus
scorecard. A real implementation still owes: the both-orderings guard, a corpus
scorecard run, and the golden movement (pre-authorized on Linux CI under
same-failure-set discipline).

### RETRACTION — stage 5 is NOT producing invalid geometry (2026-08-22)

**A claim this session raised repeatedly, and called the highest-value open
thread, is false.** After the `_row_spans` crash fix landed (PR #202), the
standing worry was that the guard only repaired at the consumer while stage 5's
pull compensation kept emitting self-intersecting polygons into every other
consumer. Measured, that is not what happens.

| checked | result |
|---|---|
| `PlannedRegion.polygon` values from stage 5 | **0 invalid** |
| `_largest_polygon` inputs / outputs | **0 invalid** |
| the source polygon that later goes invalid | **VALID** — area 1255.28 mm², 2 holes |

**The invalidity is created transiently by floating-point ROTATION**, inside
`best_fill_angle_deg`'s angle sweep (`stage6_fill.py:259`), not by any producer.
That function rotates the shape through 17 candidate angles to count columns.
On this shape, **11 of those 17 rotations turn a valid polygon into a
self-intersecting one** — e.g. angle 11.25° gives
`Self-intersection[-38.330, -1.663]`. `_row_spans` then hands it to
`poly.intersection(line)` and GEOS raises `TopologyException`.

Two consequences, both important:

1. **The consumer-side guard is the CORRECT fix, not a workaround.** No producer
   change could prevent this: the polygon is valid when it leaves stage 5, and
   rotation is arithmetic. Repairing where the invalid geometry is first *used*
   is the only place the repair can live. `stage6_border` (:249) and
   `stage6_contour` (:109) were right all along; fill was the odd one out.
2. **The angle search is NOT silently degraded.** The obvious follow-on worry —
   that column counts taken on invalid geometry pick bad fill angles — was
   measured and refuted: repairing before the sweep changes the chosen angle on
   **0 of 8 shapes**. The crash was the only consequence.

**Method note, since this took four wrong turns.** The first three hypotheses —
stage 5's `.difference()` chains, `unary_union`, and `_fill_paths`' own rotation
— were each checked and each produced zero invalid polygons. The fourth found it
only by instrumenting `_row_spans` itself with a stack trace, which named
`best_fill_angle_deg:259` rather than `_fill_paths:787`. **Testing the call site
you assume is the one is how three of those turns were wasted**; instrument the
failing function and let it tell you who called it.

### Real-artwork validation of the trim work: it is INERT on client logos (2026-08-22)

Kent asked for the path-order selector (PR #205, +143 trims across the committed
photo corpus) to be checked against real artwork rather than synthetic fixtures.
Checked, against all six real-artwork fixtures in the repo — the four
`testdata/reference/becker_*.jpg` client logos plus `becker_marine_logo.png` and
`logo_script_tires.png`.

**Result: zero difference. Byte-identical trims and stitches on all six.**
Reproduce with
`trim_exchange_sweep.py --glob 'testdata/reference/*.jpg' --diff before after`.

Why, measured per fixture:

| fixture | fill shapes | with cuts | reorder accepted | holed regions |
|---|---|---|---|---|
| `becker_chest_small…` | 3 | 0 | 0 | 1 |
| `becker_hat_polo_large…logo_hat` | 1 | 0 | 0 | 4 |
| `becker_hat_polo_large…logolc` | 3 | **1** | 0 | 5 |
| `becker_hat_small…` | 3 | 0 | 0 | 1 |
| `becker_marine_logo.png` | 2 | 0 | 0 | 5 |
| `logo_script_tires.png` | 1 | 0 | 0 | 1 |

Real client logos carry **1–3 fill shapes each and essentially no cutting
fills.** They are predominantly satin — lettering and borders. They *do* have
holed regions (1–5 each), but those fills do not fragment into the many
travel-stranded columns the selector exists to reorder. Exactly one shape across
all six designs had any cuts at all, and there the incoming order was already
the cheaper of the two.

**What this does and does not mean.**

- It does NOT retract PR #205. The +143 trims on the photo corpus are real, and
  the change is byte-identical here, so it carries **zero risk** on this class of
  work.
- It DOES mean the headline number is about photo-lane and large-fill designs,
  not about the logo work this shop actually sews. Anyone quoting "+143 trims"
  as a customer-visible win is over-claiming.
- It is the 2026-08-16 handoff's warning **in reverse**: there, synthetic
  fixtures flattered the ENGINE by 11.3 points; here they flatter a FIX. The
  committed photo corpus is not representative of real client artwork in either
  direction, and a result measured only there needs this caveat attached.

**Follow-on this suggests, unsized:** if real logo work is satin-dominated and
barely fills, then fill-side trim work has a low ceiling on it regardless of
mechanism, and `logo_hotel_fremont`-style perforated fields are the exception
rather than the type. Satin-side trim behaviour is where the customer-visible
gain would have to come from. Not measured.

### Where real-artwork trims actually come from — and the prize behind gate 1 (2026-08-22)

Follows the finding above that the fill-side trim work is inert on client logos.
If not fill, then what? Measured across all six real-artwork fixtures.

**Every shape transition costs a cut.** First-of-shape trims track shape count
almost exactly:

| fixture | trims | first-of-shape | mid-shape | shapes |
|---|---|---|---|---|
| `becker_marine_logo.png` | 29 | 10 | 19 | **10** |
| `becker_hat_polo_large…logo_hat` | 31 | 11 | 20 | **12** |
| `becker_hat_polo_large…logolc` | 34 | 14 | 20 | **16** |
| `becker_hat_small…` | 13 | 8 | 5 | **8** |
| `becker_chest_small…` | 9 | 7 | 2 | **8** |
| `logo_script_tires.png` | 8 | 4 | 4 | **4** |

Ten of ten, eleven of twelve, fourteen of sixteen, eight of eight. Entering a
shape costs a trim, and real logos are many small shapes.

**Underlay, not satin or fill, is the largest single trim kind** — 23 of 29 on
`becker_marine_logo`, 7 of 8 on `logo_script_tires`. But it is NOT an
intra-shape ordering problem: every underlay call returns fewer than 3 paths, so
there is nothing to reorder. `_reorder_for_fewer_cuts` was prototyped against
underlay and qualified on **0 shapes across all six fixtures**. The underlay
trims are the shape-entry trims, counted by kind.

**So the lever for real artwork is inter-shape linking — which is
`chain_links`, and it is gate-1 frozen.** Measured with the flag ON, as a probe
only (the default stays OFF):

| fixture | trims OFF → ON | stitches OFF → ON |
|---|---|---|
| `becker_hat_polo_large…logolc` | 34 → **19** | 3999 → **3919** |
| `becker_hat_polo_large…logo_hat` | 31 → **21** | 4265 → **4221** |
| `becker_marine_logo.png` | 29 → **20** | 4466 → **4420** |
| `becker_hat_small…` | 13 → **8** | 2354 → **2325** |
| `becker_chest_small…` | 9 → **7** | 2440 → **2428** |
| `logo_script_tires.png` | 8 → **6** | 2302 → **2292** |
| **total** | **130 → 87, −33%** | **lower on every fixture** |

**Better on both axes on every fixture.** Contrast the fill-side selector, which
cost stitches on the photo corpus and did nothing at all here.

**This does not reopen gate 1 and is not a request to flip the flag.**
`LINK_COVER_TOL_MM` is a thread spec; the gate is a refusal and it holds. What
this adds is a number the gate decision did not previously have on REAL artwork:
the sew-out that Kent accepted as-is (2026-08-21) is standing in front of a
**33% trim reduction at zero stitch cost on the work this shop actually sews**,
not merely a corpus-metric gain. Whether that changes his call is his to decide;
it should at least be decided against the right number.

**Session synthesis.** Fill-side trim work (PR #205) helps photo-lane and large-
fill designs and is byte-identical on client logos. The customer-visible trim win
is `chain_links`, already built, already measured, blocked only on cloth.

### Stage-2 splitting of the perforated field: sized, and NOT recommended (2026-08-22)

The last of the four items Kent queued. The idea was to stop handing a 46-hole,
2,095 mm² field to the filler as one shape.

**First: the holes are real artwork, not segmentation noise.** Measured — median
**11.7 mm²**, p75 19.6, max 39.3, and only **2 of 46** fall under the sewable
floor (`RUN_MIN_AREA_MM2` 0.16). Total hole area is 651.8 mm², **23.7% of the
filled bbox**. These are letters and elements punched through a background
field. Any argument for splitting on speckle-removal grounds is dead on arrival,
and `docs/segmentation-alignment-2026-08-17.md`'s 95.8%-speckle finding is about
a different thing (grid straddle at cell level), not these holes.

**Second: the remaining gain is small, because PR #205 already took most of it.**

| state | cuts on `S78e6cd01` |
|---|---|
| before PR #205 | 57 |
| **shipped today** | **33** |
| split into its 17 travel-connected components (estimated) | ~17 |

*(Correction: an earlier prototype predicted 24 for the shipped state. That was
the UNCAPPED selector; the 25 st/trim cap Kent set correctly rejects the
expensive trades, landing at 33. 24 was never shipped and should not be quoted.)*

So the split is worth roughly **16 further trims on one shape** — real, but
against a large cost:

- **It restructures segmentation output.** Region count, shape IDs, the review
  UI a user edits, and every golden that touches this fixture class. One field
  becomes seventeen shapes.
- **It is a UX regression for a geometry win.** A user who sees one white
  background now sees seventeen pieces to reason about.
- **The fixture class is unrepresentative.** Today's real-artwork measurement
  found client logos carry 1–3 fill shapes each with essentially no cutting
  fills. `logo_hotel_fremont`'s perforated field is the exception, not the type.
- **The entry trims it trades into are the ones `chain_links` removes.** Each of
  the 17 new shapes costs an entry trim today; with chaining those largely
  vanish. Splitting is therefore worth much MORE after a sew-out than before —
  which is an argument for sequencing it after that decision, not now.

**Recommendation: do not build it.** Revisit only if `chain_links` ships, at
which point the entry-trim cost of splitting falls and the arithmetic changes.
Recorded so the next session sizes it from these numbers rather than rebuilding
the measurement.

### Satin travel fails at the CURSOR, not the target — and that is gate-clear (2026-08-22)

The satin-side counterpart to the fill work, measured on real client artwork
because that is where satin dominates (1–3 fill shapes per logo, 9–40 satin
runs).

**First, a stale claim corrected.** `docs/fragmentation-attribution-2026-08-18.md`
§2 says `_graph_travel` "never returns a path". Measured over 124 calls on six
real-artwork fixtures, it returns one **18–30% of the time** (0% on one small
fixture). Not never.

**A hypothesis of mine, refuted before it reached a doc.** `_graph_travel` walks
only UNSEWN spines, so the obvious theory is that the web is progressively
consumed and late travels fail. Measured, it is backwards:

| web already sewn | calls | succeeded |
|---|---|---|
| **nothing sewn at all** | **37** | **0 (0%)** |
| 0–20% | 112 | 27 (24%) |
| 20–40% | 12 | 0 |

With the entire web available, travel fails every time. Consumption cannot
explain a failure when nothing is consumed.

**The real constraint is the cursor-side snap.** For those 37 failures:

| | distance to nearest web node |
|---|---|
| cursor, on failing calls | median **6.96 mm**, max **62.11 mm** |
| cursor, on succeeding calls | median 1.11 mm, max **2.66 mm** |
| target, on failing calls | median **0.00 mm** |
| snap radius (`trim_at_mm`) | **3.0 mm** |

**31 of 37 have the cursor outside the snap radius.** The destination is on the
web; the needle simply arrives from elsewhere and cannot get onto the web to
start walking. This is the cursor-side snap the attribution doc named, now with
numbers.

**Two ways to fix it, and only one is available.**

1. **Widen the snap radius — GATE 1, refused.** The radius *is* `trim_at_mm`,
   and `_graph_travel`'s own docstring says the coupling is deliberate: "both
   answer how long a leg is sewable needle-down — but it is one knob, not two."
   Whether a needle-down leg from an off-web cursor is sewable is a cloth
   question. Not touchable without a sew-out.
2. **Put the cursor somewhere better — GATE-CLEAR, unbuilt.** The cursor sits
   ~7 mm off the web *because of where the previous shape ended*. Nothing
   physical forces that. Choosing each shape's exit — or the shape order — so
   the needle finishes near the next shape's web would bring the cursor inside
   the existing 3 mm radius without changing any constant. This is the same
   move that worked on the fill side: **choose the order so the geometry
   works, rather than widening a threshold.**

**Not built, and deliberately not sized here.** It touches stage 7 sequencing
and the exit-point coupling that PR #205's last-path pin exists to contain, so
it wants its own measurement pass. Recorded because it is the first gate-clear
lever found on the code path that actually dominates real client artwork —
everything else measured tonight either helps only photo-lane work or sits
behind the sew-out.

#### Sizing the cursor-placement lever: 81% upper bound (2026-08-22)

Of the 31 satin-travel failures where the cursor sits outside the 3 mm snap
radius, **25 (81%) have geometry from another shape passing within 3 mm of the
target web.** So for four in five, a needle finishing somewhere else would
already be inside the existing radius — the placement is available, nobody is
choosing it.

| fixture | out-of-snap failures | other geometry within 3 mm |
|---|---|---|
| `becker_hat_polo_large…logo_hat` | 8 | **8** |
| `becker_hat_polo_large…logolc` | 7 | **7** |
| `becker_hat_small…` | 5 | **5** |
| `becker_chest_small…` | 4 | **4** |
| `becker_marine_logo.png` | 7 | 1 |
| **total** | **31** | **25 (81%)** |

**Read this as an upper bound, not a forecast.** Three reasons it will come in
lower:

- "Other geometry passes within 3 mm" is not "a valid exit exists there **and**
  the sequence can be reordered to use it". Exit points are constrained by where
  a shape's own stitching can legitimately end.
- The owner-of-web attribution is a heuristic (nearest-mean matching of plan
  points to web nodes); a misattributed web would inflate the count.
- 31 is the out-of-snap subset of the 37 zero-sewn failures, which is itself a
  subset of the ~97 total `_graph_travel` failures across these fixtures. This
  sizes one slice, not all satin travel.

`becker_marine_logo` is the honest outlier at 1 of 7 — its shapes are genuinely
far apart, and no sequencing fixes distance. Expect the win to be design-shaped,
not uniform.

**Still the most promising unbuilt lever measured this session**, because it is
the only one that is simultaneously gate-clear, on the code path that dominates
real client artwork, and grounded in a measured bound rather than a hypothesis.

#### The exit point is never chosen — and choosing it is worth 58% of inter-shape trims (2026-08-22)

`stage7_sequence.py:1487` decides every shape-entry trim:

```python
d = math.dist(cursor, runs[0].points[0])
runs[0].trim = d > trim_at        # NO travel attempt between shapes
cursor = runs[-1].points[-1]      # exit is wherever the shape happened to end
```

Shape ORDER is already nearest-neighbour (`polygon.distance(here)`), and ENTRY
is already cursor-aware (`stitch_one(p, cursor)` → `start_near`). **The EXIT is
not chosen at all.** It is whatever point the shape's last run finished on, and
it becomes the next shape's cursor.

Sized on real client artwork — for each consecutive shape pair, the gap as
sewn versus the best gap achievable over all exit/entry point pairs:

| fixture | transitions | trims now | with ideal exit | saveable |
|---|---|---|---|---|
| `becker_hat_polo_large…logolc` | 15 | 12 | 8 | 4 |
| `becker_hat_polo_large…logo_hat` | 11 | 9 | 3 | **6** |
| `becker_marine_logo.png` | 9 | 9 | 4 | 5 |
| `becker_hat_small…` | 7 | 7 | 1 | **6** |
| `becker_chest_small…` | 7 | 6 | 2 | 4 |
| **total** | **49** | **43** | **18** | **25 (58%)** |

**~19% of ALL trims on real artwork, with no constant touched.** Compare
`chain_links` at 33%, which needs a sew-out. This is the gate-clear alternative
and it is unbuilt.

**Upper bound, and the assumption is a real one:** it assumes any point of a
shape can serve as its exit. That is false — a satin column ends at its end, a
fill ends where its last row lands. The realizable share is lower, and the
honest way to find out is to build it against
`tools/trim_exchange_sweep.py --diff`.

**What building it needs.** An `end_near` hint threaded into `stitch_shape` and
the satin router, mirroring the existing `start_near`, plus a greedy
look-ahead in the stage-7 loop (pick the next shape, then aim the current
shape's exit at it). Blast radius is every design, so it needs the
baseline-then-after suite comparison and golden re-capture — pre-authorized on
Linux CI under same-failure-set discipline. **This is the recommended next
build.**

#### CORRECTION to the entry above: 58% was inflated ~2x; the honest figure is 28% (2026-08-22)

The entry immediately above called exit-choice the "recommended next build" on a
58% saveable figure. **That bound assumed any point of a shape can be its exit,
and it flagged the assumption without testing it. Tested, it costs half the
prize.**

A shape can realistically finish at the END of one of its runs — a satin column
ends at its end, a fill where its last row lands — not at an arbitrary interior
point. Re-sizing with run endpoints as the only candidate exits (and entries):

| fixture | trims now | any-point bound | run-endpoints only |
|---|---|---|---|
| `becker_hat_polo_large…logolc` | 12 | 8 | 9 |
| `becker_marine_logo.png` | 9 | 4 | **9 (saves nothing)** |
| `becker_hat_polo_large…logo_hat` | 9 | 3 | 7 |
| `becker_hat_small…` | 7 | 1 | 4 |
| `becker_chest_small…` | 6 | 2 | 2 |
| **total** | **43** | **18** | **31** |

**Realistic saving: 12 of 43 inter-shape trims (28%), not 25 (58%).** Against
~130 total real-artwork trims that is roughly **9%**, not 19%.

`becker_marine_logo` saves **nothing** at all under realistic exits (9 → 9),
consistent with its earlier 1-of-7 showing: its shapes are genuinely far apart
and no choice of endpoint reaches across.

**Revised recommendation: do NOT build this next.** Nine percent of real-artwork
trims does not justify threading `end_near` through `stitch_shape` and the satin
router plus a greedy look-ahead in stage 7 — the highest-blast-radius change
available, touching every design's sequencing. The honest comparison:

| lever | real-artwork trim reduction | status |
|---|---|---|
| `chain_links` | **33%**, and fewer stitches | built, measured, gate-1 frozen |
| exit choice | **~9%** | unbuilt, large blast radius, gate-clear |
| fill ordering (PR #205) | **0%** | shipped; helps photo-lane only |

**The lesson is the one this session kept relearning.** An upper bound with a
named-but-untested assumption is not a sizing. Testing the assumption took one
measurement and halved the answer — before a large change was built on it,
rather than after.
#### The chain_links number is robust across palette sizes (2026-08-22)

The 33% figure is the one Kent may weigh against his accept-the-sew-out-as-is
call, so it was stress-tested rather than left on a single config.

| `max_colors` | trims | stitches | designs worse on either axis |
|---|---|---|---|
| 4 | 119 → 77 (**35%**) | −217 | **0** |
| 6 | 116 → 75 (**35%**) | −211 | **0** |
| 8 | 116 → 75 (**35%**) | −211 | **0** |

Identical reduction at every palette size, stitch count down at every one, and
zero designs worse on either axis in all three runs. Not a config artifact.

**Precision note on the headline.** The widely-quoted **33%** comes from a
seven-fixture set that includes `logo_alpha.png` and `logo_script_tires.png`;
`logo_alpha` shows no change at all and dilutes the ratio. Across the six
real-artwork fixtures alone it is **35%**. Both are true of their own sets —
**quote 33%**, it is the conservative one, and say which set it is from.

Still gate-1 frozen. Still not a request to flip the flag.

#### CORRECTION: the cursor-snap story covers 34% of satin travel failures, not all (2026-08-22)

The entry titled "Satin travel fails at the CURSOR, not the target" drew its
numbers from the `sewn == 0` subset — 31 of 37 — and then **let that stand as a
claim about satin travel generally. It is not.** Measured over the full call
population on the same six real-artwork fixtures:

| | count | share of failures |
|---|---|---|
| `_graph_travel` calls | 124 | |
| failures | **97** | |
| cursor **outside** the 3 mm radius — the snap story | **33** | **34%** |
| cursor **inside** the radius — not a snap problem | **64** | **66%** |

**Two thirds of satin travel failures have the cursor comfortably in range** and
fail for other reasons — genuine graph disconnection between glyphs, or the
already-sewn edges that `_graph_travel` is forbidden to reuse. Cursor placement
cannot touch those.

So the gate-clear cursor lever addresses **at most 34% of satin travel
failures**, on top of the earlier correction that exit-choice is worth 28% of
inter-shape trims rather than 58%. Both corrections point the same way: the
gate-clear satin work is smaller than it first looked, and `chain_links` remains
the only measured lever with a large real-artwork effect.

**Size-dependence, measured while checking this** (`becker_marine_logo` at four
widths): success rate 12% at 40 mm, 8% at 60 mm, 25% at 80 mm, and at 120 mm
`_graph_travel` is **never called at all** — the design routes without needing
it. No clean trend; do not model this as "worse on small garments".

**The habit that caught it**, for the third time tonight: a number measured on a
subset was carrying a claim about the whole. Check the denominator before the
heading generalises.

## The two evaluation harnesses

Moved here from MASTER_SCOPE 2026-08-22 under the 800-line budget (rule 5). The
live verdict and the link back stay in MASTER_SCOPE's "Evaluation corpus &
harness" entry; this is the supporting detail.

**Harness half: BUILT — `digitizer/tools/corpus_scorecard.py`.** `capture` runs
all 14 committed `testdata/` fixtures (top-level and `photo/`) through
`digitize()` + the existing `digitizer_core.preflight.run_preflight` — which
already produced a 0-100 score, letter grade, typed findings and ~20 metrics, so
this aggregates existing signal rather than inventing a metric — at two configs
(80 mm width × `left_chest`/`hat_front`, two distinct fabric presets), writing
`testdata/corpus_scorecard_baseline.json`. `diff` re-runs that matrix and reports
score deltas, findings appeared/resolved, and metric drift past a 5% noise
threshold. **Deliberately a REPORTING tool, not a CI gate** — the docstring cites
this file's own corpus-laws-23/26 history (a "desk-safe" threshold picked without
validation, later reverted) as the reason not to invent pass/fail numbers yet.
Sole hard signal: a brand-new `block`-severity finding flips `diff`'s exit code.
**Verified, not just written:** a real baseline (14 × 2, grades A to F — the F/0
on `drone_render.png` and `summit_badge.png` are documented rough edges in those
photo-tier stress fixtures, not harness bugs) then an immediate re-`diff` with no
code changes reporting no drift at exit 0, so the pipeline is deterministic and
the harness does not false-positive on itself. **Scope limit:** that determinism
covers re-running the SAME code twice only — a recapture spanning real commits
can fold in genuine undiagnosed drift, as "Fix #6.1 landed" (area 1) found for
three fixtures. No dedicated test file, matching the convention that no
`tools/*.py` has one (including `capture_flat_lane_golden.py`); a full capture is
too slow for the regular suite.

**A second, different harness also exists: `tools/pro_parity/`.** Where
`corpus_scorecard.py` asks "did our own preflight score move", this one asks
"how close is our output to the PROFESSIONAL digitization of the same
design" — 23 of Kent's customer designs, decoded from their PES/DST, scored
0–100 across six weighted components (coverage, direction, stitch type,
density, underlay, travel) after a registration search aligns the two.
**Its scale changed 2026-08-14:** `direction` and `sttype` are bounded
agreement measures whose floor was ~0.5, so both are now chance-corrected
against analytic floors (`sttype`'s being Cohen's kappa) and guessing scores
0. See the Gotcha above before comparing any number to a pre-2026-08-14 one.
*(confirmed 2026-08-14 — PR #151)*

### Corpus scorecard — per-fixture state (moved from MASTER_SCOPE 2026-08-22)

**Still open here: `summit_badge.png` (#6.2) alone.** Re-measured at HEAD it is
F/0 at both configs with `thread_worst_delta_e` 10.2 — the grade is saturated,
so judge a fix on that metric and never on score. **#6.3
`repro_gradient_white_icon.png` is CLOSED**, though this list carried it as open
until 2026-08-21: `stage4_vectorize.revalidate_threads` landed 2026-08-11 and it
now measures **B/76 at both configs, worst dE00 6.8**, up from the corpus's worst
grade. `drone_render.png`'s #6.1 landed too but does not move its grade; the
"preflight pooled-metric gap" that used to explain that is itself closed —
`619e9ad` rescored `THREAD_MATCH_POOR` per region, not per pooled thread median.
**Next step:** run the tool against a few real classifier changes to learn what a
genuine regression looks like before setting any hard threshold.
*(measured 2026-08-21 — `corpus_scorecard._score_one` at HEAD, both MATRIX configs)*

## The detail layer sewed the background a subject cutout had just removed — FIXED 2026-08-24

`cfg.photo_prep_background_removal` runs rembg in an isolated venv and hands
stage 1 a real subject/background split. Stage 2 respects it (background
pixels get label -1 and never become regions). The FDoG **detail layer** did
not, because it does not read regions at all — `extract_detail_lines` runs
over `SourcePixels.rgb`, the whole frame, and there was nothing on
`SourcePixels` for it to respect.

### Measured, per block

`baby_deck_laugh.png`, `forced_class=photo_subject` + `photo_prep` +
`photo_prep_background_removal`. rembg puts the subject at **10.0% of the
frame**. Every stitch point mapped back through `SourcePixels.to_px` and
tested against the mask the pipeline itself derived:

| | in subject | in removed background | bg share |
|---|---|---|---|
| blocks 0-15 (regions) | 4,278 | 301 | 6.6% |
| **block 16 (FDoG detail)** | 1,022 | **10,813** | **91.4%** |
| **design total** | 4,278 | **11,114** | **72.2%** |

The regions' 301 is boundary spill — fills reaching a hair past the mask,
plus nearest-pixel rounding in the probe. It is not worth chasing. The
detail block is **97.3% of all background stitches** on the design.

### The fix

`SourcePixels.subject_mask` (True = subject), set by `finish_generation`
from the same rembg mask stage 2 already receives, carried across the
generation cache on `Generation`. `stage6_detail._mask_to_subject` resamples
it to the field's working resolution (INTER_AREA, majority vote), dilates by
`_SUBJECT_SLACK_PX = 1`, and ANDs it into the line map.

Masking the **line map** rather than the traced polylines is load-bearing: a
polyline is kept or dropped whole, so post-filtering would keep any line that
merely starts inside the subject and then runs off across the deck.

| | before | after |
|---|---|---|
| detail-block background stitches | 10,813 | **537** |
| detail-block subject stitches | 1,022 | 1,062 |
| design stitches | 15,392 | **5,156** |
| design background share | 72.2% | **16.3%** |

**The 537 survivors are the slack band, not a leak** — verified by distance
transform, not asserted: median 0.82 working px outside the subject, p99
1.67, **worst 1.79, and zero beyond 3**. That band is the subject's own
silhouette, which is the single most valuable line FDoG finds on a cutout
portrait, and keeping it is why the dilation is there.

### Why the mask is the rembg one and not `~Prep.bg_mask`

The wider rule — mask to every background stage 1 knows about, including the
border flood — sounds more general and is very nearly inert. A flooded
background is uniform by construction and FDoG responds to a luminance step.
Measured on `testdata/logo_whitebg.png` (flat class, detail layer forced on,
flood covering **74.4%** of the frame): **0 of the detail block's 1,523
stitches** sew flooded background. So the narrow scope gives up nothing, and
it buys a guarantee the wide one could not — with no cutout the field is
`None` and `_mask_to_subject` returns its input array *by identity*, so no
pre-existing lane can have moved a stitch.

### The reason nobody saw this

**No acceptance arm had ever set `photo_prep_background_removal`.** Every
contact sheet judged to date sewed the whole frame, so "the background is
being embroidered" was never on screen as a thing to notice — it was the
picture. `variant_matrix` now carries a `subject_cutout` arm, gated on the
isolated venv the way `sam2` is (an ungated arm would sew a byte-identical
copy of `classical_prep` under a name promising a cutout — a silently-inert
column reads as "the cutout changed nothing", which is worse than a missing
one). Measured on the fixed code, all three unbound:

| arm | regions | blocks | cones | stitches |
|---|---|---|---|---|
| classical | 110 | 79 | 50 | 17,167 |
| classical_prep | 175 | 140 | 62 | 33,371 |
| **subject_cutout** | **29** | **21** | **13** | **5,190** |

Against its one-flag control `classical_prep`: **-83% regions, -79% cones,
-84% stitches**. And note the middle row — prep alone is the most expensive
arm on the sheet, and the cutout is the only thing that has ever paid it
back.

*(measured 2026-08-24 — per-block stitch/mask audit and distance-transform
check, both re-runnable against the acceptance stage dir)*

## The cutout ships ON, and the fallback direction was backwards — RULED 2026-08-24

Kent's ruling the day the subject cutout became visible in thread. Two parts,
and the second is the one with teeth.

### 1. The pair ships on

`photo_prep` and `photo_prep_background_removal` both default True, **as a
pair**. They are not independently defaultable, because prep alone is the most
expensive arm the acceptance harness measures — worse than doing nothing, on
all four portraits.

Measured on `baby_deck_laugh`, forced photo class, everything else default:

| path | regions | blocks | cones | stitches |
|---|---|---|---|---|
| cutout available (the shipped default) | **29** | 17 | **7** | **5,156** |
| cutout requested, venv missing → fallback | 110 | 48 | 12 | 16,570 |
| prep alone — what the OLD fallback gave | 175 | 84 | 12 | 32,663 |
| control, `photo_prep=False` | 110 | 48 | 12 | 16,570 |

Rows 2 and 4 are **identical geometry**, asserted by comparing every emitted
stitch coordinate rather than a pair of counts (`test_an_unavailable_cutout_
falls_back_to_no_prep_at_all`). Row 3 is 6.3x the stitches of row 1.

### 2. The fallback was failing in the expensive direction

A fallback is supposed to be the safe direction to fail in. This one degraded
onto row 3 — the worst result on the sheet — on precisely the machines least
able to absorb it. `pipeline.build_generation` now resolves the cutout first
and, if it was REQUESTED and could not be delivered, skips the whole prep
block: no face detection, no tone/texture pass.

The asymmetry is deliberate: `photo_prep=True` with the cutout flag OFF is an
explicit request for prep alone and still gets exactly that. Only an
undeliverable *requested* cutout triggers the skip. Without that, the fix would
have quietly deleted `classical_prep` — the acceptance ladder's second rung.

**Four existing tests had to pin `photo_prep_background_removal=False`.** Each
set `photo_prep=True` while relying on the cutout flag defaulting off, so each
would have silently stopped testing the gate it is named for and started
testing the fallback. Exactly what happened to every forced-class acceptance
arm when `shade_palette_bind`'s default moved, and worth expecting the next
time a default flips.

### 3. rembg is a deploy requirement — and CI is not evidence

Kent ruled the isolated venv a required deploy step, the same shape as building
`digitizer/.venv` itself. CI deliberately does NOT build it, so **CI exercises
the fallback path and a green CI run says nothing about the cutout.** That is
defensible — the fallback is the real shipped behaviour on a box without the
venv — but it must not be mistaken for coverage of the feature.

### 4. It ships knowingly inert for real uploads

Measured 2026-08-24: all four acceptance photos classify **`gradient` at
confidence 1.00**, and `gradient` is not in `PHOTO_CLASSES`, so the double gate
never opens for them. The pair is live only for a caller that forces
`photo_subject`/`photo_scene` — every acceptance arm, and any Studio photo
override, but not a user upload.

Kent's call was to ship it anyway and revisit at gate 2 rather than widen the
gate to gradient. The reason widening is not free: `gradient` is also the class
for genuine gradient LOGOS (`drone_render`, `summit_badge` are in the corpus),
where rembg would invent a subject that is not there. Telling photo-gradient
from logo-gradient is stage-0 discrimination wearing a different hat — which is
gate 2 itself.

*(ruled 2026-08-24 — Kent; measurements same day, re-runnable from the
acceptance stage dir)*

## Fill quality INSIDE the shapes — Kent's front as of 2026-08-25

Kent, on the first thread renders of the subject-cutout arm: *"your
shape/bordering and feature recognition is getting VEERY good ... My main
concern is how the stitching looks within each one of those photos."*

That is a different problem from everything area 1 has worked on this month.
Region identification got good enough that what shows is what happens
**inside** each region.

### The number already exists

`stitchviz.coverage` (PR #234) renders a design twice — once on black, once on
white — and reads the per-pixel difference, so a fully covered pixel matches,
a bare one differs by 255, and an anti-aliased edge differs in proportion. It
runs at a fixed `COVERAGE_PX_PER_MM`, never the display scale, because a
number that moves with how you look at it is not evidence.

| route | covers its own footprint |
|---|---|
| streamline thread-paint (`classical`, `bound_shade`, `subject_cutout`, …) | **0.55 – 0.59** |
| gradient blend (`default_stock`, `default_relaxed`) | **0.99** |

**Nearly half the cloth inside a photo-route shape is bare.**

### Why this is not simply a bug

The streamline tier's *fabric-as-value* intent is documented and deliberate:
the garment colour reads as a tone, and the thread supplies the darker values.
That is a legitimate embroidery idiom, not an accident.

But it is a **different product** from a filled design, and no contact sheet
ever said so — the two routes sat in adjacent columns of the same sheet,
scored by the same counts, with nothing indicating that one covers the cloth
and one does not. Kent has been judging them side by side without that being
visible.

### What NOT to assume

- **Not necessarily density.** Raising row density on a tier whose whole
  premise is exposed fabric may just make it a bad fill instead of a sparse
  one. The question is which product each design should be, and possibly
  whether the tier choice itself is the defect.
- **Not settled by geometry.** How much bare fabric reads as "shading" versus
  "unfinished" is a fabric-and-thread question — ROADMAP gate 1 territory the
  moment it turns into a spacing constant.
- **Not measurable from the old instrument.** Every pre-2026-08-24 sheet was
  vector proofs, which cannot show coverage at all. Any prior judgement about
  fill appearance was made without the evidence.

*(measured 2026-08-24 — PR #234's coverage column; Kent's framing 2026-08-25)*

## Letterform quality — MEASURED 2026-08-26, four mechanisms, nothing fixed yet

Kent, on a sewn `drone_render` wordmark: *"All N's look bad — bottom right
drops away too quickly"*, *"the H edges are not clean and crisp"*, *"the E in
THERMAL doesn't look clean"*; and on a sewn **Becker Marine** logo the same
day: *"We lost the bottom right portion of the R — ROOKIE MISTAKE"*, *"the R
Radius is rough and jumpy, lettering should be smooth (along with the A)"*,
*"When doing lettering, fill angle should be the same ... Why is the N running
Vertically?"*

**No code changed. Narrative, traps and the ruled-out list:
`.claude/memory/letterform-fidelity-2026-08-26.md`. Re-derivation:
`digitizer/tools/letterform_fidelity/`.** (measured 2026-08-26 — 13-agent
workflow on `drone_render.png`, plus Kent's annotated Becker screenshot)

### The instrument was the reason this survived

**Bare-fabric coverage scores THERMAL's `H` at 1.9% bare — "fine". The `H` is
visibly deformed.** Coverage cannot see a tilted column, a rounded corner or a
scalloped edge; thread is present in all three, just in the wrong place.
Shape fidelity (thread-vs-artwork IoU, `s11_iou.py`) reads **0.587** design-wide
over 20 letters — 0.652 big text, 0.489 small. Screening only: it saturates on
small letters (`DRONE` `E` scores 0.534 against a 0.580 ceiling while sewing as
an "L"). Per gate 4 it is a direct geometric measure, not an agreement rate —
**but no quality claim rides on it yet.**

### The four mechanisms, ranked

| # | Mechanism | Site | Evidence | Gate |
|---|---|---|---|---|
| 0 | **No stitch-angle policy for satin.** `satin_shape()` takes no angle argument; every cross is that shape's own spine tangent, so each letter and each stroke picks its own angle. `fill_angle_deg` exists for FILL with a global + per-shape override + PCA fallback; satin has **no counterpart**. | `stage6_satin.py:2339`, `:1241`; cf. `config.py:452` | Kent's Becker note. Coverage and fidelity are **blind** to it — wrong angle can score a perfect IoU. | none (design decision; the angle a pro picks is Kent's call) |
**Measured against the pro (2026-08-26).** Cross angles by stitch length
(>= 0.8 mm), mod 180, from the professional `becker_*.dst` for artwork we also
have; EMB-Bot's side read from the planner, never through a DST. Pro: modal
2 deg, **6/7 letter runs within +/-20 deg**, 50.7% of satin length within
+/-15. EMB-Bot, same artwork: modal 92 deg, **9/43 = 21%**, 18.0%. **A +/-20
window is 22% by chance — our letter angles are indistinguishable from
random; the pro's are not.** Not a matched benchmark (the pro side is one text
band, ours the whole logo, and we fragment 43-vs-7), and the pro itself spreads
~19 deg, so the convention is "one angle held loosely". *(measured 2026-08-26)*

| 1 | **Pull comp is a blunt round-join dilate applied BEFORE decomposition**, with no minimum-feature floor. Corners become 0.3 mm arcs (N: 11 vertices → 130); every exterior concavity narrows by `2 × pull`. The min-feature guard **exists but is scoped to `poly.interiors`** — counters protected, the E's arm slots and the N's crotch untested. | `stage5_overlap.py:227`, guard at `:424` | THERMAL E slots 0.936 → **0.336 mm** (< one thread); DRONE E 0.728 → **0.128 mm**, sealed. `pull=0` control: fidelity 0.587 → 0.747. | Fix not blocked (subtracts only, changes no constant). The **control** is diagnostic — pull comp itself is gate 1. |
| 2 | **`_prune_spurs` destroys the branch node its docstring promises to keep.** Deleting a short corner twig drops a 3-way node to degree 2, so the walker welds two arms into one column folding ~108°. `_WELD_MAX_DOT` exists for this and is never consulted; it would have refused (dot +0.386). | `stage6_satin.py:958`, called `:1126`; consts `:93`, `:100` | Ablation: PRECISION.N bare **12.7 → 4.1%**, DRONE.N 18.6 → 0.9%, AND.N 14.0 → 1.3%. Confirmed on Becker's `R`. | none |
| 3 | **"AND DRONE" is below renderable size** — 0.55–0.70 mm strokes at 2.91 mm caps, against a ~5 mm / ~1 mm trade minimum. | `s12_stroke.py` | With pull comp it covers but reads `AИD DROИX`; without, letterforms are right but 20–39% bare, reading `ΛND DRONL`. **Coverage or shape, not both.** | not a code problem — Kent's sizing call, parked 2026-08-26 |

### Text clustering — WIDENING ATTEMPTED AND REVERTED 2026-08-26 (code: `10ae9cc`)

Kent's scope call, built, measured, and then **backed out of PR #267 by his
decision** when it turned a real e2e contract red. The code is preserved at
commit **`10ae9cc`** — pick it up from there rather than rebuilding.

**What it proved (all measured, all still true):**

- The `rescued_small_shape` gate at `textcluster.py:541` is what blinds this
  feature: `becker_marine_logo.png` 17 regions -> 0 candidates;
  `drone_render.png` 74 -> 10 candidates, 0 clusters.
- Two extra doors fix that — an eligibility bound (aspect + height 1.5–60 mm,
  a sewability floor and a *cost* ceiling) and a looser stroke-CV bound for
  non-rescued regions. `STROKE_CV_MAX = 0.32` is calibrated on fragments and
  too tight for whole glyphs, whose skeletons cross junctions: Becker's six
  text-band letters read **0.41–0.48** and were all rejected. 0.55 clears them
  and still refuses that logo's graphic mark at 0.68.
- Result: becker **11** in 1 cluster, drone_render **26** in 2,
  enthusiast_logo 25 in 2, summit_badge 24 in 3, logo_bridge_bar 18 in 4. On
  `enthusiast_logo` it correctly finds **"ENTHUSIAST"** (10 letters, thread 14,
  6.5 mm caps) alongside the pre-existing rescued "ENTERPRISES INC" (14, 1.6 mm).
- Keeping `regularize_text_clusters` scoped to all-rescued clusters (via a new
  `text_cluster_all_rescued` flag) means **no stitch moves**: all 60 golden
  byte-identity tests passed, full suite 1417 passed / 3 failed (the documented
  deselects, unchanged node IDs).

**Why it was reverted — two separable problems:**

1. **A stale e2e contract.** `app/e2e/text-cluster-convert.spec.js:225` converts
   one cluster then asserts *page-wide* that zero "looks like text" badges
   remain, and that `unstitched == unstitchedBefore + badgeCountBefore`. Both
   hold only while a design has exactly ONE cluster. Mechanical to fix — the
   assertions need to be per-cluster — but it is a real behavioural change the
   golden suite could not see, because `text_candidate` drives a **UI badge and
   the Convert-to-text flow**, not geometry.
2. **A false positive with no known discriminator.** That new cluster has 11
   members and "ENTHUSIAST" has 10. The extra is the star inside the red shield
   (`x −35.6…−30.2`, 5.4×5.4 mm, thread 149 vs the letters' 14). Converting the
   cluster would drag a graphic glyph into the text.

3. **A suspected COST regression — the one that was least expected.** CI's
   digitizer job went red on `10ae9cc` with
   `test_service.py::test_review_payload_carries_text_cluster_fields_over_http`
   timing out: that test polls `/digitize` on `enthusiast_logo.png` 600 x 0.1 s
   and got `running` at the 60 s budget. The run took **17:55** against
   **9:38** for the same suite locally, where it passed.

   Suspected, not proven. **For:** removing the `rescued_small_shape` early
   exit makes `_skeleton_stroke_stats` (rasterize + skeletonize) run on far
   more regions, and the single test that failed is the one most directly
   exercising text clusters — generic slowness would have been likelier to
   hit some other long test. **Against:** four CI runs were queued
   concurrently, so runner contention alone could explain a slower wall clock.
   The cheap aspect/height pre-filters were added ahead of the skeleton call
   for exactly this reason and evidently were not enough on a slow runner.

   **One datapoint added 2026-08-26, and it is a datapoint, not a control.**
   `312574f` — docs, standalone tools and one docstring, so **zero Python
   behaviour change** — ran the digitizer job GREEN in **15:28**, with the
   `test_service` test passing. That is the same suite without the widening.
   It does not settle it: the red run had FOUR CI runs queued against this
   one's TWO, so the contention is not matched. What it does do is make
   "contention alone" a longer stretch than it was — contention at this level
   cost 15:28 and passed.

   **Whoever resumes this must measure `detect_text_clusters` wall time
   directly**, per fixture, before and after — not infer it from suite
   duration, including not from the paragraph above. A 60 s service budget is
   the constraint to design against.

**Do not reach for thread purity — it is DISPROVEN.** Requiring one thread per
cluster excludes the star and destroys `drone_render` detection entirely: its
23 genuine letters span six near-identical quantized threads
(`{308:6, 17:1, 16:3, 119:5, 8:7, 101:1}`). Measured 2026-08-26.

Next candidate is inter-glyph gap — the star sits **6.3 mm** from its neighbour
against **~0.4 mm** between letters — but a bound tight enough to exclude it
risks splitting "ENTERPRISES INC" at its word space, so it needs measuring
across fixtures, not tuning on one. *(measured 2026-08-26)*

### The angle policy's prerequisite is not free

`detect_text_clusters` (`textcluster.py:618`, wired at `pipeline.py:564`)
already groups regions into words — but its candidate set is gated on
`rescued_small_shape` (`textcluster.py:541`), so ordinary lettering never
enters it. Measured: `becker_marine_logo.png` 17 regions / 0 rescued / **0
text_candidate**; `drone_render.png` 74 / 10 / **0**. **We currently identify
zero letters on both a real client logo and the wordmark fixture.** Widening
the entry condition is necessary and may not be sufficient —
`MIN_CLUSTER_MEMBERS = 3` and the stroke-CV/aspect filters are next in line.
*(measured 2026-08-26)*

**A pattern worth carrying:** this is the third mechanism in one investigation
that is correctly implemented and scoped to a subset excluding the common case
— with `stage5_overlap.py:424` (guard tests `poly.interiors` only) and
`stage6_satin.py:958` (`_prune_spurs` keeps the node pixel, drops its degree).
Each is invisible to tests because the narrow case it *does* cover works.

### Two candidate fixes that must NOT ship as written

- **`_SPLIT_TURN_DEG 90 → 70`** cures all three N's in one line, and breaks
  `test_satin.py:799` plus the `ribbon_curve.png` byte-identity golden
  (1001 → 1019 stitches) — a key clean today, not a sanctioned exception, whose
  rule reads *"If this test ever goes red, the change under review is wrong."*
  The 90.0 is corpus-derived (1,436 in-run corner events vs 18 splits across 19
  professional files). **Withdrawn.**
- **Mitre join instead of round** keeps corners square but deposits
  `pull / sin(θ/2)` — measured 0.4243 mm at 90°, 0.9405 mm on a 3.4° wedge —
  against a 0.30 preset, failing the repo's own invariant (0.3746 vs 0.3 ±
  0.002). **ROADMAP gate 1 — blocked until a sew-out.**

### Ruled out — do not re-investigate

Stages 1–3 (per-glyph IoU 1.000 for 24 of 27 glyphs, never below 0.995).
Stage 4 `approxPolyDP`/`simplify_tol_mm`/`min_detail_mm` (worst deviation
0.196 mm against a 0.2 mm promise; sweeping `min_detail_mm` 1.5 → 0.3 recovers
no area — stage 4 is the healthiest stage in the pipeline). Tier
misclassification (all 24 letters correctly satin; flat and gradient identical
by construction; forcing flat is worse, 74 → 350 regions). Forcing letters to
FILL (threshold swings with `fabric.pull_comp_mm`, the coupling
`stage7_sequence.py:1197-1203` forbids). `SATIN_MIN_CROSS_MM` dropping the N's
crosses (drops 2 of 54, both ~9 mm from the fold — the corner is bare because
no spine goes there).

### Separate ticket, different fixture

On `summit_badge.png`, where glyphs sit on a filled ground, **stage 2 fuses
"U"+"M" and cuts the "S" in half.** Irrelevant to `drone_render`, whose glyphs
are topologically isolated islands, but real.

## Lettering house-angle: the three miscalibrated thresholds (moved from MASTER_SCOPE 2026-08-27)

Moved verbatim under the 800-line budget rule. Nothing edited in the move.

Three things had to be corrected to get there, each a threshold applied to a
population it was not calibrated on — the reusable lesson:
- `detect_text_clusters`' candidate set is gated on `rescued_small_shape` and
  on `STROKE_CV_MAX` (0.32). **Zero** of that logo's 17 regions carry the flag,
  and all 17 score CV **0.36–0.68**, so it finds no real lettering at all.
  `_lettering_groups` keeps the tests that transfer and drops those two;
  `detect_text_clusters` itself is untouched.
- The confidence gate was `directionfield.COHERENCE_FALLBACK_MIN` (0.25), which
  grades a per-pixel structure-tensor field. Real lettering sits UNDER it
  (R = 0.197 and 0.203). No raw threshold works: directionless square rings sit
  at 0.167. Replaced with Rayleigh's test — chance-corrected, rings and letters
  separate 10× where raw they separate 1.2×. Gate 4 in miniature.
  **Correction 2026-09-02:** the 0.167 was read on a DEGENERATE fixture —
  buffered square rings survive spur pruning as 2.5–3.5 mm corner-arc
  remnants, and true circular annuli read R = 0.008, which a raw floor WOULD
  separate from lettering. The chance-corrected conclusion still stands on
  independent evidence (the 8-bar fan at R = 0.209 admitted on n_eff; the
  3-bar fan at 0.234 rejected on n_eff — `test_textcluster.py`).
- **7 of 11 lettering regions sew as FILL**, where the satin angle is not read
  and `best_fill_angle_deg` picks rows per shape by minimising that shape's own
  column count — which put two adjacent near-identical capitals at 22.5° and
  90.0°. That is the half Kent's complaint actually names. The house angle now
  sets `fill_angle_deg` too.
*(fixed 2026-08-27 — PRs #282/#283, mutation-checked; renders in the #283 body)*

## Lettering house-angle: the FOURTH miscalibrated threshold, and the four-fold reading (2026-09-02)

The doubled-angle Rayleigh gate above is blind to lettering whose horizontals
balance its verticals — most slab-serif and many sans block faces. Hotel
Fremont's twelve capitals: R = 0.055, n_eff 1554, nR² 4.7 against 6.9,
rejected, and the whole word sewed per-stroke — which is Kent's *"E heavy on
top and bottom"* and *"T left side drops"* (hanging-serif corner fans, see the
mechanism table in `docs/hotel-fremont-fine-details-2026-09-02.md`).

`_cluster_house_angle_deg` now tries a second reading in four-fold space when
the first finds nothing. Three measured constraints, each pinned by a test in
`tests/test_textcluster.py`:

| | raw pixel steps | 4 px chord |
|---|---|---|
| 24 annuli (no direction) | R4 **0.160 @ 45°** | 0.051 |
| 4 bars 45° apart (cancel by construction) | **0.527** | 0.127 |
| Hotel Fremont capitals | 0.185 | **0.444** (nR4² 90) |
| Hotel Fremont "THE" (2.6 mm) | 0.316 | **0.657** |
| 6 synthetic I-beams | 0.707 | **0.903** |

Raw steps carry the raster's own four-fold staircase, so the four-fold votes
are resampled at `SATIN_HOUSE_CHORD_PX` = 4; the doubled votes stay raw, so
every previously admitted cluster is byte-identical (Becker, enthusiast:
md5-checked). The residual ~0.05 is systematic and clears significance at 24
annuli (8.0), so `SATIN_HOUSE_FOURFOLD_MIN_R` = 0.25 is an effect floor
against a biased null — a floor against bias, not a quality threshold. The
angle is the 45° bisector: house = 0 scrambles every horizontal through
`_clamp_to_span`'s ±45 sign flip (rendered, worse than nothing); and because
the axis is only defined mod 90, `_bisector_deg` picks the bisector nearer
the convention — raw "axis + 45" gave drone 45.1 and Fremont 134.4.

Fires on `drone_render`'s THERMAL (T, H, E, R gain 45.1°, +0.4% stitches,
trims flat) — the letters of the 2026-08-26 complaint.

**Default OFF — `PipelineConfig.satin_house_fourfold`.** On `enthusiast_logo`
@ 93 mm (the chaining benchmark's pitch) the reading angles the eleven
ENTHUSIAST capitals at 48°: E, T, H uniform, but the N's diagonal runs near
the house and `_clamp_to_span` piles it at the junction, and trims go 19 → 22
chaining off, 8 → 15 chaining on — **2.43 → 4.62/1k against the 4.1 ceiling**.
Measured trim regression, rendered gain on two wordmarks, rendered loss on
one diagonal: the exterior-notch guard's shape, so the same disposition.
Off, ten fixtures md5-identical to main. *(measured 2026-09-02)* **Still open:** the
pro sews horizontals as wide short columns at ONE near-horizontal angle; our
rail model cannot (a cross along a bar collapses to the centreline). That is
a new construction, Kent's call.

## Curve-fidelity instrument — the fuller MASTER_SCOPE entry (moved 2026-08-28)

Compressed in MASTER_SCOPE under the 800-line budget; kept here in full.

**Both halves of the smoothness complaint now have instruments, and they are not
the same measurement.** `tools/edge_smoothness.py` owns the edge noise; the curve
half — *"Lines/circles are not smooth like the photo"* — is
`tools/curve_fidelity.py`, read from `plan.iter_runs()` because it is **not
readable from a raster** (a rasterised circle scores more angular than a 40-gon;
the raster boundary is itself a staircase). Rebuilt on path geometry it is
monotonic across the n-gon ladder at 0.5/1.0/2.0 mm sampling, and **dead at
3.0 mm** — a physical floor, not a bug: the needle is then as coarse as the
polygon, so never compare arms across stitch lengths. **Read `roughness_deg` per
design. `turn_gini` is substantially a COMPLEXITY statistic** (Pearson −0.763 vs
log trace count; two 2-trace designs pin the top at 0.95) and belongs only on the
ladder or inside a paired arm holding one design fixed. The two instruments are
not redundant — `roughness_deg` vs `ragged_mm` is Spearman 0.028, which on n = 12
rules out redundancy without proving independence. Instrument only, no engine
change. *(measured 2026-08-27 — PR #281;
`docs/curve-fidelity-from-the-stitch-path-2026-08-27.md`)*

## Fill travel under cover — defect 21 FIXED, default ON by Kent's flip (2026-09-03)

Kent's *"the in-fill stitching doesn't look clean"* (Hotel Fremont, 2026-09-02)
was 22 of 27 fill-phase travel runs, 286 of 450 mm, laid on top of columns
already sewn. Two mechanisms in `stage6_fill`, behind
`PipelineConfig.fill_travel_under_cover` (built False, flipped True by Kent
the same session; False is md5-identical to main on becker, drone,
enthusiast, Fremont):

- `travel_path(..., sewn=...)`: straight only if straight crosses unsewn
  ground; else the inset rings of the UNSEWN remainder (`cover − sewn`, half-
  row inset, either way round, endpoints allowed one travel stitch — clipped
  to the shape, and every covered route is hard-tested against the shape);
  else the shape's rings both ways; else the exposed route it always took.
- `_reorder_for_cover`: the nearest-first column walk prefers a next column
  whose straight bridge is inside the shape and off the fill laid so far;
  scored by `_order_cost` (cuts × 25 + travel + exposed travel × 2 — the 2.0
  ratified by Kent 2026-09-03 alongside the flip) against the incoming
  order and kept only when cheaper; last path pinned.

Measured ON (fill-phase travel over the sewn footprint, one-stitch tolerance;
`tools/fill_exposure.py`):

| fixture | exposed before → after | stitches | trims |
|---|---|---|---|
| `logo_hotel_fremont` | 286 → 90 mm | 6473 → 6385 | 47 → 52 |
| `logo_gaulke_roofing` | 204 → 8 mm | 3954 → 3863 | 24 → 26 |
| `becker_marine_logo` | 30 → 14 mm | 4557 → 4529 | 28 → 28 |
| `drone_render` | 546 → 89 mm | 9317 → 8753 | 86 → 91 |
| `photo_dof_meadow` | 691 → 324 mm | 10116 → 9667 | 33 → 35 |
| `photo_sunset_backlit` | 711 → 344 mm | 12345 → 11620 | 53 → 42 |

Routing alone was measured first and moved nothing (Fremont 286 → 286): the
inset ring runs through sewn columns, and by the time a bridge is built the
exposure is already decided by the order. Cost: digitize +7–11% on logos,
+49–67% on sunset's 263-run blend fill after two optimisations (`_ring_route`
rebuilt its arc table per call — 34.8 s of a 90 s profile — now cached; the
unsewn rings are reused across bridges and re-checked against the current
unsewn ground). The trims that return with the flag are the score buying
hidden travel with cuts at 2 : 25, Kent's price. The `logo_whitebg` goldens
moved by their travel (2166 → 2162 penetrations) and are re-pinned per the
recapture doctrine with the pre-change tree.
*(measured 2026-09-03 — `docs/fill-travel-under-cover-2026-09-03.md`)*

## Stitch-angle rule, pass 1 — fading lean, 30° cap, density under lean (2026-09-03)

Kent's ruling (DOCTRINE) built in `stage6_satin` and `textcluster`, flag
`satin_house_fourfold` still OFF; every fixture without a house angle
md5-identical. Full record `docs/stitch-angle-convention-2026-09-03.md` §7.

- `_clamp_to_span`: house held within the lean cap (`SATIN_HOUSE_MIN_SPAN_DEG`
  60, a 30° lean); past it the lean fades linearly to zero at the house axis
  — a bar along the axis takes its own perpendicular with no side to choose,
  a 45° diagonal leans 22.5°. Continuous, pinned in twentieth-degree steps.
- `_cross_angles` (factored out of `_rail_points`, byte-identical with no
  house) returns each station's lean against the smoothed perpendicular;
  `_resample_by_pitch` spreads the stations along ∫cos(lean) ds and the
  outer-rail refinement targets the same pitch, so the thread pitch across
  the column stays 0.20 mm however far the cross leans. Cosine floored at
  cos(cap) by construction.
- Four-fold reading: the bisector is replaced by the stems' perpendicular,
  stems = the family square to the line of text (`_line_of_text_deg`, the
  principal axis of member centroids; `_house_along_line_deg`). "Longer
  family" was measured wrong on THERMAL and ENTHUSIAST.

| housed lettering (`tools/satin_lean.py`) | thread pitch | crosses | stitches | trims |
|---|---|---|---|---|
| Fremont, flag on, house 44° → 0° | **0.152 → 0.198 mm** | 885 → 812 | 6405 → 6343 | 52 → 52 |
| ENTHUSIAST @ 93, flag on, 48° → 3° | **0.152 → 0.200** | 1096 → 1001 | 3072 → 3005 | 22 → 25 |
| THERMAL, flag on, 45° → 0° | 0.175 → 0.195 | 1829 → 1859 | 8791 → 8856 | 91 → 93 |
| Becker MARINE (doubled reading) | 0.193 → 0.186 | 694 → 724 | 4529 → 4524 | 28 → 28 |

Lean off each cross's own perpendicular on Fremont: p50 45 → 20°, past 45°
50% → 3%, against a stock floor of p50 19°, 1% (raster wander). The
chaining benchmark with the flag on: 4.62 → 4.09/1k against 4.1 (off: 2.43,
unchanged). Corners still sweep (a merged stem-to-bar chain turns its cross
90° across the smoothing width; Becker 40% past 45° vs 24% stock) — the
Goldman join, pass 2. Two limits found: hairline columns under ~0.6 mm lose
crosses to the 0.5 mm minimum under any house angle (Fremont's 2.6 mm
"THE"; the shipped default already loses its bars; a lean floor was built,
fanned 45→2→45° on a 2.5 mm stem, withdrawn), and `place` dents one whole
rail of a rotated stock bar by 15% (1.22–1.27 vs 1.44–1.46 mm on a 3 mm bar)
— pre-existing, in every golden, its own PR.
*(measured 2026-09-03 — `docs/stitch-angle-convention-2026-09-03.md` §7)*

## Stitch-angle rule, pass 2 — the Goldman corner join (2026-09-03)

`stage6_satin._split_sharp_corners` finds JOIN corners (spine turn ≥
`_JOIN_TURN_DEG` 45° over a half-width, with a reflex boundary corner ≥ 45°
within a 1 mm arc window near the apex, `_boundary_corner_near`) and records
them on the stroke (`Stroke.corners`) instead of splitting it; `satin_stroke`
→ `_satin_joined` sews the members as separate columns end to end, the
longer one capped over the corner square, the other tucked under the
owner's corridor. Fold cuts (≥ 90°) split as before; welded corner twigs are
dropped and the stem capped square; tapered tips and hairlines (< 0.6 mm)
never join. Why one stroke: a split bought an underlay hop and a trim per
piece (Becker 28 → 50 trims, benchmark 4.09 → 5.03/1k).

| fixture | corners joined | stitches | trims | bare fabric | crosses > 45° off perpendicular |
|---|---|---|---|---|---|
| Fremont | 10 | 6343 → 6365 | 52 → 52 | 3.4 → 3.2% | 3 → 3% |
| drone | 18 | 8856 → 8729 | 93 → 93 | 2.8 → 2.2% | 26 → 17% |
| Becker | 21 | 4524 → 4479 | 28 → 28 | 6.0 → 5.5% | 40 → 27% |
| ENTHUSIAST @ 93 | 8 | 3005 → 2959 | 25 → 25 | 1.8 → 1.8% | 31 → 21% |

Benchmark 4.09 → 3.81/1k. Goldens untouched. Closed rings keep the fold rule
(review: the join had opened a hexagon at two, three, two or one of six corners
by rotation). Capitals measured; a lowercase bowl joins its stem corner too,
unmeasured. Junction fans at 3-way nodes are
not corners and are left to `_junction_entry_mm`; THERMAL's E arms remain
pull-comp-sealed slots (gate 1). *(measured 2026-09-03 — `docs/stitch-angle-convention-2026-09-03.md` §9)*

## Round curves (defect 22) built OFF, and the fill-dust half-stitches (defect 25) — 2026-09-03

`stage4_vectorize._refine_curves` behind `PipelineConfig.curve_turn_deg`
(default None, byte-identical): re-reads each Douglas-Peucker edge against
its raw contour arc and splits at the arc midpoint until the sagitta is
under min(`simplify_tol_mm`, chord × turn/8), floored at 1 px, inserted
vertices a ±2 px mean. Fremont's O counter 9 → 33 vertices (47° → 17°),
inner rail σ 0.038 → 0.026 mm. With the dust splitter masked the flag moves
stitch counts ≤ 2% everywhere; `curve_fidelity` roughness ribbon 9.45 →
8.72, drone 9.32 → 9.11, ENTHUSIAST 10.59 → 11.42 (half-pixel jitter at
11 px/mm — the resolution limit). Becker at 4 px/mm unchanged.

Defect 25 — FIXED the same day (Kent's ruling; `stitches.SPLIT_TOLERANCE_MM`,
a micron): `split_long_moves(path, stitch_mm)` halved grid steps that exceed
3.0 mm by float dust — `tools/fill_dust.py`: whitebg 180 of
1520 fill steps (8.3% of the design), Fremont 576 of 2450 (9.0%), sunset
1198 of 7102 (10.3%), alpha 5.0%, Becker 1.3%, drone 0.7%. After the fix:
whitebg 2162 → 1982 st, alpha 2072 → 1968, Fremont 6365 → 5789, sunset
11614 → 10416, drone 8729 → 8670, Becker 4479 → 4421; no row, trim or region
moves; whitebg and alpha goldens re-pinned with the pre-change tree. The
curve flip is held; near-floor lettering (ribbon width within 20% of the
minimum cross) is not refined, Kent's ruling. *(measured 2026-09-03 — `docs/round-curves-2026-09-03.md`)*

## Rail dents — defect 23 FIXED, and what it actually was (2026-09-03)

The recorded defect ("`place` dents one whole rail of a rotated bar by 15%,
in every golden") was a synthetic-bar reading: with an exact spine the
smoothed width equals the ray hit to the ulp and `covers` is a coin flip
(29–54% of stations dented at 10/25/45°; a micron of tolerance → 0%). On
the real fixtures that case is 1–11% of the containment misses and the
micron alone moved 4 stitches on Fremont, 4 on drone, 2 on ribbon. The
mechanism that matters: 250–1000 rail placements per design overshoot the
edge, 70–90% of them by under 50 µm (a pixel or less), and three quarters
then took the ladder's 0.85× step — a 0.15–0.25 mm dent for a micron of
overshoot. Fixed by placing the overshooting rail on the nearest boundary
crossing along its own normal (`_COVERS_TOL_MM` = 1e-6 on containment; the
ladder stays for rays with no crossing; taper zones and terminal stations
keep the old ladder — rails placed exactly on a converging tip bunch and
feed the short-stitch guard, measured on the ribbon head). Rail jitter p50:
Fremont 0.0120 → 0.0045, ENTHUSIAST 0.0421 → 0.0241, drone 0.0404 → 0.0258,
Becker 0.0612 → 0.0378, ribbon 0.0161 → 0.0071 mm; same-rail holes Fremont
11 → 5, Becker 72 → 63; median cross wider everywhere; median rail-to-edge
0.02–0.08 mm further out; max outside the art unchanged (pull comp); trims
unchanged. Still open: 8–24% of rail points on lettering sit > 0.1 mm
inside the art from the symmetric-offset model itself (smoothed width below
the local edge on the wider side), the guard on bends, junction caps — a
different construction. Goldens: alpha, ribbon ×3 re-pinned with the
pre-change tree (main at 70df648); whitebg byte-identical.
*(measured 2026-09-03 — `docs/rail-dents-2026-09-03.md`)*

## #328 review follow-up — the near-floor curve guard is per ring (2026-09-03)

The shell-only guard skipped Fremont's near-floor letters correctly and
they fell to fill anyway: the letters are holes of the background region,
those holes were refined, and stage 5 reshapes a letter against its
background's hole (24 → 0 satin penetrations on `S54b55cf1` under
`curve_turn_deg=15`, pre-change tree). `stage4_vectorize` now gates every ring on its own
ribbon width and repairs an invalid ring before measuring it. Fremont ON
vs OFF: `S54b55cf1` 28 → 28 satin penetrations, `S9bac9a3c` 16 → 16, 19
satin / 5 fill shapes either way, trims 52 → 45. Open: a ring letter at
the floor is measured by its shell alone (no fixture has one).
*(measured 2026-09-03 — `docs/round-curves-2026-09-03.md`, review follow-up)*

## Round curves — the flip (2026-09-03): `curve_turn_deg` = 15 by default, gated to four pixels

Per-shape tier diff over every fixture (`tools/curve_tiers.py`, shapes
paired by centroid): ungated, Fremont (31 px/mm) counter 9 → 33 vertices,
roughness 3.19 → 2.91, trims 52 → 45, no tier change; drone (19) roughness
7.51 → 7.36 but a 12 × 3 mm ribbon fell satin → fill (`explained` 0.83 →
0.70: the 1-px skeleton grew 17% more spurs off the refined boundary);
gaulke (16), ENTHUSIAST (15), sunset, meadow, whitebg/alpha/ribbon (10)
all ROUGHER with 40–80% more vertices, meadow a 2.4 mm blob fill → satin
(cv 0.53 → 0.48). Floors of 2–3 px cost half the O (17 vertices, 27°).
Gate at four pixels of tolerance (`_CURVE_MIN_EPS_PX`): only Fremont among
the fixtures refines; everything else byte-identical, no golden moves.
*(measured 2026-09-03 — `docs/round-curves-2026-09-03.md`, "The flip")*

## Satin/fill classifier under boundary detail — measured negative (2026-09-03)

`tools/ribbon_stability.py`: over the 219 shapes the DT gates judge on the
ten fixtures, 5 verdicts flip when the polygon gains boundary detail (the
ungated curve refinement) — drone's 12 × 3 mm ribbon (`explained` 0.83 →
0.70), a 0.85 mm drone shape at the aspect gate, two gaulke shapes at
cv 0.5, meadow's 2.4 mm blob at cv 0.5. Eight cures measured (spur pruning
at 1/1.5/2× the junction radius: flips 8/4/3, shipped verdicts changed
2/12/16; the sewing spur rule: 6/4; hybrid: 6/2; raster smoothing 1 px:
7/18, 2 px: 12/48 and BAR/T fall to fill; regularity band: 6/15). None
adopted. The classifier depends on the whole skeleton to see a blob, and
its thresholds are knife edges on statistics that move ~0.05–0.1 with
boundary detail. *(measured 2026-09-03 — `docs/classifier-stability-2026-09-03.md`)*
