# Why the letters are botched, and the instrument that hid it (2026-08-26)

Kent, on a sewn `drone_render` wordmark: *"All N's look bad — bottom right
drops away too quickly"*, *"the H edges are not clean and crisp"*, *"the E in
THERMAL doesn't look clean."* A 13-agent workflow measured it end to end.

**Method and re-derivation: `digitizer/tools/letterform_fidelity/`. Standing
consequences: `docs/scope/1-auto-digitizing-quality.md`.** What follows is what
a future session should carry into the work.

## The headline: there is no single root cause

Two mechanisms compound in a definite order, and a third of the wordmark is
below the size any digitizer can render. **Anyone who offers one tidy root
cause is wrong.** All three are measured below.

**And they are not the whole story.** Kent, looking at a sewn Becker logo the
same day, named a FOURTH thing none of the 13 agents examined: the stitch
angle is inconsistent between letters, and there is no mechanism in the code to
make it consistent. It is listed first, as #0, because coverage and fidelity —
the instruments this whole investigation built — are blind to it.

## The instrument is why this survived

**Bare-fabric coverage scores THERMAL's `H` at 1.9% bare — "fine". The `H` is
visibly deformed.** Coverage cannot see a tilted column, a rounded corner, or a
scalloped edge: thread is present in all three, just in the wrong place. Every
earlier letter check used coverage, so every earlier check passed.

Re-scored on shape fidelity (thread-vs-artwork IoU, `s11_iou.py`): design mean
**0.587** over 20 letters — big text 0.652, small text 0.489. That is the
number behind the word "botched". It **saturates on small letters** (`DRONE`'s
`E` scores 0.534 against a 0.580 thread-width ceiling while sewing as an "L"),
so screen with it; do not rule on it.

## #1 — Pull comp is a blunt dilate applied BEFORE the letter is decomposed

`stage5_overlap.py:227` — `poly.buffer(pull)`, shapely's default **round**
join, no minimum-feature floor. On `pique_knit`, `pull_comp_mm = 0.3`:

- Every convex corner becomes a 0.3 mm arc. `PRECISION` `N`: 11 polygon
  vertices → **130**. `THERMAL` `E`: 12 → 140.
- Every exterior concavity narrows by exactly `2 × pull = 0.600 mm`.
  `THERMAL` `E` arm slots: median **0.936 → 0.336 mm**, narrower than one
  0.4 mm thread. `DRONE` `E`: **0.728 → 0.128 mm**, sealed.
- **The guard that would stop this exists and is scoped wrong.**
  `stage5_overlap.py:424` holds a feature open only when it is an *interior
  ring* (`for ring in poly.interiors`). The counters in `O` and `D` are
  protected; the `E`'s arm slots and the `N`'s crotch get **no test at all**.
- It also poisons stage 6, which skeletonises the *grown* polygon — the acute
  vertices routing needs are already rounded off before it looks.

Control (`s6_pull0.py`, `pull=0`): fidelity **0.587 → 0.747**, big text
**0.652 → 0.829**. **That control is a diagnostic, NOT a proposal** — pull
compensation is gate-1, settled by a sew-out.

## #2 — `_prune_spurs` destroys the node its own docstring promises to keep

`stage6_satin.py:958`, called at `:1126` with `max(3.0, half_px * 1.6)`.
Docstring: *"Erase short dead-end twigs in place, **keeping their branch
node**."*

**Be precise about this, because the function was already fixed once** (PR
#186, the satin extremity drop: it used to re-measure a stem its own first pass
had un-branched). That fix holds. The node is still *there* as a pixel — the
promise is kept geometrically. What is not kept is its **degree**: deleting the
third arm drops a 3-way node to 2-way, so every downstream consumer that asks
"is this a junction?" now answers no. The same deletion, a different
consequence, one layer further on.

On `PRECISION`'s `N` the medial axis has a 3-way node at the lower-right
vertex: diagonal 43.11 px, right stem 29.14 px, corner branch 10.66 px. The
threshold is 14.377 px, so the corner branch goes — and the node drops to
degree 2, so it **stops being a node**. The walker runs straight through and
returns one 12.042 mm column that folds ~108°. `_WELD_MAX_DOT = -0.5` (`:93`)
exists for exactly this and **is never consulted**; had it been, it would have
refused (measured arm dot +0.386). `_SPLIT_TURN_DEG = 90.0` (`:100`) under-reads
the fold as 70.1° over its ±1.414 mm baseline, so it doesn't cut either.

Ablation (`_prune_spurs` → no-op, nothing else changed): `PRECISION.N` bare
**12.7% → 4.1%**, `DRONE.N` **18.6% → 0.9%**, `AND.N` **14.0% → 1.3%**.

