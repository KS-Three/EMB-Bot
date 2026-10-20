# golden_tee's O at 4 and 5 mm: the satin hold-off and the glyph guard behind `cfg.open_cored_counters` (built OFF, 2026-10-19)

#988 built `cfg.open_cored_counters` and named two things that had to exist before it
could be flipped: the satin tiers must hold off the sub-floor hole the flag traces, and a
guard must keep the flag to letters (its one corpus move was five false positives on the
phone screenshot). Both are built here, OFF, behind the same flag. No new default
behaviour, no new constant, no mm number touched (gate 1).

Thread renders of EMB-Bot's own output (`digitizer_core.stitchviz` via
`tools/small_print.py`'s `render_line`), 40 wt thread at its laid width, 120 px/mm, red
= the source outline traced at the 100 mm reference (line "second", GOLF). Windows, one
digitize at a time, this branch on main 346912eb.

## What was built

**The glyph guard** (`pipeline.cored_counter_core`). The taggers that say what a glyph
is run after vectorization; the walk that names a counter runs in stage 3, on masks, in
both stage-3 calls (the gradient lane's and the pipeline's). So the question is put to
the generation the flag would otherwise change: stages 0-4 run once more with the flag
OFF, every region `columns.is_lettering` calls a letter is painted into the frame
(exterior less interiors), and a core of stage 1's `enclosed_mask` is kept only when at
least half its pixels lie under one. A core the guard drops leaves the mask whole, so
both stage-3 calls take the OFF path there by the same code. The pre-pass is paid only
when the enclosed mask has a component between the run floor and the area floor.

**The satin hold-off.** Stage 3 marks each cored counter (`RegionMask.cored_counter`,
`Region.meta["cored_counter"]`); `plan_stitches` hands their polygons to stage 7, which
finds the interior of each satin shape a counter covers (`cored_holes_of`) and gives THAT
hole the small-print floor's two holds, at half the block's laid width:

- the Column lane (`lettering_columns_shape`, `counter_holes`): `_clear_counters` and
  `_counter_safe_pieces` on the cored holes alone (`counter_hold_polygon`), the letter's
  other holes sewn as the lane sews them with the floor off; with `small_print_floor` ON
  every hole is held already and nothing changes;
- the plain tier (`satin_shape`, `counter_holes`): the skeleton reads a sub-floor hole as
  a pinhole (its loop collapses into the junction cluster, the width profile smooths
  across it), so each column is read back as stations (`strip_splits`), held and cut by
  the same two functions, and re-emitted as one column per piece (`_hold_off_counters`);
  underlay and travel runs are cut at the counter (`_cut_runs_off_counters`), the link
  rule does not sew across one, and no chained link does either.

## golden_tee GOLF, the O's counter open (`tools/small_print.py`'s `counter_open`, 40 wt)

| cap | OFF | #988's flag alone | flag now (guard + hold-off) | floor ON, flag now | guard bypassed (scratch) |
|---|---|---|---|---|---|
| 4 mm | 0.147, 1,044 st / 11 tr | 0.204, 1,044 / 13 | **0.147, 1,044 / 11** (the guard refuses: ON is OFF) | 0.147 | **0.535**, 1,042 / 13 |
| 5 mm | 0.000, 933 / 11 | 0.069, 976 / 11 | **0.143**, 970 / 11 | 0.143, 982 / 14 | (admitted: same as the flag) |

`open` is the share of the REFERENCE counter (the 100 mm trace, scaled) that no thread
of any shape covers, the thread painted at its laid width. Two ceilings bound it:

- **the instrument's**: a thread held exactly at the hole's edge all round leaves the
  hole eroded by half a laid width open. For the reference counter that is 0.41 at 4 mm
  (1.19 mm²) and 0.51 at 5 mm (1.85 mm²);
- **the trace's**: the engine only knows the hole it traced, and the raster's inner edge
  comes out fat. At 4 mm the traced hole is 0.90 mm² (0.76 of the counter); at 5 mm it is
  0.77 mm² (0.42 of the counter), and eroded by half a width that leaves 0.115 of the
  counter. The 5 mm arms sit at that ceiling (crosses are not perpendicular to the edge
  everywhere, so a held column leaves a little more than the erosion says).

**At 5 mm the hold-off does what #988 asked.** The O (`Sbf659511`, the Column lane) lays
no stitch in its traced hole: 27 satin, 4 underlay and 3 travel segments ran through it
with #988's flag alone, 0 of each now. The opening goes 0.069 → 0.143, level with the
floor-ON arm, 6 stitches fewer than #988's flag alone (976 → 970); the floor-ON arm
itself is unchanged (982 / 14, as #988 measured it), since the floor already holds
every hole. What still sews in the hole is a
different shape: `S9ef10791`, the non-lettering ground the letters sit on, 14 satin
segments in the traced hole under both arms. Its own artwork polygon never reaches the
counter (it is not among the shapes round it); stage 5 extends it under the O and that
extension carries no hole for the cored counter. That is stage 5's, not the satin
tiers', and it is not touched here.

**At 4 mm the guard refuses the O.** The gold O is sub-floor (2.13 mm²) and is absorbed
into the Champagne satin shape `Sc7d3eacb` (9.4 mm², no tagger calls it lettering), so
its core lies under no glyph and the flag does nothing: ON is OFF, byte for byte, 0.147.
With the guard bypassed in a scratch run (`pipeline.cored_counter_core` replaced by the
raw enclosed mask; not reachable through the flag) the plain tier's hold-off opens the
counter to **0.535** — the widest opening measured on this O at any cap — 22 satin
segments in the counter → 4, 7 in the traced hole → 0. The cut drops the halves of the
crosses through the hole that fall under the cross floor (`SATIN_MIN_CROSS_MM`), so the
opening reaches past the traced hole to the counter's own edge, and a little past it at
the top right (`golden_tee_4mm_o_noguard.png`). Not a physical-constant question: the
cross floor is the engine's own, and a ring column round the hole (a loop the skeleton
kept) would sew that band; the pinhole read is the next thing to fix on this tier.

