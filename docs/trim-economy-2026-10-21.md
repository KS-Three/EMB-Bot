# Trim economy: why we cut ~1.7x the pro's trims, and the one rule built (2026-10-21)

Study first, then one flag, built OFF. Follows PR #1026
(`docs/pro-digitizer-rules-2026-10-21.md`, its R14: "fewer trims than ours,
median ours/pro 1.7 over ten paired jobs"). Kent asked on 2026-10-21 to build
every cross-job rule; this is the trim one.

## What was measured

The ten jobs that have both committed artwork and the pro's DST, ours
digitized through `tools/pro_pair.py`'s path (the Studio's request through the
service parser) at the pro's own width and garment, on `main` at `2e873933`:

| job | art | pro DST | mm | garment |
|---|---|---|---|---|
| Fremont patch | `art/logo_hotel_fremont_patch.png` | `HOTEL FREMONT .DST` | 92.5 | patch |
| Becker large | `becker_marine_logo.png` | `beckers logo hat.DST` | 101.9 | hat_front |
| Becker small | `becker_marine_logo.png` | `beckers logo hat 2 A.DST` | 76.5 | hat_front |
| Golden Tee | `photo/logo_golden_tee.jpg` | `GOLF HAT.DST` | 74.9 | hat_front |
| Roofing | `art/logo_golke_roofing.png` | `c golke logo hat.DST` | 114.2 | hat_front |
| Drone | `photo/logo_drone_thermal_badge.png` | `PRECISION DRON HAT 2.DST` | 62.6 | hat_front |
| Tires | `logo_script_tires.png` | `TIRES HAT 3D.DST` | 114.3 | hat_front |
| MFab | `art/logo_mfab_hat.png` | `mf4b logo hat.DST` | 104.9 | hat_front |
| Machine | `art/logo_toat_machine.png` | `Machine HAT.DST` | 89.5 | hat_front |
| To a T beanie | `art/logo_toat_beanie.png` | `To a T Beanie.DST` | 82.3 | beanie |

Fremont here is the patch artwork, so our count (78) is higher than #1026's 45,
which was read from a different input; every other row matches #1026 exactly. Pro-only rows (Plowing, Proseal) are classified too, but enter no ratio.

**Instrument: `digitizer/tools/trim_classes.py`, new.** It reads any machine
file and treats both sides the same way, so it reads DSTs only (the PES reader
reports a TRIM at every jump). Each trim is one hop, from the last penetration
before the cut to the first after it. The tool samples the hop's straight line
every 0.1 mm against a raster of every needle-down segment, drawn one thread
(0.4 mm) wide and stamped with its sew index:

- **colour**: a colour change between the two penetrations.
- **under_later**: at least 90% of the line lies under thread sewn after the
  hop, so travel there would have been hidden.
- **on_work**: at least 90% lies under thread, but not later thread, so travel
  there would sit on top of finished work.
- **bare_letters**: on fabric, between two separate letter-sized pieces (pieces
  20 mm or less on a side).
- **bare_other**: on fabric, anything else.

Both DST writers put no TRIM before a colour stop, so `colour` reads 0 on both
sides. Colour changes are counted separately, as #1026 did.

## The classification

