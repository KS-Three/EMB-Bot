# Beanie knockdown, ON for beanies (2026-10-21)

Rule R9 of [`pro-digitizer-rules-2026-10-21.md`](pro-digitizer-rules-2026-10-21.md):
every beanie in the professional's zip opens with a **knockdown**, a sparse fill under
the whole design, sewn first in its own colour block. It presses the knit's pile flat
so the design sits on top instead of sinking between the ribs. We had nothing like it.
This builds it behind `cfg.beanie_knockdown`, in
`digitizer/digitizer_core/knockdown.py`. Built OFF, then **flipped ON by Kent the same
day** over the renders below, with the ruling that the engine should know what a garment
needs, the way it knows backing, rather than ask per logo. So every beanie with a known
garment colour gets one; nothing else changes.

## What the pro's files say (read from the DST, block 0)

Six beanie files, five jobs. `row_pitch_union` for rows; the outline margin is the
distance from the knockdown's edge to the rest of the design, both drawn as 0.3 mm
lines at 10 px/mm (so it reads about 0.2 mm short; see "ours" below, built at 2.0).

| file | stitches | pieces | trims in it | stitch (mm) | rows (mm) | angle | margin p10 / p50 / p90 (mm) |
|---|---|---|---|---|---|---|---|
| Becker beanie | 2,340 | 1 | 0 | 3.45 | 0.49 | 157.5 | 1.26 / 1.80 / 2.22 |
| Plowing beanie | 2,709 | 1 | 0 | 3.45 | 0.49 | 157.5 | 1.14 / 1.60 / 2.60 |
| Roofing beanie | 1,981 | 1 | 0 | 3.01 | 0.45 | 21.5 | 1.52 / 1.82 / 2.31 |
| Proseal beanie | 2,007 | 1 | 0 | 3.01 | 0.41 | 17.5 | 1.40 / 1.70 / 2.33 |
| To a T beanie | 2,407 | 1 | 0 | 3.50 | 0.51 | 0.5 | 0.76 / 0.84 / 0.92 (badge) |
| Machine beanie E | 2,021 | 1 | 0 | 3.50 | 0.51 | 0.5 | 0 (inside the badge's satin border) |

- **One needle-down piece, no trim, every file.** The outline is the design grown and
  every hole filled (no hole over 1 mm² in any of them); lines of text close into one
  slab where they sit within ~4 mm.
- **No underlay** (the rules doc's §1d: BARE or RUNONLY).
- **Colour:** both PES files that carry the job name the knockdown cone **Khaki** /
  **PMS 155**, a colour the design never uses: the garment's. DST carries no colour.
- **The badge files differ:** on To a T and Machine E the badge's own satin border is
  the outline, so the knockdown stops level with it (0 to ~0.7 mm). Not copied here.

## What was built

`knockdown.knockdown_block`, called from `pipeline.plan_stitches` after stage 7:

1. Union of every planned shape (stage 5's polygons), grown by `MARGIN_MM` 2.0, holes
   filled, pieces under 10 mm² dropped.
2. `stage6_fill.stitch_shape`, tatami, rows `ROW_MM` 0.50, stitch `STITCH_MM` 3.5,
   `underlay_style="none"`, angle auto.
3. **Every lift inside a piece becomes a run along the edge** (`_stay_down`). Stage 6's
   travel gives up past 4x the straight distance or 20 mm and lifts; on Becker that cost
   the first build three trims where the pro has none. The thread is the garment's
   colour and everything sews on top of it, so a long edge run costs only thread.
4. Tied like any block, sewn in the cone nearest `cfg.garment_rgb`, prepended as block
   0. If the design's first block is that same cone it joins that block across a trim
   instead of costing a stop.

**Keyed off the garment AND a flag.** It only ever fires for `garment_id == "beanie"`
(the Studio already sends it, and `fabrics.GARMENT_FABRIC` maps it to jersey); the flag
exists so the pre-flip engine stays one switch away. **No garment colour, no knockdown**: one in a design
colour would sew a visible 2 mm halo round the logo.

`tools/pro_pair.py` gains `--set KEY=JSON` (repeatable) so a flag and `garment_rgb`
can ride the Studio request; without it the tool is unchanged.

## Ours against the pro (`pro_pair`, garment `beanie`, flag ON)

Read off our `ours.dst` with the same script as the pro's table.

| job | knockdown stitches | pieces / trims in it | rows (mm) | stitch (mm) | margin p10 / p50 / p90 | pro margin p50 | trims OFF -> ON (DST) | stitches OFF -> ON (DST) |
|---|---|---|---|---|---|---|---|---|
| Becker @ 76.8 mm, khaki | 2,514 | 1 / 0 | 0.49 | 3.47 | 1.62 / 1.86 / 2.28 | 1.80 | 23 -> 23 | 5,698 -> 8,212 |
| Roofing @ 90.8 mm, charcoal | 1,682 | 1 / 0 | 0.48 | 3.47 | 1.68 / 1.82 / 2.02 | 1.82 | 33 -> 33 | 6,092 -> 7,774 |
| To a T @ 80.6 mm, khaki | 2,356 | 1 / 0 | 0.51 | 3.50 | 1.50 / 1.64 / 1.74 | 0.84 (badge) | 62 -> 62 | 17,714 -> 20,070 |

Trims and stitches are pystitch's read of each `ours.dst`, OFF and ON alike. The
knockdown costs no trim on any of the three and one colour change each. On the
two free-standing logos the margin lands on the pro's (1.86 vs 1.80, 1.82 vs 1.82).
On To a T, a badge, ours reaches about 0.8 mm further than his: he stops the
knockdown at the badge's satin border.

Renders: `docs/renders/beanie-knockdown-2026-10-21/` — `<job>_on.png` is
art | ours ON | pro at 20 px/mm (pro colours are pystitch's stand-ins: a DST has none),
`<job>_off.png` is the same sheet with the flag OFF.

## Gate 1

`ROW_MM` 0.50, `STITCH_MM` 3.5 and `MARGIN_MM` 2.0 are a professional's physical
constants read from his files, **not sewn here**. Kent flipped the default ON over
them anyway (2026-10-21); they remain the pro's numbers, and a sew-out that disagrees
moves the constants, not the rule. The rest (sew it first, one piece, no underlay,
garment colour) is the pro's habit on 6 of 6 files.

## Not done

- The badge case (knockdown level with a satin border rather than 2 mm past it).
- Manual digitizing (`manual.py`) does not call it.
- The browser engine (`src/`) has no knockdown.
- OFF is the pre-flip engine byte for byte: `tests/test_beanie_knockdown.py` pins
  `logo_alpha.png` at 60 mm on a beanie (OFF) and on a hat (ON, which must not fire)
  against md5s captured from `git archive 2e873933`.
