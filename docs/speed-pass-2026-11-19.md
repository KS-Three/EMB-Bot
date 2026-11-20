# Digitize time: the second exact pass (2026-11-19)

**Asked.** Kent un-parked speed (parked 2026-11-16) and asked for the four
hat jobs over his 25 s bar to come down: MFab 28 s, Fremont 31, Drone 36 and
Golden Tee 38 on an idle laptop (`docs/speed-pass-2026-11-16.md`).

**Answer.** Four more exact cuts, with stitches md5-identical on all four
jobs. Three jobs lose about a fifth of their compute. MFab barely moves: its
time is the lettering lane, which was the 11-16 pass's ground.

**Measured on a loaded laptop, so these are CPU seconds, not wall seconds.**
About 25 `tools.flag_sweep` runs from other sessions and a `pytest -n 12`
held the laptop at 100% for the whole session, with `% Processor
Performance` at about 135 against about 185 when idle. Every cell below is
the process's own CPU seconds (`time.process_time`), which load moves far
less than the wall clock. The figure is the median of three rounds, with
base and lane run back to back in each round, one job at a time.

| job | base CPU s | lane CPU s | change | generation | finish | plan | plan md5 |
|---|---:|---:|---:|---|---|---|---|
| MFab (hat) | 35.3 | 33.5 | -5% | 5.4 -> 5.7 | 4.6 -> 1.6 | 25.3 -> 25.9 | same (3/3) |
| Hotel Fremont (hat) | 53.9 | 44.7 | -17% | 27.0 -> 24.5 | 11.9 -> 4.4 | 15.0 -> 16.4 | same (3/3) |
| Precision drone | 53.6 | 41.8 | -22% | 19.6 -> 15.0 | 7.9 -> 2.5 | 26.5 -> 24.4 | same (3/3) |
| Golden Tee (hat) | 49.3 | 41.5 | -16% | 27.7 -> 22.1 | 5.5 -> 2.1 | 16.2 -> 17.3 | same (3/3) |

Rounds (base / lane CPU s): MFab 35.3 35.5 35.2 / 33.5 33.9 31.1;
Fremont 57.1 53.9 51.9 / 44.7 44.2 48.1; Drone 54.8 52.3 53.6 / 41.6 41.8
41.9; Golden Tee 49.3 57.4 48.9 / 39.3 46.0 41.5. The plan column does not
move past noise. The cuts are in generation and finish.

**Idle wall seconds are NOT measured yet**, so nothing here says whether any
job now meets Kent's 25 s bar. Time the two trees back to back on a quiet
machine before quoting a wall figure.

## Where it went

cProfile on each job, whole run, after one untimed warm-up digitize. The
machine was loaded throughout the profiling, so only shares and call counts
are read below; the seconds are profiled seconds.

- **The size ring's corner check was the largest single item on three of the
  four jobs.** `stage7_sequence.tag_border_by_size_groups` asks
  `_corner_loss` of each shape, which runs `stage6_border.round_inward`, and
  `_relax_corners` iterates up to 240 times per ring. Each iteration made
  `2k + 3` calls to `np.roll`. That came to 0.8-1.6 M calls per job, and
  20.6 of Fremont's 69 profiled seconds, 13.1 of the Drone's and 9.6 of
  MFab's. It is most of what `finish_generation` costs: Fremont's finish
  step took 11.9 CPU s before this pass and 4.6 after.
- **One working frame converted to Lab four times in generation.** On Golden
  Tee's hat the same 4.8 Mpx frame went through `threads.rgb_to_lab` from
  stage 1, thin ink, and two stage-4 reads, about 0.5 s each (md5 of the
  bytes, the same on all four calls).
- **Stage 2's edge snap read the whole frame every pass.** On the Drone,
  `stage2_photo_segment.snap_region_edges` was 4.4 profiled seconds. It runs
  up to 64 passes, and after the first only a few pixels can still move.
- **The fine-bar ink test read the whole frame per bar.** On Golden Tee,
  `fine_bar.apply_fine_bar_survive` took 2.3 profiled seconds of generation.
  It computed two Lab distances over every pixel for each bar, inside a band
  a few pixels wide.

## The cuts (each one exact; `tests/test_speed_exact_1119.py` holds each to the code it replaced)

1. **Corner relaxation without `np.roll`** (`stage6_border._roll0`,
   `_window_any`). A roll moves values and computes none, so two slices
   joined give the same array. The `+-k` window flag becomes a running count
   over the ring, which gives the same boolean. Every float in
   `_relax_corners` is computed as before.
2. **Edge snap, incremental** (`stage2_photo_segment.snap_region_edges`).
   The region means are fixed, and each pass decides from a snapshot. So a
   pixel whose own label and 8 neighbours did not change decides what it
   decided last pass, which is to stay. After the first full-frame pass only
   the moved pixels and their neighbours are read, in the same raster order.
3. **One Lab conversion per frame per job** (`threads.rgb_to_lab`,
   `lab_memo_scope`, round `pipeline.build_generation`). An input of 100,000
   values or more is keyed by its shape, dtype and a blake2b of its bytes.
   Each caller gets its own copy, and the memo holds one frame. Nothing is
   kept past the `build_generation` call. The cost is memory: the frame's Lab
   (about 115 MB on Golden Tee) stays alive for the rest of generation.
4. **Fine-bar ink on the band's box** (`fine_bar._seeded_ink`). Every ink
   pixel lies inside the band. The colour test, the components and the seed
   therefore read the band's bounding box, and the coordinates are offset
   back. That gives the same pixels in the same order.

## Not taken, and why

- **Thread revalidation's CIEDE2000** (`revalidate_threads`, 2-4 CPU s per
  job), for the same reason as on 11-16. Scoring each distinct colour once
  rests on numpy's vector maths giving the same answer for a value wherever
  it sits in an array. That holds in practice, but not by construction.
- **Stage 0's k-means assignment** (`stage0_classify._assign`, 4.8 Mpx x 16
  centres on Golden Tee). A per-centre loop gives the same distances, which
  was measured equal, but it was no faster (3.4 s against 3.5).
  Smaller chunks were 10-15% faster, which is within noise.
- **Stage 2's majority filter in uint8** (the same counts), measured at
  0.53 s against 0.61, which is noise.
- **Memoising `round_inward` across finish and plan.** Only 2 of 79 calls
  repeat on Fremont, and 12 of 59 on MFab.

## What is left

The rest is spread thin across GEOS calls (`buffer`, `intersection`,
`union_all`) in the plan, revalidation's CIEDE2000, and MFab's lettering
lane. These are the same two levers the 11-16 note named, and neither is
exact by default:
fewer passes (the fold judge, `_edge_walk`, the size ring's 240-iteration
relaxation) or more cores (measured at a 7% ceiling for the letter cuts).

## Method

`python -m tools.flip_timing run SLUG main` (the Studio's request at the
pro's size, one warm-up digitize, then `build_generation`,
`finish_generation` and `plan_stitches`). Base is `origin/main` at
`ab5a144c`, exported to its own folder. Each job ran base and then lane, back
to back in fresh processes, and identity was checked by the plan's md5
(`tools.flip_timing.plan_md5`).
