# A design-level stitch direction policy — item 7

**Status: BUILT and measured 2026-09-09, Kent's pick after #438. One flag,
`cfg.design_angle`, DEFAULT OFF and byte-identical off (ten fixtures). No
new constant, no per-shape override — §4.1 is why. Decisions in §7.**

## 0. What already governs this — read before changing the plan

- **The stitch-angle rule** (`docs/stitch-angle-convention-2026-09-03.md`,
  adopted by Kent, cap 30°): for satin lettering the house angle is the
  perpendicular to the stems; a stroke that cannot span it takes its own
  perpendicular; diagonals lean toward the house within the cap, with
  density compensated. For FILL: "lettering that routes to fill takes the
  same house angle (already wired). Non-lettering shapes: the trade default
  is 45° with variation between neighbours; this repo's measured answer is
  fragment-count minimisation over 16 candidate angles" — built as
  `stage6_fill.best_fill_angle_deg`, PER SHAPE.
- **The house angle pass** (`textcluster.set_lettering_house_angle`, DEFAULT
  ON via `satin_house_fourfold`): one angle per line of lettering, written
  to `Region.meta["satin_angle_deg"]` and `["fill_angle_deg"]`, so a word's
  letters agree across both tiers. It fires only on `_lettering_groups`
  (glyph-shaped regions in a line); everything else keeps its own answer.
- **The gradient lane already holds one angle per design** (the 2026-08-03
  angle-fragmentation fix: the design ramp's row angle, or the plain colour
  fit). The flat lane's tatami is the population with no design-level rule.
- **The masters teardown** (`docs/masters-teardown-2026-08-01.md`): "per-
  region PCA angle is our biggest measured quality defect... every letter
  filling at its own PCA angle reads as visible patchwork"; the fragment
  count objective (G3, expired patent) replaced PCA per shape. Item 7 is
  the same objective one level up.
- **The pro-parity scorecard's `direction` component** (20 points: the
  chance-corrected agreement of dominant stitch direction per 2 mm cell
  over the shared solid area; `tools/pro_parity/scorecard.py`) is the
  yardstick the review names. The pro-parity corpus is not in this
  checkout; the five sewn Becker files under `testdata/reference/` are, and
  `tools/design_direction.py --pro` reads them the scorecard's way.
- **Gate 1 does not apply**: an angle is a design choice, as
  `fill_angle_deg`'s docstring says. **Gate 4 does**: every agreement figure
  here is chance-corrected or reported beside its raw value.
- **Carry-forward**: `match_shape_ids` is not wired; `assign_shape_ids`
  re-derives ids and the review resends `shape_overrides` each request, so
  a derived meta key does not survive into the next generation on its own
  (regions.py's docstring). A separate key still keeps the review's
  `fill_angle_deg` distinguishable from a derived one.

## 1. The gap

A flat design's non-lettering fills each choose their own row angle by
their own column count, and adjacent shapes land on different angles. The
review measured Bridge Bar's fills spread across the half-circle where the
pro holds one, and the pro's own Becker files hold one fill angle at every
size. Non-lettering satin gets no cross angle at all: each stroke follows
its own spine tangent, with no lean rule.

## 2. The design

`cfg.design_angle` (DEFAULT OFF), a pass after `set_lettering_house_angle`
in `pipeline.run_stages`, metadata only (`Region.meta["design_angle_deg"]`):

- **The design angle.** Where a lettering house angle was set, the design
  angle is the house angle (area-weighted doubled-angle mean across the
  lines, so a two-line wordmark whose lines agree keeps one number; lines
  that disagree fail the same Rayleigh test the house pass uses and the
  fills keep their own answers). Where no lettering exists and the design
  is on the gradient lane, the design angle is that lane's own shared
  fill-row angle (`design_row_angle_deg`, the ramp fit) — its fills sew at
  it whatever the metadata says, so its satin leans to the same number
  (added after the first corpus sweep leaned the white icon's strokes to
  the objective's 0° against its ramp's 134° rows, §4.5). Otherwise the design
  angle is the one row direction that cuts the design's fill shapes into
  the FEWEST columns in total — `best_fill_angle_deg`'s sixteen candidates
  plus the shapes' area-weighted principal axis (its own seventeenth
  candidate, one level up) and its objective, summed over every fill-tier
  shape instead of scored per shape, ties to the candidate nearest that
  axis. On one polygon at one row spacing a lone fill gets exactly the
  per-shape answer (pinned in the tests); through the pipeline the pass
  reads the stage-4 polygon, since stage 5's comp axis needs the key
  before it runs, so a near-round fill with no real axis can still land
  elsewhere (§4.4). No new constant: the candidates, the row spacing and
  the tie rule are the ones the per-shape function already has.
