# Transparent white in-fill: `enclosed_white_skip_transparent` (2026-11-11)

**ON by Kent's ruling 2026-11-11, eye-check of 7 designs: "Flip ON
(Recommended)"** (relayed by the director, after the source | OFF | ON
pictures below). Built OFF the same day (#1395), when Kent picked the guarded
rule ("Guarded rule (Recommended)"). See "The flip" at the end for what moved.

## The finding (verified at this lane, same stitches as `950855b`)

Kent's second defect-marks sitting (`docs/defect-marks-2026-11-11/`):
`C_kanji_seal` pin 1 "#1-#28 extra in-fill, some empty spaces have it while
others don't", `C_devanagari_logo` pin 1 "the only lettering in-fill, it
doesn't match the rest" and pin 5 "in-fill only in select spots (#5-#6)".

The fault reader in #1392 suggested a mechanism. Checked here region by
region, with each pin mapped into the regions' frame:

- **All 28 kanji pins and Devanagari pins 1, 5 and 6** (31 of the 31 pins on
  empty space) sit in a region that `sew_enclosed_white` marks `field` and
  sews white (`enclosed_white.plan_enclosed_white`). Each region is 0.89-0.98
  transparent in the source PNG's alpha, and each carries stage 4's
  `enclosed_colour_unknown` tag. Devanagari pins 2-4, 7 and 8 sit on ink.
- **Both answers are yes:** the white is over transparent pixels, and it comes
  from the `sew_enclosed_white` path.

Kent's "some have it, others don't" has two sources. On kanji, every enclosed
space is sewn (39 of 39) while the spaces that open to the outside are bare.
On Devanagari, 5 of 11 enclosed spaces sew as `field` and 6 stay open as
counters.

## Where alpha goes, and the rule

Alpha is not lost. Stage 1 finds enclosed background through the alpha
channel when the art has one (`Prep.bg_from_alpha`). Stage 4 tags a region
`enclosed_colour_unknown` when at least 0.6 of it lies in one transparent
component (`ENCLOSED_TAG_OVERLAP_THRESHOLD`, the existing tagger,
`enclosed_alpha_hole_parts`). The flag reads that tag, so nothing new is
carried and no new threshold exists. **Partly transparent:** a region under
0.6 transparent is not enclosed background at all; it sews in its own colour
as before. The 0.6 is the tagger's layout number, not cloth (gate 1 does not
apply). The regions this moves measure 0.89-0.98 transparent.

**ON:** an enclosed area the art leaves transparent is not sewn and shows the
garment, as the art's open spaces already do. It also stops holding a counter
in a sewn field. **Except** an area that is itself lettering
(`enclosed_white._is_letter`), which is a hollow letter's BODY. A JPEG or an
opaque PNG has no `enclosed_colour_unknown` area, so the flag is a no-op
there. Tests prove it on `logo_whitebg.png` and on an RGBA file with alpha
255 everywhere.

**Why the guard.** On alpha art EVERY enclosed area is transparent, by
construction. The plain rule ("never sew transparent") is therefore just
"Sew white areas OFF on alpha art". Becker's art (`becker_marine_logo.png`)
leaves its five letter interiors transparent, and the pro sews them. Plain
rule, measured at commit `5c3049a4`:

| job | white areas | stitches OFF -> plain ON | trims | colour changes |
|---|---|---|---|---|
| becker_hat_large | 5 -> 0 (1,557 mm2) | 16,262 -> 8,350 | 13 -> 11 | 1 -> 0 |
| becker_lc_large | 5 -> 0 (1,374 mm2) | 14,922 -> 7,744 | 14 -> 12 | 1 -> 0 |
| becker_hat_small | 5 -> 0 (881 mm2) | 10,546 -> 5,619 | 13 -> 11 | 1 -> 0 |
| becker_chest_small | 5 -> 0 (881 mm2) | 10,309 -> 5,372 | 13 -> 11 | 1 -> 0 |
| becker_beanie | 5 -> 0 (958 mm2) | 13,864 -> 8,585 | 16 -> 12 | 2 -> 1 |

All 25 areas lost are tagged lettering. None of kanji's 39 or Devanagari's 5
are. With the guard (the flag as built), Becker sews the same five bodies on
all five pairs. Hat large was planned in full on both arms and the stitches
are identical (16,262, 13 trims). `test_becker_five_transparent_bodies_still_sew`
pins it at 101.9 and 76.5 mm.

## What moves (guarded rule, the flag as built)

Tool: `python -m tools.transparent_white_ab` (stages 0-4 once, OFF and ON
forks; both arms planned when the forks differ). OFF arm = the stored
`950855b` capture's stitches on every corpus mover. Instrument figures, not a
quality claim (gate 4).

**21 Commons logo rows: 6 move**, all with alpha art:

| row | transparent areas: open on ON / kept (letter) / open both | stitches | trims | colour changes |
|---|---|---|---|---|
| kanji_seal | 39 / 0 / 0 (999 mm2) | 29,505 -> 10,945 | 72 -> 22 | 1 -> 0 |
| devanagari_logo | 5 / 0 / 6 (52 mm2) | 6,281 -> 4,935 | 20 -> 12 | 2 -> 1 |
| pixel_art_sprite | 1 / 0 / 4 (38 mm2) | 11,199 -> 11,239 | 17 -> 17 | 1 -> 0 |
| heraldic_crest | 5 / 1 / 7 (28 mm2) | 36,532 -> 36,171 | 193 -> 201 | 7 -> 7 |
| neon_outline_sign | 1 / 0 / 3 (21 mm2) | 2,718 -> 2,501 | 6 -> 5 | 2 -> 1 |
| isometric_icon | 2 / 0 / 0 (149 mm2) | 11,487 -> 10,859 | 29 -> 30 | 7 -> 6 |

