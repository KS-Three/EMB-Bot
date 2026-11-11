# Fix B: one thread per connected drawn line, `line_chain_one_thread` (built OFF, 2026-11-11)

Context: Kent's pin 2 on `C_low_poly` ("border stitches that contain colour changes"),
the finding that it is a drawn line re-snapped to grey, and the first, blunt flag
`resnap_hairline_never_lightens` (PR #1391, OFF) are in
`docs/border-colour-change-2026-11-11.md` (on that PR's branch until it merges).
Kent saw four pictures of that flag (low_poly's inner lines went blue-grey,
isometric's top slab went from dark gold to bright yellow) and answered "Keep OFF,
build fix B". This is fix B. A new flag, default OFF, nothing flipped on (gate 3),
no physical constant (gate 1: every threshold is a raster measure or the existing
1.2 mm line width). All numbers are instrument readings (gate 4). Our own
output only; no pro files.

## What it does

`digitizer_core/line_chain.py`, called once from `pipeline.py` right after the
thread re-check and the rehome, before the colour cap counts cones:

1. **Candidates**: a region no wider than a drawn line (`bean_rule.LINE_MAX_MM`,
   1.2 mm).
2. **Core colour and ink test**: for each, the colour of the pixels farthest from
   the ground beside it (the ring just outside every candidate; pixels shared with
   another candidate are not read), 20% of its footprint, averaged in CIELAB. A
   candidate whose core is under `INK_CONTRAST_DE00` (25) from its ground is a thin
   sliver of the face beside it, not a line, and takes no part.
3. **Chains**: ink candidates within `LINK_MM` (0.3 mm) of each other. Only chains
   whose pieces carry more than one thread can change.
4. **Uniformity test**: the pieces whose core is within `UNIFORM_DE00` (12) of the
   chain's median core must hold at least 90% of the chain's area. A line that
   really changes colour fails and is left exactly as it was. A speck outside the
   band does not stop the line and is left as it is.
5. **Thread**: the loaded spool nearest the median core colour (loaded = every
   non-candidate region's thread plus the chain's own, so the cone set never
   grows); among spools within 15 dE00 of the nearest, the most used (one near-black
   line is not split between Black and Blackberry).
6. The chain's pieces take it and move to that cone's earliest layer, as
   `rehome_resnapped_regions` does, so one spool sews at one position.

## Results, 21 Commons rows, tree 950855bf + this change (rembg venv present)

OFF is byte-identical to the stored capture `corpus_runs/main-950855b`: the full
stitch list is equal on the 4 rows that move (low_poly, silhouette, vintage,
chalkboard) and on the 8 rows run both ways for the earlier flag. 17 of 21 rows are
identical with the flag ON.

| row | stitches OFF to ON | trims | colour blocks |
|---|---|---|---|
| `C_low_poly` | 10,866 to 10,844 (-22) | 91 to 84 | 6 to 6 |
| `C_silhouette_logo` | 24,911 to 25,003 (+92) | 39 to 38 | 6 to 6 |
| `C_vintage_engraved_badge` | 22,440 to 22,432 (-8) | 199 to 199 | 3 to 3 |
| `C_chalkboard_lettering` | 27,583 to 27,513 (-70) | 110 to 107 | 6 to 6 |
| the other 17 rows | identical | identical | identical |

**What Kent asked about, named:**
- **low_poly's fin outline: moved, fixed.** One black ribbon round the silhouette
  (chains found 6; 5 unified onto 1776 Blackberry, 1 left alone, two pieces whose
  cores really differ).
- **low_poly's inner lines: not turned blue-grey.** The inner mesh lines are in the
  same chains and take the same Blackberry; the blue-grey stretch near the tail that
  OFF has comes out black. No new spool: 6 colours, 6 blocks, as OFF.
- **isometric's top slab: not moved.** The row has 7 line candidates and 0 pass the
  ink test, so nothing is recoloured and the design is identical to OFF
  (11,487 stitches, 8 blocks). The slab swing of the first flag was the colour cap
  re-choosing a cone, and this flag changes no cone.
- **A genuinely two-colour line is not forced**: unit test, and on vintage_engraved_badge
  5 of 7 chains were refused by the test (light and dark pieces of one drawing)
  while 2 uniform ones were unified.

What else moved (all small, chain counts from a debug run of the final module):
silhouette_logo has 3 chains and unifies 2 (2 light-green line pieces, 5422 to
5050), refusing 1; vintage 7 chains, 2 unified (black/eggshell pairs to black), 5
refused; chalkboard 4 chains, 2 unified (3 pieces to black 0020), 2 refused.

## Pictures

Same-scale three-panel pictures (Commons art, OFF, fix B), our own output only, in
the gitignored `digitizer/eye_pairs_out/border-colour-1111/`:
`low_poly_art_off_fixB.png`, `low_poly_zoom_art_off_fixB.png`,
`isometric_icon_art_off_fixB.png`, `isometric_icon_zoom_art_off_fixB.png`.

## Catches

- The thresholds (25, 12, 0.9, 15 dE00, 0.3 mm) are raster measures set on these
  21 rows. They are not a corpus-wide calibration: 21 Commons logos, and low_poly is
  the only row that shows the defect clearly. A wrong uniformity test forces one
  colour on a truly coloured line; the test refuses on a 50/50 two-colour line and
  on 5 of 7 vintage chains, but there is no row in the corpus with a real
  coloured-outline drawing to prove it on.
- It reads the art's pixels (`Prep.rgb`), so it only sees what stage 1 handed over;
  a line thinner than a source pixel gets a core from the halo too (the pieces of
  low_poly are 1 to 2 source pixels wide and it works there, but that is one image).
- Not run: the full digitizer suite, the three expected CI goldens, a sew-out, the
  Studio. Not flipped on: that is Kent's.

Tests: `tests/test_line_chain.py` (7): default OFF; a black line cut into black and
grey pieces takes one thread and the layer; a red/blue line is not forced; a speck
outside the band is left alone; a pale face sliver near a line neither vetoes it nor
is recoloured (fails if the ink test is removed); one-thread chains untouched; the
cone set never grows.

## Ruling: OFF (Kent, 2026-11-11)

After the eye-check of five rows (low_poly, isometric, silhouette, vintage,
chalkboard), Kent: **"Keep off, very little improvements were made, if any."**
`line_chain_one_thread` stays default OFF. No flip PR, no pro-pair run, no further
build on this line, and no retuning of the thresholds to look for a bigger effect.
Do not propose the flip again from the dE00 numbers above: they say the recoloured
pieces moved toward the art's ink; Kent judged the pictures and the effect too
small to ship. `resnap_hairline_never_lightens` (the first flag, PR #1391) is
likewise OFF; he chose this one over it and then ruled this one OFF.
