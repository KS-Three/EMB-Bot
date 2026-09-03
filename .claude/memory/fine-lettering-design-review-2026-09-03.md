# Fine-lettering design review (2026-09-03)

Kent's spot check: an "Embroidery 101" write-up on digitizing fine lettering
against the engines. Full record: `docs/design-review-fine-lettering-2026-09-03.md`.

## What it settled

- **The write-up is Laws 45–58.** Nothing in it was new to the project; the
  gaps were in enforcement. Seven half-built rules found; Kent chose three
  plus the underlay rung.
- **Defect 24's mechanism is fixed in BOTH engines**: a hairline STRETCH of
  a stroke (crosses under `SATIN_MIN_CROSS_MM`, at least three bean stations
  of spine) sews as a 3-pass bean along its spine instead of vanishing.
  Python: `satin_stroke(parts=...)` hands `satin_shape` satin/run/satin
  parts per stroke; JS: `splitByCrossFloor` + `beanFromGeom`. Fremont's
  2.6 mm "THE" reads. The TIER question (does a 0.5 mm bean read better on
  cloth than a dropped bar) is card block 5 and stays open.
- **A whole-stroke fallback cannot work** on Goldman-joined strokes: each
  member keeps its junction crosses, so the T's bar never reads as "all
  under the floor". The split has to be per station.
- **A bean earns its place only where the ART has ink.** Pull comp grows a
  0.04 mm vectorization needle into a 0.44 mm "stroke" whose spine clears
  the run floor (Fremont: a dark tick above the hexagon band, invisible in
  the source). Stretches are trimmed while the cross measured in the
  UNCOMPENSATED polygon is under `simplify_tol_mm`. That floor took Fremont
  from +276 to +12 stitches — most of what the fallback "found" on real art
  was compensation-grown nothing. Python-only: fonts have no vectorizer.
- **No satin underlay under a 5 mm extent** (`SATIN_UNDERLAY_MIN_EXTENT_MM`,
  the JS `UNDERLAY_CAP_MIN_MM`). Kent gated it without a sew-out.
- **Convert-to-text sees ordinary lettering** — the third attempt after
  `10ae9cc`'s revert, and each revert reason is answered: e2e asserts per
  cluster (reads the bar's "N shapes"); the shield star is out on a one-ink
  CIEDE2000 link (`TEXT_CLUSTER_DELTA_E_MAX` 20: within-word quantization
  needs ≤ 16.4, star 34.2, grey-vs-orange lines ≥ 27.7 — thread IDENTITY is
  disproven, and the inter-glyph GAP is measured dead: the star sits 0.97
  heights from its word while ENTERPRISES INC's own word space is 1.56);
  cost measured directly — enthusiast +0.9 s, drone +2.9 s, the 60 s service
  test at 12.4 s solo.
- **Two doors, two ROUNDS is the safety argument, not a flag.** The rescued
  door clusters first and alone with its old bounds, so every cluster that
  regularizes is computed by unchanged code; the letter door clusters the
  rest at the house-angle height ratio (0.8) and is never redrawn.

## Traps hit

- The JS "warn only" approval: a per-cross drop alone leaves the survivors
  joined by CHORDS across the glyph on an outline face. Went one step past
  the wording (bean run) and said so.
- `python script.py` from a pre-change worktree imports the MAIN tree's
  package when the script lives elsewhere: `sys.path.insert(0, os.getcwd())`.
  Every "pre == post" I read before that fix was bogus.
- `-n auto` plus probes plus renders on four cores: the 60 s service test
  reads `running`, and the suite takes 27:42 instead of 9:38. Measure cost
  on a QUIET box, solo, before believing a timeout.
- `pgrep -f <name>` inside a background command matches the command's own
  shell. Use a script file.
- vitest hook timeouts while pytest runs are the documented load artifact.
- **A thread pool over pytesseract is a measured NEGATIVE**: four
  concurrent tesseract processes each open their own OpenMP team and thrash
  four cores — enthusiast's 24-glyph OCR pass went 3.3 s → 21.8 s. Serially
  `OMP_THREAD_LIMIT=1` changes nothing (129 vs 132 ms/glyph). Left serial
  with the numbers in the comment.
- Memoizing `_skeleton_stroke_stats` on the (immutable, bytes-hashed)
  polygon made the house-angle pass 2.0 → 0.9 s on enthusiast: three passes
  were skeletonizing the same regions.
