# golden_tee's O at 4 and 5 mm caps, and `cfg.open_cored_counters` (built OFF, 2026-10-19)

MASTER_SCOPE 47's residue: with `small_print_floor` ON, golden_tee's O is still shut at
4 and 5 mm caps. The doc called it "a trace question". It is one, and this folder shows
where the counter goes and what the new flag changes.

Thread renders of EMB-Bot's own output (`digitizer_core.stitchviz`), 40 wt thread at its
laid width, not cloth. Red is the source outline traced at the 100 mm reference
(`tools/small_print.py`, line "second", GOLF). Windows, one digitize at a time, main
5fbcf02f.

## Where the counter goes

`prep_raster_o_counter.png` is the prep raster round the O's counter, 16x nearest. The
counter is not one colour. It holds a white core (stage 1's `enclosed_mask`, page
colour), a dark keyline, a grey bevel, and cream and orange slivers. Each is under
`min_detail_mm`² and under a thread wide.

A spy on both `resolve_small_regions` calls (the gradient lane's, then the pipeline's)
shows two paths.

| cap | gradient-lane stage 3 | stage 4 | result |
|---|---|---|---|
| 5 mm | the gold O is full-size (3.33 mm²); keyline 0.56, bevel 0.66, cream 0.10 and orange 0.19 mm² are each **absorbed into the O** (3.33 → 5.95 mm²) | the white core (0.34 mm², the enclosed population) is a hole under the hole floor (0.5625 mm²) and is **filled** | the O (Wheat) has **no hole**; satin across the counter, 0.00 open |
| 4 mm | the gold O is itself under the floor (2.13 mm²), so the bands have no full-size neighbour: the keyline (0.36 mm²) is **rescued** as a shape of its own, the bevel is dropped | the keyline ring's inside is filled, then the shape re-snaps by its pixels | a 0.99 mm² **Silver disc** sewn by the run tier inside the O's real hole; 0.15 open |

So the counter is its own colour region at 4 mm and part of the letter at 5 mm. Neither
`keep_counters` (its colour test reads the keyline as nearer the letter than the page)
nor the bean tagger is involved.

## What the flag does

`cfg.open_cored_counters` (`stage3_segment.cored_counters`). For each enclosed core of at
least `RUN_MIN_AREA_MM2` and under the area floor, it walks the shapes round the core
inside out. A shape narrower than the thread's laid width everywhere (twice its largest
distance-transform value) is a band, and the walk goes past it. The first shape that is
not a band is the letter. When its hole round the core is under the area floor, every
sub-floor region in that hole is kept out of the letter as `source="counter"`, tagged
`counter` and `enclosed_background` and left unsewn. It runs in both calls, gated to
logos the way `keep_counters` is. No new constant.

## golden_tee GOLF, the O's counter open (`tools/small_print.py`'s measure)

| cap | floor OFF, flag OFF | floor OFF, flag ON | floor ON, flag OFF | floor ON, flag ON |
|---|---|---|---|---|
| 4 mm | 0.15 open, 1,044 st, 11 tr | 0.20, 1,044 st, 13 tr | 0.15, 1,044, 11 | 0.20, 1,044, 13 |
| 5 mm | 0.00, 933 st, 11 tr | 0.07, 976, 11 | 0.01, 964, 12 | **0.14**, 982, 14 |

The O's polygon now carries the counter as a hole at both sizes (0.90 mm² at 4 mm,
0.77 mm² at 5 mm, where it had none). The Silver disc is gone at 4 mm. **The counter is
still mostly shut**, because the satin over it still lays across the hole:

- At **4 mm** the O sits in a non-lettering satin shape (`Sc7d3eacb`, Champagne). The
  plain satin tier's columns cross the 0.90 mm² hole, and `small_print_floor` does not
  reach that tier.
- At **5 mm** the O is lettering (Column lane). With the floor ON a real opening shows
  (`golden_tee_5mm_o_floor_on.png`), but the rails' pull still closes most of it.

That second blocker is the satin tiers', not the trace's, and is not fixed here.

Renders: `golden_tee_{4,5}mm_o_off_on.png` and `_line_off_on.png` (floor off, flag OFF
left, ON right); `_floor_on.png` (floor ON both sides, flag OFF left, ON right).

**One side effect shows in the 5 mm renders:** the O's thread moves Wheat → a brighter
yellow, and a neighbour sews darker grey. The kept bands still enter the gradient lane's
palette selection as regions.

## The 17-design corpus (`small_lettering_compare.corpus_designs`), OFF beside ON

| design | OFF | ON | changed shapes |
|---|---|---|---|
| becker | 8,758 / 29, `19b38100` | identical | 0 |
| tires | 2,732 / 8, `6a6ada47` | identical | 0 |
| enthusiast | 2,414 / 8, `9944fec7` | identical | 0 |
| fremont | 20,882 / 49, `44382087` | identical | 0 |
| bridge | 18,923 / 99, `197a3287` | identical | 0 |
| golden_tee (80 mm) | 8,412 / 45, `9208ffe4` | identical | 0 |
| gaulke | 4,893 / 23, `9f1a2036` | identical | 0 |
| drone | 19,281 / 130, `a709b157` | identical | 0 |
| **screenshot** | 8,505 / 62, `ae664b23` | **8,436 / 60, `b38e5446`** | **47** |
| fremont_hat81 | 15,359 / 42, `799ba5bc` | identical | 0 |
| fremont_hat925 | 18,725 / 55, `24936229` | identical | 0 |
| sp_synthetic_2.5 | 318 / 1, `42401291` | identical | 0 |
| sp_synthetic_3 | 378 / 2, `88822294` | identical | 0 |
| sp_synthetic_4 | 547 / 4, `290e5ab0` | identical | 0 |
| sp_fremont_tagline_2.5 | 590 / 5, `c57e1189` | identical | 0 |
| sp_fremont_tagline_3 | 719 / 5, `df03b9cc` | identical | 0 |
| sp_fremont_tagline_4 | 985 / 10, `35ff0da6` | identical | 0 |

Sixteen of 17 are byte-identical. **screenshot moves, and the move is false positives**:
five shapes kept as counters (0.19 to 0.90 mm²), −69 stitches, −2 trims, bare area
7.19 → 8.44 mm², `ARTWORK_UNCOVERED` unchanged. `screenshot_*.png` (OFF left, ON right,
60 px/mm): ON unsews a dark run curve and a grey satin mark inside the tyre tread, and
opens a bare hole inside a grey fill. None of these is a letter's counter. Golden_tee
itself does not move at its corpus size (80 mm), where its O's counter is over the
floor.

md5s are Kent's Windows box; Fremont's stream md5 is per machine (see
`docs/renders/detail-spokes/README.md`).

*(measured 2026-10-19 — `stage3_segment.cored_counters`,
`tests/test_open_cored_counters.py`)*
