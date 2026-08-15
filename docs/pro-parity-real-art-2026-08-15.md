# Pro-parity on REAL customer artwork — the honest baseline (2026-08-15)

The 23-design corpus behind `pro-parity-program-2026-08-14.md` graded the engine
on artwork **reconstructed from the pro's own stitches**. That file named the
problem itself (§2, "arguably bigger" than the chance-floor caveat) and
estimated the flattery at +10-18 points by extrapolating from
`hotel_fremont_patch`, the only design that had any source image at all.

Kent supplied the actual customer artwork on 2026-08-15. This is the re-run.
**Measurement only — no engine change was made or proposed here.**

## 0. First, the compression worry is unfounded

The concern that prompted this was that the pro files pushed to GitHub had been
compressed, so the earlier comparison ran against degraded references. It did
not. Every file in the repo's `Embroidery Files.zip` was hashed against the
Google Drive originals:

```
identical: 110   different: 0   notfound: 0      (md5, all non-__MACOSX entries)
```

Zip and git store binaries losslessly, so DST/PES/EMB/PDF/JPG all round-trip
byte-exact. The pro reference stitches were never the problem. **The artwork
was**, and that is a different defect with a different fix.

## 1. Headline

15 designs have real customer artwork. Both lanes run the same pro files, the
same engine at the same commit, and the same config — the only difference is the
image handed to stage 1.

| | recon art | real art | delta |
|---|---|---|---|
| **corpus mean** | **69.9** | **57.1** | **-12.8** |

The recon lane reproduces the 2026-08-14 figures almost exactly
(`becker_beanie` 70.6 vs 70.6, `gaulke_roofing_lc` 79.8 vs 79.8, `mfab_hat`
76.3 vs 76.3, `tires_hat_3d` 53.7 vs 53.7), so the harness is anchored and the
-12.8 is a like-for-like delta, not drift.

**-12.8 lands inside the old +10-18 estimate.** That estimate was right about
the magnitude. It was wrong about the mechanism, and the mechanism is what
matters for deciding what to build.

## 2. Per design

`art_iou` is new (`artfidelity.py`): how faithfully the PRO reproduced the
customer's artwork, measured as IoU between the artwork's ink and the pro's own
stitch coverage at the pro's physical size, best shift within +/-4 mm.

```
design                art_iou   recon    real   delta   dpi   ours/pro stitches
hotel_fremont_hat       0.973    68.2    68.3   +0.1    686        0.59
hotel_fremont_patch     0.972    57.2    60.7   +3.5    687        0.66
bridge_lc               0.953    79.9    61.9  -18.0     92        1.21
bridge_hat              0.950    72.8    62.2  -10.6    111        0.99
tires_hat_3d            0.930    53.7    60.5   +6.8    235        0.47
precision_drone         0.795    62.3    53.1   -9.2    313        0.44
mfab_hat                0.743    76.3    69.6   -6.7     45        0.83
mfab_lc                 0.742    72.5    69.8   -2.7     49        0.79
becker_lc_large         0.588    72.9    46.1  -26.8     39        0.77
becker_chest_small      0.583    71.5    48.8  -22.7     48        0.66
becker_hat_large        0.583    69.7    48.5  -21.2     36        0.79
becker_hat_small        0.583    68.1    50.4  -17.7     48        0.66
becker_beanie           0.474    70.6    51.1  -19.5     46        0.52
gaulke_roofing_hat      0.363    73.5    53.2  -20.3    286        1.60
gaulke_roofing_lc       0.337    79.8    52.9  -26.9    343        1.59

MEAN                    0.705    69.9    57.1  -12.8               0.84
```

## 3. The delta is mostly the PRO deviating from the artwork, not engine deficit

```
r(art_iou, delta)       = +0.766
r(art_iou, real score)  = +0.646
r(art_iou, recon score) = -0.434   <- recon lane is blind to art fidelity, as it must be
```

Split the corpus by how faithful the pro was:

