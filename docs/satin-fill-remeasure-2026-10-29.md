# Defect 5 re-measured: satin-vs-fill routing on today's main (2026-10-29)

**Measured on main `44ecf1cb`**, 22 paired jobs (`tools.pro_baseline.JOBS`), each
digitized once per arm with the Studio's request at the pro's width and garment.
Instrument: `digitizer/tools/satin_fill_census.py` (this PR; `table` prints every figure below). Every figure is
chance-corrected (ROADMAP gate 4); no raw agreement is quoted. No pro render is
committed.

**Verdict up front.**

1. **Routing is no longer at chance, and a better per-region router has nothing
   left to buy.** Mean stitch-type kappa 0.387 over 21 jobs. An oracle that
   gives each of OUR regions the pro's majority type scores **0.365**, beating
   today's routing on only 10 of 21 jobs. In August the same oracle sat 21
   points above us (raw, 76.6 against 55.4); today it sits below.
2. **The cell kappa is capped by the instrument well short of 1.** The pro's
   own file, read against itself 0.5 mm off, scores **0.650**; 1.0 mm off,
   **0.415**. Our 0.387 is measured against that ceiling, not against 1.
3. **Per shape, by area, we agree with the pro at 0.77**, against the tier
   reader's own **0.80** on our plan, where the truth is known. The
   count-weighted figure (0.17) is the reader's noise on small shapes, not
   routing: the same reader scores our own known plan at 0.22 by count.
4. **The segmentation verdict stands, for a different reason.** The straddle
   is still 96% "speckle" by `splitprobe`'s classes. But only 21% of the
   minority cells are single cells, and 33% sit in blobs of 10 or more cells
   (40 mm² and up). Those blobs are in a dozen large GROUND regions, where the
   pro sews pieces of another type inside what we sew as one field. That is
   layering construction, owned elsewhere (`silhouette_underfill`, the
   layering census). It is not grid noise, and a region splitter would not
   reach it.
5. **`satin_per_stroke`: recommend it stays OFF.** It is a wash on every
   number: 13 of 22 jobs byte-identical, mean kappa +0.002, bare cloth
   unchanged on all 22. It buries the drone's crosshair arm under wide grey
   satin, and fans Becker's bowl where the pro sews parallel satin. The
   2026-10-20 reading (8.3 against 6.8 mm² bare) no longer reproduces.

## 1. Per job

