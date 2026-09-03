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
