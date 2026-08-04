# M0 — running `shape_lens.py`, the measurement DT-first sequencing calls for

Status: **Unit-fixture + real-art + timing + taper legs DONE** (this session,
2026-08-04). **Corpus leg (37 `scratch_corpus/` files) BLOCKED** — that data
is gitignored and local-only (`CLAUDE.md`: "Gitignored means 'not in git
history,' not 'safe to delete'"), and this remote session's checkout has
`scratch_corpus/` empty. Needs Kent to run one command locally (below).

## What M0 actually was

Per `docs/dt-first-architecture-2026-08-01.md` §2 and
`docs/superpowers/plans/2026-08-03-dt-first-sequencing.md`: instrument only,
zero engine change, zero golden impact — measure the current
`2*area/perimeter` satin-vs-fill call against distance-transform statistics
sampled at skeletal pixels (the patent-record method), on the fixture logo
and the professional corpus, and report where they disagree.

**The instrument already existed.** `digitizer/tools/shape_lens.py` (commit
`70a14e8`, 2026-08-02, already on `main`) is not a stub — it has the full `dt`
table, nine candidate rule arms (`R1`/`R2`/`R2n`/`R3`/`MIN`/`MIN2`/`VAR`/
`P90`/`VP90`), a `corpus` command against professional `.dst` files, a
`taper` sweep, and a `timing` cost measurement. What was missing, per
`docs/hardening-closeout-2026-08-02.md`'s own audit two days after it landed:
*"Nothing is wired in... The commit is two uncollected files"* — built,
never run to completion, never reported. This session ran it.

## Unit fixtures (21 adjudicated synthetic shapes) — and a cap change that matters

`PYTHONPATH=. .venv/bin/python tools/shape_lens.py dt --ablate`

```
confusion vs stated truth, satin = positive, cap = machine.SATIN_MAX_WIDTH_MM (5.0 mm, current):
  arm       TP  FP  TN  FN   wrong
  ribbon     9   6   6   0   6/21   <- shipped engine today
  R1         9   3   9   0   3/21
  R2         9   1  11   0   1/21
  R2n        9   1  11   0   1/21
  R3         5   1  11   4   5/21
  MIN        9   1  11   0   1/21
  MIN2       9   0  12   0   0/21   <- perfect
  VAR        9   2  10   0   2/21
  P90        9   1  11   0   1/21
  VP90       9   0  12   0   0/21   <- perfect
```

**Before trusting that table, a real discrepancy had to be reconciled.**
`MASTER_SCOPE.md` already carried a verdict on this exact tool from
`docs/hardening-closeout-2026-08-02.md`: *"the dt-first recommendation
(VP90) is worse than the shipped rule at main's actual cap... do not
land."* That finding is real and reproduces exactly — but it was measured
at `SATIN_MAX_WIDTH_MM = 3.0`, which was `main`'s value on 2026-08-02 and
is **not** the current value. `machine.py`'s own history shows a later,
unrelated, corpus-driven change (little-romeo/beckers width study) moved
the shipped cap from 3.0 to 5.0 — already merged to `main` before this
session started. Re-running the audit's exact command confirms both
numbers, at each cap, to the digit:

```
--cap 3.0 (the OLD shipped value, main on 2026-08-02):
  ribbon   wrong 4/21     VAR   wrong 1/21     VP90  wrong 5/21   <- VP90 clearly worse
--cap 5.0 (the CURRENT shipped value):
  ribbon   wrong 6/21     VAR   wrong 2/21     VP90  wrong 0/21   <- VP90 clearly better
```

VP90's 5 misses at cap 3.0 (`C_STROKE 3 wall`, `T_SHAPE 3 wall`, `WEDGE
1->5`/`2->4 over 30`, `BAR 40x4.8`) are all shapes whose 90th-percentile
width sits just above 3.0 mm but under 5.0 mm — genuinely satin, but the
`p90 <= cap` term wrongly rejects them at the tighter cap and stops
wrongly rejecting them at the wider one. This is a real, cap-sensitive
result, not noise or a stale re-run: **the audit's "do not land" verdict
was correct for the cap it measured, and the ground under it moved for an
unrelated reason.** The honest conclusion is not "VP90 is vindicated" —
it's that the verdict needs re-measuring against the corpus at today's
actual cap (5.0) before it can be trusted either way; a 21-shape synthetic
set is exactly what the audit already demonstrated is too small to settle
this alone. `MASTER_SCOPE.md` is being corrected to say this, not to
reverse the verdict.

The shipped rule's 6 misses at cap 5.0 are all **false positives** (0 false
negatives — it never calls something fill that should satin, on this set):
`WEDGE 1->9 over 30`, `SERRATED disc r10 t0.6`/`t1.2`, `BAR 40x5.2`,
`SQUARE 4x4`, `SQUARE 8x8`. Every one is exactly the failure mode the
architecture doc predicted — `2*area/perimeter` mistaking a fattening
wedge, boundary-serrated noise, or a compact blob for a uniform ribbon.

## Real artwork — the "garment defect" reproduces exactly

The hardening-closeout audit's independent finding reproduces to six digits
in this run:

```
logo_whitebg/Sb253ebba   2A/P 5.03   dtmax 9.50mm   ribbon=fill   (.)
logo_whitebg/Sf5200f3f   2A/P 5.02   dtmax 9.60mm   ribbon=fill   (.)
logo_alpha/Sb253ebba     2A/P 5.00   dtmax 9.50mm   ribbon=SATIN  (Y)
logo_alpha/Sf5200f3f     2A/P 5.00   dtmax 9.50mm   ribbon=SATIN  (Y)
```

`logo_alpha.png` and `logo_whitebg.png` are the same design, different file
encodings (`test_alpha_and_opaque_variants_agree_on_the_artwork` pins their
foreground masks to within 98% IoU) — yet the shipped classifier sews the
**same shape as a satin column on one file and a fill on the other**, purely
because `2*area/perimeter` lands on opposite sides of the 5.0 mm cap by
antialiasing noise between formats (4.997 vs 5.033). Every DT arm (`dtmax`
~9.5 mm either way) calls this shape `fill` on **both** files — the DT
statistic doesn't care which format the customer happened to upload.

(3 of the 7 `default_art()` real-art fixtures — `serif_text`, `curved_ribbon`,
`nested_colors` under `debug_out/cases/` — aren't present in this checkout
either; `debug_out/` is gitignored and apparently generated by a prior
session's own tooling run. Not blocking — `logo_whitebg`, `logo_alpha`,
`bg_uncertain`, and `ribbon_curve` (14 regions total) were available and are
the numbers above.)

## Cost — `timing`

```
stages 1-4, logo_whitebg.png @80mm:                          1140.3 ms (6 regions)
current classify (2A/P + aspect), all regions:                  0.105 ms =  0.009%
DT @20px/mm, ALL regions (full DT-first restructure):         265.14 ms = 23.251%
DT @20px/mm, only regions the CURRENT rule already calls satin: 20.36 ms =  1.786%
```

A full DT-first restructure (every region gets a medial-axis pass before the
satin/fill call) costs a real ~10-23% of stages 1-4 depending on grid
resolution. The "add-a-term" arms (`MIN`/`MIN2`/`VAR`/`P90`/`VP90` — the
shipped rule decides first, DT only refines shapes it already called satin)
cost ~1.5-1.8%, because stage 6 already pays for a medial axis on exactly
that subset today — this is work moved earlier, not new work. Resolution
sensitivity (p90 width across 6/10/20/30 px/mm grids) spreads 0.03-0.23 mm,
well under any plausible decision margin.

## `taper` — where the variance rule alone gives up

Matches the closed-form prediction in the tool's own docstring: `2*sigma <
mu` (the "uniform thickness" half of Goldman's rule) stays satisfied for a
linear wedge taper up to `b/a ≈ 13.93` — i.e. a shape whose width varies
nearly 14x along its length still reads as "regular" on variance alone. This
is exactly why the recommended arms (`VP90`, `MIN2`) pair the variance term
with a width term (`p90` or `max`) rather than relying on regularity alone.

## What's still blocked

The architecture doc's corpus leg — `shape_lens.py dt --ab` / `corpus`
against all 37 professional `.dst` files in `scratch_corpus/` — needs data
that is gitignored and not present in this remote checkout (0 `.dst` files
found; `CLAUDE.md`'s own footgun list already warns "gitignored means not in
git history, not safe to delete," which cuts both ways — it also means this
session cannot conjure it). **Kent needs to run this locally, at the
CURRENT cap** (the flag matters — see the cap-3.0-vs-5.0 finding above,
`--cap` defaults to `machine.SATIN_MAX_WIDTH_MM` so plain default is fine
now, but say so explicitly since the last run at the old cap is exactly what
went stale):

```bash
cd digitizer && PYTHONPATH=. .venv/bin/python tools/shape_lens.py corpus scratch_corpus/ --against VP90
# sanity check the cap it's actually using, first line of output prints it:
PYTHONPATH=. .venv/bin/python -c "from digitizer_core import machine; print(machine.SATIN_MAX_WIDTH_MM)"
```

and hand the output back for M0 to actually close out per the architecture
doc's original spec ("run it over all 37 corpus files"). Everything else M0
asked for is measured above.

## Where this leaves M1 / M2 / M3

Per the sequencing doc, M1 (hoisting `ShapeField` — mask, skeleton, exact
EDT computed together, behind `cfg.extra["shapefield"]`, byte-identical
output required) is next, and does not need the corpus leg to proceed — it's
a pure refactor with no classifier change. M2/M3 (actually swapping the
classifier) is corpus-gated **and** sew-out-gated per the sequencing doc, and
does need the corpus run above before it can be judged — this session's
unit-fixture and real-art numbers are suggestive (`VP90`/`MIN2` at 0/21
wrong at the current cap, cheap when added as a term) but are the same
class of small-synthetic-set evidence the 2026-08-02 audit already showed
can flip entirely with a cap change. Whoever runs M2/M3 needs the corpus
table at today's cap before treating this session's numbers as more than a
lead worth chasing.
