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

**And that pixel gate is now a measured defect of its own (2026-09-06 —
MASTER_SCOPE 28).** `preflight._MIN_COLOR_PIXELS` is **50**, so every shape of
**50–199 px** can be scored and BLOCKED by preflight and never corrected here.
On `screenshot_phone_ui_golke` the function asks about 74 shapes, skips 67 as
`enclosed_background`, and REFUSES 12 — all 12 in that band, 7 of which would
change answer under this function's own estimator and its own 3.0 dE gate.
Worst is the design's worst finding: `S43831dcd`, **177 px against a floor of
200**, `0111 Whale` at 32.7 dE where `0015 White` scores **1.4**. Across the
seven F-grade fixtures the refusal counts are 0/0/0/4/7 against `bridge_bar`
**63** and `screenshot` **12** — the two the F-wall decomposition attributes to
this cause.

**FIXED, DEFAULT ON since 2026-09-10** (`cfg.revalidate_small_shapes`, built 2026-09-06, flipped with the colour bundle). ON, the
re-ask uses `THREAD_REVALIDATE_MIN_PX_SMALL = 50` — preflight's own floor — and
a shape admitted only by it may take only a cone the design already carried at
pass entry. `screenshot_phone_ui_golke`'s worst thread ΔE00 **33.0 → 21.2**
(`S43831dcd`, 177 px, `0111 Whale` 32.7 → `0015 White` **1.4**), 21 of 26
fixtures byte-identical, and **no grade or block count moves anywhere**:
`THREAD_MATCH_POOR` blocks per thread on that thread's worst patch, so fixing
six of a thread's shards is invisible while a seventh is bad. It fixes sewn
colour the scorecard cannot see — a phase-1 datum, with the render at
`docs/renders/small-shape-resnap-2026-09-06/`. Flipping it ON was Kent's (done — flipped 2026-09-10; confirmed 2026-10-08 — `digitizer/digitizer_core/config.py` `revalidate_small_shapes: bool = True`).

**And a sibling correction in the check that condemns those shapes**
(2026-09-06): `preflight._region_color_errors` scored `enclosed_background`
regions, which are unstitched by default and whose colour is the background's
— the category error `revalidate_threads` already refuses. Skipping them
removes exactly ONE finding across the 26-fixture matrix
(`logo_gaulke_roofing`'s `4174`, F 0 → F 4, blocks 3 → 2) and moves no grade
letter. Two constructions were rejected on the way and are recorded in
DOCTRINE: a plan-derived denominator (breaks ten deliberate `test_preflight`
cases that pass a synthetic plan) and an instrument that filtered `run.jump`,
which is how the needle ARRIVED and not travel — it falsely made this look
like eleven findings.

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
(1 block, 6 warn), worst dE 10.2. *(These were the `307e69d` figures; the
baseline was recaptured 2026-10-04 and 2026-10-05 and now reads, at
`hat_front` and `left_chest` alike, `drone_render.png` grade F with 9 `THREAD_MATCH_POOR` (3 block,
6 warn) and `summit_badge.png` grade F with 10 (2 block, 8 warn) —
confirmed 2026-10-08 — `digitizer/testdata/corpus_scorecard_baseline.json`,
captured at `d000e370`.)* The paragraphs above stand as the record
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
  sharing were explicit, documented non-goals of THIS fix specifically
  (both closed later: the gradient ruling of 2026-09-04 and the radial
  design ramp the same day — scope-history). Full
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
  alive). ~~Shipped `FILL_ROW_MM=0.40` unchanged pending sew-out.~~
  **STALE — `FILL_ROW_MM` is 0.15 since `a794208`** ("the professional's
  pitch, by Kent's ruling; the coverage grader re-based in fill layers"). The
  two-population finding above is untouched by that; only the shipped number
  moved. *(confirmed 2026-09-06 — `tools/doc_claims.py`)*
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
**`info` since 2026-10-05 (Kent's call, issue #630):** the 2026-10-04 scorecard
recapture bisected its 12 points onto three photo-lane band falls (2.1–2.3 mm²
holes on `photo_chrome_specular`) while it moved no stitch; the finding, its
`extra` and the `uncovered_*` metrics stay, the grade is blind to it.

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
   **Corrected 2026-09-03:** the "physical-scale limitation" half is wrong. The
   professional's PES for this very patch (`Embroidery Files.zip`, Hotel Fremont/
   Hotel Patch) sews THE, EST 1895 and EAT | STAY | PLAY legibly at the same
   92.5 mm, as ~0.8 mm satin columns (median stitch 0.82 mm in the tagline band,
   0.90 mm for THE). Not dropped is still true; too small to sew is not. See
   `docs/kent-review-2026-09-03.md`, Fremont.
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
are moves under 11.8 mm.**

> **Correction 2026-09-06: 11.8 mm is not "the floor the professional never
> cuts below."** That figure is `becker_hat_small` ALONE
> (`docs/fragmentation-attribution-2026-08-18.md` §"The pro's actual cut
> rule", 35 trims). The broader measurement already in the record —
> `.claude/memory/pro-trim-threshold.md`, **910 needle-up moves across all 23
> pro designs**, 2026-08-15 — has **542 cuts with a minimum of 1.9 mm** beside
> 368 floats to 16.1 mm, heavily overlapping, and concludes *"no single
> threshold reproduces this pro"*. Pros cut BELOW our 3.0 and float well above
> it. The 86% figure above stands; what it is measured against does not.

`trim_at_mm` is gate-1 territory and the sew-out is accepted as-is, so this is
**not retunable** — it is the diagnosis, not a fix. And the corpus gives a
second reason: distance is not the pro's decision variable at all.

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

> **The satin tier reached the same place independently, 2026-09-06.**
> `stage6_satin`'s `_graph_travel` on `becker_marine_logo`'s 27-stroke
> `Sead76620`: 32 calls, 8 succeed; a connectivity-aware `_order_strokes` is
> byte-identical; Eulerian chaining is WORSE (32 trims vs 29); widening the
> travel graph's node merge moves nothing. Same three dead ends as this
> section, on the other tier. What the satin side adds is *when* it dies —
> travel may only cross UNSEWN strokes, so logging progress through the shape
> gives ok at 5/15/20/40% and then "no route" on all nine calls from 45% to
> 85%. "There is no path to find" is not a fixed property of the shape; it
> becomes true as the shape fills in. (scope-history 09-06, DOCTRINE)

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

### Text clustering — RESUMED and SHIPPED 2026-09-03 (third attempt)

Each of the three reasons above is answered, not argued past. Full record:
`docs/design-review-fine-lettering-2026-09-03.md` §6.

- **The e2e contract** now reads the converted bar's own "N shapes" count and
  asserts per cluster (the other cluster's badges stay, `unstitched` grows by
  exactly N, Undo restores exactly N). The fixture carries two clusters —
  the rescued "ENTERPRISES INC." subline and the 6.5 mm "ENTHUSIAST".
- **The star** is out on a ONE-INK link, `textcluster._same_ink`: CIEDE2000 on
  the job's chart, `TEXT_CLUSTER_DELTA_E_MAX = 20`. Measured: the letters
  (0134 Smoky) are 34.2 from the star (1720 Not Quite Red); drone's PRECISION
  greys need chain links ≤ 16.4 (pairwise max 25.3) to stay one word; grey
  vs orange lines ≥ 27.7. The inter-glyph GAP proposed above is measured
  dead — the star sits 0.97 heights from its word, ENTERPRISES INC's own word
  space is 1.56 heights. Thread identity stays disproven.
- **Cost, measured directly** on a quiet box: enthusiast @ 90 `run_stages`
  7.9 → 8.8 s (detect +0.4 s, OCR +1.4 s for 10 more glyphs at ~0.13 s each,
  house angle −0.9 s from memoizing `_skeleton_stroke_stats` on the polygon —
  three passes were skeletonizing the same regions); drone @ 80 25.9 → 28.8 s;
  becker @ 100 2.0 → 3.4 s. The service test that timed out on CI runs in
  12.4 s solo against its 60 s budget. It DID time out again under a
  saturated box (`-n auto` with a probe and two renders alongside, 27:42 for
  a 9–10 minute suite) — the loaded-box artifact, and the test to watch.
  **A thread pool over pytesseract is a measured negative** (3.3 → 21.8 s:
  four tesseract processes each open an OpenMP team and thrash four cores);
  OCR stays serial, with the numbers in the code. **The same OpenMP teams are
  why the service test times out under `-n auto`:** pre vs post under three
  CPU hogs 19.3 vs 32.7 s (idle 11.1 vs 11.9). The tesseract child is now
  pinned to one thread (`_one_tesseract_thread`): 12.1 s under the same hogs,
  faster than the pre-change tree and immune to contention — the likeliest
  root cause of the `10ae9cc` CI timeout, fixed at the source.

**The structure is the safety argument.** `_candidates` (the rescued door) is
unchanged and clustered FIRST, alone, with its original bounds, so every
cluster that `regularize_text_clusters` redraws is computed by exactly the
code that computed it yesterday. Then `_letter_candidates` (10ae9cc's letter
door: aspect, 1.5–60 mm, CV ≤ 0.55) plus any rescued leftover is clustered at
`LETTER_HEIGHT_RATIO` = `SATIN_ANGLE_HEIGHT_RATIO` (0.8 — one text element
is one line at one size: MARINE and the arched BECKER were one cluster at
0.5 and are two at 0.8; drone's three lines were one 23-member cluster) with
the ink link; those clusters carry `text_cluster_all_rescued = False` and are
never redrawn (`cluster_not_all_rescued`). Results: becker 0 → 11 tagged in 2,
drone 0 → 21 in 3 (10 greys, 4 oranges, 7 Whale), enthusiast 14 → 24 in 2
with the subline's cluster id unchanged, Fremont 13 + 5 + three rope
fragments. `_lettering_groups` (the house angle) is untouched.
*(measured 2026-09-03 — `tests/test_textcluster.py` +9)*

### Defect 24's mechanism — FIXED 2026-09-03 (the tier stays open)

A stretch of stations under `SATIN_MIN_CROSS_MM` used to leave the zigzag to
hop from the last survivor to the next, and the art between sewed nothing:
Fremont @ 92.5 lost 41 of 282 strokes and 83.5 mm of spine, the T's bar both
halves while its junction crosses survived (Goldman-joined members keep their
junction crosses, so a whole-stroke fallback never fires — the split is per
station). `satin_stroke` now hands `satin_shape` PARTS per stroke — satin /
bean run / satin — and a hairline stretch of ≥ three bean stations of spine
sews as a 3-pass bean along it (`_hairline_stretches`, `_bean_along`); stage 7
reports `HAIRLINE_STROKES_AS_RUN`. Shorter stretches stay dropped (a 0.45 mm
rail dent was becoming a bean tail: chaining 3.8 → 5.0/1k, back to 3.81 with
the floor). **Only where the ART has ink:** pull comp grows a 0.04 mm
vectorization needle into a 0.44 mm "stroke" (Fremont: a dark tick above the
hexagon band), so a stretch is trimmed while the cross measured in the
UNCOMPENSATED polygon is under `simplify_tol_mm` (`_trim_to_art`) — Fremont
went from +276 stitches to +12 with it. No satin underlay under a 5 mm extent
(`SATIN_UNDERLAY_MIN_EXTENT_MM`, the JS `UNDERLAY_CAP_MIN_MM`): Fremont's
underlay 446 → 408, drone 1101 → 993. Enthusiast and becker byte-identical.
The JS font path got the same stretch split (`satinplay.splitByCrossFloor`),
area 2. *(measured 2026-09-03 — `tests/test_small_lettering.py`, 9 tests;
`docs/design-review-fine-lettering-2026-09-03.md` §3–§4)*

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

**Default OFF — `PipelineConfig.satin_house_fourfold`.** *(A 2026-09-02
snapshot. **Kent flipped it DEFAULT ON on 2026-09-03** once the stitch-angle
rule's pass 1 landed — see `config.py`'s own note; the benchmark reads
4.09/1k under its 4.1 ceiling.)* On `enthusiast_logo`
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

*Update: `curve_roughness_deg` no longer stays offline — it reaches preflight as `curve_roughness*` metrics (judges nothing), alongside `edge_wobble_<tier>_*` (defect 46). (confirmed 2026-10-08 — `digitizer_core/preflight.py` `_edge_wobble_metrics`/curve-roughness metrics, commits 84fb94a5, 1d6297ed)*

*Moved from MASTER_SCOPE (2026-09-19), verbatim, to make room under its word
budget:* On Kent's four Becker artworks the two SPARSE ones measure roughest —
complexity, not size (an earlier "small placements sew rougher" reading is
withdrawn).

## The wobble attributed to its stage — SATIN RAILS, not the outline (2026-09-19)

Kent: *"right shapes, bad edges … wobbly / lumpy curves … it needs to be
perfect."* A third smoothness instrument, and the first that can say WHICH
STAGE a wobble was born in. A spike put both halves in one unit (offset
removed): on `enthusiast_logo` stage 4's polygon tracks the artwork at
**0.011 mm** std while the sewn rails wander **0.071** about that polygon; on
Becker (0.55 mm source pixels) both wobble ~0.08; synthetic `logo_whitebg` is
clean on both sides, which is why no suite saw it.

`tools/edge_wobble.py` keeps the stitch-side half: `result.regions[].polygon`
against `plan.iter_runs()`, signed distance, high-passed over 3 mm along the
edge; no raster, no registration. On `main` at `24fce102`:

| fixture | satin std / p95 / >0.15 mm | fill std | bean/run |
|---|---|---|---|
| `enthusiast_logo` | 0.110 / 0.230 / 12.5% | 0.010 | 0.000 |
| `becker_marine_logo` | 0.099 / 0.200 / 9.5% | **0.177** | 0.000 |
| `logo_gaulke_roofing` | 0.088 / 0.170 / 6.7% | 0.019 | 0.000 |
| `logo_whitebg` | 0.038 / 0.067 / 0.8% | 0.022 | 0.000 |

**By zone (`rail_zones`), share of rail penetrations over 0.15 mm:** corner
26.0 / 14.9 / 12.0% (enthusiast / Becker / Gaulke), series end 10.5 / 12.8 /
5.4%, mid-column 3.5 / 4.1 / 3.7%. Corners first, ends second, a lumpy curve a
distant third — three different fixes. Renders of the five worst spots per
logo: `docs/renders/edge-wobble-2026-09-19/` (`--render DIR`). Becker's fill
row is probably the instrument misreading a split column's mid-points as row
ends (DOCTRINE) — unconfirmed.

**The reverse direction (`unsewn`) — outline with no thread within 0.5 mm:**
Becker 32.6 mm in 16 spans (2.7% of its sewn outline; MARINE's square corners
and feet), Gaulke 6.6 mm in 4, Enthusiast 2.2 mm in 3, synthetic 0.0. This is
what stitches → outline cannot see, and what Kent's *"you missed quite a few"*
was. Whole-design pages with every mark on a lettered grid: `*_all.png` in the
same render folder. Blind still: bean-tier small text, and outline vs artwork.

**`cfg.satin_cap_recentre` — ON since 2026-10-03 (Kent's flip, on his labelled
sitting: after on becker and tires, before on none —
`docs/eye-pairs-2026-10-03/`). Built 2026-09-19; what follows was measured
then, with the flag off as the default.** A
free end whose spine tail is a surviving cap fork is cut at the kink and
rebuilt square. Bare outline Becker 32.6 → 29.3 mm, Enthusiast 2.2 → 0.8,
Gaulke unchanged; satin wobble not worsened (Becker std 0.097 → 0.094), where
`satin_rails_follow_edge` reaches 14.8 mm by roughening the rails to 0.137.
Small because the fork is ~3 mm of Becker's 32.6 (7 of 44 free ends fork, 3
pass the guards). NOT in MASTER_SCOPE's "Waiting on Kent" — that file sat at
26,999 of 27,000 words. *(DOCTRINE 2026-09-19; `tests/test_satin_cap_recentre.py`)*

Satin barely moved across 2026-09-19's satin flips (0.106 / 0.101 / 0.098 on
the pre-flip base), and `satin_rails_follow_edge` moved the spike's figure
~10% — neither is the lever. **Open:** why the rails wobble (worst points are
all inward dips, 0.5–0.95 mm); whether 0.10 mm is what Kent's eye sees;
Becker's fill tier (0.037 → 0.177 across the flips, unread); and the low-res
OUTLINE half, which needs registration and was left in the spike.
*(measured 2026-09-19 — `tests/test_edge_wobble.py`, 10; DOCTRINE 2026-09-19)*

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
`satin_house_fourfold` still OFF **at the time of this pass — Kent flipped
it ON later the same day (2026-09-03)**; every fixture without a house angle
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
7.51 → 7.36 (drone is 9.6 px/mm in the pipeline, not the 19 of its frame — review of #330) but a 12 × 3 mm ribbon fell satin → fill (`explained` 0.83 →
0.70: the 1-px skeleton grew 17% more spurs off the refined boundary);
gaulke (16), ENTHUSIAST (15), sunset, meadow, whitebg/alpha/ribbon (10)
all ROUGHER with 40–80% more vertices, meadow a 2.4 mm blob fill → satin
(cv 0.53 → 0.48). Floors of 2–3 px cost half the O (17 vertices, 27°).
Gate at 20 px/mm (`_CURVE_MIN_PX_PER_MM`, four pixels of tolerance at 0.2 mm): only Fremont among
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

## Rails follow the edge — `satin_rails_follow_edge`, built OFF (2026-09-03)

*Update: the flag is no longer a bool-OFF — the shipped default is now the string `"envelope"` (ON since 2026-09-30, Kent's pick after #561); `False` is the symmetric model this section measured against, `True` (the per-station following measured below) stays parked. (confirmed 2026-10-08 — `digitizer/digitizer_core/config.py` `satin_rails_follow_edge`, PR #563)*

Per-side rail profiles behind a flag. The 17–23% of lettering rail points
> 0.1 mm inside the art (rail-dents record §3) are not the symmetric model:
instrumented on Becker, 353 of 670 are short-stitch guard retractions on
bends, 115 corridor caps, 129 corners/oblique edges, 48 tip zones, 25
smoothing under-reads. Coverage measured as bare satin area
(`tools/rail_edge.py --bare`): Becker 8.63 → 5.84%, ENTHUSIAST 5.70 →
4.36%, drone 6.07 → 4.59%, Fremont 8.60 → 6.94%, ribbon 1.11 → 1.08%.
Costs: thread +10–17% on lettering, stitches +4–7%, rail jitter p50 +50%
(0.038 → 0.061 mm on Becker), same-rail holes (guard retractions) 63 → 79
Becker, 67 → 108 drone; wider per-side filters trade back with no knee.
Pull comp was tuned with the far rail stopping short — sew-out question,
Kent's flip. *(measured 2026-09-03 — `docs/rail-dents-2026-09-03.md` §7)*

## 2026-09-03 — fill density: the professional's rows, read as rows

`tools/row_pitch_union.py` (7 tests) reads the adjacent-row pitch of the UNION of every pass: pro Fremont patch ground **0.141 mm** (one pass, 52 rows in 8 mm), pro Becker letter bodies **0.166–0.169**; ours **0.400** on every fill including the blend bands. The per-pass `fill_pitch.py` reading of 0.37–0.40 on the same pro files is its autocorrelation locking onto the tatami penetration cycle. Gate 1 untouched. Record and the tool-wide plan for Kent's five sew-out findings: `docs/sewout-findings-2026-09-03.md`.


## What photo tonal splitting BUYS — measured 2026-09-06 (MASTER_SCOPE 20)

Defect 20 recorded the tier's cost and said the other half could not be
measured: *"No off switch for photo classes (`effective_split_tonal` ORs flag
with class)."* **That was already false when written** — the switch landed
2026-09-01 in PR #316 (`231ca4b`), and `effective_split_tonal`'s docstring
names defect 20 as the reason it exists.

Every photo-class fixture, default against `split_tonal_regions=False`, 80 mm /
left_chest (`digitizer/tools/tonal_split_ab.py`):

| fixture | grade ON → OFF | coverage_max | same_hole | worst ΔE00 | regions | stitches |
|---|---|---|---|---|---|---|
| `photo_chrome_specular` | C 64 → **B 88** | 7.09 → 6.98 | 0.03 → 0.03 | 8.80 → **5.90** | 19 → 6 | **−15.8%** |
| `photo_dof_meadow` | D 52 → **B 88** | 7.97 → **7.01** | 0.04 → **0.01** | 10.70 → **9.40** | 20 → 5 | **−31.8%** |
| `photo_scene_stub` | B 76 → **A 100** | 6.68 → 6.52 | 0.03 → 0.03 | 6.30 → **9.70** | 21 → 4 | **−20.9%** |
| `photo_sunset_backlit` | B 76 → **A 100** | 7.04 → **6.43** | 0.04 → **0.02** | 12.00 → **11.00** | 10 → 3 | **−29.6%** |
| `fur_ramp` · `photo_grass_macro` · `photo_owl_pale` · `photo_subject_stub` · `logo_script_tires` | unchanged | | | | | byte-identical |

**Four of nine score higher with the tier off; none score lower.** Over the
photo lane: **−22,352 stitches, −16.4%**, `coverage_max` down on every fixture
that moves, `same_hole_fraction` down or equal everywhere, colour fidelity
better on three of the four (`photo_scene_stub` worsens, 6.30 → 9.70).

### The caveat is the point

**The scorecard has no instrument for what this tier is FOR.** It scores
density, coverage, trims and thread-to-artwork ΔE00; nothing in it scores
tonal gradation. A photo sewn in 3 cones instead of 5 can score better and
look flatter, and this table cannot tell the difference. So the honest reading
is *"the yardstick prefers the tier off by a wide margin, on a design question
the yardstick cannot see"* — phase 1's exit condition restated
(*"nothing he judges better ever scores worse"*), not a verdict on the tier.

Kent ratified tonal splitting as spec decision 2 (2026-08-18), re-confirmed
deliberate 2026-09-02. **A datum for him, not a flip.**


## Letterform mechanisms 2 and 4 — moved out of MASTER_SCOPE 2026-09-07

Moved verbatim, not edited. `MASTER_SCOPE.md` hit its own 800-line budget (now enforced by `digitizer/tests/test_scope_budget.py`), and its own tool named this section as the reclaim: **107 lines in the dashboard against 3,871 here.** These two are per-mechanism detail that already point at their own documents, which is exactly what this file is for. Nothing is dropped; the dashboard keeps a pointer.

**Mechanism 2 — pull comp's min-feature guard scoped to `poly.interiors` —
PROTOTYPED AND COSTED, not shipped.** An exterior-pocket branch holds 15 real
slots at 0.528–0.920 mm and reds the chaining benchmark (3.8 → 6.4 trims/1k vs
4.1; +2 trims at the shipped `chain_links=False`). **Kent's call 2026-08-28:
hold it.** `docs/exterior-notch-guard-2026-08-28.md`. *(prototyped 2026-08-28)*

**Mechanism 4 — the instrument that hid all of it — is HALF CLOSED
2026-08-28.** Coverage and IoU average, and deformation is local, so
`stroke_coverage.py` reports the WORST medial-axis stroke (DRONE's E: 58.3%
worst vs 72.7% mean). **Still blind to TILT**; the obvious tilt metric was
built and REJECTED (ranks a good O worse than the deformed H). Detail in
`tools/letterform_fidelity/README.md`. *(2026-08-28)*

## Evaluation corpus — detail moved from MASTER_SCOPE 2026-09-07

Moved under the 800-line budget (skill rule: per-area supporting detail
belongs here, with the verdict and a link left behind). Verbatim; the
dates and pointers are the originals.

**Corpus half — the real-artwork entries keep contradicting the synthetics.**
Seven distinct real customer logos ship in `FIXTURES`: **stage 0 routes six of
seven to GRADIENT**, because real logo art carries JPEG ringing and anti-aliased
edges the synthetics lack, so a "flat spot-colour art" claim tuned only on
synthetics is untested against real input.
`logo_script_tires.png` classifies `photo_scene` outright — a misroute kept so
the bug has a fixture. **Real PHOTOGRAPHS go further: all four of Kent's
portraits classify `gradient` with the LOWEST `unique_color_mass` in the corpus,
below every gradient logo** — the measurement behind `cfg.is_photographic`
being declared rather than detected.
*(2026-08-15 / 08-25 — `corpus_scorecard.py:FIXTURES`; scope-history 08-25)*


**A second harness exists: `tools/pro_parity/`** — how close our output is to
the PROFESSIONAL digitization of the same design, 23 designs, six weighted
components. **Its scale changed 2026-08-14** (chance-corrected floors); see the
Gotcha in [`DOCTRINE.md`](DOCTRINE.md) before comparing to any earlier number.
*(confirmed — PR #151)*


**Half that corpus is in the repo; the half that matters is not.** The tracked
`Embroidery Files.zip` carries all 23 pro STITCH files, so `prep_all.py`'s recon
lane runs from a fresh checkout. It carries **zero customer artwork**, so
`prep_both.py`'s real lane — the one behind the 42.5 baseline — still needs the
Drive copy. *(corrected 2026-08-18 — prep_both from the zip fails 0/15)*


## Shade-merge candidates — measurement moved from MASTER_SCOPE 2026-09-07

Kent TABLED the shade-merge 2026-09-02; the ruling stays in the decision
queue, the numbers behind it live here. Verbatim.

12. **Merge a tiny cone into an ADJACENT SHADE — a colour call, and the
   COMMITTED corpus can now pose it.** The sew-out's b4/b7 class: cutting such
   a cone further means sewing its patches in a neighbouring shade's thread —
   a colour step for a stop, quality not gate-1 physics. `sequence_census.py`
   reports colour since 2026-09-02, and committed art carries defensible
   pairs — ΔE **1.41** (`screenshot_phone_ui_golke`, 62st → 79st), **1.78**
   (`logo_bridge_bar`, 197st → 444st), **2.65** (`drone_render`, 338st →
   1560st); the repro had none (closest cones 33.4 ΔE) until 2026-09-04, when its sweep became five shade bands 5–6 ΔE apart by design — adjacent shades of one ramp, not candidates. Real artwork runs
   15–18 cones, so the population is not rare.
   **TABLED — Kent, 2026-09-02:** *"I'm honestly not concerned about the
   hopping idea, we can table this one for a further discussion."* Do not
   build the shade-merge or further hopping polish until he reopens it; the
   08-31 mechanical fixes (`start_near`, the re-snap rehome) are merged and
   unaffected. *(measured 2026-09-02 — `sequence_census.py`, 26 fixtures; tabled 2026-09-02 — Kent)*

## Lettering house-angle: the THIRD reading — the line of text itself (2026-09-19)

Both votes above can refuse a plain block word. "MARINE" in `manga_impact`,
traced at 80 mm: its verticals and horizontals cancel in doubled-angle space
(nR² 5.0 against 6.9) and its diagonals hold the four-fold resultant at
0.164, under the 0.25 floor whose own comment names "the diagonal blind spot"
— so the word got no house and its crosses read 0.23 concentration, while
the same word at 127 mm passed (17.6). `_cluster_house_angle_deg` now has a
third reading, `PipelineConfig.satin_house_from_line`: a group both votes
refuse takes the cross along its own line of text — the stems' perpendicular
for upright lettering, the rule's own anchor. A group with no line
(`_line_of_text_deg` None) still fails open. Limit carried from the four-fold
reading: a vertically STACKED upright word would get its cross along the
stems; bars and stems then fade to their own perpendicular under
`_clamp_to_span`, so the exposure is diagonals leaning toward the wrong axis.
No fixture has one.

Fires on three of the nine real logos' 24 lettering groups: the ENTHUSIAST
wordmark (nR² 0.9, R4 0.243 — it straddles the four-fold floor between 80 mm
and 93 mm, passing at 93) and two tiny groups on the phone screenshot.
ENTHUSIAST at 80 mm: house None → 179.9°, the word's satin runs' cross
concentration 0.059 → 0.287, +7 stitches, +1 trim; the chaining benchmark at
93 mm is unchanged. **Built and flipped ON the same day — Kent's call.**
Five tests in `tests/test_house_from_line.py` on a word built at test time
from the committed `manga_impact.json`.

The probe that found it also found what the doubled reading does on a
diagonal-heavy word it ACCEPTS: a house pulled off the line by the single-
diagonal residue (AMAZE 27°, NAVY 147°; on real logos enthusiast's subline
130°, fremont 97.9° / 162°) — not the stems' perpendicular. That is step 1 of
`docs/superpowers/plans/2026-09-19-lettering-construction.md`.
*(built, measured, flipped 2026-09-19 — scope-history's entry of that day)*

## Lettering house-angle: ANCHORED to the line of text (`satin_house_anchor`, built OFF and flipped ON 2026-09-19)

Plan step 1. Both votes decide the house from every stroke, and on lettering
with diagonals the diagonals pull the answer off the stems' perpendicular
the 09-03 rule names: of the nine real logos' 24 lettering groups, the
doubled-angle vote accepts twelve with a line and stems and puts NINE of
them 12–79° off their own line (enthusiast's subline 130°, Fremont's EAT
STAY PLAY 98°, drone 115° / 108°), and on the font word HOTEL 27° — 45° once
the word is turned 20°. ON, a group that makes a line takes house = line +
slant, the slant being the length-weighted median offset from the line's
normal of the strokes within the 30° lean cap of it, on chord-resampled
chains; a family under 10% of the skeleton is silent and the votes answer
as before, as they do a group with no line. Output: drone's satin
self-crossings 496 → 430 and Fremont's 87 → 66, at drone +167 stitches /
+5 trims, enthusiast +16 / +2, the rest within ±24. Instrument check: the
slant reads under 2° on 15 of the 19 anchored groups; the four it does not
are the Fremont rope's twists (not letters) and two 1–2 mm screenshot
groups. A leaned script reads its own slant (`mam_script` +15.4°); the
votes were not needed as a detector. **What the flip decides:** on
THERMAL the vote's accidental 108° put both stroke families inside the fade
(one uniform lean); anchored at 0° the stems sew square and the bars take
their own perpendicular — the fonts' convention the rule adopted, not the
pro's one angle. `tools/satin_lean.py drone [--anchor]`: THERMAL's cross
concentration 0.319 → 0.248, AND DRONE's 0.227 → 0.297; the word's lean off
each cross's own perpendicular p50 17.0° → 11.8°, bars at their own
perpendicular 7% → 14% of crosses. Render
`docs/renders/lettering-anchor-2026-09-19/drone_lettering_anchor_off_above_on_below.jpg`.
Rejected on measurement: a kernel mode for the slant, a straightness gate on
the votes. Limits: stem-poor words read their diagonals' middle (ZANY −12°);
brush scripts with curved strokes read near zero. `tests/test_house_anchor.py`
(15); `tools/satin_lean.py [--anchor]` prints each group's house and cross
concentration. **Flipped ON the same day — Kent's call over the THERMAL
render, keeping the fonts' bar rule (a bar takes its own perpendicular) over
the pro's one angle; False is the pre-flip engine.** *(built, measured and
flipped 2026-09-19 — scope-history, step 1 and its addendum)*

## Lettering: one path per letter — the Euler-walk stroke order (`satin_stroke_order`, built and flipped ON 2026-09-19)

Plan step 2. A satin shape's strokes sew nearest-first and travel between
strokes along the unsewn web or trim when none is left; on a letter of
several strokes that web is used up after the first few, and 18 of the
plan fixture's 45 trims were that hop inside one letter. `"euler"` orders
the strokes along one walk of the web — the font engine's `routeGlyph`
construction: Chinese-postman duplication where a dead end forces it, a
Hierholzer trail, each stroke sewn at its last visit so every travel leg it
emits lies under a column sewn later (a stroke with an interior junction —
an H's stem — sews whole and can still strand the needle at a dead end,
which trims as before). Each stroke is walked through (column in
at the walk's arrival end and out the other, underlay chained backwards
from the entry), the graph builder's self-loop stubs are skipped, and the
cursor may snap to the nearest node it can leave from. Fixture: 45 → 27
trims, 2,564 → 2,482 stitches, uncovered 0.0 both ways; nine logos:
trims **592 → 486** across the nine (Becker 46 → 38, tires 11 → 8, ENTHUSIAST 27 → 19, Fremont 75 → 55, Bridge Bar 112 → 85, Golden Tee 66 → 45, gaulke 39 → 35, drone 144 → 132, the screenshot 72 → 69) at a net −19 stitches (−58 to +65 per logo), travel 1,478 → 2,934 mm, satin self-crossings, uncovered area and preflight warnings unchanged on every one. Applies to every satin shape. `tools/travel_cover.py` reads every travel leg
against the thread sewn after it (gate 3's instrument): at 80 mm across the nine logos the walk adds 1,064 mm of travel and 1.4 mm of new exposure (244.7 → 246.1 mm; the 245 mm exposed is not the satin tier's at all — traced 2026-09-19 with `tools/travel_legs.py`, 97.7% is the FILL tier's column bridges lying on their own finished fill, defect 21's residual, 0.0 mm on bare fabric; scope-history, "the exposed travel legs"); Becker at 80 mm reads uncovered 18.5 → 26.0 mm² because a nearest-order travel leg had lifted six half-millimetre cells of a bare column seam over the 0.25 floor.
`tests/test_stroke_order_euler.py` (10). **Flipped ON the same day — Kent's
call; "nearest" is the pre-flip engine.** *(built, measured and flipped
2026-09-19 — scope-history, step 2 and its addendum)*

## Lettering corners: the spur pruner's structure rule (`satin_corner_twigs`, built and flipped ON 2026-09-19)

Plan step 3a, the letterform study's mechanism #2. `_prune_spurs` erased a
corner's twig and with it the junction's degree, so a letter's diagonal and
stem welded into one column folding through the corner (PRECISION's N,
Becker's R foot). The study's tip-width classifier does not exist on this
raster (census of 739 spurs: every one over 0.5 mm ends at a 1 px distance
transform), so the rule is by structure: two short free arms at a node off
a stem are a cap and both go; one short free arm between two longer arms
is a corner and stays, holding the junction open. Fixture: satin
self-crossing pairs 277 → 103 at 2,480 → 2,192 stitches; nine logos:
1,813 → 1,004 at trims 486 → 488 and uncovered unchanged (Becker 34.8 →
35.5 mm²), stitches +588 of which Becker's band at 100 mm is +725 — three
more strokes, each with its own zigzag underlay, the cost to name. A
synthetic N stops folding; a square-capped bar's spine is straight either
way. `tests/test_corner_twigs.py` (6). **Step 3b, `satin_rail_comp`,
re-measured on today's engine:** IoU-to-target Fremont 0.681 → 0.836,
ENTHUSIAST 0.875 → 0.900, drone 0.803 → 0.826; meadow 0.811 → 0.779 at
+340 stitches; its skeleton is RULED the artwork (Kent, 2026-09-19) and
its flip waits on a sew-out (plan `2026-09-09-rail-side-pull-comp.md` §7).
**3a flipped ON the same day — Kent's call; False is the pre-flip
pruner.** *(built, measured and flipped 2026-09-19 — scope-history, step
3a and its addendum)*

## Lettering: split, never fill (`satin_lettering_split`, built OFF 2026-09-19)

Plan step 4, Kent's 2026-09-11 rule for the browser lettering engine on the
traced path. A text-cluster member is classified and sewn with no width
ceiling (`_satin_ceiling_for`: ∞, the per-stroke rung on, the fold guard
on; every other shape keeps `satin_ceiling_mm`), so `classify_ribbon`'s
width gates never send a letter to tatami and `split_satin` carries the
width; the shape gates still apply, a blob still fills. Fixture, MARINE
traced at 127 mm: the six members go fill 6 → satin 6 at 9,642 → 7,753
stitches, trims 31 → 47, uncovered 0.0 — and satin self-crossings 0 →
311, every one in the R's junction ball, with `DENSITY_EXTREME`
(coverage_max 5.49 → 6.24); at 80 mm +328 stitches, the zigzag underlay
the oversize skip used to withhold. Becker at 100 mm 12,037 → 9,056 at
trims 39 → 71; composed with `satin_patch_junctions="satin"` its uncovered
35.5 → 0.0 mm². Nine logos: only Becker moves. **The limit is DOCTRINE
2026-09-09's — a junction blob is not a column: the flag lifts the ceiling
and builds no junction**, so the flip trades tatami letters for split-satin
letters whose junction balls fan until the bold-letter junction
construction exists. Kept OFF (Kent, 2026-09-19), then FLIPPED ON
later that day once `satin_junction_stack` took the fold out of the R and
the split-satin density finding proved to be the instrument (Kent's call;
False is the pre-flip engine). `tests/test_lettering_split.py`
(7); renders `docs/renders/lettering-split-2026-09-19/`. *(built and
measured 2026-09-19 — scope-history, step 4)*

## Lettering: no edge cap on lettering (`edge_cap_skip_lettering`, built and flipped ON 2026-09-19)

Plan step 5. The design-silhouette cap sews only the stretches of the
outline nothing linear already covers, and on a satin-sewn letter that is
exactly the bare corners and junction seams the decomposition leaves — on
the 80 mm MARINE fixture 17 of the cap's 18 runs and 418 of its 457 stitches
stood on the letters' outlines, the cap patching a defect upstream. A typed
glyph gets no cap. ON, a text-cluster member that sewed satin hands its sewn
polygon to the cap's `omit` (`_satin_lettering_cover`, read off the runs
laid, never a verdict); a member that filled keeps its cap, since a tatami
letter's rows end in open air at its edge. Fixture: stitches 2,192 → 1,774,
trims 23 → 7 (the typed word: 3), cap runs 18 → 1, uncovered 0.0 both ways,
every non-cap run byte-identical; Becker at 80 mm 6,588 → 6,444 at trims 43
→ 36, uncovered 18.5 both ways; the 127 mm fixture and Becker at 100 mm,
whose letters fill, byte-identical. Nine logos: five move — ENTHUSIAST 2,478
→ 2,442 stitches at trims 18 → 16, Golden Tee 6,969 → 6,945 / 44 → 43,
gaulke 4,536 → 4,454 / 41 → 38, drone 18,733 → 18,715 / 127 → 126, the
screenshot 8,244 → 8,085 / 73 → 68; Becker (its letters fill at 100 mm),
tires, Fremont and Bridge Bar byte-identical; trims 488 → 476 at −319
stitches, with uncovered area, self-crossings and warnings unchanged on
every one. Found on the way: the wide-column fold guard's load-bearing case
on Becker at 80 mm is gone under the corner rule (coverage_max 4.67
unguarded, against 7.07 on 2026-09-09); its test is pinned on the pruner it
was read on.
**Flipped ON the same day — Kent's call; False is the pre-flip cap.** `tests/test_edge_cap_lettering.py` (10);
render `docs/renders/lettering-edge-cap-2026-09-19/`. *(built and measured
2026-09-19 — scope-history, step 5)*

## The bold-letter junction: `satin_junction_stack` (designed, built and flipped ON 2026-09-19)

Kent's ruling on
`docs/superpowers/plans/2026-09-19-junction-construction.md`: A + B + C as
one flag. The defect: the R of the 127 mm fixture under
`satin_lettering_split` folds one column over itself through one welded
corner (311 self-crossing pairs, 294 in one junction blob), and across the
nine logos 1,420 of 1,607 seam pairs sit in the 30–60° welds. A: a weld is
refused past 30° of turn by the merge's own baseline — the corpus number
(`tools/weld_turns.py`: the trough is 20–30° at 13 pairs on 75 welds) — and
the arms end at the node; the fold guard's radius rule was tried at three
windows and separates nothing. B: an arm ending at a meeting of several runs
into the node by its own half-width. C: the satin junction cover under the
arms. Measured: the R fixture 311 → 0 pairs at 7,253 → 7,283 stitches and
trims 34 → 44 (the R's welds 8 → 3, all five over 30° refused), uncovered
0.0 both ways; MARINE 80 mm 103 → 0 at trims 7 → 9 (the doc's A + C proxy
paid +12: B is the lever on trims); Becker 100 mm under the split flag
uncovered 35.5 → 0.0 at 8,612 → 8,353 stitches and trims 53 → 61, its remaining letter pairs not welds (read the same day: all four
strokes that carry them are Goldman joins — the mitre, the pro's kind,
counted within the run; nothing to build). Two predictions falsified: the layers inside the
junctions do not rise toward the pro's (p95 3.3–4.2 against 3.9–7.2; B
overlaps ends, it does not stack), and the fixture's trims pay +10 not +4.
Nine logos: stitches 89,105 → 89,723 (+0.7%), trims 476 → 489 (Bridge Bar 82
→ 95, Becker 38 → 44, Golden Tee 43 → 47, ENTHUSIAST 16 → 18, Fremont 56 →
57, tires and the screenshot level, drone 126 → 122, gaulke 38 → 29), the
lettering groups' self-crossing pairs 1,004 → 596 (Golden Tee 381 → 113,
gaulke 186 → 106, drone 264 → 220, ENTHUSIAST 19 → 8, the screenshot 141 →
136), uncovered unchanged on eight and Becker's 35.5 → 0.0, warnings
unchanged on every one. Off byte-identical. `tests/test_junction_stack.py`
(10); renders `docs/renders/junction-construction-2026-09-19/`. **Flipped ON the same day — Kent's call; False is the pre-flip
engine.** Step 4's `DENSITY_EXTREME` was the
instrument (below); its flip is Kent's again. *(built and measured 2026-09-19 — scope-history, the junction
build)*