The other 15 do not move. Thirteen have no alpha. `gradient_mascot` has alpha,
but its 4 transparent areas are open on both arms. `hotel_fremont` has alpha
and no enclosed area. `kanji_brush` was planned in full: ON = OFF. Its OFF
differs from the `950855b` capture on both arms alike, which is tree drift
since `950855b`, not this flag.

**20 pro pairs: 1 moves.** `precision_drone` leaves one 0.85 mm2 speck in the
bottom badge open: 14,769 -> 14,760 stitches, 95 -> 94 trims, 8 colour changes
on both arms. Becker x5 is identical (above). MFab x2, Tires, To a T x3,
Gaulke x3, Golden Tee and Bridge x2 have no alpha. Fremont x2 has no enclosed
area. ProSeal was not run (its art is not committed).

## Where the tagger and the guard disagree with the art

Every transparent area on the moving rows was read by eye against the
numbered ON panel. Red = left open by the flag, blue = kept as a letter body,
grey = open on both arms.

- **A letter body left open: 0.** The 53 areas the flag opens on corpus rows
  are seal-script gaps (39), Devanagari counters and the यू bowl (5), the
  pixel sprite's transparent slot, the "d" counter of Radikal (whose "a"
  counters were already bare), the isometric frame's hole and its neighbour,
  and gaps between the crest's mantling leaves. The one on Drone is a speck in
  the badge. None is the body of a hollow letter.
- **A non-letter kept sewn: 1.** `heraldic_crest` area #2: a 9.8 mm2 gap
  between mantling leaves on the right, tagged lettering, so it stays white,
  while its mirror twin #1 on the left (10.0 mm2, untagged) goes open. That is
  the same "some have it, others don't" Kent pinned, left on one gap.
- **Letter bodies kept: 25 of 25** (Becker's five on all five pairs).
- **White drawn as transparency on purpose:** Becker is the only case found,
  and the guard keeps it. None of the six corpus movers is a white-on-dark
  logo. On `kanji_seal` the transparent gaps are the paper of a stamp. ON sews
  them as fabric, so on a dark garment the seal reads red on dark, which is
  what its open outer spaces already do.

## Pictures (gitignored, our output and Commons art only)

`digitizer/eye_pairs_out/transparent-white-1111/` in this lane:
`<slug>_source_off_on.png`, with the source on a checkerboard, then OFF, then
ON, at 12 px/mm. There is one per mover: kanji_seal, devanagari_logo,
pixel_art_sprite, heraldic_crest, neon_outline_sign, isometric_icon and
precision_drone. Drone's panel is OFF | ON only, because its art is a
client's. The rows are in `corpus.json` and `pro.json`; the plain-rule rows
are in `plain/`.

## What Kent decided

From the seven pictures Kent chose "Flip ON (Recommended)" (2026-11-11). He did
NOT choose "fix the crest gap first", so the tagger and the crest's one tagged
mantling gap are left as they are. The catch stands: the guard is the text
tagger. A hollow letter it misses goes open (none found here), and a non-letter
it tags stays white (one gap on the crest).

This refines the 2026-10-27 "Every job" white recipe; it does not undo it.
`sew_enclosed_white` still sews every job. Only areas the art leaves
transparent stay open.

Not run: no sew-out; ProSeal (no committed art); no kappa or pro-side reading
(this moves only our white).

## The flip (2026-11-11)

Default `True` in `config.py`. `tests/engine_2026_10_27.json` and
`conftest.PRE_FLIP` (`WHITE_2026_11_11_OFF`) hold it False, so every
`frozen_cfg()` pin still runs the engine from before the flip. What moves
when the default goes ON (Windows box, OFF vs ON; OFF reproduces the
committed figures):

- **Goldens and md5 pins: none.** Full suite with default ON: the only
  failures were tests ABOUT the OFF behaviour (5 in this flag's file, 2 in
  `test_sew_enclosed_white.py`, now pinned OFF explicitly) and the two
  enthusiast_logo platform reds, which are byte-identical OFF and ON.
- **Tripwire ledger: 1 of 18 jobs.** `precision_drone`: stitches 14,769 ->
  14,760, trims 86 -> 85, hops 122 -> 121, needle-up 1,442.6 -> 1,419.8 mm,
  direction kappa 0.084 -> 0.088, **sttype kappa 0.376 -> 0.374**. That last
  figure is past its tolerance of 0, in the "worse" direction. The cause is
  the 0.85 mm2 badge speck going open. The ledger needs a CI capture. Becker
  x5 is identical, and the others have no alpha or no enclosed area.
- **Corpus scorecard: 2 of 26 fixtures.** `logo_alpha.png`: its blue ring's
  transparent hole, 160.7 mm2, now stays open (synthetic art, the rule as
  written). `photo/drone_render.png`: a 1.6 mm2 speck. Both garments each.
  The baseline needs a CI capture. The other 24 are identical.
- **Lettering board (11 jobs): not re-run.** Becker x4 plans identical
  stitches. Gaulke x2 and MFab x2 have no alpha. Fremont x2 has no enclosed
  area. On Drone the one change is a speck in the badge, outside every
  lettering line. So no recapture is asked for.
- **Service default path, one real `/digitize`** (`kanji_seal.png`, the
  Studio's request shape: 80 mm, `sew_enclosed_white` true, white, flag not
  sent). 39 transparent enclosed shapes, **0 stitched**, one thread
  (Poinsettia), 10,945 stitches, 21 trims. The same request with
  `enclosed_white_skip_transparent: false`: 39 of 39 stitched, Poinsettia +
  White (10.96 m), 29,505 stitches, 71 trims.
