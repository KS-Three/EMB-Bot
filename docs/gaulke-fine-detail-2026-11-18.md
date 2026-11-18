# Gaulke hat: closed gaps, choked counters, fat letters, blunt wing tip (2026-11-18)

Prime grader faults for `L_gaulke_roofing_hat` (scorecard 2026-11-18, 114.2 x 47.6 mm on hat_front). Main at `ea4257d0`,
Studio request. Every figure is an instrument reading (ROADMAP gate 4), not a quality claim.

## How it was measured
Art (white strip of the screenshot, ink = dark, ink box 114.2 mm wide) against our sewn coverage (every needle-down
segment drawn as a 0.40 mm ribbon, `counter_slots.thread_rasters`), registered by a shift search (IoU 0.70). The
width of a white gap is the local width: the largest disc that fits (opening at 0.1 mm steps). Scripts:
`docs/renders/gaulke-gap-taper-2026-11-18/tools/`. **Caveat that governs every number:** the 0.40 mm ribbon
adds about 0.2 mm to each edge of anything drawn, in ours and in a professional's file alike, so a gap reads about
0.4 mm narrower than the needle points leave it. Compare variants with each other, not with the art alone.

## What closes each gap (white width in a 10 x 10 mm window at the art's gap, mm; % = share of the art's gap pixels still white)

| feature (mm) | art | OFF (main) | `growth_keeps_gaps_between` | pull 0 (`fabric_profile` delta -0.4) |
|---|---|---|---|---|
| sun / roof gap (45, 14) | 1.30 | 0.30 (23%) | 0.60 (53%) | 0.70 (51%) |
| peak (62, 14.5) | 1.30 | 0.40 (34%) | 0.80 (59%) | 0.80 (57%) |
| roof band gaps (60, 20) | 0.50 | 0.40 (49%) | 0.40 (49%) | 0.40 (56%) |
| window mullions (57, 24.5) | 0.60 | 0.40 (59%) | 0.40 (59%) | 0.50 (61%) |
| G counter (19.5, 35.5) | 1.00 | 0.40 (43%) | 0.40 | 0.70 (49%) |
| S (6, 44) | 1.40 | 0.50 (34%) | 0.50 | 0.90 (58%) |
| R / E (98, 35.5) | 1.40 | 0.40 (33%) | 0.40 | 0.80 (51%) |
| PP (104, 44) | 1.10 | 0.30 (21%) | 0.30 | 0.50 (38%) |

Total sewn ink 1882 mm2 against the art's 1330 (+41%); pull 0 gives 1670 (+26%); the professional's file under the
same reader reads 1709 (+28%, registered by the same shift search, IoU 0.60, so indicative only).

**Verdict by fault**
- **Letter strokes fattened, counters and the G/R/E/& openings choked, mullions thin:** the hat's 0.40 mm pull
  (`Fabric.pull_comp_mm`, structured cap) plus the ribbon. Pull 0 restores counters to 0.7-0.9 mm; it is the cause.
  `pull_comp_by_stroke` ON (existing, OFF) moves nothing here (strokes are thin, so it keeps the 0.4). That is a
  physical constant (ROADMAP gate 1): sew-out settles it. **No flag built** (the brief says to build one only if the
  cause is not a gate-1 constant).