## `DENSITY_EXTREME` on split satin was the instrument (fixed 2026-09-19)

The first of the two findings the junction build surfaced, read the same
day. `preflight._satin_rail_advance_mm` reads the satin rail pitch as the
distance between points two apart (rails alternate A, B, A, B), and a
split satin column carries extra penetrations along each cross, so on
split lettering two apart was a mid-cross hop: the lettering plan's
127 mm fixture under `satin_lettering_split` read 1.09 mm against the
0.40 target (ratio 2.8, a `DENSITY_EXTREME` warn) on columns sewn at
0.43. The reader now strips the splits with `stage6_satin.strip_splits`
first, the reader the coverage map already used; unsplit runs are
unchanged (MARINE 80 0.445 → 0.444, Becker 100 under the split flag
0.455 → 0.415, the fixture 1.094 → 0.428, no finding). The playbook's
parity trap in its second form — the parity broken by the splits instead
of the slicing. `tests/test_density_split_satin.py` (3). *(read and
fixed 2026-09-19 — scope-history)*

## Rail comp: the flip's price and the seams (2026-09-29/30)

Moved out of MASTER_SCOPE's quality-review Item 6 entry on 2026-09-30 to keep
that file inside its budget; the verdict and a link stay there.

- **Priced at the flip, 2026-09-29, same tree OFF → ON:** MARINE 80 mm 9 → 22
  trims at +15% stitches, ENTHUSIAST `lost_frac` 0.2748 → 0.2565 for bare
  6.27 → 7.10%, Becker 114 mm under `wide_columns` 5.38 → 7.47 — the trims a
  ceiling in `tests/test_rail_comp.py`; the price ACCEPTED by Kent 2026-09-29,
  "take the price, let it merge". *(measured 2026-09-29)*
- **Trims.** Half of MARINE's trims were the walk's target sitting a
  half-width off the web, fixed the same day — corpus trims 671 → 654 (OFF
  634), MARINE 21 — the rest cursor-side and parked with
  `satin_walk_cursor_reach_mm`. The junction tuck's floor and reach-in were
  put in sewn terms the same day (MARINE bare 7.38 → 7.03% at +32 stitches,
  corpus trims 654 → 651), and BECKER's C sews its 8 mm bowl as the cover's
  fill BY DESIGN, two thirds of its junction bare —
  `docs/renders/rail-comp-junctions-2026-09-29/`. *(measured 2026-09-29)*
- **The seams, skeleton half (2026-09-29).** golden_tee's +65% stitches were
  the SEAMS of stage 5's on-rails polygon (a hairline wherever two vectorised
  edges meet, a skeleton branch each: 178 → 494 strokes), and the skeleton
  reads that polygon with the seams of its construction closed — golden_tee
  11,377 → 7,966, MARINE byte-identical, corpus trims 651 → 640, the
  artwork's own boundary untouched (`docs/renders/rail-comp-seams-2026-09-29/`).
  *(measured 2026-09-29)*
