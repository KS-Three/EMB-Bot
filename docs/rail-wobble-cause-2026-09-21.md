# Why satin rails wobble: a ray that cannot tell "wider here" from "escaped into the next arm"

Measured 2026-09-21 on `origin/main` at `b14c0a95`, in a temp worktree, with
the main checkout's `.venv`. Diagnosis only — **no engine change, and the two
probes below were written into a throwaway worktree, not the repo.**

Kent's question was the one from 2026-09-19: *"right shapes, bad edges"*, and
`edge-wobble-is-satin-rails-2026-09-19` left **"WHY rails wobble"** open.

## 0. First, a framing that was wrong — including in this session's own opening

The 2026-09-20 bisect names ~0.0069 of the `lost_frac` residual as the
symmetric-offset rail model, `rail_edge` reading **17.6%** of
`enthusiast_logo`'s rail points more than 0.1 mm INSIDE the art. It is
tempting — it was tempting here — to read that, `edge_wobble`'s inward worst
points, and Kent's eye as three views of one defect.

**They are not.** PR #536 (open, and see §5) measures `enthusiast` as **0%
unsewn / 100% overshoot**: 3.5 mm² of its 395.5 mm² of ink carries no thread
(0.90%), largest component 0.88 mm², and thread covers **1.51×** the ink. Its
conclusion — *"there is no coverage there to recover, and closing that item
pushes the headline up"* — stands against anything below. Coverage and
smoothness are different questions on this fixture, and only smoothness is
open.

## 1. The measurement, today, on three real logos

`tools/edge_wobble.py`, default config (`pique_knit`, `pull_comp_mm` 0.30):

| fixture | tier | n | std | p95 | >0.15 mm | **offset** |
|---|---|---:|---:|---:|---:|---:|
| enthusiast | line | 535 | 0.000 | 0.000 | 0.0% | **+0.00** |
| enthusiast | fill | 105 | 0.010 | 0.007 | 0.0% | **+0.30** |
| enthusiast | **satin** | 828 | **0.089** | 0.198 | 8.7% | **+0.25** |
| becker | fill | 152 | 0.010 | 0.011 | 0.0% | +0.30 |
| becker | **satin** | 2402 | **0.092** | 0.189 | 8.2% | **+0.25** |
| gaulke | fill | 364 | 0.019 | 0.043 | 0.0% | +0.30 |
| gaulke | **satin** | 1581 | **0.070** | 0.138 | 4.4% | **+0.24** |

**The sign is settled and it is OUTWARD.** Satin sits a mean +0.24 to +0.25 mm
outside the artwork — the pull compensation, landed slightly short. The worst
individual points are inward (−0.78, −0.87, −0.95 mm), i.e. they dip about a
millimetre BELOW that pedestal. Mean outward, tail inward: the same "two
opposite defects" #536 names, visible in one row.

**The control is the other two tiers.** `line` reads std 0.000 / offset +0.00
and `fill` reads std 0.010–0.019 / offset **+0.30 exactly**, on the same
designs, same fabric, same pull comp. Only satin misses its own pedestal
(0.25 against 0.30) and only satin has variance.

Zones reproduce 2026-09-19 — corners 5–7× mid-column:

| fixture | corner >0.15 | end | mid |
|---|---:|---:|---:|
| enthusiast | **19.2%** | 8.0% | 2.1% |
| becker | **14.6%** | 10.1% | 3.4% |
| gaulke | **12.0%** | 3.2% | 1.8% |

## 2. Hypothesis 1 — the width profile's low-pass filter. REFUTED

`_rail_points` median-filters the half-width (window 5) then runs **4** mean
smoothing passes. A low-pass filter cannot follow a local maximum, and a
corner is a local maximum of the corridor — so relaxing it should collapse the
corner zone.

It does the opposite. `enthusiast_logo`, one variable at a time:

| arm | satin n | std | p95 | offset | corner> | end> | mid> |
|---|---:|---:|---:|---:|---:|---:|---:|
| shipped (5, 4) | 828 | 0.089 | 0.198 | +0.25 | 19.2% | 8.0% | 2.1% |
| no smoothing (5, 0) | 847 | 0.090 | 0.196 | +0.27 | 17.5% | 8.4% | 3.3% |
| no median (1, 4) | 762 | 0.095 | 0.211 | +0.23 | **26.0%** | 6.4% | 1.0% |
| neither (1, 0) | 823 | 0.103 | 0.230 | +0.28 | 18.1% | 10.9% | **5.7%** |

