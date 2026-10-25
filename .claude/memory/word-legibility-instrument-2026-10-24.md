---
name: word-legibility-instrument-2026-10-24
description: tools/word_legibility.py reads each pinned word of ours and the pro's file at native/4/7/12 mm, chance-corrected; the pro's small words are the hard part to find, MFab scores nothing
metadata:
  type: project
---

`digitizer/tools/word_legibility.py` (PR for I3, 2026-10-24). Per word: crop ours and
the pro's file each in its own frame, tesseract psm 7, `cc = (raw - base)/(1 - base)`
with `base` = E[ratio(read, shuffle(known text))] (gate 4). No engine change.

**What it found.** At 7 mm and up the thread reads: Fremont ours 1.00 over 8 words
(pro 0.93 over the 5 it could locate), ProSeal 1.00 both. Real gaps: Becker ours
+0.04 native (pro +1.00; ours' bodies read as grey hatch, `BECKER` art ceiling 0.00
so tesseract cannot read the art either), and 4 mm (Becker, Fremont FREMONT ours
0.00 vs pro 1.00). The instrument is COARSE: most cells saturate at 1.00, so it is a
tripwire for "reads / does not read", not a grade.

**What it could not do.** MFab scores NOTHING (all 8 cells not located): the lettering
is white keyline on the art's white ground, so the art word mask and the thread
disagree (best match costs 2.3-2.5 > 2.0). Pro 1895 / STAY / PLAY (Fremont) and
SPRAY FOAM (ProSeal) are not located either: the pro sews them bigger, bolder and
touching the rope. A not-located word is reported `n/loc` and left OUT of the figure,
never scored 0 (that would score the locator).

**Traps found building it (each cost a run):**
- A DST has no thread colours: the pro's render is one black block. Use the `.PES`
  (Fremont, MFab, Becker); ProSeal only has a DST.
- A correlation shift of the art word onto the pro's thread latched onto the rope and
  read the pro's EST as nothing. The locator now fuses each spool colour's letters and
  scores candidates on aspect, size, place and `shape_sim` to the art word.
- Pro files carry 12 mm travel stitches (Fremont three) that weld FREMONT's R to the
  border; `drop_travel` (9 mm) for both files.
- Our file's registration to the art is EXACT (plan frame, `exact_registration`); a
  fitted one was half a Becker line off.
- Scaling a stitch layout UP opens gaps no engine would sew, so heights are SHRINK
  ONLY; a word shorter than H is not read at H.
- Windows has tesseract 5.4.0 (bash PATH) although the brief says none; the WSL box
  would not start (`CreateVm ERROR_TIMEOUT`), so the PR numbers are 5.4.0, not CI's 5.3.4.

**How to apply.** Put a `cc` beside a lettering PR's render with
`--digitize` then `--read`; compare only words scored in BOTH files (`both:` rows).
Pin new words in `testdata/word_legibility_words.json` (text + art-ink-box fractions
only; Kent's art is not committed). Related: [[glyph-legibility-instrument]]