| job | pro | ours | under_later pro/ours | on_work | bare_letters | bare_other |
|---|---|---|---|---|---|---|
| Fremont patch | 20 | 78 | 0 / 13 | 20 / 64 | 0 / 0 | 0 / 1 |
| Becker large | 9 | 27 | 0 / 4 | 5 / 3 | 4 / 7 | 0 / 13 |
| Becker small | 10 | 15 | 1 / 0 | 4 / 2 | 5 / 6 | 0 / 7 |
| Golden Tee | 9 | 30 | 0 / 6 | 1 / 10 | 0 / 0 | 8 / 14 |
| Roofing | 41 | 33 | 0 / 2 | 2 / 5 | 18 / 13 | 21 / 13 |
| Drone | 58 | 112 | 6 / 12 | 32 / 66 | 1 / 10 | 19 / 24 |
| Tires | 9 | 9 | 1 / 0 | 0 / 0 | 0 / 0 | 8 / 9 |
| MFab | 18 | 59 | 1 / 4 | 17 / 20 | 0 / 0 | 0 / 35 |
| Machine | 30 | 46 | 0 / 2 | 30 / 14 | 0 / 3 | 0 / 27 |
| To a T beanie | 30 | 40 | 0 / 0 | 30 / 14 | 0 / 6 | 0 / 20 |
| **total** | **234** | **449** | **9 / 43** | **141 / 198** | **28 / 45** | **56 / 163** |
| pro only: Plowing hat | 50 | — | 1 | 17 | 19 | 13 |
| pro only: Proseal hat | 53 | — | 2 | 14 | 26 | 11 |

Ours over pro: median **1.73** (#1026: 1.7). The excess is 215 trims. Per class:
`bare` +124, `on_work` +57, `under_later` +34.

Our side has a second reading, from our own plan, which knows each trim's
shapes. Of 478 plan trims (29 of them colour stops):

- **in a shape**: 131, of which 32 are `under_later`. These are fill-underlay
  hops and fill bridges whose own later rows cover them (Fremont's field: 13).
- **between shapes**: 308.
- **the edge cap**: 39. Each stretch of the silhouette cap is cut on its own.

### What explains the gap, class by class

1. **`under_later` (+34): the one difference that is a trim POLICY.** The pro
   almost never cuts a hop that later thread will cover: 9 such cuts over the ten
   jobs, and 1-2 on the pro-only jobs. He travels under the work. We cut 43,
   mostly inside a shape (32): underlay legs and fill bridges that the shape's
   own top rows bury, and between-shape hops that a later colour buries. This
   is the habit #1026 described as "travels where a fill sits underneath".
2. **`bare` (+124): mostly not a trim policy. It comes from leaving white as
   fabric.** On Machine, To a T and MFab the pro has **zero** bare trims; we have
   91 between them. He sews the white badge field and the white letters (#1026
   R11), so every hop lands on work. We leave those areas as fabric, so the
   pieces are islands. That is a design change (R11, its own build, the
   "sew white interiors" option), not something a trim rule can recover. Most
   of the rest is in-shape satin hops across a letter's own gaps (Becker,
   Golden Tee) and the edge cap's stretches.
3. **`on_work` (+57): fragmentation.** The pro cuts on-work hops too (141 of his
   234), so the question here is not "cut or travel" but how many pieces there
   are. Fremont alone is +44: field bridges cut by `fill_bridge_cut` (ruled ON
   2026-09-19 because that travel would show on finished fill), letters on the
   field, and 11 edge-cap stretches. Drone is +34, the photo lane's region
   count.
4. **`bare_letters` (+17): small, and the pro does it too.** He cuts between
   letters on bare fabric: Roofing 18, Plowing 19, Proseal 26, against our
   Roofing 13. Our between-letter cuts are not the gap. Roofing is the one job
   where we cut fewer than the pro (33 vs 41).

### What memory says has been tried, and how it relates

- **Distance is not the variable** (`pro-trim-threshold`). The pro cuts from
  1.9 mm and leaves no needle-up move uncut in his DSTs; the note's old "floats
  up to 16.1 mm" was a needle-DOWN stitch 7.5 mm or more long (a `hop` in
  `beckers logo hat.PES`), not a jump (`docs/settings-vs-pro-2026-10-21.md`).
  This study agrees: what separates his cuts from his travel is cover, not
  length. His median cut hop is 6.8-18.8 mm per job, ours
  4.9-15.9 mm.
- **`chain_links`** (-33% on real logos; gate 1 and gate 3, OFF). It routes a
  link under a later colour's POLYGON (eroded by `LINK_COVER_INSET_MM`) or on
  top of this colour's ALREADY-SEWN thread. The second half is travel on top of
  finished work, which the pro does not do (he cuts those, `on_work` 141). The
  new rule is the narrow half: under later thread only, real stitches only.