**The filters are REDUCING the wobble, not causing it** — dropping the median
filter costs 7 points of corner share, dropping both costs 0.014 of std. Do
not go tuning `_WIDTH_MEDIAN_WINDOW` or `_WIDTH_SMOOTH_PASSES` to fix edges.
(Caveat: the arms move the satin point count 762–847, so these are not
perfectly matched populations; the direction is consistent, the third decimal
is not.)

## 3. What the rail position actually depends on

Per station `_rail_points` casts **two rays** along the cross direction
(`nx, ny = cos(angles[i]), sin(angles[i])` — the leaned cross, so there is no
cosine error here) and keeps

    raw = min(dist(station, pa), dist(station, pb))

against `boundary = poly.boundary` — **the whole region's boundary, not the
stroke's**. With `satin_rails_follow_edge` OFF (the default) both rails are
then placed at that minimum. The file says so itself: *"The symmetric profile
above is the NEARER edge at every station."*

Measured, `enthusiast_logo`, 60 strokes / 653 stations (`_probe_sides.py`):

    near-edge half-width      mean 1.102   median 1.096 mm
    |side_a - side_b|         p50 0.141   p75 0.437   p90 1.485   p95 2.022
                              mean 0.439   std 0.707   max 5.242
                              over 0.15 mm  48.7%      over 0.30 mm  34.8%

**Half of all stations have their two rays disagreeing by ≥ 0.141 mm on a
1.10 mm half-width — 13% of the column's own half-width — and in the tail they
disagree by more than the entire half-width.**

