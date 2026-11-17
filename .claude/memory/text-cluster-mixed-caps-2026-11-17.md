---
name: text-cluster-mixed-caps-2026-11-17
description: To a T's small A = 3 patches because the row (T, T 11.9 mm; o 7.2; A 7.7) never tags (0.8 height link); `text_cluster_mixed_caps` OFF cures it (3 TOAT better of 44) but tags a gradient icon's bands as lettering; flip withdrawn 11-17
metadata:
  type: project
---

2026-11-17, prime grader scorecard (TOAT hat and beanie: small A a clump, counter
shut). **Not a thread limit:** the pro's A is two level-crossed legs, an open gap, a
short crossbar. **Cause:** the A was never lettering: `textcluster`'s letter door
links glyphs only within `LETTER_HEIGHT_RATIO` 0.8 of each other's height; the row is
T, T, o, A, so two pairs form and none reaches `MIN_CLUSTER_MEMBERS` 3.

**Flag** `text_cluster_mixed_caps` (`textcluster._mixed_caps`, OFF, PR #1637):
leftover candidates re-cluster at `HEIGHT_BAND_MIN` 0.6. A line that tags only this
way is marked and keeps its DRAWN size (`small_text._drawn_size_only`; the first
build's re-set grew a phone screenshot's "Photo" to 2x).

**The trap, 11-17:** Kent said "Flip ON" on "3 better, 4 no visible change, 0 worse
across 44". With it ON, CI's `test_borders_last` repro test failed: on
`repro_gradient_white_icon` six of the icon's gradient bands (34-645 mm2) were tagged
as LETTERING and reordered a block. The census had called that design "no visible
change" by eye; the sewn picture hid a wrong TAG. **A flag that changes tagging needs
the tests that read tags run before a flip question, not only pictures.** Flip
reverted; the bound (admit only what the door's own glyph test admits, and need a
tagged or pairable letter in the row) is the follow-up. Pictures:
`docs/renders/text-cluster-mixed-caps-2026-11-17/`. Related: [[prime-grader-2026-11-17]].
