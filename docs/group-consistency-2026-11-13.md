# Like things sewn unlike: census and the group rule (2026-11-13)

Kent pins one fault in many clothes across his three defect-marks sittings
(1110, 1111, 1112): like things sewn unlike. The Director's hypothesis: every
construction decision (tier, angle, border, enclosed white, thread) is taken
per region against a threshold, so two like shapes that straddle it come out
different, where a person decides once per group. This note tests it on main
`7ad9c124`, eye first, then by number, and records what was built.

Method: the Studio request (`tools.fremont_triage.studio_request`) at the kit
size, one digitize at a time, `PipelineConfig(debug_dir=...)` stage dumps, the
render beside the art, and a trace of which stage-7 rung each shape took
(module emitters wrapped; the caller's line number names the rung). Renders,
per-shape JSON and dumps: `digitizer/eye_pairs_out/group-consistency-1113/`
(gitignored, primary checkout). No artwork is committed.

## Census: every "like things differ" note, traced on main

| item (size) | his note | what is mixed | the decision that split it |
|---|---|---|---|
| lt_ahora (80 mm) | "This stitch is different than the AH RA" (O, !) | AH, RA fill under a pink satin loop; O, ! satin | **Threshold straddle.** The sewn pink field reads as an art outline (reach 0.906 against 0.90), and `art_outline`'s body test (`stroke >= OUTLINE_BODY_RATIO x band`, 1.0) takes AH (1.059) and RA (1.023) as bodies; O (0.612), ! (0.456) and its dot (0.220) go to the classifier, which says satin for all four. The outline census saw no pro body between 0.87 and 1.34. No text cluster fires: AH and RA are fused in the art. |
| lt_k_line (80 mm) | (no pin; found by the census) | grey subline: 17 letters bean outline, 6 satin | **Threshold straddle.** The run tier's area floor `min_detail_mm^2` = 2.25 mm^2: 1.13-2.25 mm^2 run, 2.54-3.07 mm^2 satin; one thread, one line, 2.5 mm caps. All 24 are ink strays (not lettering), so `bean_only_lines` allows the bean. |
| lt_hed_p_e (80 mm) | "The letter e changes stitch type" | e body fill under its keyline loop; its lower stroke satin | **Thread split, stage 2.** The art is one maroon (152, 44, 64); the 0.5 mm stroke reads lighter from anti-aliasing and snaps to a second spool (1335 Dark Rust, 2.4 dE00 from 2011), becomes its own region, and its outline ratio is 0.67 against the body's 2.56. Both periods are 1335 too. |
| Bridge hat (63.3 mm) | "This is the only letter that is thinly stitched" | U of RESTAURANT: run, 5422 Swiss Ivy; its 10 siblings satin, 4531 Caribbean | **Thread split.** A thin blue letter on yellow reads green and snaps 18.4 dE00 off its word. `lettering_thread.stray_word_thread` does not reach it: it is a cluster member, not a stray, and the cluster has two threads. |
| flat_emoji_icon (80 mm) | "right leg infill doesn't match left leg" | legs filled at 11.3 and 180 deg, same spool 1334 | **Fill angle per shape** (stage 5's axis). |
| gradient_mascot (80 mm) | "feet are differnt colors" | feet filled at 39.4 and 134.3 deg (mirror images), same spool 1120 | **Fill angle per shape**; the lit render reads direction as tone (as the 11-12 reader found). |
| devanagari_logo (80 mm) | "the only lettering in-fill" | nothing on main | Fixed by `enclosed_white_skip_transparent` (Kent's 11-11 flip): every white area open, every letter satin. |
| kanji_seal (80 mm) | 28 pins, "some empty spaces have it while others don't" | nothing on main | Same flip: 39 spaces open, 11,139 st. |
| pixel_art_sprite (80 mm) | "some have bean stitching around the openings" | border loops some openings | Not a group threshold: the 15 plain holes clear the 8.8 mm loop floor and are looped; 5 more openings are separate `enclosed_background` regions (the `regular-structure` census), left bare. A tag split, **not fixed here**. |
| lt_k_line | "The tip of the E has ... 3 different stitch angles" | inside one satin letter | Column decomposition of one letter, not a group. |
| MFab F, Bridge handles | | | Not re-traced here (travel and stage-4 shape per the 11-12 reader). |

So the hypothesis holds for two of eleven notes as stated (a tier threshold
straddled inside a line), and in a wider form for four more: thread (2) and
fill angle (2) are also decided per region, with no group. Two are already
fixed on main; three have other causes.

## The rule (`digitizer_core/group_consistency.py`)

GROUP: like shapes on one line, one thread, heights within
`lettering_thread.STRAY_HEIGHT_RATIO`, sharing `STRAY_MIN_OVERLAP` of the
shorter height, within `STRAY_MAX_GAP_H` heights of a member (the stray rule's
own line test), at least `textcluster.MIN_CLUSTER_MEMBERS` (3). No new
grouping constant.

VERDICT: a member more than `MARGIN` (1.5x) off the threshold, either way, is
evidence; the group takes the decided members' side when they agree, the
median's side when none is decided, and keeps every shape's own call when the
decided disagree. A member inside the band follows, unless its shape cannot
take that construction. `MARGIN` is a grouping candidate fitted on this census
(gate 1 does not apply: no machine settles it).

Four flags, all OFF, byte-identical OFF, each separable:

* `cfg.group_consistent_tier`: the run tier's area floor per line. A letter
  moved onto the run tier sews the run its line-mates sew (skips
  `small_solids_satin`, which otherwise sewed K-Line's W and K as one satin
  column each); one moved off it only onto satin `_sews_satin` grants.
* `cfg.group_consistent_outline_body`: the art-outline body test per line of
  like candidates within one outline. A candidate made a body must be
  `machine.MIN_FILL_WIDTH_MM` across on average.
* `cfg.group_consistent_thread` (`lettering_thread.word_thread`): a
  text-cluster letter on a thread held by under a quarter of its word takes
  the thread over half the word sews, within `STRAY_MAX_DE00` (25), and drops
  a dark-ink bean none of its word-mates carries. A pinned recolour never
  moves. A word in two colours by design (two groups of comparable size)
  stays two.
* `cfg.group_consistent_fill_angle` (`group_consistency.shared_angles`):
  ONE angle per group of like shapes -- the biggest member's own, for every
  member, not mirrored for a mirrored pair (Kent read the mascot's feet,
  one spool at 39 and 134 deg, as "differnt colors"). Group: the
  `regular_structure` worker's `meta["congruent_group"]` when present (angle
  relative to each member's `angle_deg`), else one spool, areas within 1.5x,
  elongations within 1.25x. Fill rows only where no rule names an angle.
  Satin crosses only for a tagged, unmirrored congruent group (inert on main
  until the `regular-structure` tag lands): the house angle of a
  non-lettering member with none (the slot `cfg.design_angle` uses), never
  on a column under 0.6 mm. **Measured negative:** the likeness fallback on
  satin (tried first) pushed To a T machine's mirrored satin pair from 9 to
  15 deg apart and turned a 286 mm^2 shape 5.5 deg; on the flag it only
  nudged the stripes 87.2-88.2 -> 87.3-87.4 deg. Neither named satin case
  is reachable here: the flag's 50 stars sit in the lettering house-angle
  group (`fill_angle_deg`, `satin_angle_deg` already written) and sew via
  the fill emitter's small-shape path, where an angle does not set the
  stitch direction; To a T's rule lines are 0.4-0.6 mm, under the guard.
  Lettering and the photo classes are out.

## Proof

OFF byte-identical: lt_ahora 80 mm, design md5 `3108dbd3ea975ff8542d27493b2e499f`
(9,262 stitches) on main and on this branch with both flags off.

ON below is every flag this note builds. Sheets (art | OFF | ON):
`digitizer/eye_pairs_out/group-consistency-1113/sheets/`.

| design (mm, garment) | OFF st | ON st | what changed, by eye |
|---|---|---|---|
| lt_ahora (80, left chest) | 9,262 | 8,732 | AH and RA leave the pink loop and sew satin like O and !: one construction for the word. **Price:** AH and RA are fused in the art, and as one satin shape each they sew rougher than OFF's fills (the A's apex a lump, a zigzag at the A-H foot). |
| lt_k_line (80) | 3,372 | 3,442 | The six satin letters of the grey subline (W, three K's, H, D) sew bean outlines like the other 18; W, K, H and D read cleaner than OFF's satin tangles. |
| Bridge hat (63.3, hat) | 8,569 | 8,594 | RESTAURANT's U: thin Swiss Ivy skeleton bean -> Caribbean satin like its ten siblings. |
| lt_hed_p_e (80) | 3,849 | same md5 | nothing: its e is a stage-2 thread split with no text cluster |
| devanagari_logo (80) | 4,960 | same md5 | nothing |
| kanji_seal (80) | 10,996 | same md5 | nothing |
| Hotel Fremont hat (92.6, hat) | 16,106 | same md5 | nothing |
| ProSeal hat (85.9, hat) | 6,434 | same md5 | nothing |
| Becker hat large (101.9, hat) | 16,289 | same md5 | nothing |

Fremont, ProSeal and Becker were digitized ON with the two tier flags; the
thread flag moves no region on any of them (`word_thread` over their final
regions: 0, 0, 0), so with it they are the same.

The thread rule also drops the moved letter's dark-ink bean when none of its
word-mates carries one: Bridge's U came from the dark-ink lightness read, and
its own mis-snapped green against the yellow is what made it a skeleton bean.

## Not built here

* The (hed)p.e. e and periods: a thread split with no text cluster to group
  by; the fix is at stage 2 (an anti-aliased stroke snapping to a second
  spool 2.4 dE00 off), not here.
* Pixel sprite's openings: 5 are `enclosed_background` regions, 15 are
  plain holes; the bean goes round only the holes.
* AHORA's fused letters: the satin tier sews AH and RA as one shape each. A
  per-letter split belongs to the text tagger's neck split (another worker's
  file).
