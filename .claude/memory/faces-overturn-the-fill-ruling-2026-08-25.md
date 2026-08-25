# Faces overturned the ruling three PRs were built on — 2026-08-25 (evening)

**Read this before proposing any tonal or border work.** The day answered a
product question confidently on an owl and two landscapes, shipped three PRs on
that answer, and then the first human face inverted it.

## START HERE — Kent's decision, made 2026-08-25 before a /clear

**BUILD THE AUTO-DETECT ROUTE.** He chose it explicitly. The design is settled
and measured below; nothing about it is an open question:

1. Read EXIF camera Make/Model at decode.
2. Use the YuNet detector that ALREADY RUNS (`stage1_photo_prep.detect_faces_seam`).
3. Default `cfg.is_photographic` from EITHER signal.
4. Keep the explicit declaration as the fallback for the residual case — a
   stripped photo with no people in it, which is exactly what `owl_kent` is.

**It is a shipped-default change**: photographs start getting the palette bind
and preflight's photo yardstick automatically. Kent wants to see the first
renders land rather than discover it, so show him before treating it as routine.

Two more of his calls the same evening: MASTER_SCOPE stays at 809 lines against
its 800 budget (it was 865 that morning — the budget did its job), and his four
family portraits were DELETED from the container at his request. **They are gone.
Any face work needs him to re-attach them to chat first** — git is barred by
spec decision 6 and Drive corrupts binary silently.

## The shape of the day, which is the lesson

Kent opened with "what would you do if I said 'A'?" — a live referent: lane A of
`docs/superpowers/plans/2026-08-25-fill-coverage-team-brief.md`, which he had
already chosen. Lane A asked whether a photo should sew as thread-paint (~0.55
coverage) or filled (~0.99).

**The brief's own recipe for answering it did not work**, and that is worth
knowing because the same trap is still live one field over. It said an explicit
`fill_technique="tatami"` beats `auto_photo_tier`. It does not:
`pipeline.py:119` reads `explicit = (cfg.fill_technique or "tatami").lower() !=
"tatami"`, so `"tatami"` IS the default sentinel and never reads as explicit —
both arms render streamline, silently, and the natural misreading is "the
difference doesn't matter". **What works: do not force the class.** Let the photo
classify on its own (it lands `gradient` or `photo_scene`), and
`cfg.fill_technique` survives as tatami. Corrected in the brief.

Filled won decisively on `owl_kent` and two landscapes. Kent: *"the left image is
WAAAAAAAAYYYY BETTER."* Three PRs followed.

**Then four real family portraits arrived and inverted it.** Filled quantizes a
face to one flat skin field: the eyes and nose disappear entirely, and on the
adult portrait the person vanished altogether, leaving a floating flag shirt on
a brown ground. Thread-paint rendered both as recognisable people at 3-4x the
trims. **The mechanism is the subject's own contrast** — an owl's features ARE
distinct colour regions and survive quantization; a face's are continuous
low-contrast tone and do not. Kent tabled faces: *"a little too challenging at
this stage... table it for later when the tool gets more powerful."* TABLED on a
capability blocker, explicitly NOT a non-goal.

## What survived the faces, and why that matters more than what didn't

Every MECHANICAL result held. The border gate's 3.5 raggedness cutoff landed in
a real empty gap on all four portraits (3.46→3.53, 3.31→3.68, 3.29→3.65,
3.44→4.26) despite having only ever seen a bird. `is_photographic` brought every
portrait inside `max_colors` (20→10, 19→12, 25→12, 20→12) and lifted every grade
(F/0 → F/10, D/52, D/40, C/64). **A threshold that survives the population it was
least tested on is worth more than one never challenged** — but note it was the
PRODUCT judgement that failed, and it failed because the fixtures were never the
content the business sells against.

## "Is this a photograph" — declared today, but detectable, and I got this wrong first

Stage 0 CANNOT answer it from colour. Real photographs are the **lowest**
`unique_color_mass` content in the whole corpus — below every gradient logo:

    portrait_two_faces_sky   0.0230     summit_badge  (LOGO)  0.1152
    portrait_adult_shirt     0.0267     drone_render  (LOGO)  0.1592
    portrait_child_closeup   0.0586     owl_kent             0.1107
    portrait_sparkler        0.0686

