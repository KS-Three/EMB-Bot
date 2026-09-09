# Serifs as their own columns, and a junction cover sewn as satin under the arms — item 5, PR 2

**Status: IN BUILD 2026-09-09, Kent's pick after #434. Two flags, both
DEFAULT OFF and byte-identical off: `cfg.satin_serifs` and
`cfg.satin_patch_junctions = "satin"`.**

#434 measured what the wide band buys and what stops it: MARINE at 100 mm
goes satin at −13% stitches and comes out fanning and crossing at the
letters' feet (251 self-crossing pairs, 6.3–6.5 mm terminal crosses at the
A's foot), 3–5 strokes and 4–7 trims per letter against the pro's ~2, and
drone's admitted wing leaves 7 mm² bare inside itself. The renders
(`docs/renders/wide-columns-2026-09-09/`, and `letter_Sf62099db.png` /
`letter_Sa587cbf9.png` here) say why: every stem ends as a CAPPED FREE END
sitting above a slab serif, so `_extend_to_cap`'s terminal cross fans out
to the serif's corners; and the junction blobs are covered only by the
"modest overlap of the arms". The pro's M (`pro_marine_M.png`) sews each
serif as its own short column across the foot and each stem as a plain
column ending on it.

## 0. What already governs this — read before changing the plan

- **When thread is missing at a junction, sew the hole — do not tune a
  cross** (DOCTRINE 2026-09-06): four cross-length knobs were measured and
  none moved Becker's crotch; `cfg.satin_patch_junctions` (tatami, appended
  at the end of the shape, +0.25% corpus-wide, over-fires on one fixture)
  did. Its two rules stand: patch to `preflight._UNCOVERED_MIN_PATCH_MM2`,
  the grader's own floor, and PROVE the fix through the instrument that
  reported the defect. Kent's reasons it is OFF — the tatami sheen against
  satin, and the needle hopping to the end — are exactly what a satin patch
  sewn FIRST addresses.
- **A junction is a cluster, not a pixel** (#433): the graph the cover
  works on is the clustered one; the K's crotch is 9.0 mm² there.
- **The Goldman join** (`_split_sharp_corners`, `Stroke.tuck_under_*`,
  `capped_*`): the owner of a corner runs through and is extended, the
  other member butts in. A serif is the same idea turned round: the serif
  column owns the foot, the stem ends on it.
- **"Free" in the skeleton is not the same as capped by the merge**
  (`extract_strokes`' stub filter). A serif column is a new stroke with
  both ends free; a stem's end that now stops on a serif is neither free
  nor at a junction — it is FIXED, a third kind, and `satin_stroke` has to
  know it (no trim, no extension, no fan).
- **Goldens re-capture on ubuntu-latest with the pre-change proof.** Off is
  byte-identical, so none move in this PR.

## 1. The gap

MARINE's M at 100 mm (`wide_columns` on): 3 strokes. The left stem's end
is capped 2.4 mm above a 7.5 mm serif foot; the top-left serif is welded
INTO the diagonal's stroke through a 135° turn; the right stem's top is a
cluster of four corner forks. The R: the stem and the leg both end capped
above serifs; the bowl/leg junction is a 3-arm node with the crotch under
it. Across the corpus, `tools/letterforms.py` (this PR) counts the capped
ends that sit above a flare and the junction nodes with bare cells within
their blob.

## 2. Why the current pipeline cannot do this itself

`_prune_spurs` removes the serif's corner twigs as it removes any flat
cap's, so by the time strokes exist a serif is indistinguishable from a
square end — and `_extend_to_cap` then does the only thing it can, run the
stem's column to the outermost edge and let the terminal cross reach the
corners. The junction cover exists only as tatami appended last.

## 3. The design

**Serif columns** (`cfg.satin_serifs`), a pass at the end of
`extract_strokes`: at every free end of every stroke, probe the polygon
across the stroke's end tangent — the chord at offsets from the skeleton's
end toward the cap. A serif is a flare: the chord widens past
`_SERIF_FLARE × (stroke width)` within `_SERIF_DEPTH_WIDTHS` of the cap and
stays wide to the cap, and its thickness (cap minus flare onset) is at
least `SATIN_MIN_CROSS_MM`. Then: a new `Stroke` across the flare at its
mid-thickness, tip to tip, both ends free and capped (it is a column with
two flat ends), and the stem's spine cut or extended to the flare's inner
edge plus a small overlap and marked FIXED there. Stems sew before serifs
(`extract_strokes` sorts longest first, and the serif is on top, as in the
pro's M).

**Junction cover** (`cfg.satin_patch_junctions = "satin"`): the same bare
regions `_uncovered_patches` finds (the grader's floor, the same grow), but
each sewn as a satin column along the patch's principal axis and placed
FIRST in the shape's runs, under the arms. `True` keeps today's tatami
appended last, byte for byte.

## 4. What it should move — predictions, to be tested

- MARINE at 100 mm with `wide_columns` + both flags: the feet stop fanning
  (crossing pairs 251 → under 50), strokes per letter close on the pro's,
  trims do not rise beyond one per serif, uncovered worst stays under
  1.5 mm².
- Becker at 80 mm: the K's crotch 9.0 → 0.0 through preflight's own
  `ARTWORK_UNCOVERED`; drone's wing 7.0 → 0.0.
- No fixture's `coverage_max` rises past `COVERAGE_WARN_UNITS`; stitches
  within +2% where the flags fire; byte-identical where they do not.

## 5. Instrument first — `tools/letterforms.py`

The serif census (capped ends with a flare, per fixture and size, with the
flare ratio and thickness) and the junction census (nodes with bare cells
in their blob), plus `--compare` for OFF/ON on stitches, trims, crossing
pairs, coverage and uncovered.

## 6. What must not regress, with its fixture

- The flat-lane goldens and pushcomp pins — off byte-identical.
- The E fixture's Goldman corner (`test_satin.py`), the T fixture's tuck,
  the ribbon's taper (no flare at a taper: the chord NARROWS).
- `test_wide_columns.py`'s apex and Becker-bend pins.

## 7. Size and staging

| PR | content | size | gate |
|---|---|---|---|
| 2 (this) | serif columns; the satin junction cover; the census; MARINE and Becker measured | ~300 lines + tests | none — geometry; flipping either flag is Kent's on the render |
| 3 | polygon-native medial axis with a millimetre-scale significance prune | large | goldens move |

## 8. Decisions for Kent

- Flip `satin_serifs` and the satin patch on together with `wide_columns`,
  or keep all three OFF until a sew-out of MARINE.
