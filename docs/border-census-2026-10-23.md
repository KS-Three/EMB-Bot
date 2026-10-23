# Border census: ours versus the pro's, every paired logo (2026-10-23)

**Question.** Kent saw our output put satin-looking borders on small shapes (ProSeal's
blue bubbles) where the pro's file has none. Is that one logo or a pattern? This
measures every closed shape of every logo that has both the customer's art and a pro
stitch file, so the fix can be a rule.

**Scope.** The 15 designs of `pro-parity-real-art-2026-08-15.md` section 2 (7 logos)
plus ProSeal's hat. Each design digitized at the pro's own width with the matching
preset (hat, beanie, left chest, patch), through the Studio's request
(`tools/pro_pair.digitize`). Regenerate with `python tools/border_census.py run`
(digitize and table) or `... table --crop-ids slug:id` (crops). No engine change, no flag.

## Verdict, in four lines

1. **Our `stage6_border` almost never runs.** The Studio sends no `border`, so the
   border tier is off for flat art; it produced border runs on exactly ONE shape in
   all 16 designs (`tires_hat_3d` `S91cf86bf`). The rings on small shapes come from
   the **edge cap** (`edge_cap="bean"`, stage 7 cap pieces: 21 cap runs on ProSeal
   against 0-6 elsewhere) and the **run tier** that outlines a small rescued shape
   (`routes_to_run`: 26 shapes on ProSeal, 4-7 on Bridge, 28 on the Drone). They are
   bean (triple-run) rings, not satin, but they read as borders at hat size.
2. **ProSeal is the clean case.** Our 7 ringed shapes (1.1-3.8 mm smallest dimension,
   the cyan bubbles) all sit in a pro file with no ring on any of them. The pro sews
   the bubbles as plain fills (crop `proseal_hat_Sa257d683_a.png`) and drops the
   smallest dots to nothing at all (`proseal_hat_S24ff7560_a.png`).
3. **It is a pattern, but a size pattern, not a logo pattern.** The pro rings
   shapes in proportion to how big they are; we ring them in proportion to how
   bean-able they are. Below 4 mm we ring about as often as the pro or a little more
   (19 of 709 shapes against 12); above 6 mm we ring far less often (7 of 47
   against 23 of 47) because we sew those whole in satin where the pro sews a
   fill with a satin border.
4. **Instrument caveat, read before using a row.** The detector (below) is an
   approximation; the pair-level counts are stable from run to run, single rows are
   not. Several (b) rows on 6 mm glyph rings are the SAME satin ring labelled
   differently on each side. Every row class has a crop; trust the crop over the row.

## The rule the pro appears to follow

> The pro lays a satin border (about 1.5-2.5 mm wide, sewn on top of the fill) round a
> closed shape only when its smallest dimension is about 4 mm or more (area roughly 20
> mm2 and up; about half of shapes of 6 mm and up are bordered), and round almost
> nothing under 3 mm, whatever the contrast: bubbles, dots and small hexagons are
> filled and left bare.

Measured on the 805 shapes of at least 1 mm2 that we sewed something for:

| smallest dimension | shapes | pro ringed | share | ours ringed | share |
|---|---|---|---|---|---|
| under 2 mm | 590 | 4 | 0.7% | 7 | 1.2% |
| 2-3 mm | 73 | 5 | 6.8% | 7 | 9.6% |
| 3-4 mm | 46 | 3 | 6.5% | 5 | 10.9% |
| 4-6 mm | 49 | 14 | 28.6% | 20 | 40.8% |
| 6 mm and up | 47 | 23 | 48.9% | 7 | 14.9% |

- **Contrast is not the variable.** The pro's ringed shapes read 70 dE median against
  their surround, but Becker's big letters are ringed at 30 dE while ProSeal's bubbles
  (about 50 dE) are left bare. Size separates the two groups; contrast does not.
- **Shape kind.** 23 of the pro's ringed shapes have holes (letters and badges); the
  border follows the outer edge and the counters. Round or hexagonal blobs under 4 mm
  are not ringed where we can see the fill (ProSeal); the star on Hotel Fremont is
  the exception below.

