# A blend rim between two inks becomes its own thread (2026-11-14)

The blind eye census (`digitizer/eye_pairs_out/agent-eye-1113/REPORT.md`, class 8
"wrong thread colour", cause 3) and the group-consistency census agree: an
anti-aliased or JPEG edge between two colours is quantised to a third thread and
sewn. This note traces each case to the function, the measure and the value that
let it through, and records the flag built.

Method: the Studio request at the kit size; the flat lane's own stage-2 loop
(`stage2_quantize._quantize_population`) instrumented to print, per colour
cluster, its pixel count, its edge fraction at 0-3 px depth and its residual
off the chord between two other colours; renders and `debug_dir` dumps under
`digitizer/eye_pairs_out/blend-band-1114/` (primary checkout, gitignored).

## Census

| design (lane, raster) | stray piece | width | colour vs its two sides | why no dissolve took it |
|---|---|---|---|---|
| silhouette_logo 80 (flat; JPEG kept at its 13.65 px/mm) | mint rims round the white letters, sewn Swiss Ivy 5422 (39 regions) | 0.37-0.83 mm, 6-13 source px | cluster Lab 66.7 / -32.3 / 18.9: 5.4 dE off the green-white chord (gate `merge_delta_e` 6.0), t 0.45 | round one: edge fraction 0.64 under `aa_phantom_edge_frac` 0.9. Round two (`flat_ramp_blend_dissolve`, ON) reads 0.98 at 1 px but never ran: `quantize` sets `ramp_px` only for an ENLARGED raster. |
| silhouette_logo | dark-green ring round the bear, Green Dust 5643 | 0.30 mm, 4.8 source px | 3.8 dE off the bear-green chord, t 0.48 | edge fraction 0.36; 0.95 at 2 px; same skipped round. |
| ProSeal hat 85.9 (flat; kept at its 9.20 px/mm) | Spearmint 4240 band, 0.33 mm, the whole 85.7 mm length of the teal bar | ~4 source px | 6.3 dE off the page-teal chord in Lab (gate 6.0), on the RGB chord | edge fraction 0.65; round two skipped; the RGB-chord reading is round one's, and only for enlarged rasters. |
| Precision Drone 62.6 (GRADIENT) | bezel sewn grey / white / grey | 0.2-1.0 mm | on chords, but the art's bezel is a metallic ring with real highlights | not an anti-alias band: posterised shading, photo lane. One thread per drawn line was `line_chain_one_thread`, ruled OFF 2026-11-11. Not touched. |
| (hed)p.e. 80 (flat) | the e's lower stroke and both periods on 1335 Dark Rust | 0.5 mm stroke | 2.4 dE00 from 2011, not between two neighbours | a later re-snap of a thin piece (`revalidate_threads`): the ground of `resnap_hairline_never_lightens`, ruled OFF 2026-11-11. Not re-proposed. |

## Built: `cfg.flat_blend_band_any_scale` (OFF)

The existing round, on a flat raster the grid did NOT enlarge:

* depth `stage2_quantize.BLEND_BAND_PX` = 2 working px (0.25 mm at 8 px/mm),
  the smaller depth that reaches all three measured clusters;
* a candidate is a blend on the Lab chord OR the RGB one (`_rgb_chord_t`:
  the space a blend is mixed in, residual judged in Lab), between two KEPT
  colours or one and the page, never between two other blends;
