# A border that changes colour: what we do, what the pro does, what to build (2026-11-11)

Kent, defect-marks sitting 2026-11-11, `C_low_poly` (graded Bad), pin 2, kind
colour, nitpick: "The change in bean stitch bordering looks off, though it
matches the photo... You should have an agent investigate how to do border
stitches that contain color changes."

Every figure is an instrument reading on tree `950855bf` (the corpus capture
`corpus_runs/main-950855b`), not a quality claim (ROADMAP gate 4). No pictures:
the art is a Commons logo but the pro files are not ours to show. Nothing here is
a physical constant (gate 1), and nothing default-OFF was flipped on (gate 3).

## Short answer

1. **There is no border on `C_low_poly`.** The "bean border" Kent pinned is the
   art's own drawn outline, sewn as thin satin regions (about 1.05 mm columns),
   each region in one thread. `border_by_size`, `border_from_outline` and the
   edge cap sewed **0 stitches** on this row (0 runs with role `border` or
   `edge_cap`; turning either flag off changes nothing; `edge_cap="satin"` adds
   15 stitches).
2. **The colour change at the pin is not a seam of the art.** The art's line is
   black on every pixel along the fin (darkest pixel 0 of 255 in all 63 samples
   of the grey stretch and all 319 of the black one). A thread re-check in
   stage 4 (`revalidate_threads`) moved that stretch to Silvery Grey because the
   median of a hairline's own pixels is mostly halo. With the re-check off the
   whole silhouette sews black.
3. **The pro does not keep one outline colour either**, but his changes are at
   seams of the art, ends meet inside one column width, and the thing that
   changes colour is a border per patch, not a drawn line.
4. **Built, default OFF:** `resnap_hairline_never_lightens` keeps a drawn line's
   ink through that re-check. Low_poly's outline becomes one black ribbon.
   5 of 21 rows move, 16 are byte-identical. It costs +2 colour blocks on
   low_poly. Pick and catches are under "Options".

## 1. The pin

Pin 2 is at 37.61, 5.94 mm from the render's top-left, 2 mm pad included
(`marks.json`). The render's frame is `stitchviz._frame` (x right, y up in the
stored job, bbox of every stitch and jump), so the pin lands at design
(-2.6, +19.0) mm from the job's centre line, on the dorsal fin's leading edge
where the back outline meets the fin.

Stitches within 0.8 mm of it in `low_poly.json`:

| run | shape | thread | what |
|---|---|---|---|
| 188 | `S217d4f0e` | 1972 Silvery Grey, block 0 | thin satin, 98 stitches, mean step 1.05 mm, the fin's top edge; ends 0.12 mm from the pin |
| 703 | `S4b3cef25` | 1776 Blackberry, block 5 | a 0.3 mm2 speck sewn as a 17-stitch run (0.5 mm steps): the black dot on the join (`lettering_ink_stray`, `color_cap_merged_from` 0134) |
| 815 | `S45fdda37` | 1776 Blackberry, block 5 | thin satin, 196 stitches, mean step 1.08 mm, the back outline; starts 0.76 mm from the pin |
| 484 | `Sc32dc0fc` | 0015 White, block 3 | the white fill both sit against |

What the design does there, in plain words: the black outline ribbon runs along
the back, stops at the pin in a round blob (the speck), and a grey ribbon takes
over round the top of the fin, 18 mm of it, to a second handover at design
(14.5, 22.4) mm where Blackberry satin `S4fc8ef1e` takes over again (0.85 mm
end gap). The grey is sewn first (block 0) and the black last (block 5), so the
black end lies on top of the grey end. What looks off:

- **A colour break mid-run, at no seam.** The art has one black line; the
  ribbon turns grey for 18 mm and black again.
- **Not** a jump, a doubled pass or an uneven width: both columns are 1.05-1.08
  mm; the ends are 0.99 and 0.85 mm apart, under one column.
