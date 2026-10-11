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
(tier policy + the gate-1 column floor), C halo strands (stage 2/3; GONE on the 10-08 engine, 0-4%, docs/text-halo-2026-10-08.md), D blob
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
stage 5 keeps the artwork polygon. Becker MARINE letters 42 -> 8 trims WITH the
Euler walk (routeGlyph ported: span graph, postman duplication, Hierholzer,
last visit satin / earlier underpath, hops through the junction, in-letter
hops up to 2 W sewn); without it enthusiast went 13 -> 22 and Fremont
17 -> 38, with it 13 -> 11 and 17 -> 22. Three traps (the first two CORRECTED below: stations 0.4 apart with BOTH ends
down is the engine's density; the spike's 0.2 with both ends was the double); with an underlay the
needle ends at the column's START, so order from the last emitted point,
not from `col.end`. The local flat-lane golden on enthusiast is red on
main's engine too (one of the three standing reds). GitHub refuses a push to a branch whose
PR is auto-merge-armed AND dirty against main with a bare Internal Server
Error; disable auto-merge, push, re-arm. The E/F cut is the second look
reading 30-degree corners; the S was never a cut problem but shared needle
holes (the engine's `_short_stitch_guard`, now on every column). The junction tuck
(fourth step): a butting column sewn BEFORE the stroke it meets runs under it
by stage6's `_JUNCTION_TUCK_MM` + pull, capped at half a stroke; sewn after,
a plain butt to the cut line. The walk starts at a butting column's free end
(within trim_at of the needle) and the postman never pairs that node unless
nothing else is odd -- paired, it goes even and the T's stem doubled and its
bar split (caught by the reviewer agent, not by the tests). Only where half a
stroke >= tuck: on 0.96 mm strokes the reorder cost six entry trims for a
sliver. MARINE 8 -> 7, enthusiast 14 -> 12, gaulke 23 -> 26, Fremont 22.
Slanted terminals (fifth step) and the
yardstick that found them: BARE ARTWORK (polygon inset 0.15 minus 0.3 mm thread
round every satin cross) -- the straight scan dropped whole segments (an N's
diagonal, 2.1 mm2) and that now counts as over-long so the second look cuts;
`_fan_ends` fans a slanted end from the SCAN (crosses under 0.85 of the median
= the slant; a rail-walking version swept a fan across a B); the curved path's
free ends are not squared any more so DTW fans the tip. A symmetric shrink (round cap) stays
square; a fan is all or nothing. DENSITY CORRECTION the same night: the lane
sewed one end per station = 0.80 mm per rail, HALF the satin tier's 0.40 (the
engine's zigzag is A1,B1,A2,B2, both ends, stations 0.4 apart); the 'one
penetration per station' trap above was wrong. Full density: becker letters
4,709 -> 3,095 (not 1,629), trims 42 -> 8. Count needles per rail, never
totals across tiers. At 0.15 mm thread the terminals still hold: MARINE bare
3.1 -> 2.7%, Fremont 2.0 -> 0.6%. E/F stem cut 10-08: slot backs = depth
peaks along each hull pocket's outline (one pocket holds both slots when the
middle arm is short); guards: solid between backs (M's V), piece behind <=1.6 W
(MARINE's M read as an E on its side). Five E's, long crosses 4 -> 0, trims
unchanged. TRAP: outline_cut's medial_axis was unseeded (random ties, same
letter cut differently in one process); rng=0 now, like every other caller.
An A/B that moves untouched shapes is noise first. Next: Kent's pairs.

**Kent's pairs DRAWN (after #660, ahead of the E cut on the caller's word):**
`docs/eye-pairs-2026-10-07/` -- 7 pairs + tires identical, sitting tag
`columns-1007`, price table from the new `tools/eye_pairs_price.py`
(whole design, the changed shapes' own stitches/trims, fidelity rows).
Found first: `outline_cut._spine_ends` called `medial_axis` WITHOUT `rng=0`,
so the lane was nondeterministic (golden_tee 8,311-8,319 stitches run to
run); fixed and AST-pinned for every engine call. Becker letter trims
42 -> 8; lost_frac up on six of seven logos. Not published; the E is still
three slabs on the page.

**L1 BUILT 2026-10-08, OFF: `cfg.lettering_words`** -- see
`word-tagger-l1-2026-10-08`. Under it `is_lettering` reads `word_id` only.