All four portraits classify `gradient`. Re-tuning that gate cannot work and
would be stage-0 recalibration (gate 2) besides.

**But I wrote "cannot be detected" into a standing ruling and that was too
strong.** Kent asked "why do we need check boxes?" and the answer is that two
signals the repo ALREADY SHIPS separate them cleanly, neither a colour statistic:

| signal | real photos | logos / art |
|---|---|---|
| EXIF camera Make/Model | 4/4 | 0/9 |
| YuNet `stage1_photo_prep.detect_faces_seam` | 4/4 (1,1,1,2) | 0/9 |

The face detector is a real CNN, already wired, already deterministic. Blind
spots: **EXIF dies on re-save** (`owl_kent` is a real photo with ZERO tags) and
faces miss pets and landscapes. EXIF-or-face covers everything here except a
stripped photo with no people — which is exactly `owl_kent`. **Design: auto-detect
with `cfg.is_photographic` as fallback, never a checkbox as the primary
mechanism.** Not built. Building it makes photos get the palette bind
automatically — a shipped-default change Kent should see land.

## Traps this session hit or found

- **`git worktree` + agents.** Six read-only agents in ONE checkout: one ran
  `git checkout` "just to compare" and reverted a colleague's committed work
  into the index. The memory already warned about this and it happened anyway.
  Give writing agents a worktree; forbid git state commands in the prompt
  explicitly, by name.
- **The decode ceiling is service-only.** `DECODE_MAX_SIDE_PX = 2800` lives in
  `digitizer_service/app.py`, NOT in `digitizer_core`. A direct `run_stages()`
  call on a raw phone photo gets no protection, and 7.4 MP is exactly what
  OOM-killed the service at 13.9 GB. Mirror it in any direct-call harness.
- **Acceptance photos come through CHAT, nothing else.** git is barred (public
  repo, spec decision 6) and Drive corrupts binary silently. They survive a
  container restart but not a `/clear` of the knowledge of what they are.
- **`cv2.imread` applies EXIF rotation; PIL's `.size` does not.** Phone photos
  preview sideways in chat and decode upright in the pipeline. Not a defect.
- **MASTER_SCOPE's line budget makes you destructive if you chase it.** I
  deleted a live defect to hit 800 and had to restore it, and paraphrased a
  gotcha losing the 42.5 baseline the file's own banner cites. Compact by
  MOVING, verify by grep that the target already carries what you drop, and
  report over-budget rather than cutting something in force.

## Two defects found in my own shipped code, both by outside pressure

Neither was found by re-reading my own diff. **An adversarial review lane found
that `BORDER_SIGNIFICANT_AREA_SHARE` INVERTS with design size** — inert at the
80 mm it was tuned on, and at 160 mm it deleted 8 of 9 borders at 4.2-62.3 mm²
(iris and nostril scale). A fixed share gets stricter as a design grows, because
stage 2 resolves more regions and every share shrinks. Disabled to 0.0;
significance now lives downstream in `border_runs` against the corpus-measured
`BORDER_WIDTH_MM`. **And a thin smooth ring was refused a border** because
whole-shape raggedness summed every ring's perimeter over hole-subtracted area,
so thinness read as raggedness — the gate was measuring WIDTH, which
`border_runs` already does better. Now measured per RING.

Also fixed: `_seam_band` did `.boundary.buffer()` unguarded and shapely 2.x
returns None for `GeometryCollection.boundary` — `border="auto"` died outright
on `photo_dof_meadow.png`. Never fired because `border` was "off" for everything.

**Raggedness measures MACRO SPRAWL, not edge noise**, and the first version of
that comment said the opposite. Douglas-Peucker already runs at
`simplify_tol_mm` 0.2 and meets it to 0.002 mm — there is no pixel staircase.
Solidity on owl_kent's three largest regions is 0.873/0.476/0.329. Smoothing at
8.6x the tolerance moves the worst by 0.04. **"Smooth the polygons to fix ragged
edges" is a measured negative.**

## Kent's own rule, which produced the border work

*"A clean satin border around 'significant' shapes helps [create pop]. Doing the
stitched border is typically very clean and smooth — if it's abrupt, it probably
doesn't require a border, or is wrong."* Blanket `border="auto"` spends +60%
stitches to make the silhouette WORSE. The abruptness half is what fixes that,
and it is the half doing the real work.