- **`fill_travel_under_cover`** (ON) and **`fill_bridge_cut`** (ON). These order
  and route fill columns inside one shape, and lift a bridge that would show on
  finished fill. The new rule leaves those lifts alone unless later thread buries
  the hop. Example: a field bridge across a hole that a later letter fills.
- **`satin_hop_under_column`** (OFF). This is the underlay-to-own-column case
  inside satin, and it is a strict subset of what the new rule covers in any
  tier.
- **`real-artwork-trim-truth`** said real logos are "shape-ENTRY" trims, with the
  fill tier essentially never cutting. That was read on the vendor renders and is
  tainted (its 2026-08-23 correction). On genuine art, 32 of our 43 buried-able
  cuts are inside a shape: fill underlay and bridges.

## The rule: `cfg.trim_bury_under_later` (built OFF)

`stage7_sequence._bury_trims_under_later` runs once over the artwork blocks,
after the same-thread merge and hoist and before the ties. When thread sewn after
it covers a cut hop inside a colour block, it sews the hop needle-down as a TRAVEL
run. "Thread sewn after" means every non-travel run sewn later, in this block and
in every later artwork block.

- **Cover is real stitches, never a polygon.** Each later run's centreline is
  read at half `COVERAGE_THREAD_W_MM`. The travel is sampled every 0.1 mm at its
  centre and at both thread edges, and every sample must lie within half a thread
  of a later centreline. That covers the whole thread, not just the centreline.
- **Nothing on bare fabric, nothing on top of finished work.** The one allowance
  is one thread width around the two penetrations the hop starts and ends on.
  There, the previous run's own last stitch also counts.
- **Straight first, then bent.** A raster (20 px/mm, the later thread eroded by
  half a thread plus the simplify margin) PROPOSES a geodesic route. The exact
  sampled test then DECIDES every leg. The raster can lose a route; it cannot
  pass one.
- **Chaining's own laws, no new constant.** Routes are kept within
  `LINK_MAX_GAP_MM` and `_link_budget_mm`, and stitched by `_link_stitches` at
  `RUN_STITCH_MM`. The 0.1 mm sample step and the 20 px/mm grid are search
  resolutions, not tolerances.
- **The first run of a block is never touched**, because that cut is a colour
  change. Later passes (edge cap, hairlines, spoke marks) only append or insert
  blocks, so "later" stays later. Their thread is not counted as cover, which is
  the cheap direction to be wrong in.

### Measured, OFF vs ON, the same ten jobs

DST trims read by `trim_classes.py`; stitches from the plan; travel exposure
read off the plan on a 10 px/mm raster (needle-down TRAVEL with no thread at
all under it, and with only earlier thread under it).

| job | pro | OFF | ON | ours/pro OFF -> ON | under_later OFF -> ON | stitches OFF -> ON | travel bare / on top, mm |
|---|---|---|---|---|---|---|---|
| Fremont patch | 20 | 78 | 67 | 3.90 -> 3.35 | 13 -> 3 | 23,773 -> 23,737 | 0.0 / 71.1, unchanged |
| Becker large | 9 | 27 | 24 | 3.00 -> 2.67 | 4 -> 1 | 9,432 -> 9,423 | 33.1 / 58.0, unchanged |
| Becker small | 10 | 15 | 15 | 1.50 -> 1.50 | 0 -> 0 | 5,946 -> 5,946 | 11.4 / 55.8, unchanged |
| Golden Tee | 9 | 30 | 23 | 3.33 -> 2.56 | 6 -> 0 | 8,365 -> 8,345 | 48.9 / 18.2, unchanged |
| Roofing | 41 | 33 | 31 | 0.80 -> 0.76 | 2 -> 0 | 8,192 -> 8,185 | 55.9 / 102.3, unchanged |
| Drone | 58 | 112 | 98 | 1.93 -> 1.69 | 12 -> 2 | 14,842 -> 14,815 | 27.0 / 141.5, unchanged |
| Tires | 9 | 9 | 8 | 1.00 -> 0.89 | 0 -> 0 | 8,075 -> 8,076 | 0.0 / 25.1, unchanged |
| MFab | 18 | 59 | 52 | 3.28 -> 2.89 | 4 -> 0 | 12,192 -> 12,202 | 9.7 / 41.9, unchanged |
| Machine | 30 | 46 | 44 | 1.53 -> 1.47 | 2 -> 0 | 8,740 -> 8,728 | 9.1 / 2.9, unchanged |
| To a T beanie | 30 | 40 | 40 | 1.33 -> 1.33 | 0 -> 0 | 6,740 -> 6,740 | 4.6 / 3.9, unchanged |
| **total** | **234** | **449** | **402** | **median 1.73 -> 1.59** | **43 -> 6** | -100 net | **+0.0 / +0.0** |

