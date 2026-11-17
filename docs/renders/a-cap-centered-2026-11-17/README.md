# `lettering_columns_a_cap_centered` (built OFF): ORIGINAL | BEFORE | AFTER

Flag: `cfg.extra["lettering_columns_a_cap_centered"]`, default OFF. Cause: the A's
full-width level band (`apex_pro_joints`' flat-A case) fires on Becker MARINE's
**R** too, because the R's counter is a pentagon whose top vertex sits at the
counter's left edge, so the R is cut slab-from-bowl across its whole width.
ON, the band needs the counter's top vertex in the middle third of the counter's
width.

## How many moved (stitch lists compared OFF vs ON, md5)

- **9 pro jobs** (`tools.prime_grader.population()`): **1 moved** (becker_hat_large), 1 pictured.
- **Other `pro_baseline.JOBS` rows, 11 resolved in this container: 4 moved**
  (becker_lc_large, becker_hat_small, becker_chest_small, becker_beanie), 4 pictured.
  7 identical (bridge_hat, bridge_lc, gaulke_roofing_lc, gaulke_roofing_beanie,
  hotel_fremont_patch, mfab_lc, toat_machine_beanie). **2 not run**: proseal_hat and
  proseal_beanie (their art is a gitignored third-party file, not in this container).
- **26 corpus fixtures** at the Studio request, 80 mm, left_chest: **1 moved**
  (`becker_marine_logo`, the same art as the Becker jobs), 1 pictured whole-design
  only (not zoomed, not judged separately; same R as the Becker jobs). 25 identical.
- Total: 46 runs, **6 moved, 6 pictured** (5 also zoomed on the R). Inside every
  moved design only the R moved (checked per letter polygon on the first job); the
  flat A keeps its band.

## By eye (the R in MARINE)

| design | call |
|---|---|
| becker_hat_large | **modestly better**: slab and bowl are one piece, the horizontal seam is gone; a vertical seam where the stem's cap meets the fan |
| becker_beanie | **better**: the bowl turns smoothly round as one fan, the leg stays plain |
| becker_lc_large | **mixed, slightly better**: the bowl is one smooth fan, but the leg's crosses now splay at the foot |
| becker_hat_small | **mixed**: the bowl is much better (a clean radial fan, like the pro's R), but a dense radial fan now radiates from the counter's lower-left into the leg, the kind of fan the grader flagged on the E |
| becker_chest_small | **mixed**, as hat_small |
| fx_becker_marine_logo | same art and R as the Becker jobs; whole-design picture only |
| the 40 others run | no change (identical stitches) |

Not changed by this flag, and still visible: the counter stays a small slot
(pull compensation, ROADMAP gate 1, not touched). No design got worse overall; the
two small sizes trade a better bowl for a new leg fan.

Files per design: `<slug>_R_zoom_before_after.png` (the R, BEFORE | AFTER),
`<slug>_MARINE_original_before_after.png` (the word, ORIGINAL / BEFORE / AFTER),
`<slug>_original_before_after.png` (the whole design). No render of the
professional's file is committed here (Kent 2026-10-27).
