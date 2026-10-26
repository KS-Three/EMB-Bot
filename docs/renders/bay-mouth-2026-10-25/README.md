# Keep each bay's mouth open: OFF | ON | pro (W3-02, 2026-10-25)

`cfg.extra["small_text_bay_mouth"]` (built OFF; `small_text._open_mouths`), measured with
`tools/bay_census.py`. Ours: digitized at the pro's width on main `c531c7b8`, with the re-set made
explicit (`small_text_cap_mm` 4.0, `max_width_scale` 1.05, `min_stroke_mm` 0.85, `letter_gap_mm` 0.25,
`bold_scale` 1.45, `lettering_columns_small_bold`: #1057's defaults). OFF is that. ON adds the switch.
Pro: his DST, read out of the committed `Embroidery Files.zip`.

Both files are read with the same reader, each in its own frame: `small_text_columns.pieces`
(needle-down stitches drawn 0.4 mm wide at 20 px/mm). A mouth is `small_text.bay_mouths`: twice the
bottleneck clearance from a pocket to the outside, where 0 means enclosed. An 8's or 9's counters
read 0 by design. **This is a picture of the file, not of cloth**: whether a mouth stays open on a cap
is a sew-out question (ROADMAP gate 1).

## The census (`python -m tools.bay_census --census`)

The pro's E, S and 5 on Fremont Hat and Patch (EST 1895) and on the ProSeal hat and beanie (SPRAY):
n 18, range 0.27-1.20, **median 0.51** = `BAY_MOUTH_MM`.

## OFF | ON | pro

| job | letter | mouths mm OFF | ON | pro | aspect OFF / ON / pro | OCR OFF / ON / pro | OCR pulled 0.13 mm OFF / ON / pro |
|---|---|---|---|---|---|---|---|
| Fremont hat 92.6 | E | 0, 0, 0.30, 0.36 | 0.56, 0.58 | 0.49, 0.56 | 0.753 / 0.758 / 0.796 | E / E / E | E / E / E |
| | S | 0, 0.36, 0.44 | 0.30, 0.70, 0.72 | 0.50, 0.72 | 0.707 / 0.720 / 0.667 | 8 / S / S | E / S / S |
| | 1 | 0.30, 0.30, 0.32 | same | 0.36 | 0.539 / 0.539 / 0.518 | I / I / 1 | 1 / 1 / 1 |
| | 8 | 0 | 0 | 0, 0, 0.32, 0.42 | 0.731 / 0.731 / 0.660 | 8 / 8 / 8 | 8 / 8 / 8 |
| | 9 | 0, 0.42 | same | 0, 0.80 | 0.753 / 0.753 / 0.804 | 9 / 9 / 9 | 9 / 9 / 9 |
| | 5 | 0, 0.13, 0.27, 0.36 | **0**, 0.65 | 0.30, 0.50, 1.20 | 0.733 / 0.681 / 0.685 | 3 / 3 / 3 | 3 / **5** / 3 |
| Fremont patch 92.5 | E | 0, 0 | 0.62, 0.70 | 0.27, 0.36, 0.40 | 0.626 / 0.634 / 0.729 | G / E / E | E / E / E |
| | S | none (filled) | 0.66, 0.70 | 0.62, 0.64 | 0.568 / 0.574 / 0.644 | ? / S / S | ? / S / S |
| | 1 | 0.30, 0.30 | same | 0.30 | 0.483 / 0.483 / 0.487 | 1 / 1 / I | I / I / I |
| | 8 | 0, 0.30 | same | 0, 0, 0.30, 0.42 | 0.624 / 0.624 / 0.624 | 8 / 8 / F | 8 / 8 / 8 |
| | 9 | 0, 0.36 | same | 0, 0.56 | 0.648 / 0.648 / 0.714 | 9 / 9 / 9 | 9 / 9 / 9 |
| | 5 | 0, 0.42 | 0.42 | 0.42, 1.02 | 0.602 / 0.564 / 0.635 | ? / **5** / 5 | ? / 8 / 3 |
| Fremont hat THE | E | 0, 0 | 0.40, 0.56 | 0.36, 0.39 | 0.642 / 0.619 / 0.711 | E / E / E | 3 / E / E |
| | H | 0.09, 0.42, 0.58 | 0.32, 0.66, 0.82 | 0.38, 0.38 | 0.763 / 0.753 / 1.041 | H / H / H | H / H / H |
| ProSeal beanie 75 SPRAY | S | 0.42, 0.50 | 0.32, 0.62 | 0.52, 0.56 | 0.753 / 0.701 / 0.667 | ? / ? / S | ? / S / 5 |
| | P R A Y F O A M | unchanged | | | | | |
| ProSeal beanie COATINGS | G | 0.71 | 0.90 | 0.56 | 0.818 / 0.829 / 0.901 | G / G / G | G / G / G |
| | C O A T I N S | unchanged | | | | | |
| ProSeal hat 85.9 | all | **byte-identical** OFF/ON (md5 `7f95033c`) | | | | | |
| Drone 62.6 AND DRONE | all | **byte-identical** OFF/ON (md5 `c814fc4d`) | | | | | |

"OCR pulled" erodes the thread mask by the pull the engine added to these letters (`small_bold`'s
0.15 of the 0.85 mm stroke, a side) through `glyph_read.pull_erode`, which is what
`glyph_legibility --pull-mm` does. Single-letter tesseract is noisy: the pro's own 5 reads 3 and his
1 reads I. **The mouths are the measurement; OCR is a second reader.**

## Every cut (from the ON growth report), and what moved

No letter's height moved (`dh_mm` 0 everywhere). Three letters lost a little sewn width: Fremont hat
5 −0.14 mm, Fremont patch 5 −0.10 mm, beanie S −0.11 mm. Cuts were 0.1-1.15 mm along the stroke,
0.04-0.85 mm2 of ink. Stitches / trims, OFF → ON: hat 18,546 / 51 → 18,511 / 48; patch 20,612 / 55 →
20,588 / 54; beanie 8,547 / 43 → 8,539 / 43.

## The one miss

The Fremont hat 5 keeps one enclosed pocket (0) under its top bar. In the letter as drawn, that gap
is a uniform slot (bar to bowl top, the same width along its length). The stroke widening fills all
of it, so the switch's sewn-extent read sees no pocket there; the Column lane sews it as a small
hole, and OFF sewed it as a 0.13-0.36 mm slit. A slot opens only with a thinner stroke, which is
gate 1. Cutting a slit into it is the reverted bay carving. The bowl, the mouth that made the 5 read
3, opens to 0.65.
