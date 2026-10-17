# `cfg.detail_spokes`: the pro's asterisk on Fremont's star — built OFF (2026-10-15), ON tightened (2026-10-16)

The one fine detail still missing from Kent's Hotel Fremont hat at 80 mm after #976 and
#977: the white star inside the black Wisconsin. Our engine painted it over (stage 3
absorbs it into the black: 0.2 mm² is over the run tier's area floor, but its
2 x max(w, h) loop proxy, 1.3-1.6 mm, is under `RUN_MIN_LOOP_MM` 2.2). The
professional's file (`HOTEL FREMONT HAT.PES`, colour 10 of 11, sewn after the black)
sews ONE white run of 15 points: five spokes from a common centre, each ~1.45 mm, out and
back (two 1.4-1.5 mm stitches per spoke), tips 72° apart, ~2.9 mm across on a 92.6 mm
design whose art star is ~0.9 mm, then a tie. The pro exaggerates the detail about three
times and sews it as spokes, not as a hole and not as an outline. Kent chose "Pro's
asterisk" over a tack dot.

`cfg.detail_spokes` does that: stage 3 reads the enclosed detail's mask for tips
(`detail_spokes.find_tips`), keeps a spoked one as a region of its own while the host
still takes its pixels (solid underneath, as the pro's black is), and stage 7 sews it as
one run of its own thread from the centroid out to each tip and back, after its host, in
the next block of that thread (here the white bean edge cap, so no colour change) else in
a block added after the host's.

**Built OFF in #980 (2026-10-15); ON since 2026-10-16, Kent's call, "ON, tightened":**

- `detail_spokes.MIN_TIPS` 3 → 4. At 3 the corpus had one false positive, a 0.15 mm²
  three-tipped speck of tyre tread on `screenshot_phone_ui_golke`
  (`corpus_screenshot_S8c127526.png`, kept here as the record of why); at 4 it is refused
  and every star and cross still passes.
- The spoke floor scales with the design width: `machine.DETAIL_SPOKE_MIN_MM` 1.45 (the
  pro's spoke) x the artwork's width / `machine.DETAIL_SPOKE_REF_WIDTH_MM` 92.6 (the Hat
  PES it was read from) — 1.45 at 92.6, **1.25 at Kent's 80 mm**. At the fixed 1.45 an
  80 mm Fremont's eastern spoke ended a thread width past the state's edge; scaled, every
  end is inside (table below). Both numbers are the pro's sewn file; the scaling is Kent's
  call. Nothing was sewn: gate-1 candidates.

Thread renders of EMB-Bot's own output (`digitizer_core.stitchviz` through
`tools/fremont_triage`'s panel helpers), not cloth. Every cell below was digitized twice
with the flag set EXPLICITLY (OFF / ON) at the scaled floor, on the ON lane cut from
`main` 6218641e (#980 merged), so the OFF column is today's main with the flag down and the
ON column is what today's default sews.

## Fremont, Hat, the Studio's request (`tools/fremont_triage.run_arm`)

| width | OFF | ON (today's default) | changed shapes | the mark | renders |
|---|---|---|---|---|---|
| **80 mm (Kent's job)** | 14,824 st / 43 tr, 3 colour changes, `75f44f90` | **14,843 / 44**, 3 colour changes, `6e929b96` | 1 (the mark; every OFF shape byte-identical) | `S044d3595`, white #0015, 0.167 mm², 5 spokes of 1.25 mm, block 4 of 4 (the edge cap) | `hat80_wisconsin.png`, `hat80_star.png`, `hat80_full_pair.png` |
| 81 mm | 15,340 / 41, `a69f0719` | 15,359 / 42, `799ba5bc` | 1 | `S044d3595`, 0.172 mm², 5 spokes of 1.27 mm, block 4 of 4 | `hat81_*.png` |
| 92.5 mm (the pro's width) | 18,706 / 54, `12032076` | 18,725 / 55, `24936229` | 1 | `Sb81784b4`, 0.224 mm², 5 spokes of 1.45 mm, block 4 of 4 | `hat92p5_*.png` |

The OFF cells are the bean-holds-on README's ON cells, byte for byte. ON costs 19 stitches
(one 19-point run: 5 spokes x 2 + the centre start, plus the tie-in and tie-off legs, both
laid along a spoke) and one trim (the hop from the cap's end into the mark) at every
width, and no colour change, because the white edge cap already follows the black. The
#980 ON md5s (`8a2d73f3`, `e45e20de`, `37231abc`) were the fixed 1.45 mm floor; these are
the scaled one. (md5s are from Kent's Windows box; CI's Linux reads the same counts under
its own md5s — the goldens' per-fixture platform numerics, pinned per platform in
`test_detail_spokes.py`.)

What the renders show (`*_wisconsin.png`: artwork | OFF | ON over the whole state at
40 px/mm; `*_star.png`: the same at 120 px/mm, tight on the star): OFF, solid black where
the star is; ON, a five-spoke white asterisk centred on the star, over solid black, its
tips at the star's five tip headings.

Where each spoke's END lands against the black state's traced edge (mm inside the host's
artwork polygon), per width, at the scaled floor; the #980 numbers at the fixed 1.45 mm
floor in brackets where they differed:

| width | artwork width | floor | star tip radius | WNW (-163°) | N (-90°) | ENE (-17°) | SE (53°) | SW (128°) |
|---|---|---|---|---|---|---|---|---|
| 80 | 79.9 mm | 1.252 mm | 0.32-0.36 mm | 1.81 | 1.03 | **0.13 inside** (was 0.04 past) | 0.29 (was 0.11) | 1.49 |
| 81 | 80.9 mm | 1.267 mm | 0.32-0.37 mm | 1.84 | 1.04 | **0.14 inside** (was 0.03 past) | 0.29 | 1.51 |
| 92.5 | 92.4 mm | 1.447 mm | 0.37-0.42 mm | 2.10 | 1.19 | 0.16 | 0.33 | 1.72 |

Every end inside at every width now; at Kent's 80 mm the mark is 3.8 x the star's own
radius (the pro's is ~3 x at his width).

## The 17-design lettering corpus (`small_lettering_compare.corpus_designs`)

Every design digitized twice, the flag set explicitly, logos at the Studio's six colours
and their corpus widths. Stitches / trims, stream md5 (`small_lettering_compare.stream_md5`).

| design | OFF | ON (today's default) | changed shapes | the mark |
|---|---|---|---|---|
| becker | 8,758 / 29, `19b38100` | identical | 0 | |
| tires | 2,732 / 8, `6a6ada47` | identical | 0 | |
| enthusiast | 2,414 / 8, `9944fec7` | identical | 0 | |
| fremont (92.5 mm patch) | 20,863 / 48, `528e12a9` | 20,882 / 49, `44382087` | 1 | `Sb81784b4` white #0015, 5 spokes, 0.224 mm², block 4 of 4 (the edge cap) |
| bridge | 18,923 / 99, `197a3287` | identical | 0 | |
| golden_tee | 8,412 / 45, `9208ffe4` | identical | 0 | |
| gaulke | 4,893 / 23, `9f1a2036` | identical | 0 | |
| drone | 19,281 / 130, `a709b157` | identical | 0 | |
| screenshot | 8,505 / 62, `ae664b23` | **identical** (was 8,520 / 63 at `MIN_TIPS` 3) | 0 | |
| fremont_hat81 | 15,340 / 41, `a69f0719` | 15,359 / 42, `799ba5bc` | 1 | `S044d3595` white, 5 spokes, 0.172 mm², block 4 of 4 |
| fremont_hat925 | 18,706 / 54, `12032076` | 18,725 / 55, `24936229` | 1 | `Sb81784b4` white, 5 spokes, 0.224 mm², block 4 of 4 |
| sp_synthetic_2.5 | 318 / 1, `42401291` | identical | 0 | |
| sp_synthetic_3 | 378 / 2, `88822294` | identical | 0 | |
| sp_synthetic_4 | 547 / 4, `290e5ab0` | identical | 0 | |
| sp_fremont_tagline_2.5 | 590 / 5, `c57e1189` | identical | 0 | |
| sp_fremont_tagline_3 | 719 / 5, `df03b9cc` | identical | 0 | |
| sp_fremont_tagline_4 | 985 / 10, `35ff0da6` | identical | 0 | |

Three cells move — the three Fremont ones, each by exactly one new shape (the star's
mark) with every other shape's run byte-identical. **Fourteen designs are byte-identical
ON**, including `screenshot`, whose three-tipped tyre-tread speck `MIN_TIPS` 4 now refuses
(`corpus_screenshot_S8c127526.png` is what it sewed at 3), the whole small-print set and
every design with no enclosed detail of another colour under the loop floor. The three
flat goldens (`logo_alpha`, `logo_whitebg`, `ribbon_curve`) are md5-pinned both ways in
`test_detail_spokes.py` and do not move.
