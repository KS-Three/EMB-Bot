# Golden Tee hat: where ours is +95% stitches and +160% trims (2026-10-27)

**Kent's ruling, 2026-10-27 (relayed by the director), verbatim: "Record it, no build
(Recommended)".** Nothing here changes the engine. Numbers only: no pro file, render or crop is
committed.

**The pro simplified the design.** 39% of our extra stitches are two layers of the artwork that he
never sews at all: GOLF's silver extrusion and the GT's red inner stroke. The white faces, the
starting suspect, are 22%.

## What was measured

- Main `8341d1f7`, the Studio's request at the pro's 74.9 mm on `hat_front`, through
  `tools.pro_pair.digitize`.
- Our `ours.dst` is byte for byte the file in the pro baseline (#1141, md5 `a45b0763`): 11,629
  stitches and 26 trims, against the pro's 5,973 and 10 (`pro_pair.pro_counts`).
- Both machine files go through one reader, each in its own frame:
  - `tools/pro_parity/prep_all.decode` splits each file into needle-down runs;
  - a 12-stitch window classes every stitch as satin, fill or run, with `tools.inpiece_cuts.character`'s thresholds;
  - `tools/pro_fill_underlay.py` reads the fills, `tools.trim_classes` and `tools.inpiece_cuts` the trims.
- Our layer and kind of each stitch comes from the plan's own runs.
- An AREA is the pro's element nearest to the stitch, once the two files' extents are laid on each other.

## The pro's file: 7 blocks in 3 threads

| block | thread | stitches | element | construction |
|---|---|---|---|---|
| 0 | white | 1,770 | GT faces: G 1,101, T 669 | one tatami run per face (below) |
| 1 | orange | 922 | GT bevel band: G 516, T 406 | satin over the face's edge |
| 2 | black | 1,043 | GT outline (G 601, T 375), the TM (29), one 38-stitch piece on GOLF's G | satin; the TM is a double run |
| 3 | orange | 697 | GOLF: G 220, O 225, L 107, F 145 | one satin per letter |
| 4 | white | 430 | ball band | one satin band |
| 5 | black | 771 | ball arc 444, tee shadow 327 | satin |
| 6 | orange | 340 | tee | satin |

He sews no silver and no red. GOLF's extrusion and bevel highlights, and the GT's red inner stroke,
are gone; GOLF is one orange satin per letter.

## Where our +5,656 stitches are

**By thread**

| thread | ours | pro | gap | share of the gap |
|---|---|---|---|---|
| Silver `3971` (GOLF's extrusion, small GT pieces) | 1,503 | 0 | +1,503 | 27% |
| Cardinal `1904` (the GT's red inner stroke) | 676 | 0 | +676 | 12% |
| White `0015` (faces, ball crescent) | 3,712 | 2,200 | +1,512 | 27% |
| Pumpkin `1102` + Orange Peel `0703` | 2,944 | 1,959 | +985 | 17% |
| Black `0020` | 2,794 | 1,814 | +980 | 17% |

**By area**

| area | ours | pro | gap |
|---|---|---|---|
| GOLF | 3,884 | 997 | +2,887 (51%) |
| GT (faces, bevel, red stroke, outline) | 5,726 | 3,406 | +2,320 (41%) |
| ball | 1,307 | 874 | +433 |
| tee | 712 | 667 | +45 |
| TM | 0 | 29 | -29 (stage 2 drops it: [`tm-mark-golden-tee-2026-10-26`](../.claude/memory/tm-mark-golden-tee-2026-10-26.md)) |

GOLF is half the gap. He sews it as 4 satins (697 stitches). We sew it as layers in five threads:
the letters in Pumpkin, an 85 mm² silver extrusion under the whole word, black, Orange Peel
highlights and Cardinal.

## Trims: 26 against 10 (+16)

- **Inside one piece: ours 6, his 0** (`tools.inpiece_cuts`):
  - `fill_section` 3: the G face 2, the T face 1;
  - `satin_split` 3: the ball crescent 1, a black GOLF shape 2.
- **Between pieces: ours 20, his 9** (`tools.trim_classes` reads 9 hops in his file, a run of trims
  counting once). We sew 33 shapes in 6 threads and 9 blocks. He sews 16 runs in 3 threads and 7 blocks.

| thread | ours | pro |
|---|---|---|
| white | 5 (4 of them inside a piece) | 1 (G face to T face) |
| silver + cardinal | 7 | 0 |
| black | 8 | 4 |
| orange family | 6 | 4 |

## The white faces: +1,243 (22% of the gap)

| | ours | pro |
|---|---|---|
| G face | 2,122: fill 1,295, **ring 640**, underlay 115, travel 72 | 1,101, one run |
| T face | 891: fill 795, underlay 68, travel 28 | 669, one run |
| row angle (most common) | G 92 deg, T 12 deg | both 20-25 deg |
| top stitch length, p50 of stitches over 1 mm | 1.97 mm (p90 3.0) | 3.45 mm |
| top row pitch, as `pro_fill_underlay` reads it | 0.12 mm | 0.17 mm |
| underlay | CROSS, 1.0 mm pitch, 2.75 mm stitch, 89.8 deg, 10.8% of the thread | CROSS, 0.98 mm, 3.76 mm, 89.1 deg, 16.7% |
| edge run | none | none |
| cuts inside a face | 3 | 0 |
| ball crescent | 699: satin 344 + underlay 355 | 430, one satin band |

**The 640-stitch ring is `border_by_size`** (ON since 2026-10-23).
- It rings the G face because its smallest dimension is 6 mm or more; the T face's is not.
- `border_from_outline` exempts a body from that ring only when ONE art shape loops it, as on Becker
  and MFab. Golden Tee's ring is four shapes in four threads (bevel, red stroke, outline), so the G
  face is not anyone's body and gets a ring of its own.
- It shows: under 0.3 of its length lies under satin sewn later. The pro's face has no ring.

### The pro's rule for these faces

Each white face is ONE tatami run at about 22 deg, on a CROSS underlay (0.98 mm pitch, 3.76 mm
stitches, 89 deg, 17% of the thread), with no edge run and no ring of its own. His orange bevel
satin and black outline satin sew over its edge afterwards.

**Where it holds and where it doesn't**, read by `tools/pro_fill_underlay.py` on every pro file with a
sewn white or hollow area:

| file, block | underlay | top pitch | underlay pitch / stitch / angle / share | edge run |
|---|---|---|---|---|
| Golden Tee, 0 | CROSS | 0.17 | 0.98 / 3.76 / 89.1 / 16.7% | no |
| Becker hat small, 1 and 3 | CROSS | 0.17, 0.18 | 0.97-0.99 / 3.99 / 89.4-89.5 / 16-17% | yes, no |
| Becker hat large, 1 and 3 | CROSS | 0.17, 0.18 | 0.94-0.98 / 3.99 / 89.4-89.7 / 15.6% | no, no |
| Fremont hat, 0 | CROSS | 0.17 | 0.75 / 3.51 / 88.7 / 17.3% | no |
| MFab hat, 0 and 1 | CROSS | 0.17, 0.19 | 0.99 / 3.31-3.99 / 88.9-89.5 / 7.7-19.7% | no, yes |
| To a T Machine hat, 0 | CROSS | 0.18 | 0.98 / 4.02 / 89.8 / 17.9% | yes |
| To a T beanie, 1 | CROSS | 0.17 | 0.99 / 4.02 / 89.8 / 16.8% | yes |

- The CROSS underlay holds on every one, and the 22 deg tatami holds on Becker too
  ([`white-faces-fill-2026-10-25`](../.claude/memory/white-faces-fill-2026-10-25.md)).
- "No edge run" does NOT hold: four of these fills walk one.
- On our side, the ring is the defect, and across the 22 baseline jobs only Golden Tee's G face takes
  one on a sewn white field.
  - Read over #1141's `design.json` files: `border` rings sit on 7 jobs (Bridge LC, the three Gaulke
    Roofing jobs, Golden Tee, MFab hat, Tires), and only Golden Tee's and MFab hat's are white.
  - MFab hat's 128-stitch white ring is the one not checked; it needs a digitize for its region meta.

## Priced (each a `plan_stitches` re-plan of one digitize)

| arm | DST md5 | stitches | trims | colour changes | what changes |
|---|---|---|---|---|---|
| today | `a45b0763` | 11,629 | 26 | 8 | |
| no ring on a sewn white field (a runtime patch, pricing only, never built) | `63d86d18` | 11,000 | 26 | 8 | G face 2,122 -> 1,493 |
| `sew_enclosed_white_fields_fill` ON | `31543a09` | 12,430 | 30 | 9 | worse (below) |
| fields_fill + no ring | `b8eb40f4` | 11,798 | 30 | 9 | |
| `cfg.extra["fill_section_travel"]` ON | `20ce428b` | 11,622 | 26 | 8 | none of the three face cuts goes |
| fields_fill + no ring + fill_section_travel | `3590936f` | 11,747 | 27 | 9 | |
| `pro_measured_values` ON (gate 1, report only) | `c2c197cf` | 11,958 | 25 | 8 | face fills -80 stitches each, satins up |

**`sew_enclosed_white_fields_fill` makes Golden Tee worse.**
- The G and T faces keep their 92 and 12 deg rows: the 22 deg it sets does not reach them, and why
  was not traced.
- The ball crescent, a sewn white field too, moves from satin to a 1,251-stitch fill. The pro satins it.

## Candidates for the next sew-out card (gate 1: fabric decides, geometry cannot)

1. **Fill stitch length.** Our face fills sew 1.97 mm top stitches against his 3.45 mm.
   `pro_measured_values` already carries his value, built OFF.
2. **The ball crescent's underlay.** We lay 355 underlay stitches (530 mm of thread, median stitch
   0.8 mm) under 344 satin stitches; his whole band is 430 stitches.

## What a build would have bought

- **A `white_field_no_ring` flag, built OFF:** -629 stitches and no trims, on one job.
- **Dropping layers the pro never sews** (R15, `docs/pro-digitizer-rules-2026-10-21.md`): up to -2,179
  stitches and -7 trims here.
  - Only 2 artworks have such layers: Golden Tee, and Drone's gradient letters.
  - Becker contradicts it: its drop shadow is the outline's own black, and the pro sews it, filled under the loop.
  - Nothing yet reads a "shadow layer".
