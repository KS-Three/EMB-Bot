# Tier D: flags deleted by flag consolidation

Kent, 2026-11-19: "Delete all six" (`docs/flag-audit-2026-11-19.md`, tier D). Each was OFF by default and
ruled against; the code, the tests that turned it on and the tool arms that built it are gone, and the
field names are in `digitizer_core.config.RETIRED_FIELDS` (a request or snapshot that still names one is
ignored, never an error). What each one was, and why it went, is below, moved verbatim from its config
comment, PR pointers kept. The research docs it cites still stand.

## `coverage_edges` (field)

Last default: OFF. Kent 2026-10-12: no. Also removed with it: the `PipelineConfig.__setattr__`
`DeprecationWarning`, `stage4_vectorize._coverage_parts` / `_one_ink_cutout`, `tests/test_coverage_edges.py`.

```text
The same upscaled alpha cutout, outlined from the source's alpha
DIRECTLY instead of repaired from the mask. The `alpha < 128` mask and
its NEAREST enlargement throw the ramp away and stage 4 then walks a
staircase of source pixels, moving one vertex at a time back toward
where the ramp says the edge is. ON, a region bounded by transparency
all the way round takes its polygon from the half-coverage contour of
the source's own alpha (marching squares, `skimage.measure.
find_contours` at 127.5) — the line the mask's threshold was a
one-pixel quantisation of — then the same Douglas-Peucker and the same
area floors as any other region (`stage4_vectorize._coverage_parts`).
Measured 2026-10-10 on the busiest single-colour layer of golden_tee
and hotel_fremont at 1.8 px/mm against their own native-resolution
edges (`docs/tracer-head-to-head-2026-10-10.md`, addendum): median
edge error 0.09-0.12 mm for the shipped polygon, 0.04-0.05 for this
one, a third of the turning and a quarter of the vertices; by 5 px/mm
the two agree. On `becker_marine_logo.png` the shipped polygon's
reversals (vertices turning back more than 120 degrees, which the
native read above introduces: 7.1 per 100 mm of outline, 0.0 with it
off) go to none.
It applies to ONE class of source: a single ink with its whole shape
in alpha, enlarged by stage 1 (`stage4_vectorize._one_ink_cutout`).
There every edge is an alpha edge; an enclosed transparent region is
read from the same contour's other side, so ink and hole share a line.
What it does NOT touch: a source at its own resolution, a source with
no alpha, and a cutout with a second ink in it (two colours meet along
an edge alpha says nothing about) — each keeps today's polygon whole.
The costs on the table: half coverage cuts across a sharp corner by a
fraction of a source pixel, where the native read above fits the two
sides and squares it — on a clean synthetic bar that read is the
better polygon (0.03 mm at worst against 0.22), and it is real
artwork, where the fit is refused more often than not, that the
contour wins on; and a stroke under about one source pixel wide never
reaches half coverage, exactly as it never reached the mask. No
physical constant — every number is a raster quantity of the source.
Default OFF and byte-identical off; no sew-out has seen it.
`tests/test_coverage_edges.py`.
DEPRECATED (Kent 2026-10-12: no). Still readable and still behaves as
described above — setting it True changes nothing but emits one
`DeprecationWarning` naming this ruling (`PipelineConfig.__setattr__`).
The trail: PR #818 built it; PR #824 found it helps only under the
Column lane; PR #841 (`tools/counter_slots.py`) found it narrows three
MARINE slots below one thread (0.4 mm) at 80 mm that the lane alone keeps
open. Kent 2026-10-12: no. The research docs
(`docs/coverage-edges-under-columns-2026-10-11.md`,
`docs/coverage-counters-2026-10-11.md`) and `tools/counter_slots.py`
stay as the record; do not flip it, and do not build on it.
    coverage_edges: bool = False
```

## `resnap_hairline_never_lightens` (field)

Last default: OFF. Kent chose fix B (`line_chain_one_thread`) over it on 2026-11-11 and ruled that OFF too
(`docs/border-colour-change-2026-11-11.md`). Also removed: the `hairline_keeps_ink` guard in
`stage4_vectorize.revalidate_threads`, `tests/test_resnap_hairline.py`.

