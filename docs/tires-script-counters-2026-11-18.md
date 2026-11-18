# Tires "ires": e crossing, counters, e/s step, stroke ends (2026-11-18)

**Not a flip candidate as built (mode `true`):** it opens the e and s counters (sewn 19.3 / 33.2 -> 25.9 / 41.2 mm2 against the art's 28.7 / 43.3) but preflight uncovered patches on Tires go 12 -> 220. It is the pull-comp constant, so cloth decides (ROADMAP gate 1). Mode `"counter"` keeps most of the gain with patches 12 -> 17.

Prime grader scorecard faults on `L_tires_hat_3d` (114.3 x 42.3 mm, hat_front). Reproduced with
`tools.pro_pair.digitize('testdata/logo_script_tires.png', 114.3, 'hat_front')`; plan read from
`plan.iter_runs()`, polygon from `result.regions`. Art: committed `testdata/logo_script_tires.png`
only (no professional's file used here).

| spot (mm) | fault | verdict |
|---|---|---|
| (72.5, 31) e/r crossing | lump, square notch | **Limit of the art**, already written up in `docs/tires-join-2026-11-17.md`. Not re-opened. |
| (76.5, 28.5) e counter, (102, 28) s counter | pinched / narrower | **Real in the stitches; cause is the fixed 0.4 mm pull comp = ROADMAP gate 1.** Built OFF (below). |
| (93.5, 35.5) e/s step, s lower left | blocky step | **Real, column end face; not fixed.** See below. |
| (21.5, 37) i entry end, (110, 31) s exit end | flat slanted cut | **Real, same end-face family as the i; not fixed.** |
| (80.5, 34) e upper exit edge | straight run, corner | Polygon edge; `curve_chord_stage4` does not move it (see its README). Not fixed. |

## Counters: the pull, not the trace

Hole areas, mm2 (30 px/mm masks, art ink registered by silhouette fit):

| counter | art ink | traced polygon | sewn thread | sewn, flag ON |
|---|---|---|---|---|
| e | 28.7 | 29.3 | 19.3 | 25.9 |
| s | 43.3 | 44.6 | 33.2 | 41.2 |

The polygon is right (within 1.3 mm2); 10-11 mm2 is lost between polygon and thread. Hole perimeters are
about 22 and 24 mm, so that is about 0.4 mm a side: the fabric's fixed pull (`fabrics.pull_comp_mm`, 0.4 on
`structured_cap`) pushes every script rail 0.4 mm into the counter. `script_strokes_shape` passes the
preset's pull to `column_runs`; the per-stroke fit `pull_comp_by_stroke` (`columns.pull_for_width`: +0.58 on
0.85 mm, +0.42 on 2.6, nothing at 4, read off the pro's hat files) is only read by the Column lane's
letters. Tires' pen is 4.7 mm. The s's right wall: crosses start 0.6 mm inside the art's counter edge.

## What was built: `script_strokes_pull_by_stroke` (OFF)

`PipelineConfig.script_strokes_pull_by_stroke`, default False, OFF byte-identical (sweep below, and
`tests/test_script_strokes_pull_by_stroke.py`). ON, each script stroke's rails get
`min(preset pull, pull_for_width(its width, preset pull))`, on hat / LC / beanie presets only. It is the
existing fit applied to the lane it skipped: no new constant. Flipping it is still a physical-constant
call (gate 1): Kent after a sew-out.

**Sweep, 18 tripwire jobs + 26 `corpus_scorecard.FIXTURES` (md5 of `design["stitches"]`): 6 of 44 move.**

| run | stitches | trims | jumps | needle-up mm |
|---|---|---|---|---|
| tires_hat_3d | 4644 -> 4536 | 7 -> 8 | 8 -> 9 | 71.3 -> 75.6 |
| toat_machine_hat | 17100 -> 17097 | 19 -> 19 | 32 -> 32 | 267.9 -> 268.0 |
| toat_machine_beanie | 16862 -> 16860 | 18 -> 18 | 31 -> 31 | 323.6 -> 323.6 |
| toat_beanie | 17193 -> 17176 | 27 -> 28 | 35 -> 37 | 233.6 -> 245.2 |
| fx logo_script_tires 80 mm LC | 2512 -> 2243 | 3 -> 3 | 4 -> 4 | 65.4 -> 65.5 |
| fx logo_bridge_bar 80 mm LC | 10830 -> 10801 | 17 -> 15 | 26 -> 23 | 224.9 -> 219.2 |

The other 38 runs are byte-identical.

**WRONG WAY: preflight `uncovered_patches` on Tires 12 -> 220 (worst 0.2 -> 0.6 mm2); 80 mm fixture 9 -> 21.**
The thread no longer reaches the art's edge in small slivers: the pull is what covers it. `coverage_p95`,
`subject_edge_recall` (0.9997 -> 1.0) and the rest do not worsen; `edge_wobble_satin_p95` improves 0.28 ->
0.18 mm. The other four movers' patches are unchanged. Whether 0.6 mm2 slivers show on cloth is the sew-out's
question, which is why the flag stays OFF. Related files with the flag forced ON: 304 pass; the 2 that fail
are the test that asserts the default is OFF and the one that compares ON against the default.

**By eye (`docs/renders/script-pull-by-stroke-2026-11-18/`): at print size the whole word is not clearly
better.** The e and s counters open visibly in the close-up; the word reads the same.

## Mode `"counter"` (second OFF mode of the same flag; the director's option C)

Rails facing a counter take the word's by-width pull (`stage6_satin.COUNTER_PULL`, read in `_push_rails`'
counter probe); every other rail keeps the full 0.4 mm. `True` is the all-rails mode above. A gap under about
1.5 mm (the director's second condition) is NOT handled: only polygon holes.

| Tires, 114.3 mm hat | OFF | `true` | `"counter"` | art |
|---|---|---|---|---|
| e counter mm2 | 19.3 | 25.9 | 26.8 | 28.7 |
| s counter mm2 | 33.2 | 41.2 | 41.1 | 43.3 |
| uncovered patches (preflight) | 12 | 220 | **17** | |
| stitches | 4644 | 4536 | 4644 | |
| trims / jumps | 7 / 8 | 8 / 9 | 6 / 7 | |
| needle-up mm | 71.3 | 75.6 | 69.0 | |

Same sweep (44 runs): 6 move, the same six. Under `"counter"` toat_machine_hat, toat_machine_beanie,
toat_beanie and fx logo_bridge_bar keep their stitches, trims, jumps and needle-up exactly and every
preflight figure above (their md5 still differs: rail positions at small bays moved, size not measured); fx
logo_script_tires 80 mm LC +33 stitches (2512 -> 2545), trims/jumps and patches unchanged,
`coverage_p95` 2.62 -> 2.60. `edge_wobble_satin_p95` on Tires improves 0.28 -> 0.24 mm. Related
files with the default forced to `"counter"`: 306 pass; the one that fails asserts the default is OFF.

**By eye (`docs/renders/script-pull-by-stroke-2026-11-18/counter-mode/`): at print size the whole word is
not clearly better than OFF**; the counters open a little (s right wall stays straight and notched; that
wall is the polygon's straight run, not the pull). `"counter"` costs nothing in cover and is the one worth a
sew-out arm; it is not a flip on pictures alone.

## Not fixed: stroke ends and the e/s step

The i's entry end (21.5, 37) has crosses square to the pen path and a polygon end within 0.25 mm of a circle
(`.claude/memory/round-dot-ring-2026-11-18.md`); a satin end of parallel square crosses is a flat slanted
face by construction, while the art's end is a round cap. A cure is a fanned cap in `columns.py`'s terminal
faces, which three attempts did not find; I did not try a fourth. The s lower left (94-96, 35-38) is column 8
starting with a flat end face across the word's long column (12, 650 points); art is one smooth arc.
Both are small (the reader's own grade: nitpick/noticeable) and need that end-face work, not a flag here.
