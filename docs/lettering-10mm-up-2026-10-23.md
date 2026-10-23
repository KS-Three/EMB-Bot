# The 10 mm and up lettering band against the pro (2026-10-23)

The band after `docs/lettering-5-10mm-2026-10-23.md`: letters with a cap
of 10 mm or more, read per letter on both files the same way. Of the
sixteen paired designs (`tools/border_census.py`'s `PAIRS`, the pro's
files in the repo root's `Embroidery Files.zip`), eight have a word in the
band; Fremont, Drone, Proseal, Gaulke and the Bridge LC do not. Everything
is read off DST files: ours written through `tools.pro_pair.digitize` at
the pro's own design width and preset (the Studio's own request,
`tools/border_census.py one SLUG`), his from the zip.

| job (preset, width) | word | cap, ours / pro | pro's construction | ours |
|---|---|---|---|---|
| Becker hat small 76.5 | MARINE | 12.8 / 12.8 | whole satin, 4.0 mm wide | Column lane satin, 4.1-4.5 |
|  | BECKER | 21.5-25.6 | fill under the art's 2.4 mm satin outline | the outline ring sews; the five WHITE faces sew nothing |
| Becker hat large 101.9 | MARINE | 17.1 / 17.1 | whole satin, 5.2 mm wide | Column lane satin, 5.3-5.9, split |
|  | BECKER | 22.9-34.1 | fill, cross underlay, under the outline | faces unsewn |
| Becker left chest large 95.7 | MARINE | 16.1 | whole satin, 4.9-5.1 | Column lane satin, 4.8-5.5, split |
|  | BECKER | 21.5-32.1 | fill under the outline | faces unsewn |
| Becker beanie 79.8 | MARINE | 13.4 | whole satin, 4.0-4.1 | Column lane satin, 4.2-4.7 |
|  | BECKER | 17.9-26.7 | fill under the outline | faces unsewn |
| MFab hat 104.9 | MFAB | 17.9 | black fill (the badge's) under a 2.0 mm WHITE satin keyline | black satin columns, 3.6-4.9; the white keyline web unsewn |
| MFab left chest 96.7 | MFAB | 16.5 | the same | the same |
| Tires hat 3D 114.3 | Tires (script) | 19-33 (x-height ~15) | whole satin, 4.3-4.6 mm, 0.14 mm pitch (puff) | the T and swash satin; "ires" (93 x 25 mm, stroke 4.6) a FILL under a bean edge cap |
| Bridge hat 63.3 | Bridge / Bar (script) | 11.4 / 11.5 | fill under a 1.5 mm satin border / fill bare; cross underlay | satin, 38 and 25 columns, 41 trims |

Not in the band, for the record: Gaulke's two lines are 6-7 mm; Fremont
7.5; Drone 6.3; Proseal 9.4; Bridge's tagline 2 mm.

## How it was read

One scratch reader over both DSTs (`band10.py` in the session's
scratchpad, with `band_measure.py`'s column rules from the 5-10 mm band;
its rules follow so the next person re-measures):

- **Letters** are OUR segmentation's regions (the cache's `ours.json`
  polygons), grouped into words by `text_cluster_id`; the pro's frame is
  `pairframe.register_pair`'s (the census's registration), each polygon
  carried across by it. A word is in the band when its median letter
  height is 10 mm or more. Tires and Bridge carry no text tag (a script is
  one shape), so their shapes were named by id. A stitch is ON a letter
  when it lies inside the polygon grown 0.5 mm (ours) / 0.8 mm (pro).
- **Crosses and columns**: split-satin legs (A->M->B, collinear, both
  over 0.5 mm) are fused back into one cross first, counting the
  penetrations (`pens per cross`: 1 whole, 2+ split); then `band_measure`'s
  rule -- consecutive anti-parallel stitches of like length, two short
  stitches skipped, six make a column. Rails are the cross ends by parity.
- **Construction**: `satin` when 60% of the letter's needle-down thread is
  satin crosses; `fill+border` when a column's spine hugs the outline (mid
  within half its width + 0.6 mm) over half the outline AND dense rows lie
  inside; `fill bare` when dense rows carry 30% of the thread; `run/other`
  (BECKER's white faces: 166-744 mm of a neighbour's travel and edge cap).
- **Fill rows, pitch, stitch, underlay**: `tools/pro_fill_underlay.py`'s
  `analyse_block` over the letter's NON-cross passes -- verdict (CROSS /
  PARALLEL / BARE), the top rows' axial angle, their pitch and median
  stitch, the under-pass's length and share.
- **Cross lean**: each cross's angle from the line of text (0 = the stems'
  horizontal cross), median per letter.
- **Rail wobble**: `tools/letter_band.py`'s polygon-free jitter (a line
  through nine same-rail stations, the middle one's residual), p90 per
  letter, satin columns; `border wobble` the same on the hugging column.
- **Fan ends / ends, butts (gaps)**: as in the 5-10 mm band -- an end whose
  crosses turn over 20 deg from the column's middle; a column end within
  0.8 W of another column's body, a gap when the 0.4 mm thread covers under
  90% of a half-width disc there.
- **Counters open**: each hole of the polygon eroded 0.35 mm; open when the
  file's 0.4 mm thread covers under 40% of it.
- **Word**: trims = needle-up groups beside a run that touches the word;
  needle-up = their jump length; travel = a word run's stitches with
  neither end on a letter; stitches = the word's runs (for BECKER and MFAB
  the pro's badge fill runs under the letters, so his word travel and
  stitch counts there are the badge's, not the letters').

Renders in `docs/renders/lettering-10mm-up-2026-10-23/` (thread renders,
ours above the pro, each in its own frame; `README.md` there lists them).

## The table

Per letter, `ours` over `pro`. Shape ids are our segmentation's
(`tools/border_census.py` cache); widths and heights are the polygon's.

### Becker hat small 76.5: MARINE (6 shapes, cap 12.8 mm)

Word: trims 9 / 3; needle-up 99.6 / 117.1 mm; travel on the word 0.0 / 0.0 mm; stitches 2036 / 2170 (ours / pro).

