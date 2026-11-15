# Timing and Cancel pass over the day's flips (2026-11-14)

**Question (the Director).** #1515 turned on `outline_redraw_k` 0.75,
`inshape_piece_lift`, `small_text_reset_one_baseline`,
`text_cluster_solid_guard`, `group_consistent_tier`,
`group_consistent_fill_angle` and `flat_blend_band_any_scale`. Nobody had
timed the corpus before and after. Also wanted: the longest stretch with no
`deadline.check` on main (a Cancel waits that long), and the flags Kent has
ruled ON that are about to flip, timed ON.

**Answer.**
- **No flip of #1515 costs more than 15% CPU except `outline_redraw_k` on an
  upscaled source with many rings.** To a T machine (hat) went 22 -> 33 CPU s
  (x1.52). All of it is the redraw's ring fit in generation (5.2 -> 17.3 CPU
  s; "ring fit" 17 s and "outline redraw" 16 s wall). Every other design
  measured is within 15% or faster: MFab is faster on main (65 -> 47 CPU s,
  its plan changed).
- **The four about-to-flip flags cost nothing measurable**:
  `lettering_columns_connectors_edge_walk`,
  `lettering_columns_corner_fold_apex_side`, `group_consistent_thread`,
  `group_consistent_outline_body`. CPU next/main is 0.93-1.06 on every
  design measured. But ON, To a T machine opened a **15.2 s stretch with no
  check** in the art-outline search. Seamed here.
- **Seams added; every one moves no number.**
  - `stage0_classify._assign`, the colour-mass k-means: 3.7 of classify's
    6.4 s on Tires, all before stage 0's first check.
  - `script_strokes`: the station loop, the ink grid, the skeleton and the
    pen strokes. Tires' script word ran 6-14 s wall from stage 7's per-shape
    check to the satin rail push.
  - `stage1_prep`'s intrusion loop.
  - `art_outline.find_art_outlines`: per holder, body and measure.
- **One speed fix, byte-identical:** `stage1_prep`'s background-intrusion
  warning painted and eroded a FRAME-sized hull for every foreground shape.
  It now uses the hull's own box, grown by the kernel's reach. Drone prep
  3.57 -> 0.90 s, Golden Tee 7.38 -> 4.52 s. bg_mask, rgb and warnings were
  identical on 7 images (4 tripwire jobs, 3 fixtures), old against new in
  one process.
- **Not touched:** `_push_rails` (the counters worker's) and the redraw's
  ring fit (the flips worker's). Remaining stretches over 1 s are listed
  below.

## Method

`python -m tools.flip_timing arms SLUG ...` (new). One process per design
with one untimed warm-up digitize. It runs three arms, each through
`tools.pro_pair` (the Studio request, the service's parser) at the pro's size:
- `pre`: main with #1515's seven flips set back (`PRE_1515`);
- `main`: today's defaults;
- `next`: main with the four flags above ON.

`deadline.check` is wrapped by a recorder that only reads the clock (the
`tests/test_cancel_seams_1113.py` method). Each run records wall and CPU
seconds per step, seconds per check label, the longest stretch between
checks, and the md5 of the plan's runs. `pre` against `main` on the SAME
tree isolates the flips. Commits that merged since #1515 are in both arms.

**Read the CPU column, not the wall.** The laptop ran about ten other
sessions. Tires took 17 s wall at 19:00 and 35-58 s at 21:15. Wall ran 2-4x
the process's CPU time, and the order of the arms moved it more than any
flag. CPU (`process_time`) is from Golden Tee on. One design per process,
one run per arm: n = 1, a laptop reading, not a benchmark.

Designs: one size each of the tripwire set's eight designs (`tools.tripwire
jobs`, which lists 18 jobs over those eight). Runs that started after a
seam was committed carry it, in all three arms alike, so the arms stay
comparable within a design. The "longest gap" column mixes trees: Tires,
drone and Golden Tee ran before the seams, Becker onward after some.

## Table

| design (job) | wall s pre / main / next | CPU s pre / main / next | CPU main/pre | CPU next/main | plan md5 pre vs main | longest gap on main |
|---|---|---|---|---|---|---|
| Tires (hat 3D) | 35 / 47 / 58 | - | - | - | same | 14.3 s, stage 7 -> satin rail push (script word; seamed here) |
| Precision drone | 110 / 90 / 119 | - | - | - | same | 5.9 s, stage 0 -> stage 1 (prep; seamed and sped up here) |
| Golden Tee (hat) | 273 / 185 / 146 | 66 / 63 / 64 | 0.95 | 1.01 | same | 9.3 s, stage 0 -> stage 1 (prep; seamed here) |
| To a T machine (hat) | 50 / 73 / 71 | 22 / 33 / 31 | **1.52** | 0.93 | moved | 3.9 s, plan_stitches -> stage 5 (art outlines; seamed here); 15.2 s in `next` |
| Becker (hat, large) | 35 / 36 / 30 | 20 / 21 / 21 | 1.06 | 0.97 | moved | 0.5 s |
| Gaulke (hat) | 32 / 45 / 41 | 24 / 24 / 25 | 0.99 | 1.06 | same | 0.7 s |
| MFab (hat) | 129 / 81 / - | 65 / 47 / - | 0.73 | - | moved | 1.5 s, stage 5 -> stage 7 |
| Hotel Fremont (hat) | 155 / 99 / 103 | 64 / 63 / 63 | 0.98 | 1.01 | same | 7.8 s, stage 1.5 -> stage 2 |

**Per stage, where CPU moved more than 15%:**
- **To a T machine:** generation 5.2 -> 17.3 CPU s. The redraw is
  "outline redraw" 15.8 s and "ring fit" 17.3 s wall on main, absent from
  pre. Its plan is 15.1 -> 14.4 CPU s. The source is upscaled, so the
  redraw runs; its seams (#1524) hold, the longest redraw stretch is under
  1 s. Cost, not latency.
- **MFab, faster:** plan 60.3 -> 34.8 CPU s ("column build" 33.7 -> 12.9,
  "keyline" 20.6 -> 11.3 wall). Generation +7.9 CPU s is the redraw again.

## Stretches still over 1 s on main (laptop wall, loaded)

- **stage 0, before and after the colour mass** (Golden Tee: 8-10 s before
  the first k-means call, 6-12 s after the last): classify's other
  features. Golden Tee only; Gaulke's whole start is 0.7 s.
- **stage 1.5 -> stage 2** (7.4-7.8 s on Fremont, every arm): the step
  between photo prep and the quantizer.
- **stage 2 -> thin ink** (2-5 s): the quantizer's tail after its last check.
- **small text placement** (Fremont, up to 3-5 s a stretch, 25-53 s in
  all) and **art outlines -> stage 5** (3-5 s on Fremont: the rest of the
  plan's set-up before stage 5's check).
- **`script_strokes.ink_grid`'s `ink.field()`** (about 1.7 s, one whole-image
  colour conversion, cached per source).
- **stage 5 -> stage 7, stage 7 bury trims, stage 7 hoist** (1.2-1.5 s on
  MFab, wall under load).
- **The redraw's ring fit** (the flips worker's code): seamed by #1524,
  under 1 s a stretch, but 12 CPU s on To a T machine.

Next lever, if the To a T cost matters: the ring fit's per-ring cost on a
many-ring upscaled logo.
