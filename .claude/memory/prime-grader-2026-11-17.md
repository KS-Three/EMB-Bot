---
name: prime-grader-2026-11-17
description: "Kent 2026-11-17: Claude's grade of a render is 'almost SPOT ON', so a session's eye is the standing grader (tools/prime_grader.py, nightly, magnifier tiles); first run weak vs his old pins (kappa 0.29 n 6, 9/41 at 3 mm); color_cap_least_loss built and flipped ON from it"
metadata:
  type: project
---

**Kent, 2026-11-17:** the computed yardstick is "sub par"; "When I ask claude to grade the image it is almost
SPOT ON". He chose: grader + magnifier, "Claude reads nightly", closed loop as a dev tool only. This replaces
the 11-14 "no nightly run"; flips stay his.

**Built (PR #1613):** `digitizer/tools/prime_grader.py` (`capture`, `kit`, `record`, `scorecard`, `kent`),
rubric `prime_grader_rubric.md` pinned by sha, `docs/prime-grader/` (scorecards, README, RUNBOOK). Kit per
design: overview (original | ours | pro), tiles at 30 px/mm with a mm ruler (original patch placed by a
silhouette fit), travel picture. One fresh blind subagent per design; about 950k tokens a run for 9 designs.

**First run against Kent's 11-10..14 marks:** grades linear kappa 0.29 [0.00, 0.47] n 6, all within one step
but 7 of 9 "Okay"; his gross pins at 3 mm 9 of 41 vs 0.14 chance (0.09 above); 28 of 41 within 8 mm. NOT
shown to land on his spots. His marks are on tree 950855bf; the readers saw 3608ef63. A fair test needs both
on the same renders: RUNBOOK section B, a sitting on his machine (he said yes; not done as of this note).

**Nightly:** a fresh scheduled session had no push access to the repo (07:47 UTC 11-17, stopped in a minute).
The schedule now fires into the session that built the tool. If that session is archived the run stops; the
lasting fix is a routine made in the claude.ai UI with the repo selected.

**Fix from the scorecard:** Precision Drone "no blue thread". The colour cap kept the 6 largest threads (four
greys). `color_cap_least_loss` (PR #1625): least sewn area x dE00 squared, guarded (incomer chroma >= 25 and
>= 20 dE00 from every kept thread; outgoing thread has a nearer kept neighbour). Unguarded it made
summit_badge worse (a grey took the lavender). Guarded: 2 of 35 runs move. Kent: "Flip ON (Recommended)".
Still open on the Drone: the navy sky is black from stage 2; "A" of AND a shade darker than "ND".

**How to apply:**
- The first run's nine readers were started with no `model`, so they ran on the session's own model: a
  breach of [[agents-cheap-models-2026-11-02]] (that note had not been read). RUNBOOK A.3 now requires the
  worker model on every reader. The 11-17 card and later cards are different instruments.
- Kent heard "stop trying to make a formula imitate Claude" as mean. Lead with what he asked for; do not
  frame his ask as a mistake.
- Golden Tee's scorecard faults are what `bevel_ring_fold` (his 11-14 tickbox, OFF) cures: not a new fault.
- To a T's speed lines still sew heavy with `fine_bar_survive` and `border_from_outline_hairline_run` ON;
  cause not traced.
- A new typed `PipelineConfig` field needs `tests/engine_2026_10_27.json`; a tool that names a `.md` needs
  `tests/test_tools_console.py` (`NAMES_ONLY`). CI caught both.
Related: [[vlm-judge-100-2026-11-06]], [[eye-first-diagnosis-2026-11-13]], [[bevel-ring-fold-2026-11-13]].

- **2026-11-18:** kit renders flat-ended (butt) strips (`stitchviz.render_design(caps="butt")`, kit-only) after readers called round-cap bumps "saw-toothed"; rubric 2026-11-18 adds "what the pictures cannot show truthfully". Next card is the first under it, not comparable with earlier.
