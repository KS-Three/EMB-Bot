---
name: word-tagger-l1-2026-10-08
description: L1 of the lettering lane BUILT OFF as `cfg.lettering_words` (words.py) -- one tagger, scored on hand labels of 8 real logos; pooled kappa 0.907 vs text cluster 0.881 / house group 0.616 / either 0.637, line ARI 0.99 vs 0.65; rope out by congruent twins, rows split by gap
metadata:
  type: project
---

# L1, one tagger (2026-10-08)

**Built:** `digitizer_core/words.py`, `cfg.lettering_words` default OFF. Under
the flag the lettering readers group by `word_id` (is_lettering, satin
split, cap skip, bean word, stitch width, house angle, priors -- which then
refit every word member). The rescued redraw keeps the text cluster on
purpose. Kappa is LEVEL with the text cluster (paired CI spans 0); constants
fitted in-sample; ARI gain is two fixtures. Studio badge / OCR / rescued redraw / legibility keep the text cluster.
Doc: `docs/word-tagger-2026-10-08/README.md`.

**Instrument:** `tools/word_tagger_eval.py` + `testdata/lettering_truth.json`
(shape ids at b7d63ae, corpus sizes, max_colors 6). Kappa for detection,
ARI for lines, fixture bootstrap. A fixture whose labelled ids vanish is
reported STALE, never scored -- re-label it by drawing regions with indices.

**What moved the score, in order:** (1) a row split across the line (gaulke
and screenshot: two lines were ONE group in both old taggers, ARI 0);
(2) the pattern test -- Hu-moment "diversity" did NOT work (rope 0.96 vs
BECKER 0.91), congruent-twin COUNT within 5 heights does (rope median 10-14,
letters max 3; counted over the whole component it would drop a lockup's
repeated letters -- reviewer caught it); (3) CV screen 0.60 (fitted, thin: highest letter 0.57).

**Traps:** a line angle is an axis: 179.9 deg reversed reading order until
the direction was oriented rightward. Cap height off centroids reads ~3% high
(T sits high, L low). Running full `digitize()` ON/OFF on nine logos takes
~25 min on 4 cores.

**Still misses:** connected script (one region is not a group), bridge's arc
blobs, gaulke's window panes (mirror pairs, 1 twin each). Flip is Kent's.

**Pairs drawn same day** (`docs/eye-pairs-2026-10-08/`, `lettering_words` arm,
sitting `words-1008`): 5 pairs, 3 identical; golden_tee's tee shaft turns
(false-positive word). Page gitignored, built locally per the README recipe.
