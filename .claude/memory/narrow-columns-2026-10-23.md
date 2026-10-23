---
name: narrow-columns-2026-10-23
description: The Column lane on Fremont's grown ~4 mm letters rebuilt like the pro's patch — serif blocks absorbed into their stroke's column, junction corners read as chords past the trace's chamfers, no mitre onto a chamfer; all under `lettering_columns_small_bold`, OFF byte-identical; `tools/column_harness.py` draws before | after | pro per word
metadata:
  type: project
---

2026-10-23, follow-on to [[small-bold-columns-2026-10-21]] and
[[small-text-reset-2026-10-21]]. Renders and numbers:
`docs/renders/narrow-columns-2026-10-23/` (README, table.md, one sheet per
word, the before/after constructions as JSON).

**Read the pro first, as needle paths, not thread.** The patch DST's EAT
STAY PLAY drawn as lines with needle dots (`tools/column_harness.py`'s
reading of `small_text_columns.read_blocks`) shows the construction the
thread render hides: every stroke ONE column with crosses square to it; a
serif is never its own piece — the T's stem zigzag just widens through its
foot, the E's arm crosses grow taller at the tip, the A's legs end in wide
flat crosses; the S one curved column whose inner rail bunches at the curl
(the pro's S fans there too); a centre-run underlay down each stem (the
`short-col-underlay` lane's subject, not this one's).

**What ours did at the same flags** (cap 4.0 / gap 0.25 / bold 1.45 /
stroke 0.85 / small_bold ON, 92.5 mm Hat, 21 letters): 0 pieces unsewn and
0 station fans past 45 degrees already — #1025's floor and rescan had
cured the 10-20 note's dropped bars and starbursts. What was left was
construction: 74 columns for 21 letters, every slab serif a 1-1.5 mm2
block of its own with a cut, a travel and a knot where the stem turned to
meet it; a T whose bar was never cut through (stem sewn up into half the
bar, crosses along the bar); a 3-5 cross mini-fan at every chamfered
corner from `_mitre_ends`.

**Built, all under `_SMALL_BOLD` (OFF pins unchanged):**
`outline_cut._absorb_serifs` (a piece under 2.5 W2 at a straight column's
end, scanned with it along the column's axis when every cross stays under
2.2 W — an A's crossbar fails that and stays a column); `_chord_dir` /
`CHORD_W` 0.5 (a corner's edge direction as a chord over half a stroke, so
the trace's 0.2-0.3 mm chamfer at the under-bar corner no longer refuses
the through pair); `SMALL_BOLD_MITRE_SPAN` 0.6 (a mitre face must span
most of the column). Measured: columns 74 -> 55, crossed legs 13 -> 7,
trims 3 -> 1, travel 83.8 -> 59.2 mm; crosses over 1.5 W 15 -> 55 (the
widened serif crosses — the pro's foot). The S's curl and the 8/9 rings
pivot as before; THE's T gained 5 mm of travel and one trim.

**Traps:** the harness swaps nothing — to get a BEFORE from an older
engine, `git show <ref>:…/outline_cut.py > outline_cut.py`, run
`--save-runs`, `git checkout -- outline_cut.py`; every engine test you
run meanwhile tests the OLD file (cost me one misread fixture).
`corners()` gathers turn over W/8 only and with one sign, so a convex
chamfer before a concave corner is never folded into it — hence the chord.
A synthetic chamfered stem never mitred even OFF; the mitre fan needs the
real grown letters.

**Why:** the pro's construction is visible in his needle paths at 120
px/mm and invisible in a thread render. **How to apply:** before tuning a
lane rule on small text, draw both files' needle paths side by side
(`column_harness --out DIR`); judge layout there (Kent 10-22: layout is the
preview's, only pull needs fabric).