- **The seams, rails half (2026-09-30, PR #565).** The rails, caps and
  underlay still read the seamed polygon, so a spine down a closed seam had
  its crosses stopped at the seam's walls: on main, golden_tee's mean satin
  stitch was 1.301 mm with rail comp ON against 1.414 mm OFF — rail comp
  sewing NARROWER than no comp. `satin_shape` now closes the polygon once and
  sews the whole shape off it (raw polygon if the closed one sews nothing);
  mean stitch 1.508 mm, golden_tee 7,952 → 7,965 stitches, 43 → 44 trims,
  satin thread 7,777 → 9,208 mm; MARINE, ENTHUSIAST, ribbon_curve
  byte-identical, drone +4 stitches. The same PR closes before
  `simplified` mode simplifies, lets an unreadable artwork boundary close
  nothing, and leaves a seam open where closing it would seal a bay.
  *(measured 2026-09-30 — PR #565)*

## Item 8's colour bundle — moved from MASTER_SCOPE (2026-09-30)

Lifted verbatim to bring `MASTER_SCOPE.md` back under its 27,000-word budget after Kent's 2026-09-29 merge put two lanes' additions in one file (each was legal alone). The RULINGS stay in the summary; this is the measurement record behind them, which is settled and dated and was never current status.

**Item 8 is MEASURED, nothing flipped (2026-09-10)**: the five colour flags priced as one set with `tools/flip_sheet.py` (26 fixtures, 80 mm, tree `920ebcd`). At the engine budget the four not ruled (`colour4`) take **−22 cones / −22 stops / −22 blocks** off nine fixtures with three grades up and none down; with the ruled `dissolve_phantom_blends` (`colour5`) −4,023 stitches and −77 trims on top, Bridge Bar's phantom halo gone on the render. At the Studio's shipped 6 the same four take **−47 cones / −43 stops** and every real logo lands on the promised 6 (drone 23 → 6), one synthetic grade down (summit F 16 → F 0, a new `THREAD_MATCH_POOR` block). Forced flat the bundle still takes 28 cones off five real logos (Golden Tee 24 cones under a budget of 12), so item 1 does not retire it. Forced flat the bind does most of it (−26) and the cap the rest (−21); only the dissolve is byte-identical there. Decision doc `docs/colour-bundle-decision-2026-09-10.md`. **Kent's ruling the same day: the four not ruled are ON by default as one set** (`enforce_color_cap`, `resnap_mask_matches_grader`, `revalidate_small_shapes`, `bind_resnap_all_classes`; the dissolve stays banked); False on each is the pre-flip engine. **Its one visible price on a real logo, found by the flip's own test run and understated by the sheet Kent ruled on: Bridge Bar's disc sews `6031` Limelight, 7.0 ΔE00 from the artwork's yellow (`0501` Sun sits 1.0 away), under the bind at both budgets — stage 2 hands the palette the disc REGION's mean, (223, 220, 77), pulled 12 ΔE00 darker and greener by the anti-aliased edges of the lettering, bird and rope inside it, the palette's nearest spool to that mean is Limelight, and the bound re-snap can no longer read the source pixels and correct it as the escape did. The fix is a robust region colour in stage 2, not in the bind — BUILT 2026-09-10 as `cfg.robust_region_colour`, DEFAULT ON since 2026-09-10 (Kent's pick after item 9; built OFF that day in #445 and flipped in the PR after on his ruling over the flip sheet and the Bridge Bar render; False is the pre-flip engine byte for byte): the one point each SLIC+RAG region hands the palette becomes the modal mean of its Lab pixels (the mean over the pixels within 5 ΔE00 of the per-channel median), chosen by `tools/region_colour.py`'s census over 20 lane fixtures / 422 regions — the median and the modal mean move nearly the same regions' spools (146 vs 163) and where they differ the modal mean lands on the artwork (the disc: mean → Limelight, median → Lemon at 2.1, modal mean → Sun at 1.0); 33 regions are bimodal, 27 of them on the phone-UI screenshot. The real logos move most of their AREA's spools (Bridge Bar 56.9%, drone 65.2%, the screenshot 65.0%; Golden Tee 33.8%), the photographs and ramps none. **Flip sheet, 26 fixtures at 80 mm:** 11 move, 15 byte-identical (every flat-lane fixture, gaulke, Fremont, the ramps, the photographs). At the engine's 12: Bridge Bar 12 cones and a repeated `0108` (13 blocks) → **11 / 11**, the disc `6031 → 0501`, `COLOR_STOPS_HEAVY` and one of three blocking threads gone, F 0 → F 4; the screenshot 11 → **10 cones**; Golden Tee 11 → 12 cones (+118 stitches, +5 trims) while its blocking threads fall 4 → 2; the synthetic photo-scene stub takes a fifth spool and +3,382 stitches / +29 trims at the same B 76 (the one real price, on no customer's artwork); net +2,498 stitches / +24 trims / +1 cone / 0 blocks. At the Studio's 6: net +2,244 stitches / +3 trims / 0 blocks / 0 stops; Bridge Bar **13,820 / 96 / 6 / 6 against 14,588 / 124 / 6 / 7** (−768 stitches, −28 trims, the repeated cone gone) with one more blocking thread on a shard while its 1,023 mm² disc leaves the blocking list, Golden Tee +249 stitches and one blocking shard fewer (four to three, all shards), the screenshot's 470 mm² ground off the list, drone level at five with its 211 mm² orange entering (Pumpkin at 10.9 for Fox Fire — the one large shape that gets worse); no grade letter moves. Renders `docs/renders/region-colour-2026-09-10/`: the disc goes from yellow-green to yellow. The flip's price is the sheet's, accepted: the stub's stitches and Golden Tee's twelfth cone at 12, drone's orange at 6. The photo-lane snapshot golden pins stage 2, so the flip re-captured it on ubuntu CI with the pre-change proof, on six of its seven keys (fur_ramp alone unmoved; region_blobs moves one stage-2 medoid on a blob the tonal split sews as its own bands, so its plan is byte-identical and the sheet read it as still). `tests/test_robust_region_colour.py` (10). *(measured 2026-09-10 — `tools/region_colour.py`, `tools/flip_sheet.py` `region_colour`)*** *(measured 2026-09-10 — scope-history's item 8 entries; decision sheet §2 bind entry)*


## Defects 27 and 28 in full — moved from MASTER_SCOPE (2026-09-30)

Both are LIVE and their verdicts stay in the dashboard; what moved is the evidence, under Kent's 250-word-per-entry cap the same day. #28 was 1,783 words — 7% of the whole file in one entry, and the single largest thing the total-only budget never touched.

27. **Compression halos become their own cones — and the flat lane has dissolved them all along.** `stage2_quantize._quantize_population` runs "majority filter, then phantom-blend dissolve" and its comment records the bill without it ("two extra pale threads, plus ~30 sliver regions"); `Prep.bg_edge_rgb`'s docstring says it again. **The SLIC+RAG lane never got that pass** — so the defect is a missing PORT, not a missing idea. `logo_bridge_bar.jpg` (400 px JPEG, four ink colours) pays it in six grey cones — Cobblestone, Whale, Skylight, Saturn Grey, Silver, Umber — sewing the ringing around its black spokes. **FIXED, DEFAULT OFF** (`cfg.dissolve_phantom_blends`, `stage2_photo_segment.dissolve_phantom_blends`): a merged label that is more than half boundary AND a Lab interpolation of its own two adjacent sides folds into the side it is nearer, the page included, so the rebuilt edge lands at the step's midpoint instead of growing every shape by the halo stack. Bridge Bar 74 → **32** regions, 14,607 → 11,524 st, **114 → 64 trims**, silhouette −4.2%. Read the cone count (13 → 11) LAST: five of six greys go, all four real cones survive, and three NEW cones arrive on artwork the palette could not afford — what changed is what the cones SEW, measured by the palette's worst excess, **20.76 → 3.68** dE00. Residual: 0111 Whale survives as 12 shards, 0.7% of the design, cause not established. `tools/halo_spools.py` bills it — 44 halo regions before, 2 after — and across eleven fixtures finds halo cones on bridge (4), golden_tee (1) and gaulke (1) and NONE on the other eight, Becker (1.5 px/mm PNG, many thin features, no compression) included: the test is specific to compression, not to thin features. Corpus A/B, PRE-FIX and superseded: *"ten of fifteen fixtures byte-identical, gaulke a second clear win (blocks 4→3, trims 30→18), two mild negatives (golke +2 trims, tires +1)"* — the gaulke win was the lettering being deleted. **Post-fix, 26 fixtures, 2026-09-07: 22 byte-identical and FOUR move** — bridge_bar (14,338→11,506 st, **125→62 trims**, 18→12 blocks and cones), screenshot (71→**66** trims, 17→15 blocks — the "+2 trims" negative reversed), golden_tee (+24 st, trims flat), tires (+1 trim). **gaulke is byte-identical now**; it is no longer on this flag's credit side at all. **Kent has SEEN the render and ruled: leave it OFF and bank it** (2026-09-04) — not pending his eyes any more, deliberately parked. **That gaulke grade is RETRACTED as evidence (2026-09-06).** It read **F 0 → C 64 … the difference between "do not sew" and a usable design**; measured on the cones rather than the grade, the C 64 is a design that DROPPED ITS LETTERING: gaulke is black text on a white label, `off` loads `1375 Dark Charcoal` (L* 15.9, 288 st), and the flag leaves `0015`/`4071`/`0145` — **nothing darker than L* 85.7 on a white ground**. The only arm that loads real Black (`bind_resnap_all_classes`, `0020`) grades **F 16**. `THREAD_MATCH_POOR` grades per thread on its worst patch, so deleting the dark cone deletes the badly-scoring thread — the metric rewards not sewing the hard part (flip sheet). **That last conclusion is itself RETRACTED (2026-09-07)**: it shipped as yardstick-disagreements row 7, and it was the bug's artifact, not the metric's preference. Post-fix every gaulke arm loading real `0020 Black` grades HIGHER (F 16) than every arm that does not (F 4), and across seven arms × 26 fixtures **ten (arm, fixture) pairs remove a cone and not one scores higher** — all ten on fixtures at exactly 0, where the floor (defect 28) makes the question unanswerable on this corpus. What survives is the RULE that caught the bug: on a fixture where a flag removes a cone, read the cone list, not the grade. **CAUSE FOUND AND FIXED 2026-09-06 — one line, and the regression is gone.** `valid` inside the pass is `base_valid`, which already has the ENCLOSED pixels removed, so `~valid` is NOT the page: it also covers donut holes, letter counters and the inside of a label. Gaulke is black lettering on a white label on a black canvas, so reading `~valid` as the page told every letter it bordered the near-black background — its colour genuinely lies between that and the label's L* 98.8 ground — and the page endpoint DELETES rather than recolours: **12,961 px, 50.3 mm², the 21.0 mm² wordmark included, dropped to background.** The pass now takes stage 1's real background (`page_mask`). **Costs the flag nothing:** bridge_bar keeps 125 → 62 trims and 18 → 12 blocks, screenshot still 71 → 66 trims, gaulke byte-identical, and no grade moves either way. (An intermediate note here retracted the fold as the cause; that retraction was wrong — the probe behind it counted only relabelled pixels and a page-dropped label keeps its label. `tests/test_phantom_blend_photo.py::test_an_INTERIOR_band_is_never_sent_to_the_page` pins both directions.) The flip is a one-line default plus a 26-fixture scorecard recapture, to be decided alongside other gradient-lane work; his stated reasons for not flipping on the day were the two mild negatives and the five-of-six residual. *(measured 2026-09-04 — scope-history 09-04; `tests/test_phantom_blend_photo.py`; `docs/renders/halo-dissolve-2026-09-04/`)*

28. **The largest quality wall in the corpus is three problems wearing one code — and one of them is two floors set 4× apart.** `THREAD_MATCH_POOR:block` grades **7 of 26 fixtures F 0** (14 of 52 matrix entries), all `gradient`, which is where real logo art goes. Decomposed 2026-09-06: **(1) the raw yardstick, 4 of 7** — `golden_tee`, `drone_render`, `region_blobs`, `summit_badge` clear every block once scored on EXCESS over the loaded spools (the photo route's 2026-08-24 rescoring, which the gradient lane never got). **REPRODUCIBLE as of 2026-09-07** (`tools/spool_remedy.py --yardstick`, no patch — excess is reported on every route, so forcing `_is_photo_class` and its confounds is unnecessary): it names those same four and no others. Nothing had reproduced this claim before, and its neighbour turned out to be a bug's artifact. **The offender set moves with the yardstick** — a thread's worst RAW patch can have a close loaded alternative while its second-worst does not, so 6 of the 24 findings block on a row raw scoring never looks at; a probe that keeps the raw top and reports its excess gets this wrong; **(2) halo cones, 1 of 7 — RETRACTED 2026-09-07, the category is EMPTY** (it read *"`gaulke_roofing`, defect 27's flag alone, F 0 → C 64"*; on the fixed tree that flag is byte-identical to `off` on gaulke on BOTH garments — F 4, raw 4, 2 blocking, worst ΔE **63.6 unchanged** — so the wall decomposes 4 + 0 + 2 and **gaulke is the seventh, unexplained**; its 63.6 names `1375`, a spool the design already loads, which points at category 1, unmeasured); **(3) survives EXCESS too — 3 of 7, not 2 (2026-09-07).** `screenshot` (`0111 Whale` excess 32.4, `2776 Black Chrome` 16.3), `bridge_bar` (`6156 Olive` 10.3) and now **`gaulke_roofing`**, which category (2) used to hold: it goes 2 raw blocks → **1** under excess, and the survivor is real — `3971 Silver` at raw 63.6, **excess 58.6**. So the wall decomposes **4 + 0 + 3**. **ROOT-CAUSED 2026-09-07: the MASK GAP accounts for TWO of the three, and it needs the small-shape floor to finish either** (`tools/spool_remedy.py --masks`). **(a) `gaulke` — the mask gap, newly named.** `revalidate_threads` and `_region_color_errors` claim the same estimator and have it (both take the median of the per-pixel CIEDE2000), but they do NOT share a MASK: preflight erodes the polygon raster one pixel and drops `p.bg_mask` (*"to keep anti-alias halo pixels from dragging a flat color toward the background"*), while `_region_footprint` is a bare `cv2.fillPoly` and does neither. On `Se6eddd27` (0.58 mm² at 16.1 px/mm) stage 4 scores **247 px** — 4.6× preflight's — and that set is BIMODAL, **103 near-black + 65 near-white**, so its median-of-per-pixel-dE makes `3971 Silver` the argmin **over the whole chart at 11.4 dE00**; preflight's eroded, background-excluded **54 px** read **[45,45,45]** and score that same Silver **63.6**. A **52.2 dE00 gap on one polygon.** Stage 4 is behaving correctly on the pixels it is given; the pixels are wrong. The RAW footprint is not held back by the small-shape floor — 247 px is above `THREAD_REVALIDATE_MIN_PX = 200`, `revalidate_small_shapes` alone leaves the region byte-identical, and an earlier draft of this entry had that backwards. (The MASKED footprint is a different matter — see the matched pair below.) **(b) `bridge_bar` — ALSO the mask.** A first version of this entry said "neither, still open" on the grounds that the two masks agree to 1.3 dE00 on `S880e5dff`. **That compared the wrong quantity** — the re-snap's gate reads the improvement over the best LOADED spool, not the assigned thread's score, and there the two masks read **1.8 against 10.3**, on opposite sides of `THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00 = 3.0`. So the raw footprint declines a re-snap the grader's mask would take. **(c) `screenshot` — the floor, and only the floor**: both footprints reach the same decision (`0015` best loaded either way, gain 31.3 vs 32.4) and both fail the pixel floor at 177/114 px; `revalidate_small_shapes` fixes it 32.7 → 1.4. **The mask and the floor are a matched pair**, which is the operational point: masking OUT the halo shrinks the footprint, so a shape the raw raster floated over the 200-px floor drops under it — gaulke 247 → 54, bridge_bar 240 → 156. `resnap_mask_matches_grader` alone therefore cannot re-snap either region; measured, bridge_bar needs **mask + `revalidate_small_shapes`**, which does move it (`6156` → `5866`, 21.3 → **16.2**) at the cost of one more block on that fixture, so it is improved rather than solved. On gaulke that pair is byte-identical to the mask alone, because the mask collapses the palette and `1375 Dark Charcoal` is no longer loaded for the small-shape rule to offer. **FIXED, DEFAULT ON since 2026-09-10** (`cfg.resnap_mask_matches_grader`, flipped with the colour bundle as one half of a pair): the re-snap applies preflight's two operations — erode one pixel, drop `p.bg_mask`, hairline fallback included — and the pixel floor then counts the MASKED set, which also feeds the small-shape restriction. Masks agree to **99.99% IoU** on gaulke and 100% on `logo_alpha` (the residual is `_region_footprint` rounding mm→px where `_region_color_errors` truncates; aligning the rasteriser would touch `tag_enclosed_background`, so it is deliberately left). **Corpus A/B, 26 fixtures: 19 byte-identical, −1,715 stitches, −5 blocks, −4 cones, +2 trims, and `logo_gaulke_roofing` F 4 → D 46 — no grade moves down anywhere.** **The effect is bigger than the one shape:** gaulke's cone list goes 6 → 3 and its plan palette 4 → 2, because the re-snap was reaching `1375` and `3971` *for halo pixels* — **a SECOND cause of defect 15's resnap escape**, distinct from the missing palette binding `bind_resnap_all_classes` treats (that one restricts WHERE the argmin may land; this one fixes WHY it goes wrong). **Residual, named:** `Se6eddd27` improves 63.6 → **16.7**, not to zero — with the halo gone the re-snap DECLINES the region and it keeps stage 2's `4174`, and `1375 Dark Charcoal` (5.0 dE00 from this artwork) is no longer loaded for the small-shape rule to offer; `revalidate_small_shapes` is byte-identical on top of this flag for that reason. Flipping it is Kent's — it moves the flat and gradient goldens the phase-4 spec pins. *(measured 2026-09-07 — `tools/spool_remedy.py --yardstick` and `--masks`; `tests/test_resnap_mask_matches_grader.py`, 10)* The mechanism under two of the three: **`revalidate_threads` refuses the shapes preflight condemns.** Stage 4 already re-snaps threads that drift off their colour during simplification (fix #6.3) — 46 of 153 shapes on `screenshot_phone_ui` wear a re-snapped thread — but `THREAD_REVALIDATE_MIN_PX = 200` against `preflight._MIN_COLOR_PIXELS = 50`, so **every shape of 50–199 px can be blocked and never corrected.** 12 refusals on `screenshot` (all in-band), 7 would change answer, worst `S43831dcd` at **177 px**: `0111 Whale` 32.7 ΔE → `0015 White` **1.4**. Corpus agrees with the split — refusals are 0/0/0/7/4 on the five other F fixtures against **63 (`bridge_bar`) and 12 (`screenshot`)**. **FIXED, DEFAULT ON since 2026-09-10** (`cfg.revalidate_small_shapes`, the pair's other half): ON, the re-ask uses `THREAD_REVALIDATE_MIN_PX_SMALL = 50` — preflight's own floor — and a shape admitted only by it may take only a cone the design already carried at pass entry. `screenshot_phone_ui_golke`'s worst thread ΔE00 **33.0 → 21.2** (`S43831dcd`, 177 px, `0111 Whale` 32.7 → `0015 White` **1.4**), **21 of 26 fixtures byte-identical**, and **no grade or block count moves anywhere** — `THREAD_MATCH_POOR` blocks per thread on its worst patch, so fixing six of a thread's shards is invisible while a seventh is bad. It fixes SEWN COLOUR that the scorecard cannot see, which is a phase-1 datum; the render is at `docs/renders/small-shape-resnap-2026-09-06/`. Two constructions rejected with measurements: the unrestricted chart argmin (buys `screenshot` 10 → 9 blocks but costs `drone_render` 4 → **5** and takes `bridge_bar` to **22** cones) and restriction to the stage-2 palette (13 spools against the design's 16, so it forbids moves onto cones already on the machine — no regression and no win). Residual, measured not guessed: `drone_render` 19 → **20** cones because a shard lands on `0674`, which the shipped pass otherwise VACATES. Flipping it ON is Kent's. `THREAD_MATCH_POOR` also has **no area floor at all** (worst shapes: min 0.58 mm², p50 3.17, max 1,648.5 — 12 of 23 under 5 mm²) while every sibling check has one. **It no longer judges `enclosed_background` regions** (2026-09-06): unstitched by default, their colour is the background's, and `revalidate_threads` already refuses that category error. Worth ONE finding across the whole matrix — `logo_gaulke_roofing` drops `4174` (24.5 ΔE00 on 6.16 mm²), F 0 → F 4, blocks 3 → 2, no grade letter moves. A hardening, not a rescue. Two rejected constructions are recorded with it: a plan-derived denominator (breaks ten deliberate `test_preflight.py` cases that pass a synthetic plan) and, before that, an instrument filtering `run.jump` — which is how the needle ARRIVED, not travel, and falsely made this look like eleven findings (DOCTRINE gotcha 2026-09-06). *(measured 2026-09-06 — `digitizer/tools/revalidate_floor.py`; scope-history 09-06)* **And the check knew which cone to use and did not say — FIXED 2026-09-06:** `_best_loaded_spool_error` ran on the photo route only, so off it the remedy read "pick a closer thread" without consulting the design's own cone list, and **5 of the F-wall's 24 blocking findings name a spool the design ALREADY LOADS** (gaulke 63.6 → `1375` loaded and 58.6 closer; screenshot 33.0 → `0015` loaded and 32.4 closer; bridge_bar 21.3 → 10.3; screenshot 17.3 → 5.0; drone 12.8 → 9.0) — the first two being this defect's own headline numbers. Reported on every route now, with `yardstick` in `extra` naming which one judged the severity (its ABSENCE used to carry that signal, a contract a test caught — DOCTRINE), and **no severity or grade moves anywhere**, measured over ten fixtures. Whether the gradient lane should be JUDGED on excess was **RULED 2026-09-10: it stays on RAW distance** — a logo's palette can be changed and a photograph's cannot, so on a logo the closest loaded cone is one to buy, not a pass; nothing in the code moves (the lane was never rescored) and row 4 of the disagreements closes. `tools/spool_remedy.py`, `tests/test_thread_match_better_spool.py` (11). **And the F wall has a DEPTH nobody had measured (2026-09-06, `tools/floor_depth.py`):** the score is `max(0, ...)`, so **12 of the corpus's 52 design/garment combos sit on exactly 0 with unclamped scores from −272 to −38 — a 234-point spread behind one printed value.** `screenshot_phone_ui_golke` must clear **312 points, ~11 blocking findings**, before its grade moves one letter; `drone_render` 228 (~8); the shallowest, `summit_badge` and `bridge_bar`, 78 (~3). That is the missing half of why a real thread fix here moves nothing — the check aggregates per thread AND the design is hundreds of points under water — and why `gaulke_roofing` is the one that moves (F 4, shallow, not floored). Un-clamping re-bases every grade, so it is a product call. *(measured 2026-09-06 — yardstick-disagreements row 6)*


## Evidence moved from MASTER_SCOPE's live defects (2026-09-30)

Kent's rule 4b caps a numbered entry at 400 words. These five entries keep their verdicts and their open questions in the dashboard; what follows is the measurement each rested on. Nothing here is current status — read the dashboard entry first, then this for the numbers.

### Defect 19

**MEASURED 2026-09-11, and GATED** (`tools/pro_silhouette.py`; the two sides are read differently ON PURPOSE — ours exactly from the plan's run kinds, his as a LOWER BOUND through `border_pro`'s certified fill-edge test, because a stitch file has no kinds). **Ours, `edge_cap` off: 5.9–100.0% of the sewn silhouette has no linear stitch on it** (3,266 mm; enthusiast 5.9, drone 20.2, Becker 24.5, gaulke 76.7, whitebg 82.6, **Fremont 100.0** — a badge whose satin is all interior lettering). **His: at least 19.1–26.1% of 7,063 mm of fill edge carries a certified border**, none in the fill's own colour block — he lays thread along fill edges as a matter of course; whether it adds to a whole silhouette is not knowable from a stitch file. **GATED AND FLIPPED ON, DEFAULT `"bean"` 2026-09-11** (Kent: "gate it, then flip"). The gate (`silhouette_cap(omit=…)`) caps only what is genuinely open: the bill falls from +8.6–100.4% to **+5.9–26.3%** (median +13.4%) and uncovered falls to **0.1–6.2%**. **Style NOT settled and still the sew-out's** — bean is cheaper in stitches on five of six, satin cheaper in TRIMS on five of six, and at Kent's own 25-stitch trim price the two are within 4%. **Two costs, stated:** the trim rate moves both ways (becker 6.26→8.03, gaulke 2.42→3.50, but fremont 4.55→4.28 and drone 5.26→5.24; four of six were already over the 4.1 professional ceiling with the cap off), and the cap re-loads a cone on **all six** fixtures — Kent ruled that stop acceptable rather than put a 5.4%-frontage cone on gaulke's edge instead of a 95.0% one (`test_duplicate_cone_layers` carries the carve-out). 45 tests moved; **no golden was recaptured** — the byte-identity guards pin `edge_cap="none"`, `conftest.PRE_FLIP`'s posture. **The accepted stop then broke TWO buyer-facing displays, caught by CI's e2e and fixed the same day (2026-09-11).** Since the cap re-loads a cone, sew BLOCKS and SPOOLS TO BUY stopped being the same number — and both screens were showing blocks: the Digitize panel's summary read *"3 colors"* for a two-spool vector logo (`e2e/digitize-auto-start.spec.js`, whose own comment says it asserts the colour count because *"the colour count is the thing the customer pays for"*), and the review's **"Threads to load"** list — a shopping list — named one spool twice with its metres split across the two rows, so a customer buying from it buys a spool they have and under-orders the one they need. `digitizer.spoolCount` folds by cone id for the panel and `QualityReport.cones` folds and SUMS for the list (the thread total is unchanged: a sum of sums is the same sum). **This is MASTER_SCOPE defect 42(e)'s rule hitting a second time** — "a colour is a cone to buy and a re-thread on a single-needle machine" — and the lesson is that a ruling which changes what the ENGINE DOES changes what every existing display of it MEANS. *(fixed 2026-09-11 — `QualityReport.spec.js` +1, `digitizer.spec.js` +3, both mutation-proved)* **`satin_rails_follow_edge` is NOT answerable this way** — a stitch file holds the rails and not the artwork, so asking whether they reach its edge is circular. *(measured 2026-09-11 — `docs/superpowers/plans/2026-09-11-edge-cap-from-the-pro.md`; `tests/test_pro_silhouette.py`, 4)* **The flip's CLOCK was not measured and cost 86 minutes a design for one day.** The gate built its cover as `unary_union(lines).buffer(...)`, which NODES every satin zigzag at every crossing — Fremont's 138 runs / 9,677 points become a 49,535-part MultiLineString — and buffering that soup was **5,189 of `hotel_fremont_hat`'s 5,203.9-second prep**, exhausting a 39 GB box (GEOS `bad allocation`). Buffering each run and unioning the RIBBONS is the same set (`buffer(A ∪ B, r) == buffer(A, r) ∪ buffer(B, r)`) and gives a **byte-identical `ours.dst` in 14.5 s** (md5 `57c1abf9…`, compared against the 86.7-minute run itself); `hotel_fremont_patch` — the corpus's missing 23rd design — preps in 26.7 s. Cap-only speedups, output identical stitch-for-stitch: roofing_lc 60.5×, drone 14.0×, gaulke_jb 1.2×. *(fixed 2026-09-12 — PR #464; `tests/test_edge_cap.py` +2, both watched red; DOCTRINE "Never `unary_union` a stitch path before buffering it")*

### Defect 5

is 95.8% grid noise). **The per-stroke rung was BUILT INERT 2026-09-05 and WIRED behind the flag 2026-09-06** (`stage6_satin.classify_strokes` still has no caller; the pipeline consults the same reading via `_stroke_rung_takes` — do not read "inert" as current): at the bare ≥ 0.75 area rule it reproduces the plan's Becker @ 100 mm 274.0 → 1,708.3 mm² exactly — but that rule is NOT what shipped (see the cap veto below, which cuts it to **3 regions, 78.8 mm²**); it adds 5.7 mm² at the corpus's own 80 mm (Becker is ALREADY 88.2% satin there) and +143.8 mm² over 14 fixtures. Becker's 17 regions sit ON the `cv = 0.50` gate — 11 within ±0.10 at 80 mm, 16 at 100 — so its satin share is a segmentation coin flip, not an artwork property (scaling a fixed polygon 1.25× moves cv < 0.02). Its real value is decisiveness (median |cv − 0.50| 0.154 per region vs 0.221 per stroke; knife-edge share 40.9% → 24.7%), and it MUST be promotion-only or it demotes 15 regions incl. one of 638.8 mm² (DOCTRINE). **The flag exists since 2026-09-06 — `cfg.satin_per_stroke`, DEFAULT OFF, byte-identical off** (threaded to all three call sites; the rung sits on the `dt_irregular` branch alone so the machine cap and Law 31's floor stay out of its reach). **The machine cap is a VETO in it, not a vote** — the render caught the first cut leaving 28.0 mm² of bare cloth (a 9.32 mm stroke sewn as capped satin, DOCTRINE's measured negative). ON, measured on the stitches: Becker @ 100 mm goes **B 88 `DENSITY_EXTREME` → A 100 with no findings**, uncovered 0.0 both ways, crossing 2.2 → 4.0%, median column 0.29 → 0.64 mm (**a whole-plan figure and 80% tatami turns** — our SATIN runs there measure 3.82 mm median, p90 4.93, against the pro's 2.52/5.00; read our widths off `satin_columns.py`'s second row, DOCTRINE 09-06), 11,374 → 11,206 stitches, and satin **75.2 → 154.0 mm² — 3.5% → 7.2% of the 2,125.6 mm² that actually SEWS**, which is the only honest denominator here: 1,462 mm² of Becker is `BACKGROUND_ENCLOSED` and never becomes thread, so every "% of region area" quoted for this rung (the plan's 7.6% → 47.6% included) divided by shapes the plan leaves open (DOCTRINE, 2026-09-06). Modest, and honest — but the gap's old diagnosis is WRONG: **the pro's own p90 column is 5.00 mm** on `beckers_logolc.dst`, which is 95.7 × 58.3 mm, i.e. the same artwork at our test size, so the 5 mm cap is not what separates us and raising it is not the path (DOCTRINE 09-06). What differs is how few shapes reach the tier — ONE at 100 mm — and the columns we do sew are already professional width. **Segmentation, full stop.** Separately, and now FIXED behind a flag: **100% of that fixture's `ARTWORK_UNCOVERED` at 80 AND 90 mm is inside SATIN shapes** — the crotch of the K (37.2 mm² at 80, 32.2 at 90) and an R, where arms meet and no cross is placed. **`cfg.satin_patch_junctions`, DEFAULT OFF, byte-identical off** (2026-09-06): sews what the emitted thread missed, as tatami under the shape's own id, and takes uncovered **23.8 → 0.0 mm² at 80 mm and 44.5 → 0.0 at 90, B 76 → B 88**, for +7-8% stitches — and clears the corpus's only other positive too (`photo_scene_stub` 6.5 → 0.0, +2%), i.e. **30.3 → 0.0 mm², 100% of the bare cloth in SATIN shapes**. Corpus A/B at 80 mm: **23 of 26 fixtures byte-cost-identical, +0.25% overall**, with one over-fire (`logo_bridge_bar` +59 st at 0.0 uncovered both ways — this pass is deliberately stricter than the grader). It cannot reach the corpus's two LARGEST uncovered figures — `photo_subject_stub` 956.0 mm² (23.4%, D 58) and `photo_grass_macro` 407.5 (8.9%, B 76) — and does not need to: both are baseline AND the parked thread-paint ruling (`photo_subject` routes to `streamline_fill`; coverage p50 0.49/0.54, inside DOCTRINE's 0.52-0.59 band). Four cross-LENGTH knobs were measured first and none reached it. Flipping it is Kent's — the patch's tatami sheen inside a satin letter is a look question (render: `docs/renders/junction-bare-2026-09-06/`). The p90 gate IS blind to a tail — `promoted_ribbon` admits `Sead76620` at p90 2.67 mm whose width maxes at 7.80, 2.8% of the spine over cap — but that tail is NOT the cause: lifting `_rail_points`' 5 mm ceiling to 99 moved uncovered 23.8 → 22.8 mm² for +13% stitches, and `satin_rails_follow_edge` only to 21.0 (DOCTRINE 09-06, hypothesis refuted the same day). @ 80 mm byte-identical (Becker already reads 54.5%, above the pro). **Flipping it ON is Kent's — render at `docs/renders/satin-per-stroke-2026-09-06/`.** *(measured 2026-08-14/17, 2026-09-05/06 — `docs/satin-gate-attribution-2026-08-16.md` §9; plan §PR 2)*

### Defect 18

*(2026-09-01 — `test_duplicate_cone_layers.py`, 13)* **A THIRD mechanism is open, found 2026-09-06 by `COLOR_STOPS_HEAVY`'s new `repeated_cones` field: 4 of the corpus's 52 design/garment combos still sew a cone in more than one block WITH this fold ON**, by two routes it cannot see — `region_blobs` sews `0182` in two blocks that are each a gradient BLEND BAND from a different parent (`Sb971b1c2-blend2`, `S0ad9734d-blend4`; a band is not a layer declaration), and `screenshot_phone_ui_golke` sews `3971` in two blocks of plain regions that all carry `thread_resnapped_de00` in layers 2 and 8 — i.e. the duplicate is created by `revalidate_threads`, not by stage 2's quantize, which is the only thing this fold addresses. Each costs a real machine stop and each merge is FREE (the cone is already loaded). Recorded, not fixed: extending the fold to bands and to re-snap output is a sequencing change owed its own measured work. The finding now names it to the operator. *(measured 2026-09-06 — scope-history 09-06)* **SPLIT AND HALF-CLOSED the same day.** The re-snap half needs no new code: `rehome_resnapped_regions` refuses a cone no layer declares (its docstring: *"there is no 'home' to send it to"*) and this fold works on that same quantize-time list, so an invented cone is invisible to both — verified, `3971` is declared by none of `screenshot`'s 13 layers. `cfg.bind_resnap_all_classes` (defect 15) removes it outright, so fixing the rehome would add a SECOND switch for a cause the first already prices. **Still open: the blend-band half** — `region_blobs` sews `0182` in two bands of different parents, built in stage 6 long after this fold, and unchanged with the bind ON. One synthetic fixture; any fix is a sequencing change. *(measured 2026-09-06)* **PRICED 2026-09-06 (`tools/cone_revisits.py`), and "each merge is FREE" is true of THREAD cost only:** across 26 fixtures × 2 garments the four duplicates sit at block gaps of **7 and 11 — NOT ONE is adjacent**, so every remaining fold is a reorder through `covered_by`, which `cone_merge_survey.py` already measured as the expensive across-layer case. Both halves re-confirmed by re-running with the flag rather than on the record: `screenshot` 17 blocks → **11 with the duplicate gone**, `region_blobs` 16 → 16 with it intact. So the open half is **one GENERATED fixture** (`make_photo_region_fixture.py` — three Gaussian blobs) at an 11-block reorder, against a flag already built that closes the other half and buys `screenshot` six blocks. That is the case against building the band fold, in numbers. `tests/test_cone_revisits.py` (8). *(measured 2026-09-06 — scope-history 09-06)*

### Defect 20

needle-breakage signal. ~~No off switch for photo classes~~ — stale when written; it landed 2026-09-01 (PR #316), so **the other half is measured: the tier costs −22,352 st / −16.4% of the photo lane and with it OFF four of nine score HIGHER, none lower** (B 88, B 88, A 100, A 100), coverage_max falling wherever it moves. **A yardstick finding, not a flip** — nothing in the scorecard scores tonal gradation, and Kent ratified the tier (spec decision 2). Detail: `docs/scope/1-auto-digitizing-quality.md`. *(2026-09-06 — `digitizer/tools/tonal_split_ab.py`; 2026-09-02 bisect, [notes](docs/scorecard-baseline-attribution-2026-09-02.md))* **Numbers above are in the pre-2026-09-03 coverage base** (one 0.40 fill = 1.0); since the fill row moved to 0.15 the same stack reads 8.0 against a 9.33 block / 6.67 warn, i.e. a warn — the thread is unchanged, the ruler is in fill layers now (scope-history 2026-09-03). **The re-base left old-base numbers in the PROSE, and four were found and fixed 2026-09-06** — `preflight`'s module docstring said "1.0 is one full covering layer" (it is one 0.40 mm ribbon; a fill lays 2.67), `_coverage_findings` named `COVERAGE_WARN_UNITS`/`COVERAGE_BLOCK_UNITS` and gave their values as "2.5 and 3.5" when they evaluate to **6.67 and 9.33**, and two `test_preflight.py` docstrings quoted 3.00 and 3.5 beside assertions computing 8.00 and 9.33. **And the check has never fired on real artwork:** swept over all 26 fixtures, `DENSITY_STACKED` fires on **0 of 52 combos** — six carry a peak over the warn level (`photo_dof_meadow` 7.97 the highest, still under the 9.33 block ceiling) and every one yields **0.0 mm² of qualifying patch**, so `_COVERAGE_MIN_PATCH_MM2` is doing all the work and the synthetic `_stacked(n)` plans are the ONLY exercise a block-severity check gets. It now emits `patches`/`worst_patch_mm2`/`worst_patch_at_mm` — the "where" its own message always asked for and discarded. `tests/test_stacked_where.py` (6). **And the SAME row change silently recalibrated a second check**: `SAME_HOLE_HEAVY` scores repeat points over total penetrations, so the 0.15 mm row grew its denominator — A/B'd at both pitches, penetrations **×1.17–2.30**, repeat points ×0.98–1.15 (28 vs 28 on `logo_whitebg`), rate **×0.43–0.83**, and `max_strikes` **identical on all four fixtures**. Its docstring's "our benchmark is 9.8%" is old-base and now reads ~2.7%; the corpus runs 0.001–0.103 and it fires on **0 of 26** against a threshold set as "far above" 9.8%. Gate 4 in miniature. `SAME_HOLE_RATE_MAX` deliberately NOT retuned (its baseline is pro files at their own pitch); fixed by emitting the density-invariant half — `max_strikes`, `points_3plus`, `worst_at_mm`. `tests/test_same_hole_depth.py` (8). *(measured 2026-09-06 — scope-history 09-06)*

### Defect 15

gradient and the re-snap sews more spools than the cone list names. **Counted 2026-09-06** (`digitizer/tools/resnap_escape.py`): **34 cones added corpus-wide, 25 outside the selected palette, every escape on the GRADIENT lane** — screenshot 7, drone 5, bridge_bar 5, golden_tee 4, gaulke 3 — while all nine photo-class fixtures add none. The binding works; the lane real logo art routes to never got it. **FIXED, DEFAULT ON since 2026-09-10** (`cfg.bind_resnap_all_classes`, Kent's ruling on the colour bundle — `docs/colour-bundle-decision-2026-09-10.md`; False is the pre-flip engine): binding every class removes **19 colour stops across five designs** (drone 19→14, bridge_bar 18→14, screenshot 16→11, golden_tee 16→13, gaulke 6→4; gaulke also −10.9% stitches, drone +3.1%) and costs **+2 blocks net** — screenshot 10→8, golden_tee 2→5, bridge_bar 3→4. **It is NOT a raw-yardstick artefact:** forcing the excess yardstick (probe, reverted) still gives golden_tee D 52→F 22 and drone D 40→F 28, the latter with no thread block moving, so part of the price is the extra stitches. The escape is the pipeline BUYING colour accuracy with unplanned cones. **I would not flip it on this evidence** — the value is the price tag. *(measured 2026-09-06 — `tests/test_bind_resnap_all_classes.py`, 13)* **A benefit the price tag did not have, added 2026-09-06:** binding also removes a SPOOL REVISIT on real customer artwork. An undeclared cone can only exist because this escape put one there, and nothing rejoins the regions that land on it (defect 18's third mechanism) — `screenshot_phone_ui_golke` goes **17 blocks / 16 distinct with `3971` sewn twice, to 11 / 11 with no duplicate**. That belongs on the credit side of this trade. *(measured 2026-09-06 — scope-history 09-06)*

### Defect 15

is untouched; only the photo direction moved. **DETECTION BUILT 2026-09-11, DEFAULT OFF** (`cfg.detect_photographic`, stage 1.25): EXIF camera then the shipped YuNet detector; a hit fills `is_photographic` in as True — never False, never over a declaration — so it can only ADD photographs. Gate 2 untouched: no colour gate moves. **It changes nothing on this repo's artwork** — all 22 committed fixtures read identically on and off, because not one carries a camera header or a face (0 false positives across 14 logos; `owl_kent` is the real photograph BOTH signals miss, which is why the declaration stays the fallback). The value is on real uploads, which is

## Area 1 lanes in full — moved from MASTER_SCOPE (2026-10-08)

Moved verbatim for MASTER_SCOPE's word budget (rule 4), each leaving its
verdict and current flag state behind. The text below is as it stood in
MASTER_SCOPE on 2026-10-08; its dated figures are snapshots, not live status.

### Gradient lane (2026-09-04)

**Gradient lane, 2026-09-04 (Kent's ruling): a design whose ramp fits is ONE sweep.** `design_ramp.py` (trimmed + consensus plane gate: r² ≥ 0.4, ≥ 60% riding, sigma ≤ 4; colour as a profile along the sweep) flattens stage 2's merge and gives stage 6 one shade scheme per design, and a riding region never takes the satin rung: the icon repro at 80 mm goes 10 → 8 regions and its three ramp pieces decompose into five shades along the diagonal where they sewed flat or as one-thread satin; drone/summit/blobs/owl are refused and untouched (angle included). Two tier defects fixed on the way: blend bands had sewn at n× the row since the tier's first commit (a quarter of a fill; #339's preflight exemption for it withdrawn), and `_band_clip` shifted a linear ramp's bands by the region's own centre — the committed engine never sewed **46%** of `gradient_ramp_linear` at 80 mm, suite green. **Blend regions sew stage 5's compensated outline since 2026-09-04 (Kent's pick):** stage 7 had handed `blend_fill` the ARTWORK polygon, so every region of a gradient-class design — bands and tatami fallback alike — sewed with no pull comp and no seam tongue while `tools/seam_underlap.py`, which reads the plan, showed the tongue present; `tools/sewn_compensation.py` reads the stitches: repro strips 29% → 100% covered, blobs 36% → 100%; repro 22,087 stitches, 26 trims. **The machine's cone list is on the wire since 2026-09-04** (`stats.blocks`, one per sewn block with the review shapes it sews): the download's thread list always read `design.colors` and was right; the Sequencer header, its rows and the quality report's metres now read the blocks too, and `reviewFromJob` no longer indexes the per-layer palette by `sew_block`. **The satin raster ate every counter's edge until 2026-09-04:** `fillPoly` paints boundary pixels, so a hole painted in 0 lost half a pixel of material all round while the exterior gained one; the medial axis moved outward and the hole-side rail (the NEARER hit) stopped 0.18 mm short of the compensated outline on the repro's frame and ring while the exterior rail sat within 0.006 mm. Holes are painted half a pixel smaller in both rasterisers (`shapefield.hole_px`; `_rasterize` and `rasterize_polygon` are twins by test — the boundary-redraw form closed small counters and was measured out): frame strip 57 → 66% covered, ring 47 → 59%, against the instrument's ~80% ceiling for a perfect satin; the rest is the smoothed width profile at corners, which `rails_follow_edge` (sew-out gated) recovers. Hole-free shapes byte-identical. **Band seams feathered the same night (Kent's call on the render):** a 1.5 mm zone per seam sewn by both shades on one row lattice, alternating row by row, where rows run along the seam; repro 22 trims, 20,820 stitches. **Radial sweeps ride too (2026-09-04):** `design_ramp.py` fits a radial model (Gauss-Newton centre from the centroid, trimmed-then-consensus line in radius, colour profile along radius) gated at r² ≥ 0.6, ≥ 15 of 17 radius knots at consensus and the centre inside the stitched foreground, winning only when it beats the plane; `gradient_ramp_radial` at 80 mm 2 → **1** region, 5 shades (its 4,069 mm² outer ring had sewn flat), summit refused on knots, the owl on r², the linear fixture and the repro on the centre; linear designs byte-identical; a non-riding region on a radial design sews level. Ring seams keep the hard seam + underlap (rows cross rings; a stitch-level dither is a later item). **The blend tier takes the density stage 7 resolved since 2026-09-04** — it read `machine.FILL_ROW_MM` directly, so neither a per-job `fill_row_mm` nor a fabric's `density_adjust` reached a gradient: on a towel (0.85, pile needs TIGHTER rows) every band sewed 0.150 against the design's own 0.128, the repro 23,375 → 26,561 stitches. Invisible on the corpus scorecard, whose two garments both sit at 1.0. **The `-blend` suffix made four instruments blind until 2026-09-04** — preflight's bare-fabric check examined 0.0 mm² of a one-region sweep and a fifth of the repro (1,091 of 5,729.5 mm²), its thread match scored five cones as one, and the service filed a gradient's sew order and block ids under names no review shape has; `preflight._owning_region_id` is the one rule (a prefix test is not a substitute — region ids are not prefix-free). A fifth defect fell out of the same reading and is not an id bug NOR gradient-only: every region filled into ONE shared mask, so a ring's hole erased the artwork a nested region claims — the repro's shared mask claimed 136,341 px where the union claims 802,474, and the flat `logo_bridge_bar` (77 regions, no derived ids) rises 551.0 → 1,381.2 mm² examined. Scores fall where they were false: repro A 100 → D 58 on a band wearing a cone 13 ΔE off. Satin as SEWN is measurable since 2026-09-04** (`tools/satin_columns.py`, calibrated on two committed professional files in CI): a cross is sign alternation about the chord, not a turn angle, because a fixed angle gate is blind to columns under ~0.69 mm. Pro Becker **44.3%** of penetrations in columns at a 2.52 mm median; ours on the same logo **2.2%** of penetrations — the biggest measured gap to a professional file. **The width half of that line was contaminated and is corrected (2026-09-06):** "0.29 mm, 84% of columns under 0.7" is the WHOLE-PLAN row, 80% of it tatami turns; our SATIN runs there measure **3.82 mm median, p90 4.93, 23% under 1.0** against the pro's 2.52 / 5.00 / 7%. Read our widths off `satin_columns.py`'s second row (DOCTRINE 09-06). The share gap is real; the width gap was not (plan: `docs/superpowers/plans/2026-09-04-per-stroke-satin-routing.md`). **No physical tests until Kent says — the render is the judge.** *(measured 2026-09-04 — scope-history; DOCTRINE)*

### Item 1, PR 5 — the stage-0 signal re-read (2026-09-11)

**Item 1's PR 5 is MEASURED (2026-09-11, gate-2 clean — it changes nothing): `tools/color_diversity.py` re-reads the 08-15 spec's candidate signal** (3-bit colours covering 90% of foreground) on today's corpus. Two findings. **(a) The foreground definition is load-bearing and was never written down**: the art bbox reproduces the spec's table and separates the classes by 4; counting only what stage 1 digitizes puts `bridge` at 39 above `drone`'s 24, which does not order at all. Quote the bbox reading. **(b) The two real flat logos enrolled since August WIDENED the gap** (2 → 4: `golden_tee` 4, the screenshot 1, both far below `drone`). **The blocker is unchanged: one real tonal artwork labelled** where the spec asks four — the acceptance directory is empty in any clone and the tool refuses a boundary below four. One drag and one command unblocks it (`docs/stage0-signal-decision-2026-09-11.md`). PR 6a (the signal) is supported, not authorised; PR 6b (route by the ramp gate's refusal) needs no boundary and is Kent's ruling. *(measured 2026-09-11 — `tests/test_color_diversity.py`, 18)*

### Thin-stroke instruments and `keep_thin_strokes` (2026-09-08/13)

**The thin-stroke plan's instruments are BUILT** (`digitizer/tools/thin_strokes.py`, `legibility.py`; the width test corrected to the 90th percentile 2026-09-08 after its median admitted Fremont's white ground as a 1,758 mm stroke — the per-band and per-component figures here never depended on it): the two lanes lose DIFFERENT width bands — Fremont routed sews strokes under 0.5 mm at **53%** recall and 0.5–1.0 mm at 90%; forced flat, 26% and **51%** — and `logo_gaulke_roofing` loses **16 of 18** thin strokes on BOTH lanes with lettering legibility **0.32**, because its black frame makes stage 1's background black and every black element inside the card "enclosed background", unstitched by default. **`cfg.keep_thin_strokes` is BUILT on both lanes and **DEFAULT ON since 2026-09-13** (Kent's ruling on `docs/thin-strokes-flip-2026-09-13.md`: *"Flip it — take gaulke and becker as the price"*; False is the pre-flip engine and stays tested)** (PR #426 the flat absorb-by-colour rule, PR #427 the gradient lane's thin population): Fremont forced flat 135 → **3** lost thin strokes (recall 61.2% → 92.7%) for 33 → 165 regions and 71 → 81 trims; Fremont ROUTED 18 → **3** lost (85.2% → 92.5%) at **MORE** stitches and FEWER trims — 18,316 → 19,881 and 103 → 76, re-measured 2026-09-13 on `8a94bfe` (`docs/thin-strokes-flip-2026-09-13.md`). **The "fewer stitches" half of this line was true on 2026-09-08's engine and is false on this one**: the cause is `cfg.subpixel_edges` alone, flipped ON 09-09 — with it off today Fremont reads 18,337 → 16,974 and the saving returns, and putting all seven post-09-08 defaults back reproduces the old pair within 0.4%. Sub-pixel vertices grow polygons 45–155%, and ON there are 110 more regions to grow; drone routed 29 → 2 lost (51% → 96%) for 59 more trims. Photo classes are gated out. Flipping it is Kent's.

### `lettering_min_column_mm` (2026-09-09)

**`cfg.lettering_min_column_mm` is BUILT with its tier rule, DEFAULT OFF (None)**: the floor widens a rescued glyph's polygon, and (2026-09-09, the PR after #428) stage 7 sews that widened population on its compensated polygon instead of routing it to the run tier on its area, while stage 5 lets it grow over the ground it was vectorized as a hole in (without that, every widened Fremont glyph was clipped back to a 0.28 mm hole and the first measurement read as a negative) and plans the layers around it against its sewn column, so a ground whose thread sews after the lettering no longer buries 79% of it. Fremont ON: 8 of 10 widened glyphs sew **169 satin columns at a 0.91 mm median** (the pro's file: 0.82–0.90), routed legibility 0.551 → 0.577, stitches 16,006 → 15,823 — but the crops (`docs/renders/column-tier-2026-09-09/`) show the 1.0 mm column filling counters at a 2.2 mm cap height; ENTHUSIAST's 1.6 mm subline SMEARS (columns p10 0.16 mm, legibility **1.00 → 0.72**) — a glyph-height gate is the open question before the flag can ship on, Kent's call.

### Item 7 — `design_angle` (2026-09-09)

**Item 7 is BUILT as `cfg.design_angle`, DEFAULT OFF (2026-09-09)**: one stitch direction for the design's shapes without a house of their own — the lettering house where its lines agree, else the fewest-columns row direction summed over the fills — read by stage 7 before the per-shape derivation, by satin before the per-stroke tangent (so non-lettering satin gets the lean rule) and by stage 5's comp axis. The pro's three sewn Becker files hold ONE fill angle at every size (20.5° slab, 13–14° small fills), so no per-shape override was built. Becker at the pro's 95.7 mm: spread 0.15 → **0.999**, chance-corrected `direction` **0.0 → 0.289** (raw 0.43 → 0.64), stitches +4.2%, trims 27 → 22; at 76.5 / 101.9 mm `direction` 0.388 → 0.41 / 0.0 → 0.249 at −1.5% / +6.3% stitches. Forced flat, Bridge Bar's 15 fills 0.781 → 1.0 at −2.6%, gaulke +7.5%. The last ~20° to the pro's angle is a house-style number no objective derives — Kent's. Byte-identical off on ten fixtures. *(measured 2026-09-09 — scope-history's item 7 entry; `tests/test_design_angle.py`, 7)*

### Item 9 — `enclosed_by_garment` (2026-09-10)

