# Adjudicating `ARTWORK_UNCOVERED` — 2026-09-30

Kent's pick: *"Make preflight see these holes."* The constant
`preflight._UNCOVERED_MIN_PATCH_MM2` had asked for this in writing since
2026-08-20 — *"nobody has looked at whether ... 4.50 mm² and ... 3.25 mm² are
real drops or acceptable. Widen the fixture set and adjudicate the middle
before trusting this number."*

**The first finding was that the floor was not the problem.** With it set to
zero, the check still read **0.00 mm²** on ENTHUSIAST, where two other
instruments read a 1–2 mm² hole at the A's apex. Two other filters were
hiding it, and one had a cliff exactly at its shipped value:

| `_UNCOVERED_ERODE_MM` | 0.1 | 0.2 | 0.3 | **0.4 (shipped)** |
|---|---|---|---|---|
| apex, mm² | 0.80 | 0.80 | 0.80 | **0.00** |

`_UNCOVERED_CELL_MM` did the same: 0.60 at 0.20 mm, 0.40 at 0.25, **0.00 at
the shipped 0.5**. And swept across all six erosion × cell combinations, the
largest patch the check could see **anywhere on the nine corpus logos** was
1.90 mm² — so a 5.0 mm² floor sat above the entire population and
`ARTWORK_UNCOVERED` could not fire on any real logo at any setting.

## What replaced them

The erosion was a proxy for *"ignore the rim"*. It cannot tell a rim from a
hole that touches a boundary, and a tapered tip's hole is nothing but
boundary. Two direct tests do what it was approximating:

| filter | refuses | value |
|---|---|---|
| `_UNCOVERED_MIN_HALF_MM` | one-cell seams between adjacent columns | 0.30 mm |
| `_UNCOVERED_MIN_FILL` | outlines — a rim is long, not thick | 0.15 |
| `_UNCOVERED_MIN_PATCH_MM2` | everything smaller than a hole | 1.0 mm² |

Cell 0.5 → **0.25 mm**, erosion 0.4 → **0.0 mm**.

**Mean thickness was tried as the compactness test and is refuted**: the
full-bleed rim's mean inscribed half-width is 0.332 mm, *higher* than
fourteen of the twenty adjudicated holes (0.252–0.354). A frame of
thread-width cloth is not thinner on average than a 1 mm hole — it is only
longer. Fill ratio separates where mean does not: rim 0.007, golden_tee's
band seam 0.078, every real hole 0.239–0.706.

## The corpus, on the shipped constants

| fixture | patches | holes | largest patch |
|---|---|---|---|
| golden_tee 80 | 108 | **0** | 3.12 mm² (a band seam) |
| becker 100 | 93 | **17** | 3.00 |
| bridge 80 | 58 | 0 | 0.88 |
| screenshot 80 | 51 | 0 | 0.81 |
| gaulke 80 | 48 | 0 | 0.31 |
| drone 80 | 40 | **1** | 1.44 |
| enthusiast 80 | 27 | **2** | 1.56 — the A's apex |
| tires 80 | 9 | 0 | 0.06 |
| fremont 92.5 | 1 | 0 | 0.25 |

**438 patches, 20 holes, three fixtures warn.** The four fixtures with the
most patches — golden_tee, bridge, screenshot, gaulke, 265 between them —
report zero.

## The pictures

Each is one crop per patch, **lit** (what the Studio previews) beside the
same design on **magenta** cloth (every magenta pixel is cloth no thread
reached), drawn through `stitchviz.render_design` — the real stitch stream,
not the mask that found the patch.

| file | what it shows |
|---|---|
| `enthusiast.png` | the A's apex at 1.56 mm², and a 1.00 mm² gap between two letters — **MASTER_SCOPE defect 49, now visible to preflight** |
| `enthusiast150.png` | the same fixture at 150 mm: 5 holes, worst 4.81 mm², the apex again |
| `becker.png` | the four largest of its 17 — cloth between a fill edge and its border run |
| `drone.png` | 1.44 mm² between two white fills |
| `chrome.png` | the full-bleed guard's **real** hole: a 2.38 mm² void in dense stitching, fill 0.43. Its 73.94 mm² rim (fill 0.007) is refused and is not pictured |
| `golden_tee_seam.png` | the case for `_UNCOVERED_MIN_FILL`: 3.12 mm² that is a thread-width **line** between two colour bands. Area alone fires six times on this fixture; the filters fire none |

## The honest risk

Three filters tuned on nine logos plus two guard fixtures is a narrow base,
and the margins are 1.5–2x, not the two orders of magnitude
`_COVERAGE_MIN_PATCH_MM2` earned. What can be claimed is that each filter
refuses a **named** false-positive class with a committed guard behind it,
rather than being a number that happened to work. It stays a `warn`, never a
block.

## Reproduce

```bash
cd digitizer
.venv/bin/python tools/uncovered_floor.py --corpus
.venv/bin/python tools/uncovered_floor.py --legacy   # the 2026-08-20 table
.venv/bin/python -m pytest tests/test_preflight.py -q -k uncovered
```
