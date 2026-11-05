---
name: free-digitizer-survey-2026-11-04
description: Kent 11-04 asked why free auto-digitizers were never shared; the field surveyed (40+ tools), the three benchmark tiers, and the artwork/licence rules for running them
metadata:
  type: project
---

**The ask (Kent, 2026-11-04):** "I just presented 3 websites that have auto
digitizing that are free. Why haven't you shared these with me throughout this
entire project? ... find all of the free digitizing softwares, and identify
which ones we should be benchmarking." Full survey:
`docs/free-digitizer-survey-2026-11-04.md`.

**Why it never happened:** the six competitor docs (masters patents 08-01, Ember
x3 08-07..09, Hatch manual 08-08, DADE 11-04) each tear down ONE product; no
session surveyed the field, and until DADE no competitor engine ran on our
art. The Hatch trial (30 unwatermarked exports / 30 days) and the Wilcom
EmbroideryStudio 2026 trial (14 days, no stated export limit) were available
all along. The runnable open-source engines are 2026 projects.

**The field in one line each.** No free desktop tool auto-digitizes a raster
(Stitch Era's free edition ended July 2013; Chroma, PE-Design 11 and Embird
trials block export; SewArt's trial caps 3 colours). Web: Stitch AI
(dynamicmockups.com/stitch) previews free but its DST is gated behind a sales
call ("Machine files are access-only", measured 11-04, Tier 3 stopped after 1
job; only the operator-sheet PDF downloads); Stitchist (1 free,
$50 once), Embrowser (2 traces/week), click-stitch (3 colours, 3 in),
SewFlow Classic (tatami only) and EmbroidAI (one free download, then ~$1 each)
give a free stitch file; the rest preview free and charge for the file.
Research code: heatstitch (MIT, heatstitch.app, Rust+TS, run <1 mm / satin
<=7 mm even / else fill), openstitch (AGPL, PySide6, skeleton classifier,
/100 stitch-out score), Nuizu (Apache/MIT, `uvx nuizu dst img -s 100`),
Needler (no licence, SAM2 optional). No paper goes raster -> machine file with
code; none compares to a pro's file, so our kappa/cc instruments have no
published peer.

**Benchmark tiers proposed:** 1 = heatstitch + openstitch + Nuizu over the
corpus (free, local, scriptable); 2 = Hatch and Wilcom trials on Kent's box
(one shot each: plan the 18 tripwire pairs + spares before installing);
3 = Stitch AI while free. **Kent's pick (11-04): tiers 1 and 3 now; Hatch and
Wilcom trials after those complete** ("let's do Hatch and Wilcom after this is
completed"). **Tier 3 then died on the DST gate and Kent ruled "Drop Tier 3
(Recommended)" the same day**; its one-job notes live in gitignored
`scratch_bench/stitch_ai/notes.md`. **Later 11-04: Kent approved the Hatch 30-export
list as written** (`docs/hatch-trial-export-plan-2026-11-04.md`: the 18 pairs, 3
instrument exports for the teardown's spacing / satin-fill threshold / pull-comp gaps,
Bridge x2 + ProSeal x2, owl + Pooh, 3 reserve; Hatch's own pages say 30 AND 100
exports, the first export's counter decides) **and ruled "Skip Wilcom"**: the laptop
fails Wilcom's 60 GB free disk and 4 GB dedicated GPU requirements (39 GB free,
integrated Radeon 0.5 GB). Install waits for Tier 1 (PR #1239) to land.

**How to apply:** their files are third-party stitch files: gitignored
`scratch_bench/`, never committed without asking. Upload only public artwork
(the 18 tripwire pairs) to web tools; MFab/ProSeal/Fremont/Drone are clients'
files and need Kent's OK per job. AGPL/no-licence engines: benchmark the DST,
never read the source into ours (Ink/Stitch clean-room ruling). Compare at
the pro's size, chance-corrected (gate 4), with a render per row.
Related: [[dade-app-teardown-2026-11-04]], [[nightly-tripwire-2026-11-02]],
[[garment-size-like-pro-2026-10-26]], [[yardstick-pro-pair-2026-11-01]].

**Tier 1 result (2026-11-04, `docs/scoreboards/free-digitizers-2026-11-04.md`):**
18 committed pairs at the pro's width, engine defaults. Medians against the pro:
ours sttype kappa 0.38, **heatstitch 0.13** (0.67x stitches, needle travel
1.02x pro), **Nuizu 0.02** (4.7x stitches, a JUMP per fill row = needle-up
55x pro, 6-colour confetti on grey anti-aliasing), **openstitch 0.04** over the
8 jobs it ran (ours 0.45 on the same 8; 0 of 8 reach ours): the classifier
refused launching the downloaded exe, so Kent launched it by hand and the lane
drove its GUI (computer-use, second access request granted). Exe in
`scratch_bench/_tools/openstitch/`. None of the three beats ours; heatstitch
ties/passes on 2 of 18. openstitch's other figures, its job list and the 10
jobs not run are the scoreboard's openstitch row and section, not repeated here.
Tool: `digitizer/tools/bench_free_digitizers.py`; competitor files in
`scratch_bench/<engine>/` (gitignored, in Kent's live checkout).
