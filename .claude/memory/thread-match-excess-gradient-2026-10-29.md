---
name: thread-match-excess-gradient-2026-10-29
description: "2026-10-29 — defect 28 re-measured on 44ecf1cb: 14/52 F entries carry a THREAD_MATCH_POOR block (7 gradient fixtures, not the 09-06 seven); `thread_match_excess_gradient` built OFF (against Kent's 09-10 raw ruling) takes them 14 -> 4, md5s identical; gaulke is B 76, no thread finding; clamp priced, not built"
metadata:
  type: project
---

# Gradient lane on the excess yardstick — 2026-10-29

Kent asked (2026-10-29) for defect 28 to be fixed. Re-measured first on main
44ecf1cb (52-entry scorecard matrix, Windows). **The F wall moved:**
gaulke left it (B 76, no thread finding), `region_blobs` routes photo now,
and `gradient_ramp_radial` (F 34) and `logo_hotel_fremont` (F 16/28) joined.

**Built OFF: `cfg.thread_match_excess_gradient`.** It has one reader,
`preflight._thread_match_findings`. ON, the traced class `gradient` scores on
`_excess` like the photo route. Plan md5s are identical OFF/ON on all 52
entries. ON takes the F entries carrying a thread block 14 → 4 and the
score-0 entries 10 → 2. **Flipping it re-makes Kent's 2026-09-10 ruling**
(gradient stays raw, because a logo's cone can be bought), so the decision
is his. The survivors are real: fremont's `0020 Black` at dE 100 with White
loaded, summit's `0111` band, and the photo stub.

**Gaulke's "unexplained seventh" was the bimodal-median failure twice:**
first stage 4's re-snap mask (09-07), then the grader reading anti-alias grey
under kept roof lines (fixed 10-08 c2161d9c, reproduced by grading the plain
re-read). Do not quote 63.6 as live.

**Clamp:** keeping it moves 0 letters (`raw_score` already in metrics).
Printing raw moves 0 letters. A saturating curve moves 12, all on unfloored
designs. Recommended: keep. Not built.

Doc: `docs/thread-match-gradient-excess-2026-10-29.md`. Tests:
`tests/test_thread_match_excess_gradient.py`. PRE_FLIP and
`engine_2026_10_27.json` carry it False ([[flip-proof-pins-2026-10-27]]).
