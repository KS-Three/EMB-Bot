# Two stitches in one hole: the browser fill's stitches under the file's unit (2026-10-03)

It measures a finding handed over from PR #617 and sets out the choices.
**Kent chose the same day: choice 4.** It is built as `dedupeHoles` on
`buildQualityDesign`, OFF by default, so no stitch changes until he flips it
("Waiting on Kent" 25). What follows is what was put to him; what was built
is at the end.

## What it is

`buildQualityDesign` rounds every point to the stitch file's unit, 0.1 mm
(`T` in `src/digitize.js`). Two penetrations nearer than that can land on one
point: two `stitch` records in a row with the same x and y. The DST, EXP and
PES writers keep such a record (`00 00 03` in a DST), and pystitch reads it
back from all three as a stitch on the spot the needle is already on. So the
needle goes down twice in one hole.

It is in what ships today, with every flag absent. It is not a regression and
not part of #616 or #617.

## How many

Three sets of designs, read by `tools/sub-unit-stitch-census.mjs`. The tool
wraps `tatamiFill`, finds each pass in the finished stream, and says for each
pair how far apart the two points were before rounding. A second reader, an
instrumented `pushRun` in a scratch copy of the engine, gave the same counts
on the sweep. Both reproduce the handover to the stitch.

| designs | flag absent (what ships) | `fillColumns` on, after #617 |
|---|---|---|
| the 8,255 of the #616 and #617 sweep | 16,575 pairs on 7,097 designs | 3,783 on 2,553 |
| 8,270 from the Studio's own shape lanes | 16,399 in tatami passes, 23,549 in satin | 7,791 and 23,549 |
| the 49,920 of #617's independent audit | 76,483 on 36,183 | 21,136 on 13,189 |

On the sweep that is two a design and one stitch in 1,100. EXACT pairs were
one point before rounding too. SHORT pairs were a real distance apart:

| the sweep | exact | short |
|---|---|---|
| flag absent | 12,344 | 4,231 |
| flag on, plain-walk passes | 1,094 | 68 |
| flag on, column-walk passes | 0 | 2,621 |

Flag absent, the engine at `main` and the engine at #617's head give the
same record stream on every design of the first two sets.

*(measured 2026-10-03, `node tools/sub-unit-stitch-census.mjs <src>`, engines
at `cf9f89f1` and `dcec1f91`. The audit's set was read through an adapter
round its own generator, which is in that session's scratchpad and not in
the repo.)*

## What makes them

Read off the tool's own scanline, cut from the rings the builder gave the
fill.

| what | sweep, absent | sweep, on | Studio lanes, absent | Studio lanes, on |
|---|---|---|---|---|
| **corner**: a scanline through a corner, a span of no length | 12,072 | 1,094 | 13,087 | 4,470 |
| **touch**: two spans of one scanline that meet at a point | 272 | 0 | 0 | 0 |
| **tip**: the last rows of a strip that narrows to nothing | 1,366 | 1,720 | 1,534 | 1,794 |
| **gap**: the move across a gap under the unit wide | 2,700 | 686 | 1,055 | 375 |
| **lone**: a narrow row with no row over or under it | 112 | 229 | 595 | 1,012 |
| **turn**: from one row's end to the next row's start | 36 | 35 | 91 | 103 |
| **waist**: a strip narrowed between two wider parts | 17 | 17 | 37 | 37 |
| anything else | 0 | 2 | 0 | 0 |

- **Corner is the plain walk's, and is most of what ships.** Its first
  scanline sits on the shape's topmost point, so a shape whose top is a
  corner gets a doubled hole there in every pass: 5,687 of the sweep's 12,072
  are in underlay. The column walk has left these out since #616.
- **A tip is one or two rows deep** on the sweep, and up to six in the
  Studio lanes.
- **A gap is not a row.** It is the move from the end of one span to the
  start of the next across the mouth of a notch. The audit's "15,518 along a
  row" are 11,561 rows and 3,957 of these moves; the other 48 are turns.
  `spansWithLength` keeps the first kind, `sewTo` the second.