## Known limits (from the review of the first cut)

- **The guard reads `is_lettering` on the flag-OFF generation**, where the counter is
  filled, so a letter whose only hole is that counter can read as a solid blob
  (`lettering_columns_skip_blobs`, default ON) and be refused. A refusal is OFF, so
  nothing is lost against today, but it bounds what the flag can ever open.
- **A column that merely grazes the hold zone is re-emitted** through the Column lane's
  zigzag (`columns._satin_points`), whose split comb reads the cross legs alone where
  `satin_stroke`'s reads cross and return legs in turn. Identical for crosses up to
  `SPLIT_SATIN_ABOVE_MM` (every small-print column); on a wider column beside a cored
  hole the split points can move. Cosmetic.
- **A hop across the counter is a jump, and under `trim_at_mm` an untrimmed one** --
  the link rule's own answer, the same the small-print floor gives in the Column lane
  (a routed path round the counter where one exists, else a jump). `counter_open`
  paints needle-down thread only, so a float would read as open. Counted at 5 mm: no
  jump, trimmed or not, crosses the counter; the O's pieces are linked round it.
- **A bean or underlay run is cut stitch by stitch**, never as one polyline: GEOS's
  overlay dedups overlapping edges, and the first cut turned a three-pass bean into one
  pass over its whole length (found by the review, fixed, pinned in the tests). The 5 mm
  numbers above are unchanged by the fix (970 / 11, 0.143).

## The guard's verdicts

| design | core's holder, flag-OFF generation | tags | verdict |
|---|---|---|---|
| golden_tee 5 mm, the O | `S34c0ae97`, 6.2 mm² | `lettering_group` | kept |
| golden_tee 4 mm, the O | `Sc7d3eacb`, 9.4 mm² (the Champagne satin) | none | refused |
| screenshot, `S390dbd8c` 0.90 mm² | `Sc8148c53`, 490 mm² ground; `S7407a854`, 0.5 mm² rescued fragment | none; `lettering_group` but a drawing fragment (`is_lettering` False) | refused |
| screenshot, `S4d8bca9f` 0.20 mm² | `Sc8148c53` | none | refused |
| screenshot, `S8beb51c0` 0.47 mm² | `Sa5732b09`, 41.7 mm² fill | none | refused |
| screenshot, `Sf6cc12cd` 0.19 mm² | `Sc8148c53` | none | refused |
| screenshot, `Sac1dc87b` 0.40 mm² | `Sac1dc87b`, 0.4 mm² rescued fragment | `lettering_group`, `is_lettering` False | refused |

Screenshot ON is OFF: see the corpus table.

## What the pre-pass costs

One stages-0-4 run more, on a design with a candidate core. golden_tee at a 4 mm cap:
139 s OFF, 262 s ON; at 5 mm: 138 s OFF, 248 s ON (the whole digitize, `measure`).
The screenshot at 80 mm: `build_generation` 58 s OFF, 111 s ON; the whole digitize
78 s OFF, 127 s ON. Stages 0-4 are most of a gradient logo's time, so a design with a
candidate core pays close to double. A logo whose enclosed mask has no component
between the run floor and the area floor pays nothing.

## The 17-design corpus (`small_lettering_compare.corpus_designs`), OFF beside ON

Measured on this branch (main 346912eb), Windows, one digitize at a time. Every OFF md5
is #988's OFF column. ON is OFF on all 17: the guard refuses the screenshot's five cores,
and no other design has a candidate core a glyph holds at its corpus size (golden_tee's
O counter is over the floor at 80 mm). Where no core is a candidate the ON run costs
nothing extra (becker 25 → 27 s, fremont 133 → 124 s).

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
| screenshot | 8,505 / 62, `ae664b23` | identical | 0 |
| fremont_hat81 | 15,359 / 42, `799ba5bc` | identical | 0 |
| fremont_hat925 | 18,725 / 55, `24936229` | identical | 0 |
| sp_synthetic_2.5 | 318 / 1, `42401291` | identical | 0 |
| sp_synthetic_3 | 378 / 2, `88822294` | identical | 0 |
| sp_synthetic_4 | 547 / 4, `290e5ab0` | identical | 0 |
| sp_fremont_tagline_2.5 | 590 / 5, `c57e1189` | identical | 0 |
| sp_fremont_tagline_3 | 719 / 5, `df03b9cc` | identical | 0 |
| sp_fremont_tagline_4 | 985 / 10, `35ff0da6` | identical | 0 |

md5s are Kent's Windows box; Fremont's stream md5 is per machine
(`docs/renders/detail-spokes/README.md`).

## Renders

- `golden_tee_4mm_o_off_on.png`: OFF (left) | ON (right), the guard refusing: identical.
- `golden_tee_4mm_o_noguard.png`: OFF | the hold-off with the guard bypassed (scratch).
- `golden_tee_5mm_o_off_on.png`: OFF | ON, `small_print_floor` off.
- `golden_tee_5mm_o_floor_on.png`: `small_print_floor` ON both sides, flag OFF | ON.

*(measured 2026-10-19 — `pipeline.cored_counter_core`, `stage6_satin._hold_off_counters`,
`columns.counter_hold_polygon`, `tests/test_open_cored_counters.py`)*
