# Why BECKER's C sews a stretch as fill at 80 mm under rail comp (2026-09-29)

Kent's pick after PR #557. The satin-only bare instrument (`rail_edge.bare_area`)
read the BECKER wordmark's junction bare as 1.39% → 3.80% of its satin art when
`satin_rail_comp` went on; two thirds of that is one ~47 mm² patch in the C's
bowl that is **sewn, as tatami fill**, by the junction cover (`junction_stack`
part C). These four crops are the answer to "why fill there".

- `becker_80mm_wordmark_bare_*.png` — the whole wordmark (`S118e45fc`, 689 mm²):
  red = artwork outside a thread's width of any satin cross, grey = sewn by satin,
  green = the strokes' spines. Grown polygon (rail comp OFF) 44.3 mm² red;
  artwork rails (ON) 90.1 mm² red on the satin-only reading, 58.5 mm² once the
  cover's fill is counted as cover.
- `becker_80mm_C_bowl_*.png` — the C's bowl at 60 px/mm: blue = satin crosses,
  green = the cover's fill, grey = underlay, magenta = spines, dots = stroke ends
  (hollow = free).

**What the crops show.** The C's bowl is a blob about 8 mm across inside a
letter whose strokes are 1.8–2.4 mm wide — wider than the 5 mm satin ceiling
any column can span. On the GROWN polygon the medial axis happens to route a
short connector stroke through the blob's middle, and that connector's crosses
(capped at the ceiling, 5 mm) cover the blob almost entirely: no hole, three
small satin cover patches. On the ARTWORK the medial axis hugs the bowl's outer
edge — the free-end arm's spine sits close to the outside of the curve — and
the symmetric-offset rail model places both rails at the NEARER edge's
distance, so its crosses reach the outer edge and stop the same distance short
of the inner one. Nothing else crosses the blob. The cover finds a 47 mm²
hole, wider than the ceiling, and sews it as fill, which is what part C was
built to do for a hole a column cannot span.

So the fill is the cover's designed answer to the artwork skeleton's
decomposition of a blob, not a defect in the tuck: stating the tuck's floor
and reach-in in sewn terms (this PR) restores the grown polygon's junction
clearances and takes Becker 42 → 39 trims at 80 mm, but the bowl's hole
shrinks by only 1 mm². The alternative for a blob like this is Kent's parked
`satin_patch_junctions="satin"` (item 5 PR 2), which sews such a patch as
satin columns along its long axis; whether a tatami patch inside a satin
letter reads right is a render-and-cloth question, recorded here and not
decided.

Measured on the `main` tree at bc999033 with the tuck fix applied, Becker at
80 mm, `max_colors` default. Full numbers: DOCTRINE 2026-09-29 and
`docs/scope-history.md`.