| shape | side | construction | cols | pens per cross | split share | cross lean deg | fan ends / ends | butts (gaps) | satin width | rail wobble p90 | border width / outline cover | border wobble p90 | fill: underlay / angle / row pitch / stitch | fill underlay | counters open |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Sd13db8a7 13.7x12.8  ours | satin | 5 | 1 | 0.48 | 5 | 6/10 | 8 (4) | 4.32 | 0.211 | 2.21 / 0.18 | 0.300 | - | non-cross thread 94 mm | - |
|   pro | satin | 11 | 1 | 0.03 | 5 | 10/22 | 22 (9) | 4.02 | 0.038 | 4.10 / 0.41 | 0.000 | - | non-cross thread 294 mm | - |
| S3952fead 12.6x12.8  ours | satin | 3 | 1 | 0.40 | 15 | 1/6 | 4 (2) | 4.05 | 0.269 | 3.65 / 0.20 | 0.333 | - | non-cross thread 68 mm | 1/1 |
|   pro | satin | 9 | 1 | 0.03 | 16 | 9/18 | 18 (6) | 4.02 | 0.173 | 4.22 / 0.41 | 0.034 | - | non-cross thread 164 mm | 0/1 |
| S9c56de23 11.3x12.8  ours | satin | 2 | 2 | 0.97 | 17 | 3/4 | 2 (1) | 4.53 | 0.319 | 4.54 / 0.72 | 0.340 | - | non-cross thread 69 mm | 1/1 |
|   pro | satin | 8 | 1 | 0.04 | 35 | 7/16 | 16 (5) | 3.96 | 0.205 | - | - | - | non-cross thread 182 mm | 1/1 |
| S793fbe32 4.5x12.8  ours | satin | 1 | 2 | 0.98 | 2 | 0/2 | 0 (0) | 4.42 | 0.113 | 4.42 / 1.00 | 0.113 | - | non-cross thread 32 mm | - |
|   pro | satin | 2 | 1 | 0.02 | 10 | 3/4 | 4 (4) | 4.00 | 0.224 | - | - | - | non-cross thread 26 mm | - |
| S886362a5 12.2x12.8  ours | satin | 3 | 2 | 0.99 | 7 | 5/6 | 4 (1) | 4.60 | 0.173 | 4.30 / 0.34 | 0.146 | - | non-cross thread 85 mm | - |
|   pro | satin | 7 | 1 | 0.01 | 6 | 6/14 | 14 (8) | 4.10 | 0.225 | - | - | - | non-cross thread 186 mm | - |
| Se08e8496 9.8x12.8  ours | satin | 4 | 2 | 0.54 | 82 | 2/8 | 6 (2) | 4.11 | 0.263 | 3.32 / 0.26 | 0.073 | - | non-cross thread 69 mm | - |
|   pro | satin | 7 | 1 | 0.01 | 76 | 7/14 | 13 (6) | 4.00 | 0.218 | - | - | - | non-cross thread 8 mm | - |

### Becker hat small 76.5: BECKER (5 shapes, cap 21.5 mm)

Word: trims 10 / 7; needle-up 178.6 / 222.5 mm; travel on the word 1123.4 / 991.7 mm; stitches 3892 / 6524 (ours / pro).

| shape | side | construction | cols | pens per cross | split share | cross lean deg | fan ends / ends | butts (gaps) | satin width | rail wobble p90 | border width / outline cover | border wobble p90 | fill: underlay / angle / row pitch / stitch | fill underlay | counters open |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1c041c47 14.2x24.9  ours | run/other | 1 | 1 | 0.00 | 83 | 0/2 | 0 (0) | 0.81 | - | 3.42 / 0.18 | 0.340 | - | non-cross thread 345 mm | 0/2 |
|   pro | fill bare | 4 | 1 | 0.34 | 31 | 2/8 | 5 (0) | 1.89 | 0.713 | 3.51 / 0.18 | 0.136 | CROSS / 22 deg / 0.16 / 3.45 | CROSS 204 mm (22%) | 0/2 |
| Sc32ce326 20.5x21.5  ours | run/other | 0 | - | - | - | - | - | - | - | 1.77 / 0.02 | 0.462 | - | - | - |
|   pro | fill bare | 11 | 1 | 0.23 | 23 | 5/22 | 15 (0) | 1.94 | 0.187 | - | - | CROSS / 22 deg / 0.18 / 3.47 | CROSS 199 mm (22%) | - |
| Se1db73b6 12.5x17.2  ours | run/other | 0 | - | - | - | - | - | - | - | 2.43 / 0.24 | 0.210 | - | - | - |
|   pro | fill bare | 5 | 1 | 0.07 | 10 | 3/10 | 8 (0) | 1.73 | 0.084 | 3.05 / 0.07 | - | CROSS / 22 deg / 0.16 / 3.45 | CROSS 94 mm (18%) | - |
| Sa0252bdc 10.1x19.9  ours | run/other | 0 | - | - | - | - | - | - | - | - | - | - | - | - |
|   pro | fill bare | 5 | 1 | 0.00 | 26 | 8/10 | 4 (0) | 2.14 | 0.389 | - | - | CROSS / 22 deg / 0.16 / 3.50 | CROSS 101 mm (18%) | - |
| S466091d1 14.8x25.6  ours | run/other | 0 | - | - | - | - | - | - | - | 2.79 / 0.14 | 0.326 | - | - | 0/1 |
|   pro | fill bare | 6 | 1 | 0.03 | 21 | 4/12 | 11 (1) | 1.96 | 0.344 | 9.27 / 0.20 | - | CROSS / 22 deg / 0.16 / 3.45 | CROSS 196 mm (19%) | 0/1 |

### Becker hat large 101.9: MARINE (6 shapes, cap 17.1 mm)

Word: trims 8 / 4; needle-up 104.1 / 177.9 mm; travel on the word 0.0 / 13.6 mm; stitches 3264 / 2639 (ours / pro).

