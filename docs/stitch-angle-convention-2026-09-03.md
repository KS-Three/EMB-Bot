# Stitch-angle convention — what the trade does, measured, and a rule to derive it per design (2026-09-03)

Kent, on being asked whether the four-fold house angle should sew at 45° or
135°: *"You'll need a logical way to determine this for every logo and photo.
Please research standard digitizing angle procedure."* And, on the same day:
rule on how a diagonal stroke takes a house angle before `satin_house_fourfold`
is flipped on.

This file is that research. Four sources, three of them measured in this repo
rather than quoted, then one rule. Every number carries where it came from.

## 1. What the published trade says

Thin, and mostly about *fill*. What survives a read of the sources:

- **Satin: stitches perpendicular to the column.** *"If you place your points
  straight across from each other, the stitch angle remains perpendicular … If
  it is off-axis, the satin stitches will look 'twisted,' and light will
  reflect poorly."* Corners are **mitred**: the two objects' angle lines are
  set *parallel where they overlap, "usually at a 45-degree angle in the
  corner"*, so *"the light reflection should appear to turn the corner
  fluidly"*; *"abrupt turns create gaps or lumps."* Angles are set per
  segment, not once per word. *(Wilcom Column A/B/C guide,
  embroideryhoopstore.com)*
- **Fill: 45° is the software default, and the advice is to vary it.**
  *"Digitizing programs by default like to fill areas of stitching at a 45
  degree angle"*; an unvaried angle *"will look very one-dimensional"*; angles
  chosen *"to fight pull and stretch"* on the fabric. One source puts the
  grain argument the other way: 45° to the grain is where many materials
  stretch most, and *"15 to 20 degrees off the horizontal is generally
  enough"*. *(machineembroiderygeek.com; Impressions; mySewnet digitizing
  guide)*