The same threshold fails the other way on the `H`: a 45° cap arm measuring
10.90 px clears the 10.740 px bar **by 0.027 mm**, survives, and hijacks the
stem spine into the corner.

## #3 — "AND DRONE" is below the size satin can render

Stroke widths (`s12_stroke.py`): `PRECISION` 1.73–2.04 mm at 7.6–8.4 mm caps;
`THERMAL` 1.34–1.52 at 5.72; **`AND DRONE` 0.55–0.70 mm at 2.91 mm caps**
(`DRONE`'s `E` is 0.551, barely over `machine.SATIN_MIN_CROSS_MM = 0.5`).
Trade minimum for satin block lettering is ~5 mm caps and ~1 mm stroke.

The bind, proven by the control: **with** pull comp the line covers but reads
`AИD DROИX`; **without** it the letterforms are right but the letters are
20–39% bare and read `ΛND DRONL`. At this size the pipeline can have coverage
or shape, **not both**. 5 mm caps means sewing at ~138 mm wide, not 80 mm.
Kent's call, parked 2026-08-26 ("address it as we go").

## Mapping Kent's three complaints

- **N's bottom right** → #2, enabled by #1. One connected bare blob of
  **4.387 mm²** at the bottom-right foot, 8.9% of the letter; the mirror-image
  lower-left box is **0%** bare. Both fixes cure it independently.
- **H not crisp** → #1 and #2, and they separate cleanly. Stage 4's polygon is
  *excellent* (13 vertices tracking the edge). What ships adds a 0.3 mm arc at
  every corner plus a scalloped halo of **11.4 mm² = 44.5% of the letter's own
  area**, and tilts the right stem's column ~45° at both ends. **The rounding
  and halo vanish at pull=0; the tilt does not.** So "not crisp" is stage 5 and
  "wrong shape" is stage 6.
- **THERMAL's E** → **#1 almost entirely.** Its arm slots close to 0.336 mm, so
  the three arms are joined before satin ever sees them. **Fixing
  `_prune_spurs` does nothing for this letter.**

## #0 — There is NO stitch-angle policy for satin. Kent found this, we missed it

Later the same day Kent annotated a sewn **Becker Marine** logo (his own client
fixture, `testdata/becker_marine_logo.png` + the pro's
`testdata/reference/becker_*.dst`) with three notes. Two confirm findings above
on a second, real logo. The third is a defect class the 13-agent investigation
never looked at, because it measured *coverage and shape*, not **trade
convention**:

> *"When doing lettering, fill angle should be the same (for almost every block
> style font like this). Why is the 'N' running Vertically?"*

He is right, and it is structural:

- **`satin_shape()` takes no angle argument at all** (`stage6_satin.py:2339`).
- Every cross angle is derived *solely* from that shape's own spine tangent —
  `atan2(b.y - a.y, b.x - a.x) + pi/2` at `stage6_satin.py:1241`, unwrapped and
  smoothed six times. Correct for one isolated stroke; it means **each letter,
  and each stroke within a letter, picks its own angle in isolation.**
- The project already HAS this concept — for the other tier. `fill_angle_deg`
  (`config.py:452`) carries a global default, a per-shape override that "beats
  the global and the per-region PCA", and a PCA fallback. **Satin has no
  counterpart.** Nothing in the code can make a word's letters agree.

So the `N` does not run vertically because of a bug in the `N`. It runs
vertically because nothing ever told it not to, and its medial axis happened to
come out that way — while `R` and `I` beside it happened to come out otherwise.

### Measured against the pro, same logo (2026-08-26)

Kent's observation is now a number. Cross angles measured on stitch LENGTH
(>= 0.8 mm, so underlay and travel cannot wash the signal out), angle mod 180,
from `testdata/reference/becker_*.dst` — the professional digitizer's own file
for artwork we also have. EMB-Bot's side is read straight from the planner's
runs, never through a DST, so the axis bug cannot colour it.

| | modal angle | letter runs within +/-20 deg of it | satin length within +/-15 deg |
|---|---|---|---|
| **Pro**, Becker chest logo, text band | 2 deg | **6/7 = 86%** | 50.7% |
| **EMB-Bot**, same artwork | 92 deg | **9/43 = 21%** | 18.0% |
| *random baseline* | — | *22%* | *~17%* |

**A +/-20 deg window is 40 of 180 degrees, so chance alone scores 22%.
EMB-Bot's letter angles are statistically indistinguishable from random. The
pro's are not.** Per-run means on our side run 113, 24, 75, 77, 83, 22, 22, 22,
35, 179, 175, 26, 178, 149, 8, 67, 90, 90, 154 ... — every stroke choosing for
itself, which is exactly what the code does.

The modal angle held at 2 deg across cross-length thresholds of 0.8 / 1.5 /
2.2 mm, so the pro signal is not an artefact of where the cut is drawn.

