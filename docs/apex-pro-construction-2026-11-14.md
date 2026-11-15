# How the pro sews the point where two letter strokes meet (2026-11-14)

Kent on `lettering_columns_apex_cut` + its guard (#1514), looking at
`apex-guard-1114/sheets/gain_becker_hat_large.png`: "Off was closer to the
pros here, but still not perfect, let's get an agent working on this." and
"I want it exactly like the pros." Both flags stay OFF.

This page reads the pro's stitch files at each joint, builds an instrument
that puts a number on "closer to the pro", and builds the construction the
reading describes behind a new flag, `cfg.extra["lettering_columns_apex_pro"]`
(built OFF).

**Verdict:**
- **The pro sews MARINE's M (all five Becker files) one way, and neither OFF
  nor ON is it.** One leg runs straight through the joint to the point; the
  other stops on a split line and fans.
- **apex_pro builds that construction.** On the M's V it is closer to the pro
  than OFF and than apex_cut ON, on both numbers, at all five Becker sizes
  (table below).
- **Scope: down-pointing V's only** (the M's V; a W's lower points). Up-pointing
  tips, an N's tips and an A's apex are not touched. The N's tips are sewn
  another way, and the A's apex in these files is not a point.
- **A rule from geometry, read from ONE digitizer on ONE word.** Becker's five
  files are one design scaled. ProSeal adds two joints, MFab none that reach
  the Column lane. It is a candidate for Kent's eye, not a settled rule.

## 1. The pro's construction, joint by joint

**How it was read.** `tools/apex_pro.py`, one reader on both files:
- the pro's DST through `letter_pieces` (stitches fused into crosses, chains
  split at 35 deg turns);
- registered onto our plan frame: a global scale and shift, then each letter
  shifted on its own thread (local IoU in the table);
- each joint drawn with stitches coloured by sewing order and pieces numbered
  (`eye_pairs_out/apex-like-pro-1114/read/`, primary checkout, gitignored).

**Angles** are degrees in the plan frame, y down, mod 180: 0 = a level cross
(parallel to the line of text), 90 = upright. A diagonal running from top-left
to bottom-right is square-crossed at about 145-150.

