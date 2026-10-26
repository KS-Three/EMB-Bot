# Word legibility: why the small words were `n/loc`, and a finer number (2026-10-25)

Dated research, append-only. The instrument is `digitizer/tools/word_legibility.py`
(I3, 2026-10-24); its two holes were MFab and the pro's small words reading
`n/loc`, and a `cc` that sits at 1.00 for any word that reads. Measured on Kent's
laptop (tesseract **5.4.0**, `C:\Program Files\Tesseract-OCR`, on the bash PATH;
CI installs 5.3.4, so a figure quoted from here says which), engine `a6be6b78`,
today's main defaults, the art digitized at the pro's width as `--digitize` does.
No engine change. Every figure is chance-corrected (ROADMAP gate 4): `cc` is
`(raw - base) / (1 - base)` against a shuffle of the word's own letters, and
`reach` is built from `cc` alone.

## 1. Why the words were not locatable

It was not the locator's size floor (`SIZE_RATIO`/`HEIGHT_RATIO` admitted the
pro's words, which it sews 1.9-2.5x bigger), not the OCR scale, and not the
registration (the fit's error is a few mm and the search reaches 0.8 word widths
past it). Five separate things, each found by drawing the file with the art's
boxes over it (`--dump DIR` now writes `<job>_<file>_located.png`: blue where the
art says, green where the word was found):

| word | file | cause | fix |
|---|---|---|---|
| MFab AND WELDING LLC | pro | The pro sews them in white thread (240) over a black bed, on art whose ground is white (254). `drop_ground_blocks` dropped every ground-coloured stitch as "the cloth": the letters went with it. | `keep_visible_ground`: a ground-coloured stitch is kept when thread already lies under it, a jump when it lies on bare cloth. |
| MFab all four | ours, pro | The lettering is outlined letters on a black bed. In a thread mask the letters are welded to the bed (the pro sews the bed solid UNDER the white satin and the black letters). | `visible_masks`: the masks of what SHOWS of each spool (a flat colour render), so the white satin is in the way as it is in the picture. Where no piece is clearly the word, the art's own place is read if the thread there LOOKS like the art's word (`appearance_sim >= 0.5`): `registered`. |
| Fremont STAY, PLAY, 1895 | pro | A thin run of thread (8 px at 20 px/mm) ties each word to the rope: one piece 10x the word, thrown away whole as "a rope". | `_pieces`: a piece that big is peeled by a 0.35 mm opening, and the letters left are the pieces. |
| ProSeal SPRAY FOAM; COATINGS | ours, pro | The + is as far from FOAM as FOAM's own word space, so no dilation welds the words and leaves the mark (SPRAY FOAM + came back one piece; COATINGS came back as COATIN). | `_run_candidates`: every maximal run of consecutive letter pieces on a line, beside the fused pieces; the word ends where a run does. |
| (cost) | pro | `find_word` charged 0.5 x \|ln width ratio\| + 0.5 x \|ln height ratio\|: 0.9 of the 2.0 budget for a word the pro re-set 2.4x bigger (the small-text floor). | `SIZE_WEIGHT = 0.25` of the scale (aspect already carries the rest). |

Every pinned word of the four jobs is now located in both files (8 + 2 + 4 + 3
words). Not all equally well: MFab's AND WELDING LLC are `registered` (ours) /
`visible` (the pro's, cost 1.4-1.8, a box up to 3 mm taller than the art's) and
the reader cannot read them off the ART either (art `cc` 0.00 on all four), so
see 4.

## 2. The crop was part of the problem

The words the locator newly found read as NOTHING at first (pro STAY `7`, PLAY
`''`, EST `ELT`). The crops were right; what was in them was not. The pro's
black bars stand a millimetre from STAY, and Otsu's threshold sat between the
black and the orange, so the orange letters binarised to ground. White rope over
the pro's black ring (newly visible, see `keep_visible_ground`) added more.
Two changes and one rule:

- A ground-coloured stitch is drawn in a word's crop only inside the word's own
  box (`ground_in_box`): white over black is a letter in MFab's box and a border
  beside Fremont's EST.
