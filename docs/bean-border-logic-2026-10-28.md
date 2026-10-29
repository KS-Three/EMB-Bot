# Bean, border and outline: when to use each, and where ours breaks it (2026-10-28)

Kent's question: when do professionals use a bean stitch or a border/outline, and when not?
Turn it into logic, compare it to the pro files, and explain the Instagram icon. When we
auto-digitize the icon, rings go round the **colours** but not round the **primary shape**.
There is no satin border round the whole logo.

Sources:
- Web: [`bean-outline-practice-research-2026-10-28.md`](bean-outline-practice-research-2026-10-28.md).
  Vendor manuals (Wilcom, Ink/Stitch, Embrilliance, Embird, Melco) and named practitioners
  (Campbell, Bruce, Goodall, Freeman). Every claim there is linked.
- Pro files: censuses already in the repo, re-read here, not re-run:
  - [`bean-census-reference-2026-10-27.md`](bean-census-reference-2026-10-27.md): 17 jobs.
  - [`border-census-2026-10-23.md`](border-census-2026-10-23.md): 805 shapes.
  - `outline_census` (memory `border-from-outline-2026-10-24`, kappa 0.76 → 0.85 with the
    line-art guard, n 588).
  - DOCTRINE 2026-09-11 on silhouette cover.
- Ours: the Instagram icon digitized on main `d8769ab6` four ways, below. **No pro file of
  the Instagram icon exists.** The comparison to the pro is by rule, from the census, not
  file to file.

## The logic

Decide per **element**, then per **edge**. The first rule that matches wins.

| # | Element / edge | Do | Don't | Evidence | Main today |
|---|---|---|---|---|---|
| 1 | **Drawn LINE**: a stroke of another colour, smallest dimension ≤ 1.2 mm | Run if very fine; **bean** for a line that must read heavier; satin for a free bar ≥ ~0.85 mm | Fill or ring it | Pro: all 17 of his bean runs in 17 jobs (780 mm, 2 passes, 1.31 mm pitch) are drawn lines. Web: bean = bold or hand-look line; run under ~0.8 mm (Campbell) | `bean_only_lines` ON, `fine_bars_satin` ON ✔ |
| 2 | **Letter** | Satin; raise text under ~3.2 mm to ~4 mm | Bean, at any size | Pro beans 1 of 251 small letters. Web: text minimum ~4 mm / ¼ in | `bean_only_lines` ON, small-text floor ✔ |
| 3 | **Small solid**, under ~4 mm | One satin blob or a bare fill | Ring it, bean or satin | Pro rings 0.7% of shapes under 2 mm, ~7% at 2–4 mm; 0 of 81 small solids beaned | `compact_solids_satin` / `small_solids_satin` OFF, bean cap neutered ✔ |
| 4 | **Body whose outline the ART draws** | One satin loop at the art outline's own thickness (1.5–2.5 mm); body filled under it | Add a second generated ring | Pro: border follows the art outline, kappa 0.76 → 0.85. Web: Wilcom says use the art's outlines *or* generate them, never both | `border_from_outline` ON + line-art guard ✔ |
| 5 | **Edge between two colours of ONE object**: gradient bands, tonal steps, butting fills | Overlap + pull comp; blend the steps | **Ring each band** | Web: butting fills get overlap, not an outline (Hatch, Wilcom, Ink/Stitch); gradients are blended light-density layers and no source outlines the steps (Bruce). Pro: big plain fills bordered on some jobs, bare on others | **Broken: `border_by_size` rings every region ≥ 6 mm on its own** ✘ → `border_by_size_fabric_edges` (built OFF, below) |
| 6 | **Outer silhouette of a multi-colour object** | If anything, ONE satin ring round the whole ("Common" outline, Wilcom) | A bean ring; a ring per colour | Pro beans 0 of 231 bare body edges; he borders at least 19–26% of fill edge with satin (DOCTRINE 2026-09-11, a lower bound; his silhouette cover cannot be known). Web: outlines are optional and only for crispness (Embrilliance) | `edge_cap` bean → sews nothing under `bean_only_lines`; satin style exists, not default — open edge ✘ |
| 7 | **Large body ≥ 6 mm, no art outline, against fabric** | Fill + satin border ~2.1 mm is the pro's habit on some jobs | Wide whole satin | Pro rings 49% at 6 mm+, a coin flip per design (MFab, Drone, Fremont patch bordered; Bridge, Gaulke bare) | `border_by_size` ON ✔ (this edge is fine; rule 5's edges are not) |

**Never bean:** a letter, a solid, or the bare edge of a filled body. **Never ring:** a
seam between colours of one object, a shape under ~4 mm, or an edge the art already
outlines.

Ordering, from the web note: an outline sews right after its own object (Wilcom, Freeman,
Melco). No source says "all outlines last". Travel goes under later work. This is not
changed here.

## The Instagram icon on main

`instagram_original.png` at 80 mm, left chest, through the Studio's request
(`tools/pro_pair.digitize`). It classifies gradient. The renders stay in the session
scratchpad and are not committed: the art is trademarked (memory
`instagram-gradient-lane-edges-2026-09-30`).

| arm | stitches | trims | colour blocks | border thread | what you see |
|---|---|---|---|---|---|
| main today | 32,023 | 24 | 11 | 9,316 mm (9 runs) | a satin ring round **each colour band** (purple, pink, orange, yellow), the circle and the dot; the outer edge is ringed only where a band touches it |
| `bean_only_lines=false` (before 10-27) | 32,023 | 24 | 11 | same | identical; `EDGE_CAP_EMPTY`: the bean cap had nothing left to cover |
| `border_by_size=false` | 27,488 | 24 | 10 | 0 | no rings; glyph clean; outer edge bare (tatami row ends) |
| `border_by_size=false`, `edge_cap="satin"` | 29,014 | 30 | 15 | 2,525 mm (cap) | **one satin ring round the whole logo**, each stretch in the colour of the band beside it; no band rings |

