# border_by_size + enclosed_alpha_hole_parts ON (Kent 2026-10-23): OFF | ON | pro

`tools/flip_two_proof.py` (the Studio request on the hat preset, OFF = the two
flags set back through `extra`, ON = plain defaults; `rows.json` is its output).

Ring = BORDER or OUTLINE by `tools/border_census.py`'s detector, shapes of 1 mm2 and up, `ours ring / shapes`.

| design | band | OFF | ON | pro |
|---|---|---|---|---|
| hotel_fremont_hat 92.6 | 4-6 / 10+ | 2/3, 1/1 | 2/3, 1/1 | 2/3, 1/1 |
| becker_hat_large 101.9 | 4-6 / 6-10 / 10+ | 2/3, 2/10, 0/1 | same | 1/3, 4/10, 1/1 |
| mfab_hat 104.9 | 4-6 / 6-10 | 0/1, 1/6 | 0/1, **2/6** | 0/1, 6/6 |
| gaulke_roofing_hat 114.2 | 4-6 / 10+ | 1/1, 0/1 | 1/1, **1/1** | 0/1, 0/1 |
| precision_drone 62.6 | 4-6 / 6-10 | 0/1, 1/3 | 0/1, 1/3 | 0/1, 2/3 |

| design | stitches OFF / ON / pro | trims OFF / ON / pro |
|---|---|---|
| hotel_fremont_hat | 17563 / 17563 / 17067 | 45 / 45 / 52 |
| becker_hat_large | 9294 / 9294 / 12356 | 24 / 24 / 57 |
| mfab_hat | 13466 / 13577 / 17568 | 65 / 64 / 46 |
| precision_drone | 14080 / 14200 / 14554 | 114 / 109 / 69 |
| gaulke_roofing_hat | 7404 / 7509 / 6138 | 33 / 34 / 42 |

Drone's O counter (4.07 x 3.42 mm polygon hole, our stitch points inside it
shrunk by 0.3 mm): OFF 70, ON 11, pro 28. Shut OFF (two hole regions sewn in
the letter's thread), open ON, as the pro's.

Fremont and Becker are tag-for-tag unchanged; MFab's bar, Gaulke's arch and
Drone move. Becker's 4-6 band reads 2 vs the pro's 1 in both arms (not this flip).

Crops (`tools/pro_pair.py`, `sheet_band.png` = art | ours (ON) | pro, `runs_<id>.txt`
the shape's runs): `mfab_S127f7bff` (the 17 x 6.5 mm bar), `gaulke_S4e044819`
(the arch), `drone_O_Sb86e7811` (the O's polygon; the band shows "AND DRONE").
