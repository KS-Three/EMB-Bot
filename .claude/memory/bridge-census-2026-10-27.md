---
name: bridge-census-2026-10-27
description: Bridge hat+LC through 14 pro rules on main 8341d1f7: 8 AGREES, 4 N/A, 2 CONTRADICTS (border_by_size fields, proSized LC); ours' text is a reach gap (2 folds vs 35 on the hat), not a rule contradiction
metadata:
  type: project
---

`docs/bridge-census-2026-10-27.md` (worker session of the 2026-10-27 director, main `8341d1f7`, `script_strokes` ON).
Bridge hat (63.3 mm) and LC (76.6 mm) digitized once each, read beside his DST by one reader per row, numbers only.
Rules checked: corner fold, inside stagger, text lean, border_by_size, border_from_outline + line-art guard,
small-text floor, fine_bars_satin, outline_loop_mitre, proSized, sew_enclosed_white, bay mouth, tie_in_off,
cut_every_jump (premise), silhouette_underfill (premise).

**What it found**
- **CONTRADICTS 2.** `border_by_size`: ours rings both fields (8.2 and 10.0 mm, 1.6 mm), the pro sews them bare; the rule's
  own comment already names Bridge bare. `proSized` on LC: box 64.5 mm against his 76.6 (-15.8%); hat fits (+1.1%).
- **AGREES 8, N/A 4.** Pro folds Ls (35 / 39 folds), staggers at 0.20 depth with no pile, raises 2.0-2.8 mm text to
  5.0 / 5.5 mm, cuts all 19 needle-up moves, locks 1 of 48 starts, sews 17 of 17 contained pieces on their ground; the
  line-art guard reads both Bridge outlines as line art (outline kappa -0.05 -> 0.00). N/A: text lean (script is the
  letter door's refusal), fine bars (no bar), loop mitre, enclosed white (no white thread).
- **Where ours is far from him is reach, not a rule.** Folds on text and anchor 2 / 20 against 35 / 39, zones 0 / 9
  against 37 / 31; 14 uncut needle-up moves per file against 0; 7 of 96 starts read locked against 1 of 48;
  bare-fabric trims 4 / 4 against 0; stitches 9,419 / 14,861 against 6,650 / 8,535.

**Why it matters:** Bridge's "mixed" kappas are mostly not the rules failing. Ours quantizes the blue text into teal,
green and yellow pieces that never reach the Column lane's folds and zones (art redrawn by him, no bowl, no waves).

**How to apply:**
- Quote the table before proposing a Bridge rule; do not call a reach gap a contradiction.
- Re-run: mirror his files under a `PRO_PARITY_ROOT` as `border_census.PAIRS` names them, one digitize each under one
  CPU slot take (commands and the six drivers are in the doc's appendix; the drivers are not repo tools).
- **Trap:** `TaskStop` on a slot waiter killed its shell but not the `bash` subshell and `python` it had spawned; the old
  waiter survived, took `cpu.lock` the minute CPU freed and ran a second digitize into the same cache beside the new
  one. After a HOLD, list the processes (`Get-CimInstance Win32_Process`, by command line) before starting again.

Related: [[border-from-outline-line-art-guard-2026-10-25]], [[border-by-size-2026-10-23]], [[garment-size-like-pro-2026-10-26]], [[script-strokes-2026-10-26]], [[tie-in-off-2026-10-22]], [[cut-every-jump-2026-10-21]], [[layering-census-2026-10-26]].
