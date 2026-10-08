# L1, one lettering tagger: built OFF and scored (2026-10-08)

**Status: built default-OFF as `cfg.lettering_words`. No default changed.**
L1 of the lettering-lane architecture
(`docs/lettering-architecture-rd-2026-10-07.md` §5 and §6, item 2). It
addresses failure E, "two taggers". Built from `main` `b7d63ae`. It does
not depend on PR #665: that PR touches the Column lane's pairs and its
determinism, not tagging.

## What was built

`digitizer/digitizer_core/words.py` finds each line of lettering once:

- **One door.** Every region whose box could be a glyph is a candidate:
  aspect 0.05–2.0, height 1–60 mm, skeleton stroke CV ≤ 0.60. Rescued and
  ordinary glyphs are judged alike.
- **One link.** Members must share a size (0.8), a stroke weight (0.5) and
  one ink (ΔE00 ≤ 20), and sit near each other. The link is
  `textcluster._linked`, unchanged.
- **Rows split.** A linked component that sits in two rows is cut at the
  widest gap across its line of text, when that gap is over 0.75 of a cap.
- **Patterns out.** A candidate congruent with five or more others within
  five of its own heights is dropped before words form. Congruent means IoU ≥ 0.8 after
  normalising for position, scale, rotation and mirror. Rope twists and
  border beads are dropped this way. The rest re-link without them.
- **The word model.** Each word carries its members in reading order, the
  line of text and the stems' slant (the house angle's own readings), the
  cap height, the stroke width and its spread, and the baseline. The OCR
  string is joined from the per-member read.

**Under the flag, these readers group by the word:**

| Reader | Grouped before by | Under the flag |
|---|---|---|
| `columns.is_lettering` (the Column lane) | text cluster OR house group | word |
| `satin_lettering_split` ceiling | `text_candidate` | word |
| Cap-skip cover | `text_candidate` | word |
| Bean-letter word | `text_cluster_id` | word |
| Shared stitch width | `text_cluster_id` | word |
| House angle | `_lettering_groups` | word |
| Letterform priors | both | word |