| pro's fidelity to art | n | recon | real | delta |
|---|---|---|---|---|
| faithful (`art_iou` >= 0.90) | 5 | 66.4 | 62.7 | **-3.6** |
| re-worked (0.70-0.90) | 3 | 70.4 | 64.2 | -6.2 |
| redesigned (< 0.70) | 7 | 72.3 | 50.1 | **-22.2** |

Where the pro sewed what the artwork actually said, real art costs 3.6 points.
Where the pro redesigned the logo, it costs 22.2. A linear fit puts the score
at `23.4 * art_iou + 40.6`, i.e. **64.1 against a perfectly faithful pro** —
so of the 38-point gap from 57.1 to the 95 target, roughly **7 points are not
reachable by engine work on this corpus at all**, because the reference deviates
from the input.

What the deviations concretely are, per `pro_extra` / `art_missed`:

- **Becker (`pro_extra` 0.37-0.52, `art_missed` ~0.10).** The artwork draws
  BECKER as *outlined* letters — black keyline, hollow interior. The pro filled
  them solid in colour. Our engine reproduced the outline, correctly, and lost
  the coverage IoU for it. This is a pro judgement call ("an outline that thin
  will not sew at 100 mm, fill it"), not an engine bug.
- **Gaulke Roofing (`art_iou` 0.34, `art_missed` 0.33, best shift pinned at the
  +/-4 mm search boundary).** Proportions differ: the art's ink bbox is 2.79:1,
  the pro's design is 2.35:1. The pro re-composed the layout — tightened the gap
  between the roof mark and the two text lines to fit a cap front. No shift can
  align that, which is why the search ran to its edge.
- **MFab (`pro_extra` 0.25, `art_missed` 0.006).** The pro sewed everything the
  art asked for and then added weight around it — bolder keyline than the art
  carries.

## 4. Art resolution turned out not to matter

Effective DPI (artwork ink pixels across the width the pro sewed) ranges 36 to
687 across this set. It barely predicts anything:

```
r(dpi, real score) = +0.296
```

`mfab_hat` / `mfab_lc` at 45 and 49 DPI score 69.6 and 69.8 — the **best** pair
in the corpus. `gaulke_roofing_*` at 286 and 343 DPI score 53.2 and 52.9.
Low-resolution art is not what is holding these scores down; `art_iou` is.
(Stage 1's own low-resolution warning still fires on the Becker and MFab art and
that is correct — it is simply not the dominant term.)

## 5. The scorecard is anti-correlated with visual quality on this corpus

Rendered side by side, the real-art outputs are **visibly better embroidery**
than the recon-art outputs on most designs while scoring 12.8 lower.
`gaulke_roofing_lc` is the clearest case: from recon art the engine emits an
illegible smear where the wordmark should be and scores 79.8; from real art it
emits clean, readable "C GOLKE INDUSTRIES / STEEL ROOFING & SUPPLY" and scores
52.9.

That is not a paradox, it is the metric working as designed and being read as
something it is not. `coverage` (20 pts, whole-design IoU against the pro),
`direction` (20) and `sttype` (20) are **similarity-to-this-pro** measures. Feed
the engine art derived from the pro's stitches and it can echo the pro; feed it
the customer's art and it must *decide*, and every decision that differs from
the pro's costs points even when it is defensible or better.

Coverage did essentially all of the damage:

| component | recon | real | delta |
|---|---|---|---|
| coverage | 0.830 | 0.572 | **-0.258** |
| density | 0.715 | 0.542 | -0.173 |
| travel | 0.851 | 0.709 | -0.142 |
| underlay | 0.707 | 0.598 | -0.109 |
| sttype | 0.575 | 0.529 | -0.046 |
| direction | 0.562 | 0.519 | -0.043 |

`direction` and `sttype` moved -0.04 and sit at 0.52 / 0.53 — still on the
~0.50 chance floor `pro-parity-measurements-2026-08-14.md` identified. **Both
lanes are paying about 20 of those 40 points for answers uncorrelated with the
pro.** Real artwork does not fix that; only rescaling or replacing those two
components does.

## 5b. GARMENT drives the pro's deviation — and every run so far ignored it

Added 2026-08-15 after Kent pointed out that the filenames carry the garment:
`hat` is a Richardson 112 (structured, foam-backed cap front), `beanie` is a
knit winter hat, `LC` is a left chest. That turned out to be the missing driver
behind §3, and it exposes a methodology bug in this run and the last one.

**The harness never told the engine what garment it was digitizing for.**
`prep_all.run_ours` builds a bare `PipelineConfig()`, so `garment_id` and
`fabric_id` are both `None` and `fabrics.py` falls back to
`DEFAULT_FABRIC_ID = "pique_knit"`. Every design in both the 2026-08-14 run and
this one — 12 hats and 7 beanies included — was digitized as a **polo left
chest**.

### What the pro actually varies

Measured on the full file set (pro side only, so the 10 art-less designs count
too): n=12 hat, n=7 left chest, n=7 beanie, n=1 patch.

Thread per mm² of *covered* ground barely moves by garment, and within-garment
spread swamps it:

| garment | n | mean mm/mm² | median | range |
|---|---|---|---|---|
| hat | 12 | 9.66 | 8.99 | 6.93 - 13.77 |
| left chest | 7 | 8.92 | 8.78 | 6.83 - 11.33 |
| beanie | 7 | 8.82 | 8.56 | 5.79 - 11.43 |
| patch | 1 | 11.33 | — | — |

Paired within a single job — same artwork, same digitizer, one variable —
**hat vs left chest is a null result**: solidity is identical to three decimals
(becker 0.662/0.663, gaulke_plowing 0.450/0.450, machine 0.767/0.767, mfab
0.888/0.888) and paired density differs by **+1.4%** across six jobs. The pro
treats a cap front and a left chest the same and just rescales.

**Beanie is the one placement that gets different treatment, and the difference
is large:**

```
job                solidity   density/covered   thread per design area
becker               +37.8%        -4.8%              +31.2%
gaulke_plowing       +44.9%        -7.7%              +33.7%
gaulke_roofing       +70.4%       -12.9%              +48.3%
machine               +0.3%       +30.2%              +30.6%
proseal              +85.9%       -16.5%              +55.3%
MEAN                 +47.9%        -2.3%              +39.8%
MEDIAN               +44.9%        -7.7%              +33.7%
```

A beanie gets **~34% more thread over the same design area, delivered as ~45%
more covered footprint rather than as tighter rows.** Rows hold or loosen
slightly on 4 of 5 jobs. `machine` is the coherent exception: its hat is already
0.767 solid, so there was no room to solidify and the thread went into density
instead (+30.2%).

Physically that is the right answer for a lofty rib knit — thin outlines and
small detail sink into the nap, so you bolden and solidify rather than pack rows
tighter, which would only pucker.

### This is the same mechanism as §3, with a driver attached

Within the Becker series (one artwork, five garments), the beanie has the
**lowest** fidelity to the artwork and the **highest** added coverage:

```
slug                 garment  width  cov mm2  solidity  art_iou  pro_extra
becker_hat_large     hat      101.9     4186     0.662    0.583      0.370
becker_lc_large      lc        95.7     3697     0.663    0.588      0.368
becker_hat_small     hat       76.5     2421     0.676    0.583      0.376
becker_chest_small   lc        76.5     2421     0.676    0.583      0.376
becker_beanie        beanie    79.8     3645     0.912    0.474      0.517
```

So `art_iou` is not a fixed property of a logo. **The pro deviates from the
customer's artwork as a function of the garment**, and the beanie is where the
deviation is largest.

### Setting `garment_id` would NOT fix this

`density_adjust` is **1.0** for `structured_cap`, `pique_knit`, `jersey_tee`,
`canvas_tote` and `woven_dress` alike; only `fleece_sweatshirt` (0.90) and
`terry_towel` (0.85) differ. So threading the garment through changes
`pull_comp_mm` (0.4 cap vs 0.3 polo vs 0.35 jersey) and `fill_underlay`
(`edge_zigzag` vs `edge_run`) — real effects on the `underlay` component (0.598)
and on edge quality, worth doing — but it **cannot produce +45% solidity,
because no solidity or minimum-sewable-feature control exists in the engine at
all.**

Two follow-ups, in order:

1. **A garment-driven minimum feature size.** Below it, promote an outline to a
   solid fill, bolden a thin stroke, drop detail that will not survive. Beanie
   sets the floor high, twill patch low, cap front and left chest in between and
   equal to each other. This is the §7.1 capability, now with a measurable
   target (+45% solidity, beanie vs cap, at flat row spacing) and a measurable
   driver.
2. **`GARMENT_FABRIC["beanie"] = "jersey_tee"` deserves a second look**, though
   *not* for its density: `jersey_tee` carries `density_adjust` 1.0 and the data
   above says row spacing should indeed stay flat. What a lofty knit plausibly
   wants is `jersey_tee`'s heavier underlay neighbours — this corpus cannot
   settle it, and it is sew-out territory.

**Every number in §1-§6 was produced with `garment_id=None`.** They remain valid
as a like-for-like recon-vs-real comparison, since both lanes had the same
config. They are not a measurement of the engine's best available output.

## 6. Real engine deficits this run does expose

These are visible in the renders and in the numbers, and are not explained by
`art_iou`:

1. **A thread-volume deficit that is mostly the solidify gap, not row spacing.**
   Mean `ours/pro` stitch ratio is 0.84, with the spread being the story:
   `precision_drone` 0.44, `tires_hat_3d` 0.47, `becker_beanie` 0.52,
   `hotel_fremont_hat` 0.59. `density` averages 0.542, the second-largest
   component loss. §5b reframes this: on the pro side the same kind of gap is
   paid in *coverage*, not row spacing, so "increase density" is the wrong
   remedy — `becker_beanie` is the extreme case here (0.52 of the pro's stitch
   count) precisely because it is the design the pro solidified most.
2. **Over-stitching in the other direction.** `gaulke_roofing_*` at 1.59-1.60x
   the pro's count. Same engine, same config — so whatever is choosing density
   is not choosing it from anything stable.
3. **Small text is lost.** `hotel_fremont_*` drops "EST 1895" and
   "EAT | STAY | PLAY" to unreadable marks; `precision_drone` loses "AND
   DRONE"; `gaulke_roofing_*` renders the second text line thin and broken. The
   pro sews all of it.
4. **`tires_hat_3d`'s leading stroke blobs.** The script's entry stroke comes out
   thick and lumpy where the pro's is even. Scored 60.5 with `sttype` 0.32 —
   this design is 3D foam, still unimplemented, so part of that is expected.

## 7. What this changes about the target

The 95/100 target was set against a metric that (a) pays ~20 points for chance
on two components and (b) on this corpus penalises correct art reproduction
wherever the pro chose to deviate. **57.1 is the honest number for "how close
are our stitches to this pro's stitches, given the customer's art."** It is not
the same question as "is this good embroidery," and this run is the first time
the two have visibly pointed in opposite directions.

Three things follow, in the order they should be decided:

1. **The pro's deviations from the artwork are a capability, not noise — and
   §5b shows the garment drives them.** Fill an outline too thin to sew at size;
   bold up thin strokes; tighten layout to fit a cap front; drop detail below a
   sewable threshold. Seven of fifteen designs turn on exactly those calls, and
   the beanie series puts a number on the target: **+45% solidity at flat row
   spacing**. Nothing in the engine does this, and no density tuning
   substitutes.
2. **Thread the garment through the harness** (`garment_id` from the filename —
   `hat` -> `hat_front`, `beanie` -> `beanie`, `LC` -> `left_chest`, patch ->
   `patch`). Cheap, and every parity number to date was produced as
   `pique_knit`. It will move `underlay` and edge quality; per §5b it will not
   move density, so do it to stop measuring the wrong configuration, not
   expecting a score jump.
3. **Fix the metric before chasing the number.** Rescale or replace `direction`
   and `sttype` off the chance floor, and decide whether `coverage` should be
   measured against the *artwork* rather than against the pro's stitches. This
   re-bases every historical score, so it needs an explicit decision (already
   flagged in the 2026-08-14 measurements doc, still open).
4. **Then row spacing.** Over-stitching `gaulke_roofing_*` at 1.6x while
   under-stitching `precision_drone` and `tires_hat_3d` at 0.44-0.47, from one
   config, means whatever picks spacing is not picking it from anything stable.
   This is genuinely a spacing problem, unlike item 1.

## 8. Reproducing this

```
cd digitizer
PRO_PARITY_ROOT="G:/My Drive/EMB-Bot/Embroidery Files" \
PRO_PARITY_OUT=<out> .venv/Scripts/python ../digitizer/tools/pro_parity/prep_both.py
.venv/Scripts/python ../digitizer/tools/pro_parity/scorecard.py <out>/real/*/
.venv/Scripts/python ../digitizer/tools/pro_parity/scorecard.py <out>/recon/*/
.venv/Scripts/python ../digitizer/tools/pro_parity/artfidelity.py <out>/real/*/
```

New instruments, all additive — nothing existing was modified:

- `digitizer/tools/pro_parity/real_art.py` — prepares customer artwork. Applies
  exactly one transform (uniform-bar crop, needed because the Gaulke art is a
  phone screenshot with solid black bars that stage 1 would read as foreground).
  Deliberately does NOT remove backgrounds, flatten alpha, sharpen or upscale.
- `digitizer/tools/pro_parity/prep_both.py` — runs both lanes over the 15
  designs, ~5 minutes total.
- `digitizer/tools/pro_parity/artfidelity.py` — the `art_iou` / `pro_extra` /
  `art_missed` instrument.

`digitizer/.venv` did not exist on Kent's machine and was created per
`digitizer/README.md` §Setup. The `tesseract-ocr` system binary is still not
installed; `pytesseract` imports fine without it and nothing in this run needed
OCR.

## 9. Corpus coverage, and what is still missing

Real artwork exists for 15 designs. `bridge_hat` and `bridge_lc` are **new** —
the Bridge Bar job arrived with this artwork drop and was never in the 23.

Still art-less, so still only measurable in the flattered lane:
`gaulke_plowing_hat`, `gaulke_plowing_lc`, `gaulke_jb`, `machine_hat`,
`machine_lc`, `machine_beanie`, `toat_beanie`, `golf_hat`, `proseal_hat`,
`proseal_beanie` (10 designs).

**One correction to a claim in the 2026-08-14 docs:** they treat
`Hotel Fremont/Hotel Patch/HOTEL FREMONT .BMP` as that design's real source art.
It is a Wilcom backdrop *proof composite* — the logo above a render of the
finished patch — not clean artwork. The two `BRIDGE LOGO *.BMP` files are the
same kind of thing, and are visibly stitch renders. So the +10-18 flattery
estimate was calibrated against a weaker reference than it claimed. The estimate
survived anyway; the reasoning behind it did not.

## 10. Untapped in the supplied files

- **14 `.EMB` files (Wilcom native).** `DesignDocument` is encrypted (Shannon
  entropy 8.00/8.00), so per-object geometry is out of reach. But `Contents` is
  zlib and inflates cleanly, carrying the stitch-type presets the design
  actually used (`<PRESET_RUN_1>`, `<PRESET_RUN_2>`, `<PRESET_SATIN_1>`,
  `<PRESET_TATAMI_1>`, `<PRESET_TATAMI_2>`) plus the thread/colourway table; and
  `\x05WilcomDesignInformationDDD` is a readable property set with object count,
  longest/shortest stitch, trims, stops and thread length. That is real
  aggregate ground truth for `sttype`, which is the component sitting on the
  chance floor.
- **21 `.PDF` Wilcom ES-65 worksheets.** Vector stitch renders plus a spec sheet
  (stitch count, colour changes, trims, machine, H/W in inches). Useful as an
  independent dimension cross-check; not source art.