So ON removes 47 cuts (10.5%) and closes 22% of the 215-trim excess. It lays
not one millimetre of travel on bare fabric or on finished work that OFF did
not already lay. Stitches fall by 100 net, because each lifted cut also drops
its two locks. The travel exposure that is already there (Roofing's 55.9 mm
bare, for example) is stage 6's own in-shape travel; it is the same OFF and ON.

Two things the first draft of the rule got wrong, both found by measuring:

- An end allowance of "one thread width round each penetration, whatever is
  there" showed up as +0.1 mm bare and +0.2 mm on top on Becker. Now, within
  that width, only the previous run's own thread counts.
- Eroding a union of later thread by half a thread made GEOS return an empty
  polygon on a 33-row band. The pass now samples the travel's own edges
  against an STRtree instead. That is also 17-75x faster: on Kent's loaded
  laptop the pass costs 1-12 s per design, against 50-300 s for the pipeline.

Runtime: ON adds about 5-10% to the pipeline.

Renders, OFF and ON side by side, our stitches only:
`docs/renders/trim-economy-2026-10-21/golden_tee_off_on.png` and
`drone_off_on.png`. In the OFF panel, dashed blue marks every cut inside a
colour block. In the ON panel, red marks the hops the flag now sews. The red is
drawn on top so it can be seen; on cloth it lies under the later fill (GOLF's
letters, the T's stem, the drone's dome).

**OFF is byte-identical.** All ten `ours.dst` md5s match between a pre-change
run and a post-change run (for example Fremont `dac6bf81…`, Becker large
`e8b62499…`, Drone `bd4d626c…`). The unit fixtures are pinned to
md5s captured on the base commit (`tests/test_trim_bury_under_later.py`).

### What it does not do, and why the gap stays open

ON closes 47 of the 215-trim excess (22%). The rest is not trim policy:

- White left as fabric (R11): 91 bare cuts on Machine, To a T and MFab.
  This is the "sew white interiors" option, a design change.
- Fragmentation: Fremont's field and letters, and the photo lane's region count
  on Drone.
- The edge cap, cut stretch by stretch: 39 trims. `edge_cap_fold_into_colour`
  (OFF) already moves stretches into their host's block. A fold or chain for the
  cap is the next trim lever this table points at.

## Gates

- **Gate 3 (chaining).** This is needle-down thread that a later pass is
  trusted to hide, so it is a chaining-class tier. It is built OFF. A flip needs
  the instrument, and this PR ships one: `trim_classes.py` reads the cuts, and
  the invariant test re-measures every buried leg against the real later thread.
- **Gate 1.** No new physical constant. One question is still for cloth: does a
  0.4 mm travel under dense fill, or under 0.40 mm satin, show? It matters most
  for dark thread under light satin. `chain_links` waited on the same question.

Scratch scripts (digitize-and-dump, the plan-side reading, the travel-exposure
raster) lived in the session scratchpad. The tables reproduce with
`tools/trim_classes.py` over `tools/pro_pair.py`'s `ours.dst` at the widths
above.
