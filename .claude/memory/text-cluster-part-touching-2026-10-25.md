---
name: text-cluster-part-touching-2026-10-25
description: Task 5 "letters the tagger misses": Fremont OTE/NT is NOT a tagger miss (trace apart, all tagged; O+T touch only in the sewn file). MFab's are: hat IN touches at a <0.08 mm neck and passes as ONE letter, LC's AND N overshoots the cap (0.79). Built OFF as `text_cluster_part_touching`; ON sends LC's N into the bean-letter keyline misread.
metadata:
  type: project
---

2026-10-25, lane `tagger-fused-serifs-e5a440`. Doc
`docs/text-cluster-part-touching-2026-10-25.md`, renders
`docs/renders/text-cluster-part-touching-2026-10-25/`.

**Premise half false.** #1051 said our serifs fuse Fremont's OTE / NT. At the
pro's width (hat and patch, rembg on) all 12 HOTEL FREMONT letters trace as 12
regions and are all `text_candidate`. Only the SEWN file fuses O+T (board reader
11 components vs the pro's 12), and it is PULL: trace gap 0.62 mm at the O's flank
vs the T's hanging serif, our needle paths 0.14 (0.40 of the 0.48 closed is the
0.4 mm pull comp), no serif overshoot; the pro keeps 0.36. Gate 1, not layout.
Check the trace before blaming the tagger for a fused read.

**What the tagger does miss (MFab).** Hat: I+N of WELDING touch at a neck under
0.08 mm, one region of aspect 1.03 the door admits as ONE glyph -- the wide pass
(#1060) only looks past aspect 1.4. LC: AND's N is 7.90 mm beside 6.25 mm letters
(ratio 0.79 < 0.8), untagged; WELDING's N (0.77) and G (0.71) house-group only.
The face's N and G overshoot the cap band (spike, tail); a letter of another line
sits above or below it.

**Built OFF:** a touch under `TOUCH_MAX_MM` 0.15 between letter-height pieces
parts any region beside a line (cut by the wide pass's stroke rule, so its
pieces are the same; the absolute bound only JUDGES the neck -- cutting at
r 0.075 left a straight-edge sliver in the neck on synthetic L's); a taller glyph
spanning a member's cap band joins the line down to ratio 0.6, never makes one.
Sized on six jobs: touches part at r 0.02-0.04, letters never below r 0.125.

**ON:** Fremont, Drone, ProSeal md5-identical; MFab hat I gets its own clean
column (trims inside letters 8 -> 5); LC 16 -> 12 trims, but AND's N goes HOLLOW:
the cluster sews as bean letters under the true-size switch (line 0.5 mm) because
`beanletters`' ink read gives 0.44 mm on a letter traced 1.23 mm wide (the art
draws white faces in a thin black outline). The A is already hollow OFF; the pro
sews A/N/D satin. **Don't flip before that.**

**OFF is md5-identical to main on all six** -- but MFab hat twice read `7296b420`
(11,855 / 67) on a loaded laptop: rembg ran past its 60 s timeout, the pipeline
dropped the whole photo prep, and the plan said `PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE`.
Raised to 600 s the same tree reads `3673370d`. Check that warning before calling
a photo-path md5 mismatch a regression.

**How to apply:** capture the regions entering `detect_text_clusters` (wrap it in
the pipeline module) and re-run the tagger OFF/ON offline in seconds -- the six
full digitizes took ~40 min a set on a loaded laptop. For pro per-letter reads,
fit the letter locally (his lettering sits up to 0.8 mm off the whole-design
registration) and read `letter_pieces` crosses on the letter's own block, never
column counts in a box (MFab's white keyline wins the block vote).

**ON since 2026-10-27, Kent's flip** from the wave-5 sheet, together with
`bean_ink_outlined_letters` ("Both ON (Recommended)"), which cures the LC N
misread above; [[outlined-bean-ink-2026-10-27]], [[flip-sheet-wave5-2026-10-27]].

Related: [[wide-letters-mfab-w-2026-10-23]], [[lettering-5-10mm-band-2026-10-23]],
[[word-legibility-instrument-2026-10-24]], [[lettering-board-2026-10-25]].
