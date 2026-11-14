---
name: shaped-outline-gear-2026-11-13
description: "2026-11-13 — `border_from_outline_follow_shape` built OFF (Kent on Commons Ahora: \"now fix the Ahora gear so it sews as a gear\", then \"it's an improvement but not across the board\"): a shaped band is laid out from its OUTER edge (`shaped_band`), a needle hole on every corner and wall end, no line on top"
metadata:
  type: project
---

# A shaped outline follows its outer edge (`border_from_outline_follow_shape`) — 2026-11-13

**What Kent saw.** Commons "Ahora" (`testdata/art/commons_lettering/logo_ahora.png`):
a white gear, 17 teeth, round a yellow disc inside the O. "the ring on Ahora
looks better, but its still a circle and not a gear like the image", then
"now fix the Ahora gear so it sews as a gear". After the first build (#1455):
"Keep improving this feature change, it's an improvement but not across the
board".

**Cause.** `border_from_outline` reads the gear as an outline round the disc
and sews one satin loop of ONE width on the disc's edge. The toothed outer
edge is never looked at.

**First build (#1455, merged, OFF): the needle placed from the WRONG edge.**
It kept `_satin_loop`: stations on the disc's ring, each cross cast outward
and cut at the art, plus a 3-pass bean on the outer edge for corners. Rendered
on the gear at 8 sizes and 5 drawn shapes, every fault was that one choice:
- a tooth got 2 or 3 stitch ends wherever the ring's stations cast them, none
  on its corners; yellow showed inside every tooth;
- crosses from a small ring fan: 0.3 mm apart on the ring is 0.5 on the tooth;
- nothing pivoted round a square corner of the body (a notched frame's
  corners were left to four stitches);
- the bean sat half a thread outside the art and made 0.6 mm teeth lumps
  (60 to 80 mm);
- 40 and 50 mm were not taken at all.

**Second build (`digitizer_core/shaped_band.py`, same flag, still OFF).** A
band round ONE body is laid out from its outer ring:
- a needle hole on every corner (`CORNER_DEG`) and on both ends of every SIDE
  WALL. A wall is read off the edge: a stretch within 30 degrees of its own
  crosses that steps the thickness by `SATIN_SHORT_STITCH_AT_MM` or more.
  Vertex angle alone is not enough: a TRACED tooth has rounded corners (two
  or three shallow vertices) and the real gear at 60 mm stayed ragged until
  walls were read this way;
- between holes, spacing is measured SQUARE TO THE STITCH (lateral length /
  density): a wall gets nothing between its ends, tips and roots get 0.4 mm;
- each hole's ring partner is the nearest ring point, never stepping back;
  round a square corner they pile on it (the fan);
- ring holes that bunch are short-stitched by the LEAST pull that clears the
  two before (the full 0.35 pull halved the ring edge's cover in the roots);
- a wall is sewn once: its second end is reached along the wall, outer hole
  to outer hole (two crosses there were one line laid three times);
- no line on top.
- Shaped threshold `art_outline.SHAPED_MIN_SWING_MM`: 0.5 -> 0.3
  (`SATIN_SHORT_STITCH_AT_MM`: a step two holes can show). Between 0.3 and
  0.5 the swing must be STEPPED: `shaped_band.stepped_share` (share of the
  thickness change where the edge runs within 30 degrees of its crosses) at
  least half. Without it the lower threshold took "(hed) p.e."'s white
  keyline at 180 mm (0.57 to 0.92 mm thick, share 0.09: a line of uneven
  width, the pro's widened loop). The gear at 40 mm is 0.76, at 50 mm 0.78.
  Found by the logo scan, not by a test.
- A band `shaped_band.sews_shaped` takes is kept out of the hairline mark:
  that gate's width is 2A/P and teeth are perimeter, so the gear at 40 mm
  (0.57 to 0.93 mm thick) read 0.6 and sewed as a thin ring with the ground
  showing where the teeth were.
- A band shared by several bodies keeps the first build's ring-cast loop.

**Measured.**
- Drawn shapes, bare band / thread past the art (0.4 mm thread), OFF -> ON:
  12-tooth gear 5.6% / 10.1 mm2 -> 0.3% / 0.00; 24-tooth 4.4% / 5.2 -> 0.0% /
  0.00; scallop 5.1% / 9.1 -> 0.6% / 0.00; notched frame 10.0% / 5.8 -> 0.1%
  / 0.00.
- The real gear, 40 to 160 mm wide: 17 teeth at every size, on the traced
  outline. White satin points 40 mm bean 50 -> 80, 60 mm 78 -> 131, 100 mm
  125 -> 195, 160 mm 192 -> 283. Design at 100 mm 13,095 -> 13,185 points.
- Scan, flag ON, every repo logo with an outline loop (To-a-T, Becker, MFab
  hat and LC, hed, K-Line, beanie, Bridge): none taken but the gear.
- Size table: `docs/scope/1-auto-digitizing-quality.md`, same heading.

**Traps.**
- My renderer draws round thread caps 0.2 mm past each needle hole, which
  makes a satin edge look lumpier than a run on top of it. The first build's
  bean looked crisp at 100 mm for that reason. Judge on the close-up with
  needle holes drawn, not the thumbnail.
- `python board.py ... gear` is 16 digitizes, about 20 min on a loaded laptop.

**Open.** Pull on a 0.6 mm tooth is a sew-out question (gate 1). The closing
overlap (1.4 mm) is a dense patch on a 5 to 7 mm gear, as it is on every
loop. A band with a FEW notches (under 10% of its ring) is not shaped by the
p90 - p10 rule. A star round a disc is not read as an outline at all. The
flip is Kent's.

Related: [[hairline-keyline-bean-2026-11-13]], [[eye-first-diagnosis-2026-11-13]],
[[border-from-outline-line-art-guard-2026-10-25]].
