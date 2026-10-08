# Can the image lane's `fillColumns` price come down? (2026-10-08) — HOLD

The image lane has passed `fillColumns` since Kent's call on 2026-10-08
(PR #673), at a measured +10.3% stitches (+10.4% on the full 2/4/6-colour
set). The foreman asked for a fix that cuts that price (stitches, travel
over sewn rows, rim pile-up) **without bringing back floats off the fill**.
This is the evidence. **Verdict: HOLD — no engine change.** The image lane
stays ON as Kent ruled; nothing here changes what the Studio sews. **Not
sewn.**

## Where the stitches go

`node tools/fill-columns-price.mjs --colors 4` (14 real logos at 4
colours, the Studio default, on left chest, hat front and full back):

42 designs: 1,125,149 stitches off, 1,240,919 on (+115,770, 10.3%); cuts 1,243 -> 1,072

| run | off | on | added | landings off (now penetrated) | added beyond the landings | of the whole design |
|---|---|---|---|---|---|---|
| fill | 919,628 | 993,880 | +74,252 | 57,511 | +16,741 | 1.5% |
| underlay | 133,937 | 175,455 | +41,518 | 6,967 | +34,551 | 3.1% |
| satin | 71,584 | 71,584 | +0 | 0 | +0 | 0.0% |

The landings alone, the floor any fix that keeps the floats away still pays: +64,478 (5.7%).

- **A landing is not overhead.** With the option off, a split row reaches
  each span after the first by a jump. The jump lands without a penetration,
  so the thread floats from the last span straight to the second point of
  the next one. With the option on, that span is reached by thread, and its
  first point is sewn. Those 64,478 stitches **are** the floats being taken
  away. Every fix that keeps the floats off pays them.
- So the part a fix could go after is the **51,292 stitches (4.6%)** beyond
  the landings. Two-thirds of it is in the **underlay** (+34,551: +26% on the
  underlay's own count). In the underlay, column walks at a 2–2.5 mm pitch on
  traced art fall into many short columns. summit_badge at full back: 774
  underlay rows in 1,103 columns, 866 of them one row long. Getting from one
  column to the next costs travel.

## Four candidate fixes, measured

The same 42 designs, through `tools/fill-columns-lanes.mjs --lane image
--colors 4 --src <candidate engine>`. Each candidate is a patch against
`src/` in [`candidates/`](candidates/), switched on through a global.
None was shipped.

| arm | stitches vs off | worst design | cuts | floats off the fill | verdict |
|---|---|---|---|---|---|
| **today (fillColumns on)** | +10.3% | +29.6% | 1,072 | 151 | the reference |
| A. round a deep row turn along the ring instead of splitting the column (`__ROUND`) | +10.2% | +28.1% | 1,077 | 152 | no gain: only 248 turns are deep on summit_badge, so the short columns come from the rows' own layout and not from splits |
| B. let an underlay float over ground the fill covers (`__FLOAT`) | +9.6% | +27.9% | 1,074 | **407** | rejected: **new floats off the fill** |
| C. sew the underlay as a plain walk, cutting where it would cross open ground (`__CHECKED`) | **+7.3%** | +20.7% | **8,268** | 150 | rejected: **7.7× the cuts** |
| C'. as C, but going round the ring instead of cutting | +16.4% | +37.8% | 2,660 | 150 | rejected: costs more than today on every measure; rim lines 97 → 178 |
| D. edge runs hug only the outer side of the ring, 0.4 mm allowed inward (`__INWARD`) | +10.2% | +28.4% | 1,072 | 151 | no gain: 444 stitches out of 115,770 |

*(measured 2026-10-08 — the tables these rows come from are the
`--src` runs of `tools/fill-columns-lanes.mjs`; A in
`round-turns-and-underlay-floats.diff` with only `__ROUND` set, B with
only `__FLOAT`; C' is `underlay-checked-plain-walk.diff` as committed, and C
is the same patch with `plainRingWay` returning null, so every open crossing
is cut; D in `edge-run-one-sided-hug.diff`)*

## What this says

- **The price is structural.** About 56% of it is the floats being replaced
  by thread. The rest is mostly the underlay walking around columns, and
  every way tried of walking around them more cheaply (A, C') did no better,
  or broke the one hard rule (B, new floats) or the cut count (C).
- **The one lever with real stitch savings is C**: −3 points mean, −9
  points on the worst design. It costs 7,200 more cuts across 42 designs
  (each cut is a trim on the machine and two thread ends). It is a cuts vs
  stitches trade, and neither geometry nor this measurement can say which
  costs more on the machine. It would need a sew-out or Kent's call, so it
  stays a patch here and is not an option.
- **What is not tried:** smoothing traced outlines before the fill. The
  rows' short columns and the rim stitches both follow the 1.6 px
  Douglas-Peucker staircase of `imageRegions.js`. That is a change to
  every image design, with or without `fillColumns`, and is its own lane.
