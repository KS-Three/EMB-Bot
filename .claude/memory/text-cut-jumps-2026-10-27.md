---
name: text-cut-jumps-2026-10-27
description: `cutEveryJump` (built OFF) on buildLetteringDesign, the JS twin of `cut_every_jump`: typed names float 1-3 mm hops in every DST path; ON buries, walks or cuts each (95% cut: bare cloth), trims about double; oracle samples 10x finer than Python's walk
metadata:
  type: project
---

Typed lettering leaves one or two DST jump records (a float no machine
cuts) wherever a hop is under `trimAtMm` (3 mm). Measured from the BYTES on
both export paths, 1 in 7 of 85 fonts x 3 names x 50/90 mm x cap/left chest
(143 designs, `node tools/lettering-uncut-jumps.mjs --every 7 --on
--pystitch <venv python>`): 2,216 uncut moves, and the stream, the browser
DST (own reader, src/dstimport, pystitch) and the service /export DST (all
three readers) agree on every row. 1,225 are inside a glyph, 991 between
glyphs; their straight thread lies under later thread on 126, on sewn
thread on 97, on bare cloth on 1,993. Heavy tail: mai_en_fleur 307 on one
cap name (its glyphs come apart at 50 mm into pieces joined by travel).

`cutEveryJump` (src/digitize.js `cutOrBuryJumps`, built OFF 2026-10-27;
Kent 2026-10-26: OFF-beside-ON arm on sew-out card v8 with the Python flag,
neither flips alone): bury under later thread, else walk on sewn thread
(travel is not cover, as in Python), else trim before the jump and let
`applyTies` lock both sides. ON on the sample: 46 buried, 58 walked, 2,110
cut; trims 2,184 -> 4,294, stitches +6.3% (8 lock stitches a cut); 0 uncut
moves in the DST; all 4,294 trims locked both sides.

- **The oracle earned its keep twice.** (1) Python samples a hop every
  0.1 mm (`_BURY_STEP_MM`); a raster of the DST at 0.01 mm found 17 sewn
  segments whose centre ran along a satin rail and dipped up to 0.015 mm
  off the thread between stitch tips. The JS walk samples every 0.01 mm
  (`COVER_STEP_MM`) and judges the legs AS WRITTEN (rounded), not the
  straight hop. Python's twin has the same 0.1 mm blind spot: unmeasured.
  (2) A glyph part that is ONE penetration (neon's apostrophe) between two
  new cuts lays no thread and takes no lock: it is left out with one cut
  (`lone`, 2 on the sample).
- Locks are judged by centreline only: a lock rides the stitch it locks,
  and its far point rounded to 0.1 mm puts one edge up to 0.035 mm past
  that stitch's edge, in OFF files too.
- OFF pin: md5 of all 85 fonts' DSTs, literal garments, explicit width and
  a FROZEN flag dict, so neither #1118's auto-fit nor a later flip moves it.

**Why:** the brief's 28.8 floats a name counted the stream; the bytes agree,
so the problem is real on every path, and the cure costs about a cut per
float. **How to apply:** judge a walk with the oracle at file units before
trusting a sample step; the flip is Kent's, after card v8. Related:
[[cut-every-jump-2026-10-21]], [[cut-after-bury-2026-10-23]],
[[layout-judged-in-preview-2026-10-22]].