* each band pixel takes the label of the NEAREST pixel outside the band, the
  page included, so a rim splits between the two things it lies between. A
  rim against the page goes half to the page: joined all to the ink,
  ProSeal's hexagon cells each grew a pixel a side into their 0.3-0.5 mm
  white gaps and stage 6 closed them (at stage 2 the teal fell from 31
  separate pieces to 25). **Tried first and wrong:** folding the whole cluster
  into the chord's ink side. The same pale colour rings other strokes as
  JPEG noise elsewhere, and every speck of it went teal (ProSeal's subline
  grew a teal N, the gun's trigger glint went teal).
* once a band dissolves, round one's blends join the same way. They used to
  go to the nearest KEPT centre in Lab. ProSeal's black subline letters have
  a grey anti-alias edge (two clusters, L* 60 and 83, between the black and
  the page). OFF the pale one goes to the Spearmint, which is kept, and the
  darker one to the teal: one pixel of teal and Spearmint down each side of
  every letter at stage 2, merged away later. With the Spearmint dissolved,
  the nearest kept centre for both is the teal. The letters grew a full
  teal rim, and stage 4 kept a 0.27 mm² teal stroke in the I and 0.18 mm²
  in the N. Joined to what they touch, the greys go to the black: the teal
  falls from 665 pieces to 31 and the letters are black to the edge. These
  round-one greys join the ink only, never the page, so a thin letter keeps
  the width it had.
* a band pixel joins only a piece at least stage 4's hole floor
  (`min_detail_mm`² / 4) that is thicker than a hairline (it survives a
  one-pixel erosion); a lesser piece the band touches goes with the band.
  silhouette_logo's disc edge is a green-to-page ramp. Stage 2 labels its
  outer one or two pixels with the pale letter colour (5050) and the next
  one mint. OFF, stage 3 cuts that into specks and drops them. Without
  this rule the mint joined the pale row, which grew into strips three
  pixels deep that sewed as white satin on the green border (top and left).
  The rule changes 0 px on ProSeal.

The colour test is unchanged, so a thin colour that is NOT between its
neighbours (a keyline) stays. An enlarged raster is the line as it was, ON or
OFF.

**How this differs from the bevel/shadow fold** (`regular-structure` lane,
`enforce_color_cap`): that folds a ONE-sided band (a bevel or drop shadow
beside a shape) by size, after the palette cap, on threads. This folds a
TWO-sided blend (a colour lying on the chord between the two things it
separates) at stage 2, on colour clusters, before any thread exists.

## Proof

Studio request at the kit size, one digitize at a time. Sheets (art | OFF |
ON, Kent's pins drawn: green = the pin's stray thread is gone ON, grey = a
pin about something else) are in `digitizer/eye_pairs_out/blend-band-1114/sheets/`
(primary checkout, gitignored).

| design | lane, raster | stitches OFF / ON | shapes OFF / ON | threads OFF -> ON | Kent's pins |
|---|---|---|---|---|---|
| silhouette_logo 80 | flat, 13.65 px/mm kept | 25,036 / 21,989 | 93 / 51 | 5510 1375 5050 5422 5643 0010 -> 5510 1375 5050 0010 | 12 of 32 sat on a stray blend thread OFF (mint 5422 x9, Green Dust 5643 x3); all 12 land on a real thread ON. The other 20 read the same thread both ways. |
| ProSeal hat 85.9 | flat, 9.20 px/mm kept | 6,434 / 5,707 | 94 / 75 | 1375 4101 4240 0015 -> 1375 4101 0015 | pin 1 ("The satin border is changing colors too much"): the bar is one teal satin ON, hit. Pins 2-4 (S spacing, crisp edge, M) are other faults, unchanged. |
| Precision Drone 62.6 | GRADIENT | 14,984 / 14,984 | md5 identical | unchanged | pin 3 (bezel bean colour) not reached: gradient lane, see census. |
| (hed)p.e. 80 | flat, 23.05 px/mm kept | 3,849 / 3,849 | md5 identical | unchanged | pin 1 (the e's stitch type) not this fault: a later re-snap. |

What else moves ON, by eye:

* silhouette_logo: the green field's fill turns from horizontal to vertical
  rows (the field now holds the old mint rims and the bear ring, and the
  angle is chosen again); same thread. The bear has no ring, the letters
  are white to the edge, the disc border is clean.
* ProSeal: the 31 hexagon cells stay 31 separate shapes; their pale
  slivers and the trigger's pale glint are gone. As OFF, the cells touch
  where the art has 0.3-0.5 mm white gaps (stage 6, not this flag).

Real keylines and thin strokes, OFF vs ON stitches md5:

| design | raster | round ran | md5 |
|---|---|---|---|
| low_poly 60 (drawn black lines) | flat, 10.57 px/mm kept | yes | identical |
| outline_lineart_logo 80 | flat, 21.98 kept | yes | identical |
| lt_k_line 80 | flat, 22.27 kept | yes | identical |
| hotel_fremont_hat 92.6 | flat, 27.00 kept | yes | identical |
| low_poly 80 | flat, enlarged (7.92 -> 8) | no | identical |
| mfab_hat 104.9 | photo_scene, enlarged | no | identical |
| becker_hat_large 101.9 | flat, enlarged (1.42 -> 5.69) | no | identical |

Becker's and MFab's keylines are never on a live flat raster at their kit
sizes, so the round cannot reach them; low_poly at 60 mm is the live
drawn-line case.