| shape | side | construction | cols | pens per cross | split share | cross lean deg | fan ends / ends | butts (gaps) | satin width | rail wobble p90 | border width / outline cover | border wobble p90 | fill: underlay / angle / row pitch / stitch | fill underlay | counters open |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Se264484b 18.2x17.1  ours | satin | 4 | 2 | 0.68 | 4 | 4/8 | 6 (3) | 5.60 | 0.185 | 5.80 / 0.44 | 0.100 | - | non-cross thread 112 mm | - |
|   pro | satin | 11 | 1 | 0.01 | 4 | 6/22 | 22 (11) | 5.21 | 0.025 | 5.20 / 0.41 | 0.000 | - | non-cross thread 84 mm | - |
| Sff923e8d 16.8x17.1  ours | satin | 3 | 2 | 0.88 | 16 | 3/6 | 5 (3) | 5.28 | 0.282 | 4.54 / 0.18 | 0.430 | - | non-cross thread 99 mm | 1/1 |
|   pro | satin | 7 | 1 | 0.01 | 14 | 4/14 | 14 (6) | 5.27 | 0.165 | 5.41 / 0.37 | 0.044 | - | non-cross thread -124 mm | 1/1 |
| S82f28c31 15.0x17.1  ours | satin | 3 | 2 | 0.96 | 14 | 5/6 | 5 (3) | 5.90 | 0.255 | 6.12 / 0.67 | 0.263 | - | non-cross thread 135 mm | 1/1 |
|   pro | satin | 7 | 1 | 0.00 | 26 | 1/14 | 14 (6) | 5.20 | 0.184 | - | - | - | non-cross thread -246 mm | 1/1 |
| S9059f9a2 6.0x17.1  ours | satin | 1 | 2 | 0.99 | 1 | 0/2 | 0 (0) | 5.61 | 0.082 | 5.61 / 1.00 | 0.082 | - | non-cross thread 41 mm | - |
|   pro | satin | 2 | 1 | 0.00 | 9 | 4/4 | 4 (4) | 5.20 | 0.198 | - | - | - | non-cross thread -86 mm | - |
| S1365beb6 16.2x17.1  ours | satin | 3 | 2 | 1.00 | 4 | 3/6 | 3 (1) | 5.81 | 0.213 | 5.71 / 0.35 | 0.216 | - | non-cross thread 112 mm | - |
|   pro | satin | 6 | 1 | 0.01 | 4 | 5/12 | 12 (9) | 5.21 | 0.195 | - | - | - | non-cross thread 56 mm | - |
| Sa42b7e5b 13.1x17.1  ours | satin | 4 | 2 | 0.75 | 81 | 2/8 | 6 (3) | 5.32 | 0.226 | 4.22 / 0.23 | 0.044 | - | non-cross thread 100 mm | - |
|   pro | satin | 6 | 1 | 0.00 | 77 | 4/12 | 12 (8) | 5.12 | 0.194 | - | - | - | non-cross thread -244 mm | - |

### Becker hat large 101.9: BECKER (5 shapes, cap 28.5 mm)

Word: trims 22 / 7; needle-up 366.9 / 296.1 mm; travel on the word 2494.3 / 3002.8 mm; stitches 6147 / 9717 (ours / pro).

| shape | side | construction | cols | pens per cross | split share | cross lean deg | fan ends / ends | butts (gaps) | satin width | rail wobble p90 | border width / outline cover | border wobble p90 | fill: underlay / angle / row pitch / stitch | fill underlay | counters open |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Sd6d16b15 19.0x33.3  ours | run/other | 1 | 1 | 0.43 | 68 | 0/2 | 0 (0) | 1.86 | - | 4.31 / 0.18 | 0.304 | - | non-cross thread 194 mm | 0/2 |
|   pro | fill bare | 2 | 1 | 0.21 | 59 | 2/4 | 0 (0) | 2.28 | 0.786 | 4.60 / 0.18 | 0.110 | CROSS / 22 deg / 0.16 / 3.45 | CROSS 259 mm (17%) | 0/2 |
| S9b51aba1 27.4x28.5  ours | run/other | 2 | 1 | 0.00 | 45 | 0/4 | 0 (0) | 0.78 | - | 2.25 / 0.07 | 0.231 | - | non-cross thread 600 mm | - |
|   pro | fill bare | 5 | 1 | 0.44 | 29 | 2/10 | 1 (0) | 2.33 | 0.043 | - | - | CROSS / 22 deg / 0.17 / 3.45 | CROSS 242 mm (15%) | - |
| S030953b8 16.6x22.9  ours | run/other | 1 | 1 | 0.00 | 8 | 2/2 | 0 (0) | 0.71 | 0.073 | 2.52 / 0.10 | 0.357 | - | non-cross thread 366 mm | - |
|   pro | fill bare | 5 | 1 | 0.11 | 12 | 1/10 | 6 (0) | 2.28 | 0.112 | - | - | CROSS / 22 deg / 0.16 / 3.49 | CROSS 184 mm (19%) | - |
| S780cc713 13.5x26.5  ours | run/other | 2 | 1 | 0.00 | 12 | 4/4 | 0 (0) | 0.72 | 0.095 | 2.65 / 0.12 | 0.452 | - | non-cross thread 192 mm | - |
|   pro | fill bare | 5 | 1 | 0.00 | 48 | 10/10 | 7 (0) | 2.28 | 0.373 | - | - | CROSS / 22 deg / 0.16 / 3.50 | CROSS 98 mm (9%) | - |
| Sb7019eaf 19.7x34.1  ours | run/other | 0 | - | - | - | - | - | - | - | 3.27 / 0.38 | 0.309 | - | - | 0/1 |
|   pro | fill bare | 1 | 2 | 1.00 | 23 | 0/2 | 0 (0) | 6.42 | - | 3.60 / 0.19 | 0.161 | CROSS / 22 deg / 0.15 / 3.45 | CROSS 294 mm (16%) | 0/1 |

### Becker left chest large 95.7: MARINE (6 shapes, cap 16.1 mm)

Word: trims 8 / 5; needle-up 63.5 / 141.8 mm; travel on the word 0.0 / 0.0 mm; stitches 2991 / 2496 (ours / pro).

