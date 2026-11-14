# "Random cross over stitch": the long needle-down joins (2026-11-14)

Kent pinned six "random" stitches in the 11-10 sitting: four on Becker hat
large ("Random Cross over stitch shouldn't be here", @56.98,12.6 /
37.28,16.79 / 89.02,62.82 / 95.43,50.74) and one on MFab hat ("This random
stitch in the middle doesnt match the pros", @69.99,16.77). The Director
asked whether they are the single needle-down stitches of 14-92 mm found in
`docs/satin-flat-ends-2026-11-14.md`, why stage 7 writes them, and to fix
them at the cause.

## The pins, by eye on the render Kent saw (the 950855bf kit)

| pin | what is there | cause |
|---|---|---|
| Becker #0 (56.98, 12.6) | a straight black thread across the white letters, 0.46 mm from the pin | a **15.0 mm** needle-down join, fill -> underlay, in shape `S92f2350b` (the border body) |
| Becker #1 (37.28, 16.79) | the long black diagonal across the B and the C, 0.02 mm from the pin | a **37.5 mm** needle-down join, fill -> fill, same shape |
| Becker #14 (89.02, 62.82), #15 (95.43, 50.74) | a short diagonal ridge across the black E's block | a different cause: the Column lane's TRAVEL connector (1.6-1.9 mm stitches) sewn after the letter's own satin, on top of it (`lettering_columns_inside_connectors`) |
| MFab #2 (69.99, 16.77) | an inner loop in the white triangle | not a long stitch: no stitch over 4 mm within 12 mm of the pin. The white fill and its underlay; not traced further here |

**So 2 of the 6 pins are the long joins.** Two more are thread laid on top
of finished work by another mechanism (the connectors), and one is
something else.

## Where the join comes from

Not the fill emitter: every bridge `stage6_fill` emits between sections is
densified (`travel_path`), and a wrapper on `stitch_shape` saw no long gap
in any shape's own output. The joins first appear in the run list stage 7
hands `_shade_blocks`. Stage 7 sews one shape as several `stitch_shape`
pieces and concatenates them in two places:
- `border_from_outline`'s body pieces;
- `enclosed_white_keyline`'s field pieces.

Both come off `keyline_rest`, both are ON by default, and in both:

    f_runs, f_report = stitch_shape(piece, ...)
    o_runs += f_runs

`stitch_shape` hands its first run back needle-down (the step INTO a shape
is the caller's). Nothing ever sets that step, so the adapter writes it as one
straight stitch from the last piece's last point, whatever its length and
whatever lies between. On Becker that is 37.5 mm across the white letters.
**A plain bug: no machine sews a 37.5 mm stitch as written.** A DST record
holds 12.1 mm (`machine.MAX_STITCH_MM`). The writer encodes the rest as jump
records with the thread down, so the machine flies it uncut over the
letters. The pro cuts every such move on Becker (0 uncut, 51 cuts over his
five files, `docs/float-census-2026-11-06.md`).

That census found the same joins on 2026-11-06 (`S92f2350b`, `Sd86ce3cb`,
`S118e45fc`) and built `cfg.extra["split_long_inshape_stitches"]` (OFF). It
splits the step at 12.1 mm, as travel that "tacks the line down where it
lies". That makes the stitch sewable but keeps the same thread across the
white letters. It is what Kent pinned.

## The fix: `cfg.inshape_piece_lift` (built OFF)

At both concatenation sites, `lift_piece` decides the step:
- on the shape (the region's own polygon, holes included, within the
  0.4 mm seam tolerance stage 5 reads): sewn as travel split at
  `MAX_STITCH_MM`, as before but never longer;
- off the shape (across a hole, i.e. across someone else's work): a lift,
  `jump` and cut past `trim_at`. That is the rule `_shade_blocks` already
  applies to a run rejoining its bucket. `_chain` runs later over the
  finished group and buries the lift under later thread where a covered
  route exists; otherwise it stays cut, as the pro's is.

No new constant beyond the seam tolerance (a raster quantity of the
outline). OFF: never read.

## Census: stitches over the machine's maximum

`machine.MAX_STITCH_MM` is 12.1. "On top" is the length with no thread sewn
after it within 0.3 mm. Default config, every pro job and lettering logo
measured:

| job | over 12.1 mm (length, on top, runs joined) |
|---|---|
| becker_hat_large | 15.0 (8.9, fill -> underlay), 37.5 (18.6, fill -> fill) |
| becker_lc_large | 16.7 (8.2), 34.5 (15.7) |
| becker_hat_small | 13.7 (7.4) |
| becker_chest_small | 13.7 (7.4) |
| becker_beanie | 14.5 (7.7) |
| mfab_hat | 15.4 (9.1), 60.6 (9.1) |
| mfab_lc | 47.3 (10.0) |
| bridge ×2, gaulke hat, fremont hat, proseal hat, tires, drone, golden tee, to-a-T ×3 | none |
| lettering logos (and_pizza, k_line, jakarta, dot_music, ahora) and low_poly | none |

The bug is in BOTH default-ON sites, but it only fires where a body splits
into pieces separated by a hole: Becker's and MFab's borders. The trees vary
by row (7ad9c124 for #1479's captures, d0b4981a for this branch's); the
piece concatenation is the same code on both.

## OFF | ON (`long-joins/sheets/` in the primary checkout)

Same tree, d0b4981a (this branch, flag off vs on):

| job | longest stitch mm | joins > 6 mm (n, mm) | trims | jumps | exposed travel mm |
|---|---|---|---|---|---|
| becker_hat_large | 37.5 -> 10.3 | 3, 62.8 -> 1, 10.3 | 12 -> 14 | 13 -> 15 | 0 -> 0 |
| mfab_hat | 60.6 -> 6.5 | 2, 76.0 -> 0 | 17 -> 19 | 28 -> 30 | 0 -> 0 |

ON for the other sizes (OFF from #1479's captures): no stitch over 12.1 mm
anywhere. The longest is 4.1-5.1 mm, and each costs +1 or +2 trims.

By eye (`*_full_off_on.png`):
- Becker: both lines across the white letters (the B -> C diagonal and the
  C -> K line) are gone.
- MFab: the long white thread across the black field under "M=F" is gone.
- Nothing else visibly changes.

Becker's one remaining join over 6 mm (10.3 mm, satin -> underlay in a
letter, `S1365beb6`) is another site, inside one shape and under the
machine limit.

**md5.** OFF is byte-identical (the flag is read once and nothing else
changes). Flipped ON:
- the flat-lane golden fixtures (`FLAT_GOLDEN_MD5`: logo_alpha, whitebg,
  ribbon_curve) do not move, in the golden's config or the default one;
- `becker_marine_logo.png` does move, in both configs;
- the nightly tripwire's Becker ×5 and MFab rows will move;
- pins on a frozen config (`engine_2026_10_27.json` now names the field,
  false) cannot.

## Not fixed here

- **Becker #14, #15:** the Column lane's connector sewn over the letter's
  own satin (`lettering_columns_inside_connectors`, ON). A connector should
  run under the satin still to come, or be cut, not walk on top of finished
  satin. A separate change in `columns.column_runs`.
- **MFab #2:** not a long stitch; untraced.
