# A DST machine cuts where the builder only floated (2026-10-04)

This note measures a finding handed over from PR #623 and sets out the
choices. **Kent chose the same day: choice 2.** It is built as `cutFloats` on
`buildQualityDesign`, OFF by default, so no file changes until he flips it
("Waiting on Kent" 28). What follows is what was put to him; what was built
is at the end.

## What it is

A DST has no cut. `src/dst.js` writes a `trim` as three or more jump records,
because a machine set to cut at three jumps cuts there. It also writes any
needle-up move longer than one record holds, 12.1 mm an axis, as several jump
records. So a float over 24.2 mm is three jump records too, and a machine
cannot tell it from a cut.

The builder wrote no `trim` there, so nothing that goes by `trim` records
knows of the cut:

- `ties` lays no lock either side of it;
- the trim count on the review screen and the sheet leaves it out;
- so does the run time, which charges 11 s a trim.

EXP and PES have a trim of their own, and there the float stays a float.

It is in what ships, with every flag absent, in the shape builder's lanes:
preset shapes, hand-drawn shapes and the image lane were measured (SVG import
goes through the same builder and was not). The lettering builder has none.

## How many

Counted again with a reader of this note's own, `tools/file-cut-census.mjs`.
It writes each design with each of the three writers, reads the file back
from the format and not with `dstimport.js`, and lines every record of the
file up with the stream's. A run of three or more jump records is a cut.

| engine at `f887e27d` | `trim` records in the stream | cuts in the DST |
|---|---|---|
| the sweep of #616 and #617, 8,255 designs | 8,175 | 21,340 |
| the same, `fillColumns` on | 2,177 | 5,060 |
| the Studio's shape lanes, 8,270 designs | 7,028 | 120,912 |
| the same, `fillColumns` on | 2,686 | 13,969 |

All four rows of the handover reproduce. On `main` at `227cdd9e` the Studio
rows are 120,959 and 14,016, since #624 changed the preset star; the rest of
this note is measured there.

**pystitch reads the same.** On 498 designs sampled across the four sets it
makes 75,922 TRIMs of the DST files, where this reader counts 75,922 cuts
with thread attached: the same on every design, against 5,493 `trim` records
in the stream. In the EXP and PES files it finds the 5,493.

## What each cut was

"As shipped" is every flag absent. Three kinds are no harm: a `trim` the
builder wrote, the move after a colour change, and the file's first move,
where no thread is attached. The other three are cuts nobody asked for.

| | sweep | with `fillColumns` | Studio shapes | with `fillColumns` | image lane, 252 | with `fillColumns` |
|---|---|---|---|---|---|---|
| a `trim` the builder wrote | 8,175 | 2,177 | 7,028 | 2,686 | 2,844 | 2,567 |
| the move after a colour change | 0 | 0 | 0 | 0 | 122 | 108 |
| the file's first move | 819 | 819 | 4,370 | 4,374 | 90 | 90 |
| **between two runs of one shape** | 7,109 | 2,009 | 7,714 | 5,211 | 1,059 | 438 |
| **between two shapes** | 0 | 0 | 0 | 0 | 0 | 0 |
| **a float inside a run** | 5,237 | 55 | 101,847 | 1,745 | 69,376 | 13 |
| **cuts nobody asked for** | 12,346 | 2,064 | 109,561 | 6,956 | 70,435 | 451 |
| designs with one | 4,460 | 1,685 | 4,805 | 3,544 | 183 | 107 |
| a design, on average | 1.5 | 0.25 | 13 | 0.84 | 280 | 1.8 |
| the most in one design | 74 | 4 | 958 | 19 | 7,342 | 50 |

- **A float inside a run is the plain walk's.** A fill row ends, the next
  begins across a hole or a notch, and the frame goes there with the thread
  on: defect 52. Of the Studio's 101,847, 93,226 are in a fill run and 7,093
  in the lattice underlay, which is a tatami pass too. The column walk sews
  round: 71 and 146.