| shape | side | construction | cols | pens per cross | split share | cross lean deg | fan ends / ends | butts (gaps) | satin width | rail wobble p90 | border width / outline cover | border wobble p90 | fill: underlay / angle / row pitch / stitch | fill underlay | counters open |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S32b446a3 17.2x16.1  ours | satin | 7 | 2 | 0.78 | 42 | 7/14 | 12 (2) | 5.12 | 0.251 | - | - | - | non-cross thread 147 mm | - |
|   pro | satin | 10 | 1 | 0.01 | 4 | 5/20 | 20 (9) | 5.00 | 0.032 | 4.90 / 0.41 | 0.000 | - | non-cross thread 122 mm | - |
| Sbf7cf86a 15.8x16.1  ours | satin | 3 | 2 | 0.78 | 15 | 2/6 | 6 (3) | 4.85 | 0.249 | 3.59 / 0.17 | 0.373 | - | non-cross thread 91 mm | 1/1 |
|   pro | satin | 6 | 1 | 0.01 | 17 | 5/12 | 12 (6) | 5.10 | 0.108 | - | - | - | non-cross thread -84 mm | 1/1 |
| Sa1103fec 14.1x16.1  ours | satin | 3 | 2 | 0.99 | 5 | 3/6 | 4 (2) | 5.51 | 0.217 | 5.57 / 0.58 | 0.229 | - | non-cross thread 92 mm | 1/1 |
|   pro | satin | 6 | 1 | 0.01 | 27 | 3/12 | 12 (6) | 4.91 | 0.222 | 5.00 / 0.35 | 0.000 | - | non-cross thread -298 mm | 1/1 |
| S1a1d6bde 5.7x16.0  ours | satin | 1 | 2 | 0.99 | 2 | 0/2 | 0 (0) | 5.22 | 0.088 | 5.22 / 1.00 | 0.088 | - | non-cross thread 39 mm | - |
|   pro | satin | 2 | 1 | 0.00 | 10 | 4/4 | 4 (4) | 4.90 | 0.190 | - | - | - | non-cross thread -79 mm | - |
| S64bc1dbe 15.2x16.1  ours | satin | 4 | 2 | 0.99 | 6 | 4/8 | 6 (2) | 5.37 | 0.145 | 5.40 / 0.47 | 0.099 | - | non-cross thread 111 mm | - |
|   pro | satin | 6 | 1 | 0.01 | 5 | 4/12 | 12 (8) | 4.91 | 0.200 | 5.20 / 0.31 | 0.000 | - | non-cross thread 91 mm | - |
| S9e70ec80 12.3x16.0  ours | satin | 4 | 2 | 0.74 | 82 | 4/8 | 7 (3) | 4.80 | 0.212 | 3.81 / 0.23 | 0.044 | - | non-cross thread 84 mm | - |
|   pro | satin | 6 | 1 | 0.00 | 77 | 5/12 | 12 (8) | 4.82 | 0.215 | - | - | - | non-cross thread -149 mm | - |

### Becker left chest large 95.7: BECKER (5 shapes, cap 26.9 mm)

Word: trims 21 / 6; needle-up 317.1 / 279.0 mm; travel on the word 1995.8 / 2167.0 mm; stitches 5052 / 8778 (ours / pro).

| shape | side | construction | cols | pens per cross | split share | cross lean deg | fan ends / ends | butts (gaps) | satin width | rail wobble p90 | border width / outline cover | border wobble p90 | fill: underlay / angle / row pitch / stitch | fill underlay | counters open |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S7d68682c 17.8x31.3  ours | run/other | 1 | 1 | 0.00 | 90 | 2/2 | 0 (0) | 0.50 | - | 3.98 / 0.18 | 0.270 | - | non-cross thread 390 mm | 0/2 |
|   pro | fill bare | 2 | 3 | 0.92 | 22 | 0/4 | 4 (0) | 10.45 | - | 4.40 / 0.18 | 0.136 | CROSS / 22 deg / 0.15 / 3.45 | CROSS 240 mm (18%) | 0/2 |
| Sef4e6850 25.7x26.9  ours | run/other | 2 | 1 | 0.00 | 45 | 0/4 | 0 (0) | 0.71 | - | - | - | - | non-cross thread 660 mm | - |
|   pro | fill bare | 5 | 1 | 0.15 | 21 | 5/10 | 8 (0) | 2.19 | 0.070 | - | - | CROSS / 22 deg / 0.16 / 3.45 | CROSS 251 mm (18%) | - |
| S9abe3aa7 15.6x21.5  ours | run/other | 1 | 1 | 0.00 | 34 | 2/2 | 0 (0) | 0.81 | 0.072 | 4.44 / 0.20 | 0.201 | - | non-cross thread 277 mm | - |
|   pro | fill bare | 7 | 1 | 0.07 | 10 | 4/14 | 12 (0) | 2.10 | 0.086 | - | - | CROSS / 22 deg / 0.15 / 3.45 | CROSS 147 mm (15%) | - |
| S5be3de64 12.7x24.9  ours | run/other | 0 | - | - | - | - | - | - | - | - | - | - | - | - |
|   pro | fill bare | 5 | 1 | 0.00 | 50 | 9/10 | 6 (0) | 2.22 | 0.343 | - | - | CROSS / 22 deg / 0.15 / 3.50 | CROSS 133 mm (15%) | - |
| Sb59612cb 18.5x32.1  ours | run/other | 0 | - | - | - | - | - | - | - | 2.98 / 0.28 | 0.298 | - | - | 0/1 |
|   pro | fill bare | 3 | 1 | 0.31 | 12 | 1/6 | 0 (0) | 1.93 | 0.231 | 3.42 / 0.18 | 0.162 | CROSS / 22 deg / 0.15 / 3.45 | CROSS 298 mm (20%) | 0/1 |

### Becker beanie 79.8: MARINE (6 shapes, cap 13.4 mm)

Word: trims 9 / 4; needle-up 181.1 / 171.0 mm; travel on the word 5955.1 / 5130.2 mm; stitches 4863 / 4574 (ours / pro).

