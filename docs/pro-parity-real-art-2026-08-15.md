# Pro-parity on REAL customer artwork — the honest baseline (2026-08-15)

The 23-design corpus behind `pro-parity-program-2026-08-14.md` graded the engine
on artwork **reconstructed from the pro's own stitches**. That file named the
problem itself (§2, "arguably bigger" than the chance-floor caveat) and
estimated the flattery at +10-18 points by extrapolating from
`hotel_fremont_patch`, the only design that had any source image at all.

Kent supplied the actual customer artwork on 2026-08-15. This is the re-run.
**No engine behaviour was changed to improve a score here.** The one engine-side
change is a restore of work that had been reverted, justified by measurement in
§0b; the harness changes are in §8.

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

## 0b. Two things moved mid-analysis — read before comparing to older docs

Neither is a measurement artifact. Both are real changes to the tree, and both
landed between this corpus's first run and its verification.

**1. PR #146 was reverted, then restored here.** `a6435f2` (Kent, 2026-08-14
14:13, via GitHub's Revert button on PR #146) undid the pro-parity engine stack:
`stage6_satin.py` -500 lines, `pipeline.py` -135, the fill/overlap/sequence work,
and **three test files deleted** — `test_pro_parity_prep.py`,
`test_pro_parity_scorecard.py`, `test_unsewn_shapes_are_loud.py`, 713 lines.
It reached the local checkout in a pull at 07:00:28, nineteen minutes after this
corpus's first run finished at 06:41:57 — so that first measurement described an
engine the working tree no longer had.