Findings:

- **The rings Kent saw are satin, not bean, and they come from `border_by_size`.** That rule
  (ON since 2026-10-23) reads each region alone. Every gradient band is a body ≥ 6 mm (the
  bordered ones read 8.7–18.6 mm smallest dimension), so each gets a fill + 2.1 mm border on
  its whole perimeter, seams included. That breaks rule 5. Cost: +4,535 stitches (+16.5%)
  over no rings.
- **The bean flip of 10-27 is not involved.** Before it, the bean edge cap found nothing
  open to cover, because the band rings already covered the edge.
- **The existing "one gradient" hook does not catch it.** `region_rides_design_ramp`
  already keeps sweep bands off the satin rung. On this file the design-ramp fit refuses:
  0 of the 4,527 border stitches sit on a ramp rider. A ramp-based fix would miss
  Instagram.
- **A lane-wide switch is wrong too.** 8 of the 14 pro jobs route gradient (memory
  `lane-census-2026-10-25`). The border census's 6 mm+ numbers come largely from those, so
  "no `border_by_size` on gradient" would undo the pro match there.
- **Arm 4 is Kent's description,** at +1,526 stitches and +6 trims over no rings. It has a
  defect: one stray white/orange cap stretch runs across the yellow band at the bottom.
  That would need a fix before shipping.

## Built: `border_by_size_fabric_edges` (OFF)

Kent picked "build OFF + measure" on 2026-10-28. **A `border_by_size` ring now skips every
stretch of its edge that it shares with another sewn region**, earlier or later in the
sequence. It uses the same seam band and the same threshold (twice the column width) that
seam ownership (`_owned_by_later`, ruling 2026-09-09) already uses. What remains is the
stretch facing bare fabric. Edges against colour fall to the ordinary seam (overlap, pull
comp), the way the web sources handle butting fills. Where the art outlines a body against
colour, `border_from_outline` still holds it, and this flag does not read it. The flag only
changes what a `border_by_size` ring omits. No width, density or length moves.

| arm | stitches | trims | border thread | what you see |
|---|---|---|---|---|
| Instagram, main (OFF) | 32,023 | 24 | 9,316 mm, 9 runs | ring per colour band |
| Instagram, ON | **28,972** (−9.5%) | 23 | 2,992 mm, 3 runs | no band rings; one satin ring on the outer edge where the purple and yellow bands meet fabric |

**Against the pro (gate 4).** I re-ran `border_census` on its 16 paired designs, OFF and
ON (`tools/border_census.py run --extra '{"border_by_size_fabric_edges": true}'`, then the
new `kappa` subcommand):

| arm | shapes | ours ring | pro ring | raw | kappa | kappa < 4 mm | 4–6 mm | ≥ 6 mm |
|---|---|---|---|---|---|---|---|---|
| OFF | 692 | 28 | 28 | 0.977 | 0.730 | 0.661 (n 620) | 0.609 (n 36) | 0.717 (n 36) |
| ON | 692 | 28 | 28 | 0.977 | 0.730 | 0.661 | 0.609 | 0.717 |

**All 16 ON DSTs are byte-identical to OFF.** On today's main, `border_by_size` rings only 3
shapes in the whole paired corpus (Gaulke hat and LC, Tires). `border_from_outline` and the
lettering lanes hold the rest, and none of those 3 shares a seam long enough to drop. So
the flag cannot move the pro match. It acts where big fills of different colours butt each
other with no art outline between them. Instagram is one such design. No paired design is.

**What this does not show.** It says nothing about the population ON changes: gradient and
tonal logos with no pro file. That population is the logo-census and photo-corpus renders,
which nobody has read with this flag ON yet. The remaining gaps on Instagram ON:

- **Short outer stretches stay bare.** Where a band under 6 mm smallest dimension owns the
  outer edge (left pink, bottom-right coral), nothing rings it. `border_by_size` does not read
  bands that small, and the bean edge cap sews nothing under `bean_only_lines`.
- **`edge_cap="satin"` would close those stretches** (arm 4 above). It has a stray cap
  stretch across the yellow band that would need fixing first.
- **Ring colour is open.** The ring could follow the adjacent band (today's
  `edge_cap_follow_adjacent`) or be one cone. That is a look call for Kent.

Gates: 1 does not apply (layout only, no physical constant). 3: the flag is built OFF, and
its instrument is `border_census` plus renders. 4: kappa quoted above.

## Instrument notes

- My first "where does the border lie" split (silhouette vs inner seam) is **not quoted**.
  It read 3,441/156 mm one way and 0/3,597 the other after a fix, against renders that
  plainly show both. The plan's frame and the regions' frame probably differ. Trust the
  renders and the stitch deltas.
- `bean_census.bean_segments` flags ~50 mm of "bean" inside Instagram's fills. Those are
  row turns and fill retraces, not beans; the census excludes fills for this reason.
- Scripts: session scratchpad `insta_beans.py` / `insta_ramp.py` (not committed). The arms
  can be reproduced through `tools.pro_pair.digitize(..., extra)`.
- `border_census`'s shape-level kappa is **blind to this flag by construction**. A shape that
  keeps any ring still reads "ringed". Byte-identity of the DSTs is the stronger statement
  here. A stretch-level census (which seams the pro rings) does not exist.
