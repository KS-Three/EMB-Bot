# Free auto-digitizers against ours and the pro's (2026-11-04)

Numbers only, by rule: every competitor file and every render drawn from one is a
third-party file and lives in the gitignored `scratch_bench/` (Kent's disk:
`C:\Users\EE-LT-11030\Claude Personal\EMB-Bot\scratch_bench\`), never in this repo.
Survey and picks: [`docs/free-digitizer-survey-2026-11-04.md`](../free-digitizer-survey-2026-11-04.md).
Tool: `digitizer/tools/bench_free_digitizers.py` (the engine runners are
`bench_run_nuizu.py` and `bench_run_heatstitch.mjs`).

## What ran

The 18 committed pro pairs (`python -m tools.tripwire jobs`), each digitized by the
engine at the **pro's width** (`pro_baseline.JOBS`; the art cut to its ink box first,
Gaulke's phone screenshot to its white panel) with the engine's **defaults**, one run per job:

| engine | how | settings | result |
|---|---|---|---|
| Nuizu 0.3.1 (Apache-2.0/MIT) | own venv, `nuizu dst <art> -s <longest side mm>`; arm 2 (`nuizu-satin-auto`) adds `--satin-outline --auto-angle` | defaults: 8 colours max, fill 45 deg, 3 mm max stitch, no background | 18 / 18, both arms |
| heatstitch (MIT; the public build of heatstitch.app) | a static copy served from `127.0.0.1`, driven by Playwright with every non-localhost request aborted (no Rust toolchain here to build from source) | "Convert a picture", Width (mm) set per job, Flat style, 6 colours, smooth 3, smallest area 3 mm2, background left out, Stable woven, 40 wt; DST export | 18 / 18 |
| openstitch v0.4.0 (AGPL-3.0+) | Windows release exe (146,368,665 bytes) launched by Kent by hand, then driven through its GUI (computer-use) | Auto-Digitizer dialog: Target design width set per job, everything else default; Tajima DST export | 8 / 18 (Becker x5 + Hotel Fremont hat, Precision Drone, Golden Tee hat) |
| Stitch AI (Dynamic Mockups) | dropped (Tier 3) | n/a | **not run**: its DST download is gated behind a sales call; Kent ruled "Drop Tier 3" |

Figures are the nightly tripwire's seven, read from the written DST by one reader
(pystitch) for ours, the competitor and the pro: stitches, trims, hops, needle-up mm,
stitch-type kappa and direction kappa over the shared solid area (chance-corrected only,
ROADMAP gate 4; the stitch-type kappa carries its chance floor in brackets), and word cc at
native size (the three jobs whose words are pinned). In the per-job tables a count cell reads
**ours / engine / pro**; a kappa or cc cell reads **ours-vs-pro / engine-vs-pro**. The size the
engines actually produced was 0.96x-1.02x the pro's width on every job (the size column).

## Headline

Medians over the 18 jobs, every engine read against the pro's file. The "ours" row is today's
main, the same run the nightly tripwire digitizes.

| engine | jobs | stitches vs pro (median x) | trims vs pro (median delta) | hops vs pro (median delta) | needle-up vs pro (median x) | sttype kappa ours / engine (median) | direction kappa ours / engine (median) | jobs engine sttype kappa >= ours |
|---|---|---|---|---|---|---|---|---|
| nuizu | 18 | 4.69 | 12.5 | 16912.5 | 54.57 | 0.38 / 0.02 | 0.37 / 0.0 | 1 of 18 |
| nuizu-satin-auto | 18 | 4.0 | 29.0 | 17895.0 | 55.22 | 0.38 / 0.01 | 0.37 / 0.0 | 1 of 18 |
| heatstitch | 18 | 0.67 | 8.0 | 8.5 | 1.02 | 0.38 / 0.13 | 0.37 / 0.11 | 2 of 18 |
| openstitch | 8 | 0.69 | 81.5 | 78.0 | 5.11 | 0.45 / 0.04 | 0.35 / 0.01 | 0 of 8 |
| ours (today's main) | 18 | 1.2 | -1.0 | 5.0 | 0.86 | 0.38 | 0.37 | - |

openstitch ran 8 of the 18 jobs (see its section), so its row above is a median over those 8. Every
engine over the **same 8 jobs** (Becker x5, Hotel Fremont hat, Precision Drone, Golden Tee hat):

| engine | stitches vs pro (median x) | needle-up vs pro (median x) | trims vs pro (median delta) | sttype kappa ours / engine (median) | direction kappa ours / engine (median) | jobs engine sttype kappa >= ours |
|---|---|---|---|---|---|---|
| Nuizu | 4.8 | 67.3 | 13.0 | 0.45 / 0.03 | 0.35 / 0.09 | 0 of 8 |
| heatstitch | 0.83 | 2.75 | 54.5 | 0.45 / 0.21 | 0.35 / 0.07 | 0 of 8 |
| openstitch | 0.69 | 5.11 | 81.5 | 0.45 / 0.04 | 0.35 / 0.01 | 0 of 8 |
| ours | 1.21 | 0.93 | 2.0 | 0.45 | 0.35 | - |


## What each engine did (read from the render sheets: art | ours | engine | pro)

**Nuizu.** A fill-everything floor, and it behaves as one. It sews 4-5x the pro's stitches
(median) and flies the needle 55x the pro's distance: it writes a JUMP at the end of every
fill row (4,556-24,669 needle-up hops per file against the pro's 10-80) and mostly no trim,
so as written the machine would carry the thread across the whole design (its 11-431 trims
per file are not what to read here; the hop count is). Stitch-type kappa against the pro is
at chance (median 0.01-0.02); only Tires, a one-colour script a fill covers fine, ties ours.
Its colour quantiser is the visible failure: the grey anti-aliasing of the art is cut into
six colour blocks, so Becker's face and lettering come out as confetti of small coloured
regions (BECKER and MARINE take effort to read) and Tires gets a ring of speckled blocks round
a clean black body. Becker's word cc against the pro is -0.23 on the default arm (ours 0.84).
What it got right: it hit the requested size (0.99-1.00x) every time, its outlines follow the
art, and the one-colour jobs (Tires, Gaulke) read. The satin-outline + auto-angle arm changes
the structure little: kappa median 0.01, 4.0x the pro's stitches against 4.7x. It does help
reading: Becker's word cc moves from -0.23 to +0.05 and Fremont's from 0.52 to 1.00.

**heatstitch.** The closest peer. It sews 0.67x the pro's stitches (median) with needle travel
within 2% of the pro's (1.02x median); at MFab hat it cuts 13 times against the pro's 19, at
Tires 6 against 10: cuts and travel of a hand digitizer's order. Stitch-type kappa against the
pro is 0.13 (median) against ours 0.38; it passes ours on Gaulke hat (0.22 against 0.14) and
ties it on Tires (0.00, both at the floor), and in the renders it separates satin outlines
from fills much as the pro does on Becker and MFab, with MFab's lettering outlined and
readable. Where it loses: it spends its colour changes on greys (1-5 changes on near
black-and-white art), leaves a stray hatched patch in the counter of Tires' "r", and is thin
where the pro is dense: Hotel Fremont 3,265 stitches against the pro's 17,067 (word cc 0.79
against ours 1.00) and Golden Tee 3,900 against 5,973 with 49 cuts against the pro's 10. Its
Width control sizes the design to within 4% of the request (0.96-1.00x; the reported box is
the sewn extent, not the art's). Tonal polarity cannot be judged from these renders: a DST
holds no thread colours, so every file here is drawn in the palette the pairframe reader
assigns, and heatstitch's own colour choices are not visible.

**openstitch.** See its section below: at the 8 jobs it ran, stitch-type kappa 0.04, a decent structure on Becker, lost fills on Golden Tee and Fremont, many more trims than the pro.

**Nuizu against heatstitch.** On these 18 the free engine that makes a satin or fill decision
sits at stitch-type kappa 0.13 (median) against 0.02 for the one that does not, with needle
travel of the pro's order against 55x. Neither reaches ours (0.38): heatstitch matches or
passes it on 2 of 18 jobs, Nuizu on 1 (a tie at the floor).

## openstitch

OpenStitch Studio 0.4.0 (AGPL-3.0+; Windows release exe, sha256
`8dab516c660aa38bdf1866b7a49ab5d253846d7924d44ab1894005f81559bcd5`, in
`scratch_bench/_tools/openstitch/`). The session's permission policy refused launching the downloaded
exe, so **Kent launched it by hand**; a first request for computer-use access to its window was denied,
a second one was granted, and the window was then driven for **8 of the 18 jobs**: Becker x5 (hat large,
left chest large, hat small, chest small, beanie) plus Hotel Fremont hat, Precision Drone and Golden Tee
hat, picked as the jobs where ours and the pro differ most. Per job: "Turn an image into embroidery",
the ink-cropped art, **Target design width set to the pro's width and nothing else changed** (defaults:
6 colours, 0.40 mm density, 6.50 mm satin limit, 1.5 mm2 tiny-area filter, background removed, colours
matched to the thread palette, no satin outline), "Digitize & apply", Export as Tajima DST. The 10 jobs not
run are Gaulke x3, Hotel Fremont patch, MFab x2, Tires and Toat x3; the
engine has no batch mode, so it is a GUI hand-drive per job. `openstitch.analysis` (the /100 stitch-out
score) was not run on ours.

Results, 8 jobs against the pro: 0.69x the pro's stitches (median), a stitch-type kappa of 0.04
(ours 0.45 over the same jobs; the engine never reaches ours on any of the 8), direction kappa 0.01, 81.5
more trims than the pro (median; Becker hat large 141 against 10) and 5.1x the pro's needle-up distance.
Its own production numbers are honest: the stitch count it states (status bar, and "saved and verified ...
stitches read back" on export) equals what our reader counts in the DST on all 8, and the three trim counts
recorded matched too. The renders: on Becker it draws satin-style outlines round the lettering, grey tatami
with directional rows inside BECKER and black fill in MARINE with small counters kept open, and both words
read; on Golden Tee it keeps the outlines and thin shapes but leaves the body of the G and part of the T as
bare outline (3,878 stitches against the pro's 5,973, 82 trims against 10, word cc not scored on this
job), and on Hotel Fremont it sews 1,702 stitches against the pro's 17,067 (word cc 0.76 against ours
1.00). It hit the requested width on every job (0.96x-1.00x). What it got right: a structure that looks
like a digitizer's on Becker (outlined satin plus directional fill, open counters) and an export that
reads back exactly. What it got wrong at a glance: cuts and travel (many more trims and 5x the needle-up distance) and lost fills on the mixed-colour jobs. Tonal polarity is not judged from these renders
(a DST holds no thread colours). The survey's ruling stands: its output was benchmarked, its code was not
read.

## Stitch AI (Dynamic Mockups)

Not run. Its DST turned out to be gated behind a sales call (recorded in the survey), and Kent ruled
"Drop Tier 3". The harness keeps `--bench-dir` / `--out-dir` and the manifest check for the Hatch and
Wilcom files to come.

## What to borrow, what not to

Borrow (as measurements, never code):
- **heatstitch's stated width rule beside our classifier**: run < 1 mm, satin <= 7 mm and
  even, else fill, narrow regions sewn last. On these 18 it earns a stitch-type kappa of 0.13
  with no tuning, ours is 0.38; a cheap tripwire row: a classifier change that drops our kappa
  on a job toward 0.13 means a rule of thumb is catching up.
- **A "needle-up mm against the pro" check per engine.** Nuizu's 55x is what a missing trim
  step costs; ours is 0.86x median and the number to keep near 1.
- **Reading a tool's stated stitch and trim counts back from its file.** openstitch re-reads every export ("saved and verified: N stitches read back") and heatstitch prints a production sheet; both matched our reader. The manifest comparison in this tool does it for any engine that leaves a `manifest.json` (the survey's idea 3).

Do not take:
- **Nuizu's colour quantiser** (k-means over the greys of anti-aliased edges): the confetti on
  Becker is what that looks like. Our stage 0 and colour cap avoid it; keep it that way.
- **Fill-everything as a baseline to beat.** It reads on one-colour script (Tires) and Gaulke;
  it is not a floor on mixed art.
- **A low stitch count as a goal.** heatstitch sews fewer stitches than the pro and still loses
  on kappa (Hotel Fremont); fewer is not closer.

## Limits

One default run per job and engine; no sew-out (ROADMAP gate 1), so nothing here says how
any file sews. Kappa and direction kappa are measured on the solid area the two files share
after registration; a 0.00 direction figure on both sides is a tie, not a win. openstitch ran 8 of 18 jobs and its medians are over those 8. Word cc covers
the three jobs with pinned words among the committed pairs (Becker hat, Fremont hat, MFab hat);
heatstitch's MFab word was not located (n/loc, left out, not scored 0), and Nuizu's MFab cc is
0.00 against ours 0.22. The engines ran on Kent's laptop in one session; their DSTs and sheets
stay local.

## Tables

### nuizu against the pro and ours (2026-11-04)

18 jobs scored, 0 with no competitor file.

Counts: ours / competitor / pro. Kappas and word cc: ours-vs-pro / competitor-vs-pro (stitch-type kappa carries its chance floor; chance-corrected only, ROADMAP gate 4).

| job | competitor size mm (vs pro width) | stitches | trims | hops | needle-up mm | colour chg | sttype kappa | direction kappa | word cc |
|---|---|---|---|---|---|---|---|---|---|
| becker_hat_large | 101.2x63.4 (0.99x) | 16,262 / 58,520 / 12,356 | 11 / 32 / 10 | 14 / 17432 / 13 | 327.3 / 37,178.6 / 416.1 | 6 | 0.29 / 0.00 (0.47) | 0.35 / 0.21 | 0.84 / -0.23 |
| becker_lc_large | 95.0x59.4 (0.99x) | 14,922 / 54,907 / 11,274 | 12 / 28 / 12 | 15 / 16430 / 14 | 292.1 / 33,315.3 / 375.6 | 6 | 0.33 / 0.00 (0.44) | 0.35 / 0.20 | - / - |
| becker_hat_small | 76.0x47.6 (0.99x) | 10,546 / 42,392 / 8,694 | 11 / 15 / 11 | 16 / 13091 / 14 | 281.3 / 22,550.3 / 321.9 | 6 | 0.53 / 0.03 (0.29) | 0.42 / 0.18 | - / - |
| becker_chest_small | 76.0x47.6 (0.99x) | 10,309 / 42,392 / 8,694 | 11 / 15 / 12 | 16 / 13091 / 14 | 281.4 / 22,550.3 / 292.4 | 6 | 0.58 / 0.03 (0.29) | 0.45 / 0.18 | - / - |
| becker_beanie | 79.4x49.6 (0.99x) | 13,864 / 44,736 / 11,411 | 14 / 16 / 11 | 19 / 13703 / 15 | 339.4 / 24,244.9 / 375.5 | 6 | 0.24 / 0.04 (0.43) | 0.40 / 0.00 | - / - |
| gaulke_roofing_hat | 114.2x46.8 (1.00x) | 7,446 / 52,469 / 6,138 | 30 / 17 / 42 | 45 / 17608 / 41 | 371.5 / 17,443.9 / 501.9 | 6 | 0.14 / 0.02 (0.02) | 0.51 / 0.00 | - / - |
| gaulke_roofing_lc | 95.2x39.0 (1.00x) | 5,778 / 42,925 / 5,151 | 23 / 12 / 42 | 47 / 14308 / 41 | 316.9 / 13,309.7 / 372.6 | 6 | 0.29 / 0.03 (0.01) | 0.51 / 0.00 | - / - |
| gaulke_roofing_beanie | 93.8x38.4 (1.00x) | 7,602 / 42,352 / 7,051 | 24 / 11 / 42 | 48 / 14100 / 42 | 327.6 / 13,054.1 / 408.6 | 6 | 0.31 / 0.03 (0.04) | 0.00 / 0.13 | - / - |
| hotel_fremont_hat | 92.6x49.8 (1.00x) | 15,899 / 55,249 / 17,067 | 25 / 35 / 21 | 175 / 18569 / 30 | 501.1 / 14,296.3 / 506.9 | 6 | 0.53 / 0.01 (0.01) | 0.00 / 0.00 | 1.00 / 0.52 |
| hotel_fremont_patch | 92.4x49.8 (1.00x) | 14,856 / 55,257 / 15,458 | 20 / 34 / 21 | 175 / 18545 / 28 | 475.9 / 14,266.3 / 533.0 | 6 | 0.52 / 0.01 (0.01) | 0.42 / 0.00 | - / - |
| mfab_hat | 104.8x39.6 (1.00x) | 20,801 / 68,480 / 17,568 | 16 / 214 / 19 | 30 / 22825 / 22 | 556.2 / 51,102.3 / 391.8 | 5 | 0.56 / 0.07 (0.16) | 0.00 / 0.18 | 0.22 / 0.00 |
| mfab_lc | 96.4x36.2 (1.00x) | 18,092 / 53,935 / 15,786 | 19 / 72 / 20 | 31 / 17432 / 23 | 345.2 / 32,211.6 / 367.5 | 5 | 0.57 / 0.09 (0.18) | 0.00 / 0.14 | - / - |
| precision_drone | 62.6x64.6 (1.00x) | 14,769 / 49,377 / 14,552 | 86 / 71 / 59 | 122 / 16449 / 80 | 1,442.6 / 28,397.9 / 900.6 | 6 | 0.38 / 0.02 (0.11) | 0.08 / 0.00 | - / - |
| tires_hat_3d | 114.2x42.2 (1.00x) | 4,544 / 18,725 / 5,555 | 3 / 19 / 10 | 3 / 4556 / 10 | 52.7 / 8,657.5 / 273.0 | 5 | 0.00 / 0.00 (0.01) | 0.71 / 0.26 | - / - |
| goldentee_hat | 74.8x62.6 (1.00x) | 11,018 / 34,671 / 5,973 | 25 / 25 / 10 | 42 / 11957 / 15 | 536.3 / 12,879.9 / 288.9 | 6 | 0.83 / 0.04 (0.01) | 0.24 / 0.00 | - / - |
| toat_machine_hat | 89.4x63.8 (1.00x) | 18,869 / 75,573 / 13,886 | 22 / 431 / 31 | 37 / 24669 / 31 | 328.7 / 42,554.1 / 528.0 | 6 | 0.32 / 0.00 (0.05) | 0.22 / 0.00 | - / - |
| toat_machine_beanie | 80.8x57.6 (1.00x) | 18,310 / 68,850 / 14,817 | 21 / 383 / 31 | 35 / 22377 / 32 | 335.1 / 35,988.0 / 531.1 | 6 | 0.38 / 0.00 (0.03) | 0.38 / 0.00 | - / - |
| toat_beanie | 82.2x55.0 (1.00x) | 18,253 / 68,474 / 15,111 | 20 / 24 / 31 | 34 / 22648 / 32 | 310.7 / 16,022.5 / 533.3 | 6 | 0.40 / 0.00 (0.03) | 0.39 / 0.00 | - / - |

Medians over the scored jobs: stitches vs pro (x) 4.69; needle-up mm vs pro (x) 54.57; trims vs pro (delta) 12.5; hops vs pro (delta) 16912.5; sttype kappa ours 0.38; sttype kappa competitor 0.02; direction kappa ours 0.37; direction kappa competitor 0.0; jobs competitor sttype kappa >= ours 1 of 18.


### nuizu-satin-auto against the pro and ours (2026-11-04)

18 jobs scored, 0 with no competitor file.

Counts: ours / competitor / pro. Kappas and word cc: ours-vs-pro / competitor-vs-pro (stitch-type kappa carries its chance floor; chance-corrected only, ROADMAP gate 4).

| job | competitor size mm (vs pro width) | stitches | trims | hops | needle-up mm | colour chg | sttype kappa | direction kappa | word cc |
|---|---|---|---|---|---|---|---|---|---|
| becker_hat_large | 102.4x64.4 (1.00x) | 16,262 / 57,937 / 12,356 | 11 / 54 / 10 | 14 / 18998 / 13 | 327.3 / 37,049.0 / 416.1 | 6 | 0.29 / 0.00 (0.60) | 0.35 / 0.00 | 0.84 / 0.05 |
| becker_lc_large | 96.2x60.6 (1.00x) | 14,922 / 53,243 / 11,274 | 12 / 37 / 12 | 15 / 17938 / 14 | 292.1 / 33,281.8 / 375.6 | 6 | 0.33 / 0.00 (0.58) | 0.35 / 0.00 | - / - |
| becker_hat_small | 77.2x48.6 (1.01x) | 10,546 / 40,351 / 8,694 | 11 / 14 / 11 | 16 / 14318 / 14 | 281.3 / 22,758.1 / 321.9 | 6 | 0.53 / 0.00 (0.46) | 0.42 / 0.00 | - / - |
| becker_chest_small | 77.2x48.6 (1.01x) | 10,309 / 40,351 / 8,694 | 11 / 14 / 12 | 16 / 14318 / 14 | 281.4 / 22,758.1 / 292.4 | 6 | 0.58 / 0.00 (0.46) | 0.45 / 0.00 | - / - |
| becker_beanie | 80.4x50.8 (1.01x) | 13,864 / 42,497 / 11,411 | 14 / 16 / 11 | 19 / 14879 / 15 | 339.4 / 24,435.8 / 375.5 | 6 | 0.24 / 0.00 (0.65) | 0.40 / 0.00 | - / - |
| gaulke_roofing_hat | 115.2x48.0 (1.01x) | 7,446 / 43,644 / 6,138 | 30 / 15 / 42 | 45 / 17703 / 41 | 371.5 / 17,232.9 / 501.9 | 6 | 0.14 / 0.01 (0.03) | 0.51 / 0.11 | - / - |
| gaulke_roofing_lc | 96.2x40.2 (1.01x) | 5,778 / 35,009 / 5,151 | 23 / 11 / 42 | 47 / 14442 / 41 | 316.9 / 13,196.7 / 372.6 | 6 | 0.29 / 0.03 (0.03) | 0.51 / 0.10 | - / - |
| gaulke_roofing_beanie | 94.8x39.6 (1.01x) | 7,602 / 34,394 / 7,051 | 24 / 10 / 42 | 48 / 14214 / 42 | 327.6 / 12,993.9 / 408.6 | 6 | 0.31 / 0.03 (0.12) | 0.00 / 0.00 | - / - |
| hotel_fremont_hat | 93.6x51.0 (1.01x) | 15,899 / 49,026 / 17,067 | 25 / 56 / 21 | 175 / 20899 / 30 | 501.1 / 14,775.2 / 506.9 | 6 | 0.53 / 0.03 (0.04) | 0.00 / 0.51 | 1.00 / 1.00 |
| hotel_fremont_patch | 93.6x51.0 (1.01x) | 14,856 / 48,965 / 15,458 | 20 / 56 / 21 | 175 / 20881 / 28 | 475.9 / 14,692.2 / 533.0 | 6 | 0.52 / 0.03 (0.04) | 0.42 / 0.00 | - / - |
| mfab_hat | 105.8x40.8 (1.01x) | 20,801 / 63,815 / 17,568 | 16 / 537 / 19 | 30 / 24109 / 22 | 556.2 / 50,878.6 / 391.8 | 5 | 0.56 / 0.05 (0.27) | 0.00 / 0.00 | 0.22 / 0.00 |
| mfab_lc | 97.6x37.4 (1.01x) | 18,092 / 50,353 / 15,786 | 19 / 399 / 20 | 31 / 19215 / 23 | 345.2 / 32,201.9 / 367.5 | 5 | 0.57 / 0.10 (0.22) | 0.00 / 0.00 | - / - |
| precision_drone | 63.8x65.6 (1.02x) | 14,769 / 44,546 / 14,552 | 86 / 145 / 59 | 122 / 17946 / 80 | 1,442.6 / 27,564.5 / 900.6 | 6 | 0.38 / 0.01 (0.17) | 0.08 / 0.00 | - / - |
| tires_hat_3d | 115.4x43.2 (1.01x) | 4,544 / 13,585 / 5,555 | 3 / 23 / 10 | 3 / 4475 / 10 | 52.7 / 8,042.3 / 273.0 | 5 | 0.00 / 0.00 (0.01) | 0.71 / 0.09 | - / - |
| goldentee_hat | 75.8x63.2 (1.01x) | 11,018 / 29,474 / 5,973 | 25 / 43 / 10 | 42 / 11989 / 15 | 536.3 / 13,105.0 / 288.9 | 6 | 0.83 / 0.03 (0.04) | 0.24 / 0.00 | - / - |
| toat_machine_hat | 90.4x64.8 (1.01x) | 18,869 / 59,430 / 13,886 | 22 / 689 / 31 | 37 / 23901 / 31 | 328.7 / 47,850.0 / 528.0 | 6 | 0.32 / 0.02 (0.23) | 0.22 / 0.00 | - / - |
| toat_machine_beanie | 82.0x58.8 (1.01x) | 18,310 / 53,472 / 14,817 | 21 / 619 / 31 | 35 / 21836 / 32 | 335.1 / 40,119.5 / 531.1 | 6 | 0.38 / 0.01 (0.19) | 0.38 / 0.00 | - / - |
| toat_beanie | 83.2x56.2 (1.01x) | 18,253 / 53,488 / 15,111 | 20 / 36 / 31 | 34 / 21613 / 32 | 310.7 / 17,459.5 / 533.3 | 6 | 0.40 / 0.03 (0.20) | 0.39 / 0.00 | - / - |

Medians over the scored jobs: stitches vs pro (x) 4.0; needle-up mm vs pro (x) 55.22; trims vs pro (delta) 29.0; hops vs pro (delta) 17895.0; sttype kappa ours 0.38; sttype kappa competitor 0.01; direction kappa ours 0.37; direction kappa competitor 0.0; jobs competitor sttype kappa >= ours 1 of 18.


### heatstitch against the pro and ours (2026-11-04)

18 jobs scored, 0 with no competitor file.

Counts: ours / competitor / pro. Kappas and word cc: ours-vs-pro / competitor-vs-pro (stitch-type kappa carries its chance floor; chance-corrected only, ROADMAP gate 4).

| job | competitor size mm (vs pro width) | stitches | trims | hops | needle-up mm | colour chg | sttype kappa | direction kappa | word cc |
|---|---|---|---|---|---|---|---|---|---|
| becker_hat_large | 101.6x64.3 (1.00x) | 16,262 / 12,719 / 12,356 | 11 / 87 / 10 | 14 / 89 / 13 | 327.3 / 1,448.1 / 416.1 | 4 | 0.29 / 0.17 (0.56) | 0.35 / 0.00 | 0.84 / 0.00 |
| becker_lc_large | 95.8x60.3 (1.00x) | 14,922 / 11,143 / 11,274 | 12 / 83 / 12 | 15 / 85 / 14 | 292.1 / 1,366.8 / 375.6 | 4 | 0.33 / 0.32 (0.52) | 0.35 / 0.00 | - / - |
| becker_hat_small | 76.6x48.4 (1.00x) | 10,546 / 8,190 / 8,694 | 11 / 66 / 11 | 16 / 68 / 14 | 281.3 / 904.3 / 321.9 | 5 | 0.53 / 0.47 (0.48) | 0.42 / 0.32 | - / - |
| becker_chest_small | 76.6x48.4 (1.00x) | 10,309 / 8,190 / 8,694 | 11 / 66 / 12 | 16 / 68 / 14 | 281.4 / 904.3 / 292.4 | 5 | 0.58 / 0.47 (0.48) | 0.45 / 0.32 | - / - |
| becker_beanie | 79.8x50.5 (1.00x) | 13,864 / 8,292 / 11,411 | 14 / 72 / 11 | 19 / 74 / 15 | 339.4 / 1,008.4 / 375.5 | 5 | 0.24 / 0.10 (0.50) | 0.40 / 0.00 | - / - |
| gaulke_roofing_hat | 114.0x47.2 (1.00x) | 7,446 / 5,187 / 6,138 | 30 / 45 / 42 | 45 / 47 / 41 | 371.5 / 523.2 / 501.9 | 1 | 0.14 / 0.22 (0.73) | 0.51 / 0.43 | - / - |
| gaulke_roofing_lc | 95.2x39.4 (1.00x) | 5,778 / 3,798 / 5,151 | 23 / 36 / 42 | 47 / 46 / 41 | 316.9 / 397.0 / 372.6 | 1 | 0.29 / 0.13 (0.66) | 0.51 / 0.31 | - / - |
| gaulke_roofing_beanie | 93.8x38.8 (1.00x) | 7,602 / 3,695 / 7,051 | 24 / 32 / 42 | 48 / 43 / 42 | 327.6 / 370.0 / 408.6 | 1 | 0.31 / 0.13 (0.56) | 0.00 / 0.07 | - / - |
| hotel_fremont_hat | 92.4x50.1 (1.00x) | 15,899 / 3,265 / 17,067 | 25 / 38 / 21 | 175 / 46 / 30 | 501.1 / 485.5 / 506.9 | 2 | 0.53 / 0.00 (0.59) | 0.00 / 0.10 | 1.00 / 0.79 |
| hotel_fremont_patch | 92.3x50.1 (1.00x) | 14,856 / 3,265 / 15,458 | 20 / 34 / 21 | 175 / 50 / 28 | 475.9 / 508.0 / 533.0 | 2 | 0.52 / 0.09 (0.61) | 0.42 / 0.13 | - / - |
| mfab_hat | 104.7x40.2 (1.00x) | 20,801 / 11,717 / 17,568 | 16 / 13 / 19 | 30 / 12 / 22 | 556.2 / 387.1 / 391.8 | 4 | 0.56 / 0.16 (0.46) | 0.00 / 0.00 | 0.22 / - |
| mfab_lc | 96.9x36.8 (1.00x) | 18,092 / 9,778 / 15,786 | 19 / 9 / 20 | 31 / 8 / 23 | 345.2 / 195.2 / 367.5 | 2 | 0.57 / 0.21 (0.45) | 0.00 / 0.00 | - / - |
| precision_drone | 62.4x62.8 (1.00x) | 14,769 / 7,415 / 14,552 | 86 / 80 / 59 | 122 / 91 / 80 | 1,442.6 / 947.9 / 900.6 | 5 | 0.38 / 0.00 (0.45) | 0.08 / 0.04 | - / - |
| tires_hat_3d | 114.6x42.4 (1.00x) | 4,544 / 3,746 / 5,555 | 3 / 6 / 10 | 3 / 5 / 10 | 52.7 / 167.5 / 273.0 | 1 | 0.00 / 0.00 (0.39) | 0.71 / 0.21 | - / - |
| goldentee_hat | 72.2x58.5 (0.96x) | 11,018 / 3,900 / 5,973 | 25 / 49 / 10 | 42 / 52 / 15 | 536.3 / 542.6 / 288.9 | 5 | 0.83 / 0.25 (0.48) | 0.24 / 0.33 | - / - |
| toat_machine_hat | 88.3x62.7 (0.99x) | 18,869 / 11,131 / 13,886 | 22 / 31 / 31 | 37 / 35 / 31 | 328.7 / 495.1 / 528.0 | 3 | 0.32 / 0.13 (0.59) | 0.22 / 0.46 | - / - |
| toat_machine_beanie | 79.8x56.8 (0.98x) | 18,310 / 9,325 / 14,817 | 21 / 33 / 31 | 35 / 38 / 32 | 335.1 / 441.0 / 531.1 | 3 | 0.38 / 0.10 (0.57) | 0.38 / 0.00 | - / - |
| toat_beanie | 81.4x54.1 (0.99x) | 18,253 / 9,008 / 15,111 | 20 / 25 / 31 | 34 / 28 / 32 | 310.7 / 297.2 / 533.3 | 2 | 0.40 / 0.13 (0.58) | 0.39 / 0.48 | - / - |

Medians over the scored jobs: stitches vs pro (x) 0.67; needle-up mm vs pro (x) 1.02; trims vs pro (delta) 8.0; hops vs pro (delta) 8.5; sttype kappa ours 0.38; sttype kappa competitor 0.13; direction kappa ours 0.37; direction kappa competitor 0.11; jobs competitor sttype kappa >= ours 2 of 18.


### openstitch against the pro and ours (2026-11-04)

8 jobs scored, 0 with no competitor file.

Counts: ours / competitor / pro. Kappas and word cc: ours-vs-pro / competitor-vs-pro (stitch-type kappa carries its chance floor; chance-corrected only, ROADMAP gate 4).

| job | competitor size mm (vs pro width) | stitches | trims | hops | needle-up mm | colour chg | sttype kappa | direction kappa | word cc |
|---|---|---|---|---|---|---|---|---|---|
| becker_hat_large | 101.6x63.6 (1.00x) | 16,262 / 11,536 / 12,356 | 11 / 141 / 10 | 14 / 140 / 13 | 327.3 / 2,448.2 / 416.1 | 4 | 0.29 / 0.03 (0.43) | 0.35 / 0.00 | 0.84 / 0.50 |
| becker_lc_large | 95.6x59.6 (1.00x) | 14,922 / 9,102 / 11,274 | 12 / 117 / 12 | 15 / 116 / 14 | 292.1 / 2,039.0 / 375.6 | 3 | 0.33 / 0.05 (0.42) | 0.35 / 0.00 | - / - |
| becker_hat_small | 76.6x48.2 (1.00x) | 10,546 / 6,283 / 8,694 | 11 / 93 / 11 | 16 / 92 / 14 | 281.3 / 1,758.6 / 321.9 | 5 | 0.53 / 0.03 (0.48) | 0.42 / 0.15 | - / - |
| becker_chest_small | 76.6x48.2 (1.00x) | 10,309 / 6,283 / 8,694 | 11 / 93 / 12 | 16 / 92 / 14 | 281.4 / 1,758.6 / 292.4 | 5 | 0.58 / 0.03 (0.48) | 0.45 / 0.15 | - / - |
| becker_beanie | 79.6x50.2 (1.00x) | 13,864 / 6,761 / 11,411 | 14 / 97 / 11 | 19 / 96 / 15 | 339.4 / 1,802.4 / 375.5 | 5 | 0.24 / 0.00 (0.40) | 0.40 / 0.02 | - / - |
| hotel_fremont_hat | 91.6x49.0 (0.99x) | 15,899 / 1,702 / 17,067 | 25 / 48 / 21 | 175 / 47 / 30 | 501.1 / 661.1 / 506.9 | 4 | 0.53 / 0.17 (0.56) | 0.00 / 0.00 | 1.00 / 0.76 |
| precision_drone | 62.6x64.0 (1.00x) | 14,769 / 7,173 / 14,552 | 86 / 101 / 59 | 122 / 100 / 80 | 1,442.6 / 1,299.0 / 900.6 | 6 | 0.38 / 0.07 (0.46) | 0.08 / 0.07 | - / - |
| goldentee_hat | 72.2x58.0 (0.96x) | 11,018 / 3,878 / 5,973 | 25 / 82 / 10 | 42 / 81 / 15 | 536.3 / 1,036.4 / 288.9 | 6 | 0.83 / 0.48 (0.49) | 0.24 / 0.00 | - / - |

Medians over the scored jobs: stitches vs pro (x) 0.69; needle-up mm vs pro (x) 5.11; trims vs pro (delta) 81.5; hops vs pro (delta) 78.0; sttype kappa ours 0.45; sttype kappa competitor 0.04; direction kappa ours 0.35; direction kappa competitor 0.01; jobs competitor sttype kappa >= ours 0 of 8.

The tool's own production sheet against what our reader counts in its DST (stated -> read):

- becker_hat_large: stitches 11536 -> 11536, trims 141 -> 141
- becker_lc_large: stitches 9102 -> 9102, trims 117 -> 117
- becker_hat_small: stitches 6283 -> 6283, trims 93 -> 93
- becker_chest_small: stitches 6283 -> 6283
- becker_beanie: stitches 6761 -> 6761
- hotel_fremont_hat: stitches 1702 -> 1702
- precision_drone: stitches 7173 -> 7173
- goldentee_hat: stitches 3878 -> 3878
