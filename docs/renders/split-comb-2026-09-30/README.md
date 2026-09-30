# The split comb is a property of the column — Becker's lettering under three split rules (2026-09-30)

Kent's pick after the envelope's sibling rule (PR #577): the split satin on
Becker's letters flickers. At 100 mm the six satin letters of MARINE sew
columns 5–7 mm wide, straddling `SPLIT_SATIN_ABOVE_MM` (5.0), and the
engine split leg by leg — a 5.1 mm leg with a mid-column penetration, the
4.9 mm leg after it raw. Numbers in `census.json`; every leg count below is
per LEG (a cross and its return leg are each split on their own length).

## What was flickering

**Becker at 100 mm, the engine after PR #577.** 68 satin runs, 4,222 legs,
1,078 split (26%), 25 runs mixing split and raw legs, **122 on/off
changes** of the split state along the runs; 584 legs within half a
millimetre of the threshold. The letters: 22 runs, 1,412 legs, 1,029 split
(73%), 18 mixed, **59 changes**, 443 legs in the band. The N's stem runs at
a median 5.4 mm with p10 5.1: every few legs one dips under 5.0 and sews
raw between two split ones.

**What the pro did with the same letters.** The five professionally sewn
Becker files in `testdata/reference` (24,108 satin legs, columns by
`tools/study_pro.classify`): legs p50 2.50, p90 4.90, p99 6.91 mm; split
share **1–2% up to 5.5 mm, 8% at 5.5–6, 17% at 6–7, 32% at 7–9, 78% above
9**. Inside the 40 columns that split at all, legs between one segment and
the threshold are split 1% of the time. Becker's own digitizer sews raw
crosses to about 7 mm and combs nothing — the "beckers logo hat sews raw
crosses to ~6" house style `machine.py` already records beside the
corpus-wide 5.0 vote (53% split at 5.0, 65% at 5.5, 92% at 7.0).

## The rules tried

Add-only, so no leg ever sews longer than the threshold (the invariant
`test_wide_crosses_split_and_stay_under_the_threshold` pins), simulated on
the shipped run, on/off changes after (legs newly split):

| rule | design | letters |
|---|---|---|
| shipped, per leg | 122 | 59 |
| majority of five neighbours | 85 (+28) | 40 (+17) |
| per-run median | 103 (+136) | 40 (+136) |
| **hysteresis: the comb stays on while legs are at least one segment long** | **35 (+402)** | **24 (+184)** |

The majority filter fills isolated holes and leaves every stretch boundary;
the per-run median cannot help a run whose median sits under 5.0 with a
wide half. The hysteresis is the statement of the thing itself: a comb is
a property of the column, not of each leg.

## The rule shipped

`_comb_thresholds` (`stage6_satin.py`, read once per column before the
first point is written): once a leg over `SPLIT_SATIN_ABOVE_MM` turns the
comb on, it stays on for every following leg at least `SPLIT_SEGMENT_MM`
(3.0) long, and it starts at the first leg at least one segment long
before that; a leg under one segment is where the column has narrowed to
a single stitch, and the comb ends. An over-threshold leg keeps its own k
(`ceil(len / segment)`, the same k either way); a leg between one segment
and the threshold inside the comb gains one penetration, staggered with
its neighbours; a leg under one segment never splits. `split_satin=False`
(threshold inf) never turns the comb on, and a column with no leg over the
threshold is byte-identical.

**Measured on the tree:** Becker 122 → **37** changes (the letters 59 →
26), 1,078 → 1,479 split legs, 8,932 → 9,333 stitches (+4.5%); tires 21 →
5 (2,646 → 2,835), bridge 20 → 5 (16,085 → 16,175), screenshot 8 → 3
(8,161 → 8,201); golden_tee 4 → 4 and unchanged, enthusiast, fremont and
gaulke have no leg over the threshold and are byte-identical. The two
changes the simulation did not predict are the seam hops between a joined
stroke's members, which keep the per-leg rule.

## For Kent's eye

Each strip is one letter of MARINE at 100 mm three ways — **per-leg split
as shipped | the column comb | raw to 7 mm (the pro's Becker style,
`split_satin_above_mm=7.0`)** — with the thread render on top and, below
it, every needle penetration as a dot. **The thread renderer barely shows
a mid-column penetration** (a filament continues through it with a break
in the shading), so the page renders Kent judges cannot tell these three
apart; the holes are what the cloth shows, and the dots are them.

- `becker100_E_Sf1c25fcd.jpg`, `becker100_N_Sdd5f27fb.jpg`,
  `becker100_A_S5a3cd301.jpg`, `becker100_R_Sa587cbf9.jpg`.
- Shipped: the holes run down a column as an interrupted line, on for a
  few legs and off for one. Comb: continuous staggered lines of holes down
  every column wider than one segment. Raw to 7: almost no mid-column
  holes at all, the widest legs only (8 changes on Becker, 8,292 stitches).

## What this leaves to Kent

Two house styles are both real in the corpus, and the engine now sews the
5.0 one without flicker. The pro who sewed Becker's own files kept the
other: raw crosses to about 7 mm, 8,292 stitches against the comb's 9,333.
Raising the threshold is a constant with cloth behind it (a 6–7 mm stitch
floats or it does not, on pique or on a cap), so it is a sew-out question
under gate 1, and a ruling of Kent's, not a measurement's.