**Read the honest limits before quoting this.** The comparison is *not*
perfectly matched: the pro side is restricted to one text band while EMB-Bot's
is the whole logo, and EMB-Bot fragments far more (43 letter-sized runs against
7). The dispersion gap is far too large to be explained by either, but the
exact percentages are not a benchmark. Scripts are KEPT:
`digitizer/tools/letterform_fidelity/{pro_angles,pro_band,pro_house,embot_angles}.py`
(they lived only in a session scratchpad until the end of that session; lifted
in and made portable before it closed). Quote `CROSS_MIN_MM` with any figure —
the modal angle is stable across 0.8 / 1.5 / 2.2 mm but the agreement count is
not (6/7, 6/7, 5/7). Also note the pro spreads about 19 deg across its letters (per-run
means -17 to +2 deg), so the convention is "one angle, held loosely", not a
single rigid value.

**This is a capability gap, not a defect.** There is no constant to change and
no test to fix; it needs a design decision — a house angle for satin-classified
lettering, per word or per design, with the per-shape override `fill_angle_deg`
already models. **No ROADMAP gate blocks designing it** (it changes no physical
constant), but which angle a pro would actually pick, and whether the diagonal
of an `N` is an exception, is Kent's domain call, not geometry's.

### The prerequisite is NOT free — and it fails the same way, a third time

An angle policy needs to know *which regions form a word*. That machinery
already exists and is already wired in: `detect_text_clusters`
(`textcluster.py:618`, called from `pipeline.py:564`) unions similarly-sized,
aligned regions into text clusters and tags them `text_candidate` /
`text_cluster_id`.

**It fires on nothing we care about.** Measured 2026-08-26:

| fixture | regions | `rescued_small_shape` | `text_candidate` |
|---|---|---|---|
| `becker_marine_logo.png` (a real client logo) | 17 | **0** | **0** |
| `drone_render.png` (the wordmark fixture) | 74 | 10 | **0** |

The reason is one line, `textcluster.py:541`:

```python
if not r.meta.get("rescued_small_shape"):
    continue
```

**Only regions that were RESCUED SMALL SHAPES are ever candidates.** Ordinary
lettering — anything large enough to survive segmentation on its own, which is
most real lettering — never enters the candidate set at all. On `drone_render`
candidates do exist (10) and still no cluster qualifies, so widening the entry
condition is necessary but may not be sufficient (`MIN_CLUSTER_MEMBERS = 3`
plus the stroke-CV and aspect filters are next in line).

**Widening was BUILT and then REVERTED the same day** (code at commit
`10ae9cc`, Kent's call). It worked — becker 0 -> 11 letters, drone_render 0 ->
26, and on `enthusiast_logo` it correctly found "ENTHUSIAST" — and moved no
stitches (60 goldens green, 1417 passed). It was backed out because
`text_candidate` also drives a **UI badge and the Convert-to-text flow**, which
the golden suite cannot see: `e2e/text-cluster-convert.spec.js:225` asserts
page-wide that zero badges remain after converting one cluster, true only while
a design has exactly one. And the new cluster carried a false positive — the
star inside the shield, 11 members for a 10-letter word.

**The obvious fix is disproven, so do not spend the hour:** requiring one
thread per cluster excludes the star AND destroys drone_render, whose 23 real
letters span six quantized threads. Gap is the next candidate (6.3 mm vs
0.4 mm) but risks splitting "ENTERPRISES INC" at its space.

A THIRD problem surfaced only in CI: the digitizer job timed out on
`test_review_payload_carries_text_cluster_fields_over_http`, a 60 s `/digitize`
budget that returned `running`. Suspected to be the skeleton cost of screening
many more regions — the failing test is the one most directly about text
clusters — but four CI runs were queued concurrently, so contention is a live
confound. Measure `detect_text_clusters` wall time per fixture directly before
resuming; do not infer it from suite duration.

**The lesson worth carrying past this feature:** a green golden suite proved
only that GEOMETRY was unchanged. Detection metadata drives UI, and nothing in
the Python suite touches it. "No stitch moved" is not "nothing changed".

**This is the same failure shape for the third time in one investigation:**

1. `stage5_overlap.py:424` — the min-feature guard, scoped to `poly.interiors`,
   so it protects `O`'s counter and never tests the `E`'s arm slots.
2. `stage6_satin.py:958` — `_prune_spurs` keeps the node as a *pixel* and drops
   its *degree*, so every consumer asking "is this a junction?" answers no.
3. `textcluster.py:541` — text detection, scoped to rescued small shapes, so it
   cannot see ordinary lettering.

Each is a real mechanism, correctly implemented, **scoped to a subset that
excludes the common case** — and each is invisible to the tests because the
narrow case it does cover works. Worth carrying as a smell, not just three
bugs.

**Weight it accordingly.** Kent's words for this whole class are *"lettering
should be smooth"* and *"ROOKIE MISTAKE"*. Fidelity and coverage — everything
ranked below — cannot see an inconsistent angle at all: a letter sewn at the
wrong angle can score a perfect IoU and full coverage.

## Kent's Becker notes, mapped

- *"We lost the bottom right portion of the R"* → **#2, confirmed on a second
  fixture.** Same corner, same class as every `N` bottom-right. It generalises
  past the `N` and past `drone_render`.
- *"The R Radius is rough and jumpy ... along with the A"* → **#1.** The
  round-join buffer turns a 12-vertex letter into 130 (`THERMAL` `E`) and the
  skeleton is built from that grown polygon, so the spine inherits the wobble;
  the six smoothing passes at `stage6_satin.py:1249` fight it but start from
  bad input. Curves and diagonals show it worst, which is exactly `R` and `A`.
- *"Why is the N running Vertically?"* → **#0 above. New.**

## Two fixes that look irresistible and are not

- **`_SPLIT_TURN_DEG 90 → 70`.** One line, cures all three N's. Breaks
  `test_satin.py:799` and reds the `ribbon_curve.png` byte-identity golden
  (1001 → 1019 stitches) — a key clean today and not a sanctioned exception,
  whose own rule reads *"If this test ever goes red, the change under review is
  wrong — not this test."* The 90.0 is corpus-derived (1,436 in-run corner
  events vs 18 splits across 19 professional files); lowering it makes EMB-Bot
  split more corners than the pros do. **Withdrawn.**
