# Keyline loop chain: the pro's white as a few long satin chains (2026-10-26)

`cfg.keyline_loop_chain`, built OFF. It is the last piece of the MFab recipe's
trim gap that #1102 left: the white keyline's loop-to-loop cuts.

Kent's MFab request was that our satin follow the lettering's flow like the
pro's. With the gate's recipe and its extras on (#1122, Kent 2026-10-26:
"MFab extras into the gate", "All four"), the white-loop cuts are hat 11 /
LC 11, against the pro's 5 / 6.

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
  LC 5 (the recipe's plan, main `65fd6ce2`).
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

## Results

**Base:** today's main with #1122 (the gate's recipe and all four extras),
i.e. what MFab sews by default once #1122 lands. Each job is digitized once
and planned with the flag OFF and ON (`arm3.py`, scratch), one run at a time
under the CPU lock.

**Readers:**

- **Trims:** read from the DST with one reader on both files
  (`tools/sequence_pro.read_file`).
- **White-loop cuts:** each cut placed by the run it follows (#1102's
  `measure.py`); the pro's, by #1094's DST rule.
- **Exposed travel, read the same way on both files:** `walks_read.py`
  (scratch), one DST rule. A walk is >= 3 non-reversing 1.0-3.5 mm steps
  that are not a fill row; its thread is exposed where no later needle-down
  thread lies within 0.2 mm of its centre and both edges. `travel_cover`
  is beside it, on our plans only.
- **New bare garment:** garment no thread of the arm covers that OFF
  covered (0.4 mm threads on a 0.1 mm grid, patches >= 0.15 mm2).

| | DST trims | white-loop cuts | stitches | exposed walk mm, white / all (one DST rule) | exposed travel mm (`travel_cover`, ours) | new bare mm2 |
|---|---|---|---|---|---|---|
| hat, chain OFF | 30 | 11 | 20,561 | 2.0 / 10.8 | 21.0 | -- |
| **hat, chain ON** | **22** | **5** | 20,516 | **1.1 / 9.9** | 23.3 | **0.0** |
| hat pro | 18 | 5 | 17,568 | 0.0 / 4.1 | n/a | |
| LC, chain OFF | 25 | 11 | 17,777 | 6.0 / 15.5 | 35.4 | -- |
| **LC, chain ON** | **19** | **5** | 17,754 | **5.6 / 15.1** | 35.8 | **0.6** |
| LC pro | 19 | 6 | 15,786 | 0.1 / 0.8 | n/a | |

- **White-loop cuts fall to the pro's:** 11 -> 5 on both jobs, against his
  5 / 6.
- **Trims:** total DST trims go hat 30 -> 22 and LC 25 -> 19. The LC is now
  the pro's 19; the hat is 4 over his 18.
- **Exposed walk falls, read the same way on both files:** hat all-blocks
  10.8 -> 9.9 mm, LC 15.5 -> 15.1. The chain's walks lie under the white
  sewn after them, as the pro's do.
- **`travel_cover` rises a little on our plans:** hat +2.3 mm, LC +0.4. The
  hat's rise is in the black riders' block: their sequence starts from where
  the white now ends. The LC's is the one white walk it reads at all (0.42
  mm, within the 1 mm the bury rule allows). Thread on bare garment
  (`hairline_travel`) stays 0.0 on both.
- **The LC's 0.6 mm2 lies inside the black A of AND.** Main sews that A
  hollow (outlined small lettering, its own open lane). The loop's underlay
  used to cross that spot. The hat has no new bare garment.
- **Colour changes are unchanged** at 2 (the pro's 4).

![MFab hat: chain OFF | ON | pro](renders/keyline-loop-chain-2026-10-26/mfab_hat_off_on_pro.jpg)

Travel and cuts, OFF | ON (green: travel over thread; black rings: cuts):
`mfab_hat_travel_and_cuts_off_on.jpg`, `mfab_lc_travel_and_cuts_off_on.jpg`.
The LC: `mfab_lc_off_on_pro.jpg`.

### Bystander: Becker (the `border_from_outline` loops)

The flag is OFF by default, so Becker's default file does not change. With
the flag ON, Becker changes, as it should: its outline loops are the same
`keyline_runs` loops.

- **Trims:** DST trims 24 -> 20; four loop-to-loop lifts become walks.
- **The one-rule DST walk read is flat:** all-blocks 40.0 -> 40.1 mm.
- **`travel_cover` reads +4.1 mm on those walks.** They run a few tenths
  inside a satin rail, where the 1 mm cells are mostly off the satin. The
  `_bury_walks` docstring records this artifact.
- **Two small costs:**
  - one walk runs along the band's lower edge: 0.1 mm of thread on bare
    garment (`becker_walk_edge_off_on.jpg`);
  - a loop's seam moved to its chained start and opens 0.3 mm2 there
    (`becker_loop_seam_off_on.jpg`, 0.64 mm2 over three patches in all).

  Both appear only with the flag ON. They are why the flag is not proposed
  for Becker's outline loops yet.

## Tests

`tests/test_keyline_loop_chain.py`, 8 tests:

- the scope sets nothing when off, and OFF never reaches the new code;
- OFF lifts between letters, and ON makes the lift a walk under the next
  loop's satin;
- each loop starts nearest the next;
- the band's first loop is entered where it was;
- where no buried walk exists, ON cuts what OFF cuts and lays no exposed
  walk;
- a plan sets the flag from its config.
