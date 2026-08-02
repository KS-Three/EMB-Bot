# Law 19 — fill row spacing: 0.20 mm or 0.40 mm?

**Verdict: REFUTED.** `machine.FILL_ROW_MM = 0.40` stands. No constant changed.

Law 19 (`digitizer/docs/pro-digitizing-playbook.md:39`) records professional fill
row spacing as **~0.20 mm effective**, against our 0.40. If true, every filled
design we ship is half the density it should be and the fix doubles stitch
counts. It was recorded and deliberately not applied for two days because of one
specific doubt: that the corpus number measures rows *consecutive in sew order*
while ours measures rows *adjacent as generated*, and that those differ by
exactly 2 when the fill is a two-pass interleave.

Both halves of that doubt are now settled by measurement, and the answer to the
second one is not the answer that was expected.

---

## 1. The interleave hypothesis is refuted — and it was pointing the wrong way

Across **427 fill patches in 29 files**, the corpus sews rows in geometric
order:

| test | result |
|---|---|
| `ratio sew-order gap / geometric gap` | p10 = **1.0**, median = **1.0**, p90 = **1.0** |
| patches with ratio in [1.7, 2.3] (interleave signature) | **2 / 427** |
| patches with ≥60 % of steps at ±2 geometric rank | **1 / 427** |
| patches whose median sew-order step is ±1 geometric rank | **423 / 427** |

The two definitions are **the same number** in this corpus. There is no
factor of 2 hiding between them.

The instrument was calibrated on a fill built to be interleaved on purpose, so
this is a real negative and not a blind one — see §4.

**The doubt was also directionally backwards.** Calibration shows interleaving
makes the *sew-order* gap **twice** the geometric gap (a 0.40 fill sewn
alternate-rows-first reads sew = 0.80, geo = 0.40). So if the corpus 0.20 had
been a sew-order reading of an interleaved fill, the true geometric spacing
would have been **0.10 mm — four times denser than ours**, not equal to it.
Interleaving could never have rescued 0.40. That escape hatch was never
load-bearing.

Our own fill is sequential too, confirmed at the call site and by measurement:
`stage6_fill.py:80` places rows at exactly `row_mm` (`y = miny + row_mm*(i+0.5)`)
and `col_points` walks them in geometric order. Measured through the same
instrument, our fill at `FILL_ROW_MM = 0.40` reads geo 0.400 / sew 0.400 /
ratio 1.0 / **coverage 1.00**.

---

## 2. Where the 0.20 actually comes from: it is satin, not tatami

The 0.20 population is real and correctly measured. It is measuring the wrong
object.

A zigzag column's points alternate rails, so **consecutive crossings advance
half a same-rail density**. Calibration, on a synthetic column built at
same-rail 0.40 — an utterly ordinary satin:

```
ZIGZAG COLUMN same-rail 0.40   ->  geo = 0.20   coverage = 2.02
TATAMI        row     0.40     ->  geo = 0.40   coverage = 1.02
```

**A perfectly normal 0.40 satin reads 0.20 through a fill-spacing ruler.** That
is the factor of 2 the doubt was groping for — it is the satin rail half-step,
not a fill interleave.

Three independent things say the corpus 0.19–0.22 population is that object:

- **Coverage.** It carries 1.8–2.3 thread layers, matching the calibrated satin
  reading of 2.02, not the tatami reading of 1.02.
- **The corpus's own satin density.** `study_pro` measures same-rail satin
  density on these same files at **0.40–0.51 mm** by a completely different
  code path (`pts[0::2]` vs `pts[1::2]`). Doubling the measured pitch of the
  dense cluster gives **0.38–0.43** — the mechanism predicts exactly this.
- **The files.** Every dense-cluster file is script/lettering. Dumping the raw
  points of `mom-smile` run 0 patch 0 shows traverses growing 5 → 15 mm from a
  rail **pinned at x ≈ −52 mm**: a fan column, not a 2-D region. `be-joy` patch
  0 is a fixed-width band, traverses running 20.3 ↔ 27.0 mm.

Genuine 2-D area fills — the illustration and sketch designs — run **pitch
0.28–1.00 mm at coverage 0.35–1.12**, i.e. at or below one covering layer.
Our 0.40 (coverage 1.00) sits inside that band.

This also corroborates law 16 from the other side: 0.40 spacing with 0.40 mm
40wt thread is exactly one covering layer, and that is what the corpus's real
area fills do.

---

## 3. Per file, because house style does not average

Median row pitch = `span along normal / (rows − 1)`; coverage = thread length ×
0.40 mm / hull area. `satin` is `study_pro`'s independent same-rail density for
that file. `ilv` = interleaved patches.