- The black speck at the join reads as a stud (a lettering-ink stray the colour
  cap merged into Blackberry).

Kent's "though it matches the photo" is a fair read of the picture at screen
size: the art's line is 1-2 source pixels wide, so at a glance the fin top is
lighter. The art's pixels say black.

**Same place elsewhere in this design: 2 ends of that one stretch** (pin 2 and
the trailing edge). The re-check re-snapped 8 regions in the design; 7 are
outline pieces of this kind. Six only went Black (0020) to Blackberry (1776),
12.2 dE00 apart, which nobody sees beside each other; one, `S217d4f0e`, went to
Silvery Grey, 43.6 dE00 from black. So one visible break, two visible ends.

Experiments, all on the stored job's own config on tree `950855bf`'s code (the
worktree tree differs only by this PR; OFF reproduces the stored design
stitch for stitch):

| arm | stitches | trims | blocks | note |
|---|---|---|---|---|
| stored / OFF | 10,866 | 91 | 6 | |
| `border_from_outline` off | 10,866 | 91 | 6 | identical: no art-outline loop sewed |
| `border_by_size` off | 10,866 | 91 | 6 | identical: no size ring sewed |
| `edge_cap="satin"` | 10,881 | 92 | 7 | +15 stitches, 1 more block |
| re-snap off (constant patched, throwaway) | 11,267 | 84 | 7 | silhouette one black ribbon |
| `resnap_hairline_never_lightens` ON | 11,205 | 85 | 8 | silhouette one black ribbon |

## 2. The code path

A border has three sources, and all three take their thread from somewhere
other than the art's edge colour:

