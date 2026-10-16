# `cfg.detail_spokes`: the pro's asterisk on Fremont's star, built OFF (2026-10-15)

The one fine detail still missing from Kent's Hotel Fremont hat at 80 mm after #976 and
#977: the white star inside the black Wisconsin. Our engine paints it over (stage 3
absorbs it into the black: 0.2 mm² is over the run tier's area floor, but its
2 x max(w, h) loop proxy, 1.3-1.6 mm, is under `RUN_MIN_LOOP_MM` 2.2). The
professional's file (`HOTEL FREMONT HAT.PES`, colour 10 of 11, sewn after the black)
sews ONE white run of 15 points: five spokes from a common centre, each ~1.45 mm, out and
back (two 1.4-1.5 mm stitches per spoke), tips 72° apart, ~2.9 mm across on a 92.6 mm
design whose art star is ~0.9 mm, then a tie. The pro exaggerates the detail about three
times and sews it as spokes, not as a hole and not as an outline. Kent chose "Pro's
asterisk" over a tack dot.

`cfg.detail_spokes` (default OFF; this is Kent's flip) does that: stage 3 reads the
enclosed detail's mask for tips (`detail_spokes.find_tips`), keeps a spoked one as a
region of its own while the host still takes its pixels (solid underneath, as the pro's
black is), and stage 7 sews it as one run of its own thread from the centroid out to each
tip, extended to `machine.DETAIL_SPOKE_MIN_MM` (1.45, the pro's spoke, a gate-1
candidate) and back, after its host, in the next block of that thread (here the white
bean edge cap, so no colour change) else in a block added after the host's.

Thread renders of EMB-Bot's own output (`digitizer_core.stitchviz` through
`tools/fremont_triage`'s panel helpers), not cloth. Nothing was sewn. Every cell was
digitized twice with the flag set EXPLICITLY (OFF / ON), on this lane cut from `main`
1f276cd8 (#978), so the OFF column is today's main.

## Fremont, Hat, the Studio's request (`tools/fremont_triage.run_arm`)

| width | OFF | ON | changed shapes | the mark | renders |
|---|---|---|---|---|---|
| **80 mm (Kent's job)** | 14,824 st / 43 tr, 3 colour changes, `75f44f90` | **14,843 / 44**, 3 colour changes, `8a2d73f3` | 1 (the mark; every OFF shape byte-identical) | `S044d3595`, white #0015, 0.167 mm², 5 spokes, block 4 of 4 (the edge cap) | `hat80_wisconsin.png`, `hat80_star.png`, `hat80_full_pair.png` |
| 81 mm | 15,340 / 41, `a69f0719` | 15,359 / 42, `e45e20de` | 1 | `S044d3595`, 0.172 mm², 5 spokes, block 4 of 4 | `hat81_*.png` |
| 92.5 mm (the pro's width) | 18,706 / 54, `12032076` | 18,725 / 55, `37231abc` | 1 | `Sb81784b4`, 0.224 mm², 5 spokes, block 4 of 4 | `hat92p5_*.png` |

The OFF cells are the bean-holds-on README's ON cells, byte for byte: this lane changes
nothing with the flag down. (Every md5 here is from Kent's Windows box; CI's Linux reads
the same 14,824 / 43 at 80 mm OFF with its own md5, `027d14e6` — the goldens' per-fixture
platform numerics, pinned per platform in `test_detail_spokes.py`.) ON costs 19 stitches (one 19-point run: 5 spokes x 2 + the
centre start, plus the tie-in and tie-off legs, both laid along a spoke) and one trim
(the hop from the cap's end into the mark) at every width, and no colour change, because
the white edge cap already follows the black.

What the renders show (`*_wisconsin.png`: artwork | OFF | ON over the whole state at
40 px/mm; `*_star.png`: the same at 120 px/mm, tight on the star): OFF, solid black where
the star is; ON, a five-spoke white asterisk centred on the star, over solid black, its
tips at the star's five tip headings. **At 92.5 mm (the pro's width) the mark sits inside
the state as the pro's does. At 80 and 81 mm the fixed 1.45 mm spoke is the same length
on a state 15% smaller, so the two eastern spokes reach the state's edge** (measured
below). The floor is the pro's number at the pro's size; whether it should scale with the
design (1.45 x width / 92.6) is a call for Kent, not built here.

Where each spoke's END lands against the black state's traced edge (positive: inside, mm
to the edge; negative: past it), per width, from the host's artwork polygon:

| width | star tip radius (mm) | spoke to WNW (-163°) | N (-90°) | ENE (-17°) | SE (53°) | SW (128°) |
|---|---|---|---|---|---|---|
| 80 | 0.32-0.36 | 1.69 inside | 0.99 | **0.04 past the edge** | 0.11 | 1.33 |
| 81 | 0.32-0.37 | 1.72 | 1.00 | **0.03 past the edge** | 0.13 | 1.36 |
| 92.5 | 0.37-0.42 | 2.10 | 1.19 | 0.15 inside | 0.33 | 1.72 |

So at Kent's 80 mm the mark is 4 x the star's own radius (0.33 mm) and one spoke end
sits a thread width (0.04 mm) outside the state, on the cap's white; at the pro's 92.5 mm
every end is inside.

## The 17-design lettering corpus (`small_lettering_compare.corpus_designs`)

Every design digitized twice, the flag set explicitly, logos at the Studio's six colours
and their corpus widths. Stitches / trims, stream md5 (`small_lettering_compare.stream_md5`).

| design | OFF | ON | changed shapes | the mark |
|---|---|---|---|---|
| becker | 8,758 / 29, `19b38100` | identical | 0 | |
| tires | 2,732 / 8, `6a6ada47` | identical | 0 | |
| enthusiast | 2,414 / 8, `9944fec7` | identical | 0 | |
| fremont (92.5 mm patch) | 20,863 / 48, `528e12a9` | 20,882 / 49, `111715f8` | 1 | `Sb81784b4` white #0015, 5 spokes, 0.224 mm², block 4 of 4 (the edge cap) |
| bridge | 18,923 / 99, `197a3287` | identical | 0 | |
| golden_tee | 8,412 / 45, `9208ffe4` | identical | 0 | |
| gaulke | 4,893 / 23, `9f1a2036` | identical | 0 | |
| drone | 19,281 / 130, `a709b157` | identical | 0 | |
| screenshot | 8,505 / 62, `ae664b23` | 8,520 / 63, `459546c4` | 1 | `S8c127526` #0108, 3 spokes, 0.154 mm², block 6 of 10, no colour change added |
| fremont_hat81 | 15,340 / 41, `a69f0719` | 15,359 / 42, `e45e20de` | 1 | `S044d3595` white, 5 spokes, 0.172 mm², block 4 of 4 (the edge cap) |
| fremont_hat925 | 18,706 / 54, `12032076` | 18,725 / 55, `37231abc` | 1 | `Sb81784b4` white, 5 spokes, 0.224 mm², block 4 of 4 (the edge cap) |
| sp_synthetic_2.5 | 318 / 1, `42401291` | identical | 0 | |
| sp_synthetic_3 | 378 / 2, `88822294` | identical | 0 | |
| sp_synthetic_4 | 547 / 4, `290e5ab0` | identical | 0 | |
| sp_fremont_tagline_2.5 | 590 / 5, `c57e1189` | identical | 0 | |
| sp_fremont_tagline_3 | 719 / 5, `df03b9cc` | identical | 0 | |
| sp_fremont_tagline_4 | 985 / 10, `35ff0da6` | identical | 0 | |

Four cells move, every one by exactly one new shape (the mark) with every other shape's
run byte-identical: the three Fremont cells (the star, 5 spokes, in the white edge cap's
block) and **screenshot** (`photo/screenshot_phone_ui_golke.jpg` at 80 mm), where a
0.154 mm² detail of thread #0108 inside another shape read 3 tips and sewed as a
three-spoke mark in a later block of its own thread (no colour change added).
**That one is a false positive**, and it is reported as one: `corpus_screenshot_S8c127526.png`
(artwork | OFF | ON, an 8 mm box at 40 px/mm) shows a light speck of the tractor's tyre
tread, inside the dark tread shape, read as three tips and sewn as a 1.45 mm three-spoke
Y over the tread. The detector's floor is `detail_spokes.MIN_TIPS` = 3 (the build spec's
"a star, a cross or an asterisk", a triangle being the smallest); at 4 the speck is
refused (it reads exactly 3) and every star and cross still passes (pinned in
`test_detail_spokes.py`), so with the flag ON at 4 the corpus would move on the three
Fremont cells only. Which floor is Kent's call; 3 is built. Thirteen designs are
byte-identical ON, including the whole small-print set and every design with no enclosed
detail of another colour under the loop floor.
