# Adversarial review of the 2026-11-13/14 director run

This review covers the engine PRs the director run produced: #1476-#1490, #1508, #1510 and #1512-#1518. The checklists were `.claude/agents/emb-bot-reviewer.md`, `stitch-geometry-auditor.md` and the `CLAUDE.md` footguns.

**How it was read:**
- Four Sonnet readers took the diffs in four groups, and every finding they raised was traced at its line before it went in here.
- I read #1515 and the flipped code myself.
- Every number is from stitches I digitized on the laptop, at main 66b11432 unless a row says otherwise, with about eleven other sessions sharing the CPU. So seconds are loaded seconds; compare them only within one row.
- The harness is the service's own request parser (`tools/pro_pair.config`), with the md5 taken over every run's points, kind, jump, trim and colour. "Steps over 12.1" counts needle-down steps longer than a DST record, inside one colour. The harness is not committed (scratchpad only).

Severity is stated plainly per finding: **real problem** or **nitpick**. There are no style notes.

## Verdict

**Two real bugs in code that ships, both Cancel latency, both fixed:**
- [#1521], merged: the group code that #1515 turned ON tested every pair of shapes, with no seam.
- [#1524], open: #1515's seams for the redraw left a ring's fit and cap check unseamed.

Neither makes a stitch wrong. **No stitch-level bug was found in the 21 PRs.**

**No flag leaks while OFF.** With every director flag OFF, main is md5-identical to the tree before the run (a15e8ae6) on all four designs below. That covers every built-OFF PR in the run on those four.

| design | before the run (a15e8ae6) | main 66b11432, every director flag OFF |
|---|---|---|
| Becker, 100 mm hat | `5f2a2257da4f`, 15,798 st, 12 trims | `5f2a2257da4f` |
| Precision Drone render, 80 mm left chest | `2c9649f16f19`, 19,112 st, 106 trims | `2c9649f16f19` |
| Bridge Bar, 100 mm hat | `ca69af73d3e6`, 16,587 st, 20 trims | `ca69af73d3e6` |
| Hotel Fremont, 100 mm hat | `1924ae8ff665`, 17,875 st, 30 trims | `1924ae8ff665` |

## Findings, most severe first

### 1. Real problem, fixed in [#1521] (merged): the group code flipped ON is quadratic and never hears a Cancel

**Where.** `digitizer/digitizer_core/group_consistency.py` (line numbers at 66b11432):
- `like_lines`, at :133, pair loop :147-152;
- its `_adopt_stacked`, at :85-117;
- `like_shapes`, at :343, pair loop :362-369;
- `shared_angles`, at :381.

Stage 7 calls them at `stage7_sequence.py:3160` (`group_consistent_tier`) and `:3489` (`group_consistent_fill_angle`). Both flags are ON since #1515.

**Scenario.**
- Every pair of shapes went through shapely (bounds, area, distance), and no `deadline.check` sat anywhere in the module.
- A flat design with many same-thread auto shapes held a Cancel for tens of seconds:
  - 1,600 squares: `like_lines` 31.6 s and `like_shapes` 27.8 s;
  - 82.1 s for the two together in the new test;
  - 400 squares: 1.7 s each.
- It runs once per stage-7 pass, and twice when the Column lane sews.
- Real designs reach it with fewer shapes:
  - qr_code at 80 mm: 45 shapes reach it, and `shared_angles` ran 2.3 s with no seam (one `best_fill_angle_deg` per member);
  - To a T beanie: 23 shapes reach it, 0.9 s, twice.

**Fix.**
- Each shape's bounds and area are read once.
- Sorted sweeps visit only pairs that can pass, with a box-gap reject before the distance.
- There is a seam per shape and per group member.

**Proof it moves no stitch.**
- The groups match the old loops (kept verbatim in the test) on six random scenes and a grid.
- The test fails 4 of 11 before the fix and passes after.
- End to end with the flips ON, the fix's tree is md5-identical to main on Becker 100 hat (`6a1fbe5320fc`) and Bridge 100 hat (`98574c91a0ce`).

### 2. Real problem, fixed in [#1524]: the redraw ON still holds a Cancel for seconds inside one ring

**Where.**
- `letterform_priors._offenders` (:760) and `_cap_check` (:890) each read one shapely `Point` plus `distance` per sample, with no seam.
- `outline_redraw._merge_runs` (:77) has none per run.
- #1515 put seams in `_worst_breach` only, and #1515's last seam (`outline_redraw.py:353`) is followed by `_cap_check`.

**Scenario: To a T beanie at 100 mm, redraw ON (the default).**

| what | time |
|---|---|
| longest gap between two `outline redraw` checks | **7.07 s** |
| one `fit_ring_plain` (421-point ring) | 7.07 s |
| `_cap_check` calls | 6.06 s, 5.07 s, 3.63 s |
| one shape's `redraw_polygon` | 25.1 s |
| Becker at 96 mm hat, longest redraw gap | 0.6-0.9 s |

**Profile** on a 40 mm staircase disc at 4 px/mm (one 1.62 s fit): `_offenders` 0.97 s, `_merge_runs` 0.39 s, then `_cap_check` 0.61 s more.

**Fix.**
- A check every 256 samples in both reads, labelled "ring fit".
- A check per run in `_merge_runs`.
- It moves no number: an armed-but-unset scope gives the same fit and cap, and the test pins that.
- The test fails 4 of 5 before the fix and passes after.

**The cost the flip did not price.** Over the 5-pass ledger #1515 captured, the three To a T jobs got slower; every other job is flat:

| job | median seconds, before -> after |
|---|---|
| toat_beanie | 6.9 -> 10.9 |
| toat_machine_hat | 9.6 -> 13.4 |
| toat_machine_beanie | 7.5 -> 11.5 |

That is about 1.5x. To a T is upscaled (4.1-4.5 px/mm), so the redraw runs on every shape, and the 25 s polygon above is the redraw. This was not attributed by an A/B on one runner. The seams make it cancellable; they do not make it faster.

### 3. Real problem for the flips, not a code bug: guards and constants fitted on the designs they were judged on

None of these has a hold-out design.

| constant | where | fitted on | state |
|---|---|---|---|
| `SOLID_STROKE_FRAC` 0.45, `SOLID_GROUP_SHARE` 0.75 | `textcluster.py:1061-1062` | Jakarta's mark alone (squares 0.58, letters 0.15-0.21) | **ON** since #1515 |
| `BLEND_BAND_PX` 2 | `stage2_quantize.py:371` | silhouette logo, ProSeal, Swiss Ivy ("the smaller depth that reaches all three") | **ON** since #1515 |
| `MARGIN` 1.5 as the width tie-break | `group_consistency.outline_side` (#1517) | MFab hat 113.5 (1.46x / 3.4%) and AHORA | OFF; another lane is flipping it |
| `APEX_GUARD_SHARE` 0.9 + hairline rule | `outline_cut.py:419` | the 43-design apex corpus that also judged it | OFF |
| `GUARD_MIN_FRAC` 0.5, `GUARD_MIN_MM2` 5.0, and acceptance by `worse_mm2` | `proofread_guard.py:43-49` | the 26-design census that ranked the step | OFF |

**Failing scenarios.**
- **Solid guard.** Any small word whose letters stage 4 traced solid reads at least 0.45 on three quarters of its members. Examples are a heavy slab at 6 mm, or a word whose counters closed. The word loses its text tagging silently. The guard's own comment names the case ("808"), and no such word is in the corpus.
- **Blend band.** A real line 2 to 4 working px wide, whose colour sits on the chord between its two neighbours, is dissolved into them. Examples are a grey keyline between black and white, or orange between red and yellow. Chord colour is the only test of a blend.
- **Proof-read guard.** It keeps a replan when `worse_mm2` falls by 5 mm2. Nothing prices the double thread its remedy lays over a colour already sewn, so the instrument that wrote the rule also accepts it.

**What would settle it.** Each needs a pass over designs it was not fitted on, read by eye beside the art:
- the solid guard: a census of clusters it untags, which should be 0 outside Jakarta's mark;
- the band: the commons logos with thin mid-tone keylines.

### 4. Real problem before any flip: four OFF features have no Cancel seam in their loops

**#1512 edge-walk.** `columns.py:2622` `_edge_walk_trails` and `:2804` `_edge_walk`. The module never imports `deadline`. Per letter whose base walk leaves a trim or a hop on finished satin, it does two things:
- prices up to `_EDGE_WALK_MAX_TRAILS` = 400 Euler trails with shapely unions;
- re-sews `column_runs` for up to 8 candidates.

**#1513 fine bars.** `fine_bar.py:206` loops over bar candidates. Each builds a full-image band mask, two full-image Lab norms (:238), `connectedComponents` and `np.isin` (:246). It should crop to the band's box, then check per candidate.

**#1477 / #1487 proof-read.** `proofread.py` and `proofread_guard.py` contain no `deadline` at all:
- `thread_raster` (:288);
- `read_arrays` (:709);
- `_best_shift`;
- `guard_clipped`, which reads twice around a replan.

**#1486 / #1480.** Neither `bevel_fold.py` nor `regular_structure.py` has a seam. `find_groups` (:548) is bounded by `MAX_ALIGNS` 2000.

None is timed here, and nobody waits on an OFF flag today. Each needs a seam and a measured gap before its flip. The lesson of findings 1 and 2: both seam bugs shipped through a flip.

### 5. Real but minor: a piece lift is never counted as a lift inside a shape

**Where.** `stage7_sequence.py`:
- `:3828-3830`: `lift_piece` makes the next piece's first run a jump (with a trim past `trim_at`), but `o_jumps` adds only `f_report["jumps"]`;
- `:4124-4126`: the same for `k_jumps`.

Every other stage-7 lift is counted (`:3883`, `l_report["jumps"] += 1`). The count feeds `LONG_JUMPS_TRIMMED`, "The thread is lifted N times inside a shape" (`:5531`). The docstring at `:836` says that count "still reports what the machine will actually do".

**Scenario.** On Becker at 100 mm hat, piece lift ON adds a trim (12 -> 13). Read from the code, the count does not add that lift. I did not read the warning off a run.

`inshape_piece_lift` is ON since #1515. The customer sees no warning (Kent's no-warnings ruling), so this is a metric understating, not a wrong stitch. **Not fixed here.** A test needs a constructed outline body sewn in pieces.

### 6. Nitpick: #1515's flip table priced the redraw by bare fabric only; the trims sat in its doc

**Ledger as re-captured in #1515** (all flips together, CI, 5 passes):

| job | trims | needle-up |
|---|---|---|
| Becker hat large | 11 -> 18 | 327 -> 488 mm |
| MFab hat | 16 -> 24 | 556 -> 735 mm |
| Becker LC large | 12 -> 16 | not shown |
| MFab LC | 19 -> 21 | not shown |

**My own runs, Becker at 100 mm hat:**

| arm | trims |
|---|---|
| OFF | 12 |
| piece lift alone | 13 |
| redraw alone | 16 |
| all flips | 18 |

The director's "catch" column for `outline_redraw_k` named only Becker's bare fabric. The redraw's own table did carry its trims: Becker hat 12 -> 16, MFab hat 17 -> 21 (`docs/satin-flat-ends-2026-11-14.md:30-37`, and the memory note's "redraw alone" line). So the cost was recorded, not hidden. When a flip moves trims by +4 to +8 on the pro designs, the table Kent reads should say so, and so should its wall time (finding 2).

### 7. Nitpick: nine test files now test shipped features on a configuration that does not ship

#1515 pinned `outline_redraw_k` to `PRE_FLIP` (None) in the tests of:
- `coverage_edges`;
- the edge-cap budget;
- run spans;
- subpixel edges;
- wide columns;
- satin per stroke;
- small stem;
- rail comp;
- junction patch.

Each says why: the record was measured on that engine. The consequence is that nothing but the nightly tripwire checks those features with the redraw ON. A regression of, say, `subpixel_edges` under the redraw would pass the suite. The flip PR itself measured that pair: the redraw sits a 50 mm disc's edge 0.065-0.088 mm inside the true circle.

### 8. Nitpicks in the group code (ON), not changed by #1521, so that it moves no output

**`_adopt_stacked` can add one piece to two lines, or to one line twice** (`group_consistency.py:116`, after `g.extend([x, y])`). `x` and `y` stay in `free`, so a second pair that includes `x` extends again.
- It needs one piece stacked with two partners.
- It skews `group_verdict`'s median, which decides when no member is decided.
- `out.update` lets the last line's verdict win.

**`like_shapes` is single-linkage.** A same-thread size ramp (areas 1, 1.4, 2, 2.8 ...) chains into one group, and every member takes the biggest member's `best_fill_angle_deg`. The reference member is the biggest by area even when it does not sew as a fill.

### 9. Nitpicks elsewhere

- **`stage2_quantize.py:860`** reads `getattr(cfg, "flat_blend_band_any_scale", False)` while the field defaults to True. Only a hand-built stub config differs.
- **`outline_cut.build_column`'s memo key** (`:1917`) holds `_APEX_CUT` and `_CORNER_FOLD` but not `_APEX_GUARD`. It is harmless, since `_MEMO` lives for one `letter_columns` call inside one guard scope, but it is one line to add.
- **`tests/test_text_cluster_solid_guard.py:111-114`** asserts on pipeline SOURCE TEXT. A reformat breaks it, and a behavioural regression would not. The default assertions beside it do pin the right thing.

## Outside the director's PRs: long Cancel gaps seen while measuring

These two came up in the same timing runs. Neither code path is one these PRs touched, and they need their own trace.

| design | longest gap | between the checks |
|---|---|---|
| qr_code, 80 mm LC | 17.3 s | "stage 1.5" -> the first "stage 2" (design ramp, cored-counter core, quantize set-up) |
| To a T beanie, 100 mm | 15.4 s | "plan_stitches" -> "stage 5" (art outlines, underfills, hairlines) |

## Checked and clean

- **#1515's promotion of two `cfg.extra` keys to fields.** No reader of the old keys is left in `digitizer_core`, `digitizer_service`, `tools`, the tests or `app/src`. Nothing in the Studio or the service sends any flipped flag, so nothing pins an old value. The generation cache is in memory (`jobs.GenerationCache`, 4 entries), so a restart drops anything planned under old defaults.
- **Shape memo.**
  - The shared fill and satin angles reach `stitch_shape` / `satin_shape` as arguments, so they are in the key.
  - `_APEX_GUARD` and `_CORNER_FOLD` are listed in `_AMBIENT`.
  - #1487's `_INERT` reasoning for `stage5_overlap._KEEP_ART` holds: `resolve_overlaps` (`pipeline.py:2291`) runs before the stage-7 scope opens (`:2368`), and the guard's replan runs after that scope has closed and emptied.
- **Customer angles are never overwritten** by `group_consistent_fill_angle`. Review angles, the design angle, the cfg angle and the stage-5 axis all make a shape ineligible (`_fill_angle_for` not None).
- **Studio "Flatten shading" (#1508).** The request key is a dataclass field accepted by `_CONFIG_FIELDS`. `generation_key` changes with it, so a toggle re-digitizes.
- **`lift_piece` (#1483) branches.** It replaces runs without mutating them, sets no double trim, and keeps every TRAVEL point within `MAX_STITCH_MM`.

## One headline number per engine PR, re-measured

| PR | claim | measured here | holds? |
|---|---|---|---|
| every built-OFF PR (#1476-#1480, #1483, #1485-#1490, #1510, #1512-#1514, #1517) | off, byte-identical | md5 equal on 4 designs (table above) | **yes** |
| #1483 `inshape_piece_lift` | no needle-down step past a DST record; +1 to 2 trims | Becker 100 hat. OFF: 2 steps over 12.1 mm, longest 36.9 mm. Lift alone: 0 over, longest 4.94 mm; trims 12 -> 13 | **yes** |
| #1479 `outline_redraw_k` 0.75 | Becker hat trims 12 -> 16 (its table) | Becker 100 hat, redraw alone: 12 -> 16, 15,798 -> 15,412 st. It keeps the 3 long steps (longest 39.5 mm) that the lift then removes | **yes** |
| #1488 `flat_blend_band_any_scale` | byte-identical on Drone | band alone, Drone 80 LC: `2c9649f16f19` = OFF | **yes** |
| #1476 one baseline + solid guard | Fremont replayed 0 shapes different | both alone, Fremont 100 hat: `1924ae8ff665` = OFF | **yes** |
| #1515 the flips together | ledger Becker hat large trims 11 -> 18 | Becker 100 hat, all flips: 12 -> 18, 15,798 -> 15,444 st, 0 steps over 12.1 | **yes** (finding 6) |
| #1480 `regular_structure` | Bridge's handles alike | Bridge 100 hat, ON over the flips: trims 22 -> 20, 16,292 -> 16,049 st, 0 long steps; handle shape not measured | sane; shape claim not re-measured |
| #1486 `bevel_ring_fold` | Golden Tee's bevel flattens | Golden Tee 100 hat, ON over the flips: 7 -> 6 colours, trims 62 -> 46, 19,330 -> 18,844 st, 0 long steps | consistent; not seen by eye |
| #1513 `fine_bar_survive` | To a T's speed lines kept | To a T machine 100 LC, ON over the flips: +95 st, trims 25 -> 22, 0 long steps | consistent; not seen by eye |
| #1490 / #1512 / #1514 lettering stack | each alone | apex cut + guard + edge walk + buried together, Becker 100 hat: trims 18 -> 19, +73 st, 0 long steps | sane together |
| #1485 fat ink | small gain | both, Becker 100 hat with the flips: `6a1fbe5320fc`, the same md5 as the flips alone. No effect on Becker | holds, trivially, here |
| #1517 outline-body guard | MFab 113.5, outline body + redraw = redraw alone, 22,785 st, 19 trims | MFab hat 113.5, flips ON, body ON vs OFF: both `ae6efb3b8625`, 3 colours, 22,789 st, 20 trims. The +4 st / +1 trim is piece lift, which merged after it | **yes** |
| #1482 renderer | render only | not re-measured (no stitch moves) | n/a |
| #1477 / #1487 / #1510 | metrics only | covered by the OFF md5 | yes |
| #1508 | Studio tick reaches the service | read, not run | yes, by reading |
| #1516, #1518 | open at review time | diffs read; no bug found | not re-measured |

## Untried pairs

All runs are on main with the #1515 flips ON, plus the pair named. Nothing crashed, and no run sewed a needle-down step over 12.1 mm.

| pair | design | result |
|---|---|---|
| `regular_structure` + redraw + group fill angle | Bridge 100 hat | trims 22 -> 20 |
| `bevel_ring_fold` + blend band | Golden Tee 100 hat | 7 -> 6 colours, trims 62 -> 46 |
| apex cut + guard + edge walk + connectors buried, + redraw | Becker 100 hat | trims 18 -> 19 |
| fat ink (both) + redraw | Becker 100 hat | md5 unchanged |
| `fine_bar_survive` + redraw | To a T machine, 100 LC | trims 25 -> 22, +95 st |
| `group_consistent_outline_body` + redraw (the known bad pair, after #1517) | MFab 113.5 hat | md5 identical to the redraw alone: the guard holds the vote |

These are counts, not an eye. A pair that sews no long step and moves trims a little can still look wrong. Only the MFab row has a sheet (#1517's).

[#1521]: https://github.com/KS-Three/EMB-Bot/pull/1521
[#1524]: https://github.com/KS-Three/EMB-Bot/pull/1524
