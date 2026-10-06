# Outline-cut columns: a spike on "lettering looks like worms" (2026-10-05)

**Status: spike only.** Nothing here is wired into the pipeline, nothing is
sewable, no default changed. The code is four standalone scripts in
`digitizer/tools/outline_cut_spike/` on lane `claude/outline-cut-columns` (cut
from `origin/main` at `838c3451`); nothing in the engine imports them. The
inputs (`<logo>.pkl`) and every render live in `scratch_outline_cut/` in that
worktree, which is gitignored and NOT backed up: they hold client artwork and
this repo is public. `run.py` regenerates the inputs.

## Why

Kent, 2026-10-05: digitized lettering "looks like worms"; he wants
"structured, smooth flowing lettering". Four research agents ran first
(prior-work map, a fresh measurement on seven logos, pro practice, recognition
algorithms). Their findings, then his two decisions, set the direction.

## "Worms" is three defects, by letter size

Measured on seven logos at shipped defaults (see "Caveats" for which engine).

| | What it is | Where | Measured | The pro's file |
|---|---|---|---|---|
| A. Patchwork | one letter sewn as several satin slabs at unrelated angles, crossing mid-stroke | bold caps and script, all seven | Becker MAR: 16 satin runs over 3 letters, 3-4 directions per letter, 48% sewn twice | one column per stroke, mitred at joins, stitches fan round a bowl |
| B. Tube letters | ~2 mm caps sewn as a bean run round the OUTLINE | Fremont EAT/STAY/PLAY, EST 1895; Enthusiast ENTERPRISES | 17 of 17 glyphs on the run tier, 0 satin | 0.8-2 mm satin columns, text slightly enlarged |
| C. Halo strands | anti-alias colours sewn on top of single-colour text | Gaulke, bridge, drone | 23-30% of the stitches in Gaulke's text are not black | one colour |

Second order: rails about twice as rough as the pro's (11 of 15 word boxes).
Width wander is NOT a difference from the pro; do not chase it.

**Kent picked A first.** B and C are not started. C has an existing global
flag (`dissolve_phantom_blends`, OFF, his verdict mixed) and would need a
text-scoped version. B's width floor is a sew-out constant (ROADMAP gate 1).

## The idea

Three agents reached it independently: every commercial letter builder found
(Wilcom, Embird, Ink/Stitch, the expired Viking patent US6934599) takes a
column's rails FROM THE OUTLINE and uses the skeleton only to decide where to
cut the letter. The engine does the opposite (rails = skeleton plus or minus a
smoothed width), and that model was already measured at its floor
(`rail-wobble-is-the-models-floor-2026-09-21`).

So: cut the letter's outline into stroke pieces at its concave corners; each
piece's rails are stretches of the outline itself.

## What the spike does (`scratch_outline_cut/oc.py`, pass 18 plus the ring fix)

Preparation, per letter polygon:

- Drop pinhole holes under 0.05 W^2 (W = 2 x area / perimeter). One sat exactly
  on the corner of Becker's A counter and blocked every cut from it.
- Simplify by max(0.12 mm, W / 16). Becker's 146 px trace otherwise reads its
  own lumps as junctions.

Corners: turn summed over W / 8 of outline, so a chamfered or two-vertex
corner is one corner and a curve's vertices are not. Concave at 55 degrees,
convex at 35. Concave corners closer than 0.25 W are one; a dent with no edge
of 0.25 W either side is ignored.

Cuts, in priority order:

1. **Through.** Two concave corners joined by a segment that continues an edge
   at BOTH ends (alignment over 0.94): a stroke butting a through-stroke. T
   stems, crossbars, R's bowl.
2. A lone concave corner cuts only at an **elbow**: a convex corner of 45+
   degrees lies across it (0.6-2.6 W away, within about 53 degrees of the
   bisector, visible). With no such corner the stroke is bending, and it is
   not cut. This is what stops an S being chopped.
   - **Mitre** to that corner when the two edges are comparable (ratio under
     1.6), it sits on the bisector (over 0.9) and is within 1.8 W.
   - Else **extend the longer edge** through to the far side (accepted when the
     cut is no longer than 1.5 x that edge). A stem keeps its full height and
     the diagonal butts it. These cuts are legitimately long; an earlier cap in
     stroke-widths was wrong.
