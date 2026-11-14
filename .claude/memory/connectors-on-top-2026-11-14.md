---
name: connectors-on-top-2026-11-14
description: Kent's Becker #14/#15 "random cross over stitch" = Column-lane connectors sewn across a letter's finished satin; `lettering_columns_connectors_buried` (OFF) clears 268 -> 44 mm over 28 designs at +50 trims; MFab #2 = photo-lane border lightened to a bean loop
metadata:
  type: project
---

Director's part 3 on 2026-11-14 (after [[flip-candidates-2026-11-14]]).

**Becker hat large #14/#15** are Column-lane connectors: 6.2 and 9.3 mm of
travel from one E arm's satin end to the next leg, sewn after that arm and
across it.
- The leg's zigzag ends on its last cross's b rail.
- The link rule calls an inside-letter hop "under thread sewn later" without
  checking that anything covers it.

**The pro:**
- Running stitch on finished satin is zero on 17 of his 22 files, at most
  0.97 mm on two.
- Drone's 230 mm is outline detail and ProSeal's runs along a stroke's
  edge; neither is a hop across a stroke.
- At Becker's E he lays centre runs first and covers them with the satin.

**`lettering_columns_connectors_buried` (built OFF)** in `columns.column_runs`:
1. End each leg on the rail whose hop lies less on finished satin. This
   alone fixes the E, at no trim.
2. Any hop still over `_ON_TOP_MAX_MM` 1.0 mm on finished satin is rerouted
   under later satin, else cut (jump + trim).

Over 28 lettering designs:
- letters' travel on finished thread 268 -> 44 mm;
- trims +50 (+1.8 each, at most +5);
- exposed travel 0;
- pins #14/#15 clean by eye.

The reroute never fired; an edge-walk (the pro's ProSeal way) would save
most of the trims.

**MFab hat #2** is not a connector. MFab classes `photo_scene`, so
`border_style` "significant" rings its small white enclosed counter. The
counter is 3.35 mm, too narrow for the 1.7 mm column, so the ring lightens
to a bean loop 0.85 mm inside the fill, on top. The pro sews one fanned
satin.

**Why:** Kent's flip; this is the evidence. **How to apply:** before claiming
"the pro never does X", read all 22 pro files. The first 14 said "never"
here, and Drone and ProSeal said otherwise. Write-up:
`docs/connectors-on-top-2026-11-14.md`.
