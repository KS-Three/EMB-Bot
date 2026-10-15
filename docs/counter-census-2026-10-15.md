# Counter census: does 0.5 mm separate the true-size switch's wins from its losses? (2026-10-15)

Measure only. No engine change, no flag flipped. The 0.5 mm guard is a ROADMAP gate-1 candidate,
and nothing here was sewn.

## The question

The true-size flip (#955) is replacing its cap-height guard with a counter-width guard. The switch
acts on a line only if the line's smallest counter is at least 0.5 mm across (× thread weight / 40).
A line with no counter passes. This census reads that quantity before the guard is built.

## Method

`digitizer/tools/counter_census.py`. Each design is digitized twice, as the corpus cells run it:

- **main**: the switch off;
- **switch**: `small_text_true_size` + `small_text_keep_stray_lines`, as #955 will ship it.

The designs are the 17 of `tools/small_lettering_compare.py --corpus` plus Fremont's Hat at 65 and
72 mm.

Each text line of the switch run (a cluster that `small_text._core` reads as one line of 3 or more
letters) records:

- **cap height**;
- **min counter**: the smallest inscribed width of any hole in its members, at 40 px/mm. Lines under
  restore's 3.0 mm cap are retraced from the source raster, so for small lettering these are the
  source counters;
- **bean count**;
- **changed**: whether its stitches changed (per-shape digest);
- **verdict**: on Fremont's four words (EST, 1895, THE, tagline), WIN / LOSS / TIE from
  `glyph_legibility`'s OCR glyphs recovered, then legibility (±0.02).

Full table: `docs/renders/counter-census-2026-10-15/table.md`; per-design rows in `census_*.json`.

## Lines with a verdict (Fremont Hat)

| width | line | min counter mm | verdict | guard 0.5 | guard 0.45 |
|---|---|---|---|---|---|
| 65 | tagline | 0.44 | LOSS (OCR 10/11 → 5/11; A apexes fill) | hold ✓ | hold ✓ |
| 65 | date (EST+1895, merged) | 0.45 | not bean; 1895 0/4 → 1/4 | hold | pass |
| 65 | THE (own line since #960) | none | TIE (3/3 both) | pass | pass |
| 72 | tagline | **0.47** | **WIN** (9/11 → 10/11) | **hold ✗** | pass ✓ |
| 72 | 1895 | 0.50 | WIN (0/4 → 2/4) | pass (on the edge) | pass |
| 72 | EST | none | TIE | pass | pass |
| 81 | tagline / 1895 | 0.55 / 0.55 | WIN / WIN | pass | pass |
| 81 | THE / EST | none | WIN / WIN | pass | pass |
| 92.5 | 1895 | 0.65 | WIN | pass | pass |
| 92.5 | tagline | 0.60 | "LOSS" by OCR (11/11 → 10/11) but legibility 0.69 → 1.00 | pass | pass |
| 92.5 | THE / EST | none | WIN / WIN | pass | pass |

## Answers

1. **0.5 mm does not quite separate them.** It holds the one real loss (the 65 mm tagline, 0.44),
   but it also holds a win: the 72 mm tagline at 0.47. It passes the 72 mm 1895 at exactly 0.50.
2. **0.45 separates them on this data.** The only loss is at 0.44 and the smallest win at 0.47.
   That gap is 0.03 mm, about one raster step at 40 px/mm. It rests on one losing line, and that
   loss is itself partly an instrument effect: whole-word OCR reads EAT / STAY / PLAY at 65 mm
   under every arm (#958 thread). So treat 0.45 as the candidate and the evidence as thin. A sew-out
   of the 65 / 72 mm tagline is what settles it (gate 1).
3. **Lines with no counter:**
   - Fremont's THE and EST at every width (win or tie everywhere);
   - Bridge's script line;
   - a screenshot line;
   - Fremont's 3.03 mm THE in the 80 mm logo.
   "No counter = pass" holds on all of them.
4. **The guard needs two scope rules, or it reads noise:**
   - **Speck holes.** Becker's 28 mm and 17 mm letters read min counters of 0.05 and 0.14 mm. Those
     are tracer specks, not counters, and the census marks those lines HOLD. Ignore holes that are
     specks: e.g. an inscribed width under 0.1 mm, or under a few percent of the cap height.
   - **Lines the switch never touches.** Read the guard only on lines the switch would act on (under
     restore's cap, or bean candidates). Becker's lines are unchanged by the switch, so their HOLD is
     harmless, but it is noise in any count.
5. **Unread lines that the 0.5 guard would hold:** `sp_synthetic_2.5` (0.48, changed, no word
   reader). Every other changed line passes either value.

Also seen: a few wordmark lines read "changed" under the switch (Fremont Hat 65 and 81 mm, caps
4.8–6.0 mm, not bean). That is a per-shape digest difference on lines the switch does not sew as
bean; a neighbour's sequencing is the likely cause, and it was not traced here.
