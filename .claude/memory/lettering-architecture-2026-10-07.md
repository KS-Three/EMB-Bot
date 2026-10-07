---
name: lettering-architecture-2026-10-07
description: Why auto-digitized lettering is poor (five failures by letter size, A patchwork is the construction MODEL — skeleton-derived rails — not any flag), the outline-cut spike re-run on today's main polygons (holds; E and bowls still fan), the survey (every vendor and both patent families take rails FROM THE OUTLINE), and the lettering-lane architecture: one tagger → letterform priors → word size policy → outline-cut Column objects → the font engine's construction
metadata:
  type: project
---

# Lettering: the architecture, not another flag (2026-10-07)

Kent asked why lettering digitizes badly and what architecture a professional
result needs. Full report: `docs/lettering-architecture-rd-2026-10-07.md`;
renders `docs/renders/lettering-rd-2026-10-07/`.

**What it is, measured on `main` 32b0dd3 at corpus sizes:** Becker MARINE
6–9 satin columns and 7–9 trims per letter, angle concentration 0.20–0.58
(pro: one path, one angle); enthusiast's clean 1400 px wordmark the same, so
it is not resolution. Fremont's taglines (2.6 mm caps, 0.27 mm strokes)
sew as bean tubes round the outline. Gaulke's 4.4 mm caps all sew now but
choke their counters. Bridge's tagline is 10–13 source px tall = 2 mm caps:
a SIZE problem, not segmentation.

**Five failures by letter size:** A patchwork (stage 6 model), B tube letters
(tier policy + the gate-1 column floor), C halo strands (stage 2/3), D blob
letterforms on 0.5–0.7 mm/px uploads (stage 1/4), E two taggers
(`text_candidate` vs `_lettering_groups`) that the flags read inconsistently.

**The outline-cut spike on TODAY's polygons** (`oc.py` from
`claude/outline-cut-columns`, untouched): becker 10.8% over-long, 5/11 its
"clean"; fremont 2.1%, 16/32 — the same as on its 135-commit-old inputs. The
month of stage-4/6 work neither helped nor hurt it. M/A/R/I/N become one
column per stroke; the E's body and the band's C/B bowls still fan (missing
cut rules, not a ceiling).

**Survey:** no vendor auto-digitizes raster text (Wilcom, Pulse, Embrilliance,
Brother, Ink/Stitch all go through a font object or user-drawn rails/rungs);
Soft Sight US6804573 (expired 2018), Viking US6934599 (expired 2023),
Ink/Stitch Fill-to-Satin, StrokeStyles 2022, Tian 2005 all put rails on the
outline and use the skeleton only to cut. Adobe US11704848 (to ~2041) claims
the medial-axis-plus-width representation today's engine builds. Small-text
numbers are universal: 0.8–1.0 mm column floor, ~5 mm cap floor, run font
at 3–4 mm.

**Architecture (proposed, nothing built):** a lettering lane whose unit is
the Column object (railA/railB/rungs — what an `.embf` glyph already is):
L1 one tagger/word model → L2 letterform priors (wired OFF on
`claude/letterform-priors-wire`; run it BEFORE the house angle) → L3 size
policy per WORD (floor value gate-1) → L4 outline-cut emitting Columns
(+ E-as-stem-plus-arms, bowl rules) → L5 the font engine's construction
(port `routeGlyph` rules to Python, or play Columns back in the Studio —
**Kent picked (a) port to Python, and L4 outline-cut Columns as the next lane, 2026-10-07**). Font ID stays dead; no learned SR. Order: L4+L5, L1, L2
order, L3 mechanism, C.

**Traps met:** `MASTER_SCOPE.md` is 14 words under budget — do not add to it
without cutting. `plan.stats` is a property, not a method. The design dict's
stitches are in 0.1 mm units. Keep `_lettering_groups` and `text_candidate`
apart in your head until L1 merges them: enthusiast's wordmark is only in the
first, its subline only in the second.

**L4 BUILT the same day, OFF: `cfg.lettering_columns`.** `outline_cut.py`
(the spike, emitting `columns.Column` stations instead of stitches) +
`columns.py` (Column, `column_runs`: `_push_rails` per side, cross floor,
`_comb_thresholds`/`_split_points`, centre underlay, nearest-next from the
needle's REAL position, the satin tier's link rule) + a stage 7 hook ahead
of the classifier gated on `is_lettering` (= `text_candidate` OR the new
`lettering_group` tag the house pass now writes) + `_sews_satin` branch so
stage 5 keeps the artwork polygon. Becker MARINE letters 34 runs / 42 trims
-> 17 / 14; enthusiast 13 -> 22 trims and Fremont 17 -> 38 WITHOUT the
Euler walk. Two traps: the engine's satin spacing is ONE cross per 0.4 mm
(the spike stationed at 0.2 and doubled every count); with an underlay the
needle ends at the column's START, so order from the last emitted point,
not from `col.end`. The local flat-lane golden on enthusiast is red on
main's engine too (one of the three standing reds). Next on this lane: the
Euler walk across a letter's columns, the E/F stem-plus-arms cut, the bowl
rule (the S), junction overlap, then Kent's pairs.

