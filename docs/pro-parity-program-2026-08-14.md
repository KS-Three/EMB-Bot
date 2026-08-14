# Pro-parity program — state, findings, and what to do next (2026-08-14)

Goal: compare EMB-Bot's digitizing against 23 professionally digitized files and
improve piece by piece toward 95% parity. Corpus built from the `Embroidery
Files.zip` Kent pushed to the repo (commit `9f81a83`).

This file is the index and the current recommendation. The evidence lives in:

- `pro-parity-measurements-2026-08-14.md` — every number, on all 23 designs
- `pro-parity-judge-report-2026-08-14.md` — independent judge over 5 lanes
- `pro-parity-lane-reports-2026-08-14.md` — the 5 lane self-reports, verbatim
- `pro-parity-engine-work-2026-08-14.patch` — the engine commits (see §6)
- `digitizer/tools/pro_parity/` — the harness and every diagnostic instrument

---

## 1. The headline recommendation

**Do not land the lane-B merge (`070a113`) as it stands.**

It does the thing it was built to do — it removes a real family of satin
starbursts, and it fixes an outstanding bare-fabric regression at the exact
coordinate that regression was recorded at. But measured across all 23 designs
it raises total bare fabric by **6.1%**, with two designs losing 20-30 mm² and
five designs' largest hole growing. Scorecard is -0.20.

This contradicts the judge's recommendation, and the reason is worth keeping:
**the judge measured the scorecard and a fan metric; neither instrument sees
bare fabric.** Coverage in the scorecard is a whole-design IoU, so a 5 mm² hole
inside an otherwise-covered letter barely registers. Bare fabric is what ruins
a physical sew-out. When the two disagree, bare fabric wins.

The work is not wasted — see §4 for what it established and §5 for the fix that
would make it landable.

## 2. Where things stand numerically

| | value |
|---|---|
| Corpus mean, shipped weights | **70.92 / 100** at `3a1f673` (target 95) |
| Corpus mean, chance-corrected | ~53.4 |
| Best designs | machine_lc 80.3, machine_hat 80.3, gaulke_roofing_lc 79.8 |
| Worst designs | tires_hat_3d 53.5 (3D foam, unimplemented), hotel_fremont_patch 57.6, mfab_hat/precision_drone ~63 |

**The scorecard's most important caveat:** `direction` and `sttype` sit near a
~0.50/0.49 CHANCE FLOOR. About 20 of their 40 points are paid for answers
uncorrelated with the pro file. Use the chance-corrected number to judge real
progress. Rescaling the components would re-base every historical score, so it
needs an explicit decision before anyone does it.

**Second caveat, arguably bigger:** the corpus artwork is *reconstructed from
the pro's own stitches*. That flatters us by roughly +10-18 points (measured on
`hotel_fremont_patch`, the only design with real source art). True real-world
parity is likely ~43-53 chance-corrected.

## 3. The key reframe — what the defect actually is

Four iterations were spent on "the metrics are fine but the render looks
shattered." Two findings resolved it:

1. **The starburst is largely a RENDER ARTIFACT.** At 1px hairlines the letters
   look destroyed; re-rendered at real thread width (0.5 mm) the same letters
   are 87-90% covered and legible, with max rotation between consecutive
   crosses of 4.7° and rails advancing 0.35-0.70 mm. That is a well-behaved
   column, not a fan.

2. **The real deficit is stitch TYPE, not geometry.** `becker_lc_large` scores
   coverage 0.91 but direction 0.60 and sttype 0.55 — the pro *fills* letters
   where we *satin* them, including the MARINE wordmark (pro block 3, len_p50
   2.64 mm, row spacing 0.4 mm).

So fill-vs-satin **routing** for bold display lettering is worth ~40 of 100
points and is the highest-value remaining work. Satin geometry polish is not.

## 4. What the five lanes settled

Five independent approaches to the starburst, measured identically, then judged
by an agent that re-derived every number from scratch. **All five lanes'
self-reports reproduced exactly in the judge's hands** — worth stating after
three prior iterations of over-claiming.

| Lane | Idea | Verdict |
|---|---|---|
| **B** | never build a column on a corner fork | real, narrow, +0.08 held-out |
| D | route letterforms to one-angle fill | real but **overfit**: +1.76 tuned, **-0.60 held-out**, two ~6pt regressions |
| C | sew the junction as its own patch | noise; fan metric *worse* on 3/5 |
| A | directional cross-section width | honest negative, 7 new golden failures |
| E | outline rail-pair decomposition | honest negative, structurally can't cover a letterform (57% area) |

**Ruled out — do not redo:**

1. The starburst is **not** a width-measurement error. Proven twice by opposite
   methods: A showed `field.half_at` never binds (it feeds a cap that never
   engages; it actually sets the TRIM DISTANCE), and E supplied a perfect
   junction-immune width and the design still fanned.
2. Outline rail-pairing cannot cover a letterform. Structural, not tuning.
3. Per-stroke directional fill is dead — pro direction vs our stroke tangent
   deviates 44-52°.
4. No junction radius / arm-width ratio can classify a junction as a blob: a
   right-angle meeting of equal ribbons is intrinsically √2 wider, so a clean T
   and a bold corner measure the same.
