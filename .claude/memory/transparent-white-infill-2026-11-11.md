---
name: transparent-white-infill-2026-11-11
description: enclosed_white_skip_transparent (built OFF, guarded rule Kent picked 11-11) — transparent enclosed areas not sewn unless a hollow letter body; kanji 39 + Devanagari 5 open, Becker's 25 bodies kept; plain rule would drop them all
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

**How to apply:** default OFF; a flip is Kent's call from the pictures
(`eye_pairs_out/transparent-white-1111/`, gitignored). Doc
`docs/transparent-white-infill-2026-11-11.md`; tool
`tools/transparent_white_ab.py`. Related:
[[enclosed-white-like-pro-2026-10-23]], [[white-recipe-every-job-2026-10-27]].
