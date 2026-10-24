---
name: small-text-floor-2026-10-24
description: The pro's small-text floor -- every line drawn under ~3.2 mm re-set to ~4-4.6 mm bold satin, every line >= 5 mm sewn as drawn, never run/bean/dropped; #1029's re-set never reached ProSeal (design edge, mid-line A, split word); `small_text_cap_reach_edges` OFF reaches it
metadata:
  type: project
---

2026-10-24, L8, follow-on to [[small-text-reset-2026-10-21]] and
[[small-bold-columns-2026-10-21]]. Doc: `docs/small-text-floor-2026-10-24.md`;
tool `tools/small_text_floor_census.py` (one reader on both DSTs, its own
`register` without the y-flip -- Fremont's hexagon registers upside down at
IoU 0.98 with it).

**His floor:** nothing under ~3.2 mm is sewn as drawn: ProSeal tagline 3.0 ->
4.55 (hat) / 2.6 -> 4.0 (beanie), Drone 2.2 -> 4.25, Fremont 1.85-3.0 -> 4.15-4.95,
columns 0.86-1.26 mm, gaps 0.05-0.2. Lines >= 5 mm sewn as drawn (x1.02-1.11).
No run, no bean, no drop anywhere. Only exception: Golden Tee's 0.86 mm TM sewn as
a 2.35 mm RUN (we drop it -- never traced). No line drawn 3.2-5.0 mm in the corpus.

**Why #1029 missed ProSeal:** `no_room` / `design_edge` -- the placement asked the
0.8 mm CLEARANCE HALO to fit in the design box, so a line on the design's edge can
never grow; SPRAY's A traces in its own thread and blocked its own line; the beanie's
COATINGS is two interleaved clusters, and word clusters 1.3 mm apart collide through
two halos. Built `small_text_cap_reach_edges` (OFF, only under the re-set): ProSeal
hat 3.15 bean -> 4.35/4.45 satin (pro 4.55), beanie 2.8 -> 3.65/3.7 (pro 4.0);
Fremont and Drone DSTs byte-identical OFF/ON.

**Traps:** a census crop must use EACH arm's own `ours.json` blocks (a joined letter
changes block order: the bar rendered black). Tagging a joined letter with its
cluster's tags changed nothing on ProSeal (byte-identical) -- the joined A's poor
construction is downstream in stage 7. Our columns 0.70-0.73 vs his 1.1-1.26 is
stroke weight: gate 1.

**How to apply:** before tuning a re-set constant on a line, run `enlarge_small_text`'s
report (`skipped` / `blocked_by`) -- a line the re-set never reached looks like a
tuning problem.
