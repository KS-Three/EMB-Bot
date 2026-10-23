---
name: lettering-5-10mm-band-2026-10-23
description: The 5-10 mm lettering band read per letter against the pro on four paired jobs (Fremont, Drone, Proseal, MFab): width and curve pitch are the pro's; the construction gap is corners (pro folds one column round a corner, ours cuts and butts); the legibility gap was Drone's O sewn shut — a transparent counter split into two colour regions fails tag_enclosed_background's second ratio; `enclosed_alpha_hole_parts` built OFF
metadata:
  type: project
---

2026-10-23, session on branch `claude/pull-comp-by-stroke-61868c` after #1045.
Doc `docs/lettering-5-10mm-2026-10-23.md` (per-letter table, reader rules),
renders `docs/renders/lettering-5-10mm-2026-10-23/`.

**The band's jobs:** Fremont HOTEL FREMONT 7.5 mm, Drone PRECISION 6.3,
Proseal PROSEAL 9.4, MFab AND WELDING 7.1 — all at the pro's hat width.
**Becker has nothing in it**: MARINE is 13.2 mm in the pro's 76.5 file; the
brief's "4 to 5.6 mm" was MARINE's sewn STROKE from the pull note, not a cap.

**Read the same way on both DSTs** (a scratch reader over
`small_text_columns.pieces`; rules copied into the doc). The pro's columns
must be read with short stitches SKIPPED: his inner rail short-stitches a
tight ring, which breaks strict side-alternation, so `letter_band`'s
`_short_columns` cuts his one O into a dozen pieces and reads most of his
satin as "underlay". Ours is cut into the pro's letter boxes, because at
1.0 mm opening our serifs fuse letters (OTE, NT) that his do not.

**What is NOT a gap at 5-10 mm:** sewn width (within 0.1 mm per letter on
every word), curve outer-rail pitch (0.40-0.42 vs 0.36-0.41, #650 closed it),
underlay kind (centre run both sides). What is: the pro short-stitches a
ring's INNER rail (Fremont O 0.22 vs 0.45); he FOLDS one column round a
corner where we cut and butt (ours 156 columns / 242 butts / 75 gaps to his
134 / 195 / 54 over 38 letters; Drone trims 17 vs 9); he sews an N/M
diagonal with crosses square to the line of text like the stems.

**The legibility gap and its mechanism.** Drone's O sews as a solid blob.
Its polygon CARRIES the 4.1 x 3.4 mm counter; two regions (7.1 and 4.9 mm²)
sit in it in the letter's own thread, stitched. The counter is transparent;
`alpha_edge_extend` paints it with the nearest opaque colour, light from the
letter's top edge and dark from its chrome bottom, so it vectorizes as TWO
regions, and `tag_enclosed_background`'s second ratio (component mostly
this region: 0.51, 0.36 vs 0.6) fails for each — fail-open sews both. The
P and R counters are one region each and stay open. Not a lettering-lane
defect at all: a stage-4 tagging rule meeting a stage-1 flag.

**Built OFF: `cfg.enclosed_alpha_hole_parts`.** On the alpha path a region
is tagged when IT is mostly inside one transparent component (first ratio
alone); colour path unchanged. Layout → ON-eligible from renders (Kent's
10-22 ruling). `tests/test_enclosed_alpha_hole_parts.py`: a two-tone ring
with a transparent middle reproduces the defect OFF and is cured ON. Price
on every alpha fixture is in the doc.

**Traps:** a word's trims/travel must be read from runs that TOUCH the
word's letters, not from the block's first-to-last stitch — our white block
holds the whole design and read 1,585 mm of "travel" the first time. The
Drone art is 41.7 mm tall where the pro's design is 63.8: he re-laid the
badge out, so nothing registers by y between art and pro.

Related: [[lettering-architecture-2026-10-07]], [[lettering-thickness-fremont-2026-10-06]],
[[pull-comp-by-stroke-2026-10-22]], [[layout-judged-in-preview-2026-10-22]],
[[edge-wobble-is-satin-rails-2026-09-19]].
