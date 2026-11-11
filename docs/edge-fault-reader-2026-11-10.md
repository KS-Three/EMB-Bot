# Edge-fault reader vs Kent's pins: not shown better than chance (2026-11-10)

**Verdict: no.** At the pre-registered 3.0 mm, the first edge-smoothness reader
lands near 12 of Kent's 20 "this edge should be smooth" pins (0.60). The same
flags land near 0.49 of randomly placed points on the stitched area. The
difference is +0.11, kappa 0.21, and its 95% item-bootstrap interval is
[-0.04, +0.21]. The interval includes 0, so by the rule written before the
run, the reader is **not shown** to find what he pointed at. The flag
strength does not rank his pins above random points either: AUC 0.51 against
both nulls. Every figure here is an instrument reading on one sitting of one
person on one tree (`950855bf`), n = 20 pins on 7 logos. It is not a quality
claim (ROADMAP gate 4).

The radius, the pin-selection rule, both nulls and the verdict rule were
committed before the reader ran on any item:
[`defect-marks-2026-11-10/edge-reader-preregistration.md`](defect-marks-2026-11-10/edge-reader-preregistration.md)
(commit `a281aa65`). The selected pins are in `edge-reader-pins.json` and the
full scored output is in `edge-reader-score.json`, both in that folder. No
picture is committed. The overlays used to read the misses below stayed in a
scratch folder.

## What was built

- **Harness:** `digitizer/tools/fault_reader_harness.py`. It takes a reader's
  flags (mm, render frame, strength) and Kent's pins for an item, and reports
  hits within the radius beside two chance figures: the same flags against
  random points on the stitched area, and against random points on the
  stitched area's 1 mm edge band. 2,000 draws per item, seeded. Pooling is
  pin-weighted, with a bootstrap over items. It also reports a
  threshold-free strength AUC. The pure helpers need no engine. To reuse it,
  write a new reader that emits `<item>.flags.json` and `<item>.mask.npz`.
- **Reader:** `digitizer/tools/edge_fault_reader.py`. It invents no
  measurement. It re-runs each job with the stored config and the job's own
  artwork, and **refuses** the item unless the re-run's stitches match the
  stored design stitch for stitch. All 11 matched. It then takes
  `edge_wobble.analyse_plan(...)["flagged"]`, which lists every edge
  penetration whose high-passed deviation from its own shape's outline is
  over `OVER_MM` 0.15 mm. That is the instrument behind preflight's
  `edge_wobble_*` metrics; preflight keeps three numbers per tier and drops
  the locations. The reader maps those points into the pins' frame and merges
  them within 2.0 mm, strongest first.
- **Frame check:** a test pins the mapping to `stitchviz._frame`'s own pixel.
  On the Becker overlay, Kent's pins 1 and 2 ("random cross over stitch") sit
  exactly on the two stray lines.

## Per item, 3.0 mm

| item | relevant pins | flags | hit | chance (area) | chance (edge band) | AUC area / edge |
|---|---|---|---|---|---|---|
| `L_becker_hat_large` | 7 | 139 | 5/7 | 0.47 | 0.44 | 0.56 / 0.58 |
| `L_bridge_hat` | 1 | 85 | 1/1 | 0.74 | 0.65 | 0.64 / 0.70 |
| `L_gaulke_roofing_hat` | 2 | 121 | 2/2 | 0.74 | 0.69 | 0.60 / 0.64 |
| `L_hotel_fremont_hat` | 1 | 78 | 0/1 | 0.43 | 0.40 | 0.28 / 0.29 |
| `L_mfab_hat` | 3 | 226 | 2/3 | 0.69 | 0.89 | 0.36 / 0.21 |
| `L_proseal_hat` | 2 | 61 | 1/2 | 0.50 | 0.34 | 0.43 / 0.51 |
| `L_tires_hat_3d` | 4 | 28 | 1/4 | 0.21 | 0.16 | 0.54 / 0.57 |
| `L_precision_drone`, `L_goldentee_hat`, `L_toat_machine_hat`, `L_toat_beanie` | 0 | 139, 101, 127, 127 | - | - | - | - |

Pooled over the 7 items with pins, 20 pins:

| radius | hit | chance (area) | diff | kappa | 95% CI (items) | chance (edge) | diff | 95% CI |
|---|---|---|---|---|---|---|---|---|
| **3.0 (verdict)** | **0.60** | **0.49** | **+0.11** | **0.21** | **[-0.04, +0.21]** | 0.48 | +0.12 | [-0.07, +0.25] |
| 2.0 (sensitivity) | 0.55 | 0.32 | +0.23 | 0.34 | [+0.00, +0.37] | 0.37 | +0.18 | [-0.07, +0.35] |
| 5.0 (sensitivity) | 0.80 | 0.75 | +0.05 | 0.20 | [-0.18, +0.16] | 0.68 | +0.12 | [-0.12, +0.26] |

