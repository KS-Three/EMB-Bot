# The photo lane's subject cut-out on a scene with no subject — measurement record (2026-10-28/29)

**Every number here is an instrument reading, not a quality claim** (ROADMAP
gate 4). Readings were taken on the 18 photographs of the Commons corpus
(`digitizer/testdata/photo/corpus/corpus.json`, real artwork, fetched as the
corpus tool fetches them), the same files PR #1178 sited stage 0 on. Nothing
synthetic calibrated anything (gate 2). Nothing was sewn (gate 1).

**What shipped, and by whom.** This session was started to find out why the
cut-out emptied six scenes and to build a guard behind a flag. While it was
measuring, PR #1179 (Kent's own session, 2026-10-28 23:50) landed the guard
on main: `cfg.photo_cutout_min_kept` (0.20 of stage 1's artwork, ON; 0.0 =
the old engine), `PHOTO_CUTOUT_REFUSED`, refused → the classical route. The
parallel flag built here (`photo_cutout_min_subject_frac`, OFF, on the frame
share) was dropped on rebase; one knob for one thing. What this record adds
is the measurement: the cause in rembg's own numbers, the arm comparison
Kent asked for, the per-row readings and the time cost.

## 1. Intent

PR #1178 (2026-10-28) sends every corpus photograph to the photo lane. The
first capture through it (`head-b6ec26a`) showed the lane's own gap: on six
scenes the subject cut-out (`stage1_photo_prep.remove_background_seam`,
rembg `isnet-general-use`) removed 95–100 % of the frame, and the lane sewed
0–3,117 stitches where the gradient lane had sewn 13,000–40,000:

| row | `cutout_removed_frac` | stitches | size mm |
|---|---|---|---|
| landscape_lake | 1.000 | 14 | 1.6 × 1.1 |
| snow_highkey | 1.000 | 0 | 0 × 0 |
| underwater_reef | 0.998 | 37 | 3.7 × 4.9 |
| night_neon | 0.987 | 513 | 9.5 × 43.4 |
| night_skyline | 0.980 | 532 | 12.7 × 23.2 |
| stained_glass | 0.958 | 3,117 | 46.2 × 62.2 |

The photo-style census (`docs/photo-style-census-2026-10-27.md`, item 1)
named the mechanism on `snow_highkey` and `pencil_sketch` a day earlier.
Kent, 2026-10-27: the photo lane must improve ALL photos, not the ones on
hand; the lane was tuned on four portraits and the owl, every one of which
HAS a subject.

## 2. Cause (measured)

rembg's alpha, thresholded at `REMBG_ALPHA_THRESHOLD` (128), as a share of
the frame, on 800-px rasters of the corpus files (the stage-1 raster is of
that order at 80 mm):

| row | subject share (alpha ≥ 128) | alpha p90 | | row | subject share | alpha p90 |
|---|---|---|---|---|---|---|
| snow_highkey | 0.0001 | 1 | | fireworks | 0.270 | 190 |
| landscape_lake | 0.0006 | 12 | | bw_street | 0.307 | 254 |
| pencil_sketch | 0.0011 | 43 | | dark_dog | 0.311 | 254 |
| underwater_reef | 0.0031 | 31 | | group_people | 0.376 | 254 |
| night_neon | 0.0053 | 10 | | food_plate | 0.572 | 254 |
| night_skyline | 0.0139 | 2 | | architecture | 0.756 | 254 |
| stained_glass | 0.0541 | 31 | | | | |

A scene is not a cut-out problem rembg solves badly; it is one it answers
"no subject" to, with low alpha everywhere (p90 ≤ 43). Three things then let
that answer empty the hoop before #1179:

1. the seam thresholds at 128 and calls everything below background;
2. `_clean_background_mask` fills back only SMALL background islands (under
   `min_detail_mm² × px_per_mm²`) — a frame-wide one is kept as is;
3. `pipeline.run_stages` treated only a `None` return as failure, so the
   mask was OR-ed into `p.bg_mask`, stage 2 found no foreground, and the
   design was empty or a few strays.

`cutout_removed_frac` on the sxs page is after-minus-before, so a photo
whose border already flood-filled as background under-reads it:
`pencil_sketch` shows 0.842 while rembg kept 0.1 % of it. The guard's own
reading — what rembg kept — is what the page now shows as `cutout refused
(kept frac)`.

## 3. The guard, read against these numbers