- **A turn rounds to nothing only under fleece and terry**, whose row pitch
  (0.135 and 0.128 mm) is under the unit times the square root of two, on
  rows near a diagonal. It is the longest of them: up to 0.14 mm.
- **No sliver.** No strip two rows long that is narrow from end to end, in
  any of the three sets.
- Every preset and none, every row angle, fill and underlay.
- **A slit makes a line of them.** A slot a hair wider than twice the
  preset's pull compensation is sewn under the unit wide, and the plain walk
  doubles a hole on every row that crosses it: 212 in a design of 4,817
  stitches for a slot 1.21 mm wide and 28 mm long under terry, 2 at 1.30 mm.
  Neither set has one; the island lane reported it. The column walk goes
  round and has none.
- **Not in these counts:** one hole twice with only a jump between the two.
  One run ends and the next begins on the spot (every run opens with a
  jump): 15 on the sweep with every flag absent and 58 with the flag on, 2
  and 7 in the Studio lanes. Or a satin column floats away and comes back to
  sew where it was: 59 in the Studio lanes, all on 12-point stars. A rule on
  the record stream has to say whether it looks through a jump. *(on `main`
  at `f887e27d`)*

**How short.** Of the 4,231 short ones, 4,170 were under 0.1 mm apart. As
many stitches that short land a unit APART as land together (4,111): which
it is turns on where the row sits on the file's grid. And both sit among
1.85 million stitches under 0.3 mm, a tenth of the sweep: the row turns,
one row pitch long by design.

## What the Python engine does

- **A scanline through a corner:** never the first one, which sits half a
  row inside the top edge, and a span of no length is dropped (`_row_spans`).
- **A row under `TINY_STITCH_MM` (0.5 mm):** one penetration at its middle,
  not two (`_row_points_at_phase`).
- **A move under 0.5 mm between columns:** no travel stitch (`travel_path`).
- **At the record stream:** a penetration within `SAME_POINT_MM` (0.01 mm) of
  the one before it on a continuous path is dropped; a jump, a trim or a new
  block resets it (`stitches.iter_machine_commands`, and the adapter the
  Studio reads). Measured before rounding, so a turn under terry can still
  round onto one point there too.
- **No pass that drops short stitches.** `stitches.py` says why: a row turn
  is one row pitch long and its ends are the edge.

## What a machine does with the record

It depends on the machine. Manuals read for this note:

| machine | what its manual says | as shipped |
|---|---|---|
| Barudan BEXS | `0 admit`: how many zero-data stitches are let in when a design is read (BEKT has the same setting) | 0: all deleted |
| Ricoma 8S | `Filter 0 Stitch Data` | Yes |
| Brother PR680W | `Short Stitch Delete` removes stitches under the set length; zero-pitch stitches in the data are listed as a cause of upper thread breaks | 0.3 mm |
| ZSK T8 | cleaning removes stitches under 3 INC (0.3 mm) on loading; the reason given is the needle going into one hole twice | on with standard optimisation |
| Dahao BECS-A15 | `Filter Short Stitch` | Yes, 0.5 mm |
| Happy HCS | `Skip null stitch`, `Stitch sweeper` | both No |
| Tajima TEHX-C, TFHX | Cleanup is an edit the operator runs (0.4 to 0.9 mm); "repeated stitching at the same point" is a cause of thread breaks, and the remedy is to correct the data. The TMEZ-SC manual says the same of numerous stitches of 0.5 mm or less | no filter found |

Ink/Stitch drops any stitch of 0.1 mm or less at the end of its stitch plan
(`min_stitch_len_mm`), except after a jump, a trim or a colour change and in
a lock stitch. Wilcom uses a zero-length stitch on purpose, as a tie.

**Not known.** No source read says what a Tajima does with ONE such record.
That it sews it is inference: no automatic filter in its manuals. No source
measures the harm of one; the warnings are about repeated or numerous ones.
Nothing here has been sewn.

