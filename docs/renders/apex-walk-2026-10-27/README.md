# Apex-cut walk: renders (2026-10-27)

One letter per sheet, OFF | ON (main 2c6b656c) | ON with the new walk, from
`python -m tools.apex_walk_census render` (`stitchviz.render_design`, palette-reduced
for the repo). Only our own stitches are drawn here. Write-up and numbers: `docs/apex-walk-2026-10-27.md`; per-letter and
per-job tables: `table.md`.

- `<job>_<letter>_view.png`: at 8 px/mm, about viewing size.
- `<job>_<letter>_40ppm.png`: at 40 px/mm.
- `<job>_<letter>_paths.png`: ours only, at 40 px/mm: the satin's needle path (grey),
  its centre underlay (orange), travel (red) and jumps (blue, a circle at each
  landing). His file labels no travel. Read these for the walk: on ON, travel
  crosses a tip after it is sewn (PROSEAL's A, MFab LC's W, MFab hat's N) and
  jumps leave tips (MARINE's M at 101.9 mm). On the new walk, each tip is entered
  under itself and sewn from its point.

**No pro panel, on purpose.** Kent's ruling of 2026-10-27 commits no new image of
a pro's stitch file under `docs/renders`. The first push of these sheets drew his
stitches as a fourth panel on 16 of them: the M's, MFab's 4s, and PROSEAL's A and
N. That panel was cropped off, and the originals were moved to the gitignored
`scratch_apex_walk_pro/`. `render --with-pro` draws the panel again, for a local
look only. His trims and crosses stay in `table.md` as numbers.
