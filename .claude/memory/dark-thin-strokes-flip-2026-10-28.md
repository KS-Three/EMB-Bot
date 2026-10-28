---
name: dark-thin-strokes-flip-2026-10-28
description: "2026-10-28 — `keep_dark_thin_strokes` flipped ON (Kent on #1170: \"Flip ON now (worker's pick)\"); OFF pinned in PRE_FLIP / FLIP_2026_10_23 and engine_2026_10_27.json; the five gradient fixtures that move and the 30 dark reads judged against the artwork"
metadata:
  type: project
---

# `keep_dark_thin_strokes` ON — 2026-10-28

Kent's words on #1170 (the two fixes: a glyph's counter refused, a carved
ground's shades read from the tails): **"Flip ON now (worker's pick)"**. PR
#1172 flipped the one default in `config.py`; the Studio/service request carries
no value for the flag, so it rides the default. Gradient class only
(`pipeline.run_stages`): flat and photo fixtures are byte-identical either way.

**Pins (the #1165 pattern).** `PRE_FLIP["keep_dark_thin_strokes"] = False` and
the same key in `FLIP_2026_10_23` (so every "before the 10-23 flips" site on a
gradient fixture pins it off), `sewout_card_v3_1.PRE_TRUE_SIZE` (the v3.2 owl
card was cut without it), `fremont_triage` `small_glyph_keep_off`,
`flip_eight_proof.BEFORE`. `engine_2026_10_27.json` already held it `false`, so
no new snapshot. The flip's own moves (owl, Fremont patch, drone, Bridge, Fremont
webp) were re-pinned from the PR's CI run with `tools.ci_repin`.

**Sheet:** `docs/renders/keep-dark-thin-strokes-flip-2026-10-28/` (OFF = pre-flip
arm, ON = shipped default; `tools.dark_ink_flip_sheet`, which now sets both arms
explicitly and takes several `--hero` fixtures). The 30-read table (owl 16, Fremont
patch 14, each with area and an on-ink verdict) is in #1172's body.
Related: [[dark-thin-strokes-2026-10-27]], [[flip-proof-pins-2026-10-27]].
