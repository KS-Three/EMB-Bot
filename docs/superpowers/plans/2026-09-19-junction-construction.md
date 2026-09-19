# The bold-letter junction — the construction step 4 needs (2026-09-19)

**Status:** design document, for Kent's ruling before code. Kent's pick
2026-09-19 after the lettering plan's five steps were built (steps 0–3a
and 5 ON, 4 kept OFF on the R's fanning junction ball). No engine code
in this document; every number below was read on today's engine
(`main` at #516) with the arms composed from existing flags and one
monkeypatched constant, so the build can be priced before it is
written. §7 is what is Kent's — **and his ruling, the same day: build
A + B + C as one flag (`satin_junction_stack`, OFF), each part
measurable inside it; this document lands first, on its own PR.
BUILT the same day as `cfg.satin_junction_stack` and FLIPPED ON the
same day (Kent's call over the fixtures, the nine-logo sheet and the
goldens; False is the pre-flip engine) — §6 carries the predictions
against the build's results. Step 4's `DENSITY_EXTREME` was READ the
same day: the instrument, not the letters — the satin density reader
counted split penetrations as rail steps (fixed; the fixture reads 0.43
against the 0.40 target). Step 4's flip is Kent's again. Becker's
residual letter pairs were read too: all in four Goldman-joined strokes,
the join's own mitre counted within the run — the pro's kind, not a
fold; nothing to build.**

## 0. What governs this — read before changing the plan

- **A junction blob is not a column** (DOCTRINE 2026-09-09, item 5 PR 3
  measured out). A bold letter at 17 mm is 45–90% junction blob; sewing
  the blob as its own column with the arms ending on it adds layers the
  pro's file says are fine, to fix a look the pro's file also has. That
  brief is not revived here.
- **When thread is missing at a junction, sew the hole — do not tune a
  cross** (DOCTRINE 2026-09-06). Four cross-length knobs moved nothing;
  the cover did. `cfg.satin_patch_junctions = "satin"` exists, OFF:
  the grader's own patches as satin columns FIRST in the shape, under
  the arms; +0.25% across the corpus, over-fires by two trims on Becker
  at 100 mm.
- **Crossing pairs at a join are the join** (DOCTRINE 2026-09-09). The
  pro's own MARINE carries 2,593 seam pairs between columns; the metric
  was built for a column folding over ITSELF, and only that reading is
  a defect. §1 is that reading.
- **The corpus overruled a 35° cut** (`stage6_satin`, the corner-cut
  constant): across 19 professional files, 1,436 corner events sit
  inside a continuing column. A turn is not a defect by its angle; a
  fold is.
- **A weld is a decision about where a column goes** (`_merge_through_junctions`):
  "the threshold admits a bend but refuses a corner sharp enough that
  the column would have to pivot, which no parallel-rail satin can sew."
  `_WELD_MAX_DOT = -0.5`, the arms' directions read over two half-widths.
- ROADMAP gates 1 and 4: no physical constant moves; no quality claim on
  a raw number. The pro's file is the calibration (`tools/pro_layers.py`),
  read at the same junctions.
- Kent's 2026-09-11 rule for lettering: split, never fill. Step 4
  (`satin_lettering_split`) is built and waits on this.

## 1. The defect, named (measured 2026-09-19)

The R of the plan's fixture (MARINE traced at 127 mm) under
`satin_lettering_split`: six satin runs, **311 self-crossing pairs, all
of them in ONE run** — 109 points, the foot of the leg, x 1.7–10.4 /
y 3.0–9.3 mm — and **294 of the 311 seated in one junction blob** at
(5.24, 6.25): three arms, the merge's decisions **weld, weld, dropped**.
Node radius 3.11 mm on 1.64 mm arms (ratio 1.9), blob 38.6 mm²,
coverage layers max 5.43, bare 8%. The R's other eight blobs seat 0–2
pairs each. So the "junction ball fanning" is exact: **one column
welded through one corner, folding over itself** — the fold step 3a's
corner rule stopped at the PRUNER, made again at the MERGE.

Renders: `docs/renders/junction-construction-2026-09-19/` — the R's
nine blobs on its merged strokes, and its stitches alone at 20 px/mm
(the fan is the dense dark sweep at the leg's foot, bottom right).

Two hypotheses, tested on the fixture before anything else:

| arm | stitches | trims | R's pairs | uncovered | what it says |
|---|---|---|---|---|---|
| as shipped (`_WELD_MAX_DOT` −0.5) | 7,253 | 34 | 311 | 0.0 | the fold |
| `_corner_forks` disabled (the dropped arm kept) | 7,531 | 36 | 311, in a different run | 0.0 | **not the fork drop**: the weld is made with three arms standing too |
| welds refused past a turn (dot −0.7, ≈46°) | 7,103 | 40 | 311 | 0.0 | the R's weld turns less than 46° by the merge's baseline |
| welds refused past dot −0.8 (≈37°) | 7,110 | 47 | **0** | 0.0 (with the cover) | the fold is a weld turning **44.4°** over two half-widths (the probe's reading at that node) |
| welds refused past dot −0.9 (≈26°) | 6,906 | 43 | **0** | **25.8** | refusing bares the junction: the arms end short of it |

The probe that read the corpus (`weld_turns`, §5): **every weld in the
nine logos turns under 60° by the merge's baseline** — the threshold
admits nothing sharper — and **the seam pairs sit in the 30–60° bin**:
the fixture 296 of 296, Becker at corpus width 734 of 734, Golden Tee
403 of 537, Bridge Bar 106 of 106, drone 70 of 70, gaulke 89 of 126.
Over the nine logos at their corpus widths, **1,420 of the 1,607 seam
pairs (88%) sit in the 30–60° welds**; the 187 under 30° are Golden
Tee's 134, gaulke's 37 and the screenshot's 16 (the fixture and Becker
seat none there; the screenshot's 1–3 mm lettering splits 16 / 18).
Becker's
734 at corpus width are not in the band at all: they sit in the BECKER
outline's own welds at 53–58° (301 and 251 pairs at two nodes), the
same mechanism on a non-letter shape. The fold is the bendy weld, and
the bendy weld is common: of the corpus's
welds, 30–60° is 9 of 16 on the fixture, 11 of 21 on Becker, 37 of 88
on Golden Tee, 25 of 54 on drone, 19 of 30 on gaulke.

Why the baseline misreads it: the merge measures an arm's direction over
`arm_px` = two half-widths — on a 5 mm column, 5 mm along the arm — and
"a column cannot resolve direction finer than its own width" is right
for the DECISION and wrong for the COST. The cost is what
`_fold_caps` already prices on a wide column: the spine's radius of
curvature at the node against the column's half-width. A 40° turn over
five millimetres is a bend a 2 mm column sews and a 6 mm column pivots
through.

## 2. What the pro does at the same junctions

`tools/pro_layers.py --blobs` on Becker at 100 mm, today's engine,
`satin_lettering_split` ON so the band sews as columns (the pro's
`beckers_logolc.dst`, aligned on the whole design's stitch box):

| MARINE shape | blob (arms) | ours mean / p95 / max, bare | pro mean / p95 / max, bare |
|---|---|---|---|
| M (`Scc08b907`) | (−43.8, 18.6) 3 | 2.38 / 4.87 / 9.24, 0.07 | 2.68 / 4.88 / 8.21, 0.03 |
| M | (−34.8, 18.6) 3 | 1.75 / 3.40 / 5.51, 0.09 | 2.88 / 4.64 / 7.37, 0.00 |
| A (`S5a3cd301`) | (−23.2, 17.6) 4 | 1.79 / 3.55 / 5.04, 0.07 | 2.90 / 4.73 / 6.48, 0.00 |
| R (`Sa587cbf9`) | (−6.4, 17.6) 4 | 1.55 / 3.54 / 4.86, 0.10 | 1.62 / 4.03 / 6.12, 0.00 |
| R | (−0.9, 26.0) 3 | 2.28 / 3.97 / 4.86, 0.06 | 3.64 / 7.25 / 10.15, 0.00 |
| I (`S14230a1b`) | (10.9, 16.9) 3 | 1.14 / 2.06 / 3.29, 0.02 | 2.94 / 4.38 / 5.48, 0.00 |
| N (`Sdd5f27fb`) | (20.4, 18.3) 4 | 1.82 / 4.13 / 5.74, 0.13 | 2.87 / 4.42 / 6.46, 0.00 |
| N | (21.2, 16.8) 1 | 1.32 / 2.71 / 4.49, **0.23** | 2.60 / 3.83 / 5.24, 0.00 |
| E (`Sf1c25fcd`) | (38.2, 22.6) 3 | 2.59 / 4.23 / 6.28, 0.00 | 2.59 / 4.19 / 6.23, 0.00 |

The same shape as 2026-09-09: at every junction the pro's mean and p95
are higher than ours and his bare fraction is 0.00–0.07 where ours
reaches 0.23. His photo (`testdata/reference/becker_hat_polo_large_beckers_logolc.jpg`)
shows it: each stroke of MARINE is its own column, sewn to the junction
and INTO it, the junction being where two or three columns overlap. He
does not weld a column through a corner; he ends columns on each other
and lets the overlap stack. **The pro's junction is a stack of arms, not
a column through them** — which is also what `_merge_through_junctions`'
own docstring calls the intent ("the junction gets the modest overlap of
its arms") for the arms that do NOT weld.

## 3. The construction — three parts, in the order they are priced

**A. The weld gate reads the column's own fold, not the arms' baseline.**
At a node where two arms would weld, price the turn the way the column
will pay it: the spine's radius of curvature through the node against
the column's half-width there, with `_fold_caps`' rule — the constant it
already holds, no new number. A weld the column can sew as a bend
stands; one it would pivot through is refused, and the arms END at the
node instead. This keeps every straight-through weld (a T's bar, an H's
stem — the 0–30° bin, where the corpus seats no seams) and refuses the
folds. **Measured today by proxy** (`_WELD_MAX_DOT` −0.9, ≈26° by the
baseline, coarser than the rule): the fixture's R **311 → 0**, MARINE
at 80 mm **103 → 0**, Becker's band under the split flag 1,260 → 556
(its letters 546 → 467 — the residual is not folds; §5's first job is
to say what it is).

**B. An ending arm runs INTO the junction, not short of it.** Today an
arm that ends at a junction of three or more clears the blob by
`_junction_entry_mm` ("the modest overlap"), and refusing a weld makes
two more such ends. The proxy shows the price of ending short: the
fixture's uncovered artwork **0.0 → 25.8 mm²**, MARINE 80 **0.0 →
22.8**, Becker under the split **35.5 → 108.5**. The pro's arms reach
the node with their full width and stack (his p95 4–7 layers inside the
blobs against our 2–4, §2). Rule: an arm ending at a junction runs to
the node's centre plus its own half-width along its tangent, so two or
three arms' caps overlap inside the ball. Priced by layers against the
pro's per-blob figures — the calibration exists — and by
`ARTWORK_UNCOVERED`. Not built; not measurable by proxy.

**C. The cover under the arms, for whatever is still bare.**
`satin_patch_junctions = "satin"`, as shipped: the grader's patches as
satin columns first in the shape. With A alone it is load-bearing
(measured); with B it should be the backstop. Composed today:

| fixture | today | A (dot −0.9) | A + C | Δ vs today |
|---|---|---|---|---|
| R fixture, 127 mm, split: stitches / trims / pairs / uncovered | 7,253 / 34 / 311 / 0.0 | 6,906 / 43 / 0 / 25.8 | **7,018 / 46 / 0 / 0.0** | −235 stitches, **+12 trims**, the fold gone, `DENSITY_EXTREME` still raised (coverage_max 6.20 → 5.34) |
| MARINE 80 mm (default) | 1,774 / 7 / 103 / 0.0 | 1,475 / 13 / 0 / 22.8 | **1,829 / 19 / 0 / 0.0** | +55 stitches, **+12 trims**, the 103 gone |
| Becker 100 mm, split | 8,612 / 53 / 1,260 / 35.5 | 7,461 / 59 / 556 / 108.5 | **8,059 / 67 / 556 / 0.0** | −553 stitches, +14 trims, uncovered cleared, letters' pairs 546 → 467 |

At dot −0.8 (≈37°) with the cover: the R 7,110 / 47 / 0; MARINE 80
1,736 / 14 / 42; Becker 8,194 / 71 / 675 — a coarser proxy keeps some
folds and pays the same trims, which is why A is specified on the fold
rule and not on the baseline angle.

**The price is trims.** Refusing a weld turns one stroke into two, each
with its own entry, and the cover adds a run per hole; the Euler walk
(step 2) chains strokes that share a node, but a cap-extended column
starts on a rail, not at the node, and the hop exceeds `TRIM_AT_MM` as
often as not (DOCTRINE 2026-09-06, "the needle lives on rails"). Part B
is the lever on that too: an arm that runs into the node ends where the
next arm begins.

## 4. Fixtures

- The R of the 127 mm fixture under `satin_lettering_split`: the fold
  (311 → 0), `DENSITY_EXTREME`, uncovered 0.0, trims.
- MARINE at 80 mm, default: 103 → 0 with uncovered held at 0.0; the
  yardstick beside it (typed 1,782 / 3; traced today 1,774 / 7).
- Becker at 100 mm under the split flag: the band's 546 letter pairs
  and its 35.5 mm² bare; the pro's layers per blob (§2).
- The nine logos at corpus widths, defaults: self-crossings 1,004 today
  (the 30–60° welds' seams), uncovered, trims 476, stitches; no golden
  moves (the flat-lane keys have no branch node — the same proof the
  clustering PR used).
- Then step 4 re-measured with the construction ON: the R sewn split,
  no fold, no `DENSITY_EXTREME` — the flip Kent kept OFF, re-priced.

## 5. The instrument

`weld_turns` — the probe that produced §1's histogram, to be committed
as `tools/weld_turns.py`: every weld the merge makes, the turn it asks
of the column (by the merge's baseline AND by the fold rule, so the two
readings can be compared on the same node), the node's ball against its
arms', and the seam pairs and layers the blob census reads inside that
blob. Its first job on the build: split Becker's residual 467 pairs into
folds within a column and seams between columns (`tools/letterforms.py`
already has the within/between split for ENDS; the weld probe needs it
for INTERIORS), so the target is "folds → 0" and not "pairs → 0", which
DOCTRINE says is the wrong target.

`tools/junction_blobs.py` and `tools/pro_layers.py --blobs` price B:
layers and bare per blob, ours against the pro's. `tools/wide_columns.py
--compare` and preflight price the whole: stitches, trims, coverage,
uncovered, findings.

## 6. Predictions against the build's results (built 2026-09-19, the same day)

| prediction | fixture | falsified if | result |
|---|---|---|---|
| A refuses the R's weld and no other weld in the R | R at 127 mm, split | the fold survives, or a straight-through weld (0–30°) is refused | **falsified as written, held as meant**: the gate refuses FIVE of the R's eight welds (34.5, 35.7, 44.4, 46.5, 47.8°), none under 30° (2.5, 3.9, 26.9 stand); the design's welds 16 → 7; the fold 311 → 0 |
| A + B: uncovered stays 0.0 on the fixture WITHOUT the cover | R at 127 mm; MARINE 80 | uncovered > 0.5 mm² with C off | **held** on MARINE 80 (`test_marine_80_keeps_its_cover_without_the_junction_cover`, the cover neutralised: 0 folds, uncovered ≤ 0.5) |
| A + B: layers inside the R's blobs rise toward the pro's p95 (4–7) and stay under `COVERAGE_WARN_UNITS` | Becker 100, split, vs `pro_layers` | any blob's max over the warn line, or p95 still under 3 | **falsified**: the R's blobs read p95 3.33 / 3.93 / 4.18 (split alone 3.54 / 3.60 / 3.97) against the pro's 3.90 / 5.13 / 7.18, the I's 2.01 against 4.32; every letter blob's max under the warn line (≤ 6.37). B reaches in by one half-width and the layers do not move; the pro's stack is denser than an overlap of ends |
| trims on the fixture within +4 of today (34), not the proxy's +12 | R at 127 mm | trims > 38 | **falsified**: 44 (+10); MARINE 80 pays +2 (7 → 9), where the proxy paid +12 |
| nine logos: the 30–60° welds' seam pairs fall by more than half; uncovered unchanged or down; stitches within ±1% | corpus, defaults | pairs fall by less than half, or any logo's uncovered rises | **partly falsified**: the lettering groups' self-crossing pairs fall 1,004 → 596 (−41%, not more than half: Golden Tee 381 → 113, gaulke 186 → 106, drone 264 → 220); uncovered unchanged on eight and Becker's 35.5 → 0.0; stitches +0.7% (89,105 → 89,723); trims 476 → 489, Bridge Bar's 82 → 95 the cost to name, gaulke's 38 → 29 the gain |
| no golden moves | flat-lane keys, pushcomp, stage-2 | any byte moves | **held**: the flat-lane, pushcomp and stage-2 keys byte-identical — 481 passed in the lettering-adjacent subset with the goldens (CI's three deselects), 0 failed |

**What the build found beyond the table.** The corpus histogram by ten
degrees (383 welds): 0–10 carries 127 seam pairs on 64 welds, 10–20 47
on 82, 20–30 **13 on 75** — the trough — 30–40 302 on 72, 40–50 274 on
58, 50–60 844 on 32; the fold guard's radius rule (§3 A as written)
separates nothing at 1, 2 or 3 mm (the R 0.97 at 2 mm, Becker's
301-seam weld 1.25, a clean weld 0.80), so the gate reads the merge's
own baseline at **30°**, the corpus number, swept on the fixtures at
20–45 (fold-free from 30 down, MARINE 80 keeps 42 pairs at 35, the R
folds again at 45). Becker's band keeps **528 letter pairs under the
flag at every threshold** — 469 in plain columns, 59 in Goldman-joined
strokes — so they are not welds — and read stroke by stroke the same day they are
not bends inside an arm either: **every one sits in a Goldman-joined
stroke** (the A's 260 at a 52° join, the E's 209 at 64°, the R's 59 at
47°, one more at 57°), the owner's corner cap sweeping over the member
that butts into it, counted within the run because a joined stroke sews
as one run. That is DOCTRINE 2026-09-09's "crossing pairs at a join are
the join" (the pro's file carries 2,593); the earlier plain-column count
was a matching artefact of the probe. Nothing to build. The R fixture's
`DENSITY_EXTREME` is the split flag's (satin pitch 1.12 mm against a
0.4 target) and the stack leaves it at 1.09.

## 7. What is Kent's

1. **Whether to build it at all**, against the alternative the review
   named: a per-letter override in the Studio ("sew this letter as
   typed") — the font engine's columns need no junction construction
   because the font's strokes are given. The construction is what makes
   TRACED bold lettering sew as the pro sews it; the override is what
   makes it unnecessary for a customer who will pick a font.
2. **Which parts**: A alone is a measured negative-space fix (folds → 0)
   that costs trims and bares junctions; A + C is measurable today and
   clears the bare cloth at +12 trims per word; A + B + C is the pro's
   construction and the only one that can bring the trims back. The
   recommendation is A + B + C, built as ONE flag (`satin_junction_stack`,
   OFF), each part measurable on its own inside it.
3. **The fold rule's constant**: `_fold_caps`' own radius rule, reused
   — no new physical constant, so gate 1 does not apply; if the build
   finds the rule needs its own number, that is a sew-out question and
   the build stops there and says so.
4. **Step 4 afterwards**: the split flag re-priced with the construction
   ON, and its flip put to Kent again on that measurement.

## Not this document

The junction cover's over-fire on Becker at 100 mm (two trims on a
finding the grader reads as 0.0 both ways — DOCTRINE 2026-09-09, the
tatami's too). The density gap to the pro in the letters (+58% thread,
Law 27/50, a sew-out question). Serifs (measured absent in the artwork,
2026-09-09).
