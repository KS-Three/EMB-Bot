# Ruling re-check — do the standing rulings survive an honest renderer?

Two of Kent's standing rulings were decided by eye on acceptance sheets, and
those sheets were drawn by the **pre-2026-08-25 renderer, which had no light in
it**. Every stitch got the same flat core down its centre regardless of
direction, so a sparse design drew as tidy hatching instead of as the bare
cloth it is. Kent's own words on seeing one: *"It feels like i'm looking at an
image made up of vectors and not stitches."*

That matters more than it sounds. **The instrument was flattering one arm of a
comparison** — the sparse one. So the rulings needed re-checking against the
fixed renderer before anyone leaned on them again.

These are the scripts that did it. They exist because the entries they support
in `MASTER_SCOPE.md` ("RE-VERIFIED 2026-08-26") are worth nothing without the
means to re-derive them.

## Running

```bash
cd digitizer
.venv/bin/python tools/ruling_recheck/fill_ab.py            # all four fixtures
.venv/bin/python tools/ruling_recheck/fill_ab.py owl_kent.jpg
.venv/bin/python tools/ruling_recheck/border_ab.py
```

Output goes to `$RR_OUT` (default `/tmp/ruling_recheck`). Roughly 20 s per arm.

## What each answers

**`fill_ab.py`** — the Lane A ruling, *a photo sews FILLED, not as thread-paint*.
Renders both arms per fixture at 16 px/mm, labelled with the class each arm
actually ran under. The two arms are exactly as the fill-coverage brief defines
them, and the filled one is **not** selectable by config: an explicit
`fill_technique="tatami"` reads as "no choice made" and loses to the auto route
(`config.py`'s sentinel trap), so the filled arm is "let it classify on its own".

Measured 2026-08-26 — filled / thread-paint coverage:

| fixture | filled | thread-paint |
|---|--:|--:|
| `owl_kent` | 0.991 | 0.594 |
| `photo_sunset_backlit` | 0.994 | 0.547 |
| `photo_dof_meadow` | 0.991 | 0.544 |
| `drone_render` | 0.516 | 0.364 |

**Verdict: the ruling holds, and holds harder than when it was made.** Lit, the
thread-paint arm reads as bare fabric between strokes rather than as texture.

**`border_ab.py`** — the border ruling, *significant AND smooth, never blanket*.
Three arms on `owl_kent`:

| arm | stitches | vs off | recorded |
|---|--:|--:|--:|
| off | 11,370 | — | — |
| `significant` (shipped) | 11,845 | **+4.2%** | +4% |
| blanket `auto` | 18,138 | **+59.5%** | +60% |

**Verdict: reproduces.** Lit rendering also makes the "worsens the silhouette"
claim plainer — blanket wraps every shape in a heavy rim so the bird reads as a
cut-out, while `significant` spends its 4% on the eyes.

## What these scripts do NOT settle

- **Faces.** The four family portraits that overturned the fill ruling for faces
  are not committed, so this kit cannot re-check that half from a clean
  checkout. #248's face finding still rests on pre-fix renders. It is probably
  unaffected — features dissolving into a flat skin field is a quantization
  outcome, not a lighting one — but that is reasoning, not measurement.
- **Anything about how it SEWS.** These are renders. ROADMAP gate 1 stands.
- **Coverage is blind to shape.** It cannot see a tilted column or a rounded
  corner — see `../letterform_fidelity/README.md`, which is the whole lesson of
  the letterform investigation.

## The trap that made this safe to do at all

`stitchviz.coverage()` is measured BY RENDERING. Restyling the draw would have
rewritten every coverage figure on record — it happened twice during the
renderer fix before the split was right. `coverage()` now renders `lit=False`,
which reproduces the pre-shading draw exactly, so the numbers above are
comparable to ones recorded before the change. Verified bit-identical on four
stitch angles. Full account in `COOKBOOK.md`.
