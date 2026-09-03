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

- **Bold's counter guard (follow-up PR).** The weight rides apart from
  pull comp and is held per rail station where the rail FACES another rail
  of the glyph (`railCloud`/`counterGap`/`stationPush`): whole on an outside
  edge, across a counter only what the gap can spare with the cross floor
  kept, nothing where it is already under. Two-stem probe: 0.72 mm eye
  0.50 guarded vs 0.42; 0.36 mm untouched vs 0.06. Junctions that nearly
  touch hold too (initials_XL at 35 mm caps: 725 stations) — right for the
  thread, wrong word for a note, so there is no Studio line. On hairline
  scripts the guard changes what bold IS: mai_en_fleur's connectors stay
  bean runs (1,393 stitches) instead of becoming dense satin (3,043).

- **Short stitches in the font path (second follow-up PR).** The Python
  `_short_stitch_guard` mirrored into `emitZigzag` with its numbers (0.3 /
  0.35 / 0.6 mm), width-gated by the cross-floor bound (Law 53: Melco's
  "excessively small stitches in narrow lettering" trap), on only with the
  cross floor. geneva S: 43% → 0% of same-rail advances under the trip;
  stitch counts never change. Faces at the floor at 5.5 mm caps keep their
  bunching because the gate refuses the pull — that is the gate working.
  Two underlay tests read rails off the satin's own penetrations and broke
  on the moved points; they now read an unpulled reference layout.

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
- **Tesseract's OpenMP team is why the 60 s service test dies under
  `-n auto`.** Pre vs post under three CPU hogs: 19.3 vs 32.7 s (idle 11.1
  vs 11.9) — ten extra spawns cost 13 s because each child's four spinning
  threads fight for the cores. `OMP_THREAD_LIMIT=1` on the child alone:
  **12.1 s under the same hogs**, faster than pre-change and immune. The
  likeliest root cause of 10ae9cc's CI timeout. Measure under CONTENTION,
  not just idle — idle showed +0.8 s and hid a 13 s problem.
- Memoizing `_skeleton_stroke_stats` on the (immutable, bytes-hashed)
  polygon made the house-angle pass 2.0 → 0.9 s on enthusiast: three passes
  were skeletonizing the same regions.
