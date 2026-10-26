---
name: lane-census-2026-10-25
description: lane census (W3-09): 4 of 14 pro jobs reach flat (all Becker), 8 gradient, 2 photo_scene; 6b as written = the button's file; kappas a wash. KENT RULED 2026-10-26: 6b NOT built, the button stays
metadata:
  type: project
---

**KENT'S RULING, 2026-10-26 (relayed by the foreman session), verbatim: "Don't build; keep the button
(Recommended)".** The option as he saw it: auto stays the default, and "Sew as flat art" stays the manual fix,
because the kappas give no reason to switch and flat costs trims on most jobs. He ruled from this table and four
sheets (Golden Tee, Fremont hat, Drone, Becker beanie). **6b is ruled NOT built; the button stays.** Do not
propose a 6b / "route by consequence" build again without new evidence the census could not see (edges, colour
placement). Plan 2026-09-08's PR 6b, the open ruling DOCTRINE 2026-09-30 names, is answered.

`digitizer/tools/lane_census.py` (2026-10-25/26, engine `d36ff80e`, doc `docs/lane-census-2026-10-25.md`).
Auto vs forced flat ("Sew as flat art") vs Kent's 6b as written vs the planner's variant, at the Studio's
request, each pro job at its pro width and garment, judged against the pro's DST. Evidence for Kent's open
6b ruling (plan 2026-09-08 PR 6b). Built nothing, changed no routing (gate 2).

**What it found** (14 committed pro jobs; ProSeal measured locally, not in the doc):
- **The question does not shrink.** Flat 4 (all ONE logo, Becker, at 76.5-101.9 mm), gradient 8, photo_scene 2
  (Tires, MFab hat). Per distinct art: 1 flat, 7 gradient, 2 photo_scene of 10. The old "every real logo at
  80 mm is gradient" / "6 of 7" is a width-specific reading and no longer holds.
- **6b's gate fires on the 8 gradient jobs, shut on the 2 photo_scene** (its text says "gradient-class").
- **6b as written == forced flat, byte for byte, on 7 of 8** (Drone: 42 stitches apart). The class kept "for
  reporting" changes nothing that is sewn, so 6b and the planner's variant are one decision.
- **Against the pro's file: a wash.** Thread kappa and stitch-type kappa move at most 0.08, mixed sign
  (7 usable thread pairs; Gaulke x2 and Tires are DEGENERATE, one joint label, excluded). cc on Fremont
  0.60 -> 0.63 (8 words). Flat sews more trims than auto on 8 of 10 jobs (median +7).
- **Cones no longer separate the routes**: nothing over 6, flat changes none (Golden Tee's 24 under 12 is gone).

**Why:** the instruments score conformance to the pro's stitches; they cannot see edges or colour placement,
which is what Kent ranked forced flat on (2026-09-30). The ruling rests on the sheets, not the kappas.

**How to apply:**
- Before proposing 6b, quote the byte-identity table: building it OFF is "press the button when the ramp gate
  refuses a non-photographic gradient design", on 8 of 14 jobs; Tires and MFab hat stay with the button.
- To measure a lane question, run `python -m tools.lane_census premise` first: it stops at the region-former
  dispatch (minutes), the full run is an hour or two. Same-class-and-gate as the full run on 14 of 14.
- **Traps:** (1) `forced_class="flat"` on a job stage 0 already calls flat is byte-identical to auto: it is
  not an arm there. (2) The 6b arm is a shim around four names in `digitizer_core.pipeline` for one `with`;
  it is not an engine edit and must stay that way. (3) After `origin/main` moved mid-run (#1098 stage 0,
  #1057 three flags ON) all 36 rows were re-measured: no LANE moved, every file did. A census names its sha.
  (4) `heredoc` Python written through the Bash tool turns `"\\n"` into a real newline: use Edit.
- Rows not committed: ProSeal (art on Kent's box) and Bridge (no pro file on this machine). Never commit them.

See [[word-legibility-reach-2026-10-25]] (cc), [[border-census-2026-10-23]] (the pair registry),
[[pro-intake-2026-10-25]] (the job list).
