---
name: pro-overlay-loop-2026-09-09
description: "2026-09-09 — Kent's real goal behind \"stitch/photo/digitizing quality\": overlay OUR digitization of the customer art on the PRO's file, catalogue differences, replicate. His ruling: replicate CRAFT only (tier, column width, direction, pitch, underlay, order/trims, cones); SHAPE decisions (filled bodies, recomposed layout, added keyline) are catalogued and put to him. Brainstorm paused before any design was approved — another session is on it."
metadata: 
  node_type: memory
  type: project
  originSessionId: 9e90971b-174b-4014-ad33-ce02654638d9
  modified: 2026-09-09T22:55:44.950Z
---

**Kent's clarified ask (2026-09-09, verbatim intent):** take the professionally
digitized DST/PES files, run the SAME source artwork through EMB-Bot, overlay
ours on the pro's, see what differs, replicate it in code.

**Kent's ruling, same day (AskUserQuestion, option 1):** auto-target only HOW
the pro lays thread — satin-vs-fill per element, column width, stitch
direction, row pitch, underlay recipe, sew order/trims, cone count. WHAT is
sewn (BECKER's filled hollow letters, Gaulke's re-composed layout, MFab's
bolder keyline — `docs/pro-parity-real-art-2026-08-15.md` §3) is catalogued
per design and put to HIM, never copied. Reason he accepted: the scorecard
already IS "match the pro" and is anti-correlated with visual quality (§5,
real art looked better and scored 12.8 lower); a pro scores 75–84 vs a pro;
yet `direction` and `sttype` sit near chance, which is the craft half.

**Why:** the loop's judge cannot be the existing score. The overlay is the
human-readable instrument phase 1 never had; Kent's eye stays the arbiter on
shape calls.

**How to apply:** when the brainstorm resumes, do NOT re-ask this. Propose
approaches that (a) reuse `tools/pro_parity/prep_both.py <slug>` (single
design works via argv), `scorecard.register()` (translation-only hill-climb,
no scale/rotation — Gaulke pins at the search edge), and
`stitchviz.render_design` (already rendered the pro's decoded PES on 09-03);
(b) add what is MISSING: a registered overlay + diff mask per design/block,
and a per-design difference catalogue joining the two-sided instruments
(`satin_columns` file+plan, `row_pitch_union`, `fill_pitch`, `sewout_card`)
with the file-only ones (`study_pro.classify`, `census_pro` recipes,
`border_pro`) — cheapest route is `export.write_dst(plan)` so every pro-file
instrument reads ours identically; (c) label each difference craft vs shape.
Start designs: Fremont patch, Becker hat large, Bridge Bar LC (the three he
reviewed 09-03). Renders are gitignored; `renders/` is not in the repo.

**Process finding, answered the same day:** superpowers specs stopped
2026-08-19 (15 specs, 40 plans vs 438 PRs; 112 PRs since 08-25 with 3
plans). Told Kent plainly: the bigger blockers are phase-1 exit (yardstick
disagrees with his eye, last verdicts 08-27 on output that no longer exists)
and nine built-but-OFF flags waiting on his call. He did not dispute it.

**State:** paused 2026-09-09 by Kent — *"I have another session working on
this exact fix, we can resume once that is completed."* No code, no spec
written. Two `digitizing-quality-auditor` agents were launched and produced
nothing usable (first stalled on pipeline runs, second was cut by the session
end) — do not count on their output. Related: [[quality-review-2026-09-08]],
[[real-artwork-parity]], [[kent-eye-vs-instruments-2026-08-27]].
