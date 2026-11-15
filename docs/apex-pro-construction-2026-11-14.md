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

(filled from `tools/apex_pro.py measure`; see the table in the PR body and
`eye_pairs_out/apex-like-pro-1114/sheets/`, primary checkout, gitignored)