| shape | side | construction | cols | pens per cross | split share | cross lean deg | fan ends / ends | butts (gaps) | satin width | rail wobble p90 | border width / outline cover | border wobble p90 | fill: underlay / angle / row pitch / stitch | fill underlay | counters open |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Saee8fbe5 14.3x13.4  ours | satin | 5 | 1 | 0.44 | 13 | 5/10 | 8 (0) | 4.40 | 0.233 | 4.42 / 0.43 | 0.187 | BARE / 117 deg / 0.48 / 3.47 | BARE 0 mm (0%) | - |
|   pro | satin | 11 | 1 | 0.03 | 4 | 6/22 | 22 (0) | 4.00 | 0.047 | - | - | BARE / 155 deg / 0.50 / 3.48 | BARE 0 mm (0%) | - |
| Sff8aab95 13.1x13.4  ours | satin | 4 | 1 | 0.42 | 20 | 5/8 | 6 (0) | 4.16 | 0.347 | 3.86 / 0.15 | 0.068 | BARE / 118 deg / 0.48 / 3.47 | BARE 0 mm (0%) | 0/1 |
|   pro | satin | 9 | 1 | 0.03 | 16 | 8/18 | 18 (0) | 4.10 | 0.166 | 4.22 / 0.45 | 0.051 | BARE / 158 deg / 0.49 / 3.50 | BARE 0 mm (0%) | 0/1 |
| S3a506002 11.7x13.4  ours | satin | 2 | 2 | 0.94 | 13 | 3/4 | 2 (0) | 4.66 | 0.293 | - | - | BARE / 119 deg / 0.47 / 3.49 | BARE 0 mm (0%) | 0/1 |
|   pro | satin | 8 | 1 | 0.03 | 34 | 8/16 | 16 (0) | 4.00 | 0.193 | - | - | BARE / 158 deg / 0.50 / 3.50 | BARE 0 mm (0%) | 0/1 |
| Sfac22dc3 4.7x13.4  ours | satin | 1 | 2 | 0.99 | 2 | 0/2 | 0 (0) | 4.52 | 0.087 | 4.52 / 1.00 | 0.087 | BARE / 114 deg / 0.48 / 3.49 | BARE 0 mm (0%) | - |
|   pro | satin | 2 | 1 | 0.00 | 10 | 3/4 | 4 (0) | 4.10 | 0.189 | - | - | - | non-cross thread -7 mm | - |
| Sf795e8d1 12.7x13.4  ours | satin | 3 | 2 | 0.96 | 8 | 3/6 | 3 (0) | 4.60 | 0.186 | 4.32 / 0.34 | 0.204 | BARE / 116 deg / 0.49 / 3.49 | BARE 0 mm (0%) | - |
|   pro | satin | 7 | 1 | 0.01 | 5 | 6/14 | 14 (0) | 4.01 | 0.194 | - | - | BARE / 159 deg / 0.50 / 3.45 | BARE 0 mm (0%) | - |
| S714b55d9 10.2x13.4  ours | satin | 4 | 2 | 0.59 | 76 | 2/8 | 5 (0) | 4.45 | 0.211 | 3.51 / 0.46 | 0.234 | BARE / 124 deg / 0.48 / 3.49 | BARE 0 mm (0%) | - |
|   pro | satin | 7 | 1 | 0.01 | 76 | 8/14 | 13 (0) | 4.00 | 0.222 | - | - | BARE / 157 deg / 0.49 / 3.52 | BARE 0 mm (0%) | - |

### Becker beanie 79.8: BECKER (5 shapes, cap 22.3 mm)

Word: trims 21 / 8; needle-up 432.9 / 276.4 mm; travel on the word 6306.7 / 4801.6 mm; stitches 6629 / 9179 (ours / pro).

| shape | side | construction | cols | pens per cross | split share | cross lean deg | fan ends / ends | butts (gaps) | satin width | rail wobble p90 | border width / outline cover | border wobble p90 | fill: underlay / angle / row pitch / stitch | fill underlay | counters open |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S51503c0c 14.8x25.9  ours | fill bare | 1 | 1 | 0.00 | 51 | 0/2 | 0 (0) | 1.42 | - | 3.04 / 0.32 | 0.287 | BARE / 124 deg / 0.49 / 3.49 | BARE 0 mm (0%) | 0/2 |
|   pro | fill bare | 5 | 2 | 0.62 | 23 | 1/10 | 8 (0) | 6.66 | 0.707 | 3.51 / 0.18 | 0.155 | BARE / 12 deg / 0.16 / 3.45 | BARE 11 mm (1%) | 0/2 |
| S19262c07 21.4x22.3  ours | run/other | 0 | - | - | - | - | - | - | - | 2.55 / 0.07 | - | BARE / 124 deg / 0.49 / 3.49 | BARE 0 mm (0%) | - |
|   pro | fill bare | 14 | 1 | 0.36 | 22 | 6/28 | 21 (0) | 2.02 | 0.182 | - | - | BARE / 11 deg / 0.17 / 3.49 | BARE 0 mm (0%) | - |
| S4bb149e1 13.0x17.9  ours | fill bare | 0 | - | - | - | - | - | - | - | 2.31 / 0.28 | 0.209 | BARE / 124 deg / 0.49 / 3.49 | BARE 0 mm (0%) | - |
|   pro | fill bare | 8 | 1 | 0.14 | 12 | 3/16 | 15 (0) | 1.80 | 0.099 | 5.70 / 0.10 | - | BARE / 13 deg / 0.16 / 3.47 | BARE 0 mm (0%) | - |
| S559c0f2e 10.6x20.7  ours | fill bare | 0 | - | - | - | - | - | - | - | - | - | BARE / 124 deg / 0.48 / 3.49 | BARE 0 mm (0%) | - |
|   pro | fill bare | 3 | 1 | 0.00 | 27 | 5/6 | 1 (0) | 1.77 | 0.405 | - | - | BARE / 15 deg / 0.16 / 3.50 | BARE 7 mm (1%) | - |
| S6399ecd4 15.4x26.7  ours | fill bare | 0 | - | - | - | - | - | - | - | 2.34 / 0.23 | 0.337 | BARE / 124 deg / 0.49 / 3.49 | BARE 0 mm (0%) | 0/1 |
|   pro | fill bare | 4 | 1 | 0.31 | 22 | 2/8 | 1 (0) | 1.71 | 0.875 | 2.81 / 0.17 | 0.156 | BARE / 14 deg / 0.16 / 3.47 | BARE 0 mm (0%) | 0/1 |

### MFab hat 104.9: MFAB (4 shapes, cap 17.9 mm)

Word: trims 31 / 9; needle-up 340.7 / 264.3 mm; travel on the word 349.7 / 22235.7 mm; stitches 4267 / 15879 (ours / pro).

