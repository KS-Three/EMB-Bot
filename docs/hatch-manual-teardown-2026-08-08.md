# Hatch Embroidery v3 manual — teardown for the auto-digitizing engine

Source: the Wilcom/Hatch v3 online help, `hatch.embroideryhelp.net/v3/en/`.
Extracted 2026-08-08 across 20 primary topic pages. Every quote below was
re-fetched from its page by hand for this document — see *Provenance and how
much to trust this* at the bottom, which matters more than usual here.

**What this doc is for.** Hatch is a vendor manual, not a measurement. It sits
BELOW `digitizer/docs/pro-digitizing-playbook.md` (39 DSTs, 410,163 stitches)
and `docs/machine-physics-playbook-2026-07-31.md` in evidence rank. Nothing
here overturns a corpus number. What a vendor manual is uniquely good for is
three things, and this doc is organized around them:

1. **Independent confirmation** of a number we derived ourselves.
2. **Rules we have no instrument for** — decisions Hatch states qualitatively
   that our corpus study cannot see (it measures output, not intent).
3. **Named gaps** — where Hatch documents a mechanism and withholds its
   numbers, which tells us precisely where we are on our own.

Provenance tag used throughout: **[V]** = vendor documentation. That is one
tier below **[M]** (measured on the corpus) and above **[D]** (our derivation).
Where a Hatch [V] and one of our [M]s disagree, the [M] wins and the
disagreement is recorded rather than resolved.

Scope note: PRODUCT.md benchmarks against Ember, not Hatch. This is a
domain-knowledge mine, not a feature-parity checklist, and findings that land
on the non-goal list are tagged **[PARKED]** rather than dropped.

---

## 0. The five things worth acting on

Everything else in this document is supporting detail.

| # | Finding | Where it lands |
|---|---|---|
| 1 | Trim threshold default is **3 mm** — identical to our `TRIM_AT_MM` | Confirms a corpus number from an independent direction. Stop treating 3.0 as provisional. |
| 2 | **Travel-on-edge auto-engages above 0.9 mm** fill row spacing | We have no such rule. `machine.py` needs one; it only bites on overridden spacing today, and `fill_row_mm` is caller-settable. |
| 3 | Pull compensation is **directional overstitching**, applied only "on the sides where the needle penetrates" | Vendor confirmation of exactly what `PipelineConfig.directional_comp` does — and it is `False` today. |
| 4 | Hatch's satin-vs-tatami discriminator is **turning/curvature**, not area | Lands directly on the queued DT-first migration; `stage7_sequence.py:97` decides on `2·area/perimeter`. |
| 5 | Tatami spacing is defined as **"the distance between two forward rows"** | A possible 2× unit trap. Do not port any Hatch spacing number until this is settled. |

---

## 1. Stitch type taxonomy and selection rules

### 1.1 Auto Split beats tatami on turning geometry [V] [ACTIONABLE]

> "Auto Split looks more satin-like and works well with turning stitches,
> creating soft lines and a little more depth. By contrast, tatami fill is flat
> and can show unwanted patterns with tight curves."
> — [Satin_fills.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Stitches/stitch_basics/Satin_fills.htm)

This is the single most interesting sentence in the manual for us, because it
contradicts the assumption our own classifier is built on. The intuitive rule
is *wide area → tatami*. Hatch's stated discriminator is **curvature**: a wide
shape that turns should stay satin (split), because tatami on a tight curve
produces a visible artifact pattern.

Bearing on our queue: `stage7_sequence.py:97` makes the satin/fill call from
`2·area/perimeter`, a pure size statistic with no curvature term at all. The
DT-first migration (`docs/dt-first-architecture-2026-08-01.md` §2, queue item
2) already exists to replace that statistic. This is a second, independent
argument for the same change — and it suggests the replacement wants a
turning/curvature term, not only a distance-transform width term.

It does **not** tell us where the boundary sits. No angle, no radius, no
threshold of any kind is given.

### 1.2 Maximum stitch length is machine-dependent, not universal [V] [BACKGROUND]

> "Usually 12.1 or 12.7 mm, this maximum value varies with the selected machine type."
> — [Satin_fills.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Stitches/stitch_basics/Satin_fills.htm)

