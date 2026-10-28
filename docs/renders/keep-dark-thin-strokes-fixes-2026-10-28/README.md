# `keep_dark_thin_strokes` OFF | ON before | ON after the two fixes (2026-10-28)

PR #1162's sheet (`../keep-dark-thin-strokes-2026-10-28/`) found that on `testdata/photo/summit_badge.png`
the flag's one "stroke" is the counter of a letter (the dark ground inside the lower bowl of the S of
SUMMIT) and that carving it cost the badge's vignette two of its four greys. Kent ruled "Hold OFF, queue
two fixes". This sheet is the same look after the two fixes, with the earlier engine's ON kept as a third
arm. **The flag is still OFF**; nothing here changes a default. Open **`sheet.html`** (one self-contained
page, every image inline); the JPEGs beside it are the same tiles.

**How it was made.** `digitizer/tools/dark_ink_flip_sheet.py` (`run` on this engine and on a clean
`git archive origin/main` extract of `09cfbaea`, then `report --before <main's cache>`), the Studio request
at 80 mm `left_chest` (`tools.fremont_triage.studio_request(80.0)`), shipped defaults. OFF is the default;
ON sets the one flag. Counts are the DST's own records (pystitch): stitches, TRIM records, colour blocks;
regions from the plan. The crop rule is `tools.flip_sheet_renders`': needle points OFF and ON on a 0.05 mm
grid as a multiset, the 18 x 11 mm window holding the most changed points, 40 px/mm; where ON after is
OFF byte for byte the window is where OFF and ON before differ. **No pro file exists for any fixture here,
so there is no pro column.**

## The two fixes

1. **Counter refusal** (`thin_ink.find_dark_thin_ink(..., glyphs=thin.mask)`, `is_counter`): a dark
   component whose one ground (the ring pixels within `DARK_INK_GROUND_DE00` of the ring's median) is
   thin-population pixels at `THIN_INK_GROUND_SHARE` or more is ringed by a glyph, not drawn on a ground.
   Summit's bowl: 251 foreground ring pixels, 190 of them the S (an 11.5 mm² thin component), the one-ground
   pixels all of them (share 1.0). Refused: `Sccd9bce6`, 2.58 mm² (2.88 mm² as a raw mask) at
   x -14.2..-11.8 / y 29.7..31.5 mm.
2. **Tail read for a carved ground** (`stage6_blend.carved_ground`, `tail_extremes`,
   `SourcePixels.dark_ink`): a blend region the carve re-shaped reads its shade count from the mean Lab of
   the samples in the first and last 5% of its ramp (the design path's own read) instead of two single
   pixels. OFF's read of summit's background was its t = 0 pixel at L* 5.9, a near-black pixel inside the
   counter, against L* 74 at t = 1: 60.4 dE00, five bands; ON before, with the counter gone and the seeded
   sample re-drawn over a mask 325 px smaller, 28.3 dE00, four bands. The tails read 28.4 and 29.4.

## summit_badge (gradient; a synthetic badge)

| | OFF | ON before | ON after |
|---|---|---|---|
| regions | 42 | 43 (1 `dark_ink`) | 42 (0) |
| stitches | 31,057 | 29,802 | 31,057 |
| trims (DST) | 36 | 40 | 36 |
| colour blocks | 12 | 10 | 12 |
| DST md5 | `01da6626…` | `28840c9b…` | `01da6626…` = OFF |

The `whole_*` tiles: four concentric greys OFF, a flat Charcoal ground with one Armour ring ON before, the
four greys back ON after. OFF's md5 is the same on the main extract and on this engine.

## Every fixture (DST md5 OFF and ON)

| fixture | OFF regions / st / tr / blocks | ON before | ON after | DST |
|---|---|---|---|---|
| photo/summit_badge.png | 42 / 31,057 / 36 / 12 | 43 / 29,802 / 40 / 10, 1 dark | 42 / 31,057 / 36 / 12, 0 dark | ON after = OFF |
| photo/screenshot_phone_ui_golke.jpg | 149 / 8,429 / 49 / 8 | 149 / 8,437 / 49 / 8, 1 dark (`Se1ffdaff`, 0.86 mm², the o of "Photo") | 149 / 8,429 / 49 / 8, 0 dark | ON after = OFF |
| photo/drone_render.png | 119 / 18,671 / 83 / 11 | 122 / 18,607 / 85 / 11, 3 dark | same as before | moves, unchanged by the fixes |
| photo/logo_bridge_bar.jpg | 54 / 15,192 / 38 / 7 | 54 / 15,238 / 38 / 7, 1 dark | same | moves, unchanged |
| photo/logo_hotel_fremont.webp | 162 / 13,509 / 22 / 4 | 162 / 13,515 / 20 / 4, 156 dark | same | moves, unchanged |
| photo/owl_kent.jpg | 105 / 35,665 / 129 / 12 | 115 / 36,587 / 139 / 11, 16 dark | same | moves, unchanged |
| art/logo_hotel_fremont_patch.png | 86 / 18,979 / 35 / 3 | 76 / 18,788 / 34 / 4, 14 dark | same | moves, unchanged |

OFF is byte-identical to main on all seven. On the five that still move, no region reaches the per-region
shade chooser at all (every one falls to tatami or sews as satin/run), so the tail read cannot act there;
their ON is the same bytes as before the fixes. `sheet.json` carries every number above, the dark-ink
regions per fixture per arm with the OFF regions they were cut from, and the colour blocks that changed.