**ROADMAP gate 1.** No choice below sets a physical constant. "The same
point of the file" is the file's arithmetic. A rule with a length in it
(a machine's 0.3 mm, the Python row's 0.5 mm) is a constant, and is not
offered.

## The choices

Priced on scratch copies of the #617 engine. Pairs left are for the sweep and
then the Studio lanes.

| | acts when | pairs left | what else moves |
|---|---|---|---|
| **1. Leave it** | | 16,575 and 39,948 absent; 3,783 and 31,340 on | nothing |
| **2. Column-walk passes lay no second stitch in a hole** | `fillColumns` on | on: 1,162 and 28,314 | nothing. 1,801 and 1,514 streams lose those records and no other; cuts 2,196 and 2,686 as before |
| **3. Leave such a row out of the columns** | `fillColumns` on | on: 1,894 and 28,758 | 1,328 and 1,299 designs change some other way: the tip's hole goes with its row and the walk plans again; cuts 4 and 19 fewer |
| **4. No run lays a second stitch in a hole, behind a new flag** | that flag is passed | 0 and 0, either arm | nothing. 7,097 and 7,518 streams lose those records and no other; cuts as before; 16,575 and 39,948 fewer stitches |

- **2** is three lines in `pushRun`, on passes the column walk made. It
  leaves a plain shape's pairs with the flag on, and all that ships.
