# Lettering below 4 mm: the pro's floor (2026-10-24, L8)

Measured with `digitizer/tools/small_text_floor_census.py`: one reader on both
machine files, each in its own frame, ours digitized at the pro's width through
the Studio request. Heights are needle points plus 0.3 mm of painted thread
(about 0.3 mm over a stage-5 letter polygon); `stroke` is the median satin cross.

## His rule, one sentence

**Every line of lettering drawn under ~3.2 mm he re-sets to ~4.0–4.6 mm (read
this way) bold satin with 0.9–1.26 mm columns and the gaps closed to
0.05–0.2 mm. Every line drawn at 5 mm or more he sews as drawn (×1.02–1.11).
He never sews a small line as a run or a bean, and never drops one.**

No paired job has a line drawn between 3.2 and 5.0 mm, so where in that band
the rule switches is not measured; ~4 mm is his own re-set target.

**Contradicting row:** Golden Tee's ™ (0.86 mm in the art) he sews 2.35 mm tall
as a run — enlarged ×2.7, but a mark, not a 4 mm satin word. We drop it: no
region of ours holds it (the tracer never sees a 0.1 mm stroke).

## The census (today's main, `small_text_true_size` ON, re-set OFF)

| job | line | art h mm | ours (main) | pro | pro stroke | pro gap |
|---|---|---|---|---|---|---|
| ProSeal hat 85.9 | SPRAY FOAM | 3.04 | bean 3.15 | satin 4.55 | 1.20 | 0.20 |
| ProSeal hat | + COATINGS | 3.15 | run 3.15 | satin 4.55 | 1.26 | 0.15 |
| ProSeal beanie 75.0 | SPRAY FOAM | 2.56 | bean 2.80 | satin 4.00 | 1.10 | 0.05 |
| ProSeal beanie | + COATINGS | 2.66 | run 2.80 | satin 4.00 | 1.17 | 0.05 |
| Drone 62.6 | AND DRONE | 2.20 | satin 3.15 | satin 4.25 | 1.20 | (one blob: travel) |
| Fremont hat 92.6 | THE | 3.04 | bean 2.95 | satin 4.15 | 0.89 | — |
| Fremont hat | EAT\|STAY | 2.44 | bean 2.65 | satin 4.95 | 0.90 | — |
| Fremont patch 92.5 | EST | 1.85 | run 2.15 | satin 4.45 | 0.86 | — |
| Fremont patch | THE | 3.03 | bean 2.95 | satin 4.25 | 0.90 | — |
| Fremont patch | EAT\|STAY | 2.44 | bean 2.65 | satin 4.25 | 0.89 | — |
| Golden Tee 74.9 | ™ | 0.86 | dropped | run 2.35 | — | — |
| Gaulke beanie 93.8 | STEEL ROOFING | 5.02 | satin 5.65 | satin 5.35 | 1.40 | 0.25 |
| Gaulke LC 95.2 | STEEL ROOFING | 5.10 | satin 5.65 | satin 5.65 | 1.33 | 0.35 |
| Drone | THERMAL | 5.99 | satin 6.95 | satin 6.65 | 2.06 | 0.25 |
| Gaulke hat 114.2 | STEEL ROOFING | 6.11 | satin 6.75 | satin 6.55 | 1.51 | 0.40 |
| To a T hat 89.5 | LLC | 6.66 | satin 7.25 | satin 6.85 | 1.61 | 0.40 |
| ProSeal beanie | PROSEAL | 8.05 | satin 8.65 | satin 8.25 | 2.57 | 0.55 |
| ProSeal hat | PROSEAL | 9.22 | satin 9.85 | satin 9.75 | 2.98 | 0.90 |

Not read (the reader's known misreads, see the tool's docstring): Fremont
EST/1895/PLAY on the hat and 1895 on the patch, whose pro letters join through
in-block travel and the patch field — `small-text-reset-2026-10-21` reads them by
colour block at 2.1× (date), 1.55× (tagline), 1.25× (THE); MFab's outline letters;
Bridge and To a T beanie (pro files not on this machine).

## The gap, and what is built

The layout rule is already built: #1029's re-set (`small_text_cap_mm` 4.0 with
`small_text_cap_letter_gap_mm`, `small_text_cap_bold_scale`, OFF, on the flip
sheet). It reaches Fremont and Drone. **It did not reach ProSeal at all** —
both tagline clusters `no_room`, blocked by `design_edge`, and SPRAY also by its
own A:

1. the line sits on the design's bottom edge, and the placement asked the
   letters' 0.8 mm clearance halo to fit inside the design box — impossible at
   any growth. The pro sews the tagline 0.6 mm past our design's bottom
   (needles 27.2–32.0 mm against the art's 28.3–31.5) inside the same design
   height (63.3 against our 63.1 mm);
2. the A of SPRAY traces in a thread of its own, so it is in no cluster and
   stood in its own line's way (`_join_line_ends` joins only past the ends);
3. on the beanie, COATINGS is split into two interleaved clusters (C O A N /
   T I G S) whose hulls overlap, and word clusters 1.3 mm apart collided
   through each other's ~1 mm halos.

`small_text_cap_reach_edges` (OFF) fixes all three, only under the re-set:
the design edge holds the letters (not their halo) and gives way by half the
line's growth; a letter-sized shape inside the line's span joins it; clusters
of one line whose hulls overlap are placed as one; clusters of one line keep a
sewn letter gap from each other instead of two halos.

| line | main | re-set, flag OFF | **re-set, flag ON** | pro |
|---|---|---|---|---|
| ProSeal hat SPRAY FOAM | bean 3.15, gap 1.55 | bean 3.15, gap 1.55 | **satin 4.35, gap 0.25** | satin 4.55, gap 0.20 |
| ProSeal hat + COATINGS | run 3.15, gap 1.25 | run 3.15, gap 1.25 | **satin 4.45, gap 0.25** | satin 4.55, gap 0.15 |
| ProSeal beanie SPRAY FOAM | bean 2.80, gap 1.35 | bean 2.80 | **satin 3.65, gap 0.25** | satin 4.00, gap 0.05 |
| ProSeal beanie + COATINGS | run 2.80, gap 1.15 | run 2.80 | **satin 3.70, gap 0.25** | satin 4.00, gap 0.05 |
| PROSEAL (both) | — | unchanged | unchanged | — |

Fremont hat and Drone: the flag-ON DST is byte-identical to flag OFF (md5
`4d0b1dadd126…`, `1328be806ec3…`). Renders, art | main | OFF | ON | pro:
`docs/renders/small-text-floor-2026-10-24/`.

## Not layout — gate 1, not built

Our re-set satin columns read 0.70–0.73 mm against his 1.10–1.26 on the same
ProSeal lines. That is stroke weight (`small_text_cap_min_stroke_mm` 0.85 and
`small_text_cap_bold_scale` 1.45, both candidates): fabric settles it.

## Still open

- Beanie stops at ×1.15 (3.65 against his 4.0): the bar above leaves no more
  room at the 0.8 mm clearance, and the pro also re-lays the bar. Measure his
  bar move before building one.
- A joined letter (ProSeal's A, Drone's A from #1029) sews as a plain shape in
  its own thread, not as a letter of the line; tagging it with the cluster's
  tags did not route it into the Column lane (ProSeal hat byte-identical), so
  the cause is downstream in stage 7.
- The ™: the pro keeps it as a 2.35 mm run; we never trace it.