5. A single global letterform fill angle is not the lever; per-shape principal
   angle scores *worse* than the 20° constant on both tuned and held-out sets.
6. Junction-GRAPH correctness is not the cause — two real graph bugs were fixed
   and the render was pixel-for-pixel unchanged.
7. Forcing all detected text through satin is wrong; the pro picks per element.

## 5. What would make lane B landable

Lane B's mechanism is sound and its fork classifier is the right *shape* of fix
— it is what finally closed the `hotel_fremont_patch` regression, because it
removes forks **before welding** and hands the corner to a named arm instead of
just deleting geometry. The problem is that the handoff is never verified.

**The fix is a coverage precondition, one level up from where it was applied
before:** before dropping a fork, confirm the corner it occupies is actually
reached by the *emitted crosses* of the arms it grew from — not by their
polygons, and not by a length bound. This is the same prescription that closed
the last regression; it simply needs to apply to lane B's own drop as well.

Two ablations narrow the target considerably (§5 of the measurements doc):

- The **3.77 mm² hole on `mfab_lc` IS the fork drop** — it vanishes when the
  classifier is disabled.
- The **5.40 mm² hole on `mfab_lc` is NOT** — it survives with the classifier
  off, so it comes from lane B's cap/weld changes. Retuning
  `_FORK_NODE_MULT` to chase it would be tuning the wrong constant.

Lane B's own risk list flagged that `_FORK_NODE_MULT = 1.7` sits between
populations that *touch* below 2 mm stroke width, so tagline-scale text is
where it misclassifies. That matches where the damage lands.

## 6. The engine work, and how to get it back

Four commits sit on branch `claude/pro-parity-loop`, which is a clean
descendant of `9f81a83`. They are preserved here as
`pro-parity-engine-work-2026-08-14.patch` (`git am` or `git apply`):

| commit | what it does | status |
|---|---|---|
| `2c49a96` | thread-mislabeling fix — 22/96 blocks shipped under the wrong cone NAME across 6 designs, plus the harness truth pass | **safe, zero stitch changes** |
| `c91ab60` | density-targeted fill (gated OFF via `PipelineConfig.fill_density_boost`) + satin fabric density parity (ships live) | corpus 69.37 -> 70.62 |
| `3a1f673` | satin arm starts where its own ribbon does, not at the junction blob radius | corpus 70.62 -> 70.92, **carries the bare-fabric regression** |
| `070a113` | lane B corner-fork removal, twig drop deleted | **do not land — see §1** |

`2c49a96` is a genuine bug fix with no stitch-level consequences and is the one
piece here that could land on its own merits.

## 7. Methodology lessons — hard-won, do not relearn

- **A score gain with the defect still visible is a FAILURE.** Always read the
  rendered PNG. Correspondingly: a metric that doesn't move is not proof a
  change did nothing — check whether that metric can even see the defect. Both
  errors happened in this program.
- **Any satin demo must call `satin_shape(p.polygon, ...)` on the STAGE-5 GROWN
  polygon under harness config** — not `extract_strokes()` on the artwork
  polygon under `PipelineConfig()` defaults. The latter shows 8 strokes where
  the shipped path has 3. One iteration's headline proof was invalidated by
  exactly this.
- **Never pipe pytest to `tail`** — you get tail's exit code. Redirect to a
  file and check `$?`. Full suite is ~16-24 min; baseline is 7 pre-existing
  failures (5 tesseract-dependent, 2 `enthusiast_logo` platform goldens).
- **Parallel agents must use separate `PRO_PARITY_OUT` dirs** or they corrupt
  each other's numbers.
- **Validate on ≥12 designs, not 5.** Lane D looked like the winner at +1.76 on
  five tuned designs and was -0.60 on seven untuned ones. This is the single
  most expensive lesson in the program.
- Model switches and container restarts kill running workflows; resume with
  `Workflow({scriptPath, resumeFromRunId})` and completed agents replay from
  cache.

## 8. Next steps, in priority order

1. **Fill-vs-satin routing keyed on a real measurement**, not a proxy. Lane D
   proved the corpus answers this — pro direction-coherence R runs 0.53-0.98
   against our 0.07-0.34 — and then threw the measurement away in favour of a
   "≥3 skeleton strokes and ≥2.2 mm width" rule that fires on script wordmarks
   the pro satins. Build the rule on the measurement. Validate on ≥12 designs.
2. **Add the coverage precondition to lane B's fork drop** (§5), then re-measure
   bare fabric across all 23 before considering it landable.
3. Land `2c49a96` (thread mislabeling) on its own merits.
4. Decide the direction/sttype chance-floor rescaling — it re-bases every
   historical score, so it needs an explicit call.
5. Un-bias the corpus: reconstructing art from pro stitches flatters us
   ~+10-18 points.
6. Density boost stays gated OFF pending a physical sew-out sign-off; turning
   it on requires re-baselining ~15 golden tests across 6 files.

Unattacked by any lane so far: **small text.** `hotel_fremont_patch` and mfab's
tagline are unchanged in all five. FREMONT's problem is upstream art
reconstruction merging letters into blobs, not satin at all.