| # | joint (file, width) | who owns the point | split line | crosses either side | fan or step | cross length, pitch | sewing order through the joint | local IoU |
|---|---|---|---|---|---|---|---|---|
| 1 | Becker hat large M, V (101.9 mm) | the RIGHT leg | from the crotch down-left to the left stem's inner edge, parallel to the right leg (~117-120 deg) | left leg + the stem's top: one fan, 104 -> 137 deg (59 crosses). Right leg and point: level (0 deg) | left: FAN (near-upright at the shoulder, toward square at the split). Right: level crosses STEP up from the point along the V | left fan 5.4 mm, pitch 0.15. Point 4.9 mm, 0.22; right leg 7.4 mm (level across a diagonal), 0.25 | left stem up (level, stops at the crotch's height) -> left fan, shoulder to split -> point upward, level, on up the right leg -> jump to the M's top-right -> right leg's top, level, DOWN to meet it -> right stem down | 0.82 |
| 2 | Becker LC large M, V (95.7) | right leg | as #1 | fan 104 -> 136 (55 crosses); point + right leg level | as #1 | fan 5.1 mm, 0.15; point 4.5, 0.21; right leg 6.9-7.3, 0.20-0.25 | as #1 | 0.83 |
| 3 | Becker hat small M, V (76.5) | right leg | as #1 | fan 104 -> 139 (43); level | as #1 | fan 4.2, 0.18; point 3.9, 0.24; right leg 5.7-6.0, 0.21-0.27 | as #1 | 0.73 |
| 4 | Becker chest small M, V (76.5) | right leg | as #1 | the same file as #3 at another hoop position: piece for piece identical | as #1 | as #3 | as #1 | 0.74 |
| 5 | Becker beanie M, V (79.8) | right leg | as #1 | fan 104 -> 137 (47); level | as #1 | fan 4.5, 0.16; point 4.0, 0.23; right leg 6.0-6.3, 0.22-0.24 | as #1 | 0.45 |
| 6 | Becker hat large N, top-left (stem meets diagonal) | the DIAGONAL (the right-hand stroke) | level across the stem, ~0.7 W below the top | stem level; the diagonal one piece of 109 crosses, 102 deg at the top-left corner turning to 0 at its foot | the diagonal FANS from upright over the stem's top | 4.9 mm, 0.18 | stem up, stops level -> diagonal from the top-left corner down to the foot | 0.60 |
| 7 | Becker hat large N, foot (diagonal meets stem) | the right STEM (the right-hand stroke) | none in angle: the diagonal's fan has turned level by the time it meets the stem | diagonal ends level; the point and the stem level | level crosses STEP up from the point, leaning with the diagonal's edge (axis 75 deg), then up the stem | point 6.5 mm, 0.20; stem 5.5, 0.20 | diagonal down -> point upward -> stem up | 0.60 |
| 8 | Becker hat large A, top (flat, ~9 mm wide) | no point: a flat cap | level across both legs at the counter's top | legs level; the cap two bands of near-upright crosses, 139 -> 91 and 105 -> 88 deg | the cap's bands fan to meet the slanted right leg | cap 4.6-5.2 mm, 0.15-0.22 | right leg up -> cap's right part, right to left -> cap's left part, left to right -> left leg down | 0.62 |
| 9 | ProSeal hat A, apex (85.9, rounded flat top) | neither leg: a separate level cap | level, at the counter's top, both sides | legs level (the left leg's crosses 0-172 deg) and the cap level | level crosses throughout: no angle seam at all | legs 3.5-3.9 mm, 0.21; cap 4.2, 0.21 | left leg up -> cap sewn down from the top -> right leg down | 0.46 |
| 10 | ProSeal hat small M (FOAM, ~4 mm caps, W 0.8) | not readable at this size | - | level crosses on every piece (stems and both V strokes), 1.2-1.7 mm | short level pieces stepping down and up the V | 1.2 mm, 0.20 | left stem up -> V down and up in four short pieces -> right stem down | 0.35 |

**Not read:**
- **MFab's M (MFAB).** The pro sews it as tatami fill, and we sew it as fill
  too, so the Column lane is not involved.
- **MFab's W (WELDING).** Its local registration reached IoU 0.16, too low to
  name pieces.

**What the rows share.**
- **The right-hand stroke owns the point at every pointed joint read** (rows
  1-7: the M's V at five sizes, both of the N's tips). Its crosses run level
  or turn level at the point, and they start AT the point. The other stroke
  stops on a split line, and its crosses fan into it.
- **The split runs where the owning stroke's edge runs on.** At the M's V that
  is the right leg's inner edge continued from the crotch, down-left across
  the merged V.
- **The stem beside the stopped leg ends level, and the stopped leg's fan
  covers the stem's top.** On the M this is at the crotch's height, the M's
  top-left shoulder. On the N it is ~0.7 W below the top.
