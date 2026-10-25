---
name: flip-sheet-wave2-2026-10-24
description: Flip sheet wave 2 -- four flags (#1063 monoline, #1064 under-fill, #1065 outline border, #1066 reach edges) rendered OFF|ON|pro; the tool gained per-flag fixtures, shared base OFF arms, an art fallback for G:-only jobs
metadata:
  type: project
---

2026-10-24, follow-on to [[flip-sheet-inline-2026-10-24]]. Tool changes in
`tools/flip_sheet_renders.py`: a flag may list its own `fixtures` (run and
report cross only those), flags with the same `base` share one OFF arm via
`base_name` (white_sewn = sew_enclosed_white + enclosed_white_keyline, Kent's
10-24 flips), `EXTRA_PAIRS` (proseal_beanie), `ART_FALLBACK` (MFab's corpus
crops when G: is unmounted -- MFab's counts still matched #1064 exactly), and
readers `sub_1mm`, `satin_loops`, `travel_runs`, `small_lines` (the
small-text census's own reader per listed line, pro registered against our OFF).

Unmerged flags were run from a detached local merge in the scratchpad
(`--engine`), never committed; with three PRs only MEMORY.md conflicted.

Eye at viewing size (whole design, 6 px/mm): ProSeal reach YES (2x letters);
Becker under-fill / outline border YES; MFab LC under-fill YES (white over
black); MFab hat under-fill yes, subtle (white travel streaks gone); MFab hat
outline border barely; Tires monoline NO (black on black -- its catch is trims
9 -> 32 and a stray at the e). Bridge not rendered (pro only on G:).

**How to apply:** for a flag that acts only under another flag set, give it a
`base`, and a `base_name` when a sibling shares that base, or the sheet
digitizes the same OFF twice.

**Kent's ruling from this sheet (2026-10-24), PR #1070:** `border_from_outline`
and `small_text_cap_reach_edges` ON; `silhouette_underfill`, `monoline_script_satin`
held OFF. reach_edges is INERT until the re-set itself flips (#1049 closed).
The full suite on the flip found three bugs in #1065's ON path, none of them
visible on its own OFF-default CI: empty `outline_holes` crashed the digitize
(max of []), the body fill lacked `slant_turns=`, and the gradient repro's
sweep square read as an outline (riders now excluded, Kent's 09-04 gradient
ruling). **How to apply:** a flag built OFF has never had the suite run with it
ON; the flip's full run IS its first ON test, so expect engine bugs, not just pins.