**Rows that contradict the rule** (pro rings a shape under 4 mm), and what they are:

- `hotel_fremont_patch` `S3d684c8d` (2.9 x 2.4 mm star): both files ring it, so ours
  matches the pro here; on the hat file the pro sews the same star as plain satin (an
  `a` row).
- `proseal_hat` `S5d125db3` (2.3 mm), `mfab_hat` `Sdbb6b935` (2.4), `mfab_lc`
  `S8a9cdd7f` (2.2), `tires_hat_3d` `Sf41eecf1` (3.6): the pro's file shows a ring we
  did not sew (ours: unsewn, run, or fill). Four counterexamples to "never under 4 mm".
- Six more rows under 4 mm (Gaulke `S78912344`, `S9dc6b87b`; MFab `S201d3670`,
  `S279c65cd`; Bridge `Sa045b0ab`, `Sdd0362d5`) are satin ring-shaped glyphs (an O, a
  badge ring): the pro's ring detection fires on the glyph's own satin loop. I did
  not verify each by crop; treat them as detector noise unless a crop says otherwise.

## What the table cannot say

- **One detector, both sides.** Ours is written to DST and read back, so both go
  through `census_pro._phases` and the same masks. A BORDER is a satin column whose
  spine closes into a round loop hugging the shape's outline, or satin along at least
  60% of the outline with the shape's centre not satin (the pro splits a border into
  two open half columns, as Fremont's shield does); an OUTLINE is the same with a run
  or bean loop sewn over the interior (a loop sewn BEFORE the interior is underlay and
  is dropped). Hotel Fremont's shield border is found on both sides, the one place
  this was checked against `tools/border_pro.py`.
- **Shapes are ours.** A pro ring on an outline our segmentation lacks lands on
  whichever of our shapes it crosses.
- **Registration.** Pro and ours are aligned by `pairframe.register_pair`; on 1-2 mm
  shapes half a millimetre of drift moves a ring onto its neighbour. The five Becker
  files are one artwork at five sizes and show the same (b) row each time: one
  observation, not five.
- **Crops** use the same registration; they show the neighbourhood, not always the
  exact shape (the Fremont and MFab crops are the loosest).

## Which of our rules produced our choice

| what we sewed | function | where it showed |
|---|---|---|
| bean ring round a fill, small shapes | edge cap, stage 7 (`edge_cap="bean"` cap pieces, gate `_sewn_linear_cover`) | ProSeal bubbles, Bridge fills, Gaulke |
| bean outline in place of a fill | run tier, `routes_to_run` in `stage7_sequence.stitch_one` (small-shape rescue) | ProSeal dots, Drone, Bridge |
| whole satin on a big ring-shaped region | satin tier, `stage6_satin` (`_sews_satin`) | Becker, MFab, Bridge big letters (the pro: fill plus border) |
| satin border (`border` kind) | `stage6_border.border_runs`, wanted per `_border_wanted` | one shape in the whole corpus (Tires `S91cf86bf`) |
| seam handed to the shape sewn later | `_owned_by_later` (ruled 2026-09-09) | decided no row: it only acts where `border` runs exist |

## The numbers

<!-- generated by tools/border_census.py; regenerate, do not hand-edit -->

### Per pair

