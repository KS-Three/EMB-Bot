# Ink/Stitch teardown — what's portable to EMB-Bot

**Date:** 2026-08-10 · **Scope:** full capability survey of Ink/Stitch (Inkscape
embroidery extension) against EMB-Bot's current state, for concept-level
gap-finding, not code reuse (see §0 licensing).

**Version verified:** repo tag **v3.3.0** (dated 2026-07-31, the newest
non-dev-build tag as of this research) — source: [github.com/inkstitch/inkstitch/tags](https://github.com/inkstitch/inkstitch/tags).
All file citations below are against `main` at the commit serving that tag
unless noted; Ink/Stitch moves fast (multiple `dev-build-*` tags per week), so
treat exact line numbers as approximate and file-level claims as the durable
part.

**Method:** every capability claim below was checked against the live GitHub
source (`raw.githubusercontent.com/inkstitch/inkstitch/main/...`) or the live
docs site (`inkstitch.org/docs/...`), not against training-data memory of
Ink/Stitch. Fetches were run through a summarizing tool rather than reading
every file byte-for-byte in this session, so **[V]** below means "verified via
direct source/doc fetch this session," not "read in full." Where a claim
could not be verified (docs page 404, ambiguous doc wording), it's marked
**[U]** and flagged explicitly rather than asserted. Two corrections to the
task brief's assumed sources, found during research, are called out inline
(§0 fonts repo name, §8 pyembroidery vs. pystitch).

Cross-reference note: EMB-Bot's own `docs/fill-techniques-2026-08-01.md` and
`docs/lettering-mastery-2026-08-01.md` already cite Ink/Stitch extensively
(concept-level, not code) — this document verifies those citations against
live source and fills the areas neither doc covered (DST/pyembroidery, params
architecture, palettes, commands, preflight, print worksheet, cutwork).

---

## 0. Licensing — read this before any "should we port it" decision

**Ink/Stitch's own code is GPL-3.0-or-later** — confirmed via the repo's
license footer, [github.com/inkstitch/inkstitch](https://github.com/inkstitch/inkstitch).
GPL-3.0 is a strong copyleft license. Concretely, for EMB-Bot:

- **Copying or adapting Ink/Stitch Python source into EMB-Bot's codebase is
  off-limits** unless the receiving EMB-Bot module (and arguably the whole
  distribution, depending on linking/derivative-work analysis) becomes
  GPL-3.0-compatible. EMB-Bot is not GPL today and nothing in the docs
  reviewed suggests that's on the table — so **no literal code, no
  near-verbatim translation, no "port the function and rename the
  variables."**
- **What IS fair game, independent of the code license:** the underlying
  geometric/algorithmic *concepts* (level-set offsetting for contour fill,
  Eulerian-path fill routing, phase/inverse-CDF row placement, etc.),
  published parameter names and taxonomies, file-format knowledge (DST byte
  layout, font.json schema), and anything Ink/Stitch's own docs state as
  fact about embroidery physics or machine formats. None of that is
  copyrightable. A clean-room reimplementation *from the concept*, written
  without the Ink/Stitch source open in the same window, is legally clean.
  This is exactly the posture EMB-Bot's own `fill-techniques-2026-08-01.md`
  and `lettering-mastery-2026-08-01.md` already take ("Ink/Stitch's
  `cross_stitch.py` (GPL-3.0 — method only, no code)") — this document
  extends that same posture to the areas those two didn't cover.
- **The `pystitch` format library is a different story — MIT-licensed**, see
  §8. Depending on it as a runtime library (the way Ink/Stitch itself does)
  carries none of GPL's copyleft obligations. This is the one place in this
  report where literal *use* (not copying) of Ink/Stitch's own dependency is
  actually available to EMB-Bot.
- **Fonts are licensed per-font, separately from the code**, and mostly
  **not** GPL — see §6. This directly matters given EMB-Bot's own
  font-license compliance gate (`docs/font-license-audit-2026-07-31.md`).

**Correction to the task brief:** the fonts repo is
**`github.com/inkstitch/embroidery-fonts`**, not `inkstitch-fonts` — verified
via the main repo's `.gitmodules` (`path = fonts`, `url =
https://github.com/inkstitch/embroidery-fonts`). EMB-Bot's own
`font-license-audit-2026-07-31.md` already cites this correct URL
consistently (e.g. `raw.githubusercontent.com/inkstitch/embroidery-fonts/main/src/<key>/LICENSE`),
so this is a correction to the research brief, not to any EMB-Bot doc.

---

## 1. Fill algorithms

Ink/Stitch's fill implementations live in `lib/stitches/`. Directory listing
verified via GitHub API against tag `v3.3.0`
([api.github.com/repos/inkstitch/inkstitch/contents/lib/stitches](https://api.github.com/repos/inkstitch/inkstitch/contents/lib/stitches?ref=v3.3.0)):
`tatami_fill.py`, `fill.py` (legacy), `circular_fill.py`, `contour_fill.py`,
`meander_fill.py`, `guided_fill.py`, `linear_gradient_fill.py`,
`tartan_fill.py`, `cross_stitch.py`, `cross_stitch_half.py`,
`ripple_stitch.py`, `running_stitch.py`, `auto_run.py`, `auto_satin.py`.
**Nine distinct fill algorithms, not the ~4 the task brief anticipated** —
`circular_fill` and `contour_fill` are separate files/features (both cited
individually below), and cross-stitch is effectively a tenth fill-family
member.

### 1.1 Tatami fill — `lib/stitches/tatami_fill.py` [V]

Eulerian-path-based, explicitly cited in the source: "The idea comes from
this paper: `sciencedirect.com/science/article/pii/S0925772100000158`" — a
different algorithmic lineage than EMB-Bot's own boustrophedon-row generator,
though the end result (parallel staggered rows) looks similar. Signature
(verified): `tatami_fill(shape, angle, row_spacing, end_row_spacing,
max_stitch_length, running_stitch_length, running_stitch_tolerance,
staggers, skip_last, starting_point, ending_point=None, underpath=True,
gap_fill_rows=0, enable_random_stitch_length=False, random_sigma=0.0,
random_seed="", pull_compensation_px=(0,0), pull_compensation_percent=(0,0))`.
Underpathing, when enabled, builds a travel graph from **three auxiliary
gratings at +45°, −45°, and +90° from the fill angle**, weighting boundary
edges higher to discourage travel along the outline — a materially different
(and more elaborate) travel-routing approach than EMB-Bot's edge-walk
`travel_path`. `gap_fill_rows` repeats a row offset by spacing when the
back-and-forth pattern detects a discontinuity that would distort fabric —
EMB-Bot has no equivalent instrumented gap-fill mechanism.

**Row-spacing convention — the specific question the task asked to settle.**
Verified directly in `lib/stitches/fill.py`'s `intersect_region_with_grating()`
(the function `tatami_fill.py` calls for row generation): the row-advance
loop is

```python
current_row_y += row_spacing + (end_row_spacing - row_spacing) * ((current_row_y - start) / height)
# (or, without a gradient:) current_row_y += row_spacing
```

**Row *i* sits at exactly `i * row_spacing` from row 0. There is no factor of
2 anywhere in this loop.** `row_spacing` is the distance between
*consecutive stitched rows in sew order* — i.e. between a row and the very
next row the needle sews, regardless of that row's direction — the same
convention EMB-Bot's `stage6_fill.py:80` already uses (`y = miny +
row_mm*(i+0.5)`, confirmed against `docs/fill-techniques-2026-08-01.md`'s own
citation of that line). **This directly corroborates the conclusion EMB-Bot's
own `docs/law19-fill-spacing-2026-08-02.md` §1 reached independently from
corpus measurement** ("the two definitions are the same number in this
corpus... there is no factor of 2 hiding between them") for genuine 2-D
tatami fills, and weighs against the alternative "spacing means between
same-direction rows" theory that document was written to test. It does
**not** resolve §5/§8 of that same doc (whether the true professional density
target is 0.40 mm or ~0.19 mm) — Ink/Stitch's docs page for fill stitch
(`inkstitch.org/docs/stitches/fill-stitch/`) [V, fetched] defines Row Spacing
only as "Distance between rows of stitches" with no numeric default stated
on the page and no disambiguation of the same-direction question — so this
finding settles the *definition* question, not the *magnitude* question,
which EMB-Bot's own doc already correctly flags as sew-out-gated.

### 1.2 Legacy fill — `lib/stitches/fill.py` [V]

`legacy_fill(shape, angle, row_spacing, end_row_spacing, max_stitch_length,
flip, reverse, staggers, skip_last)` — a simpler grating-intersection fill
kept for backward compatibility, documented stagger pattern: "first row is
offset 0%, second 25%, third 50%" (a 4-stagger, matching EMB-Bot's own
existing 4-element stagger table per `fill-techniques-2026-08-01.md`'s
Tier-A golden-test proposal). Low value to port — EMB-Bot's tatami already
covers this ground.

### 1.3 Contour fill — `lib/stitches/contour_fill.py` [V]

This is the file EMB-Bot's own `fill-techniques-2026-08-01.md` §1 already
analyzed in depth (citing `inkstitch.org/docs/stitches/contour-fill/`) and
planned a from-scratch `stage6_contour.py` against. Verified this session
against live source: `offset_polygon(polygon, offset, join_style, clockwise)`
builds nested isocontours via Shapely's `offset_curve()`; a `Tree`
(networkx `DiGraph` subclass) tracks parent/child containment with holes as
a distinct node type; three strategies — **inner-to-outer** (default,
`_find_path_inner_to_outer()`, recurses into children before siblings, the
only strategy Ink/Stitch's own docs [V] say "handles bottlenecks" because it
has no single-child topology requirement), **single spiral** and **double
spiral** (`_get_spiral_rings()` + `_interpolate_linear_rings()`, both require
"each parent has only one child" per an explicit code comment — confirming
EMB-Bot's plan to build inner-to-outer first was the right call). Entry
points use soft/hard buffer thresholds at **1.5× and 2.05× the offset
spacing** — EMB-Bot's own plan independently arrived at the same two
constants (`CONTOUR_ENTRY_SOFT = 1.5` / `_HARD = 2.05`), which is worth
flagging as a coincidence to double check isn't accidental over-anchoring
from having read Ink/Stitch's docs page (the plan doc doesn't cite this
specific number's source). **Confirmed limitation, matching EMB-Bot's own
citation:** the contour ring-generation code contains no underlay logic at
all — Ink/Stitch's docs page states "Underlay in Contour Fill doesn't follow
the contour, but uses the fill angle" [V], meaning underlay is generated by
the ordinary angle-based tatami underlay mechanism layered underneath,
not by this file. EMB-Bot's plan to build contour-following underlay
(`stage6_contour.py` §1.2: "Ink/Stitch's documented limitation is that
contour underlay doesn't follow contours... beating that is one function
call and a visible differentiator") is a genuine, verified point of
differentiation, not an assumed one.

**Status: EMB-Bot has NOT built this yet** (per `MASTER_SCOPE.md`'s current
state — only tatami + concentric/contour fill "newly-landed" is mentioned in
context, but the detailed `stage6_contour.py` design in `fill-techniques
-2026-08-01.md` is a plan, not confirmed shipped as of this research pass).
**Concept-level, already well-scoped by EMB-Bot's own prior research — no
new concept to add here beyond confirming the plan's citations check out.**

### 1.4 Circular fill — `lib/stitches/circular_fill.py` [V] — genuinely new to EMB-Bot

Distinct from contour fill: generates concentric **circles** (not
shape-conforming offset rings) radiating from a center point, computing ring
count from the Hausdorff distance to the shape boundary, then connects them
via a **Fermat (double) spiral** specifically "so we don't get stuck in the
middle of the spiral" (verbatim code comment). The spiral is intersected
with the actual shape boundary; non-circular results get segmented and run
through the standard running-stitch normalizer. This produces radial,
target/bullseye-style texture — visually and structurally different from
contour fill's shape-hugging rings. **EMB-Bot has no equivalent of either
the circular target-pattern OR the Fermat-spiral center-crossing solution**
(EMB-Bot's own contour-fill plan explicitly defers Fermat/CFS spirals: "Do
not build the Voronoi route... Fermat/CFS... does not gate v1"). Low-to-medium
priority — a decorative/novelty fill more than a production workhorse, but
cheap once contour fill's ring machinery exists, since it shares the
same-family geometry.

### 1.5 Meander / stipple fill — `lib/stitches/meander_fill.py` [V] — EMB-Bot has zero equivalent

Confirmed: EMB-Bot's stated gap list is accurate — no meander/stipple fill
exists anywhere in the codebase per the docs reviewed. Ink/Stitch's approach
is **graph-based, not a random walk**: a tile pattern is converted to a graph
fitted to the shape (`fill.meander_scale`, `fill.meander_angle` control the
tile), then `generate_meander_path(graph, start, end, rng)` builds an initial
shortest path and **iteratively replaces edges with longer detour paths**
(`nx.all_simple_edge_paths(subgraph, edge[0], edge[1], 7)`, max depth 7) to
"meander" through more of the shape while a `graph_nodes` set of unvisited
vertices prevents self-crossing by construction (replacement subgraphs only
contain unvisited nodes). Post-processing chains: smooth → optional
perpendicular zigzag offset (`zigzag_spacing`, `offset1 = stroke_width / 2`)
→ clip to boundary → uniform stitch spacing → bean stitch → repeat-with-
reversal. **This is a real, structurally different fill family** (organic
stipple texture vs. EMB-Bot's rows/rings) and the graph-replacement approach
to self-avoidance is a genuinely reusable *idea* (not code) — a clean-room
version would need its own tiling-to-graph construction, but "grow a path by
replacing edges with longer detours through unvisited nodes" is a clean,
implementable concept independent of Ink/Stitch's specific code.

### 1.6 Guided fill — `lib/stitches/guided_fill.py` [V] — EMB-Bot has zero equivalent

Entry point `guided_fill(fill, shape, guideline, anchor_line,
starting_point, ending_point)`. Three distinct strategies selectable via
`fill.guided_fill_strategy` (0/1/2): **Copy** (translate the guide line
parallel to itself), **Offset** (Shapely `offset_curve()` parallel-curve
generation), **Buffer** (bidirectional `buffer()` to reach both sides of the
guide at once). This maps closely onto EMB-Bot's own planned "curved/flow-
following fill" (`fill-techniques-2026-08-01.md` §4, Laws 39–44,
`stage6_curved.py`) — but EMB-Bot's plan is architecturally different and,
on its own analysis, *more rigorous*: EMB-Bot explicitly chose a
**parametric-map (Wilcom UT transform)** approach over "normal-offset level
sets" specifically because normal-offset "destroys" the penetration lattice
and "fails at cusps/swallowtails" — and Ink/Stitch's Offset/Buffer strategies
are exactly the normal-offset family EMB-Bot's own research rejected for
that reason. **This is a case where EMB-Bot's own prior research already
out-designed Ink/Stitch's shipped implementation on a documented technical
argument** — worth noting as a confidence point for that plan, not a reason
to copy Ink/Stitch's simpler approach. One parameter worth taking as a
concept regardless of implementation: `guided_fill_strategy` as a named,
user-facing choice among approaches (Copy/Offset/Buffer) rather than one
fixed algorithm — EMB-Bot's plan currently commits to one architecture
(Florentine/Liquid), and exposing a strategy switch is cheap UI-level
flexibility worth considering once the core map exists.

### 1.7 Linear gradient fill — `lib/stitches/linear_gradient_fill.py` [V]

Directly comparable to EMB-Bot's planned crossfade fill
(`fill-techniques-2026-08-01.md` §3). Confirmed: Ink/Stitch generates **one**
row set (bounding box rotated to the gradient angle) then assigns each row a
color by mapping gradient stop offsets onto row indices
(`round((gradient_line.length * offset) / fill.row_spacing)`) and subdividing
each color's row-run via a **square-root-based subdivision** that mirrors the
first half onto the second half for smoother blending — i.e., **no explicit
per-pixel interpolation between colors; blending is achieved entirely by row
alternation/banding**, same "physical row alternation" approach EMB-Bot's own
plan already identified for its Part 3 gradient (Wilcom/Hatch "Colour
Blending" = which rows belong to which color varies, spacing does not).
EMB-Bot's plan already goes further than what's verified here: it derives a
formal **largest-remainder / highest-averages scheduler** (`acc += alpha(t);
c = argmax(acc); acc[c] -= 1.0`) with a proven `|count_c(n) − Σα_c| < 1`
guarantee, which is more rigorous than Ink/Stitch's square-root mirrored
subdivision (no error-bound guarantee stated or apparent in the verified
approach). **Confirms EMB-Bot's planned approach is a genuine improvement on
the shipped reference implementation, not a re-derivation of it.**

### 1.8 Tartan / plaid fill — `lib/stitches/tartan_fill.py` [V] — EMB-Bot has zero equivalent

Confirmed real and distinct: generates true two-axis (warp/weft) striped
crossing patterns from a `tartan_settings` palette definition
(`get_tartan_stripes()`, per-axis widths via `get_palette_width()`), splits
lines into warp/weft via `_split_warp_weft()`, and computes color at each
crossing by intersecting generated lines against per-stripe color-band
polygons (`_get_tartan_color_segments()`). Ships a **herringbone variant**
(`_generate_herringbone_lines()`, alternating diagonal blocks) alongside the
standard 45°-default crossing pattern. Not on EMB-Bot's roadmap docs
reviewed at all — genuinely net-new capability, matches the task brief's
"EMB-Bot does NOT have: tartan/plaid fill" note. Niche demand (plaid/tartan
is a specific, recognizable aesthetic, not a general-purpose technique) —
**medium build cost, narrow addressable use case** (kilts, Scottish-themed
merch, flannel-look graphics) — rank accordingly in §12.

### 1.9 Cross-stitch / motif tiling — `lib/stitches/cross_stitch.py` [V]

This is the file EMB-Bot's own `fill-techniques-2026-08-01.md` §2 already
cites by name as the basis for its planned Tier-B motif fill ("taken from
Ink/Stitch's `cross_stitch.py` (GPL-3.0 — method only, no code)"). Verified:
a `CrossGeometries` model per cross-stitch unit (center + corner anchor
points, categorized "good"/"bad" by stitch-order constraints), a NetworkX
graph connecting centers to corners, `_build_connect_subgraphs()` extracting
connected components, and Eulerian-cycle construction that walks
`crosses_by_good_point`/`crosses_by_bad_point` lookups to splice adjacent
crosses at shared anchors without an explicit "connector" stitch —
confirms EMB-Bot's own description of the anchor-based routing concept is
accurate to the source. EMB-Bot's plan already improves on one specific
point it flags: Ink/Stitch matches anchors "by exact float-tuple equality,"
which EMB-Bot's plan replaces with integer lattice keys as "strictly more
robust" — verified as an accurate characterization of a real fragility in
the reference approach, not a strawman.

### 1.10 Ripple stitch — `lib/stitches/ripple_stitch.py` [V] — EMB-Bot has zero equivalent

Not covered by any EMB-Bot doc reviewed. Docstring, quoted verbatim: "Ripple
stitch is allowed to cross itself and doesn't care about an equal distance
of lines. It is meant to be used with light (not dense) stitching." Four
guide modes: **linear** (helper lines radiate from every outline point
toward one target point), **circular** (concentric helper lines converging
inward, for closed shapes), **guide-line** (affine-transformed copies of the
outline stepped along a path), and **satin-column** (interpolates between
the paired rails of an existing satin column). Parameters:
`line_count`/`min_line_dist` (density), `exponent`/`flip_exponent`
(non-linear step distribution via `_get_steps()`), `repeats` (forward/back
passes), `grid_size` (perpendicular secondary grid). This is a genuinely
distinct, low-density decorative/textural stitch type — closer to a
"light coverage flourish" than a structural fill, explicitly *designed* to
tolerate self-crossing (the opposite invariant from every fill EMB-Bot has
built, all of which treat self-crossing/overlap as a defect to guard
against). **Concept-level: worth having as a named technique**, but it's a
genuinely different design philosophy (accept crossing, prioritize organic
line flow) rather than a variant of anything EMB-Bot's engine already does —
would need its own guard-relaxation pass, not a drop-in.

---

## 2. Satin column features

Verified against `lib/elements/satin_column.py` [V] (single-file
implementation; EMB-Bot's own memory notes its satin subsystem is
medial-axis based, a different construction than Ink/Stitch's explicit
rails-plus-rungs input model — the comparison below is capability-level, not
architectural).

**Rails/rungs model.** A satin column is "two long paths (rails) plus
optional cross-connecting paths (rungs)." For a plain two-rail satin with no
authored rungs, `_synthesize_rungs()` derives implied rungs from node
endpoints — i.e. rungs are optional, not mandatory, which is a real
authoring-convenience feature (a user can draw just two parallel strokes and
get a working satin column without manually placing crossbars). EMB-Bot's
medial-axis approach sidesteps rails/rungs authoring entirely by deriving
both from arbitrary closed-polygon skeletonization (confirmed by
`MASTER_SCOPE.md`'s 2026-08-07 entry: "EMB-Bot's satin/fill machinery
already derives rails/caps from ANY closed polygon via medial-axis
skeletonization") — a genuinely different and, for EMB-Bot's raster-in
digitizing use case, more appropriate input model than Ink/Stitch's
vector-authoring-first rails/rungs. **Not a gap; a legitimately different
architecture for a legitimately different input pipeline.**

**Satin method variants — `satin_method` property**, four values verified:
`satin_column` (`do_satin()`, the standard zigzag), **`e_stitch`**
(`do_e_stitch()`, "E"-shaped left-right-left pattern with split-stitch
subdivision of long segments), **`s_stitch`** (`do_s_stitch()`, alternating
"S"-shaped direction every cycle via `split_segment_even_dist()`), and
`zigzag` (`do_zigzag()`, computes point pairs at double density then
alternates rail selection for a consistent rhythm — distinct from plain
`satin_column`'s direct rail-to-rail crossing). **EMB-Bot confirmed to have
none of e-stitch or s-stitch** (matches task brief) — these are genuinely
different surface textures for satin (E-stitch in particular is a common
choice for wide, low-sheen coverage where full zigzag satin would be too
glossy or too dense) and are cheap to add once EMB-Bot's medial-axis rail
extraction exists, since they're alternate *point-selection* strategies over
the same two-rail geometry, not alternate geometry.

**Satin underlay variants**, three confirmed: **center-walk**
(`_get_center_line_stitches()`, `center_walk_underlay_repeats` default 2,
odd counts reverse direction), **contour** (`do_contour_underlay()`, "runs up
one rail, crosses between, returns down opposite rail," with
`contour_underlay_inset_px`/`_percent` controlling edge inset), and
**zigzag** (`do_zigzag_underlay()`, lower-density diagonal pattern,
`zigzag_underlay_spacing_mm` default 3 mm). This exactly matches the three
Ink/Stitch underlay defaults EMB-Bot's own `lettering-mastery-2026-08-01.md`
Law 50 already cites for the lettering underlay ladder ("Ink/Stitch shipping
defaults are the usable public numbers: center-walk 2 repeats at 3 mm...
contour 3 mm length, 0.4 mm inset each side; zigzag 3 mm spacing") — verified
consistent with live source, not just the docs page that doc originally
cited. **EMB-Bot's satin subsystem needs to be checked directly against
these three (task's own framing) — this document did not find independent
evidence either way on whether EMB-Bot's non-lettering satin underlay
already implements center-walk/contour/zigzag as distinct styles or a single
generic style; flagging as an open verification item, not asserting a gap.**

**Pull compensation.** Two properties, `pull_compensation_px` and
`pull_compensation_percent`, both supporting **asymmetric two-value input**
("two space-separated numbers for each side") — i.e. Ink/Stitch lets a user
compensate the two rails of a satin column by different amounts. Worth
checking whether EMB-Bot's pull-comp implementation supports asymmetric
per-rail values or only a single symmetric offset; not verified either way
from the docs reviewed.

**Short-stitch handling.** `short_stitch_distance` (default 0.25 mm — exact
match to the value EMB-Bot's `lettering-mastery-2026-08-01.md` Law 53
already cites) triggers `inset_short_stitches_sawtooth()`, using a
`short_stitch_inset` list (default `[0.15]`, i.e. 15%) for progressive
inset on consecutive short stitches — confirmed as a "sawtooth" pattern
specifically to avoid the ridge a uniform inset would create (matches Law
53's citation of Wilcom's "Randomize option to kill the ridge"). **EMB-Bot's
own lettering doc already correctly cited these Ink/Stitch defaults; this
verifies they're accurate against live source, not just a docs page.**

**Cutwork — not part of `satin_column.py`.** Ink/Stitch's cutwork feature is
a separate extension, `lib/extensions/cutwork_segmentation.py` [V] — see
§11.6. Not a satin *variant* at all; it's an unrelated technique for
specialty multi-needle cutting machines. The task brief's grouping of
cutwork under "satin column features" appears to be a miscategorization —
correcting that here.

**Auto-Satin — `lib/stitches/auto_satin.py` [V].** Important finding: **this
file contains no shape-classification heuristic at all.** It assumes every
input element has *already* been typed as a `SatinColumn` or `Stroke` by the
user (via other tools: "Stroke to Satin," "Fill to Satin," etc.) and its job
is purely **routing** — building a graph of ~1mm-discretized segments
(`SatinSegment.break_up(segment_size)`), inserting `JumpStitch`s (with a
`should_trim()` check against how much the jump path overlaps the source
shape) or `RunningStitch` bridges (`is_sequential()` merges paths within
0.5 units) between already-typed elements, and running NetworkX pathfinding
to minimize total jump distance. **There is no Ink/Stitch equivalent to
EMB-Bot's `is_satin_candidate` ribbon-width classifier** — Ink/Stitch is a
vector-authoring tool where the human draws the satin/fill distinction
directly in the SVG; it never has to infer "is this raster region shaped
like a ribbon" the way EMB-Bot's raster-in auto-digitizer must. This is a
genuine, verified architectural difference, not a gap on either side — it
means **there is nothing to compare `is_satin_candidate` against**, and any
future confidence-building on that heuristic needs to come from EMB-Bot's
own corpus work, not from Ink/Stitch. Worth recording so a future session
doesn't waste time looking for an Ink/Stitch classifier that isn't there.

---

## 3. Running / bean / zigzag stroke-to-stitch conversion — `lib/stitches/running_stitch.py` [V]

Three entry points confirmed: `even_running_stitch(points, stitch_length,
tolerance, min_stitch_length=0.1, adapt_to_length=True)` (uniform spacing via
`stitch_curve_evenly()`), `random_running_stitch(points, stitch_length,
tolerance, stitch_length_sigma, random_seed)` (randomized length within a
sigma band, explicitly to avoid moiré patterns on parallel curves), and a
`running_stitch()` dispatcher selecting between them via `is_random`.
Curve-fitting tolerance is enforced via a **Zhao–Saalfeld curve
simplification** with angle-interval checking (`take_stitch()`) — a named,
citable algorithm EMB-Bot's own docs don't reference by name anywhere
reviewed; worth a citation check if EMB-Bot's own running-stitch tolerance
logic wants a formal basis.

**Bean stitch — the exact mechanism the task asked about.** `bean_stitch()`
takes a `repeats` list where each integer is a per-stitch back-and-forth
repeat count, verbatim from source: *"repeats is a list of a repeated
pattern e.g. `[0, 1, 3]` doesn't repeat the first stitch, goes back and
forth on the second stitch, goes 3 times back and forth on the third
stitch."* This is a **per-stitch-position pattern**, not a uniform "sew every
stitch N times" — i.e. bean stitch weight can vary stitch-by-stitch across a
repeating cycle, which is more expressive than a single "pass count" knob.
Worth checking whether EMB-Bot's own bean-stitch handling (if any exists —
not found in the docs reviewed, may be an outright gap) supports anything
beyond a flat repeat count.

**Auto-run routing — `lib/stitches/auto_run.py` [V].** `autorun(elements,
preserve_order=False, break_up=None, starting_point=None, ending_point=None,
trim=False, group=None)` connects a set of open stroke elements into one
continuous path via NetworkX graph pathfinding (`build_graph()` +
`find_path()`), splitting self-intersecting strokes at crossing points
(`LineSegments`, via Shapely `unary_union`), and marking segments as visible
("autorun") vs. buried ("underpath," for backtracking under already-sewn
thread — conceptually close to EMB-Bot's own "needle-down links under
later-sewn shapes" chaining mechanism, though verified only at the
single-element level here, not the whole-design sequencing level EMB-Bot's
chaining laws operate at). **Trim threshold: 0.75 mm** — jumps longer than
this get a trim inserted, per the `trim` parameter and code path. This is a
**flat, single-number distance threshold — even simpler than EMB-Bot's own
current `trim_at_mm` (3.0–4.0 mm) that `docs/chaining-laws-2026-08-01.md`
already found to be wrong against the professional corpus** (which links
roughly two-thirds of transitions regardless of gap distance up to 40 mm,
driven by coverage rather than distance). **This is a useful negative
result: Ink/Stitch's own reference trim/travel logic is not a source of
better practice here — EMB-Bot's own corpus-derived Laws 59–62 (coverage-
routed links, not distance-routed) are already more sophisticated than what
a mature, widely-used tool ships.** Nothing to port from this file for
sequencing; the curve-simplification and per-position bean-repeat pattern
above are the two real takeaways.

---

## 4. Lettering / font system

### 4.1 Font file format — verified via `inkstitch.org/tutorials/font-creation/` [V, docs page] and cross-checked against EMB-Bot's own already-completed audit of the same repo

Each font is a folder containing: **`font.json`** (metadata + kerning:
`horiz_adv_x` per-glyph advance width, `hkern` pair-kerning table),
**glyph-layer SVG file(s)** (`ltr.svg` and optionally `rtl.svg`, one Inkscape
layer per character named `GlyphLayer-[character]`, each requiring a
"baseline" guide), a **15:1 aspect** `preview.png`, and a **`LICENSE`** file
per font. Authoring tools confirmed: FontForge for TTF/OTF → SVG conversion,
then Ink/Stitch's own extensions — `lettering_svg_font_to_layers.py`,
`lettering_generate_json.py`, `lettering_organize_glyphs.py`,
`lettering_force_lock_stitches.py`, `letters_to_font.py` (all confirmed
present in `lib/extensions/` [V, GitHub API directory listing against
`v3.3.0`]). **Glyphs are authored as whichever stitch type the font designer
chooses per glyph** — the docs page states satin columns work best for
1.5–7 mm letters, with no format-level restriction forcing satin-only or
fill-only; a font can freely mix stitch types across its glyph set.

**Comparison to EMB-Bot's pipeline:** Ink/Stitch's format is fundamentally
**vector-SVG-per-glyph**, authored by a human digitizing each letterform
directly (or converting from an existing outline font as a starting point,
then hand-fixing). EMB-Bot's Google-Fonts-to-satin pipeline is **fully
automated outline-to-satin conversion** with no per-glyph hand authoring —
a different point on the automation/quality tradeoff. Ink/Stitch's approach
almost certainly produces better default stitch quality per glyph (a human
placed every rail), at the cost of the ~55-font-and-shrinking library size
this research measured (§4.2) vs. EMB-Bot's 72+-font automated set. Neither
approach is strictly better; they're optimizing different constraints. One
concrete idea worth lifting as a *concept*: Ink/Stitch's kerning-pair table
format (`hkern`, keyed by glyph pair) is architecturally identical to what
EMB-Bot's own `lettering-mastery-2026-08-01.md` already confirms EMB-Bot
ships (up to 97,090 pairs per font) — **no gap here**, already matched.

### 4.2 Font licensing — this repo (`github.com/inkstitch/embroidery-fonts`) is exactly what EMB-Bot's own `font-license-audit-2026-07-31.md` already surveyed in detail

That audit is, in effect, a complete per-font license census of Ink/Stitch's
font library (69 fonts as EMB-Bot found them at audit time) — this research
did not re-derive that census (it would be pure duplication) but did verify
its top-level claims against live source this session: the repo is a
**submodule of the main `inkstitch` GitHub org** (not a personal fork),
confirmed at `github.com/inkstitch/embroidery-fonts`, described as "a
collection of machine embroidery fonts for use with Ink/Stitch," with **no
single repo-wide license** — "please see the LICENSE files" per font,
matching EMB-Bot's audit's finding of a per-font mix (51 OFL-1.1, 12
CC-BY-SA-4.0, 2 CC-BY-SA-2.5, 1 CC-BY-4.0, 2 CC0, 1 SEE-LICENSE-FILE, plus a
70th, `precious`, correctly excluded for being GPL-3.0).

**Direct implication for EMB-Bot's compliance work, restated for this
report's purpose:** EMB-Bot's font set is a *derivative selection* from this
same upstream — EMB-Bot's OFL/CC-BY-SA/CC0 percentages (per its own audit,
post-remediation: 52 OFL-1.1, 1 CC-BY-4.0, 2 CC0, zero ShareAlike) trace
back to fonts originally digitized and licensed by Ink/Stitch's community.
**This document adds one new fact the font-license audit doesn't state
explicitly: the `precious` font (GPL-3.0) is Ink/Stitch's one shipped font
under the *code* license rather than a content license** — worth double-
checking EMB-Bot never accidentally pulled that specific font, since a
GPL-3.0 font is the one license tier EMB-Bot's audit didn't need to reason
about (it wasn't in EMB-Bot's shipped set) but that a future font-import
pass pulling more from `embroidery-fonts` needs to explicitly exclude.
Everything else in the font-licensing area is already more thoroughly
covered by EMB-Bot's own audit than this research could add.

### 4.3 Lettering docs page — thin on technical detail [U, partially unverifiable]

`inkstitch.org/docs/lettering/` did not surface font-format technical
specifics when fetched (redirects to a UI-usage page, not a format spec) —
the format details above came from the font-creation tutorial page instead.
No further lettering-specific findings beyond what EMB-Bot's own
`lettering-mastery-2026-08-01.md` already extracted (that document's own
Laws 45–58 already cite Ink/Stitch specifics — underlay ladder, short-stitch
gating, script `auto_satin: false` — verified consistent with source in
§2/§3 above).

---

## 5. Stitch plan / route optimization — trim vs. link

Already substantially covered by §3's `auto_run.py` finding (flat 0.75 mm
trim threshold) and §2's `auto_satin.py` finding (jump-distance-minimizing
graph routing with an overlap-based `should_trim()` check, not a
coverage/burial-aware routing decision). **Neither of Ink/Stitch's two
routing modules implements anything resembling EMB-Bot's own Law 60**
("links are routed to be COVERED, not to be short" — a link is legal
specifically where `stage5_overlap`'s `later[L]` shows something will sew
over it later). Ink/Stitch's `JumpStitch.should_trim()` checks geometric
overlap with the *source* element only ("does the jump path clear the shape
it's leaving"), not whether a *future* element will bury the thread — a
narrower, more local check. **This is a second independent confirmation
(alongside §3) that EMB-Bot's corpus-derived chaining laws are ahead of
Ink/Stitch's own shipped logic in this specific area** — there is nothing
to port here; if anything, this is worth noting as a point of genuine
competitive advantage for EMB-Bot once Laws 59–62 ship in the engine.

---

## 6. DST / machine format read-write — the highest-value finding in this report

**Correction to the task brief's premise:** Ink/Stitch does **not** depend on
`pyembroidery` (the `EmbroidePy/pyembroidery` PyPI package). Verified
directly against `requirements.txt` [V, fetched raw, full file contents
reproduced] — the single relevant line is simply `pystitch`, no version pin.
`lib/output.py`'s import section [V] confirms: `from pystitch.exceptions
import TooManyColorChangesError` / `import pystitch` — no `pyembroidery`
import anywhere in that file.

**`pystitch` is Ink/Stitch's own maintained fork of pyembroidery** — not
merely "a fork Ink/Stitch happens to use," but a fork **hosted under the
`inkstitch` GitHub org itself** (`github.com/inkstitch/pystitch`), verified
via PyPI's JSON metadata [V, `pypi.org/pypi/pystitch/json`]: summary
"Embroidery IO library," description opens **"NOTE: This is an updated fork
of the original `github.com/EmbroidePy/pyembroidery`,"** author "Tatarize,"
**license MIT**, project URLs pointing at `github.com/inkstitch/pystitch`.
The repo's own README [V] adds a specific disambiguation: *"This software is
in no way derived from or based on Jackson Yee's abandoned 2006
'pyembroidery' project"* — i.e. the name lineage is "libEmbroidery concepts
implemented in Python," and it explicitly claims broader format coverage
than the original: **writes 11 formats (the required PES/DST/EXP/JEF/VP3
plus GCode/PEC/SEW/TBF/U01/XXX), reads 46 formats** including many
specialty machine formats pyembroidery upstream doesn't cover (Toyota,
Husqvarna, Pfaff, Janome, Mitsubishi, Singer, plus `.pmv`/`.col`/`.edr`/
`.inf` sidecar formats).

**This directly and concretely bears on EMB-Bot's open DST axis bug.**
Verified the DST bit-layout in `pystitch`'s own reader/writer source
(`src/pystitch/DstReader.py` and `DstWriter.py` [V, both fetched raw]):

- Decode: X uses bits 0–3 of the three-byte record (`getbit(b0/b1, 0/1)` =
  ±1, `getbit(b0/b1, 2/3)` = ±9, `getbit(b1, 2/3)`/`getbit(b2, 2/3)` = ±27/±81);
  Y uses bits 4–7 (`getbit(b0/b1, 6/7)` = ±1, `getbit(b0/b1, 4/5)` = ±9, etc.).
- Encode (`encode_record`): mirrors this exactly — `x > 40: b2 += bit(2)`
  (X, high byte, low nibble bit), `x < -40: b2 += bit(3)`, down through
  `x > 0: b0 += bit(0)` / `x < 0: b0 += bit(1)`; Y follows an identical
  pattern shifted into bits 4–7.

**Low nibble (bits 0–3) = X, high nibble (bits 4–7) = Y, in every byte —
exactly the "consensus table" EMB-Bot's own `dst-axis-verdict-2026-07-31.md`
already established from four independent sources (pyembroidery,
libembroidery, EduTech Wiki, achatina.de).** This is now a **fifth
independent source confirming the same convention**, and arguably the
single most authoritative one available: it's the read/write implementation
a mature, actively-maintained, widely-used open-source embroidery tool
depends on for every DST file its users export, maintained by the same
project that would have every incentive to notice and fix an axis bug
(20,000+ Ink/Stitch users would immediately notice transposed DST output).
**EMB-Bot's own JS DST codec (`src/dst.js`/`src/dstimport.js`) remains
confirmed transposed against this — this finding adds confidence to the
existing verdict, it does not change it.** The fix EMB-Bot's own verdict
memo already recommends (swap the movement bits to the consensus table) is
unchanged by this research; what's new is a fifth, highly credible
confirming citation to put in front of Kent if he wants more evidence before
authorizing the fix.

**Directly actionable, separate from the axis bug:** EMB-Bot's Python
digitizer service already depends on `pyembroidery` (per this task's own
context). Given `pystitch` is (a) MIT-licensed — zero license friction to
adopt, (b) actively maintained under the same org that ships a
production-grade embroidery tool consumed by a large user base, (c) claims
broader format read coverage (46 vs. pyembroidery upstream's smaller list)
and explicit maintenance motivation ("updated fork" — implying the original
had accumulated unfixed issues), **evaluating a switch from `pyembroidery`
to `pystitch` in `digitizer/` is a concrete, low-risk, high-signal action
item.** This is not a licensing question at all (MIT → any use), just an
engineering one: does `pystitch`'s API match closely enough to `pyembroidery`'s
for a low-effort swap, and does it fix anything EMB-Bot has hit. Not
verified in this research (would require diffing `pystitch`'s API against
EMB-Bot's actual `pyembroidery` call sites, out of scope here) — flagged as
the top follow-up action, see §12.

---

## 7. Params system / UI-to-engine parameter architecture — `lib/extensions/params.py` [V]

Architecture verified: `Params.embroidery_classes()` inspects the selected
SVG node(s) and determines which `EmbroideryElement` subclasses apply
(`Clone`, `FillStitch`, `SatinColumn`, `Stroke`); each subclass defines its
own parameter set via a `get_params()` classmethod. `create_tabs()` groups
parameters into UI tabs via `group_params()` (sorted by group name + sort
index), with a **parent/dependent tab hierarchy** — `pair_tabs()`
specifically identifies mutually-exclusive inverse toggles (Stroke vs. Satin
Column) so the UI can gray out incompatible tabs, and `assign_parents()`
propagates "disable parent → disable dependents." **Multi-element editing**:
`get_values()` pulls each parameter from every selected node and
deduplicates via `list(set(...))`; when values disagree, the UI shows a
`wx.ComboBox` populated with all distinct values rather than picking one, or
a tri-state checkbox (`wx.CHK_UNDETERMINED`) for booleans — and critically,
**only parameters the user actually touched get written back**
(`self.changed_inputs` tracking), so editing one field across a mixed
selection never silently overwrites the other fields' per-element values.
**Presets**: `PresetsPanel` persists named parameter sets; a reserved
`"__LAST__"` preset name implements "Use Last Settings" without a separate
mechanism.

**Relevance to EMB-Bot's Studio** (which per this task's context has a
similar per-shape override design in flight): the two ideas most directly
transferable as *concepts* — (1) **the "only changed fields get written"
rule for multi-select edits** is a real UX correctness property worth
matching explicitly if EMB-Bot's Studio doesn't already guarantee it (editing
one param across 5 selected shapes should never clobber the other 4 params on
any of them); (2) **the parent/dependent tab pairing for mutually-exclusive
stitch types** is a clean pattern for a UI where a shape can be "satin OR
fill" — surfacing that as paired, auto-disabling tabs rather than a single
flat property list. Neither requires touching GPL code; both are UI/state-
management patterns, not algorithms, and doubly clear of any copyright
concern.

---

## 8. Palette / thread libraries — `palettes/*.gpl` [V, full directory listing, 75 files]

All 75 files use the **`.gpl` (GIMP Palette) format** — a simple, open,
plain-text format (name + hex per line), not a proprietary or
binary-encoded thread database. Manufacturer count: distinct brands
represented (some with multiple thread-type variants — e.g. ARC
Polyester/Rayon, Aurifil across 5 types, Brildor across 5 types) come to
**roughly 40–44 distinct manufacturers**: Anchor, Aurifil, Brildor, Brother,
Brothread, Coats, DMC, Embroidex, Emmel, Fil-Tec, Floriani, FuFu, Gunold,
Gutermann, Hemingworth, Isacord, Isafil, Isalon, Janome, King Star, Madeira,
Magnifico, Marathon, Metro, Mettler, Outback, Princess, RAL, Radiant,
Robison-Anton, Royal, Sigma, Simthread, Sulky, Swist, Threadart, Tristar,
Viking, Vyapar, Wonderfil, ARC, Admelody, MTB-Embroidex, BFC, Poly X40. **This
is narrower than EMB-Bot's own 68-brand / ~19,857-color chart set** (per this
task's own framing of EMB-Bot's existing state) — EMB-Bot's coverage already
exceeds Ink/Stitch's on manufacturer count. No color-matching algorithm
details were found in the `.gpl` files themselves (they're static color
lists, not matching code) — the actual nearest-color logic lives in
`lib/extensions/apply_palette.py`/`generate_palette.py`/`palette_to_text.py`
(present per the `lib/extensions/` listing, not individually verified this
session for matching-distance-metric choice; EMB-Bot's own CIEDE2000
approach was not directly compared against Ink/Stitch's because the specific
matching-distance code wasn't fetched). **One concrete, low-effort action
item:** since `.gpl` is a trivial plain-text format, it would be
straightforward to diff Ink/Stitch's 40-ish manufacturer list against
EMB-Bot's 68 to spot-check for any manufacturer or thread-line EMB-Bot might
be missing (RAL, for instance, is a general color-standard, not strictly a
thread brand, and Ink/Stitch ships it — worth checking if EMB-Bot has an
equivalent generic reference palette). Not done in this pass — flagged as a
cheap follow-up, not a finding.

---

## 9. Everything else notable

### 9.1 Visual commands / on-canvas markers — `lib/commands.py` [V]

Twelve command types confirmed verbatim from the `COMMANDS` dictionary:
`starting_point`, `ending_point`, `target_point`, `autoroute_start`,
`autoroute_end`, `stop`, `trim`, `ignore_object`, `satin_cut_point`,
`ignore_layer`, `origin`, `stop_position`. Each is an SVG `<symbol>`
prefixed `inkstitch_` (e.g. `#inkstitch_trim`), placed either as a
**connected command** (a `<use>` + a connector `<path>` carrying
`CONNECTION_START`/`CONNECTION_END` XML attributes linking the marker to a
target object) or a **standalone command** (bare `<use>`, for document-level
directives like `origin`). This is a clean, inspectable convention for
embedding machine-control intent directly in editable vector art — but it's
tightly coupled to Ink/Stitch's Inkscape-SVG-authoring model. EMB-Bot's
Studio is not an SVG-authoring surface in the same sense (it has its own
element/param JSON schema), so this is **lower relevance than most other
findings** — noted for completeness per the task's "catalog broadly" request,
not recommended for adoption.

### 9.2 Preflight / validation — `lib/extensions/troubleshoot.py` [V] and `lib/extensions/density_map.py` [V]

`troubleshoot.py` is a **framework, not a rule engine** — it doesn't define
checks itself; it calls `element.validation_errors()` /
`element.validation_warnings()` on each element (defined per-element-class
elsewhere) and renders results as **on-canvas visual pointers**: triangular
markers placed at the exact problem location, grouped into a dedicated
"Troubleshoot" SVG layer with Error (red)/Warning (yellow)/Type-Warning
(orange) severity sub-layers, plus a text-box summary panel. **No aggregate
score or grade** — unlike EMB-Bot's `preflight.py`, which per this task's
context already computes a 0–100 score, letter grade, and ~20 typed metrics.
EMB-Bot's preflight is more sophisticated in aggregation; **Ink/Stitch's
genuinely different and worth borrowing idea is the on-canvas spatial
pointer** — marking exactly where on the design each problem lives, in the
same view the user is already editing in, rather than only in a separate
report panel. Worth considering for EMB-Bot's Studio if its current
preflight surface is report-only.

`density_map.py` is a **separate, complementary tool**: a live density
heatmap using a Shapely `STRtree` spatial index to count stitch-penetration
neighbors within a configurable radius per point (defaults: red circles at
≥6 neighbors within 0.5 mm, yellow at ≥3), rendered as a color-coded overlay
layer. This is a different measurement than EMB-Bot's own "per-region
density coverage" (which per this task's context is presumably a
region-aggregate metric) — Ink/Stitch's version is **point-local and
spatial**, showing exactly which small patches are over-dense rather than
flagging a whole region. **Concept worth considering**: a live local-density
heatmap overlay as a Studio visualization layer, complementary to (not a
replacement for) EMB-Bot's existing region-level preflight scoring.

### 9.3 Print / PDF worksheet — `lib/extensions/print_pdf.py` [V]

Architecturally distinctive: **not a static PDF generator** — it runs a
local Flask web server (localhost) serving a Jinja2-templated HTML worksheet
with live palette-switching via POST endpoints (a user can swap which
thread-manufacturer palette the worksheet displays color-matched names
against, in real time, without regenerating the document from Inkscape).
Content confirmed: per-color hex/name/manufacturer/thread-number, total
stitch/color/stop/trim counts, design dimensions, **estimated thread
consumption**, and both schematic and "realistic" SVG previews per color
block. **Two concrete features EMB-Bot's worksheet (thread key + stitch
counts, per this task's context) may not have**: (a) **estimated thread
consumption** — a genuinely useful, cheap-to-compute number (total stitch
length × thread diameter/waste factor) that matters for shop costing; (b)
**per-color-block realistic preview thumbnails**, not just a swatch — showing
what each color actually looks like stitched, not just its hex value. Both
are low-effort, high-value additions to a PDF-generation pipeline that
already has the underlying stitch-plan data.

### 9.4 Realistic preview rendering — `lib/extensions/png_realistic.py` [V] and `lib/extensions/simulator.py` [V]

`png_realistic.py`: renders via `render_stitch_plan(svg, stitch_plan, True,
visual_commands=False, render_jumps=False)` after matching the design's
thread palette to a real thread catalog (`ThreadCatalog().
match_and_apply_palette()`), rasterized at a configurable DPI (default 300).
The actual thread-shading/lighting technique lives inside `render_stitch_plan()`
itself, which was not fetched this session — **the specific rendering
algorithm (how individual stitches get their sheen/shadow) was not
verified**, only the pipeline around it. `simulator.py` launches a separate
wxPython window for a live animated stitch-by-stitch playback
(`simulator.load(stitch_plan)`, `.go()`), with page/desk/border coloring and
shadow rendering pulled from SVG metadata — confirmed to exist and be a
distinct feature from the static realistic PNG export, but its playback
controls (speed, jump visibility toggles) were not visible in the fetched
file (likely live in a `SimulatorWindow` class not fetched this session).
**Not able to state confidently whether EMB-Bot has an equivalent live
animated simulator** — this wasn't established from the docs reviewed for
this task, only that EMB-Bot has a static PDF worksheet and (per its docs
folder naming) some internal `debugviz` tooling. **Flagging as an open
question rather than asserting a gap**: worth a quick direct check of
whether Studio has any stitch-by-stitch animated playback before treating
this as a roadmap item.

### 9.5 Cutwork — `lib/extensions/cutwork_segmentation.py` [V]

Confirmed: this is for **specialty multi-needle cutting-and-embroidery
combination machines** (needles that cut fabric along a path, at one of up
to 4 configurable angular sectors/needles). `CutworkSegmentation` splits
stroke elements by segment angle into up to 4 sector groups
(start/end angle + color per sector), with "sort by color" and "keep
original" options. **This is a genuinely different technique from anything
in EMB-Bot's satin or fill system** — it's not a stitch style at all, it's
routing geometry to physical cutting needles on specialty hardware. Given
EMB-Bot's stated market (small shops doing left-chest logos, caps, towel
monograms — per `lettering-mastery-2026-08-01.md` §3.5's own framing of the
target customer), cutwork machines are a rare, specialty equipment class.
**Correctly low priority** — noted for completeness, not recommended.

### 9.6 Knockdown fill — `lib/extensions/knockdown_fill.py` (referenced, not independently fetched this session)

Surfaced via the fill-tools docs page [V] as a distinct extension
("Selection to Knockdown") for flattening high-pile/textured fabric (terry,
fleece) under a subsequent fill or satin — conceptually the same purpose as
the "laydown stitch" EMB-Bot's own `lettering-mastery-2026-08-01.md` §3.4
already researched from Wilcom's monogram documentation ("It is common to
use laydown stitch with monograms in order to flatten the nap of textured
fabrics like terry toweling"). **Already an identified gap in EMB-Bot's own
prior research, not a new one** — this is corroboration that the technique
is real and shipped elsewhere (a second independent vendor confirms it),
not new information.

---

## 10. Prioritized recommendations

Ranked by value-to-EMB-Bot, with explicit legal posture per item (concept
port = clean; direct dependency = the one case literal reuse is available).

### Tier 1 — do next, concrete and low-risk

1. **Evaluate `pystitch` as a replacement for `digitizer/`'s current
   `pyembroidery` dependency** (§6). MIT-licensed, actively maintained by
   the same org shipping a production embroidery tool with a large user
   base, broader claimed format-read coverage. This is a direct dependency
   swap, not a concept port — zero licensing friction. Concrete next step:
   diff `pystitch`'s public API against EMB-Bot's actual `pyembroidery` call
   sites in `digitizer_service/formats.py` and equivalent, for a
   compatibility/effort estimate.
2. **Cite `pystitch`'s DstReader.py/DstWriter.py bit layout as a fifth
   independent confirmation** in the DST axis dispute (§6) if Kent wants
   more evidence before authorizing the `dst.js`/`dstimport.js` fix. Doesn't
   change the recommended fix, adds a highly credible citation.
3. **On-canvas spatial validation pointers** (§9.2) — a concept-level UI
   pattern (mark exact problem locations on the canvas, not just in a report
   panel) worth prototyping in Studio, alongside the existing preflight
   score. No code to port, pure UX pattern.
4. **Thread consumption estimate + per-color realistic thumbnails in the
   PDF worksheet** (§9.3) — cheap additions given the stitch-plan data
   EMB-Bot's worksheet generator already has.

### Tier 2 — real gaps worth building, concept-level only (GPL blocks code copy)

5. **Contour fill** (§1.3) — EMB-Bot's own `fill-techniques-2026-08-01.md`
   already has a fully-scoped, clean-room `stage6_contour.py` plan; this
   research confirms its citations of Ink/Stitch's approach/limitations are
   accurate. Highest-value fill gap, already de-risked by prior EMB-Bot
   research — just needs building.
6. **Meander/stipple fill** (§1.5) — genuinely zero EMB-Bot equivalent. The
   "grow a path by iteratively replacing edges with longer detours through
   unvisited graph nodes" self-avoidance concept is clean-room-portable and
   well-specified from this research; needs its own tiling-to-graph
   construction (not Ink/Stitch's).
7. **Satin e-stitch and s-stitch variants** (§2) — cheap once medial-axis
   rail extraction exists (alternate point-selection over the same rail
   geometry, not new geometry). Confirmed genuinely absent from EMB-Bot.
8. **Ripple stitch** (§1.10) — a distinct design philosophy (tolerates
   self-crossing) worth having as a named light-coverage decorative
   technique, not a variant of an existing EMB-Bot fill.
9. **Bean stitch per-position repeat pattern** (§3) — `[0,1,3]`-style
   variable-weight bean stitching, if EMB-Bot's current bean-stitch handling
   (if any) is flatter than this.

### Tier 3 — lower priority, narrow use case or already matched

10. **Tartan/plaid fill** (§1.8) — real, zero EMB-Bot equivalent, but narrow
    addressable market (kilts/tartan-themed merch specifically).
11. **Circular fill / Fermat spiral** (§1.4) — decorative novelty, cheap once
    contour-fill's ring machinery exists; not urgent standalone.
12. **Guided fill** (§1.6) — EMB-Bot's own planned parametric-map approach
    (`stage6_curved.py`) is architecturally more rigorous than Ink/Stitch's
    shipped normal-offset strategies on EMB-Bot's own documented reasoning
    (cusp/swallowtail failure modes) — proceed with EMB-Bot's existing plan,
    do not downgrade to Ink/Stitch's simpler approach.
13. **Cutwork** (§9.5) — specialty hardware, doesn't match EMB-Bot's stated
    customer base. Skip unless a customer specifically requests it.
14. **Visual command SVG markers** (§9.1) — tightly coupled to an
    SVG-authoring UI model EMB-Bot's Studio doesn't share. Skip.

### Already matched / no action needed

- **Auto-Satin shape classification** (§2) — confirmed Ink/Stitch has none;
  nothing to compare `is_satin_candidate` against. Not a gap on EMB-Bot's
  side, just an area where Ink/Stitch offers no reference.
- **Trim/link routing sophistication** (§5, §3) — EMB-Bot's corpus-derived
  chaining laws (coverage-routed) are already ahead of both of Ink/Stitch's
  routing modules (distance-threshold-routed). No action; a point of
  confirmed competitive strength worth remembering next time chaining logic
  is questioned.
- **Linear gradient fill scheduler rigor** (§1.7) — EMB-Bot's planned
  largest-remainder scheduler is more rigorous (proven error bound) than
  Ink/Stitch's shipped square-root mirrored subdivision. Proceed with
  EMB-Bot's existing plan.
- **Kerning-pair table architecture** (§4.1) — already structurally
  equivalent between the two systems.
- **Font licensing** (§4.2) — EMB-Bot's own `font-license-audit-2026-07-31.md`
  already covers this repo in more depth than this document could add;
  no further action from this research beyond the `precious` GPL-3.0
  exclusion-check note.

### Legally off-limits without a clean-room rewrite

Every algorithm cited above with a `lib/stitches/*.py` or
`lib/elements/satin_column.py` source citation is GPL-3.0 code. **None of it
may be copied, translated, or closely paraphrased into EMB-Bot.** Every
recommendation in Tiers 2–3 assumes a from-scratch implementation written
from the *geometric concept* described in this document (or independently
re-derived from first principles / published academic sources the way
EMB-Bot's own fill-techniques and lettering-mastery docs already do), with
Ink/Stitch's source not open in the same editor session as the
implementation work, the same posture EMB-Bot has already established for
`cross_stitch.py` and `contour_fill.py` in its own prior research.
