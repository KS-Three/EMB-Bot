---
name: letter-fault-reader-2026-11-11
description: Second fault reader vs Kent's defect-marks pins: per-colour topology (counter lost / join / bay closed) hits 9/14 closed-or-merged-letter pins vs chance 0.24 at 3 mm, CI [+0.08,+0.57] = shown, but leave-one-item-out loses it on 3 of 6
metadata:
  type: project
---

Built 2026-11-11 after [[edge-fault-reader-2026-11-10]] and
[[defect-marks-sitting-2026-11-10]]. The harness is the same
(`tools/fault_reader_harness.py`, `--fault letters`).

**Pins:** `select_letter_pins`. The note decides: a closure word, or a read
word on a letter. 14 pins on 6 logos (`letter-reader-pins.json`). Gaulke 3 is
shared with the edge rule, and the rule says why.

**Reader** `tools/letter_fault_reader.py`. It works per thread colour: art
(stage-1 raster, nearest spool, `bg_mask` = unsewn) against an exact label
render (filaments in sew order, no AA). It flags counter lost (under half its
width), join (thread across the Voronoi midline between two art shapes,
wider than 1.5 filaments) and bay closed (a thread hole where the art has
none). Three dev bugs on the unpinned logos were fixed before the
pre-registration (`71ef90ef`): a bg colour equal to a thread colour, AA
edges reading as grey, a white field closing "bays".

**Result (n = 14 / 6 logos, tree 950855bf):** hit 0.64 vs stitched-area
chance 0.24, kappa 0.53, CI [+0.08, +0.57]; AUC 0.66. Shown by the rule.
Fragile: dropping Bridge, Fremont or MFab gives a lower bound of -0.03, and
the 2 mm row crosses 0. The edge-band null is near 0 here (the letters sit in
sewn fields), so it is no stronger claim. Misses: both S "no spacing" pins
(a bay filled solid changes no topology), Bridge's B holes, TOAT T-into-border.
Bridge's B+R hit came through the B's lost counter, not a join.

**How to apply:** not a metric or gate yet; replicate on a second sitting
with the same constants first. A negative-space reader (glyph_read `space`)
is what would catch the S/E bays. Write-up: `docs/letter-fault-reader-2026-11-11.md`.