- **Between two runs of one shape** is the move from one underlay pass to the
  next (4,239 in the Studio's shapes) or from the underlay to the fill
  (3,425). The builder leaves the thread on there on purpose: "Under the fill
  that float is hidden". With `fillColumns`, 2,907 and 2,254.
- **A satin column that floats to another arm** of its shape: 1,528, in
  either arm. These are defect 57's shapes.
- **None between shapes.** There the builder already cuts any move over the
  fabric's `trimAtMm`, 3 to 4 mm.
- **Lettering: none**, in 765 designs (85 fonts, three texts, three garments).
- **`fillColumns` takes away** 94% of the Studio's, 99% of the image lane's
  and 83% of the sweep's.

**Which lanes.** Hand-drawn shapes 92,308 in 3,238 of 5,400 designs; preset
shapes 17,253 in 1,567 of 2,870; the image lane 70,435 in 183 of 252. With
`fillColumns`: 4,227, 2,729 and 451.

**Which sizes.** They grow with the design.

| sewn width | Studio designs | as shipped | with `fillColumns` |
|---|---|---|---|
| under 30 mm | 2,679 | 456 | 417 |
| 30 to 60 | 1,298 | 3,756 | 1,665 |
| 60 to 100 | 2,957 | 18,723 | 2,535 |
| 100 and over | 1,336 | 86,626 | 2,339 |

In the image lane 67,330 of the 70,435 are in the 105 designs 100 mm and
wider.

**How long the floats are**, from the stitch before to the stitch after:

| | under 24.2 mm | 24.2 to 30 | 30 to 50 | 50 to 100 | 100 and over | longest |
|---|---|---|---|---|---|---|
| Studio shapes, as shipped | 715 | 7,011 | 60,683 | 35,947 | 5,205 | 387 mm |
| with `fillColumns` | 682 | 1,156 | 2,601 | 1,816 | 701 | 388 mm |
| image lane, as shipped | 18 | 21,970 | 25,183 | 13,120 | 10,144 | 334 mm |
| with `fillColumns` | 1 | 68 | 248 | 89 | 45 | 301 mm |

Under 24.2 mm the frame went further than the two stitches lie apart: several
jump records in a row, or a satin column out and back. 862 of the Studio's,
in either arm, are a move that two records could hold.

**Thread ends without a lock, with `ties` on.** Two ends a cut. In the
Studio's shapes 219,122 ends and 303 of them locked, by a lock laid for
something else; with `fillColumns` 13,912 and 78. In the image lane 140,870
and 36; with `fillColumns` 902 and none.

**Time the sheet does not show**, at its own 11 s a trim: on average 2.5
minutes a Studio design and 52 minutes an image design as shipped; the worst
image design has 7,342 such cuts. With `fillColumns`, 10 and 20 seconds.

**A machine set to cut at two** (below) also cuts at two jump records in a
row, which is any float over 12.1 mm: 121,101 more in the Studio's shapes as
shipped and 5,671 with `fillColumns`; 39,646 and 554 in the image lane.

*(measured 2026-10-04 on `main` at `227cdd9e`,
`node tools/file-cut-census.mjs --set tools/file-cut-sweep-set.mjs --set shapes --set image --set lettering`)*

## What the Python engine does

It never floats that far.

- **Every needle-up move over the fabric's trim length is cut.**
  `machine.TRIM_AT_MM` is 3.0 and each fabric carries its own `trim_at_mm`,
  3.0 to 4.0. Every stage that joins two runs sets `trim = d > trim_at_mm`
  (`stage6_contour`, `stage6_border`, `stage6_detail`, `stage6_blend`, the
  fill's lifts inside a shape). `machine.py` gives the reason: "leaving long
  floats means someone picks them out with scissors afterwards".
- **The cut is in the stream.** `stitches.iter_machine_commands` yields a
  TRIM and then the JUMP, and `apply_ties` locks the thread either side. The
  worksheet's trim count is that same stream.
- **No leading move.** "A jump is only emitted once something has been
  sewn": the file starts at its first stitch.
- **pystitch writes a cut the way `dst.js` does.** A TRIM is three jump
  records (`DstWriter.py`, `trim_at` 3) and a JUMP over 12.1 mm is split
  (`MAX_JUMP_DISTANCE = 121`). Reading, it makes a TRIM of three jumps in a
  row once something has been sewn since the last cut
  (`EmbPattern.interpolate_trims`).

The browser builder has the same number, `fabric.trimAtMm`, and as shipped
uses it between shapes only. By Python's rule it would also cut the floats of
one jump record: 213,210 of 4 mm and over in the Studio's shapes as shipped,
14,868 with `fillColumns`.

## What a machine does with three jumps in a row

Every controller whose manual was read acts on it as shipped: seven cut, and
Tajima's steps the frame with the main shaft stopped. The number is an
operator's setting.

| machine | the setting | as shipped |
|---|---|---|
| Brother PR680W | "DST" jump codes for trimming: that many jump codes in a row are converted to a trim code, one fewer are not | on, 3 |
| Barudan BEXS, BEVT, BEKT | `Trim Jumps`: set at 3, the machine stops and trims on reading three or more jump stitches in a row | 2 |
| Happy HCS | `Cut at jump data` | 3 |
| Ricoma 8S, EM-1010 | `Jump to Trim` | 3 |
| Dahao BECS-A15 | `Jump & Trim` | 3 jumps |
| SWF B series | `JUMP CONVERT` ("Trimming after jumps") | 3 |
| ZSK T8 | `Trimming 3 Jump stitches` | 3 on the manual's screen |
| Tajima TEHX-C, TFHX | `Jump Convert`: that many jump codes in a row become frame stepping, the frame moving with the main shaft stopped | 3 on the manual's screen |

- **Brother says what a mismatch does:** the number must be the one the DST
  was made with, or a trim comes where none was meant, or none where one was.
- **A Barudan cuts at two as shipped**, so it also cuts every float over
  12.1 mm.
- **Some controllers tie in after a cut by themselves.** Barudan's `Lock
  Stitch` splits the first stitch after a trim in two as shipped, Dahao lays
  two lock stitches after a trim, and Happy's settings list `STR. Lock
  stitch: Yes`. No manual read has the machine tie OFF before a cut it made
  itself.
- **Happy can undo it:** `Combine jump` joins jump records in a row into
  moves of up to 12.7 mm when the design is read. Off as shipped.
- **A PES is not safe from it either.** With `Thread Cut Initial Setting`
  on, a Brother trims any jump stitch over a set length in a pattern that is
  not a DST.

**Not known.** What a trim before the first stitch costs: the file's first
move is three jumps or more in 4,370 of the 8,270 Studio designs, and no
manual read says. What an unlocked cut under a fill does to the sew-out.
Nothing here has been sewn.

**ROADMAP gate 1.** "Three jump records" is the format's arithmetic and the
writer's own rule for a cut, not a physical constant. No choice below sets a
length.

## The choices

Choice 2 was priced on a scratch copy of `main`'s engine. Numbers are the
Studio's shapes and then the image lane.

| | what moves | cuts nobody asked for | what it costs |
|---|---|---|---|
| **1. Leave it** | nothing | 109,561 and 70,435; with `fillColumns` 6,956 and 451 | what it costs today |
| **2. The builder cuts where the writer lays three jumps**, behind a new flag | the stream gains a `trim` at each; no stitch moves | 0 and 0, in either arm | EXP and PES gain those cuts: 0.84 and 1.8 a design with `fillColumns`, 13 and 280 without. With `ties`, four stitches a lock: 0.09% and 0.07% more stitches with `fillColumns`, 1.4% and 12% without |
| **3. The writer keeps a float under three records where it can** | `dst.js` joins jump records in a row into one move | 862 fewer in the Studio's shapes, 1 fewer in the image lane | DST bytes change with no flag wherever the stream has two jump records in a row. Nothing over 24.2 mm is reached |
| **4. Count them for the operator** | the review screen and the sheet count the cuts a DST machine makes, and their time | all still there | no stitch or byte moves. The ends stay unlocked. A DST-only number on a sheet that is not per format |

- **2 in full.** One pass over the finished stream, before `ties`. A float
  is the jump records between two stitches of one thread; where the writer
  would lay three or more for it, counting the move to the stitch after, the
  stream gets a `trim`. Inside a run the float's first jump becomes the
  `trim`, as the center-out fill's own cut is written. At a run's opening
  jump a `trim` on the spot goes in before it, as between shapes today.
- **What 2 does to the files**, on 414 Studio designs: every stitch and
  colour record is the same and in the same order in all that get a cut (253
  as shipped, 178 with `fillColumns`). The DST's cuts are the ones a machine
  already makes (120,959 before and after) and the frame travels the same
  lines. The file gains jump records: three of no length for each cut put in
  before a run, as every trim between shapes has today. And where a float
  whose first jump is one or two records becomes the `trim`, the writer lays
  it as three, so the frame stops at other points along that line.
- **2 belongs after `fillColumns`.** Before it, it writes into the stream
  the hundreds of cuts the plain walk's floats already are on a DST machine,
  and `ties` would then lock each one.
- **2 at three leaves the floats of two records**: 5,671 and 554 with
  `fillColumns`, which a Barudan as shipped still cuts.
- **Not offered: Python's rule**, a cut at every float over the fabric's
  trim length inside a shape too. It asks a different question, how long a
  float may be, and with `fillColumns` it adds about 27,500 cuts to the
  Studio's shapes where choice 2 adds 6,956.
- **Not offered: sewing the way** from the underlay to the fill instead of
  floating. Not measured.

## What was recommended

Choice 2, built OFF like `fillColumns`, `ties`, `fillStagger` and
`dedupeHoles`, and flipped after `fillColumns`.

As shipped this is a real problem, and it is defect 52 seen from the machine:
the floats the plain walk leaves across holes are not floats on a DST
machine, they are cuts with nothing to hold them, 280 a design in the image
lane. The cure for that is the flip already waiting, `fillColumns`. What is
left is one or two a design, and on its own that is a nitpick. But it is
exactly where `ties` cannot reach, the stream would say what the machine
does, and it moves no stitch.

## What was built

`cutFloats: true` on `buildQualityDesign`: one pass over the finished stream,
before the locks (`cutLongFloats` in `src/digitize.js`). OFF by default, and
no Studio caller passes it.

- **A float** is the jump records between two stitches of one thread. Where
  the writer would lay three or more jump records in a row for it, the stream
  gets a `trim`.
- **The count is the writer's own**, asked of it (`dst.jumpRecords`), not
  worked out from a length. The move to the stitch after the float counts:
  after a jump the writer lays a long move to a stitch as jump records up to
  its last.
- **Inside a run** the float's first jump becomes the `trim`. **At a run's
  opening jump** a `trim` on the spot goes in before it, so the run still
  opens on its jump and the cut is in no span.
- **No thread, no cut**: the stream's first move, a move after a cut or a
  colour change, and a float that ends in a cut are left.
- **Floats of two records are left**, as priced.
- **Not the lettering builder**, which has none to cut.

The engine merged with `main` at `4fb4fcd4`, against that `main`:

| | the sweep, 8,255 | the Studio's shapes, 8,270 | the image lane, 252 |
|---|---|---|---|
| flag not passed: designs whose stream and spans are `main`'s | 8,255, and 8,255 with `fillColumns` | 8,270, and 8,270 | 252, and 252 |
| `cutFloats` alone: cuts nobody asked for | 12,346 to 0 | 109,561 to 0 | 70,435 to 0 |
| `trim` records in the stream | 8,175 to 20,521 | 7,028 to 116,589 | 2,844 to 73,279 |
| designs that change, each by cuts put in and nothing else | 4,460 | 4,805 | 183 |
| designs that change some other way | 0 | 0 | 0 |
| cuts in the DST, as its reader finds them | 21,340 before and after | 120,959 before and after | 73,491 before and after |
| stitches | 18,424,406 before and after | 60,695,036 before and after | 4,513,269 before and after |
| with `fillColumns` too: cuts nobody asked for | 2,064 to 0 | 6,956 to 0 | 451 to 0 |
| designs that change, by cuts put in and nothing else | 1,685 | 3,544 | 107 |
| designs that change some other way | 0 | 0 | 0 |
| cuts in the DST | 5,060 before and after | 14,016 before and after | 3,216 before and after |

Every cut put in is one the count above found: 8,175 and 12,346 is 20,521.

The lettering builder's 765 designs are `main`'s with the flag and without
it. Against the scratch engine the choices were priced on: the same stream
and spans on every fourth design of the three sets (4,195 designs, in all
four arms), and every count of the full run is that engine's.

- **Tests first.** Fifteen in `test/digitize.test.js` and two for
  `jumpRecords` in `test/encoder-split.test.js`, each seen to fail: on the
  engine before the rule, or on a mutant.
- **Twenty-two mutants, twenty-two die**: the flag read backwards, the rule
  without the flag, cuts not counted, a cut at two records and at four, the
  move to the stitch after left out or counted whole, a float cut that ends
  in a cut or ends the stream, a float cut with no thread on it, a run's
  opening jump made the trim itself, every cut put in before its float, the
  cut before a run counted into the run or put where the jump lands, spans
  not moved or half moved, the cut inside a run put where the float ends or
  keeping its jump, only the first float cut, a float measured from its
  second record, and `jumpRecords` wrong two ways.
- **Engine suite** 818 passed. **Doc guards** 76 passed.

**The independent re-measure** (a separate agent, with its own generator and
its own readers of the files) is running as this is written. The PR is not
armed until it reports, and its result goes here.

*(measured 2026-10-04, `node tools/file-cut-census.mjs --set tools/file-cut-sweep-set.mjs
--set shapes --set image --on cutFloats --against <main's src>`)*

## Seen on the way, not this note's

- **The file's first move is three jumps or more** in half the Studio
  designs: the builder centres the design and travels to its first stitch.
  pystitch does not read it as a cut. Python writes no such move.
- **A satin column that floats away and sews back where it was**:
  `s-91,-3 j94,1 s-101,0` on a four-point star at 20 mm. The float is two
  records and the move back to the stitch a third. Defect 57's shapes.

## To reproduce

```bash
node tools/file-cut-census.mjs                                     # this checkout: shapes, lettering, image
node tools/file-cut-census.mjs --set tools/file-cut-sweep-set.mjs  # the sweep of #616 and #617
node tools/file-cut-census.mjs <src> --set shapes                  # another engine
node tools/file-cut-census.mjs --on cutFloats                      # beside each arm, the arm with the flag on
node tools/file-cut-census.mjs --on cutFloats --against <src>      # and how each stream differs from another engine's
node tools/file-cut-census.mjs --keep <dir>                        # a run that picks up where it was cut short
node tools/file-cut-census.mjs --pystitch <python>                 # pystitch's count beside this reader's
```

Manuals: [Brother PR680W](https://download.brother.com/welcome/doch102285/884t23_om01en.pdf) (pages 109 and 110),
[Barudan BEXS](https://www.barudan.co.uk/wp-content/uploads/2020/09/BEXS-Instruction-manual_en.pdf) (machine conditions 2 and 3),
[Barudan BEVT](https://www.barudan.co.uk/wp-content/uploads/2020/09/BEVT-Instruction-manual_en.pdf),
[Barudan BEKT](https://www.barudan.co.uk/wp-content/uploads/2020/06/BEKT-V1-Instruction-manual_en-1.pdf),
[Happy HCS](https://happyemb.com/files_tech/hcs_manual_bdi701.pdf),
[Ricoma 8S](https://www.ricoma.cn/upfile/news/pdf/2021-02-26/6038c4a423d1b.pdf),
[Ricoma EM-1010](https://www.ricoma.cn/upfile/news/pdf/2024-11-15/6736f5b255761.pdf),
[Dahao BECS-A15](https://www.cabolisan.com/wp-content/uploads/2021/01/BECS-A15-User-Manual-Version-2020-04.pdf) (a reseller's copy),
[SWF B series](https://www.silmaq.com.br/wp-content/uploads/downloads/MANUAIS/SWF/Manual%20de%20Instru%C3%A7%C3%A3o/swf-serie-b-b-t1201c-manual-de-instrucoes-ingles.PDF) (a dealer's copy),
[ZSK T8](https://www.zsk.de/pdf/download/manual-anwendung/03-t8_bedieneinheit/gb/02399v10-t8-user_manual-21-03-2018.pdf),
[Tajima TEHX-C and TFHX](https://silmaq.com.br/wp-content/uploads/downloads/MANUAIS/TAJIMA/Manual%20de%20Instru%C3%A7%C3%A3o/tehx-c-and-tfhx-lcd-m-efhx-lcd-04-e-2003-07.pdf) (a dealer's copy).