3. Crossing cuts: lower rule number wins, then shorter. A cut that only shaves
   off a piece under 0.4 W^2 is taken back out.

Stitching a piece:

- **Straight** (its own non-cut outline edges agree on a direction, or its
  skeleton chord is straight): stitches square to that axis, each end exactly
  on the outline, axis snapped upright within 7 degrees. A serif bump is
  absorbed into the stem's column.
- **Curved**: two outline arcs paired by dynamic time warping (the monotone
  matching with the shortest stitches), pitch held on whichever rail is
  moving, so the outside of a bend stays covered and the inside takes the
  short stitches.
- **Still wraps a counter** (an O, an uncut bowl): outer ring against the
  counter's ring, both started at the thinnest place. Before this an O sewed
  straight across its hole.

## Results

Becker MAR and Gaulke INDUSTRIES were the tuning fixtures. On those the M
(two stems, two mitred diagonals), A (two legs, crossbar), R (stem, bowl,
leg), and I, N, D, U, T, E, and the last S match the pro's construction.
Kent, shown R / D / U / I / E at pass 3: "Yes, keep going."

All seven logos, rules untouched, text-tagged shapes only (`batch.py`):

| Logo | Letters | Clean | Thread off the art | Over-long stitches |
|---|---|---|---|---|
| Becker | 11 | 9 | 2.3% | 23.9% |
| Gaulke | 39 | 30 | 0.2% | 5.9% |
| Drone | 22 | 19 | 0.0% | 7.4% |
| Enthusiast | 24 | 21 | 0.0% | 0.6% |
| Fremont | 32 | 21 | 0.2% | 3.2% |
| Bridge | 8 | 5 | 1.3% | 3.1% |
| Tires | 0 | - | - | - |
| Total | 136 | 105 | | |

No crashes. **"Clean" is the spike's own check** (every piece sewn, under 2% of
thread off the artwork, under 5% of stitch length in stitches longer than
max(2.5 x the piece's width, 1.6 W), over 90% covered). It is not Kent's eye
and must not be quoted as a quality figure.

Fremont's HOTEL FREMONT (slab serif) and Drone's PRECISION / THER were never
tuned on and came out as structured strokes.

Failure classes, largest first:

1. **Compound pieces left uncut, then fanned.** Becker MARINE's E and N,
   BECKER's B, R, K. This is Becker's 24%. A piece whose stitches run far
   longer than its stroke is wide is the tell; use it as the trigger to look
   for another cut.
2. **Blob outlines from low-res input.** Bridge, and BECKER's outlined band.
   The letter is not letter-shaped before construction starts. No cut rule
   fixes this.
3. **Strokes under about 0.5 mm.** They sew, but a column that thin means
   nothing. That is defect B's tier.
4. **Script is not text-tagged**, so Tires and "Bridge" never reach it.

Also still wrong: Gaulke's first S (its trace is a blob at the top, and two
lumps pair as a false through cut), one N in Fremont, stubby ends.

## The second look (2026-10-06)

Failure class 1 above, taken on. After the junction rules, any piece that
still sews more than 12% of its thread in over-long stitches is looked at
again (`_refine`): every concave corner of that piece offers three cuts (each
edge continued, and the bisector), each is tried, and the one that leaves the
least over-long thread is kept if it takes it below 60% of what it was. Up to
three deep. No scrap under 0.4 W^2.

**The yardstick had to change, and that makes the two tables not comparable.**
"Over-long" was first measured against the piece's OWN width (2.5 x). A
compound piece is wide by its own measure, so the check passed exactly the
letters it existed to catch: with that yardstick the run read Becker 11/11 and
0.1% over-long while MARINE's N and E were, on the sheet, still fanned and
unchanged. It is now 1.6 x the LETTER's stroke width, in both the trigger and
the check.

| Logo | Clean | Over-long stitches | (first table) |
|---|---|---|---|
| Becker | 6/11 | 9.5% | 9/11, 23.9% |
| Gaulke | 27/39 | 5.2% | 30/39, 5.9% |
| Drone | 20/22 | 0.2% | 19/22, 7.4% |
| Enthusiast | 17/24 | 0.6% | 21/24, 0.6% |
| Fremont | 16/32 | 2.1% | 21/32, 3.2% |
| Bridge | 4/8 | 21.5% | 5/8, 3.1% |

