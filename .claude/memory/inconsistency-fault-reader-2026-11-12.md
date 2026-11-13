---
name: inconsistency-fault-reader-2026-11-12
description: Fifth fault reader (like features sewn unlike their siblings) on both sittings' sibling-contrast notes: per note 0.43 vs chance_pick 0.47, -0.04 CI [-0.42,+0.42] = not shown; feet "different colors" = one spool, fill direction read as tone
metadata:
  type: project
---

Built 2026-11-12 after [[infill-fault-reader-2026-11-11]] and
[[space-fault-reader-2026-11-12]]. Reader `tools/inconsistency_fault_reader.py`,
harness `--fault inconsistency` (`select_inconsistency_pins`: a sibling
contrast, colour allowed, not against the pro or the art). Pre-registration
`a1452f7e`, write-up `docs/inconsistency-fault-reader-2026-11-12.md`.

**Target:** 10 notes, 39 pins, 7 items (kanji 28 of them). Power: CI about
0.5 wide; only a gain over +0.45 could be shown. Not a hold-out.

**Rule:** F1 = top-thread components grouped by geometry (area x1.5,
elongation x1.25, solidity 0.10), odd on colour / run kind / stitch angle /
rim when it disagrees with over half its group; F2 = the in-fill reader's
spaces, frozen. No pipeline: in-fill rasters + stored stitches, ~10 s.

**Result:** not shown; LOO: without devanagari (F2's hits) -0.29. Emoji legs
hit on the right mechanism (border vs fill) and mascot feet on angle, but
those groups are almost the whole candidate set (pick 0.92, 0.99). Missed by
every reader: Bridge handles (shape), MFab F (travel), pixel-art openings,
nostril.

**How to apply:** both feet are 1120 Sunset; mirrored fills at 39/134 deg
render as two tones (`stitchviz` lit shading), so a "colour" note can be
direction. A deciding sitting needs ~20 such notes on 10+ items with many
alike features, which sibling named, and the colour question asked on the
flat render too. Not a gate or metric.
