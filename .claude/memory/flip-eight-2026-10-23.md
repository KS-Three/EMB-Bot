---
name: flip-eight-2026-10-23
description: Kent's ruling on the flip sheet 2026-10-23 — "flip the eight ON, hold two"; a layout flag is judged by its NUMBERS against the pro's file when the eye cannot tell OFF from ON at viewing size; the eight defaults (Python and JS twins), the two held OFF and why, the pre-flip pin (FLIP_2026_10_23 / TRIO_OFF)
metadata:
  type: project
---

2026-10-23. Kent read `docs/flip-sheet-2026-10-23.md` (PR #1047: ten layout
flags, OFF | ON | pro crops on Fremont 92.5 hat, Becker, MFab, with stitches,
trims and one number per flag) and ruled: **flip the eight ON, hold two.**

**The rule he applied:** at viewing size most ON crops are not tellable from
OFF (as in [[six-flags-invisible-at-viewing-size-2026-09-18]]). Where the eye
cannot tell, the flag is judged by the number it is about, read off the DST
with ONE reader for ours and the pro's: does ON move it TOWARD the pro
without a cost the pro does not pay? Layout needs no sew-out
([[layout-judged-in-preview-2026-10-22]]); only pull/comp and density do.

**Flipped ON as plain defaults (False / None is the off arm):**
`fill_turn_slant` (#1036; sub-0.5 mm stitches 2161 -> 989 on Fremont, pro
295), `trim_bury_under_later` (#1030; Fremont 51 -> 37 trims, pro 21),
`tie_in_off` (#1042; locked run starts 82 -> 38, pro 3), `small_solids_satin`
(#1023), `compact_solids_satin` (#1040), `satin_underlay_short_columns`
(#1044; short columns bare 9% -> 0%, pro 1.6%), `fill_underlay_cross` on the
hat / LC / beanie presets (#1033; the pro's crossing pass under every dense
fill), and the small-text set (#1029) **as the sheet's exact arm**:
`small_text_cap_mm` 4.0, `max_width_scale` 1.05, `min_stroke_mm` 0.85,
`letter_gap_mm` 0.25, `bold_scale` 1.45 AND `lettering_columns_small_bold`
(Fremont's small letters 2.15 -> 4.40 mm median, pro 4.25). Kent then named
`lettering_columns_small_bold` a NINTH flag in its own right ("Yes, add it to
the flip"; PR #1046's construction sits behind it, under 5 mm only). JS twins
flipped with them: `fillTurnSlant`, `crossUnderlay`, `underlayShortColumns`.

**Held OFF, and why:** `cut_every_jump` (#1035) removes every uncut jump but
Fremont's trims go 51 -> 201 against the pro's 21 — the pro buries, he does
not cut; `sew_enclosed_white` (#1031) sews MFab 45% over the pro's stitch
count (25,512 vs 17,568) — white interiors are a per-job Studio option (R11),
not a default.

**How the flip was built (the pattern for the next one):** every pin that
measured another flag on the old engine keeps measuring it there —
`tests/conftest.py` `FLIP_2026_10_23` (merged into `PRE_FLIP`),
`tools/pro_parity/flagcost.FLAGS`, the JS tests' `TRIO_OFF` dicts and
`text-lane-flags`' `OFF`; synthetic md5 fixtures take the dict, not a re-pin
(`test_trim_bury_under_later._plan`, `test_cut_every_jump.roofing_hat`).
Sew-out card tools pinning a flag explicitly (`sewout_card_cross_underlay.ARMS`,
`sewout_card_v6.GROW`, `sewout_card_v3_1`'s `small_text_cap_mm: None`) are the
OFF arms and were not touched; cards with NO pin for a flag now carry it ON in
every arm. Proof: `tools/flip_eight_proof.py` ->
`docs/renders/flip-eight-2026-10-23/` (BEFORE | AFTER | pro, counts in its
README). The eight PRs' branches that were still open (#1036, #1042, #1044)
were merged into the flip lane rather than waited on.

**Why:** eight OFF flags had stacked in one evening with the engine not
improving on Kent's machine; the sheet put the decision in front of him in one
read and he took it in one line. A flip that moves what "no override" means
must carry its pre-flip dict, or every test priced on the old engine re-pins
for the wrong reason ([[bean-holds-on-2026-10-15]]).
**How to apply:** build a layout flag OFF, render it onto the flip sheet
(`tools/flip_sheet_renders.py`, add a FLAGS row), let Kent read the row, flip
as he rules; never park it waiting for fabric.
