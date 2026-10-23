# The 10 mm and up lettering band: ours against the pro (2026-10-23)

Thread renders (`digitizer_core.stitchviz.render_design`, the Studio's
previewer), each panel in its own frame, cropped to the same shape ids of
our segmentation (the pro's crop through `pairframe.register_pair`'s
registration). Ours is the Studio's own request at the pro's design width
and preset (`tools/border_census.py one SLUG`); the pro's is his file from
`Embroidery Files.zip`. Companion of `docs/lettering-10mm-up-2026-10-23.md`.

- `becker_hat_small_MARINE_before_after_pro.png` -- MARINE at 76.5 mm, 14
  px/mm: the Column lane as shipped | `lettering_columns_text_lean` ON | pro.
  The N's diagonal, the A's legs and the M's diagonals take the stems'
  cross after; the M's V still tangles (the corner-folds lane's).
- `becker_hat_small_MARINE_paths_before_after_pro.png` -- the same three as
  needle paths (1 px lines, red needle points, 24 px/mm), the artwork
  outline in pale green. The pro's crosses are horizontal on every stroke.
- `becker_hat_large_MARINE_ours_pro.png` -- 101.9 mm, 12 px/mm: his 5.2 mm
  crosses sewn whole, ours split.
- `becker_hat_small_BECKER_ours_pro.png` -- 10 px/mm: the five white faces
  sew nothing on our side (`sew_enclosed_white` OFF); his are a 22 deg
  tatami under the art's 2.4 mm outline, which we do sew.
- `mfab_hat_MFAB_ours_pro.png` -- 104.9 mm, 12 px/mm: his letters are the
  badge's black fill drawn by a 2.0 mm white satin keyline; ours are black
  satin columns on the badge with the 0.7 mm keyline unsewn.
- `tires_hat_script_ours_pro.png` -- 114.3 mm, 8 px/mm: his whole script
  is 4.3-4.6 mm satin (3D puff, 0.14 mm pitch); our "ires" is a fill under
  a bean edge cap (`wide_columns` OFF).
- `bridge_hat_script_ours_pro.png` -- 63.3 mm, 14 px/mm: his 11 mm script
  is a fill under a 1.5 mm border; ours 38 satin columns.

Nothing here is a customer file: every pro panel is a render of a stitch
file already in the public zip.
