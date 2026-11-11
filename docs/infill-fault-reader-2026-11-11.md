# In-fill reader vs Kent's pins: not shown (2026-11-11)

**Verdict, by the pre-registered rule: not shown.** n = 6 items, 8 notes,
36 pins (sitting 1: 2 pins on 1 logo; sitting 2: 34 pins on 5 logos). At
3 mm, per note (each note weighs one): hit 0.29 against 0.27 for pins placed
on random candidate spaces (`chance_pick`), item-bootstrap 95% CI on the
difference [-0.31, +0.28]. Per pin: 0.33 against 0.82. Against random
points on all thread (the earlier readers' null) it is 0.29 against 0.04 per
note, CI [-0.003, +0.63]: the reader finds the region where the fault sits,
and this record cannot show it finds the spaces Kent pinned.

Pre-registration: `docs/infill-fault-reader-2026-11-11/preregistration.md`,
commit `ba01dcb7`, before any run on an item holding a selected pin. Pins:
`pins-sitting-1.json`, `pins-sitting-2.json` (same folder). Score:
`score.json`. Reader `digitizer/tools/infill_fault_reader.py`, harness
`digitizer/tools/fault_reader_harness.py --fault infill`. Tree `950855bf`
(the primary checkout, untouched); every item re-ran to its stored stitches.
Every figure here is an instrument reading beside its chance figure
(ROADMAP gate 4), not a quality claim.

## What "extra in-fill" is

Read at the pins before the reader was designed (the pre-registration's
first section). On `C_kanji_seal` (all 28 pins) and `C_devanagari_logo`
(pins 1, 5, 6) the top thread is white satin over pixels the source PNG
leaves transparent. **Correction to the pre-registration's wording:** it
says the background mask "never reached" those spaces, so the pipeline sewed
them "as a white shape". The mechanism is a deliberate rule:
`sew_enclosed_white` (ON) sews enclosed background it takes for a body or
field and leaves what it takes for a letter counter open, the rule the
2026-10-23 census matched to the pro's files
(`.claude/memory/enclosed-white-like-pro-2026-10-23.md`). On seal script and
Devanagari that split falls between spaces Kent sees as alike. The reader
was built from what the stitches are, so the correction changes nothing in
it; it changes where a fix would go.

## The score

At 3.0 mm (the verdict radius). `pick` = random candidate spaces, `cand` =
random points on candidate interiors, `area` = random points on thread.

| item | pins | notes | flags | candidates | hit | pick | cand | area |
|---|---|---|---|---|---|---|---|---|
| `C_kanji_seal` | 28 | 1 | 20 | 20 | 9 | 1.000 | 0.819 | 0.128 |
| `C_devanagari_logo` | 3 | 2 | 5 | 10 | 3 | 0.500 | 0.496 | 0.083 |
| `C_pixel_art_sprite` | 1 | 1 | 1 | 6 | 0 | 0.167 | 0.148 | 0.009 |
| `C_gradient_mascot` | 1 | 1 | 0 | 2 | 0 | 0 | 0 | 0 |
| `C_flat_emoji_icon` | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| `L_bridge_hat` | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |

Pooled, 3 mm (2 and 5 mm in `score.json`; the same picture):

| weighting | null | hit | chance | diff | 95% CI (items) |
|---|---|---|---|---|---|
| per note | pick (verdict) | 0.29 | 0.27 | +0.02 | [-0.31, +0.28] |
| per note | cand | 0.29 | 0.25 | +0.05 | [-0.22, +0.30] |
| per note | area | 0.29 | 0.04 | +0.25 | [-0.003, +0.63] |
| per pin | pick | 0.33 | 0.82 | -0.49 | [-0.65, +0.33] |
| per pin | area | 0.33 | 0.11 | +0.23 | [-0.003, +0.63] |

Notes beating their item's `chance_pick`: 2 of 8 (both Devanagari).
**Precision:** 12 of 26 flags on pinned items lie within 3 mm of a selected
pin (0.46), against 0.40 for the same number of candidates chosen at random,
CI [0.00, +0.30].

Per note:

| note | pins hit | pick | why |
|---|---|---|---|
| kanji 1 "#1-#28 extra in-fill" | 9/28 | 1.000 | see below |
| devanagari 1 "the only lettering in-fill" | 1/1 | 0.500 | flagged (32 mm2 white bowl) |
| devanagari 5 "(#5-#6) in-fill only in select spots" | 2/2 | 0.500 | flagged (3.6 and 2.2 mm2) |
| pixel art 1 "bean round some openings" | 0/1 | 0.167 | the pin sits on ink, not an empty space |
| gradient 1 "extra bean stitch ... nostril" | 0/1 | 0 | the pin sits on ink |
| emoji 3 "leg infill doesn't match" | 0/1 | 0 | fill direction: not read (predicted) |
| Bridge 1 "wheel handles look different" | 0/1 | 0 | shape: not read (predicted) |
| Bridge 4 "the only letter thinly stitched" | 0/1 | 0 | width: not read (predicted) |

## What it missed, and why

- **Kanji, 19 of 28.** Every one of the 28 pins sits in an empty space of
  the art sewn white; the reader saw 40 spaces there and read 20 as in-fill,
  19 as `closed`, 1 bare (the page). 11 pins sit in spaces read in-fill (9
  hit; the other 2 are more than 3 mm from their large space's deepest
  point, where the flag sits) and 17 in spaces read `closed`: the white satin spills over the red strokes, so the commonest
  thread on the 0.6 mm ring outside the space is white too, and the rule
  reads that as "covered in the surrounding ink's colour" (a lost counter).
  A reader defect found after scoring; no constant was changed. It does not
  move the verdict: fixed, the reader would flag every white space, every
  candidate again, and `chance_pick` on this item stays 1.0. On kanji the
  pins and the reader's candidates are nearly the same set, so this item
  cannot show selection whatever the reader does.
- **Pixel art and gradient mascot:** both pins sit on pixels the art inks
  (empty share 0.0 in a 1 mm window), so no empty space holds them. What
  Kent calls "openings" there is not transparent in the art.
- **Emoji, Bridge 1, Bridge 4:** direction, shape and width, which this
  reader does not read; written down as predicted misses before the run.

## What it flags that Kent did not pin

- On kanji, the six strongest unpinned flags are white-sewn spaces he left
  unpinned (the top-centre block's interiors, 12-35 mm2). He pinned 28 of
  the white spaces, not all of them.
- On Devanagari, two more small white-sewn counters (2.5 mm2 each) in the
  same grey line as his pins 5 and 6, about 4.5 mm from them.
- On the 26 items with no selected pin: 20 read (6 refused at registration,
  `C_qr_code`, `C_halftone_dots`, `C_chalkboard_lettering` with an empty
  `bg_mask`, `C_duotone_poster` 0.21, `C_vintage_engraved_badge` 0.64,
  `L_mfab_hat` 0.89; `L_gaulke_roofing_hat` refused by the worker, its
  prepped raster not a plain resize of the art). 14 of the 20 carry no flag.
  The other 14 flags, against the nearest pin Kent placed for ANY fault
  (not scored; the rule's exclusions stand):

  | item | flags | nearest pin |
  |---|---|---|
  | `C_neon_outline_sign` | 1 (the "d" counter sewn white, the "a"'s bare) | **0.3 mm** from his pin 2, kind `extra`, no note |
  | `C_isometric_icon` | 2 | 2.3 mm from pin 8 (bare, under "7-8 does not portray the image definition", kind `extra`); the other 11 mm away |
  | `L_becker_hat_large` | 5 (its five white letter bodies) | 2.9-14 mm; the near ones are his "random cross over stitch" pins |
  | `C_outline_lineart_logo` | 4 (0.35-0.51 mm2 gaps the grey keyline fills) | 14-24 mm |
  | `C_heraldic_crest` | 1 | 29 mm |
  | `C_low_poly` | 1 | 10 mm |

  Two of Kent's bare `extra` pins sit on or near a flag. His rule leaves bare
  pins with no note and no range out on purpose, and they are not counted;
  they are what a third sitting would ask him to write a note on.

## The edge-band null (task item 3)

`chance_edge` read 0.00 on `L_bridge_hat` (letter reader, sitting 1) and
`C_silhouette_logo` (letter hold-out, sitting 2) beside 21 and 65 flags.
Not a bug: the band is thread within 1 mm of FABRIC, so on a design whose
faults sit inside a sewn field the band is the field's outer rim, and no
point on it is within 3 mm of a flag. Measured: the nearest flag lies 3.27 mm
(Bridge) and 9.19 mm (silhouette) from the band. Pinned by
`test_edge_band_null_is_zero_for_flags_inside_a_field`; documented in
`edge_band`. No code changed in the null, so #1388's and #1389's figures do
not move. It is the right null only for a reader whose flags sit at fabric
edges; the candidate nulls replace it for this reader.

## One fix made after the first score

The first score pooled `chance_pick` as NaN, because three items (Bridge,
emoji, gradient) carry pins but no flags, and Bridge and emoji no candidates
either. With no flags nothing can be hit, so every null is 0 there; the
harness now says so (`pick_rate`, `chance_cand`; test
`test_an_item_the_reader_reads_nothing_on_pools_as_zero_not_nan`). It cannot
move a hit, and on those items hit = null = 0.

## What this does and does not say

- Kent's in-fill notes describe a real, findable pattern: thread in spaces
  the art leaves empty. On the two items where his pins land on empty space,
  every pin does (31 of 31).
- Among the empty spaces the pipeline fills, this record cannot show the
  reader picks the ones he pinned. On kanji it flags all of them and he
  pinned most; on Devanagari it flagged 5 of 10 and his 3 pins fell on 3 of
  those 5; that is 2 notes.
- The reader cannot tell a hollow letter body the pro also sews (Becker's
  five white interiors, flagged; the 10-23 census says the pro sews those)
  from a counter sewn by mistake. Which spaces SHOULD be sewn is a role
  question, and the role is what `sew_enclosed_white` already guesses.

Not run or not verified: no third sitting (the reader's concept was read off
the two largest notes, so this is not a hold-out); no sew-out; the full
digitizer suite (only the targeted tests, in the PR body).