`machine.MAX_STITCH_MM = 12.1` with the comment "format limit (not tunable)".
Both framings are correct and they are about different things: 12.1 mm is the
DST record encoding ceiling (±121 units of 0.1 mm per axis), and 12.7 mm is
0.5 in, which is what non-DST machine families allow. Hatch surfaces it as a
machine setting because Hatch exports to many formats.

**We target DST, so 12.1 stays and the comment stays right.** Worth knowing
only so that nobody "corrects" it to 12.7 after reading a Hatch forum post.

### 1.3 Outline stitch type selection is stated qualitatively only [V] [BACKGROUND]

Backstitch is for "delicate outlines", stemstitch emulates a hand look, satin
for "thicker borders"
([Outline_stitches.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Stitches/stitch_basics/Outline_stitches.htm)).
No width, length, or area threshold appears anywhere on the page.

This is a **negative result worth recording**: an auto-digitizer cannot derive
a run-vs-satin-outline decision boundary from Hatch. Ours comes from the
corpus instead — border laws 11–14 in the pro-digitizing playbook, where a
satin border measures 1.40 mm median and the bean/triple-run tier takes over
below that. Hatch has nothing to add and does not contradict it.

### 1.4 Centerline extraction claims to be thickness-independent [V] [BACKGROUND]

> "This tool will always find the center of the line no matter how thick it is."
> …"designed for use with narrow column-like objects. Results may be
> unsatisfactory if you use them on larger objects."
> — [Auto-digitize_lines.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Automatic/auto-digitize/Auto-digitize_lines.htm)

Both halves in the same topic, and no number defining "narrow" versus "larger".
Note that this is a *manual* tool in Hatch — the operator picks it — so Hatch
never has to state the threshold that an automatic pipeline is forced to
decide. That asymmetry is worth internalizing: **most of Hatch's missing
numbers are missing because a human supplies the judgment.** We do not have
that luxury.

---

## 2. Numeric parameters and defaults

Hatch publishes far fewer numbers than its page count suggests. This is the
complete set found across 20 topics.

| Value | Context | Source |
|---|---|---|
| **1.8 mm** | Run stitch length on tight, sharp curves | [Simple_outlines.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Stitches/stitch_basics/Simple_outlines.htm) |
| **4.0 mm** | Run length to mimic hand embroidery | [Simple_outlines.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Stitches/stitch_basics/Simple_outlines.htm) |
| **0.9 mm** | Fill row spacing above which Travel on Edge auto-engages | [Adjust_tatami_fill_density.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Stitches/stitch_basics/Adjust_tatami_fill_density.htm) |
| **12.1 / 12.7 mm** | Max satin stitch length, machine-dependent | [Satin_fills.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Stitches/stitch_basics/Satin_fills.htm) |
| **3 mm** | Default connector length at/above which a trim is inserted | [Automatic_connectors.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Editing/edit_advanced/Automatic_connectors.htm) |
| **2–3 mm** | Column width band that gets Center Run underlay | [Automatic_underlay.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Digitizing/digitize_objects/Automatic_underlay.htm) |
| **< 3 mm** | Typical lettering column width at normal sizes, normal fonts | [Lettering_underlay.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Lettering/lettering/Lettering_underlay.htm) |
| **≤ 15 mm** | Height of most embroidery lettering | [Lettering_underlay.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Lettering/lettering/Lettering_underlay.htm) |
| **5 / 6–10 / >10 mm** | Lettering underlay ladder, by letter height | [Lettering_underlay.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Lettering/lettering/Lettering_underlay.htm) |
| **20–65 mm** | Size band of one fancy font (Charcuterie), as an example | [Lettering_underlay.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Lettering/lettering/Lettering_underlay.htm) |
| **300 DPI** | Recommended input art resolution | [Image_quality.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Artwork/artwork/Image_quality.htm) |

That is the whole list. Eleven numbers.

### 2.1 Curvature-adaptive run length, and a coincidence worth noting [V] [ACTIONABLE-ish]

> "If a line has tight, sharp curves, reduce stitch length, for instance, to
> 1.8 mm, so that stitches follow the line more closely. To reduce the stitch
> count for flatter curves, increase stitch length."
> — [Simple_outlines.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Stitches/stitch_basics/Simple_outlines.htm)

