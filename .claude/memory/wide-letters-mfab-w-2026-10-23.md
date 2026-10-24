---
name: wide-letters-mfab-w-2026-10-23
description: MFab's W of WELDING never reached the Column lane for two stacked reasons in stage 4's text tagger, not the lane — it touches the E through the keyline (one region, aspect 2.55) and is wide on its own (1.58), both past the letter door's ASPECT_RATIO_MAX 1.4. Built as `text_cluster_wide_letters` (OFF): neck split + wide-glyph adoption. Measure MFab with the main checkout's rembg venv.
metadata:
  type: project
---

2026-10-23, lane `mfab-w-segmentation-bff5f7` (task L5). Renders and the
stage-by-stage trace: `docs/renders/mfab-w-wide-letters-2026-10-23/`.

**Where the W drops out.** Stage 1-3: the W's right vertex and the E's foot
meet through the keyline (2-3 anti-aliased px at 3.9 px/mm), so SLIC and
the masks make them one black region. Stage 4: `S6ee94d7e`, 17.5 x 6.9 mm,
aspect 2.55 (an opening at r 0.03 mm parts it: a touch, not a stroke).
`textcluster._letter_candidates` refuses anything over `ASPECT_RATIO_MAX`
1.4, so no `text_candidate`, no `lettering_group`, and `columns.is_lettering`
is false: the satin ladder sews W+E as one shape (343 mm of satin outside
it). Split by hand, the W ALONE is still 1.58 (its lead-in arm): two
conditions stacked, and fixing either alone does not tag the W.

**The photo path changes the picture.** With rembg (main checkout) the A
and N of AND also touch (aspect 1.76), the D is left short of three, and
the whole word is untagged. A worktree has no rembg venv, so the 10-23 band
captures (from worktrees) had AND separate. Point
`stage1_photo_prep.REMBG_VENV_PYTHON` at the main checkout's venv before
measuring MFab from a lane (see [[seeds-request-and-the-worktree-blind-spot-2026-09-22]]).

**Built OFF:** `cfg.text_cluster_wide_letters` -- `_neck_split` (a too-wide
region beside a line cut at necks under a quarter of its stroke; kept only
if every piece is tagged) and `_adopt_wide` (aspect 1.4-1.8 joins a tagged
line, never makes one). MFab hat ON: W 8 -> 4 columns (pro 7), 263 -> 149
stitches (pro 154), 0 travel off the letter (was 67.5 mm); design 11,605 /
65 -> 11,375 / 62. Sized over the paired jobs at the pro's widths: ON is
md5-identical on Becker, Fremont, Gaulke and Bridge; MFab LC's W (alone,
aspect 1.49) is adopted; six letters over the two MFab files, nothing
elsewhere. MFab LC's N of AND is untagged for a DIFFERENT reason (height
ratio 0.79 against `LETTER_HEIGHT_RATIO` 0.8) -- not fixed here.

**Why:** the lettering week's Column-lane work could not reach letters the
tagger never admitted. **How to apply:** when a letter "never reaches the
lane", check `text_candidate` / `lettering_group` on its region first, and
its aspect against 1.4, before touching `columns.py`.

Related: [[lettering-5-10mm-band-2026-10-23]], [[column-corner-folds-2026-10-23]],
[[word-tagger-l1-2026-10-08]].
