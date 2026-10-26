# Cuts inside one piece: where they come from, and the fill-section fix (2026-10-25)

Queue item W4-01. PR #1072 (`docs/sequence-like-pro-2026-10-25.md`) measured
that sew ORDER is not why we trim more than the professional; construction
is, and the largest construction gap was cuts INSIDE one sewn piece: 84 ours
against 25 his over five hats. This page reads where those cuts come from,
on both sides, and measures the fix built for the biggest class:
`cfg.extra["fill_section_travel"]`, built OFF.

## Instrument

`digitizer/tools/inpiece_cuts.py` (new, pinned by `tests/test_inpiece_cuts.py`).
It uses `tools/sequence_pro.py`'s piece rule unchanged -- a TRIM between two
penetrations of one connected footprint (every needle-down segment a thread
wide, opened 0.6 mm so a lone run line does not join two bodies) -- so its
totals are #1072's `trims - inter_trims`.

- **Ours:** every DST command is attributed to the plan run that emitted it
  (`stitches.iter_machine_commands` re-walked with the run alongside; the
  stream reproduces the DST's trim count exactly on all ten arms), and each
  cut is classed by the runs either side, underlay and travel standing for
  their own shape's top stitching: `fill_section` (one shape, fill both
  sides), `satin_split` (one shape, satin both sides: a split satin
  restarting, usually stroke to stroke via its next underlay),
  `satin_fill_section`, `edge_cap` (the `__edge_cap__` run tier),
  `shape_to_shape` (two shapes whose thread touches), `same_shape_other`.
- **The pro:** his DST has no shapes, so each cut is read by the stitch
  character of the twelve penetrations either side: satin (steps reverse),
  fill (long parallel steps), run (steady 1.2-3.2 mm), `?` (tiny satin).

