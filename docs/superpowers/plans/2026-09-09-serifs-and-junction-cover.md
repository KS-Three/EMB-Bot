# Serifs as their own columns, and a junction cover sewn as satin under the arms — item 5, PR 2

**Status: MEASURED AND SHIPPED 2026-09-09, half of it. The census this PR
built first (`tools/letterforms.py`) overturned the brief's premise, so
the serif column is NOT built; the satin junction cover is —
`cfg.satin_patch_junctions = "satin"`, DEFAULT OFF, `True` and `False`
byte-identical to before.** §1 is what the brief said; §2 is what the
instrument found; §3 what shipped and what it measures; §4 the
predictions against results; §8 what is Kent's.

#434 measured what the wide band buys and what stops it, and read the
render as serifs merged into stems and columns fanning at the feet: 251
self-crossing pairs on MARINE at 100 mm, 6.3–6.5 mm terminal crosses at
the A's foot, drone's wing 7 mm² bare. The brief for this PR was two
flags: serifs as their own short columns with the stem ending FIXED on
them, and the junction patch sewn as satin FIRST in the shape instead of
tatami last.

## 0. What already governs this — read before changing the plan

- **When thread is missing at a junction, sew the hole — do not tune a
  cross** (DOCTRINE 2026-09-06): four cross-length knobs were measured and
  none moved Becker's crotch; `cfg.satin_patch_junctions` (tatami, appended
  at the end of the shape, +0.25% corpus-wide, over-fires on one fixture)
  did. Its two rules stand: patch to `preflight._UNCOVERED_MIN_PATCH_MM2`,
  the grader's own floor, and PROVE the fix through the instrument that
  reported the defect. Kent's reasons it is OFF — the tatami sheen against
  satin, and the needle hopping to the end — are exactly what a satin patch
  sewn FIRST addresses.
