# Hatch 4 trial: the export list (2026-11-04)

Tier 2 of the free-digitizer survey ([`docs/free-digitizer-survey-2026-11-04.md`](free-digitizer-survey-2026-11-04.md)),
to run after Tier 1 lands (Kent, 2026-11-04: "let's do Hatch and Wilcom after this is
completed"). Hatch's trial is one shot per machine and its export counter is the whole
budget, so the list is fixed BEFORE the install. Nothing below has run yet.
**Kent approved the 30 as written, 2026-11-04** ("Approve as written"); install waits for
Tier 1 (PR #1239) to land and an afternoon of his.

## The budget, as Hatch states it (read 2026-11-04)

- **30 days from first installation and sign-in** (Hatch FAQ, free-trial page). The clock
  starts at sign-in, so install on a day the first exports can follow. Needs a Hatch account
  (profile.hatchembroidery.com); no card. **Windows 11 64-bit only**: this laptop is Windows
  11 Pro 10.0.26300, so fine.
- **Exports to machine formats are counted; `.EMB` saves are not.** FAQ: "You can save your
  working .EMB file as often as you wish — there is no limit on saving." Save every job as
  `.EMB` beside its DST: a re-export later costs one count, a re-digitize costs the run.
- **The cap is 30 or 100 and Hatch's own pages disagree.** The help-centre trial article the
  survey cited and the trial page's search snippet say **30**; `hatchembroidery.com/faq/free-trial`
  read today says "up to **100** times during the 30-day period". **The first export decides**:
  Hatch 4 has an Exports docker; read the remaining count there (or in the export dialog) after
  export 1 and write it at the top of the run log. The list below spends 30. Wave 2 exists only
  if the counter says 100.
- One export = one machine file. **DST only** (the harness reads DST through pystitch, the
  same reader as ours and the pro's). No PES copies: a second format is a second count.

## Rules for every row

1. **Art in = the file every other engine got**: `scratch_bench/_art/<slug>.png`, the art cut
   to its ink box (Gaulke to its white panel). White background left in. If Hatch's prep gate
   refuses a file ("will not let you apply automatic digitizing until the image has been
   suitably processed"), accept its own prepare step with defaults and write down that it fired.
2. **Size before stitches.** Select the inserted bitmap, Context toolbar **Width = the pro's
   width in mm** (lock proportions on), THEN digitize. Hatch's auto-digitizers work from the
   bitmap's physical size; a resize after digitizing is a different test.
3. **Tool = Auto-Digitize > Auto-Digitize Instant Embroidery**, every default, no edits after.
   That is the one-click peer of our Auto Digitize button and of what Nuizu and heatstitch ran.
   The dialog arm (Auto-Digitize Embroidery, where colours are tagged fill / detail / omit)
   is wave 2 or reserve, never mixed into wave 1.
4. **Export: Output Design > Export Design (Shift+E), file type DST**, into
   `scratch_bench/hatch/<slug>.dst`, exactly that slug. Then File > Save as `.EMB` beside it.
5. **Write a one-line log per row** in `scratch_bench/hatch/run_log.md`: counter before and
   after, size Hatch reports, colours it produced, any prompt it showed. Hatch's own stitch
   count and trim count go in `scratch_bench/hatch/manifest.json` (`slug -> {stitches, trims,
   colors, width_mm, height_mm}`); the harness compares them to what its file says.
6. **Third-party files stay in `scratch_bench/`** (gitignored). No DST, EMB or render drawn
   from one is committed; the scoreboard carries numbers only.

## Wave 1: the 30

**Exports 1-18, the committed pairs** (the nightly tripwire's population; ours and the pro's
figures are already in `scratch_bench/_ours/figures.json`). Width is `pro_baseline.JOBS`.

| # | slug | art | width mm | garment |
|---|---|---|---|---|
| 1 | becker_hat_large | `_art/becker_hat_large.png` | 101.9 | hat_front |
| 2 | becker_lc_large | `_art/becker_lc_large.png` | 95.7 | left_chest |
| 3 | becker_hat_small | `_art/becker_hat_small.png` | 76.5 | hat_front |
| 4 | becker_chest_small | `_art/becker_chest_small.png` | 76.5 | left_chest |
| 5 | becker_beanie | `_art/becker_beanie.png` | 79.8 | beanie |
| 6 | gaulke_roofing_hat | `_art/gaulke_roofing_hat.png` | 114.2 | hat_front |
| 7 | gaulke_roofing_lc | `_art/gaulke_roofing_lc.png` | 95.2 | left_chest |
| 8 | gaulke_roofing_beanie | `_art/gaulke_roofing_beanie.png` | 93.8 | beanie |
| 9 | hotel_fremont_hat | `_art/hotel_fremont_hat.png` | 92.6 | hat_front |
| 10 | hotel_fremont_patch | `_art/hotel_fremont_patch.png` | 92.5 | patch |
| 11 | mfab_hat | `_art/mfab_hat.png` | 104.9 | hat_front |
| 12 | mfab_lc | `_art/mfab_lc.png` | 96.7 | left_chest |
| 13 | precision_drone | `_art/precision_drone.png` | 62.6 | hat_front |
| 14 | tires_hat_3d | `_art/tires_hat_3d.png` | 114.3 | hat_front |
| 15 | goldentee_hat | `_art/goldentee_hat.png` | 74.9 | hat_front |
| 16 | toat_machine_hat | `_art/toat_machine_hat.png` | 89.5 | hat_front |
| 17 | toat_machine_beanie | `_art/toat_machine_beanie.png` | 81.0 | beanie |
| 18 | toat_beanie | `_art/toat_beanie.png` | 82.3 | beanie |

**Exports 19-21, instruments** (art in `scratch_bench/_art_instrument/`, 300 DPI metadata, so
Hatch reads the size on import; confirm Width anyway). These answer three rows of the Hatch
manual teardown's gap list (`docs/hatch-manual-teardown-2026-08-08.md` §7) that no page states.
They are software readings from a file, not physical constants; ROADMAP gate 1 does not apply.

| # | slug | art | width mm | what the DST answers |
|---|---|---|---|---|
| 19 | inst_square_default | `_art_instrument/square_40mm.png` | 50.0 (the square is 40.00) | default tatami row spacing (row pitch), default stitch length, pull compensation (sewn width minus 40.00 mm) |
| 20 | inst_square_spacing060 | same object as 19, after Object Properties > Fill: Spacing = 0.60, re-exported | 50.0 | teardown §2.3: is Hatch's spacing figure per row or per forward-row pair (pitch 0.60 or 0.30 in the file) |
| 21 | inst_bars_1_14 | `_art_instrument/bars_1_to_14mm.png` | 86.0 (bars 1, 2, ... 14 mm wide, 30 mm tall) | the satin-vs-fill width threshold, and whether 1 mm became a run |

**Exports 22-25, the four pro pairs that are not committed** (client art, so not in the public
repo; the pro's files are on this box). Art pre-cut to its ink box the same way as the 18, in
`scratch_bench/_art_spare/`; `jobs_spare.json` beside it has the widths and the pro's box.

| # | slug | art | width mm | garment | pro file |
|---|---|---|---|---|---|
| 22 | bridge_hat | `_art_spare/bridge_hat.png` | 63.3 | hat_front | `Claude Personal/Embroidery/Digitized Designs/Bridge Logo/BRIDGE LOGO HAT.DST` |
| 23 | bridge_lc | `_art_spare/bridge_lc.png` | 76.6 | left_chest | `.../BRIDGE LOGO LC.DST` |
| 24 | proseal_hat | `_art_spare/proseal_hat.png` | 85.9 | hat_front | `scratch_kent/Embroidery Files/Proseal/PROSEALHAT.DST` |
| 25 | proseal_beanie | `_art_spare/proseal_beanie.png` | 75.0 | beanie | `.../PROSEALHAT BEANI.DST` |

**Exports 26-27, two photo-lane rows** (no pro file: counts, size and the render only).

| # | slug | art | width mm | tool |
|---|---|---|---|---|
| 26 | owl_photostitch | `digitizer/testdata/photo/owl_kent.jpg` | 100.0 | Auto-Digitize > Color PhotoStitch, defaults (the photo tool; Instant Embroidery is the wrong peer for a photograph) |
| 27 | pooh_instant | `scratch_kent/pooh_hunny_266px.jpg` | 90.0 | Instant Embroidery, defaults. 266 px wide is far under Hatch's 300 DPI advice: whether its prep gate fires, and what it does to the dark ink our `dark_ink_floor_rescue` reads, is the measurement |

**Exports 28-30, reserve.** Unassigned until rows 1-27 are done. First call on them: a redo
of any row that went wrong (wrong width, wrong format, a prompt answered the wrong way).
If nothing went wrong, the dialog arm on three jobs where Instant and the pro disagree most:
`becker_hat_large`, `mfab_hat`, `hotel_fremont_hat` as `<slug>__dialog.dst`, Auto-Digitize
Embroidery with its own colour classification left as proposed.

## Wave 2 (exports 31-60): only if the counter says 100

- 31-48: the dialog arm (Auto-Digitize Embroidery, its classification untouched) over all 18,
  as `<slug>__dialog.dst`. Settles whether Hatch's one-click and its tagged path differ on our art.
- 49-58: Color PhotoStitch over ten public rows of the photo corpus
  (`docs/scoreboards/photo-corpus/`, the Commons rows Kent graded), 100 mm wide.
- 59-60: reserve.

## Measuring

```bash
cd digitizer && .venv/Scripts/python -m tools.bench_free_digitizers measure --engine hatch
```

writes `scratch_bench/hatch/renders/<slug>.png` (art | ours | hatch | pro) and
`scratch_bench/report-hatch-<date>.md`; `scoreboard --engines nuizu heatstitch openstitch hatch`
regenerates the numbers-only board for `docs/scoreboards/free-digitizers-2026-11-04.md`.

Two small pieces of tooling do not exist yet and are written when the files do, not before:

- `measure` takes `tripwire.committed_jobs()` only, so rows 22-25 need a flag that admits any
  `pro_baseline.JOBS` slug whose art and pro file resolve on this box (`bridge:` resolves via
  `Claude Personal/Embroidery`, `kent:` via `scratch_kent/`; both present here).
- An instrument reader for rows 19-21: row pitch histogram and sewn box from the DST
  (pystitch), satin/fill per bar by zig-zag width. Twenty lines on `tools.pro_pair`.

What the Hatch rows add to the scoreboard: the first "professional tool's automatic output"
column beside the hobbyist engines and the hand digitizer, read with the same seven figures
(chance-corrected only, ROADMAP gate 4), plus the three constants the teardown could not get
from the manual.

## Wilcom EmbroideryStudio 2026 trial: SKIPPED (Kent, 2026-11-04)

**Kent's ruling, 2026-11-04: "Skip Wilcom."** This laptop fails two of the trial's stated
requirements (table below), so the Wilcom column is not measured; Hatch is the one Tier 2 row.
Kept for the record, and for a machine that meets the requirements:

wilcom.com/free-trial, read 2026-11-04: **14 days**, all four levels plus the Elements, "Trial is
available only on Windows OS", no card; **no export limit stated, and none denied**: the first
export decides whether the fortnight measures anything. Stated requirements against this laptop:

| requirement | stated | this laptop (read 2026-11-04) |
|---|---|---|
| OS | Windows 11 64-bit, latest updates | Windows 11 Pro 10.0.26300: ok |
| RAM | 32 GB | 39 GB: ok |
| free disk | 60 GB on a 512 GB+ SSD | **39 GB free of 238 GB: short by 21 GB** |
| graphics | 4 GB or more, non-integrated | **AMD Radeon integrated, 0.5 GB: not met** |
| monitor | 1920 x 1080 or higher | 1920 x 1080: ok |

Whether the installer refuses on the GPU or only runs slowly is unknown; the disk shortfall is
real either way. If a qualifying machine ever appears: run rows 1-25 through Smart Design
one-step, DST into `scratch_bench/wilcom/<slug>.dst`, and stop at the first export if it is
watermarked or blocked.

## Sources

hatchembroidery.com/faq/free-trial (100-export wording, .EMB unlimited, Windows 11, sign-in
clock); hatchembroidery.com/products/hatch-embroidery/trial (30 days, every level, Exports
docker); the help-centre trial-restrictions article cited by the survey (30 exports);
hatch.embroideryhelp.net v3 OnlineHelp: `Instant_embroidery.htm`, `Auto-digitize_embroidery.htm`,
`Export_designs.htm` (Output Design > Export Design), `Dimensionar_ilustraciones.htm` (Context
toolbar Width/Height, lock); help.hatchembroidery.com "How to export (save) my designs to DST
format"; wilcom.com/free-trial. This laptop: `Get-CimInstance` Win32_OperatingSystem /
ComputerSystem / VideoController, `Get-PSDrive C`, 2026-11-04.
