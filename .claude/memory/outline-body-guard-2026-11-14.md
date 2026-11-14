---
name: outline-body-guard-2026-11-14
description: group_consistent_outline_body's guard (flag still OFF, Kent "G4 alone looks the best") - the vote's width tie-break needs one side wider by more than MARGIN, else no verdict; redraw's re-fit had tipped MFab hat 113.5's small line to bodies on a 3.4% width gap, riders 12 -> 0
metadata:
  type: project
---

Kent held `group_consistent_outline_body` OFF on 2026-11-14 ("G4 alone looks
the best"): beside `outline_redraw_k` 0.75 it turned MFab hat's small line
(113.5 mm, the Studio hat config of `test_underfill_small_size`) into thick
white loops over its black letters. Each flag alone reads clean. See
[[group-consistency-2026-11-13]] and [[jag-source-2026-11-13]].

**Traced, not guessed.** These were the same in all four arms (body OFF/ON x
redraw None/0.75): the finish-stage vote, `find_art_outlines`' kept bodies,
and the white-keyline-art verdict.

The break is at stage 7's own vote (`pipeline` `find_art_outlines` ->
`outline_side`) on a 9-letter line:
- Without the redraw, the ink reads 2.54x to the ladder side, so it decides
  "not bodies".
- The re-fit moves two letters' own readings, and the ink falls to 1.46x,
  inside `MARGIN` 1.5.
- The width tie-break then decides "bodies" on 1.336 vs 1.292 mm, a 3.4% gap.

So 5 of 8 and 3 of 4 small letters became keyline bodies. Their words read
"mostly bodies", so `silhouette_underfill.find_riders` found 12 riders -> 0,
and the last black block was lost (B/W/B -> B/W, 22,785 -> 20,256 stitches).

**Guard (`group_consistency.outline_side`):** the width tie-break needs one
side wider by more than `MARGIN`, the module's own bar for evidence. Without
that, there is no verdict and each letter keeps its own call. The unit test's
widths moved from 1.5x apart to 1.75x apart, because exactly MARGIN is no
longer enough.

**Measured:**
- MFab 113.5 with body + redraw + guard is identical to redraw alone
  (B/W/B, 22,785 stitches, 19 trims).
- AHORA keeps its fix (O and ! fill like AH): ink decides it at 3.42x, and
  the tie-break is never reached.
- Across all 21 pro and corpus sheet designs (shipping flags, body ON), AHORA
  is the only vote, so the guard changes nothing else.
- Sheets: `eye_pairs_out/body-guard-1114/`.

**How to apply:** a vote that goes to a tie-break is a near-tie. Hold the
tie-break to the same evidence bar as the main rule, or a 1% geometry change
upstream flips the whole group.
