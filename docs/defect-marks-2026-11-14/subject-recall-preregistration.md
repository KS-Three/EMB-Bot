# Pre-registration: does `subject_edge_recall` read lost subjects among photos? (2026-11-14)

Written and committed **before** the kit's renders were digitized and before
Kent sits. Nothing below changes after this commit. A deviation, if any, is
recorded in the scoring doc as a deviation and is not edited in here.

## Why

`docs/subject-loss-2026-11-14.md` (PR #1502) measured `subject_edge_recall`
against Kent's earlier grades and found Somers' D +0.88 [+0.63, +1.00]
between rows he ticked "detail lost" / "can't tell what it is" and rows he
graded Good. Every Good row was flat art, though, and "the class is not flat"
alone read +0.77. The reading has not been shown to measure anything beyond
photo-vs-flat. Kent's ruling (2026-11-14, via the foreman): **metric only,
plus a photo sitting**. This is that sitting.

## The question

**Among photos only**, does `subject_edge_recall` separate photos Kent grades
Good from photos where he says the subject or its detail is lost?

## The set (15 items, one tree)

The rule: **every Commons-corpus photo row Kent has not graded before, plus the
walkthrough's toadstool.** The corpus has 18 `kind: photo` rows. Four were
graded in `defect-marks-2026-11-10` (`bw_street`, `night_neon`,
`architecture`, `landscape_lake`, all Terrible) and are left out. The other 14
are all in. Nothing was picked by reading or reading off a metric, so no
selection could lean on which side of the cut-off an item falls.

Spanning the metric's range was checked on the OLD capture (`main-950855b`,
`docs/subject-loss-2026-11-14/rows.json`), not on these renders. Those 14 rows
read 0.56 to 0.94. They include cut-outs (`dark_dog`, `flower_macro`,
`food_plate`, `oil_painting`, `watercolor`) and faces (`group_people`,
`sports_action`, `vintage_sepia`, routed flat by the face rule), which are the
photos most likely to grade Good.

| item | source | old-tree `edge_recall` |
|---|---|---|
| `P_food_plate` | Commons corpus | 0.751 |
| `P_vintage_sepia` | Commons corpus | 0.860 |
| `P_fireworks` | Commons corpus | 0.772 |
| `P_snow_highkey` | Commons corpus | 0.791 |
| `P_flower_macro` | Commons corpus | 0.576 |
| `P_dark_dog` | Commons corpus | 0.702 |
| `P_underwater_reef` | Commons corpus | 0.808 |
| `P_watercolor` | Commons corpus | 0.938 |
| `P_pencil_sketch` | Commons corpus | 0.879 |
| `P_stained_glass` | Commons corpus | 0.606 |
| `P_group_people` | Commons corpus | 0.915 |
| `P_sports_action` | Commons corpus | 0.968 |
| `P_night_skyline` | Commons corpus | 0.559 |
| `P_oil_painting` | Commons corpus | 0.917 |
| **`P_toadstool_dof_meadow`** | `digitizer/testdata/photo/photo_dof_meadow.png` (the walkthrough's photo) | **0.940** |

**Renders:** one tree (`origin/main` `dcd21120` plus this folder), one
digitize at a time, through `photo_corpus.capture` with that tree's own Studio
request: **80 mm wide, left chest**, the same request every corpus capture
uses. The page shows each item at 12 px/mm beside its artwork, through
`tools/defect_marks.py`, the page of the 11-10, 11-11 and 11-12 sittings.
Kent gives a grade (Great / Good / Okay / Bad / Terrible), pins what he likes,
and ticks whole-design problems. "Can't tell what it is" and "Too much detail
lost" are two of those ticks. The page never shows the preflight grade or this
metric.

**The toadstool is named here because it is the case that started this.** On
the old tree it read 0.940, under the cut-off below by only a hair. If Kent
marks it LOST and it reads at or above the cut-off on these renders, that is a
miss, and the scoring says so in its own line.

## Labels (the 11-14 definitions, unchanged)

- **LOST**: Kent ticks `detail_lost` or `unrecognizable`, whatever the grade.
- **GOOD**: graded Good or Great, with neither tick.
- **MIDDLE**: every other graded item (Okay / Bad / Terrible with neither
  tick). These sit out of the contrast and are reported.
- An item with no grade and no tick is left out and reported.

## Readings and statistics (fixed now)

- **The reading:** `subject_edge_recall`, computed with `tools/subject_detail.py`
  (the code in PR #1502, constants as committed there) on these renders'
  saved stitches against the source re-read. It is computed **only after the
  foreman says Kent is done.** Low means lost.
- **Primary:** Somers' D = 2 × AUC − 1, LOST against GOOD, with a 95% interval
  from 5,000 bootstrap resamples within each group (seed 0,
  `tools/subject_detail_score.somers_d`). 0 is chance.
- **At the cut-off:** **c = 0.90**. An item is "flagged" when it reads below
  0.90. The figure is Cohen's kappa between flagged and LOST, over the LOST and
  GOOD items only, with a 95% bootstrap interval (5,000 resamples, seed 0,
  resampling items). Why 0.90: it lies between the 11-14 LOST photos' median
  (0.79) and the lowest GOOD row (0.949). It is set before any of these
  renders exists and is not moved afterwards.
- **Minimum counts for ANY verdict:** at least **4 LOST and 4 GOOD** items.
  Below that, the result is "no verdict: class not filled", the metric stays
  as it is, and nothing else is read into the numbers.
- **Reported, decides nothing:** the MIDDLE items' readings; the photo-lane
  items alone (dropping the 3 face-routed flat ones), as a robustness line;
  the toadstool's reading and label.

## What each result means (decided now)

Read only when the minimum counts are met.

| result | means |
|---|---|
| D's interval includes 0 **or** D ≤ +0.20 | **Drop it**: remove `subject_edge_recall` from preflight; it does not read lost subjects among photos |
| D's lower bound > 0 but kappa's lower bound ≤ 0 | **Keep as a metric, no change**: it ranks but the 0.90 line does not sort |
| D's lower bound > 0 **and** kappa's lower bound > 0 | **Propose a finding**: info severity, no grade cost, text naming the subject loss. This goes to Kent as a proposal, because his 2026-10-02 no-warnings ruling needs his word |
| As above **and** D ≥ +0.60 **and** no GOOD item reads below 0.90 | **Propose a grade cost** (a warn) as an option beside the finding. Kent chooses |

A raw agreement percentage is never the figure (ROADMAP gate 4). Every
number above is an instrument reading or Kent's own answer.