The principle — chord length should fall with radius — we already implement,
and implement *better*: `CONTOUR_TOLERANCE_MM = 0.10` caps stitch length by
curvature at `L ≤ sqrt(8·R·tol)`, which is the continuous form of the rule
Hatch states as an anecdote.

The coincidence: at R = 4 mm, `sqrt(8 × 4 × 0.10) = 1.79 mm`. Hatch's
hand-waved "for instance, 1.8 mm" is our formula evaluated at a 4 mm radius.
That is weak evidence, but it is evidence, and it points the same way: **our
tolerance constant is in the right neighborhood.**

Gap on our side: that formula lives in the *contour ring* tier
(`machine.CONTOUR_TOLERANCE_MM`). Whether the plain run/outline generator and
the bean tier apply the same curvature cap is worth checking — `BEAN_STITCH_MM`
is a flat 0.73 mm with no curvature term, which is fine because it is already
short, but the travel and border paths are not obviously covered.

### 2.2 Travel on Edge at 0.9 mm — a rule we do not have [V] [ACTIONABLE]

> "Notice that the Travel on Edge setting is activated automatically for
> spacings larger than 0.9mm. This forces underlying travel stitches to the
> edges of shapes, preventing them from showing through open stitching."
> — [Adjust_tatami_fill_density.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Stitches/stitch_basics/Adjust_tatami_fill_density.htm)

The physics is obvious once stated: at tight spacing the fill hides its own
travel runs; past some openness it does not, and an interior travel becomes a
visible line through the design.

Our position today:
- `FILL_ROW_MM = 0.40` — well under 0.9, so at defaults this never fires.
- `TRAVEL_INSET_MM = 0.6` — travel hugs the edge but never reaches it, which
  is *already* edge-travel behaviour, always on.

So we may be accidentally compliant. But `PipelineConfig.fill_row_mm` and
`contour_spacing_mm` are both caller-overridable and both default to `None`
meaning "ask the machine table" — a caller that opens the fill up for an open
/ low-count look can cross 0.9 mm with no guard at all. And
`fabrics.py::density_adjust` scales spacing: terry towel at 0.85 and fleece at
0.90 move it *down*, but nothing stops a future preset moving it up.

**Suggested change:** a `TRAVEL_ON_EDGE_ABOVE_MM = 0.9` constant in
`machine.py`, tagged [V] Hatch, with the fill traversal path forced to
boundary routing above it. Cheap, additive, defaults unchanged.

### 2.3 The tatami spacing unit trap — unresolved [V] [CONFLICT]

> "The spacing setting is the distance between two forward rows."
> — [Adjust_tatami_fill_density.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Stitches/stitch_basics/Adjust_tatami_fill_density.htm)

Tatami rows alternate direction. "Two forward rows" therefore reads most
naturally as *two rows travelling the same way* — which are **two spacings
apart**, not one.

If that reading is right, a Hatch spacing figure is **2× the adjacent-row
centreline spacing** that Ink/Stitch, and our `FILL_ROW_MM`, use. Port a Hatch
number naively and the fill comes out half as dense as intended, or twice.

Two things make this more than pedantry:
- It would mean Hatch's own 0.9 mm travel-on-edge threshold is 0.45 mm in our
  units — which is very close to `FILL_ROW_MM = 0.40`, and would mean we sit
  just *under* the trigger rather than comfortably clear of it. That materially
  changes §2.2's conclusion.
- Hatch publishes no default spacing value at all, so there is no second number
  on the page to disambiguate against.

**Status: unresolved, and deliberately not guessed.** Settling it needs either
a Hatch trial (set spacing to a known value, export, measure the DST) or a
careful read of a Wilcom parameter reference. Until then: **do not port any
Hatch spacing figure into `machine.py`,** and treat §2.2's constant as
"0.9 mm in Hatch units, conversion unknown".

### 2.4 A number on the underlay page that should NOT be ported [V] [TRAP]

`Underlay_settings.htm` renders "Stitch length: 2.0 mm" and "Stitch length:
4.0 mm" — but these are image captions comparing two illustrations, not
underlay defaults, and the surrounding prose does not tie them to underlay at
all. `UNDERLAY_STITCH_MM = 2.5` stands on its own corpus evidence (law 8:
professional travel/run median 2.02 mm). Ignore the 2.0/4.0 pair.

---

## 3. Underlay, pull compensation, fabric profiles

