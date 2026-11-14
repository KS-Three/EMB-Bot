---
name: group-consistency-2026-11-13
description: Kent's "like things sewn unlike" pins traced on main — 2 of 11 tier straddles (AHORA outline body, K-Line run floor), 2 thread, 2 fill angle, 2 fixed; 4 OFF flags; outline body decided by ink; render tone follows row order
metadata:
  type: project
---

Director's hypothesis 2026-11-13: every construction call is taken per region
against a threshold, so like shapes that straddle it differ. Census by eye and
by stage-7 rung trace (`docs/group-consistency-2026-11-13.md`):

- **Tier straddle (2):** lt_ahora — `art_outline` body ratio AH 1.059, RA
  1.023 vs `OUTLINE_BODY_RATIO` 1.0 (fill under the sewn pink field's loop),
  O 0.612 / ! 0.456 satin; no text cluster fires (AH, RA fused). lt_k_line
  subline — run floor 2.25 mm2: 17 bean outlines vs 6 satin, one line.
- **Thread per letter (2):** Bridge's U (5422 vs 4531, 18.4 dE00, a cluster
  MEMBER so `stray_word_thread` skips it); (hed)p.e.'s e — AA stroke snapped
  to 1335 (2.4 dE00, art is one maroon), own region, satin vs fill.
- **Fill angle per shape (2):** emoji legs 11/180 deg, mascot feet 39/134.
- **Already fixed (2):** devanagari, kanji by `enclosed_white_skip_transparent`.

**Built OFF:** `group_consistent_tier` (run floor per line; a moved letter
skips `small_solids_satin`, which sewed W/K as one column), `group_consistent_
outline_body` (outline body test per line), `group_consistent_thread` (lone
cluster letter < 1/4 of word, <= 25 dE00, takes the word's thread, drops a
dark-ink bean its mates lack), `group_consistent_fill_angle` (like shapes
share the biggest's fill angle; satin only for `congruent_group`-tagged).
Run floor: members > `MARGIN` 1.5x off the threshold decide; band members
follow. Outline body: by INK (side with more area; close -> wider strokes).

**Wrong way first:** the margin rule made AHORA's fused AH/RA satin (lumpy);
the Director: the odd ones are O and ! (Kent's pins), decide by ink (435 vs
121 mm2) -> O, ! and its dot fill under the loop. Decide a group by what
Kent pinned as odd, not by region count. K-Line ON reads better.
**Render tone = row ORDER:** feet at one 39.4 deg, AH/RA at one 90 deg still
render as two shades: rows advance opposite ways and `stitchviz` draws each
row over the last one's shaded half. Kent's "differnt colors" was read off it.
Negative: likeness fallback on SATIN pushed To a T's mirrored pair 9 -> 15
deg apart. Flag stars are lettering-house-grouped, out of reach.

**How to apply:** a "this one differs" pin: trace the rung first
(`stitch_one` emitters wrapped, caller line number) before blaming a tagger;
the text cluster did not fire on 3 of 4 lettering logos. Related:
[[inconsistency-fault-reader-2026-11-12]], [[eye-first-diagnosis-2026-11-13]].
