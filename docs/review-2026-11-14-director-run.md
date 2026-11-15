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

## Round two: the evening wave (#1519, #1522, #1523, #1526, #1528-#1532)

This round was read the same way as round one: four Sonnet readers over four groups of PRs, and every finding traced at its line before it went in.

**How the numbers were taken:**
- Merged PRs ran on main (10d1d863, with #1528 merged since as 1a1e0b54); open PRs ran on their heads.
- The runs used the same harness, on the shared laptop.
- Every open head (flags OFF) is a descendant of a main commit that gives the same Becker md5 as main before the wave, so "OFF equals its parent" is read against that one md5.

### Verdict

**No stitch bug in code that ships.** Every flag in the wave is OFF, and the one customer-reachable change (#1522) acts only when the Studio's Flatten shading box is ticked.

**One PR is red in CI for a real reason:** #1530 (finding R1).

**Two combinations go wrong without saying so**, both latent:
- `apex_pro` with `apex_cut` (R2), in an open PR, so it is the owner's to fix;
- `outline_inlets_kept` with the proof-read guard (R4), merged code, fixed in [#1534].

**No OFF leak.** With its flags OFF:

| tree | Becker 100 hat | other |
|---|---|---|
| main 10d1d863 (#1519, #1522, #1523 merged) | `6a1fbe5320fc` = main before the wave (66b11432) | MFab 113.5 hat: `ae6efb3b8625` = 66b11432; Fremont 100 hat: `1924ae8ff665` = 66b11432 |
| #1526 head | `6a1fbe5320fc` | |
| #1528 head | `6a1fbe5320fc` | |
| #1529 head | `6a1fbe5320fc` | |
| #1530 head | `6a1fbe5320fc` | |
| #1531 head | `6a1fbe5320fc` | |
| #1532 head | `6a1fbe5320fc` | Fremont 100 hat: `1924ae8ff665` |

### R1. Real problem: #1530 is red in CI and cannot pass as it stands

**Where.** The #1530 head adds `outline_cut._CURVE_CHORD` and `_CURVE_TRACE` (`outline_cut.py:383-384`) and lists neither in `shape_memo._AMBIENT` / `_CACHES` / `_INERT`.

**Failure.**
- `tests/test_shape_memo.py::test_every_contextvar_in_the_package_is_ambient_or_a_cache` fails.
- That test's own census, run on the head tree, reports exactly those two unlisted. The other five heads and main report none.
- CI shard 2/6 failed on the PR.

**Fix (the owner's).** Add `_CURVE_CHORD` to `_AMBIENT`, since it changes column geometry. Add `_CURVE_TRACE` to `_AMBIENT`, or to `_INERT` with a reason.

**Stale hits.** None today: `build_column`'s memo key hashes the densified piece, and the plan sets one chord.

### R2. Real problem for any flip of the pair, latent today: `apex_pro` turns `apex_cut` and its guard off for every letter

**Where.** `outline_cut.find_cuts` at the #1526 head, `:342-345`:

```
if _APEX_PRO.get(): kept = _apex_pro_cuts(...)
elif _APEX_CUT.get(): kept = _apex_cuts(...)
```

The guard (`_apex_guard_refuses`) lives inside `_apex_cuts`.

**Scenario.** With both flags ON, every letter `apex_pro` does not handle cuts as OFF, not as `apex_cut`. That covers anything under `APEX_PRO_MIN_W_MM` 2.0 and any crotch other than its V. Measured by the reader on `testdata/apex_letters.json`:
- `mfab105_N`: `apex_cut` alone cuts apex x3 + stub; with `apex_pro` it cuts `again, again`, the OFF cut;
- `mfab105_W`: the same.

Downstream, `apex = _APEX_CUT.get()` (`:2922`) still steers the scrap rule as if `apex_cut` were on, with no apex cut in the list.

**Gaps.**
- No test covers `apex_pro` beside `apex_cut` or the guard.
- `test_column_apex_pro.py` runs without `corner_fold`, which is True in production.
- `test_off_is_the_lane_as_it_was` compares two calls that are the same call, so it proves nothing.

**What to do.** Run `_apex_pro_cuts` first and `_apex_cuts` on the crotches it left, or refuse the pair loudly.

### R3. Real risk when ticked: #1522's Flatten shading rules were fitted on Golden Tee alone, and one rule deletes ink

**Where.** `bevel_fold._pro_read_rules`, rule (b), `bevel_fold.py:698-735` on main. A band qualifies when it:
- is a colour-cap-merged band (`color_cap_merged_from`);
- is up to `BAND_MAX_MM` wide;
- faces the page (`EDGE_HUG_FRAC`);
- touches exactly one body colour and does not wrap it.

Such a band is **deleted, not re-threaded**.

**Scenario.** A ticked design over the colour cap, where a thin real accent stroke's colour lost its spool. The stroke disappears and the garment shows through. Nothing tells the customer (the no-warnings ruling).

**Fitted on.**

| constant | value |
|---|---|
| `PAGE_OWN_DE00` | 3.0 |
| `COUNTER_PAGE_FRAC` | 0.3 (GOLF's O, 22%) |
| `COUNTER_BAND_FRAC` | 0.5 |
| `DARKEST_L_TOL` | 5.0 |
| `DARK_L_MAX` | 35 |

All were set from Golden Tee. The controls that moved were Drone and the crest; the four that stayed md5-identical show only that the rules do not fire there. **No design outside Golden Tee shows a rule firing correctly.**

**Seams.** `bevel_fold.py` has no `deadline.check`, and #1522 adds two kinds of loop:
- uncached `_Graph.contacts()` queries, re-walked per failed face;
- a pairwise `polygon.distance` in `_union_group`.

**Measured on low_poly at 80 mm LC:**
- Ticked, the stretch that holds the fold (`stage 4 thread revalidation` -> `text cluster neck splits`, `pipeline.py:1040-1133`) is 1.46 s with no check, the longest in the job.
- Unticked, that stretch is not among the five longest gaps (all under 1.22 s).

That is near the 1 s line on an 89-region design. A design with more bands goes further, and none was timed.

### R4. Real problem if both are ON, latent: `outline_inlets_kept` (#1528) and `proofread_guard_clipped` do not compose

**Where.** `pipeline.plan_stitches` at #1528 (now merged):
- `:41-42` re-plans `replace(result, regions=as_fill(...))`;
- the guard's `replan` (`:52-54`) calls `_plan_stitches(result, cfg)` on the ORIGINAL regions.

**Scenario.** Both are ON and a gear was moved to fill. If the guard prefers its replan, it keeps a plan in which the gear is a satin again, silently.

**Fixed in [#1534]:** the guard now reads and replans the result the plan was sewn from. Its test fails 1 of 3 before the fix and passes after.

### R5. Real problem before any flip: thresholds with no hold-out

| PR | constants | fitted on | hold-out |
|---|---|---|---|
| #1526 `apex_pro` | `APEX_PRO_DOWN_DEG` 30, `_SPLIT_W` 2.6, `_SNAP_DEG` 25, `_MIN_W_MM` 2.0, the 0.25 W shoulder, 0.3 slope ratio | Becker MARINE's M at five sizes | none. NEW reads worse than OFF on 2 of those 5 by its own instrument (chest small 12.6 -> 14.3, beanie 14.9 -> 16.5) |
| #1531 `rail_pair_bars` | 1.0, 0.5, `RAIL_PAIR_MIN_SHARE` 0.6 | and_pizza's Z (0.73), MARINE's R | final rule run on 2 designs; the 11-design pass was on the first rule |
| #1528 `outline_inlets_kept` | `SATIN_OVER_INLET_SHARE` 0.03 | the gap between Ahora's gear (0.104) and Becker's border (0.002) | none in between |
| #1529 `satin_push_keeps_gaps` | `keep_floor` 0.5 | Gaulke's E and S pins (pro 0.36) | Jakarta only as a guard; To a T's speed lines sew thinner |
| #1532 ground ring | `GROUND_RING_MM` 0.3, `GROUND_RING_SHARE` 0.5, `GROUND_MIN_IN` 0.25 | Fremont's EST 1895 | six designs where it does not fire; none where it fires |
| #1523 `speck_prune` | `SPECK_WIDTH_SRC_PX` 2, `_FIGURE_CONTACT_MIN` 0.75, `_PAGE_CONTACT_MAX` 0.1, `_MIN_DE00` 10 | low_poly | arabic_calligraphy, Fremont and outline_lineart do not move or barely move; none where it fires |

### R6. Nitpicks

- **#1528 matches more than notches.** `inlets()` also takes an acute concave valley (under about 70 degrees: a star's valleys, a heart's cleft) as an inlet. The tests use only a rectangular slot.
- **#1528 can double the plan's cost.** ON, any satin over an inlet re-runs the whole of stages 5-7 (`_plan_stitches` again).
- **#1531 merge hygiene.**
  - `pipeline.py` has `rail_pair_bars_scope(...)` joined onto the `apex_guard_scope` line with its continuation lost.
  - It will conflict textually with #1526's `with` block and `_AMBIENT` lines.
  - `_rail_pair_bar_axis` returns None when the share fails, instead of trying the next candidate.
- **#1523's test docstring is stale.** It says low_poly goes to 10,201 st / 70 trims; the body and doc say 10,325 / 76.
- **#1522's `dark_cut` is computed twice**, before and after `_pro_read_rules` deletes regions. If the darkest region is dropped, the second cut is lighter.
- **#1530's stage-4 guard is coarser than the lane's.** Stage 4 allows one source pixel (about 0.11 mm at 9.3 px/mm); the lane allows min(tol/2, 0.08 mm).

### Checked and clean (round two)

- **OFF paths, read line by line.** All are identical to their parents:
  - #1519: `room=None`, built only under its key;
  - #1529: `keep=None`; the union is built lazily inside `push_keep`;
  - #1528: not imported OFF; `GROWTH_FLAGS` strips it from `_off_angles`;
  - #1532: `_is_ground(..., False)` is the old `< 0.5`;
  - #1530: no densify;
  - #1526, #1531: their scopes yield without setting.
- **Shape memo.**
  - `_APEX_PRO` and `_RAIL_PAIR_BARS` are in `_AMBIENT`.
  - `_RAIL_PAIR_BARS` is in `build_column`'s key.
  - #1529's `rail_keep` / `pull_keep` are emitter arguments, so they are in the key.
  - Every new scope resets in a `finally`.
- **Cancel.** #1529's `_push_rails` keeps its per-rail-pair `deadline.check`. Measured with the flag ON on Becker: the longest gap anywhere is 0.84 s, and none falls in `satin rail push`.
- **Service and Studio.** `speck_prune` is a field, in `_CONFIG_FIELDS`, and in `engine_2026_10_27.json`. Every other new flag is a `cfg.extra` key read with `.get`, with no Studio or service reader to disagree.

### R7. Nitpick, but price it before a flip: #1532 ON adds 7 trims on Fremont

Measured on Fremont at 100 mm hat, both keys ON at the #1532 head: 17,875 -> 18,060 stitches, and trims **30 -> 37**.

The PR's table gives stitches only (15,968 -> 16,242 at 92.6 mm). The re-set moves the date 1.47 mm and re-sews its beans, so trims are the likely cost of the new spines, but that is not traced.

### R8. Nitpick: the group fill angle (ON since #1515) costs low_poly about 5.7 s a digitize

On low_poly at 80 mm LC, `shared_angles` ran 2.91 s and 2.78 s, once per stage-7 pass. That is about 10% of a 54 s job (loaded laptop): one `best_fill_angle_deg` per member of 63 shapes.

Since #1521 it is cancellable (a seam per member), but not cheaper. I did not check whether stage 6 then scans the same angles again for the members a group leaves alone. If it does, caching them would save that work.

### Headline numbers and pairs, re-measured

| PR | claim | measured here | holds? |
|---|---|---|---|
| #1519 `border_significant_ring_room` | MFab hat 113.5: md5 identical ON | MFab hat 113.5, main, ON: `ae6efb3b8625` = OFF | **yes** |
| #1523 `speck_prune` | low_poly 10,539 -> 10,325 st, 97 -> 76 trims | low_poly 80 LC, main: 10,539 -> 10,325 st, 98 -> 77 trims | **yes** (the same -21 trims; both arms read one trim higher here) |
| #1528 `outline_inlets_kept` | Ahora's gear re-planned as a fill, 9,229 -> 9,453 st | Ahora 80 LC, #1528 head: 9,208 -> 9,428 st, trims 9 -> 11 | **yes**, at +2 trims |
| #1529 `satin_push_keeps_gaps` | Gaulke's E and S held open | Becker 100 hat, ON: 15,444 -> 15,407 st, trims 18 -> 18, longest Cancel gap 0.84 s (none in `satin rail push`) | sane; the Gaulke claim not re-measured |
| #1530 `curve_chord_mm` 0.4 | rails smoother; the thread barely moves | Becker 100 hat: md5 moves, +8 st, trims same | consistent |
| #1531 `rail_pair_bars` under apex cut | and_pizza's Z bars straight; nothing else moves | and_pizza 80 LC, under apex cut: 2,524 -> 2,485 st, trims 7 -> 7 | counts consistent; not seen by eye |
| #1532 ground ring + bean follows | EST 1895 re-set 2x; +274 st at 92.6 mm | Fremont 100 hat: +185 st, **trims 30 -> 37** (R7) | stitches consistent; trims unpriced |
| #1526 `apex_pro` | the M's V as the pro sews it | Becker 100 hat: 15,444 -> 15,518 st, trims 18 -> 19 | not seen by eye |
| #1522 Flatten shading | GT one gold ring | not re-run (Golden Tee is 7-9 min a run loaded); low_poly ticked: no gap over 1.46 s (R3) | not re-measured |

**Pairs, at the #1526 head with the #1515 flips.** Edge walk and the corner fold are the pair Kent ruled ON this week. No run sewed a needle-down step over 12.1 mm.

| arm | Becker 100 hat | and_pizza 80 LC |
|---|---|---|
| all OFF | `6a1fbe5320fc`, 15,444 st, 18 trims | `6eb54e50c58a`, 2,440 st, 6 trims |
| `apex_pro` | 15,518 st, 19 trims | = OFF (no V in and_pizza) |
| edge walk + corner fold (apex side) | 15,650 st, 17 trims | 2,391 st, **8 trims**, needle-up 40.5 -> 63.2 mm |
| `apex_pro` + edge walk + corner fold | 15,801 st, 17 trims (its own md5; nothing undone, nothing doubled by count) | = edge walk + corner fold |
| `apex_cut` + guard | `6731816c1683`, 15,477 st, 18 trims | not run |
| `apex_pro` + `apex_cut` + guard | **= `apex_pro` alone** (`1e924ddab74b`). `apex_cut` alone moves Becker, but beside `apex_pro` it and the guard add nothing (R2) | not run |

**The pair to watch.** Edge walk + corner fold, ruled ON, add 2 trims and 23 mm of needle-up on and_pizza. That is the opposite of what the walk is for, on a design that is not Becker. Read it beside the art before it lands.

[#1534]: https://github.com/KS-Three/EMB-Bot/pull/1534