This is the richest section of the manual and the one that maps most directly
onto code we already have.

### 3.1 Underlay is an ordered pair, not a boolean [V] [ACTIONABLE]

> "You have a choice two layers of underlay – Underlay 1 and Underlay 2. This
> allows you to apply dual underlays to design objects. A typical combination
> might be Edge Run with Tatami or Zigzag for larger objects."
> — [Automatic_underlay.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Digitizing/digitize_objects/Automatic_underlay.htm)

Named types: **Center Run, Edge Run, Zigzag, Tatami**. The structural point is
the composition: a *perimeter-stabilizing* pass plus an *area-stabilizing*
pass, ordered.

Our `fabrics.Fabric` carries `fill_underlay` and `satin_underlay` as single
strings, with composites baked into the id (`double_lattice`, `edge_lattice`,
`edge_zigzag`). That encodes the same idea but flattens it into an enum, so a
combination we did not pre-name cannot be expressed, and the two passes cannot
be tuned independently.

Not urgent — the enum covers the presets we ship. Worth knowing if the underlay
system is ever reopened: the natural model is `list[UnderlayPass]`, max 2.

### 3.2 Underlay scales on two axes: area and fabric stretch [V] [ACTIONABLE]

> "Larger areas and stretchy fabrics such as knits and pique generally need
> more underlay than smaller areas and firm fabrics such as drill or leather."
> …"On knits, edge run is best."
> — [Underlay_settings.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Digitizing/digitize_objects/Underlay_settings.htm)

Two named endpoints — knits/pique high, drill/leather low — and **no numeric
threshold for "larger" versus "smaller"** anywhere on the page.

Cross-check against `fabrics.py`, which is the interesting part:

| Our preset | Our `fill_underlay` | Hatch's rule |
|---|---|---|
| `pique_knit` | `edge_lattice` | pique named as high-underlay ✔ |
| `jersey_tee` | `edge_lattice` | knit, high underlay ✔ |
| `canvas_tote` / `woven_dress` | `edge_run` | firm woven, low underlay ✔ |
| `terry_towel` / `fleece_sweatshirt` | `double_lattice` | lofty, heaviest ✔ |

The *direction* agrees everywhere. One mild divergence: Hatch says flatly "on
knits, edge run is best", and we give knits `edge_lattice` — a heavier choice.
Not a defect (Hatch is talking about lettering-scale objects on the same page,
and lattice is edge-run-plus), but if a knit sew-out ever reads over-stabilized,
this is the first knob.

Also note our presets have **no area term at all** — underlay style is chosen
per fabric, never per region size. Hatch says area is a co-equal axis. That is
a real gap, and it is cheap to close because `Region` area is already known at
stage 5.

### 3.3 Pull compensation is directional — vendor confirmation [V] [ACTIONABLE]

> "counters the pull effect by 'overstitching' outlines of filled shapes on the
> sides where the needle penetrates."
> — [Pull_compensation.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Digitizing/digitize_objects/Pull_compensation.htm)

"On the sides where the needle penetrates" is precisely the directional model:
growth along the stitch direction on the edges the rows penetrate, and *not*
on the edges the rows run parallel to.

`PipelineConfig.directional_comp` implements exactly this and defaults to
`False`, with the comment: *"one isotropic `buffer(pull)` outward in every
direction, which is right on average and wrong everywhere specific — no major
package does it, because pull acts ALONG the stitch direction."*

**Hatch confirms that comment's premise from the vendor side.** The largest
consumer digitizing package on the market describes directional overstitching,
not an isotropic buffer. That does not by itself justify flipping the default —
the flag is sew-out-gated (playbook Part 4 test 4) and every committed golden
is pinned to the isotropic result — but it removes "maybe the isotropic model
is what the industry actually does" as a live objection.

Hatch states **no numeric value, no unit, no default** for pull compensation
anywhere in the topic. `Fabric.pull_comp_mm` (0.2–0.6 mm across our presets)
gets no vendor support and no vendor contradiction.

### 3.4 Fabric presets parameterize four object groups [V] [ACTIONABLE]

> "Tatami/Embossed Fill, Wide Satin, Narrow Satin, and Lettering"
> — [Manage_fabrics.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Basics/customize_designs/Manage_fabrics.htm)