- **Sun/roof gap and peak:** stage-5 growth (`resolve_overlaps`) grows both shapes into the 1.3 mm gap; this is
  placement, not a constant, and `growth_keeps_gaps_between` (#1630) does fix it (0.3 -> 0.6, 0.4 -> 0.8).
- **Roof band gaps 0.5 mm and the window's 0.6 mm mullions:** within a thread width (0.4) of closing in any file; no
  digitizing flag changes them (rows above: unchanged by the flag, +0.1 at most with pull 0).
- **Upper roof wing tip about 1 mm blunt:** measured. Art tip at x 27.95 mm (left) / 86.1 (right); ours reaches
  28.5 / 85.4 as drawn (ribbon included), the professional's reaches 27.7 / 86.5. Our needle points start at x 28.7,
  so the last 0.65-0.75 mm, where the art is under 0.4 mm wide (0.25 mm at x 28.2, 0.35 at 28.6), is not sewn. Pull 0
  and the gap flag leave it the same; the lower wing tips are within 0.15 mm. It is the satin column's end rule at a
  taper (the wing is satin, measured stroke 2.5 mm), not scalloping and not pull. Not fixed here: a taper-to-point end
  is a satin-end change (stage 6) and I did not build it.

## `growth_keeps_gaps_between` against today's main: is it a flip candidate?
Swept all 18 tripwire placements and the 26 `corpus_scorecard.FIXTURES` (44 designs; tripwire jobs at the pro's size,
fixtures at 80 mm hat_front), OFF vs ON by md5 of `design["stitches"]`. Table: `docs/renders/gaulke-gap-taper-2026-11-18/sweep.json`.

**As built (#1630): no. 30 of 44 move.** Worst: `photo/summit_badge` 28526 -> 32682 (+14.6%, trims 39 -> 50, jumps 69 -> 88,
needle-up 1008 -> 1368 mm, +196 travel runs, +668 fill runs), `photo_scene_stub` +8.9%, MFab lc +7.4%, Drone +7.0%,
MFab hat +6.1%, Golden Tee +3.7%. What stops it: the rule also holds the 0.5 mm seams between big art shapes (summit_badge:
a 47 mm long 0.5 mm seam against the 2776 mm2 base) and the lens round thin neighbours of a big fill (MFab, Drone), and
every held gap splits fill rows into runs.

**With two gates and a taper (new keys under the same flag; absent = as #1630, OFF byte-identical):**
`growth_keeps_gaps_between_min_mm2` (both shapes at least this big) = 100, `growth_keeps_gaps_between_min_gap_mm` (art gap at
least this wide) = 1.0, `growth_keeps_gaps_between_taper_mm` (growth ramps back to the full pull over this length from a held
gap, in 4 steps, instead of a 0.4 mm step) = 1.5. **13 of 44 move** (`sweep.json`, key `gtaper`; the gates alone, key
`gate100g1`, moved 10):

| design | stitches | trims | jumps | needle-up mm | plan change (runs) |
|---|---|---|---|---|---|
| becker_marine_logo.png | 10953 -> 10926 | 12 -> 12 | 14 -> 14 | 370.7 -> 298.2 | {'travel': -3, 'satin': -1, 'underlay': -1} |
| logo_alpha.png | 6259 -> 6253 | 7 -> 8 | 9 -> 10 | 164.1 -> 171.4 | {'travel': -1} |
| logo_script_tires.png | 2652 -> 2654 | 4 -> 4 | 5 -> 5 | 67.9 -> 68.0 | {} |
| logo_whitebg.png | 6781 -> 6660 | 8 -> 8 | 10 -> 10 | 203.2 -> 209.3 | {'travel': 6, 'fill': 3, 'underlay': 3} |
| photo/logo_bridge_bar.jpg | 10437 -> 10436 | 18 -> 18 | 26 -> 26 | 214.1 -> 214.1 | {} |
| photo/photo_scene_stub.png | 21505 -> 21805 | 83 -> 87 | 97 -> 100 | 1499.4 -> 1480.6 | {'travel': 3, 'fill': 12, 'satin': 1, 'underlay': 8} |
| photo/region_blobs.png | 18802 -> 18786 | 26 -> 25 | 32 -> 31 | 449.9 -> 439.0 | {'travel': -1, 'underlay': 2} |
| photo/summit_badge.png | 28526 -> 28507 | 39 -> 38 | 69 -> 69 | 1008.3 -> 971.6 | {} |
| becker_beanie | 13653 -> 13675 | 13 -> 13 | 15 -> 15 | 385.0 -> 310.5 | {'travel': -1, 'satin': -1, 'underlay': -1} |
| gaulke_roofing_hat | 6618 -> 6576 | 30 -> 29 | 47 -> 50 | 341.0 -> 293.9 | {'travel': -3, 'fill': 2, 'underlay': 2} |
| toat_beanie | 17193 -> 17126 | 27 -> 24 | 35 -> 35 | 233.6 -> 241.8 | {'travel': -3, 'satin': -1, 'underlay': -1} |
| toat_machine_beanie | 16862 -> 16860 | 18 -> 18 | 31 -> 31 | 323.6 -> 323.6 | {} |
| toat_machine_hat | 17100 -> 17100 | 19 -> 19 | 32 -> 32 | 267.9 -> 267.9 | {} |

The other 31 are byte-identical. No shape is dropped or added in any mover. ORIGINAL | BEFORE | AFTER, whole design and
close-up, for all 13: `docs/renders/gaulke-gap-taper-2026-11-18/`. By eye: Gaulke's sun/roof and peak gap is open and wider
(the main gain, visible in the whole design too; the letters are as fat as before); Toat beanie's gap between two script
strokes is wider; the other eleven show no visible change at print size.

**The border wobble, traced.** `edge_wobble` reads each border rail's deviation from the art polygon, high-passed over 3 mm,
so a standoff that steps from 0.4 mm (pull) to 0 where growth stops at a held gap reads as wobble. Gaulke's flagged points
(0.3-0.9 mm) all sit at the sun's flanks where its growth is cut by the lens at the gap's mouth: the step, not a
pixel-by-pixel staircase. Taper length against Gaulke's border p95 / max (OFF 0.037 / 0.14): none 0.244 / 0.87, 0.6 mm
0.186 / 0.86, 1.0 mm 0.170 / 0.87, **1.5 mm 0.110 / 0.40**, 2.0 mm 0.303 / 0.97, 3.0 mm 0.108 / 0.42. The border sample is
240 points of two or three shapes and not monotonic in the taper, so this is a noisy instrument; 1.5 is a point that reads
low, not an optimum. The gap gain is the same at every taper (sun/roof 0.7 mm, peak 0.8-1.0 mm). **The wobble is not back to
OFF's:** 0.11 p95 against 0.037, still above the 0.15 mm visibility line only at the max (0.40). The border wobble of the other
movers is the same or lower (logo_whitebg p95 0.097 -> 0.076, region_blobs 0.176 -> 0.162).

Preflight on the 13: grade, score and findings identical on every one. Gaulke: `coverage_area_mm2` 2060 -> 2044,
`coverage_max` 5.87 -> 5.72, `satin_short_fraction` 0.075 -> 0.072; Toat beanie `coverage_max` 9.23 -> 8.71.

**Why it is still not a recommendation to flip**
1. The three thresholds were chosen on this same 44-design set, so the clean result is fitted to it. 1.0 mm is derived from
   2 x 0.4 pull + one thread; if the pull ever changes (gate 1) it moves with it.
2. Border wobble on Gaulke is 0.11 p95 / 0.40 max against 0.037 / 0.14 OFF (instrument is noisy, see above).
3. Gaulke's gain shows only on the hat; at left chest and beanie the gap is under 1.0 mm and the flag no longer moves them.
4. `becker_marine_logo` (-27 stitches, a satin run fewer) and `becker_beanie`, `toat_beanie` lose a satin run with the gates
   where the ungated flag left Becker byte-identical. Not traced; pictures show no visible change.
5. Whether a held 0.6-1.0 mm gap stays open on cloth is a sew-out matter (gate 1).

Built behind keys `extra.growth_keeps_gaps_between_min_mm2`, `..._min_gap_mm`, `..._taper_mm`, read only with
`extra.growth_keeps_gaps_between`; absent or 0 is #1630 exactly. Tests in `tests/test_growth_geometry.py`. Nothing is flipped.

## The wing tip in the professional's file (numbers only)
Upper wing, left tip. Art tip at x 27.95 mm. The professional's satin runs to the tip: its last cross stitch is at x 27.9
(design mm), **0.9 mm long**, and the crosses then lengthen 0.9, 1.0, 1.1, 1.2, 1.3 mm over the next 1.0 mm (one cross about
every 0.2 mm). The cross never drops under 0.9 mm, the art there is 0.25-0.35 mm wide, and no run stitch carries the tip:
a longer single stitch at 1.5-2.8 mm is the underlay running out to x 27.4 / 26.1. So the construction is a satin column
that starts at the art's very tip at full cross width (about 0.6 mm beyond the art's width), not a taper below 0.4 mm. Ours
starts its first cross (0.9 mm) at x 28.7, 0.75 mm in. A taper flag in this construction would mean the column's first
station begins at the art's tip with the 0.9 mm cross; not built (stage 6 satin-end work; time).