Read the over-long column, not the clean count: the count fell because the
check got stricter, not because the letters got worse. On the Becker sheet
(looked at): MARINE's N is now left stem, diagonal, right stem; its E is three
pieces instead of one fan; all six MARINE letters pass. All five failures are
the outlined BECKER band letters, whose traced outlines are lumps. Bridge got
worse (21.5%): its blobs now get cut, and cutting a blob does not make it a
letter. The stricter yardstick also flags slab-serif bars that are honestly
wider than the letter's mean stroke, so some Fremont and Enthusiast failures
are the check, not the construction. Those sheets were NOT looked at after
this change.

The lesson is the repo's usual one: a check that is tuned on the thing it
measures passes it. The sheet caught this; the number did not.

## Tried and backed out

- Close/open buffering of the outline to remove notches: wrecked the M's crotch.
- "Through" with one loose end: false pairs on M and N.
- Stitching curves square to a smoothed spine: a starburst on S, gaps on bowls.
- Telling S from R by the length of the straight edge leading into a corner:
  measured, no separation (S 1.45-1.57 W, R 0.53-0.66 W).
- Cut-length caps in stroke-widths: reject the stem-side cuts an M needs.

## Not built

Underlay, sequencing and travel, pull compensation, the wide-column split, tie
stitches, any pipeline wiring. When it is wired in it lands default-OFF and is
shown to Kent as labelled before/after pairs; the flip is his.

## Caveats

- The input polygons and the "engine today" renders come from a run on the
  main checkout at `cf9f89f1`, which was 135 commits behind `origin/main`
  (`satin_cap_recentre` is ON upstream, OFF there). Rerun on current engine
  output before any before/after claim.
- Becker's upload is a 146 px trace; the pro did not digitize from that file.
- Sheets actually looked at after the ring fix: Fremont, Bridge. Becker and
  Drone were looked at before it. Gaulke and Enthusiast sheets were not looked
  at in the all-logo pass at all.
- Every threshold above was set on two words.

## Open questions

- The repo's lettering plan says the pro stacks MORE layers at junctions;
  Wilcom's own help says never more than two strokes on top of each other.
  Reconcile (underlay versus cover may be counted differently) before junction
  overlap work.
- Adobe US11704848 (active to about 2041) covers "filled path -> medial axis ->
  stroke width -> stroked path". Outline-cut is a different method; a
  ribbon-refit alternative would sit closer. Only a summary of claim 1 was
  read. Counsel's question.
- Wilcom's "Match Ends" leans a diagonal's stitches the full way to its end
  cut; the house rule caps lean at 30 degrees. Unresolved; the spike sews
  diagonals square to the stroke.

## How to pick this up

The worktree has no venv; use the main checkout's Python.

```bash
cd "C:/Users/EE-LT-11030/Claude Personal/EMB-Bot/.claude/worktrees/outline-cut-columns/scratch_outline_cut"
PY="C:/Users/EE-LT-11030/Claude Personal/EMB-Bot/digitizer/.venv/Scripts/python.exe"
"$PY" run_spike.py becker S32b446a3,Sbf7cf86a,Sa1103fec mar.png     # M, A, R: cut plan over thread
"$PY" batch.py                                                       # all seven -> sheet_<logo>.png + numbers
```

- `oc.py` the construction; `run_spike.py` one word with the cut plan drawn;
  `batch.py` all seven with the self-check; `run.py` regenerates the
  `<logo>.pkl` inputs. The scratch folder holds the working copies and the
  inputs; the committed copies in `digitizer/tools/outline_cut_spike/` are the
  same code with machine paths removed, and expect the `.pkl` files beside
  them. `wlib.py` (scratch only, not committed) loads the pro's files from
  `scratch_kent/`.
- `MAR_three_way.png` and `INDUSTRIES_three_way.png`: engine / spike / pro.

Next, in order: (1) look at every sheet after the second look, Fremont and
Enthusiast first, and decide whether the 1.6 W yardstick is flagging real
faults or honest serif bars; (2) the E as stem plus three arms, not three slabs;
(3) rerun on current-main polygons; (4) wire into stage 6 default-OFF with
underlay and sequencing; (5) labelled pairs for Kent.
