---
name: short-column-underlay-2026-10-22
description: satin_underlay_short_columns built OFF; the pro runs a centre walk under 83-97% of satin columns at every width, and the "3.5 mm pitch" in the brief was a width threshold
metadata:
  type: project
---

`cfg.satin_underlay_short_columns` / browser `underlayShortColumns` (built
OFF 2026-10-22, gate 1: Kent's flip after a sew-out). ON, a shape under
`SATIN_UNDERLAY_MIN_EXTENT_MM` (5 mm, law 50's first rung) keeps the
fabric's satin underlay in both the satin tier and the Column lane, and
`_stroke_underlay`'s floor drops from `UNDERLAY_STITCH_MM` (2.5) to
`MIN_STITCH_MM` (1.0, with a 1e-6 tolerance: a 2 x 1 mm column's skeleton
spine is 0.9999999), and so does the Column lane's own 1.8 mm floor
(`columns._centre_underlay`, the end inset giving way first) -- without
that third reach Fremont ON was byte-identical to OFF: its 13 bare spans
were all 1.1-2.0 mm serif blocks in that lane. Nothing else moves: not
the zigzag threshold (2.5 mm width), not its 1.45 pitch, not the hairline
tier. MFab's residue ON (28% of short satin runs by kind) is satin-tier
junction pieces whose spine holds no 1.0 mm stitch.

**The pro's table** (`tools/pro_satin_underlay.py`, his 27 job DSTs; TIRES
HAT 3D is puff foam, 87% bare, excluded): a centre run under 83-97% of satin
columns in every length band (2-2.5 / 2.5-5 / 5-10 / 10+ mm) and width band
(<1.5 / 1.5-2.5 / 2.5-3.5 / 3.5-5 mm). Columns under 5 mm long: bare 0-13%
per job (ours 46%, audit row 5b). Edge run appears from 3.5 mm width
(37-73%). Zigzag is NOT settled: its share and pitch swing with the
reader's dense-satin gate (three crosses in a row: 25-80% at 0.6-1.0 mm;
any cross under 1 mm advance: 7-35% at 1.1-1.3 mm). The one band he leaves
bare: stubs under 2.5 mm long and 3.5-5 mm wide (68% bare, n=60).

**"3.5 mm pitch" was never measured.** The brief carried it as his zigzag
pitch; row 5a says 3.5 is the WIDTH where edge run + zigzag start. His
centre-run stitch is 1.4-1.7 mm (ours 2.5); his zigzag leg advance reads
0.6-1.3 mm by gate (ours 1.45, and ours is a LADDER: a rung across with no
advance, then a rail step -- `test_pro_satin_underlay.py` pins it). **Why:** a session that builds a 3.5 mm
pitch constant builds a number no file contains. **How to apply:** re-run
the tool before quoting any pro underlay number; a brief's number is a
pointer to a row, not the row.

**The instrument's first cut read every short column bare** because it
dropped any stitch with an end outside the column's footprint, and under a
2 mm column most of a 2 mm run stitch is outside. Clip to the footprint
first. Also: rail-to-rail thread advancing under 1.0 mm is satin (a fan
corner, a taper), not a zigzag leg -- without that gate zigzag read 24-40%
at 0.7 mm "pitch" on columns under 2.5 mm.

Renders: `docs/renders/short-column-underlay-2026-10-23/` (underlay drawn
OVER the top thread in red, the only way to see it; the preview hides it).
Related: [[underlay-under-fills-2026-10-05]], [[cross-underlay-presets-2026-10-21]],
[[small-bold-columns-2026-10-21]], [[sew-out-accepted-as-is]].
