# The director's night, 2026-11-13 to 11-14

The night's director worked one laptop with about eight local worker sessions,
from Kent's 11-10 to 11-13 defect-marks pins. This page is that director's report
(written 04:55, updated 07:50 on 11-14), landed in the repo along with the
three reports it rests on:
- the agent-eye test against Kent's pins;
- the census of where the pro departs from the art;
- the trace of why our own steps did not adapt.

Those four reports sit gitignored in the primary checkout under
`digitizer/eye_pairs_out/` (`director-1113/`, `agent-eye-1113/`,
`pro-redraws-1113/REPORT.md` and `ADAPTATIONS.md`), and so do their pictures.
A cloud session does not have them.

Every agreement figure here is chance-corrected (ROADMAP gate 4). Counts are
counts; none is offered as an agreement rate. No flag changed: every flag
named is OFF on main unless it says otherwise.

## The answer

**There is no single switch inside the engine.** The director went looking for one and named
three candidates during the night; the workers' measurements knocked down two
of them ("What I got wrong"). Kent's pins split into many small causes, each
worth a handful of pins.

**What did work is the method.** Eight sessions did the same three things:
looked at the render beside the ORIGINAL, traced the fault to a stage, and
fixed one cause at a time. In one night that gave 11 merged PRs and five fixes
the director confirmed by eye, with no sitting and no yardstick. Kent said it
on 11-13 ("you know what the issues are perfectly fine, so why do you need me
to grade them"). The blind test below backs it, partly. See memory
`eye-first-diagnosis-2026-11-13` for the rule.

Three structural gaps came out of it, each now with code behind a flag:
1. **Nothing compared what is sewn with the art.** There is now a proof-read
   pass (`cfg.proofread`, report-only, OFF, PR #1477). It is not yet good
   enough to steer the engine (below).
2. **Like things were decided one at a time.** The letters of one word, two
   feet or two legs each took their own stitch type, thread and angle. Four
   `group_consistent_*` flags fix the cases found (PR #1478).
3. **The pro adapts the art to thread; we trace it.** He flattens bevels and
   shadows, raises small text 1.3 to 2.2 times, thickens hairlines and cleans
   blurry edges. We do some of this and miss the rest ("Where the pro departs
   from the art").

## Checked by the director's eye (render beside the art)

| What | PR | Flag (all OFF) | What the director saw |
|---|---|---|---|
| Jakarta's tagline sewn as two rows of scattered letters; its squares welded into bars | #1476 | `small_text_reset_one_baseline`, `text_cluster_solid_guard` (`cfg.extra`) | ON: one line, in order; squares separate |
| Ahora in three stitch types; the mascot's feet in two colours | #1478 | `group_consistent_tier`, `_thread`, `_outline_body`, `_fill_angle` | ON: one tone, one construction; feet match |
| Two long black threads across BECKER's white faces (Kent's "random cross over stitch" #0, #1) | #1483 | `inshape_piece_lift` | ON: both gone, nothing else moves |
| Becker's stair-stepped border (the art is 1.42 px/mm) | #1479 | `outline_redraw_k` (None = off; 0.75 proposed) | ON: straighter and more even at 3 of 4 pinned spots; still short of the pro |
| The renderer drew two tones for one thread at one angle | #1482 | none (a renderer fix) | Feet and Ahora now one tone each. Part of "different colour" was the picture |
| Bridge's eight handles all different | #1480 | `regular_structure` | ON: more alike. Modest |
| Golden Tee's bevel, shadow and layer sandwich | #1486 | `bevel_ring_fold` | ON: cleaner than OFF, still well short of the pro (two yellows, black rings; the pro's orange side band is lost) |
| Silhouette logo: mint outlines round the white letters, a green ring round the bear (30 pins, graded Bad) | #1488 | `flat_blend_band_any_scale` | ON: bear clean, ring gone, letters white and readable. Clear gain. 6 threads -> 4. Side effect: the green field's fill turns 90 degrees |
| A diagonal thread lying across MARINE's E (Becker pins #14, #15) | #1490 | `lettering_columns_connectors_buried` | ON: the thread at pin #14 is gone, nothing else moves there. Worker's count: letters' travel on their own finished satin 268 -> 44 mm over 28 designs, at +50 trims (`docs/connectors-on-top-2026-11-14.md`) |
| Everything sewn wider than the art | #1485 (open) | `pull_comp_along_stitch_only`, `growth_keeps_gaps` (`cfg.extra`) | ON: small gain only |

Not checked by the director's eye; the worker's word only:
- the apex-cut corpus render (#1489, `docs/apex-cut-corpus-2026-11-14.md`);
- the edge-blend thread work;
- the proof-read guard (#1487, open).

## Flips the director recommends (Kent's to make)

| Flag | Why | Catch |
|---|---|---|
| `inshape_piece_lift` | A plain bug: one needle-down stitch of 13.7 to 60.6 mm, where a DST record holds 12.1 mm. Only Becker and MFab have them | +1 to 2 trims per design. Becker's pinned output and the nightly tripwire's Becker and MFab rows re-baseline |
| `small_text_reset_one_baseline` + `text_cluster_solid_guard` | A lowercase line stays one line; a row of squares is not a word | Checked on Jakarta and Bukit Asam; no regression seen on Fremont, ProSeal or MFab small text |
| The four `group_consistent_*` flags | Ahora, K-Line's subtitle, Bridge's U, the mascot's feet, the emoji's legs | Byte-identical ON on `hed_p_e`, the flag, To a T, ProSeal, Becker large and Fremont. Small corpus |
| `outline_redraw_k = 0.75` | Roughness falls on all 12 low-res pro jobs (Becker by 2.8 to 3.1 degrees, the others 0.3 to 1.1); clean uploads byte-identical (#1481) | Becker bare fabric +0.07 to 0.35 mm2 at 4 of 5 sizes |
| `flat_blend_band_any_scale` | A JPEG blend rim between two inks no longer becomes its own thread: the silhouette logo and ProSeal's bar | Byte-identical on Drone, `hed_p_e` and four guard designs; only two designs show the gain |

**`lettering_columns_apex_cut`: do NOT flip as built.** It was built 10-25 and
never flipped, and it cures the Z-joint pins on and_pizza. Over the 43-design
corpus (#1489, the worker's eye) 25 designs moved:
- 10 better (Becker x5, ProSeal x2, Bridge x2, duotone);
- 10 the same;
- 1 mixed (and_pizza: the Z pins cured, one corner fans out);
- 4 worse: outline_lineart_logo badly (Kent graded it Great; line art tagged
  as text turns into long bars), k_line, Precision Drone and MFab LC.

It needs a guard, then the table re-run.

**Kent's call, no recommendation:** `lettering_columns_connectors_buried`
(#1490). Flip now, and the stray threads across letters are gone at about 2
more trims per lettering design, which puts Becker and MFab past the pro's trim
count. Or wait for a second PR that walks the travel along the stroke's edge
the way the pro does, then re-count trims (the worker's pick).

**Not recommended yet:**
- `bevel_ring_fold` as a default: partial. The worker's pick is a Studio
  "Flatten shading" tickbox.
- `regular_structure`: modest.
- The two fat-ink flags: small.
- `outline_redraw_native`: opens a seam.

## What the evidence says

### The agent eye against Kent's pins

The protocol was written before any reader ran: blind readers on 45 designs
(11 pro logos, 21 Commons logos, 9 Commons lettering logos, 4 photos). Kent's
270 pins were collapsed into 139 fault groups, 83 of them rated "ruins" or
"noticeable". Two blind readers per design looked at the ORIGINAL beside the
render. A blind text matcher decided "same fault", and position had to agree
within 4 mm.

**Verdict by its own pre-registered bar: PARTIAL.**

| | Opus reader (zoomed) | Sonnet reader (overview only) |
|---|---|---|
| Kent's gross groups found at his spot, chance-corrected [95% CI] | **0.35 [0.25, 0.49]** (32 of 83; the bar was 0.40) | 0.17 [0.08, 0.27] |
| all 270 pins, chance-corrected | 0.25 [0.16, 0.36] | 0.11 |
| same fault named anywhere in the design, corrected against another design's faults | **0.52** | 0.35 |
| grade against Kent, linear-weighted kappa (n 42) | **0.66 [0.52, 0.78]** | 0.61 [0.46, 0.73] |
| same, leaving out his Terrible designs (n 28, post hoc) | 0.44 | 0.31 |

*(measured 2026-11-13: `agent-eye-1113/REPORT.md`, `score.json`)*

By design group (Opus, gross groups, corrected):
- pro logos 0.33 [0.21, 0.48];
- Commons logos 0.41 [0.19, 0.81];
- lettering 0.43 [0.17, 0.73];
- photos: 0 of 2. Kent pinned only 2 faults on the 4 photos.

**What the numbers mean:**
- **It finds more than Kent pinned.** A model adjudicator judged 19 of 20
  sampled unmatched Opus faults real. Kent pins "the 2-3 worst" of a repeat, so
  a reader that finds another instance of the same fault scores as a miss.
- **It is weak exactly where Kent is strong.** Of the gross groups in each
  class, Opus found at his spot, with the count found anywhere in the design
  in brackets:
  - jagged edges 2 of 18 (11);
  - pen flow 4 of 21 (13);
  - wrong colour 1 of 7 (3);
  - coverage gaps 0 of 5 (0).

  It does best on merged letters, 12 of 23 (19).
- **Whole-design ticks, Cohen's kappa against Kent:** unrecognizable 0.71,
  detail lost 0.49, not for thread 0.46, too busy 0.12, colours off 0.12.
- **Opus and Sonnet agree on grades** (linear kappa 0.81) but barely on faults
  (chance-corrected 0.13), largely because the Sonnet readers did not zoom.
- **Its limits:**
  - one sitter;
  - small strata (ruins n 6, photos n 2) with wide item-bootstrap CIs;
  - the readers and Kent saw renders from older trees, not main.

  This tests finding gross faults against the original. It is not a test of
  judging a sew-out or of picking between close variants, where the session
  eye read kappa +0.34 on 11-06 (memory `vlm-judge-100-2026-11-06`).

### Kent's pins by cause

Designs affected per class, from the blind matcher's classes:
- whole design unreadable or not for thread: 18;
- letters merged, counters closed, spacing gone: 18;
- shape detail lost: 14;
- jagged edge: 13;
- element missing: 12;
- pen flow or stitch direction: 11;
- invented element: 8;
- wrong thread colour: 8;
- like things treated differently: 7.

Kent almost never says "stroke weight" (1 group), but the readers flag it on 23
designs: he files the same thing as merged letters or closed counters.
*(measured 2026-11-13: `agent-eye-1113/census_table.md`)*

**Post hoc readings by the analyst.** Each still needs a `debug_dir` stage
trace.
- **The whole-design-unreadable class is not a stitch bug.** It is photos and
  tonal or busy art (halftone, kanji brush, QR code) digitized as-is: a
  "should this be sewn" question, Phase 4 and gate 2.
- **The jagged-edge designs are not low-resolution inputs.** Their median
  input is 12.3 px/mm against 13.6 on the rest. At the Tires pin the pro's edge
  steps much like ours, so part of this class is the renderer's fill-row look.

### Where the pro departs from the art (11 jobs, 93 pins)

**45 of 93 pins (26 of 71 complaints, counting stated repeats once) sit where
the pro changed the art, we traced it, and Kent's note names what his change
fixes.** One reader, not blind, so these are counts, with no agreement figure
claimed.

The 45 by kind of departure:
- flattened shading 24 (20 of them Golden Tee);
- lettering rebuilt or raised 14;
- clean edge on low-resolution art 7;
- made regular 0.

Without Golden Tee, 17 of the other 25 sit on the three low-resolution jobs:
Becker (1.4 px/mm), MFab (3.8) and Bridge (4.4).

Of the other pins:
- 18 failed in a way the art does not show;
- 17 are construction;
- 12 sit on clean art where we added the noise.

*(measured 2026-11-13: `pro-redraws-1113/REPORT.md`)*

**We copy his additions and not his adaptations.** Over 44 departures:
- filled interiors and knockdown: copied, 5 of 5;
- lettering rebuilt or raised: traced 9 of 12;
- shaded art flattened: traced 6 of 9.

**On Bridge, the pro's "made regular" is not what it looks like:**
- **Handles.** The art's eight handles are already alike: 0.21 mm p95
  boundary distance after rotation alignment, the same as the pro's. Ours
  spread them to 0.58 mm, so our pipeline adds the irregularity. The pro's
  real change is the handle's SHAPE: spindle to paddle, with a collar nub.
- **Text arc.** Its feet are no more regular in his file than in the art
  (0.56 against 0.52 mm). His change there is size: letters 1.65 times
  taller.

**A correction to two older docs.** `pro-digitizer-rules-2026-10-21.md` §1b,
citing `pro-parity-real-art-2026-08-15.md` §3, says the pro tightened Gaulke's
mark toward its text (art 2.79:1, pro 2.35:1). Measured on dark ink only, the
art is 2.44:1 (pro 2.35, ours 2.40). 2.79 counts the screenshot's light panel
edges as ink. Treat that reading as a scale artefact.

### Jagged edges, 49 pins (PR #1479)

Of Kent's 49 smooth-edge pins:
- facets from tracing clean curves: 18 (14 on one logo);
- jag already in the art's pixels: 10;
- stitch construction: 21. Of those, 14 are satin ends that should form a
  flat edge or square corner, and they share no single mechanism.

See memory `jag-source-2026-11-13`.

### Why our steps did not adapt where the pro did

Read from code at `950855bf` (the tree of the renders) and from the run
records. Rows marked UNCONFIRMED there stay unconfirmed. *(confirmed
2026-11-13: `pro-redraws-1113/ADAPTATIONS.md`)*
- **Nothing in `digitizer_core` knows a bevel, an extrusion or a drop
  shadow.** The only flattening tools are the colour count, `merge_delta_e`,
  the design ramp and the gradient lane's blend fit, and none of them reads a
  shape's role. Golden Tee's bevel pairs sit 13.9 to 14.3 dE00 apart, far past
  the merge.
- **The small-text re-set grows horizontal lines only**, so Bridge's arc
  text is never raised (by design: the comment at `MAX_LINE_HEIGHT_RATIO`).
- **Fremont's EAT | STAY | PLAY is re-set, but what sews is bean spines
  written earlier at art size.** `thin_ink.bean_dark_ink` runs in
  `pipeline.py` before `enlarge_small_text`, and nothing clears its spines.
  This is a side effect of Kent's 11-07 `flat_light_text_runs` flip.
- **The re-set's report of what it skipped, and why, is thrown away** (in
  `pipeline.py`, at the `enlarge_small_text` call), so nobody can see why a
  line was not raised. Fremont's EST 1895 stays at art size for a reason the
  record cannot give.
- **Drone and ProSeal's raised small text sews thin columns.** They sew 0.90
  and 0.81 mm against the pro's 1.26. `_stroke_target`'s 1.45 was fitted on a
  medial-axis stroke, but it multiplies a mean skeleton half-width, which
  reads lower, so the 0.85 floor sews instead. Changing it moves a sewn width:
  gate 1.
- **MFab's letterform priors are gated off by the photo lane's grid.** The
  tolerance is 0.195 mm against a grid of 0.25 mm. MFab classes
  `photo_scene` and `photo_work_grid` is OFF. See memory
  `mfab-photo-route-2026-11-04`.
- **To a T's hexagon border sews at the `machine.OUTLINE_WIDTH_MM` floor of
  1.52 mm** where the pro sews 2.12 (hat) and 1.96 (beanie). Its speed lines
  sew at the pro's width where they sew, but one of 14 is lost on each design
  and five more break on the beanie. Which gate removes them: UNCONFIRMED.

**The worker's ranked build list, all default OFF:**
1. Bevel fold plus a tone merge: built as `bevel_ring_fold`, #1486.
2. Fine bars that survive (To a T, 5 pins). A `debug_dir` trace first.
3. A guard on the dark-ink carve within a word (Bridge's U, confirmed), plus
   an arc re-set (Bridge, 3 pins, unconfirmed).
4. Measure the existing `photo_work_grid` on MFab, then a gap hold if needed.
5. Keep the re-set's skip report as an info warning, then re-spine after the
   re-set (Fremont).
6. A small-text stroke read with the measure 1.45 was fitted on (0 pins;
   gate 1).

## What I got wrong (the director)

- **"The pro makes repeats identical."** Wrong. Bridge's handles are already
  alike in the art (0.21 mm), and ours spreads them to 0.58 mm. Our pipeline
  adds irregularity. *(measured 2026-11-13: `pro-redraws-1113/REPORT.md`)*
- **"We sew everything fat; the pro matches the art within 1%."** Wrong as
  stated.
  - That figure was a dark-pixel count on shaded renders.
  - Measured with both files drawn the same way, the pro is as heavy as us on
    Becker (1.19 against our 1.18 times the art) and Bridge (1.09 against
    1.09). We are heavier on MFab (1.12 against 0.95) and Gaulke (1.37 against
    0.74) only.
  - What closes small counters is pull compensation on satin rails plus thread
    width, and the amount of pull is a fabric constant: gate 1, sew-out first.

  *(measured 2026-11-13: the width ledger, `digitizer/tools/width_ledger.py`
  on PR #1485, still open; table in its body)*
- **The proof-read's "a counter" findings on Jakarta**, which the director
  told Kent had been checked, were the instrument reading transparent holes as
  ink. Fixed since (memory `proofread-2026-11-13`).
- **Proof-read as a judge.**
  - Its findings land on Kent's fault groups barely above chance: satin 38
    groups hit against 29.7 by chance, fill 23 against 19.7.
  - It raises findings on designs he graded Good.

  It is a tool for tracing, not yet a guard. *(measured 2026-11-14: PR #1487
  body, Table A)*

## Limits the director hit

- **75% was not reached: 67% at 04:45.** One laptop's CPU is the ceiling. All
  workers were local; the cloud was not used because Kent did not ask for it.
- **The message cap.** The app stops a session after 20 messages to other
  sessions until its user types there. From about 02:50 the director could not
  re-task, nudge or redirect anyone, and four workers finished and sat idle.
- **Timer-fired turns cannot start sessions.** After the first wave the
  director could only re-task workers that already existed.
- **Disk** sat between 9.3 and 12 GB free all night, against a floor of 10.
- **A worker's final message reached the director only through an explicit
  `SendMessage`.** The app's turn-end note is a short recap, not the report.
- **`archive_session` leaves the lane folder behind.** The lane still has to
  be removed with `git worktree remove`. A file lock at removal left an empty
  `.claude/worktrees/pen-stroke`.

The app limits are in the traps list of
`docs/superpowers/plans/2026-10-23-opus-team-architecture.md` §8.

## Still open (2026-11-14)

- **#1485 fat ink**: open. At 04:55 it was red on
  `tests/test_tools_help.py::test_tool_help_exits_zero[tools/width_ledger.py]`.
- **#1487 proof-read census and first guard**: open. At 04:55 it was red and
  conflicted on
  `tests/test_shape_memo.py::test_every_contextvar_in_the_package_is_ambient_or_a_cache`
  (`stage5_overlap._KEEP_ART` unlisted).
- Both features are OFF.
- **MFab's "random stitch in the middle" pin is named, not fixed.** A 3.35 mm
  white triangle gets a bean loop sewn on top of the fill; the pro sews one
  fanned satin. See `docs/connectors-on-top-2026-11-14.md`.

## Kent's rulings, 2026-11-14

He picked each option on its sheet. *(ruled 2026-11-14 — Kent, relayed by the director)*

1. `inshape_piece_lift`: "Flip ON".
2. `small_text_reset_one_baseline` + `text_cluster_solid_guard`: "Flip both ON".
3. The four `group_consistent_*` flags: "Flip all four ON".
4. `outline_redraw_k`: "Set 0.75".
5. `flat_blend_band_any_scale`: "Flip ON".
6. `lettering_columns_connectors_buried` stays OFF. His words, on the Becker
   pin #14 OFF | ON sheet: "Build edge-walk, notice how the pro makes a nice
   corner with the thread andc continues the stitch to the right".
7. `bevel_ring_fold`: "Studio tickbox, OFF".
8. An agent eye, with the original beside the render, as the working judge:
   "Yes, gross faults only" (missing, merged, invented, unreadable). It does
   not judge jagged edges, pen flow or close A/B picks, and there is no nightly
   run. Flips stay his.
9. The run: "Builds + next wave".
   - First the flips PR, the edge-walk and the tickbox.
   - Then arc text with the skip report, thin bars kept whole, flat satin ends
     and the apex_cut guard.
   - At most 4 of the director's workers at once, Opus. Stop at 90% usage or
     under 10 GB of disk.

Flips 1 to 5 land in their own PR. Until that merges, every flag on this page
is still OFF on main.

## Decisions that were waiting for Kent (before his 11-14 rulings)

1. The flips in the table above.
2. Flattening shaded art: default ON, OFF, or a Studio tickbox.
3. Whether an agent's eye, with the original beside the render, becomes the
   working judge for gross faults in the dev loop. It would not judge close
   A/B picks. It scored partial against him.
4. Pen + auto-branch PR 2 (PR 1 merged as #1462).
5. The next wave, in the director's order:
   - raise arc text, and keep the re-set's skip report;
   - keep thin bars whole (To a T's speed lines, 5 pins);
   - satin ends that form a flat edge;
   - a wide unseen logo corpus, proof-read by an agent eye each night.
6. A sew-out. Counters closing under pull compensation cannot be settled any
   other way.

## What merged from the night

#1476, #1477, #1478, #1479, #1480, #1481, #1482, #1483, #1486, #1488, #1489 and
#1490, plus #1462 and #1469 from two sessions that an app restart had cut off.
Open: #1485 and #1487.