**One reader that changes stitches keeps the text cluster on purpose:**
`regularize_text_clusters`. It runs before the tagger and redraws rescued
members, widening them too when `lettering_min_column_mm` is set, and its
evidence is the rescued population only. So with that floor set, a word
member outside the text cluster (Fremont's P and A) is not widened. The
Studio's text badge, Convert-to-text, the OCR read and the legibility
warning also keep the text cluster; they do not change stitches.

**The letterform priors refit every word member under the flag**, not only
`text_candidate` members. That includes the tagger's own false positives
(two rope twists, three drone scenery pieces, gaulke's window panes). The
fit's own gates may refuse them; gaulke reads byte-identical ON.

## How it was scored (ROADMAP gate 4: chance-corrected only)

**The labels.** `digitizer/testdata/lettering_truth.json` labels eight of
the nine real logos (`tools/thin_strokes.REAL_ART`, Studio's six colours,
corpus sizes). I drew every region with its index over the artwork and
named the letters by eye, line by line. A line is one row of text at one
size.

- **Not letters:** counters, dividers, rope twists, window panes and halo
  crumbs.
- **Letters:** whole-word script regions, such as tires' "ires" and
  bridge's "Bridge". No tagger that groups three glyphs can find them, and
  the score should say so.
- **Ignored (scored neither way):** the screenshot's status bar and title
  bar.
- **Not labelled:** `golden_tee`. Its 3D bevel makes every letter four to
  six stacked slivers, so no letter / non-letter call would be honest.

**The scores.** `digitizer/tools/word_tagger_eval.py` reports two figures:

- **Detection:** Cohen's kappa of "is a letter", per fixture and pooled.
  The pooled figure has a fixture-bootstrap 95% interval.
- **Grouping:** the adjusted Rand index of the tagger's groups against
  the labelled lines, over the regions both call letters.

Shape ids are only valid for the segmentation they were labelled on. When
segmentation renames a labelled shape, the tool marks that fixture STALE
and does not score it.

| Fixture | Regions | Letters | text_cluster κ / ARI | house_group κ / ARI | either κ / ARI | **words κ / ARI** |
|---|---|---|---|---|---|---|
| becker | 17 | 11 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | **1.00 / 1.00** |
| tires | 6 | 4 | 0.00 / – | 0.00 / – | 0.00 / – | **0.00 / –** |
| enthusiast | 31 | 24 | 1.00 / 1.00 | 0.90 / 1.00 | 0.90 / 1.00 | **1.00 / 1.00** |
| fremont | 164 | 33 | 0.83 / 0.94 | 0.34 / 0.94 | 0.32 / 0.94 | **0.94 / 0.95** |
| bridge | 76 | 13 | 0.73 / – | 0.00 / – | 0.73 / – | **0.73 / –** |
| gaulke | 52 | 35 | 0.81 / **0.00** | 0.81 / **0.00** | 0.81 / **0.00** | **0.81 / 1.00** |
| drone | 119 | 24 | 0.84 / 1.00 | 0.89 / 1.00 | 0.84 / 1.00 | **0.93 / 1.00** |
| screenshot | 117 | 35 | 0.98 / −0.02 | 0.64 / 0.00 | 0.64 / 0.00 | **0.92 / 1.00** |

"either" is what `columns.is_lettering` reads today. Pooled over all
fixtures:

| Tagger | Pooled κ [95%] | Mean ARI |
|---|---|---|
| text_cluster | 0.881 [0.801, 0.940] | 0.65 |
| house_group | 0.616 [0.420, 0.858] | 0.66 |
| either | 0.637 [0.435, 0.871] | 0.66 |
| **words** | **0.907 [0.833, 0.945]** | **0.99** |

Paired fixture bootstrap, words' pooled κ minus each other tagger's:

| Against | 95% interval | Verdict |
|---|---|---|
| text_cluster | [−0.030, +0.078] | Level: the interval spans zero |
| house_group | [+0.052, +0.484] | Better |
| either | [+0.023, +0.486] | Better |

The full numbers are in `scores.json`.

**What the numbers say:**

- **Detection is the text cluster's or better.** Fremont's rope gave the
  house group 58 false letters, and the pattern test removes them. Drone's
  THERMAL M, A and L are found; the old 1.4 aspect ceiling had cut the M.
- **The Column lane's reading improves most.** It reads either tagger
  today, and on Fremont and the screenshot that carries the house group's
  false positives.
- **Grouping is the clearest win, on two fixtures.** ARI is only defined
  where a fixture has two or more lines both sides found, and the mean
  moves on gaulke and the screenshot alone (0 → 1); no interval is given.
  Gaulke's two lines and the
  screenshot's two lines were each one group in both old taggers (ARI ≈ 0).
  The row split gives each line its own word. Fremont's EST and 1895 were
  two text clusters and are one line now.

**What it still misses:**

- **Script:** tires 0/4, and bridge's "Bridge". A word that is one region
  is not a group. That needs a different detector, not a gate.
- **Bridge's BAR & RESTAURANT:** five of twelve arc blobs fail the stroke
  screen or the link.
- **Fremont:** two rope twists still ride in the EAT STAY PLAY word.
- **Gaulke:** its four window panes read as a four-letter word. They are
  mirror pairs, so each has one twin, under the pattern threshold.
- **Drone:** three scenery pieces.

## Limits, said plainly

- **The constants are fitted on the same eight logos they are scored on.**
  There is no held-out set. The CV screen (0.60) is the one fitted number
  that matters, and it is thin: the highest labelled letter reads 0.57.
- **The sweep, pooled κ** (each constant moved alone):

  | Constant | Values tried → pooled κ |
  |---|---|
  | CV screen | 0.55 → 0.899 (Fremont's P and A lost), 0.60 → 0.907, 0.65 → 0.884, 0.75 → 0.737 |
  | Line gap | 0.5 / 1.0 → unchanged |
  | Congruent IoU | 0.75 → unchanged; 0.85 → −0.02 |
  | Pattern twins | 4 / 8 → unchanged |
  | Aspect ceiling | 1.4 → −0.005; 1.6 → unchanged; 2.5 → −0.02 |

  ARI stays at 0.99–1.0 throughout.
- **Labels are one person's eye on one render each.** No inter-rater
  agreement exists.
- **The pattern test treats glyphs as congruent under rotation, mirror and
  scale**, so b/d/p/q, n/u, M/W, 6/9 and plain bars are each one shape. It
  counts twins only within five heights, so a letter repeated across a
  lockup survives (MILLION DOLLAR BILLS' six L's: pinned by a test), but
  six of one such family within five heights of each other would be
  dropped. The worst labelled case is four I's.
- **A component under six members is never split into rows**, so a short
  stack ("EST" over "INC") stays one word, and a stack taller than it is
  wide reads its principal axis vertical and does not split either.
- **Reading order:** a line steeper than 45° reads top to bottom whichever
  way its letters face. Nothing reads the order or the baseline for
  stitches yet; L2 and L3 will.

## What the flag does to stitches (through `digitize()`, defaults otherwise)

| Fixture | OFF stitches / trims | ON stitches / trims |
|---|---|---|
| becker, tires, gaulke | byte-identical | byte-identical |
| enthusiast | 2,614 / 15 | 2,604 / 15 |
| fremont | 20,177 / 58 | 20,177 / 58 (points move) |
| bridge | 18,493 / 102 | 18,479 / 102 |
| golden_tee | 8,941 / 45 | 8,972 / 45 |
| drone | 19,353 / 139 | 19,355 / 141 |
| screenshot | 8,341 / 70 | 8,363 / 70 |

The ON changes come through the house angle, the satin split, the cap
skip and the priors now reading the word. Every change is ≤ 0.4% of
stitches; drone pays two more trims (139 → 141). Nothing was rendered for Kent: the flag is a grouping change
whose quality claim is the score above, not a look.

Re-run on the final code (after the review's fixes), 2026-10-08.

## Reproduce

```bash
cd digitizer
.venv/bin/python -m tools.word_tagger_eval                 # the table above (~5 min)
.venv/bin/python -m tools.word_tagger_eval --patterns      # what the pattern test removes
.venv/bin/python -m pytest -q tests/test_words.py
```

## Next, per the architecture's order

- **L2:** run the priors before the house angle. Under this flag they
  already read the word.
- **L3:** the size policy per word. It reads `word_cap_mm` and
  `word_stroke_mm`. Its floor value is gate 1.
- **L1 itself:** a flip is Kent's call. The price is the table above.
