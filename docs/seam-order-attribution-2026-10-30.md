# What `fill_seam_order` costs, and where (2026-10-30)

Kent flipped `fill_seam_order` ON on 2026-10-30 (#1198) from the Instagram-led
sheet. Re-reading a held flag on that base showed it moved two jobs the wrong
way. Kent's ruling: "Render and attribute (Recommended)". The flag stays ON.

Sheet: [`flip-sheet-seam-order-2026-10-30.md`](flip-sheet-seam-order-2026-10-30.md).
The pro's panels are local, in `pro_renders/`.

## Results

| | seam order OFF | seam order ON (main) | ON + both switches | pro |
|---|---|---|---|---|
| Becker beanie cuts | 12 | 14 | 14 | 4 |
| Becker beanie exposed mm | 38.6 | **105.8** | 38.6 | |
| Becker beanie bare mm, 0.20 / 0.25 / 0.30 | 3.72 / 0.4 / 0 | **14.84** / 0 / 0 | 3.72 / 0.4 / 0 | |
| Drone cuts | 87 | **93** | 86 | 58 |
| Drone exposed mm | 20.0 | 23.6 | 22.0 | |
| Drone bare mm, 0.20 / 0.25 / 0.30 | 2.54 / 2.12 / 1.27 | 2.20 / 1.79 / 0.95 | 2.54 / 2.12 / 1.27 | |
| MFab LC cuts | 25 | 21 | 22 | 19 |
| MFab LC exposed mm | 38.7 | 19.8 | **10.8** | |

## Cause 1: Becker beanie is one walk in the knockdown

The beanie's whole rise is one TRAVEL run in the `knockdown` shape:

- OFF, 38.7 mm, 10.6 of it exposed.
- ON, 77.9 mm (chord 69.6), all of it exposed: 63.0 on its own fill, 14.8 on
  fabric.
- That is the job's whole exposed rise (+67.2 mm) and whole bare rise.

`knockdown._stay_down` turns every lift inside the knockdown into a walk,
because the pro's knockdown never trims. So when seam order re-sequences the
field's sections, the longer hop cannot be cut: it is sewn, however long.

How much this matters:

- It is garment-coloured thread on the garment, in a sparse fill, so it is
  hard to see.
- The bare rise is in the 0.20 band only. At 0.25 and 0.30 ON reads 0, so that
  walk lies within a quarter millimetre of a knockdown row.
- It is still 39 mm of thread with no job to do.

**A blanket skip is wrong. ProSeal beanie goes the other way:** seam order ON
gives 150.5 mm exposed and 100.25 mm bare; with the knockdown held out of seam
order, 297.8 and 118.36. So `knockdown_shorter_walk` sews the knockdown both
ways and keeps the shorter walk.

Becker beanie's other +2 cuts are in its field, `S51503c0c`, and the switch
does not reach them.

## Cause 2: the drone's +6 cuts are the chord picking the wrong way round

`_order_for_seams` builds two valid progressions and sews the one with the
shorter flown chord. The chord cannot see a section walled in behind finished
fill, and `fill_bridge_cut_exposed` then cuts that hop. On the drone:

| shape | fill-section cuts, seam OFF -> ON |
|---|---|
| `Sb5e7d7ed` | 1 -> 7 |
| `S09963415` | 3 -> 6 |
| `S1f7420c4` | 1 -> 4 |
| `S00c2fb94` | 2 -> 0 |
| `Sefc0e086` | 3 -> 1 |

Choosing the other progression takes the drone to 86 cuts, one under seam
order OFF.

**A first build of `fill_seam_order_priced` let `_score` choose outright, and
it put flips back:** Becker beanie 0 -> 6, Becker hat large 0 -> 2. Those flips
are part of why Kent flipped seam order. So the switch reads the lay first
(`_seam_faults`: ridges plus flips), and `_score` only settles a tie.

## What the chord left behind

Read on the order leaving `_order_for_seams`, per job:

| | ridges | flips |
|---|---|---|
| incoming order, the 15 jobs read | 324 | 810 |
| main (chord), 17 pairs | 1 | 59 |
| `fill_seam_order_priced`, 17 pairs | **0** | **2** |
| main (chord), 5 logos | 5 | 28 |
| `fill_seam_order_priced`, 5 logos | **0** | **0** |

Seam order was already doing most of the work. The switch finishes it: on the
chord, Becker small had 15 flips left and the crest 5 ridges and 25 flips.

## Both switches, every job

Cuts / exposed mm / bare mm at 0.20. Pairs not listed are byte-identical.

| job | main | ON | pro cuts | note |
|---|---|---|---|---|
| becker_beanie | 14 / 105.8 / 14.84 | 14 / 38.6 / 3.72 | 4 | bare at 0.25 rises 0 -> 0.4 |
| precision_drone | 93 / 23.6 / 2.20 | 86 / 22.0 / 2.54 | 58 | **bare rises at all three bands, +0.34** |
| becker_lc_large | 15 / 31.1 / 0.40 | 12 / 31.1 / 0.40 | 11 | |
| becker_hat_small | 11 / 21.7 / 4.61 | 11 / 21.7 / 4.61 | 10 | flips 15 -> 0 |
| becker_chest_small | 11 / 21.3 / 4.82 | 11 / 21.3 / 4.82 | 11 | flips 15 -> 0 |
| mfab_lc | 21 / 19.8 / 0.0 | 22 / 10.8 / 0.0 | 19 | |
| mfab_hat | 25 / 6.0 / 0.0 | **29** / 7.9 / 0.0 | 18 | **+4 cuts** |
| proseal_hat | 36 / 17.8 / 1.56 | **38** / 13.7 / 1.56 | 53 | |
| Instagram | 13 / 32.0 / 0.0 | **7** / 30.3 / 0.0 | | |
| emoji | 12 / 0.9 / 0.0 | 11 / 0.5 / 0.0 | | |
| silhouette | 21 / 9.2 / 0.0 | 18 / 10.6 / 0.0 | | |
| isometric | 15 / 6.1 / 0.0 | 16 / 5.6 / 0.0 | | |
| heraldic crest | 161 / 47.1 / 0.1 | **176** / 61.7 / 0.1 | | **+15 cuts, +14.6 mm** |

Totals, 17 pairs: cuts 399 -> 396 (pro 409), exposed 509 -> 429 mm. Totals, 5
logos: cuts 222 -> 228, exposed 95 -> 109 mm. Bare is read per job above: it
falls on Becker beanie, rises 0.34 mm on the drone (the seam-OFF figure, a
satin lead-in leg, not a fill walk), and is unchanged on the rest.

The stitch instruments cannot judge lay. The cuts and exposure this table
prices are what the flips cost or buy, and a flip is a picture: read the sheet.

**CPU**, plan replayed warm, twice each: Becker beanie +11%, drone +4 to +20%,
crest +16 to +20%, MFab hat no rise. Stitches move +1.7% at most (Becker LC).

## The switches

- `cfg.knockdown_shorter_walk` (OFF): one job's walk, nothing else moves. The
  other beanie is byte-identical.
- `cfg.fill_seam_order_priced` (OFF): the lay first, `_score` on a tie.

Off, the engine is unchanged: DST md5 equals the run before the switches on the
four jobs read both ways, and the arm stayed byte-stable across all 22. Tests:
`digitizer/tests/test_seam_order_costs.py`. The sheet's cells carry these two
switches' code on engine label 6e1e8555, the base before they were committed.

## Open

- ProSeal beanie's 150.5 mm exposed and 100.25 mm bare are its knockdown's own
  walks, on every arm. The bare is the 0.20 band only (0.25 reads 0).
- Becker beanie sews 14 cuts against the pro's 4, 6 of them inside one piece.