- **Mitre join instead of round.** Keeps corners square but deposits
  `pull / sin(θ/2)` at a corner instead of exactly `pull` — measured 0.4243 mm
  at 90° and 0.9405 mm on a 3.4° wedge, against a preset saying 0.30. Fails the
  repo's own invariant (0.3746 vs 0.3 ± 0.002) and reintroduces a starburst a
  previous fix removed. **ROADMAP gate 1 — blocked until a sew-out.**

## Traps for whoever picks this up

- **The one prototype tried for the #1 fix is a measured mathematical no-op.**
  "Keep the components of `grown − poly` that don't touch the outer boundary"
  leaves exactly one component, sharing 23.038 mm of boundary with the grown
  exterior. Don't repeat it.
- **The `_prune_spurs` fix is prototyped twice and NOT shippable as written.**
  End-to-end it is good — 24 letters, bare **12.54 → 5.84 mm² (−53%), 7
  improved, 0 worse**, machine cost flat. But on a plain square-capped bar the
  guard hooks the spine into the cap corner (45 × 4.5 mm rectangle: last spine
  segment 0.0° → 45.0°). **That is the H defect, propagated to every
  square-capped satin bar.** It regresses `enthusiast_logo.png` and reds
  `test_pushcomp.py:380`. It needs a cap-arm classifier first — a cap arm has a
  tip as wide as the stroke (the N's real corner twig: tip dt 1.667 mm vs a
  0.524 mm bar), so the test exists, it just isn't wired in.
- **Two prototypes of nominally the same rule disagreed off identical
  baselines** — one measured −18.3% (5 worse, 0 better), the other +20.5%
  (4 better, 1 worse). Somebody has to write it once, carefully, before that
  `enthusiast_logo` regression is treated as a blocker.

## Ruled out — do not re-investigate

Stages 1–3 (per-glyph IoU 1.000 for 24 of 27 glyphs, never below 0.995;
`resolve_small_regions` absorbs 0 of 93). Stage 4 `approxPolyDP` /
`simplify_tol_mm` / `min_detail_mm` (worst deviation 0.196 mm against a 0.2 mm
promise; sweeping `min_detail_mm` 1.5 → 0.3 recovers *no* area). Tier
misclassification (all 24 letters correctly route to satin; flat and gradient
are identical by construction — `design_class` branches only against
`_PHOTO_CLASSES`; forcing flat makes it worse, 74 → 350 regions). Forcing
letters to FILL (reads 0.912 on an *ideal* satin bar and its threshold swings
with `fabric.pull_comp_mm`, the coupling `stage7_sequence.py:1197-1203`
forbids). `SATIN_MIN_CROSS_MM` dropping the N's crosses (drops exactly 2 of 54,
both ~9 mm from the fold; at the fold crosses are full 2.93–3.02 mm — the
corner is bare because no spine goes there).

## Unrelated finding, worth its own ticket

On `summit_badge.png`, where glyphs sit on a filled ground, **stage 2 fuses
"U"+"M" and cuts the "S" in half.** Irrelevant to `drone_render` (whose glyphs
are topologically isolated islands with a 64–100% background halo), but real.