| pair | shapes >=1 mm2 | ours ring | pro ring | both | (a) | (b) | (c) | pro width mm |
|---|---|---|---|---|---|---|---|---|
| becker_hat_large | 17 | 3 | 7 | 3 | 0 | 1 | 0 | 101.9 |
| becker_lc_large | 17 | 3 | 6 | 2 | 1 | 1 | 0 | 95.7 |
| becker_hat_small | 17 | 2 | 7 | 2 | 0 | 1 | 1 | 76.5 |
| becker_chest_small | 17 | 3 | 7 | 2 | 1 | 1 | 0 | 76.5 |
| becker_beanie | 17 | 2 | 6 | 2 | 0 | 1 | 0 | 79.8 |
| gaulke_roofing_hat | 52 | 1 | 5 | 0 | 1 | 0 | 0 | 114.2 |
| gaulke_roofing_lc | 52 | 1 | 4 | 0 | 1 | 0 | 0 | 95.2 |
| hotel_fremont_hat | 149 | 3 | 2 | 2 | 1 | 0 | 0 | 92.6 |
| hotel_fremont_patch | 149 | 3 | 4 | 3 | 0 | 1 | 2 | 92.5 |
| mfab_hat | 75 | 3 | 8 | 1 | 2 | 6 | 0 | 104.9 |
| mfab_lc | 68 | 1 | 8 | 0 | 1 | 7 | 0 | 96.7 |
| precision_drone | 95 | 2 | 3 | 1 | 1 | 2 | 0 | 62.6 |
| tires_hat_3d | 6 | 1 | 2 | 0 | 1 | 2 | 0 | 114.3 |
| bridge_hat | 32 | 4 | 2 | 0 | 4 | 1 | 0 | 63.3 |
| bridge_lc | 32 | 7 | 1 | 0 | 7 | 0 | 0 | 76.6 |
| proseal_hat | 64 | 7 | 4 | 0 | 7 | 1 | 0 | 85.9 |

- pro ringed shapes: n=76, min dim median 5.4 mm (range 1.4-10.3), area median 126.4 mm2, contrast median 70 dE, with a hole 29
- our ringed shapes: n=46, min dim median 4.5 mm (range 1.2-10.0), area median 43.5 mm2, contrast median 72 dE, with a hole 10
- pro shapes with no ring (FILL, SATIN, RUN, NONE): n=783, min dim median 1.0 mm (range 0.3-10.2), area median 3.1 mm2, contrast median 46 dE, with a hole 84

| min dim (mm) | shapes | pro ring | our ring |
|---|---|---|---|
| 0-2 | 609 | 5 | 7 |
| 2-3 | 90 | 13 | 7 |
| 3-4 | 50 | 7 | 5 |
| 4-6 | 57 | 22 | 20 |
| 6-10 | 50 | 28 | 6 |
| 10-up | 3 | 1 | 1 |

### Rows (a) ours borders, pro does not; (b) pro borders, ours does not; (c) both, widths differ

