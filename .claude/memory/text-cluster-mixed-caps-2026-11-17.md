---
name: text-cluster-mixed-caps-2026-11-17
description: To a T's small A sewed as 3 patches, counter shut, because the row (T, T 11.9 mm; o 7.2; A 7.7) never tagged: letter door links within 0.8 height; `text_cluster_mixed_caps` re-clusters leftovers at 0.6; ON 11-17 (Kent "Flip ON"); 3 TOAT jobs better, 4 no visible change, 0 worse of 44
metadata:
  type: project
---

2026-11-17, prime grader scorecard (TOAT hat and beanie: "the small A is a clump
of mixed-direction stitches, counter all but closed").

**Not a thread limit.** The pro's A (hat DST, read stitch by stitch) is two
level-crossed leg columns, a narrow open gap and a short crossbar.

**Cause (a stage, then a number).** The A was never lettering. `textcluster`'s
letter door links two glyphs only within `LETTER_HEIGHT_RATIO` 0.8 of each
other's height; "To A T" is T, T (11.9 mm), o (7.2), A (7.7): the T's pair, the
o and A pair, no pair reaches `MIN_CLUSTER_MEMBERS` 3, nothing tags, and the
generic satin folds the A's left leg over the apex into a fan. Tagged by hand
the column lane sews it as the pro does.

**Flag** `text_cluster_mixed_caps` (`textcluster._mixed_caps`): glyphs no
cluster took cluster once more at `HEIGHT_BAND_MIN` 0.6, 3+ tag. A line that
tags ONLY this way is marked `meta["text_cluster_mixed_caps"]` and keeps its
drawn size: `small_text._drawn_size_only` skips it in `enlarge_small_text` and
`restore_small_text`, and `regularize_text_clusters` never redraws it.

**Trap, the first build:** without that exemption the small-text re-set grew
the phone screenshot's "Photo" (ascender over x-height) to twice its size.
Excluding lowercase-ascender lines was NOT the answer (TOAT holds a lowercase
o): skip the re-set instead. Zero worse after.

**Census (44 designs):** 9 pro jobs + 9 other pro rows + 26 fixtures at the
Studio request (80 mm left chest): 7 move. TOAT hat and both beanies better; drone_render,
repro_gradient_white_icon, golke screenshot, mfab_lc no visible change. Pictures:
`docs/renders/text-cluster-mixed-caps-2026-11-17/`. **Kent 11-17: "Flip ON
(Recommended)"**; PR #1637; OFF arm `TEXT_CLUSTER_MIXED_CAPS_2026_11_17_OFF`.
Related: [[prime-grader-2026-11-17]].