| shape | side | construction | cols | pens per cross | split share | cross lean deg | fan ends / ends | butts (gaps) | satin width | rail wobble p90 | border width / outline cover | border wobble p90 | fill: underlay / angle / row pitch / stitch | fill underlay | counters open |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Sfb63bcf2 20.9x17.9  ours | satin | 8 | 2 | 0.62 | 35 | 12/16 | 14 (7) | 4.82 | 0.197 | 1.10 / 0.10 | 0.044 | - | non-cross thread 38 mm | - |
|   pro | fill bare | 5 | 1 | 0.01 | 21 | 10/10 | 7 (0) | 2.05 | 0.274 | - | - | CROSS / 22 deg / 0.17 / 3.50 | CROSS 348 mm (28%) | - |
| S384bf43b 11.3x17.8  ours | satin | 6 | 2 | 0.53 | 20 | 8/12 | 12 (5) | 3.61 | 0.319 | 3.90 / 0.31 | 0.283 | - | non-cross thread 26 mm | - |
|   pro | fill bare | 2 | 1 | 0.00 | 49 | 3/4 | 0 (0) | 1.89 | 0.033 | - | - | CROSS / 21 deg / 0.17 / 3.50 | CROSS 108 mm (24%) | - |
| Sc4d2fcb1 20.9x18.0  ours | satin | 6 | 2 | 0.62 | 51 | 8/12 | 12 (3) | 4.10 | 0.172 | 1.02 / 0.11 | 0.055 | - | non-cross thread 11 mm | 1/1 |
|   pro | fill bare | 2 | 1 | 0.02 | 10 | 3/4 | 0 (0) | 2.40 | 0.061 | - | - | CROSS / 22 deg / 0.17 / 3.49 | CROSS 199 mm (15%) | 0/1 |
| S02609ac7 19.5x17.9  ours | satin | 8 | 2 | 0.59 | 76 | 7/16 | 15 (9) | 4.90 | 0.199 | 5.00 / 0.82 | 0.175 | - | non-cross thread 35 mm | 1/1 |
|   pro | fill bare | 4 | 1 | 0.04 | 42 | 2/8 | 5 (0) | 2.70 | 0.050 | - | - | CROSS / 22 deg / 0.17 / 3.49 | CROSS 340 mm (19%) | 0/1 |

### MFab left chest 96.7: MFAB (4 shapes, cap 16.5 mm)

Word: trims 28 / 10; needle-up 212.6 / 261.6 mm; travel on the word 78.6 / 21049.2 mm; stitches 3582 / 15768 (ours / pro).

| shape | side | construction | cols | pens per cross | split share | cross lean deg | fan ends / ends | butts (gaps) | satin width | rail wobble p90 | border width / outline cover | border wobble p90 | fill: underlay / angle / row pitch / stitch | fill underlay | counters open |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S181d0b1a 19.2x16.5  ours | satin | 8 | 2 | 0.60 | 35 | 11/16 | 15 (5) | 4.23 | 0.213 | 0.80 / 0.10 | 0.035 | BARE / 73 deg / 0.00 / 2.50 | BARE 0 mm (0%) | - |
|   pro | fill bare | 5 | 1 | 0.06 | 20 | 7/10 | 7 (0) | 2.02 | 0.147 | - | - | CROSS / 22 deg / 0.17 / 3.49 | CROSS 287 mm (30%) | - |
| S50968abc 10.5x16.4  ours | satin | 7 | 2 | 0.58 | 27 | 8/14 | 13 (4) | 3.70 | 0.231 | 3.45 / 0.35 | 0.228 | - | non-cross thread 97 mm | - |
|   pro | fill bare | 2 | 1 | 0.00 | 28 | 3/4 | 0 (0) | 1.75 | 0.036 | - | - | CROSS / 21 deg / 0.16 / 3.50 | CROSS 94 mm (27%) | - |
| S6ad1cae7 19.2x16.6  ours | satin | 7 | 1 | 0.46 | 51 | 9/14 | 13 (4) | 3.61 | 0.158 | - | - | BARE / 111 deg / 0.02 / 2.36 | BARE 0 mm (0%) | 1/1 |
|   pro | fill bare | 4 | 1 | 0.02 | 30 | 5/8 | 3 (0) | 2.22 | 0.058 | - | - | CROSS / 22 deg / 0.16 / 3.49 | CROSS 230 mm (21%) | 0/1 |
| S03c02d63 17.9x16.5  ours | satin | 9 | 2 | 0.52 | 78 | 8/18 | 18 (10) | 4.02 | 0.208 | 1.74 / 0.28 | 0.244 | BARE / 4 deg / 0.01 / 2.51 | BARE 0 mm (0%) | 1/1 |
|   pro | fill bare | 3 | 1 | 0.04 | 44 | 1/6 | 2 (0) | 2.62 | 0.047 | - | - | CROSS / 22 deg / 0.17 / 3.49 | CROSS 331 mm (21%) | 0/1 |

### Tires hat 3D 114.3: script (3 shapes, cap 24.6 mm)

Word: trims 10 / 9; needle-up 272.0 / 248.0 mm; travel on the word 0.0 / 329.9 mm; stitches 7793 / 5548 (ours / pro).

| shape | side | construction | cols | pens per cross | split share | cross lean deg | fan ends / ends | butts (gaps) | satin width | rail wobble p90 | border width / outline cover | border wobble p90 | fill: underlay / angle / row pitch / stitch | fill underlay | counters open |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S667dbd3b 65.0x19.4  ours | satin | 1 | 2 | 0.97 | 77 | 2/2 | 0 (0) | 4.92 | 0.265 | 4.92 / 1.00 | 0.265 | - | non-cross thread 91 mm | - |
|   pro | satin | 1 | 1 | 0.00 | 76 | 2/2 | 0 (0) | 4.25 | 0.048 | 4.25 / 1.00 | 0.048 | - | non-cross thread 89 mm | - |
| Sdab4587a 31.7x32.7  ours | satin | 1 | 2 | 0.94 | 35 | 1/2 | 0 (0) | 4.97 | 0.245 | 4.97 / 1.00 | 0.245 | - | non-cross thread 52 mm | - |
|   pro | satin | 1 | 1 | 0.00 | 34 | 1/2 | 0 (0) | 4.63 | 0.049 | 4.63 / 1.00 | 0.049 | - | non-cross thread 51 mm | - |
| S396ab4ae 93.2x24.6  ours | fill+border | 12 | 3 | 0.98 | 45 | 4/24 | 8 (5) | 6.22 | 0.178 | 6.22 / 0.60 | 0.178 | PARALLEL / 135 deg / 0.14 / 2.97 | PARALLEL 52 mm (4%) | 2/2 |
|   pro | satin | 6 | 1 | 0.00 | 44 | 9/12 | 6 (2) | 4.33 | 0.051 | 4.33 / 1.00 | 0.051 | BARE / 130 deg / 0.09 / 1.95 | BARE 0 mm (0%) | 2/2 |

