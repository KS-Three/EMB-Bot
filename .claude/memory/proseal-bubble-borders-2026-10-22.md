---
name: proseal-bubble-borders-2026-10-22
description: Why EMB-Bot ringed ProSeal's small blue hexagons when the pro's DST has no border on any of them, measured at the pro's 85.9 mm hat width; the pro's rule (one satin blob per compact shape up to the ceiling) built OFF as `compact_solids_satin`, on top of the sibling `small_solids_satin`
metadata:
  type: project
---

# ProSeal bubble borders (2026-10-22)

Kent's question: why do our spray bubbles carry a satin border when the
pro's file has none? Measured on `scratch_kent/Embroidery Files/Proseal/`
(art + `PROSEALHAT.DST`, 85.9 x 63.3 mm, 54 trims, 4 colour changes), ours
digitized the Studio's way (`tools.pro_pair`, hat preset, 85.9 mm).

**The ring is not the border tier.** `cfg.border` is None, so a logo gets
"off". Two different things read as a border, by bubble size:

- **2.0-3.7 mm hexagons (16 of them, at or over the 2.25 mm² detail floor):**
  `classify_ribbon` refuses them for ASPECT (a regular hexagon's length
  estimate is ~1.3 widths against the 3 a ribbon needs), so they sew tatami
  rows; every row end is in open air, so the bean edge cap
  (`edge_cap="bean"`, ON since 09-11) draws a `__edge_cap__` run round each
  one. That ring is what Kent saw. Pro: one satin blob, 21-32 stitches,
  nothing round it.
- **1.1-1.3 mm hexagons (6, under the floor):** the run-tier rescue sews a
  bean ring on the outline with bare cloth inside. Already answered by the
  sibling flag `small_solids_satin` (built OFF 2026-10-20).
- 3 to 4 of the smallest were not sewn at all (`stitched: false`).

**The pro's rule, one sentence:** every compact solid in the spray and the
honeycomb, 1.6 to 4.8 mm across on the hat (5.5 on the beanie), is ONE
satin column across its short side at ~0.37 mm pitch, 15-32 stitches, with
no fill, no underlay and no outline anywhere. The satin ceiling (5.0 hat)
already holds that size; no new constant.

**Built:** `cfg.compact_solids_satin` (OFF). A non-lettering solid with no
hole that the classifier refused for aspect only (width already under the
ceiling), not riding a design ramp, whose ring would leave its inside bare
(`is_small_solid`), sews `small_solid_satin` on `p.polygon` at the block's
satin pitch. On the ARTWORK polygon it stopped a pull width inside the
silhouette and the cap ringed it anyway: sew the stage-5 polygon, the one
the fill would have sewn. Satin is linear cover, so the cap omits that edge
on its own. Tests: `tests/test_compact_solids_satin.py`.

**JS twin: not needed.** `src/digitize.js` has no aspect test: `thin =
widthMmFinal <= satinMaxWidthMm && holes.length === 0`, so the browser
engine already sews a compact blob under the ceiling as satin.

**Gotchas.** `is_lettering` already untags a solid blob
(`lettering_columns_skip_blobs` ON), so a text-tagged hexagon is not
lettering; a holed hexagon can pass the classifier as a ribbon and sew
satin both ways. The lane's OFF `ours.dst` md5 equalled main's before the
change. Flip and the 4.8 mm-dot-on-a-cap question are Kent's (gate 1).

Related: [[satin-small-shapes-2026-10-20]] (the browser's small shapes),
[[border-seam-ownership-2026-09-09]] (the real border tier's seam rule).
