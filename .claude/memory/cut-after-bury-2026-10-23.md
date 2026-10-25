---
name: cut-after-bury-2026-10-23
description: Why `cut_every_jump` ON took Fremont to 187 trims and what cured it — 150 of its 171 uncut jumps lie on the FIELD (letter to letter, ≤3 mm); the pro walks those needle-down on the work (his shortest Fremont cut is 3.4 mm), so the pass now buries, else walks on work, else cuts. Fremont 37 -> 44 ON (pro 20), MFab 61 -> 87 (19 bare cuts: white left as fabric). Still OFF, Kent's flip
metadata:
  type: project
---

Census 2026-10-23 of every uncut jump `_cut_or_bury_jumps` sees, on the
three flip-sheet jobs with `trim_bury_under_later` ON (the pickled block list
right before the pass, each hop classified by what its straight thread lies
on, and the pro's nearest move within 3 mm of it in his DST):

| job | uncut jumps | under later (buried) | on work only | bare | pro at the spot |
|---|---|---|---|---|---|
| Fremont hat 92.5 | 171 | 21 | 150 (140 run-to-run, the small lettering on the field) | 0 | no move at 130 of the 150: he sews through |
| Becker hat 76.5 | 1 | 0 | 0 | 1 | no move (he sews the white) |
| MFab hat 104.9 | 32 | 1 | 12 | 19 | no move at 15 of the 19 bare: R11, white left as fabric |

- **The pro walks short moves on the work.** `HOTEL FREMONT HAT.DST`: 20
  cuts, all `on_work`, shortest 3.4 mm. Over his 28 DSTs the shortest
  on-work cut is 1.91 mm, 64 of 1,002 are 3 mm or under. He never lays a
  needle-down stitch across bare fabric (a raster of his three files finds 0).
- **The cure is inside the flag, no new constant:** `bury(k, on_work=True)`
  in `_later_thread_burier` — the straight hop, every sample of its thread
  (centre and both edges) within half a thread of ANY centreline, sewn
  before or after. Bury first, walk second, cut only bare. A hop ≤ 2 mm is
  one plain stitch; longer walks are run stitches at `RUN_STITCH_MM`.
- **Measured end to end (trims / uncut / stitches), DST both sides:**
  Fremont OFF 51/172, bury 37/172, bury+cut-as-built 187/1, bury+walk
  **44/1** (143 walked, 21 buried, 7 cut), pro 20/1. MFab 65/33, 61/33,
  92/1, **87/1**, pro 18/1. Becker 15/2, 15/2, 16/1, **16/1**, pro 10/1.
- **What still costs, exactly:** the 1.5x target (Fremont 30, MFab 27,
  Becker 15) is not met by any jump cure. Fremont's 44 are 37 trims that
  existed BEFORE the flag (hops over 3 mm on the field, the pro cuts those
  too but has fewer pieces) plus 7 jumps whose thread EDGE leaves the work.
  MFab's 87 are 61 pre-existing (40 bare: white as fabric) plus 19 bare
  jumps plus 7 edge cases. The jump class the flag adds is now 7 and 26
  trims, not 150 and 31.
- The 7 "edge" cuts: the centreline is on work, a thread edge 0.2 mm out is
  not. Loosening that is a tolerance, so it was left alone.
- Renders: `docs/renders/cut-after-bury-2026-10-23/` (cut as built | walk |
  pro, 40 px/mm). The walk shows as run stitches between the small letters
  on the field, as the pro's own crop shows between his.
- Trap: `tools/pro_pair.digitize` with the Column lane calls `sequence()`
  TWICE (the lane sequences once lane-OFF for its order). A spy on a stage-7
  pass that keeps the FIRST call reads the wrong plan; keep the last.

**Why:** a session told "cut every jump 4x'd Fremont's trims" would reach
for a length threshold; the census shows the class is "on the field", and
the pro's answer to it is a walk. **How to apply:** classify before tuning;
the flag is still OFF and the flip is Kent's, judged in the preview (the
walk is layout, [[layout-judged-in-preview-2026-10-22]]). Related:
[[cut-every-jump-2026-10-21]], [[trim-economy-2026-10-21]],
[[pro-trim-threshold]].
