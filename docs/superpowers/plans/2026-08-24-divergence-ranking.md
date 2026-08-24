# Where EMB-Bot diverges from the pro — a ranked decomposition

**Date:** 2026-08-24
**Instrument:** `digitizer/tools/pro_parity/blockcensus.py` (landed PR #225)
**Status:** measurement complete; no engine change proposed by this document.

This is the follow-on to `2026-08-23-region-identification.md`. That document
diagnosed region identification from the pipeline's own internals and named four
hypotheses. This one points the element instrument at every genuine artwork
fixture and asks a different question: **of the total disagreement with the pro,
what fraction sits where?**

The short answer is that two of the three dominant divergences fit none of the
four hypotheses, and the largest single fix named by the earlier diagnosis
(option B, grouping) moves the headline number by exactly zero. Both are
developed below.

## Ceiling first — gate 4

Every kappa here is read against a *measured* ceiling, never against 1.0.

| pair | kappa | what it is |
|---|---|---|
| independent pro-vs-pro, same logo | **0.826–0.889** | two professionals, same artwork |
| one job saved twice (self-test) | 0.995–1.0 | instrument noise floor |
| `becker_hat_vs_chest_small` | **0.652** | the *same pro* re-blocking one logo |

That last row is the load-bearing one. A professional re-blocking their own logo
for a different placement disagrees with themselves at 0.652 — so a fixture of
ours reading near 0.65 is at human-disagreement level on that artwork, not
failing.

## Fixture table

kappa (raw/chance), region IoU, and block structure:

| fixture | class | kappa (raw/chance) | reg_iou | ours | pro |
|---|---|---|---|---|---|
| hotel_fremont | gradient | **0.390** (.54/.245) | .967 | 55r → 5b/3t/2ret | 11b/3t/8ret |
| drone_thermal | gradient | **0.426** (.49/.115) | .869 | 67r → 20b/14t/6ret | 23b/8t/15ret |
| becker_marine | flat | **0.641** (.77/.371) | .597* | 17r → 1b/1t/0ret | 4b/2t/2ret |
| golden_tee | gradient | **0.748** (.80/.201) | .612* | 38r → 14b/13t/1ret | 7b/3t/4ret |
| script_tires | photo_scene | 1.0 DEGENERATE | .912 | 6r → 1b | 2b — excluded |

`r` = our regions, `b` = blocks, `t` = threads, `ret` = thread returns.

Median 0.53 across the four non-degenerate fixtures, reproducing the PR #225
headline.

\* The low region-IoU on becker and golden is **not** frame misregistration —
dx,dy ≤ 0.6 mm and the extents match. It is genuine footprint difference: the
pro sews surface the artwork does not have. The instrument cannot tell these two
apart on its own; the dx/dy-plus-extent check is what separates them.

## Ranked divergences

Shares are of total joint-domain disagreement, 3,012 mm² across n=4.

### D1 — One base-field region per design carries 43–88% of all disagreement

Not the region soup. The background.

| fixture | region | area | share of disagreement | kappa if fixed |
|---|---|---|---|---|
| hotel_fremont | k0 (white badge ground) | 2100 mm² | 1159/1316 mm² | 0.390 → **0.933** |
| drone_thermal | k0 (dark ring + panels) | 1015 mm² | 752/971 mm² | 0.426 → **0.875** |
| becker_marine | k0 (grey arch) | 579 mm² | 203/469 mm² | 0.641 → **0.808** |
| golden_tee | k34 (white ground) | — | 60/256 mm² | 0.748 → **0.809** |

### D2 — Same-thread block splits: 38.6% of all disagreement (1,162 mm²)

The pro sews one thread as several separate blocks — becker as
`[black, grey, black, grey]`, hotel as 11 blocks across 3 threads, drone as 23
across 8. Our regions can only land on one of them, so the instrument scores the
rest as misses.

Exact counterfactual, "forgive same-thread confusion": 0.641→0.807, 0.390→0.616,
0.426→0.699, 0.748→0.792 — **median 0.53 → 0.75**.

This also explains the unhit-block roll. Of 14 blocks we never hit:

- **12 are repeats of a thread we did hit elsewhere**
- 1 is a buried sliver (the pro's own later blocks cover 92% of it)
- **exactly 1 is a genuinely missed thread** (drone b5, 168-grey, 48 mm²,
  swallowed by the dark fusion)

### D3 — Craft rewrite of the artwork (~35–38%, estimated split)

- **becker**: the source artwork is *literally one colour plus alpha* — a single
  RGB (35,31,32) at every non-transparent pixel. The pro invented a grey second
  thread covering the majority of the ink, inverted the knockout (positive
  letters over a continuous panel), and layered returns. All 266 mm² of becker's
  cross-thread error is this one decision.
- **hotel**: the pro's black visible surface is 846 mm² against our art-faithful
  534 (bolder redraw); tan 359 against our 137 (we drop the thin rope and
  taglines); plus re-typeset glyph offsets — our black text regions
  majority-land on the pro's WHITE, dE 93 from their own assignment.
- **golden**: the pro flattened the gold-gradient "GOLF" and dropped the red
  accents — 3 threads where the art genuinely has more.

### D4 — Merge across soft boundaries (drone only, ~166 mm² plus a share of D1)

The one clean H1 case. drone k0 fuses black (0,0,0) against dark grey (41,49,51)
work that the pro cuts — dE 7–11 boundaries, soft render gradients. Exactly the
"guard blind to defocus" mechanism the earlier diagnosis described.

### D5 — Phantom palette (golden mainly)

golden sews 13 threads against the pro's 3; 10 have no pro counterpart within
dE00 10, carrying 554/1313 mm² (42%) of sewn area but only 71/256 mm² of
disagreement. drone: 3 phantom threads, 20 mm², ~0 minority. hotel: no phantoms,
but our tan is dE 19.7 from the pro's chosen tan — thread-choice divergence, not
segmentation.

### D6 — Confetti is kappa-irrelevant

Regions under 40 mm² are 53/55 (hotel), 62/67 (drone), 28/38 (golden) of region
*count* but only 10% / 1.5% / 14% of disagreement *area*. Their real cost is
machine structure: our trims-per-1k run 7.4–9.7 against the pro's 0.5–1.4, and
cut paths 39–104 against 9–31.

### The existence gap the kappa cannot see

Pro ink we leave bare is 6–19% per fixture — the pro's solid tan band, extended
grey panel, fatter strokes. It falls outside the joint scoring domain by
construction, so it is reported here separately rather than folded into any
number above.

## Against the four hypotheses

- **H1 (merge above the one-thread line)** — supported **only** on drone's dark
  fusion, plus small golden straddles. Not the main driver anywhere else. And
  the fix is not the threshold, which measured negative on a plateau, but
  boundary-evidence-aware merging.
- **H2 (split residue as connected components)** — present as confetti counts,
  but 1.5–14% of disagreement. Real for machine cost, marginal for kappa.
- **H3 (L\* quantile boundaries)** — **unattributable on this corpus.** The only
  fixture that actually runs `TONAL_REGIONS_SPLIT` is the degenerate one. The
  instrument cannot measure H3 here. Recorded as unmeasured rather than guessed.
- **H4 (phantom colours)** — confirmed on golden (10 threads, 42% of area), but
  worth ≤0.08 kappa even if made perfect.

**Fits none of them — the finding.** The two dominant divergences are outside
the hypothesis set entirely:

1. **Same-thread layering splits (38.6%)** — a block-structure property that no
   region segmentation can express, however good.
2. **The pro's craft rewrite (~38%)** — invented colour on monochrome art,
   figure-ground inversion, bolder and re-typeset detail, palette flattening.

On becker the whole gap reduces to those two, and our 0.641 sits at the pro's
own re-blocking noise for that very logo (0.652).

## Fix ranking by measured leverage

1. **Depth-split base layer.** Sew the ground continuous under detail and split
   base-field regions across blocks in background→detail→background order.
   Measured ceiling: **median 0.53 → 0.75** (exact counterfactual, n=4); rescues
   12 of 14 unhit blocks; manufactures true thread returns (pro 55% headline,
   ours 0–6 incidental shade repeats including one machine-pointless adjacent
   stop, hotel `[0,1,2,2,1]`). Cost: option B's "weeks, largest blast radius"
   plus a depth-split design the earlier diagnosis never scoped. No gate applies
   — no physical constants, no default-OFF tier flip.
2. **Soft-boundary merge discrimination** (H1's real fix). drone-only on this
   corpus; upper bound 0.426→~0.87 if k0 were fully fixed at thread level, but
   realistically far less — estimated +0.05–0.10 on the median. Its value beyond
   the median is the portrait/defocus problem. Threshold retune stays
   measured-negative and is not proposed.
3. **Logo palette discipline / input normalization (option C).** golden 13→~3
   threads, −42% phantom area; **kappa gain ≤ +0.08 on one fixture, ~0
   elsewhere.** Its value is structure — stops, spools, trims — not kappa.
4. **Thin-detail coverage** (hotel tan 137 vs 359, black 534 vs 846). Governed by
   the effective part floor at 2.25 mm², the satin width floor, and pull comp.
   **Gate 1 applies: reporting position only, proposing nothing.**
5. **Colour-role controls (option D).** The only home for becker's invented-grey
   class. A human decision; no engine kappa in it.

## The single highest-leverage change, with its counter-argument

**The depth-split base layer.** 38.6% of all measured disagreement is same-thread
block confusion; the exact counterfactual takes the median from 0.53 to 0.75 —
over half the distance to the ceiling — and it is simultaneously the only change
that touches returns, layering order, and the unhit-block roll.

**Strongest argument against it:** `grouping_join` already grants best-case
grouping, so **option B as specced (grouping only) moves this kappa by exactly
zero.** The +0.21 lives entirely in the *splitting* extension, which is unscoped
extra design. The counterfactual assumes pixel-perfect splits at the pro's block
boundaries, while the pro's own two saves of one job disagree at 0.652 on
precisely that structure — so a real implementation likely lands well short of
0.75, and part of what it chases is one digitizer's re-blocking idiosyncrasy,
the phase-1 conformance trap ROADMAP already names.

Practical consequence: if plain option B lands and only the kappa median is
watched, it will read as no progress. The wins would surface on the census's
return, layering, and blocks axes instead.

## Instrument limits that bound every conclusion above

- The join is **colour-blind** — allocation geometry only. A black region of ours
  "agrees" with a pro white block if it majority-assigns there (hotel k5–k7).
  Majority-vote binarization also makes fine interleaved detail (golden
  white-on-black b4/b5) score all-or-nothing.
- Kappa's domain excludes pro ink we leave bare (6–19%) and our ink off pro
  (1–8%).
- H3 is unmeasurable on this corpus.
- becker's "the pro invented grey" is relative to the committed PNG. The
  delivery zip holds only stitch previews and encrypted `.EMB`, so what artwork
  the pro actually received is unverifiable. See the provenance correction in
  `.claude/memory/real-artwork-trim-truth.md`.

## Assumptions not readable from the code

1. Thread identity is RGB tuple equality (matches the census's own `uniq`
   construction).
2. "Phantom thread" = dE00 > 10 to every pro thread; "confetti" = under 40 mm²
   (from `TONAL_SPLIT_MIN_PART_MM2`'s documented intent); unhit-taxonomy
   "buried" = under 25% visible share. All three cutoffs were chosen for this
   analysis, not inherited.
3. The D3 sub-split (bolder vs re-typeset vs band-undersew) is judged from
   per-block histograms and renders, not a pixel-classified measurement.
4. becker's and golden's low region-IoU is read as content difference rather
   than misregistration, on the dx/dy≈0 plus matched-extent evidence.

## Reproducing

```bash
cd digitizer
.venv/bin/python -m tools.pro_parity.blockcensus ceiling
.venv/bin/python -m tools.pro_parity.blockcensus join --only becker_marine
```

The per-fixture decomposition ran from an instrumented replica calling the
committed instrument's own functions (`census_design`, `grouping_join`,
`paint_*`, `scorecard.register`), cross-checked digit-for-digit against
`blockcensus join --only becker_marine` (0.641/0.774/0.371) and against the
earlier committed-tool run on golden_tee (0.748). The replica lived in a
scratchpad and is not committed; the numbers above are what it produced.

**Memory note.** One fixture per process. golden_tee was OOM-killed once while a
10.5 GB acceptance-sheet run was live and succeeded on a memory-gated retry —
the same stage-2 footprint defect that killed 11 arms of the 2026-08-24
acceptance sheet outright. See MASTER_SCOPE defect 10.
