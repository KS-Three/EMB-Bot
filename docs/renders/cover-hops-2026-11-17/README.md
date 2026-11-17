# `lettering_columns_cover_hops` (built OFF), 2026-11-17

Prime grader scorecard fault: Toat beanie, "a thin bare run stitch crosses the
open mouth of the c of Machine (38.5, 31.5 mm) and another at its lower left
(37, 36)". Confirmed by eye against the original: the art has open space there.

**Cause.** Not a connector between satin pieces. The word Machine is one
script-stroke word (`script_strokes.py` -> `columns.column_runs`). Its needle-down
travel (an underpath along a stroke's centreline, a hop between strokes) is
accepted as "inside the letter" when `poly_hop` (the outline grown by the pull)
covers it, and that growth also closes the notch the satin leaves open. Run 14897
of the stitch stream (17 stitches) has two segments, (39.5,35.0)->(37.6,36.6) and
(37.6,36.6)->(36.5,34.9), 1.3 and 1.6 mm of which lie on no satin; a 1.2 mm hop at
(39.2,31.7)->(38.2,31.0) is the other.

**Flag.** `lettering_columns_cover_hops` (default False; `tests/engine_2026_10_27.json`
has it false). A travel segment with more than 0.3 mm off the ground of every
satin leg of the word is dropped; the piece after it begins with a jump and a trim.
The entry walk is kept. OFF is byte-identical (the kwarg defaults False in both
emitters). Tests: `tests/test_column_cover_hops.py`.

## The 9 pro jobs, OFF vs ON

5 moved, 4 are byte-identical (Hotel Fremont, MFab, Golden Tee, Toat Machine hat).
All 5 movers are pictured (`*_zoom.png` at the changed stitches, `*_full.png` whole
design). Each picture is ORIGINAL | BEFORE | AFTER.

| design | trims OFF -> ON | by eye |
|---|---|---|
| toat_beanie | 24 -> 26 | **better**: both bars across the c are gone (`toat_beanie_c_mouth_30px.png`; `toat_beanie_zoom.png`) |
| becker_hat_large | 17 -> 18 | no visible change (E of MARINE's foot, stitch order only) |
| precision_drone | 99 -> 100 | no visible change (a few stitches at the R of DRONE) |
| tires_hat_3d | 3 -> 7 | no visible change (black on black at this size); +4 trims is the cost |
| gaulke_roofing_hat | 33 -> 33 | no visible change (4 stitches at the &); the zoom's ORIGINAL panel is mis-registered by the picture script, the two threads panels are right |

None got worse by eye. The cost is 8 more trims over the 9 jobs, 4 of them on
Tires where nothing shows.
