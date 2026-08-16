---
name: real-artwork-parity
description: 2026-08-15/16 — real customer artwork put the honest baseline at 42.5, and a pro scores only 75-84 against a pro, so 95 is above the metric's ceiling
metadata:
  type: project
---

Kent supplied 7 real customer artworks on 2026-08-15 (covering 15 designs, in
`G:\My Drive\EMB-Bot\Embroidery Files`). Before that, every pro-parity number had
been measured on artwork **reconstructed from the pro's own stitches** — the engine
was graded on an input derived from the answer.

**Honest baseline: 42.5 / 100**, chance-corrected, measured in an isolated
worktree. Reconstructed artwork was flattering the engine by **11.3 points**.

**The 95 target is above the metric's own ceiling.** Scoring two of the pro's OWN
files for one logo against each other, a professional scores **75-84 against a
professional**. So `42.5/95` is NOT a 52-point engine deficit, and `direction`
(20 points) ceilings anywhere from 0.11 to 0.85 between two jobs by one digitizer
— it measures a choice, not a standard. Target deliberately left at 95 because
n=2; growing that sample needs scale-normalised registration in `scorecard.py`.

**The load-bearing pattern:** synthetic references have flattered this codebase in
four independent places — stage 0's flat/gradient gate (calibrated on fixtures
reading <0.0006, real logos read 0.205-6.135), `stage6_blend`'s ramp gate
(synthetic ramps fit r2 = 1.000, real content ~0.1), the parity corpus itself, and
the `direction`/`sttype` weights. **Getting more real customer artwork is the
highest-leverage non-code action available** — one real gradient example is what
blocks the classifier recalibration.

Kent tabled gradient work on 2026-08-16 in favour of non-gradient artwork first.

Full trail: `docs/handoff-2026-08-16.md` indexes everything. Two standing rulings
went into MASTER_SCOPE (the ceiling, and measure-parity-in-a-worktree). See also
[[windows-goldens-fail-locally]] and [[emb-bot-digitizer]].