The PR title carried the *superseded* verdict ("DO NOT MERGE — top commit raises
bare fabric 6.1%"), which `pro-parity-program-2026-08-14.md` §1 had already
corrected to **-8.0% bare fabric, +1.35 score** against the right baseline.
Measured here on real artwork the stack is worth **+2.0** (39.4 -> 41.4): the
doc's claim holds, slightly better than stated. Restored on branch
`claude/real-art-parity-and-restore-146`.

Evidence the restore is clean: the non-OCR failure set is **identical (3)** on
untouched `main` 842d3a1, after the harness commit, and after the restore. Full
suite 1007 passed / 16 failed, dropping to **7 failed** once the documented
optional `.[service]` deps are installed — exactly the "7 failed, identical
failure set, zero new" the 2026-08-14 program doc recorded. Those 7 are 4 OCR
tests needing the `tesseract-ocr` system binary (a separate non-pip install per
`digitizer/README.md`) plus **3 failures pre-existing on `main`**: two goldens on
`photo/enthusiast_logo.png` and `test_pushcomp[logo_whitebg.png-towel]`. `main`
was already red before any of this work.

**2. `53e02ae` chance-corrected `direction` and `sttype`** (2026-08-14 21:28),
settling the open decision the 2026-08-14 measurements doc flagged. It re-bases
every earlier score. Any number in an older doc is on the old scale.

**Lesson worth keeping.** The first symptom was a no-op edit appearing to change
engine output. It had not — a `git pull` had replaced the engine between the run
and the check. When a measurement moves and the code you edited cannot explain
it, check whether the tree moved before hunting for non-determinism. The engine
*is* deterministic: same art, same commit, four separate processes,
byte-identical output.

## 1. Headline

15 designs have real customer artwork. Both lanes run the same pro files, the
same engine at the same commit, and the same config — the only difference is the
image handed to stage 1.

**All scores here are CHANCE-CORRECTED** per `53e02ae`. `direction` now reads
**0.00 on 11 of these 15 designs**, where it previously paid ~0.50 for angles
uncorrelated with the pro. Old-scale equivalents are bracketed so this file can
be read against the 2026-08-14 tables; the corrected number is the one to trust.

| | recon art | real art | delta |
|---|---|---|---|
| **corpus mean** | **54.0** [69.7] | **42.0** [57.8] | **-12.0** |

**42.0 is the honest baseline.** Target is 95.

The same corpus was measured four ways because of §0b. Real-art lane,
chance-corrected:

| engine | garment passed | real | recon |
|---|---|---|---|
| post-revert (`main` at 2026-08-15 07:00) | no | 39.4 | 52.1 |
| PR #146 restored | no | 41.4 | 53.9 |
| PR #146 restored | **yes** | **42.0** | **54.0** |

The recon lane at the restored engine reproduces the 2026-08-14 old-scale figures
almost exactly (`becker_beanie` 70.6 vs 70.6, `gaulke_roofing_lc` 79.8 vs 79.8,
`mfab_hat` 76.3 vs 76.3, `tires_hat_3d` 53.7 vs 53.7), so the harness is anchored
and -12.0 is a like-for-like delta, not drift.

**-12.0 lands inside the old +10-18 estimate.** That estimate was right about the
magnitude. It was wrong about the mechanism, and the mechanism is what matters
for deciding what to build.

### Threading the garment through is worth +0.6, and verifies itself

Per §5b the harness never passed `garment_id`. Now it does. Real-art lane,
restored engine, same everything else:

| garment | n | delta |
|---|---|---|
| `left_chest` | 5 | **+0.0 on every single design** |
| `hat_front` | 8 | +1.2 (best: `becker_hat_large` +6.7) |
| `beanie` | 1 | -0.7 |
| `patch` | 1 | -0.4 |
| **all** | 15 | **+0.6** |

The five `left_chest` designs moving **exactly zero** is the control: `left_chest`
maps to `pique_knit`, which was already the silent default, so a correct
implementation must change nothing there and something elsewhere. It does.

Component movement is where §5b predicted — `travel` +0.031, `underlay` +0.007,
`density` +0.009, `coverage` +0.001. Pull compensation and underlay style, not
row spacing. Small, and worth having so the corpus stops measuring a
configuration nobody ships.

## 2. Per design

`art_iou` is new (`artfidelity.py`): how faithfully the PRO reproduced the
customer's artwork, measured as IoU between the artwork's ink and the pro's own
stitch coverage at the pro's physical size, best shift within +/-4 mm.

Restored engine, garment passed, chance-corrected:

```
design                art_iou   recon    real   delta   dpi   ours/pro stitches
hotel_fremont_hat       0.973    52.5    58.3    +5.8   686        0.59
hotel_fremont_patch     0.972    40.4    46.4    +6.0   687        0.66
bridge_lc               0.953    68.4    48.0   -20.4    92        1.21
bridge_hat              0.950    57.9    47.3   -10.6   111        1.10
tires_hat_3d            0.930    43.1    45.4    +2.3   235        0.49
precision_drone         0.795    45.1    38.5    -6.6   313        0.43
mfab_hat                0.743    62.8    54.6    -8.2    45        0.83
mfab_lc                 0.742    56.1    55.7    -0.4    49        0.79
becker_lc_large         0.588    56.2    28.2   -28.0    39        0.77
becker_chest_small      0.583    56.0    32.1   -23.9    48        0.66
becker_hat_large        0.583    53.8    36.2   -17.6    36        0.88
becker_hat_small        0.583    52.9    35.7   -17.2    48        0.71
becker_beanie           0.474    54.7    30.5   -24.2    46        0.52
gaulke_roofing_hat      0.363    52.8    36.1   -16.7   286        1.60
gaulke_roofing_lc       0.337    57.4    37.0   -20.4   343        1.59

MEAN                    0.705    54.0    42.0   -12.0               0.86
```

## 3. The delta is mostly the PRO deviating from the artwork, not engine deficit

```
r(art_iou, delta)       = +0.690
r(art_iou, real score)  = +0.694
r(art_iou, recon score) = -0.166   <- recon lane is near-blind to art fidelity, as it must be
```

Split the corpus by how faithful the pro was:

| pro's fidelity to art | n | recon | real | delta |
|---|---|---|---|---|
| faithful (`art_iou` >= 0.90) | 5 | 52.5 | 49.1 | **-3.4** |
| re-worked (0.70-0.90) | 3 | 54.7 | 49.6 | -5.1 |
| redesigned (< 0.70) | 7 | 54.8 | 33.7 | **-21.1** |

Where the pro sewed what the artwork actually said, real art costs 3.4 points.
Where the pro redesigned the logo, it costs 21.1 — a 6x difference driven by the
reference, not by us. A linear fit puts the score at `29.8 * art_iou + 21.0`,
i.e. **50.8 against a perfectly faithful pro** — so of the 53-point gap from 42.0
to the 95 target, roughly **9 points are not reachable by engine work on this
corpus at all**, because the reference deviates from the input.

Every one of these figures was recomputed on the restored engine at the
chance-corrected scale, and every conclusion held: the old-scale values were
-12.8 flattery, r=+0.766, and -3.6 / -6.2 / -22.2 on the same three-way split.
The finding is not an artifact of either scale or of which engine was measured.

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
| coverage | 0.824 | 0.573 | **-0.251** |
| density | 0.715 | 0.551 | -0.163 |
| travel | 0.853 | 0.739 | -0.113 |
| underlay | 0.701 | 0.605 | -0.096 |
| direction | 0.146 | 0.073 | -0.073 |
| sttype | 0.207 | 0.182 | -0.025 |

**`direction` at 0.073 and `sttype` at 0.182 are the chance correction doing its
job.** On the old scale these read 0.52 and 0.53 and looked like half credit; the
corrected view is that we score close to **zero** for stitch direction on real
artwork — `direction` is literally 0.00 on 11 of 15 designs. The 2026-08-14 doc
suspected ~20 of those 40 points were being paid for noise. It was worse than
that. **40 points of the 100 sit on two components we are barely above chance
on**, and that is now visible instead of hidden.

That reframes the gap: the engine is not 42% of the way to a pro. It reproduces
*coverage* respectably (0.573) and *travel* well (0.739), and is close to
guessing on the two components that encode how a stitch is actually laid.

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

**Threading it through is now done** — see §1's garment table. It is worth +0.6
overall, +1.2 on cap fronts, and exactly +0.0 on all five left-chest designs
(which is the control that proves it is wired correctly, since `left_chest` maps
to the `pique_knit` that was already the silent default). It moved `travel`
+0.031 and `underlay` +0.007 and left `coverage` untouched at +0.001 — the
prediction in this section held. Every number in §1-§6 is measured with the
garment passed.

## 6. Real engine deficits this run does expose

These are visible in the renders and in the numbers, and are not explained by
`art_iou`:

1. **A thread-volume deficit that is mostly the solidify gap, not row spacing.**
   Mean `ours/pro` stitch ratio is 0.86, with the spread being the story:
   `precision_drone` 0.43, `tires_hat_3d` 0.49, `becker_beanie` 0.52,
   `hotel_fremont_hat` 0.59. `density` averages 0.551, the second-largest
   component loss. §5b reframes this: on the pro side the same kind of gap is
   paid in *coverage*, not row spacing, so "increase density" is the wrong
   remedy — `becker_beanie` is the extreme case here (0.52 of the pro's stitch
   count) precisely because it is the design the pro solidified most.
2. **Over-stitching in the other direction.** `gaulke_roofing_*` at 1.59-1.60x
   the pro's count. Same engine, same config — so whatever is choosing density
   is not choosing it from anything stable.
3. **Stitch direction is near chance.** `direction` 0.073 on the real-art lane,
   0.00 on 11 of 15 designs. This is the single largest recoverable deficit in
   the scorecard and it was invisible before `53e02ae`.
4. **Small text is lost.** `hotel_fremont_*` drops "EST 1895" and
   "EAT | STAY | PLAY" to unreadable marks; `precision_drone` loses "AND
   DRONE"; `gaulke_roofing_*` renders the second text line thin and broken. The
   pro sews all of it.
5. **`tires_hat_3d`'s leading stroke blobs.** The script's entry stroke comes out
   thick and lumpy where the pro's is even. Scored 45.4 with `sttype` 0.00 —
   this design is 3D foam, still unimplemented, so part of that is expected.

## 7. What this changes about the target

The 95/100 target was set against a metric that (a) pays out heavily on two
components the engine is barely above chance on, and (b) on this corpus penalises
correct art reproduction wherever the pro chose to deviate. **42.0 is the honest
number for "how close are our stitches to this pro's stitches, given the
customer's art."** It is not the same question as "is this good embroidery," and
this run is the first time the two have visibly pointed in opposite directions.

What follows, in the order it should be decided. Items marked DONE landed in this
session.

1. **The pro's deviations from the artwork are a capability, not noise — and
   §5b shows the garment drives them.** Fill an outline too thin to sew at size;
   bold up thin strokes; tighten layout to fit a cap front; drop detail below a
   sewable threshold. Seven of fifteen designs turn on exactly those calls, and
   the beanie series puts a number on the target: **+45% solidity at flat row
   spacing**.

   **SUPERSEDED IN PART, same day — see `enclosed-background-verdict-2026-08-15.md`.**
   This item was written as "the largest single lever, not yet started." Both
   halves were wrong. A design session on it established that (a) the mechanism
   is NOT a stroke-width floor — measured, such a rule fires on the designs the
   pro left alone and stays silent on the ones it filled; (b) the real mechanism
   is that the artwork's *transparent enclosed regions* are an intended colour
   the pro stitches and we leave bare; and (c) **that capability already ships**
   end to end, as `shape_overrides[sid]["stitched"]` / contract v1.1. Turning it
   on is worth +8.0 per affected design but only **+2.7 on the corpus**, since
   only the five Becker designs carry material enclosed area. The verdict is not
   to flip the default: the colour an enclosed region inherits is an artifact of
   PNG flattening, and the +8.0 is `coverage` rewarding overlap while `density`
   and `sttype` fall. Item 4 below is the larger lever.
2. **DONE — thread the garment through the harness.** `garment_id` from the
   pro's filename convention. Worth +0.6, +1.2 on cap fronts, +0.0 on every
   left-chest design; moved `travel` and `underlay`, not `coverage`. Exactly as
   §5b predicted. The value was never the score — it was that the corpus had
   been measuring `pique_knit` for cap fronts and beanies.
3. **DONE, by someone else — `direction`/`sttype` off the chance floor.**
   `53e02ae` landed the rescale the 2026-08-14 doc flagged as needing an explicit
   decision. Still open from that list: whether `coverage` should be measured
   against the *artwork* rather than against the pro's stitches. §3 and §5 are the
   argument that it should — 9 of the 53 remaining points are unreachable because
   the reference deviates from the input, and `coverage` is where that is paid.
4. **Stitch direction, now that it is visible.** `direction` 0.073, and 0.00 on
   11 of 15 designs. Worth 20 points and we are at ~0.4 of one of them. This was
   hidden behind the old scale and is arguably a bigger recoverable deficit than
   row spacing.
5. **Then row spacing.** Over-stitching `gaulke_roofing_*` at 1.6x while
   under-stitching `precision_drone` and `tires_hat_3d` at 0.43-0.49, from one
   config, means whatever picks spacing is not picking it from anything stable.
   This is genuinely a spacing problem, unlike item 1.

## 8. Reproducing this

From the repo root, on branch `claude/real-art-parity-and-restore-146`:

```
PRO_PARITY_OUT=<out> digitizer/.venv/Scripts/python digitizer/tools/pro_parity/prep_both.py
digitizer/.venv/Scripts/python digitizer/tools/pro_parity/scorecard.py <out>/real/*/
digitizer/.venv/Scripts/python digitizer/tools/pro_parity/scorecard.py <out>/recon/*/
digitizer/.venv/Scripts/python digitizer/tools/pro_parity/artfidelity.py <out>/real/*/
```

`PRO_PARITY_ROOT` defaults to `G:/My Drive/EMB-Bot/Embroidery Files`. Set
`PRO_PARITY_GARMENT=0` to reproduce the pre-2026-08-15 behaviour where every
design digitizes as `pique_knit`. ~15 minutes for all 15 designs, both lanes.

New instruments:

- `digitizer/tools/pro_parity/real_art.py` — prepares customer artwork. Applies
  exactly one transform (uniform-bar crop, needed because the Gaulke art is a
  phone screenshot with solid black bars that stage 1 would read as foreground).
  Deliberately does NOT remove backgrounds, flatten alpha, sharpen or upscale.
- `digitizer/tools/pro_parity/prep_both.py` — runs both lanes over the 15
  designs.
- `digitizer/tools/pro_parity/artfidelity.py` — the `art_iou` / `pro_extra` /
  `art_missed` instrument. Pro-side only, so its numbers are independent of
  whichever engine is checked out.

Two changes to the existing `prep_all.py`, both of which fix silent
mis-measurement rather than changing what is measured:

- `run_ours` takes an optional `garment_id`, defaulting to `None` so every
  existing caller reproduces its recorded numbers exactly.
- `cfg.fill_density_boost = True` is now guarded by a
  `__dataclass_fields__` check. `PipelineConfig` is a plain dataclass, so on a
  tree without that field the bare assignment set a stray attribute nothing read
  and raised nothing — which is exactly what happened when `a6435f2` removed the
  field. It now prints a warning instead of quietly measuring a different
  configuration than its own comment claims.

`digitizer/.venv` did not exist on Kent's machine and was created per
`digitizer/README.md` §Setup, with the optional `.[service]` extra added (it
clears 9 test failures that are pure missing-dependency noise). The
`tesseract-ocr` system binary is still not installed — 4 OCR tests fail for that
reason and nothing in this run needed OCR.

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