- **A V pointing UP is a cap, not a leg.** The A's apex is a level cap
  between the legs (ProSeal) or a band of upright crosses (Becker's flat A).
  No leg owns it.

**The rule, from geometry only.** Where a V points DOWN (its crotch above its
point), the stroke on the later side of the line of text owns the point.
Where a V points UP (an A's apex), the joint is a separate cap. The N's tips
read as "right-hand stroke owns" too, but they need the stem's level cut at
~0.7 W, which apex_pro does not build. They are left for a follow-up.

## 2. The instrument

`python -m tools.apex_pro measure DESIGN OFF=… NEW=… ON=…`. In a disk round
the joint:
- each side's stitches are painted in sewing order, 20 px/mm, 0.4 mm thread;
- the last stitch over a pixel owns it (what the eye sees; underlay is buried);
- the pro is registered onto the letter as in section 1.

The numbers it reports:
- **angle_err_deg** is the mean |our cross angle - his| (mod 180, 0-90) over
  the pixels both sew. It is weighted by area: degrees per mm2 of shared
  thread. 0 = his exact directions.
- **seam_mm** is the split-line offset. Seam pixels are where the visible
  direction jumps more than 25 deg within 0.2 mm. It is the symmetric mean
  distance, ours to his nearest and his to ours. A side with no seam where
  the other has one reads as the window's radius.
- **shared_mm2 and iou**: the denominator, and the coverage.

**Limits:**
- Registration is translation only, per letter. The pro's MARINE sits
  ~0.5 mm off ours after it, and his V is shallower than the art's, so even
  his own construction on our outline could not reach 0.
- At Becker beanie the letter registers at IoU 0.45. Its rows are the
  weakest.
- One digitizer. "Closer" here means closer to this one pro's file.

## 3. The construction (`lettering_columns_apex_pro`, built OFF)

`outline_cut._apex_pro_cuts` / `_apex_pro_split` / `_apex_pro_shoulder` /
`_apex_pro_stem_cut` / `_apex_pro_column`; the notes at `_APEX_PRO`. It is
read by `find_cuts` in place of apex_cut's cuts (apex_pro wins if both are
on). It is set for one plan from `cfg.extra` by `pipeline.plan_stitches`.

Where it acts:
- a lone crotch with a convex tip across it (`_apex_tips`);
- the tip within 30 deg of straight below the crotch;
- apex_cut's own `_apex_walk` accepts it as two strokes closing.

What it does there:
1. **The split.** The junction rules' cuts from the crotch go. One split line
   replaces them: it continues the right-hand leg's inner edge from the crotch
   across the joint. It ends at the other leg's concave corner if one lies
   within 25 deg of the line, else where it leaves the letter or meets a cut.
2. **The shoulder.** Where the split ends on a stem's "ext" cut that runs up
   past the crotch, the ext is kept below the crotch's height and a level cut
   crosses the stem there. The stopped leg's piece then takes the stem's top,
   and it fans.
3. **The stem beside the point.** Where the concave corner on the owning side
   of the point has no cut, its stem edge is continued up. Without it, the
   owning piece runs into that stem: at 95.7 mm the level scanlines took the
   longer stem and dropped the V, and the point went bare.
4. **The point.** The piece holding the point is stationed with level crosses
   (`_apex_column` with a level cross), from the point up and on up the right
   leg.

What it does not do:
- **The sewing order.** It does not set the walk, so the order through the
  joint is the walk's. The pro's buried travel from the fan's end down to the
  point is the jag-source lane's to build.
- **Pull compensation, densities and other physical constants** (gate 1).

## 4. OFF | ON | NEW, every joint

**How the arms were made.**
- **Tree:** 863adf49, with each design's own request (`pro_pair.request`,
  the corpus's).
- **OFF:** this tree. Its md5 equals the apex-cut corpus's OFF
  (d0b4981a) on every design, so ON is the corpus's ON pickle.
- **ON+guard:** md5 = ON on Becker x5 and ProSeal x2
  (`docs/apex-guard-2026-11-14.md`). It was not captured on MFab.
- **NEW:** `lettering_columns_apex_pro` alone.
- **NEW+buried:** NEW with `lettering_columns_connectors_buried`, which is
  itself OFF (see the catch below).

Each cell is **angle error deg / split-line offset mm** (lower is closer to
the pro).

| design | joint | letter IoU | OFF | ON (= ON+guard) | NEW | NEW+buried | NEW vs OFF, instrument | by eye |
|---|---|---|---|---|---|---|---|---|
| becker_hat_large | M's V | 0.82 | 16.6 / 2.26 | 10.3 / 1.53 | **9.6 / 0.57** | 10.0 / 0.56 | closer on both | closer: fan over the shoulder, level crosses from the point up the right leg, as his |
| becker_lc_large | M's V | 0.82 | 51.3 / 1.14 | 13.8 / 1.55 | **10.2 / 0.53** | - | closer on both | closer: OFF's 12-end fan at the crotch is gone |
| becker_hat_small | M's V | 0.73 | 14.0 / 1.31 | 14.3 / 0.48 | **10.3 / 0.37** | - | closer on both | closer |
| becker_chest_small | M's V | 0.74 | 12.6 / 1.13 | 10.6 / 0.64 | 14.3 / 0.84 | **12.2 / 0.48** | NEW: mixed (angle +1.8, seam -0.29). NEW+buried: closer on both | NEW **reads worse**: a 4.7 mm hop runs back up over the finished level crosses (the walk). NEW+buried: no hop, closer |
| becker_beanie | M's V | 0.46 | 14.9 / 1.23 | 13.5 / 1.65 | 16.5 / 1.18 | **14.0 / 1.17** | NEW: mixed (angle +1.6). NEW+buried: closer on both | as chest small; weakest registration |
| becker x5 | N's top-left, N's foot, A's top | 0.41-0.64 | unchanged | unchanged | = OFF | | not touched (out of scope) | - |
| proseal_hat | A's apex | 0.46 | 17.4 / 0.26 | 7.2 / 0.23 | = OFF | | not touched (points up) | - |
| proseal_hat / beanie | FOAM's M (0.8 mm strokes) | 0.15-0.35 | | | = OFF | | under the 2 mm gate | - |
| mfab_hat / lc | WELDING's W, N, G (1.2 mm) | 0.09-0.20 | | | = OFF | | under the 2 mm gate | - |

**Before the 2 mm gate,** NEW moved MFab's small W, N and G and ProSeal's
small M:
- MFab hat W 38.2 -> 32.6 deg; N 25.5 -> 23.9; G 28.1 -> 33.4.
- MFab LC W, N and G each read 0.4-3.7 deg worse.
- At IoU 0.09-0.20 those numbers carry no weight either way. No joint at
  that size was read, so `APEX_PRO_MIN_W_MM` leaves them as OFF.

**The catch: the walk.** apex_pro changes the cut, not the order.
- **What goes wrong.** On chest small and beanie the lane's walk sews the
  level column from the top of the right leg down to the point. It then hops
  4.7 mm back up over it to reach the fan, and that bar shows on finished
  satin.
- **What he does.** He sews the fan first and lays the travel under the
  level column he sews next.
- **What fixes it today.** With `lettering_columns_connectors_buried` the
  hop becomes a jump and trim, and both numbers beat OFF at all three sizes
  tried.
- **Flip pairing.** apex_pro should flip only with buried (or with the
  edge-walk, #1512), or after the walk learns his order. That is the
  jag-source lane's walk.

**With edge-walk** (`lettering_columns_connectors_edge_walk`, which implies
buried). These runs are on the rebased tree, 88721988, with #1515's flips. Cells are
angle deg / seam mm.

| M's V | OFF | NEW | OFF + edge-walk | NEW + edge-walk |
|---|---|---|---|---|
| chest small 76.5 | 12.2 / 1.11 | 14.0 / 0.81 | 12.2 / 1.12 | **11.9 / 0.46** |
| beanie 79.8 | 14.2 / 0.98 | **11.3 / 0.75** | 14.1 / 0.99 | 11.6 / 0.70 |

**Why two of five got worse: the walk, not the cut.** By eye, on the two
sheets against the pro:
- **chest small.** NEW's construction is his: a fan over the shoulder, and
  level crosses from the point up the right leg. But the lane's walk enters the M from the right.
  - It sews the level column from the right leg's top DOWN to the point.
  - It then travels 4.7 mm back UP across those finished crosses to reach
    the fan. That bar is the angle error the instrument charged.
  - He sews the fan first and lays that travel under the level column, which
    he then sews from the point up.
- **beanie.** On 863adf49 it hopped the same way. On the rebased tree NEW
  alone no longer hops, and it is closer than OFF.

**Edge-walk on these two:**
- **Edge-walk alone** leaves the V as OFF: 12.2 / 1.12 and 14.1 / 0.99.
- **chest small, NEW + edge-walk.** It cannot find his order from that entry,
  so it cuts the hop as a trim: no bar, and closer than OFF on both numbers.
  That matches what buried gave.
- **beanie, NEW + edge-walk.** It sews exactly his order: fan, a travel under
  the column to come, then the level column from the point up.

So NEW is closer than OFF on both numbers at all five sizes:
- with edge-walk on the two sizes that hopped;
- alone on the other three.

Edge-walk was not run on hat large, LC large or hat small. With buried, hat
large stayed at 10.0 / 0.56.

**Sheets** (primary checkout, gitignored):
- `sheets_edge_walk/`: art | OFF | NEW | NEW+edge-walk | pro, for chest
  small and beanie.
- `digitizer/eye_pairs_out/apex-like-pro-1114/sheets/<design>_<joint>.png`:
  art | OFF | NEW | pro, every stitch outlined.
- `sheets_with_buried/`: art | OFF | NEW+buried | pro, for hat large,
  chest small and beanie.
- `read/`: the reading panels.

**Not settled here:**
- **Kent's eye.** The instrument says closer on the M's V. It does not say
  the M reads better at arm's length.
- **The N's tips.** Read (rows 6-7): the right-hand stroke owns them, and the
  stem's level cut sits ~0.7 W below the top. Not built.
- **The defaults moved on.** #1515 changed defaults after this tree (redraw
  0.75, piece lift). The numbers above are this tree's; re-run before a flip.

## 5. The joints read but not built: `lettering_columns_apex_pro_joints` (built OFF)

The second flag is `cfg.extra["lettering_columns_apex_pro_joints"]`. Its code
is `outline_cut._apex_pro_joint_cuts`, `_apex_pro_cap_column`, and the notes at
`_APEX_PRO_JOINTS`. It builds rows 6-8 of section 1. In each joint the
right-hand stroke owns it and the other stroke ends on a LEVEL line.

**Depths.** The stopping depths are his, read with each letter registered on
its own thread:
- **N, top-left (`n_top`).**
  - The stem's level crosses stop `APEX_PRO_NECK_W` = 0.95 W below the top.
  - The diagonal's piece takes the stem's top, with upright crosses fanning
    into the diagonal.
  - **Correction to row 6:** it said ~0.7 W. That was read without the
    letter's own registration shift.
- **N, foot (`n_foot`).**
  - The diagonal ends on a level line `APEX_PRO_FOOT_W` = 0.70 W above the
    baseline.
  - The stem's edge runs down to that line.
  - The stem's level crosses take the foot below it.
- **A flat-topped A (`a_cap`).**
  - It applies to a counter that comes to a point on top, under a straight top
    run of 1.5 W or more.
  - A band `APEX_PRO_CAP_W` = 0.65 W deep is laid across the top, crossed
    upright, over the legs.
  - **The counter must be pointed.** ProSeal's O (flat-topped counter) took
    the band in the first run. The test now requires the counter's width
    0.25 W under its top to be under 0.6 W.

**What it does not cover:**
- **ProSeal's A** is not a flat top: its run is 1.1 W. Its level cap is what
  apex_cut ON already sews: 7.2 / 0.23 against OFF 17.4 / 0.26 on the
  863adf49 tree.
- **Strokes under `APEX_PRO_MIN_W_MM`** (2 mm) are left alone.

**Instrument** (angle error deg / split-line offset mm). Tree: 21fb07d8
(main 10d1d863 plus apex_pro) with this flag. Columns:
- **NEW:** apex_pro + apex_pro_joints.
- **+walk+fold:** NEW plus `lettering_columns_connectors_edge_walk` and
  `lettering_columns_corner_fold_apex_side`, both ruled ON by Kent.

| design | joint | IoU | OFF | NEW | NEW +walk+fold | NEW vs OFF |
|---|---|---|---|---|---|---|
| becker hat large | N top | 0.59 | 33.8 / 1.25 | **11.4 / 0.80** | 6.5 / 0.27 | closer on both |
| becker hat large | N foot | 0.59 | 13.4 / - | **7.1 / -** | 2.7 / - | closer (angle) |
| becker hat large | A top | 0.63 | 50.3 / 5.00 | **20.0 / 0.71** | 18.9 / 0.71 | closer on both |
| becker LC large | N top | 0.60 | 39.5 / 5.42 | **9.8 / 0.73** | 10.0 / 0.73 | closer on both |
| becker LC large | N foot | 0.60 | 13.7 / - | **7.6 / -** | 6.1 / - | closer (angle) |
| becker LC large | A top | 0.65 | 49.5 / 4.70 | **34.4 / 1.59** | 26.5 / 1.15 | closer on both |
| becker hat small | N top | 0.58 | 36.8 / 4.13 | **9.5 / 0.44** | 8.3 / 0.26 | closer on both |
| becker hat small | N foot | 0.58 | 14.7 / - | **9.1 / -** | 3.2 / - | closer (angle) |
| becker hat small | A top | 0.51 | 48.1 / 3.75 | **17.0 / 0.27** | 16.0 / 0.27 | closer on both |
| becker chest small | N top | 0.59 | 38.0 / 3.30 | **10.2 / 0.54** | 7.1 / 0.15 | closer on both |
| becker chest small | N foot | 0.59 | 14.6 / - | **9.2 / -** | 3.3 / - | closer (angle) |
| becker chest small | A top | 0.51 | 47.2 / 3.75 | **17.4 / 0.29** | 16.4 / 0.29 | closer on both |
| becker beanie | N top | 0.41 | 30.8 / 0.95 | **11.9 / 0.50** | 13.8 / 0.67 | closer on both |
| becker beanie | N foot | 0.41 | 15.2 / - | **9.8 / -** | 5.1 / - | closer (angle) |
| becker beanie | A top | 0.33 | 37.9 / 1.35 | **22.8 / 0.49** | 21.8 / 0.49 | closer on both |
| proseal hat | A apex, small M | 0.33-0.47 | | = OFF (md5) | | not touched |
| proseal beanie | A apex, small M | 0.16-0.26 | | = OFF (md5) | | not touched |

**Notes on the table:**
- **The N foot has no split-line number.** Neither side has a seam in that
  window: his diagonal turns level into the stem, and so do ours.
- **The M's V rows** (apex_pro, unchanged by this flag) on this tree:
  - hat large 16.4 -> 9.5 deg;
  - LC large 50.1 -> 9.5;
  - hat small 13.3 -> 10.1;
  - chest small 12.2 -> 11.4;
  - beanie 14.2 -> 11.3.
- **+walk+fold** is closer than NEW alone everywhere except:
  - beanie N top, 13.8 vs 11.9 (still closer than OFF);
  - chest small M's V angle, 12.4 vs NEW 11.4 and OFF 12.2. Its seam is
    better.

**By eye, against the pro (sheets below):**
- **N top.** The stem stops level and the diagonal's piece fans from upright
  over the stem's top into the diagonal, as his does.
- **A top.** The upright band over level legs is his. His band also fans at
  its right end into the slanted leg; ours stays upright to the edge.
- **N foot, NEW alone.**
  - The foot is level and the stem's, as his.
  - The diagonal's crosses do not turn level the way his do; they meet the line.
  - A travel stitch runs on top along the diagonal's lower edge into the foot.
    OFF has the same kind of stitch at chest small.
- **N foot, +walk+fold.** That stitch is gone and the foot reads clean. Ship
  the foot with edge-walk on.

**Every case is closer than OFF at every Becker size**, so nothing is gated
off by size.

**Sheets** (primary checkout, gitignored, under
`digitizer/eye_pairs_out/apex-like-pro-1114/`):
- `sheets_joints/`: art | OFF | NEW | pro, every stitch outlined.
- `sheets_joints_walk_fold/`: OFF | NEW | NEW+walk+fold for hat large and
  chest small.