```text
A drawn outline keeps ONE colour (built OFF 2026-11-11, Kent on
`C_low_poly` pin 2: "the change in bean stitch bordering looks off").
The thread re-check (`stage4_vectorize.revalidate_threads`) re-matches a
shape to the median of the pixels its final polygon covers. For a LINE
(smallest dimension at most `bean_rule.LINE_MAX_MM`, 1.2 mm: the
reference digitizer's own definition of a drawn stroke) those pixels are
mostly the anti-alias halo and the ground beside it, so a black outline
laid against a pale face reads grey and is re-snapped to a grey spool:
the dolphin's fin edge sews 18 mm in Silvery Grey where the art's line
is black on every pixel (darkest 0 of 255), and the ribbon changes colour
at an arbitrary point, not at any seam of the art. ON, a line the
re-check would move to a LIGHTER spool (CIELAB L*) keeps the one stage 2
chose from the whole cluster; a line it would darken, and every shape
wider than a line, re-snaps as before. The 1.2 mm is geometry, not
cloth: gate 1 does not apply. False is the engine before the flag, byte
for byte. Tests: `tests/test_resnap_hairline.py`;
`docs/border-colour-change-2026-11-11.md`. OFF; Kent chose fix B
(`line_chain_one_thread`) over it on 2026-11-11 and ruled that OFF too.
    resnap_hairline_never_lightens: bool = False
```

## `line_chain_one_thread` (field)

Last default: OFF. Kent 2026-11-11, eye-check of 5 rows: "Keep off, very little improvements were made, if
any." Also removed: `digitizer_core/line_chain.py` (the whole module; its docstring is below),
`tests/test_line_chain.py`, the call in `pipeline.py`. 4 of 21 rows moved
(`docs/line-chain-one-thread-2026-11-11.md`).

```text
One thread per connected drawn line (built OFF 2026-11-11, Kent on
`C_low_poly` pin 2, then "Keep OFF, build fix B"). The art's outline is
one black line; stage 2 and the thread re-check read each piece of it
from its own anti-aliased pixels, so it sews black, Blackberry and
Silvery Grey. ON, after the re-check (`line_chain.apply`): lines no
wider than `bean_rule.LINE_MAX_MM` that touch (within 0.3 mm) form a
chain; when its pieces carry different threads AND every piece's CORE
colour (the pixels farthest from the ground beside it) lies within
`line_chain.UNIFORM_DE00` of the chain's median, the chain takes the
loaded spool nearest that core colour and its pieces move to that cone's
layer. A chain whose core colours really differ is left alone. The cone
set never grows, so the colour cap works from the same palette. False
is the engine before the flag, byte for byte. Tests:
`tests/test_line_chain.py`; `docs/border-colour-change-2026-11-11.md`.
OFF by Kent's ruling 2026-11-11, eye-check of 5 rows: "Keep off, very
little improvements were made, if any." Do not propose the flip from the
dE00 numbers (`docs/line-chain-one-thread-2026-11-11.md`).
    line_chain_one_thread: bool = False
```

`digitizer_core/line_chain.py`, module docstring as it stood:

```text

Kent on `C_low_poly` pin 2 (docs/border-colour-change-2026-11-11.md): the
art's outline is ONE black line, and it sews in two or three colours because
stage 2 and the thread re-check read each piece of it from its own anti-aliased
pixels. The flag that only stops the re-check lightening a hairline
(`resnap_hairline_never_lightens`) moved other things: the inner lines went
blue-grey and a whole slab changed colour through the colour cap. This works
on the LINE, not on each piece:

1. **Candidates.** A region no wider than a drawn line (`bean_rule.LINE_MAX_MM`,
   1.2 mm: geometry, not cloth, so gate 1 does not apply) that is not an
   enclosed-background hole or a specialty step.
2. **Core colour and ink test.** For each candidate, the colour of the pixels of
   its footprint that stand farthest from the ground beside it (the ring of
   pixels just outside every candidate; pixels shared with another candidate are
   not read): a black
   line reads black, not the grey of its halo. The farthest `CORE_FRAC` of the
   footprint, averaged in CIELAB. A candidate whose core is within
   `INK_CONTRAST_DE00` of its ground is a thin sliver of the FACE beside it,
   not a drawn line, and takes no part.
3. **Chains.** Ink candidates whose polygons lie within `LINK_MM` of each other
   are one drawn line (the pieces an outline is cut into by colour, and the
   mesh lines that cross it).
4. **Uniformity test.** A chain is ONE colour only when the pieces whose core
   sits within `UNIFORM_DE00` (CIEDE2000) of the chain's median core colour
   hold at least `MAJORITY_AREA_FRAC` of its area. A line that really changes
   colour (a red piece beside a blue piece) holds half at most, fails this and
   is left exactly as it was: a chain is never forced. A speck outside the
   band does not stop the line and is left as it is.
5. **The thread.** The loaded spool nearest the median core colour of the
   pieces inside the band; among spools within `TIE_DE00` of the nearest, the
   most used (so one near-black line is not split between Black and Blackberry).
   "Loaded" = the thread of every region that is not a candidate, plus the
   chain's own current threads: the cone set never grows, so the colour cap
   that runs after this has the same palette to work from (the slab-colour
   swing of the hairline flag came from changing which cones exist).
6. Every piece of the chain takes it, and moves to the earliest layer that
   declares that cone, as `stage4_vectorize.rehome_resnapped_regions` does, so
   one spool sews at one position and no layer sandwiches another.

Chains whose pieces already share one thread are untouched. Off, never called.
"""
```

## `cfg.extra["fill_angle_pro_slant"]` (extra key)

