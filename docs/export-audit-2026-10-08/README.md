# Export audit, 2026-10-08

Produced by `tools/export-audit.mjs` (Python half `tools/export_audit.py`,
logos digitized by `tools/export_audit_digitize.py` at the Studio's default
parameters). Re-run it rather than trusting these numbers once the code moves:

    node tools/export-audit.mjs --renders OUT_DIR

Each cell is **sewn stitches / trims / colour stops** as pystitch reads the
file. A colour stop counts COLOR_CHANGE plus STOP, since pystitch reads a change
between two blocks written with the same chart cone as a STOP. U01 counts
NEEDLE_SET after the first. ⚠ marks a cell `flags()` objects to: on this run,
service PES/PEC cut at every jump, and VP3 writes travel as stitches. Both are
in `docs/scope/4-export-formats.md` as questions for Kent. Orientation was
identity in all 132 files, and the sewn extents matched the model within 0.1 mm.
Stitch counts above the model's are over-length sewn moves split into stitches
(the chain rule). DST trims above the model's are long travel, which a reader
takes as a cut.

| design | model: stitches / trims / colour stops / mm | BROWSER DST | BROWSER EXP | BROWSER PES | SERVICE DST | SERVICE PES | SERVICE EXP | SERVICE JEF | SERVICE XXX | SERVICE VP3 | SERVICE PEC | SERVICE U01 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| shape_star | 2263 / 1 / 0 / 51.3×49 | 2263 / 2 / 0 | 2263 / 1 / 0 | 2263 / 1 / 0 | 2263 / 2 / 0 | 2311 / 50 / 0 ⚠ | 2263 / 1 / 0 | 2263 / 50 / 0 | 2263 / 1 / 0 | 2263 / 2 / 0 ⚠ | 2311 / 50 / 0 ⚠ | 2263 / 1 / 0 |
| shape_heart | 5444 / 1 / 0 / 70.5×64.3 | 5444 / 2 / 0 | 5444 / 1 / 0 | 5444 / 1 / 0 | 5444 / 2 / 0 | 5444 / 2 / 0 | 5444 / 1 / 0 | 5444 / 2 / 0 | 5444 / 1 / 0 | 5444 / 2 / 0 ⚠ | 5444 / 2 / 0 | 5444 / 1 / 0 |
| manual_three | 14323 / 4 / 2 / 102.2×61.5 | 14386 / 6 / 2 | 14386 / 4 / 2 | 14386 / 4 / 2 | 14386 / 6 / 2 | 14388 / 9 / 2 | 14386 / 4 / 2 | 14386 / 5 / 2 | 14386 / 4 / 2 | 14386 / 5 / 2 ⚠ | 14388 / 9 / 2 | 14386 / 4 / 2 |
| text_fritsch | 1341 / 6 / 0 / 101.8×15.1 | 1341 / 6 / 0 | 1341 / 6 / 0 | 1341 / 6 / 0 | 1341 / 6 / 0 | 1341 / 6 / 0 | 1341 / 6 / 0 | 1341 / 6 / 0 | 1341 / 6 / 0 | 1341 / 7 / 0 | 1341 / 6 / 0 | 1341 / 6 / 0 |
| text_two_colour | 1343 / 15 / 1 / 101.8×7.3 | 1343 / 15 / 1 | 1343 / 15 / 1 | 1343 / 15 / 1 | 1343 / 15 / 1 | 1343 / 18 / 1 | 1343 / 15 / 1 | 1343 / 14 / 1 | 1343 / 15 / 1 | 1343 / 16 / 1 ⚠ | 1343 / 18 / 1 | 1343 / 15 / 1 |
| text_arc_script | 2647 / 13 / 0 / 101.8×32.5 | 2647 / 13 / 0 | 2647 / 13 / 0 | 2647 / 13 / 0 | 2647 / 13 / 0 | 2647 / 13 / 0 | 2647 / 13 / 0 | 2647 / 13 / 0 | 2647 / 13 / 0 | 2647 / 14 / 0 | 2647 / 13 / 0 | 2647 / 13 / 0 |
| mixed_full_back | 24814 / 10 / 1 / 261.3×196.6 | 24814 / 144 / 1 | 24814 / 10 / 1 | 24814 / 10 / 1 | 24814 / 144 / 1 | 25012 / 212 / 1 ⚠ | 24814 / 10 / 1 | 24814 / 211 / 1 | 24814 / 10 / 1 | 24814 / 11 / 1 ⚠ | 25012 / 212 / 1 ⚠ | 24814 / 10 / 1 |
| logo_golke_roofing | 5014 / 32 / 5 / 79.8×33.4 | 5014 / 32 / 5 | 5014 / 32 / 5 | 5014 / 32 / 5 | 5014 / 32 / 5 | 5014 / 61 / 5 | 5014 / 32 / 5 | 5014 / 22 / 5 | 5014 / 32 / 5 | 5014 / 33 / 5 ⚠ | 5014 / 61 / 5 | 5014 / 32 / 5 |
| logo_mfab_lc | 10903 / 75 / 6 / 80.1×30.6 | 10903 / 75 / 6 | 10903 / 75 / 6 | 10903 / 75 / 6 | 10903 / 75 / 6 | 10903 / 96 / 6 | 10903 / 75 / 6 | 10903 / 63 / 6 | 10903 / 75 / 6 | 10903 / 76 / 6 ⚠ | 10903 / 96 / 6 | 10903 / 75 / 6 |
| logo_hotel_fremont_patch | 16800 / 51 / 4 / 80.5×42.4 | 16800 / 51 / 4 | 16800 / 51 / 4 | 16800 / 51 / 4 | 16800 / 51 / 4 | 16800 / 119 / 4 | 16800 / 51 / 4 | 16800 / 47 / 4 | 16800 / 51 / 4 | 16800 / 52 / 4 ⚠ | 16800 / 119 / 4 | 16800 / 51 / 4 |
| logo_golke_roofing_250mm | 5014 / 32 / 5 / 250×104.6 | 5024 / 32 / 5 | 5024 / 32 / 5 | 5024 / 32 / 5 | 5024 / 32 / 5 | 5024 / 61 / 5 | 5024 / 32 / 5 | 5024 / 52 / 5 | 5024 / 32 / 5 | 5024 / 33 / 5 ⚠ | 5024 / 61 / 5 | 5024 / 32 / 5 |
| imported_becker_dst | 8694 / 14 / 3 / 76.5×46.8 | 8694 / 11 / 3 | 8694 / 14 / 3 | 8694 / 14 / 3 | 8694 / 11 / 3 | 8694 / 14 / 3 | 8694 / 11 / 3 | 8694 / 11 / 3 | 8694 / 11 / 3 | 8694 / 12 / 3 | 8694 / 14 / 3 | 8694 / 11 / 3 |

## Renders

Each render shows the Studio preview's strands first, then each file as
pystitch decodes it. Every panel is fitted to its own extents, so a mirror or a
turn would show as one. Grey lines are travel.

- `manual_three_before.png` / `_after.png`: the hand-drawn satin L. Before
  the service fix, the service DST/EXP/JEF/XXX panels have lost the L's long
  cross-stitches, which went out as needle-up jumps.
- `text_fritsch_before.png` / `_after.png`: default black lettering. The
  browser PES panel is Deep Green (#132b1a) before the cone-metric fix and
  Black after.
- `mixed_full_back.png`: a Full Back text + star. The VP3 panel shows travel
  written as stitches (VP3 has no jump record).

Logo and becker renders are left out of the repo on purpose: they are drawn
from client and third-party artwork, so regenerate them locally.
