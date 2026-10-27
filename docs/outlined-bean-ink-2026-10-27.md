# Outlined bean ink: MFab's AND read its white keyline as the letter (W5-05, 2026-10-27)

**Flag:** `bean_ink_outlined_letters`, built OFF. Layout (ruling 2026-10-22:
judged in the preview). It moves no width, stroke, ratio or line, and no
constant: `bean_letter_max_stroke_mm` and `INK_SHAPE_MAX_RATIO` are untouched.

**Why it was built:** it blocks `text_cluster_part_touching`. With that flag
ON, the LC's AND N joins the A in the fault below.

## The fault

MFab's small line, AND WELDING LLC (6.25 mm drawn), is black letters on a
black body. Each letter is ringed by a thin white keyline.

`ink_path.read_cluster_ink` finds a cluster's ink in two steps:

1. The **ground** is the median colour of the pixels at least 0.8 mm from
   the members.
2. The **ink axis** is the colour near the members that differs most from
   that ground.

On MFab the ground is the black body, the same colour as the letters. So
the colour that differs most is the WHITE keyline, and the reader traces a
line round the outside of each letter instead of down its stroke.

Measured on the LC on today's main, re-reading the replayed regions with the
same reader:

| letter | ink read mm | shape / ink ratio | spine inside the letter | median distance |
|---|---|---|---|---|
| A (`Sbd0d3e9f`) | 0.417 | 2.94 | 1.7% | 0.15 mm outside |
| N top (`S30c08aba`) | 0.417 | 2.64 | 1.4% | 0.15 mm outside |
| N (`S81d1d4a6`) | 0.441 | 2.54 | 0.4% | 0.14 mm outside |
| D (`S6815bbe5-2`) | 0.350 | 3.17 | 0.0% | 0.17 mm outside |

The A, N and N top pass the shape gate (`INK_SHAPE_MAX_RATIO` 3.0). Their
group's median is under the 0.5 mm line, so they go bean. The D fails the
shape gate and sews satin either way. (The N is its own member only with
`text_cluster_part_touching` ON; OFF, it is merged into the black under-fill.)

WELDING and LLC are NOT in this fault on today's main. Their members read
0.083 mm or nothing, fail the shape gate, and sew satin on both arms. Their
crops and per-letter counts are identical OFF and ON (below).

**What OFF sews** (crops below):

- The A, and with `part_touching` the N, come out as **white letters with a
  thin black line round them**, where the art and the pro have black satin
  letters on a white keyline.
- DROP_MECHANISM

## The rule

A real ink read lies inside its letter. Two populations on today's engine:

- **Bridge** (`testdata/photo/logo_bridge_bar.jpg`, the fixture the bean rule
  was built on) has eight bean letters at the 1.0 mm line. Their spines lie
  **98.4-100%** inside their letters.
- **The same MFab words on the hat.** There the reader does find the letters
  (0.167 mm, which fails the ratio gate, so they sew satin). Their spines lie
  **67.7-100%** inside.

AND's outline reads on the LC lie **0.4-1.7%** inside.

`INK_INSIDE_MIN_SHARE = 0.5` sits between the two populations. It is
geometry, not cloth, so gate 1 does not apply.

ON, a read whose spines lie less than half inside the letter is treated like
a shape-gate miss: it is left out of the weight decision and never goes bean.
The letter then sews as the rider it is, a black satin column. `ink_stroke_mm`
is still recorded.

## Measured

Arms: stages 0-4 captured once per job (`build_generation`), then
`finish_generation` + `plan_stitches` replayed per arm on today's engine
(d3f8819f), with the config rebuilt from the Studio request. One fresh LC
digitize with the flag ON reproduced the replay byte for byte (plan
`1deb8417`). Hat route on every hat arm: `PHOTO_SCENE` +
`BACKGROUND_REMOVED`, mask `9fac5f2e`, 60 regions into the tagger. The LC is
`CLASSIFIED_GRADIENT` (no rembg).