- Each crop is read in two **views**: WIDE (everything in reach, the only crop
  every earlier number used) and TIGHT (only the thread within
  `CROP_NEIGHBOUR_MM = 0.5` of the word's own box). A tight view alone is worse:
  BECKER's black letters in a grey outline binarise apart only beside the next
  line's grey (pro BECKER: wide `BECKER` 96, tight `M7E7SSA` 40). The most
  confident of the six readings (3 variants x 2 views) wins, chosen without the
  truth, the wide view on a tie.
- The ground-colour and neighbour changes were measured on the way: with the
  tight view on its own, BECKER flipped to ours +1.00 / pro +0.00 (it was ours
  +0.42 / pro +1.00): a binarisation artefact either way, which is why the rule
  is "both views", not "the better crop".

## 3. The finer number: `reach`

`cc` is 1.00 for any word that reads, so it cannot show a word getting better.
Two ways of degrading a word were built and measured:

1. **Wear the layout smaller** (the existing 4/7/12 mm rows, as a ladder: the
   stitches scaled about the word's centre, the filament at its real 0.4 mm).
   Rejected. It scored the pro's 4.95 mm EST at 0.25 octaves and ours' 2.45 mm
   EST at 0.52: shrinking a bold layout closes its counters at once, so it
   answered "could this layout be worn smaller", not "which word is more
   legible". Also noisy: `cc` 1, 0, 1 down three rungs of one word.
2. **Show the picture smaller** (the word's native crop, area-averaged down in
   half-octave steps to 3 px tall: the word seen from farther). Kept. At 6 px
   tall tesseract still read most words (a floor of 6 px saturated at
   log2(native / 6)), so the ladder runs to 3 px, below which nothing reads.

`reach` = the area under `cc` against the log of the height, in OCTAVES: how many
times the word can be halved, the distance doubled, and still be read.
`floor px` is the smallest height it is still read at (`cc >= 0.5`), the part
that does not depend on how big the word was sewn. `reach` moves with both: a
small word re-set bigger gains; a word whose letters hold together less well as
the picture shrinks loses. It is zero for a word not read at native.

A worked reading of the table below: Fremont's EST. Both files read it, `cc`
1.00 and 1.00. Ours is 2.45 mm tall and reaches 2.75 octaves (floor 7 px); the
pro's is 4.95 mm and reaches 3.98 (floor 7 px). The floors agree (the letters
hold up the same); the 1.2-octave gap is the size, which is the small-text
floor, and a lettering PR that re-sets small text moves exactly this number.

## 4. Old score, new score, ours beside the pro

`old` is the instrument as merged in #1067, run on the same cache. `found` is
how the word was found (`t` thread, `v` visible, `r` registered window) and
which view read it (`w` wide, `n` tight). `n/loc` is "not located, left out of
the figure, never scored 0". Heights are the word's, in mm.

### Fremont (8 words, pro file `.PES`)

| word | art cc | old cc ours / pro | new cc ours / pro | found . view | height mm | reach oct ours / pro | floor px |
|---|---|---|---|---|---|---|---|
| EST | +1.00 | +1.00 / +1.00 | +1.00 / +1.00 | tn / tw | 2.5 / 5.0 | 2.75 / 3.98 | 7 / 7 |
| 1895 | +1.00 | +1.00 / n/loc | +1.00 / +1.00 | tn / tw | 2.5 / 4.8 | 2.23 / 4.09 | 14 / 6 |
| THE | +1.00 | +1.00 / +1.00 | +1.00 / +1.00 | tw / tw | 3.1 / 4.3 | 4.20 / 3.75 | 3 / 6 |
| HOTEL | +1.00 | +1.00 / +1.00 | +1.00 / +1.00 | tw / tn | 8.0 / 8.2 | 5.25 / 5.25 | 4 / 4 |
| FREMONT | +1.00 | +1.00 / +1.00 | +1.00 / +1.00 | tw / tn | 8.0 / 8.2 | 4.75 / 5.28 | 12 / 4 |
| EAT | +1.00 | +1.00 / +0.49 | +1.00 / +1.00 | tw / tn | 2.9 / 5.0 | 3.25 / 2.73 | 6 / 27 |
| STAY | +1.00 | +1.00 / n/loc | +1.00 / +1.00 | tw / tn | 3.0 / 5.0 | 2.77 / 3.75 | 7 / 8 |
| PLAY | +1.00 | +1.00 / n/loc | +1.00 / +1.00 | tw / tn | 2.9 / 4.8 | 3.25 / 3.75 | 6 / 7 |

Job, words both files scored: old cc ours +1.00 / pro +0.93 (n=5); new cc +1.00 /
+1.00 (n=8); new **reach ours 3.73 / pro 4.27** octaves. The old table said the pro
was ahead on nothing and behind on three words it could not find; the new one
says the thread reads for both and the pro stands about half an octave farther
away, nearly all of it EST, 1895, STAY: the small words it re-sets 2x bigger.
The pro's EAT is the one place it is behind (reach 2.73 to ours' 3.25, floor 27 px).

### Becker (2 words, pro file `.pes`)

| word | art cc | old cc ours / pro | new cc ours / pro | found . view | height mm | reach oct ours / pro | floor px |
|---|---|---|---|---|---|---|---|
| BECKER | +0.00 | +0.42 / +1.00 | +1.00 / +1.00 | tn / tw | 44.2 / 42.9 | 4.43 / 0.40 | 255 / 722 |
| MARINE | +1.00 | +1.00 / +1.00 | +1.00 / +1.00 | tn / tw | 18.1 / 18.4 | 4.25 / 5.94 | 19 / 6 |