| source | colour rule | where |
|---|---|---|
| **A drawn line** (this row) | The thread of the region the art's line segmented into: stage 2's cluster colour, then `revalidate_threads` re-matches it to the median CIEDE2000 of the pixels its final polygon covers (`stage4_vectorize.py`, after the 3x3 erosion the grader uses), then `enforce_color_cap` | `stage4_vectorize.revalidate_threads`, `pipeline.py` ~1036 |
| **A ring round a body** (`border_by_size`, `border_wanted`) | The host's own colour: `border_runs(p.visible_geom, ...)` runs right after the host's fill in the host's thread group. Rings skip every seam with another sewn region (`border_by_size_fabric_edges`, ON since 2026-10-28), so a ring faces fabric only | `stage7_sequence.py` ~4310-4350, `_owned_by_later` |
| **The silhouette cap** (`edge_cap`, "none" in the Studio's request) | Per stretch, the thread of the shape it stands against (`edge_cap_follow_adjacent`, ON, Kent 2026-10-06); stretches under `_CAP_PIECE_MIN_MM` fold into a neighbour so a junction never flickers | `stage7_sequence.py` ~4765 |

Start and end points: a ring's arcs start where `_owned_by_later` leaves them
(seam ends); a drawn-line region starts where its own path starts. Neither is
placed to hide a join. The earlier rulings:

- DOCTRINE 2026-09-09: a shared seam is bordered once, by the colour sewn on
  top, and the shape underneath skips that stretch (`_owned_by_later`).
- Memory `border-by-size-colour-seams-2026-10-28`: ring fabric edges only;
  `docs/bean-border-logic-2026-10-28.md` rule 5 ("never ring a seam between
  colours of one object").
- Memory `bean-census-2026-10-27`, `bean_only_lines` (ON): a bean only on a
  line of at most 1.2 mm. This is where "bean" for a thin drawn outline comes
  from; `bean_rule.LINE_MAX_MM` is the same 1.2 mm the new flag reuses.
- DOCTRINE 2026-09-11: the pro borders at least 19-26% of fill edge, never in the
  fill's own colour block.
- `revalidate_threads`' own docstring: the re-check exists because a thread
  chosen at stage 2 can drift off the pixels a simplified polygon covers. That
  holds for a body; for a hairline the pixels it covers are the halo.

## 3. The survey

### Ours: the 21 Commons rows, tree `950855bf`

From `corpus_runs/main-950855b/*.json` (run `role` field plus the stitch frame).

| measure | rows |
|---|---|
| rows with any role-`border` ring | 9 of 21 (93 ring runs: sprite 7, QR 34, crest 6, emoji 8, halftone dots 4, duotone 10, isometric 2, kanji brush 18, chalkboard 4) |
| rows with any `edge_cap` run | 0 of 21 |
| ring ends of different colours meeting within 1.5 mm | 3, all on `C_kanji_brush`; same-colour ends meeting: 14 (QR 10, duotone 2, kanji brush 2) |
| silhouette colour handovers, instrument below | low_poly 19, vintage badge 15, chalkboard 9, comic 8, isometric 7, duotone 4, neon 2, crest 2; 0 on the other 13 |

The silhouette instrument is crude: samples the outer contour every 0.5 mm,
labels each with the block of the nearest satin or run stitch within 1.6 mm,
merges 0.5 mm flickers. It also counts face satin sitting at the rim, so read
it as an upper bound; low_poly's 19 includes about 18 mm of grey that really is
a re-snapped outline and some belly satin that is a face colour.

Reading: a generated ring that crosses a seam is rare here (3 ends on 1 row of
21). The colour breaks that show are in **drawn lines and rim satin**, and
low_poly is the worst case by a wide margin.

### The pro: the 18 committed tripwire pairs (`testdata/tripwire_ledger.json`)

`border_pro.study` (v3) on each pro DST: a border = a satin column lying on a fill's
edge; a handover = two border columns of different blocks whose ends meet within
1.5 mm. Files read from Kent's Drive, read-only.

| result | files |
|---|---|
| no border column at all | 3 (Gaulke hat and LC, Tires hat) |
| border all in one block, never meets another colour | 4 (Gaulke beanie; the three To a T) |
| at least one different-colour handover | **11** (Becker x5, Golden Tee, Fremont hat and patch, MFab hat and LC, Drone) |
| a single fill bordered in 2 or more colours | 8 (Becker small hat and chest, Golden Tee, Fremont hat and patch, MFab hat and LC, Drone: 3 fills) |
| border in the fill's own block | 9 columns, all in the three To a T files and Gaulke beanie; 0 elsewhere |

44 different-colour handovers in all. End gap: median 0.97 mm, range 0.21 to
1.45; the columns are 1.1 to 3.5 mm wide, so ends meet **inside one column**,
which is overlap, not a gap. Golden Tee 7, Drone 14, Fremont 5-6, Becker 2 each.
Border columns are open arcs more than closed loops (any closed loop in only 6 of 18 files).

Reading: **the pro sews a border per colour patch and lets neighbouring borders
meet end to end within a column.** He does not hold one outline colour round a
whole shape, and he does not leave it out when two patches meet (11 of 18
files). Three of 18 have no border at all, so "none" is a real habit too. The
instrument is an approximation (border_pro's own caveat: a detector, not a
census); what this does not show is how his join is hidden (tie-offs, which
column sews on top), only that ends meet within a column.

## 4. Options

Two readings of Kent's note, kept apart: (a) a **drawn line** that comes out in
two colours where the art has one (low_poly); (b) a **generated border** that
has to change colour where two patches meet (the pro's habit; ours is rare).

**A. A drawn line keeps its ink: `resnap_hairline_never_lightens` (BUILT, OFF).**
In `revalidate_threads` a region of at most 1.2 mm smallest dimension that the
re-check would move to a lighter spool (L*) keeps the thread stage 2 chose from
its whole cluster. Everything wider, and a line it would darken, re-snaps as
before. Reuses `bean_rule.LINE_MAX_MM`; no new constant.

Measured, tree `950855bf` + this PR, rembg venv present, OFF byte-identical to the
stored capture on all 8 rows run both ways:

| row | stitches OFF to ON | trims | colour blocks |
|---|---|---|---|
| `C_low_poly` | 10,866 to 11,205 (+339) | 91 to 85 | 6 to 8 |
| `C_isometric_icon` | 11,487 to 11,380 (-107) | 28 to 29 | 8 to 9 |
| `C_comic_halftone` | 57,207 to 57,043 (-164) | 202 to 198 | 7 to 7 |
| `C_halftone_dots` | 37,849 to 37,838 (-11) | 122 to 121 | 6 to 6 |
| `C_chalkboard_lettering` | 27,583 to 27,581 (-2) | 110 to 109 | 6 to 6 |
| the other 16 rows | identical | identical | identical |

Catches, plainly:
- **+2 colour blocks on low_poly** (6 to 8, still 6 distinct spools). Black
  (0020) now sews as layers 5 and 7 with Battleship Gray (layer 6) between them
  where Blackberry sewed as one block. I did not isolate why layer 6 ends on
  Battleship; it is a stop per layer, not a new colour. A fix would merge
  same-spool layers after the colour cap (not built).
- **The ink changes spool**, Blackberry 1776 to Black 0020 (12.2 dE00, a
  sewing-room call, not visible in the render): the thread that stage 2 chose
  from the cluster, not the one the re-check preferred.
- It fixes only the re-check. A drawn line that stage 2 itself splits into two
  clusters, or that the colour cap merges unevenly, still breaks.
- Gate 3: this is a new flag, default OFF; flipping it ON is Kent's.

**B. One thread per connected drawn line (chain level, not built).** After the
cap, group connected thin-line regions (ends within about one column) into
chains and give each chain one thread, chosen from the art's core pixels (the
darkest per cross-section), but only when the chain's art colour is uniform;
leave it per patch when the art line really changes colour (neon sign, crest).
Fixes A's two gaps (stage-2 splits, +2 blocks via one layer per chain). Cost:
a chain graph over regions and layers, a uniformity test on the art; trims fall
(one tie-off pair fewer per handover; low_poly has 2 ends); risk: a coloured
line forced to one colour, so the uniformity test has to be right. Moderate.

**C. Border per colour patch, ends tucked under the later colour (the pro's habit).**
Rings and the cap already follow the patch beside them (follow-adjacent, seam
ownership). What is missing is the join: make each arc end overlap its
neighbour by at least half a column and begin or end under the colour that sews
on top. Our ring ends of different colours meet on 1 row of 21, so the payoff
on this corpus is small; do it only if a design with real per-patch borders
(Instagram, a heraldic crest) is judged on the join.

**D. Border fabric edges only.** Already on (`border_by_size_fabric_edges`).

**Pick: A now (done), eye-check it on low_poly and isometric, then B if Kent
likes the outline.** A is one early return and one config line, off by default;
B is the right fix for the whole class but needs Kent's eye on A first, and the
uniformity test needs a corpus of drawn-line art that we do not have beyond the
21. C is a later, join-only change.

## What I did not run or verify

- No sew-out. Whether a black outline lying across a Black/Blackberry change
  reads the same on fabric is untested; the 12.2 dE00 is a chart number.
- The full digitizer suite. Targeted only: 82 tests (the new file, the
  frozen-pin test, the revalidate, resnap, rehome and bean-rule files), EXIT 0.
- The flag's effect on the pro pairs and on the flat-lane golden: the 21
  Commons rows only. CI's three expected goldens were not exercised.
- The silhouette-handover counts (our rows) are a crude instrument; the pro
  counts come from `border_pro` v3's detector and a 1.5 mm join radius. Neither
  was cross-checked against a second tool.
- Why layer 6 ends on Battleship with the flag ON (the +2 blocks) was not
  isolated.
- No Studio click-through: the flag is not exposed in the UI.