### Whole file

| arm | bean letters | stitches | trims | plan md5 | CPU s (finish + plan) |
|---|---|---|---|---|---|
| LC OFF | 2 | 17,777 | 27 | `d6802182` | 76.9 |
| LC ON | 0 | 17,700 | 26 | `1deb8417` | 77.7 |
| LC + part_touching, OFF | 3 | 17,999 | 22 | `8b898d6d` | 71.5 |
| LC + part_touching, ON | 0 | 17,857 | 22 | `7cfd4f57` | 74.3 |
| hat OFF | 0 | 20,561 | 33 | `8b0ea048` | 175.5 |
| hat ON | 0 | 20,561 | 33 | `8b0ea048` | 173.2 |
| hat + part_touching (fresh digitize), OFF and ON | 0 | 20,573 | 27 | `8b733544` | 177-193 (whole digitize) |

**The hat does not move.** Its AND and WELDING read 0.167 mm on letters
1.0-1.2 mm wide, fail the shape gate, and sew satin on every arm. ON costs
no measurable CPU.

### Per letter (LC)

Satin **pieces**, **crosses**, and **trims** inside the letter, read off each
DST by `tools.letter_pieces` (same reader on ours and the pro's). The pro's
letter is our polygon registered into his frame.

| letter | OFF | ON | OFF + pt | ON + pt | pro |
|---|---|---|---|---|---|
| A | 3 p / 44 x / 0 t | 4 / 116 / 1 | 1 / 40 / 0 | 3 / 115 / 1 | 2 / 114 / 0 |
| N | 0 / 0 / 0 | 0 / 0 / 0 | 1 / 40 / 0 | 3 / 104 / 0 | 5 / 95 / 0 |
| N top | 0 / 0 / 2 | 4 / 58 / 0 | 1 / 4 / 0 | 3 / 57 / 0 | 2 / 77 / 0 |
| D | 2 / 118 / 0 | same | same | same | 2 / 115 / 0 |
| **word AND** | **8 / 116 / 5** | **10 / 292 / 4** | 9 / 229 / 2 | 11 / 394 / 2 | 9 / 324 / 0 |
| word WELDING | 23 / 675 / 2 | same | 20 / 685 / 1 | same | 23 / 610 / 2 |
| word LLC | 5 / 193 / 1 | same | 3 / 195 / 1 | same | 3 / 189 / 0 |

ON, the A's crosses go from 44 to 116 against the pro's 114. AND as a word
goes from 116 crosses to 292 (pro 324).

### Lettering board (LC, the 6-10 mm line, ours / pro)

BOARD_TABLE

## Crops

Ours OFF, ours ON, the pro, each in its own frame
(`docs/renders/outlined-bean-ink-2026-10-27/`):

- `lc_AND.png`: main's defaults.
- `lc_AND_part_touching.png`: with `text_cluster_part_touching` ON.
- `lc_WELDING.png`, `lc_LLC.png`: identical OFF and ON.

## Tests

`digitizer/tests/test_bean_outlined_ink.py`:

- **Geometry:** what `spines_inside` measures.
- **Construction:** a drawn raster of black letters on a black body with a
  white keyline, read by the real ink reader at keylines of 0.2 and 0.3 mm.
  OFF reproduces the fault (all three letters bean, under 5% inside). ON tags
  none. The control (thin letters on a white page) goes bean both ways.
- **Decision:** with stubbed reads, an outline read is left out and the rest
  decide, under word tiers too.
- **Bridge:** ON keeps all eight bean letters with identical spines.
- **Goldens:** OFF is byte-identical on logo_alpha, logo_whitebg and
  ribbon_curve, and ON moves none of them.

## Not done here

- The flip is Kent's.
- Why the earlier brief listed WELDING and LLC: on today's main they never
  reach the bean decision, so whatever is wrong there is a different
  mechanism, not this one.
