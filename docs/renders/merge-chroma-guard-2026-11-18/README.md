# merge_chroma_guard: the full sweep, and a bounded version (2026-11-18)

Default stays OFF. Nothing here is a flip. Every figure below is flag OFF
-> flag ON on the same tree; ORIGINAL | BEFORE | AFTER pictures sit beside
this file (whole design and close-ups, same frame).

## 1. Who moves (76 runs, OFF vs ON, md5 of the written DST)

Swept: the 18 tripwire placements (`tripwire.committed_jobs()`, each at its
own size and garment), the 26 `corpus_scorecard.FIXTURES` at the Studio
request (80 mm left_chest) AND at the bare `PipelineConfig(80, left_chest)`
the tests use, plus the exact configs of the failing tests.

| run | moves? |
|---|---|
| 17 of 18 placements, 24 of 26 fixtures at both configs | identical |
| `precision_drone` (pro hat, 62.6 mm) | yes |
| `drone_render` (Studio, bare, thread-match test, forbid-gap test) | yes, all four |
| `logo_golden_tee` | only at the thread-match test config (`stage0_scale_relative_grad=False`), not at any shipped config |
| `logo_bridge_bar` | only at the PRE_FLIP config of `test_thread_match_better_spool` |

The 11-17 "2 of 35" was true for its one config; it missed that the bare
config the tests use moves the Drone differently (colours 16 -> 14) and that
two old configs move two more designs.

## 2. What it costs (unbounded guard)

| run | stitches | trims | hops | needle-up mm | colours | stacked-thread area |
|---|---|---|---|---|---|---|
| precision_drone, pro hat | 13,966 -> 15,057 | 93 -> 94 | 134 -> 147 | 1,557 -> 1,576 | 9 -> 9 | 74 -> 161 mm2 (peak 10.2 -> 11.2) |
| drone_render, Studio 80 mm | 18,123 -> 20,270 | 102 -> 131 | 147 -> 186 | 2,094 -> 2,283 | 10 -> 8 | 107 -> 203 mm2 (peak 11.6 -> 12.2) |
| drone_render, bare 80 mm | 18,431 -> 20,367 | 109 -> 119 | 155 -> 171 | 2,540 -> 2,666 | 16 -> 14 | 74 -> 180 mm2; score 40 -> 28, D -> F; new ARTWORK_ELEMENT_DROPPED (2 elements, 14 mm2) |
| golden_tee, old config | 10,404 -> 10,116 | 31 -> 23 | 47 -> 40 | 787 -> 591 | 14 -> 14 | n/a |
| bridge_bar, PRE_FLIP | 15,571 -> 15,695 | 88 -> 93 | 137 -> 139 | 1,685 -> 1,592 | 17 -> 16 | n/a |

Bare-artwork, cover and coverage figures were not asked for separately; the
preflight findings above are what moved. No placement outside the Drone
changed a figure.

## 3. Golden Tee: each new blocking finding

Config of `test_thread_match_area_in_message` (gradient-lane plan).
Regions that do not match 1:1 (IoU < 0.85) between the arms: a 26.4 mm2
teal region and a 10.1 mm2 teal piece become one 37.4 mm2 teal region plus a
new 28.9 mm2 grey region (art 178,178,178); the orange 0232 pieces (17.2 +
6.7) become one 24.0 mm2 piece. So the guard kept a neutral grey apart from
its coloured neighbours in the "GOLF" shadow.

| new block | what it is |
|---|---|
| Silver 3971, 4 of 5 shapes, worst S1fba0aac 28.87 mm2 | the new grey region, art (178,178,178), thread Silver, 10.7 dE. Before, Silver was a warn (3 of 4 shapes, worst 96.8 mm2). The grey existed in both arms; it is now a separate shape. |
| Candlelight 0811, worst 39.4 mm2 | the orange shape that OFF sews in Sunset 1120 (12.1 dE) is now handed Candlelight at 11.1 dE; same art (250,181,28). The cap picked a different spool for the same colour. |
| Sunset 1120, 1 shape 65.3 mm2 | the same shape and the same 10.5 dE as OFF's; its count of shapes fell, its severity did not. |

Every number sits at 10.5 to 12.1 dE in both arms; nothing is worse in
colour, three findings are re-labelled. The whole-design pictures (`golden_tee_80mm_oldconfig_whole.png`)
read the same by eye. Not a shipped config.

Drone's 3 -> 4: the 1,475 mm2 navy-ground block (Darkest Blue 3574) is
gone (the sky is blue now); four small ones (Whale 8.7 mm2, Pumpkin 199 mm2
as before, Blackberry 7.7, Cherry 19.5) appear. Largest blocked area falls
1,475 -> 199 mm2.

## 4. The dark bar on the C

With the shipped `keyline_fragment_drop` ON there is **no bar on the C** in
any render (`*_closeup_PRECISION.png`). Turn `keyline_fragment_drop` OFF and
the guard ON and it appears: a 0.29 mm2 region (3.3 x 1.3 mm, thread 2564
Titanium 90,94,97) split off the silver C (3971, 204,204,204). In the stage-2
merge the C's dark bluish hairline edge is a colour (chroma >= 30) against a
neutral silver and is no longer allowed to join it. The narrowed keyline rule
already drops it, so this is spared today.

A pixel bound does NOT remove the fragment: with `keyline_fragment_drop`
OFF it still appears at every bound tried (0, 300, 1000, 2500 px: 0.25-0.29
mm2). Its cause is not a guard firing on the tiny piece; I did not trace it
further.

## 5. A bounded version

`CHROMA_GUARD_MIN_PX` (built, 1000, same style as `AREA_RATIO_MIN_SMALL_PX`):
the guard needs both sides at least that many foreground pixels. Found while
tracing: background node 0 carries a count of 0, and the unbounded guard was
firing on its edges (most of the small-side firings); the bound
removes those and every fragment under 1000 px.

| run | OFF | unbounded | bound 1000 |
|---|---|---|---|
| Studio drone: stitches / trims | 18,123 / 112 | 20,270 / 139 | 20,199 / 124 |
| Studio drone: blue sewn (mm2) | 0 | 388.7 | 386.0 |
| pro hat drone: stitches / blue | 13,966 / 33.7 | 15,057 / 238.0 | 15,025 / 240.0 |
| bridge_bar PRE_FLIP | 15,571 | 15,695 | 15,571 (identical to OFF) |
| golden_tee old config | 10,404 | 10,116 | 10,174 (still moves) |

Related tests forced ON with the bound (default flipped in the working tree
only, then reverted): 8 failures remain: the two enthusiast goldens (red
with the flag OFF too), the Drone's own pins (`test_forbid_gap`,
`test_duplicate_cone_layers`, `test_no_severity_moved[drone]`, the shard
test), and `test_no_severity_moved[golden_tee]`. `test_thread_match_better_spool`
(Bridge Bar) now passes; `test_off_is_the_weight_it_always_was` fails only
because the default was forced ON.

## 6. Verdict

**Not a flip candidate yet.** The bounded guard keeps the Drone's gain
(the blue sky and water read right, same as 11-17) and cuts the extra trims
from +24% to +11% (plan stats, 112 base: 139 -> 124) and removes Bridge Bar, but at the shipped Studio request
the Drone is the only design it moves: one design is not evidence for a
default for every photo-style design. The Drone still sews 12% more stitches
and doubles the stacked-thread area (107 -> 203 mm2; stacking is a fabric
question, which needs a sew-out), and Golden Tee and three Drone pins still
need re-pinning. If Kent wants the Drone fixed without a default flip, a
per-design route is the cheaper path.