- **Who takes it.** Every fill-tier shape without a review override or a
  house angle, and every satin-tier shape without a house angle. Stage 7
  reads it after `meta["fill_angle_deg"]` and `cfg.fill_angle_deg` and
  before the directional-comp axis and the per-shape derivation; for satin
  after `meta["satin_angle_deg"]` and `cfg.satin_angle_deg`, so
  `_clamp_to_span` gives non-lettering satin the same lean rule lettering
  has. Stage 5's `_comp_axis` reads it in the same order, so directional
  comp compensates along the axis the shape sews.
- **The per-shape override on strong aspect** the review asked for is
  decided by §4's measurement of the pro, not assumed: if the pro's own
  files hold one angle inside elongated shapes too, there is no override
  and no threshold to invent.

## 3. Instrument first — `tools/design_direction.py`

Per fill-tier shape: the row direction it sewed (length-weighted doubled-
angle mean of its fill segments), area, aspect (principal-moment ratio) and
the angle's source (house / review / cfg / comp axis / derived). Per design:
the number of fills, their area-weighted spread R (1.0 = one angle, 0 =
even over the half-circle), the number of 11.25° bins occupied, the modal
angle, the house angle; non-lettering satin counted with whether it was
handed a cross angle. `--pro FILE` digitizes at the pro's width, registers
the pro's stitches into our frame with the scorecard's own search, and
reports the pro's spread over its solid cells, ours, the chance-corrected
`direction` agreement over the shared cells, and the pro's direction inside
each of our fill shapes against that shape's aspect. `--compare` runs
OFF/ON; `--corpus` the 26 scorecard fixtures at 80 mm.

## 4. Results — measured 2026-09-09

### 4.1 The pro holds one angle, at every size, in every shape

`--pro` on the three Becker files that share the artwork (registration IoU
0.61–0.63, no flip):

| pro file | width | pro spread R (its solid cells) | modal | inside the slab (aspect 2.5) | inside the small fills (aspect 1.5–2.0) |
|---|---|---|---|---|---|
| chest_small `logo_lc_2_a` | 76.5 mm | 0.527 | 19.1° | — (routes to satin at this size) | 14.2° (R 0.95) |
| hat_polo_large `logolc` | 95.7 mm | 0.565 | 18.3° | 20.5° (R 0.53, 271 cells) | 12.6–13.0° (R 0.95–0.97); 3.6° on a 3-cell fill |
| hat_polo_large `logo_hat` | 101.9 mm | 0.569 | 19.5° | 20.6° (R 0.58, 320 cells) | 12.8–13.6° (R 0.96–0.97) |

The pro's R over ALL its cells is 0.53–0.57 because its MARINE letters are
per-stroke satin (R 0.11–0.45 inside each letter's cells, five letters);
its fills are at one angle everywhere — the slab of aspect 2.5 and the
27–44 mm² fills of aspect 1.5–2.0 within 8° of each other. **So there is
no per-shape override on aspect and no threshold**, as §2 left open.

### 4.2 Becker OFF → ON at the pro's three sizes

Prediction (§2): R → ~1.0 and `direction` up, at a stitch cost from the
slab's columns. Measured (`--compare --pro`, chance-corrected `direction`
beside its raw agreement and the within-20° share, gate 4):