`sttype kappa` is `pro_parity.scorecard`'s, byte for byte (`pro_baseline.kappas`),
with its chance floor. `oracle` is the same cells with every cell owned by one
of our sewn regions relabelled to the pro's majority type there. A cell belongs
to the SMALLEST sewn region over it, the one sewn on top: in list order a
ground (Fremont's 2,137 mm² field) claimed every cell. `pro vs pro` is the
pro's type map against itself shifted 0.5 / 1.0 mm on both axes. `straddled` is
the share of graded cells in regions under 75% one pro type.

| job | sttype kappa (chance) | oracle | pro vs pro 0.5 / 1.0 mm | straddled |
|---|---|---|---|---|
| bridge_hat | 0.14 (0.49) | 0.45 | 0.61 / 0.36 | 50% |
| bridge_lc | 0.10 (0.49) | 0.46 | 0.67 / 0.40 | 63% |
| becker_hat_large | 0.29 (0.53) | 0.44 | 0.74 / 0.39 | 83% |
| becker_lc_large | 0.35 (0.51) | 0.49 | 0.69 / 0.54 | 82% |
| becker_hat_small | 0.55 (0.50) | 0.61 | 0.70 / 0.51 | 53% |
| becker_chest_small | 0.60 (0.50) | 0.63 | 0.70 / 0.51 | 54% |
| becker_beanie | 0.24 (0.56) | 0.12 | 0.62 / 0.40 | 84% |
| gaulke_roofing_hat | 0.14 (0.84) | 0.01 | 0.50 / 0.29 | 14% |
| gaulke_roofing_lc | 0.29 (0.87) | 0.00 | 0.48 / 0.20 | 15% |
| gaulke_roofing_beanie | 0.31 (0.51) | 0.41 | 0.58 / 0.40 | 52% |
| hotel_fremont_hat | 0.54 (0.43) | 0.46 | 0.78 / 0.45 | 74% |
| hotel_fremont_patch | 0.52 (0.43) | 0.06 | 0.76 / 0.49 | 77% |
| mfab_hat | 0.55 (0.48) | 0.56 | 0.69 / 0.48 | 53% |
| mfab_lc | 0.56 (0.49) | 0.60 | 0.70 / 0.60 | 50% |
| precision_drone | 0.38 (0.50) | 0.34 | 0.69 / 0.51 | 63% |
| proseal_hat | 0.20 (0.78) | 0.05 | 0.56 / 0.38 | 11% |
| proseal_beanie | 0.40 (0.47) | 0.45 | 0.63 / 0.25 | 52% |
| tires_hat_3d | 0.00 (0.51), undefined | - | - | 0% |
| goldentee_hat | 0.84 (0.62) | 0.82 | 0.76 / 0.54 | 25% |
| toat_machine_hat | 0.32 (0.57) | 0.22 | 0.56 / 0.33 | 96% |
| toat_machine_beanie | 0.38 (0.58) | 0.27 | 0.63 / 0.38 | 83% |
| toat_beanie | 0.44 (0.55) | 0.23 | 0.60 / 0.32 | 96% |
| **mean of 21** | **0.387** | **0.365** | **0.650 / 0.415** | |

`tires_hat_3d` is left out of the means. The pro sews it as one type, so its
side of the chance floor is degenerate and its kappa says nothing either way.

**Why the oracle can sit BELOW us.** One label per region collapses the type
mix a region carries (a satin edge cap on a fill, a border tier, a split satin
reading as fill in one cell). The chance floor then rises: Fremont patch 0.43
→ 0.61, the drone 0.50 → 0.63, ProSeal hat 0.78 → 0.89. Where we beat the
oracle, our sewn map varies INSIDE a region the way the pro's does. That is
construction, and a region label cannot express it. Gate 4 exists for exactly
this: by raw agreement the oracle would read as the higher number.

## 2. Per shape (`tier_census`'s reader, both files)

Each of our shapes is read twice, through ours and through the pro's DST, by
the same stitch reader (FILL / SATIN / SPLIT / RUN; BAR left out as
undecidable). Ours is taken from the PLAN, where the truth is known. Shapes
with another sewn region inside them are left out (grounds read the pro's
letters on top).

| population | kappa by area | kappa by count | n |
|---|---|---|---|
| all shapes | 0.77 | 0.17 | 531 |
| lettering | 0.87 | 0.26 | 324 |
| the rest | 0.73 | 0.08 | 207 |
| **the reader on OUR plan (its own error)** | **0.80** | **0.22** | 553 |

By count the reader disagrees with our own known plan on most small shapes
(0.22), so the count column measures the reader, not routing. By area routing
sits at 0.77 against a reader ceiling of 0.80.

Misroutes by area (ours → pro): ours satin, pro fill 970 mm² (76 shapes); ours
fill, pro satin 1,084 mm² (15 shapes); ours satin, pro run 999 mm² (40 shapes);
agreeing 28,618 mm². Still both directions, at about 1,000 mm² each, against
the reader's own error of the same order.

## 3. Segmentation: the 2026-08-17 verdict re-checked

`splitprobe.classify_straddle` on today's tree, over the regions' OWNED cells:

| pattern | shapes | cells | share of straddled |
|---|---|---|---|
| speckle | 58 | 6,599 | 96.2% |
| split | 70 | 256 | 3.7% |
| ring | 1 | 8 | 0.1% |
| pure | 495 | 3,478 | |

The classes reproduce August's (95.8 / 3.8 / 0.4). Their reading does not.
"Speckle" means more than two connected blobs per type, and says nothing about
blob size. Here is the minority type's blob size inside straddled regions:

| blob (2 mm cells) | 1 | 2-3 | 4-9 | 10+ |
|---|---|---|---|---|
| minority cells | 521 (21%) | 585 (23%) | 588 (23%) | 825 (33%) |

The 10+ blobs sit in 12 regions, every one a ground or a large field:
Fremont's field (232 cells on the patch), To a T's 3,074 mm² field (97 / 90 /
67), MFab's silhouette (72 / 40), and Becker's slab (54 / 35). Inside each, the
pro sews pieces of another type that we sew as part of one field. That is the
layering the layering census found (W4-06: the pro sews every contained piece
ON its ground), not cell noise. The grid noise is real too: the pro against
himself 0.5 mm off loses a third of kappa (0.650).

**So: still do not build the region-level fix**, because the oracle above says
a perfect per-region label buys nothing (0.365 against 0.387). What is left
lives inside regions (edge caps, border tiers, split satin) and under them
(grounds). Defect 26's threshold cures were not retried.

## 4. `satin_per_stroke` OFF | ON (flip proposal)

The same 22 jobs, `--set satin_per_stroke=true`. Bare is preflight's
`uncovered_total_mm2` (worst patch in brackets), the figure the flag's guard
test reads.

| job | identical | moved | kappa OFF / ON | stitches OFF / ON | trims OFF / ON | bare mm² OFF / ON |
|---|---|---|---|---|---|---|
| bridge_lc | no | fill→satin 6.3 mm² | 0.10 / 0.13 | 11,322 / 11,422 | 23 / 23 | 0.0 / 0.0 |
| becker_hat_large | no | fill→satin 23.5 | 0.29 / 0.29 | 16,053 / 16,012 | 14 / 14 | 14.7 / 14.7 |
| becker_lc_large | no | fill→satin 20.7 | 0.35 / 0.35 | 14,585 / 14,540 | 17 / 17 | 11.6 / 11.6 |
| becker_hat_small | no | fill→satin 12.9 | 0.55 / 0.55 | 10,270 / 10,247 | 15 / 15 | 6.0 / 6.0 |
| becker_chest_small | no | fill→satin 12.9 | 0.60 / 0.60 | 10,033 / 10,010 | 15 / 15 | 6.0 / 6.0 |
| mfab_hat | no | fill→satin 12.7 | 0.55 / 0.56 | 20,677 / 20,763 | 19 / 19 | 0.0 / 0.0 |
| precision_drone | no | 4 shapes fill→satin, 50.1 | 0.38 / 0.35 | 14,491 / 14,610 | 93 / 90 | 0.0 / 0.0 |
| proseal_hat | no | fill→satin 21.1 | 0.20 / 0.21 | 6,317 / 6,244 | 37 / 39 | 0.0 / 0.0 |
| proseal_beanie | no | fill→satin 16.1 | 0.40 / 0.41 | 8,157 / 8,106 | 32 / 33 | 0.0 / 0.0 |
| the other 13 | **byte-identical DST** | - | same | same | same | same |

Mean kappa over 21 jobs 0.387 → 0.389. Per-shape area kappa 0.769 → 0.772.
Promotion-only held: no shape lost satin.

**The guard's figure, re-read.** On Becker @ 100 mm left chest (the flag
test's fixture), today's defaults leave **14.4 mm² bare with it OFF and 14.4
ON** (worst 4.0 both). On the test's own pin (`subpixel_corner_runs` pre-flip)
it reads 13.6 / 13.6. The 10-20 reading of 8.3 against 6.8 no longer
reproduces: the flips since have moved Becker (one shape satins ON, −43
stitches).

**Renders** (`docs/renders/satin-per-stroke-2026-10-29/`, OFF | ON around
every moved shape; the pro's crops are local in `pro_renders/`, Kent
2026-10-27):

- **mfab_hat**: a white piece of the N goes satin, as the pro sews it. Toward
  him.
- **proseal_hat / beanie**: one hexagon goes satin; the pro's hexagons are
  satin. Toward him.
- **becker (four sizes)**: a bowl goes from fill to satin, but its crosses
  FAN from one point, where the pro sews it as parallel satin. The tier moves
  toward him; the look does not.
- **precision_drone**: two ground pieces (29.0 and 14.9 mm²) go to wide grey
  and orange satin, sewn after the white crosshair arm and **burying it**. The
  pro fills that ground and keeps the arm on top. Away from him, and visible.
- **bridge_lc**: a 6.3 mm² brown piece, hard to see at any size.

**Proposal: keep OFF.** The measurable gain is +0.002 kappa, with no bare
cloth either way. The one visible change on a whole design (the drone) is a
regression, and Becker's bowl trades a fill for a fan. Flipping it is Kent's.

## Rebuild

From `digitizer/`, on the head to be measured (`EMB_SCRATCH_KENT`,
`EMB_BRIDGE_PRO` set as in `tools/pro_baseline.py`):

```
python -m tools.satin_fill_census digitize --runs OFF
python -m tools.satin_fill_census digitize --runs ON --set satin_per_stroke=true
python -m tools.satin_fill_census measure --runs OFF      # and ON
python -m tools.satin_fill_census table --runs OFF --vs ON
python -m tools.satin_fill_census flip --runs OFF --vs ON
python -m tools.satin_fill_census render --runs OFF --vs ON --out ../docs/renders/NAME
```

One digitize per job per arm: 22 jobs took 63 minutes of digitizing on the
OFF arm (Fremont and MFab hat over 6 minutes each), plus preflight, on Kent's
laptop with two other sessions' runs on it.
