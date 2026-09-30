# The envelope's teeth — a reach shorter than the window is not a reach (2026-09-30)

Kent's pick after the split comb (#578): the genuine reaches the envelope
keeps after its sibling rule (#577) are short, and the rail jitter where
they sit is three times the symmetric rails'. Measured on the tree after
both PRs, Becker at 100 mm; numbers in `census.json`.

## What a tooth is

Of Becker's 23 remaining stretches, **8 are a single station**: the
envelope's running minimum clears the 0.3 mm gap at one station and not
its neighbours, and the rail steps out 0.34–0.83 mm and straight back
within 0.4 mm of travel. Four sit on the letters (the M at (−41.4, 19.5),
the A's top, the I's foot, the N), four on the emblem band. tires, bridge
and screenshot had one, two and one such stations and no other reach at
all. The running minimum cannot follow a feature shorter than its window
(±3 stations), so a stretch shorter than the window that clears the gap is
a bump in the profile, not an edge.

## What the rules would do

Simulated on the captured offsets (extension area = Σ reach × 0.4 mm; the
added rail step is what the reach adds to the symmetric width's own
step between consecutive stations):

| rule | stretches | teeth | extension area | max added step | steps > 0.25 mm |
|---|---|---|---|---|---|
| as is | 23 | 8 | 20.60 mm² | 1.83 mm | 30 |
| **drop stretches shorter than the window (3)** | **15** | **0** | **19.11 (−7%)** | 1.83 | 21 |
| + slope limit 0.3 mm per station | 15 | 0 | 13.85 (−33%) | 0.30 | 25 |
| + slope limit 0.2 | 15 | 0 | 10.57 (−49%) | 0.20 | 0 |
| + ramp over 2 stations at each end | 15 | 0 | 15.73 (−24%) | 1.02 | 24 |
| + ramp over 3 stations | 15 | 0 | 12.61 (−39%) | 0.73 | 13 |

The minimum length removes every tooth for 7% of the extension area and
touches nothing else. The steps that remain are the ones a **long** reach
opens with — up to 1.8 mm in one station — and those are the artwork's
own features: a serif's edge is a step, and the reach following it is the
reach doing its job. Ramping or slope-limiting them costs a quarter to a
half of everything the envelope reaches for; that is a coverage-against-
flow trade, and it is Kent's, not a measurement's.

## What shipped

`_drop_short_reaches` in the envelope branch of `_rail_points`: a stretch
of fewer than `_ENVELOPE_WINDOW` consecutive stations at which the
envelope's offset exceeds the symmetric width reverts to the symmetric
width. The window is the minimum — no new constant.

**Measured on Becker:** reached stations 78 → 72, stretches 23 → 17
(the letters 19 → 16), teeth 8 → 0, stitches 9,333 → 9,321, the
envelope's new ground on the letters 15.2 → 14.8 mm² (87% bare before,
either way). Rail jitter over 0.15 mm at the reached stations **28.4 →
26.3%** (the same stations symmetric: 9.3%); the letters' unreached crosses
11.3 → 11.0%; all crosses 12.2 → 11.9%. golden_tee 12 stretches → 7
(five teeth), 8,581 → 8,575 stitches; tires, bridge and screenshot lose
their only reaches and keep their stitch counts.

**So the teeth were not where the roughness lived.** Two points of the
28% at reached stations were theirs; the rest is the long stretches'
plateaus and steps — the running minimum is piecewise constant, and a
reach that follows a serif or a corner steps with it. The strips below
show how little a tooth is to the eye.

## For Kent's eye

`becker100_tooth_M.jpg`, `becker100_tooth_A.jpg`, `becker100_tooth_N.jpg`:
a 7 mm window at 40 px/mm on a tooth, as shipped | with reaches shorter
than the window dropped, thread render on top and the rails drawn below
(the symmetric width in orange, the sewn rails in red, artwork grey). The
thread renders are all but identical; the red rail's one-station kink is
the tooth, gone on the right.

## What this leaves

- The steps a long reach opens with (1.8 mm max on Becker) read as the
  artwork's features. If the eye wants them softened, the slope limit or
  the ramp is the lever, at 24–49% of the extension area: Kent's trade.
- The remaining jitter at reached stations (26%) is the running minimum's
  plateaus. A smoother envelope (a running minimum blended over its
  window) would round genuine features too; not built.
