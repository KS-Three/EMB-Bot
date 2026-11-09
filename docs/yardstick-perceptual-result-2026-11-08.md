# Perceptual yardstick vs Kent's eye: the pre-registered run (2026-11-08)

The one run that [`yardstick-perceptual-prereg-2026-11-08.md`](yardstick-perceptual-prereg-2026-11-08.md)
committed to, read once against the claim rule written there.

**Result: the claim holds.** DreamSim agrees with Kent's picks above chance:
3-way kappa **+0.197**, 95% interval over pairs **[+0.07, +0.32]** (over designs
[+0.10, +0.29]), n 100, against `mse`'s **+0.053**. Both halves of the rule are met:
the lower bound is above 0 and DreamSim beats mse's point kappa.

No flag, route, default or phase moves on this. It licenses a proposal to Kent,
nothing more (prereg, "What is read").

## The figures

`tools/yardstick_perceptual.py score pairs.csv --labels --oracles`, shipped defaults,
`scores.csv` md5 `5735a8311ed0b26903e7f8000a180caf` (212 rows: 200 pair rows + 6 self
+ 6 blank oracle rows). Kent decided 41 of the 100 pairs; the other 59 are his ties
(`same` 39, `both_bad` 20). No raw agreement share is computed (ROADMAP gate 4).

| metric | kappa 3-way (ties in, n 100) | CI pairs | CI designs | reading | kappa 2x2 (n both decided) | CI pairs |
|---|---|---|---|---|---|---|
| **dreamsim (primary)** | **+0.197** | [+0.07, +0.32] | [+0.10, +0.29] | above chance | +0.432 (40) | [+0.11, +0.70] |
| mse (control) | +0.053 | [-0.08, +0.19] | [-0.06, +0.21] | no evidence | +0.049 (39) | [-0.24, +0.35] |
| lpips_vgg | +0.211 | [+0.09, +0.33] | [+0.06, +0.38] | above chance | +0.457 (40) | [+0.16, +0.72] |
| lpips_alex | +0.092 | [-0.04, +0.22] | [-0.00, +0.21] | no evidence | +0.167 (40) | [-0.13, +0.45] |
| flip | +0.042 | [-0.09, +0.17] | [-0.11, +0.22] | no evidence | +0.069 (40) | [-0.21, +0.34] |

Oracles: every metric reads 0 on the self row. "Blank is worst" holds for mse and
DreamSim, and FAILS for flip, lpips_alex and lpips_vgg (a blank canvas scores closer
to some reference than a real pair does); all five pass it within the same reference.

## How far to trust it

- **lpips_vgg is a lead, not a second claim.** The prereg says one secondary
  clearing is a lead for a second labelled sitting. It also fails the blank oracle,
  which weakens even that.
- **"Beats mse" is a point-kappa pass, not a separation.** DreamSim's interval
  overlaps mse's. The rule asked for the point comparison, and that is what passed.
- **Pairs are not independent.** Pairs within a design share one "before" render
  (drone's 18 pairs share one), so the pairs interval is optimistic. The
  design-clustered interval, [+0.10, +0.29], is the honest one, and it also clears 0.
- **Weighting.** The shipped kappa is linear-weighted with tie as the middle
  category; the prereg says "Cohen's kappa" and "shipped defaults". Unweighted, DreamSim
  reads 0.141 and mse 0.078: still ahead, by less. Its interval unweighted was not
  computed.
- **Registration** is weak on becker and golden_tee (IoU about 0.64): a quality caveat
  on those pairs, not a prereg clause.
- **Same direction as the eye sessions.** Claude-as-the-eye read +0.36 on 99 of these
  pairs (memory `vlm-judge-100-2026-11-06`); DreamSim is lower but on the same side.

## Compliance with the pre-registration

Checked by two independent read-only agents after the score existed.

- **Settings:** `report.json` reads ppm 12, pad 3, max-px 1024, registration on,
  monochrome, tie-band 0, dreamsim ensemble, B 10,000, seed 20261107, oracles on. Equal
  to the defaults; nothing was overridden.
- **Instrument:** `tools/yardstick_perceptual.py` and `digitizer/tools/eye_pairs/` diff
  clean against main `15b0f5a0`.
- **Render trees:** the 11 trees in `render.log` are exactly the 9 `SITTINGS` trees plus
  the 2 reference trees in `pro_pooled_build.py`; none extra, none missing.
- **Renders:** 143 started, 143 done, no error. Well under the 10% partial threshold.
- **Kappa re-computed** from `scores.csv` without the tool's own kappa code: every point
  kappa within 0.001, intervals within 0.01.
- **Two things to know:**
  1. The first `from-pro-pooled` build skipped 19 Bridge pairs: run from a scratchpad
     worktree, the pro-file lookup could not walk up to Kent's `Bridge Logo` folder. It
     was rebuilt with `EMB_BRIDGE_PRO` pointed there, giving 100 pairs / 0 skipped, at
     16:25, about 40 minutes before any score existed (scores first written 17:04). No
     setting or label changed. The prereg's "left out, never imputed" clause covers
     render failures; this was a path, and is fixed rather than left out.
  2. The render started at 13:37, about 4.5 minutes before the prereg commit
     (`be3f4d36`, 13:42). Renders carry no score, and the settings fixed in the prereg
     are the scorer's, so nothing was seen before it was committed.

## Reproduce

Renders are gitignored (pro-file content, Kent 2026-10-27). On Kent's laptop, with the
yardstick venv (`tools/requirements-yardstick.txt`):

```bash
python -m tools.eye_pairs.pro_pooled_build render --runs <R>   # from digitizer/
# the next two from the repo root
EMB_BRIDGE_PRO="<...>/Embroidery/Digitized Designs/Bridge Logo" \
  python -m tools.yardstick_perceptual from-pro-pooled --runs <R> --out <R>/pairs.csv
EMB_BRIDGE_PRO="<...>/Embroidery/Digitized Designs/Bridge Logo" \
  python -m tools.yardstick_perceptual score <R>/pairs.csv --labels --oracles --out <R>/score
```

`scores.csv` md5 above is the check.