Jobs and arms as #1072: Fremont hat 92.5 mm, Becker hat large 101.9, MFab
hat 104.9, Precision Drone 62.6, Gaulke roofing hat 114.2; hat preset; the
Studio's request (`tools.pro_pair`), stages 0-4 once per job and
`plan_stitches` per arm. Tree: `main` c531c7b8. `off` = main's defaults;
`cut` = `trim_bury_under_later` + `cut_every_jump` (#1072's arm); `on` /
`cuton` = the same with `fill_section_travel`.

## Where the cuts inside a piece come from (main, `off`)

| job | ours | fill sections | satin split | satin/fill | edge cap | shape to shape | other | pro | pro, by stitch character |
|---|---|---|---|---|---|---|---|---|---|
| Fremont | 36 | **23** (13 fill, 10 underlay, all the field) | 0 | 0 | 1 | 12 | 0 | 1 | satin>? 1 |
| Becker | 7 | 0 | 5 | 1 | 1 | 0 | 0 | 1 | satin>run 1 |
| MFab | 27 | 0 | 18 | 0 | 5 | 3 | 1 | 3 | satin>run 3 |
| Drone | 31 | **12** (5 fill shapes) | 13 | 1 | 3 | 2 | 0 | 20 | satin / small satin / run, no fill |
| Gaulke | 8 | 0 | 4 | 0 | 1 | 3 | 0 | 0 | -- |
| **total** | **109** | **35** | **40** | 2 | 11 | 20 | 1 | **25** | **0 fill** |

(Ours is read from the stream; the DST reader agrees on all but MFab, 26
against 27, one penetration landing a pixel either side of a piece edge.)
The `cut` arm: 89 (Fremont 17: fill 11; Becker 10; MFab 23; Drone 28: fill
12; Gaulke 11). #1072's 84 was read on main a7a7259f; main has moved
(`border_from_outline` and `small_text_cap_reach_edges` ON, #1070).

**The pro never cuts between two sections of one fill** -- every one of his
25 has satin on at least one side: letters touching inside a word (Drone's
small text is most of them) and a satin column restarting. So the biggest
class by EXCESS is fill sections (35 ours, 0 his); satin splits are 40 ours
against at most 25 his.

### How the pro gets from one section to the next without a cut

He does not have sections. Fremont's field is ONE piece, ONE section, zero
cuts: rows near-vertical, swept left to right, and the HOTEL FREMONT letters
are NOT knocked out -- the field is filled under them and the white letters
are sewn on top. That is `silhouette_underfill`'s construction (built OFF
2026-10-24, its note reads Fremont's ground covering 0.92 of its outline),
not a routing trick. We knock the letters out of the field with horizontal
rows, which forks the rows round every letter into 84 sections.

On Drone, `silhouette_underfill` ON takes the cuts inside a piece 31 -> 21
(fill sections 12 -> 10) and trims 106 -> 95, the same session's run.

### Why ours cut between sections

A spy on `stage6_fill.stitch_shape`'s `emit` (every lift it makes, with the
shape and the ground) on Fremont and Drone:

- **Underlay (Fremont 10).** `edge_lattice` walks every hole's ring as its
  own path; the hop from one ring to the next has no route `travel_path` can
  find -- straight crosses a letter, and its rings are the shape's OUTER
  inset only. 22 of 22 such hops have a geodesic inside the shape within
  `travel_path`'s own length budget, and the fill sews over all of it.
- **Fill (Fremont 13, Drone 12).** 54 fill lifts on Fremont, 60 on Drone,
  almost all "no route" (only 4 are `fill_bridge_cut` lifts). A geodesic over
  ground still to sew exists for 4 of the 54: the needle finishes a section
  walled in by fill already sewn and by holes. On Fremont's horizontal rows
  nearest-first sews the wide bands above and below the letters first, and
  each gap between letters is then an island. That is the ORDER of the
  sections, not the router.

## The fix: `cfg.extra["fill_section_travel"]` (OFF)

`digitizer_core/fill_section_travel.py`, called from `stage6_fill`; read in
`pipeline.plan_stitches` (a context var), so `config.py` and
`stage7_sequence.py` (#1057's files) are untouched -- the single line is
`pipeline.plan_stitches`' `with fill_section_travel.enabled(cfg)`.

1. **Routing.** Where `travel_path` finds no route, or only one lying on
   finished fill past its tolerance, `bridge` looks for one: FILL under the
   footprint of the paths not sewn yet (the next sections' rows), touching
   finished fill only inside the footprint of the column it leaves (two
   rows); UNDERLAY anywhere inside the shape inset by `TRAVEL_INSET_MM`.
   Proposed on a raster (`MCP_Geometric`, as `_bury_route` does), decided
   exactly -- every leg tested against the shape and the allowed ground.
   `travel_path`'s own length budget; a hidden route always beats one that
   shows.
2. **Order.** A planner on a raster: take a section the needle reaches under
   rows still to sew (within the budget, and never further than the travel a
   cut is worth at `_score`'s rate, 25 x 2.5 mm), leaving by an end from
   which another is still reachable (one step of lookahead over the six best),
   preferring sections whose sewing leaves the rest connected (articulation
   points last) or the nearest -- both are planned. Each plan is priced by
   `_order_cost` with the routes above and kept only if `_score` prices it
   cheaper AND it cuts no more AND lays no more thread on finished fill than
   the incoming order (gate 3: the planner may not buy cuts with exposure even
   where the rate would). The last path is pinned: the shape exits where it
   did, no other shape moves.

Fill only under `fill_travel_under_cover` (what knows the fill already laid;
default ON); two-pass fills are not planned.

## Result: OFF | ON | pro

Trims, cuts inside a piece and needle-up moves left uncut are read from each
DST with `tools/sequence_pro.py`; fill-section cuts with `tools/inpiece_cuts.py`;
exposed travel (travel no later thread covers) with `tools/travel_cover.py`;
bare thread with `tools/hairline_travel.scan` (the chaining benchmark's
instrument). The pro's DST has no travel runs, so those two read n/a.

| job | side | trims | inside a piece | of which fill sections | needle-up uncut | exposed travel mm | bare thread mm | stitches |
|---|---|---|---|---|---|---|---|---|
| Fremont | off | 51 | 36 | 23 | 171 | 45.8 | 0.00 | 18,563 |
| | **on** | **41** | **26** | **13** | 171 | 45.8 | 0.00 | 18,572 |
| | cut | 44 | 17 | 11 | 0 | 45.8 | 0.00 | 18,598 |
| | cut+on | 44 | 17 | 11 | 0 | 45.8 | 0.00 | 18,626 |
| | pro | 20 | 1 | 0 | 0 | n/a | n/a | 17,067 |
| Becker | off / on | 19 / 19 | 7 / 7 | 0 / 0 | 5 / 5 | 14.0 / 14.0 | 0.00 / 0.00 | 8,056 / 8,056 |
| | cut / cut+on | 22 / 22 | 10 / 10 | 0 / 0 | 2 / 2 | 14.0 / 14.0 | 0.00 / 0.00 | 8,080 / 8,080 |
| | pro | 9 | 1 | 0 | 0 | n/a | n/a | 12,356 |
| MFab | off / on | 64 / 64 | 26 / 26 | 0 / 0 | 15 / 15 | 27.4 / 27.4 | 3.77 / 3.77 | 11,855 / 11,855 |
| | cut / cut+on | 69 / 69 | 22 / 22 | 0 / 0 | 0 / 0 | 27.4 / 27.4 | 2.23 / 2.23 | 11,962 / 11,962 |
| | pro | 18 | 3 | 0 | 0 | n/a | n/a | 17,568 |
| Drone | off / on | 106 / 106 | 31 / 31 | 12 / 12 | 47 / 47 | 35.2 / 35.2 | 4.63 / 4.63 | 14,077 / 14,077 |
| | cut / cut+on | 114 / 114 | 28 / 28 | 12 / 12 | 4 / 4 | 35.2 / 35.2 | 1.24 / 1.24 | 14,184 / 14,184 |
| | pro | 58 | 20 | 0 | 0 | n/a | n/a | 14,552 |
| Gaulke | off / on | 32 / 32 | 8 / 8 | 0 / 0 | 16 / 16 | 19.6 / 19.6 | 9.02 / 9.02 | 7,881 / 7,881 |
| | cut / cut+on | 47 / 47 | 11 / 11 | 0 / 0 | 0 / 0 | 19.6 / 19.6 | 0.20 / 0.20 | 8,005 / 8,005 |
| | pro | 41 | 0 | 0 | 0 | n/a | n/a | 6,138 |
| **five jobs** | off | 272 | 108 | 35 | 254 | 142.0 | 17.42 | 60,432 |
| | **on** | **262** | **98** | **25** | 254 | **142.0** | **17.42** | 60,441 |
| | pro | 146 | 25 | 0 | 0 | n/a | n/a | 67,681 |

OFF is byte-identical to main on all five jobs and both arms (DST md5,
`off` and `cut`), and on the unit fixtures (`tests/test_fill_section_travel.py`).
What ON buys is Fremont's field's underlay: its ten ring-to-ring hops are
sewn inside the field (+9 stitches net). The other four jobs have no underlay hop the flag reaches and
no fill order the gate lets through, so they are unchanged. On the cut arm
`trim_bury_under_later` already buries those hops, so cut+on = cut.

## What it does not do, measured

- **The fill order loses to the gate on these five jobs.** A looser first
  build (bridges allowed `travel_path`'s 2.5 mm on finished fill, plans kept
  on `_score` alone) took Drone 106 -> 99 DST trims (inside a piece 31 -> 24)
  and Fremont 51 -> 40, but `tools/travel_cover`'s exposed travel rose 35.2 ->
  43.0 mm and 45.8 -> 46.6 (bare thread unchanged): the planner bought cuts
  with thread on finished fill, which `_score`'s weight-2 rate allows and
  gate 3 does not. Offline on Drone's three holed fields the two plans found
  10 -> 3 cuts (one field 3 -> 0) and on Fremont's field 12 -> 9, each order
  laying some thread on finished fill or, on Fremont, travelling 259 stitches
  for 3 cuts (86 per cut against the 25 Kent ratified). With the strict rule
  none survives: what ON buys is the underlay.
- **Fremont's 12 remaining field cuts are the knock-out construction.** The
  pro's field has no sections to travel between. Copying that is
  `silhouette_underfill` (and its row angle), not routing.
- **The cut arm already buries Fremont's underlay hops** (`trim_bury_under_
  later`), so `cuton` = `cut` in trims there.
- **Satin splits (40 ours, <= 25 his) are the next class**, then the edge
  cap (11, his 0) and shapes touching (20).

## Exposed travel and the bare-thread floor

- Five jobs, `tools/travel_cover` (travel with no later thread over it) and
  `tools/hairline_travel.scan` (thread on bare fabric): ON equals OFF on every
  job (table above).
- The chaining benchmark (`tests/test_chaining.py`'s `_thread_bare_mm`),
  flag OFF -> ON, chain links OFF / ON:

| tree | benchmark | full_back | left_chest |
|---|---|---|---|
| main c531c7b8 | 3.93 -> 3.93 / 3.93 -> 3.93 | 4.75 -> 4.75 / 4.75 -> 4.75 | 0.00 -> 0.00 / 0.00 -> 0.00 |
| #1057 head 177be6b6 + this diff | 5.17 -> 5.17 / 4.12 -> 4.12 | 8.88 -> 8.88 / 7.55 -> 7.55 | 0.00 -> 0.00 / 0.00 -> 0.00 |

Trims and stitches are identical too: the benchmark fixtures have no fill
the flag reaches. (#1057's own reading is higher than main's on both art
fixtures with the flag OFF; that is #1057's, not this flag's.)

## Runtime

`plan_stitches` seconds, OFF -> ON, on a machine shared with other sessions'
runs (so a few-hundred-second swing is load, not the flag): Fremont 504 ->
630, Drone 637 -> 533, Becker 60 -> 198, MFab 495 -> 820, Gaulke 366 -> 405.
The cost is real but bounded: the planner prices up to two candidate orders
per holed fill that still cuts (one geodesic raster map per step, six more
for the lookahead, inside a window of the travel a cut is worth), and the
bridges are memoized per shape. Fremont's field is sewn twice per plan (the
Column lane sequences once lane-OFF), so it pays twice.

## Reproduce

```
cd digitizer
python -m tools.inpiece_cuts hotel_fremont_hat precision_drone            # ours (main) beside the pro
python -m tools.inpiece_cuts hotel_fremont_hat --extra fill_section_travel=true
python -m pytest tests/test_fill_section_travel.py tests/test_inpiece_cuts.py -q
```

Render: `docs/renders/in-piece-cuts-2026-10-25/fremont_field_off_on.jpg`,
the field colour's sew path (blue early, red late, X a cut), OFF beside ON.