- **A junction is a cluster, not a pixel** (#433): the graph the cover
  works on is the clustered one; the K's crotch is 9.0 mm² there.
- **The Goldman join** (`_split_sharp_corners`, `Stroke.tuck_under_*`,
  `capped_*`): the owner of a corner runs through and is extended, the
  other member butts in.
- **Synthetic fixtures are barred as substitutes** (ROADMAP gate 2's
  spirit, DOCTRINE's "nothing enters unless it would change what someone
  DOES"): a feature with no corpus defect to fix is not built on a
  synthetic one.
- **Goldens re-capture on ubuntu-latest with the pre-change proof.** Off is
  byte-identical, so none move in this PR.

## 1. The brief, as written

MARINE's M at 100 mm (`wide_columns` on): 3 strokes; "the left stem's end
is capped 2.4 mm above a 7.5 mm serif foot". Every stem was read as ending
in a capped free end above a slab serif, with `_extend_to_cap`'s terminal
cross fanning to the serif's corners, and the 251 crossing pairs as that
fan. The plan: probe the chord across each free end's tangent, call a
widening past `_SERIF_FLARE × width` a serif, sew it tip to tip as its own
column and end the stem FIXED on it.

## 2. What the instrument found — the premise did not survive it

`tools/letterforms.py` reads every column END of every satin shape (a
plain stroke, or one member of a Goldman join, exactly as `_satin_joined`
sews them): its kind, how far the skeleton stops short of the cap, the cap
face's obliquity to the crosses, the flare along the cap face, and the
crossing pairs seated at it — split into pairs WITHIN one column and pairs
BETWEEN two — plus the bare artwork at every junction node.

- **The feet have no serif.** The M's stems read a constant 5.35 mm chord
  from six millimetres above the baseline to the cap. The source image is
  146 × 91 px — 1.46 px/mm at 100 mm — so the font's 0.6 mm foot serif is
  under a pixel there, and the pro digitized the font, not the file. The
  "7.5 mm foot" was the polygon's top-left BEAK, which the skeleton runs
  along, not across.
- **Every crossing pair is a seam between two columns.** On MARINE at
  100 mm: within a column 0, between columns 359, all of it at two
  Goldman joins (the A's apex — slab member against right-leg member —
  and the R's crossbar/leg join), where the owner's corner cap runs 5–6 mm
  crosses over the corner square the butting member also covers. Across
  the corpus under `wide_columns`: Becker 80 mm 0 within / 716 between,
  drone 0 / 486, ENTHUSIAST 0 / 305, Fremont 0 / 263, Gaulke 0 / 79 —
  and OFF reads the same (Becker 80: 6 / 714). **The pro's own sewn
  MARINE carries 2,593 such pairs within its eleven passes, 652 in the
  M's sixth alone**: thread crossing thread at a join is what a join is.
  The metric was built (2026-08-05) for one column folding over ITSELF;
  read whole, it counts mitres.
- **Where slab serifs DO exist in the artwork — ENTHUSIAST at 93 mm — they
  already sew as Goldman members**: capped ends with flare 2.6–2.75, one
  column each, seated crossing pairs that are the join's. Nothing bare,
  nothing fanning.
- **What IS bare is junction blobs**: the K's crotch (7.7 mm² at 80 mm),
  the M's top-right junction (5.2 mm² at 100 mm under `wide_columns`),
  and Fremont's hexagon band under `wide_columns` — eight blobs of
  3.3–10.5 mm², 128.2 mm² by preflight, grade D.

So there was no serif defect on any fixture for a serif column to fix,
and the crossing count the brief was written against is not a defect.
The half of the brief that had a measured hole under it is the half that
shipped.

## 3. What shipped

**`cfg.satin_patch_junctions = "satin"`** (`stage6_satin._junction_cover_runs`,
`_principal_spine`): the same patches `_uncovered_patches` finds — the
grader's floor, the same grow — each sewn as a satin COLUMN along the long
side of its minimum-area bounding rectangle, half-width from the short
side, both ends capped free so `_extend_to_cap` and the terminal cross
finish it square; placed FIRST in the shape's runs, under the arms, each
column turned to end nearest the shape's first run, and joined to it —
and to the next cover — by needle-down travel along the unsewn skeleton
web (`_graph_travel`), the way strokes already travel. No underlay. A
patch wider across than the satin ceiling, or whose column comes out
degenerate, takes the tatami patch for that one hole. `True` keeps the
tatami patch appended last, byte for byte; the applique route forwards the
same field. Priced on the flip sheet as the `satin_cover` arm beside
`satin_patch`.

**Not shipped, measured and dropped**: a second round of the finder with
the first round's thread down — identical `uncovered_total_mm2` on Becker
100 mm and Fremont under `wide_columns`, +26 / +114 stitches, +1 / +3
trims.

## 4. Predictions against results

| prediction (this plan's first draft) | result |
|---|---|
| MARINE crossing pairs 251 → under 50 by serif columns | not a defect: 0 within any column, all at joins; the pro's file has 2,593 (§2) — no serif column built |
| the K's crotch 9.0 → 0.0 through `ARTWORK_UNCOVERED` | **held**: Becker 80 mm 9.0 → 0.0, B 76 → B 88 — the same grade the tatami reaches, at +122 stitches (+2.2%) and +2 trims against the tatami's +297 (+5.3%) and +3; under `wide_columns` 9.0 → 0.0 at +158 / +3 |
| drone's wing 7.0 → 0.0 | **held**: drone 80 mm under `wide_columns` 7.0 → 0.0 (worst 2.5) at +38 stitches and +1 trim; the tatami reaches 0.0 (worst 1.2) at +177 and +1 |
| `coverage_max` under the warn line everywhere the flag fires | held (4.72 / 5.08 / 3.83 / 6.41, all unmoved by the cover) |
| stitches within +2% where it fires | Becker 80 +2.2%; Fremont's band under `wide_columns` **+10.6%** (8,005 → 8,851, +17 trims) for 128.2 → 13.0 mm² — the tatami costs +34.5% for 6.0 |
| not predicted | Becker 100 mm under `wide_columns`: the grader reads 0.0 both ways, the cover adds 2 trims and trips `TRIM_HEAVY`, B 88 → B 76 — the same over-fire the tatami has (B 76 at 44 trims): this pass is stricter than the grader by design |
| corpus cost (the tatami's row: +0.25%, 3 of 26 moved) | 26 fixtures @ 80 mm: the cover moves the same 4 fixtures as the tatami, to the same 2 grade-ups, at **+313 stitches / +7 trims** against the tatami's +733 / +9 |

## 5. The instrument — `tools/letterforms.py`

Per satin shape and column end: kind (free / capped / junction), reach to
the cap, cap obliquity, flare along the cap face, the stroke's own width,
crossing pairs seated there; per case: pairs within a column vs between
columns, bare artwork over the grader's floor, bare blobs at junction
nodes. `--flag NAME[=VALUE]` repeatable, `--widths`, `--json`.

## 6. What must not regress, with its fixture

- The flat-lane goldens and pushcomp pins — off byte-identical, `True`
  byte-identical (`tests/test_junction_patch_flag.py`, 14 tests).
- `logo_alpha` pays nothing for `"satin"` (no hole to patch).
- The cover is the shape's FIRST run and satin; never outside the artwork.

## 7. Size and staging

| PR | content | size | gate |
|---|---|---|---|
| 2 (this) | the census; the satin junction cover; the correction | ~350 lines + tests | none — geometry; flipping the mode is Kent's on the render |
| 3 | the junction BLOB as its own column with the arms ending on it (the pro's A apex), a junction-aware width statistic for the classifier | large | goldens move |

## 8. Decisions for Kent

- `satin_patch_junctions`: keep OFF, flip `True`, or flip `"satin"` — the
  renders in `docs/renders/junction-cover-2026-09-09/` (the K's crotch
  OFF / tatami / satin) are the argument; the over-fire at Becker 100 mm
  is the catch, and it is the tatami's too.
- Whether `crossing_pairs` stays in `wide_columns.py --compare` as a
  headline number at all, now that it counts mitres.