| width | fills | spread R OFF → ON | bins | `direction` OFF → ON (raw; within 20°) | stitches | trims | the design angle |
|---|---|---|---|---|---|---|---|
| 76.5 mm | 2 | 0.777 → 1.0 | 2 → 1 | 0.388 → 0.41 (0.694 → 0.705; 52 → 53%) | 4,590 → 4,523 (−1.5%) | 38 → 39 | house 178.4° (lines 178.1 / 178.8) |
| 95.7 mm | 9 | 0.15 → 0.999 | 2 → 1 | **0.0 → 0.289** (0.429 → 0.644; 25 → 42%) | 10,558 → 11,006 (+4.2%) | 27 → 22 | house 179.3° (2.2 / 177.2) |
| 101.9 mm | 8 | 0.221 → 0.995 | 2 → 2 | 0.0 → 0.249 (0.432 → 0.624; 25 → 36%) | 11,498 → 12,221 (+6.3%) | 27 → 25 | house 175.5° (169.6 / 179.7) |

OFF at 95.7 mm the slab sews at 90.0° and the three small fills at 85–91°
against the five MARINE fills' house at 2.3°; ON every non-house fill
sews at 179.2–179.3° (the sewn direction within 0.1° of the argument —
`_fill_angle_for` reaches all five `stitch_shape` sites). The stitch cost
is the slab's columns (58 at 0°, 50 at 90°): the price of one angle, which
the pro's file pays at its 20° too (202 columns by our objective).