### Bridge hat 63.3: script (2 shapes, cap 11.5 mm)

Word: trims 41 / 6; needle-up 397.8 / 132.8 mm; travel on the word 4472.5 / 5561.0 mm; stitches 6731 / 5104 (ours / pro).

| shape | side | construction | cols | pens per cross | split share | cross lean deg | fan ends / ends | butts (gaps) | satin width | rail wobble p90 | border width / outline cover | border wobble p90 | fill: underlay / angle / row pitch / stitch | fill underlay | counters open |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Sb3f2bb76 29.8x11.4  ours | satin | 38 | 1 | 0.12 | 56 | 48/76 | 72 (0) | 2.14 | 0.403 | 2.15 / 0.96 | 0.403 | - | non-cross thread 676 mm | 0/3 |
|   pro | fill+border | 14 | 1 | 0.01 | 36 | 25/28 | 14 (0) | 1.51 | 0.263 | 1.50 / 0.92 | 0.263 | CROSS / 0 deg / 0.20 / 3.50 | CROSS 64 mm (6%) | 0/3 |
| Sc4c11440 22.8x11.5  ours | satin | 25 | 1 | 0.06 | 63 | 26/50 | 50 (0) | 1.58 | 0.267 | 1.62 / 1.00 | 0.267 | - | non-cross thread 549 mm | 0/3 |
|   pro | fill bare | 9 | 1 | 0.00 | 48 | 13/18 | 13 (0) | 1.62 | 0.113 | 1.70 / 0.48 | 0.113 | CROSS / 0 deg / 0.20 / 3.50 | CROSS 84 mm (18%) | 0/3 |

## What the table says

**Only one word in the band is sewn in full on both sides: MARINE**, four
times (hat small 76.5, hat large 101.9, left chest 95.7, beanie 79.8), the
pro as whole satin 4.0-5.2 mm wide, ours through the Column lane
(`lettering_columns`, ON since 2026-10-12). Totals over the 24 letters:

| MARINE, four files | ours | pro |
|---|---|---|
| columns | 77 | 163 |
| fan ends / ends | 72 / 154 | 131 / 326 |
| junction butts (gaps) | 108 (35) | 324 (123) |
| penetrations per cross, share split | 2 on 0.91 of crosses | 1 (0.01) |
| sewn width, median of letter medians | 4.73 mm | 4.46 mm |
| rail wobble p90, median of letters | 0.215 mm | 0.194 mm |
| word trims | 34 | 16 |
| word stitches | 13,154 | 11,879 |

- **Width** is the pro's plus the pull: 4.3-4.6 against 4.0 at 76.5 mm,
  5.3-5.9 against 5.2 at 101.9 (gate 1, not touched).
- **Construction count**: the pro cuts MORE pieces than we do (163 columns
  to 77, three butts to our one) and fans more ends (40% to 47%) -- his
  M alone is 11 columns. By the 5-10 mm band's instruments ours is the
  cleaner construction; the eye says otherwise, and the paths render says
  why (below).
- **Split crosses**: the pro sews a 4.0 mm cross whole and a 5.2 mm cross
  whole (p99 6.2 in his LC file, `machine.py`); ours puts a second
  penetration in 91% of MARINE's crosses -- `SPLIT_SATIN_ABOVE_MM` 5.0 plus
  the comb's carry down a column once one leg passes it. A stitch-length
  ceiling is cloth (gate 1); listed below, not built.
- **Rail wobble**: level overall (0.215 vs 0.194 p90), except the M's
  straight stems: ours 0.19-0.25, his 0.03-0.05 -- our rails are stretches
  of a 0.52 mm/px upload's traced outline; his are drawn lines. The
  letterform-priors lane's problem, not this band's.
- **Trims**: 34 to 16. He sews M-A-R-I-N-E with 3-5 trims a word, jumping
  between letters uncut (the 16 mm float rule, `pro-trim-threshold`); ours
  trims every jump over 3 mm. The trim-economy lane's.