- **Small lettering:** running stitch under ~1 mm stroke, satin 1–7 mm,
  minimum stroke 1 mm, letters ≥ 5 mm — and the one practitioner article that
  asks *"How to digitize corners properly? How to digitize serifs properly?"*
  leaves both unanswered. *(forum.embroideres.com; Impressions "How to
  Digitize Small Lettering")*

No published source gives a rule for the angle of a diagonal stroke under a
word's house angle. The repo's own evidence does.

## 2. What the professional file does (Becker Marine, Wilcom operator)

Already measured 2026-08-26 (`.claude/memory/letterform-fidelity-2026-08-26.md`):
on the MARINE text band, letter runs sit at a modal cross angle of **2°**, **6/7
within ±20°** of it (chance 22%). Rendered through `stitchviz` on 2026-09-02:
the pro sews **every** stroke of MARINE at that one near-horizontal cross —
the E's arms and the A's crossbar become short wide columns of 3–4 mm stitches
laid *along* the bar, and the N's and A's diagonals lean toward it.

Re-measured 2026-09-03 on all five `testdata/reference/becker_*.dst`, satin
zigzags only (consecutive stitches reversing direction, column advancing
≤ 0.7 mm per stitch, crosses ≥ 0.8 mm), deviation of the cross from the
perpendicular to the column's own advance:

| column advances… | n crosses | median | p75 | p90 |
|---|---|---|---|---|
| vertically | 6,379 | 4.7° | 11.3° | 20.4° |
| horizontally | 4,089 | 7.9° | 13.7° | 25.9° |
| diagonally | 8,022 | **15.9°** | 26.1° | 43.2° |

Read the limit: "column advance" is where the needle walks, not the letter
stroke — a bar sewn as a wide short column advances *vertically* and lands in
the first row. So this table says the pro leans crosses **more on diagonal
columns than on axial ones, and rarely past ~45°**; it cannot by itself say
whether horizontals are sewn as bars or as wide columns. The render says wide
columns.

**The pro's convention, stated:** one house angle per word, perpendicular to
the stems; horizontals sewn as wide short columns at that same angle;
diagonals held loosely toward it, typically 15–25° off their own perpendicular.

## 3. What 86 fonts do (Ink/Stitch authors, the shipped library)

The font library carries the authors' own **rungs** — explicit cross
directions along each satin column — so it is a direct record of how 86
digitizers angle strokes. Measured 2026-09-03 over every uppercase glyph's
columns (`scratchpad/fontangles.py`; column direction read from the rails at
each rung, class by that direction):

| stroke class | n crosses | cross deviation from the stroke's perpendicular: median | p75 | p90 |
|---|---|---|---|---|
| stem (vertical) | 13,367 | **1.8°** | 10.4° | 32.5° |
| bar (horizontal) | 14,772 | **3.0°** | 14.3° | 45.0° |
| diagonal | 20,439 | **18.1°** | 45.0° | 72.3° |

- **Stems and bars are perpendicular.** Font authors do NOT sew a bar as a wide
  column; they sew it as a column with vertical crosses.
- **Diagonals lean.** Median 18° off perpendicular; on N A V K M W X Y Z alone
  the median lean is **29.5°**, and **58% of those leans are toward the stems'
  cross angle**, 42% away — a loose pull toward the house, not a rule.
- **"One angle for the whole word" is a minority style.** Per-glyph resultant
  of cross angles has median R = 0.3; only **5 of 64** fonts with enough data
  hold R > 0.8 across all their capitals (`mimosa`, `inkstitch_masego`,
  `roaring_twenties`) — and those are the flat, single-angle "block satin"
  faces.

## 4. What the expired patents say — the two that answer the question

From `docs/masters-teardown-2026-08-01.md` (Goldman/Brother US7587256B2,
expired; Pulse US6390005B1, expired 2018):

- **Diagonals and sharp corners, Goldman, verbatim:** *"Stitching
  continuously around such areas of sharpness may produce unfavorable results
  … excessive interpolation of associated stitching causing a sparseness on
  one side of the column and a bunching or overstitching on the opposite side.
  To remove this problem, the column smoothing mechanism breaks the column into
  two separately sewable regions that meet at the area of sharpness … the
  diagonal line region would be extended on either end and made into a single
  column of satin stitches. Subsequently, the two vertical lines would be
  shortened slightly at the area where they meet the diagonal."* Threshold
  **45°**. Policy: **one member runs through and is extended; the others butt
  into it and are shortened.** On an N, the *diagonal* is the member that runs
  through.
- **Density under a leaned cross, Pulse:** hold the **perpendicular**
  interstitch distance constant and let the along-column inset float. Their
  published calibration at 0.4 mm density: stitch angle 30° → inset 26.8%,
  45° → **58.6%**, 60° → 100%. A fixed along-spine spacing is *"only correct
  near 30°"*.

That second one is the mechanism behind the pile on ENTHUSIAST's N
(`docs/hotel-fremont-fine-details-2026-09-02.md`): `_rail_points` spaces
stations 0.4 mm along the **spine**, so a cross leaned θ from perpendicular
lands its neighbours 0.4·cos θ apart measured across the thread — at 45° that
is 0.28 mm, **1.41× the intended density**, on every leaned stroke. The
"uniform" 45° Hotel Fremont render is also 1.41× dense everywhere. Nobody has
sewn it; the arithmetic is not in doubt.

## 5. The rule — derived per design, no convention constant

Three findings agree: stems perpendicular (pro 4.7°, fonts 1.8°); horizontals
perpendicular in the community and wide-column in the commercial file; diagonals
leaned loosely toward the house, rarely past ~45° and typically 15–30°. The
bisector this repo shipped (off) is what none of them do — it was a workaround
for one limitation of ours, that a horizontal cannot take a 0° cross without
the span clamp flipping sign on tangent noise.

**Satin lettering.**

1. **House angle = perpendicular to the dominant stem family.** The doubled-
   angle reading already derives this where stems dominate (Becker 171–176°).
   Where two orthogonal families balance (slab serifs, the four-fold case), the
   house is the perpendicular to the **longer** family — for Hotel Fremont the
   stems, 112 mm against 44 mm — not their bisector. No 45-vs-135 choice
   exists: the angle comes from the art and rotates with it.
2. **A stroke that cannot span the house takes its own perpendicular.** That
   is what every font does with a bar (3.0°), and it removes the ±45° sign flip
   entirely: the clamp's failure mode was choosing a *side* by noise, and
   "perpendicular" has no side. Sewing horizontals as wide columns at the house
   angle (the commercial pro's way) is a new construction (sweep the bar's
   full extent along its perpendicular); until it exists, perpendicular is the
   trade's other convention and the one the library already follows.
3. **Diagonals lean toward the house, capped.** Hold the house where the
   stroke can span it within a lean limit; past it, lean by the limit toward
   the house rather than snapping to perpendicular. The measured band is
   15–30° (pro p50 16°, p75 26°; fonts p50 18°, diagonals-only 29.5°), so
   `SATIN_HOUSE_MIN_SPAN_DEG` = 45 (a 45° lean) sits at the *edge* of what the
   pro ever does (p90 43°). A 30° lean limit (`SATIN_HOUSE_MIN_SPAN_DEG` = 60)
   is inside both bands.
4. **Compensate density for lean (Pulse).** Station spacing along the spine
   becomes `SATIN_SPACING_MM / cos(lean)` so the perpendicular pitch stays the
   0.4 mm the constant already means. This changes no physical constant — it
   makes the existing one hold under lean — and it is what turns the N's pile
   back into a column. Gate 1 is untouched; a sew-out of a leaned column would
   still be the proof.
5. **Corners ≥ 45° between members (the hanging-serif L, the N's junctions):
   the Goldman rule.** One member runs through and is extended, the other is
   shortened and butts into it — the diagonal runs through on an N, the longer
   arm on a serif L. This is NOT `_SPLIT_TURN_DEG` 90 → 70 (withdrawn: it
   splits into two capped columns and reds a golden); it is a butt-join with
   an extended through-member, which is the mitre the Wilcom guide describes.
   The corpus statistic that pros sew *through* corners (1436:18) is about
   turning a column round a bend, not about two straight members meeting at
   90°; the Goldman disclosure is explicit that the latter is broken, not
   turned.

**Fill.** Lettering that routes to fill takes the same house angle (already
wired). Non-lettering shapes: the trade default is 45° with variation between
neighbours; this repo's measured answer is fragment-count minimisation over 16
candidate angles (G3 in the masters teardown, expired patent, not built),
which chooses the angle that costs the fewest needle repositions — a better
objective than either 45° or per-region PCA, and the patchwork-angle defect
Kent named on 2026-08-01 is the PCA one.

**Photos.** Direction field, as shipped (`directionfield`); the angle question
here is per-pixel and already answered by the art.

## 6. What this changes about `satin_house_fourfold`, and what Kent decides

The flag's *reading* (two orthogonal families, four-fold space) is sound; its
*answer* (the bisector) is the wrong convention by every source above. Under
the rule: Hotel Fremont's house is 0° (stems perpendicular), its E arms and T
bar sew perpendicular (vertical crosses, no sign flip), its hanging serifs are
Goldman-joined, and ENTHUSIAST's N leans ≤ 30° at compensated density instead
of piling at 48°. None of that is measured yet — items 2, 4 and 5 are code.

Kent's decisions, in order of what each unblocks:

1. **Adopt the rule** (house = stems' perpendicular; perpendicular fallback;
   lean cap; density compensation; Goldman butt-join)? This retires the
   45-vs-135 question and the bisector.
2. **Lean cap: 30° or 45°?** 30° is inside both measured bands; 45° is the
   pro's p90. One constant, `SATIN_HOUSE_MIN_SPAN_DEG`.
3. **Order of build.** Density compensation (item 4) is small, gate-1-clean,
   and fixes the pile on its own; the Goldman join (item 5) is the corner
   work the letterform memory has circled since 08-26 and is the larger job.

## Sources

- [Wilcom Logo Digitizing: Column A, B, C, mitres](https://embroideryhoopstore.com/blogs/articles/wilcom-logo-digitizing-master-column-a-b-and-c-for-clean-satin-perfect-miters-and-gap-free-borders-cap-ready)
- [Digitizing Tips and Tricks — Machine Embroidery Geek](https://www.machineembroiderygeek.com/digitizing-tips-and-tricks-for-machine-embroidery/)
- [How to Digitize Small Lettering — Impressions](https://impressionsmagazine.com/process-technique/how-to-digitize-small-lettering/16215/)
- [Lettering in machine embroidery: basic rules — embroideres.com](https://forum.embroideres.com/articles.html/articles/lettering-in-machine-embroidery-the-basic-rules-of-digitizing-text-by-hand-r147/)
- [mySewnet Digitizing Guide (fill angles)](https://softwarehelp.mysewnet.com/SampleGuides/100/mySewnetEmbroidery_DigitizingGuide_100.pdf)
- [Common Embroidery Stitch Matrix — A&E](https://www.amefird.com/wp-content/uploads/2010/02/CommonEmbStitchMatrix-2-11-10.pdf)
- Goldman US7587256B2 and Pulse US6390005B1 as digested in `docs/masters-teardown-2026-08-01.md`
- Measurements: `testdata/reference/becker_*.dst` (five files, pystitch), `src/fonts/*.json` + `src/fonts/bin/*.embf` (86 fonts, `EMBF` decoded in Python)

## 7. Pass 1 BUILT (2026-09-03, same day) — items 2, 3, 4; one correction to item 1

Kent adopted the rule and the 30° cap, then picked pass 1 (fallback, cap,
density compensation) over the Goldman join. Built in `stage6_satin` and
`textcluster`; `satin_house_fourfold` stays OFF (Kent's flip), and every
fixture without a house angle is md5-identical (whitebg, alpha, ribbon_curve,
Fremont with the flag off).

**Item 2 + 3, reconciled as one function.** Items 2 and 3 read against each
other at the boundary: "a stroke that cannot span the house takes its own
perpendicular" and "past the cap, lean by the cap". If the cap simply
held past its edge, a bar 89.9° from the house would lean +30 and one at
90.1° would lean −30 — the same side flip the bisector was built to dodge,
narrowed but not gone. `_clamp_to_span` now holds the house within the cap
and past it **fades the lean linearly to zero at the house axis**:
`lean = cap · (90 − |d|) / (90 − cap)`. Continuous everywhere (pinned in
half-degree steps), the full cap at the cap's edge, 22.5° on a true 45°
diagonal (pro p75 26°, fonts diagonals-only 29.5°), perpendicular with no
side for a bar along the axis. `SATIN_HOUSE_MIN_SPAN_DEG` 45 → 60.

**Item 4.** `_cross_angles` (factored out of `_rail_points`, byte-identical
with no house) returns each station's lean against the smoothed perpendicular
the stroke would otherwise carry; `_resample_by_pitch` spreads the stations
evenly along ∫cos(lean) ds, so the along-spine step is spacing / cos(lean)
and the pitch across the thread stays what `SATIN_SPACING_MM` means; the
outer-rail refinement targets the same lean-corrected pitch. Measured with
`tools/satin_lean.py` (thread pitch = half the station spacing, two threads
per station):

| housed lettering | thread pitch before → after | crosses | stitches | trims |
|---|---|---|---|---|
| Fremont, four-fold on (house 44° → **0°**) | **0.152 → 0.198 mm** | 885 → 812 | 6405 → 6343 | 52 → 52 |
| ENTHUSIAST @ 93, four-fold on (48° → **3°**) | **0.152 → 0.200** | 1096 → 1001 | 3072 → 3005 | 22 → 25 |
| THERMAL, four-fold on (45° → **0°**) | 0.175 → 0.195 | 1829 → 1859 | 8791 → 8856 | 91 → 93 |
| Becker MARINE (doubled reading, 171°) | 0.193 → 0.186 | 694 → 724 | 4529 → 4524 | 28 → 28 |

The ENTHUSIAST chaining benchmark with the flag on: **4.62 → 4.09 / 1k**
against the 4.1 ceiling (off: 2.43, unchanged). Lean off each cross's own
perpendicular on Fremont: p50 45 → **20**, p90 64 → 37, past 45°: 50% → 3%
— against a stock (no house) floor of p50 19, p90 32, 1%, which is the
raster wander a skeleton column carries anyway. Corners still sweep (a
merged stem-to-bar chain turns its cross 90° across the smoothing width;
Becker 40% past 45° against a 24% stock floor): that is the Goldman join,
pass 2.

**Item 1, corrected: "the longer family" is the wrong tie-break.** On
end-trimmed chains Fremont's stems win 84 : 72 mm, but THERMAL reads
20 : 23 and ENTHUSIAST's eleven capitals 61 : 71 — the bars longer on two
upright wordmarks, and "longer" would have sewn their stems as bars. What
makes a stem a stem is that it stands square to the **line of text**, which
a lettering group knows and a glyph does not: `_line_of_text_deg` is the
principal axis of the members' centroids, and the house is the four-fold
family nearer it (`_house_along_line_deg`). Right on all four measured
groups (Fremont 179.4°, THE 177.8°, THERMAL 0.1°, ENTHUSIAST 3.0°), agrees
with the doubled reading on both Becker lines, rotates with the art, fails
open when the centroids make no line (second singular value over a third of
the first). Known limit: stacked glyphs, where the line runs along the
stems — no fixture has one, and the doubled reading still answers where
stems dominate. `_bisector_deg` and `SATIN_HOUSE_BISECTOR_DEG` are gone.

**Found on the way, NOT fixed here — rail dents on rotated columns.**
`_rail_points`' `place` puts each rail at the measured width and shrinks it
to 0.85× when `poly.covers` fails; on a **stock** 3 mm bar rotated 25° one
whole rail sits at 1.22–1.27 mm against the other's 1.44–1.46 — the thread
stops ~0.2 mm short of the artwork on one side of every rotated column,
today, in every golden. Under lean the same dust fires on a few stations of
an upright bar and the outer-rail refinement re-inserts a station at each
dent, so the compensation's count saving on a synthetic leaned bar is 3%
where cos(25°) says 9% (real art above is unaffected: the pitch is what was
measured). A fix touches every satin golden; recorded as a defect.

**Found on the way, tried and WITHDRAWN — hairline columns under a house
angle.** Fremont's 2.6 mm "THE" has 0.40–0.45 mm bars and 0.52 mm stems. A
perpendicular cross on them is at or under `SATIN_MIN_CROSS_MM` (0.5) once
the rails sit symmetric at the nearer boundary hit and `place` dents one, so
under the rule the bars vanish (3 runs where the bisector sewed 7). The
shipped default already loses THE's bars — its stems survive only because
the ~19° raster wander happens to lengthen the cross — and the bisector kept
them by accident at 0.62 mm. A per-station lean floor (lean as far as a
target cross length demands, from the boundary distance) was built and
measured: the distance collapses toward the caps, the lean fans 45→2→45°
over a 2.5 mm stem, and the crosses still come out 0.44–0.49 mm (H stems 0
of 10 kept against the stock's 8–10). Withdrawn; lettering that small wants a
different tier (running stitch, or a bar sewn as a wide column), not a lean
hack. Recorded as a limit, not a defect of the rule.

**Review hardening.** The lean is a difference of two separately unwrapped
sequences, so a spine turning ~60° between adjacent stations (nothing the
smoothing delivers today) could push the smoothed difference through 90° and
the compensation to ×60; the cosine is floored at cos(cap), a no-op on
every output measured. `_resample_by_pitch` snaps both ends exactly.

What pass 1 does not do: sew a bar as a wide column at the house angle (the
pro's way; new construction), join corners (Goldman, pass 2), or flip the
four-fold flag — the numbers above are what the flip would buy.

## 8. `satin_house_fourfold` DEFAULT ON — Kent's flip (2026-09-03, same session)

On the pass-1 numbers Kent flipped the four-fold reading on. What moves:
`logo_hotel_fremont` (6385 → 6343 st, trims 52) and `drone_render`'s
THERMAL (8872 → 8856, trims 93). Byte-identical with the flag on: whitebg,
alpha, ribbon_curve, becker, bg_uncertain, gaulke, summit_badge,
region_blobs, fur_ramp, repro_gradient_white_icon, enthusiast @ 80 (the
eleven-capital group fires at 93 mm, the chaining benchmark's pitch, where
the benchmark reads 4.09/1k under 4.1). Digitize time unchanged on all
thirteen. No golden moves: drone's golden pins stage 2 only, enthusiast's
flat-lane entries are the platform reds CI already deselects. The function
default in `set_lettering_house_angle` stays False. The 0.01 margin under
the benchmark ceiling is thin and the test is the tripwire.

## 9. Pass 2 BUILT — the Goldman corner join (2026-09-03, same session)

Kent picked the join next. Built in `stage6_satin._split_sharp_corners`,
`_boundary_corner_near`, `Stroke.corners` and `_satin_joined`.

**What a corner is.** The spine turns ≥ 45° (`_JOIN_TURN_DEG`) over one
half-width **and** the artwork has a **reflex** corner of ≥ 45° within a 1 mm
stretch of its boundary near the apex. Two members meeting always make one
on the inside of the meeting (the crotch of an L, the underside of a slab
serif) and pull comp leaves it sharp where it rounds the convex corner into
a ~0.5 mm arc. A bend has none, and neither does a tapered tip — whose point
is convex, and which the first draft cut 1.6 mm from the ribbon_curve
golden's end (1001 → 987; the reflex test restored it). The fold rule (≥ 90°,
cut anywhere) is unchanged, so every stroke without a join is byte-identical:
whitebg, alpha, ribbon_curve md5-identical.

**What the join does.** The corner is NOT a split into two strokes. The first
draft split, and every extra stroke bought an underlay hop and a trim
(Becker 28 → 50 trims, the ENTHUSIAST benchmark 4.09 → 5.03/1k): the
sequencer enters a satin column at its free cap (Laws 27/29) and the pieces'
free ends pointed away from each other. So the chain stays **one stroke**
for sequencing, underlay and the travel web, and carries `Stroke.corners`
(apex index, which member owns). `satin_stroke` hands it to `_satin_joined`,
which sews each member as its own column and lays them end to end: the
owner — the longer member — gets a capped free end at the corner and
`_extend_to_cap` runs its column over the corner square to the artwork
edge; the other member gets a junction-style end tucking under the owner's
own corridor (`_member_corridor`, the median half-width one to three
half-widths in), exactly as a T's stem tucks under its bar. The hop between
members is the corner itself, under the owner's column when the butting
member sews first and lapped over its cap when the owner does — both are
corners the trade sews. Trims: Becker 28 → 28, Fremont 52 → 52, drone
93 → 93, ENTHUSIAST 25 → 25; benchmark **4.09 → 3.81/1k**.

**Twigs and hairlines.** A short (< 2·half) free-ended side whose tip has no
corridor (distance transform under `_FORK_TIP_FRAC` of the half-width) is a
corner twig the skeleton welded onto a stem — THERMAL's H carried a 2.3 mm
45° arm into its crossbar corner and its stem's cap tilted 45° with it
(the letterform memory's #2). It is cut off and dropped and the stem is
capped square. A short side with a cap is a tapered tip: no cut. Columns
under 1.2 × `SATIN_MIN_CROSS_MM` never join: the join rescued a 0.5 mm-wide
3.4 mm² squiggle on drone into four satin points and 79% bare fabric where
`satin_shape` had reported it empty and stage 7 had sewn it as fill.

**Measured** (`tools/satin_lean.py`; bare = polygon area outside a 0.2 mm
thread buffer of the satin runs):

| fixture | corners joined | stitches | trims | bare fabric | crosses > 45° off own perpendicular |
|---|---|---|---|---|---|
| Fremont, flag on | 10 in 6 letters | 6343 → 6365 | 52 → 52 | 3.4 → 3.2% | 3 → 3% |
| drone (THERMAL, PRECISION) | 21 in 16 | 8856 → 8803 | 93 → 93 | 2.8 → **2.0%** | 26 → **16%** |
| Becker | 21 in 4 | 4524 → 4495 | 28 → 28 | 6.0 → **5.5%** | 40 → **27%** |
| ENTHUSIAST @ 93 | 8 in 5 | 3005 → 2959 | 25 → 25 | 1.8 → 1.8% | 31 → 21% |

Digitize time +8–11% on lettering logos (`_boundary_corner_near` walks the
polygon rings per candidate apex), drone unchanged. Rendered: Fremont's E
arms and L foot meet their slabs in a butt instead of a fan; THERMAL's H
stem caps square where its cap tilted into the corner; the corners still
visible are junction fans (arm to stem at a 3-way node), which the join
does not touch — that is the `_junction_entry_mm` machinery's, and the
E's arms on THERMAL are pull-comp-sealed slots (letterform memory #1),
gate 1.

Tests: `test_an_L_corner_is_one_stroke_with_one_goldman_corner`,
`test_a_bend_of_the_same_angle_is_not_a_corner`,
`test_the_joined_corner_has_no_fan_and_no_bare_corner_square` (the L's
corner square < 10% bare, no square cross within a column width of the
apex more than 20° off its member's perpendicular — the un-joined corner
fans ≥ 3), `test_a_tapered_tip_is_not_a_corner`.
