---
name: letterform-priors-lane-2026-10-06
description: "2026-10-06 — Kent asked for \"another agent, something new\" on lettering; the first pick (outline rails) was yesterday's live lane claude/outline-cut-columns; second pick letterform priors dispatched on claude/letterform-priors. Check sibling lanes before proposing \"new\""
metadata:
  node_type: memory
  type: project
  originSessionId: b02a2c93-3da9-4564-9d3e-51e214148b60
  modified: 2026-10-08T01:04:07.708Z
---

Kent, 2026-10-06: *"get another agent going on lettering details and cleanliness,
try something new … move a little quicker."* Main checkout was 165 commits
behind `origin/main` (fast-forwarded, clean).

**The trap this session nearly walked into:** every memory pointed at the rail
model as the ceiling ([[rail-wobble-is-the-models-floor-2026-09-21]]), so the
first proposal was "rails from the outline, rungs from the vector medial axis's
generator pairs" — and Kent picked it. One `git worktree list` later: lane
`claude/outline-cut-columns` had built exactly that the day before
(`docs/outline-cut-columns-2026-10-05.md` on that lane: rails from the outline,
skeleton only to cut; 136 letters on 7 logos; Kent at pass 3 "keep going";
second look committed 08:40 on 10-06). "Another agent" meant a SECOND lane,
not that one restarted. Re-asked with a corrected menu.

**Kent's second pick: letterform priors** — refit a text-tagged low-res
outline to lines + arcs under word-shared stem direction, stroke width,
baseline; vertex move capped at k × source pixel so clean uploads are
byte-identical. Attacks the outline-cut spike's own failure class 2 ("blob
outlines from low-res input … no cut rule fixes this": all 5 Becker band
fails, bridge). Brief:
`docs/superpowers/specs/2026-10-06-letterform-priors-design.md` on
`claude/letterform-priors` (worktree `.claude/worktrees/letterform-priors`).
Spike first, wiring is a second decision, default-OFF, his flip.

**Not picked, recorded:** text-scoped halo dissolve (defect C, 23–30% of
Gaulke's text stitches are halo; `dissolve_phantom_blends` global flag OFF,
mixed verdict); tube letters (defect B) are ROADMAP gate 1 — the width floor
is a sew-out constant.