| file | n | p10 | pitch | p90 | cover | satin | ilv |
|---|---|---|---|---|---|---|---|
| hope-christmas-inscription | 51 | 0.140 | 0.150 | 0.158 | 2.98 | 0.50 | 0 |
| sweet-heart | 3 | 0.154 | 0.156 | 0.192 | 2.99 | 0.41 | 0 |
| gather | 37 | 0.182 | 0.188 | 0.226 | 2.13 | – | 0 |
| mom-smile | 13 | 0.188 | 0.189 | 1.009 | 1.81 | 0.45 | 0 |
| miss | 7 | 0.189 | 0.191 | 0.210 | 1.90 | 0.41 | 0 |
| hello-summer | 4 | 0.189 | 0.191 | 0.192 | 2.09 | 0.50 | 0 |
| be-joy | 19 | 0.156 | 0.194 | 0.199 | 2.22 | 0.41 | 0 |
| autumn-time | 3 | 0.195 | 0.199 | 0.205 | 2.26 | 0.50 | 0 |
| i-love-pumpkin | 32 | 0.195 | 0.199 | 0.214 | 2.15 | – | 0 |
| little-romeo | 4 | 0.184 | 0.200 | 0.216 | 1.98 | 0.50 | 0 |
| best-friend | 65 | 0.191 | 0.201 | 0.229 | 2.09 | – | 0 |
| boy-mama | 17 | 0.193 | 0.201 | 0.208 | 1.98 | 0.42 | 0 |
| i-love-pets | 10 | 0.201 | 0.210 | 1.258 | 1.86 | 0.40 | 0 |
| hello-fall | 23 | 0.188 | 0.214 | 0.989 | 1.81 | 0.45 | 0 |
| think-positive | 3 | 0.205 | 0.217 | 0.224 | 1.88 | 0.42 | 0 |
| birthday-squad | 9 | 0.209 | 0.262 | 0.273 | 1.65 | – | 0 |
| smile | 16 | 0.231 | 0.268 | 0.353 | 1.60 | – | 0 |
| summer-umbrella | 9 | 0.238 | 0.283 | 0.487 | 1.50 | – | 0 |
| future-mrs | 11 | 0.268 | 0.297 | 0.448 | 1.43 | 0.51 | 0 |
| creative | 1 | 0.342 | 0.342 | 0.342 | 1.12 | 0.41 | 0 |
| bunny-star | 12 | 0.300 | 0.343 | 0.736 | 0.93 | 0.51 | 0 |
| chamomile-love | 15 | 0.275 | 0.396 | 0.423 | 1.08 | – | 0 |
| cat-and-girl-sketch | 7 | 0.400 | 0.458 | 0.947 | 0.88 | – | 0 |
| corgi-sketch | 29 | 0.232 | 0.506 | 0.812 | 0.78 | – | 0 |
| rose-hand | 2 | 0.454 | 0.666 | 0.666 | 0.78 | – | 0 |
| snowman-christmas | 16 | 0.584 | 0.686 | 0.925 | 0.61 | – | 0 |
| christmas-sleigh-reindeer | 1 | 0.833 | 0.833 | 0.833 | 0.53 | – | 0 |
| teddy-bear-vintage-sketch | 3 | 0.767 | 0.997 | 1.001 | 0.35 | 0.82 | 0 |
| *breathe-feathers* | 5 | 0.029 | 0.043 | 0.070 | 3.77 | 0.42 | 2 |

**18 files at coverage ≥ 1.6** (all script/lettering — the satin population),
**11 files at coverage < 1.6** (all illustration/sketch — the real area fills).
This is a genuine bimodal house-style split, not a distribution around a mean.
There is no cluster at 0.20-with-coverage-1.0, which is what "fills are
0.20 single pass" would require.

`breathe-feathers` is italicised because its 0.043 mm pitch is below the DST
0.1 mm quantum and therefore physically impossible as a row pitch — it is an
instrument artefact on that file, and it supplies both of the two "interleaved"
patches in the whole corpus. Excluded from interpretation; named, not hidden.

---

## 4. Method, and why the instrument is trusted

Built from scratch in the scratchpad — nothing imported from the engine or from
`study_pro`, so a bug shared with the subject cannot hide (house rule 5).

- **Patches** are found bottom-up: a *stroke* is a chain of ≥2 long (≥1.2 mm)
  segments turning <30°, i.e. one straight traverse; a *patch* is consecutive
  strokes agreeing in angle within 4°. Patch angle is the circular median of
  per-stroke total-least-squares fits, because a 30 mm row misaligned by 0.2°
  smears the projection by 0.1 mm — half the quantity in dispute.
- **Instrument A, comb** — project every penetration onto the row normal and
  find the lattice period by circular resultant. No notion of a row at all.
- **Instrument B, rows** — sew-order gap vs nearest-neighbour on the sorted
  positions.
- **Instrument C, sequence** — rank rows by geometry, read the sew-order
  visiting permutation. ±1 = sequential, ±2 = interleave. Uses neither spacing.
