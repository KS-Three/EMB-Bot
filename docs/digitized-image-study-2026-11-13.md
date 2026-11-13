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
code trace; row 7 was then re-read by the director at
`stage5_overlap.py:1202-1231`, because the agent's headline and the code disagreed.

| # | What the professionals do | Why | Seen in about | EMB-Bot today |
|---|---|---|---|---|
| 1 | A narrow, even-width shape (letter stroke, border, stripe, leaf, claw) is a satin column sewn across its width, the angle turning with the path | Short stitches across the width cover cleanly; the sheen follows the form | 45 | Does (`satin`, ceiling `SATIN_MAX_WIDTH_MM` 5.0) |
| 2 | A wide flat area is a tatami fill at ONE angle, however complex its outline | An even sheen; the outline is drawn by the edge, not by the rows | 30 | Partial: each shape picks its own angle by fewest columns |
| 3 | A fill gets a satin border or outline sewn over its edge | Fill rows end in a sawtooth; the border hides it and hides registration error | 25 | Does (`border_by_size`, fabric edges only) |
| 4 | Ink outlines and line art are sewn LAST, on top of every colour | The line lands on the seams between fills and covers them | 14 | Partial: `borders_last` (on) sews satin-dominated layers after fill-dominated ones, otherwise largest area first. No rule names an outline, and where bean or dark-ink runs land on flat cartoon art was not traced (`stage7_sequence.py:434-502`) |
| 5 | A hairline (smile, whisker, string, feather line, a thin gap in the art) is a run stitch on top of the fill. Never a satin, never a gap held open | Satin cannot sew that narrow; a gap that thin closes from pull | 20 | Does (`bean_only_lines`, `dark_ink_bean`, `keep_dark_thin_strokes`) |
| 6 | Touching fills of similar colour get DIFFERENT angles, or an outline between them | Thread reflects by direction, so the angle step is the boundary | 22 | Does not. See "The one real disagreement" |
| 7 | Small shapes inside a big one (spots, eyes, stripes, text on a panel) are sewn ON TOP of a solid fill | A hole per spot puckers, gaps and misregisters | 20 | Does not. The ground keeps a hole under every later shape: the hole shrinks by the pull growth and gets a 0.25 mm tongue (`overlap_mm`), and a hole that would close is held open at its original size (`held_hole_bare_only` off). `silhouette_underfill` covers rings only |
| 8 | Strokes that cross or join are separate overlapping columns; the seam is accepted | One column cannot make a T, Y or X; a butt joint opens | 9 | Partial: skeleton arms run into the junction and overlap there (`satin_junction_stack` on), corners of 45 degrees or more butt, a patch covers what stays bare (`stage6_satin.py:148-183`) |
| 9 | A column too wide for satin is split (sections, or two lengthwise columns) or becomes outline-plus-fill before it becomes plain fill | Keeps the sheen of the mark; long stitches snag | 8 | Does (`split_satin` above 5.0 mm; `wide_columns` off) |
| 10 | Shading becomes 2 to 5 flat steps as separate shapes (cartoons, logos, metal) | Thread has no continuous tone | 14 | Partial (`max_colors`, `color_cap_sewn`) |
| 11 | A ground that matches the cloth is left unsewn. Six of the seven real uniform patches fill nothing | Saves stitches, keeps the piece flat, avoids fill pull | 12 | Does (`enclosed_by_garment_de00`, `enclosed_white_skip_transparent`) |
| 12 | A light shape on a dark field, or a dark subject on a mid-tone, gets a contrast outline | Separation, and a second chance to cover the edge | 10 | Does not. No step adds an outline the art lacks; the white-keyline recipes act only on art that already carries one |
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

1. **Rule 7 is the clearest gap between the pictures and our output.** The
   professionals sew spots, eyes, stripes and panel text on a solid ground; we
   knock a hole for each and rely on a 0.25 mm tongue. Before anything is built:
   on the cartoon and patch fixtures, count the later shapes that sit wholly
   inside a ground, the stitches a solid ground would add, and the bare fabric
   the knock-out leaves at those seams today. A stitch file from Kent's
   professional would say whether he stacks or knocks out, and at what size.
2. Rule 12: a count of light-on-dark shapes we sew with no separating edge.
3. Rule 4: where bean and dark-ink runs land in the order on flat cartoon art.
   The professionals put the ink line last without exception.
4. Rule 16: how the house angle reads a text line that sits on an arc.