Plus a stabilizer recommendation per fabric. **No fabric list and no numeric
value of any kind is published** — the mechanism is documented, the table is
withheld. That is Wilcom's actual product moat and they know it.

The granularity is the takeaway. Hatch splits satin into **wide** and
**narrow** buckets with independent fabric-dependent settings, and treats
**lettering** as a class distinct from narrow satin.

Our `Fabric` dataclass has one `pull_comp_mm` and one `density_adjust` for the
whole design, plus separate `fill_underlay` / `satin_underlay`. So we split
fill-vs-satin but not wide-vs-narrow satin, and we have no lettering-specific
fabric row at all — the lettering path (`buildLetteringDesign` in
`src/digitize.js`) reads the same preset a fill does.

That matters because pull comp is a *width-dependent* effect: 0.4 mm of
overstitch on a 1.4 mm border column is 29% of its width, and on a 5 mm column
it is 8%. A single per-fabric `pull_comp_mm` cannot be right for both. Hatch
splitting the bucket is a strong hint that a single number is a known
insufficiency, not an oversight.

**Suggested (not urgent):** widen `Fabric` to key on
`{fill, wide_satin, narrow_satin, lettering}` when pull comp is next revisited.
Additive and back-compat if the extra rows default to today's single value.

### 3.5 Lettering underlay ladder by letter height [V] [ACTIONABLE]

> "Lettering with heights under 5 mm should not have underlay" ·
> "Lettering 6 mm to 10 mm can use a center-run underlay" ·
> "Lettering larger than 10 mm can use an edge-run underlay" ·
> "Large lettering for jacket backs and the like can use a second layer of underlay"
> — [Lettering_underlay.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Lettering/lettering/Lettering_underlay.htm)

A clean three-branch rule keyed on one measured dimension, plus a fourth tier.
Supporting context from the same page: most lettering is **≤ 15 mm** high, and
normal-font columns at normal sizes are **< 3 mm** wide.

This is the most directly implementable rule in the whole manual, and it
matches something we already believe from a different direction: COOKBOOK.md's
known limitation *"small stacked text (< ~4 mm cap height at final size) drops
below what thread can hold"*. Hatch's "no underlay under 5 mm" is the same
physical regime seen from the underlay side — below that size there is no room
for a supporting pass.

**Check needed:** whether our lettering path gates underlay on glyph height at
all. `fabrics.Fabric.satin_underlay` is a flat per-fabric string with no size
term, which suggests it does not. If so, a 4 mm cap-height word on a polo is
getting `center_run` underlay it should not have.

### 3.6 Auto Split is mandatory above a font's size band [V] [BACKGROUND]

> "Even at 20mm, Auto Split should be turned on otherwise stitch length will be
> too long"
> — [Lettering_underlay.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Lettering/lettering/Lettering_underlay.htm)

Said of a fancy font with a 20–65 mm published size band. Confirms that split
satin is not an optional refinement at large lettering sizes — it is the only
thing keeping crosses inside the machine limit. `SPLIT_SATIN_ABOVE_MM = 5.0`
(corpus median vote) is far more aggressive than "only when you hit 12.1 mm",
and the corpus is the better authority. Consistent, no action.

---

## 4. Auto-digitizing pipeline

Hatch documents its pipeline's *shape* clearly and its *numbers* not at all.
Both halves are useful.

### 4.1 The stated pipeline [V] [BACKGROUND]

Image prep — the tool "automatically flattens colors, sharpens outlines, and
reduces noise", against inputs suffering "dithering, anti-aliasing, or other
sources of 'noise' in the image"
([Prepare_artwork_for_auto-digitizing1.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Artwork/artwork_edit/Prepare_artwork_for_auto-digitizing1.htm)).

Classification — "Hatch Embroidery will attempt to classify image colors as
fills or details. Details may take the form of outlines or 'pickout runs'",
with details rendered "as a centerline, satin line, or a satin fill"
([Auto-digitize_embroidery.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Automatic/auto-digitize/Auto-digitize_embroidery.htm)).

One-click — Instant Embroidery "automatically determines colors to treat as
fills or outlines, or omit altogether" and "chooses the most suitable stitch
types to apply with default settings"
([Instant_embroidery.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Automatic/auto-digitize/Instant_embroidery.htm)).

