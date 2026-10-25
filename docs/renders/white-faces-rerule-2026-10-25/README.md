# White switches, re-rule packet (2026-10-25)

`tools/enclosed_pro_census.py render`: ours carried into the pro's frame by
the census's own registration (`pairframe.register_pair`), every tile on one
canvas, Studio previewer on a mid-grey ground so white and black thread both
show. Each job at the pro's width, the Studio's request for its garment;
`main` at 82b0bf28 (`border_from_outline` ON). The pro is drawn from his PES
(thread colours) centred on his DST; his counts are the DST's.

Arms: `off` = shipped; `white` = `sew_enclosed_white` alone; `white_keyline`
= plus `enclosed_white_keyline`; `on` = plus `sew_enclosed_white_fields_fill`
(all three).

- `becker_chest765_whole_off_white_on_pro.jpg` -- Becker chest small, 76.5 mm
  left chest, whole design. The pro recoloured this job: his BECKER faces are
  BLACK under a GREY outline (his PES and his own preview JPG agree); the art
  has white faces in a black outline, which is what ours sews.
- `becker_chest765_BEC_off_white_on_pro.jpg` -- the same, cropped to the three
  leftmost faces. `white`: the faces fill under the outline at the word's house
  angle, 0 deg (horizontal rows). `on`: 22 deg (`machine.WHITE_FIELD_FILL_ANGLE_DEG`).
  Pro: 20-22 deg.
- `mfab_hat1049_band_off_keyline_on_pro.jpg` -- MFab hat, 104.9 mm, the left 40%
  of the white keyline band. `white_keyline` is byte-identical to `white` on main
  (`border_from_outline` takes the band); `on` sends the band to the fill tier.
- `golf_hat749_S04c12d7a_off_white_pro.jpg` -- Golden Tee hat, 74.9 mm, the one
  census miss outside Tires: a 5.4 mm2 hole the pro leaves open and our OFF
  already covers with white thread (so no white switch moves it). Registration
  here is weak (IoU 0.63, calibration 0.78): read the picture, not the number.