**Spike result (PR #652, same day, 52 min of agent time):** k=0.75 × source px.
Becker 10/11 refit (merged "BEC" refused), stem spread 4.1→2.7°, outline-cut
over-long 9.3→6.2%, stage-6 bare 4.33→2.65% at +11 trims; gaulke held out
5.2→3.1%; bridge is lost at stage 2 (segmentation blobs, no outline prior
helps); drone/enthusiast/fremont byte-identical. Pro IoU neutral by number
(±0.013) — his M/E are sharp-cornered, so the arc rules were set against him.
**For the outline-cut lane:** its `oc.letter_columns` is NON-DETERMINISTIC
(same polygon, 3 calls, 2 stitch sets on 4 of 6 fremont letters) — ~0.1 pt
noise under every number it reports.

**Wired 2026-10-07 (Kent's option A), PR #654, default OFF** —
`cfg.letterform_priors_k` (None = off; module imported only inside the
branch, OFF byte-identical by WKB hash + `sys.modules` test), engine module
`digitizer_core/letterform_priors.py`, insert after stage 4 before the house
angle, per-letter outcome on region meta. #652 (the spike) had auto-merged
while the wiring sat unpushed, so the wiring is its own lane
`claude/letterform-priors-wire`. The labelled page (2 pairs: becker, bridge;
5 identical with the reason in the caption) is republished to Flag Before
After, version 11 — the publish was refused once by the auto-mode classifier
(provenance), cleared by Kent's go in chat + a whole-file Read of index.html.
The corpus gaulke is the 14 px/mm photo file (grid-capped, all pass), not the
607-px `art/` file the spike measured — two gaulkes, say which. Laptop slept
overnight: 14 arm-runs took 11 wall-hours for ~40 CPU-min; the render was not
hung (CPU-seconds moved over a 20 s window).

**Kent's ruling 2026-10-07, same day: FLIP ON, log the N.** Verdicts: becker
"after", job done yes — *"the N was better before - everything else was
better after"*; bridge "both bad" (bridge is both-bad under every flag ever
shown). The N: today's stage 6 sews the sharper refit junction as a FAN of
long crosses (the outline-cut "compound piece fanned" class) — a stage-6
junction defect, not the refit; outline-cut cuts an N stem / diagonal / stem
and cannot fan. Lesson: a cleaner outline exposes the satin decomposition's
junction weakness — when a refit flag reads worse on one letter, crop the
locator's spot before blaming the refit.

**THREE sessions ran lettering in parallel on 2026-10-06/07, and this one
found out one lane at a time.** (1) this lane (priors = **L2** of the
architecture below); (2) `claude/serif-junction-fans`: `satin_join_square`
built OFF (#653 merged), its flip ON (Kent, 10-06, on renders) + `satin_slab_serifs`
(OFF) unmerged on-lane; (3) the Column lane: `lettering_columns` built OFF
(#655 merged: `outline_cut.py`, `columns.py`, MARINE 42 → 8 letter trims) and
`docs/lettering-architecture-rd-2026-10-07.md` — a five-layer **lettering
lane** (L1 one tagger, L2 priors, L3 word size policy [gate 1 floor], L4
outline-cut → Column objects, L5 font-engine construction) whose ruling is
*"touching the skeleton model further is polishing the wrong representation"*.
So the N fan (defect 59) is a skeleton-tier defect that L4/L5 ON makes moot for
tagged text: measure it under `satin_join_square` and `lettering_columns`
BEFORE building any fix in stage 6. The flip PR (#654) merged default-OFF
before the flip commit was pushed; the ON commit + 7 pinned tests sat
unpushed on the lane for hours — push before the merge window, or expect a
second PR.

**Outcome 2026-10-07 evening:** flip MERGED (#658, `letterform_priors_k=0.75`
on main; no golden moved — becker is not a flat-lane key; 5 Becker-at-defaults
tests pinned to `None` by their files' own rule). **N fan diagnosed, NOT
built (#661, tools + docs only):** `satin_tip_caps`' `_is_tip_end` reads 3 of
the refit N's 5 junction ends as tapered TIPS (neighbour's far edge at
4.56–4.81 mm against a 4.84 mm reach = 1.6 sewn half-widths, a reach set on
the A's apex and raster corner balls) where the trace's 5 all read as
meetings; each "tip" is capped and `_extend_to_cap` runs the arm 4.6–4.8 mm
through the other stroke → crosses span both and rotate. The fifth
wrong-population threshold in this repo. Four-arm census (`tools/fan_census.py`,
over-long > 1.6 × (W + 2·pull)): becker 56 → 56 (join_square, N byte-identical)
→ **0** (lettering_columns) → 0; drone 9/9/0/0; bridge blobs 7/7/2/2. The
nameable skeleton-tier fix (gate `_is_tip_end` on node degree) halves the N's
over-long at +1.07 pt bare — Kent's choice vs the Columns tier. Trap caught:
the bare 1.6 W bar reads gaulke's pulled 1 mm crosses as fans.

**Columns sitting drawn and published 2026-10-07 (page v12), Kent's pick
over the tip-end gate.** Tree: `origin/main` 07393d71 + PR #660 (1cbef252)
cherry-picked render-only as 2a87ba89 on lane `claude/columns-sitting`
(worktree `.claude/worktrees/columns-sitting`; the gallery generator's
ARM_INTENT fix is uncommitted there, for the sitting-record PR). 6 pairs
changed, tires identical (script, no tagged text). Price OFF → ON: becker
10,976 → 7,293 st, 60 → 30 trims, letter trims 38 → 8, over-long 56 → 0;
fremont trims 58 → 63. **Two instrument traps:** `rail_edge.bare_area` reads
~44% bare under Columns on every logo — it pairs stations two by two after
`strip_splits`, a skeleton-tier run-layout assumption (Becker's N 43% vs 20%
by raw-segment union; neither checked on thread) — never quote it for the
Column lane; and what IS measured there: **Columns sew ~0.7 mm between
crosses against the satin tier's 0.4** (the Column lane's own density, a
finding for the cloud session that owns it, sent one-way). The cloud Column
session is "Digitizing tool lettering quality [164463]" — messages reach it,
nothing comes back.

**Kent's Columns ruling 2026-10-07: NEEDS WORK — confounded by density.**
becker after (job yes: "columns did its job but the before stitch density is
better"), drone after ("patterning is clean"), fremont before, bridge /
enthusiast / gaulke both bad; ruling note: "the comparison could be skewed
because of the varying stitch density". Columns sew ~0.7 mm between crosses vs
the satin tier's 0.4. **Never put an arm on the page whose density differs from
the base: equalise pitch first, or the eye judges density, not construction.**
Also 10-07: join_square flip held by four enthusiast guards (#663), cause = the
join-corner cut straightening a small S's bowl ends 0.92 half-widths; fixed
with `_STRAIGHT_MAX_MOVE_HALVES = 0.6`, flip back ON in #666 (cap refuses ~half
of all straightenings corpus-wide, unread per corner). A subagent dies on the
Fable usage limit mid-task; its uncommitted lane work survives — resume it.

**The density was a STALE RENDER, not a defect, and the redraw was done
twice.** The first Columns sitting cherry-picked #660 at 1cbef252; the cloud
session then pushed 1782fbea to the same PR (a needle every 0.4 mm per rail,
was 0.8). Kent's "needs work" was on pairs one fix behind. This session's
agent redrew (`density-1007`, PR #668: `tools/satin_pitch.py` + pins, no
engine change) while the cloud session ALSO redrew and published
`full-density` (main + #667, 7 pairs incl. golden_tee) to the same page first;
the publish here was refused as not built on the live version and was NOT
forced. Lessons: never draw a sitting from an OPEN PR of a live session — wait
for the merge; and before redrawing, read the live page (`Artifact read`) to
see whether the lane's owner already has.

**How to apply:** before proposing "something new", run `git worktree list`
and `git log --oneline main..<lane>` on every lane touched in the last two
days, and read its doc. [[concurrent-session-designed-the-same-tool-2026-09-17]]
said this already; it bit anyway because the memories describe the FLOOR and
not the lane that just started on it. `regularize_text_clusters` (textcluster.py)
already redraws rescued-door text at a shared width — build beside it.
