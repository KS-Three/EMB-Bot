# Fill coverage inside the shapes — brief for a multi-agent session

**Status: RECONNAISSANCE DONE, no fix attempted, nothing decided.** Kent named
this the front on 2026-08-25 after the first thread renders: *"your
shape/bordering and feature recognition is getting VEERY good ... My main
concern is how the stitching looks within each one of those photos."*

Read this before spawning anything. Two read-only agents already mapped the
mechanism on 2026-08-24/25; everything below is `file:line`-checked. Starting a
team without it means paying for that sweep twice.

---

## The mechanism, settled

**Coverage on the streamline tier is `THREAD_MM / d_sep`. Nothing else.**

```
_d_sep(d) = 3.2 - 2.4 * clamp((d - 0.08) / 0.92, 0, 1)   stage6_streamline.py:300-305
```

| darkness | d_sep (mm) | 0.4 / d_sep |
|---|---|---|
| 1.00 (black) | 0.800 | **0.500** |
| 0.50 | 2.104 | 0.190 |
| 0.08 (cutoff) | 3.200 | 0.125 |
| < 0.08 | — | **0.000** — nothing sews |

`STREAMLINE_D_SEP_DARK_MM = 0.8` (`stage6_streamline.py:147`) is commented
*"Two thread widths"*. **So 0.50 is a hard analytic ceiling at pure black, by
construction.** There is no second pass, no underlay, no crossing pass
(`stage7_sequence.py:114-118`: the meander/scanline/streamline/sketch tiers
sew no underlay — *"fabric-as-value is those tiers' whole point"*).

**The blend tier reaches 0.99 for one reason:** `machine.FILL_ROW_MM = 0.40`
(`machine.py:49`) equals `stitchviz.THREAD_MM = 0.4` — rows sit edge to edge,
one full covering layer. Corroborated at
`docs/law19-fill-spacing-2026-08-02.md:65` (`TATAMI row 0.40 -> coverage 1.02`).

**There is no density lever exposed to a caller on the streamline tier at
all.** `cfg.fill_row_mm`, `fabric.density_adjust` and `cfg.fill_density_boost`
never reach it; the module's only `cfg` reads are `shade_axis_normalize`,
`chart_for`, `fill_angle_deg`, `streamline_mode`, `debug_dir`.

## Three findings the sweep produced that were NOT already written down

1. **On real photos the blend tier is not doing shade decomposition — it is
   doing plain tatami.** `blend_fill` tries `detect_ramp_detail` and, when no
   ramp survives the gates, calls `stitch_shape` at `FILL_ROW_MM`
   (`stage6_blend.py:601-605`). Its own comment: *"This is the branch EVERY
   k-means fragment of a real gradient actually takes, not an edge case ...
   all 23 regions fall back here."* So the 0.99 column is ordinary tatami, and
   the sophisticated blend path is largely theoretical on this corpus.

2. **Layered mode makes the shade TRANSITION BANDS the sparsest cloth in the
   design**, and this is nowhere documented as a coverage effect. The auto
   photo route is always layered (`pipeline.py:760`, `:1052`). In layered mode
   `d_sep` is driven by each shade's *coverage share* (a triangular tent), not
   by tone (`stage6_streamline.py:519-684`, `:872-875`). A pixel midway
   between two shade centres has both at ~0.5, so both layers draw at
   `d_sep ≈ 2.10` — and because each `_trace_streamlines` call builds its own
   fresh `_SampleGrid` (`:377`), the two layers are placed independently and
   partly overlap. Combined, that is LESS thread than the mono tier would lay
   at the same tone.

3. **`coverage()` is a design-wide number, not a streamline-only one.** Since
   a single Jobard–Lefer set cannot exceed 0.50, the measured 0.55–0.59 must
   include non-streamline thread — needle-down travel bridges up to
   `STREAMLINE_TRAVEL_MAX_MM = 8.0` (which lay real thread and render as
   thread), satin borders, bean detail runs, and tatami fallbacks for
   all-highlight shapes. **Measure streamline blocks in isolation before
   attributing any change.**

## Gate-1 triage — READ BEFORE PROPOSING A CONSTANT CHANGE

ROADMAP gate 1 names *"fill row spacing"* explicitly and is a refusal, not a
preference. Of the coverage-determining constants:

- **`STREAMLINE_D_SEP_DARK_MM = 0.8` — GATE 1.** Justified as "two thread
  widths", the same family as `machine.SATIN_SPACING_MM = 0.4` and
  `FILL_ROW_MM = 0.40`, both corpus-measured. Do not touch without a sew-out.
- **`STREAMLINE_D_SEP_LIGHT_MM = 3.2` — WEAKER CLAIM.** Justified only as
  *"4x the dark end, the same light:dark ratio the scan-line tier's stride
  ladder spans"*. That is house consistency, not a measurement.
- **`STREAMLINE_CUTOFF_DARKNESS = 0.08` — WEAKER CLAIM.** Justified only as
  *"Matches the scan-line tier's cutoff"*. Also not a measurement.

The two weaker ones are where an honest experiment can live without a sew-out.
Say so explicitly in any proposal rather than lumping all three together.

## What is NOT the question

- **Not "raise the density".** On a tier whose premise is exposed fabric that
  may just produce a bad fill instead of a sparse one.
- **Not "widen `PHOTO_CLASSES` to include gradient".** Kent explicitly rejected
  that 2026-08-24 — `gradient` is also the class for genuine gradient logos.
- **Not answerable from any sheet before 2026-08-24.** They were vector proofs
  and cannot show coverage at all.

## The real question, and it may be a product question

Should a photo sew as *fabric-as-value thread-paint* (0.55) or as a *filled*
design (0.99)? Both are legitimate embroidery. The tier is currently chosen by
`auto_photo_tier` (`pipeline.py:93-122`) with no coverage consideration and no
user say. **The defect may be the absence of the choice, not the value of a
constant.** That is Kent's call and should be put to him with renders of the
same photo both ways — which is now possible and was not before.

## LANE A IS KENT'S CALL — start there (2026-08-25)

He picked it on the spot when the brief was put to him: **"COPY, lane A it
is."** So lane A is not a suggestion to weigh against the others; it is the
chosen next step, and re-opening that choice is re-litigating a decision.

Why it is the right first move, restated so nobody has to reconstruct it:
every other lane spends effort moving numbers, and one of those numbers sits
behind ROADMAP gate 1. Lane A spends no constants at all. It renders the same
photo as thread-paint and as a filled design and asks Kent which product a
photo should BE. If the answer is "filled", lanes C and D are largely moot and
the work becomes tier selection. If the answer is "thread-paint", the 0.55 is
not a defect at all and defect 14 closes as a documentation gap. **Either
answer redirects the other three lanes, which is why it goes first.**

Concretely: `forced_class="photo_subject"` gives the streamline route;
`fill_technique` set explicitly beats `auto_photo_tier` for every class
(`pipeline.py:119-121`), so an explicit `"tatami"` on the same photo is the
filled comparison. Render both with `stitchviz`, put them side by side at the
same scale, and send them to Kent. Nothing else is needed to answer it.

## The lanes

Each is independently ownable; give each its own worktree. **A first.**

| lane | question | first file |
|---|---|---|
| **A** | **CHOSEN.** Render the same photo through streamline vs forced tatami/blend, side by side in thread. Which product should a photo be? | `tools/acceptance_ab.py` |
| B | Isolate streamline-only coverage from travel/satin/detail contamination — is the real streamline number 0.50 or lower? | `digitizer_core/stitchviz.py` |
| C | The layered-mode transition-band sparsening (finding 2). Is it a defect or intended? Measure it. | `stage6_streamline.py:519-684` |
| D | Do the two weak-claim constants (`D_SEP_LIGHT`, `CUTOFF_DARKNESS`) have a defensible non-sew-out experiment? | `stage6_streamline.py:149-157` |

**Worktree setup** (a container is ephemeral — create these fresh each session):

```bash
git worktree add /home/user/EMB-Bot-<lane>-wt -b claude/<branch> origin/main
# a worktree has no .venv; run its suite with:
cd /home/user/EMB-Bot-<lane>-wt/digitizer && \
  PYTHONPATH=$PWD /home/user/EMB-Bot/digitizer/.venv/bin/python -m pytest -q -n auto
```

*(reconnaissance 2026-08-24/25 — two read-only agents, every claim file:line
checked; no code changed, no constant touched, nothing decided)*