The 2.0 mm area-null row's lower bound is +0.0035. That is a sensitivity row,
and the pre-registration says the verdict is read at 3.0 only. With 7 items it
is the kind of edge a re-pick of the radius would manufacture, so it is not
the result.

**Why chance is so high.** The reader flags 28-226 spots per design (1,239 in
all), so on a busy logo most of the stitched area has a flag within 3 mm.
Only 23 of the 738 flags on the 7 pinned items lie within 3 mm of a relevant
pin. That is not a precision figure: Kent pins the salient spots, not every
one. But it means a "hit" here mostly says that a flag was nearby anyway.

## The pins it missed (nearest flag)

- **Tires 1, 2, 3** (4.9, 5.7, 6.3 mm). "Jagged edges don't look clean
  (marks 1-4 are the same issue)." The scalloped edge he means runs along
  every stroke of the script evenly. The reader flags only spots that stand
  out from their neighbours after the 3 mm high-pass: column ends, joins and
  the i's dot. **A fault that is uniform along an edge is removed by the
  high-pass.** That is how the instrument was designed ("a constant standoff
  is pull compensation"), and here it hides the very fault Kent pinned.
- **ProSeal 4** (10.4 mm). "The M is jagged." This is the M in the small
  "SPRAY FOAM" line, and the reader puts **no flag on any of that small
  lettering**. Series shorter than `MIN_SERIES` 8, or ends it cannot read, are
  skipped, so small text is not read at all.
- **Fremont 4** (5.7 mm). "All of the letters edges are jagged." Kent says
  the fault is all over; this is one pin placed on it.
- **MFab 2** (4.3 mm). "It isn't straight like the photo." A straight edge
  sewn with a slow bow sits under the 3 mm baseline, so the high-pass removes
  it as well.
- **Becker 11, 12** (3.1, 3.5 mm). "The letters should be flat." Just outside
  the radius. The 5 mm row counts them, and that row's chance rises with it.

## Flags Kent did not pin

The strongest flags on every item are satin **column ends**: 195 `end`, 313
`corner`, 168 `mid` and 533 fill row ends across the 11 items. Almost none of
them have a pin of any kind within 3 mm. Examples: Gaulke's 1.52 mm flag at
(72.4, 30.0), Becker's 1.02 mm fill flag at (13.5, 41.1), Tires' 1.15 mm
flag at (93.7, 28.7). Kent looked at these renders and did not call these
spots faults. On this evidence, the reader's largest deviations are what
column ends do, not what he sees as jagged. The 10 strongest unpinned flags
per item are in `edge-reader-score.json` under `unpinned`.

On the 4 logos with no edge pin (Drone, Golden Tee, both TOAT jobs), the
reader still flags 101-139 spots each. Kent's silence is not proof that those
edges are smooth (he pins salient faults), so no precision is claimed.

## What this changes

1. **Do not use `edge_wobble`'s flagged locations, or its per-tier numbers,
   as a stand-in for "Kent will call this edge jagged".** Its strongest
   readings sit at column ends he did not pin, and it misses the even scallop
   and the small text he did. The preflight metrics stay as they are: they
   are reported, never judged, and nothing here flips a default.
2. **A second edge reader needs a different input, not a new threshold.**
   Three things in the misses point there. The scallop he calls jagged is
   uniform, so a reader has to measure the edge's absolute roughness, not
   its deviation from a local baseline. Small lettering has to be read. And
   on Becker and MFab the outline itself follows low-resolution art ("the
   border is jagged, but it matches the photo quality"), which a
   stitch-vs-outline instrument cannot see by construction. Tuning `OVER_MM`
   or the radius against these 20 pins would only fit noise.
3. **The harness is the reusable part.** The next reader is **closed or
   merged letters** (15 pins on 6 logos, SITTING.md), scored with the same
   harness under its own pre-registration.

## Reproduce

From `digitizer/` in a lane, with the primary checkout on `950855bf` and its
venv:

    python -m tools.edge_fault_reader run --pro-run <primary>/digitizer/eye_pairs_out/defect-marks-1110/pro_run \
        --out <primary>/digitizer/eye_pairs_out/defect-marks-1110/edge_reader --tree <primary>/digitizer
    python -m tools.fault_reader_harness score --marks ../docs/defect-marks-2026-11-10/marks.json \
        --flags <primary>/digitizer/eye_pairs_out/defect-marks-1110/edge_reader

The run takes about 7 minutes for 11 jobs, one at a time. The `pro_run`
job outputs and the masks are gitignored on Kent's machine; a cloud session
has neither.
