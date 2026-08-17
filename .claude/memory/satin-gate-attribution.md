---
name: satin-gate-attribution
description: 2026-08-16 — the DT regularity term is what loses the pro's satin ground; a promotion path on `explained` moved the corpus 45.8 to 48.1, and the sub-1mm width floor is disproved for flat art
metadata:
  type: project
---

Branch `claude/satin-gate-attribution`, 3 commits, **not pushed, no PR** — Kent's
call. Full trail: `docs/satin-gate-attribution-2026-08-16.md`; spec at
`docs/superpowers/specs/2026-08-16-satin-routing-gate-attribution-design.md`.

**What was wrong.** `is_satin_candidate` was three rejection gates with no path
back to satin (MASTER_SCOPE live defect 5). Measured on 15 real customer designs:
**63.6% of the pro-satin ground we sew as fill is rejected by the DT REGULARITY
term**, at a median miss of 0.05 past its own 0.5 limit — a taper, serif or script
stroke spreads the medial-axis radii without being any less of a ribbon.

**Loosening the limit does NOT work** — recovers 625 pro-satin cells, leaks 439.
Same for the width cap. The placement defect is real.

**What fixed it:** two statistics off the distance transform already computed.
`explained` = area / (spine length x width) — ribbons 0.85-0.94, the serrated disc
0.11-0.13, and it moves the OPPOSITE way to `2*area/perimeter` under boundary
noise, which is what makes it safe. Plus an `elongation` floor of 10, because
`explained` alone (0.974) promotes the enthusiast_logo star into the documented
starburst. Promotion reopens the regularity term ONLY, never the width cap.
**Corpus 45.8 -> 48.1**, 8 designs better, 1 worse (`bridge_lc`, unexplained), 5
unchanged. No golden churn; suite failure set unchanged.

**Two corrections worth keeping:**

1. **The sub-1mm satin width floor (live defect 2) is disproved for FLAT art** —
   61 of the 64 sub-1mm satin shapes are ground the pro also satins. It stands for
   the photo lane where it was measured; not built.
2. **The classifier is no longer the binding constraint.** An oracle knowing the
   pro's answer per shape scores 76.6% against our 55.4% — but 48% of graded cells
   sit in shapes under 75% one type, i.e. **our regions straddle the pro's
   satin/fill boundaries. That is segmentation.** Also: "call everything satin"
   scored the same 55.4% the shipped classifier did.

**Method notes.** `PRO_PARITY_FORCED_CLASS=flat` (added to `prep_all.run_ours`)
is what gets the 10 stage-0-misrouted designs to the satin/fill ladder at all —
see [[real-artwork-parity]]. `prep_all` now records each region's polygon WKT so
`tools/pro_parity/gateprobe.py` can re-ask the classifier's question without
re-running stages 0-4. Measurement worktree left at
`C:\Users\EE-LT-11030\Personal\EMB-Bot-satingate` (outside `.claude/worktrees/`).