Job: old cc ours +0.71 / pro +1.00; new +1.00 / +1.00; **reach ours 4.34 / pro
3.17**. Read this table with care: BECKER reads 0.00 off the ART, so its thread
readings say what tesseract did with a black-in-grey word, not what a viewer
sees. The old "gap" (ours +0.42 beside the pro's +1.00) was the crop's: ours
reads `BECKER` conf 81 with only its own thread in view and `BEOEER` conf 0 with
the next line's grey beside it, and the pro the other way round. The pro's
reach 0.40 is the same fragility seen from the other side (it reads at its
native crop and at no rung below). MARINE is the clean word, and there the pro
reaches 6.0 octaves to ours 4.3: its letters hold to 6 px, ours need 19.

### MFab (4 words, pro file `.PES`)

| word | art cc | old cc ours / pro | new cc ours / pro | found . view | height mm | reach oct ours / pro | floor px |
|---|---|---|---|---|---|---|---|
| MFAB | -0.00 | n/loc / n/loc | +0.25 / +0.25 | rw / rw | 19.8 / 20.1 | 0.67 / 1.38 | - / - |
| AND | +0.00 | n/loc / n/loc | -0.00 / +1.00 | rn / vn | 8.3 / 8.8 | 0.25 / 2.82 | - / 139 |
| WELDING | -0.00 | n/loc / n/loc | +0.63 / +0.88 | rn / rn | 8.3 / 8.4 | 1.26 / 2.74 | 135 / 106 |
| LLC | +0.00 | n/loc / n/loc | -0.00 / +0.00 | rn / vn | 8.3 / 7.7 | 0.00 / 0.00 | - / - |

All four words are located in both files now (this was 0 of 8). **Do not quote
MFab as a legibility verdict.** The reader reads none of the four off the art
itself (outlined letters in a 418 px logo), so the thread readings are what a reader
does with outlined lettering. `blind_words` says so for MFAB and LLC (neither
art nor either file reads at `cc >= 0.5`) and the board leaves them out as `n/a`
with that reason. AND (pro +1.00) and WELDING (+0.63 / +0.88) do read in a file,
so they count; the numbers are real readings and the gap (ours AND -0.00) is one
word. The pro's small words are `visible` at cost 1.4-1.8 against the art's
boxes: the word is found, the box is not as tight as Fremont's.

### ProSeal (3 words, pro file `.DST`, one black block)

| word | art cc | old cc ours / pro | new cc ours / pro | found . view | height mm | reach oct ours / pro | floor px |
|---|---|---|---|---|---|---|---|
| PROSEAL | +1.00 | +1.00 / +1.00 | +1.00 / +1.00 | tn / tw | 10.3 / 10.4 | 5.89 / 5.25 | 3 / 6 |
| SPRAY FOAM | +1.00 | n/loc / n/loc | +1.00 / +1.00 | tw / tw | 3.5 / 5.2 | 4.30 / 4.30 | 4 / 5 |
| COATINGS | +1.00 | +1.00 / +1.00 | +1.00 / +1.00 | tw / tn | 3.5 / 5.2 | 4.12 / 4.25 | 4 / 6 |

Job: old cc +1.00 / +1.00 (n=2, COATINGS was found as COATIN); new +1.00 / +1.00
(n=3); **reach ours 4.71 / pro 4.56**. Both files read everything and the
thread keeps up with the pro: ours' 3.5 mm SPRAY FOAM reaches as far as the pro's
5.2 mm one (4.30 each), which is the number `cc` could not give.

## 5. What this does not tell you

- Reach is **the picture shrunk**, not a sew-out and not a viewer at a distance
  (ROADMAP gate 1): no pull, no push, no nap, no sheen. It says how far the
  reader can step back, not how far a person can.
- It is built on tesseract, and tesseract is fragile exactly where a multi-tone
  word (Becker's black in grey, MFab's outlines) binarises: those words flip
  with the crop and say nothing about the lettering. The ladder is read in the
  view that read the native crop, and the BECKER pro's 0.40 is that fragility.
- `n` is 2-8 words a job. No interval is claimed.
- Pro words are re-set 2x bigger than the art draws them, so ours-vs-pro `reach`
  has the SIZE in it by design; `floor px` is the size-free half. Quote both.
- The board (`tools/lettering_board.py`) gets a `reach` column beside `cc`; the
  cells that carry the new locator and the two-view read move (Becker and
  Fremont's), so a board run before this PR is not comparable on `cc` for
  those pairs. The baseline `docs/scoreboards/lettering-board-2026-10-25.*` was
  not regenerated (an hour of digitizing on this laptop); the next board run
  writes the column.

## 6. Speed (a trap for the next reader)

A tesseract process start costs **5 s** on this laptop (a 73x151 crop: 5.1 s
wall, 0.03 s CPU; the time is the process, not the read). The first version read
8 Fremont words in 6 m 45 s. `read_crops` writes every crop's preprocessing
variants and reads them in a few list-of-images tesseract runs (12 crops: 9.7 s,
one start), 4 runs in parallel, and falls back to `read_crop` one by one if a
run does not return every page. Same readings as `read_crop` crop for crop (55
rows, 0 differences in text, `cc`, `raw`; confidence matched once it was
truncated to whole numbers as pytesseract hands it over).
