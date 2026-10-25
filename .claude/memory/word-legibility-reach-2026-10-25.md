---
name: word-legibility-reach-2026-10-25
description: word_legibility.py's two holes fixed -- every pinned word (17, 4 jobs) is located in both files, and `reach` (octaves a word survives shrinking, from cc) moves where cc sits at 1.00; the crop's neighbours, not the lettering, were why the pro's small words read as nothing
metadata:
  type: project
---

`digitizer/tools/word_legibility.py`, PR for the `legibility-small-words` brief
(2026-10-25), no engine change. Full tables: `docs/word-legibility-reach-2026-10-25.md`.
Builds on [[word-legibility-instrument-2026-10-24]] (its numbers: pass `--no-ladder`
for cc only, but the crops and locator are new, so Fremont/Becker cc moved).

**Why the words were `n/loc` (none of it the size floor, the OCR scale or the fit).**
(1) MFab's pro sews WHITE thread over a black bed; `drop_ground_blocks` dropped every
ground-coloured stitch as "cloth" -> `keep_visible_ground` keeps it where thread lies
under it. (2) Fremont's pro STAY / PLAY / 1895 sit on a thin run that ties them to the
rope: one piece 10x the word, thrown away whole -> `_pieces` peels it (0.35 mm opening).
(3) ProSeal's SPRAY FOAM beside its + (same gap as the word space) and COATINGS found
as COATIN -> `_run_candidates`, maximal runs of letter pieces. (4) MFab's outlined
lettering is welded to a black bed in a thread mask -> `visible_masks` (what shows of each
spool), else the art's own place when the thread there LOOKS like the art's word
(`appearance_sim >= 0.5`, `loc: registered`). (5) the cost charged 0.9 of its 2.0 for a
word the pro re-set 2.4x bigger -> `SIZE_WEIGHT` 0.25.

**The trap that cost the most: the CROP.** The words it newly found read as nothing
(pro STAY `7`): a black bar 1 mm away sets Otsu's threshold above the orange letters,
so they binarise to cloth. A tight view (0.5 mm of neighbours) fixes that and BREAKS
BECKER (black letters in a grey outline binarise apart only beside the next line's
grey: pro wide `BECKER` 96, tight `M7E7SSA` 40; ours the other way). So every crop is
read in BOTH views x the 3 variants, most confident wins, wide on a tie. Becker's old
"ours +0.42 vs pro +1.00" gap was this crop effect, not lettering.

**`reach`.** Shrinking the LAYOUT (4/7/12 mm rows as a ladder) was tried and dropped: it
scored the pro's 4.95 mm EST below ours' 2.45 mm (a bold layout's counters close at
once). Shown smaller as a PICTURE (half-octave steps to 3 px) is kept: `reach` = area of
cc against log height, octaves; `floor_px` = smallest height still read (size-free).
Fremont ours 3.73 / pro 4.27 (EST, 1895, STAY are the pro's 2x-bigger re-sets), ProSeal
4.71 / 4.56 (ours' 3.5 mm SPRAY FOAM reaches the pro's 5.2 mm), Becker MARINE 4.25 /
5.94. A floor of 6 px SATURATED (tesseract reads most words at 6 px); 3 px does not.

**Do not quote MFab or BECKER as lettering verdicts.** MFab's four words read 0.00 off
the ART; `blind_words` drops the ones nothing reads (MFAB, LLC) and the board shows
`n/a` with that reason. BECKER reads 0.00 off the art and flips with the crop.

**Speed.** A tesseract start is 5 s on Kent's laptop (0.03 s CPU): `read_crops` reads
every crop in a few list-of-images runs (`tesseract list.txt out --psm 7 tsv`), 4 in
parallel, falling back to `read_crop` if a run returns the wrong page count. Same text,
`cc`, `raw` as one-by-one on 55 rows; conf is truncated to ints as pytesseract does or
a tie between variants breaks the other way (that changed one art ceiling).
Kent's box HAS tesseract 5.4.0 (CI 5.3.4): quote the version.

**How to apply.** `--read JOBS --cache DIR [--dump DIR]`; `--dump` writes
`<job>_<file>_located.png` (blue = where the art says, green = found): LOOK at it before
trusting a located word. The board's new column is `reach` (octaves), beside `cc`.
The board baseline `docs/scoreboards/lettering-board-2026-10-25.*` was NOT regenerated;
Becker and Fremont `cc` cells moved under the new crops, so compare only boards run
after this PR. Pin new words in `testdata/word_legibility_words.json`.
