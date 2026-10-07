# Outer-rail pitch and the Fremont weight question (2026-10-06)

Renders behind `.claude/memory/lettering-thickness-fremont-2026-10-06.md` and
the scope-history entry of the same date.

- `fremont_studio_ours_vs_pro.png` — the Studio's realistic view at 244%:
  the original artwork, our 80 mm file, and the pro's own Wilcom DST of the
  same logo loaded as a design file. The pro's letters render at the same
  weight as ours; both are the pull-compensated column plus 0.4 mm thread.
- `zoom_ours80_HOTE.png` / `zoom_pro925_HOTE.png` — HOTE at matched letter
  height, 0.4 mm thread over the artwork (blue), ours at 80 mm pique
  (`main` cf9f89f1) and the pro's at 92.5 mm. The pro's O keeps its outer
  rail at 0.33 mm and short-stitches the inner; ours opened to 0.53.
- `fremont_HOTE_off_above_on_below.png` — `cfg.satin_outer_rail_pitch` OFF
  above, ON below, same engine otherwise: the O's outer edge tightens
  (0.53 -> 0.39 mm under rail comp), the straight letters do not move.
  Fremont at 80 mm: letter crosses 1,080 -> 1,182, design 13,606 -> 13,742
  stitches, trims unchanged, per-letter hair 1.49 -> 1.39 (pro 1.21).
