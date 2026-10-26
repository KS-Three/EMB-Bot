# Keyline loop chain: the pro's white as a few long satin chains (2026-10-26)

`cfg.keyline_loop_chain`, built OFF. It is the last piece of the MFab recipe's
trim gap that #1102 left: the white keyline's loop-to-loop cuts.

Kent's MFab request was that our satin follow the lettering's flow like the
pro's. With the recipe on, #1102 measured the white-loop cuts at hat 11 / LC 9,
against the pro's 5 / 6.

## How the pro sews the keyline

The same reader runs on both DSTs (`pro_walks.py`, scratch). A walk is a
stretch of consecutive needle-down steps of 1.0-3.5 mm that never reverses.

- **His white block is 7 stretches:** 6 cuts over 3 pieces.
- **Two long satin chains carry most of the keyline**, 1,692 and 2,082
  penetrations, each several letters long.
- **Inside them he walks.** On the hat: 131 walks in the white block, LC 130.
  - Most are 3-12 mm.
  - A few run 25-96 mm along the band to a far letter (hat: 96.5 mm from the
    M's foot to the F, then 29 mm back).
- **The walks are hidden.** Each walk's thread, read at its centre and both
  edges, lies 96-100% under white satin he sews AFTER it, with three
  exceptions on the hat's lower right (0.58-0.76). He walks under satin still
  to come, then satins back over the walk.

## Ours

The code is `stage6_border.keyline_runs`, the loops of the white field, one
per letter:

- Loops are taken nearest-first from the needle.
- Each closed loop starts at the ring point nearest the previous loop's end,
  so it also ENDS there, on the far side from the next letter.
- The hop to the next loop is 7-22 mm across finished thread: hat 7 lifts,
  LC 5 (recipe plan, today's main).
- `monoline.bury_hops` applied as it stands (route under satin still to come,
  at most 1 mm outside, no longer than max(20, 4 x direct)) buries 1 of the
  hat's 7 and none of the LC's 5. The hop starts across a finished loop.

## The change (OFF)

When the flag is ON, each loop STARTS, and so ends, at its ring point nearest
the loop sewn after it. The hop into each loop is then walked under the loops
still to sew, its own satin included (`_bury_walks`, after
`monoline.bury_hops`).

- **The rule is bury_hops':** at most `BURY_EXPOSED_MAX_MM` (1 mm) outside
  the satin still to come, and no longer than max(20, 4 x direct).
- **One difference:** the satin footprint is shrunk by half a thread
  (`COVERAGE_THREAD_W_MM`) first, so the walk's whole thread lies under the
  satin, not only its centre line.
- **The walk can run round the loop's own band to its start**, under the
  satin that follows: the pro's walk.
- **Where no buried walk exists the needle lifts, as before** (a cut past
  `trim_at_mm`). The chain never lays a bridge across finished thread.
- **The band's first loop is entered where it was** (band bridge or lift),
  then walked round under its own satin to its chained start. With no such
  walk it is the loop as it was.

It lives in `stage6_border.keyline_runs` (`_bury_walks`, `_walk_into`), set
for a plan by `loop_chain_scope` the way the mitre's scope is set. It serves
both the keyline loops (`enclosed_white_keyline`) and the outline loops
(`border_from_outline`). No new constant.

### Variants tried, band by band

Each captured `keyline_runs` call was re-sewn offline (`variants.py`,
scratch). The counts are cuts between loops; the band's entry is the same in
every column (hat 0, LC 1, Becker 1).

| | loops | OFF | first build (start chained only when the walk into it is buried) | **built** (every loop chained; bury, else lift) |
|---|---|---|---|---|
| MFab hat | 9 | 7 cuts | 6 | **3** |
| MFab LC | 7 | 5 | 5 | **2** |
| Becker | 5 | 4 | 1 | **1** |

- **The first build barely moved.** A loop's walk into its chained start
  from the needle's far side is too long to bury, so most loops kept the old
  start.
- **A third variant fell back to the band bridge** where it could not bury.
  It sewed exactly the built arm on all three: no hop needed the bridge.

RESULTS
