---
name: pro-overlay-first-run-2026-09-11
description: "First real run of the pro overlay loop (prep_both.py / overlay.py / diff.py) on three real designs — becker_lc_large (iou 0.643), becker_hat_large (iou 0.650), hotel_fremont_patch (iou 0.983) — every Becker fill/satin tier mismatch and fill angle confirmed against MASTER_SCOPE's satin_columns.py findings, the Fremont lettering-width expectation refuted, no score emitted"
metadata:
  type: reference
---

Full record: `docs/pro-overlay-first-run-2026-09-11.md`. Renders: `docs/renders/pro-overlay-2026-09-11/`.

## What worked and what did not

- **The loop is what Task 5-12 built it to be: prep, overlay, diff, three catalogues, no score.** `prep_both.py becker_lc_large becker_hat_large hotel_fremont_patch` prepped both lanes in 43.3s/38.8s/151.4s (all near the 45s/45s/175s estimate); `overlay.py --by-thread` and `diff.py` ran clean on all three, registering iou 0.643/0.650/0.983 (Becker's lower iou is the arch-banner "BECKER" text itself departing from the flat logo, not a registration failure — Fremont's flat patch geometry registers almost exactly).
- **Every flagged row on both Becker designs belongs to either "BECKER" or "MARINE"** — no unattributed flagged rows. Both spell out the same defect: our engine sews fine fill/tatami (0.19-0.41 mm) where the pro sews wide satin columns (2.26-5.20 mm), confirming MASTER_SCOPE's `satin_columns.py` finding (2.2% vs 44.3% share of penetrations in satin) qualitatively, though this catalogue reports per-region tier, not that percentage. The pro's fill-tier angle clustered 20-24° on both designs, confirming "the pro holds about 20 degrees" (`DOCTRINE`, 2026-09-09 fill-angle entry).
- **One spec expectation was REFUTED, not confirmed.** Fremont's "HOTEL FREMONT" lettering columns measure pro 1.30-1.50 mm / ours 0.70-0.80 mm — the opposite of the spec's stated "pro 0.82-0.90 mm where we sew bean runs" (ours is narrower, not wider; only 3 of 16 letter regions fall back to a non-satin tier at all). Read the width off the region's OWN `width p50` column, not an assumed number — the same trap DOCTRINE already names for `satin_columns.py`'s whole-plan row.
- **Three rulings shaped what the catalogue can say:** segment-midpoint pass assignment (no thread vanishes at a chunk boundary, R16), sub-3-point fragments excluded from the tier/width ratio not just the accounting (R17), and every shape row carrying `sewn_by` so `redesign`'s two opposite buckets (pro adding thread vs. pro leaving/merging ours) read apart (R18). All three are load-bearing for reading this run's tables correctly.
- **Registration caveat: Fremont's dust rows are large and mostly noise, not defect.** 1,799 pieces / 67.6 mm² of `redesign` dust and 3,291 pieces / 528.0 mm² of `dropped` dust come from the patch's fine rope-cord texture and small serif digits fragmenting under pixel-level comparison — read the two non-dust `redesign` rows (the EST/1895/rope band and the tagline band) as the real signal, not the dust counts.