**Item 9 is BUILT as `cfg.enclosed_by_garment`, DEFAULT ON since 2026-09-10 (built OFF that morning, flipped the same day on Kent's ruling over the renders; False is the pre-flip engine; the threshold stays 10 and alpha holes stay with the review toggle, his other two rulings)**: an enclosed background-coloured region whose colour is KNOWN (a border-flood hole, `Prep.bg_rgb`; never an alpha hole) sews by default when the garment the Studio names (`cfg.garment_rgb`, from `project.fabricRgb`) is more than `enclosed_by_garment_de00` = 10 ΔE00 (`DELTA_E_CLEARLY_DIFFERENT`, pinned) from it — one verdict per design, read by the stitched seam and by the colour cap's ranking so a hole that will sew keeps its cone; a review override still wins. At 12 / 80 mm: whitebg and Golden Tee sew their white holes white on Navy and Black (+571 st / 1 cone; +3,027 st / +7 tr / 1 cone) and are byte-identical on White and Natural (6.4 ΔE00 from Natural); gaulke's 46 black bodies sew on any light garment for +3,979 stitches and **+43 trims**, as the fragments the vectorizer kept when they were holes (STEEL ROOFING & SUPPLY reads, GAULKE INDUSTRIES does not — `keep_thin_strokes` is the other half of that lettering). At the Studio's 6 a sewing hole's cone takes a slot from the artwork on a logo already at six: Golden Tee's `1312` Burnt Orange edge merges into Black (35 ΔE00) on Navy — the slider's price, named by `COLOR_CAP_APPLIED`. And gaulke's white ground turns its fill rows from 0° to 45° when its bodies sew — `best_fill_angle_deg`'s fewest-columns argmin on the polygon the ground is now sewn as, not anything this flag does; `cfg.design_angle` (item 7) is the control that would hold it. The threshold, the alpha holes and the flip are Kent's (plan §5). *(measured 2026-09-10 — `docs/renders/enclosed-by-garment-2026-09-10/`; `tests/test_enclosed_by_garment.py`, 12)*

### Item 11 — thread-match floor, `raw_score`, `legibility_check` (2026-09-10)

**Item 11 is BUILT in three parts (2026-09-10; Kent's pick "Item 11 and 1"): (1) `THREAD_MATCH_POOR` has the sibling patch floor, `_THREAD_MATCH_MIN_PATCH_MM2` = 5.0 mm² (= `_UNCOVERED_MIN_PATCH_MM2`), ON — a graded patch under it cannot judge a thread, sub-floor offenders ride flagged in `regions`; over the scorecard matrix (52 pairs at 80 mm / 12, `tools/thread_match_floor.py`) 40 blocking findings → **26**, gaulke D 46 → **B 76** on both garments (its one block rode a 0.21 mm² patch), drone raw −140 → −80, the screenshot −116 → −38, Golden Tee −92/−104 → −50/−62, Bridge Bar unmoved (its shards judge on 9.5–9.8 mm²), no design leaves the 0 floor; (2) the un-clamped score is READ, not just carried — `raw_score` on the flip sheet's rows and verdicts and on the scorecard's score line, the baseline recaptured 2026-09-10 at `9f3d09c`: 46 of 52 pairs had moved since the 2026-09-04 capture, every mover attributed in the recapture commit — this PR's floor on drone, gaulke, Golden Tee and the screenshot (exact, from the sweep), the flips since 09-04 for the rest, and two grade drops bisected on main's first-parent history to #432 (grass_macro B 76 → D 52, the subpixel flip) and #433 (Becker at hat_front B 88 → 76, junction clustering; left_chest unmoved) and left flagged for a follow-up, not this PR's; on this engine **10 of 52 pairs sit on the clamped 0 with raw −140 .. −26** (2026-09-06: 12, −272 .. −38); (3) **`cfg.legibility_check` is BUILT and DEFAULT ON since 2026-09-10** (built OFF in #449, flipped in the PR after on Kent's ruling A over the OCR crops; False is the pre-flip report byte for byte): `LETTERING_ILLEGIBLE`, preflight reading what the thread SAYS per text cluster (`digitizer_core/legibility.py`, the 09-08 instrument moved into the package, `tools/legibility.py` a CLI over it; `ART_MIN_LETTERS` = 3, unsewn clusters left to the unsewn warnings, ~3.5 s per cluster), `LEGIBILITY_WARN` = 0.5 / `LEGIBILITY_BLOCK` = 0.0 — a warn, never a block, RULED — because the OCR crops show the similarity trustworthy at its ends and noisy between (DRONE 0.22 reads with its E lost, SPOTIFY 0.50 is blobs, HOTEL FREMONT 0.74 is clean): a warn under 0.5 catches every row Kent named (Bridge Bar 0.13, DRONE, the screenshot's 3 mm rows) and is silent on every row that reads. Kent ruled all three the same day (plan §6): option A, ON, and the gradient lane stays on raw distance (row 4 closes). **On the corpus the flip adds the warn to 7 of 52 pairs** — Bridge Bar both garments (0.13), the screenshot both (worst 0.00), summit_badge both (worst 0.00 — "Text on the bottom was dropped out", Kent 08-27) and drone at left_chest (0.36) but NOT at hat_front (0.55: the cap's density changes the RENDER the check reads) — and only Bridge Bar's clamped score moves (16 → 4, 4 → 0); the rest are on the 0 floor and move in `raw_score` alone, which is row 6's mechanism made visible. gaulke reads 0.21–0.29 and does NOT warn (its clusters are unsewn enclosed holes — the `sewn` rule), Becker and Golden Tee have no readable art truth, Fremont at 80 mm reads 0.96–1.00. The two accepted costs: it never blocks, and SPOTIFY at exactly 0.50 is missed. *(measured 2026-09-10 — `docs/superpowers/plans/2026-09-10-legibility-yardstick.md` §4; `docs/renders/legibility-2026-09-10/`; `tests/test_legibility_check.py` (7); `tests/test_thread_match_area_in_message.py`)* OCR on the render is a LOWER bound on loss: Fremont's THE reads 1.00 at confidence 95 on a render that shows T H C, while the thin-stroke instrument reads the E at 74% recall.

### Sub-pixel edges — the ladder and PRs 2–4 (2026-09-09)

**The sub-pixel plan's ladder is BUILT too** (`digitizer/tools/edge_truth_ladder.py`, 200–3200 px): below ~15 px/mm the deviation is the pixel and falls with resolution; above it the floor is the **0.2 mm simplification tolerance** and does not fall, so the plan's acceptance criterion was restated before any engine code. **PRs 2–4 of that plan are BUILT and `cfg.subpixel_edges` is DEFAULT ON (Kent's flip 2026-09-09; False is the pre-flip polygon byte for byte)** — stage 4's vertices move onto the anti-alias edge by area conservation (circle vertex spread 0.049 → 0.013 mm at 400 px; the rectangles' Hausdorff 0.12–0.18 → 0.01–0.02), which makes the polygon inscribed, so its boundary offset now reads the simplifier's chord sag until PR 3 keys the refinement to acceptance; sources stage 1 upscaled were declined until item 3's regime. **PR 3 is BUILT the same day** — the refinement keyed to that acceptance (0.25 px floor on accepted chords, the 20 px/mm gate lifted ON): the circle's boundary spread 0.057/0.047/0.035/0.023 → **0.036/0.025/0.024/0.022 mm** at 400–3200 px, the ring's 0.085 → 0.050 at 400; the §5 flip criterion (every rung ≤ OFF's 3200) is met on the circle at 3200 and bounded elsewhere by the 15° turn rule's own sag (0.06 mm on the ring's 7 mm hole). The per-shape tier diff ON flips three drone ribbons and grows vertices 45–155% on real logos (Fremont 1,501 → 2,170; trims 42 → 46). **PR 4 FLIPPED it (2026-09-09, Kent's approval)**: goldens re-captured on ubuntu-latest with the pre-change proof (whitebg 4558 → 4550, alpha 4534 → 4576, ribbon 999 → 991; enthusiast refused, the platform red), and the flip found three mechanisms balanced on a pixel — stage 6's `medial_axis` pinhole diamond (becker's worst bare patch **23.8 → 8.2 mm²**, enthusiast 150's 8.8 → 4.5), the taper zone's crowding (crowded same-rail steps **826 → 459** across the corpus at −0.18% stitches), a fault-injection fixture — each fixed where it lives, never in the polygon (DOCTRINE 2026-09-09). `curve_turn_deg` 15° and the upscaled decline are carried as Kent's.

### Item 4 — `wide_columns` (2026-09-09)

**Item 4 is BUILT as `cfg.wide_columns`, DEFAULT OFF (2026-09-09)**: a 6.5 mm ceiling read off the pro's sewn MARINE (p99 6.2) threaded as one number from classifier to emitter, with the bend's radius of curvature as the overlap guard (load-bearing on Becker at 80 mm before the corner rule, 7.07 → 5.08; under it the fold is gone, 4.67 unguarded). ON it admits exactly the band and MARINE sews satin at **−13% stitches** with **251 self-crossings** and the drone wing 7 mm² bare: the decomposition, not the width, is the blocker (`docs/renders/wide-columns-2026-09-09/`); Kent's call.

### Thin-stroke PR 2 and the 2026-09-13 flip

**PR 2 of the thin-stroke plan (`keep_thin_strokes`, ON above)** — ON, a sub-floor region is absorbed into its neighbour only when its colour is within `merge_delta_e` of the absorber's, else kept for the run tier (flat lane only until PR 3). Fremont forced flat loses **3 thin strokes instead of 135** (recall 86.1% → 97.3%; the 0.5–1.0 mm band 51% → 88%) for 33 → 165 regions, +25% stitches and 71 → 81 trims at the same three colour blocks; gaulke unmoved. **FLIPPED 2026-09-13 on the render it had never had** — re-measured that day the cost had changed sign (`subpixel_edges`, ON 09-09, grows polygons 45–155%): Fremont +8.5% stitches and 103 → 76 trims, C 64 → B 76; drone's `AND DRONE` goes unsewn → sewn on the render while its scorecard does not move (F 0, raw −68 both ways); gaulke pays 2 → 4 cones for **zero** recall change and becker a second cone on a one-cone design — both accepted prices. Landed with two flat-golden re-captures and 30 tests re-pinned across 18 files. *(measured 2026-09-13 — `docs/thin-strokes-flip-2026-09-13.md`, `docs/renders/thin-strokes-2026-09-13/`)*

## Defects 21–25 in full — moved from MASTER_SCOPE (2026-10-12)

Lifted verbatim out of MASTER_SCOPE's live list on 2026-10-12, when all five were fixed and the file needed headroom under its 27,000-word budget. MASTER_SCOPE keeps a closed one-line pointer for each, under the same number, because other docs cite them by number. Nothing here was re-measured on the move.

21. **Fill travel is laid OVER columns already sewn — FIXED, DEFAULT ON (Kent's flip
    2026-09-03)** (`cfg.fill_travel_under_cover`, PR #323): the column order prefers a next
    column reachable over unsewn ground (`_reorder_for_cover`, cuts × 25 + travel + exposed × 2,
    never worse) and an exposed bridge routes through unsewn ground. Fill-phase exposed travel
    Fremont **286 → 90 mm** (trims 47 → 52), drone 546 → 89 — 09-03 figures, STALE; OFF md5-identical; +7–11% time on logos, +49–67% on the 263-run photo fill. *(measured 2026-09-03 — `docs/fill-travel-under-cover-2026-09-03.md`)* **Residual:** 2026-09-11, 80 mm, Becker **29.6 of 76.7 mm**, Bridge Bar 114.2 of 275.4, Fremont 23.9 of 123.5. **The CAUSE is now established and it disqualifies all three fixes review item 12 proposed** (`digitizer/tools/fill_bridges.py`, 9 fixtures / 92 bridges / 912.6 mm): **88% (801 mm) have NO unsewn corridor touching both ends** — no routing rule reaches them, the column ORDER made them — 6% a corridor the router cannot use, 4% the detour cap, 2% already buried by a later cone. Priced out (DOCTRINE): routing under the covering colour (the 2%), lifting bridges under `trim_at` (26 mm, none on the four review designs), a raised detour cap (BUILT, a **perfect no-op on all nine**). A fourth arm (prefer a next column still sharing unsewn ground) is WORSE on six of nine (gaulke 3.1 → 84.0 mm): `_score` buys its fewer CUTS at 25 : 2, and a per-shape ratchet did not stop it because `_order_cost` and `emit` can disagree (`route_cache`). Both reverted (DOCTRINE). Left: Kent's exchange rate, scorer/emitter agreement, the greedy itself.
    *(measured 2026-09-11 — `docs/superpowers/plans/2026-09-11-fill-travel-bridges.md`; `tests/test_fill_bridges.py`, 4)* **`travel_cover.py`'s 245 mm on the nine logos IS this residual:** 97.7% `stage6_fill`'s `emit`, all on the shape's own finished fill, **0.0 mm on bare fabric** — not gate 3's letter; its grid under-reads (375 mm exact). **`cfg.fill_bridge_cut`, DEFAULT ON (Kent's flip 2026-09-19, over thread renders, not yet cloth):** lift a bridge costing more than the cut at 25 : 2, single-pass fills only — exposed 248.6 → 140.9 mm, trims 458 → 464, uncovered unchanged, OFF md5-identical ×9; Fremont's new `LETTERING_ILLEGIBLE` is the OCR judge (tagline runs byte-identical). *(measured 2026-09-19 — `digitizer/tools/travel_legs.py`, `tests/test_fill_bridge_cut.py`, 15; scope-history, "the exposed travel legs")*

22. **Small curves sew as polygons — FIXED, DEFAULT ON (Kent's flip, 2026-09-03)** (`curve_turn_deg` = 15; None/0 = the old polygon): a turn-per-vertex bound re-reads each Douglas-Peucker edge against its raw arc, split at the midpoint, floored at one pixel; near-floor lettering exempt per ring. Fremont's counter **9 → 33 vertices, 47° → 17°**, inner rail σ 0.038 → 0.026 mm, trims 52 → 45. **Gated to 20 px/mm** (`_CURVE_MIN_PX_PER_MM`; four pixels of tolerance at 0.2 mm): below it the 1-px floor read raster texture as arcs — every 10–16 px/mm fixture got rougher (sunset 16.1 → 16.5, meadow 15.2 → 16.5) and two borderline ribbons changed tier through the DT classifier's skeleton — so a 600–1200 px web logo at 80 mm is byte-identical and every golden stays pinned — but 1200 px art at ≤ 60 mm (2000 px at ≤ 100 mm) is over the line and refines, and the line is a cliff (60 → 61 mm changes every curve's polygon; Kent's to accept); `tools/curve_tiers.py` is the per-shape tier diff. *(measured 2026-09-03 — `docs/round-curves-2026-09-03.md`, "The flip")*

23. **Rail dents — FIXED (Kent, 2026-09-03), diagnosis corrected.** `place` stepped an overshooting rail in by 15% however small the overshoot (250–1000 placements per design, 70–90% under one pixel) and now puts it on the artwork edge along its own normal, with a micron of containment tolerance; taper zones and caps keep the ladder. Rail jitter p50 **halves on every fixture** (Fremont 0.012 → 0.0045 mm), same-rail holes 11 → 5, median rail 0.02–0.08 mm further out, nothing further outside the art. The "one whole rail 15% short in every golden" was the synthetic bar, not the goldens (the micron alone moved 4 stitches on Fremont); the 8–24% of rail points > 0.1 mm inside on real art turned out to be the short-stitch guard, corridor caps and corners, not the rail model — the honest coverage number is BARE SATIN AREA, and each rail reaching its own edge (`satin_rails_follow_edge`, **BUILT, DEFAULT OFF, Kent's flip**) takes it Becker 8.6 → 5.8%, ENTHUSIAST 5.7 → 4.4%, drone 6.1 → 4.6% for +10–17% thread, +50% rail jitter and more guard retractions; the pull comp was tuned with the far rail short — a sew-out question. Goldens re-pinned in #329: alpha, ribbon ×3. *(measured 2026-09-03 — `docs/rail-dents-2026-09-03.md`)* **Its cost is OVERSHOOT, not bare art (2026-09-20):** measured colour-free, `enthusiast` leaves **0.90% of its ink unthreaded, nothing over 1 mm²** — no lost element — while thread covers 1.51× the ink. `lost_frac` ships SPLIT. *(measured 2026-09-20 — PR #536; DOCTRINE)*

24. **Hairline columns (< 0.6 mm) — the MECHANISM is fixed, the tier is not.** A hairline STRETCH of a stroke (crosses under the 0.5 mm floor, ≥ three bean stations of spine) now sews as a 3-pass bean along its spine in both engines, only where the uncompensated art is wider than `simplify_tol_mm` (pull comp grew a 0.04 mm needle into a tick); Fremont's 2.6 mm "THE" reads. Whether a 0.5 mm bean reads better on cloth than a dropped bar is card block 5's question — `pending sew-out`. *(fixed 2026-09-03 — `docs/design-review-fine-lettering-2026-09-03.md`)*

25. **Fill stitches HALVED by float dust at the stitch-length threshold — FIXED (Kent, 2026-09-03).**
    `split_long_moves` split a 3.0000000000000004 mm grid step into two 1.5s; a micron of tolerance
    (`stitches.SPLIT_TOLERANCE_MM`) removes them: whitebg 2162 → **1982** st, Fremont 6365 → **5789**, sunset 11614 → **10416**, no row or trim moves. Goldens re-pinned (whitebg, alpha; pre-change tree). `tools/fill_dust.py`. *(fixed 2026-09-03 — same doc)*

## Phase 1's two instruments and the sittings 09-18 → 10-01 — moved from MASTER_SCOPE (2026-10-12)

Lifted verbatim from MASTER_SCOPE's evaluation-harness section when the pooled kappa of PR #842 (and PR #847's density/flow re-read) replaced the sitting-by-sitting chronology there with a verdict. Every number below was true on its date.

**Phase 1's exit condition has TWO instruments: `digitizer/tools/eye_pairs` (its second clause — Kent's picks on same-design A/B pairs; built 2026-09-17, PR #506; no blind sitting — labelled sittings instead: 09-18 and 09-28, all 77 pairs judged (today beats the 08-27 engine 7 of 9, `satin_rail_comp` the only flag leaning better, four logos bad under every setting — `docs/kent-review-2026-09-28.md`); 2026-09-30 the envelope (2 after, 0 before, flipped ON) and, that evening, the day's three lettering changes before | after with a needle-hole map beside every render: 4 no difference, 3 both bad, 1 before on a confounded pair (the ref worktree had no photo-prep venv; fixed in the yardstick), and the dissolve stays OFF on 2 before, 1 after; then, late, the lettering texture sitting: the pro's 7 mm split style read no different from the comb on every judged pair and the symmetric rails lost golden_tee, so both stay as shipped; screenshot ruled off the page; **2026-10-01 the pro's own Becker file beside ours: the pro's flows, and Kent's word is the back stitching — `tools/underlay_cover.py` (one rule on both files' stitches) finds the stems' support already equal (20.7% of the top thread on thread, both) and the difference in the comb: every MARINE stem is 5.5-6.9 mm, over the 5.0 split, 1,413 holes inside the stems against the pro's 304 (246 with the split off), so `split_off` is the next arm; the arch letters' fill is the 146-px source's, not the engine's** (`docs/eye-pairs-2026-09-30/`)) and `digitizer/tools/artfid_eye_rank.py`,** a blind rank harness correlating ARTFID's ordering with a viewer's. First run: the pre-registered primary is **null and underpowered by construction** (tau-b +0.048, n=7 after refusals). The load-bearing result sits behind it — **ARTFID scores are NOT comparable across routes**, and "preflight grade beats ARTFID" is a confound for `route == flat`. Do not pool ARTFID over mixed routes and read the ordering as quality. Also live: `colour` reads exactly 1.000 on 11 of 14 fixtures while carrying 25% of the composite. Full result and two disproved hypotheses: DOCTRINE "ARTFID is not comparable ACROSS routes". *(measured 2026-09-11 — [`docs/artfid-eye-agreement-2026-09-11.md`](docs/artfid-eye-agreement-2026-09-11.md))*

## Defects 30 and 32 in full — moved from MASTER_SCOPE (2026-10-12)

Lifted verbatim out of MASTER_SCOPE's live list on 2026-10-12: both were fixed in September and still sat under "Live defects". MASTER_SCOPE keeps a closed one-line pointer for each under the same number.

30. **The review screen's per-layer cone list named threads its layer does not sew — FIXED, DEFAULT ON since 2026-09-13** (`cfg.layer_palette_from_regions`, `stage3_segment.layer_palette_threads`). `palette[i]` answered *what stage 2 CALLED layer i*, not *what its shapes sew* — `compact_layers` drops slots and never re-reads a survivor's thread. ON, each layer's cone is elected from its own regions, pinning `palette[i].number in {r.thread_number for r in layer i}` — **not** `palette ⊆ block cones`, which the blend tier breaks. **Every number this entry used to carry was wrong** — count, direction and mechanism — and the corrections are tabled in the doc below, including that at the Studio's shipped `max_colors=6` the defect ran **5× its published size**.
    **Flip cost:** mislabelled layers 7 → 0 at 12 and 13 → 0 at 6, with the plan digest, every stitch coordinate, `design.colors` and `thread_mm_by_color` **identical off vs on, 26/26, both settings** — *review-only* is a measurement now, not a call-graph argument. **Accepted price** (Kent's, knowingly): duplicate review ROWS, 0 → 13 at 6, because `merge_duplicate_cone_layers` folds on the DECLARED cone upstream of the election; folding them is the open follow-up and moves sew order. *(measured 2026-09-12 — `docs/palette-mismatch-2026-09-12.md`, `docs/palette-flip-corpus-2026-09-12.md`; `tests/test_layer_palette.py`)*

32. **The low-resolution warning could not fire, and the Studio was wired to show it.** `stage1_prep` tested the resolution AFTER its own capped Lanczos upscale — and with `upscale_cap` and `min_px_per_mm` both **4.0**, any source at or above 1.0 px/mm lands exactly ON the floor, so the condition was false for every design a customer could send. `INPUT_LOW_RESOLUTION` has been in the Studio's `ATTENTION_WARNINGS` and had a `WARNING_TEXT` sentence the whole time; neither had ever been shown. **FIXED, no flag** (2026-09-07): it fires on `Prep.input_px_per_mm`, what the FILE supplied, and reports that plus `upscaled_to` and the floor — the old `px_per_mm` extra was the post-upscale value, i.e. the constant 4.0 dressed as a measurement. The customer sentence now carries the number and the multiple ("1.4 pixels per millimetre at this size and needs 4 … about 2.8x wider"), because "low resolution" says there is a problem and not what fixes it. **Precise, not noisy: exactly 2 of the scorecard's 26 fixtures arrive under the floor** — `becker_marine_logo` 1.81 px/mm and `logo_bridge_bar` 3.49 at 80 mm — and they are two of the three renders `docs/kent-review-2026-09-03.md` reports as settled before the engine ran ("a higher-resolution Becker source would change this render more than any engine change"). Both were silent. *(measured 2026-09-07 — `tests/test_input_resolution_warning.py`, `app/src/lib/digitizer.spec.js`)* **The warning's line and the tracer's grid are two numbers since 2026-09-30** — defect 51; the "settled before the engine ran" reading of bridge was wrong.

## Hairline tier (PR #848) and `coverage_edges` — moved from MASTER_SCOPE (2026-10-12, second pass)

Lifted verbatim from MASTER_SCOPE's area 1 verdict when PRs #850–#852 superseded parts of them. Two statements below are no longer true: #848's "the tracer widens a hairline ~0.11 mm" was a units error (the fixture rendered at 80 mm, drawn at 69.15 mm; PR #850), and steps 2 and 3 are built (PRs #850, #851). `coverage_edges` is DEPRECATED on Kent's 2026-10-12 ruling (PR #852). Every number was true on its date.

**Thread weight and a hairline tier (2026-10-12) — `cfg.hairline` DEFAULT OFF, thread weight 40 by default (PR #848).** Kent: *"Thread is extremely thin, we should be able to embroider hair!"* The research came first (PR #843, `docs/fine-detail-hair-research-2026-10-12.md`): thin thread is three steps (40/60/75 wt), no vendor publishes a diameter (√dtex scaling gives 0.32 / 0.26 mm, arithmetic), and the floor is the NEEDLE — Melco publishes run ≥ 1.5 mm and satin/column ≥ 1.0 mm — so a thinner thread changes density and lettering size, never the minimum stitch. **Correction:** `docs/trade-knowledge-2026-09-13.md` §5 says no published minimum satin width exists; Melco's service page publishes 1.0 mm. Built: `machine.thread_profile(40|60|75)` (laid width, satin spacing, a hairline limit of 1.5 × the width, cap-height note, needle advice; the minimum stitch is 1.0 mm at every weight, test-enforced); a per-colour-block weight through `shape_overrides` (today it moves satin spacing and the hairline limit only); `stage6_hairline.py` sews a stroke under the limit as ONE pass down its skeleton, Euler-walked, no stitch under 1.0 mm. A drawn 40-strand hair fixture at 80 mm: dark-thread stitches 9,574 → 1,349, dark stitches under 1.0 mm 3,729 → 0; one 32.8 mm strand 274 stitches and 197.7 mm of thread today → 24 and 32.8. **Open, from its findings:** the tracer widens a hairline ~0.11 mm (60 wt admits the hair with 0.025 mm to spare); cloth shows between strands because stage 5 knocks the ground out round the hair, so the ground must run UNDER hairline shapes — step 2, in flight ("Waiting on Kent" 45); the width check is per shape, so a thin skin sliver qualifies; curls under 1.5 mm radius look polygonal. Every 60/75 wt value and the 1.5 mm stitch is a gate-1 candidate; the sew-out card is written in the doc as a DST list, not generated. Renders only. *(measured 2026-10-12 — PR #848, `docs/hairline-prototype-2026-10-12.md`; `tests/test_thread_profile.py`, `tests/test_hairline_tier.py`)*

**Low-resolution outlines (2026-10-10/11): the hard stair-stepped mask, not the pixel count, is the limit.** An off-the-shelf tracer (vtracer, nine settings) is not closer than stage 4 (closer in 5 of 26 cases, stage 4 in 13). `cfg.coverage_edges`, DEFAULT OFF (PR #818): a one-ink alpha cutout enlarged by stage 1 takes its polygons from the source alpha's half-coverage contour — median edge error at 1.8 px/mm 0.121 / 0.094 → 0.053 / 0.042 mm (golden_tee / Fremont against native truth), Becker's outline reversals 37 → 7 — but a sharp synthetic corner gets worse (0.03 → 0.22 mm) and MARINE sews messier under the skeleton tier, so it belongs with the Column lane ("Waiting on Kent" 38). The reversals come from `subpixel_edges_upscaled`'s read at 1.8 px/mm; a resolution floor under it is built unset and left so (Kent, item 41). **The reversals' own cure is BUILT OFF — `cfg.subpixel_corner_runs` (PR #834):** one fit per corner run, an unread vertex takes its read neighbours' offset, a vertex landing behind its predecessor drops; Becker at 1.8 px/mm reversals **7.1 → 0.9** per 100 mm, right-angle turns 26.5 → 20.1, worst median edge-error change +0.0028 mm over four cases × three rungs; 16 reversal vertices remain, and at 3 and 5 px/mm Becker reads 1.3 and 1.4. Nothing sewn. *(measured 2026-10-10/11 — PRs #818, #824, #826, #834; `docs/low-res-outline-sparknotes-2026-10-10.md`, `docs/native-read-corners-2026-10-11.md`)*

## Item 6 — `satin_rail_comp` and the envelope (moved from MASTER_SCOPE 2026-10-13)

Verbatim as it stood in MASTER_SCOPE before the 2026-10-13 refresh; the verdict left there points here.

**Item 6 is BUILT as `cfg.satin_rail_comp`, DEFAULT ON since 2026-09-28** (built OFF 2026-09-09; flipped by Kent on the labelled sitting — after-better on five logos, before-better on none — `docs/kent-review-2026-09-28.md`; the sew-out is still owed; **the flip's price ACCEPTED by Kent 2026-09-29, MARINE's trims a ceiling in `tests/test_rail_comp.py`; the hairline seams of stage 5's on-rails polygon are closed for the whole satin column — skeleton since 2026-09-29, rails, caps and underlay since 2026-09-30 (PR #565); the price, the trim fixes and the seam numbers: [`docs/scope/1-auto-digitizing-quality.md`](docs/scope/1-auto-digitizing-quality.md#rail-comp-the-flips-price-and-the-seams-2026-09-2930); **the far rail's under-reach is cured by `satin_rails_follow_edge="envelope"`, built 2026-09-30 and ON the same night on Kent's eye (2 after / 0 before)**: a rail extends only where its side is short by 0.3 mm, to the running minimum of its own edge over ±3 stations — golden_tee bare 10.35 → 7.20%, Becker 100 8.14 → 7.35, ENTHUSIAST a no-op (`docs/renders/rail-envelope-2026-09-30/`, `docs/eye-pairs-2026-09-30/`); `True` stays parked, the sew-out still owed. **Becker's void-filling texture was the envelope reaching through junctions (fixed 2026-09-30):** at a junction the far ray runs along the meeting arm, so 313 of 459 reached stations over nine logos landed on satin a sibling stroke already sews (78% of the envelope's new thread on Becker's letters); `_in_sibling_ribbon` refuses a reach whose end lies in a sibling's corridor — 23 escapes left, Becker 100 9,563 → 8,932 stitches, the reach kept (Becker 80 bare 9.484 → 9.550%), golden_tee's keylines untouched; the short genuine reaches read as teeth (`docs/renders/envelope-escapes-2026-09-30/`) — **dropped the same day: a reach shorter than the envelope's window is not a reach (`_drop_short_reaches`, no new constant; Becker's 8 single-station teeth gone for 7% of the extension area, reached-station jitter 28.4 → 26.3%, the rest the long reaches' own steps, `docs/renders/envelope-teeth-2026-09-30/`)**; **the letters' split satin no longer flickers (2026-09-30): the split comb is decided per column — hysteresis on `SPLIT_SATIN_ABOVE_MM` with `SPLIT_SEGMENT_MM` as its floor, `_comb_thresholds` — Becker 100 122 → 37 on/off changes at +4.5% stitches, tires 21 → 5, bridge 20 → 5, no leg longer than the threshold; the pro's own Becker files comb nothing (raw to ~7 mm, 1–2% split under 5.5), a house style whose threshold is a sew-out question (`docs/renders/split-comb-2026-09-30/`)**): a satin-tier shape keeps its artwork polygon and each rail is pushed out along its cross by the fabric's pull (the amount untouched, gate 1; caps end at the artwork; a counter guard at `min_detail_mm`). Thread-vs-target IoU ENTHUSIAST 0.876 → **0.897**, drone 0.797 → **0.838**, Fremont 0.675 → **0.836**, Becker 0.887 → 0.884; trims 26 → 22 / 96 → 83 / 46 → 45 / 36 → 40; coverage peaks down on three; thread sewn outside the artwork 147–322 mm² → 0. The grown-polygon skeleton with artwork rails (one line away) takes most of it (drone 0.829, Fremont 0.813) and keeps Becker's decomposition (34 trims, 3 strokes on the A for the artwork's 7) — the artwork skeleton RULED 2026-09-19 (Kent). The build found `_skeleton_edges` stranding chains at junction cliques and L-corner fillers (fixed ON BY DEFAULT; OFF moves drone `S60de6f78` 43 → 45 stitches and ENTHUSIAST's house angle by 0.03°). *(measured 2026-09-09 — scope-history's item 6 entry; `tests/test_rail_comp.py`, `tests/test_skeleton_tracer.py`)*

## Item 5, PRs 2 and 3 — moved from MASTER_SCOPE (2026-10-13)

Verbatim as it stood in MASTER_SCOPE before the 2026-10-13 refresh; the verdict left there points here.

**Item 5, PR 2 (2026-09-09): the serif column was NOT built — `digitizer/tools/letterforms.py` read every column end and found no serif in the artwork's feet (146 × 91 px source) and MARINE's 251 "self-crossing pairs" to be 0 within any column and 359 between columns at two Goldman joins, which the pro's own sewn MARINE has 2,593 of (DOCTRINE 09-09). The junction cover half shipped: **`cfg.satin_patch_junctions = "satin"`, DEFAULT OFF** — the grader's patches as satin columns FIRST in the shape under the arms, Becker 80 mm `ARTWORK_UNCOVERED` 9.0 → 0.0, B 76 → B 88 at +122 stitches / +2 trims (the tatami: +297 / +3); Fremont's band under `wide_columns` 128.2 → 13.0 mm² for +10.6%; the over-fire at Becker 100 mm (0.0 both ways, `TRIM_HEAVY` on +2 trims) is the tatami's too. *(measured 2026-09-09 — scope-history's item 5 PR 2 entry; `tests/test_junction_patch_flag.py`)* **Item 5, PR 3 measured out the same day** (`digitizer/tools/junction_blobs.py`, `pro_layers.py`): a 17 mm bold letter is 45–90% junction ball, and the pro's own file stacks MORE layers at every MARINE junction than we do (p95 3.7–7.3 vs 1.8–3.8; +58% thread in the word) — no blob column, no arms-only width statistic. *(measured 2026-09-09 — scope-history's item 5 PR 3 entry)*

## Hairline tier paragraph moved from MASTER_SCOPE (2026-10-13)

Lifted verbatim from MASTER_SCOPE area 1 when PRs #872-#882 made it stale; the live status is "Waiting on Kent" 45.

**Thread weight and a hairline tier (2026-10-12) — `cfg.hairline` and `cfg.hairline_over_ground` DEFAULT OFF, thread weight 40 by default (PRs #848, #850, #851).** Kent: *"Thread is extremely thin, we should be able to embroider hair!"* The floor is the NEEDLE, not the thread — Melco publishes run ≥ 1.5 mm and satin ≥ 1.0 mm, so a thinner weight changes density and lettering size, never the minimum stitch (research PR #843; it corrects `docs/trade-knowledge-2026-09-13.md` §5). Built: `machine.thread_profile(40|60|75)` and a per-colour-block `thread_wt`; `stage6_hairline` sews each skeleton BRANCH under 1.5 × the laid width (0.60 mm at 40 wt, 0.48 at 60) as one Euler-walked run, no stitch under 1.0 mm, its width read off the SOURCE ink, and the thick rest of a mixed shape keeps today's tier (#851); the ground runs under the strands (`hairline_over_ground`, #850), cutting new bare fabric on the ground **~85%** (2.88 → 0.44 mm² at 40 wt) for +11–18% skin-fill stitches by stacking; a sliver rule keeps skin fill md5-identical to OFF at 40 wt. **#848's "tracer widens a hairline ~0.11 mm" was a units error** (the fixture rendered at 80 mm, drawn at 69.15); the tracer's error has no fixed sign. A finer fixture (`hair_fine.png`, strands 0.25–0.35 mm) admits at 60 wt with **0.179 mm** margin; `hair_strands` (median 0.43) only 0.028. **Open:** bare fabric is not zero; curls under 1.5 mm radius look polygonal; `rest_planned` keeps a split rest piece's largest part (defect 61's twin). Every 60/75 wt value, the 1.5 mm stitch and the ground's double layer wait on the hairline card ("Waiting on Kent" 45). Renders only. *(measured 2026-10-12 — PRs #848, #850, #851; `docs/hairline-prototype-2026-10-12.md`, `docs/hairline-ground-2026-10-12.md`, `docs/hairline-strand-gate-2026-10-12.md`; `tests/test_hairline_ground.py`, `tests/test_hairline_strand_gate.py`; #848's full paragraph: [area 1](docs/scope/1-auto-digitizing-quality.md))*

## Lettering construction chain steps 0 to 5 — moved from MASTER_SCOPE (2026-10-13)

**Lettering construction (Kent's route ruling 2026-09-19, plan `2026-09-19-lettering-construction.md`): step 0 BUILT and FLIPPED ON the same day (Kent) — `satin_house_from_line`**, the house angle's third reading for a word both votes refuse (ENTHUSIAST: cross concentration 0.059 → 0.287); the vote was found size-unstable and diagonal-pulled. **Step 1 ON (Kent) — `satin_house_anchor`**: house = line + stems' slant; drone's self-crossings 496 → 430. **Step 2 ON (Kent) — `satin_stroke_order="euler"`**: one walk per shape; nine logos 592 → 486 trims at −19 stitches. **Step 3a ON (Kent) — `satin_corner_twigs`**: corner twigs kept; nine logos' self-crossings 1,813 → 1,004, Becker's band +725 stitches at 100 mm; 3b `satin_rail_comp`: Fremont IoU 0.68 → 0.84, artwork skeleton ruled, **ON since 2026-09-28** (Kent's flip on the labelled sitting, sew-out still owed — `docs/kent-review-2026-09-28.md`). **Step 4 BUILT OFF — `satin_lettering_split`**: no width ceiling for a text-cluster member; MARINE at 127 mm fill 6 → satin 6 at 9,642 → 7,753 stitches — but all 311 new self-crossings sit in the R's junction ball; ON (Kent) after the stack. **The junction construction is DESIGNED before code** (`docs/superpowers/plans/2026-09-19-junction-construction.md`): the 311 are ONE weld folding through 44°; refusing the 30–60° welds reads 311 → 0. **BUILT as `satin_junction_stack`, OFF (Kent: A + B + C)**: the R 311 → 0 at +10 trims, MARINE 80 103 → 0 at +2, Becker's band uncovered 35.5 → 0.0; ON (Kent). **Step 5 BUILT OFF — `edge_cap_skip_lettering`**: fixture trims 23 → 7, stitches 2,192 → 1,774; ON (Kent). **Trims gap: exit lever ON (Kent), underlay OFF;** fixture 13 → 9. *(2026-09-19)* **Refused walks are mostly not a defect (2026-09-20):** 262 of 343 are a web that does not reach; the relaxable 47 are the needle's distance — `satin_walk_cursor_reach_mm` OFF pending a sew-out (Kent), 491 → 471 trims at +65 mm exposed, worst leg 3.3 mm. *(scope-history)* **The Studio never sent the file (fixed 2026-09-20, Kent):** a 1,200-px canvas re-encode reached the engine — alpha rewritten (Becker 59 → 175 trims), low smoothing (tires 6 → 14); the panel sends the upload, the `.embproj` carries it. **`alpha_edge_extend` ON (Kent), gated on the upscale:** Becker reads 54 trims whatever its alpha hides; nothing else moves. *(measured 2026-09-20 — scope-history, DOCTRINE)* **Item 3's upscaled regime is ON (2026-09-18, Kent, `cfg.subpixel_edges_upscaled`):** low-res sources read their own pixels (ladder Hausdorff 0.26 → 0.03 mm); Becker's 100 mm band then flips fill → satin, the decomposition follow-up. *(scope-history)*

## Items 4, 5, 7, 8, 9, 11 and sub-pixel edges — moved from MASTER_SCOPE (2026-10-13)

**Item 7 — `cfg.design_angle`, DEFAULT OFF (built 2026-09-09):** one stitch direction for shapes without a house of their own; the pro's Becker holds ONE fill angle at every size, so no per-shape override was built. Becker's chance-corrected `direction` 0.0 → 0.289 at +4.2% stitches; byte-identical off. The last ~20° to the pro's angle is a house-style number — Kent's. *(measured 2026-09-09 — `tests/test_design_angle.py`; detail: [area 1](docs/scope/1-auto-digitizing-quality.md#area-1-lanes-in-full--moved-from-master_scope-2026-10-08))* **Item 8 RULED 2026-09-10 (Kent): the four colour flags not already ruled ship ON as ONE set** (`enforce_color_cap`, `resnap_mask_matches_grader`, `revalidate_small_shapes`, `bind_resnap_all_classes`; `dissolve_phantom_blends` stays banked), and **`cfg.robust_region_colour` is ON since the same day** — a SLIC+RAG region hands the palette the modal mean of its Lab pixels, not the mean, after Bridge Bar's disc bound to a spool 7.0 ΔE00 off the artwork. False on each is the pre-flip engine. The 26-fixture flip sheet, the per-budget cone/stop tables and the accepted prices: [area 1](docs/scope/1-auto-digitizing-quality.md), "Item 8's colour bundle". *(measured 2026-09-10 — `tools/flip_sheet.py`; `tests/test_robust_region_colour.py`)* **Item 9 — `cfg.enclosed_by_garment`, DEFAULT ON since 2026-09-10 (Kent; the 10 ΔE00 threshold and leaving alpha holes to the review toggle are also his):** an enclosed background-coloured hole of KNOWN colour sews by default when the Studio's garment is more than 10 ΔE00 from it; a review override still wins. Prices accepted: gaulke **+43 trims** on a light garment; at the Studio's 6 colours a sewing hole's cone takes a slot from the artwork (`COLOR_CAP_APPLIED`). *(measured 2026-09-10 — `tests/test_enclosed_by_garment.py`; detail: [area 1](docs/scope/1-auto-digitizing-quality.md#area-1-lanes-in-full--moved-from-master_scope-2026-10-08))* **Item 11 BUILT in three parts (2026-09-10):** `THREAD_MATCH_POOR` takes a 5.0 mm² patch floor (ON; 40 → 26 blocking findings over the 52-pair matrix); `raw_score` is read on the flip sheet and scorecard (two grade drops bisected to #432 and #433, flagged for a follow-up); and **`cfg.legibility_check` is DEFAULT ON** (Kent's ruling A): `LETTERING_ILLEGIBLE` warns under 0.5 and **never blocks, RULED**; SPOTIFY at exactly 0.50 is the accepted miss. OCR on the render is a LOWER bound on loss. *(measured 2026-09-10 — `docs/superpowers/plans/2026-09-10-legibility-yardstick.md` §4; `tests/test_legibility_check.py`; detail: [area 1](docs/scope/1-auto-digitizing-quality.md#area-1-lanes-in-full--moved-from-master_scope-2026-10-08))* **`cfg.subpixel_edges` is DEFAULT ON (Kent's flip 2026-09-09; False is the pre-flip polygon byte for byte):** stage 4's vertices sit on the anti-alias edge; below ~15 px/mm the error is the pixel, above it the 0.2 mm simplification tolerance (`tools/edge_truth_ladder.py`). The three mechanisms the flip exposed were fixed where they live, never in the polygon (DOCTRINE 2026-09-09). `curve_turn_deg` 15° and the upscaled decline are carried as Kent's. *(measured 2026-09-09 — detail: [area 1](docs/scope/1-auto-digitizing-quality.md#area-1-lanes-in-full--moved-from-master_scope-2026-10-08))* **Item 5's first PR is BUILT (2026-09-09): stage 6 clusters split junctions** — stubs under 0.5 half-widths and the loops inside them, the number read off `tools/junction_nodes.py`'s corpus histogram — so a crossing decomposes into its two bars at every scale; interior over-wide rail readings **948 → 830** across 14 fixtures at +0.21% stitches, Becker's bare total 16.0 → 9.0 mm², enthusiast 150's worst 4.5 → 1.2, no golden moved (the flat-lane keys have no branch node); the K's crotch (7.8 → 9.0) stays the junction cover's problem, PR 2. **Item 4 — `cfg.wide_columns`, DEFAULT OFF (2026-09-09):** a 6.5 mm ceiling read off the pro's MARINE; ON, MARINE sews satin at −13% stitches with 251 self-crossings — the decomposition, not the width, is the blocker; Kent's call. *(measured 2026-09-09 — `docs/renders/wide-columns-2026-09-09/`; detail: [area 1](docs/scope/1-auto-digitizing-quality.md#area-1-lanes-in-full--moved-from-master_scope-2026-10-08))* **Thin-stroke PR 2** (the flat lane's absorb-by-colour rule) and the 2026-09-13 flip's accepted prices — gaulke 2 → 4 cones, Becker a second cone: [area 1](docs/scope/1-auto-digitizing-quality.md#area-1-lanes-in-full--moved-from-master_scope-2026-10-08). *(measured 2026-09-13 — `docs/thin-strokes-flip-2026-09-13.md`)*

## Overflow moved from MASTER_SCOPE (2026-10-13, fourth pass)

Moved verbatim to make room for PRs #895-#901. The verdicts stay in MASTER_SCOPE; this is the text they replaced.

### Waiting on Kent 37 (Column lane) as it stood after PR #891

37. **RESOLVED 2026-10-12 — the Column lane is ON by default (Kent's ruling,
   PR #863; renders PR #869).** `lettering_columns` True, `lettering_words`
   False: with words OFF the lane reads the two old taggers, so it needs no
   sibling. The blockers closed: rails at the satin tier's reach
   (`RAIL_REACH_INSET_MM` 0.11, #837), the slanted fan (#844), and sew order
   (#859: non-letters keep the OFF path's rank, letters reorder only within
   their span, no colour change added). golden_tee 50 mm's excess was
   `lettering_words` alone; with words at its default the lane reads under
   shipped there. ON vs OFF, real `digitize()`: `lost_frac` lower at all six
   fixture-widths (golden_tee 50 0.6700 → 0.6103, fremont 0.0302 → 0.0184,
   becker 0.0236 → 0.0186), no new colour change, trims never up;
   wrong-colour rises a little on golden_tee, the sew-order price. Tests of
   the skeleton tier on text fixtures now name the lane OFF. **Still open:**
   - **Letter reach, gate 1:** fremont's and golden_tee's letters stand
     0.06–0.07 mm inside shipped's reach, every fanned slant face 0.19 mm
     outside its traced edge — a sew-out question. Not sewn.
   - **The word tagger misses glyphs at 50 mm — MEASURED 2026-10-13 (PR #889), no dominant rule.** 58 of 190
     expected glyphs sit in no word at 50 mm (15 at 100 mm); 39 of the 58 are lost upstream of linking
     (`nested` 18, `no_region` 21), and the largest link rule, `height_ratio`, takes 5. golden_tee's
     "third glyph" is four different rules. A census of single-number relaxations and "rescue" joins found
     none with zero false joins AND a gain, so nothing shipped; the lever it points at is the `nested`
     admission drop. Fix before any `lettering_words` flip. `tools/word_tagger_trace.py`.
   - **Eye-pairs `SPEC_ARMS` still list `lettering_columns` as an OFF arm**
     (`tools/eye_pairs/pairs.py`), now equal to the base; a test asserts the
     table, so it waits on a tidy-up.
   - **Non-letter capture — guards ON 2026-10-13 (Kent, option A, PR #890).** The house-angle group had no
     ink link and no stroke test, so the lane took solid blobs (PR #881: all 12 patches of `test_preflight`'s
     grid, 8 `fur_ramp` discs; 0 of 150 lane shapes on real art) and the enthusiast shield star (a filled
     sparkle sewn as a thin X). `cfg.lettering_columns_skip_blobs` (mean stroke over longer bbox side ≥ 0.40
     and solidity ≥ 0.95) and `cfg.lettering_columns_ink_link` (PR #885: house-group-only, > CIEDE2000 20
     from every text-cluster thread, not within 1.0 mm of a text letter) are ON. Only enthusiast (+159
     stitches, star back to fill), `fur_ramp` and the grid move; every other real-art fixture is identical.
     The 1.0 mm and 0.40/0.95 cuts are candidate shape ratios from one corpus, not cloth constants.
     **Still captured: three white highlight pieces inside screenshot's truck drawing** (not status icons —
     PR #891's correction; two share the text's exact ink, so no ink cut can refuse them).
     `cfg.lettering_columns_icon_guard` (skeleton nodes ≥ 24; captures 36–45, letters ≤ 13) is built OFF:
     "Waiting on Kent" 49.
   - **Lowercase (PR #887, measured 2026-10-13):** on a CC0 Aileron fixture a lowercase station cross folds
     past 45° 1.4% of the time against 0.0% for capitals, only where a curved stroke leaves a straight one
     (u, b, g, m). `cfg.lettering_columns_fold_cuts` (OFF) cuts those (0.4%, +0.6% stitches, capitals
     identical) but leaves a knot of short crosses at u and b: NOT flip-ready ("Waiting on Kent" 50). On
     real art only 34 of about 3,000 lowercase crosses reach the lane (the rest is script or UI text); the
     lane carries no house angle for any case.
   - **Letter reach** is now card v2 block H (ROSE, `lettering_columns` OFF/ON
     pair, [`docs/sewout/card-v2-2026-10-13/`](docs/sewout/card-v2-2026-10-13/)); unsewn.
   *(measured 2026-10-12/13 — PRs #859, #863, #869, #877, #881, #885, #887, #889, #890, #891, [`docs/renders/lettering-columns-on/`](docs/renders/lettering-columns-on/), `tests/test_column_capture.py`, `tests/test_lowercase_angle.py`;
   confirmed 2026-10-13 — `config.py`; the 10-11/12 text: scope-history 10-13)*

### Waiting on Kent 45 (hairline tier) as it stood after PR #892

45. **The hairline tier — built OFF; the flip waits on a sew-out (gate 1).**
   Thread weight, the tier (PR #848), ground under strands (#850) and the
   per-strand gate (#851) are in (area 1). Card v1:
   [`docs/sewout/hairline-card-2026-10-12/`](docs/sewout/hairline-card-2026-10-12/README.md)
   (blocks A–E, 40 and 60 wt). Flipping `hairline`, `hairline_over_ground`,
   every 60/75 wt value and the 1.5 mm stitch wait on sewing it.
   *(built 2026-10-12 — `tests/test_hairline_card.py`)* **Logos (PR #872):**
   `hairline` was not flip-safe — it re-sewed 272 shapes on nine logos as 0.4 mm
   runs, 87 lost a strand (enthusiast's E read C), five new
   `ARTWORK_UNCOVERED`; no width cut separates those strokes from hair.
   **Drop guard (PR #879, built, still OFF with the tier; no flag of its own):**
   a shape whose walk would drop more than **2% of its strand length** is handed
   back whole to the ladder. **Kent RULED 2026-10-13 (via the director): keep
   the 2% share rule, not literal "any dropped strand"** (which forfeited the
   hair itself: `hair_strands` −5,637 → −152 stitches). Measured: strands
   dropped 0 on every logo bar two sub-2% survivors (0.08, 0.12 mm); hair
   fixtures lose nothing. Remaining cost: thinner outlines on gradient-lane
   logos (screenshot +8.6 mm² new `ARTWORK_UNCOVERED`) — a look for his eye. **Real
   photo (PR #876, owl_kent):** the segmenter merges bristles into ragged
   regions, so the tier barely sees strands; a line test in the strand gate
   (refuses blur rims and down) leaves 3 strands sewn, 10 dropped. **Lines route
   (PR #882, `cfg.hairline_from_lines`, OFF, needs `hairline`):** strands from
   FDoG lines over the fill ground, no fill carved — 75 strands, 0 mm² new bare
   fabric (regions: 2 strands, 2.1 mm²), +752 stitches, +45 trims; only 5 land on
   the facial bristles (31 are breast barring, not hair) — resolution (4.36
   px/mm), not tuning, is the limit; photo lanes only. Its flip is Kent's.
   **Coverage guard (PR #888, `cfg.hairline_coverage_guard`, OFF, read only under `hairline`):** with the
   drop guard ON, hairline still raised bare fabric on ordinary logos (screenshot 5.62 → 41.88 mm², new
   `ARTWORK_UNCOVERED` 8.6; drone 2.94 → 20.50). The guard hands a shape back whole when its runs would
   leave > 0.3 mm² bare AND > 0.04 mm per mm of strand (candidates from 285 shapes on 8 logos, not
   constants). It brings screenshot, drone, summit and Fremont back to within 0.3–1.5 mm² of OFF (new
   `ARTWORK_UNCOVERED` 0 on every fixture) for part of the stitch saving (screenshot −16.8% → −4.2%) and
   keeps both hair networks; it does NOT cure the "ground gap" bucket (gaulke 7.06 mm² either way, golden_tee and
   enthusiast only partly). **Ground gaps (PR #892, open and armed when written; measurement, no engine change, no
   flag):** `hairline_over_ground` closes none of it. Bare fabric is unchanged on all ten logos; 6.29 of the 6.41 mm²
   left after the guard is rim (ink within a 0.25 mm cell of the traced edge; gaulke's 0.48 mm outline stroke is 3.81
   of it), and the gradient lane's grounds are satin, which keep only a tongue. The one lever left is the run width
   (`hairline_run_width_mm`), a physical constant: a sew-out and Kent's call (gate 1). The flip is his.
   *(measured 2026-10-13 — PRs #872, #876, #879, #882, #888, #892,
   `tools/hairline_logo_bill.py`, `tools/hairline_lines_trial.py`, `tools/hairline_coverage.py` (`reach`),
   `docs/hairline-photo-trial-2026-10-12.md`)*

### Defect 51 (low-resolution line art) in full

51. **Low-resolution line art lost its fine detail at the TRACER'S GRID, not in the file — FIXED, `cfg.work_px_per_mm` ON at 8.0 (Kent's flip 2026-10-01, on renders: full-size file best, this grid second, the old grid third on every logo; None = the engine before it).** Kent's ask: bridge's "RESTAURANT" completely missing. A source under `min_px_per_mm` was enlarged to 4 px/mm and traced there; a 0.7–1.4 mm stroke is then 3–5 px, the gradient lane's superpixels hold ink and ground both, and the RAG merge — which compares MEAN colours at 26 dE00 and whose two protections are gated at 1,000 px — swallowed the letters (bridge: 67 of 81 mm² of teal held by SEEDS, **39** after the merge, six blobs sewn). The same file on a 5–10 px/mm grid keeps 64–67. Stage 1 traces line art on the working grid and `min_px_per_mm` keeps only the `INPUT_LOW_RESOLUTION` warning; photo classes keep the source line; a 2,800 px side bounds it. **Not bridge's alone:** real logos downsampled to 5 px/mm and scored against their own full-resolution digitization recover fine ink **0.64 → 0.84** on average (ENTHUSIAST 0.25 → 0.90, its tagline; Fremont's "THE"; Golke's second line), and nothing in the corpus could have shown it — bridge was the only gradient logo under 5 px/mm. **Costs:** trims rise toward the full-resolution file's own count; a blurred synthetic (`logo_whitebg` at 5 px/mm) pays 12 → 21 trims; sources at 6.5 px/mm gain little (two of five logos down). **Still open, and a different defect:** the recovered letters are 3.25–4.5 mm and each sews as ONE satin bar — present, not legible letter by letter; that is `LETTERING_TOO_SMALL`'s size question. **Not robust:** the result moves with small changes to the foreground mask (a smoother mask sent bridge's words to a grey-green cone and cost ENTHUSIAST 0.90 → 0.70), and 43 tests read on the old grid hold it (`conftest.source_line_grid`), a few of them real costs on 6–7 px/mm synthetics (the radial ramp sews 2 regions for 1). **Open, Kent's:** his verdict also says the SOURCE is the bigger lever, and `INPUT_LOW_RESOLUTION` only fires under 4 px/mm — the 5 px/mm files on his page lost to their full-size selves unwarned. Detail: `docs/fine-detail-work-grid-2026-09-30.md`. *(measured 2026-10-01 — `tools/lowres_detail.py`; `tests/test_work_grid.py`)*

### Defect 52 (browser fill across holes) in full

52. **A fill in the BROWSER engine carries thread across every hole and every notch — CLOSED in all three Studio lanes by `fillColumns` (manual 2026-10-07, shapes and image 2026-10-08, Kent's calls).** The JS tatami walk goes from one span of a split row straight to the next: a float over a long gap, a STITCH over a short one. A 40 mm manual fill with two cut-outs: **76 untrimmed floats across the 12 mm one (912 mm of thread), 20 stitches sewn across the 3 mm one.** **Hidden:** a float puts no needle point in the hole, and the Studio draws jumps only with Jumps on. **The cure:** rows cut into monotone columns (`fill.js`, a port of the Python `_columns`), and every move of every pass of the shape asked what ground it runs over, the ground being what the FILL covers. On it: unchanged. Off it by no more than a fill row (0.15 mm): sewn, never floated. Deeper: the thread goes ROUND — along the hole's own edge, or in by a strip's far end under that strip's own rows — and is cut only where there is no way round. **Audited** on 9,869 designs (three scales, all seven presets): floats that leave the fill's ground **1,154,992 → 0**; designs with thread deeper than a fill row off it **8,581 → 36**, none of the 36 across a hole. **Cost:** cuts fall from 0.89 a design to 0.25, though 3% of holed shapes keep one and a comb can gain hundreds; stitches +3.3%, at worst +37%; the travel shows, with up to nine lines of thread on a rim's worst millimetre and over 5 mm across sewn rows in one holed fill in six; a forked large fill loses center-out; the edge run of a shape with a hole or an inside corner moves 0.2 mm inside the fill. Satin shapes, and shapes with neither, are untouched. **Not sewn: no sew-out exists.** **Three builds, three independent audits.** **On** in every Studio lane (`generate.js`); the engine default stays off ("Waiting on Kent" 22). **Not built:** row stagger (tie stitches: "Waiting on Kent" 23). The sheet, the cost tables and what was seen but not changed: [`docs/renders/fill-columns-2026-10-03/`](docs/renders/fill-columns-2026-10-03/). *(measured 2026-10-03 — `tools/fill-columns-sheet.mjs`; `test/fill.test.js`, `test/digitize.test.js`; three independent audits, scope-history 10-03; flipped for manual 2026-10-07, shapes and image 2026-10-08 — `generate.js`, `generate.spec.js`)*

## Overflow moved from MASTER_SCOPE (2026-10-14, fifth pass)

Moved verbatim to make room for PRs #904-#914. The verdicts stay in MASTER_SCOPE; this is the text they replaced.

### Waiting on Kent 23 (`ties`) as it stood after the fourth pass

23. **Flip `ties` on for the browser lanes — NEW 2026-10-03, built OFF in
   both builders.** Every trim in a lettering or shape file exported from the
   Studio leaves two unlocked ends; the Python lane locks every one and always
   has. The 09-14 question was never queued here, and its lock was wrong: a
   leg of 0.8 pixels, 0.1 to 0.5 mm in practice. Now one rule for both
   builders, at 0.8 mm. Cost: lettering +3% (four letters) to +8% (a line of
   text) stitches; shapes about +1%, by how many pieces a design is in. No
   cut is added. **On shapes one lock in five lands on a stitch under 0.3 mm**
   (a fill's last row at a tip): five penetrations inside 0.3 mm. That is
   Python's rule too, and the audit's advice is to sew one first; lettering,
   under 1%, could flip alone. **Not sewn**, and neither are `machine.py`'s
   0.8 mm and three legs: a candidate for the sew-out card. A flip is
   `ties: true` at `generate.js`'s four call sites and a re-pin of every
   snapshot.
   *(measured 2026-10-03 — [`docs/lock-stitches-2026-10-03.md`](docs/lock-stitches-2026-10-03.md))*

### Waiting on Kent 24 (`fillStagger`) as it stood after the fourth pass

24. **Flip `fillStagger` on for the browser shape lanes — NEW 2026-10-03,
   built OFF.** The shape builder cuts every fill row evenly from its own
   end, so the needle holes of one row stand under the holes of the row
   before: 94% of them, and 86% head three in a line, which is the line light
   runs down (quality review 09-08 §4). One sheet, the holes as dots, as
   shipped beside staggered: `docs/renders/fill-stagger-2026-10-03/`. The
   flag puts the holes on the Python fill's shifted grid instead; 6 holes in
   148,477 still head three in a line. Row for row it is the Python rule
   (51,760 rows in thread order, equal to the bit, after an audit failed the
   first proof). Cost: +7% stitches (+2% on a plain square, +12% on a design
   in small pieces) and stitches down to 1 mm where a row meets the edge
   (2 mm today). No cut, no float and no edge moves. **What it leaves: a
   line of dashes.** A first or last step over a stitch is halved, and the
   half lands by the next row's grid hole: a pair of holes every four rows,
   about 2 mm inside a straight edge, where today there is a solid line every
   4 mm across the fill. Python's fill does the same. **Not sewn from this
   lane**; the honest choices are flip now, or sew one square and look for
   the dashes. A flip is `fillStagger: true` at `generate.js`'s three shape
   call sites and a re-pin of every shape snapshot. Lettering has no fill to
   stagger as shipped: a wide letter's fill (`satinplay.js`) sews only under
   `wideColumnFill`, off since 09-11 (8,500 Studio lettering builds, no fill
   row), and takes the stagger in whatever change flips that.
   *(measured 2026-10-03 — [`docs/renders/fill-stagger-2026-10-03/`](docs/renders/fill-stagger-2026-10-03/README.md))*

### Waiting on Kent 25 (`dedupeHoles`) as it stood after the fourth pass

25. **Flip `dedupeHoles` on for the browser shape lanes — NEW 2026-10-03,
   built OFF.** The shape builder rounds to the file's 0.1 mm, so two
   penetrations nearer than that become two stitch records on one point:
   the needle twice in one hole, about two a design in what ships (16,575
   on 8,255). The flag lays the first and not the second; no other record
   moves. Machines differ on the record. **Not sewn.** A flip is
   `dedupeHoles: true` at `generate.js`'s three shape call sites and a re-pin
   of every shape snapshot. Lettering has its own and no flag yet.
   *(measured 2026-10-03 — [`docs/sub-unit-stitches-2026-10-03.md`](docs/sub-unit-stitches-2026-10-03.md))*

### Waiting on Kent 26 (defect 57's cure) as it stood after the fourth pass

26. **Defect 57's cure — ARMED by Kent 2026-10-11 on the port's sheets (PR
   #817); built 2026-10-04.** Two of your three cures are in it (the bar's
   end; one pixel, one edge). It moves every satin shape of the browser
   lanes and no fill. Against `main` of 10-11 a hand-drawn C set to satin
   goes from 6,047 stitches with its mouth sewn solid to 304 in one column;
   a bar gains a millimetre; a star sews a third fewer stitches. Logos,
   joints and garments other than left chest were not drawn against 10-11.
   Still open:
   - **The underlay's direction — ON since 2026-10-11** (`underlayDirection`,
     built in PR #822, flipped in PR #836; item 40).
   - **Round ends, small squares and dots.** The last cross of a round end
     stands up to 0.46 mm outside it, and a square or dot up to 6 mm falls
     to the outline-split column, which leaves its ends bare. A cure for
     either is a number or a tier (dots to fill): gate 1's.
   - **Still open from 10-03: the star's tier.** Have the branch guard ask
     whether the whole rung stays inside the shape, not its midpoint; it
     would send most satin stars to fill, which nothing has sewn.
   *(ruled 2026-10-11 — defect 57; [`docs/renders/satin-spine-port-2026-10-11/`](docs/renders/satin-spine-port-2026-10-11/README.md), [`…-2026-10-04/`](docs/renders/satin-spine-2026-10-04/README.md))*

### Waiting on Kent 44 (`forbid_gap_mm`) as it stood after the fourth pass

44. **`forbid_gap_mm` flip — Kent RULED 2026-10-13: sew-out first (card v2
   block G); the flip waits on it.** Defect 47's forbid-gap half, built OFF.
   Priced (PR #874, measure and render only): at 0.8 mm over the 26 scorecard
   fixtures, bare cloth under 0.8 mm between colours 126.6 → 6.2 mm² (−95%),
   stitches +1,424 (+0.41%; bridge +3.7%), trims −14, 0 failed welds, and none of
   the findings gained. WoK 44's old "3,868 → 2,914" bridge satin figure does
   NOT reproduce (the border `S0c90443f` goes 3,383 → 3,605, +6.6%), and
   #857's bridge `ARTWORK_UNCOVERED` is gone on main. 116 of 128 pairs are
   artwork within 0.1 mm — seams, not knockout lines; a third of the strips land
   on satin shapes nobody has sewn. Options were flip at 0.8, another value, or
   hold; 0.8 mm is a physical constant (gate 1), so candidates only. **Card v2
   block G** ([`docs/sewout/card-v2-2026-10-13/`](docs/sewout/card-v2-2026-10-13/))
   sews an 8×8 mm fill and three satin bars at 0.3/0.6/1.0 mm gaps with arms
   OFF, 0.4, 0.8 (the 1.0 bar is the control). *(measured 2026-10-12/13 — PRs
   #846, #857, #874, #877, `docs/wok44-forbid-gap-bill-2026-10-12.md`;
   renders `docs/renders/claude-wok44-bridge-forbid-gap/`)*

### Quality review 2026-09-08: the three measurements and the `ties`/`fillStagger` pointers (area 1 summary)

Three measurements the ranking rests on: the curve gate reaches **2 of 29** fixtures; MARINE sews tatami at 100 mm, refused by the width cap, not by irregularity; the pro's sewn Becker files carry **7–23%** of satin crosses over the 5.0 mm cap. The browser engine locks no cut as shipped: `ties` is built OFF in both JS builders (lettering 2026-09-14, shapes 2026-10-03; "Waiting on Kent" 23). Its shape fills line their needle holes up from row to row: `fillStagger` is built OFF (2026-10-03; "Waiting on Kent" 24). **`cfg.keep_thin_strokes` is DEFAULT ON since 2026-09-13** (Kent: *"Flip it — take gaulke and becker as the price"*; False is the pre-flip engine): the instruments (`tools/thin_strokes.py`, `legibility.py`) showed the two lanes lose different width bands; ON, Fremont routed loses 3 thin strokes instead of 18, at MORE stitches since `cfg.subpixel_edges` turned the old saving into a cost. `logo_gaulke_roofing`'s black lettering is enclosed background — item 9's garment rule is what sews it. Photo classes are gated out. *(measured 2026-09-13 — `docs/thin-strokes-flip-2026-09-13.md`; detail: [area 1](docs/scope/1-auto-digitizing-quality.md#area-1-lanes-in-full--moved-from-master_scope-2026-10-08))* 

### Connected script, `SATIN_GAPS_TIGHT` and the lettering findings (area 1 summary)

**Connected script is outside the construction (measured 2026-09-30):** the letter door's aspect ceiling (1.4) refuses a script word (bridge 2.6, tires 3.8) and a word is a cluster of one; force-tagging bridge's "Bridge" moved its red-on-yellow 39.9 → 40.6 mm² — no shipped rule reads the tag for rails, pull or gaps, and 22 % of the word's gap length is under the 1.0 mm pull + thread close at 80 mm (`docs/renders/bridge-phantom-2026-09-30/script-as-lettering.json`). **The lever Kent picked, built 2026-09-30: preflight `SATIN_GAPS_TIGHT`** — a satin shape whose gaps between its own strokes are under 2 × pull + thread, with the width at which its tightest tenth clears; fires on bridge (3 shapes), golden_tee (3), tires and gaulke (tires A → B, gaulke B → C), one warn per design (scope-history 2026-09-30). **The lettering findings name the artwork's limit (2026-09-30):** under 20 source pixels per letter `LETTERING_TOO_SMALL` and `LETTERING_ILLEGIBLE` say the lettering was lost in tracing, the larger source is the lever, and — for a source under the prep's 4 px/mm floor — the width at which the grid could try (`traced_at_mm`, which the size chip jumps to); bridge's teal words, 3.5 px/mm, 118 mm predicted, back at 140 measured. 

### Kent's Fremont 81 mm Hat report as it stood after PR #902

**Kent's Fremont 81 mm Hat report — "1895" dropped out of his Studio run (2026-10-13, PRs #898, #902).** Replayed with the Studio's own request (`tools/fremont_triage.py studio_request()`: 81 mm, 6 colours, Hat, bean edge cap) it reproduces his job: 15,306 stitches against his 15,129, 3 colours, 161 shapes. **Not the Column lane (#863) and not today's guards (#890):** all six bisect arms, lane OFF and the pre-#863 core included, sew EST and 1895 identically. The causes, by stage: (1) stage 4's hole floor (`min_detail_mm`² / 4 = 0.5625 mm²) fills the 8's and 9's counters (0.30–0.52 mm²) and the white ground's hole where the "1" sits (0.47 mm²), after which stage 5's clip removes the whole "1" (`SHAPE_NOT_STITCHED`); (2) stage 7's small-shape rescue sews every glyph under `min_detail_mm`² (2.25 mm²) as a bean outline before the lane is asked — 134 of 161 shapes, EST, THE's T and the whole tagline; (3) the tagline's three A's lose counters at stage 4. **`ARTWORK_UNCOVERED` is silent in every arm: coverage cannot see illegibility**, since the thread lands on the ink in the wrong shape. Stage 0 classes this flat logo `gradient` (gated, not chased). Fremont is UNREPRESENTATIVE (it reproduces defects, it sizes nothing), and the pro sews this tagline legibly at 92.5 mm. **Kent RULED `cfg.small_glyph_keep` ON** ("Waiting on Kent" 51; built OFF in PR #902, merged; the flip PR in flight): at the replay the "1" sews, the 8 gains 2 counters and the 9 one, the three A's one each, 15,306 → 15,611 stitches, trims 44 → 46. **Open gap:** the 8's lower counter ring (2.05 mm) is under `RUN_MIN_LOOP_MM` 2.2 and sews no ring. **Live follow-ups, one defect per lane (#898):** small lettering under 2.25 mm² goes to bean outlines before the lane is asked (a new floor is a sew-out; the pro's file says what they should sew as); mixed tiers inside one word (THE: two letters satin, one run, and satin at ~0.45 mm under the cap's 0.4 mm pull closes into a blob; pull is gate 1); Column end shapes on the big letters (E arm end, N diagonal foot, M vertex join — none a lane regression, lane OFF is the same or worse); and **a legibility instrument, which must exist before any of these flips a default.** Branches pushed with no PR open on 2026-10-13: `claude/column-end-shapes`, `claude/fremont-small-lettering-tier`, `claude/legibility-instrument` (suspected in flight; their content was not read). *(measured 2026-10-13 — PRs #898, #902, `tools/fremont_triage.py`, `tests/test_fremont_triage.py`, `tests/test_small_glyph_keep.py`, `docs/renders/claude-fremont-81mm-triage/`)*

### Area 2: the `satinZigzag` paragraph as it stood after PR #901

**Studio text satin lays half the thread across a column that the Python satin does (2026-10-13, PR #901); the cure is built OFF as `satinZigzag`.** `satinplay.emitZigzag` alternated its leading rail (A1,B1,B2,A2,A3,B3), so one stitch crosses and the next steps one spacing along a rail: on a lone "l" stem **2.5 threads across per mm against 5 in the Python order and 6.7 in Ember's export** (0.3 mm per rail). The order dates from the file's first commit (2026-07-24) and no ruling chose it. `buildLetteringDesign({ satinZigzag: true })` makes one rail lead so every stitch crosses; absent or false is byte-identical (pinned). Needles per rail, the density yardstick, cannot see it. Over five font/cap cells of "Hotel Rag": stitch count unchanged (same penetrations, new order), thread +10 to +28%, trims move by one in three of five cells. Not looked at: the comb on wide split columns with the flag on, and whether browser-digitized shapes reach this emitter. A render shows open ladders off and closed columns on, but is not fabric: the default is Kent's and wants a sew-out (gate 1; "Waiting on Kent" 53). *(measured 2026-10-13 — PR #901, `test/satinplay.test.js`, `test/satinfont.test.js`)*

### Waiting on Kent 45 (hairline tier) as it stood after the fourth pass

45. **The hairline tier — built OFF; the flip waits on a sew-out (gate 1).** Thread weight, the tier (PR #848), ground under strands (#850), the per-strand
   gate (#851), a drop guard (#879, no flag; **Kent RULED 2026-10-13 (via the director): keep the 2% share rule, not literal "any dropped strand"**), a
   coverage guard (#888, `hairline_coverage_guard`), the lines route (#882, `hairline_from_lines`, photo lanes) and a strand test (#897,
   `hairline_lines_strand_test`) are in, every flag OFF. Card v1: [`docs/sewout/hairline-card-2026-10-12/`](docs/sewout/hairline-card-2026-10-12/README.md)
   (blocks A–E, 40 and 60 wt). Flipping `hairline`, `hairline_over_ground`, every 60/75 wt value and the 1.5 mm stitch wait on sewing it. Standing numbers:
   before the drop guard `hairline` re-sewed 272 shapes on nine logos as 0.4 mm runs and 87 lost a strand (#872); with both guards bare fabric is within 0.3–1.5 mm²
   of OFF on screenshot, drone, summit and Fremont, but gaulke's 7.06 mm² "ground gap" is not cured, and `hairline_over_ground` closes none of it (#892: 6.29 of
   6.41 mm² is rim; the one lever left is `hairline_run_width_mm`, gate 1). On owl_kent the line route sews 75 strands and only 5 reach the facial bristles (31 are
   breast barring); **the strand test (#897) halves the barring (31 → 15) and keeps the 5 bristles, but also drops the head-outline wisps (37 → 7) and would refuse
   dense hair (a mane)**: no shape cue separated them, so it stays OFF, and every number is in-sample on one photo at 4.36 px/mm.
   **Hairline travel (#895, MEASURED NEGATIVE):** #888's rise in thread over bare fabric on golden_tee (19.9 → 75.2 mm) is trimmed FLIGHTS, not thread; corrected, thread
   over bare is 0.94 OFF against 0.56 ON on golden_tee and never higher with hairline on any of ten logos. The real cost is **+6 trims** inside block 0's hairline
   shapes (46 → 52; screenshot +13, drone +2, which the coverage guard removes). **INSTRUMENT BLIND SPOT: `tests/test_chaining.py::_thread_bare_mm` never reads
   `run.jump` / `run.trim`, so it counts the walk-in after a trimmed jump as thread; any claim built on it, on any plan with trimmed jumps, overstates thread. Use
   `tools/hairline_travel.py`.** No fix built. The flip is his. Full prior text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-13-fourth-pass).
   *(measured 2026-10-12/13 — PRs #872, #876, #879, #882, #888, #892, #895, #897, `tools/hairline_logo_bill.py`, `tools/hairline_lines_trial.py`, `tools/hairline_coverage.py`,
   `tools/hairline_strand_test_trial.py`, `tests/test_hairline_travel.py`, `docs/hairline-photo-trial-2026-10-12.md`)*

### Waiting on Kent 32 (the four-flag contact sheet) as it stood after the fourth pass

32. **Four default-OFF flags on one contact sheet — NEW 2026-10-08 (PR #786).**
   OFF beside ON on real art, nothing sewn: `two_tone_snap` (defect 58 —
   **ON since 2026-10-11, PR #821**, so it has left this sheet's open set);
   `satin_tip_corner_gate` (defect 59, #677; Becker trims 60 → 59; shifts
   junction ends on every logo); `lettering_columns` + `lettering_words`
   (Becker 10,975 → 8,682 stitches, trims 60 → 29; the lane is **ON since
   2026-10-12**, PR #863, and `lettering_words` stays OFF, item 37); the image lane's cuts-vs-stitches patch (#697
   candidate C: summit_badge −4% stitches for 38 → 1,219 cuts; only a sew-out
   prices a cut against a stitch). *(measured 2026-10-08 — PR #786,
   `docs/renders/off-flags-2026-10-08/`; `digitizer/tools/off_flags_sheet.py`;
   flipped 2026-10-11 — PR #821; 2026-10-12 — PR #863)*

### Defect 4: the open assumption under the 3.1x (2026-09-13)

   **An open assumption under the whole 3.1x (2026-09-13):** the corpus was decoded from the pro's FILES, so it records what the file says; whether it records what the MACHINE did is unestablished — ten machine-side trim-threshold claims went to adversarial vote and **all ten were refuted**, and a machine trims only connectors longer than its own setting whatever the file requests. Not assumed either way. In our favour: **vendors publish no distance rule** (Hatch's coverage rule; a three-state override whose Off/Always bypass the mm value; Embird, sew ORDER only), so *"no single threshold reproduces this pro"* is the published model's expected shape, not an anomaly — though those rules govern needle-DOWN runs and this corpus is needle-UP. *(`docs/trade-knowledge-2026-09-13.md` §1, §6)*    

### Waiting on Kent 37: the word tagger's 50 mm misses (#889, #900)

   - **The word tagger misses glyphs at 50 mm (#889, #900), no dominant rule.** 58 of 190 expected glyphs sit in no word at 50 mm (15 at 100 mm):
     `no_region` 21 (enthusiast 14, fremont 7: segmentation, stage 0 and regions are gated), `nested` 18, `height_ratio` 5. **`nested` is a MEASURED
     NEGATIVE (#900):** 12 of its 18 are bridge's letters inside a 49.4 mm badge disc (under the 60 mm word ceiling), 4 are gaulke's house-icon window
     panes (the drop is right there), and five nesting policies each gain 8–28 glyphs only with 8–29 new strays (2x2 icon grids, wheel spokes): what
     separates bridge's line is the word's SHAPE, not containment. Nothing shipped, no flag. Fix before any `lettering_words` flip. `tools/word_tagger_trace.py`.


### Waiting on Kent 18 (faster photo reorder) as it stood after the fourth pass

18. **RESOLVED 2026-10-13 — "Faster photo reorder" (Kent): both steps merged, no flag.** `fill_travel_under_cover` was most of a cold photo run (`_reorder_for_cover` and the unsewn-ground inset buffer dominate). PR #868, byte-identical: unsewn ground memoized, about −5%. PR #871 (Kent merged it): sewn footprints kept apart, routing windowed to the length budget, the incoming order priced lazily — `owl_kent` 148 → 114 s with byte-identical stitches; drone +1 jump / +6 stitches, sunset −4 stitches, no coverage lost, exposed travel equal or lower; renders in `docs/renders/photo-reorder-fast-2026-10-13/`. *(measured 2026-10-13 — PRs #868, #871, [`docs/photo-cold-profile-2026-10-13.md`](docs/photo-cold-profile-2026-10-13.md); before: `docs/flag-runtime-bills-2026-09-12.md`)*

### Waiting on Kent 16 (hand-set sew order) as it stood after the fourth pass

16. **RESOLVED 2026-10-11 — a hand-set sew order now reaches the file (Kent
   chose option A, PR #830).** `moveBlock`/`moveShape` pin every sewable
   shape's layer, so once a customer reorders, a later tier change no longer
   gets the borders-last move — their order wins. Split/merge pieces made
   after a reorder come in unpinned; the engine half (option B, not taken)
   stays pinned red-on-fix by `test_a_partial_pin_is_still_lost_by_the_engine`.
   Triage and the `logo_whitebg` repro: scope-history 10-11, 10-12.
   *(confirmed 2026-10-11 — `digitizer/tests/test_manual_sew_order.py`;
   `DigitizePanel.spec.js`, `digitizer.spec.js`)*

### Defect 61: the twins paragraph

**Twins (PR #855):** stage 4's `max(outers)` has the same shape but is latent — 0 of 7,106 masks have a second island, guarded by a tripwire test; the forbid-gap weld's twin is fixed (PR #857); the hairline twin is fixed under `hairline` and latent — `rest_planned` now keeps every rest part over the floor and counts slivers in `CLIP_DROPPED_SLIVER` (`source: hairline_rest`), and 0 of 52 corpus rows lose ink either way (PR #861, tripwire `test_corpus_rest_pieces_lose_no_ink`).

### Waiting on Kent 37: non-letter capture, the three guards (as of PR #899)

   - **Non-letter capture — all three guards ON.** `lettering_columns_skip_blobs` and `lettering_columns_ink_link` (Kent, option A, PR #890) and
     `lettering_columns_icon_guard` (**Kent, 2026-10-13, PR #899**): skeleton nodes ≥ 24 refuse screenshot's three white truck-drawing pieces and none of 130
     hand-labelled letters. Icon guard, screenshot: lane-taken 33 → 30, stitches 8,228 → 8,295, trims 62 → 61; the other eleven measured fixtures identical.
     The 24-node, 1.0 mm and 0.40/0.95 cuts are candidate shape ratios from one corpus, not cloth constants. Scorecard baseline NOT recaptured (the screenshot row moves).


### Waiting on Kent 37: lowercase (#887, #896)

   - **Lowercase (#887, #896):** a lowercase station cross folds past 45° 1.4% of the time against 0.0% for capitals (u, b, g, m);
     `lettering_columns_fold_cuts` (OFF) is NOT flip-ready (item 50). At 80 mm the synthetic i stem (2.124 mm²) is tagged lettering but sews a RUN: stage 7's
     small-shape rescue (`routes_to_run`, under `min_detail_mm`² 2.25) fires before the lane is asked; `cfg.lettering_columns_small_stem` (OFF, item 52) keeps
     it for the lane. The i DOT (0.446 mm²) is dropped separately, by `RUN_MIN_LOOP_MM` 2.2 (a cloth value).


### Evaluation harness: the density/flow instrument (PR #847)

**A density/flow instrument coded from his own notes finds no new signal (PR #847):** of 14 candidates read from the stored stitch records, the one clearing chance on both statistics, `jumps_per_1000`, restates trims (kappa +0.72 against the trim picks); density per area does not track his picks (#842's "denser" was stitch COUNT); `flow_circvar` is a lead from one sitting; and "each stitch crosses the whole stroke", coded as more long stitches, came out REVERSED — he picks the side with fewer stitches over 4 mm. Its proposed fresh blinded sitting waits on logos Kent supplies ("Waiting on Kent" 42). *(measured 2026-10-12 — PR #847, [`docs/density-flow-instrument-2026-10-12.md`](docs/density-flow-instrument-2026-10-12.md))* 

### Waiting on Kent 22 (`fillColumns` lanes) as it stood after the fourth pass

22. **RESOLVED 2026-10-08 — `fillColumns` ON in all three browser lanes**
   (manual 10-07; basic shapes and the image lane 10-08, Kent's call with
   the price in front of him). Image lane: floats off the fill 188,952 → 484,
   cuts 3,714 → 3,208, stitches **+10.4%** (+29.7% worst); shapes +1.8%.
   **Kent's standing ask:** the next ten digitized images shown to him carry
   the off/on float picture (`tools/fill-columns-image-sheet.mjs`; memory
   `fill-columns-float-pictures-2026-10-08`). The image lane's price — HOLD:
   four cheaper walks each failed (candidate C is on #786's sheet, item 32).
   None of it is sewn. Full tables: the price doc; scope-history 10-12.
   *(measured 2026-10-08 — PR #697, `docs/renders/fill-columns-lanes-2026-10-08/price.md`)*

### Waiting on Kent 21 (`bean_letter_max_stroke_mm`) as it stood after the fourth pass

21. **`bean_letter_max_stroke_mm` at 1.0 — JUDGED 2026-10-03, stays OFF.**
   Small traced lettering sewn as bean runs along the skeleton of its SOURCE
   INK instead of satin blobs. On the labelled page Kent put today's satin
   ahead on five of six logos and called bridge both bad; his reason is the
   line's WEIGHT — *"little worms"*, *"aren't thick enough"*, *"to skinny"* —
   while granting fremont's path reads cleaner. Open, and his: a heavier line
   on the same path, or drop it. The render draws three passes as one thread,
   so "too thin" is not yet separated from the picture (`suspected`); gate 1
   holds a 3-pass bean on knit as `pending sew-out`.
   *(judged 2026-10-03 — `docs/eye-pairs-2026-10-03/kent-notes.json`)*

### Defect 57: its costs and a star's centre, standing (as of 2026-10-11)

**Its costs, standing.** A satin bar's centre-run underlay ended at the far end from where its column starts (a needle-up move a median 49 mm on left chest) — cured by `underlayDirection`, ON since 2026-10-11 (PR #836). The last cross of a round end stands up to 0.46 mm outside it. A square or dot up to 6 mm has no skeleton and takes the outline-split fallback, which starts 12% in from each end (a 6 mm square: 92% covered to 85%, stitches to 8.8 mm). **A star's centre, standing.** The longest stitch of a satin star is a median 21 mm, up to 100 mm, cast arm to arm across the centre; its strokes are joined by needle-up moves (a median 139 mm a star). The branch guard sends it there: an even-pointed star splits tip to tip into equal halves, so twelve arms pass as ONE column. 

### Waiting on Kent 39 (`bg_structural`) as it stood after the fourth pass

39. **`bg_structural` flip — waits on real tonal art, NEW 2026-10-11.** Area 1's
   two stage-1 background defects, fixed OFF. Before any flip:
   `photo_chrome_specular` changes verdict ABSENT → background (read as a fix),
   and `test_preflight` uses it as the full-bleed guard, so that guard moves
   to another fixture first. Its three constants were chosen on mostly
   synthetic fixtures; ON can change `px_per_mm` (summit traced on 949 px, not
   900). *(measured 2026-10-11 — PR #825, `tests/test_bg_structural.py`)*

### Waiting on Kent 41 (`subpixel_edges_min_px_per_mm`) as it stood after the fourth pass

41. **`subpixel_edges_min_px_per_mm` — LEFT UNSET (Kent 2026-10-11); open: the
   corner-run flip.** A floor under the native edge read clears Becker's
   outline reversals at 1.8 px/mm (7.1 → 0.0 per 100 mm) but returns the
   0.68 mm source-pixel staircase the 09-18 flip fixed (right-angle turns
   26.5 → 81.3 per 100 mm), which the reversal count cannot see. The
   reversals' own cure is BUILT OFF as `subpixel_corner_runs` (PR #834:
   7.1 → 0.9 per 100 mm, turns 26.5 → 20.1, area 1); flipping it is his. *(measured
   2026-10-11 — PRs #826, #834,
   [`docs/subpixel-res-gate-2026-10-11.md`](docs/subpixel-res-gate-2026-10-11.md))*

### Closed defect 54 in full (as of 2026-10-03)

54. a ring that says a point TWICE running (handed over CLOSED: its first point again at the end) got a WEDGE from the BROWSER builder's `offsetRing` — FIXED 2026-10-03 (`distinctCorners`, `digitize.js`: the corners said once are what `offsetRing` moves and what `isConvexRing` reads). The repeat is an edge of no length; its two ends were each moved along one neighbour's normal, the first by three times the distance. Under a preset the fill is sewn to the moved rings, so the wedge was sewn: a 40 mm box on terry was filled 1.8 mm outside the drawing at its first corner, where 0.6 is right; a closed hole and a closed island the same, and with `fillColumns` the edge run. **Exported stitches change for a ring that says a point twice, under a preset or with `fillColumns`, and for no other** (4,536 outputs on rings that do not: identical). **No Studio lane hands over an EXACT repeat**: none in 24,985 rings from basic shapes, the image lane and trace import, and a hand-drawn one is refused as crossing itself. `parseSVG` and `fonts.js` do hand them over, and nothing in the Studio calls either. **A NEAR repeat is another matter and was in the Studio's reach: defect 55 (its gesture cured, its offset open).** Older than every flag. Left: the auto angle, a satin shape's centre run, the edge run drawn toward the centroid and the order of a colour's shapes are read off the POINTS, so a closed ring's underlay still differs. Independently audited: the fix held, five sentences of its record did not and are corrected. `tools/closed-ring-census.mjs`, `test/digitize.test.js`. Full text: scope-history 10-03.

## Overflow moved from MASTER_SCOPE (2026-10-14, sixth pass)

Moved verbatim from `MASTER_SCOPE.md` by the sixth-pass refresh (PRs #919-#928) to keep the file under its word budget. Each entry stood as written after PR #917 / the fifth pass; the live text in MASTER_SCOPE carries the verdict and the current numbers.

### Waiting on Kent 51 (`small_glyph_keep`) as it stood after PR #917

51. **RESOLVED 2026-10-14 — `cfg.small_glyph_keep` is ON (Kent, option A, 2026-10-13: flip now, the sew-out block follows; PR #908 merged,
   `config.py` default True).** Built OFF in PR #902: keeps a rescued small shape's holes down to 0.16 mm² (stage 4) and plans a wholly
   clipped one on its artwork (stage 5). Fremont's "1895" at 81 mm on a Hat goes from "098" to "1895" (15,306 → 15,611 stitches, trims
   44 → 46); 4 of 5 corpus logos byte-identical, drone gains one 0.313 mm² speck (+21 stitches, +1 trim). **The price, measured after the
   flip (#908):** it does not make the tagline legible — the A counters are in the plan and the 0.4 mm thread sews over them (0.02 of each
   left bare), so at 81 mm 3 of 4 tagline counters bare-unplanned → 0 of 4, all shut, and at 92.5 mm none stays open (3 were with the flag
   OFF). The tagline needs `small_lettering_skeleton` (item 54). Both floors it moves are candidates (gate 1); card v3 block N (#910) sews OFF
   against ON. Open gap: the 8's lower counter (a 2.05 mm ring, under `RUN_MIN_LOOP_MM` 2.2). Detail: area 1, "Kent's Fremont 81 mm report".
   *(ruled 2026-10-13 — PRs #902, #908; measured 2026-10-13/14 — #905, #908, `tests/test_small_glyph_keep.py`)*

### Waiting on Kent 53 (`satinZigzag`) as it stood after PR #917

53. **RESOLVED 2026-10-13 — Kent ruled `satinZigzag` ON for Studio text satin (PR #904, merged 2026-10-14, on a
   before/after render; not sewn).** One rail leads so every stitch crosses (area 2); `satinZigzag: false` gives the old
   stream. **A cost the ruling's picture did not show:** where split satin fires the return leg is a full cross with its own
   split penetrations, so `manga_impact` "AB" goes 12,492 → 21,070 stitches at 198 mm and 27,033 → 48,079 on a Full Back
   (+69% / +78%), no segment over a DST record, worst sewn segment 4.96 mm either way. Small text: same stitch count,
   +10 to +28% thread. PR #904's body says the ruling rested on a small-text picture and that auto-merge was not to be armed
   until Kent had seen the big-text bill; it is merged, and whether he saw that bill is `suspected` not (not recorded).
   Sew-out owed (gate 1). *(measured 2026-10-13 — PRs #901, #904, `test/satinplay.test.js`)*

### Waiting on Kent 55 (Column lane ends) as it stood after PR #917

55. **Column lane ends: `lettering_columns_square_ends` + `lettering_columns_inside_connectors` — Kent RULED ON; the flip is in
   flight (`claude/letter-ends-on`, no merged PR when this was written).** Built OFF in PR #907 (`square_ends`) and #912
   (`inside_connectors` plus three refinements: N foot mitre, M vertex corner, thin-cross reach). Fremont 81 mm Hat: ends more
   than 0.10 mm past their face 36 → 0 (worst stub 0.41 → 0.048 mm), the M's travel across its counter gone, the N foot's cap
   39.9° → under 5°; six fixtures, ends past their face 15–55 → 0–2 under #907 and 0 under #912. **Costs standing:** Becker gains 3
   trims (22 → 25: three in-letter hops with no route on the letter now jump), bare outline stays above OFF on fremont 92.5
   (+0.11 mm²) and drone (+0.31 mm²), becker stitches 6,011 → 6,150. 45°, the 8°/45° mitre bounds, 10° and 0.10 mm are candidates
   sized on no fixture. Card v3.1 blocks X (Fremont E, M, O, N) and B (Becker MARINE) check it on cloth. *(ruled 2026-10-13 — Kent,
   relayed by the director; measured 2026-10-13/14 — PRs #907, #912, `tools/column_ends.py`, `tests/test_column_ends.py`)*

### Waiting on Kent 56 (true-size small lettering options) as it stood after PR #917

56. **True-size small lettering options — built OFF, none sewn; #909 KEPT (Kent) after it merged in error.** `small_text_cap_mm`
   (#909) enlarges a small line to a cap height; Kent: *"you can't change the font size for the final product"*, so it stays OFF
   and is not the route. The true-size route is `small_text_restore_mm` + `bean_letter_stitch_mm` (#911: retrace the line's
   letters from the source raster so counters survive, adopt untagged letters, a station pitch for bean letters only) and
   `bean_letter_serif_mm` (#914: trim slab-serif hooks off bean spines). Hotel Fremont 92.5 mm with restore 3.0,
   `bean_letter_max_stroke_mm` 0.4, pitch 0.45 and serif 0.45: the date reads "EST 1895" in the render (hooks kept: "B8T 1895";
   untreated: about "EST 1093"), 17,378 → 17,402 stitches, 52 → 54 trims. #909 reads "EST 1895" too (17,379 stitches, trims 52 → 42), by redrawing the line larger. That is four values for one render of one logo at one size
   (3.0, 0.4, 0.45, 0.45 and 50° are candidates, gate 1); `bean_letter_max_stroke_mm` 0.4 also turns the tagline into
   centrelines, unlooked-at elsewhere. **Overlap with item 54:** #913's skeleton run attacks the same problem another way;
   the two have not been compared on one render and only one should be on: his. *(measured 2026-10-13 — PRs #909, #911, #914,
   `tests/test_small_text.py`)*

### Waiting on Kent 37: the `SPEC_ARMS` bullet (retired by PR #926)

   - **Eye-pairs `SPEC_ARMS` still list `lettering_columns` as an OFF arm** (`tools/eye_pairs/pairs.py`), now equal to the base; waits on a tidy-up.

### Waiting on Kent 45: hair reach and chaining as they stood after PR #917

   `tools/hairline_travel.py`.** **Hair reach (#915, measure only, merged):** the Studio sends `owl_kent` down `gradient`, which the line route excludes; forced there it sews 52 strands, 4 in the bristle box, +36 trims, bare 0.0. The bristle box holds 1-6 strands across 90-250 mm and work grids 4-16 px/mm, and a bigger DESIGN pushes it DOWN (4 at 127 mm, 2 at 180, 1 at 250). On drawn hair the line route REPLACING the region tier regresses (hair_strands 28,014 → 33,448 stitches, +23 trims). Proposed, not built: `cfg.hairline_lines_gradient` OFF as a supplement; expected value small. **Chaining (#917, merged, `cfg.hairline_lines_chain` OFF):** a strand-to-strand hop of 8 mm or less sews needle-down only over laid thread; owl_kent 9 hops, trims 421 → 418, corrected bare thread unchanged, a no-op with the strand test; 3 of 4 hops differ by 12 L* or more from the fill (a short visible line); the 8 mm is a candidate (gate 3). The flip is his, after the card. Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass).

### Waiting on Kent 45: standing numbers as they stood after PR #917

   (blocks A–E, 40 and 60 wt). Flipping `hairline`, `hairline_over_ground`, every 60/75 wt value and the 1.5 mm stitch wait on sewing it. Standing numbers:
   with both guards bare fabric is within 0.3–1.5 mm² of OFF on screenshot, drone, summit and Fremont, but gaulke's 7.06 mm² "ground gap" is not cured
   (#892: 6.29 of 6.41 mm² is rim; the one lever left is `hairline_run_width_mm`, gate 1). On owl_kent the line route sews 75 strands and only 5 reach the
   facial bristles; **the strand test (#897) halves the barring (31 → 15) and keeps the 5 bristles, but drops the head-outline wisps (37 → 7) and would
   refuse dense hair**, so it stays OFF (in-sample, one photo at 4.36 px/mm). **Hairline travel (#895, MEASURED NEGATIVE):** the rise in thread over bare
   fabric is trimmed FLIGHTS, not thread; the real cost is +6 trims inside block 0's hairline shapes. **INSTRUMENT BLIND SPOT:
   `tests/test_chaining.py::_thread_bare_mm` never reads `run.jump` / `run.trim`, so it counts the walk-in after a trimmed jump as thread; use

### Waiting on Kent 47 (`small_print_floor`) as it stood after PR #917

47. **`small_print_floor` flip — waits on card v2 block F (gate 1).** PRs
   #873, #878, #880, flag OFF, OFF byte-identical (md5 pins): at 3–4 mm caps a
   counter sewn shut is the worst defect, so the flag keeps counters stage 4
   drops and holds penetrations half a laid width off them, in the Column lane
   (#873), now also the run and fill tiers (#878) and with no Column-lane
   stitch over a counter (#880). Measured (40 wt render, not cloth): synthetic
   BOARD at 3 mm counters shut 8/10 → 2/10, Fremont's tagline 0/4 shut with
   zero stitches over a counter at 3–5 mm (the A's float-hair regression found
   in #878 is fixed in #880). Costs: dust 0.103 → 0.131 at 3 mm, +25–52 stitches.
   Still shut: the synthetic 0's two counters beside the slash, golden_tee's O
   at 3 mm. **At Kent's 81 mm hat replay it does the opposite (#905):
   all four Fremont tagline counters shut** (0.50–0.85 mm across against a 0.40 mm thread; bare share 0.10–0.24 each; +150
   stitches, +2 trims) — it is a counter flag, not a tier flag, and at 92.5 mm it keeps the three A's open. Counter floor (one laid width) and hold are candidates; block F
   sews BOARD at 4 and 3 mm, OFF/ON. *(measured 2026-10-13 — PRs #873, #878,
   #880, #877, `tools/small_print.py`, `tests/test_small_print.py`)*

### Waiting on Kent 54 (`small_lettering_skeleton`) as it stood after PR #917

54. **`small_lettering_skeleton` — built OFF (PR #913); the flip and the floor are his, after the card v3.1 sew-out (gate 1).**
   Small lettering at or under one laid thread wide sews as ONE run down each letter's middle instead of a bean outline.
   Fremont 81 mm Hat replay with the stitch floor at 0.73 mm (`small_lettering_skeleton_floor_mm`): 11 of the tagline's 13
   glyphs take it, sewn width 0.47–0.73 → 0.42–0.43 mm, stitches 15,306 → 14,886, trims 44 → 44, mean glyph legibility 0.844 →
   0.916; at the default 1.0 mm floor 6 take it (15,124). EST (1.35 mm caps) and THE are declined and unchanged. **Counter
   trade-off:** a 0.40 mm thread round a 0.5 mm counter leaves 20–40% bare (P 0.15 → 0.38). OFF is md5-pinned on the three
   flat-lane goldens; ON leaves becker, bridge, golden_tee and drone identical and changes enthusiast's "ENTERPRISES INC" (2,428 →
   2,102 stitches at 0.73), where the R of PRISES reads closer to an A. Whether 0.73 mm stitches hold (shred, looping) is `MIN_STITCH_MM` 1.0's own question: 0.73, 1.0 and the 10% shape
   tolerance are candidates. Card v3.1 blocks S and E2 sew it (PR #916, merged; handed to Kent). *(measured 2026-10-13/14 — PR #913,
   `tools/small_lettering_skeleton.py`, `tests/test_small_lettering_skeleton.py`)*

### Area 1, Kent's Fremont 81 mm Hat report: what the existing flags do at 81 mm (#905), as it stood after PR #917

**What the existing flags do at 81 mm (#905, measure only):** `small_print_floor` is a counter flag, not a tier flag, and it SHUTS all four tagline counters (item 47); `lettering_columns_small_stem` does nothing here; `small_glyph_keep` (now ON) keeps counters in the plan and the thread sews over them (item 51); size alone fixes THE's tiers (the T clears 2.25 mm² at 92.5 mm). The tagline and EST strokes (0.22–0.30 mm) are thinner than one thread, so every run construction sews them 1.6–3.2× wide; THE's blob is the hat preset's 0.4 mm pull (item 57). *(measured 2026-10-13 — PR #905, `tools/fremont_small_lettering.py`, `tests/test_fremont_small_lettering.py`)*

### Area 1, Kent's Fremont 81 mm Hat report: the legibility instrument (#906), as it stood after PR #917

**A legibility instrument exists (#906, `tools/glyph_legibility.py`) and it is NOT a gate.** Per glyph it reads the sewn thread (strokes, clean, counters, space) at 20 px/mm; tesseract on each glyph alone is a second reader, not part of the number. On the lane's own output the `+space` reading ranks Kent's four red boxes below five legible words with AUC 1.000 (exact permutation p 0.008, margin +0.132; margin +0.073 to +0.170 across the space radius and a 0.32 mm thread). **It does NOT hold when the pro's own THE counts as legible** (AUC 0.885 [0.692, 1.0], margin −0.249: the pro's THE reads 0.080 / 0.042), and its failure-mode headline (`legibility`) ranks them the wrong way round (AUC 0.10): never quote that one. *(measured 2026-10-13 — PR #906, `tests/test_glyph_legibility.py`, `docs/renders/claude-legibility-instrument/`)*
### Waiting on Kent 22 (`fillColumns` lanes) as it stood after PR #917

22. **RESOLVED 2026-10-08 — `fillColumns` ON in all three browser lanes** (manual 10-07; shapes and image lane 10-08, Kent's call with the price in
   front of him). Image lane: floats off the fill 188,952 → 484, stitches **+10.4%** (+29.7% worst); shapes +1.8%. **Kent's standing ask:** the next ten
   digitized images shown to him carry the off/on float picture (`tools/fill-columns-image-sheet.mjs`; memory `fill-columns-float-pictures-2026-10-08`).
   None of it is sewn. Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass). *(measured 2026-10-08 — PR #697, `docs/renders/fill-columns-lanes-2026-10-08/price.md`)*

### Waiting on Kent 26 (defect 57's cure) as it stood after PR #917

26. **Defect 57's cure — ARMED by Kent 2026-10-11 on the port's sheets (PR #817); built 2026-10-04.** It moves
   every satin shape of the browser lanes and no fill: a hand-drawn C set to satin goes from 6,047 stitches with its
   mouth sewn solid to 304 in one column. Still open: the underlay's direction (**ON since 2026-10-11**, PR #836, item 40);
   round ends, small squares and dots (a number or a tier, gate 1); the star's tier (ask whether the whole rung stays
   inside the shape; most satin stars would go to fill, which nothing has sewn). Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass).
   *(ruled 2026-10-11 — defect 57; [`docs/renders/satin-spine-port-2026-10-11/`](docs/renders/satin-spine-port-2026-10-11/README.md), [`…-2026-10-04/`](docs/renders/satin-spine-2026-10-04/README.md))*

### Waiting on Kent 42 (the blinded sitting) as it stood after PR #917

42. **A fresh BLINDED sitting — Kent RULED 2026-10-13: source 4+ flat lettering logos FIRST, then rebuild
   to 48–60 pairs and sit.** The art is his to supply. PR #847 proposed it (new flat-art logos, sides
   randomised, arm names hidden, directions written down first, `long_share` LOWER). PR #886 built the
   machinery and a 27-pair kit from the six logos that qualify (19 live pairs, 8 controls; pre-registered
   before any render; `analyse` prints kappa with 95% bootstrap CIs and n, never a raw agreement). Three of
   its six arms pass the manipulation check (`design_angle`, `split_7mm`, `lane_off`); the density-only
   arm, the trims-only arm and `per_stroke` FAIL it, since there is no satin-density knob and the trims
   flags move whole-design trims by under 0.5 per 1000 stitches. At about 27 pairs a sides-only kappa
   interval is near ±0.5, so the kit alone licenses nothing. Once the art arrives the rebuild is one
   `logos[]` edit and about 25 min of CPU. **Rulings: no `mfab_lc` / `toat_beanie` extras (the same designs
   at another crop), no satin-density knob.** *(ruled 2026-10-13 — PRs #847, #886,
   [`docs/eye-pairs-2026-10-13/wok42/README.md`](docs/eye-pairs-2026-10-13/wok42/README.md),
   [`docs/density-flow-instrument-2026-10-12.md`](docs/density-flow-instrument-2026-10-12.md))*

### Waiting on Kent 44 (`forbid_gap_mm`) as it stood after PR #917

44. **`forbid_gap_mm` flip — Kent RULED 2026-10-13: sew-out first (card v2 block G; card v3's G is the same block,
   #910); the flip waits on it.** Defect 47's forbid-gap half, built OFF. Priced (PR #874, measure and render only): at
   0.8 mm over the 26 scorecard fixtures, bare cloth under 0.8 mm between colours 126.6 → 6.2 mm² (−95%), stitches
   +0.41% (bridge +3.7%), trims −14, 0 failed welds. 116 of 128 pairs are artwork within 0.1 mm (seams, not knockout
   lines). 0.8 mm is a physical constant (gate 1), so candidates only; block G sews an 8×8 mm fill and three satin bars at
   0.3/0.6/1.0 mm gaps with arms OFF, 0.4, 0.8. WoK 44's old "3,868 → 2,914" bridge figure does NOT reproduce. Full text:
   [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass). *(measured 2026-10-12/13 — PRs #846, #857, #874, #877, `docs/wok44-forbid-gap-bill-2026-10-12.md`)*

## Overflow moved from MASTER_SCOPE (2026-10-14, seventh pass)

Moved verbatim from `MASTER_SCOPE.md` by the seventh-pass refresh (PRs #930-#940) to keep the file under its word budget. Each entry stood as written after PR #928; the live text in MASTER_SCOPE carries the verdict and the current numbers.

### Waiting on Kent 53 (`satinZigzag` size cap) as it stood after PR #928

53. **RESOLVED 2026-10-14 — Kent has seen the big-text bill and RULED (~00:40 CDT, relayed by the VP): `satinZigzag` stays ON only below a column-width cap.**
   The cap is about 8 mm, the wide-column split point, a NAMED TUNABLE config value; above it the old stream. Big text goes back to pre-#904 counts (198 mm "AB"
   12,492; Full Back 305 mm 27,033), small text is byte-identical. **Ruled, build in flight** on `claude/satin-zigzag-size-cap`, NOT merged: until it merges the
   shipped default (#904) is ON at every size and big text still pays +69% / +78% (12,492 → 21,070; 27,033 → 48,079). Sew-out owed (gate 1).
   *(ruled 2026-10-14 — Kent; measured 2026-10-13 — PRs #901, #904, `test/satinplay.test.js`)*

### Waiting on Kent 54 (`small_lettering_skeleton`) as it stood after PR #928

54. **`small_lettering_skeleton` — built OFF (PR #913); the flip and the floor are his, after the card v3.1 sew-out (gate 1).**
   Small lettering at or under one laid thread wide sews as ONE run down each letter's middle instead of a bean outline. Fremont 81 mm Hat replay, stitch floor 0.73 mm:
   11 of the tagline's 13 glyphs take it, sewn width 0.47–0.73 → 0.42–0.43 mm, stitches 15,306 → 14,886, trims 44 → 44, mean glyph legibility 0.844 → 0.916 (6 glyphs
   at the default 1.0 mm floor). **Counter trade-off:** a 0.40 mm thread round a 0.5 mm counter leaves 20–40% bare. ON leaves becker, bridge, golden_tee and drone
   identical and changes enthusiast's "ENTERPRISES INC" (2,428 → 2,102 stitches). 0.73, 1.0 and the 10% tolerance are candidates (`MIN_STITCH_MM` 1.0's own question).
   Card v3.1 blocks S and E2 sew it (PR #916, handed to Kent). Prior text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-sixth-pass). *(measured 2026-10-13/14 — PR #913,
   `tools/small_lettering_skeleton.py`, `tests/test_small_lettering_skeleton.py`)*

### Waiting on Kent 56 (true-size small lettering) as it stood after PR #928

56. **True-size small lettering options — built OFF, none sewn; #909 KEPT (Kent) after it merged in error.** `small_text_cap_mm` (#909)
   enlarges a small line; Kent: *"you can't change the font size for the final product"*, so it stays OFF and is not the route. The true-size
   route is `small_text_restore_mm` + `bean_letter_stitch_mm` (#911) and `bean_letter_serif_mm` (#914). Hotel Fremont 92.5 mm with all four set:
   the date reads "EST 1895" in the render, 17,378 → 17,402 stitches, 52 → 54 trims; four candidate values (gate 1) for one render of one logo at
   one size. **Overlap with item 54:** #913's skeleton run attacks the same problem another way; the two have not been compared on one render
   and only one should be on: his. Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-sixth-pass).
   *(measured 2026-10-13 — PRs #909, #911, #914, `tests/test_small_text.py`)*

## Eighth pass: the small-lettering follow-ons (PR 945-956)

Full text of MASTER_SCOPE "Waiting on Kent" 59, moved here on 2026-10-14 (eighth pass) so the live file keeps its headroom. Every claim carries the pointer it had; MASTER_SCOPE holds the verdicts.

59. **Small-lettering follow-ons (2026-10-14): three built OFF and outside the switch, one instrument, one trace. Fremont is UNREPRESENTATIVE: it reproduces defects and sizes nothing; every value is a gate-1 candidate and nothing is sewn.** Full numbers: [area 1](docs/scope/1-auto-digitizing-quality.md#eighth-pass-the-small-lettering-follow-ons-pr-945-956). **(a) `bean_letter_counter_hold_mm` (PR #952, merged, OFF; not in the switch, putting it there is Kent's call):** under the switch Fremont 81 mm Hat's 8 sews both counters shut by #905's 50%-bare rule (bare 0.33 / 0.28: 0.22 mm of ink under a 0.40 mm thread), worse than main's 1 of 2 open. The hold moves each spine point near a counter under 1.0 mm across to the ink pixel furthest from every small counter. At 0.25: the 8 reads 0.627 / 0.544 (open), the 9 0.385 → 0.674, the tagline's counters 1 of 4 → 4 of 4, EST / 1895 / THE / tagline legibility unchanged at 81 mm (15,330 → 15,338 stitches, 41 trims). **Cost:** a held letter sews up to about 0.1 mm wider outside; at 92.5 mm 1895 reads 0.960 → 0.951; 8 of 17 corpus designs change, none gains `ARTWORK_UNCOVERED`. Hold 0.2 puts the 8's upper counter exactly on the 0.500 line. **Owes a sew-out block on the next card: switch vs switch + hold 0.25, EST 1895 at 81 mm** (is a 0.1 mm wider outside worse than a shut counter?). **(b) `bean_letter_passes` (PR #950, OFF):** the passes along each spine (`None` = `BEAN_PASSES` 3, byte-identical), built for Kent's 'what if we stitch on top of the other stitch for coverage'; `docs/sewout/card-passes-2026-10-14/` is one 40 wt DST (718 stitches, 35.2 × 26.8 mm, 14 trims, pystitch read-back 718/718) with Fremont's THE and 1895 at 1 / 2 / 3 passes (THE 68 / 106 / 152 stitches, 1895 54 / 89 / 124). **Card v3's pin of `small_glyph_keep` OFF is stale** (default ON since #908): its N block is still a valid A/B, its F3 and T 'today' arms are not. **(c) `small_letter_ties` (PR #956, merged, OFF, not in the switch):** no tie-in where the run already sews its opening stitch 3 times, a walk-in for single-pass runs, a walk-back tie-off cut on its own thread. Lock thread piled on the ink, bean and skeleton runs only: **−65% at 81 mm, −64% at 92.5 mm** (all letter-colour locks on the ink −42% / −45%, the rest the tagline's '|' separators, run tier, out of scope); trims unchanged (41 / 54), stitches 15,330 → 15,297 and 18,675 → 18,640; thread footprint identical to 1e-5 mm². The bar 'legibility not lower' misses by 0.001 on 1895 and one OCR read on EST at 92.5, a stitchviz paint-order effect with no thread moved. Six of nine logos byte-identical; the other three change small letters only. **Owes a card block:** the same 3 mm cap letter with the bounce lock vs `small_letter_ties`, pull each tail by hand after a wash and see whether it unravels. **(d) Trace of the 1, 5, THE's E and the tagline S (PR #953, measure only, armed, OPEN):** in none of six glyph readings does a needle point of the glyph's own runs land off its ink (0 of 26 / 33 / 26 / 39 / 80 / 52), so **the 1's OCR miss is the instrument's window, not the engine:** a black fill 0.69 mm away puts foreign thread in `glyph_legibility`'s window, and the 1's own thread reads I at 81 mm (filament width) and 1 at 92.5 mm and at half width. The 5 at 81 mm is a bay filled by thread width (64% covered); at 92.5 mm the 5 and the tagline S have no geometric cause and read S, 8, S, S across four masks: **single-glyph OCR is unstable, judge these structurally** (bays at the 50% rule, no thread hole, needle points on ink). THE's E at 92.5 mm: the instrument's 20 px/mm render closes a 0.13–0.14 mm slit between a serif tick and the middle arm into a false counter. Proposals, none built: a window restricted to shapes that own a glyph of the word; bay-bounding legs held off the bay; a free end pulled back about 0.13 mm. **(e) `cfg.preflight_glyph_metric` (PR #945, merged, OFF):** the per-glyph read of `tools/glyph_legibility.py` moved verbatim into `digitizer_core/glyph_read.py` (tool output byte-identical) behind preflight metrics on text-tagged shapes (`glyph_legibility_min` / `_mean`, `counters_shut`, per-word rows); OFF writes no key, ON changes no finding, score or grade (Kent 2026-10-02: metrics only). Fremont 81 mm Hat: `counters_shut` 5, mean 0.804 over 38 glyphs. **It costs 2.6 to 2.8 s per job, over the 2 s target, which is why it ships OFF.** *(measured 2026-10-14 — PRs #945, #950, #952, #953, #956, `tests/test_preflight_glyph_metric.py`, `tests/test_bean_counter_hold.py`, `tests/test_small_letter_ties.py`, `tests/test_bean_glyph_trace.py`)*

## Ninth pass: overflow moved from MASTER_SCOPE (2026-10-15)

Moved verbatim from `MASTER_SCOPE.md` by the ninth-pass refresh (PRs #953-#962) to keep the file under its word budget. Each paragraph stood as written after PR #956; the live text in MASTER_SCOPE carries the verdict and the current numbers.

### Item 45, the hairline tier: the #895 to #942 paragraph as it stood after PR #956

   Sampling noise ~0.1 mm per stretch: do not read single-digit `exposed` counts. `rows.json` of `claude-hairline-bare-travel` still carries the old sampling. **Hair reach (#915) and chaining (#917):** the Studio sends `owl_kent` down `gradient`, which the line route excludes; forced there it sews 52 strands (4 in the bristle box, which a bigger DESIGN pushes down: 4 at 127 mm, 1 at 250), +36 trims; the line route REPLACING the region tier regresses on drawn hair. `hairline_lines_chain` (OFF) saves 3 trims on owl_kent (421 → 418), bare thread unchanged; its 8 mm limit is a candidate. **RULED 2026-10-14, 12:15 CDT (VP relay of Kent): `hairline_lines_chain` stays OFF until a sew-out; the chaining block goes on card v3.2.** **Card v3.2 (PR #949, merged) carries it as block O** (owl_kent 127 mm, 40 wt, the 14 × 8 mm window of the chain-ON plan with the most hops; 13,355 stitches, 148 trims, 93.8 × 97.0 mm in a 4 × 4 hoop): whole owl chain OFF / ON 35,446 / 422 → 35,427 / 419 stitches / trims, 9 hops sewn needle-down (22.8 mm, 0.0 mm over bare), thread over bare fabric 751.46 mm in both arms; the window's 3 hops (longest 3.14 mm) replace 2 floats and 1 cut with none, so **the 8 mm cap is not tested above 3.14 mm** and stays a candidate. **`cfg.hairline_lines_gradient` (PR #942, merged, OFF):** the line route as a SUPPLEMENT on the gradient lane, acting only with `hairline`, `hairline_from_lines` and `hairline_lines_strand_test` all on; it refuses a line the region tier already sewed (≥ 0.5 of its length in the shapes the tier walked) and a line on a stroke shape (2A/P ≤ 5.0 mm) whose thread is within 12 L* of it. owl_kent via the Studio route (127 mm, 40 wt): 9 region + 20 supplement strands (4 in the bristle box), stitches 66,119 → 66,347, **trims 273 → 291 (+18)**, 0.0 mm² new bare over the region tier; drawn hair (`hair_strands`, `hair_fine`) byte-identical. **The catch is the logos: 3 of 9 move — drone +17 trims (19 strands), screenshot +8, golden_tee +3 — thin detail inside rendered art, not hair, 0.0 mm² new bare; a flip adds 3% to 13% trims there.** The 0.5 shares, 12 L* and 5.0 mm are candidates (the owl side's margin is 5.8 against 5.0); the supplement with `hairline_lines_chain` was not measured; the flip is Kent's, after card v1. **Fur regions (#925, `cfg.hair_regions_directional`, OFF) — MEASURED NEGATIVE:** all 28 corpus rows are byte-identical ON vs OFF (fur_ramp's discs have no strands; owl_kent's body has 0.025 mm of strand per mm² at 80 mm); item 58. **`detail_layer` vs `hairline_from_lines` (#928, measure only) — RULED 2026-10-14 (Kent, via the VP): KEEP BOTH (option A).** On owl_kent 59% of the line route's strand length lies on a detail line and 72% of the detail layer is line-only (92 of 147 lines are edge-like, which the ridge test refuses); both on sews 40 strands four times, +6,210 stitches, +116 trims. One as a mode of the other (C) only if Kent makes hair photos a priority; retiring `detail_layer` (B) needs an A/B widening `LINE_CLASSES` to `gradient` and a sew-out of the edge lines first. **`detail_layer_stitch` (PR #940, merged 2026-10-14, built OFF, default `"bean"`):** `"bean"` is the default and byte-identical (plan md5 on owl_kent, fur_ramp, photo_owl_pale); `"run"` sews each detail line once with `stitch_path` at `DETAIL_RUN_STITCH_MM` 1.5 (a candidate, gate 1; card v1 block A sews both). owl_kent: stitches added by the layer 5,466 → 1,503, **stitches under 1 mm added 5,267 → 0**, thread 3.87 m → 1.59 m, trims +72 either way, uncovered new 0.0; the render cannot show how heavy a bean line looks next to a run line on cloth. Full text of #915/#917: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-sixth-pass).

### Item 56, true-size small lettering: the #909 to #955 paragraph as it stood after PR #956

56. **True-size small lettering — RULED 2026-10-14, option A (Kent, ~16:00 CDT): drone fix first, then `small_text_true_size` ON; the drone residue is accepted. The flip PR #955 is HELD (below). #909 KEPT (Kent) after it merged in error.** `small_text_cap_mm` (#909)
   enlarges a small line; Kent: *"you can't change the font size for the final product"*, so it stays OFF and is not the route. The true-size route is
   `small_text_restore_mm` + `bean_letter_stitch_mm` (#911) and `bean_letter_serif_mm` (#914), four candidate values (gate 1). **Since:** #931 the ink reader no longer
   counts a cutout letter's counter as ink (`enclosed_mask`, alpha path only: Enthusiast 80 mm "ENTEArRISES INC" → ENTERPRISES INC, 2,299 → 2,328 stitches); #933 `restore_small_text`
   strips the tagger's strays (separator bars, rope) off the line (Fremont 92.5 mm tagline reads as centrelines, 17,466 → 17,298 stitches, 54 → 53 trims); #934 the serif-hook guard
   judges the hook it found (81 mm date "BST 1898" → "EST 1898"). Still unreached: at 65 mm the date is 1.3 mm tall, under `LETTER_MIN_HEIGHT_MM` 1.5; at 81 mm the 5 still
   reads as an 8. **Head to head (#938, measure only): "both" equals true size byte for byte** (bean letters take every glyph they can before the skeleton is offered any), so they
   are alternatives, not additive. Fremont Hat 81 mm, main / skeleton 0.73 / true size: stitches 15,625 / 15,000 / 15,281; trims 47 / 47 / 41; mean legibility EST / 1895 / THE / tagline
   0.97 / 0.55 / 0.97 / 0.61, 0.94 / 0.77 / 0.97 / 0.92, 0.94 / 0.90 / 1.00 / 0.99; OCR glyphs 14/20, 16/20, 18/20, every interval overlapping, so read the geometry. At 92.5 mm
   they are closer and THE does not move under either. True size wins or ties every word at both sizes and #944 has since looked at it off Fremont (below);
   the skeleton has a corpus check and two numbers. **The switch (#943, merged, OFF):** `cfg.small_text_true_size` fills five values when they are unset (restore 3.0, bean stroke 0.5, pitch 0.45, serif 0.45, shortest free arm `bean_letter_min_arm_mm` 0.3; an explicit value wins; OFF byte-identical); #946 adds `bean_letter_corner_deg` 50, a station ON every corner that turns 50° or more within 0.2 mm (the 5's stem and bar stopped sewing as a triangle). Fremont 81 / 92.5 mm Hat, main → switch: 15,625 / 47 → 15,330 / 41, OCR glyphs 14/20 → 18/20; 18,882 / 53 → 18,675 / 54, 13/21 → 18/21 (THE 1/3 → 3/3, as a centreline: Kent, "Centre line is fine"); the 1 keeps its flag and foot. **Corpus census (#944, 17 designs):** true size sewed drone's bold chrome PRECISION as hollow outlines, +170.8 mm² `ARTWORK_UNCOVERED`, +23 trims, +2,334 stitches. **Fix (#948, merged): `beanletters.INK_SHAPE_MAX_RATIO` 3.0** — the ink read on chrome is the white highlight strips between bevel lines (0.28–0.35 mm), so a member whose traced mean width exceeds 3.0 × its ink stroke has no read (drone's letters 4.73–6.70; bridge's counter-closed blobs, the case the ink read exists for, at most 2.28; letters that should go bean 0.66–1.34). Drone 21,660 / 154 → 19,281 / 130, uncovered 170.8 → 0.0, 0 bean shapes; no other design moves; the residue is the restore step re-tracing 8 'AND DRONE' letters (−45 stitches, −1 trim, +0.44 mm² bare), accepted. 3.0 is a gate-1 candidate, unsewn, consulted only when `bean_letter_max_stroke_mm` is set. **THE FLIP IS HELD (PR #955, OPEN, NOT armed).** Kent, 21:55 CDT: land it WITH a cap-height guard, `small_text_true_size_min_cap_mm` 1.6 (a gate-1 candidate); Kent, 23:10 CDT: HOLD. At Fremont Hat 65 mm the guarded switch still regresses the tagline (cap ≈ 1.74 mm, over 1.6): OCR 10/11 → 5/11, counters 3/4 → 1/4, THE 3/3 → 1/3; at 72 mm it is mixed (1895 legibility 0.530 → 0.786, tagline level). **A cap-height guard alone cannot separate the 81 mm dates (cap 1.65, want ON) from the 65 mm tagline (1.74, want OFF).** Kent's lettering session is diagnosing it and will propose the guard QUANTITY and its value; nothing is flipped. Residuals if flipped: THE at 92.5 mm patch 1.000 → 0.667 (the E's bay reads closed, item 59), screenshot +5 trims, small print +0.9 to +1.6 mm² bare. *(ruled 2026-10-14 — VP relay of Kent, ~16:00, 21:55 and 23:10 CDT; measured 2026-10-14 — PRs #943, #944, #946, #948, #955)*
   One unrepresentative logo, no sew-out. Prior text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-seventh-pass).
   *(measured 2026-10-13/14 — PRs #909, #911, #914, #931, #933, #934, #938, #943, #944, #946, #948, #955, `tests/test_small_text.py`, `tools/small_lettering_compare.py`)*

## Tenth pass: overflow moved from MASTER_SCOPE (2026-10-15, second refresh)

Moved verbatim from `MASTER_SCOPE.md` by the second 2026-10-15 refresh (PRs #955, #964-#967) to keep the file under its word budget. Each paragraph stood as written after the first 2026-10-15 refresh (PR #963). The live text in MASTER_SCOPE carries the verdict and the current numbers.

### Quality review 2026-09-08 and the lettering construction chain: the paragraph as it stood after PR #963

**Quality review 2026-09-08 — fourteen ranked changes, three cheap JS-lane defects, and Kent's picks:** [`docs/quality-review-2026-09-08.md`](docs/quality-review-2026-09-08.md). **Lettering construction chain (Kent's route ruling 2026-09-19; steps 0 to 5 and the trims gap).** ON by Kent: `satin_house_from_line`, `satin_house_anchor`, `satin_stroke_order="euler"`, `satin_corner_twigs`, `satin_lettering_split`, `satin_junction_stack`, `edge_cap_skip_lettering`, `satin_rail_comp` (since 2026-09-28; sew-out owed), the trims-gap exit lever (its underlay half stays OFF), `alpha_edge_extend` and `subpixel_edges_upscaled`. `satin_walk_cursor_reach_mm` stays OFF (0.0) pending a sew-out. The Studio sends the uploaded file, not a canvas re-encode (fixed 2026-09-20). Full text, moved verbatim: [area 1](docs/scope/1-auto-digitizing-quality.md#lettering-construction-chain-steps-0-to-5--moved-from-master_scope-2026-10-13). *(confirmed 2026-10-13 — `digitizer_core/config.py` defaults; measured 2026-09-19/20 — scope-history, DOCTRINE)* **Item 1's PR 5 MEASURED (2026-09-11, gate-2 clean):** `tools/color_diversity.py` supports the stage-0 signal on the art-bbox foreground (quote that reading); **the blocker is unchanged — one real tonal artwork labelled where the spec asks four** (`docs/stage0-signal-decision-2026-09-11.md`). PR 6a supported, not authorised; PR 6b is Kent's ruling. *(measured 2026-09-11 — `tests/test_color_diversity.py`; detail: [area 1](docs/scope/1-auto-digitizing-quality.md#area-1-lanes-in-full--moved-from-master_scope-2026-10-08))* Three measurements the ranking rests on, and the browser lane's `ties` / `fillStagger` pointers ("Waiting on Kent" 23, 24), are in [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass). **`cfg.keep_thin_strokes` is DEFAULT ON since 2026-09-13** (Kent: *"Flip it — take gaulke and becker as the price"*; False is the pre-flip engine): the instruments (`tools/thin_strokes.py`, `legibility.py`) showed the two lanes lose different width bands; ON, Fremont routed loses 3 thin strokes instead of 18, at MORE stitches since `cfg.subpixel_edges` turned the old saving into a cost. `logo_gaulke_roofing`'s black lettering is enclosed background — item 9's garment rule is what sews it. Photo classes are gated out. *(measured 2026-09-13 — `docs/thin-strokes-flip-2026-09-13.md`; detail: [area 1](docs/scope/1-auto-digitizing-quality.md#area-1-lanes-in-full--moved-from-master_scope-2026-10-08))* **`cfg.lettering_min_column_mm` BUILT with its tier rule, DEFAULT OFF (None):** Fremont ON sews widened glyphs at a 0.91 mm median column (the pro: 0.82–0.90), but the 1.0 mm column fills counters at a 2.2 mm cap height and ENTHUSIAST's 1.6 mm subline smears (legibility 1.00 → 0.72) — **a glyph-height gate is the open question before it ships on, Kent's call.** *(measured 2026-09-09 — `docs/renders/column-tier-2026-09-09/`; detail: [area 1](docs/scope/1-auto-digitizing-quality.md#area-1-lanes-in-full--moved-from-master_scope-2026-10-08))* **Item 5, PRs 2 and 3 (2026-09-09):** no serif column was built (the artwork's feet carry no serif, and MARINE's "self-crossings" sit between columns at Goldman joins, as in the pro's own file); the junction cover shipped as `cfg.satin_patch_junctions = "satin"`, part C of the junction stack since 2026-09-19 (item 19), Becker 80 mm `ARTWORK_UNCOVERED` 9.0 → 0.0; a bold letter is 45–90% junction ball and the pro stacks MORE layers there than we do. Full text, moved verbatim: [area 1](docs/scope/1-auto-digitizing-quality.md#item-5-prs-2-and-3--moved-from-master_scope-2026-10-13). *(measured 2026-09-09 — scope-history's item 5 entries)* **Item 6 is BUILT as `cfg.satin_rail_comp`, DEFAULT ON since 2026-09-28** (Kent's flip on the labelled sitting; price accepted 2026-09-29; the sew-out still owed): a satin-tier shape keeps its artwork polygon and each rail is pushed out along its cross by the fabric's pull (the amount untouched, gate 1). `satin_rails_follow_edge="envelope"`, ON since 2026-09-30 on Kent's eye, cures the far rail's under-reach; its junction escapes and teeth are dropped and the split comb is decided per column. Thread-vs-target IoU Fremont 0.675 → 0.836, drone 0.797 → 0.838; thread outside the artwork 147–322 mm² → 0. The full entry, moved verbatim: [area 1](docs/scope/1-auto-digitizing-quality.md#item-6--satin_rail_comp-and-the-envelope-moved-from-master_scope-2026-10-13). *(measured 2026-09-09/30 — `tests/test_rail_comp.py`, `tests/test_skeleton_tracer.py`)* **Items 4, 5 (first PR), 7, 8, 9, 11 and sub-pixel edges (2026-09-09/10).** `cfg.design_angle` and `cfg.wide_columns` stay OFF (the last ~20° to the pro's angle is a house-style number, Kent's; MARINE's decomposition, not its width, blocks `wide_columns`). ON: the four colour flags and `robust_region_colour` (Kent, 2026-09-10), `enclosed_by_garment` (Kent; gaulke +43 trims accepted), `legibility_check` (warns under 0.5 and never blocks, RULED) and `subpixel_edges` (Kent, 2026-09-09). Stage 6 clusters split junctions (built 2026-09-09). Full text, moved verbatim: [area 1](docs/scope/1-auto-digitizing-quality.md#items-4-5-7-8-9-11-and-sub-pixel-edges--moved-from-master_scope-2026-10-13). *(confirmed 2026-10-13 — `digitizer_core/config.py` defaults; measured 2026-09-09/10 — area 1)* *(measured 2026-09-08 — review doc; scope-history 09-08, four entries)* **Connected script is outside the construction, and the lettering findings name the artwork's limit (measured 2026-09-30):** preflight `SATIN_GAPS_TIGHT` (built 2026-09-30) and `LETTERING_TOO_SMALL` / `LETTERING_ILLEGIBLE` carry it; the text moved to [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass). **L1, one lettering tagger, BUILT OFF (`cfg.lettering_words`, 2026-10-08):** lettering readers group by one word model (the rescued redraw excepted); on hand labels of eight logos, constants fitted in-sample, detection kappa 0.907 — level with the text cluster (0.881), above the Column lane's reading (0.637) — and line ARI 0.99 vs 0.65 (two fixtures); flip is Kent's *(measured 2026-10-08 — `docs/word-tagger-2026-10-08/`)*; it misses glyphs at 50 mm, no single rule (item 37, PR #889). **The Column lane is ON by default (Kent, 2026-10-12, PR #863):** a text-tagged shape sews as outline-cut columns, not through the skeleton satin tier; ON beside OFF, the open items and the 0.06–0.07 mm reach question: "Waiting on Kent" 37. *(confirmed 2026-10-13 — `config.lettering_columns`)* **Column ends (PRs #907, #912):** `lettering_columns_square_ends` and `lettering_columns_inside_connectors` are ON by default since 2026-10-14 (Kent's ruling 2026-10-13, flip PR #922) — "Waiting on Kent" 55.

### Kent's Fremont 81 mm Hat report: the paragraph as it stood after PR #963

**Kent's Fremont 81 mm Hat report — "1895" dropped out of his Studio run (2026-10-13/14, PRs #898, #902, #905–#914, #916).** Replayed with the Studio's own request (`tools/fremont_triage.py studio_request()`: 81 mm, 6 colours, Hat, bean edge cap) it reproduces his job: 15,306 stitches against his 15,129, 3 colours, 161 shapes. **Not the Column lane (#863) and not #890's guards:** all six bisect arms sew EST and 1895 identically. The causes: stage 4's hole floor (0.5625 mm²) fills the 8's and 9's counters and the white ground's hole where the "1" sits, after which stage 5's clip removes the whole "1"; stage 7's small-shape rescue sews every glyph under `min_detail_mm`² (2.25 mm²) as a bean outline before the lane is asked (134 of 161 shapes); the tagline's three A's lose counters at stage 4. **`ARTWORK_UNCOVERED` is silent in every arm: coverage cannot see illegibility.** Stage 0 classes this flat logo `gradient` (gated, not chased). Fremont is UNREPRESENTATIVE (it reproduces defects, it sizes nothing), and the pro sews this tagline legibly at 92.5 mm. *(measured 2026-10-13 — PRs #898, #902, `tools/fremont_triage.py`, `docs/renders/claude-fremont-81mm-triage/`)* **Existing flags at 81 mm (#905, measure only):** the floor shuts the four tagline counters (item 47), `lettering_columns_small_stem` does nothing, `small_glyph_keep` keeps counters the thread then sews over (51); the tagline and EST strokes (0.22–0.30 mm) are thinner than one thread, so every run construction sews them 1.6–3.2× wide, and THE's blob is the hat preset's 0.4 mm pull (57). Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-sixth-pass). *(measured 2026-10-13 — PR #905, `tools/fremont_small_lettering.py`)* **A legibility instrument exists (#906, `tools/glyph_legibility.py`) and it is NOT a gate:** it ranks Kent's four red boxes below five legible words on the lane's own output (AUC 1.000, permutation p 0.008) but not once the pro's own THE counts as legible (AUC 0.885 [0.692, 1.0], margin −0.249), and its `legibility` headline ranks them the wrong way round (AUC 0.10): never quote that one. Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-sixth-pass). *(measured 2026-10-13 — PR #906, `tests/test_glyph_legibility.py`)* **The levers built since, none sewn:** the skeleton run ("Waiting on Kent" 54, OFF; EST and 1895 reach it since #936), the true-size options (56, ruled ON, the flip #955 HELD; #931, #933, #934 mend them, #938 compares them with the skeleton, #943/#946/#948 build the switch), the word tier (57, OFF), the i dot rung (52, #939 merged, OFF); the Column ends flags (55) are ON since #922. **Cards:** v3 (#910) carries blocks F3, T, N and v2's G; v3.1 (#916) adds S, E2, X, B and is with Kent for the sew-out; **v3.2 (#949)** re-cuts v3.1 on main and adds block O (the line route's chaining, OFF vs ON); **the passes card (#950)** sews Fremont's THE and 1895 at 1 / 2 / 3 bean passes (item 59).

### Item 56, true-size small lettering: the paragraph as it stood after PR #963 (flip PR #955 still open, being re-tasked)

56. **True-size small lettering — RULED 2026-10-14, option A (Kent, ~16:00 CDT): drone fix first, then `small_text_true_size` ON; the drone residue is accepted. The flip PR #955 is OPEN, not armed, and is being re-tasked (2026-10-15).** #909 `small_text_cap_mm` was KEPT (Kent) after it merged in error, but it stays OFF and is not the route: Kent, *"you can't change the font size for the final product"*. The route is `small_text_restore_mm` + `bean_letter_stitch_mm` (#911) and `bean_letter_serif_mm` (#914), now behind `cfg.small_text_true_size` (#943, merged, OFF; five values filled when unset; #946 adds `bean_letter_corner_deg` 50). Fremont Hat, main → switch: 81 mm 15,625 / 47 → 15,330 / 41 stitches / trims, OCR glyphs 14/20 → 18/20; 92.5 mm 13/21 → 18/21. True size equals "both" with the skeleton byte for byte (#938) and wins or ties every word. The drone gate (#948, merged): `beanletters.INK_SHAPE_MAX_RATIO` 3.0, a gate-1 candidate, unsewn, took drone's PRECISION `ARTWORK_UNCOVERED` +170.8 → 0.0 mm². **The cap-height guard is not enough.** Kent asked for `small_text_true_size_min_cap_mm` 1.6 (21:55 CDT), then HOLD (23:10 CDT): a cap guard alone cannot separate the 81 mm dates (cap 1.65, want ON) from the 65 mm tagline (1.74, want OFF). **Two 65 mm causes have since been found and cured, both built OFF:** (1) `cfg.ink_ground_ring_mm` (#958, merged; candidate 0.8 mm) reads the ink ground from a ring round the cluster, so the black Wisconsin state between EST and 1895 no longer thickens every digit (0.84–1.73 mm read on a stroke of about 0.15 mm, now 0.14–0.16): 65 mm 1895 OCR 1/4 → 2/4, 17-design corpus byte-identical. (2) `cfg.small_text_keep_stray_lines` (#960, merged): strays that form a line of three or more letters keep their tags as their own cluster, so the 65 mm THE sews as bean, OCR 1/3 → 3/3, and 72, 81, 92.5 mm and the corpus are byte-identical. **#955 depends on #960:** without it any cap guard below about 2.1 mm lets the 65 mm THE regress, and #958 does nothing until the cap guard is lowered or replaced. The re-tasked flip carries a 0.5 mm counter guard plus `keep_stray_lines` (the director's brief; the PR's title still names the 1.6 mm cap guard, its latest commit is "counter guard: a guarded cluster stays whole, its stray line included"); a flip needs a PRE_FLIP entry and nothing is flipped until it merges. Residuals if flipped: THE at 92.5 mm patch 1.000 → 0.667 (the E's bay reads closed, item 59), screenshot +5 trims, small print +0.9 to +1.6 mm² bare. One unrepresentative logo, no sew-out. Full text of the #909 to #955 paragraph, moved verbatim: [area 1](docs/scope/1-auto-digitizing-quality.md#ninth-pass-overflow-moved-from-master_scope-2026-10-15). *(ruled 2026-10-14 — VP relay of Kent; measured 2026-10-13/15 — PRs #909, #911, #914, #931, #933, #934, #938, #943, #944, #946, #948, #955, #958, #960, `tests/test_small_text.py`, `tools/small_lettering_compare.py`)*

### Item 59, small-lettering follow-ons: the paragraph as it stood after PR #963

59. **Small-lettering follow-ons (2026-10-14): three built OFF and outside the switch, one instrument, one trace. Fremont is UNREPRESENTATIVE: it reproduces defects, it sizes nothing; every value is a gate-1 candidate and nothing is sewn.** Full numbers: [area 1](docs/scope/1-auto-digitizing-quality.md#eighth-pass-the-small-lettering-follow-ons-pr-945-956). **(a) `bean_letter_counter_hold_mm` (PR #952, merged, OFF; not in the switch, adding it is Kent's call):** under the switch Fremont 81 mm Hat's 8 sews both counters shut by #905's 50%-bare rule (bare 0.33 / 0.28), worse than main's 1 of 2 open; hold 0.25 opens both (0.627 / 0.544), the 9 goes 0.385 → 0.674, the tagline's counters 1 of 4 → 4 of 4, legibility unchanged at 81 mm. **Cost:** a held letter sews up to about 0.1 mm wider outside; 1895 at 92.5 mm reads 0.960 → 0.951. **Sew-out card cut (#959, merged, handed to Kent, NOT sewn):** a separate 4×4 card (71.0 × 64.2 mm hoop, 20 arms, one colour, 40 wt, Hat, `small_text_true_size` ON in every arm by override). Block A is hold OFF vs 0.25 on EST (the control, no counter) and 1895 at 81 mm; B1/B2 are ties OFF vs ON at 81 and 92.5 mm; C (passes) stays on `card-passes-2026-10-14`. Arms are labelled by teeth. Card v3.2 is unsewn and not superseded; every value stays a candidate (this card IS the sew-out, gate 1). **(b) `bean_letter_passes` (PR #950, OFF):** passes per spine (`None` = 3, byte-identical), built for Kent's 'what if we stitch on top of the other stitch for coverage'; `docs/sewout/card-passes-2026-10-14/` sews Fremont's THE and 1895 at 1 / 2 / 3 passes (718 stitches, 35.2 × 26.8 mm). **Card v3's `small_glyph_keep` OFF pin is stale** (ON since #908): its N block is still a valid A/B, its F3 and T 'today' arms are not. **(c) `small_letter_ties` (PR #956, merged, OFF):** no lock where a bean already opens 3 times, a walk-in or walk-back lock elsewhere; lock thread piled on the ink of bean and skeleton runs **−65% at 81 mm, −64% at 92.5 mm**, trims unchanged, 6 of 9 logos byte-identical. **Card blocks B1/B2 (#959) sew it; still owed: the same 3 mm cap letter, bounce lock vs ties, tails pulled by hand after a wash.** **(d) Trace of the 1, 5, THE's E and the tagline S (PR #953, merged, measure only):** 0 needle points off the ink in all six readings, so **the 1's OCR miss is the instrument's window (a black fill 0.69 mm away), not the engine; single-glyph OCR is unstable (the 5 reads A, S and 8 across masks): judge structurally** — bays at the 50% rule, no thread hole, needle points on ink. Named causes: the 1's miss is a black fill 0.69 mm away inside the instrument's window (its own thread reads I at full filament width, 1 at half); the 5 at 81 mm has its upper bay filled by thread width (64% covered, the lever is #952's hold); THE's E at 92.5 mm is a tick-to-arm pinch that the instrument's 20 px/mm render closes into a false counter (0.72 mm², a legibility-metric failure, not an OCR one); the 5 at 92.5 mm and the tagline S have no geometric cause. Proposals, unbuilt: restrict the glyph window to the word's own shapes; pull a free end back about 0.13 mm where two footprints come within 0.15 mm. **(e) `cfg.preflight_glyph_metric` (PR #945, merged, OFF):** per-glyph legibility and `counters_shut` as preflight metrics (Fremont 81 mm Hat: 5 shut), no finding or grade change (Kent 2026-10-02); **2.6 to 2.8 s per job, over the 2 s target, hence OFF**. *(measured 2026-10-14 — PRs #945, #950, #952, #953, #956, #959, `tests/test_preflight_glyph_metric.py`, `tests/test_bean_counter_hold.py`, `tests/test_small_letter_ties.py`, `tests/test_bean_glyph_trace.py`)*

### Item 57, `lettering_words`: the #927 census and #935 pull-aware read as they stood after PR #963

   **#927 census (measure only):** script never reaches the Column lane, structurally: a script word is one or two wide regions (aspect 2.6 to 3.8) against every
   tagger's ceiling (1.4 / 1.4 / 2.0), and the lane needs three or more similar glyphs (0 of 4 tires glyphs, 0 of 1 "Bridge"); the repo's only lowercase IS script.
   **A `lettering_words` flip would SHRINK the lane on golden_tee, 9 → 6 shapes** (house group tags 9, text cluster and L1 tag 6): judge a flip with it. Letter
   detection over becker, bridge, tires (99 regions, 28 letters, region bootstrap): kappa text cluster 0.75 [0.59, 0.89], L1 0.75 [0.59, 0.89], house group 0.48
   [0.29, 0.67]. Do not force script in; at most a read-only `script_word` tag (monoline CV ≤ 0.35, stroke ≥ 2.5 mm: 3 of 3 in, 0 of 27 out; n = 3, a candidate).
   No decision for Kent. *(measured 2026-10-14 — PR #927, `tools/script_lowercase_census.py`)* **Pull-aware read (#935, instrument only; `tools/glyph_legibility.py --pull-mm MM|auto`, default 0 unchanged):** erodes the thread mask by the pull before any glyph is read (a thread-wide line on the artwork's ink survives; a gap under the counter floor is closed first). `auto` ESTIMATES one number per design (0.25–0.32 mm Fremont, 0 for Becker and Bridge), a way to read a render as if the cloth had pulled, not a measurement of any cloth (gate 1). Ours 81 mm: FREMONT counters 0.857 → 1.000; Kent's four boxes rise (`+space` EST 0.000 → 0.473, 1895 0.062 → 0.121, THE 0.186 → 0.456, tagline 0.228 → 0.554) and all stay under HOTEL 0.995 and FREMONT 0.942; word-level AUC, lane output only, 0.950 [0.80, 1.0] permutation p 0.016 at auto (1.000 at the cap's own 0.4); the headline `legib` inversion half repairs (AUC 0.462 → 0.769 [0.48, 1.0], p 0.061). **PARTIAL: the pro's THE still sits under our median** (`+space` 0.549 / 0.486 Hat / Patch against ours 0.968): its E sews its bays shut, as dots, and the THE reads anyway, so `space` and `counters` bill a closed bay whether or not a human still reads the letter. No flip proposed. *(measured 2026-10-14 — PR #935, `tests/test_glyph_legibility.py`)*

## Eleventh pass: overflow moved from MASTER_SCOPE (2026-10-15, third refresh)

Moved verbatim from `MASTER_SCOPE.md` by the third 2026-10-15 refresh (PRs #969-#973) to make word-budget headroom before adding. Each paragraph stood as written after the second 2026-10-15 refresh (PR #968). The live text in MASTER_SCOPE carries the verdict and the current numbers.

### Item 59, small-lettering follow-ons: the paragraph as it stood after PR #968

59. **Small-lettering follow-ons (2026-10-14/15): six built OFF and outside the switch, one instrument, one trace. Fremont is UNREPRESENTATIVE: it reproduces defects, it sizes nothing; every value is a gate-1 candidate and nothing is sewn.** Full numbers: [area 1](docs/scope/1-auto-digitizing-quality.md#eighth-pass-the-small-lettering-follow-ons-pr-945-956); the paragraph as it stood after PR #967: [area 1](docs/scope/1-auto-digitizing-quality.md#tenth-pass-overflow-moved-from-master_scope-2026-10-15-second-refresh). **(a) `bean_letter_counter_hold_mm` (PR #952, merged, OFF; not in the switch, adding it is Kent's call):** a 0.25 hold opens both of the 8's counters (bare 0.33 / 0.28 → 0.627 / 0.544) and the tagline's counters 1 of 4 → 4 of 4; a held letter sews up to about 0.1 mm wider outside. **Sew-out card cut (#959, merged, with Kent, NOT sewn):** a separate 4×4 card, 20 arms, 40 wt, Hat, the switch ON in every arm; block A is hold OFF vs 0.25, B1/B2 are ties OFF vs ON at 81 and 92.5 mm; C (passes) stays on `card-passes-2026-10-14`. Card v3.2 is unsewn and not superseded. **(b) `bean_letter_passes` (PR #950, OFF):** passes per spine (`None` = 3, byte-identical); `docs/sewout/card-passes-2026-10-14/` sews THE and 1895 at 1 / 2 / 3 passes. **Card v3's `small_glyph_keep` OFF pin is stale** (ON since #908): its N block is still a valid A/B, its F3 and T 'today' arms are not. **(c) `small_letter_ties` (PR #956, merged, OFF):** lock thread piled on the ink of bean and skeleton runs −65% at 81 mm, −64% at 92.5 mm, trims unchanged, 6 of 9 logos byte-identical; card blocks B1/B2 sew it, and still owed are the same 3 mm cap letter, bounce lock vs ties, and tails pulled by hand after a wash. **(d) Trace (PR #953, measure only):** 0 needle points off the ink in all six readings, so the 1's OCR miss is the instrument's window (a black fill 0.69 mm away), not the engine; single-glyph OCR is unstable (the 5 reads A, S and 8), so judge structurally: bays at the 50% rule, no thread hole, needle points on ink. Unbuilt proposals: restrict the glyph window to the word's own shapes; pull a free end back about 0.13 mm where two footprints come within 0.15 mm. **(e) `cfg.preflight_glyph_metric` (PR #945, merged, OFF):** per-glyph legibility and `counters_shut` as preflight metrics, no finding or grade change (Kent 2026-10-02); 2.6 to 2.8 s per job, over the 2 s target, hence OFF. **(f) `cfg.bean_letter_bay_hold` (PR #967, MERGED 2026-10-15, OFF, not in the switch; Kent's decision: into the switch, sew-out first):** each bean station within the hold of a BAY (a 0.45 mm closing of the letter's ink with its counters filled, minus the ink, at least 0.05 mm²) moves to the least crowded point of its own spine's ink; a station between a bay and a counter is never pushed into the counter, and satin runs are md5-identical OFF vs ON in all 17 designs. With the switch ON plus a 0.2 mm hold: the 5's upper bay at 81 mm Hat goes 0.36 → 0.53 bare (open by #905's 50% rule, a thin margin), THE's E at 92.5 mm goes 1 false counter → 0 and THE 0.667 → 1.000, the 92.5 mm tagline S (never a closed loop: 0 thread holes in every arm) reads S instead of 8, and 1895 legibility and OCR do not move. **Cost:** a held letter sews up to about 0.1 mm wider outside (EST at 92.5 mm 0.984 → 0.964 at 0.2, 0.930 at 0.25); 7 of 17 designs move, only in bean letters, `ARTWORK_UNCOVERED` rises nowhere. 0.2 is the corpus arm and 0.25 the alternative, both candidates; the sew-out is 1895 and THE at 81 and 92.5 mm on a cap, switch vs switch + hold. DOCTRINE 2026-09-30 (no same-shape notch guard) is about the satin rail push, which this does not touch. **(g) `cfg.edge_cap_bean_pitch_mm` (branch `claude/edge-cap-bean-pitch`, commit 3a367346; NO PR found 2026-10-15, not on main; built OFF):** None sews the BEAN edge cap at 0.73 mm byte for byte (md5-pinned on the three flat goldens and two default-config plans); a number re-spaces the cap's stations only, while the run tier, bean letters, the border's bean fallback and the satin cap keep 0.73. It is the census's option A ("Speed is the operator's", area 4). *(measured 2026-10-14/15 — PRs #945, #950, #952, #953, #956, #959, #967, `tests/test_bean_bay_hold.py`, `tests/test_bean_counter_hold.py`, `tests/test_small_letter_ties.py`, `tests/test_bean_glyph_trace.py`; confirmed 2026-10-15 — commit 3a367346's `tests/test_edge_cap_bean_pitch.py`, read on the branch, not run)*

### Item 56, true-size small lettering: the Fremont Hat before/after and accepted-cost sentences as they stood after PR #968

Fremont Hat, main → default: 81 mm 15,625 / 47 → 15,330 / 41 stitches / trims; 92.5 mm 18,882 / 53 → 18,675 / 54; 72 mm 13,363 / 44 → 13,195 / 46 (all three byte-identical to the unguarded switch); 65 mm 11,463 / 43 → 11,423 / 42 (the guard bites on the tagline only). **65 mm tagline residue ACCEPTED (VP, 04:35, 2026-10-15):** the tagline is held (legibility 0.893, counters 3 of 4, both equal to main) but the date line in its colour block acts, which moves the tagline's outline start points (+4 stitches, +1 trim in its box; OCR 10/11 → 8/11, Wilson intervals overlap). Also accepted: drone (−45 stitches, −1 trim, +0.44 mm² bare), THE at 92.5 mm 1.000 → 0.667 (the E's bay; item 59(f) cures it behind a flag), screenshot +5 trims and +2.69 mm² bare, small print +0.9 to +1.6 mm² bare.

### Defect 49, moved from the live list: as it stood after PR #968

49. **A letter's tapered apex sews BARE under `satin_rail_comp` — CLOSED 2026-09-30 behind `cfg.satin_crown_cover`, ON BY DEFAULT since Kent's flip 2026-10-02.** ENTHUSIAST's A at 80 mm: the column reaches within **0.08 mm** of the artwork's apex with the pull in the polygon and stops **1.63 mm** short with it on the rails. **The hole was settled as real before it was fixed**, because two instruments disagreed: `bare_anatomy` said 3.61 mm² but counts satin crosses only and over-reports 1.7x here (underlay threads 38.4%), while `unsewn_frac` read 0.0 and cannot fire on this fixture at all — its on-ink vote needs a region over 0.5 ink and the largest is 0.33. What survives both corrections is **2.17 mm² carrying no thread of any kind**, 1.72 mm² of it surviving the 0.50 mm opening, confirmed by a raster mask difference sharing no code with either: its largest uncovered component in the whole design, 0.97 mm², sits **0.33 mm** from the apex (next: 0.70 mm², 35 mm away). Drawn from the actual thread path: [`docs/renders/apex-verdict-2026-09-30/`](docs/renders/apex-verdict-2026-09-30/). **Preflight now sees it** (1.56 mm² on the 0.25 mm grid; its 0.4 mm erosion had hidden it entirely), and `satin_crown_cover` covers it for +0.5% stitches at an unchanged `lost_frac`. **Defects 49 and 50 are ONE mechanism** — artwork no stroke reaches — which is why one cover closes both. Still blind: `dropped_elements`' `uncovered_elements` misses it by **0.03 mm²** against `MIN_ELEMENT_MM2` 1.0. **An earlier fix was built and RETRACTED**: widening the tip closed the hole and pushed `lost_frac` 0.2573 → 0.2661 past its 0.26 bar at 100% overshoot — the reason `lost_frac` is the crown cover's gate from its first commit. *(measured 2026-09-30 — `tests/test_apex_is_real.py`, `tests/test_crown_cover.py`; scope-history 09-30)*

### Defect 50, moved from the live list: as it stood after PR #968

50. **`satin_lettering_split` leaves holes at the crowns of curved letters — CLOSED behind `cfg.satin_crown_cover`, built OFF 2026-09-30, ON BY DEFAULT since Kent's flip 2026-10-02.** MARINE 127.4: the split sews the word in 7,168 stitches with **11 holes / 22.9 mm²** where fill leaves none. It is still a NET WIN — `lost_frac` 0.2688 fill against 0.1800 split — so this was never a case for reverting the flip. **The crowns are not in any column:** five rail and pitch arms are refuted (the envelope inert, `follow_edge=True` 2 of 11, the width smoother deleted 0 of 11, pitch halved 1 of 11 for +1,567 stitches) and every arm that moved one made `lost_frac` worse. The strokes' union leaves wedges no stroke claims, 4 of 11 at a node between sub-strokes. **The cure is the junction cover with its junction gate removed and `ARTWORK_UNCOVERED`'s own thresholds** (Kent's ruling, design doc §7: a cover, all satin shapes). ON: MARINE 127 **11 → 1 hole**, 22.9 → 1.5 mm², +2.6% stitches, `lost_frac` 0.1800 → **0.1730**; corpus holes **20 → 10** with `lost_frac` never rising and golden_tee **1.4% cheaper**; the four fixtures with no holes find no wedge at all. **Flip is Kent's.** *(measured 2026-09-30 — `tests/test_crown_cover.py`; scope-history 09-30)*

### Defect 51, moved from the live list: as it stood after PR #968

51. **Low-resolution line art lost its fine detail at the TRACER'S GRID, not in the file — FIXED, `cfg.work_px_per_mm` ON at 8.0 (Kent's flip 2026-10-01, on renders; None = the engine before it).** Kent's ask: bridge's "RESTAURANT" completely missing. A source under `min_px_per_mm` was enlarged to 4 px/mm and traced there; a 0.7–1.4 mm stroke is then 3–5 px, and the RAG merge swallowed the letters (bridge: 67 of 81 mm² of teal held by SEEDS, **39** after the merge, six blobs sewn). Stage 1 now traces line art on the working grid (a 2,800 px side bounds it); `min_px_per_mm` keeps only the `INPUT_LOW_RESOLUTION` warning; photo classes keep the source line. Real logos downsampled to 5 px/mm and scored against their own full-resolution digitization recover fine ink **0.64 → 0.84** on average. **Costs:** trims rise toward the full-resolution file's count (a blurred synthetic pays 12 → 21). **Still open:** the recovered letters are 3.25–4.5 mm and each sews as ONE satin bar (a size question, `LETTERING_TOO_SMALL`); the result is not robust to small changes in the foreground mask; and Kent's verdict says the SOURCE is the bigger lever while `INPUT_LOW_RESOLUTION` fires only under 4 px/mm. Full entry: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-13-fourth-pass). **Bridge BAR & RESTAURANT (#962, MEASURED NEGATIVE, no engine change):** the corpus's least legible word (legibility 0.227) is not held back by one reader. Every glyph is too big for the small-text tiers (caps 3.2–5.5 mm, ink 0.67–1.15 mm, all three size gates are gate-1 candidates), the shipped text cluster tags 8 of the 12 letter regions (Column lane), and `textcluster.detect_text_clusters` refuses B and A (an axis-aligned box on letters set round an arc) and NT (nested in the 52 × 40 mm badge). A fixed tagger sews the same counterless blobs; the 400 px JPEG at 3.49 px/mm closes every counter in the raster itself (0 holes in every letter), so the cause is segmentation and the source (#593 territory), and `glyph_legibility` reads two round blobs there, not letters, so no change could be shown up on it. *(measured 2026-10-15 — PR #962, `tools/restaurant_trace.py`, `docs/renders/bridge-restaurant-tier/`)* *(measured 2026-10-01 — `tools/lowres_detail.py`; `tests/test_work_grid.py`)*

### Defect 52, moved from the live list: as it stood after PR #968

52. **A fill in the BROWSER engine carries thread across every hole and every notch — CLOSED in all three Studio lanes by `fillColumns` (manual 2026-10-07, shapes and image 2026-10-08, Kent's calls).** The JS tatami walk went from one span of a split row straight to the next: a float over a long gap, a STITCH over a short one (a 40 mm manual fill with two cut-outs: 76 untrimmed floats across the 12 mm one, 912 mm of thread). Hidden, because a float puts no needle point in the hole and the Studio draws jumps only with Jumps on. **The cure:** rows cut into monotone columns (`fill.js`, a port of the Python `_columns`), every move asked what ground it runs over; thread goes ROUND the hole and is cut only where there is no way round. Audited on 9,869 designs: floats that leave the fill's ground **1,154,992 → 0**. **Cost:** cuts fall from 0.89 a design to 0.25; stitches +3.3% (worst +37%); the travel shows (up to nine lines of thread on a rim's worst millimetre); satin shapes are untouched. **On** in every Studio lane (`generate.js`); the engine default stays off ("Waiting on Kent" 22); row stagger is not built (24). **Not sewn: no sew-out exists.** Sheet and cost tables: [`docs/renders/fill-columns-2026-10-03/`](docs/renders/fill-columns-2026-10-03/); full entry: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-13-fourth-pass). *(measured 2026-10-03 — `tools/fill-columns-sheet.mjs`; `test/fill.test.js`, `test/digitize.test.js`; flipped 2026-10-07/08 — `generate.js`)*

### Defect 58, moved from the live list: as it stood after PR #968

58. **Black-and-white logos sewed in four to six cones — anti-alias grey on thin strokes. FIXED: `cfg.two_tone_snap` is DEFAULT ON since 2026-10-11 (PR #821, Kent's approval of 10-08; False is the pre-flip engine).** A per-IMAGE gate on the foreground (achromatic, both inks, no grey plateau) thresholds the raster to its two inks after stage 1: five B&W logos 5–6 → 2 cones; Bridge Bar, Fremont and the golke screenshot byte-unchanged. `two_tone.keep_lines` cures the render cost (golke's white roof lines sewing as one black mass): a background channel under 1 mm, ≥ 7 mm long and ≥ 9× its width sews white at the satin floor, so golke and gaulke keep the roof chevron and window cross OFF lost. Preflight's thread grader now reads the snapped raster (`_two_tone_view`); unsnapped it blocked White on both. The halo-premise tests (each prices a COLOUR flag on gaulke's grey halo, which the snap removes) build their engine from `PRE_FLIP` with the snap off, and one house-anchor arm pins it off; nothing else in the suite moved, and no golden digitizes a fixture the gate fires on. On today's main the gate fires on the same eight images as on 10-08; the five B&W logos go 5–6 → 2 cones (mfab_lc 75 → 54 trims), gaulke stays 2 with its grey becoming white roof lines. Not sewn. *(measured 2026-10-11 — PR #821, `tools/two_tone_probe.py`; renders `docs/renders/two-tone-lines-2026-10-08/`)*

### Defect 60, moved from the live list: as it stood after PR #968

60. **The join-corner cut read ENTHUSIAST's S bowls as corners and `satin_join_square` pulled both members' ends off the apex — FIXED 2026-10-07 by the bend cap.** At 80 mm (half-width 0.87 mm) a pull-comped inner bowl is a sharp reflex vertex (60–96° at one vertex; Fremont's accepted corners 6–8° — but Becker's, gaulke's and drone's real corners 49–91°, so a vertex test would refuse those too), so `_split_sharp_corners`' 45°-at-an-artwork-corner rule cut each S at both bowls in both arms; OFF the bent ends still met, ON `_straighten_member_end` projected each apex 0.80 / 0.82 mm (0.92 half-widths) onto its fitted line and the bowl's wedge sewed bare — the fixture's first lost element over 1 mm² (1.18 mm² at (11.0, −2.6)), plus the three sibling bars *(measured 2026-10-07 — `docs/join-square-enthusiast-2026-10-07.md`)*. `_STRAIGHT_MAX_MOVE_HALVES` 0.6 keeps a member whose apex sits further off its line on its pre-flip spine (apex-move census under the flag: enthusiast p50 0.92, Fremont 0.22, Becker 0.12 half-widths). With it: enthusiast within two stitches of OFF and its four guards green; Fremont's fan ends 18 → 16 over 33 text columns either way; satin bare falls on five of six text logos against the uncapped flip (Fremont +0.04 points), trims never rise; corpus-wide about half the straightenings are refused (bridge 32 of 60, gaulke 9 of 14), all with the apex over the cap *(measured 2026-10-07 — `tests/test_join_corner_bend_cap.py`; the write-up's tables)*. Not sewn.

## Fifteenth pass: overflow moved from MASTER_SCOPE (2026-10-20)

Moved verbatim from `MASTER_SCOPE.md` by the 2026-10-20 refresh after PR #994 (`satinSmallShapes`, built OFF) to keep the file under its word budget. Each entry stood as written after the fourteenth pass (PR #988); the live text in MASTER_SCOPE carries the verdict and the current numbers. Defect 56's closed pointer, the longest in the file at 158 words, was cut to its verdict in the same pass; its full text is below. The OFF → ON table per shape, the md5 pins and the mechanism per construction are in [`docs/renders/browser-satin-small-shapes/README.md`](../renders/browser-satin-small-shapes/README.md) and PR #994's body; they are not repeated here.

### Defect 57 as it stood after PR #988 (before `satinSmallShapes` existed)

57. **The BROWSER's medial satin: its skeleton, its walk and its ends CURED (PR #817, merged 2026-10-11 on Kent's arming: "Waiting on Kent" 26); a star's centre NOT fixed.** **Cured.** `thin` never deletes a pixel on its grid's edge and every shape was laid against the grid's top and left, so a shape's top row and left column were its "skeleton": a bar's was an L, and its last cross ran the bar's length (3,853 of 14,812 satin bars). And the tracer's walk laid strokes twice and closed leftovers into "rings" with a chord, which the wrong skeleton hid on curves. Built: one spare cell; one pixel to one edge (the Python walk, ported); a free end run out to the outline. No satin bar has a stitch over 9.1 mm (was 100.6) and each is sewn to its drawn length within 0.6 mm. Of 320 hand-drawn satin arcs none has thread over open ground (167 had) and none is under 90% covered (150 were). A satin star sews a median 447 fewer stitches. Of 196 satin shapes in eight logos 96 gain over 2 points of own-thread cover and 49 lose (18 over ten, all under 3.5 mm). **Its costs and a star's centre, standing.** A satin bar's underlay start is cured (`underlayDirection`, ON since 2026-10-11, PR #836); a round end's last cross stands up to 0.46 mm outside it; a square or dot up to 6 mm takes the outline-split fallback, which starts 12% in from each end; and a satin star's longest stitch is a median 21 mm (up to 100 mm), cast arm to arm across the centre, its strokes joined by needle-up moves (a median 139 mm a star). Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass). **Reach:** every browser satin shape (basic shapes, drawn shapes set to satin, the image lane's thin shapes); no fill. Not sewn. Pictures: [`docs/renders/satin-spine-2026-10-04/`](docs/renders/satin-spine-2026-10-04/), [`docs/renders/star-walk-2026-10-03/`](docs/renders/star-walk-2026-10-03/). *(measured 2026-10-03, built 2026-10-04 — `tools/satin-walk-census.mjs`; scope-history 10-03, 10-04)*

### Waiting on Kent 26 (defect 57's cure) as it stood after PR #988

26. **Defect 57's cure — ARMED by Kent 2026-10-11 on the port's sheets (PR #817); built 2026-10-04.** It moves every satin shape of the browser lanes and no
   fill (a hand-drawn C set to satin: 6,047 stitches with its mouth sewn solid → 304 in one column). The underlay's direction is ON (item 40). Still open: round
   ends, small squares and dots (a number or a tier, gate 1); the star's tier. Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-sixth-pass).
   *(ruled 2026-10-11 — defect 57; [`docs/renders/satin-spine-port-2026-10-11/`](docs/renders/satin-spine-port-2026-10-11/README.md))*

### Defect 56's closed pointer as it stood after PR #988

56. a walk in the BROWSER's skeleton tracer never ended, and the satin emitter sewed what only its guard had stopped — FIXED 2026-10-03 (in `skeletonEdges`, `satin.js`; its rule was replaced 10-04 by one pixel to one edge, defect 57). A 20 mm star off the shape tool sewed 48,645 stitches and a 24 mm one 128,239; a design took up to 12 s to build. Three skeleton pixels that all touch are no node, so a walk went round them for `w * h` steps. **Exported stitches change only where a walk reached the guard**: 4,038 of 145,600 swept stars, 329 of 4,095 bars, 273 of 612 image-lane designs; no fill moves (an independent re-measure on 34,000 designs of its own: none moved without one). **Its cost:** the knot had been covering small round shapes, and a 2 mm one now sews four stitches. What the sweep found standing is defect 57. `test/satin-walk.test.js`. Full text: scope-history 10-03.
