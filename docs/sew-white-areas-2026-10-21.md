# Sew white areas: the customer's option (2026-10-21)

Built OFF. `cfg.sew_enclosed_white` (engine) and "Sew white areas" (Studio,
Advanced). Rule R11 of `docs/pro-digitizer-rules-2026-10-21.md`: the pro sews
the white or hollow areas inside a design on 5 of 11 jobs. That changes the
design, so it is the customer's choice and never a default.

## What it does

Every `enclosed_background` region (the white stage 1 finds enclosed by the
art, unstitched by default since the 2026-08-15 verdict) is one of two kinds
(`digitizer_core/enclosed_white.py`):

- **Counter**: the gap inside a letter. The region is not lettering itself,
  and the shape whose hole holds it is a text-cluster letter
  (`text_candidate`, or `word_id` under `lettering_words`), or `keep_counters`
  already called it one. **Stays open** unless the customer ticks "Fill letter
  holes too" (`sew_enclosed_counters`), or it sits inside a field that sews.
  A hole through a sewn field would show the garment.
- **Field**: everything else. That covers badge fields, keyline bands, and a
  hollow letter's body (BECKER's white interiors are tagged lettering
  themselves and sit inside an untagged keyline). **Sews.**

The house-angle group (`lettering_group`) does not count as a letter here.
It tagged Golden Tee's ball-arc outline, and the pro sews the crescent inside
that outline.

**Thread:** `sew_enclosed_rgb` snaps to the nearest chart thread. With None,
a hole of known colour keeps the colour it carries, and an alpha hole
(colour unknown) sews white. The Studio always sends the picker's colour,
white by default. A review recolour or `stitched` switch on one area still
wins, so per-area colour is the Edit shapes list.

**Order:** these areas go in their own layer(s) at the front of the sew
order, one layer per thread. The pro sews the fill first and the outline on
top (R13), repeating a cone to keep that order (R12). The colour cap counts
them as sewn area (`count_enclosed`).

## Measured: `tools/pro_pair.py --config '{"sew_enclosed_white": true}'`

Studio request, today's `main` (2e873933) plus this branch, at the pro's
width. Stitches and trims are as `pro_pair` reads them (ours from our own
plan; pro from its PES, so the pro's trims here read high, per the rules doc;
its DST figures are in brackets).

| job | OFF stitches / trims | ON stitches / trims | pro stitches / trims |
|---|---|---|---|
| Becker hat small, 76.5 mm | 5,928 / 16 | **8,512 / 23** | 8,694 / 40 (DST 10) |
| Golden Tee, 74.9 mm | 8,339 / 39 | 11,417 / 46 | 5,975 / 35 (DST 9) |
| MFab hat, 104.9 mm | 12,152 / 63 | 20,396 / 81 | 17,568 / 46 (DST 18) |
| To a T Machine hat, 89.5 mm | 8,736 / 49 | 24,633 / **109** | 13,886 / 31 (DST 30) |
| Fremont patch, 92.5 mm | unchanged | unchanged | — |

Renders (art | ours ON | pro): `docs/renders/sew-white-2026-10-21/*_on_art_ours_pro.jpg`.
The OFF sheets are the rules doc's, `docs/renders/pro-rules-2026-10-21/`.

- **Becker:** the five hollow-letter bodies fill and MARINE's two counters stay
  open, which is what the pro did. Stitches land within 2% of the pro's.
- **Golden Tee:** the GT interiors and the ball-arc crescent fill white, like
  the pro's. GOLF's bevel layers are R15 (flatten gradients), not this option.
- **MFab:** the white keyline band fills, and the counters of M-FAB's letters
  (inside that band) fill with it.
- **Machine:** the badge field fills, but **trims more than double (49 → 109)**.
  Our field is cut around all 26 letters and lines on it, and its fill sews
  as pieces. The pro lays one fill under the letters and sews them on top. Making
  a sewn field ignore the holes its upper layers cover is the follow-up. It is
  stage-5 work, not this option.
- **Fremont:** no change. The gradient lane already makes the hexagon's field a
  sewn white region, and nothing in it is `enclosed_background`.

**OFF is byte-identical:** `ours.dst` md5 from `pro_pair` on all five jobs is
the same on this branch and on a clean `main` worktree (2e873933): fremont
`dac6bf81`, becker `b0b04284`, golden `3f90c794`, mfab `8f929179`, machine
`fb281a29`.

**Studio, end to end:** `studio_becker_off_on.jpg`. Becker on a Tote, through
the real service: 5,746 → 8,015 stitches, 1 → 2 colours, BECKER filled white,
MARINE's counters open.

## Not done, and why

- The default thread is white. The pro sewed Becker's interiors grey and
  Machine's field black. Those are the customer's colour choices, which the
  picker carries.
- Machine's trims (above).
- An alpha hole's colour stays unknown. It sews in the chosen thread.
