# Digitize time: where it goes, and the first exact cuts (2026-11-16)

**Question (Kent, 2026-11-16).** "Why does it take so long to digitize an
image? I could understand 15-25 seconds, but over a minute is insane, no one
will want to wait that long."

**Answer.**

- **It is compute on one core, spread over many passes.** The engine is
  single-threaded Python and GEOS (only OCR uses a thread pool). CPU seconds
  equal wall seconds on every run measured. No stage is the hog: the three
  largest check labels are 37-44% of a run.
- **Nine hat jobs take 15-103 s on this laptop today; four are over a
  minute.** Table below.
- **About 9 s of Becker's time is new since 2026-11-14** (44 -> 53 CPU s on
  the same laptop in the same hour, two runs each, interleaved): the plan step
  grew 28 -> 42 s (satin rail push 1.6 -> 9.2 s, where `satin_push_keeps_gaps`
  now runs; stage 7 4 -> 9 s) and generation fell 15 -> 10.6 s. The rest of "21 CPU s on 11-14, 48 today" is
  the laptop: the 11-14 engine itself read 44 today.
- **This PR cuts 10.5% off the nine jobs' total (592 -> 530 s) with stitches
  byte-identical on all nine.** Lettering and keyline work gains most: Becker
  54.5 -> 37.4 s, Gaulke 52.5 -> 39.0, MFab 102.0 -> 85.7. Jobs whose time is
  elsewhere do not move past the laptop's noise.
- **15-25 s is not reached, and exact cuts will not reach it.** What is left
  is spread thin. The next lever is structural: more than one core, or fewer
  passes. Both are Kent's call ("What would get to 15-25 s").

## Method

One job at a time, at the pro's size, through `tools.pro_pair` (the Studio's
request, the service's parser): `build_generation`, `finish_generation`,
`plan_stitches`, after one untimed warm-up digitize. That is
`python -m tools.flip_timing run SLUG main`'s measurement; the table's runs
used the same calls from a scratch script that also prints the plan's md5
(`tools.flip_timing.plan_md5`). Base is `origin/main` at `91e3fc42`, in its
own checkout; each job ran base then lane back to back.

Laptop: Ryzen 7 4700U, 8 cores, clocked 1.4 of 2.0 GHz, other sessions at
5-86% load. **n = 1 per cell.** One GEOS call read 3.25 s and 4.27 s in two
runs of the same code that hour, so a difference under about 10% is noise.
Identity is by md5, which no load moves.

## Table (wall seconds, base -> lane)

| job | base | lane | change | plan md5 |
|---|---:|---:|---:|---|
| Becker (hat, large) | 54.5 | 37.4 | -31% | same |
| Gaulke (hat) | 52.5 | 39.0 | -26% | same |
| MFab (hat) | 102.0 | 85.7 | -16% | same |
| Hotel Fremont (hat) | 92.8 | 81.2 | -13% | same |
| Golden Tee (hat) | 103.2 | 94.6 | -8% | same |
| Bridge (hat) | 34.7 | 32.3 | -7% | same |
| Tires (hat 3D) | 15.5 | 15.1 | -3% | same |
| To a T machine (hat) | 47.7 | 50.3 | +5% | same |
| Precision drone | 89.4 | 94.3 | +5% | same |
| **total** | **592.3** | **529.9** | **-10.5%** | |

To a T was profiled on both trees to see whether the +5% is real: 67.2 s base,
68.2 s lane under cProfile, with the keyline's ray cuts 4.3 s cheaper on the
lane and an untouched single GEOS call (`stage6_fill._footprint`) 1.0 s dearer.
Noise. The drone's +4.9 s is 3.8 s of generation, which this PR does not
touch on that job.

## Where the time goes (cProfile, before the cuts)

| | Becker | MFab | Fremont |
|---|---:|---:|---:|
| whole run, profiled | 72 s | 134 s | 107 s |
| generation | 13 | 19 | 57 |
| lettering columns (cut search + sewing) | 31 | 50 | 12 |
| keyline loops | 9 | 12 | - |
| outline band reader (`shaped_width_mm`) | 6 | 19 | - |
| fills, satins, trim bury, the rest of the plan | 13 | 33 | 39 |

The lettering lane sews a letter many times before it sews it for good: once
per cut the fold judge tries, once per walk `_edge_walk` tries. Fremont's
generation is the redraw, small-text re-set, thread revalidation and stage 5
run twice (`_off_angles`, since `outline_inlets_kept`).

## The cuts (each one exact; `tests/test_speed_exact_1116.py` holds each to the code it replaced)

1. **Keyline crosses no edge touches** (`stage6_border._cross_unobstructed`).
   `_exact_cross` overlaid one ray on the whole outline at every station:
   16,000 overlays on Becker's or MFab's hat. A ray with no outline edge
   within 1e-9 mm of it past the rail is the ray's own length or 0.0, with no
   overlay. On four hat jobs it answered 29,784 of 46,334 crosses, and every
   answer was the overlay's float (0 mismatches, asked both ways on every
   call). The rest go to the overlay as before.
2. **A letter's rails pushed once** (`columns._RAILS_MEMO`). `sewn_rails` for
   the same column of the same letter with the same pull, faces and keep is
   computed once per `lettering_columns_shape` call. 234 pushes on Becker.
3. **The sewn judge's knot count** (`outline_cut.sewn_knots`). 188,000
   single `crosses` calls on Becker asked as arrays, over the pairs whose
   boxes meet.
4. **Rail samples** (`outline_cut._along`, `art_outline.band_thickness`,
   `shaped_band._read_band`). One GEOS call per ring in place of one per
   point: 74,000 calls on MFab.
5. **The rail pairing table** (`outline_cut._dtw_cost`), filled by
   anti-diagonal instead of a Python loop over every cell.
6. **The band reader** (`shaped_band._square_partners`). Every sample's ring
   stretch read as one array. A sample that reads a chord end inside a
   one-ulp back-step at the lap seam is still read alone, because
   `np.interp`'s answer there depends on its search path.
7. **The distinct-colour count** (`stage2_quantize._distinct_colors`). 7 s of
   Fremont's generation was `len(np.unique(rgb, axis=0))`; 8-bit rows are now
   counted as packed integers.
8. **Neck-split halos** (`textcluster._neck_split`): each part's buffer built
   once, not once per leftover piece.

## Not taken, and why

- **The crosses an edge does cut** (16,550 of 46,334): the answer is GEOS's
  own intersection point, and nothing short of the overlay returns that
  float.
- **Thread revalidation's CIEDE2000** (8 s on Fremont): scoring each distinct
  colour once would need numpy's vector maths to answer the same for a value
  wherever it sits in an array. True in practice, not by construction.
- **Stage 5 run twice** (8 s on Fremont): `_off_angles` is the design.
- **One frame converted to Lab five times** (2.5 s on Fremont): a cache would
  hold 50 MB between jobs for 2%.

## What would get to 15-25 s

After these cuts no single exact cut over about 3 s was found. Two levers
remain, neither exact by default:

- **More cores.** Seven of eight sit idle. The letter cut (`letter_columns`,
  10-27 s) depends on the needle's entry only through the judge; with
  `lettering_columns_judge_entry_free` (built OFF, #1589) it does not, and
  every letter's cut could then be computed ahead in a process pool. Shapes'
  fills and satins are memoized per shape (`shape_memo`) and could be warmed
  the same way.
- **Fewer passes.** The fold judge and `_edge_walk` re-sew a letter per
  candidate; a cheaper judge or a candidate cap is a quality trade.

A customer's desktop is also faster than this laptop at 1.4 GHz; that is not
measured here.