#1179's floor is 0.20 of stage 1's artwork (`pipeline._cutout_kept_fraction`:
the share of not-background pixels the cut-out keeps). On the six scenes
stage 1 floods nothing, so the artwork IS the frame and the two
denominators agree: the kept shares read in the arm-B capture were 0.000,
0.000, 0.002, 0.013, 0.020, 0.042 — all refused. The bimodal gap in section
2 puts the floor 3.7× above the largest "no subject" answer (stained glass
0.054) and 1.35× below the smallest real subject by frame share (fireworks
0.270; #1179's own smallest kept, bw_street, read 0.31 of its artwork). The
session's parallel siting had put the floor at the geometric midpoint, 0.12;
both floors refuse the same seven rows (the six scenes and pencil_sketch)
and keep the same eleven. A reading, not a re-siting proposal.

**Known limit (both floors).** A real subject covering under a fifth of its
artwork (a bird in sky, a product at the edge) is refused with the scenes
and sews WITH its background — a soft failure in the opposite direction of
the empty hoop. No corpus row has one; the corpus gets such a row before
the floor moves.

## 4. What the lane does with the refused frame — A vs B

Kent (2026-10-28, via the director): "Measure A vs B, ship better", B on a
tie. A = the refused frame still gets tone/texture/face prep; B = prep
skipped too (the `cutout_failed` route, byte-identical to
`photo_prep=False`). The 2026-08-24 ruling (`config.py`,
`photo_prep_background_removal`) had found prep WITHOUT the cut-out the worst
arm on four portraits (`baby_deck_laugh` 110 → 175 regions); those portraits
all HAD a subject, so the ruling's measurement did not reach a scene until
now.

**B is the measured arm** — `fidelity_cc` higher than A on four of the six
rows, lower on one, tied on one (section 5), and B's night_neon /
night_skyline renders read as scenes where A's read as fragments. #1179
ships B.

## 5. Readings

Base `corpus_runs/base-75efec5` (the merge-base tree, this worktree before
any edit; identical to #1178's `head-b6ec26a` numbers). A
`corpus_runs/armA-5294002` (this session's flag, prep kept; 2 processes,
2,400 s timeout). B `corpus_runs/armB-fdcc52b` (this session's flag, prep
skipped; snow / reef / skyline at 1 process and 1,200 s; lake / neon /
stained glass timed out there and were re-captured at 2 processes and
2,400 s). HEAD `corpus_runs/head-be1c718` is main's guard (#1179, engine
identical to main ad218cea) at the default request — the PR body carries
that column. All at the Studio's 80 mm `left_chest` request.

| row | base st / cc | A st / trims / cc / wall s | B st / trims / cc / wall s | kept share |
|---|---|---|---|---|
| landscape_lake | 14 / 0.144 | 28,009 / 65 / −0.272 / 595 | 33,881 / 66 / −0.288 / 448 | 0.000 |
| snow_highkey | 0 / — | 26,933 / 48 / −0.469 / 534 | 25,782 / 44 / −0.471 / 1,117 | 0.000 |
| underwater_reef | 37 / −0.065 | 36,056 / 149 / 0.102 / 650 | 37,477 / 138 / 0.118 / 1,173 | 0.002 |
| night_neon | 513 / −0.005 | 33,498 / 155 / 0.083 / 875 | 27,717 / 121 / 0.142 / 373 | 0.013 |
| night_skyline | 532 / −0.059 | 30,337 / 83 / 0.033 / 450 | 25,258 / 61 / 0.090 / 671 | 0.020 |
| stained_glass | 3,117 / −0.002 | 82,402 / 272 / 0.082 / 2,103 | 51,162 / 188 / 0.088 / 797 | 0.042 |

Base rows ran 85–454 s and sewed 0–3,117 stitches on 0–62 mm; both arms
sew the full 80.6 mm frame. Stained glass under A came out 80.6 × 120.2 mm
at 82,402 stitches. The `cc` figures are chance-corrected against blank
fabric (gate 4); the base rows' 0.144 on a 1.6 × 1.1 mm design is the
instrument flattering an empty hoop, which the renders settle.

**Wall time is a reading, not a budget.** B's first pass timed out
night_neon, landscape_lake and stained_glass at 1,200 s inside
`stage7_sequence.sequence`'s rank-only second pass (the Column lane's
`off_blocks = sequence(..., lettering_columns=False)`, via `column_lean.run`
→ `stitch_one`); the re-run of the same rows on the same tree finished in
373, 448 and 797 s. Stage 7 on a full-frame scene is both slow and unstable
(the census saw the same on `outline_lineart_logo`); the Studio stops
waiting at 600 s (Kent 10-26). That cost is the lane's, hidden until now by
the empty hoop, and the next measurement.

## 6. Not done here

- No second rembg model is tried before refusing (~60 s per photo; a scene
  gets the same answer from a saliency net).
- No routing change: a refused photo stays `photo_scene`; the gradient lane
  it used to take sewed 13,000–40,000 stitches Kent graded Bad/Terrible.
- `pencil_sketch` refuses (0.1 % kept) and sews as a whole frame; whether a
  line drawing on paper belongs in the photo lane at all is stage 0's
  question, not the guard's.
- The stage-7 cost on a full-frame scene is named, not fixed.
