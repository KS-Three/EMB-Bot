---
name: edge-wobble-is-satin-rails-2026-09-19
description: Kent's "wobbly/lumpy curves" attributed by stage — on decent art the stage-4 outline is clean (0.011 mm) and SATIN RAILS wobble ~0.10 mm about it; tools/edge_wobble.py; cause undiagnosed
metadata:
  type: project
---

Kent opened 2026-09-19 with *"work on identifying shapes and outlines"*; asked
what he sees: **"right shapes, bad edges"**, wobbly/lumpy curves worst, *"it
needs to be perfect"*. Same complaint as [[kent-eye-vs-instruments-2026-08-27]].

A spike measured both halves before any build (full table: DOCTRINE
2026-09-19). On `enthusiast_logo` the polygon tracks the artwork at 0.011 mm
std; the sewn rails wander 0.071 about that polygon. On Becker (0.55 mm source
pixels) both wobble ~0.08. Synthetic `logo_whitebg` is clean on both sides —
why no suite saw it.

`tools/edge_wobble.py` (kept, 10 tests) reads plan vs polygon only. Per tier on
real logos, `main` at `24fce102`: **satin std 0.09–0.11 mm, p95 0.17–0.23,
7–13% over 0.15 mm; bean/run 0.000; fill row ends 0.01–0.02 EXCEPT Becker,
0.177 and unread** (it was 0.037 before 2026-09-19's satin flips). Worst satin
points are all INWARD dips 0.5–0.95 mm.

**The first measurement ran on a stale base** — no `git fetch` at session
start, `main` ~70 commits ahead with the same day's satin flips in it; the PR
coming up `DIRTY` is the only thing that caught it. Satin barely moved on
re-measure (so those flips are not this lever). Fetch FIRST.
`satin_rails_follow_edge` ON moves it ~10% — consistent with
[[six-flags-invisible-at-viewing-size-2026-09-18]].

**Why:** stage-4 curve fitting was the obvious build and would have moved
nothing on decent art. Second time the outline was nearly blamed for the rails
(DOCTRINE 2026-09-09).

**How to apply:** before any "edges/outline" work, run `edge_wobble.py` and
read the satin row. Open: WHY rails wobble (not diagnosed); whether 0.10 mm is
what Kent's eye sees (unproven); the low-res outline half needs registration
and lives only in the spike's description. Instrument traps (rolling median
inverts a sawtooth; turn-angle row-end test drops the wobbly ends; excuse short
stitches by the guard's step condition, not size) are in the tool's docstring.
