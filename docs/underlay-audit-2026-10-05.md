# What a professional sews under a large fill — the audit, 2026-10-05

Follow-up to [`underlay-research-2026-10-05.md`](underlay-research-2026-10-05.md)
§3, which read a crossing underlay pass off the commissioned files with a
classifier its author flagged as unvalidated, against corpus law 26
(`corpus-laws-round3-2026-08-01.md:281-294`), which says the opposite. An
independent audit validated the classifier on ground truth, corrected it, and
ran it on every readable professional file. Scripts, ground truth and renders
are in the session scratchpad, not the repo; the per-file outputs carry
customer folder names and stay out of it.

Labels: **[M]** measured in the audit · **[D]** read in a repo doc ·
**[I]** inference.

## Verdict

**The research note is confirmed and was understated. Law 26, as a rule for
large fills, is refuted on the commissioned files and holds only on the
third-party free corpus.** Both readings are right about different
populations; the split is by who digitized the file, not by fill size.

| source | large top-density fills | with a crossing sparse pass |
|---|---|---|
| tracked `becker_*` (5 DST) | 10 | 10 |
| commissioned set | 36 | 34 |
| `Test Files` (provenance unknown) | 61 | 21 |
| third-party free corpus | 35 | 4 |

"Large" is at least 1,500 mm of dense thread at a top pitch under 0.30 mm.
[M] The commissioned set is one house style, so the honest n is folders, not
fills: 8 of 9. The two exceptions are one folder and are not clean tatami.

## The pass, measured [M]

Commissioned large fills, n = 34, min / p10 / p50 / p90 / max:

| | |
|---|---|
| row pitch, mm | 0.75 / 0.94 / 0.98 / 0.99 / 1.00 |
| stitch length, mm | 3.05 / 3.51 / 3.99 / 4.02 / 4.02 |
| angle to the top fill, ° | 82 / 88 / 89 / 90 / 90 |
| share of the top fill's thread, % | 7.7 / 11.3 / 16.1 / 19.7 / 21.2 |
| fill area within one row pitch of the pass | 0.66 / 0.76 / 0.94 / 0.99 / 0.99 |

- The research note's ~1.0 mm, ~4 mm and ~90° stand. Its thread share (~13%)
  was low: the median is 16%.
- By area the pass is in 24 of 24 fills of 300–1,000 mm² and 15 of 15 over
  1,000 mm²; 17 of 22 at 100–300 mm². Underlay rows under 4 mm are invisible
  to the classifier, which is the likely cause of the lower small-fill figure
  [I]. No area threshold was fitted.
- **An edge run is NOT reliably part of this digitizer's recipe**: at most 11
  of 34 (an upper bound; the edge-run detector had 5 false positives in 74 on
  ground truth). Our shipped knit preset is the reverse — edge run, no pass.
- Seven commissioned layers at 0.48–0.50 mm pitch over 2,400–4,000 mm² carry
  no crossing pass. They read as knockdown-type base layers, not top fills
  [I]; the research note had counted most of them as bare fills.
- `Test Files`, where it has a pass, uses a different recipe (pitch p50
  1.72 mm, 8% thread share), so it holds other digitizers [I].

## The classifier, on ground truth [M]

154 cases sewn with `stage6_fill.stitch_shape`, written to DST and PES by the
`/export` writer and read back as bare streams: eight shapes × seven underlay
styles, pro-like constants, and adversarial negatives (two-pass density
boost, crosshatch, two top angles, travel under cover, a sparse layer sewn
AFTER the fill, satin with zigzag underlay, knockdown).

| | crossing pass found (of 62) | false positives (of 65 with none) |
|---|---|---|
| the research note's classifier, as written | 18 | 1, and 80 of 154 files read "not a fill" |
| audit copy | 62 | 0 |

What was wrong with the original: it needed a reversal over 120° between
consecutive stitches, which our tatami never has; it judged a colour block,
not a fill; and its 0.9 mm "sparse" bar sat on the professional's 0.94–1.00 mm
pitch and dropped about half his rows. All three made it UNDER-count.

## Law 26's instrument [D, I]

Not recoverable. The round-3 doc says its probes "live in scratchpad, not in
the repo" (`:726-736`); none survive. What the doc records: 507 "fills" with
no size cut across 36 third-party DSTs and 4 commissioned files, "sparse-grid
tatami underlay: n=7". Two things in the record cut against it:

- the same law reports ~27% of fills carrying a "zigzag" whose angle to the
  top has p90 86° — which is what a perpendicular sparse pass looks like;
- a probe from the same week on the same corpus
  (`research-partials-2026-07-31.md:392-454`, validated on a planted fixture)
  found a grid under 42% of fills, "strongly perpendicular", and that
  "commissioned fills all carry full stacks". The synthesis replaced it
  without reconciling the two.

A surviving tool of the same family, `tools/census_pro.py::_phases`, labels a
known `edge_lattice` fill and the Becker crossing pass as plain running [M].
Whether law 26's instrument did the same cannot be known.

## Not checked

- Garment or fabric per file — stitch files carry none, so nothing here says
  the pass is knit-specific.
- Any effect on cloth. Whether 1.0 mm rows at 16% thread help or pucker on
  pique needs a sew-out.
- 14 `.EMB` and 2 `.dsb` files in the commissioned tree: unreadable by
  pystitch. An EMB carries the digitizer's own underlay setting and would
  settle this without inference.
- The JS engine as ground truth.