**The structural observation: Hatch classifies by COLOR, we classify by
REGION.** Hatch's unit of decision is a palette entry — *this color is a fill,
that color is detail, that one is omitted* — and geometry follows. Our stage 3
classifies each connected region independently after quantization. Hatch's
model is coarser and would, for instance, make every instance of the same
color take the same tier.

Not obviously better or worse, and not a change to make. But it is the natural
model for a **user-facing control** — "treat this color as detail / omit this
color" is a far more legible review-screen affordance than per-region tier
overrides, and our `shape_overrides` contract (`config.py`, keyed on
`shape_id`) is per-shape only. Worth remembering when the review screen grows.

### 4.2 Input art requirements — Hatch's version of "flat art in" [V] [ACTIONABLE]

> "Use 300 DPI high-resolution images, NOT low-res 96 DPI." · "Do use PNG
> format, not JPG." · "Do use transparent backgrounds." · "Do not use
> anti-aliasing."
> — [Image_quality.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Artwork/artwork/Image_quality.htm)

And two named art categories: **outlined** images, ideally with "a solid black
outline around each colored area", and **non-outlined** images of "solid areas
of color".

Against our numbers: `min_px_per_mm = 4.0` is a floor of ~102 DPI at final
size; 300 DPI is ~11.8 px/mm, roughly 3× that. No conflict — ours is a hard
refuse-to-proceed floor, Hatch's is a recommendation — but it does say our
user-facing guidance is quiet where Hatch's is loud. "300 DPI PNG, no
anti-aliasing, transparent background" is a better instruction to a customer
than anything we currently say, and it is exactly the "flat art in, pro out"
rule stated as a checklist.

### 4.3 Hatch *blocks* rather than warns [V] [ACTIONABLE — product]

> "Hatch Embroidery will not let you apply automatic digitizing until the image
> has been suitably processed."
> — [Image_quality.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Artwork/artwork/Image_quality.htm)

A hard gate, not a warning. Ours is the Flatten workflow, which is available
and visible but optional.

This is worth weighing against the most customer-visible defect in our pipeline
— the benchmark logo's "ENTERPRISES INC." subline silently vanishing behind a
`DROPPED_SMALL_SHAPES` warning (COOKBOOK.md, hard-won lessons). Hatch's posture
is that the user should be stopped *before* the engine produces something
disappointing. Ours is that the engine proceeds and reports. Not a bug, and not
a call to make here — it is Kent's product decision, and it belongs next to the
existing preflight work rather than as an engine change.

### 4.4 What Hatch tells us about their tools' geometry [V] [BACKGROUND]

- Click-to-Fill: "large artwork shapes with tatami fill"; Click-to-Turning
  Fill: "narrow column artwork shapes with satin stitch"
  ([Auto-digitize_fills.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Automatic/auto-digitize/Auto-digitize_fills.htm)).
  Confirms the same two-tier split we make, with no threshold given.
