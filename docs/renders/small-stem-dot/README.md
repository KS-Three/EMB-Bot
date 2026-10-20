# The i/j dot and the small stem, OFF beside ON at 50 and 80 mm (MASTER_SCOPE item 52)

Renders for Kent's two flip calls, nothing decided here. Both flags are built OFF and stay
OFF on this branch; no engine line and no constant moved (ROADMAP gate 1 holds:
`machine.RUN_MIN_LOOP_MM` 2.2 and the three `DOT_RUNG_*` candidates are as #939 left them).

- **`cfg.lettering_columns_small_stem`** (PR #896, 2026-10-13, OFF): a lettering shape under
  stage 7's 2.25 mm² small-shape floor that `columns.is_thin_stem` calls a stem (long side
  ≥ 1.5 mm, short side ≥ 0.5 mm, aspect ≥ 6) goes to the Column lane instead of the run
  tier. Measured there on the synthetic Aileron i at 80 mm only.
- **`cfg.small_dot_rung`** (PR #939, 2026-10-14, OFF): a part whose ring is between 1.35 and
  2.2 mm is admitted at stage 3 and 4 and, at stage 7, an outer ring under 2.2 mm sews as a
  0.45 mm × 3-pass tack ring instead of being dropped. Its catch: it admits photo specks too.
- **`cfg.small_dot_rung_lettering`** (PR #975, 2026-10-15, OFF; read only when the rung is
  ON): the rung admits a part only over a same-colour stem. Byte-identical to OFF on every
  photo and logo #975 measured, and keeps every synthetic dot the rung keeps.

Every cell below was digitized by `digitizer/tools/small_stem_dot_renders.py` on this branch
(`main` at 7220f3e, #987 merged), the flags set EXPLICITLY per arm, one cell per process, on
a Linux cloud container. Thread renders of EMB-Bot's own output (`digitizer_core.stitchviz`
through `tools/fremont_triage`'s panel helpers), thread at its laid width, a picture of the
file, not of cloth. md5 is the stitch stream (`tools/small_dot_rung.plan_md5`, the recipe
`test_small_glyph_keep.py` pins); "changed vs OFF" compares shapes by GEOMETRY (bounds and
area), not by id, because an admitted part renumbers the shapes after it (#975).

## The five arms

| arm | overrides |
|---|---|
| OFF (shipped) | none |
| small_stem ON | `lettering_columns_small_stem=True` |
| small_dot_rung ON | `small_dot_rung=True` |
| both ON | both |
| both ON + lettering scope | both + `small_dot_rung_lettering=True` |

## The cases, and which has what

The item names the synthetic Aileron i (#896's stem, #939's dot) and the word "hijlij"
(#939's four dots). The brief also named Fremont's tagline, the `sp_fremont_tagline`
small-print cells of the 17-design corpus and Becker. Read against the artwork:

| case | i or j dot | stem under the floor | why it is here |
|---|---|---|---|
| `lowercase_aileron.png` at 50 and 80 mm, `forced_class="flat"` as #896 and #939 ran it | the i on the lowercase line | the i stem (3.73 × 0.57 mm at 80) | both flags' home fixture |
| "hijlij" drawn at runtime in the same CC0 face, at the 50 and 80 mm scale (7.9 and 12.7 mm wide, forced flat) | two i, two j | none at 80 (the i stem clears the floor at 2.50 mm²) | #939's word |
| Fremont, Hat, the Studio's request at 50 and 80 mm (`fremont_triage.run_arm`), read over EAT \| STAY \| PLAY | none in the art | the two "\|" bars are the only thin stems | Kent's job; the brief's "tagline" |
| `sp_fremont_tagline` at 2.5, 3 and 4 mm caps (the corpus cells; the width follows the cap) | none | the two "\|" bars | the brief's synthetics |
| Becker, left chest, six colours, 50 and 80 mm | none (MARINE's I is a capital, 3 mm wide at 80) | none | the brief's "if it has them": a control |

## What the pictures show

**The synthetic i at 80 mm (`aileron_80_siv.png` at 40 px/mm, `aileron_80_i.png` at
120 px/mm).** OFF, the i's stem is a hollow box: a bean run round a 0.57 mm column, bare
fabric between its two passes, beside neighbours sewn as solid satin; its dot is not sewn at
all. `small_stem` ON turns the stem into a satin column like the I and l beside it (run 37 pts
to satin 22, 2,747 to 2,734 stitches). `small_dot_rung` ON sews the dot as a 14-point run that
the 0.4 mm thread fills to a solid 0.75 mm blob (+27 stitches, +3 trims). Both ON is the whole
letter. Each flag also moves a few crosses on other letters (5 with the rung, 15 with both:
±2 to 4 satin points each, the same ink, because the lane's walk starts where the previous
shape ended), which is why "both" is not the byte-sum of the two.

**"hijlij" (`hijlij_80_*.png`, `hijlij_50_*.png`).** OFF has no dots at either scale. The rung
sews all four. At the 80 mm scale each 0.81 mm dot is an outline run (13 to 17 points, a ring
the thread almost closes: a pinhole shows at 120 px/mm) reached with a trim (trims 1 to 4). At
the 50 mm scale each 0.51 mm dot is under the 2.2 mm loop floor and sews as the tack ring,
8 rings over 4 dots, and the rung reaches two of the four by a needle-down leg from the top of
the stem (trims 1 to 2): that leg shows as a thread bridge between stem and dot in the ON
panels, which the artwork does not have. `small_stem` is inert on the word: at 80 mm the i stem
clears the floor (2.50 mm²), at 50 mm it is 0.39 mm wide, under the 0.5 mm cross floor.

**The synthetic fixture at 50 mm is not a test of either flag (`aileron_50_i.png`).** All five
arms are byte-identical, and the i has no dot and a tapered sliver for a stem in every one,
OFF included. That is not the loop floor and not the area floor: the shipped two-tone snap
(`cfg.two_tone_snap`, ON, defect 58's fix) folds the dot and most of the stem into the
fringe before stage 2, so no region ever exists for a flag to act on. Measured by turning the
snap off: the i's ink in the prep raster goes from 945 dark pixels to the source's 2,417
(`two_tone.apply`, stage 1.3). At 80 mm the same raster keeps the dot (384 px, 0.78 mm). The
whole lowercase line at 50 mm is 2.3 mm tall and every letter of it is under the 2.25 mm²
floor, sewn as run outlines; the `siv` panel shows that. Whether the snap should fold a 0.47 mm
dot is its own question, not either flag's.

**Fremont, Hat, 80 mm, Kent's job (`fremont_hat_80_tagline.png` at 40 px/mm).**
`small_stem` is byte-identical to OFF. The two "|" bars are 3.58 × 0.29 and 0.26 mm, not
tagged lettering and under the 0.5 mm cross floor, so `is_thin_stem` never sees them; they sew
as 42- and 39-point runs OFF and ON alike. 77 other shapes under the floor carry the lettering
tag, most of them the rope's twist segments at 1.95 × 0.55 mm, aspect 3.5: it is #896's
`STEM_MIN_ASPECT` 6 that keeps the lane off the rope (the first cut's aspect 3 would have taken
all of them). `small_dot_rung` ON costs +33 stitches, no trim, and buries the Wisconsin star:
OFF sews the `detail_spokes` asterisk (Kent's call, 2026-10-16) as a 19-point white run in the
LAST block, over the black state, and ON sews an 18-point white run for the same shape in the
FIRST white block, before the black, so the black fill covers it. `fremont_hat_80_changed_1.png`
shows the state with and without the asterisk; `fremont_hat_80_S044d3595_bisect.png` cuts each
arm's stream at every colour change and shows where the mark is laid. The rung admits the star
at stage 3 as an ordinary small white part before `detail_spokes` can claim it: in
`resolve_small_regions` `clears = floors or by_rung`, the contrast rescue keeps a cleared part of
another colour as a run-tier shape of its own, and the spokes branch is asked only when `not
clears`; an ordinary part sews with its own thread's block. The same arm adds two 1.1 × 0.56 mm tan slivers at the rope's
ends (17-point runs, `fremont_hat_80_changed_2.png`) and re-walks EST, THE and the state fill by a
few points. **Scoped (`small_dot_rung_lettering`), it is byte-identical to OFF: the star stays.**

**Fremont, Hat, 50 mm (`fremont_hat_50_tagline.png`, `fremont_hat_50_changed_*.png`).**
`small_stem` identical again (the bars are 2.24 × 0.18 mm). OFF drops the whole EST 1895 line at
this width (its glyphs are 1 mm tall); the rung brings every glyph back as a tack-ring blob, one
per letter and digit (+170 stitches, +1 trim, 13 new shapes), plus rope-twist slivers top and
bottom, and cuts 0.6 mm² out of the white patch for one of them. Scoped, byte-identical to OFF:
EST 1895 stays dropped.

**`sp_fremont_tagline` at 2.5, 3 and 4 mm caps (`sp_fremont_tagline_*_design.png`).** Every arm
byte-identical to OFF at every cap (the corpus's own md5s, `c57e1189` / `df03b9cc` / `35ff0da6`,
reproduced). The bars sew as runs that the thread fills to black columns; nothing under the floor
is a thin stem and nothing sits in the rung's band.

**Becker at 50 and 80 mm.** Byte-identical in every arm (`63d6ca06`, `76620f8c`): no lettering
shape under the floor, no ring in the band, nothing for either flag. No render, since there is
nothing to see.

## Tables

md5 is the stitch stream's; "changed vs OFF" counts shapes by geometry: new (admitted),
gone, re-sewn (needle-down runs moved), and re-walked only (travel or underlay moved, the ink
the same). The bullet under a table lists the new and re-sewn shapes of the arm that first
produced them (the ON arms that share an md5 share the list).

### synthetic Aileron fixture, 50 mm (forced flat)

| arm | stitches | trims | md5 | shapes | tack rings | changed vs OFF |
|---|---|---|---|---|---|---|
| OFF (shipped) | 1,841 | 10 | `772c996b` | 49 | 0 | - |
| small_stem ON | 1,841 | 10 | `772c996b` (= OFF) | 49 | 0 | **identical** |
| small_dot_rung ON | 1,841 | 10 | `772c996b` (= OFF) | 49 | 0 | **identical** |
| both ON | 1,841 | 10 | `772c996b` (= OFF) | 49 | 0 | **identical** |
| both ON + lettering scope | 1,841 | 10 | `772c996b` (= OFF) | 49 | 0 | **identical** |

What the flags see OFF: 16 lettering shape(s) under the 2.25 mm2 floor, of which 0 pass `is_thin_stem` (none); 0 ring(s) in the rung's 1.35 to 2.2 mm band.

### "hijlij" at the 50 mm scale (7.911 mm wide, forced flat)

| arm | stitches | trims | md5 | shapes | tack rings | changed vs OFF |
|---|---|---|---|---|---|---|
| OFF (shipped) | 155 | 1 | `8afdcbd2` | 6 | 0 | - |
| small_stem ON | 155 | 1 | `8afdcbd2` (= OFF) | 6 | 0 | **identical** |
| small_dot_rung ON | 215 | 2 | `03ef446c` | 10 | 8 | 4 new ('i' ring in the rung's band, 'j' ring in the rung's band, 'i' ring in the rung's band, 'j' ring in the rung's band); 1 re-sewn ('j' lettering, under floor) |
| both ON | 215 | 2 | `03ef446c` | 10 | 8 | 4 new ('i' ring in the rung's band, 'j' ring in the rung's band, 'i' ring in the rung's band, 'j' ring in the rung's band); 1 re-sewn ('j' lettering, under floor) |
| both ON + lettering scope | 215 | 2 | `03ef446c` | 10 | 8 | 4 new ('i' ring in the rung's band rung-admitted, 'j' ring in the rung's band rung-admitted, 'i' ring in the rung's band rung-admitted, 'j' ring in the rung's band rung-admitted); 1 re-sewn ('j' lettering, under floor) |

What the flags see OFF: 5 lettering shape(s) under the 2.25 mm2 floor, of which 0 pass `is_thin_stem` (none); 0 ring(s) in the rung's 1.35 to 2.2 mm band.

- **small_dot_rung ON**: +S9204c6ff ('i' ring in the rung's band; 0.219 mm2, 0.51 x 0.51 mm): new, sews run 13; +S0c90443f ('j' ring in the rung's band; 0.219 mm2, 0.51 x 0.51 mm): new, sews run 13; +S4e82738b ('i' ring in the rung's band; 0.219 mm2, 0.51 x 0.51 mm): new, sews run 13; S6dfad8d5 ('j' lettering, under floor; 1.473 mm2, 3.64 x 0.75 mm): run 26 -> run 30; +Sfc08a8ef ('j' ring in the rung's band; 0.219 mm2, 0.51 x 0.51 mm): new, sews run 17

### synthetic Aileron fixture, 80 mm (forced flat)

| arm | stitches | trims | md5 | shapes | tack rings | changed vs OFF |
|---|---|---|---|---|---|---|
| OFF (shipped) | 2,747 | 5 | `bd990187` | 48 | 0 | - |
| small_stem ON | 2,734 | 5 | `8bc915a0` | 48 | 0 | 1 re-sewn ('i' stem); 1 re-walked only (travel/underlay) |
| small_dot_rung ON | 2,774 | 8 | `431a6fc4` | 49 | 0 | 1 new ('i'); 5 re-sewn ('s', 'T', 'I', 'Y', 'P'); 6 re-walked only (travel/underlay) |
| both ON | 2,798 | 8 | `160606b7` | 49 | 0 | 1 new ('i'); 15 re-sewn ('h', 'a', 'A', 'M', 'b', 'o', 'O', 'i' stem, 'v', 'T', 'y', 'p', 'I', 'Y', 'P'); 21 re-walked only (travel/underlay) |
| both ON + lettering scope | 2,798 | 8 | `160606b7` | 49 | 0 | 1 new ('i' rung-admitted); 15 re-sewn ('h', 'a', 'A', 'M', 'b', 'o', 'O', 'i' stem, 'v', 'T', 'y', 'p', 'I', 'Y', 'P'); 21 re-walked only (travel/underlay) |

What the flags see OFF: 1 lettering shape(s) under the 2.25 mm2 floor, of which 1 pass `is_thin_stem` (Sf524dac7 'i' 3.73 x 0.57 mm); 0 ring(s) in the rung's 1.35 to 2.2 mm band.

- **small_stem ON**: Sf524dac7 ('i' stem; 2.124 mm2, 3.73 x 0.57 mm): run 37 -> satin 22, travel 3
- **small_dot_rung ON**: Sd543e5b3 ('s'; 4.710 mm2, 3.75 x 2.75 mm): satin 60, travel 20 -> satin 64, travel 20; +S96707dd4 ('i'; 0.446 mm2, 0.75 x 0.75 mm): new, sews run 14; S1281837e ('T'; 4.461 mm2, 4.87 x 4.09 mm): satin 50, travel 3 -> satin 56, travel 4; Sbaab51af ('I'; 2.771 mm2, 4.87 x 0.57 mm): satin 28 -> satin 32, travel 2; Sb3909013 ('Y'; 4.649 mm2, 4.91 x 3.98 mm): satin 54, travel 5 -> satin 52, travel 7; S73491cce ('P'; 6.598 mm2, 4.94 x 3.45 mm): satin 70 -> satin 72, travel 4
- **both ON**: Scb193920 ('h'; 5.940 mm2, 5.23 x 3.16 mm): satin 62, travel 7, underlay 15 -> satin 64, travel 5, underlay 10; S65fe7214 ('a'; 6.260 mm2, 3.98 x 3.00 mm): satin 72, travel 23 -> satin 74, travel 23; S2f7f28b7 ('A'; 6.724 mm2, 4.94 x 4.20 mm): satin 76, travel 2 -> satin 74, travel 4; S29d24f10 ('M'; 10.981 mm2, 4.87 x 4.87 mm): satin 118, travel 2 -> satin 114, travel 6; Sf1dd03aa ('b'; 7.583 mm2, 5.33 x 3.63 mm): satin 88, travel 4, underlay 12 -> satin 84, travel 5, underlay 12; S2ef69427 ('o'; 6.167 mm2, 3.98 x 3.73 mm): satin 62, travel 10 -> satin 66, travel 3; S3044a111 ('O'; 8.069 mm2, 5.12 x 4.62 mm): satin 80, travel 11, underlay 11 -> satin 84, travel 10, underlay 11; +S96707dd4 ('i'; 0.446 mm2, 0.75 x 0.75 mm): new, sews run 14; Sf524dac7 ('i' stem; 2.124 mm2, 3.73 x 0.57 mm): run 37 -> satin 22; S5e24f665 ('v'; 4.236 mm2, 3.73 x 3.56 mm): satin 48, travel 2 -> satin 52, travel 2; S1281837e ('T'; 4.461 mm2, 4.87 x 4.09 mm): satin 50, travel 3 -> satin 52, travel 4; Se11ee830 ('y'; 5.191 mm2, 5.26 x 3.52 mm): satin 62, travel 3, underlay 13 -> satin 60, travel 5, underlay 10; S0e62b92f ('p'; 7.569 mm2, 5.30 x 3.63 mm): satin 92, travel 2, underlay 13 -> satin 88, travel 16, underlay 13; Sbaab51af ('I'; 2.771 mm2, 4.87 x 0.57 mm): satin 28 -> satin 32, travel 2; Sb3909013 ('Y'; 4.649 mm2, 4.91 x 3.98 mm): satin 54, travel 5 -> satin 52, travel 7; S73491cce ('P'; 6.598 mm2, 4.94 x 3.45 mm): satin 70 -> satin 72, travel 4

### "hijlij" at the 80 mm scale (12.658 mm wide, forced flat)

| arm | stitches | trims | md5 | shapes | tack rings | changed vs OFF |
|---|---|---|---|---|---|---|
| OFF (shipped) | 253 | 1 | `da411b5e` | 6 | 0 | - |
| small_stem ON | 253 | 1 | `da411b5e` (= OFF) | 6 | 0 | **identical** |
| small_dot_rung ON | 328 | 4 | `6a62319c` | 10 | 0 | 4 new ('i', 'j', 'i', 'j'); 3 re-sewn ('l', 'i', 'j'); 2 re-walked only (travel/underlay) |
| both ON | 328 | 4 | `6a62319c` | 10 | 0 | 4 new ('i', 'j', 'i', 'j'); 3 re-sewn ('l', 'i', 'j'); 2 re-walked only (travel/underlay) |
| both ON + lettering scope | 328 | 4 | `6a62319c` | 10 | 0 | 4 new ('i' rung-admitted, 'j' rung-admitted, 'i' rung-admitted, 'j' rung-admitted); 3 re-sewn ('l', 'i', 'j'); 2 re-walked only (travel/underlay) |

What the flags see OFF: no lettering shape under the 2.25 mm2 floor and no ring in the rung's band.

- **small_dot_rung ON**: +Sf88c5ef2 ('i'; 0.561 mm2, 0.81 x 0.81 mm): new, sews run 13; +S6f381afa ('j'; 0.561 mm2, 0.81 x 0.81 mm): new, sews run 17; Sa17d2b33 ('l'; 3.765 mm2, 5.67 x 1.12 mm): satin 34, travel 2, underlay 5 -> satin 38, underlay 5; +Sd735d376 ('i'; 0.561 mm2, 0.81 x 0.81 mm): new, sews run 17; S124c7649 ('i'; 2.502 mm2, 4.05 x 0.62 mm): satin 22 -> satin 26; S924802ac ('j'; 3.731 mm2, 5.82 x 1.21 mm): satin 36, underlay 9 -> satin 40, travel 2, underlay 5; +S22b9a646 ('j'; 0.561 mm2, 0.81 x 0.81 mm): new, sews run 17

### Fremont, Hat, the Studio's request at 50 mm

| arm | stitches | trims | md5 | shapes | tack rings | changed vs OFF |
|---|---|---|---|---|---|---|
| OFF (shipped) | 7,392 | 41 | `404de99d` | 146 | 0 | - |
| small_stem ON | 7,392 | 41 | `404de99d` (= OFF) | 146 | 0 | **identical** |
| small_dot_rung ON | 7,562 | 42 | `f1f0c9a8` | 158 | 0 | 13 new (-, lettering, under floor, lettering, under floor, lettering, under floor, -, -, lettering, under floor, -, -, lettering, under floor, -, lettering, under floor, lettering, under floor); 1 gone (-); 3 re-sewn (-, lettering, under floor, lettering, under floor); 21 re-walked only (travel/underlay) |
| both ON | 7,562 | 42 | `f1f0c9a8` | 158 | 0 | 13 new (-, lettering, under floor, lettering, under floor, lettering, under floor, -, -, lettering, under floor, -, -, lettering, under floor, -, lettering, under floor, lettering, under floor); 1 gone (-); 3 re-sewn (-, lettering, under floor, lettering, under floor); 21 re-walked only (travel/underlay) |
| both ON + lettering scope | 7,392 | 41 | `404de99d` (= OFF) | 146 | 0 | **identical** |

What the flags see OFF: 70 lettering shape(s) under the 2.25 mm2 floor, of which 0 pass `is_thin_stem` (none); 0 ring(s) in the rung's 1.35 to 2.2 mm band.

- **small_dot_rung ON**: +S78e6cd01 (-; 657.592 mm2, 48.67 x 25.29 mm): new, sews satin 3003, travel 122, underlay 239; -S78e6cd01 (-; 658.234 mm2, 48.67 x 25.29 mm): gone, sewed satin 3003, travel 122, underlay 239; Sfb63d6b6 (-; 0.304 mm2, 1.21 x 0.33 mm): run 13 -> run 17; +S4a76640c (lettering, under floor; 0.377 mm2, 1.00 x 0.80 mm): new, sews run 12; +S87f8e203 (lettering, under floor; 0.343 mm2, 1.04 x 0.74 mm): new, sews run 13; +Sd5ad2671 (lettering, under floor; 0.281 mm2, 1.00 x 0.88 mm): new, sews run 19; +Sc03f24ad (-; 0.295 mm2, 1.10 x 0.35 mm): new, sews run 10; +S134e7c81 (-; 0.259 mm2, 1.04 x 0.36 mm): new, sews run 10; +S12f61a81 (lettering, under floor; 0.313 mm2, 1.16 x 0.40 mm): new, sews run 13; +S7cee26d0 (-; 0.315 mm2, 1.17 x 0.40 mm): new, sews run 13; +Sa986c1b4 (-; 0.293 mm2, 1.11 x 0.35 mm): new, sews run 13; +Sa456dad6 (lettering, under floor; 0.180 mm2, 1.01 x 0.50 mm): new, sews run 17; +S5e578026 (-; 0.612 mm2, 1.05 x 0.75 mm): new, sews run 13; +Scd3154e8 (lettering, under floor; 0.273 mm2, 0.97 x 0.76 mm): new, sews run 13; S4fb237f2 (lettering, under floor; 0.309 mm2, 1.23 x 0.34 mm): run 17 -> run 13; +Sed4dc30f (lettering, under floor; 0.316 mm2, 1.02 x 0.72 mm): new, sews run 29; S3347fba0 (lettering, under floor; 0.310 mm2, 1.22 x 0.35 mm): run 17 -> run 13

### Fremont, Hat, the Studio's request at 80 mm

| arm | stitches | trims | md5 | shapes | tack rings | changed vs OFF |
|---|---|---|---|---|---|---|
| OFF (shipped) | 14,843 | 44 | `012b6464` | 162 | 0 | - |
| small_stem ON | 14,843 | 44 | `012b6464` (= OFF) | 162 | 0 | **identical** |
| small_dot_rung ON | 14,876 | 44 | `a3fb62b7` | 164 | 0 | 2 new (-, -); 9 re-sewn (lettering, under floor, -, lettering, under floor, -, -, -, -, -, lettering, under floor); 1 re-walked only (travel/underlay) |
| both ON | 14,876 | 44 | `a3fb62b7` | 164 | 0 | 2 new (-, -); 9 re-sewn (lettering, under floor, -, lettering, under floor, -, -, -, -, -, lettering, under floor); 1 re-walked only (travel/underlay) |
| both ON + lettering scope | 14,843 | 44 | `012b6464` (= OFF) | 162 | 0 | **identical** |

What the flags see OFF: 77 lettering shape(s) under the 2.25 mm2 floor, of which 0 pass `is_thin_stem` (none); 0 ring(s) in the rung's 1.35 to 2.2 mm band.

- **small_dot_rung ON**: +Sad066f4d (-; 0.388 mm2, 1.09 x 0.56 mm): new, sews run 17; S70e7e44c (lettering, under floor; 0.734 mm2, 2.04 x 0.67 mm): run 23 -> run 19; S31fdca10 (-; 10.169 mm2, 5.88 x 4.63 mm): satin 90, travel 18, underlay 14 -> satin 98, travel 15, underlay 14; Scead5d18 (lettering, under floor; 2.196 mm2, 2.62 x 2.24 mm): run 41 -> run 45; Sbf647133 (-; 24.806 mm2, 6.10 x 6.02 mm): fill 143, travel 1, underlay 16 -> fill 149, travel 2, underlay 16; S54b55cf1 (-; 3.248 mm2, 2.62 x 2.53 mm): run 55 -> run 51; S00d683b7 (-; 12.962 mm2, 5.84 x 5.17 mm): satin 112, travel 9, underlay 16 -> satin 110, travel 15, underlay 15; S044d3595 (-; 0.167 mm2, 0.62 x 0.59 mm): run 19 -> run 18; S6ba247be (-; 2.921 mm2, 2.62 x 2.05 mm): run 61 -> run 53; Sdcd93482 (lettering, under floor; 0.739 mm2, 2.00 x 0.64 mm): run 23 -> run 19; +S0b0ad7a3 (-; 0.369 mm2, 1.06 x 0.56 mm): new, sews run 17

### sp_fremont_tagline at 2.5 mm caps (29.75 mm wide)

| arm | stitches | trims | md5 | shapes | tack rings | changed vs OFF |
|---|---|---|---|---|---|---|
| OFF (shipped) | 590 | 5 | `c57e1189` | 17 | 0 | - |
| small_stem ON | 590 | 5 | `c57e1189` (= OFF) | 17 | 0 | **identical** |
| small_dot_rung ON | 590 | 5 | `c57e1189` (= OFF) | 17 | 0 | **identical** |
| both ON | 590 | 5 | `c57e1189` (= OFF) | 17 | 0 | **identical** |
| both ON + lettering scope | 590 | 5 | `c57e1189` (= OFF) | 17 | 0 | **identical** |

What the flags see OFF: 9 lettering shape(s) under the 2.25 mm2 floor, of which 0 pass `is_thin_stem` (none); 0 ring(s) in the rung's 1.35 to 2.2 mm band.

### sp_fremont_tagline at 3 mm caps (35.7 mm wide)

| arm | stitches | trims | md5 | shapes | tack rings | changed vs OFF |
|---|---|---|---|---|---|---|
| OFF (shipped) | 719 | 5 | `df03b9cc` | 17 | 0 | - |
| small_stem ON | 719 | 5 | `df03b9cc` (= OFF) | 17 | 0 | **identical** |
| small_dot_rung ON | 719 | 5 | `df03b9cc` (= OFF) | 17 | 0 | **identical** |
| both ON | 719 | 5 | `df03b9cc` (= OFF) | 17 | 0 | **identical** |
| both ON + lettering scope | 719 | 5 | `df03b9cc` (= OFF) | 17 | 0 | **identical** |

What the flags see OFF: 3 lettering shape(s) under the 2.25 mm2 floor, of which 0 pass `is_thin_stem` (none); 0 ring(s) in the rung's 1.35 to 2.2 mm band.

### sp_fremont_tagline at 4 mm caps (47.61 mm wide)

| arm | stitches | trims | md5 | shapes | tack rings | changed vs OFF |
|---|---|---|---|---|---|---|
| OFF (shipped) | 985 | 10 | `35ff0da6` | 17 | 0 | - |
| small_stem ON | 985 | 10 | `35ff0da6` (= OFF) | 17 | 0 | **identical** |
| small_dot_rung ON | 985 | 10 | `35ff0da6` (= OFF) | 17 | 0 | **identical** |
| both ON | 985 | 10 | `35ff0da6` (= OFF) | 17 | 0 | **identical** |
| both ON + lettering scope | 985 | 10 | `35ff0da6` (= OFF) | 17 | 0 | **identical** |

What the flags see OFF: no lettering shape under the 2.25 mm2 floor and no ring in the rung's band.

### Becker, left chest, six colours, 50 mm

| arm | stitches | trims | md5 | shapes | tack rings | changed vs OFF |
|---|---|---|---|---|---|---|
| OFF (shipped) | 2,961 | 16 | `63d6ca06` | 17 | 0 | - |
| small_stem ON | 2,961 | 16 | `63d6ca06` (= OFF) | 17 | 0 | **identical** |
| small_dot_rung ON | 2,961 | 16 | `63d6ca06` (= OFF) | 17 | 0 | **identical** |
| both ON | 2,961 | 16 | `63d6ca06` (= OFF) | 17 | 0 | **identical** |
| both ON + lettering scope | 2,961 | 16 | `63d6ca06` (= OFF) | 17 | 0 | **identical** |

What the flags see OFF: no lettering shape under the 2.25 mm2 floor and no ring in the rung's band.

### Becker, left chest, six colours, 80 mm

| arm | stitches | trims | md5 | shapes | tack rings | changed vs OFF |
|---|---|---|---|---|---|---|
| OFF (shipped) | 6,148 | 25 | `76620f8c` | 17 | 0 | - |
| small_stem ON | 6,148 | 25 | `76620f8c` (= OFF) | 17 | 0 | **identical** |
| small_dot_rung ON | 6,148 | 25 | `76620f8c` (= OFF) | 17 | 0 | **identical** |
| both ON | 6,148 | 25 | `76620f8c` (= OFF) | 17 | 0 | **identical** |
| both ON + lettering scope | 6,148 | 25 | `76620f8c` (= OFF) | 17 | 0 | **identical** |

What the flags see OFF: no lettering shape under the 2.25 mm2 floor and no ring in the rung's band.
## Renders

All at 40 px/mm unless named otherwise, artwork beside every arm, the arm's counts and md5 in
its caption; thread at its laid width (`digitizer_core.stitchviz`), a picture of the file,
not of cloth. Reproduce with `python -m tools.small_stem_dot_renders all --out DIR` then
`render` (and `bisect fremont_hat_80 S044d3595`); every cell is its own process.

| file | what it shows |
|---|---|
| `aileron_80_siv.png` | s, i, v of the 80 mm fixture; the hollow stem OFF, the satin column with `small_stem`, the dot with the rung |
| `aileron_80_i.png` | the same i at 120 px/mm |
| `aileron_50_siv.png`, `aileron_50_i.png` | the 50 mm fixture: five identical arms, the i folded by the two-tone snap before any flag |
| `hijlij_80_word.png`, `hijlij_80_ij.png` | the word at the 80 mm scale; the four dots as outline rings (the ij pair at 120 px/mm) |
| `hijlij_50_word.png`, `hijlij_50_ij.png` | the word at the 50 mm scale; the dots as tack rings, the bridge from the stem |
| `fremont_hat_80_tagline.png` | EAT \| STAY \| PLAY at 80 mm, every arm |
| `fremont_hat_80_changed_1.png` | the Wisconsin at 120 px/mm: the asterisk OFF, gone under the black with the rung, back with the scope |
| `fremont_hat_80_S044d3595_bisect.png` | the star box from each arm's stream cut at every colour change: OFF lays the mark in the last block, the rung in the first |
| `fremont_hat_80_changed_2.png` | the rope's right end at 120 px/mm: the new tan sliver the rung admits |
| `fremont_hat_50_tagline.png` | the tagline at 50 mm, every arm |
| `fremont_hat_50_changed_1.png`, `fremont_hat_50_changed_2.png` | rope slivers, and 1895 as tack-ring blobs, with the rung at 50 mm |
| `sp_fremont_tagline_2.5_design.png`, `_3_`, `_4_` | the three corpus cells, identical in every arm |

## The flip questions, for Kent (stated, not decided)

1. **`lettering_columns_small_stem`.** On everything here it changes exactly one shape: the
   80 mm synthetic i stem, hollow run to satin column, 13 stitches fewer. It moves nothing on
   Fremont at either width, on the three tagline cells, on Becker or on the word, because its
   0.5 mm cross floor and aspect 6 keep it off every thin bar and every rope segment. Flip it
   for that one letter, or leave it OFF until a corpus design puts a real stem in its window?
   The catch #896 named still holds: `STEM_MIN_ASPECT` and the 0.5 / 1.5 limits come from one
   synthetic face and one screenshot.
2. **`small_dot_rung` alone.** It buys the dots on the word at both scales and on the fixture at
   80 mm. It costs the Wisconsin star on your own 80 mm Hat (the asterisk sews first and the
   black covers it), two rope slivers there, and at 50 mm it sews EST 1895 as blobs and the rope
   ends as sausages. Unscoped, it cannot go ON without losing the star, unless `detail_spokes`
   claims its region ahead of the rung, which is an engine change nobody has made.
3. **`small_dot_rung` with `small_dot_rung_lettering`.** Byte-identical to OFF on Fremont at
   both widths, on all three tagline cells and on Becker; keeps every synthetic dot the rung
   keeps; its only measured cost is the synthetic neighbours' re-walk. Its catch is #975's: no
   corpus design puts a real i or j dot in the band, so what it buys is synthetic so far, and its
   ratios were tuned on the photos they were measured on. Is a synthetic-only benefit enough to
   flip a pair of flags, or does it wait for a customer design with a lowercase i?
4. **The 50 mm fixture is a two-tone question, not a floor question.** Neither flag reaches a
   dot the snap has already folded. If the 50 mm size is one you read, the snap's fringe rule at
   that scale (`two_tone.apply`, stage 1.3) is the thing to trace next; it is not touched here.
5. **Both together** add nothing beyond the sum: on every case but the 80 mm fixture, both ON
   has the rung's md5, and on the fixture the difference from either alone is the neighbours'
   walk order.

Gates: no physical constant moved, no default flipped, no stage-0 change, no client art
(the Fremont crops are the committed fixture). No sew-out exists: these are pictures of the
file, not of thread on cloth.