**What the remaining gap is.** ON, ours is one angle at 179° and the pro's
is one angle at 20°: the within-20° share is 42% and not 90% because the
two angles differ by 21°, not because ours spreads. The house is the
nearest constant-free candidate (§0's list, DOCTRINE 2026-09-09); the
last 20° is a house-style number — §7.1.

### 4.3 The forced-flat real logos: the rule-1 designs

`--flag forced_class=flat` at 80 mm, where the real logos become tatami
fills (routed, every one of them takes the gradient lane at this size and
has NO `stitch_shape` fill — §4.5):

| design | fills | spread R OFF → ON | bins | stitches | trims | design angle |
|---|---|---|---|---|---|---|
| gaulke roofing | 4 | 0.985 → 1.0 | 2 → 1 | 9,964 → 10,715 (+7.5%) | 32 → 31 | house 155.2° (153.5 / 179.6) |
| golden tee | 0 (64 satin, 49 non-lettering) | — | — | 9,082 → 8,934 (−1.6%) | 134 → 136 | house 38.1° (31.4 / 39.7) |
| hotel fremont | 5 | 0.94 → 1.0 | 3 → 1 | 9,893 → 10,283 (+3.9%) | 46 → 49 | house 155.5° (154.2 / 177.8) |

Gaulke is the cost case: its 2,406 mm² card ground was already at one
angle among its fills (0.985) but at 0°, the ground's own column optimum;
the house rule moves it to the lettering's 155° for +751 stitches. Golden
Tee has no fill at all: its 49 non-lettering satin strokes take the lean
rule and sew fewer, longer crosses.

### 4.4 The rule-2 designs: no lettering, the design-wide column objective

| design | fills | spread R OFF → ON | bins | stitches | trims | design angle |
|---|---|---|---|---|---|---|
| bridge bar, forced flat | 15 | 0.781 → 1.0 | 10 → 1 | 15,778 → 15,368 (−2.6%) | 170 → 167 | 135° (39 satin strokes leaned) |
| script tires, forced flat | 1 (15.7 mm², aspect 1.05) | 1.0 → 1.0 | 1 → 1 | 2,221 → 2,212 | 10 → 9 | 126.4° (the principal axis; per shape it was 160.3° — a near-round blob, a tie at every angle) |
| photo chrome specular | 12 | 0.481 → 1.0 | 6 → 1 | 34,950 → 35,341 (+1.1%) | 89 → 86 | 0.0° |
| photo scene stub | 8 | 0.419 → 1.0 | 6 → 1 | 16,170 → 16,281 (+0.7%) | 42 → 49 | 90.0° |
| photo sunset backlit | 8 | 0.743 → 1.0 | 3 → 1 | 23,950 → 24,356 (+1.7%) | 48 → 48 | 90.0° |
| photo dof meadow | 10 | 0.91 → 1.0 | 6 → 1 | 19,845 → 19,830 (−0.1%) | 40 → 37 | 101.2° (the principal axis — its three big fills were already there) |

Bridge Bar is the review's own example and the one that reproduces its
"spread across the half-circle": ten of sixteen bins OFF — the sky at
90°, the script inside it at 124°, the water's small fills anywhere —
one bin ON, at fewer stitches (the leaned satin sews fewer, longer
crosses; the fills' columns cost less at 135° than the sky's own 90° plus
the script's own 124° did together). The photo classes are the flag's
live population at 80 mm (§4.5); they take rule 2 because they carry no
lettering, at +0.7–1.7% stitches and trims moving both ways — the +7 on
scene stub is the one clear cost. Whether a tonal design's fills SHOULD
share one angle is §7.2; there is no pro photo file here to score it.

### 4.5 The corpus at 80 mm — the flag's live population is satin

`--corpus` OFF and ON over the 26 scorecard fixtures at the Studio's 80 mm:

| | OFF | ON |
|---|---|---|
| stitches, 26 fixtures | 316,271 | 316,026 (−0.08%) |
| trims | 899 | 900 |
| designs unchanged | — | 7 (no satin, and fills already at one angle or no taker) |
| designs moved | — | 19 |

**Routed at 80 mm no real logo has a tatami fill**: every one takes the
gradient lane, whose fills already share the ramp's angle (2026-08-03)
and never reach `stitch_shape`. So outside the four photo fixtures (§4.4)
the flag's whole effect at this size is non-lettering satin taking the
lean rule — fourteen designs, 1 to 29 strokes each, −2.3% (ENTHUSIAST's
12, Becker's 4) to +0.2% (drone's 22) stitches, trims −3 to +3. That is
the population the review's "spread across the half-circle" did NOT
describe, and why the forced-flat rows of §4.3–4.4 are the ones that
show the fills moving.

**The lane rule, found here.** The first sweep gave every gradient-lane
design the column objective over polygons the lane fills at its own ramp
angle: `repro_gradient_white_icon`'s four strokes leaned to 0° while its
rows run at 134°. Rule 2 (§2) now hands the lane's own shared angle to
the satin where the design holds one — the white icon moves to 134.4°
(−83 stitches for its four strokes instead of −20, +2 trims → 0); a
gradient design whose ramp the fit refuses (drone, whose blend fills
derive per-region angles) has no lane angle and keeps the objective. No
other fixture moved between the two sweeps.

### 4.6 Rendered — looked at

`docs/renders/design-direction-2026-09-09/becker-95mm-off-on-pro.png`:
OFF, the BECKER slab's rows run vertically while MARINE's run at the
house; ON, the slab's rows turn to MARINE's angle and the sheet reads as
one direction; the pro's panel (registered into our frame) is one
direction too, leaning ~20° the other way from horizontal.
`bridge-bar-flat-80mm-off-on.png` (the review's example, forced flat at
80 mm): OFF, the sky fills with vertical rows, the "Bridge" script inside
it at its own ~124°, and each of the small fills in the water at its own
angle; ON, sky, script and small fills all run at the design's 135°. The
wheel's rim and spokes (satin, grey) are the same crosses at this scale —
the lean is at most 30° and fades where the angle runs along the stroke.
One thing the sheet shows that the numbers do not: with the sky and the
script at one angle, the script no longer stands off its ground by
direction, only by its outline and colour — which is how the pro's Becker
separates them too (one angle, §4.1), but it is a look for Kent to judge.

## 5. Non-regression

- **Byte identity OFF** (`railcomp/byte_identity.sh`, HEAD `3345317`
  against the work tree, `PipelineConfig()` defaults): whitebg, alpha,
  ribbon, becker, fremont, drone, enthusiast, gaulke, sunset, meadow —
  ten of ten identical in stitches, trims and every shape's stitch count.
- `tests/test_design_angle.py` (7): OFF writes no key; the house rule
  (two lines 5° apart → one angle; 60° apart → none); the design-wide
  column objective on two combs (alone 90° and 0°, together 90°) and its
  one-fill parity with `best_fill_angle_deg`; the pass skips review,
  house and run-tier shapes and writes the slab and the bar; the gradient
  lane's shared angle beats the objective and loses to a house (folded to
  [0, 180)); Becker at 95.7 mm ON sews every fill within 3° of the house;
  Becker OFF is byte-identical to a config without the flag.
- `test_scope_budget` / `test_doc_claims` after the doc edits; flake8
  `--select=E9,F63,F7,F82` clean.
- **Full digitizer suite on the final tree** (`python -m pytest -q -n auto`,
  27:02): 2181 passed, 3 skipped, 7 xfailed, **3 failed — exactly the three
  platform reds CI deselects** (`test_flat_lane_byte_identical` and
  `test_stage2_photo_segment` on enthusiast, `test_pushcomp` whitebg-towel);
  the same three, 2180 passed, on the tree before the lane step.

## 7. Decisions — Kent's

1. **The ~20° house-style offset.** The pro's fills sit about 20° off the
   lettering's cross at every size (§4), and nothing constant-free derives
   that number: the house angle is the nearest candidate (2° here) and the
   flag stops there. Putting the offset in — "fills at the house angle plus
   a fixed lean" — would be the first taste constant in the angle code. Not
   gate 1 (an angle is a design choice), but the "no new constant" brief
   forbids it without a ruling. Options: leave it; add it as a config field
   with the pro's 20° as its default; or read it off more pro files first
   (the five Becker files are one digitizer's habit).
2. **Photo classes.** The flag applies to every class as built; on the four
   photo fixtures it moves 8–12 fills each onto one angle at +0.7–1.7%
   stitches, one of them +7 trims (§4). There is no pro photo file to score
   it against, and a tonal design's fills following one angle is a look, not
   a measurement — the thin-stroke flag gated photo classes out on a
   measured loss; this one has no such loss to point at, so it is not gated.
   Gate them out, or leave the one rule.
3. **Non-lettering satin under the lean rule.** The review asked for it and
   it is built: a border stroke, a ribbon, a swoosh now leans its crosses
   toward the design angle within the 30° cap and fades to its own
   perpendicular where the angle runs along the stroke (`_clamp_to_span`).
   Fewer, longer stitches (Bridge Bar's 39 strokes: −2.6%; Golden Tee's 49:
   −1.6%, +2 trims). The render (`docs/renders/design-direction-2026-09-09/
   bridge-bar-flat-80mm-off-on.png`) is where to judge it; the pro's own
   MARINE letters read as per-stroke crosses (R 0.11–0.45 inside each
   letter's cells), so the pro leans lettering less than a house rule does,
   and non-lettering satin is not measured against any pro file here.
4. **Flipping it.** DEFAULT OFF, byte-identical off across the ten fixtures.
   ON it costs +4–6% stitches on Becker at 96–102 mm (the slab's columns:
   the price of one angle, which the pro's file also pays) and −1.5% at
   76.5; trims move both ways by a few. Judge it on the two renders.