- **3** is in `fill.js`, which would have to be told the rounding. It reaches
  rows only (73% and 85% of the column walk's), and every changed design
  would need its thread checked against the ground again.
- **4** is Python's stream rule with "the same point of the file" in place of
  0.01 mm. Built OFF like `fillColumns`, `ties` and `fillStagger`, so
  flipping it is one more decision waiting on Kent. It is the only choice
  that can reach what ships, and the only one that reaches satin.
- **"Merge it into its neighbour"** is what 2 and 4 do: the row keeps one
  penetration. Python's own merge, the row's middle, is the length rule
  above, and moves row ends the walks are built on.

## What was recommended

Choice 4. In size this is a nitpick: two holes a design. In kind it is bad
data: every vendor that documents the record either deletes it or tells the
operator to. Taking it out moves no stitch, and only choice 4 can ever take
it out of a design a customer downloads.

## What was built

`dedupeHoles: true` on `buildQualityDesign`: no run lays a stitch on the
point its thread's last stitch is on. Fill, underlay, satin and edge run,
either walk. OFF by default, and no Studio caller passes it.

- **It is asked of the thread, not of the frame.** A jump lays nothing, so
  the stitch after one is weighed against the stitch before it. That takes
  in the run that begins where the last one ended, and the satin column that
  floats away and comes back. A cut ends the thread: the first stitch after
  a trim or a colour change is laid wherever it lands, because it is what
  holds the new thread.
- **It lives in `pushRun`** (`src/digitize.js`), the one place that knows
  the rounding. Nothing in `fill.js` changed.
- **Locks are not thinned.** `ties` is applied to the finished stream, after
  this.
- **Not the lettering builder**, which has its own stream.

On `main` at `f887e27d` with the rule added, against `main` itself:

| | the sweep, 8,255 | the Studio lanes, 8,270 |
|---|---|---|
| flag not passed: designs whose stream is `main`'s | 8,255, and 8,255 with `fillColumns` on | 8,270, and 8,270 |
| `dedupeHoles` alone: pairs | 16,575 to 0 | 39,948 to 0 |
| one hole twice with only a jump between | 15 to 0 | 61 to 0 |
| stitches | 18,424,406 to 18,407,816 | 61,318,824 to 61,278,815 |
| designs that change, each by those stitches and nothing else | 7,100 | 7,539 |
| designs that change some other way | 0 | 0 |
| cuts | 8,175, unchanged | 7,028, unchanged |
| with `fillColumns` too: pairs | 3,783 to 0 | 31,340 to 0 |
| one hole twice with only a jump between | 58 to 0 | 66 to 0 |
| designs that change, by those stitches and nothing else | 2,589 | 4,374 |
| designs that change some other way | 0 | 0 |
| cuts | 2,177, unchanged | 2,686, unchanged |

Every stitch taken out is counted in the first two rows of its block:
18,424,406 less 16,575 less 15 is 18,407,816.

- **Tests first.** Eight in `test/digitize.test.js`. Four were watched
  failing before the rule existed. The other four hold with or without it,
  and each was seen to fail on a mutant of the rule.
- **Ten mutants, ten die**: the rule without the flag, the flag read
  backwards, a cut that does not end the thread, a jump or a float that
  does, the same x or the same y taken as the same point, a hole never moved
  on, a hole never noted, and a record taken out after the spans were
  written. The float was caught by the census before a test: that mutant is
  the engine on every design of the sweep and differs on 52 of the Studio's.
- **Engine suite** 709 passed. **Doc guards** 76 passed.

*(measured 2026-10-03, `node tools/sub-unit-stitch-census.mjs --on
dedupeHoles=true --off dedupeHoles=true --against <main's src>`)*

## Seen on the way, not this note's

- **The Studio's 12-point star at its thinnest, 20 mm, sews as one satin
  shape of 48,645 stitches** (444 at 12 mm, 1,377 at 30 mm). 21,205 of the
  23,549 satin pairs above are that star. Flagged as its own task.
- **The lettering builder has its own**: 9,093 on `KENT` across the 85 fonts
  (`docs/lock-stitches-2026-10-03.md`). Not measured here.

## To reproduce

```bash
node tools/sub-unit-stitch-census.mjs                 # this checkout, both sets
node tools/sub-unit-stitch-census.mjs <src> --corpus sweep
node tools/sub-unit-stitch-census.mjs <src> --against <other src>
node tools/sub-unit-stitch-census.mjs --on dedupeHoles=true --off dedupeHoles=true
```

The first prints every table above for the engine it is pointed at. The
third says, design by design, whether two engines' streams are the same,
differ only by second stitches left out, or differ some other way. The last
runs both arms with the flag.

Manuals: [Barudan BEXS](https://www.barudan.co.uk/wp-content/uploads/2020/09/BEXS-Instruction-manual_en.pdf) (machine conditions 20 and 21),
[Barudan BEKT](https://www.barudan.co.uk/wp-content/uploads/2020/06/BEKT-V1-Instruction-manual_en-1.pdf),
[Ricoma 8S](https://www.ricoma.cn/upfile/news/pdf/2021-02-26/6038c4a423d1b.pdf),
[Brother PR680W](https://download.brother.com/welcome/doch102285/884t23_om01en.pdf) (pages 110 and 146),
[ZSK T8, Cleaning Design](https://www.zsk.de/pdf/download/howto-t8/2024_t8_functions_vol024__cleaning-design.pdf),
[Dahao BECS-A15](https://www.cabolisan.com/wp-content/uploads/2021/01/BECS-A15-User-Manual-Version-2020-04.pdf) (a reseller's copy),
[Happy HCS](https://happyemb.com/files_tech/hcs_manual_bdi701.pdf) (chapter 14),
[Tajima TEHX-C and TFHX](https://silmaq.com.br/wp-content/uploads/downloads/MANUAIS/TAJIMA/Manual%20de%20Instru%C3%A7%C3%A3o/tehx-c-and-tfhx-lcd-m-efhx-lcd-04-e-2003-07.pdf) (a dealer's copy),
[Tajima TMEZ-SC](https://www.manualslib.com/manual/3382570/Tajima-Tmez-Sc.html?page=127),
[Ink/Stitch `color_block.py`](https://github.com/inkstitch/inkstitch/blob/main/lib/stitch_plan/color_block.py).
Each was read from the page itself, the PDFs by extracted text. The Wilcom
line is from a research pass and was not re-read.
