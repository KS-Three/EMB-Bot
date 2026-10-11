# `cutFloats` on the manual lane, after `fillColumns` (2026-10-08)

**Flipped ON for the manual (hand-drawn) lane only**, in
`app/src/lib/generate.js`, beside `fillColumns` (#662). The engine default
stays off, and the image and basic-shape lanes pass nothing. "Waiting on
Kent" 28 had this sequenced after `fillColumns`; this note is the measurement
that sequencing asked for. **Not sewn.**

What the flag does is in [`dst-float-cuts-2026-10-04.md`](dst-float-cuts-2026-10-04.md):
a float the DST writer lays as three or more jump records is a cut on a DST
machine, so the stream gets a `trim` there. No stitch moves.

## The named shapes

`node tools/cut-floats-sheet.mjs`. These are `tools/fill-columns-sheet.mjs`'s
four shapes, its 36-hole badge and a plain 40 mm square. Each is built the
way the manual lane calls the engine, with `fillColumns` on, under six
garments: hat_front, left_chest, beanie, full_back, tote and towel.

| shape | stitches | trims off → on | DST cuts nobody asked for | floats (mm) | floats over 4 mm leaving the fill | locks with `ties` | stitches with `ties` |
|---|---|---|---|---|---|---|---|
| Badge, two cut-outs | 21,560 | 0 → 2 | 2 → 0 | 23 (365) → 21 (289) | 0 → 0 | 12 → 16 | 21,608 → 21,624 |
| Ring (an O) | 11,372 | 0 → 0 | 0 → 0 | 17 (189) → 17 (189) | 0 → 0 | 12 → 12 | 11,420 → 11,420 |
| Two counters (a B) | 13,078 | 0 → 0 | 0 → 0 | 23 (292) → 23 (292) | 0 → 0 | 12 → 12 | 13,126 → 13,126 |
| Wide U (a notch) | 14,827 | 1 → 1 | 0 → 0 | 10 (46) → 10 (46) | 0 → 0 | 14 → 14 | 14,883 → 14,883 |
| 36 square holes of 4 mm, 60 mm | 51,629 | 0 → 2 | 2 → 0 | 227 (2,065) → 225 (1,959) | 2 → 2 | 12 → 16 | 51,677 → 51,693 |
| Plain square, 40 mm | 22,045 | 6 → 15 | 9 → 0 | 11 (416) → 2 (39) | 0 → 0 | 24 → 42 | 22,141 → 22,213 |
| **all 72 builds** | 134,511 | 7 → 20 | 13 → 0 | 311 (3,373) → 298 (2,814) | 2 → 2 | 86 → 112 | 134,855 → 134,959 |

- **No stitch moved**, in any of the 72 builds. The needle points are the
  same and in the same order.
- **No new thread.** Not one sewn or floated segment in the "on" stream is
  missing from the "off" one. So nothing new travels over sewn rows, and no
  new float leaves the fill: a cut only takes thread away. Sewn thread is
  418,211 mm both ways.
- **The two floats leaving the fill** on the 36-hole badge are left over
  from `fillColumns` and are there with this flag off too. (The measure
  allows 1 mm outside the drawing for pull compensation.)
- **The plain square carries most of it.** The move from the underlay to
  the fill crosses its face, 40 mm or more. A shape with no hole keeps that
  float under `fillColumns`, because there is nothing to sew round.

## The corpus

`node tools/file-cut-census.mjs --set shapes --on cutFloats`: the Studio's
shape lanes, 8,270 designs, of which 5,400 are hand-drawn manual fills with
cut-outs, under six garments. Each file is written by all three writers and
read back from its format. On `main` at `32dd9a9` plus this branch; 853 s
on four jobs.

| manual lane, `fillColumns` on | `cutFloats` off | on |
|---|---|---|
| cuts nobody asked for (DST) | 4,264, in 2,560 of 5,400 designs | **0** |
| `trim` records in the stream | 1,541 | 5,805 (+0.79 a design) |
| cuts in the DST, as its reader finds them | 9,089 | 9,089 |

| whole shapes set, `fillColumns` on | off | on |
|---|---|---|
| stitches | 61,421,054 | 61,421,054 |
| needle holes, each of DST, EXP, PES | 61,435,998 | 61,435,998 |
| cuts nobody asked for | 7,063 | 0 |
| with `ties`: thread ends at such a cut, unlocked | 14,126 (76 locked by chance) | 0 |
| with `ties`: stitches | 61,507,230 | 61,562,918 (+0.09%) |

What the cuts were with `fillColumns` on (the whole set): underlay to
underlay 2,942, underlay to fill 2,326, a satin arm floating to another arm
1,528 (defect 57's shapes), inside an underlay run 146, inside a fill run 71,
underlay to satin 50.

## What it costs

- **On a DST machine it costs nothing.** The machine already cut at all
  9,089 places. The stream now says so, so the trim count and the run time
  include them, and `ties` could lock them.
- **EXP and PES gain those cuts: 0.79 a manual design.** Those formats have a
  trim of their own, so there the float was a float, mostly under the fill
  (underlay to fill, underlay to underlay), where the builder leaves it on
  purpose. **With `ties` off, as the Studio ships, the cut is not locked.**
  On a PES or EXP file this trades a hidden float for an unlocked cut. This
  is the trade-off to look at; `ties` ("Waiting on Kent" 23) is what closes
  it.
- **Build time:** within noise on the named shapes (690 → 676 ms over 72
  builds). The 2026-10-04 re-measure found 3 to 50 ms a build on large plain
  walks, which `fillColumns` mostly removes.

## Guard

`app/src/lib/generate.spec.js`, "a manual fill leaves no float a DST machine
reads as a cut". It builds a plain 40 mm manual square and checks three
things: no such float with the flag; at least one with the flag left out;
the same needle points both ways. It fails with the flag set to `false`
(checked). The `fillColumns` test beside it now compares against the call
with both flags.