- Stitch angles are editable after generation ("use Reshape to edit generated
  objects, in particular, stitch angles") but **no assignment logic or default
  is stated**. Our per-region PCA principal axis (`fill_angle_deg = None`) has
  no vendor comparison available.
- Branching "digitize[s] similar, overlapping objects – e.g. the fingers of a
  hand … without having to think about the most efficient stitching sequence
  and joins", with "connectors minimized"
  ([Branching.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Digitizing/digitize_advanced/Branching.htm)).
  Names the problem our stage 7 chaining solves. Zero algorithmic detail.

---

## 5. Sequencing, connectors, trims

### 5.1 The 3 mm trim threshold — independent confirmation [V] [CONFIRMS]

> "When selected, automatic trims are applied when connectors are greater than
> or equal to the specified value (default = 3mm)."
> — [Automatic_connectors.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Editing/edit_advanced/Automatic_connectors.htm)

`machine.TRIM_AT_MM = 3.0`. Same number, same semantics, arrived at
independently — ours from the corpus and from `src/fabrics.js`, theirs as a
shipped product default across presumably a very large installed base.

This is the strongest single validation in the document. It also retroactively
supports COOKBOOK.md's warning *"do not chase `trim_at_mm` to reduce trims"* —
3.0 is not a number we picked loosely and it should not be moved to hit a
trims-per-1k target.

Hatch's three modes are **Always / On-if-next-connector-≥ / Off**. We
effectively hardcode the middle mode. The `Always` and `Off` modes are house
styles we do not expose, and the corpus (median 0.8 trims per 1,000 stitches,
range 0.1–4.1 — playbook law 1) shows real shops sitting across that whole
spread. Not a gap worth closing now, but it explains the spread.

### 5.2 Closest joins [V] [BACKGROUND]

> "entry and exit points of objects are automatically placed close together
> while you digitize" … "Closest joins are not automatically maintained when
> objects are moved, re-sequenced, or edited."
> — [Closest_joins.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Editing/edit_advanced/Closest_joins.htm)

No threshold, no algorithm. The second sentence is the interesting one: Hatch's
join optimization is a **one-shot pass over a static sequence**, not an
invariant. Ours (stage 7) recomputes from scratch every run, which is
structurally stronger — a point in our favor worth noting, since `chain_links`
is currently off and it is easy to read that as being behind.

### 5.3 Tie-offs, locks, minimum stitch length [V] [GAP]

Hatch publishes **nothing**: no tie-off stitch count, no lock stitch length, no
minimum-stitch filter value, no short-stitch rule for tight curves. The
connectors overview page says only that connectors "can be run stitches or
jumps"
([Embroidery_connections.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Editing/edit_advanced/Embroidery_connections.htm)).

Everything we have here is ours: `TIE_STITCHES = 3`, `TIE_STITCH_MM = 0.8`
(with playbook law 6's open question — corpus median is 0.45 mm, so ours may be
long), `MIN_STITCH_MM = 1.0`, `TINY_STITCH_MM = 0.5`,
`SATIN_SHORT_STITCH_AT_MM = 0.3`. No vendor cross-check is available for any of
them.

### 5.4 Fill edge remainder handling [V] [BACKGROUND]

The tatami density page states that stitch length varies within a row to avoid
generating very short stitches where a row meets the shape boundary
([Adjust_tatami_fill_density.htm](https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Stitches/stitch_basics/Adjust_tatami_fill_density.htm)).

That is *generation-time remainder absorption* rather than a post-hoc minimum
length filter. Worth confirming which one `stage6_fill.py` does — the two
produce visibly different edges, and a post-hoc filter leaves a slightly ragged
row end where absorption does not.

---

## 6. Parked — real content, on the non-goal list

PRODUCT.md excludes decorative fills, stitch-level editing, appliqué, 3D puff,
monogram frames, team names, and imported-design re-density. Most of Hatch's
"Decorative Stitch Types" and "Stitch Effects" trees land there. Recorded so
nobody re-researches them:

- **Motif stitching** — library of pre-defined motifs repeated in parallel rows
  for decorative outlines or fills. [PARKED]
- **Stipple fills** — meandering run-stitch texture within a border. [PARKED]
- **Cross stitch fill** — "crosses in separate objects line up precisely when
  using the same fabric count". [PARKED]
- **Embossed fills** — patterned stitching within a solid field. [PARKED]
- **Organic / hand-stitch effects, feathered edges.** [PARKED]

Two entries need a flag rather than a park, because **the Python engine already
has these tiers built** even though PRODUCT.md's launch list excludes
"decorative fills":

- **Contoured / curved fills** — rows following the silhouette. We have
  `stage6_contour.py` + `fill_technique="contour"`, off by default with three
  documented defects (`config.py` lines 119–151).
- **Gradient fill effects** — spacing ramped between dense and open to shade.
  We have `stage6_blend.py`, plus `docs/fill-techniques-2026-08-01.md` law 41,
  which *corrects* Wilcom's own published "choose complementary profiles"
  instruction as arithmetically wrong (it puts a +33% coverage bulge at both
  ends of the blend).

That second one is the sharpest illustration of where Hatch sits as a source:
we have already caught the vendor being wrong on the one blend instruction they
publish with enough specificity to check.

**Open question for Kent, not a finding:** PRODUCT.md lists decorative fills as
an explicit non-goal while `digitizer/` ships contour and blend tiers. Those may
simply be different scopes — engine capability versus Studio launch surface —
but the two documents read as contradicting each other and one of them is stale.

---

## 7. What Hatch does not state — the gap list

Where we are on our own, confirmed by direct fetch rather than assumed:

| Topic | Hatch's position |
|---|---|
| Pull compensation magnitude | Mechanism documented, **no number, no unit, no default** anywhere |
| Fabric setting values | Four object groups named; **no fabric list, no values** |
| Satin-vs-fill width threshold | Never stated in mm |
| Auto-digitize region thresholds | No min detail size, no area cutoff, no color-count limit |
| Default tatami row spacing | Not published (only the 0.9 mm travel trigger) |
| Tie-off / lock stitch geometry | Nothing |
| Minimum stitch length filter | Nothing |
| Short-stitch rule on curves | Nothing |
| Stitch angle assignment | Editable, logic unstated |
| Branching algorithm | Problem named, method withheld |
| Underlay inset / margin | Nothing |
| Underlay spacing relative to cover | Nothing |

Roughly: **Hatch publishes the taxonomy and withholds the constants.** Every
number that would let a competitor reproduce their output quality is absent,
and the eleven numbers they do publish are mostly user-facing advice rather
than engine parameters. That is not an accident and it caps how much this
source can ever give us.

Practical consequence: for anything in the table above, the ladder is
**corpus measurement → Ink/Stitch → our own derivation**, in that order, and
Hatch does not enter it.

---

## 8. Suggested changes, ranked

Nothing here is a bug, and none of it is urgent against the current queue
(gradient regressions → DT-first M0/M1). Ordered by value per unit of risk.

1. **`TRAVEL_ON_EDGE_ABOVE_MM = 0.9` in `machine.py`** [V], forcing boundary
   travel routing above it. Additive; defaults unchanged; guards a knob callers
   can already turn. **Blocked on §2.3** — settle the forward-rows unit question
   first, or the constant is wrong by 2×.
2. **Size-gate lettering underlay** on the §3.5 ladder (<5 mm none, 6–10 mm
   center run, >10 mm edge run). First confirm whether the lettering path gates
   on glyph height at all today.
3. **Add an area term to underlay selection** (§3.2). `Region` area is known at
   stage 5; Hatch treats area as co-equal with fabric stretch and we have no
   area term whatsoever.
4. **Quote 300 DPI / PNG / no-AA / transparent-bg in user-facing art guidance**
   (§4.2). Zero engine risk; it is the "flat art in" rule as a checklist.
5. **Record Hatch's directional-pull-comp wording** in `config.py` beside
   `directional_comp` (§3.3) as [V] supporting evidence. Documentation only —
   the flag stays sew-out-gated.
6. **Widen `Fabric` to four object groups** (§3.4) *when pull comp is next
   revisited.* Not before — it is a schema change earning nothing until there
   are different numbers to put in the new rows.

Explicitly **not** suggested: changing `TRIM_AT_MM`, `MAX_STITCH_MM`,
`SATIN_MAX_WIDTH_MM`, or any density constant. Hatch either confirms these or
says nothing, and the corpus outranks it in both cases.

---

## Provenance and how much to trust this

Gathered by the `deep-research` workflow (102 agents; 20 primary sources
fetched; 99 candidate claims extracted). **The workflow's own verification
phase failed and its verdicts are not used in this document.**

It hit the session token limit partway through Verify: 22 verifier agents
errored out and the synthesis step never ran. Worse than the missing output,
the verdicts it *did* produce are unreliable. Four claims it marked refuted
0–3 were re-fetched by hand and found verbatim on their source pages:

- the 12.1 / 12.7 mm max stitch length (§1.2),
- the lettering underlay height ladder (§3.5),
- Center Run underlay for 2–3 mm columns (§3.1/§2),
- Auto Split preferred over tatami on turning geometry (§1.1).

The likely mechanism is that the adversarial verifiers were instructed to
default to *refuted* under uncertainty, and could not re-fetch their pages once
the session limit began biting — so a fetch failure read as a failed
verification. §1.1 in particular is the most interesting finding in the
document and was one keystroke from being thrown away.

**Every quotation in this document was therefore re-fetched directly from its
source URL and read in full before being written down.** Where a page states no
number, that is recorded as an explicit negative result (§7) rather than an
absence of research. Where a reading is ambiguous, it is flagged unresolved and
not guessed (§2.3).

Standing lesson, consistent with COOKBOOK.md's *"verify claims, don't trust
prior summaries at face value"*: **a confident refutation from an automated
verifier is a claim like any other.** Two of the four rescued findings are in
the top-five action list.