| pair | shape | size mm (bbox / min dim) | holes | contrast dE | ours (class, width) | we sewed | rule | pro (class, width) | row |
|---|---|---|---|---|---|---|---|---|---|
| becker_hat_large | S92f2350b | 101.7x42.6 / 10.3 | 5 | 31 | SATIN, 2.4 | 3516 satin, 1622 underlay, 239 fill | satin tier (stage6_satin) on a ring-shaped region | BORDER, 2.48 | b |
| becker_lc_large | Sd86ce3cb | 95.5x40.0 / 9.6 | 5 | 31 | SATIN, 2.21 | 3136 satin, 1075 underlay, 212 fill | satin tier (stage6_satin) on a ring-shaped region | BORDER, 2.37 | b |
| becker_lc_large | Sef4e6850 | 25.7x26.9 / 5.5 | 0 | 8 | BORDER, 2.28 | nothing | edge cap, stage 7 (`edge_cap=bean` cap pieces) | FILL, 2.14 | a |
| becker_hat_small | S118e45fc | 76.3x32.0 / 7.7 | 5 | 30 | SATIN, 2.28 | 2418 satin, 943 underlay | satin tier (stage6_satin) on a ring-shaped region | BORDER, 2.01 | b |
| becker_hat_small | Sc32ce326 | 20.5x21.5 / 4.4 | 0 | 7 | BORDER, 2.21 | nothing | edge cap, stage 7 (`edge_cap=bean` cap pieces) | BORDER, 1.8 | c |
| becker_chest_small | S118e45fc | 76.3x32.0 / 7.7 | 5 | 30 | SATIN, 2.11 | 2388 satin, 562 underlay | satin tier (stage6_satin) on a ring-shaped region | BORDER, 2.02 | b |
| becker_chest_small | Se08e8496 | 9.8x12.8 / 5.4 | 0 | 73 | BORDER, 2.3 | 239 satin, 30 underlay | satin tier (stage6_satin) | SATIN, 2.91 | a |
| becker_beanie | S10625c97 | 79.6x33.3 / 8.0 | 5 | 30 | SATIN, 2.2 | 2589 satin, 941 underlay | satin tier (stage6_satin) on a ring-shaped region | BORDER, 2.02 | b |
| gaulke_roofing_hat | S82b4fec1 | 58.1x18.1 / 5.7 | 0 | 94 | BORDER, 1.8 | 1228 satin, 71 underlay | edge cap, stage 7 (`edge_cap=bean` cap pieces) | SATIN, 2.75 | a |
| gaulke_roofing_lc | Sd95b397f | 2.7x3.7 / 2.8 | 0 | 95 | BORDER, 1.2 | 80 fill, 9 underlay | edge cap, stage 7 (`edge_cap=bean` cap pieces) | FILL, 1.0 | a |
| hotel_fremont_hat | S3d684c8d | 2.9x2.4 / 2.6 | 0 | 100 | BORDER, 1.4 | 77 fill, 10 underlay | fill tier (stage6_fill) | SATIN, 1.4 | a |
| hotel_fremont_patch | S78e6cd01 | 92.4x49.7 / 7.4 | 155 | 71 | FILL, 1.2 | 11248 fill, 406 underlay | edge cap (bean ring) | BORDER, 1.5 | b |
| hotel_fremont_patch | S10d3c3b0 | 5.4x5.4 / 5.4 | 0 | 100 | BORDER, 0.99 | 156 fill, 11 underlay | fill tier (stage6_fill) | BORDER, 1.49 | c |
| hotel_fremont_patch | Sf979bc42 | 5.3x5.4 / 5.4 | 0 | 100 | BORDER, 0.99 | 155 fill, 11 underlay | fill tier (stage6_fill) | BORDER, 1.48 | c |
| mfab_hat | S02609ac7 | 19.5x17.9 / 7.0 | 1 | 99 | FILL, 1.0 | 726 satin, 55 underlay | satin tier (stage6_satin) on a ring-shaped region | BORDER, 2.4 | b |
| mfab_hat | Sfb63bcf2 | 20.9x17.9 / 7.9 | 0 | 100 | FILL, 1.1 | 895 satin, 50 underlay | satin tier (stage6_satin) | BORDER, 2.1 | b |
| mfab_hat | Sc4d2fcb1 | 20.9x18.0 / 6.9 | 1 | 100 | FILL, 1.08 | 759 satin, 47 underlay | satin tier (stage6_satin) on a ring-shaped region | BORDER, 2.4 | b |
| mfab_hat | S384bf43b | 11.3x17.8 / 7.5 | 0 | 99 | FILL, 1.03 | 346 satin, 27 underlay | satin tier (stage6_satin) | BORDER, 1.89 | b |
| mfab_hat | S127f7bff | 17.2x6.5 / 6.6 | 0 | 100 | FILL, 1.08 | 382 fill, 49 underlay | edge cap (bean ring) | BORDER, 2.4 | b |
| mfab_hat | Sdbb6b935 | 4.8x5.3 / 2.4 | 0 | 99 | SATIN, 1.36 | 318 satin, 35 underlay | satin tier (stage6_satin) | BORDER, 1.48 | b |
| mfab_hat | Sfbae5fe3 | 97.9x32.6 / 3.6 | 17 | 72 | BORDER, 1.28 | nothing | edge cap, stage 7 (`edge_cap=bean` cap pieces) | SATIN, 1.6 | a |
| mfab_hat | S091d4ef1 | 4.3x5.1 / 2.5 | 0 | 59 | BORDER, 1.71 | nothing | unsewn / covered | SATIN, 1.51 | a |
| mfab_lc | Sb1779555 | 96.1x36.0 / 6.0 | 1 | 96 | SATIN, 1.77 | 2611 satin, 1025 underlay | satin tier (stage6_satin) on a ring-shaped region | BORDER, 1.86 | b |
| mfab_lc | S03c02d63 | 17.9x16.5 / 6.5 | 1 | 99 | FILL, 0.81 | 700 satin, 64 underlay | satin tier (stage6_satin) on a ring-shaped region | BORDER, 2.2 | b |
| mfab_lc | S181d0b1a | 19.2x16.5 / 7.3 | 0 | 100 | FILL, 0.89 | 702 satin, 48 underlay | satin tier (stage6_satin) | BORDER, 2.02 | b |
| mfab_lc | S6ad1cae7 | 19.2x16.6 / 6.4 | 1 | 100 | FILL, 0.89 | 536 satin, 45 underlay | satin tier (stage6_satin) on a ring-shaped region | BORDER, 2.2 | b |
| mfab_lc | S50968abc | 10.5x16.4 / 6.8 | 0 | 99 | FILL, 1.37 | 290 satin, 22 underlay | satin tier (stage6_satin) | BORDER, 1.8 | b |
| mfab_lc | Sfa7f5274 | 15.8x6.0 / 6.0 | 0 | 100 | FILL, 0.81 | 269 fill, 19 underlay | edge cap (bean ring) | BORDER, 2.13 | b |
| mfab_lc | Sfbae5fe3 | 90.2x30.0 / 3.3 | 17 | 74 | BORDER, 1.22 | nothing | edge cap, stage 7 (`edge_cap=bean` cap pieces) | SATIN, 1.53 | a |
| mfab_lc | S8a9cdd7f | 4.0x4.7 / 2.2 | 0 | 61 | SATIN, 1.66 | nothing | unsewn / covered | BORDER, 1.41 | b |
| precision_drone | S00c2fb94 | 59.8x40.4 / 7.1 | 25 | 68 | FILL, 1.39 | 4824 fill, 304 underlay | edge cap (bean ring) | BORDER, 1.22 | b |
| precision_drone | S0f8c3f10 | 1.8x2.9 / 1.2 | 0 | 33 | OUTLINE | 35 run | run tier (small-shape rescue) | FILL, 1.39 | a |
| precision_drone | Sc839deb3 | 22.1x13.8 / 3.2 | 0 | 42 | FILL, 1.2 | 210 fill, 9 underlay | edge cap (bean ring) | BORDER, 1.33 | b |
| tires_hat_3d | Sdd5f3db3 | 6.5x10.6 / 5.9 | 0 | 92 | RUN | nothing | edge cap (bean ring) | BORDER | b |
| tires_hat_3d | Sf41eecf1 | 7.4x8.0 / 3.6 | 0 | 93 | FILL | nothing | edge cap (bean ring) | BORDER | b |
| tires_hat_3d | S91cf86bf | 5.7x5.5 / 5.4 | 0 | 92 | BORDER, 1.22 | 152 fill, 111 border:border, 18 underlay | stage6_border.border_runs via _border_wanted | SATIN, 2.84 | a |
| bridge_hat | S101206bd | 36.1x36.3 / 8.2 | 13 | 95 | BORDER, 1.63 | 3411 fill, 426 underlay | fill tier (stage6_fill) | FILL, 1.17 | a |
| bridge_hat | S9c1ab3fa | 15.9x4.7 / 3.8 | 0 | 123 | BORDER, 1.57 | 321 fill, 30 underlay | fill tier (stage6_fill) | SATIN, 1.82 | a |
| bridge_hat | S50accdca | 9.5x5.0 / 3.6 | 0 | 118 | BORDER, 1.62 | 205 fill, 20 underlay | fill tier (stage6_fill) | FILL, 1.32 | a |
| bridge_hat | Sb3f2bb76 | 29.8x11.4 / 4.8 | 3 | 95 | BORDER, 1.92 | 625 satin, 224 underlay | satin tier (stage6_satin) on a ring-shaped region | SATIN, 1.55 | a |
| bridge_hat | Sa045b0ab | 4.0x3.8 / 2.3 | 0 | 90 | SATIN, 2.56 | 26 satin | satin tier (stage6_satin) | OUTLINE | b |
| bridge_lc | S3ad11cdb | 43.7x44.0 / 10.0 | 12 | 96 | BORDER, 1.6 | 4611 fill, 247 underlay | fill tier (stage6_fill) | FILL, 1.28 | a |
| bridge_lc | S3caab91b | 19.0x5.9 / 4.6 | 0 | 120 | BORDER, 1.55 | 409 fill, 14 underlay | fill tier (stage6_fill) | FILL, 2.12 | a |
| bridge_lc | Scdbf5033 | 14.4x6.5 / 4.2 | 0 | 119 | BORDER, 1.39 | 349 fill, 16 underlay | fill tier (stage6_fill) | FILL, 2.14 | a |
| bridge_lc | Sf7f6798a | 11.7x6.0 / 4.2 | 0 | 114 | BORDER, 1.49 | 301 fill, 16 underlay | fill tier (stage6_fill) | FILL, 1.43 | a |
| bridge_lc | Sf354aaef | 2.2x2.1 / 2.1 | 0 | 112 | BORDER, 1.21 | 53 fill, 7 underlay | fill tier (stage6_fill) | SATIN, 1.43 | a |
| bridge_lc | S89ca8731 | 1.6x1.9 / 1.3 | 0 | 96 | OUTLINE | 33 run | run tier (small-shape rescue) | SATIN, 1.61 | a |
| bridge_lc | S4fdc326d | 3.4x3.4 / 2.2 | 0 | 94 | BORDER, 0.78 | 67 fill, 7 underlay | fill tier (stage6_fill) | SATIN, 1.0 | a |
| proseal_hat | S5d125db3 | 2.3x2.3 / 2.3 | 0 | 52 | RUN | nothing | unsewn / covered | BORDER, 1.3 | b |
| proseal_hat | S3e794898 | 2.3x2.3 / 2.2 | 0 | 51 | OUTLINE | nothing | unsewn / covered | SATIN, 1.29 | a |
| proseal_hat | Sa257d683 | 3.5x3.8 / 3.4 | 0 | 45 | OUTLINE | 78 fill, 6 underlay | edge cap, stage 7 (`edge_cap=bean` cap pieces) | FILL, 2.73 | a |
| proseal_hat | S24ff7560 | 1.3x1.7 / 1.3 | 0 | 48 | OUTLINE | 22 run | edge cap, stage 7 (`edge_cap=bean` cap pieces) | NONE | a |
| proseal_hat | S1a7a9413 | 1.3x1.3 / 1.3 | 0 | 48 | OUTLINE | 19 run | edge cap, stage 7 (`edge_cap=bean` cap pieces) | NONE | a |
| proseal_hat | S9797a361 | 1.2x1.3 / 1.3 | 0 | 48 | OUTLINE | 19 run | edge cap, stage 7 (`edge_cap=bean` cap pieces) | NONE | a |
| proseal_hat | S3e52274e | 1.2x1.3 / 1.2 | 0 | 48 | OUTLINE | 19 run | edge cap, stage 7 (`edge_cap=bean` cap pieces) | NONE | a |
| proseal_hat | S68217daf | 1.1x1.2 / 1.2 | 0 | 48 | OUTLINE | 20 run | edge cap, stage 7 (`edge_cap=bean` cap pieces) | NONE | a |

## Crops (`docs/renders/border-census-2026-10-23/`)

Each is art | ours | pro at 40 px/mm around one shape, 3 mm of margin.

- `proseal_hat_Sa257d683_a.png`, `proseal_hat_S24ff7560_a.png` - class (a): a bean ring
  round a small filled bubble, and a lone dot ringed where the pro sews nothing.
- `mfab_hat_S02609ac7_b.png` - class (b): the pro's satin keyline round a big shape
  that we sew as one satin ring.
- `hotel_fremont_patch_S10d3c3b0_c.png` - class (c): both ring it, at different widths.

## What to do with it (not done here)

The ProSeal fix and the rule agree: stop the small-shape rings, keep the real borders.
Candidate lever, for Kent's call and the sibling session: gate the edge cap's bean ring
and the run tier's outline on the shape's smallest dimension (about 4 mm), as the pro's
rings follow size. The cut is a judgement from 13 designs of one pro's work, not a
sew-out result, and the big-shape side (we sew satin whole where the pro fills and
borders) is a separate, larger gap this census only points at.
