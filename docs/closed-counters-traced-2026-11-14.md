# Merged letters, closed counters, lost spacing: every pin traced (2026-11-14)

Kent's largest lettering complaint: letters that merge, counters that close,
spacing that disappears. The blind matcher put 23 of his fault groups (52 pins,
18 designs) in this class (`agent-eye-1113/census_table.md`, class 2). This page
traces each one to the stage that closes it, on main `66b11432` (after the
11-14 flips, #1515; the flag rebased onto `88721988`), and fixes the largest cause geometry can settle behind a
new flag, built OFF.

Evidence lives gitignored in the primary checkout,
`digitizer/eye_pairs_out/counters-1114/`:
- `merged_pins.json`: the 23 groups and their pins;
- `runs/<design>_<arm>/`: one digitize per design and arm (`scripts/ledger_run.py`);
- `strips/`: art | our render | pro at each pin, and the width-ledger
  footprints stage by stage;
- `sheets/`: `art | OFF | ON | pro`.

## Method

- **Eye first.** At each pin, the ORIGINAL art beside our render on main and the
  pro's file (`scripts/pin_now.py`).
- **Then the stage.** `tools/width_ledger.py`'s footprints at the pin
  (`scripts/pin_ledger.py`): the gap's width in mm in the art, after the trace
  (stage 4), after the small-text re-set, in stage 5's planned shapes, in the
  needle points, and with every stitch drawn 0.4 mm wide (thread). The pro's
  file is drawn the same way and registered onto ours. The gap is the art's
  non-ink nearest the pin, measured against the colour Kent saw covering it.
- **Then the stitch.** `scripts/who_at_pin.py` names the run that puts thread
  into the gap, and `scripts/shape_zoom.py` draws that shape's stitches over its
  stage-5 outline.

Pins were placed on renders from tree `950855bf`; positions are read off our
render's frame, so a probe can land a little off on a design whose layout
moved since (Bridge's arc text, the re-set lines). Those rows were read by eye.

## The trace

Gap widths in mm at the pin: art → stage 4 → stage 5 → needle → thread (pro).

| # | Design, pin | What closed (by eye) | Stage that closes it | Evidence |
|---|---|---|---|---|
| 1 | silhouette logo, #3-#32 (30 pins) | letters buried under mint blend-rim threads | stage 2-3: a JPEG blend rim sewn as its own thread | cured on main: `flat_blend_band_any_scale` ON (#1488, #1515) |
| 2 | Bridge, B "missing two center holes" | both counters of a 3 mm B | trace: the art's counters are about 2 px at 4.4 px/mm | 0.40 → 0.00 at stage 4; the pro re-drew the arc text 1.65x taller |
| 3 | Bridge, "&" | both counters of the & | trace, same | 0.72 → 0.00 at stage 4; the pro re-drew it |
| 4 | Bridge, "B and R merge" | the gap between the script B and r | trace | 0.78 → 0.00 at stage 4 |
| 5 | Bridge, "cannot read the e" | the e's eye | trace | 0.70 → 0.00 at stage 4; the pro sews an open eye at a larger size |
| 6 | Bridge, "N and T merged" | the gap between two arc letters | trace (the art's gap is about 1 px) | 0.20 → 0.00 at stage 4 |
| 7 | Bridge, i dot touching | the gap under the i's dot | needle and thread | 1.00 → 0.99 → 0.96 → 0.64 → 0.29 (pro 0.18) |
| 8 | Gaulke, window dividers | the white cross between four black panes | needle (rail push), then thread | 0.85 → 0.72 → 0.60 → 0.60 → 0.22 (pro 0.73) |
| 9 | Gaulke, "not enough spacing between the E" | the slots between the E's arms | **needle: the satin rail push into a bay** | 1.00 → 1.00 → 1.00 → 0.00 → 0.10 (pro 0.36) |
| 10 | Gaulke, "white spacing not apparent" | nothing closed: a jagged white line | not this class (jag) | 1.53 → … → 2.78 (pro 0.58) |
| 11 | Gaulke, "S has no spacing between the curves" | both bays of the S | **needle: the satin rail push into a bay**; also 1.9 mm of satin fanned across the bay | 0.78 → 0.73 → 0.73 → 0.00 → 0.00 (pro 0.36) |
| 12 | Fremont, "A is hard to read" | the A of EAT (small serif text) | small text: bean spines written at art size before the re-set (director's 11-13 trace) | sewn as runs at art size; the pro raised it |
| 13 | MFab, "can't read the G" | the G's white bowl | stage 5 growth over the white keyline, then thread | 0.86 → 0.90 → 0.70 → 0.67 → 0.32 (pro 0.85); `growth_keeps_gaps` (#1485) is that lever |
| 14 | ProSeal, "S has no spacing" | the bays of a re-set small S | thread width on a small S (the flag below does not move it) | probe in a moved area; read by eye |
| 15 | TOAT beanie, "T intersects the border" | the gap between the T's bar and the diagonal line | **needle: the rail push toward the same-thread border**, then thread | 1.28 → 1.20 → 1.20 → 1.00 → 0.60 (pro 0.32) |
| 16 | low_poly, "detail mushed together" | thin facets lost | not this class (shape detail, stage 2-4) | — |
| 17 | isometric icon, "no break between shapes" | two shaded pinks sewn one thread | not this class (tonal merge, stage 2-3) | — |
| 18 | outline_lineart, dot on the i | the dot sewn inside a satin keyline ring | keyline sewn as satin | `border_from_outline_hairline_run` is ON on main; not re-run here |
| 19 | bukit_asam, "no spacing between the rings" | the gap between the C and its thin outer arc | needle and thread: a 0.5 mm arc sewn as a satin wider than drawn | 0.64 → 0.82 → 0.82 → 0.50 → 0.14 |
| 20 | hed_p_e, e | the e's eye filled by a 1.5 mm white satin keyline | keyline sewn as satin | cured on main: `border_from_outline_hairline_run` ON (eye, `strips/now_lt_hed_p_e.png`) |
| 21 | hed_p_e, p | the p's counter, same | keyline sewn as satin | cured on main, same |
| 22 | k_line, KAWASAKI | the gaps between 2.7 mm serif letters | needle and thread on strokes under a thread's width | 0.58 → 0.58 → 0.58 → 0.32 → 0.20 |
| 23 | and_pizza, "&" has no gap | the Z-joint of the & | Column-lane joint construction | the apex-cut lane's pin (`docs/apex-cut-corpus-2026-11-14.md`) |

*(measured 2026-11-14 — `eye_pairs_out/counters-1114/runs/*_off/pins.jsonl` on `66b11432`)*

## Pins per cause

| Cause | Groups | Pins | Whose |
|---|---|---|---|
| Trace loses counters under a thread width at low resolution (the pro re-draws and raises the text) | 5 | 5 | the arc re-set lane; all on Bridge (4.4 px/mm) |
| **Satin rail push into a bay or a same-thread gap** | **4** (8, 9, 11, 15) | 4 | **this page** |
| Thread width on gaps and strokes under 0.5 mm (a physical constant) | 4 (7, 14, 19, 22) | 4 | gate 1; raising small text is the pro's answer |
| Keyline sewn as satin | 3 | 3 | cured on main (`border_from_outline_hairline_run`, ON) |
| Blend rim sewn as a thread | 1 | 30 | cured on main (#1488) |
| Stage-5 growth over an earlier colour | 1 | 1 | `growth_keeps_gaps` (#1485, OFF) |
| Small text sewn at art size | 1 | 1 | the Fremont re-set lane |
| Column-lane joint | 1 | 1 | the apex-cut lane |
| Not this class (jag, detail, tonal merge) | 3 | 3 | facets, detail |

The trace row is larger by count, but all five pins are one design at
4.4 px/mm: the counters are two pixels wide in the art and under a thread's
width at art size, so no geometry recovers them. The pro's answer there is to
re-draw the lettering larger, which is the arc re-set's work. The rail push is
the largest cause that geometry settles.

## The cause: the rail push holds back from a counter, not from a bay

Under `satin_rail_comp` (ON), the satin and Column-lane emitters push both
rails of every cross outward by the fabric's pull (`_push_rails`,
`stage6_satin.py`). A push that would enter a COUNTER (a hole of the shape) is
already held so the counter stays `cfg.min_detail_mm` wide. A gap that is not
a hole gets the full push from both sides:
- the bay of an S;
- the slot between an E's arms;
- the gap to the next pane or letter of the same thread.

Gaulke's E and S kept their gaps through stage 5 (1.00 and 0.73 mm) and lost
them in the needle points (0.00 and 0.00). `shape_zoom.py` shows the S's
satin pushed into both bays and fanning across the upper one.

**`cfg.extra["satin_push_keeps_gaps"]` (built OFF).** ON, the counter rule
also reads a gap the push crosses first along the cross: a ray from the rail
that leaves the shape and meets the shape again (a bay) or meets other ink of
the same thread (a neighbour). That gap is held exactly as a counter is. The
pull's size is untouched (gate 1); the flag decides where it goes.
- `true` holds a gap to the counter floor (`cfg.min_detail_mm`).
- A number is the floor in mm a gap keeps instead.

## What moved (OFF → ON, gap at the thread in mm, pro beside)

| Pin | OFF | ON (`true`) | ON (`0.5`) | pro | By eye |
|---|---|---|---|---|---|
| Gaulke E | 0.10 | 0.82 | 0.36 | 0.36 | both ON arms: the arms read apart; `0.5` looks like the pro's |
| Gaulke S | 0.00 | 0.67 | 0.28 | 0.36 | both bays open, reads S; `0.5` looks like the pro's |
| Gaulke window | 0.22 | 0.54 | 0.50 | 0.73 | the upper vertical divider opens; the horizontal one stays shut (stage-5 growth, below) |
| TOAT T against the border | 0.60 | 0.98 | as OFF | 0.32 | `true`: the bar stands clear of the line. `0.5`: still touching, as in the pro's own file |
| ProSeal S | | | | | no visible change in either arm (a re-set small S; thread width) |
| Bridge, MFab, k_line, bukit, Fremont | | | | | no visible change: their causes are above |

`true` cures 3 of Kent's pins outright (Gaulke E and S, TOAT T) and one in
half (Gaulke's window). It opens the E and S about twice as wide as the pro.

`0.5` lands on the pro's own gap at the E (0.36 against 0.36) and near it at
the S (0.28 against 0.36). It leaves the TOAT T touching the border, as the
pro's file does there.

*(measured 2026-11-14 — `runs/*_on/pins.jsonl`, `runs/*_on05/pins.jsonl`)*

## What else moves (whole design, OFF → ON)

Share of the render's pixels that change, and stitch count.

| Design | `true` | `0.5` | By eye, `true` |
|---|---|---|---|
| Gaulke | 3.86%, 7413 → 7371 | 0.35%, 7413 → 7420 | letter bays and the roof band's inner edge near its apex; nothing reads worse |
| TOAT beanie | 2.45%, 18081 → 18063 | 0.07%, 18081 → 18081 | the T clears the border. **Catch: the parallel speed-line bars sew thinner**: their facing sides are a same-thread gap under the floor, so they lose the pull there |
| bukit_asam | 2.52% | | the rings' satin edges; still merged |
| MFab | 1.81% | | AND WELDING's edges; no visible gain or loss |
| Becker (guard) | 0.21%, 16049 → 16023 | 0.04%, 16049 → 16041 | MARINE's letter edges; nothing reads worse |
| Jakarta (guard) | 0.83%, 3100 → 3097 | 0.57%, 3100 → 3106 | the edges of k, a and t; nothing reads worse |
| Ahora (guard) | 0.42%, 9208 → 9206 | 0.12%, 9208 → 9208 | round the O; nothing reads worse |
| hed_p_e (guard) | 0.01% | | nothing |
| Bridge, ProSeal, k_line, Fremont | 0.4-0.9% | | edges only |

*(measured 2026-11-14 — `scripts/guard_sheet.py`, sheets in `counters-1114/sheets/`. Gaulke and TOAT
are on the final code; the other rows are the first build, which differs only at grazing rays)*

## The window's horizontal divider: stage-5 growth

All four panes sew as satin. Probed at both dividers (`window_probes.json`),
gap in mm, art → stage 4 → stage 5 → needle → thread (pro):
- horizontal divider: 0.8 → 0.7 → **0.4** → 0.5 → 0.1 (0.7);
- vertical divider between the lower panes: 0.7 → 0.7 → **0.1** → 0.3 → 0.1 (0.63).

Stage 5 grows the two lower panes up and toward each other; the upper panes
keep their artwork polygon. The satin then sews the grown outline and the
thread closes what is left. That is `growth_keeps_gaps` (#1485, OFF), not this
flag. Gaulke, gap at the thread in mm:

| Arm | window (pin) | horizontal divider | E | S | panes by eye | pixels moved |
|---|---|---|---|---|---|---|
| OFF | 0.22 | 0.1 | 0.10 | 0.00 | one blob | — |
| this flag `true` | 0.54 | 0.1 | 0.82 | 0.67 | upper divider only | 3.86% |
| `growth_keeps_gaps` alone | 0.60 | 0.6 | 0.10 | 0.00 | lower divider and horizontal only | 0.93% |
| both, `true` | 0.61 | 0.6 | 0.82 | 0.67 | four panes | 4.60% |
| **both, `0.5`** | **0.60** | **0.6** | **0.36** | **0.28** | **four panes** | **1.29%** |
| pro | 0.73 | 0.7 | 0.36 | 0.36 | four panes | |

*(measured 2026-11-14 — `runs/gaulke_roofing_hat_{on,growth,both,both05}/`,
sheet `sheets/gaulke_window_E_S__art_off_on05_both05_pro.png`)*

## Cost

The first build tested each ray with shapely scalars: 15k calls, about 19 s
of Gaulke's stage 7 under cProfile. `_kept_limits` now does it per column in
arrays:
- one numpy ray-edge pass per block of 256 rays, over only the edges inside
  the block's reach;
- spans and the first bare span as array operations, with one vectorised
  `contains_xy`;
- ring edges in one `get_coordinates` call;
- the neighbour ink clipped to the column's box before the overlay;
- `deadline.check` per block, pinned by a test.

It is byte-identical to the per-ray build (Gaulke md5 `22a7ea0b` at `true`,
`0c2bba77` at `0.5`).

Digitize time, one shared generation, arms interleaved OFF, `true`, OFF,
`0.5` (stage 7 is the only stage the flag touches):

| Design | `_push_rails` OFF | `true` | `0.5` | stage 7 OFF | `true` | `0.5` |
|---|---|---|---|---|---|---|
| Gaulke | 0.8-1.0 s | 1.9 s | 2.1 s | 28.6-28.8 s | 26.5 s | 29.7 s |
| Becker hat large | 0.22-0.31 s | 0.36 s | 0.38 s | 24.2-29.5 s | 19.9 s | 20.2 s |
| MFab (105 mm, 20.9k stitches) | 0.84-1.23 s | 2.44 s | 2.57 s | 49.6-63.6 s | 59.8 s | 59.1 s |

*(measured 2026-11-14 — `scripts/time_arms.py`; the laptop carried about 11
other sessions, and two identical OFF runs of stage 7 differed by up to 30 s
under heavier load earlier the same evening)*

The new pass differs from the first build's per-ray shapely test at 32 of
Gaulke's 15,266 rail points. All are rays that run along or graze the
shape's own edge, which the first build read as a bay.

## Kent's pick

**What I would ship: `satin_push_keeps_gaps = 0.5`, and for the window
`growth_keeps_gaps` with it.** At Gaulke's three pins this pair puts our gap
at 0.36, 0.28 and 0.60 mm, against the pro's 0.36, 0.36 and 0.73. It moves
1.29% of the design; 0.5 alone moves 0.04-0.57% of the guards. `true` opens
the E and S to 0.82 and 0.67, twice the pro's, thins close parallel bars, and
moves up to 3.9%. The one thing `true` cures that `0.5` does not is TOAT's T
on its border, and the pro's own file has the T on the border too.
`growth_keeps_gaps` is #1485's flag and its own flip; its sheets are in
`eye_pairs_out/fat-ink-1113/`.

1. `0.5`, with `growth_keeps_gaps` for the window (recommended).
2. `true`.
3. Keep OFF.

## Not done

- The satin that fans across the S's upper bay (1.9 mm of thread over bare
  fabric) is construction, not push; it is untouched.
- Bridge's five trace pins wait on the arc re-set; k_line and bukit wait on
  raising small text (a 0.5 mm stroke sewn by a 0.4 mm thread).
