# The underlay's direction, flipped ON: two logos, off and on (2026-10-11)

`underlayDirection` (defect 57, built OFF in PR #822) went default ON on Kent's
ruling the same day. Each logo is digitized the way the Studio's image lane
does it (`flattenRGBA` 4 colours, background removed, left chest, underlay on),
written to `.dst` both ways, and drawn from the file by
`node tools/underlay-direction-logo-sheet.mjs <image.png> --name <slug>`.
Off on top, on below. Red: a jump record after the first stitch. Stitches
shade orange (first) to dark blue (last). Green dot: the file's first stitch.

| logo | | needle-up mm | jump records | 3-jump runs | trims | stitches |
|---|---|---|---|---|---|---|
| `hotel_fremont` (`digitizer/testdata/art/logo_hotel_fremont_patch.png`) | off | 7629.4 | 847 | 157 | 42 | 11975 |
| | on | 7329.5 | 825 | 152 | 42 | 11975 |
| `logo_whitebg` (`digitizer/testdata/logo_whitebg.png`) | off | 1876.5 | 238 | 8 | 6 | 5039 |
| | on | 1820.6 | 234 | 6 | 6 | 5039 |

"3-jump runs" counts runs of three or more consecutive jump records in the
file: what a machine set to cut on three jumps reads as a trim. "Trims" is
what the engine itself asked for. Needle-up counts every jump record after
the first stitch; most of it, in both files and in both arms, is fill travel
that the flag does not touch (the red masses), so read the difference, not the
total.

Files: `hotel_fremont{.png,-off.dst,-on.dst}`, `logo_whitebg{.png,-off.dst,-on.dst}`.
