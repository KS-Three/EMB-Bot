# Gaulke hat: closed gaps, choked counters, fat letters, blunt wing tip (2026-11-18)

Prime grader faults for `L_gaulke_roofing_hat` (scorecard 2026-11-18, 114.2 x 47.6 mm on hat_front). Main at `ea4257d0`,
Studio request. Every figure is an instrument reading (ROADMAP gate 4), not a quality claim.

## How it was measured
Art (white strip of the screenshot, ink = dark, ink box 114.2 mm wide) against our sewn coverage (every needle-down
segment drawn as a 0.40 mm ribbon, `counter_slots.thread_rasters`), registered by a shift search (IoU 0.70). The
width of a white gap is the local width: the largest disc that fits (opening at 0.1 mm steps). Scripts:
`docs/renders/gaulke-gap-size-gate-2026-11-18/tools/`. **Caveat that governs every number:** the 0.40 mm ribbon
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
fixtures at 80 mm hat_front), OFF vs ON by md5 of `design["stitches"]`. Table: `docs/renders/gaulke-gap-size-gate-2026-11-18/sweep.json`.

**As built (#1630): no. 30 of 44 move.** Worst: `photo/summit_badge` 28526 -> 32682 (+14.6%, trims 39 -> 50, jumps 69 -> 88,
needle-up 1008 -> 1368 mm, +196 travel runs, +668 fill runs), `photo_scene_stub` +8.9%, MFab lc +7.4%, Drone +7.0%,
MFab hat +6.1%, Golden Tee +3.7%. What stops it: the rule also holds the 0.5 mm seams between big art shapes (summit_badge:
a 47 mm long 0.5 mm seam against the 2776 mm2 base) and the lens round thin neighbours of a big fill (MFab, Drone), and
every held gap splits fill rows into runs.

**With two gates (new keys under the same flag; absent = as #1630, OFF byte-identical):**
`growth_keeps_gaps_between_min_mm2` (both shapes at least this big) = 100 and `growth_keeps_gaps_between_min_gap_mm`
(the art gap at least this wide) = 1.0. **10 of 44 move**, `sweep.json` key `gate100g1`:

| design | stitches | trims | jumps | needle-up mm | plan change |
|---|---|---|---|---|---|
| gaulke_roofing_hat | 6618 -> 6574 | 30 -> 30 | 47 -> 47 | 341.0 -> 339.5 | travel -1, underlay +1 |
| becker_marine_logo (fixture) | 10953 -> 10926 | 12 -> 12 | 14 -> 14 | 370.7 -> 298.2 | satin -1, underlay -1, travel -3 |
| becker_beanie | 13653 -> 13673 | 13 -> 13 | 15 -> 15 | 385.0 -> 310.5 | satin -1, underlay -1, travel -1 |
| photo_scene_stub | 21505 -> 22047 (+2.5%) | 83 -> 85 | 97 -> 100 | 1499 -> 1514 | fill +14, travel +11, underlay +4, satin -2 |
| photo/region_blobs | 18802 -> 18905 | 26 -> 26 | 32 -> 34 | 449.9 -> 452.7 | fill +11, travel +3 |
| summit_badge | 28526 -> 28601 (+0.3%) | 39 -> 38 | 69 -> 68 | 1008 -> 975 | travel +2 |
| logo_alpha, logo_whitebg | -6 / 0 | same | same | same | none |
| toat_machine_hat / beanie | -1 / -4 | same | same | same | none |

The other 34 designs are byte-identical. No shape is dropped or added in any mover. ORIGINAL | BEFORE | AFTER, whole design
and close-up, for all ten: `docs/renders/gaulke-gap-size-gate-2026-11-18/`. By eye: Gaulke's sun/roof and peak gap is open
and wider (the one gain); the other nine show no visible change at print size (fill angle re-picks in summit_badge,
scene_stub; Becker's E and Toat's letters identical).

Preflight (`run_preflight`) on the ten: grade, score and findings identical on every one. Coverage and cover on Gaulke
moved the right way (`coverage_area_mm2` 2060 -> 2042, `coverage_max` 5.87 -> 5.60). **One figure moved the wrong way:
Gaulke's `edge_wobble_border_p95_mm` 0.037 -> 0.244 and `..._max_mm` 0.14 -> 0.87**; the close-up shows the held gap's edge
a little ragged. Not traced.

**Why it is still not a recommendation to flip**
1. The gates were chosen on this same 44-design set, so the clean result is fitted to it. They are two new thresholds, not
   measured constants. 1.0 mm is derived from 2 x 0.4 pull + one thread; if the pull ever changes (gate 1) it moves with it.
2. The wrong-way border wobble above.
3. Gaulke's gain shows only on the hat; at left chest (`gaulke_roofing_lc`, 95 mm) and beanie the gap is under 1.0 mm
   and the flag no longer moves them (ungated it moved both).
4. One mover, `becker_marine_logo` (-27 stitches, a satin run fewer), moves with the gates where the ungated flag left it
   byte-identical. I did not trace why (skipping a held pair should only remove growth restrictions); the pictures show
   no visible change.
5. Whether a held 0.6-0.8 mm gap stays open on cloth is a sew-out matter (gate 1).

Built behind keys `extra.growth_keeps_gaps_between_min_mm2` and `extra.growth_keeps_gaps_between_min_gap_mm`, read only
with `extra.growth_keeps_gaps_between`; absent or 0 is #1630 exactly. Test:
`tests/test_growth_geometry.py::test_between_gates_hold_only_big_shapes_with_a_wide_gap`. Nothing is flipped.
