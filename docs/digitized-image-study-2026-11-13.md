# How professionals digitize shapes, read from 108 pictures (2026-11-13)

Research only. No engine file changed, no flag flipped, no constant touched.

**Why this exists.** Kent asked (2026-11-13) for 100 pictures of digitized designs
(pictures, not stitch files) to be studied for HOW each shape was digitized and
WHY, and seeded it with 10 of his own. Everything EMB-Bot has copied from a
professional so far came from one digitizer's files (`docs/pro-digitizer-rules-2026-10-21.md`).
This is a wider, shallower reading: many digitizers, many genres, eyes only.

## What was read

| | count |
|---|---|
| Entries studied (7 Sonnet agents + Kent's 10 seeds) | 119 |
| Same picture studied twice or three times by different agents | 9 |
| Extra frames of one design | 2 |
| **Distinct designs** | **108** |
| of which flagged as probable AI mock-ups (3 of them Kent's seeds: Somos, giraffe, AG Digitizing) | 8 |
| **Distinct designs not flagged** | **100** |

By kind (distinct): 52 photographs of real sew-outs, 33 software stitch renders,
15 art-beside-result pairs, 8 mock-up suspects.

By subject: before/after pairs, lettering and wordmarks, patches and badges,
cartoon characters, realistic animals and florals, caps / 3D puff / applique /
team crests, plus a top-up of real logo sew-outs and museum florals.

The pictures and the per-picture notes are in the gitignored
`scratch_digitized_study/` (`images/`, `notes/*.json`, `notes/rules_dump.txt`).
They are third-party artwork and are NOT in this repo. Each note records the
source page, every shape class with its stitch type, angle, edge and reason,
the lettering treatment, the layering, what changed against the art, and one
line separating what was seen from what was inferred.

## How far to trust it

- **Eyes only.** Stitch type is read from sheen and texture. Nothing here was
  measured: no size, density, underlay, pull compensation or sewing order is
  known unless overlap shows it. Every width threshold an agent wrote ("about
  5 mm", "under 3 mm") is a guess and is not carried into the table below.
- **Checked two ways.** Four notes were compared against their pictures by the
  director (tiger sew-out, NANA'S Kitchen, Munich patch, grey cat): all four
  matched. The 9 accidental duplicates were a free agreement test: independent
  agents gave the same stitch class for every large shape and differed only on
  small text and on wording.
- **Weak sets.** The before/after set is the thinnest: 9 of its 15 come from one
  vendor whose "after" pictures change colours and letter shapes, so they may be
  generated. No picture showed a real applique tack-down or a jacket back.
  Corporate left-chest logos are under-represented (5 real ones).
- **Source concentration.** About a quarter of the real designs come from one
  design shop's product photos, and 14 from one digitizing service's portfolio.
  A habit seen 10 times may be 2 digitizers' habit.
- Counts below are distinct, unflagged designs, tallied by hand from the notes;
  read them as "about".

## The rules, with the reason and what EMB-Bot does today

"EMB-Bot today" is one agent's reading of `digitizer/digitizer_core/config.py`
defaults on main `bb5655bf`. Rows 4, 7, 8, 12 and 16 come from a second agent's
code trace. **Row 7 was corrected the same day**: the first version said "Does
not", from a reading of `stage5_overlap.py:1202-1231` alone, and a measurement
of our own stitch files showed that reading wrong. See "Rule 7, measured".

| # | What the professionals do | Why | Seen in about | EMB-Bot today |
|---|---|---|---|---|
| 1 | A narrow, even-width shape (letter stroke, border, stripe, leaf, claw) is a satin column sewn across its width, the angle turning with the path | Short stitches across the width cover cleanly; the sheen follows the form | 45 | Does (`satin`, ceiling `SATIN_MAX_WIDTH_MM` 5.0) |
| 2 | A wide flat area is a tatami fill at ONE angle, however complex its outline | An even sheen; the outline is drawn by the edge, not by the rows | 30 | Partial: each shape picks its own angle by fewest columns |
| 3 | A fill gets a satin border or outline sewn over its edge | Fill rows end in a sawtooth; the border hides it and hides registration error | 25 | Does (`border_by_size`, fabric edges only) |
| 4 | Ink outlines and line art are sewn LAST, on top of every colour | The line lands on the seams between fills and covers them | 14 | Partial: `borders_last` (on) sews satin-dominated layers after fill-dominated ones, otherwise largest area first. No rule names an outline, and where bean or dark-ink runs land on flat cartoon art was not traced (`stage7_sequence.py:434-502`) |
| 5 | A hairline (smile, whisker, string, feather line, a thin gap in the art) is a run stitch on top of the fill. Never a satin, never a gap held open | Satin cannot sew that narrow; a gap that thin closes from pull | 20 | Does (`bean_only_lines`, `dark_ink_bean`, `keep_dark_thin_strokes`) |
| 6 | Touching fills of similar colour get DIFFERENT angles, or an outline between them | Thread reflects by direction, so the angle step is the boundary | 22 | Does not. See "The one real disagreement" |
| 7 | Small shapes inside a big one (spots, eyes, stripes, text on a panel) are sewn ON TOP of a solid fill | A hole per spot puckers, gaps and misregisters | 20 | Does, on logo and flat art: `silhouette_underfill` (on) closes the ground's holes and stage 5 sews it solid (`stage5_overlap.py:1009-1013`, `1102`). Measured: 120 of 126 narrow pieces fully on solid ground. Does not on photo-class art, where the under-fill is gated off |
| 8 | Strokes that cross or join are separate overlapping columns; the seam is accepted | One column cannot make a T, Y or X; a butt joint opens | 9 | Partial: skeleton arms run into the junction and overlap there (`satin_junction_stack` on), corners of 45 degrees or more butt, a patch covers what stays bare (`stage6_satin.py:148-183`) |
| 9 | A column too wide for satin is split (sections, or two lengthwise columns) or becomes outline-plus-fill before it becomes plain fill | Keeps the sheen of the mark; long stitches snag | 8 | Does (`split_satin` above 5.0 mm; `wide_columns` off) |
| 10 | Shading becomes 2 to 5 flat steps as separate shapes (cartoons, logos, metal) | Thread has no continuous tone | 14 | Partial (`max_colors`, `color_cap_sewn`) |
| 11 | A ground that matches the cloth is left unsewn. Six of the seven real uniform patches fill nothing | Saves stitches, keeps the piece flat, avoids fill pull | 12 | Does (`enclosed_by_garment_de00`, `enclosed_white_skip_transparent`) |
| 12 | A light shape on a dark field, or a dark subject on a mid-tone, gets a contrast outline | Separation, and a second chance to cover the edge | 10 | Adds none, and neither does Kent's professional. Measured 2026-11-14: every outline in his files is in the artwork, and 0 added outlines were found on either side. See "Rule 12, measured" |
| 13 | A patch border is its own satin ring, perpendicular to the edge, sewn last; two colours are two stacked rings; a subject that breaks the border is sewn after it | It locks and hides everything beneath | 14 | Partial: the ring exists, its place in the order is UNKNOWN |
| 14 | Against the art: thin keylines dropped or thickened, tiny text fattened, hatching thinned out, drop shadows made separate flat objects, stray marks removed, colours moved to the thread chart | Detail below sewable size turns to mush | 12 | Partial (`min_detail_mm`, `small_text_cap_mm` 4.0 with bolding) |
| 15 | Fur and feathers: direction follows growth or radiates from the nose; edges left ragged with NO outline; tones interleaved; each feather one fanned satin; hard features (nose, eye, beak) smooth for contrast | A satin edge "makes fur look like plastic"; direction is the drawing | 20 | Partial (`fur_style` in the photo lane; direction-follows-growth UNKNOWN) |
| 16 | Text on an arc: letters rotate with the baseline, satin stays across each stem | The stitch follows the letter, not the page | 8 | Art: partial. The angle is set per station along each stroke's spine, or by a house angle read from the text line; a line that itself sits on an arc was not checked. Typed lettering: does, each glyph rotates on the arc (`src/satinfont.js:1253-1290`) |
| 17 | 3D puff: satin only, one thick uniform stroke weight, capped ends, rounded corners, small text left flat beside it. Large flat letters: applique with a constant-width satin edge | Foam must be fully covered; thin parts cannot carry it | 7 puff, 3 applique | Puff out of scope; applique built, off |
| 18 | Small satin lettering fails first: closed counters, ragged serifs, fuzzy thin strokes | Column width reaches the thread's limit | 6 (flaws in real sew-outs) | Does (`small_text_cap_mm` raises and bolds) |

## The one real disagreement

Rule 6 says neighbours get different angles. DOCTRINE (2026-09-09) measured the
opposite on Kent's professional: one fill angle for the whole design, at every
size. Both are true, and the split is by genre:

- **Logos and crests** (his pro; the team crests and patches here): one quiet
  angle across the design, with satin borders and outlines doing the separating.
- **Cartoon characters** (the donkey, leopard and panda Kent supplied; 15 more
  here): the muzzle, ears, mane and mouth each turn, because there the angle IS
  the separator between similar colours. Where a drawn black line already
  separates two shapes, the same digitizers keep one angle across both.

EMB-Bot does neither on purpose. It picks each shape's angle to minimise that
shape's column count, so neighbours differ or agree by accident. Kent's blind
sitting on 2026-11-09 kept the pro-direction slant OFF, so this is recorded as a
finding, not a proposal.

## What the failures show

- An auto-converted cartoon (a university wiki's first take) kept its outline
  and big fills and turned the small pale detail on its backpack into a tangled
  lattice. Small light detail over a fill is where automatic conversion breaks.
- A run-stitch line drawing sewn at two sizes shows dashes where the path jumps.
- On real caps and patches the first thing to fail is small serif text and
  hairline script, every time.

## What this study cannot tell us

Underlay, density, pull compensation, trims, sequence and any number in
millimetres. Those need stitch files, and the 29 professional files already
read in `docs/pro-digitizer-rules-2026-10-21.md` remain the only measured source.

## Worth measuring next (nothing here is a build request)

1. Rule 7 on photo-class art: the owl is one fixture and 8 readable pieces. A
   character or mascot that routes to `photo_subject` / `photo_scene` is where
   our knock-out survives, and the repo has no leopard, panda or donkey to read.
2. Rule 7, wide pieces: the professional knocks out above about 5.2 mm with a
   1 to 2 mm underlap; we sew solid at 5 to 8 mm. That is thread he does not
   spend. Not priced here.
3. Rule 12 on our side: the art outlines the professional keeps on Golden Tee's
   "1" and beside Fremont's rope were not found as ringed pieces in our output,
   and our plans carry border runs the reader never matched to a piece. Where
   those outlines go in our file was not traced.
4. Rule 4: where bean and dark-ink runs land in the order on flat cartoon art.
   The professionals put the ink line last without exception.
5. Rule 16: how the house angle reads a text line that sits on an arc.

## Rule 12, measured (2026-11-14)

Kent asked for the contrast-outline rule to be counted. It was, from stitch
files on both sides, with the rule 7 reader.

**Method.** For every piece that sits on a ground: is there a thin ring of
thread hugging its edge in a thread other than its own (a contrast ring), or in
its own (an edge finish, counted apart)? Checked first on a synthetic square
with satin bars: bare reads 0 of 5; a contrast ring reads 5 of 5 at every
width from 0.2 to 2.0 mm, a single run line included; an own-colour ring reads
on pieces 4.5 mm wide or more and is invisible on narrower ones. Whether a
ring was in the customer's artwork was decided by eye, from a crop of the art
beside the render; each call is listed. Thread colours: the professional's from
the PES twin of each DST, ours from the pipeline's own output. Our DSTs are the
rule 7 ones, generated on main `19013abe`.

**The professional** (28 files): 373 pieces on a ground, a contrast ring on 32,
an own-colour ring on 3. Sixteen of the 32 are specks under 2 mm2 and were not
called one by one. The rest:

| ring | in the artwork? |
|---|---|
| Golden Tee, black ring round the bevel of the "1" | yes |
| Fremont patch and hat, black line beside the rope band (one side only) | yes |
| MFab hat and LC, white panels with an own-colour edge | yes, the art's white keyline |
| Precision Drone crosshair | not an outline; a neighbouring tone |
| 12 Gaulke Plowing / JB pieces | cannot call: no artwork, no PES colours |

**Outlines he added that the art lacks: 0 found.** The director checked the
Golden Tee and Fremont calls against their crops; both hold.

**Ours, the six paired jobs:** 129 pieces, 11 contrast rings, 0 own-colour.
Three MFab letter groups keep the art's white keyline; the Drone and Golden Tee
ones are neighbouring tones and band fragments, not outlines. **Outlines we
add: 0 found.**

**Contrast of pairs with no ring** (dE00 between the piece's thread and the
thread beside its edge):

| | pairs | lowest | quartiles |
|---|---|---|---|
| Professional | 210 | 10.7 | 42.6 / 93.0 / 93.0 |
| Ours | 115 | 17.3 | 27.5 / 71.4 / 73.2 |

Lowest pair per job, his against ours: Fremont 38.3 and 26.7, Drone 10.7 and
17.3, Becker 42.6 and 71.4, MFab 93.0 and 100.0. None of our 115 pairs falls
below his lowest. Same thread on both sides of an edge: his 1, ours 3 (MFab
letters where the keyline does not reach).

**Character art, ours only** (Pooh, owl, Tux, Bison): 18 pieces, 2 contrast
rings (both specks), 1 own-colour. Four of 16 unringed pairs fall below the
professional's lowest, all of them greys on the owl (2.6, 2.6, 8.0, 10.0).

**What it means for rule 12.** The pictures showed outlines round light-on-dark
shapes; they could not show whether the digitizer added them or the artwork
had them. On the one professional whose files and artwork we hold, he keeps the
art's outlines and adds none, and so do we. The rule stands as "keep the
outline the art gives you", not "add one".

**Limits.** A colour difference between two threads says nothing about how the
pair looks sewn. Ring calls rest on the reader's geometric constants. The
reader cannot see a ring in the ground's own colour block, or an own-colour
ring on a piece under 4.5 mm. Machine's colours were not read. A re-run of MFab
on a later commit was cut off and is unverified. Scripts are throwaway, in the
session scratchpad.

## Rule 7, measured (2026-11-13, same day)

Kent asked for rule 7 to be measured. It was, from stitch files, and it
overturned the first version of this doc's row 7.

**Method.** One reader on both sides, each DST in its own frame: needle-down
segments of 6 mm or less drawn 0.4 mm wide at 20 px/mm, split into colour
blocks. A connected piece is a GROUND when its stitches run on in rows (tatami)
and not back and forth (satin). Every later piece lying inside an earlier
ground's outline gets an under-cover: the share of its footprint that earlier
thread covers, read over the whole piece, over its core (shrunk 0.5 mm) and by
depth from its edge. Checked first on a synthetic square with satin bars on it:
solid ground reads 1.00, a knock-out with a 0.25 mm tongue reads 0.01 to 0.41
in the core, a 0.3 mm gap reads 0.00. Widths include the 0.4 mm of thread.

**The professional** (20 non-beanie DSTs with a ground and something on it):

| piece width | pieces | what he does |
|---|---|---|
| under 5.2 mm | 292 | all on solid ground: under-cover 0.92 or more, 289 at 0.99 or more |
| 5.2 mm and over | 12 | 8 knocked out with a deep underlap (ground covers fully to 1 mm in, 0.54 to 0.89 at 1 to 2 mm, 0.00 to 0.22 past 2 mm); 4 solid (Becker 5.4 mm, To a T 5.5 mm, each one design in two files) |

So he stacks small shapes and knocks out big ones, and the switch sits near
5.2 to 5.5 mm on these files. That is twelve wide pieces from six designs.

**Ours, same jobs, same reader** (seven paired jobs at the pro's width):

| | pieces | result |
|---|---|---|
| narrow | 126 | 120 at 0.99 or more; lowest 0.78, two MFab letters |
| wide | 6 | solid on Drone (6.7 to 8.2 mm), To a T (5.9), Fremont (5.0); knocked out once, MFab's 9.2 mm panel, about 1 mm underlap |

Cost of a solid ground under what we knock out: 1,570 stitches on MFab (7.6% of
that job, an over-estimate), zero on the other six. Bare fabric in a 0.5 mm
band either side of each piece: median 0.00 on both sides for every job except
the pro's Golden Tee (0.05). The reader cannot see a gap under about 0.4 mm.

**Why the code reading was wrong.** The ground does have a hole after stage 4,
and `stage5_overlap.py:1202-1231` would hold it. But `silhouette_underfill`
(on) stores the ring's outline with its holes closed, stage 5 unions that into
the ground (`1009-1013`, `1102`), and the hold-open block never fires. The hole
survives in three cases: photo classes (`gate_underfill_for_photo`,
`pipeline.py:133-163`); a ground that is not read as a ring (too small, a
letter, shapes filling under half its holes, or nested inside another ring's
contents); and MFab's panel, which `_panels` cuts back out on purpose.

**Cartoon and character art, ours only:**

| fixture | width | class | under-fill | pieces on a ground | on solid ground |
|---|---|---|---|---|---|
| Pooh | 54.6 mm | gradient | on | 5 | 4 (the fifth is a 0.5 mm2 speck) |
| Tux mascot | 80 mm | flat | on | 4 | 4 |
| Bison icon | 80 mm | flat | on | 1 | 1 |
| Owl | 127 mm | photo_scene | off | 8 | 6; the two wider ones (3.7 and 5.6 mm) have about 1 mm of underlap and nothing past 2 mm |

The owl is the knock-out the picture study described, and it is the only
photo-class fixture read. Forty-five of its fill pieces did not pass the ground
test, so its number is thin.

**Not read:** Gaulke Roofing (one colour block per file, nothing comes later),
Tires 3D (no ground), Proseal (a ground with nothing on it). Beanies were read
and kept out of every count; they show the same pattern.

**The lesson.** A claim about what the pipeline sews was made from one block of
one stage and published. Read the output before describing the output.