That tail is not off-centredness. It is the ray escaping through a junction
into another arm, which the code already knows about (*"a ray that escapes
through a junction into the next arm reports a distance belonging to a
different part of the shape, and it is always the longer of the pair"*). So
**48.7% must not be read as "48.7% of rails are short by that much"** — the
`min()` is a real defence, and this probe cannot separate a genuinely
off-centre skeleton from an escaped ray. That inability IS the finding.

## 4. The cause: the disambiguation, not the placement

Every mechanism in the file is a defence against one ambiguity — *a long ray
may mean the shape is wider here, or may mean the ray left the stroke* — and
each one picks a different side of the same trade:

| mechanism | picks | pays |
|---|---|---|
| `raw = min(side_a, side_b)` | reject the long ray | far rail stops short (the named open item, 17.6% > 0.1 mm inside) |
| median 5 + 4 smoothing passes | reject outliers | cannot follow a real width maximum — **but measured net POSITIVE, §2** |
| corridor cap `(floors+comp)*1.6+0.2` | clamp to the DT field | a real wide station is capped |
| `place`: snap only if outside | correct overshoot | undershoot is never corrected — one-sided |
| `satin_rails_follow_edge` (OFF) | trust each side's own ray | **re-admits the escapes**: Becker std 0.097 → 0.137 |
| `_short_stitch_guard` | retract alternate crosses ≤ 0.6 mm | a sawtooth (mostly excused by the instrument: 36 of 1468 points) |

This is why five attempts have moved it ~10% and no further, and why the one
cure that fixes the under-reach makes the roughness worse. **`line` and `fill`
put thread on boundary geometry and inherit its cleanliness (std 0.000 /
0.010). Satin reconstructs the edge from a medial axis plus a ray-cast
half-width, and inherits that reconstruction's ambiguity instead.**

**Read the table as the shape of the trade, NOT as a list of suspects.** §5 and
§6 went looking for the one that leaks and found that none of them does: every
mechanism here is net-positive, and the wobble is what the model cannot
represent once they have all done their jobs. The original version of this
section ended "the wobble is the residual of an unresolved disambiguation, not
a placement bug" — half right, and left on the record because the wrong half is
the one a reader would act on.

## 5. The proposal that came out of §4 — TESTED THE SAME DAY, AND IT FAILED

The idea was: clip each ray to the stroke's own corridor, so `side_a`/`side_b`
both become trustworthy and `follow_edge` stops re-admitting escapes.

**Its premise does not hold.** Two things killed it within the hour.

**(a) The escape never reaches the rails on a clean junction.** A synthetic
`⊢` — a 3 mm stem with one 13.5 mm arm running out of it perpendicular — puts
7-8 stations in a band whose outward ray escapes down the arm and reports
15 mm against a true 1.5 mm. The right rail comes out at **1.50 mm, exactly
the stem edge, in every arm and at every stroke length tried** (stem half-length
10.0 → 2.0 mm, escaping stations 7 of 51 up to 8 of 11, symmetric and
`follow_edge` alike). The existing defences absorb it completely. A cure for a
leak that does not leak is not a cure.

**(b) The escape test I reached for cannot work anyway.** For a perpendicular
junction the escaped hit's nearest spine vertex is still the firing station
itself, so "the hit belongs to this station" does not reject it. A real test
needs the *sibling* strokes' spines, which `_rail_points` is not given — so the
cheap version of this proposal does not exist.

## 6. The ablation — there is no mechanism to switch off

`enthusiast_logo`, one defence removed at a time (same method as §2):

| arm | satin n | std | p95 | corner> | end> | mid> | bare mm |
|---|---:|---:|---:|---:|---:|---:|---:|
| **shipped** | 828 | **0.089** | 0.198 | 19.2% | 8.0% | 2.1% | 2.2 |
| no short-stitch guard | 863 | 0.085 | 0.185 | 17.4% | 6.9% | 1.8% | 2.2 |
| corridor cap off | 862 | 0.101 | 0.218 | 21.4% | 11.8% | 3.0% | 2.2 |
| no taper zone | 809 | 0.091 | 0.200 | 19.4% | 7.8% | 2.2% | 1.5 |
| `follow_edge` ON | 886 | 0.102 | 0.220 | 18.5% | 8.3% | **4.8%** | **0.0** |

Together with §2's filter arms, **all six defences are net-positive or
neutral.** Removing any of them makes the wobble the same or worse; the best
any removal does is the short-stitch guard's −0.004, on a population that
moved 828 → 863 points, which is noise at that size.

**So 0.089 mm is not a defect sitting on top of a working model — it is the
floor of the model with every defence already doing its job.** That is the
answer to "why do the rails wobble": not because a step is wrong, but because
a smoothed parallel offset of a medial axis cannot represent a real letter's
edge any closer than this, and every mechanism in the file is already spending
something to hold it here.

`follow_edge` ON is worth its own line: it takes the bare outline **2.2 → 0.0 mm**
— full coverage — for std 0.089 → 0.102 and mid-column 2.1% → 4.8%. The trade
is real, it is today's, and it is a choice, not a bug.

## 7. What this means for the next attempt

Closing the wobble means **changing the rail model**, not fixing a step in it:
placing satin rails on boundary geometry the way `line` and `fill` already are
(§1: std 0.000 and 0.010 against satin's 0.089). That is a large build in the
file with the most caveats in the repo.

**It should not start before the sew-out question is answered.** Nothing here
shows 0.089 mm is visible to Kent's eye on cloth
(`kent-eye-vs-instruments-2026-08-27`), §0 shows closing it does not move
`lost_frac` on `enthusiast`, and Kent's 2026-09-18 flag review already found
that the satin/angle flags at this scale read as "no difference" at viewing
size. A model rebuild justified only by an instrument nobody has tied to cloth
is exactly the trade this project has paid for before.

Two things this does NOT claim: that 0.09 mm is what Kent's eye sees on cloth
(still unproven — `kent-eye-vs-instruments-2026-08-27`), and that closing it
moves `lost_frac`, which §0 says it would not on `enthusiast`.

## Reproducing (§6's arms are `_probe_ablate.py`, same throwaway worktree)

    # temp worktree on origin/main, main checkout's venv
    cd <worktree>/digitizer
    /c/Users/EE-LT-11030/CLAUDE~4/EMB-Bot/digitizer/.venv/Scripts/python.exe \
        -m tools.edge_wobble testdata/photo/enthusiast_logo.png \
        testdata/becker_marine_logo.png testdata/photo/logo_gaulke_roofing.png

The two probes (`_probe_widthfilter.py` monkeypatching the two filter
constants; `_probe_sides.py` reading a three-line `_SPY` appended to
`_rail_points`) were deliberately left out of the repo — a throwaway probe's
numbers expire with the probe (DOCTRINE 2026-09-11). The tables above are the
artifact; re-instrument if you need them again.
