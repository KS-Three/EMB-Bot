# `lettering_columns_fold_cuts`: the p and the crossed legs, judged sewn (2026-10-19, flag OFF)

MASTER_SCOPE item 50 left two cases open after #972: crossed legs at 80 mm above
OFF (b 10 vs 5, g 15 vs 10), and the 120 mm p (2/2/9 against OFF 0/0/4). This lane
(`claude/fold-cuts-p-crossed`, resumed) gives the fold look a **sewn judge**: a
candidate cut is sewn through `column_runs` exactly as the letter will be and read by
`outline_cut.sewn_knots` (the `tools/lowercase_angle.py` reading, restated in the
engine; `test_sewn_knots_reads_as_the_tool` holds the two equal). A candidate that
sews more short or crossed legs than the piece left whole (or than OFF's cut) is
refused. A **coverage guard** (`COVER_SLACK` 0.5 W², `_uncovered`) refuses one that
leaves more of the letter bare: unguarded, the 80 mm b's winning pair sewed 0/0/0
with 1.4 W² of its bowl shoulder bare, against OFF's 0.5 W².

The flag stays **OFF**. Every OFF plan below is byte-identical to `origin/main`
5fbcf02f.

Thread renders and stitch-path zooms of EMB-Bot's own output on the synthetic
Aileron word (`digitizer/testdata/synthetic/lowercase_aileron.png`, Pillow's bundled
CC0 face), drawn by `tools/lowercase_angle.py` `render_pair` (`_shots` /
`_write_pairs` for the 50 mm cell). OFF above, ON below. In the zooms satin is dark,
underlay blue, travel green. Not cloth: nothing was sewn.

## Per glyph, sewn: station folds >45° / short legs / crossed legs at junctions

`forced_class="flat"`, Column lane ON (shipped), real `digitize()`. "main ON" is
origin/main 5fbcf02f with the flag ON; "this ON" is this branch.

| glyph | 80 mm OFF | main ON | **this ON** | 120 mm OFF | main ON | **this ON** |
|---|---|---|---|---|---|---|
| **p** | 0/0/14 | 0/0/5 | **0/0/4** | 0/0/4 | 3/2/9 | **0/0/4** |
| **b** | 3/0/5 | 1/0/10 | **0/0/0** | 3/0/7 | 1/0/4 | **1/0/4** |
| **g** | 1/0/10 | 0/0/15 | **0/0/0** | 2/1/13 | 0/0/7 | **0/0/5** |
| a | 0/0/4 | 0/0/0 | 0/0/0 | 1/1/17 | 1/1/10 | **0/0/0** |
| m | 0/0/0 | 0/0/4 | **0/0/0** | 3/1/5 | 1/2/8 | **0/1/0** |
| u | 0/0/4 | 0/0/4 | 0/0/4 | 3/0/0 | 0/0/0 | 0/0/0 |
| e | 1/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |

No lowercase glyph sews ON above OFF on any of the three counts, at 50, 80 or 120 mm.
Main ON did at four cells: the 80 mm b, g and m, and the 120 mm p and m.

## Whole word

| cell | arm | stitches / trims | lowercase stations >45° | lowercase short / crossed | capitals >45° · short / crossed | plan md5 | digitize |
|---|---|---|---|---|---|---|---|
| 80 mm | OFF | 2747 / 5 | 5 | 0 / 75 | 2 · 1 / 54 | `702171ea` (= main) | 122 s |
| | main ON | 2746 / 5 | 1 | 0 / 76 | 2 · 1 / 54 | `62eb6254` | 150 s |
| | **this ON** | 2748 / 5 | **0** | **0 / 46** | 2 · 1 / 54 | `2fc0b87b` | 368 s |
| 120 mm | OFF | 4439 / 11 | 13 | 10 / 97 | 2 · 6 / 78 | `0dc901eb` (= main) | 179 s |
| | main ON | 4406 / 10 | 7 | 12 / 89 | 2 · 6 / 78 | `8fb7b4d5` | 185 s |
| | **this ON** | 4445 / 11 | **2** | **8 / 64** | 2 · 6 / 78 | `f48b3053` | 353 s |
| 50 mm, `small_text_true_size` OFF | OFF | 1716 / 7 | 0 | 0 / 21 | 0 · 0 / 21 | `7dc6a84a` (= main) | 54 s |
| | main ON | 1726 / 7 | 0 | 0 / 16 | 0 · 0 / 21 | `ba01eae3` | 52 s |
| | **this ON** | 1718 / 7 | 0 | 0 / 15 | 0 · 0 / 21 | `caabf786` | 178 s |

- The capitals sew as OFF in every cell. That includes the 50 mm G #972 cured: its
  per-shape run md5 is unchanged ON, and the shapes ON moves at 50 mm are the m and
  the p only.
- The plan md5 hashes every run's kind and points to 4 decimals, in plan order.
  Times are wall seconds on Kent's laptop with another session digitizing beside it.
  They show a real cost, though: the judge sews every candidate, so **ON digitizes
  this word 2–3.4x slower than main ON**. A lowercase-heavy job pays that on every
  digitize.
- `measure.json` beside this file has every cell's per-glyph counts and per-shape
  run md5s.

## Files

- `lowercase-80mm-line.png`: the 80 mm lowercase line, thread render, OFF over ON.
- `lowercase-{80,120}mm-{p,b,g,a,m}.png`, `lowercase-80mm-e.png`: stitch-path zooms.
- `lowercase-50mm-tso-line.png`, `lowercase-50mm-tso-G.png`: 50 mm with
  `small_text_true_size` OFF, the cell where #972 cured the G (identical ON).

## Candidates, not constants (gate 1)

`COVER_SLACK` (0.5 W²), `SEWN_FOLD_DEG` (45°) and `SEWN_SHORT_FRAC` (0.5) join
`STALL_FRAC`, `FOLD_DEG`, `FOLD_MIN`, `STUB_WIDTHS` and `TURN_MAX_DEG`. They are
shape ratios read from one synthetic word, and nothing has been sewn.