Last default: OFF (an `extra` key, never a field). Built 2026-11-07 (#1346's 18-job pass priced it);
`docs/fill-angle-pro-slant-2026-11-07.md` is the research. Also removed:
`stage6_fill.pro_slant_angle` / `_slant_for`, `machine.FILL_ANGLE_SLANT_COLS_RATIO` / `_SLACK`, stage 5's
`_explicit_fill_angle`, `tests/test_fill_angle_pro_slant.py`, the `--slant` arm of
`tools/fill_angle_pro_census.py`. Kept: `fill_angle_pro_offset` (a separate key) and
`machine.FILL_ANGLE_PRO_DEG`.

`machine.py`, the trims guard:

```text
The trims guard of `cfg.extra["fill_angle_pro_slant"]` (2026-11-07, built
OFF; `docs/fill-angle-pro-slant-2026-11-07.md`). A slanted candidate (+20,
then -20) is taken only when its rows cut the shape into at most
ratio x columns-at-the-angle-OFF-sews + slack monotone columns
(`stage6_fill._cols_at_angle`, at FILL_ROW_MM). Read off #1346's 18-job
OFF/ON pass, where every in-fill cut it added sat on a shape whose columns
grew x1.5 or more (MFab LC's field 19 -> 70 columns, +5 cuts; Drone's three
small fills x1.5-x2.2, +6), while Becker's fields grew x1.0-x1.12 and LOST
a cut each. A routing proxy chosen on that one pass, not a cloth constant.
```

`stage6_fill.py`, the key and the angle rule:

```text
`cfg.extra[FILL_ANGLE_PRO_SLANT_KEY]` (2026-11-07, built OFF): the same
pro angle, but per shape: +20, else -20, whichever first passes the trims
guard (`pro_slant_angle`); a shape neither passes keeps the angle it sews
OFF. Implies the offset rule; it does not need that key set too.

"""`cfg.extra["fill_angle_pro_slant"]`'s angle for one shape: +20 if its
rows pass the trims guard, else -20 (160) if those do, else None.

The SIGN of the pro's slant is not predictable from anything we read
(2026-11-07: art edge slant, our satin crossings' slant, the shape's
principal axis side, its boundary's slant and which sign cuts fewer
columns all score at or below "always +" leave-one-artwork-out, 12 of
17 jobs; `docs/fill-angle-pro-slant-2026-11-07.md`). So + is the prior,
and the only thing that moves a shape off it is cost: the guard takes a
candidate only when it cuts the shape into at most
`FILL_ANGLE_SLANT_COLS_RATIO` x the columns at `base_deg` +
`FILL_ANGLE_SLANT_COLS_SLACK`. Columns are what fill cuts grow from:
every in-fill cut #1346's fixed angle added sat on a shape whose columns
grew x1.5 or more. Memoized on the polygon's bytes (`lru_cache`, so
thread-safe): stage 5 and stage 7 ask about the same shape several times.
"""
```

## `lettering_columns_apex_cut` (field)

Last default: OFF. Built 2026-10-25. Kent 2026-11-14 withdrew the flip ("I want it exactly like the pros"):
the apex_cut corpus table (`docs/apex-cut-corpus-2026-11-14.md`, 43 designs) found it better on 10, worse
on 4, mixed on 1 and `apex_guard` did not change that (`docs/apex-guard-2026-11-14.md`). The pro's own
construction is `apex_pro` (`docs/apex-pro-construction-2026-11-14.md`), which stays: it reuses
`_apex_walk`, `_apex_tips`, `_apex_stems` and `_apex_column`, so those functions are kept. Removed:
`outline_cut._apex_cuts`, `_APEX_CUT` and `apex_cut_scope`, the "apex" cut record's consumers in
`columns.py` (`apex_crosses`, `_apex_tip_columns`, tip / dead-end handling in the span graph and Euler
trail) and `outline_cut` (`_APEX_CUT` branches, `_apex_tip_piece`), `tests/test_column_apex_cut.py` (its
shared letter fixtures moved to `tests/_apex_letters.py`), `tests/test_column_apex_walk.py`,
`tools/apex_walk_census.py`, the `letter_columns(apex_cut=...)` argument, the flip-sheet FLAGS row.
`_APEX_EXIT_MM` stays in `columns.py`: the `lean_flat_ends` hop cover reads it.

Config field comment:

```text
Under `lettering_columns`, where two strokes meet at an acute tip --
the M's V, each of a W's three apexes, a pointed A or N -- the tip
sews as ONE column whose crosses span both strokes, cut off them along
that cross (2026-10-25, built OFF; `outline_cut._apex_cuts`). Read
with one rule on the professional's DSTs and ours (Becker MARINE at
four widths, MFab AND WELDING hat and LC, PROSEAL;
`tools/letter_pieces.py`): through every such tip he sews one piece,
crosses within 16 deg of the line of text, 1.0-2.4 stroke widths
across; the lane mitres it into two fanning half-width columns (the
M's V, PROSEAL's A) or pivots one column through it (MFab's W, 30-89
deg). `lettering_columns_corner_fold` does not reach these: it folds
L corners and refuses an acute tip (`long_way`). Layout, judged in
the preview (Kent, 2026-10-22), so ON-eligible from renders. False is
the cut as it is, byte for byte. Set for the whole plan by
`pipeline.plan_stitches` (`outline_cut.apex_cut_scope`).
Tests: `tests/test_column_apex_cut.py`.
    lettering_columns_apex_cut: bool = False
```

`outline_cut.py`, the rule as written beside `_APEX_CUT`:

```text
`apex_cut` (`cfg.lettering_columns_apex_cut`, 2026-10-25, built OFF): where
two strokes meet at an acute tip -- the M's V, each of a W's three apexes,
a pointed A or N -- the professional sews the tip as ONE column whose
crosses run from one stroke's outer edge to the other's, and cuts the two
strokes off it along that cross. Read with one rule on both files
(`tools/letter_pieces.py` crosses, 2026-10-25: Becker MARINE at four
widths, MFab AND WELDING hat and LC, PROSEAL hat; the PR's table): through
every such tip zone he sews one piece, its crosses within 16 deg of the
line of text, spanning both strokes 1.0-2.4 W (7 mm at most). The
junction rules mitre the tip instead, from its inside corner (the crotch)
to its point -- two columns fanning into one seam, each crossing half the
stroke (the M's V, PROSEAL's A) -- or, past the mitre's 1.8 W reach (a W's
2.3-3.2 W tips), leave it whole and the column pivots through it (30-89
deg off the line of text). ON (`_apex_cuts`): from the crotch toward the
tip, the first cross square to the apex's axis that spans both strokes
within `APEX_CROSS_W` stroke widths and `APEX_CROSS_MM` is a cut, the
crotch is joined to it along the axis, and the cut the rules took from
that crotch is dropped. A tip is the nearest convex corner along the
crotch's bisector on which the two strokes CLOSE, as a V does: on toward
it the cross shrinks -- halfway there to `APEX_CLOSE_MID` of the cut's,
four-fifths of the way to `APEX_CLOSE_FAR` (the tips he merges read
0.44-0.68 and 0.17-0.50, PROSEAL's flat-topped A the 0.68 and 0.50; a
stroke's end, MARINE's slab corners and N foot, a crossbar's root
0.73-0.94 or 0.53-0.90), or it holds its width to halfway and then
closes to `APEX_SHOULDER_FAR` (MARINE's M at 101.9 mm, whose V runs
between its stems' edges before its point: 1.02 and 0.34; the nearest
refused, 0.89 and 0.40) -- at a rate that puts the strokes
under `APEX_MAX_DEG` apart (an L corner is 90: MFab's square A, which he
folds -- `corner_fold`), and nothing past the cut is a junction (a
crossbar's root, an N's foot: no concave corner further than half a
stroke from the cut). Candidates, not fabric constants: layout, judged in
the preview (Kent, 2026-10-22).
```

## `cfg.extra["lettering_columns_apex_guard"]` (extra key)

Last default: OFF, read only while `apex_cut` was on, so it went with it (Kent 2026-11-14 withdrew the flip;
`docs/apex-guard-2026-11-14.md`). Removed: `_APEX_GUARD`, `APEX_GUARD_SHARE`, `apex_guard_scope`,
`_apex_guard_refuses`, `tests/test_column_apex_guard.py`.

```text
`apex_guard` (`cfg.extra["lettering_columns_apex_guard"]`, 2026-11-14,
built OFF; read only while `apex_cut` is on). The corpus table
(`docs/apex-cut-corpus-2026-11-14.md`, 43 designs) found apex_cut better on
10, worse on 4 and mixed on 1. Read tip by tip, the merged tips behind the
losses are of two kinds, and the gains are neither:
- a STROKE UNDER ONE SATIN CROSS (`machine.SATIN_MIN_CROSS_MM`): the
  0.18-0.19 mm white rings outline_lineart_logo's tagger took for letters.
  Merged, the ring's notches walked long bars across the black letter
  inside it. The gains' strokes are 0.69 mm and up.
- a cross the walk found only by SLIDING TO ITS LIMIT. The cut sits below
  the crotch (an "apex_stub") and the cross takes `APEX_GUARD_SHARE` or
  more of the limit (`APEX_CROSS_W` x W, or `APEX_CROSS_MM`). The walk
  stepped off the crotch until a cross first fitted, so the limit chose
  that cross, not the strokes closing: a stroke END, not a V. The losses
  read 0.96-1.00 of the limit: k_line's K foot and N, Drone's N top (two
  long stitches across the stem), mfab_lc's W middle apex and N tops,
  duotone's "2" foot, and_pizza's Z joints. The gains that slid read
  0.39-0.76 (Bridge's crossed blocks, duotone's N, Becker LC's M). The
  rest cut through the crotch itself (Becker's M, ProSeal's A and M), and
  most crosses there sit at 0.9-1.0 of the limit too, so the share alone
  separates nothing.
The guard refuses the crotch outright. It does not try the next tip, so a
refused letter cuts as it does OFF. Kept back with it: and_pizza's Z-joint
cure. Each Z's two joints are one shape turned 180 deg, and only the
top-right one fans, so what fans is the sewing order there, not the tip.
A candidate, not a fabric constant (gate 1): layout, judged by eye.
```
