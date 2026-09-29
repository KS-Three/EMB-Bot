# golden_tee's +65% stitches under rail comp: the seams of the on-rails polygon (2026-09-29)

Kent's pick after PR #558. `logo_golden_tee` at 80 mm sewed 6,892 stitches
with the fabric's pull grown into the polygon and 11,377 with it on the rails
(`satin_rail_comp`, ON since 2026-09-28) — the flip's largest stitch cost on
any fixture. These crops are the mechanism and the fix.

- `golden_tee_80mm_before_off_on.png` — the whole design at 12 px/mm, rail
  comp OFF (left) and ON (right), before the fix: satin blue, underlay grey,
  travel red, run green. GOLF and the tee's stem shatter into stubs ON.
- `golden_tee_O_of_GOLF_before_off_on.png` — the O of GOLF (with its stem,
  one shape) at 40 px/mm, OFF and ON: 29 → 88 strokes. The grey polygon on
  the right carries hairline slivers and internal gaps the left one does not.
- `golden_tee_T_outline_before_off_on.png` — the T's outline: 12 → 70
  strokes; a doubled stretch along the right stem and clumps at every end.
- `golden_tee_O_of_GOLF_after_off_on.png`, `golden_tee_T_outline_after_off_on.png`,
  `golden_tee_80mm_after_off_on.png` — the same three with the fix.

**What the crops show.** Under rail comp stage 5 hands satin the artwork
polygon unioned with the underlap reach under whatever sews later and cut by
whatever sewed earlier. The artwork's sub-pixel edge and a buffered or
neighbouring edge never coincide exactly, so that boundary carries a hairline
seam wherever they meet — notches, slivers and holes a fraction of a pull
wide — and the medial axis reads every seam as a branch. The grown polygon
never had them: a round-joined `buffer(pull)` swallows anything narrower than
the pull. The design went 178 → 494 strokes and 148 → 473 satin runs at half
the points each: the same columns laid three times, as stubs, at the same
0.21 mm pitch.

**The fix** (`stage6_satin._close_seams`): the skeleton reads the on-rails
polygon with the seams of its construction closed — what a half-pull closing
fills where it is nowhere wider than half a pull AND touches a stretch of
boundary stage 5 added — while the rails, caps and every art reading stay on
the polygon itself. Two wider rules were measured and rejected because they
re-cut the letterforms Kent's artwork-skeleton ruling is about (DOCTRINE
2026-09-29). With the fix golden_tee ON reads 7,966 stitches (+15.6% for the
flip's +65%), 162 satin runs and 47 trims; MARINE is byte-identical on every
shape. What remains is the artwork's own boundary, which the ruling keeps.

Measured on `main` at 89161704 with the fix applied, 80 mm, `left_chest`,
`max_colors=6`. Full numbers: DOCTRINE 2026-09-29 and `docs/scope-history.md`.