- **Counters**: open on both sides everywhere (A, R; MFAB's A and B).
- **Underlay**: both centre-run under the columns; the pro also walks an
  edge run (his non-cross thread is 160-300 mm a letter at 76.5 against
  our 70-95).

**BECKER (five letters, four files) and MFAB (four, two files) are not a
construction comparison on today's engine**: the BECKER faces are WHITE in
the art (black outline, black drop shadow) and sew nothing; the MFAB
letters are black on the black badge, drawn by a 0.7 mm white keyline that
sews nothing. The pro sews the BECKER faces as a 22 deg tatami at 0.15-0.17
mm pitch, 3.45 mm stitches, under a CROSS pass of 15-20% of the fill
(`fill_underlay_cross`, #1033, OFF), with the art's 2.4 mm outline as the
satin border; he sews MFab's badge as one black fill and widens the keyline
to a 2.0 mm white satin (border wobble p90 0.03-0.27). Both are
`sew_enclosed_white` (#1031, OFF; the `white-like-pro` lane): rule R11,
"hollow letters, white letters and keylines". Our black MFAB columns on the
black badge (31 trims, 24 gaps, 35 fan ends against his 9 / 0 / 18) are
thread the pro does not sew at all.

**The border-by-size reading of this band is corrected here.** The
2026-10-23 border memo read the pro's bordered letters (BECKER, MFAB) as
"stroke over the satin ceiling, hence fill + border". Measured by the
skeleton (2 x the mean distance-transform half-width), MFAB's strokes are
4.3-5.2 mm and MARINE's at 101.9 are 4.2-5.3 -- the same -- and he satins
MARINE whole. What separates his bordered letters is the ART: both carry
an outline or keyline around the face, and the border IS that outline,
sewn at 2.0-2.5 mm whatever the art drew it at. Bridge's script (11.4 mm,
stroke 2.35, no keyline) is the one bordered letter without one: fill
under a 1.5 mm satin ring. So "fill + border for lettering" is a keyline
rule first, and a stroke rule only on the evidence of one script.

**Tires**: the pro sews the whole script as 4.3-4.6 mm satin at a 0.14 mm
rail pitch (3D puff); ours satins the T and the swash and FILLS "ires" (93
x 25 mm, stroke 4.6, over `SATIN_MAX_WIDTH_MM` 5.0 once pulled) under a
bean edge cap. `wide_columns` (6.5 ceiling, OFF, gate 1) is the existing
lever; the puff pitch is a preset.

## The gap that costs the most against his file

**The cross direction on a letter's slanted strokes.** On MARINE the pro
sews every stroke with the STEMS' cross -- square to the line of text --
diagonals included: the N's diagonal, the A's two legs and the M's two
diagonals all carry horizontal crosses, so the whole word has one sheen
and his junctions are plain overlaps
(`becker_hat_small_MARINE_paths_before_after_pro.png`, bottom panel). The
Column lane stations each straight piece square to ITS OWN axis
(`outline_cut.scan_stations`): our N's diagonal reads as a second, darker
sheen beside its stems, the A's legs likewise, and the M's V -- two leaned
pieces meeting two upright ones -- sews as a tangle of pivoting crosses
(top panel; `becker_hat_small_MARINE_before_after_pro.png` is the same word
as thread). Measured per letter, cross lean from the line of text (median,
deg): N 7.2 against his 5.6 for the whole letter, but the diagonal's own
crosses sit 30-60 deg off where his sit under 20; the test N in
`tests/test_column_text_lean.py` reproduces it (93 crosses over 20 deg off,
none on).

This is Kent's adopted stitch-angle convention (2026-09-03,
`stitch-angle-convention-2026-09-03`: stems square to the line of text, a
30 deg lean cap, station spacing over cos of the lean), built into the
satin tier as `stage6_satin._clamp_to_span` -- and the Column lane, which
took lettering from that tier on 2026-10-12, never carried it. The pro's
file is the convention sewn.

**Built: `cfg.lettering_columns_text_lean` (OFF), `digitizer_core/column_lean.py`.**
ON, every straight column of a Column letter whose axis the word's house
cross (`satin_angle_deg`, the house pass; else the design's) can span
within the cap is re-stationed with its crosses along the clamped house,
one every spacing / cos(lean) along the axis (so the distance between
crosses stays 0.40), each cross the longest segment its line cuts from the
piece, rails keeping their sides. A column the house already crosses square
(an upright stem), a curved or ring column (the R's bowl, which he fans
round as we do) and a letter with no house angle keep their stations
object for object. Layout, not a cloth number: ON-eligible from the
renders (Kent's ruling 2026-10-22). OFF is the lane as it was: the cached
`ours.dst` of Becker hat small re-digitized on this engine is byte-identical
(md5 `b0b04284…`), and the lane's tests are untouched.

**Before | after | pro** -- MARINE at 76.5 mm, Becker hat small
(`becker_hat_small_MARINE_before_after_pro.png`, 14 px/mm thread;
`..._paths_before_after_pro.png`, needle paths):

| MARINE 76.5 | before (OFF) | after (ON) | pro |
|---|---|---|---|
| N: cross lean, median deg | 7.2 | 5.2 | 5.6 |
| N: diagonal's crosses | square to the diagonal | the stems' | the stems' |
| N: fan ends / ends | 5 / 6 | 3 / 6 | 6 / 14 |
| A: cross lean, median deg | 14.8 | 4.6 | 16.4 (his bar piece) |
| A: legs | square to each leg | horizontal, on the foot | horizontal, on the foot |
| M: cross lean / fan ends | 5.1 / 6 of 10 | 4.7 / 2 of 8 | 5.0 / 10 of 22 |
| M: diagonals | square to each | horizontal | horizontal |
| M: the V | tangle | tangle, smaller | overlap |
| R, I, E | unchanged | unchanged (curved bowl; upright pieces) | — |
| word stitches | 2,036 | 1,974 | 2,170 |
| word trims / needle-up mm | 9 / 100 | 10 / 116 | 3 / 117 |
| sewn width, M / A / N | 4.32 / 4.05 / 4.60 | 4.32 / 4.22 / 4.50 | 4.02 / 4.02 / 4.10 |

The A's left leg sews 9% less thread after (714 against 781 mm): the
leaned scan reaches the slanted cut faces with shorter end crosses. The
M's V is the corner-folds lane's (a junction of four pieces), not this
flag's; the lean leaves it smaller, not gone.

**Price**: Becker hat small whole design 5,928 -> 5,866 stitches, trims
15 -> 16 (MARINE only moves; BECKER's faces are unsewn either way). A
design whose text has no slanted stroke the house can span is byte-identical
ON (every upright column keeps its station object); the other band jobs'
prices are in the PR body.

## Follow-ups (not built here)

1. **White faces and keylines**: BECKER's five faces and MFab's keyline web
   are the largest unsewn areas in the band -- `sew_enclosed_white`
   (#1031), the `white-like-pro` lane. The pro widens a 0.7 mm keyline to
   a 2.0 mm satin; a sewn 1.3 mm web would still be narrower than his.
2. **Fill + border for lettering is a KEYLINE rule** (above): a letter whose
   outline the art draws sews as fill with the outline as a 2.0-2.5 mm
   satin border; `border_by_size`'s circle test and a stroke test both put
   MARINE large and MFAB in one bucket. Build it on the enclosing-ring
   relation once the faces sew, with Bridge's bare script as the stroke
   evidence.
3. **Split crosses**: 2 penetrations on 91% of MARINE's 4.3-5.9 mm crosses
   where the pro sews whole to 5.3 (p99 6.2). `SPLIT_SATIN_ABOVE_MM` 5.0 and
   `_comb_thresholds`' carry -- a stitch-length ceiling, gate 1 (OFF flag,
   sew-out card).
4. **The M's V and the A's bar**: junction tangles that remain after the
   lean -- the corner-folds lane (`outline_cut.py`, not touched here).
5. **Rail wobble on long stems of low-res art** (M 0.19-0.25 vs 0.03-0.05):
   rails are the traced outline; the letterform-priors lane (lines + arcs
   refit) or a straight-rail fit on the Column.
6. **Trims**: 34 vs 16 over MARINE's four files; the pro jumps between
   letters uncut. The trim-economy lane (#1030).
7. **Tires**: `wide_columns` (OFF, gate 1) for the 4.6 mm script stroke; the
   0.14 mm puff pitch is a preset.
8. **Fill letters** (once they sew): the pro's 22 deg rows at 0.16 pitch,
   3.45 mm stitches, CROSS underlay at 15-28% (`fill_underlay_cross`,
   #1033, OFF).
