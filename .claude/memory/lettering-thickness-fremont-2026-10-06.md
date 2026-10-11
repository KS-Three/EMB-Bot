---
name: lettering-thickness-fremont-2026-10-06
description: Kent's "HOTEL FREMONT letters are waaaay thicker than the original" — the file is at the pro's width (ours 1.23 mm at 80 mm vs the pro's 1.40 at 92.5, both ~1.7x the 0.76/0.81 mm artwork stroke); the pro's own DST loaded in the Studio renders at the SAME weight. What is really worse than the pro: outer-rail pitch on curves (0.53 vs 0.33), serif/junction fans, edge hair 1.62 vs 1.33
metadata:
  type: project
---

# The letters are not thicker than the pro's; the preview shows the compensated column (2026-10-06)

Kent, 2026-10-06: *"the lettering is wobbly, not clean and just very
inconsistent ... compared 'Hotel Fremont' to the original logo and the letters
are waaaay thicker than they should be."* Measured on `main` cf9f89f1, the
service PID started 2026-10-05 21:25 on that tree, the Studio's own job
(80 mm, left_chest, max_colors 6) and `digitize()` direct — identical.

**Width, in the file (satin cross width, `satin_columns._crosses`):**

| | artwork stroke | sewn column | ratio |
|---|---|---|---|
| ours, 80 mm pique (0.3/side) | 0.76 mm (DT), 0.70 from pixels | **1.23** med, p90 1.29 | 1.6x |
| ours, 92.5 mm canvas (0.2/side) | 0.88 | 1.15 | 1.3x |
| ours, 371-px copy, 80 mm | 0.62–0.82 | 1.06–1.28 | ~1.7x |
| **pro's `HOTEL FREMONT .DST`** (patch, 92.5) | 0.81 | **1.40** med (≥1 mm pop. p10 1.30 p90 1.50) | 1.73x |
| pro's HAT DST (cap, 92.6) | 0.81 | 1.40 | 1.73x |

The pro widens thin lettering by ~0.3 per side on twill AND cap, tiny tagline
0.30 → 0.80 (a floor), bars 1.04 → 2.4. Wilcom's documented pull comp is per
side (0.2 cotton … 0.4 fleece), the same meaning Python uses (`_push_rails`
pushes each rail by `pull`); the JS engine's `/2` is the odd one out — the
plan's §7 "2x ambiguity" is settled by the pro's file and Wilcom's docs, no
sew-out needed.

**The decisive test:** the pro's DST uploaded as a Design file in the Studio,
same 244% zoom, renders HOTEL FREMONT at the same bold weight as ours
(`fremont_studio_ours_vs_pro.png`, sent to Kent). The Studio draws the file's
compensated column plus 0.4 mm thread; nothing simulates the pull. **And the
Original view on the digitize lane is mis-scaled** — `fitRect(iw, ih,
placement)` draws the artwork ~30% larger than the stitched rect, so the flip
the help text recommends compares different sizes.

**What IS worse than the pro, by instrument (ours 80 mm vs pro at matched scale):**
- Edge hair (raw silhouette perimeter / 0.5 mm-smoothed): **1.62 vs 1.33**, per
  letter 1.48 vs 1.21; 65% of it mid-column, concentrated on curves and
  diagonals (O, R bowl, N). NOT rail jitter (|dev| med 0.025 vs the pro's
  0.041, p90 0.19 vs 0.16) and NOT lean on stems (9.5° vs 8.1°; a symmetric
  zigzag's inherent lean is atan(pitch/2w) ≈ 9.7° for ours, 7.3° for the pro).
- **Outer-rail pitch on the O: 0.53 mm vs the pro's 0.33** (inner 0.38 vs
  0.19). `_rail_points`' refinement leaves any station interval ≤ 1.3 × pitch
  (0.52) alone, so a ring's outer rail sits right at that band. The pro holds
  the outer rail dense and short-stitches the inner (22% narrow crosses).
- Trims: ours 7 trims + 7 jumps over 12 letters; the pro 12 sequences. Equal.
- Bare artwork: 0.1% (the T's junction 0.14 mm²). Coverage is not the issue.
- Per-letter cross-width CV 0.04–0.07 (≥1 mm) vs the pro's 0.08. Not
  "inconsistent" by the file.

**Why:** every width instrument said "equal to the pro" while the screen said
"way too thick" — the screen was showing both files honestly and Kent had only
ever seen the pro's on cloth. Load the reference file into the same view
before blaming the engine for a look.

**How to apply:** when a complaint is about WEIGHT, render the pro's file in
the same viewer first. The levers that are real: a sewn-width preview or an
aligned Original view (display), the outer-rail pitch band on curves and the
serif/junction fans (engine). Pull comp per side stays; a per-fabric table
(0.2–0.6) against the pro's flat 0.3 is a gate-1 question, not a bug.

Scripts (session scratchpad, not committed): `measure_fremont.py`,
`pro_band.py`, `rail_jitter.py`, `render_raw.py`. Related:
[[letterform-fidelity-2026-08-26]], [[rail-wobble-is-the-models-floor-2026-09-21]],
[[lost-frac-is-two-metrics-2026-09-20]], [[hotel-fremont-fine-details-2026-09-02]].

**Kent flipped `satin_outer_rail_pitch` ON the same day** (PR #650). Price
in the suite: 19 movers, all re-pinned with their mechanism except the two
lettering coverage bars (0.2908 vs Kent's 0.29) — the denser outer rail
closes the overshoot instrument's ribbon scallops, +0.009 of ink; Kent
raised both to 0.30 with that reason, the bar's second attributed move, and
the test says a third means rebuilding the instrument. Goldens re-captured on the WSL box with the pre-change
proof because the token had no `workflow` scope for CI's re-capture job; CI
judges. On Windows the suite stays at its standing three reds.

**The serif fans, same day (`satin_join_square`, built OFF, lane
`claude/serif-junction-fans`).** The join was already there — the arm owns
its slab's corner — and the fan was the owner's bent spine samples under
the house angle. Straightening each member's corner end on its own line:
Fremont fan ends 7 → 5 (E 2 → 0), stitches and trims identical. Two traps:
a turn-rate fan count read the PRO at 45 (its letters are one needle path,
every serif corner a 90° turn), so read lean against the local rail normal;
and a synthetic L does not fan at all — the fixture had to be the real E,
byte for byte (a 3-dp rounding decomposes differently). T-shaped slabs
(the E's middle arm) are a cap by the twig rule and stay a fan: next.

**Where this sits (2026-10-07 morning):** #650 (outer-rail pitch, ON)
MERGED. #651 (Sewn width toggle) open, auto-merge armed. #653
(`satin_join_square` ON + `satin_slab_serifs` built OFF) open on lane
`.claude/worktrees/serif-junction-fans`, auto-merge armed; the join-square
flip moved no golden (byte-identical, no WSL re-capture needed); the full
ON suite ran overnight (`sf_suite_on.log` in the session scratchpad) and
its movers are the owed read. Kent's flip on the slab flag is the next
prompt; the E's and F's middle arms (which the 10-06 entry named as the
T-slab case) do NOT move under it — their slabs are too small to grow a
skeleton half — so if he wants those, it is a different construction.
**Trap that cost half a session:** `satin_shape` skeletonises
`_close_seams(poly)`, not `poly` — probe strokes through `satin_shape` (or
on the closed polygon), never with a bare `extract_strokes` on a stage-5
polygon; the M fixture built that way reproduced a defect the shipped
engine does not have. Main checkout holds ANOTHER session's uncommitted
memory note (letterform-priors-lane); do not pull or touch it.

**Follow-up, 2026-10-08 (lane `claude/join-square-tslab`).** The E's
middle arm at 80 mm is not a slab at all: it ends in a chamfered square cap
whose corner its spine hooks into (render). Built OFF as its own flag,
`satin_free_end_square`: a hooked square free end is laid square, and a slab
off a free end is sewn as its own column (`_free_end_reading`,
`_attach_slabs`; fixture `testdata/fremont_H_slab_feet.json`). Numbers on
top of the join-square default: the PR's census. See DOCTRINE 2026-10-08.

