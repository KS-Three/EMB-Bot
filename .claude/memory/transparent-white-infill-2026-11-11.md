---
name: transparent-white-infill-2026-11-11
description: enclosed_white_skip_transparent ON (Kent 11-11 "Flip ON (Recommended)", guarded rule) — transparent enclosed areas not sewn unless a hollow letter body; kanji 39 + Devanagari 5 open, Becker's 25 bodies kept; flip moves Drone tripwire sttype -0.002 + logo_alpha scorecard
metadata:
  type: project
---

Kent's sitting-2 in-fill pins (`C_kanji_seal` 28, `C_devanagari_logo` 1/5/6)
all sit in `sew_enclosed_white` "field" regions over pixels the PNG leaves
transparent (0.89-0.98; verified region by region, same stitches as 950855b).

**Alpha is not lost:** stage 4's `enclosed_colour_unknown` (>= 0.6 of the
region in one transparent component) already reaches `plan_enclosed_white`.
The flag reads it; no new threshold.

**On alpha art EVERY enclosed area is transparent by construction**, so the
plain rule = "Sew white areas OFF on alpha art". It drops Becker's five white
letter bodies (transparent in `becker_marine_logo.png`, sewn by the pro) on
all 5 pairs, e.g. hat large 16,262 -> 8,350 st. Kent 11-11, verbatim: "Guarded
rule (Recommended)": keep an area that is itself lettering (`_is_letter`).

Guarded, measured: 6 of 21 Commons rows move (kanji 29,505 -> 10,945 st,
devanagari, pixel sprite, heraldic crest, neon d counter, isometric hole);
pro pairs: only Drone (one 0.85 mm2 speck). Becker identical x5. Tagger
disagreements by eye: 0 letter bodies opened, 1 non-letter kept (a crest
mantling gap tagged lettering; its mirror twin opens).

**Flipped ON 11-11** (Kent, after 7 source|OFF|ON pictures: "Flip ON
(Recommended)"; he did not pick "fix the crest gap first"). Built OFF in #1395,
flipped in its own PR. Refines the 10-27 "Every job" white recipe: every job
still sews white; only transparent areas stay open. Moved outside the 7
designs: Drone's tripwire sttype kappa 0.376 -> 0.374 (tolerance 0) and the
scorecard's logo_alpha (160.7 mm2 ring hole open) + drone_render rows, both
needing a CI capture. No golden or md5 pin moved. Pre-flip value:
`conftest.WHITE_2026_11_11_OFF` in `PRE_FLIP`; the 10-27 snapshot holds False.

**How to apply:** a test about `sew_enclosed_white` on alpha art spreads
`WHITE_2026_11_11_OFF` if it means the old behaviour. Doc
`docs/transparent-white-infill-2026-11-11.md`; tool
`tools/transparent_white_ab.py`. Related:
[[enclosed-white-like-pro-2026-10-23]], [[white-recipe-every-job-2026-10-27]].