- **Instrument D, coverage** — thread length × 0.40 mm / hull area. Needs
  neither rows nor sew order, and is the quantity that actually decides
  "are we half density".

**Calibration on constructed objects whose answer is known** (this caught two
real defects — the first version silently split an interleaved fill into two
sequential patches and reported each at the full 2× spacing, which would have
produced a confident false negative on the exact question being asked):

| constructed object | expected | measured |
|---|---|---|
| tatami row 0.40, sequential | 0.40, cov 1.0, ±1 | geo 0.40, sew 0.40, cov 1.02, dRank1 1.00 |
| tatami row 0.20, sequential | 0.20, cov 2.0 | geo 0.20, cov 2.03 |
| tatami row 0.40, **two-pass interleave** | geo 0.40, sew 0.80, ±2 | geo 0.40, **sew 0.80, ratio 2.0, dRank2 0.983** |
| zigzag column same-rail 0.40 | geo 0.20, cov 2.0 | geo 0.20, **cov 2.02** |
| zigzag column same-rail 0.50 | geo 0.25, cov 1.6 | geo 0.30, cov 1.62 (0.1 mm DST quantum) |
| **ours, `FILL_ROW_MM = 0.40`** | – | geo 0.400, sew 0.400, **cov 1.00**, comb R 1.0 |

Reproduce:

```
cd .../needle-hole-guard/digitizer
PYTHONPATH=. .venv/Scripts/python.exe <scratch>/law19_probe.py scratch_corpus/*.dst
PYTHONPATH=. .venv/Scripts/python.exe <scratch>/calibrate.py
PYTHONPATH=".;<scratch>" .venv/Scripts/python.exe <scratch>/ours.py
```

Probes live in the session scratchpad only (`law19_probe.py`, `calibrate.py`,
`dump_patch.py`, `ours.py`, `summarize.py`); nothing was written into the repo
but this document.

---

## 5. What is still unproven

1. **The files that actually drove law 19 are not on disk.** Round 2's strongest
   evidence was the *commissioned cap* files — "gap 0.18–0.19 (p10=p90=0.19!)"
   — naming `PRECISION DRON HAT.DST`, `HOTEL FREMONT (2).DST`,
   `beckers logo hat.DST`. `scratch_corpus/` holds **only the 36 freebie files**;
   those three are absent from the whole repo tree. I could not re-measure the
   very files the law was written from. Everything above is the freebie corpus.
2. **No geometric test separates a wide satin/fan column from a tatami fill of a
   long thin region — they are the same object.** The 0.20 population has the
   satin signature on three independent counts (§2), and one inspected case is
   provably a pinned-rail fan, but I cannot prove *no* file uses a genuine
   0.20 area fill. The dense cluster is interpreted, not proven, as satin.
3. **Thread width 0.40 mm is an input, not a measurement.** Coverage inherits
   law 16 rather than testing it.
4. **Corpus rows are not a clean lattice.** Comb resultant is 0.16–0.28 on
   corpus fills against 1.0 on synthetic and on our own output, so "the" row
   spacing is a distribution, not a constant — medians are reported throughout,
   and p10/p90 are in the table for that reason.
5. **Nothing here was sewn.** Coverage 2.0 vs 1.0 is a geometric claim about
   thread laid per unit area, not a claim about how either looks on fabric.

## 6. What a sew-out would settle

The residual is narrow and the existing gate already covers it:
`docs/sewout-card-2026-07-31.md` decision 2 — **`FILL_ROW_MM` 0.40 | 0.20 | two
0.40 passes offset 0.20**, driven through `cfg.fill_row_mm`, never by patching
`machine.FILL_ROW_MM`. On this evidence the card's 0.20 arm is expected to come
back as visibly over-dense on an area fill (2.1× coverage against preflight's
own 2.5 warn line), and the 0.40 arm to match the corpus's illustration fills.

If the three commissioned cap files can be recovered, re-run §4's probe on them
before the sew-out — they are the only corpus evidence that ever pointed at
0.19, and they are the one thing that could still overturn this.

## 7. Recommended edit to the playbook (not applied — Kent's call)

Law 19's number is not wrong, its *object* is. Suggested restatement for
`digitizer/docs/pro-digitizing-playbook.md:39`:

> **7. Fills.** 2.0–3.4 mm stitches (median ~2.6). Real 2-D area fills run
> **0.28–1.00 mm row pitch (median coverage ~1.0 layer)**; our 0.40 sits inside
> that. The ~0.20 mm figure seen across script/lettering files is the **satin
> crossing half-step** of a 0.40–0.51 mm same-rail column (law 4), not a fill
> row spacing — consecutive crossings advance half a same-rail density because
> points alternate rails. Corpus fills sew rows in geometric order; two-pass
> interleave does not appear (2/427 patches). Stagger irregular, never a rigid
> cycle.
