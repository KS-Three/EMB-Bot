# The house angle, and four thresholds measured on the wrong population

2026-08-27/28. Kent's complaint on a sewn Becker Marine logo — *"When doing
lettering, fill angle should be the same. Why is the 'N' running Vertically?"* —
took four layers to reach, and **every layer was the same mistake in a different
place: a threshold that was correct for the population it was calibrated on,
applied to a population it had never seen.**

That pattern is the transferable part. The lettering fix is downstream of it.

## The pattern, with all four instances

| threshold | calibrated on | applied to | what it did |
| --- | --- | --- | --- |
| `rescued_small_shape` | glyphs `resolve_small_regions` saved from being dropped as noise | real lettering | **0 of the Becker logo's 17 regions carry it.** Text detection sees no ordinary lettering at all |
| `STROKE_CV_MAX` = 0.32 | rescued blobs (simple, taper-dominated) | real glyphs | all 17 regions score **0.36–0.68**. A letter's skeleton runs through junctions a blob's does not, so its width variance is genuinely higher |
| `COHERENCE_FALLBACK_MIN` = 0.25 | a per-pixel structure-tensor field | glyph skeletons | real lettering sits UNDER it (R = 0.197, 0.203) while deriving correct angles |
| the IoU "ceiling" reasoning | — | small letters | normalising by it does not help: DRONE's `E` is 92% of its ceiling while sewing as a visible **"L"** |

**I introduced the third one myself**, in the first PR of this pair, for exactly
the reason the other two existed: it looked like the same question. It is not
enough to know about this failure mode; I walked into it the same day I
documented two instances of it.

**The tell**: a gate that is *supposed* to find something, finding nothing, on
input that obviously contains it. Do not conclude the input is unusual. Measure
the gate's own statistic across the population it is being asked about, and
compare that to the population it was tuned on.

## The other recurring shape: a lever built and never pulled

`stage6_satin` grew `satin_shape(angle_deg=...)` on 2026-08-26 — clamp,
config field, per-region meta, the lot — and **nothing ever set it.** Both
levels defaulted to `None`, which is the per-stroke-tangent behaviour it was
built to replace, so the sewn output never changed and MASTER_SCOPE still said
"`satin_shape()` takes no angle argument".

Then, once wired, the first version was **inert on real artwork** (it rode the
`rescued_small_shape` gate above) and byte-identical before/after on the very
logo the complaint came from. **Rendering it is what caught that**, and only
because Kent asked for a render before merging. Green tests, green CI, 9/9
mutations killed, and zero effect.

So: when a feature is "done", check that it FIRES on the artwork it was built
for, not just that its tests pass.

## What shipped (PRs #282, #283)

One house angle per line of lettering, on **both** the satin and fill tiers.

- Grouping is `_lettering_groups` in `textcluster.py`, independent of
  `detect_text_clusters` (whose candidate set is empty on real lettering, above).
  A 0.8 height floor keeps a logotype's two lines apart — at the module's own
  0.5, MARINE's 13 mm capitals merged with the arched BECKER (18–27 mm) into one
  11-member group whose strokes cancelled to nothing.
- The gate is **Rayleigh's test** in doubled-angle space, `n_eff·R²` against
  `−ln(α)` with α = 0.001, `n_eff` being Kish's effective sample size. **No raw
  threshold can work here**: directionless square rings sit at R = 0.167 and
  real lettering at 0.197. *(Correction 2026-09-02: that ring figure is a
  degenerate fixture — 2.5–3.5 mm of corner-arc remnant per ring survives
  pruning; true annuli read 0.008. The n_eff argument now rests on the
  3-bar vs 4-bar fan pair in `test_textcluster.py`; see
  `hotel-fremont-fine-details-2026-09-02.md`.)* Chance-corrected they are 10× apart. This is ROADMAP
  gate 4 in miniature.
- The null was **checked, not assumed** — circular annuli score R = 0.0081 and
  stay rejected to n_eff ≈ 20,000.
- **7 of 11 lettering regions sew as FILL**, where `satin_angle_deg` is not read
  and `best_fill_angle_deg` picks rows per shape by minimising that shape's own
  column count. That put two adjacent near-identical capitals at 22.5° and
  90.0° — the "N running vertically", one tier over, and the half the complaint
  actually names.

Measured on the Becker logo: strokes within ±20° of the modal direction
**29% → 51%** (chance 22%), **total thread −2.4%**, trims and jumps unchanged.
Aligning crosses to a near-perpendicular house angle makes them SHORTER.

**Calibrated on two lettering groups from one logo.** It is live on `main` and
shipping in every digitize. Validating it against real client artwork and
`scratch_corpus/` needs Kent's Windows box and has not happened.

To regenerate the before/after render: patch `pipeline.set_lettering_house_angle`
to a no-op, `digitize()` the fixture, then `adapter.plan_to_design` →
`stitchviz.render_png_bytes`.

## Also from this session

- **The exterior-notch guard is built, costed, and PARKED** — Kent's call. It
  fixes an `E`'s arm slots sealing (0.936 → 0.336 mm) but reds the chaining trim
  benchmark, 3.8 → 6.4 trims/1k against a 4.1 ceiling, because restoring a notch
  breaks the gap chaining was bridging. It trades a MEASURED trim regression
  against an UNMEASURED fidelity gain. Patch and both directions:
  `docs/exterior-notch-guard-2026-08-28.md`.
- **The letterform instrument is half rebuilt** (`tools/letterform_fidelity/
  stroke_coverage.py`). Coverage and IoU are blind for one reason — **they
  average, and deformation is local** — so it reports the WORST medial-axis
  stroke. DRONE's `E` reads 58.3% worst against 72.7% mean. **Still blind to
  tilt**, and the obvious tilt metric was built and REJECTED the same day: it
  ranks a good `O` (31.7° median) worse than the deformed `H` (16.6°), because
  on a curved letter "perpendicular to the local spine" confounds curvature with
  deformation. The untried candidate is the satin RAILS as the reference.
- **`_prune_spurs` should wait for that tilt metric.** Its documented failure
  mode is the `H` defect propagated to every square-capped satin bar — i.e.
  precisely what nothing can currently measure. Two prototypes of nominally the
  same rule already measured −18.3% and +20.5% off identical baselines.
  Attempting it now means judging a fix by an instrument that cannot see what it
  breaks, which is how you get a third disagreeing number.
- **Auto-merge works now** and its two conditions are in CLAUDE.md footgun #7:
  mark the PR ready for review FIRST (a draft refuses with a third distinct
  error), and arm it while `mergeable_state` is `blocked`, not `unstable`.

## Process notes that cost time

- **Editing source while a background `pytest -n auto` runs invalidates the
  run.** Did it twice; killed and restarted both times rather than trust the
  result.
- **A crashed mutation script left a mutation IN the source**, and the next
  battery captured that as its baseline — two results were measured against
  poisoned code and read as "killed" when the tests were failing for an
  unrelated reason. Re-run from a verified-clean baseline before believing a
  battery.
- **`flake8 .` from `digitizer/` scans `.venv`** and reports ~129 findings from
  scipy and matplotlib. CI has no venv there. Use `--exclude=.venv,__pycache__`.
- A fourth digitizer failure beyond the three known goldens is a real
  regression — and confirming it means re-running those three WITHOUT the change
  and comparing the exact assertion values, not just the test names.
