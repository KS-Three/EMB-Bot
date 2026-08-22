# MASTER_SCOPE — dated history

**What this is:** the reverse-chronological work journal that used to sit at the
top of `MASTER_SCOPE.md`. Moved here on 2026-08-14 so that document could hold
current state only.

**How to read it:** every entry was accurate on its own date and has not been
re-verified since. Test counts, stitch counts, corpus grades, "still open" notes
and "as of today" claims are **snapshots, not current baselines** — never quote a
number out of this file as live status. If something in here still governs a
decision today, it belongs in `MASTER_SCOPE.md` carrying a dated evidence
pointer; if it isn't there, treat it as superseded until re-measured.

**The ordering trap.** Entries are newest-first, and several describe defects
that a *later* (higher up) entry closes. Read upward before concluding anything
is still open. Worked example: the 2026-08-06 entry flags `stage6_satin.py`'s
"E missing its bottom-left corner" as "a real, separate, still-open defect" —
the 2026-08-07 entry above it records that same defect root-caused, FIXED, and
re-verified by direct render inspection. Reading only the first one would send
you hunting a bug that closed eight days ago.

**Append-only.** New dated entries go at the top of the journal below, under
their own `**Last updated:**` line. Nothing in here is edited to stay true —
that is the whole point of the file. Corrections go in `MASTER_SCOPE.md`.

---

**Last updated:** 2026-08-22 — **the font library went 55 -> 80, and five
defects were found by LOOKING at output that every number called healthy.**

Counts as they stood: 55 fonts at the start of 2026-08-21, 70 after the upstream
sweep, 77 after cross-stitch lettering, **80** after the `fill_method` re-census.
The `--personal` build went 106 -> 120. PRs #193, #195, #196, #198, #200, #203
merged. Engine 387 pass / 0 fail; Studio 776 pass.

Three engine capabilities landed. **Bean / running-stitch lettering:** the path
was satin-only, so a runs-only font imported fine, passed most checks and
stitched exactly ONE stitch — 26 licence-clean upstream fonts were unusable for
that reason alone. **Cross-stitch fill** (`src/crossfill.js`), written from first
principles rather than ported, because Ink/Stitch's is GPL-3.0 and this product
is sold. **The sellable/personal build split**, at build time rather than as a
runtime toggle.

Five defects, and the pattern connecting them is the point. **The SVG parser
truncated every path at its first scientific-notation number** — `parsePath`
tested "is this a command?" with an unanchored `/[a-zA-Z]/`, and `5.2e-4`
contains an `e`. 119 of 132 upstream fonts contain such numbers; 63 of the 70
then-shipped ones did. It hid because satin rails carry large coordinates where
truncation lands late: montecarlo lost 95 of 195,997 rail points (0.05%) and
rendered beautifully. Kent's call was to rebuild rather than freeze the
truncation: 20 of 77 came back byte-identical, median drift 0.00%, max 7.44%
(alchemy 699 -> 751). **Even-odd vs nonzero winding** rendered `jersey_15` (one
ring per glyph) flawlessly and `jacquard_12` (two) as fragments, at ~100% lattice
fit on both. **Serpentine order dragged thread across gaps**, visible as
diagonals over the M and B of "EMB". **`roman_ags`'s credit line** named its OFL
adapter but not its LPPL base. **Four shipped fonts render a letter as a stub**
and pass QC because they do emit stitches.

Cell counts, QC verdicts and lattice fit all read healthy while glyphs were
garbage. Rendering cells as ASCII, and looking at the browser, is what caught
the parser bug, the fill-rule bug and the travel-diagonal bug. Two tests written
this cycle passed VACUOUSLY on first draft — the roman_ags guard matched nothing
because upstream's text reads "a derivative work fromm", and a crossfill fixture
asserted a wrong expectation — both found only by deliberately breaking the
thing they guarded.

The `fill_method` re-census: cross-stitch fonts declare themselves two ways,
`cross_stitch_method` and `fill_method="cross_stitch"`. The 2026-08-21 census
looked only at the first, so 13 fonts were filed as "plain fill" needing a
tatami row spacing — a gate-1 constant. They needed nothing of the kind;
`build-font.mjs` had always handled them. 25 upstream cross-stitch fonts exist,
not 12. Seven of the 18 unshipped measure a confident grid; eleven are refused
at 26.2%-87.5% fit. Only three of the seven are OFL and therefore sellable.

Terminus (inkstitch PR #2034) was re-fetched and re-evaluated: four broken
letters rather than the one QC reported, plus a 1/10-width space in a
fixed-width font, an OFL Reserved Font Name, and no size key. Recommended for
omission; the decision is Kent's.

---

**Last updated:** 2026-08-21 (later) — **the sew-out ruling collided with the
next work item, and Kent resolved it in favour of the gate.** Queuing satin
border fragmentation surfaced a conflict with the same session's accept-as-is
ruling: `docs/fragmentation-attribution-2026-08-18.md` §4 measured the defect as
**trim-dominated, 3.1x the pro** across 23 designs, and both of its primary
levers are gate-1 thread specs — `chain_links` (**9.82 → 4.06** trims/1k, 0.00 mm
added bare thread on four fixtures, gate-3 instrument rebuild MET 2026-08-18) and
`trim_at_mm` (ours 3.0; the pro never cuts for a move under **11.8 mm**). The doc
had said "no code work will beat it". Accepting the sew-out as-is froze both.

Three calls, all Kent's: (1) **Gate 1 holds** — both levers stay frozen and the
work proceeds on the gate-clear remainder, accepting a lower ceiling; the
`chain_links` latent entry now reads *frozen* rather than *pending*. (2) **First
lever is the 46-hole white field** — one 2,095 mm² region whose 46 holes break
its tatami into 280 runs, carrying **56 of the design's 135 trims (41%) inside a
single shape**, and gate-clear geometry rather than a thread spec. (3) **Golden
re-capture is pre-authorized on Linux CI** under same-failure-set discipline
(identical failure set before and after, diff reported), never on Windows —
previously a per-instance ask.

Not started here; recorded so the next session can act. The remaining gate-clear
candidates, unranked: `_graph_travel` never returning a path (no test in the repo
references it), stage 2 splitting one flat colour across two threads (47%/42%),
and running the real-art lane over all 15 designs — the 3.1x is recon-lane, which
the 2026-08-16 handoff measured as flattering the engine by 11.3 points.

**Last updated:** 2026-08-21 — **two of Kent's decisions resolved, and PR #194
landed.** (1) **The sew-out is accepted as-is.** A decision of Kent's had been
carried for days as an unresolved ambiguity — "accept as-is" had been recorded
without which item it attached to, and sessions had been refusing to guess it
into MASTER_SCOPE. Asked directly and answered: it was the **sew-out**, not
satin density. It leaves "Waiting on Kent" as a decided item and becomes a
standing ruling; the confidence scores beneath it are now permanently
`pending sew-out` rather than awaiting a date, and ROADMAP gate 1 is a standing
refusal rather than a temporary one. It explicitly does NOT decide the two
items that were parked behind it — the DST codec fix and `split_tonal_regions`
now need their own call on their own merits, and both stay in the queue,
renumbered 2 and 3. (2) **Next work item is satin border fragmentation** (live
defect 6), taken ahead of satin-vs-fill routing (live defect 5), which stays
queued behind it. (3) **PR #194 merged** (`70ec5fb`) — the crossval harness
revival, the PES initial-positioning-jump fix it surfaced, and three stale-claim
corrections. Its `engine` CI job went from 350 pass / 6 skipped to **356 pass /
0 skipped**, the first time the repo's third-party format pins have executed for
real in CI. (4) The 13 merged `claude/*` branches were verified fully reachable
from `main` (all ahead=0) and an attempt to delete them was made; the remote
refused with **HTTP 403** on `send-pack` — an egress/token policy denial, not
the local permission classifier, which a settings.json allow-rule had already
cleared. Not retried, per the proxy README's instruction to report rather than
route around 403s. `claude/emb-bot-stitch-fill-5t69ut` (PR #152's, 64 ahead)
excluded deliberately.

**Last updated:** 2026-08-17 — **four docs-review fixes landed.** (1) The
ROADMAP standing item no longer reads as a CI-colour claim (reworded to the
imperative "Keep `main` green"); at edit time `main` was in fact red again —
the PR #157 merge failed the digitizer job on two `photo/enthusiast_logo.png`
goldens (2351 vs 2363 stitches), which still needs a Linux golden re-capture.
(2) The six-scheme phase-numbering trap is now a MASTER_SCOPE gotcha, with a
one-line pointer from ROADMAP. (3) The Playwright e2e suite got a CI job
(`studio-e2e` in `python-package-conda.yml`); it builds `digitizer/.venv`
before running because the digitize-* specs skip silently without it — the
dark-suite failure mode from 2026-08-10..13. (4) A global SessionStart hook on
Kent's machine (`~/.claude/hooks/roadmap-gates-global.js`) injects the ROADMAP
gates for sessions rooted in worktrees or secondary checkouts, where project
settings don't auto-apply; CLAUDE.md footgun #4 updated to match. Verified: the
hook injects from a nested subdirectory, stays silent in the primary checkout
and unrelated directories, and both sibling checkouts currently predate
ROADMAP.md entirely, so they stay silent until they pull.

**Last updated:** 2026-08-14 (evening) — **the pro-parity scorecard was
rescaled to chance-corrected, and the corpus re-measured on the new scale**
(PR #151). `direction` and `sttype` are bounded agreement measures whose raw
floor is ~0.5, not 0 — measured across this corpus, random angles score 0.505
and a shuffled type map 0.553, so about 21 of their combined 40 points were
being paid out for a wrong answer. The scorecard's own docstring had flagged
this since it was written, deferring the fix because rescaling moves every
historical number; Kent took that decision this session, ahead of the
satin-vs-fill routing work, so the routing work would be measured on an honest
scale from the start rather than needing a re-baseline halfway through.

Both components are now rescaled `(observed - chance) / (1 - chance)`, clamped
at 0, before weighting. The floors are analytic rather than sampled, so the
score stays deterministic and seed-free: `direction`'s is exactly 0.5 for every
design (folding a random angle mod π leaves the difference uniform on [0, π/2]),
and `sttype`'s is expected agreement under independence, `Σ_c p_pro(c)·p_ours(c)`
— Cohen's kappa. Degenerate agreement passes the raw value through rather than
dividing by zero.

Corpus at that moment, all 23 designs (`score` / old `score_raw`):

| | old scale | corrected |
|---|---|---|
| corpus mean | 70.9 | 54.8 |
| `sttype` range | 0.55–0.65 | 0.00–0.54 |
| `direction` range | 0.50–0.69 | 0.00–0.37 |

Worst: `tires_hat_3d` 53.5 → 39.7. Best: `mfab_hat` 77.0 → 63.8. Two designs
(`becker_chest_small`, `tires_hat_3d`) scored raw type agreement *below* their
own chance floor — 0.435 against 0.497, and 0.195 against 0.197 — which the old
scale still paid roughly 11 points each for.

**The stitch-type confusion matrix measured the same day, over 15,953 shared
2 mm cells**, is what pointed at satin-vs-fill routing as the next work. Pro
sews 53.6% satin / 46.1% fill over that shared ground; EMB-Bot sews 47.7% /
48.5% — the *mix* nearly matches. The per-place agreement does not: 35.0% of
the pro's satin cells are sewn as fill, and 31.9% of its fill cells are sewn as
satin. Bidirectional misrouting with a nearly-correct mix is why the corrected
score is so much harsher than the raw one, and why retuning `satin_max` alone
cannot help — it would only move the mix that is already right. Per design the
spread is wide: `mfab_hat` catches 92.4% of the pro's satin (corrected 0.542),
`becker_chest_small` catches 62.0% while satinning 73% of the pro's *fill*
(corrected 0.000), and `tires_hat_3d` — a design the pro sews 98.3% satin —
is sewn 81.5% fill (corrected 0.000).

Method note: the confusion matrix uses the scorecard's own `cell_stats`
classifier and registration, so it is the same comparison the score reports,
not a re-derivation. Both runs were made against a scratch-dir corpus prepped
by `prep_all.py` from Kent's local reference art; neither the sources nor the
prepped set are in the repo.

---

**Last updated:** 2026-08-13 (evening) — **the Content step's six tiles are
three (Text · Artwork · Design file), and the drawing tools moved to a
right-click menu on the canvas** (PR #138; Kent's "remove all of the
unnecessary upload buttons" + his amendment keeping Draw shapes as a
right-click tool — see area 5's red-annotation entry). Same PR repaired the
last three e2e specs and corrected PR #136's "suite green" claim: the truth
was 9/13 then, and it is a verified **13/13** now. Also opened, not yet
built: Kent rated the auto-digitized `becker logo.png` well below its
professionally digitized version; measured tonight, forcing the flat lane on
textured logo art makes it WORSE (k-means shatters texture — `summit_badge`
8,263 → 9,579 stitches), so closing that gap needs an edge-preserving
flatten BEFORE region forming, plus a side-by-side against the pro file
(waiting on Kent for `becker logo.png` + the pro DST/PES).

**Earlier the same day** — **stage 4 was silently throwing away
whole regions, including the entire body of `summit_badge.png`.** Kent asked
about "the space in the lower portion of the owl that gets dropped". It was
not a fill problem: `make_valid`'s repair of a self-intersecting traced
outline returns different geometry types in different cases, stage 4 only
understood one of them, and the rest were discarded — **1,662 mm² lost on
`owl_kent.jpg` (two regions, and their thread colours with them), 2,787 mm² on
`summit_badge.png`** — every one of them reported to the user as a "detail too
small or thin to hold a stitch". Full write-up in **area 1**.

**Earlier the same day** — **a node drag on the canvas now moves the
stitches, not just the outline.** Kent's "i can move the nodes, but the stitch
fill STILL isn't working" was not a broken edit path: an auto-traced outline
carries a vertex every ~1.3 mm, so moving one added a needle no fill row could
occupy (measured: +7 mm² of polygon, **0** stitches in it). Canvas drags now
carry the neighbouring boundary with them. Full write-up in **area 5**, under
Kent's direct-manipulation request.

**Previously, 2026-08-12 (late)** — **the blend tier's real blocker is not
the r² gate; the multi-colour seam it feeds was never wired.** Chasing PR
#125's finding to the end found something larger and, unlike the gate, not
tunable. Merged this pass: PR #125 (blend-tier measurement), PR #126
(`owl_kent.jpg` — the first REAL photo fixture), PR #127 (two honesty fixes:
the blend tier no longer claims decomposition it didn't do, and Studio now
names which DST encoder wrote a file).

- **`stage7_sequence` never reads `shade_thread_idx` / `shade_rgb`.** Both
  `stage6_blend` and `stage6_streamline` compute a per-shade chart snap and
  put it in their report; grep finds **no consumer anywhere**. A block's
  thread is `group[0].region.thread_index` (`stage7_sequence.py:1347`) — the
  region's ONE assigned thread. **Every shade of every decomposed region
  sews in the same colour.**
- **Verified on a fixture where the ramp path fires exactly as designed**,
  not inferred: `gradient_ramp_linear.png` — 2 regions, both accepted at
  r² 1.0, 4 shades chosen — emits **2 blocks and 1 colour change**. One
  thread per region, not per shade. **The blend tier has never produced
  multi-thread shading in the product.**
- **This resets what PR #125 concluded.** "The shade machinery is fine; the
  gate is the problem" is half right. The gate does block decomposition —
  but removing it does not buy shading, because the threads never reach the
  machine. Both halves have to land for either to be visible.
- **Kent ruled the fix goes UPSTREAM (2026-08-12).** Two options were on the
  table: teach stage 5/7 that one region can own several thread stops, or
  split tonally-diverse regions at segmentation time so the existing
  one-thread-per-region model carries them. He picked the second — smaller
  blast radius, no new machinery downstream, and the same lever the
  thread-drift measurement already pointed at. An in-between attempt
  (`blend_tonal_bands`, banding inside the fill tier) was built, measured,
  and **removed** in the same pass: it decomposed the geometry correctly and
  changed nothing visible, because the shades still shared one thread —
  7,725 → 10,126 stitches, trims 33 → 105, `color_changes` unchanged at 13.
  It is recorded here so nobody rebuilds it.
- **`split_tonal_regions` (new, `stage2_photo_segment`, default OFF).** Cuts
  a region whose own pixels span more light-to-dark range than one thread can
  express into parts, each of which then gets its own mean, palette weight
  and spool by the machinery that already exists. Lightness quantiles, not a
  colour k-means — deterministic, because this module feeds byte-identity
  goldens. Placed in `kept_masks_to_quant`, the shared tail, so the classical
  and SAM2 region formers get it from one implementation.
- **It works, and it is expensive.** On Kent's owl: 3 regions qualify
  (27 → 36 masks), and the tonal structure reaches separate threads for the
  first time — palette 12 → 15 colours, which is exactly
  `max_colors + PALETTE_OVERFLOW_K`, the documented ceiling rather than a
  breach of it. Cost: **7,721 → 13,393 stitches (+74%)** and trims 33 → 91.
  **Left off pending a corpus run and Kent's read on that trade.**
- **The dominant cost is spatial, and it is worth understanding before
  tuning further.** A tonal bucket is scattered across a region by
  construction — the mid-tones of a feathered breast are everywhere — and
  stage 4 vectorises each connected component into its own polygon with its
  own underlay and entry/exit. Unfiltered, the owl became **130 regions and
  14,905 stitches**; keeping only components individually worth sewing
  brought that to 57 and 13,393. The floor was swept (8 / 20 / 40 mm² → 87 /
  60 / 57 regions), and the curve is steep below 20 and flat above it, so 40
  takes the available reduction and no more. **The remaining +74% is
  structural, not a parameter that has been left untuned** — more regions
  means more perimeter, and that is the real price of shading this way.
- **One real defect found and fixed on the way, worth keeping:** the removed
  banding attempt first reused the ramp path's `FILL_ROW_MM * n` row pitch
  and sewed the owl body at 1,971 stitches against 6,058 flat — a third of
  the coverage. Ramp bands are contiguous strips that re-tile a region, so
  widening the pitch by n is right there; tonal bands are interleaved patches
  each already covering ~1/n of the area, so the same multiplication
  under-sews them twice. **The suspicion this raised about
  `streamline_mode: "layered"` was WRONG — measured and closed 2026-08-13,
  see below.**
- **`streamline_mode: "layered"` does NOT have the blend tier's row-pitch
  bug — measured 2026-08-13, and this closes a suspicion this document
  itself raised.** Layered was flagged as a likely twin of the blend defect
  on the strength of the 2026-08-12 note that it "measured a negative
  (3,220 stitches, sparser than baseline)". Running mono against layered
  directly says otherwise — layered is consistently *denser*:

  | fixture | mono | layered |
  |---|---|---|
  | `owl_kent.jpg` | 1,902 | **3,215** (2.1x) |
  | `photo/fur_ramp.png` | 326 | **696** (1.7x) |
  | `photo/gradient_ramp_linear.png` | 614 | **1,918** (3.1x) |

  The original note compared layered against **tatami** (7,725), not
  against streamline-mono. Streamline is a line-based tier and is
  inherently sparser than a solid tatami fill, so "3,220 = worse" was a
  judgement about the TIER being wrong for that image, not a density
  defect inside it. `_d_sep` being driven by each shade's coverage share
  rather than raw darkness is deliberate (see `stage6_streamline`'s "THE
  MULTI-COLOR SEAM" docstring) and behaves sensibly in measurement. **No
  fix needed; do not go looking for one.**
- **Not a defect, recorded so it isn't re-found:** the noise fixture in
  `test_blend_falls_back_to_ordinary_tatami_on_speckle` never reaches the
  speckle gate — r² is tested first and random noise fails it, so the branch
  that test is named for is not the one it exercises. Behaviour is correct;
  the test now says so.

**Prior update, 2026-08-12 (evening):** — **first end-to-end Studio photo
session with Kent driving, and it moved area 1's diagnosis more than any
code change did.** Kent digitized a real snowy-owl photo through the Studio,
annotated the output, and the investigation that followed disproved three
hypotheses before landing on the actual cause. Merged: PR #121 (`run-emb-bot`
skill now leads with Kent's Windows launch blocks + `tools/start-emb-bot.ps1`),
PR #122 (`.eladd-row` wrap). Open: PR #123 (Studio `detail_layer` control).

- **Kent's six annotated notes are now tracked** — five on the SAM2 on/off
  comparison, one on the follow-up render. Notes 1–3 are area 1; notes 4–6
  are the shape-editor request, recorded in full under area 5 (**do not
  re-compress it — the sub-requirements are the spec**).
- **The Studio could not reach any photo-quality tier.** `detail_layer`
  (FDoG line extraction, sewn as a final block over every fill) has been
  reachable only by editing `digitizer_core/config.py`; `buildDigitizeConfig`
  never sent it. **Every photo the Studio has ever produced shipped without
  its linework.** Measured on Kent's owl at 12 colors, Studio defaults
  otherwise: tatami+off 7,725 stitches = one flat pale mass (what shipped);
  streamline-layered+off 3,220 = *worse*; streamline-layered+on 6,222 =
  readable, thin fill; **tatami+on 10,727 = silhouette, facial disc, eye
  rims, barred chest feathers**. PR #123 exposes it as a checkbox, default
  False (matching the service; +39% stitches buys nothing on flat logo art).
  Promoting it to a default wants a corpus run — one image, one config.
- **`streamline_mode: "layered"` measured a negative** on this image (3,220
  stitches, sparser than baseline). Not a bug found, but don't reach for it
  first on photo work.
- **Three hypotheses disproven — recorded so nobody re-treads them.**
  (a) *Palette collapse merging bird into wall*: no. Segmentation is clean —
  27 regions, correct silhouette (`stage2_photo_merged` debug raster).
  (b) *`max_colors` is the binding constraint*: no. 6→12 left region count
  at 27 and worst `THREAD_RESNAPPED_AFTER_DRIFT` at dE00 18.3 either way;
  the chart-restricted k-medoids self-limited to 9 threads when allowed 12.
  (c) *`MERGE_DELTAE00_THRESH` needs retuning*: no evidence for it on a real
  photo, and its own tuning history (`stage2_photo_segment.py:452-496`) says
  a global change costs more than it gains. **Leave 26.0 alone.**
  All three came from extrapolating the *synthetic* `photo_owl_pale.png`
  fixture, which is a near-featureless blob (6 regions, one at 98.1% of
  canvas) and behaves nothing like a real photograph.
- **Corpus gap, sharpened:** the photo fixtures are procedurally generated
  on purpose (licensing-clean — see the cross-cutting corpus entry). That
  cleanliness cost real diagnostic accuracy this session. **Kent ruled the
  photo's provenance is not a concern (2026-08-12)**, so `owl_kent.jpg` on
  `kent/owl-fixture` is cleared to land as a real-photo corpus fixture —
  still unmerged, but no longer blocked.
- **The "thread drift defect" is NOT an independent defect** — measured
  2026-08-12, and this closes the item rather than opening it. Instrumenting
  every shape in Kent's owl (error to current thread, error to the BEST
  thread the chart can offer, and each shape's own internal colour spread)
  shows the spread *sets the floor*: S18356282 best-possible 14.70 with
  spread 17.25; Scbdb8ecc 13.22 / 13.09; S45f13ef0 10.54 / 10.55; and at the
  clean end S949f0c61 6.60 / 2.98. Current-thread error sits within ~1 dE00
  of best-possible on nearly every shape, so `stage4_vectorize`'s re-snap is
  working correctly and has almost nothing left to win. **No single thread
  can match a shape whose own pixels differ from each other by more than the
  error being complained about.** The two eyes sew in different threads
  because each is a ~260–320px shape carrying a *different* mixture of iris,
  pupil edge and surrounding tissue (spreads 7–13), so "best available
  thread" honestly resolves differently for each. This is the same root
  cause as the detail-layer finding — flat fill assigns one thread per
  region, and photo regions legitimately contain tonal variation — so the
  real options are narrower: tighten simplification so small features stop
  absorbing their surroundings, or let a high-spread region decompose into
  shades — but NOT via `stage6_blend` as currently gated; see the next entry,
  which measured that. **Do not spend time on the re-snap code itself.**
- **The blend fill tier never fires on a real photo — measured 2026-08-12,
  and this is the live lead for photo colour fidelity.** On Kent's owl
  (classified `gradient`, `source_pixels` populated, so blend is fully
  wired), **all 25 regions are rejected**: 24 on `detect_ramp`'s
  `RAMP_R2_MIN` and one on speckle. `detect_ramp` accepts a region only when
  its *lightness fits a linear or radial ramp* at r² ≥ 0.5; measured bests
  were iris 0.295 / 0.232, mid-size shapes 0.478, and the 4200mm² body 0.385
  — against the 0.994-0.999 that `RAMP_R2_MIN`'s own comment cites for the
  committed synthetic ramps. **The gate was calibrated on synthetic gradients
  and real photographic structure is nowhere near it.** This is not a tuning
  miss: an iris is a *ring* (dark pupil, amber band, darker rim), which
  neither a linear slope nor a centroid-radial fit describes. Lowering r²
  would force a ramp model onto things that are not ramps.
  Three consequences:
  1. **The user-facing warning is wrong today.** "The blend fill tier will
     decompose the ramp into a few thread shades instead of flattening it to
     one flat colour per region" fires on *classification*, before any region
     is tested — then every region is flattened anyway. Kent believed blend
     was working because the app said so. Small honest fix: only claim
     decomposition when it happened.
  2. **The shade machinery is fine; the gate is the problem.**
     `streamline_mode: "layered"` reuses the SAME `stage6_blend`
     shade-selection code driven by each shade's coverage-share map, with no
     r² test — which is exactly why it produced visibly different output in
     the tier comparison. A 3-5 shade decomposition of a photo region is
     already achievable in this codebase.
  3. ~~**`_speckle_ratio` looks scale-broken**~~ — **WITHDRAWN 2026-08-14,
     it is not broken.** The original note (0.35 max vs values of 39.93,
     49.45, 78.72 on real regions) was hedged "confirm before trusting it"
     and then hardened into a suspected defect as it was copied forward.
     Checked: `stage6_blend.py:295-299` computes an **unnormalised
     Laplacian-gain ratio**, so its scale is not comparable to a 0-1 ratio by
     inspection, and it discriminates correctly at the shipped threshold.
     Kept struck through rather than deleted because this is the SECOND
     suspicion in this document to evaporate on measurement (the streamline
     row-pitch one was the first) — the pattern is a hedged observation
     losing its hedge as it is re-copied, and it is worth being able to see
     that pattern rather than tidying the evidence away.
  **Direction — KENT RULED "option A", 2026-08-12. START A FRESH SESSION
  HERE.** Scoped but deliberately not started; the scoping below is the
  handoff.

  **A (chosen): tatami + shade bands.** Add a darkness-based fallback at
  `stage6_blend.blend_fill`'s `if model is None:` branch (currently
  `blend_fill` line ~544) so a ramp-less region *still* decomposes into 3-5
  shades and fills each with tatami, instead of collapsing to one flat
  colour. That `model is None` branch is the norm, not an edge case — its own
  comment says "all 23 regions fall back here" on the repro fixture, and all
  25 do on `owl_kent.jpg`.
  - **The machinery mostly exists.** `stage6_streamline._shade_layers`
    already does ramp-free 3-5 shade decomposition off the darkness field,
    reusing `stage6_blend`'s `_choose_shade_count` / `_shade_lab_colors` /
    chart snap verbatim, and needs only >= 12 samples
    (`_SHADE_MIN_SAMPLES`). Its docstring states the premise outright: "a
    photo region has no ramp to fit, only the same source-darkness field
    this tier has always read."
  - **THE OBSTACLE, and where the design effort goes.** `_shade_layers`
    returns a *continuous* `membership(x_mm, y_mm) -> [0,1]`. Streamline
    tracing consumes that directly to modulate line density; **tatami needs
    actual polygons per shade.** So this needs a new darkness-field ->
    per-shade geometry step. `_band_clip` does not help — it slices by ramp
    position, which is exactly what does not exist here. Write the design
    before the code; this step is where a wrong choice gets expensive.
  - **Validation bar:** corpus run against `drone_render` (must stay inside
    its documented [20, 80] region band) and `summit_badge`, plus a
    before/after on `owl_kent.jpg`, now a committed fixture.

  **B (considered, rejected as "cheap"): make streamline `d_sep`
  subject-relative.** Measured and it is not the shortcut it looks like.
  Streamline spacing is driven by *absolute* darkness —
  `STREAMLINE_D_SEP_DARK_MM = 0.8`, `STREAMLINE_D_SEP_LIGHT_MM = 3.2` — so a
  near-white subject sits at the light end and gets ~3.2mm spacing, roughly
  25 lines across an 80mm design. That is why the layered variant measured
  **3,220 stitches against tatami's 7,725**: the tier is working as designed
  for a subject class it was not designed for. Making `d_sep` relative to a
  region's own darkness *range* would retune a tier with its own calibration
  history, against designs that currently work. Not obviously cheaper than A,
  and lower ceiling.

  **Net state of the two fill paths, for whoever picks this up:** tatami
  gives solid coverage but one flat thread per region; streamline-layered
  shades correctly but goes sparse on pale subjects. Neither serves a pale
  photograph today, and A is the path to one that does.
- **Still open, not started:** 14 jump-trims on an 80mm design, in every
  variant measured.
- **`.eladd-row` had been hiding "+ Auto-digitize"** (PR #122): six
  non-shrinking buttons overflowed the 400px sidebar by 136px, putting the
  last one 111px past the panel edge. Because that button only renders when
  the digitizer is reachable, a clipped button was indistinguishable from a
  dead service — and it silently routed Kent's photo work through the
  *browser* engine (`+ Image`), which emits none of the pipeline warnings.
  A full SAM2 on/off comparison was run, and published two result sets, that
  never touched SAM2 at all. **Worth remembering as a class of bug:** a UI
  affordance that gates on service health fails indistinguishably from the
  service itself. *(2026-08-13, PR #138: this whole bug class is now
  structurally closed for the upload path — the tile row is three
  always-rendered tiles and "+ Artwork" routes on service health internally
  instead of appearing/disappearing; the browser-engine fallback is
  announced in the offline note rather than silently substituted.)*

**Prior update, 2026-08-12 (small hours):** — **wave 2 of the same night
landed:** the LINK_UNCOVERED false-block + raster-overhead fix (see the
entry below this one), plus:

- **Five procedurally-generated photo-class fixtures** committed
  (`tools/make_photo_fixtures.py`, licensing-clean, deterministic): owl_pale
  F/22, sunset_backlit F/34–D/46, dof_meadow D/40–52, grass_macro C/64,
  chrome_specular C/64–B/76 — the photo lane finally has a graded
  regression net and a to-do list. Finding worth keeping: stage-0's
  photo_subject gate is bimodal — textured subjects on smooth backdrops
  can't reach photo_subject (pinned in the routing test's docstring);
  and `stage0_classify._load` treats raw ndarrays as BGR (A/B probes must
  convert first).
- **DT-first classifier probe: architecture swap is a measured negative**
  (`docs/dt-first-verdict-2026-08-11.md`): the patented rule as printed
  sends 62/83 clean satins to fill; corrected arms lose every disagreement
  they create. One real find — the stage-7 ladder has **no width floor
  under satin**: 19/162 corpus regions (all photo-class) sew sub-millimetre
  satin today (Law 31 violations); a near-free `2·p90 < ~1.0mm → run`
  reroute is proposed, gated on a threshold sweep + the sew-out.
- **Four cross-lane test regressions fixed** (blend ramp-angle ×2, preflight
  photo happy path, service stitched-restore): all were built on the
  repro/stub fixtures' flooded prep state, which the new background guards
  correctly no longer produce at defaults — each now disables the guards
  explicitly, documented (same pattern as test_enclosed_background). One
  real capability note rode out of this: **ramp-angle detection declines on
  full-bleed gradient prep at the new defaults** (end-to-end repro grade
  still improved D/58→B/76); if full-bleed gradient angle-sharing matters,
  the detector needs a no-flood design-mask path — logged as follow-up.
- Corpus baseline recaptured with all of the above; known env failures
  (enthusiast OCR goldens, pushcomp towel, tesseract-dependent OCR tests)
  unchanged.

**Prior update, still the same night (2026-08-11 late):** — **the "let it
rip" wave: two launch-checklist items shipped, five confirmed engine defects
fixed, and the corpus baseline re-graded under the honest per-region
yardstick.** All landed on `main` and pushed; every merge passed its
targeted test gate (356/356 engine JS, 671/671 Studio vitest, per-lane
pytest subsets; full-suite run in flight at write time).

1. **Launch items 2 and 4 shipped.** Hoop picker (`HOOPS`/`suggestHoop`/
   orientation-aware `hoopFit` in `src/garments.js`, Garment-step picker,
   `.embproj`-persisted `hoopId`, hoop on review stats + PDF) and the basic
   shapes tool (`app/src/lib/shapePresets.js` circle/rect/heart/star riding
   the manual-draw `shapesToRegions → buildQualityDesign` lane, new `"shape"`
   element type). PRODUCT.md checklist updated; remaining launch work is the
   starter design pack (needs licensed designs) and the billing session.
2. **Kent ruled (recorded in PRODUCT.md):** engine quality is a parallel
   investment, NOT a launch gate; SAM2 ships post-v1 as an opt-in download
   (`docs/sam2-ship-path-brief-2026-08-11.md`).
3. **Background flooding fixed — the owl case.** Stage 1's border flood
   deleted a subject that dominates the border ring (93.8% of the owl-repro
   subject's pixels). Two guards landed: ported border-agreement
   (`BACKGROUND_ABSENT`, `bg_border_agreement_min=0.75`) + new rival-ring
   guard (`BACKGROUND_UNCERTAIN` reason=`subject_dominated_border`). Owl
   fixture bare cloth 93.4%→3.0%; all 9 real-background fixtures bit-identical
   bg_mask (verifier re-derived the hashes independently). Two accepted
   residuals from adversarial review: a one-notch-tighter crop where the
   subject owns all 4 corners still floods silently, and edge-bleed flat art
   can false-positive into stitch-everything+warn (conservative direction).
4. **SVG import is in the engine** (salvaged from the broken WIP branch):
   tokenizer kept, flattening error metric rewritten with a provable bound
   (the old AGG-style check used a ×16 constant from the wrong criterion),
   arcs implemented, `EMB.parseSVG` wired into the Studio engine list.
   Studio UI wiring (ImagePanel accept path, shape-pack picker) still to do.
5. **Export/stats circularity broken** (`stitches.iter_machine_commands` is
   now the single command stream both consume) and the block-boundary dedupe
   defect fixed — a block opening without jump/trim flags no longer loses its
   first penetration (tie_run's lock anchor now lands 5 of 5).
6. **Chaining cover model completed** (tier-blindness closed: a later
   run-tier shape provides no areal cover) — `chain_links` still default
   False pending the sew-out; contour's directional_comp non-composition now
   warns (`CONTOUR_DIRECTIONAL_COMP_UNSEWN`); appliqué's promised no-fabric
   fall-through implemented (was: docstring lied, contiguity broke, overlap
   warning silent). One accepted residual: stage-5-dropped split-shape
   pieces still count as cover (verifier finding, logged for follow-up).
7. **Corpus baseline recaptured** under the per-region metric + tonight's
   fixes: flat lane unchanged (A/100, B/88); repro_gradient D/58→B/76 and
   photo_scene_stub D/52→C/64 are real now-visible improvements;
   gradient/blob/badge entries dropped because the pooled median had been
   hiding per-region error — that is the new honest baseline, not a
   regression. photo_subject_stub A/100→C/70 grades output whose subject
   now actually survives.
8. Hygiene: worktree yard emptied (one checkout, `main` only), merged/
   superseded branches deleted locally and on origin, remote URL moved to
   KS-Three, fresh Drive backups (`EMB-Bot-2026-08-11.bundle` +
   `scratch_ink-2026-08-11.zip` — the 368 MB font-source bus-factor risk is
   closed). Known pre-existing env failures unchanged: enthusiast_logo
   OCR-goldens and pushcomp `logo_whitebg/towel` byte-identity.

**Addendum, 2026-08-11 (after the wave, `fix/link-uncovered-preflight`
lane):** both confirmed LINK_UNCOVERED defects from the 2026-08-02 hardening
closeout (finding 4) are fixed. (1) The false block on clean artwork: a
fill's OWN row-skip travel was scored as a between-shape chain link, which
blocked a clean one-shape design (`bg_uncertain`) at 104–107 mm. The
transport classification (`preflight._transport_and_content`) now scores
BETWEEN-shape transport only — a travel piece whose nearest content on both
sides is the same shape it names is that shape's internal routing, not a
link. Pinned synthetically (the exact one-shape false-block plan, red on the
old code) and by a pipeline sweep at 90/104/105/106/107/120 mm on both
garments that fired; a chain-OFF plan now honestly reports zero link thread
(the fixture logo's old 87.8 mm "link" reading was all internal routing —
goldens re-pinned with comments). The false block was LIVE on tonight's own
corpus baseline, not just historical: `photo/region_blobs.png @ 80mm` was
blocking on both garments — a chain-off plan, where no between-shape link
can exist, reading 298 mm of phantom "link thread" with a 7.32 mm max bare
stretch from the meander/scanline tiers' in-shape travel; it recaptures to
F/10 -> D/40 with the block gone (its other findings are real, it is a
stress fixture). (2) The 1.94x preflight slowdown: the
per-sample disk-stamping raster was replaced with per-run `cv2.polylines` at
thread width plus an earliest-transport early-exit — link check 10.5→0.6 ms
(whitebg), 10.2→0.6 (alpha), 12.5→0.8 / 9.4→3.8 chain-on (enthusiast@82);
whole preflight ~25→~16 ms on the corpus fixtures. Corpus scorecard
baseline's `link_*` metrics recaptured under the new semantics. One
pre-existing failure noted, NOT from this lane:
`test_every_photo_guard_stays_quiet_on_the_committed_photo_happy_path`
(`subject_bg_delta_l` reads None on `photo_scene_stub`) fails identically on
this branch's HEAD before the preflight edit — likely fallout of tonight's
stage-1 background-flood guards.

**Prior update below, still 2026-08-11 (evening):** — **one of the two SAM2
open risks below is closed, fix #6.3 landed, and fix #6.2 was REFUTED on
measurement.**

1. **The SAM2 venv is a real install now, not a junction.** The 875 MB venv
   was moved out of `.claude/worktrees/sam2-segmentation` into
   `digitizer/sam2_isolated/venv` and re-verified end to end on its new
   path: `torch 2.13.0+cpu` / `torchvision 0.28.0+cpu` / `sam2` / `cv2 5.0.0`
   all import, `sam2_worker.py --prewarm tiny` exits 0, and README step 5's
   real job-mode run produced a correct `(1024, 1536) int32` label array with
   `-1` present in 50.5s. The venv's console-script `.exe` shims DID break on
   the move (they embed an absolute interpreter path — `pip.exe` exited 1
   silently) and were regenerated offline via pip's own vendored
   `distlib.ScriptMaker`; all 9 verified working. `tests/test_sam2_segment.py`
   + `test_sam2_worker.py` 42 passed. The now-empty, fully-merged
   `sam2-segmentation` worktree was removed at Kent's go-ahead.
   **SAM2 no longer silently falls back if a worktree disappears.**
2. **Fix #6.3 landed** — `stage4_vectorize.revalidate_threads`. See area 1.
3. **Fix #6.2 refuted and NOT built.** See the follow-up section appended to
   `docs/photo-quality-root-cause-2026-08-11.md` for the full measurement.

**STILL OPEN — the second SAM2 risk, now with real user evidence.**
`points_per_side=12` is still validated only against the synthetic
`photo_scene_stub.png`. The A/B harness for the real measurement now exists
(`digitizer/tools/sam2_points_per_side_ab.py`, verified against the stub:
26 regions at 12, matching the number recorded below, with SAM2 genuinely
engaged rather than silently fallen back — the tool refuses to report a
comparison that fell back). It is waiting on the image file only.

**NEW, from Kent on the real photo (a snowy owl, white bird on a beige
wall):** SAM2 is better "but still needs improvements — it recognized the
white space in the owl as the background." **Working hypothesis, mechanism
identified but NOT yet confirmed against the file:** this is very likely
stage 1, not SAM2. `stage1_prep` picks `_dominant_border_color` — the modal
colour of a 2 px border ring — and floods every border-connected pixel close
to it. In a tight portrait crop the subject IS most of the border ring, so on
a white owl the flood's own seed colour is the owl, and the whole white body
floods out as background before any segmenter runs. `stage1_prep` already has
the guard that should catch this (`BACKGROUND_UNCERTAIN`, fired when
border-connected background intrudes deeper than `cfg.bg_margin_mm` into the
artwork hull, written for "white text touching a white border" — the same
shape of failure); whether it fires here is the first thing to check. The
real fix for a photo is `photo_prep_background_removal` (rembg subject
cutout), which is built and behind a double gate, default OFF. **Nothing here
is confirmed until the owl file is on disk and measured.**

**Previously (2026-08-11, later the same day):** **the SAM2 photo
segmentation lane became reachable from the product, and is staying.**
Three things landed together:

1. **SAM2 merged to `main`** (from `sam2-segmentation`, which had been
   complete but unmerged): config gate, isolated-venv subprocess worker,
   never-raises seam with silent SLIC+RAG fallback. Still `photo_segment_
   sam2=False` by default.
2. **A Studio dev seam to switch it on** — `localStorage` key
   `embstudio:sam2` = `"1"`, read by `sam2Enabled()` in
   `app/src/lib/digitizer.js`, which sets `photo_segment_sam2` in
   `buildDigitizeConfig`. Deliberately **no UI**: SAM2 needs a hand-built
   ~1 GB isolated venv and real per-image latency, so this is an internal
   seam in the same shape as the existing `embstudio:digitizerUrl` one.
   Design: `docs/superpowers/specs/2026-08-11-sam2-studio-seam-design.md`.
   **No service change was needed** — `digitizer_service/app.py` derives
   its config allowlist from `PipelineConfig`'s dataclass fields, so all
   five `photo_segment_sam2*` fields already validated (verified by
   parsing a real config through `_parse_config`, not assumed).
3. **`photo_segment_sam2_points_per_side` lowered 16 → 12** on measurement:
   ~59.7s → ~42.3s (-29%) end-to-end through the real service on
   `photo_scene_stub.png`, finding *more* regions (25 → 26), not fewer.

**Kent verified SAM2 on a real photo and reported it "drastically better
at the photo recognition portion."** That is why it is staying. Note the
committed corpus proves nothing about this either way — SAM2 only engages
for `photo_subject`/`photo_scene` classes, and the only two such fixtures
are synthetic stubs that produce near-identical output with it on or off.
Measured cost on this machine (CPU-only): ~1.03 GB footprint (875 MB venv
+ 156 MB tiny checkpoint) and roughly +15 to +30s per photo at
`points_per_side=12`.

`docs/sam-alternatives-research-2026-08-11.md` asked whether a smaller or
photos-only SAM could cut that cost. **Answer: don't swap the model** — in
automatic-mask-generation mode SAM2's image *encoder* is only ~8% of
per-image cost and the `points_per_side**2` prompt-decode loop is ~92%,
while every lightweight SAM variant optimizes the encoder (they target
interactive click-to-segment). Also settled there: SAM2's video machinery
is 30.1 MB of 156.0 MB and costs zero runtime, and SAM 1 — the actual
image-only predecessor — is *heavier* (375.0 MB smallest checkpoint).
**License findings worth keeping:** FastSAM is AGPL-3.0 despite a README
claiming Apache (the claim hyperlinks to the AGPL file itself) and vendors
that code in-tree; EdgeSAM is non-commercial (NTU S-Lab 1.0) — same
category as the `bria-rmbg` rejection. Both disqualified for a commercial
product. Those two license claims came from a research subagent and were
**not** independently re-verified — treat as strong leads, not settled
fact, if either is ever reconsidered.

**A recommendation from that same research was tried and REJECTED on
measurement:** `photo_segment_sam2_max_side_px` 1024 → 512, pitched as
"~-21% wall-clock, same masks". Measured end-to-end it is not the same
masks — regions drop 25 → 20, reproducibly, at both `points_per_side` 16
and 12. The ~11% saved sits inside this box's timing noise (the same
config measured 51.3s and 59.7s across runs), so it buys a deterministic
quality loss with a saving indistinguishable from noise. Stays 1024; the
rejection and its evidence are recorded at the field in `config.py`.

**Two open risks on this lane — the first is CLOSED as of the evening
update at the top of this document (the venv is a real install now); the
second is still open, and now has real user evidence attached to it:**
`digitizer/sam2_isolated/venv` is currently a Windows **junction** into
`.claude/worktrees/sam2-segmentation` (created to avoid copying 875 MB
back when the expectation was that SAM2 would be switched off) — that
worktree is merged and looks deletable, and if it goes SAM2 silently
falls back with no error, so it should become a real install now that
SAM2 is staying. And `points_per_side=12` was measured **only** against
the synthetic `photo_scene_stub.png`; the real photo that justified
keeping SAM2 has never been re-measured at 12, so the new default is not
yet validated against the content that actually matters.

**Previously (2026-08-11):** fix #6.1 landed:
`digitizer_core/palette.py`'s `select_palette` gets a bounded, floor-aware
overflow past `max_colors` (`docs/photo-quality-root-cause-2026-08-11.md`).
Verified correct at the algorithm level — unit test plus a direct trace
against the real `photo/drone_render.png` fixture, not just Task 1's
synthetic scenario: both target regions (floor 1.506/1.978 ΔE00) get
rescued to Titanium/White chart spools, and `select_palette`'s own
`max_excess_de00` improves 7.599 → 1.969 exactly as designed. **Does not
move `drone_render.png`'s `corpus_scorecard.py` grade**, though — still
F/0 at both `80mm/left_chest` and `80mm/hat_front` after recapturing the
baseline (`color_changes` 14→16, `THREAD_MATCH_POOR` findings 5→6,
`thread_worst_delta_e` unchanged at 9.2) — because `preflight.py`'s
`THREAD_MATCH_POOR` finding measures a pooled per-thread median color
across every region sharing a spool, a structurally different signal than
this fix's per-region excess-over-floor target; the same pooled-vs-
per-region gap the root-cause doc already flags for `summit_badge.png`
(fix #6.2, still open, along with #6.3 `repro_gradient_white_icon.png`).
Three other fixtures also moved in the recapture, but not from this
fix — a stale baseline, not noise. See area 1 below and "Evaluation
corpus & harness" in Cross-cutting issues for the full before/after,
root-cause trace, and why this fix can only hold a design's grade flat
or lower it on the current scorecard.

**Previously (2026-08-10):** Ink/Stitch open-source teardown
(`docs/inkstitch-research-2026-08-10.md`) integrated as a new cross-cutting
research item: `pystitch` (Ink/Stitch's own MIT-licensed pyembroidery fork)
flagged as a concrete, not-yet-evaluated `pyembroidery` replacement
candidate; a fifth independent source corroborates the DST axis bug (no
verdict change); a genuine satin-underlay gap (no `contour` style, only
`center_run`/`zigzag`) confirmed by direct code read, not just doc research;
and Ink/Stitch's own real capability gaps (meander fill, tartan fill, ripple
stitch, satin e/s-stitch, bean stitch variable-repeat) catalogued alongside
areas where EMB-Bot's own prior research is already ahead of Ink/Stitch
(chaining laws, gradient fill scheduler, guided fill). Documentation only —
no area's Status/Confidence moves. See Cross-cutting issues below.

**Previously (2026-08-10):** UI icon system fully rolled out (all 13
files, not just the foundation two), three more fill techniques added
(wave, chevron, brick, alongside crosshatch). See areas 1 and 3 below.

**Previously (2026-08-09):** cross-hatch fill added as a new opt-in fill
technique (Python digitizer pipeline), the first of a planned small family
of new named fill patterns. See area 1 below.

Prior update below, still 2026-08-09:

**Last updated:** 2026-08-09 — manual-digitizing Trace feature shipped, real
user UX feedback fixed (shape editor + step nav), appliqué zigzag cover
bugfix, legacy standalone tool removed. See areas 1 and 3 below.

**Previously (2026-08-07):** two backlog cleanup items closed in one pass.

**(1) `DigitizePanel.svelte` gained a component-test harness — a real,
previously-self-flagged gap, not a newly-invented one.** Every per-shape
Layers-panel control (stitch type, fill angle, underlay style, border,
recolor, delete/restore, `moveShape`/`moveShapeWithinLayer` reorder) and
the just-shipped Sequencer view had ONLY ever been checked via live-browser
passes — no Svelte component test harness for this file existed anywhere
in the repo, this doc's own area 5 said so explicitly for the
underlay-style control specifically. `DigitizePanel.testHarness.svelte`
follows the exact precedent `ManualPanel.testHarness.svelte` set (a real
`*.svelte` wrapper listening with `on:elupdate`, since Svelte 5 dropped
`$on` on a mounted instance) — 21 new tests in `DigitizePanel.spec.js`,
scoped deliberately to the Layers panel's edit controls, NOT the upload
-> Digitize -> poll flow (already covered by the real Playwright e2e spec,
`app/e2e/digitize-stale-edits.spec.js`; no element in these tests ever
touches `element.params`, so the "auto re-digitize on param change"
reactive statement never fires and no network call happens). Two real,
previously-unverified behaviors came out of writing these: the "Fill
angle"/"Border" labels are ambiguous with the design-wide params section's
own same-named controls (fixed in the tests via an `aria-label` attribute
selector, not a component change — the app's own accessibility labeling
was already fine, just not literally testable via `getByLabelText`
without disambiguation); and `moveShape`'s "join vs. step past" branch
(commented in the component, never exercised by a test) is real and
correctly reachable — confirmed both branches with two dedicated fixtures
rather than assuming the comment's own claim. Branch
`digitize-panel-test-harness`. Full 490/490 app suite passes, `vite
build` succeeds. Doesn't move area 5's Status/Confidence verdict (closing
a testing gap on already-shipped, already-correct behavior, not new
capability or a found defect).

**(2) `feat/svg-import-shapes` formally evaluated and NOT resumed** —
standing item from before that 2026-08-07 session, re-examined rather than left to
keep sitting untouched indefinitely. Checked directly, not assumed: the
branch is 277 commits behind `main`; of its own 10-task plan
(`docs/superpowers/plans/2026-07-27-svg-import-and-shapes.md`) only Task 1
(a path-data tokenizer) is actually complete, and Task 2 (bezier
flattening) — the branch's own last commit message calls it "interrupted
mid-implementation, UNREVIEWED, tests not confirmed" — genuinely does not
work: running its own test suite (`node --test test/svgpath.test.js`)
fails one real assertion, a cubic-bezier flattening deviating 8.75 units
against its own 0.5-unit tolerance, not just an unreviewed-but-working
stub. Tasks 3–10 (arcs, transforms, primitives, document parsing, the
Studio upload path, and the shape-element/shape-pack UI) were never
started. The core end-user motivation — getting curved vector shapes into
the Studio without hand-tracing — is now partially covered by this
session's manual curve-drawing tool (see the entry below), though a true
SVG-file-import feature (preserving an EXISTING vector file's exact paths,
distinct from hand-drawing) remains a real, uncovered use case if wanted
later. Decision: not worth resuming as-is — reconciling 277 commits of
drift against code that's already known-broken in the one part that was
attempted is closer to a fresh build than a resume. The branch is left in
place, untouched (deleting it is Kent's call, not this pass's to make
unilaterally); if the underlying need resurfaces, treat it as a fresh
plan against current `main` rather than a rebase of this branch.

Prior update below, still 2026-08-07:

**Last updated:** 2026-08-07 — the Layers panel (`DigitizePanel.svelte`)
gained a Sequencer view: a collapsible, color-block-grouped alternative to
the plain per-shape list — one row per color/thread carrying its swatch,
member count, and sew-index span, with block-level "sew this color
earlier/later" buttons. Prompted by Ember Design's own "Sequencer: Colors"
panel, but the promoted backlog item was specifically that cross-color
sequencing had zero geometric-adjacency signal — checked directly, not
assumed: `layer`/`sew_order` were ALREADY fully wired `shape_overrides`
with working per-shape UI controls (`moveShape`/`moveShapeWithinLayer`),
so this landed as presentation-only, no new backend plumbing. The
block-level reorder (`moveBlock`) swaps two whole blocks' layer numbers in
one batched override patch — one undo step, same convention every other
edit in this panel follows. Better-than-Ember, not just parity: the
header surfaces `trims_per_1000`/`TRIM_HEAVY` from `preflight.py`'s own
report, computed server-side every job but never previously shown
anywhere in the Studio (confirmed via grep before writing a line of UI) —
exactly the number a user reordering color blocks needs and Ember's
equivalent panel has no counterpart for. The Layers-list sort/grouping
logic (`effLayer`, `sortShapes`, `effSewOrder`, `layerSiblings`, `effRgb`,
plus the new `groupIntoBlocks`) moved from component-local functions into
`digitizer.js` as named exports, the same place `reorderWithinLayer`
already lived — one implementation to test and keep in sync with the
override contract, not two. 12 new pure-logic tests plus live-browser
verification: ran a real image through the real local digitizer service,
expanded the Sequencer, reordered two color blocks, confirmed the visual
order and swatch/count/span data updated correctly, and confirmed one
Undo fully reverted the block swap. Branch `color-block-sequencer-ui`.
Doesn't move area 3's Status/Confidence verdict (additive UI over an
already-shipped, already-tested override contract, not a quality or trust
finding).

Prior update below, still 2026-08-07:

**Last updated:** 2026-08-07 — fill angle selection (`stage6_fill.py`)
gained a 16-candidate-angle sweep for the auto case (no explicit
per-shape/global/comp-axis override): `best_fill_angle_deg` tries 16 evenly
spaced row directions PLUS `principal_angle_deg`'s own answer and keeps
whichever cuts the shape into the fewest monotone columns (`_columns`),
the same "enumerate candidate angles, minimise fragment count" method the
expired Goldman/SoftSight patents disclose (docs/masters-teardown-2026-08
-01.md's gap **G3**, closed by this pass). `principal_angle_deg` alone
already gets this right for anything with a real long axis — the gap was
specifically shapes where the plain PCA angle is technically correct (a
real long axis by area) but a bad row direction for the shape's actual
structure: measured on a synthetic diagonal staircase of overlapping
squares, PCA's 45deg axis sews as 13 columns while the sweep's chosen
near-perpendicular angle sews the same shape as 1. Including PCA's own
angle as a candidate means the sweep can only tie or beat it, never do
worse — confirmed by a dedicated regression test, and by the fact the
**entire 937-test Python suite passes unchanged** except one fixture
(`test_run_tier.py`'s empty-fill rescue test) that had to pin its angle
explicitly rather than rely on a specific angle failing to fill, since the
whole point of this change is that fewer angles fail to fill now. Branch
`fill-angle-candidate-sweep`. Doesn't move area 1's Status/Confidence
verdict (a fill-quality improvement within already-shipped, already-tested
technique, not a new capability or a trust finding).

Prior update below, still 2026-08-07:

**Last updated:** 2026-08-07 — manual (hand-drawn) shape authoring
(`ManualPanel.svelte`) gained curved as well as straight-line edges: drag
the small handle at any edge's midpoint to bow it into a quadratic curve,
drag it back to straighten it — live during drafting and retroactively via
"Edit points" on a finished shape. Prompted by directly observing Ember
Design's own manual digitizing tool (draw curved/straight lines, satin-fill
the closed shape) — and confirms something already suspected: EMB-Bot's
satin/fill machinery already derives rails/caps from ANY closed polygon via
medial-axis skeletonization, so the missing piece really was just the
curve-drawing UI, not new stitch-generation capability. Curves are stored
as their own sparse per-shape field (`shape.curves`, a segment-index →
quadratic-control-point map) and only ever flattened to plain points at the
`shapesToRegions` hand-off boundary — `manual.py`, the Python pipeline, and
the stitch engines never need to know a curve exists; a shape with no
curved segments flattens to byte-identical output, so this is a no-op for
every design that predates the feature. Branch `manual-shape-curve-tool`.
30 new tests (22 pure-geometry cases in `manualShapes.spec.js`, 8
component-level drag-gesture cases in `ManualPanel.spec.js`), covering the
live-preview-follows-cursor curve math, straighten-by-dragging-back-to-
center, edit-mode re-curving, the self-intersection gate running against
the FLATTENED (not raw-anchor) geometry, and Undo point correctly dropping
a curve bound to a now-removed segment. Verified live in a real browser,
not just tests: drew a curved shape, fill-stitched it, satin-stitched it,
and re-curved a different edge after finishing — all client-side, no
backend needed. Full detail in area 3 below, in the paragraph starting
"**Manual shape drawing gained curved edges, 2026-08-07**".

Prior update below, still 2026-08-07:

**Last updated:** 2026-08-07 — streamline fill (`stage6_streamline.py`,
photo plan technique row 10) gained a per-shape review-screen override
(`shape_overrides[sid].tier == "streamline"`, contract v1.6), the same
mechanism `tier == "sketch"` already uses — closing an item raised by
Ember Design competitor research (their equivalent "Streamlines" fill ships
as a generic, per-shape pattern choice, not photo-only). Branch
`streamline-fill-flat-lane-override`. Full before/after, the direction-field
design decision (reuse the existing raster/structure-tensor field
unchanged, rather than build a new shape-geometry/medial-axis field — and
why `manual.py`'s genuinely raster-less shapes deliberately do NOT get this
technique), and the full test list live in area 1 below, in the paragraph
starting "**Streamline fill grew a per-shape form, 2026-08-07**".
Backend-and-Studio-UI-complete for this specific ask (a one-line
`DigitizePanel.svelte` dropdown addition, matching Sketch's already-shipped
pattern) — nothing stubbed. Area 1's Status/Confidence verdict is unchanged
by this pass (additive wiring on an already-shipped, already-tested tier;
not a quality or trust finding).

Prior update below, still 2026-08-07:

**Last updated:** 2026-08-07 — documentation-only pass, no code changed:
recorded that session's (2026-08-07) competitive research against Ember Design
(`emberdesign.net`) as a new cross-cutting backlog item (see "Ember Design
competitive research" below) rather than folding it into any capability
area's status, since none of it changes what's built or how much it's
trusted today. Full evidence trail: `docs/emberdesign-competitive-research-
2026-08-07.md`.

Prior update below, still 2026-08-07 — the `summit_badge.png` black-complex
regression the SLIC -> SEEDS superpixel swap shipped as a documented,
`xfail(strict=True)`-marked defect (see that entry further down, kept
verbatim) is **RESOLVED**, by a new mechanism rather than by any retuning of
the `AREA_RATIO_*` constants that pass had exhausted. Branch
`seeds-boundary-contrast-fix`.

**The prior pass's stated root cause was wrong, and that is why the fix was
findable.** It concluded the black complex is destroyed by "a CHAIN of small,
comparable-size, progressively-diluted edges ... never presenting ONE large-
ratio edge for this constant family to catch". Re-instrumenting every merge
`merge_hierarchical` performs on the fixture (1,052 of them, logging live
foreground pixel counts, raw dE00, and how much source-black pixel mass each
side carries) shows the opposite: the 129 majority-black SEEDS superpixels DO
consolidate with each other first, and the complex is destroyed by ONE
identifiable merge, the 1043rd — **65,467 px (49,369 source-black, mean Lab
L\*=11.4) into 348,309 px (214 source-black, L\*=31.1), at dE00 16.06** under
the 26.0 threshold. Area-ratio protection missed it not because no single
large edge existed, but because that edge's size ratio is **5.3** — nowhere
near the 18.0 an extreme-mismatch guard looks for. It is a big-into-big
merge, which `_area_ratio_factor` is blind to by construction, and lowering
its ratio far enough to see a 5.3 necessarily catches ordinary comparable-
size band consolidation everywhere else. That is exactly the drone_render /
gradient-ramp breakage the prior pass measured. The constant family was
never the right tool; no value of it is.

**The new mechanism: boundary contrast.** `merge_hierarchical` compares
region MEAN colors, which cannot distinguish "two halves of one continuous
gradient, cut at an arbitrary interior position" from "two different design
elements meeting at a drawn edge" when both pairs of means sit ~16 dE00
apart. `stage2_photo_segment` now measures, once per superpixel pair, the
mean per-pixel-pair Lab distance across the pair's actual shared boundary,
and carries it through merges as a length-weighted sum (exact, not an
approximation — skimage's `RAG.merge_nodes` leaves both constituent edges
readable at recompute time). Measured on the final large merge each tuning
fixture performs:

| fixture / merge | raw dE00 | boundary contrast |
|---|---|---|
| `gradient_ramp_linear` (final merge) | 16.09 | 0.54 |
| `gradient_ramp_radial` (final merge) | 15.88 | 0.64 |
| `summit_badge` (merges 1035/1037) | 11.1 / 12.7 | 0.46 |
| `summit_badge` (merge 1043 — destroys the complex) | 16.06 | **31.31** |
| `drone_render` (merges 854-943) | 14.8-23.8 | 18.5-39.7 |

A ~50x separation, not a marginal one. An edge whose boundary is genuinely
hard AND whose smaller side is a substantial share of the design's own
foreground gets a locally tighter threshold — the same "divide the weight"
dual `FACE_MERGE_FACTOR` and `AREA_RATIO_MERGE_FACTOR` already use.

Real before/after, full pipeline (`run_stages`, the same F4 metric every
retune in this module has been measured against):

| fixture | before (shipped main) | after |
|---|---|---|
| `summit_badge.png` dark-area recovery | **9.1%** | **106.9%** |
| `drone_render.png` regions | 74 | **74** (unchanged) |
| `gradient_ramp_linear.png` regions | 2 | **2** (unchanged) |
| `gradient_ramp_radial.png` regions | 2 | **2** (unchanged) |

Every other photo-path fixture in the repo is **bit-identical** with the
mechanism on vs. off, checked directly rather than assumed:
`enthusiast_logo.png` 31, `fur_ramp.png` 8, `region_blobs.png` 3,
`repro_gradient_white_icon.png` 19, `photo_scene_stub.png` 24,
`photo_subject_stub.png` 1. The fix is surgical by design, not incidentally.

**Honest accounting of the margins**, because they are not uniform. The
boundary-contrast gate itself is robust: swept 1.0-32.0, every value from
1.0 to 25.0 gives identical results, and the real window is bounded by the
fixtures at (0.64, 31.31] — the shipped 6.0 sits ~10x clear of one edge and
~5x of the other. The merge factor is expressed as `13.0 /
MERGE_DELTAE00_THRESH` (the `FACE_MERGE_FACTOR` precedent — the absolute
13.0 dE00 is what must stay under the fixture's 16.06, so it must not drift
if the base threshold moves again); swept 0.2-0.7 as a raw ratio, flat from
0.2 through 0.6 and collapsing at 0.62, and 0.5 is chosen mid-window with
~19% margin below the 0.6177 cliff. **The size gate is the weak one**: the
smaller side must be >= 9% of the design's foreground, and the measured
window is (0.074, 0.113] — a ~1.5x gap defined by two fixtures. What makes
it safe despite that is structural rather than numerical: a region must be
>= 9% of the foreground to be protected at all, so at most ~11 regions in
any design can ever be, and the mechanism therefore **cannot add more than
~10 regions to any design's final count**. It structurally cannot reproduce
the 122-region blowout the prior pass's area-ratio re-derivations caused,
because those fired on unboundedly many small regions. A fixture landing the
wrong side of 0.09 loses the protection and degrades to exactly today's
shipped behavior — the safe direction.

A third discriminator (each region's internal Lab colour spread: flat design
content 6.7-8.9 vs. drone_render's textured 13.7-26.1) was measured, works
equally well at a gate of 10.0-12.0, and was **rejected and recorded** in the
constant's docstring so it is not re-derived: it needs a new per-node
sum-of-squares attribute maintained through every merge, its window is no
wider, and it has no equivalent of the bound above.

`test_summit_badge_black_complex_survives_full_pipeline` is a real passing
assertion again — the marker removed because the bar it guards is met by
measurement, not because the regression was reinterpreted as acceptable.
Three new tests pin the mechanism itself (the constants, the ~50x contrast
separation on a synthetic ramp-meets-block fixture, and that the
length-weighted recombination survives a real `RAG.merge_nodes` call).
Targeted suites green: `test_stage2_photo_segment.py` + `test_face_priors.py`
+ `test_flat_lane_byte_identical.py` + `test_palette.py` + `test_pipeline.py`
(69 passed, **0 xfailed** — down from 1), `test_background_removal.py` +
`test_stage6_blend.py` + `test_preflight.py` (88 passed, 2 pre-existing
skips). Cost: ~31 ms on a 900x900 / 1,072-superpixel fixture.

**Confidence for the photo-path segmentation swap: raised from LOW to
MEDIUM.** The blocker named in the entry below ("do not raise this rating,
and do not merge the branch, until the `summit_badge.png` regression above is
actually resolved with real numbers behind the fix") is met on its own terms.
Not raised past MEDIUM, and deliberately: the size gate's ~1.5x margin is
calibrated against two fixtures, and the mechanism has only ever been
observed to fire on one of them, so its behavior on unseen content is
bounded and argued-for rather than broadly demonstrated.

Prior update below, still 2026-08-07 — fast follow-up to the `BACKGROUND_ENCLOSED`
bulk-restore banner (area 1, "Auto-digitizing quality" — see that section's
own entry below for the original fix): an adversarial review (`emb-bot-
reviewer`) of the merged diff found the new banner's exclusion of already-
converted text-cluster members (`textConversions`) was correct, but the
pre-existing PER-ROW "Sew it" button sitting right next to it in the same
unstitched-row branch had no such guard — clicking it on a converted
cluster member silently restores stitching for a shape a *different*
feature already replaced with a real text element, with no visual warning
(the "restored" badge only fires off the server's own `stitched` field,
which a cluster conversion's client-only override never touches). Proven
live against the real service, not just reasoned about: converting a
14-member cluster on the `enthusiast_logo.png` benchmark left all 14 with a
fully clickable "Sew it" button and the same misleading "enclosed area"
tooltip. This diff pre-dates the fix, so it never shipped to `main` in the
broken state — caught before merge, not a live regression. Fix:
`DigitizePanel.svelte` gains a shared `isClusterHidden(row, conversions)`
helper, used by both the banner's `unstitchedRows` filter (already correct)
and a new `clusterHidden` per-row const that now gates the per-row "Sew it"
button and label — a cluster-hidden row shows "hidden — converted to text"
pointing at the cluster bar's own Undo control instead. New regression
coverage in `text-cluster-convert.spec.js`: after converting a cluster, the
`Sew it` button count must equal only the pre-conversion baseline (real
enclosed-background rows, if any) and the bulk banner's live count must
exclude the converted members too — verified against the real service,
2/2 relevant e2e specs pass in isolation (the same environmental
worker-contention flake noted in the original entry reproduces when run
back-to-back with other heavy specs and is unrelated to this change).
Studio unit suite 435/435, `vite build` clean. Two smaller review findings
also closed same pass: a stale "not yet verified" sentence directly
contradicting the original fix's own new paragraph (self-resolved once
this branch was restarted from `main`, which already carried that doc fix
separately) and `.dgp-enclosed-banner`'s background swapped from a bare hex
literal to `var(--warn-bg, #fdf6e3)` for consistency with the rest of the
file's color-token convention.

Prior update below, still 2026-08-07: `stage2_photo_segment`'s superpixel
oversegmentation step (photo plan step 1, every photo/gradient-classified
design's segmentation entry point) swaps `skimage.segmentation.slic` for
`cv2.ximgproc.createSuperpixelSEEDS` (branch `seeds-superpixel-swap`, draft
PR against `main`, **not merged — do not treat this as shipped**). Motivated
by a standalone benchmark (superpixel algorithm isolated as the only
variable, every downstream step — RAG construction, area-ratio protection,
merge, CC split, min-area floor — held byte-identical) that measured SEEDS
producing 2-4x tighter boundaries than SLIC at matched region counts on the
two real busy fixtures this module's own test suite already tracks.

Real before/after, full pipeline (`run_stages`, `len(PipelineResult.
regions)`, the same F4 metric this module's threshold retunes have always
been measured against):

| fixture | SLIC (old, thresh=20.0) | SEEDS (new, thresh=26.0) |
|---|---|---|
| `drone_render.png` | 65 | 74 |
| `summit_badge.png` | 30 | 39 |
| `gradient_ramp_linear.png` | 2 | 2 |
| `gradient_ramp_radial.png` | 2 | 2 |

Both busy fixtures land inside the 20-80 accept band with real headroom;
visually inspected via `debugviz.stage2_photo_merged` on both, boundaries
read clean (drone_render's lettering/foliage/fuselage edges are crisp, no
speckle). The flagged risk going into this pass — SEEDS' extra boundary
sensitivity over-segmenting a smooth gradient ramp — was checked directly,
not assumed, and did NOT materialize: both ramps hold at their SLIC-era
counts across the whole threshold sweep tried (18.0-35.0), never exceeding
2 regions. `MERGE_DELTAE00_THRESH` moved 20.0 -> 26.0 (SEEDS' raw output
fragments WORSE than SLIC's at the OLD threshold — 106 vs 65 regions on
drone_render at 20.0 — the opposite of the benchmark's own framing that
SEEDS would need a less-aggressive merge; measured directly via a real
two-fixture sweep that the threshold had to move UP, not down).
`FACE_MERGE_FACTOR` re-derived as `5.0 / MERGE_DELTAE00_THRESH` (was a
hand-typed `0.25`) so the face-local absolute merge tolerance stays pinned
at 5.0 dE00 regardless of the base threshold, the same decoupling
`AREA_RATIO_PROTECT_THRESH` already established as precedent one retune
ago; `test_face_local_threshold_splits_shades_that_merge_outside_a_face`
confirms the absolute number held.

**[RESOLVED 2026-08-07 later the same day — see this document's own latest
entry at the top for the fix, its mechanism, and its real numbers. The
paragraph below is the original pass's record of the defect and is kept
verbatim; two of its claims (the "chain of small edges" root cause, and the
implication that this constant family needed re-deriving) are now known to be
wrong — the top entry says exactly how.]**

**KNOWN, MEASURED, UNRESOLVED REGRESSION — why this ships as a draft PR
and should NOT be merged as-is.** `summit_badge.png`'s black ring/inner-
circle/crosshair complex — real design content a prior PR (`AREA_RATIO_
PROTECT_THRESH`) fixed from ~1% to 83.7% area recovery — regresses hard
under SEEDS, to ~9-11% recovery, confirmed both numerically (`dark_area_mm2`
vs. source blackish-pixel area) and visually (`debugviz.stage2_photo_
merged`: the ring's own black stroke is almost entirely absent, only a
short arc and the crosshair needle survive dark). Root cause, measured not
guessed: under SLIC the complex consolidated into ONE large coherent RAG
node before ever facing the background — a clean big-vs-big size mismatch,
exactly what `AREA_RATIO_PROTECT_THRESH` guards. Under SEEDS the same
complex starts fragmented into ~150-260 much smaller (~750-800px)
superpixels, and the hierarchical merge walks a graduated CHAIN of small,
comparable-size, progressively-diluted edges from black to background —
never presenting the one large-ratio edge area-ratio protection is built to
catch. Every re-derivation attempted this pass — lowering `AREA_RATIO_MIN_
SMALL_PX` alone (200-1000, recovery stayed flat at ~9-10%); lowering it
together with `AREA_RATIO_PROTECT_THRESH` and a much more aggressive
`AREA_RATIO_MERGE_FACTOR` (recovery DID recover, to ~99-107%, but at the
cost of pushing `drone_render.png` to 122 regions — through the 80-region
ceiling `MERGE_DELTAE00_THRESH` was tuned against — and `gradient_ramp_
radial.png` to 8, toward the over-segmentation risk this same pass ruled
out elsewhere) — either failed to move recovery or fixed it by breaking
other already-validated behavior. No combination found cleanly decoupled
"protect this one real complex" from "keep allowing legitimate small-into-
large absorption broadly" the way the original SLIC-era tuning did.
`AREA_RATIO_PROTECT_THRESH`/`AREA_RATIO_MERGE_FACTOR`/`AREA_RATIO_MIN_
SMALL_PX` therefore ship UNCHANGED (18.0/0.6/1000) — the full investigation
trail lives in that constant's own docstring in `stage2_photo_segment.py`.
`test_summit_badge_black_complex_survives_full_pipeline` is marked
`xfail(strict=True)` (not deleted, not weakened, not silently lowered) so
this stays a live, visible regression marker — a future fix that resolves
it will flip the test to an unexpected pass, which pytest reports loudly.

**Confidence: LOW for this specific change, unresolved.** The core
algorithm swap measurably helps general busy-photo fragmentation
(`drone_render.png`) and does not regress gradient-ramp behavior — real,
validated wins. It is NOT safe to treat as a drop-in SLIC replacement across
all photo/gradient content: specifically, thin/high-contrast detail sitting
on a large similar-toned background (`summit_badge.png`'s own failure
shape) loses real design content that a previous fix restored. Full
targeted suite green otherwise: `test_stage2_photo_segment.py` (35 passed,
1 xfailed — the known regression above), `test_face_priors.py` (folded into
the same run), `test_flat_lane_byte_identical.py` + `test_palette.py` +
`test_pipeline.py` (30/30, confirming the flat/gradient golden lane and
unrelated pipeline stages are untouched), `test_background_removal.py` +
`test_stage6_blend.py` (both touch this module, both green). Do not raise
this rating, and do not merge the branch, until the `summit_badge.png`
regression above is actually resolved with real numbers behind the fix —
not just re-flagged as acceptable.

Prior update below, still 2026-08-07:

**Last updated:** 2026-08-07 — Kent's own real-world upload of the
Instagram icon (gradient rounded-square background, white camera-glyph
linework) still showed "white space, not clean crisp edges" even after the
`BACKGROUND_ENCLOSED` restore mechanism verified directly below. Not a new
geometry defect: investigated first via `digitizing-quality-auditor` to
check Kent's own diagnosis (adjust overlap/pull-comp/density/underlay,
standard commercial-digitizing knobs) against the codebase's own history —
all four are already tuned for this art class (Laws 22/23/26/27-29,
appliqué cover pull-comp #72, border seam-sharing #73) and untouched by
this complaint. Root cause confirmed by direct reproduction against HEAD
(`stage1_prep.py::prep` on `testdata/photo/repro_gradient_white_icon.png`,
essentially this fixture): the white camera-glyph lines are the same white
as the page background, so `tag_enclosed_background` correctly flags them
`enclosed_background` (the same logic that correctly leaves an "O"'s
counter unstitched) and `pipeline.py` holds them unstitched by default —
real, deliberate behavior (see the `BACKGROUND_ENCLOSED` bullet in area 1
below), but the only way to fix it was clicking "Sew it" once per shape on
a dimmed list row, easy to miss entirely.

Asked Kent directly (a real product tradeoff, not a mechanical call):
auto-restore large enclosed areas by default (zero clicks here, but risks
silently filling a genuinely-intended hole on some future design) vs. keep
today's safe per-shape default and make restoring fast/obvious instead. He
picked the latter. `DigitizePanel.svelte` gains a loud `.dgp-enclosed-banner`
(replacing the old plain-text warning bullet) showing a live count plus a
"Sew all N" bulk action (`restoreAllUnstitched`) — one merged
`shapeOverrides` patch, not a loop (looping would clobber itself against
the same stale `element` prop across iterations, the pitfall
`undoTextConversion` already documents and works around). Deliberately
excludes any row belonging to a cluster already converted to text via
`textConversions` — that row's `stitched:false` is a permanent hide from
the text-cluster feature, not a default this banner should ever offer to
undo. Per-shape default behavior is otherwise byte-for-byte unchanged: a
genuine small enclosed hole still holds out by default exactly as before.

Verified against the real digitizer service + browser, not just unit-level:
`app/e2e/digitize-background-enclosed.spec.js` gained a second test driving
the bulk path end to end (banner shows the live count, "Sew all N" restores
every enclosed region on the repro fixture in one click, Apply re-stitches
all of them through the real service) and the existing single-row test's
assertions were updated for the new banner; both pass
(`npx playwright test e2e/digitize-background-enclosed.spec.js`, 2/2, plus
the sibling `digitize-boundary-edit`/`digitize-shape-identity`/
`digitize-stale-edits`/`text-cluster-convert` specs re-run clean to confirm
no shared-component regression). Studio unit suite: `npx vitest run`
435/435 (28 files). `npx vite build` clean. Engine and digitizer suites
untouched by this pass (pure Studio UI change, no `src/` or
`digitizer_core/` edits) and not re-run.
**Last updated:** 2026-08-07 — `stage6_satin.py`'s "E missing its
bottom-left corner" defect (root-caused, deliberately left open by PR #77 —
see this doc's own 2026-08-06 entry below) is now root-caused for real and
FIXED. Re-verified fresh before touching anything: rendered `photo/
enthusiast_logo.png` at 90mm via `debugviz.stage6`, confirmed by direct
render inspection that the defect is still present on current `main`
(PRs #77-#80 all merged, none touched this) — a visible gray gap between
the satin and the underlay's own boundary trace at the glyph's flush
corner. Also re-checked the "N" PR #77 flagged as possibly-short: its satin
coverage bounds now match its polygon bounds to within 0.008mm on every
side — **not present**, confirming the earlier independent re-measurement
this doc already noted.

**Real root cause, and it is NOT what PR #77's own investigation
suspected.** The junction machinery it named (`_extend_to_cap`,
`_retract_cap_corner`, `_merge_through_junctions`) is innocent: traced
directly, the stem's own medial axis welds through all three of the E's
T-junctions into one both-ends-free stroke exactly as designed, and
`_extend_to_cap` lands each of its two caps within 0.15mm of the glyph's
real corner. The actual bug is one step later, in `_short_stitch_guard`
(same file): the cross one station in from a cap is a real, keepable
stitch on its own (measured 0.57-0.60mm, comfortably over
`SATIN_MIN_CROSS_MM`'s 0.5mm floor) — but that station's same-rail step off
the cap is short enough to trip the guard, whose pull-toward-middle is
sized for a WIDE curve (35%, capped at an absolute 0.6mm — fine when a
cross is several mm) and, applied to an already-narrow cross, pulls it
under the floor. `satin_stroke`'s degenerate-cross filter then drops it a
few lines later for a reason that has nothing to do with why that filter
exists (an actual same-point pinch) — and the corner sews as bare fabric
even though the cap machinery it was blamed for did its job correctly.
Confirmed by direct instrumentation of the real code path (not a
reimplementation) on both the real fixture and an isolated synthetic
"E"-shaped polygon carrying the identical multi-junction topology, before
and after.

**Fix:** `_pull_short` (called from `_short_stitch_guard`) now bounds its
pull so it can never take a cross under `SATIN_MIN_CROSS_MM` itself — a
pull that would have landed the result below the floor lands AT the floor
(with a 1% margin so float rounding in the two `dist()` calls along the
way can't undershoot it) instead of past it. This is a general fix, not a
per-letter patch: it changes one shared helper every satin column's
short-stitch guard already goes through, for the specific case (a
near-floor cross whose same-rail step is short) that is possible at ANY
cap zone, corner, or tight curve — not gated on being near a junction or a
specific shape. Blast radius acknowledged honestly: this touches the
short-stitch guard's behavior for every satin shape in the app, satin
being `stage6_satin.py`'s whole reason for existing. What kept the change
narrow in practice: the new bound only ever binds when a pull would
otherwise cross the floor — a curve with real room to spare (the guard's
normal case, crosses several mm wide) never reaches it, so it is a no-op
there by construction, not by luck.

Visual re-verification, same method as the reproduction: the fixture's
"E" now shows a stitch landing 0.32mm from its flush corner (was 0.59mm) —
closer to the true vertex, not a residual gap eliminated to zero (a
mathematical corner is a zero-width point; no satin cross can land exactly
on it without becoming the same kind of degenerate stitch the guard
exists to prevent). Before/after crops of the corner, rendered directly
from the real polygon and the real `satin_shape` output (not the
composite debug render, for a distraction-free comparison), confirm the
gray gap visibly closes. The glyph's OTHER flush corner (bottom bar) was
already inside the floor before this fix (0.36mm both before and after —
a different station's parity happened not to trigger the guard there) and
is unchanged, not a follow-up gap: a pre-existing non-issue this pass
confirmed rather than assumed. One labeling caveat, stated plainly rather
than glossed over: "top"/"bottom" here is this pass's own render
convention (y-down, verified against a labeled direct render of the
glyph, not assumed) — which of the E's two flush corners Kent's own eyes
called "bottom-left" when he first reported this cannot be cross-verified
without his original screenshot. What IS verified: a genuine,
reproducible flush-corner coverage gap, with the exact symptom described
(bare fabric against the underlay's own boundary trace) and the exact
geometry described (a stem crossing multiple T-junctions), was found and
fixed on this glyph.

New regression tests, `tests/test_satin.py`: a synthetic `E_LETTERFORM`
polygon (proportions taken directly from the real fixture's own vectorized
"E", translated to the origin) plus `test_a_stem_crossing_three_junctions_
welds_into_one_stroke` (confirms the fixture actually exercises the
multi-junction topology before trusting the second test) and
`test_stem_free_end_reaches_its_own_flush_corner` (the coverage
regression; fails on pre-fix code at 0.59mm, passes post-fix at 0.32mm —
verified failing on the reverted code, not just passing on the fixed one).
Targeted suites green: `test_satin.py` **51/51** (49 existing + 2 new),
`test_flat_lane_byte_identical.py` **6/6**, `test_preflight.py`/
`test_stages.py`/`test_pushcomp.py`/`test_chaining.py` **169/169**
combined. Golden impact, checked by diff rather than assumed: only
`photo/enthusiast_logo.png`'s entry in `flat_lane_golden.json` moved
(regenerated the same way the doc's own prior precedent did — one key,
not a full re-run); `logo_whitebg.png`/`logo_alpha.png`/`ribbon_curve.png`
came back byte-identical. On the moved entry, `shape_ids`/`areas_mm2`/
`warnings`/`stitch_count` are all unchanged (2363 both before and after)
— only `stitch_coords` moved, and by a wide margin (1983 of 2363 entries),
which measured out as a benign downstream cascade rather than a new
defect: re-ran `preflight.run_preflight` on the same fixture before/after
and got the same score (88/B), the same single finding
(`TRIM_HEAVY`, essentially unchanged), and near-identical coverage metrics
(`coverage_max` 4.45 both, `coverage_area_mm2` 630→631) — consistent with
a few points' worth of real change early in one shape's sew order
cascading through Laws 27-29's structural entry-point selection for every
shape sewn after it, not with anything escaping its shape or overlapping
wrong. Three other fixtures (`logo_alpha.png`, `logo_whitebg.png`,
`ribbon_curve.png`) re-rendered and visually inspected: clean, no
starburst, no new gaps — `ribbon_curve.png` in particular is the fixture
`test_a_satin_free_end_does_not_fan_into_a_starburst` pins in detail for
exactly this guard's earlier, unrelated fix, and it still passes. Full
digitizer suite **not** re-run locally per this environment's own standing
caution (COOKBOOK.md); CI runs it on the PR.

**Last updated:** 2026-08-07 — closed the one remaining verification gap on
the `BACKGROUND_ENCLOSED` / opaque-alpha fix (area 1, "Auto-digitizing
quality"): watched it run through the real Studio browser UI via Playwright
MCP, not just the HTTP-level check PR #22 already had. Uploaded
`repro_gradient_white_icon.png` through the actual `+ Auto-digitize` file
input (the same canvas-re-encode path the opaque-alpha bug lived in),
digitized it against the real service, and confirmed visually: 4 enclosed
icon-linework regions held out by default as dimmed "not sewn — enclosed
area" rows (not dropped, not merged into neighbors), the canvas preview
showing them as literal unfilled gaps; clicked "Sew it" on one, applied, and
watched the real service re-stitch it (10,916 → 11,114 stitches, gap now
solid fill) while the other three stayed correctly held out. Screenshots
under `.playwright-mcp/background-enclosed-*.png`. No code change needed —
the fix already worked; see area 1's `BACKGROUND_ENCLOSED` write-up below
for the full account. Doc-only change, committed directly (see that
section's "CLOSED 2026-08-07" note for detail).

Prior update below, still 2026-08-07: `regularize_text_clusters` gains a third,
independent safety layer on top of the selective-regularization fix directly
below (PR #77, `fix-lettering-defects-hole-and-regularization`, still open/
draft, not yet merged to `main` — this work stacks on that branch; see "Not
yet merged" at the end of this entry): an OCR-confidence quality gate. The
two existing checks (`_REGULARIZE_SKIP_TOLERANCE`, hole-preservation) are
geometric PROXIES for "would this redraw read worse" — this measures it
directly. For every cluster member that clears both existing checks and is
about to be buffered, Tesseract (Apache-2.0; new `tesseract-ocr` system
package + `pytesseract` wrapper) scores the member's own rasterized crop
before and after the proposed skeleton-buffer redraw (`--psm 10`,
single-character mode); if confidence drops by >=20.0 points
(`_OCR_CONFIDENCE_DROP_THRESHOLD`), the buffer is discarded and the member
falls back to its original polygon — the same fail-open contract
`buffer_failed` already uses. Only a confidence NUMBER is ever read:
`pytesseract`'s decoded-text field (`data["text"]`) is never accessed
anywhere in this module — verified both by code inspection and by a
regression test that makes the decoded-text field raise `AssertionError` if
anything ever touches it (`tests/test_ocr_gate.py::
test_ocr_confidence_never_reads_the_decoded_text_field`).

Threshold calibrated on real measurements, not assumed. On the real
benchmark fixture (`enthusiast_logo.png`'s 14-member subline, 90mm), the ONE
member PR #77's existing checks let through to the buffer (the +30%-off
"I") drops from 77.0 to 0.0 confidence — Tesseract finds no text at all in
the buffered crop, a 77-point loss this gate now catches and blocks. A
broader real calibration set (font-rendered glyphs E/F/H/I/L/N/S/T/Z, DejaVu
Sans Bold, individually perturbed in stroke width so each clears
`_REGULARIZE_SKIP_TOLERANCE` on its own) measured six more real buffered
examples: three clearly damaging (-49, -27, -26 points), one borderline
(-20), one mild/still-fine (-5), one genuine improvement (+11, correctly NOT
blocked). 20.0 sits between the largest real "still fine" delta (-5) and the
smallest real "genuinely damaged" one (-20). Full evidence trail, both
calibration sets, and every constant's reasoning: `digitizer_core/
textcluster.py`'s "OCR-confidence quality gate" module-docstring section.

New tests, real Tesseract, no system-font dependency (letters are hand-built
5x7 dot-matrix block glyphs — deterministic across machines/CI runners, not
a font file that may or may not be installed): `tests/test_ocr_gate.py` (6
new — a real "fine" case, 93.0->92.0, gate does not fire; a real "damaging"
case, 92.0->0.0, gate fires and falls back to the original polygon; OCR
unavailable fails open; exact threshold boundary pinned with mocked values;
two tests proving the decoded text is never touched). Two of PR #77's own
tests now correctly isolate this new layer via the same no-op-patch pattern
`test_pipeline.py` already used to isolate `regularize_text_clusters`
itself: `test_textcluster.py`'s two bare-rectangle variance/area tests
(rectangles carry no real letterform content for Tesseract to read, before
or after) and `test_pipeline.py`'s full-pipeline variance test (whose real-
fixture "after" run now patches past the gate for the same real member the
gate legitimately blocks — that block is `test_ocr_gate.py`'s job to cover
directly, not this test's). Targeted suites green: `test_ocr_gate.py`
(6/6), `test_textcluster.py` (15/15), `test_pipeline.py` (12/12),
`test_stages.py` (15/15), `test_satin.py` (49/49), `test_service.py -k
text_cluster` (1/1). Full digitizer suite not re-run locally (this
environment's own standing caution, see COOKBOOK.md); CI runs it on the PR.

No isolation needed (unlike `rembg_isolated/`): `pytesseract`'s only deps
are `packaging`/`Pillow`, both already present in `requirements.txt` — no
numpy/numba conflict, confirmed via `pip show pytesseract` before adding it
to the shared venv. System `tesseract-ocr` install step added to CI's
`digitizer` job; documented in `digitizer/README.md`'s "Setup" alongside
`rembg_isolated/`'s own system-dependency note.

**Not yet merged:** this lands on branch `text-cluster-ocr-confidence-gate`,
stacked on PR #77's own branch (`fix-lettering-defects-hole-and-
regularization`) since the `_REGULARIZE_SKIP_TOLERANCE`/hole-preservation
mechanism this extends is not on `main` yet. Opened as a draft PR against
`main`; its diff will show both PRs' changes combined until #77 merges
first, at which point it collapses down to just this one.

Prior update below, still 2026-08-06: Kent looked at a real rendered
stitch-out of the benchmark fixture (`enthusiast_logo.png` at 90mm) and
reported 5 concrete
letterform-fidelity defects. All 5 were reproduced first (`debugviz.stage6`
render, visually inspected, not inferred from stats) before touching any
code — the working hypothesis going in (all 5 traced to `textcluster.py`'s
regularization) turned out to be **half right**: the investigation found
THREE separate root causes, not one, and this pass fixes two of them, leaving
the third open and documented rather than rushing a wide-blast-radius patch.

- **Subline "ENTERPRISES INC" garbled/illegible — FIXED.** Root cause really
  was `textcluster.regularize_text_clusters`, but not the mechanism assumed:
  it redrew EVERY tagged cluster member's polygon as a skeleton-buffer,
  unconditionally, even members whose own geometry was already fine.
  Measured on the real 14-member subline cluster: 13 of 14 members' own
  pre-regularization stroke half-width already sat within +-11% of the
  cluster's shared target (only one real outlier, at +30%) — the
  unconditional buffer was replacing already-good vectorized letterforms
  with a cruder approximation for zero consistency gain, and a skeleton-LINE
  buffer structurally cannot reproduce a real interior hole (3 of the 14
  members — R/P-style counters — lost theirs). Fix: `regularize_text_
  clusters` now skips a member (leaves its polygon untouched) when its own
  measured stroke half-width is within 15% of the cluster's target
  (`_REGULARIZE_SKIP_TOLERANCE`), or unconditionally when its original
  polygon already carries a real interior ring — a line buffer is never the
  right primitive for a hole it never measured. A genuine outlier still
  regularizes exactly as before (proven both on the real fixture and a new
  synthetic unit test). Full evidence and the module's new "Selective
  regularization" section: `digitizer_core/textcluster.py`.
- **"A" missing its triangular counter — FIXED, and NOT a text-cluster bug.**
  Direct measurement showed the main wordmark's letters (including the "A")
  carry neither `rescued_small_shape` nor `text_candidate` — they never go
  through `textcluster.py` at all, which falsified half of the working
  hypothesis immediately. Real root cause: `stage3_segment.
  resolve_small_regions` treated a small but completely real enclosed hole
  — already correctly found by `Prep.enclosed_mask` at stage 1
  (2.08mm², comfortably above the sewable floor) — as ordinary segmentation
  noise and absorbed it into the "A" glyph's own ink (its only possible
  neighbor, since an enclosed hole's neighbor is always the shape enclosing
  it), erasing it before `stage4_vectorize.tag_enclosed_background`'s
  already-correct machinery ever got the chance to tag it as its own Region.
  Fix: `resolve_small_regions` takes an optional `enclosed_mask` (wired from
  `Prep.enclosed_mask` in `pipeline.py`) and protects any small region
  >=60% covered by it from absorption/drop — it still has to clear stage 4's
  own real-geometry floor to survive, same as any other kept mask. Confirmed
  interacting CORRECTLY, not colliding, with the separate same-day
  `satin-classifier-organic-shapes` DT-tightening fix (area 1 below): the
  "A" used to flip satin->fill specifically because it read as a solid,
  holeless, organic blob (exactly what that fix's DT check exists to catch)
  — restoring the hole makes it measure as the well-proportioned ribbon
  letterform it always was, and it correctly flips back to satin
  (`tests/test_satin.py` updated with the real evidence for both directions;
  visual re-render confirms clean parallel satin, not a starburst).
- **"E" missing its bottom-left corner / "N" reading short — ROOT-CAUSED,
  left OPEN. CLOSED 2026-08-07** — see this doc's newest entry at the top:
  the actual mechanism was not the junction/cap-extension machinery this
  entry's own investigation suspected (that traced out innocent), but
  `_short_stitch_guard`'s pull-toward-middle taking an already-adequate
  near-corner cross under `SATIN_MIN_CROSS_MM`. The "N" symptom is
  confirmed NOT present (coverage bounds match its polygon to 0.008mm).
  Original write-up kept below for the investigation trail. Confirmed real
  via direct render crops (bare unstitched
  fabric exactly where the underlay's own boundary trace shows the true
  polygon corner). Confirmed NOT a text-cluster or enclosed-hole defect —
  the wordmark's satin letters go through the ordinary `stage6_satin.py`
  column-generation path (`extract_strokes`/`satin_stroke`/`_rail_points`),
  which is used by every satin shape in the app, not this feature. This is a
  real, pre-existing gap in how a letterform stroke that passes through
  MULTIPLE T-junctions along its own length (the E's vertical stem meets 3
  horizontal bars) gets its rail/cap geometry built — evidence points at the
  interaction between free-end cap extension (`_extend_to_cap`/
  `_retract_cap_corner`) and the per-station width cap in `_rail_points`,
  but was not narrowed further. Deliberately NOT fixed in this pass:
  `stage6_satin.py` is the single largest, most heavily-tuned, most
  fixture-sensitive file in the codebase (1750 lines, referenced by every
  satin golden in the suite, several hard-won fixes already on record in
  this doc's own history), and a change there needs its own dedicated
  investigation and review pass, not a patch bundled into an unrelated
  feature's bugfix. Flagged here as a real, separate, still-open defect.

New regression tests: `tests/test_textcluster.py` (2 new + 1 rewritten to
match the corrected selective behavior — the old one asserted "every member
regularizes," which was the bug), `tests/test_stages.py` (1 new, the
enclosed-hole-survives-absorption case), `tests/test_satin.py` (1 rewritten
— the "A"'s satin/fill call flips as a correct consequence of the hole fix,
not a break). Targeted suites green: `test_textcluster.py` (15/15),
`test_stages.py` (15/15), `test_pipeline.py` (12/12, including both existing
text-cluster wiring tests), `test_satin.py` (49/49). **Not verified locally:**
`test_flat_lane_byte_identical.py` — `testdata/flat_lane_golden.json` is
pre-existing corrupted JSON at HEAD (confirmed via `git status`/`git log`
showing zero local diff on that file; unrelated to this pass, already
tracked by a separate in-progress fix per `git worktree list`), so it cannot
even be collected here, let alone regenerated. This pass's geometry changes
(the "A"'s hole, several subline members' polygons) almost certainly move
`photo/enthusiast_logo.png`'s golden entry once that file is fixed — flagged
explicitly rather than silently left for CI to discover. Full digitizer
suite NOT re-run locally per this task's own instruction (proven unreliable
in this environment); CI runs it on the PR.

Prior update below, still 2026-08-07:

**Last updated:** 2026-08-07 — `digitizer_core/textcluster.py`'s text-cluster
detector gains three classical-CV strengthening passes, all measured against
the real `enthusiast_logo.png` benchmark rather than assumed (area 1's
"Text-cluster detection" entry below has the full writeup): (1) three new
candidate filters — stroke-width coefficient of variation, aspect-ratio
bounds, and bbox-nesting exclusion — tightening `_candidates()`, which
previously compared only each shape's MEAN stroke half-width; (2) a Shape
Context descriptor (Belongie/Malik/Puzicha 2002, new module
`digitizer_core/shapecontext.py`, ~150 lines, no new dependency) wired into
`regularize_text_clusters` as a before/after glyph-plausibility gate — a
cluster member whose regularized redraw structurally diverges too far from
its own original shape (a corner blown out, a hole filled) is now skipped
instead of silently applied, same fail-open discipline as every other guard
in that function; (3) MSER (`cv2.MSER_create()`) was investigated as a
companion signal and deliberately NOT built — measured directly against both
the raw and prepped benchmark image, it returns zero regions everywhere,
because this module's whole domain (flat-lane, few-solid-color vector art)
structurally lacks the multi-level intensity gradient MSER's threshold-sweep
stability check requires; full reasoning in `textcluster.py`'s own "MSER"
docstring section. All three additions land on the SAME real benchmark
fixture's golden output byte-identical (`test_flat_lane_byte_identical.py`
still green) — none of the fixture's 14 real letters or its regularization
were false-positived by the new filters; the filters instead removed a class
of failure the fixture doesn't happen to trigger today (confirmed via direct
measurement on the fixture's own non-member fragments, not inferred). 30 new
tests (`tests/test_shapecontext.py`, new; `tests/test_textcluster.py`
additions), 222 total across the touched suites passing.

Prior update below, still 2026-08-06 — satin entry/exit point selection now follows
corpus laws 27-29 instead of pure nearest-point, closing the highest-value
item a `digitizing-quality-auditor` health check surfaced in the 2026-08-06 session (Kent
picked it explicitly over two alternatives it also proposed: border
seam-sharing, which needs a design sign-off on which shape wins a shared
edge before it can be built, and appliqué cover pull-comp, both still open).
Scored on 291 real professional decisions, `docs/corpus-laws-round3-
2026-08-01.md` found pros enter a satin stroke at its FREE end (the open
cap) 85.2% of the time, not whichever end is merely nearest the needle
(42.3% for that rule) — and will pay up to ~10mm of extra travel to reach
it (law 29), not more. `digitizer_core/stage6_satin.py` gains one new
helper, `_choose_stroke_entry(cur, a, free_a, b, free_b)`: when a stroke has
exactly one free end (the other welded into a junction by the existing
skeleton-weld machinery), entry prefers the free end unless the extra
travel over the nearer end exceeds the new `machine.
STRUCTURAL_ENTRY_BUDGET_MM = 10.0` (law 29's own measured cutoff), in which
case it falls back to nearest — unchanged from before. When both ends are
free (an isolated stroke) or both are junction-welded, there is no
structural signal to prefer and proximity alone decides, byte-identical to
the old rule — this is why the change's reach is narrower than "every
satin stroke": only strokes with exactly one free end are affected. Wired
into two call sites — `_order_strokes` (the sequencing simulation) and
`satin_shape`'s per-run reversal loop — but the reversal loop applies the
new rule ONLY to the visible satin column (`StitchRun` kind `SATIN`);
underlay runs keep pure-nearest orientation, since the corpus law was read
off real stitch files' visible satin entries, not hidden underlay, and
underlay orientation is already separately tuned to minimize inter-stroke
hops. **Not implemented:** law 28's finer end-CLASS ordering (cap > tee >
corner ~= butt) among junction ends specifically — that needs classifying
each junction end's own arm count/angle, which `Stroke` does not currently
carry (only the binary free/not-free distinction `extract_strokes` already
computes). Left as an explicit follow-up rather than guessed at.

Six new tests in `tests/test_satin.py`: four direct unit tests of
`_choose_stroke_entry` (prefers the cap within budget, exact-10mm boundary,
falls back past the budget, and both tie cases — both-free and
both-junction — fall back to pure proximity), plus two end-to-end tests via
`satin_shape` on synthetic T-junction polygons (a new short-stem
`T_SHORT_STEM` fixture proving the cap wins within budget; the existing
`T_SHAPE` fixture's 17mm stem proving the budget fallback still holds for a
real over-budget case). Golden impact, checked by diff rather than assumed:
`flat_lane_golden.json`'s `logo_alpha.png` and `photo/enthusiast_logo.png`
entries moved (both carry real lettering with free/junction-asymmetric
strokes) and were regenerated — deliberately, only those two keys, via the
same `snapshot()` function `tools/capture_flat_lane_golden.py` uses, not a
full re-run of that script — while `logo_whitebg.png` and `ribbon_curve.png`
came back byte-identical and were left untouched, matching the fact that
neither fixture has a qualifying stroke. `shape_ids`/`areas_mm2`/`warnings`
are identical before/after on both regenerated fixtures; only
`stitch_coords` moved (plus `stitch_count` on `enthusiast_logo.png`, 2431 ->
2454 — expected, since a different entry point reshapes travel-graph
routing between strokes). Full digitizer suite re-run to completion in the
foreground after the golden update: **867 passed, 3 skipped, 0 failed**
(1228s) — the 3 skips are the same standing container-environment goldens
this doc has tracked since 2026-08-03, deselected the same way CI does, not
new failures. Engine `node --test` re-run too: **283/283** (this doc's
267/267 figure was stale going in — more engine tests landed since it was
last written; not a regression, just catching the count up). `app/`
untouched by this change (confirmed via `git status`) and not re-run in
this environment (Studio's `node_modules` isn't installed here); carrying
forward the doc's last-verified Studio count rather than asserting an
unverified new one. Done directly on the session's own working branch, not
an isolated worktree — a solo, contained fix.

Prior update below, still 2026-08-06:

**Last updated:** 2026-08-06 — the satin/fill classifier's DT-tightening fix
(`satin-classifier-organic-shapes`, area 1 below), previously scoped to
`gradient`/`photo_subject`/`photo_scene` only on the premise that flat art's
boundaries are clean, is **extended to `design_class="flat"` too**: that
premise was empirically false, proven on this repo's own committed
`testdata/photo/enthusiast_logo.png` benchmark, where the flat-exempted rule
satin-stitched two real shapes into a literal starburst (confirmed by
rendering their actual pre-fix stitch coordinates). `is_satin_candidate`'s
`design_class == "flat": return True` early return is deleted; the DT check
(`_dt_regular_and_within_cap`, itself untouched) now runs unconditionally.
`flat_lane_golden.json` regenerated and structurally diffed — exactly the 2
predicted entries move (`logo_alpha.png`, `photo/enthusiast_logo.png`),
`logo_whitebg.png`/`ribbon_curve.png` stay byte-identical. Full detail,
exact measurements, and the pure-tightening safety re-proof (four
letterform archetypes still satin under `"flat"`) in area 1's "Satin/fill
classifier" bullet below.

Prior update below, still 2026-08-06: the "jersey_tee fill underlay"
follow-up this doc flagged as a low-priority candidate (area 1, below) is
investigated and **closed as declined, not a code change**: a direct
measurement (synthetic fill polygons at realistic sizes — 60x40mm, 100x70mm,
20x15mm — run through `digitizer_core.stage6_fill._underlay_paths`,
computing the real max distance from any interior point to the nearest
underlay stitch) shows `center_run` does NOT close the 13mm interior gap the
prior audit measured — it's statistically identical to `edge_run` (60x40mm:
19.04mm vs 19.02mm; 100x70mm: 34.02mm vs 34.01mm; 20x15mm: 6.58mm vs 6.11mm,
`center_run` actually *slightly worse* on the small shape). A single line
through the shape's principal axis is exactly as far from off-axis interior
points as a perimeter walk is; only a full grid/lattice pass (`edge_lattice`/
`edge_zigzag`) actually closes it, to 1.6-1.8mm regardless of shape size.
Even combining `edge_run`+`center_run` (a real corpus recipe, "Rg.Re") only
halves the gap on large shapes (9-17mm) — nowhere near lattice coverage. So
the flagged fix candidate would have been a no-op dressed up as a fix:
`jersey_tee` stays on `edge_run`, unchanged. The real closer (a lattice
pass) is exactly what corpus law 26 already found professional digitizers
rarely use under fills (7/507) and was the explicit reason `edge_lattice`
was removed as this fabric's default in the first place
(`docs/corpus-laws-round3-2026-08-01.md`) — so the 13mm gap reads as a
structural property of sparse running-line underlay on a large fill shape,
not a `jersey_tee`-specific misconfiguration, and law 26's own choice is
reaffirmed rather than second-guessed. Measurement script was a throwaway
scratchpad check, not committed — a one-off geometric verification, not
ongoing test coverage. No source file changed this pass.

Prior update below, still 2026-08-06: the "Evaluation corpus & harness"
cross-cutting gap (below) gets its harness half built: `digitizer/tools/
corpus_scorecard.py`, a `capture`/`diff` CLI that runs the digitizer's 14
committed `testdata/` fixtures through the already-existing
`preflight.run_preflight` scorer at two garment configs and remembers/diffs
the result — a standing, automated answer to "did this change make the
output better or worse" that this doc has flagged as missing since the
corpus-laws-23/26 pass. Shipped as a reporting tool, not a CI gate, on
purpose; the corpus half (`scratch_corpus/`) remains inaccessible and
untouched. Full detail in the cross-cutting section itself, not duplicated
here.

Prior update below, still 2026-08-05: the satin self-overlap defect this doc
has carried as an open callout since the corpus-laws-23/26 pass (area 1
below) is **FIXED**: `stage6_satin.py::_rail_points` now caps every satin cross's
per-station width to `machine.SATIN_MAX_WIDTH_MM / 2`, on top of the
existing local-corridor cap. Root cause, confirmed by direct spine
inspection (not assumed): `logo_alpha.png`'s `Sf5200f3f` carries a stroke
with BOTH ends free — no skeleton junction node on it at all — whose
half-width profiles as a smooth, single-peaked taper across all 36 of its
own stations (0.17mm at each tip, ramping continuously to 4.67mm at the
apex and back down). That is the shape's real medial-axis width, not a
measurement artifact; an initial "junction merged-footprint DT" hypothesis,
and a local-neighbourhood-outlier cap built on it, were both tried and
disproven (the outlier cap made zero difference, since a genuine continuous
taper has no isolated station to detect against). The fix instead reuses
`SATIN_MAX_WIDTH_MM` as a flat per-station ceiling — the same
corpus-validated cap the satin/fill classifier and `_stroke_underlay`'s
oversize skip (prior update below) already gate on, not a new number, so no
classifier-eligible column should need a wider cross regardless of why one
station reads wide. Measured on `Sf5200f3f`: eliminates all 2580
non-adjacent self-crossing rail-to-rail segment pairs and drops the shape's
own isolated coverage peak from 9.57 to 3.41 layers (design `coverage_max`
13.11 -> 3.24 at `target_width_mm=80`/`left_chest`). One real, minor
collision found and resolved: a synthetic `tests/test_pushcomp.py` fixture
(a 45x4.5mm bar) legitimately grows to 5.1mm under directional pull comp
(Law 22) and lost ~0.02mm of `rail_overhang` to the new cap — not a bug the
push-comp test exists to catch, so its fixture height moved 4.5 -> 4.0mm
with an inline comment explaining why, rather than loosening the cap to
route around an incidental collision. `flat_lane_golden.json` regenerated;
confirmed by structural diff that only the `logo_alpha.png` entry moved
(`logo_whitebg.png`/`ribbon_curve.png`/`photo/enthusiast_logo.png`
byte-identical). New regression coverage: `tests/test_satin.py::
test_satin_crosses_do_not_self_overlap_across_a_wide_junction` (direct
geometry, not just the aggregate coverage number) and `tests/
test_preflight.py::test_a_wide_oversize_satin_stroke_does_not_block_on_
underlay_glue`'s old `coverage_max > 10.0` floor — which existed
specifically to pin this defect as NOT yet fixed — is now inverted to a
`< 5.0` ceiling. Full digitizer suite re-run to completion in the
foreground: **852 passed, 3 skipped, 0 failed** (1136s) — 0 failures this
run, including the 3 container-environment goldens this doc usually
caveats as known-flaky, which passed clean here too. Engine/Studio
untouched by this pass (`git status` confirmed no `src/`/`app/` changes) and
not re-run, carrying forward their last-verified counts below rather than
re-asserting unverified numbers.

Prior update below, still 2026-08-05 — text-cluster detection + a regularized
lettering fallback landed across two PRs, #63 (merged: `textcluster.py`'s
geometry-only detection of text-like clusters among rescued small shapes,
pipeline wiring, the service's read-only `text_candidate`/`text_cluster_id`
review fields, geometric regularization via a skeleton-buffer redraw at each
cluster's shared median stroke width, and the Studio side — a "looks like
text" badge, a per-cluster "Convert to text" action, and undo) and #64
(open at time of writing: a real Playwright e2e run against the live
service, which caught and fixed a genuine bug, not a test mistake —
`ContentStep.svelte` forwarded `DigitizePanel`'s `converttotext` event up to
`App.svelte` but never wired the same forwarding for `removeelement`, so
undo silently never removed the created text element; fixed with the
missing one-line forward). No OCR anywhere in this slice — detection is
pure geometry (proximity, bbox-height and stroke-width similarity via the
same `ShapeField`/EDT machinery `stage6_satin` already uses), and nothing is
ever auto-substituted: converting a detected cluster creates a real,
**empty** text element with no font pre-picked, so a user always supplies
the actual word and typeface themselves. Full detail in areas 1 and 5 below,
and spec/plan at `docs/superpowers/specs/2026-08-05-text-cluster-detection-
design.md` / `docs/superpowers/plans/2026-08-05-text-cluster-detection.md`.
Verified per-step (not just at the end): digitizer full suite **851 passed,
3 skipped, 0 failed** (unaffected by the e2e-only PR #64 step, which touches
no Python source), Studio `vitest` **426/426**, and the new
`app/e2e/text-cluster-convert.spec.js` passing for real against the live
service and browser after the `removeelement` fix above. Also verified live
in a running Studio dev session against the real benchmark fixture
(`enthusiast_logo.png` at 90mm): the badge/action bar appears over the
14-shape subline cluster exactly as the Python-side pipeline tests predict.

**Also this pass: the cross-cutting "Evaluation corpus & harness" gap below
is newly tracked** (not a new capability area — this doc considered and
explicitly rejected splitting area 1 into separate "image analysis"/"stitch
planning" areas this same session, since they're pipeline stages of one
system, not separately shippable products) — see that section for why, and
for a correction to an external review's claims that this pass's own
research found inaccurate.

Prior update below, still 2026-08-05: corpus laws 23 and 26 landed for real
this pass, closing out the reverted attempt this doc has carried since the
last entry (see that entry's UPDATE note, area 1, for the historical account
of why the first attempt was backed out). Law 26: `fabrics.py`'s `pique_knit`/
`jersey_tee` `fill_underlay` moves `edge_lattice` -> `edge_run`, dropping
the crosshatch pass a fill doesn't need (corpus: 7/507 fills carry a
lattice underlay). Law 23: satin's own zigzag underlay pitch is no longer
implicitly shared with fill's — a new `machine.SATIN_ZIGZAG_PITCH_MM = 1.45`
constant (fill's lattice underlay keeps reading the old `UNDERLAY_ZIGZAG_MM
= 2.0`), wired into `stage6_satin.py`'s `_stroke_underlay()`, plus that
function's rail-narrowing factor `0.3 -> 0.09` (each zigzag leg now spans
0.82x the column width, corpus-measured, not the old 0.4x). The blocker the
first attempt hit — landing either law moves `machine.py`'s coverage-budget
thresholds' own self-fit ground truth — is resolved by recalibrating
`COVERAGE_WARN_UNITS`'s *methodology*, not its value: the old derivation
comment said "checked against what our own output actually produces" (self-
fit, circular); the new one re-derives 2.5 two ways that don't depend on
prior engine output — law 27's own prose figure for a safe classic stack,
cross-checked against law 28's underlay-cost figure (~0.1-0.2 units) computed
from the corrected engine's real underlay geometry (fill's generic zigzag
underlay prices at 0.4mm-thread/2.0mm-pitch = 0.208 units; satin's new
pitch at 0.4/1.45 = 0.283) — a classic stack lands at 2.21-2.28 units either
way, comfortably under 2.5 with headroom, not against it. The number did not
move; only its provenance did. `COVERAGE_BLOCK_UNITS` (3.5) is untouched on
purpose — the playbook tags it sew-out-gated, not desk-safe, still pending
Kent's physical stacked-fill-ladder test (`EMBBOT_SEWOUT_CARD.dst` block 2).
`STITCHES_CUTAWAY_MIN` (25,000) is also untouched — externally sourced
(OESD), independent of engine output, correct as-is — but the fixture that
exercises it (`test_a_heavy_design_prescribes_cutaway_stabilizer`, a solid
square) had to grow from 160 mm (26.7k stitches) to 180 mm (28.4k) because
law 26 alone drops the old fixture to 22.5k, legitimately under the
threshold now that the fill underlay is lighter; the STOP CONDITION for
leaving the threshold itself alone was never hit — 180 mm is still an
ordinary garment-sized design, not a contrived one. Sample measurements
(`whitebg` @ `left_chest`, pique_knit): `coverage_p50` 1.19 -> 1.00,
`stitch_count` 2469 -> 2165. Landing both laws moved geometry in more places
than the two explicitly-scoped preflight assertions — regenerated
deliberately, not defensively, and each is commented with why: `test_
preflight.py`'s `coverage_p50` and `link_thread_mm` goldens (travel-graph
routing shifted, 109.0 -> 87.8 mm on the fixture logo);
`test_flat_lane_byte_identical.py`'s `flat_lane_golden.json` (regenerated via
its own `tools/capture_flat_lane_golden.py`, all 4 fixtures move, all use
the default pique_knit fabric); `test_pushcomp.py`'s `GOLDEN_FLAG_OFF` table
(all 4 entries move — two via law 26's fabric change, two via law 23's
fabric-independent width gate, spelled out entry-by-entry in that table's
own comment); `test_stage2_photo_segment.py` needed no changes of its own,
it reuses `test_flat_lane_byte_identical.py`'s golden. One more collision
neither this doc's prior entry nor the task brief anticipated: `test_
chaining.py`'s two "bend into cover" tests pinned a specific band polygon
that landed on a knife-edge of the (inherently discrete, budget-gated) link-
routing search once law 26 thinned `pique_knit`'s underlay — non-monotonic
under small perturbations either direction, confirmed by sweeping dozens of
band placements post-landing rather than hand-fitting one value; the chosen
replacement band was checked robust to +-0.4 mm on both edges (47/49
perturbations still route as a bend). Full suite `cd digitizer && .venv/
bin/python -m pytest tests/ -q`, run to completion in the foreground:
**771 passed, 3 skipped, 0 failed** (794s) — every one of the 3 known
container-environment goldens this doc has cited every pass since
2026-08-03 (`test_flat_lane_byte_identical[logo_alpha.png]`, `test_pushcomp
[logo_whitebg.png-towel]`, `test_stage2_photo_segment[logo_alpha.png]`)
happened to pass clean in this environment on this run too — allowed to
fail per this pass's own task brief, not required to, and their passing
here isn't claimed as a fix, just an honest report of what the run showed;
engine `node --test` **272/272** and Studio `npx vitest run` **381/381** (26 files)
both re-run this pass as a sanity check even though neither `src/` nor
`app/` changed a byte — confirmed by `git status` before running. This work
was done in an isolated worktree per its own task brief and is committed
locally only — not pushed, no PR opened, merge is the coordinator's call.

**Same-day follow-up, still 2026-08-05: an independent stitch-geometry audit
caught a real peak/hotspot regression the above validation missed.** The
landing above validated `whitebg`/synthetic-square fixtures at p50/typical
behaviour only, never `logo_alpha.png`'s peak/hotspot behaviour — and
`logo_alpha` carries `Sf5200f3f`, a multi-stroke glyph classified satin on
its per-shape MEAN width (~5.0mm, right at `SATIN_MAX_WIDTH_MM`) while one
skeleton stroke's own LOCAL corridor runs 0.33-10.33mm, well past where the
corpus ever validated a satin zigzag underlay at all. `DENSITY_STACKED`
flipped `warn` -> `block` there (`coverage_max` 13.11 -> 16.69). Root cause
confirmed by isolation: the satin crosses themselves already self-overlap
on this shape in the UNMODIFIED engine (`coverage_max` 13.11 pre-law-23
too, a real, separate, pre-existing defect this fix does not touch), sitting
just under `_COVERAGE_MIN_PATCH_MM2`'s 25mm2 connected-patch gate; law 23's
denser/wider zigzag underlay supplied just enough extra thread to bridge
that pre-existing near-miss over the gate. Fix: `stage6_satin.py::
_stroke_underlay` now skips the zigzag pass entirely for a stroke whose
local width anywhere exceeds `SATIN_MAX_WIDTH_MM` (falling back to the
center-run walk only) — the corpus gives no guidance for that regime under
either the old or the new numbers, so omitting the guess beats
extrapolating either one. Reuses `SATIN_MAX_WIDTH_MM`, the same ceiling
`SPLIT_SATIN_ABOVE_MM` already gates on, not a new constant. Regression-
pinned (`test_a_wide_oversize_satin_stroke_does_not_block_on_underlay_
glue`, `test_preflight.py`); `flat_lane_golden.json` regenerated a second
time (`logo_alpha.png`/`photo/enthusiast_logo.png` entries move — both
carry oversize local strokes). Full suite re-run to completion in the
foreground: **772 passed, 3 skipped, 0 failed** (811s), 0 failures this
time (the 3 known-flaky goldens passed clean again). The pre-existing satin
self-overlap defect on `Sf5200f3f` itself (peak 13.11, unrelated to either
law) was NOT fixed by this pass and was left open — currently invisible to
`DENSITY_STACKED` because it never reaches the connected-patch gate alone,
which is arguably its own gap in the coverage instrument's peak-detection
sensitivity, flagged here rather than chased further. **FIXED, separate
same-day pass — see the top-of-doc "Last updated" entry; this paragraph is
kept as the historical record of the defect, not current status.**

**Also flagged by the same audit: `pique_knit`/`jersey_tee`'s new `edge_run`
fill underlay leaves large fill interiors up to 13mm from the nearest
underlay stitch (vs 1.6-1.8mm under the old `edge_lattice`) — investigated
and CLOSED as declined, 2026-08-06, see the top-of-doc "Last updated"
entry.** The candidate fix floated here (`center_run` in place of
`edge_run` for `jersey_tee`) was measured directly and does not work: a
single center line sits exactly as far from off-axis interior points as a
perimeter walk does (measured statistically identical max-gap across three
realistic fill sizes), so it would not have addressed the tension with
`jersey_tee`'s "needs solid underlay" note it was floated to fix. The only
style that actually closes the gap is a lattice pass, which corpus law 26
already found rare in real fills (7/507) and was the reason `edge_lattice`
was removed as this fabric's default to begin with — so `edge_run` stays,
and the 13mm figure is read as inherent to sparse running-line underlay on
a large shape, not a preset defect. This paragraph is kept as the
historical record of the flagged concern, not current status.

**Follow-up correction, 2026-08-05 (same day): the whole-stroke skip above
is the final state — a same-day per-station narrowing attempt was tried and
then dropped, not shipped.** An independent audit briefly proposed
narrowing the skip from per-stroke to per-station, reasoning that a
whole-stroke skip could over-silence a large organic photo-tier shape
(`testdata/photo/drone_render.png`) that was mostly ordinary-width with
only a small oversize fraction. That narrowing was implemented, then
reverted before landing: a separate, independent verification (real
`run_preflight` calls, not either side's own claims) found PR #60
(`satin-classifier-organic-shapes`, `digitizer_core.stage6_satin.
is_satin_candidate`'s `design_class`-scoped DT check) already resolves
`drone_render.png` completely at the classification stage — with laws
23/26 and PR #60 both applied, `drone_render.png @ 80mm/left_chest` reads
byte-identical preflight numbers (`coverage_max` 5.26, `over_warn_mm2`
68.0, severity `warn`) whether the per-station narrowing is applied on top
or not. The narrowing's entire reason for existing was moot before it ever
needed to ship, so it was dropped in favor of the simpler, already-verified
whole-stroke skip. `logo_alpha.png`'s own fix is unaffected either way —
`Sf5200f3f` is `design_class="flat"`, on which PR #60's fix is a
byte-for-byte no-op, so laws 23/26 plus the whole-stroke skip remain fully
necessary and are not superseded by anything on `main`. `drone_render.png`,
`region_blobs.png` and `summit_badge.png` are consequently out of scope
for this entry entirely — not fixed here and not flagged here as gaps,
since PR #60 already owns them at the classifier level (see that entry
below for its own numbers). Full suite re-run to completion in the
foreground: **828 passed, 3 skipped, 0 failed** (708s).

Prior update below, 2026-08-05, still earlier the same day — the
boundary-editor slice landed: area 5's
last self-flagged gap ("no reshaping/redrawing outlines... no manual point
editing") is now half-closed. A new `boundary_override` shape_overrides key
(contract v1.4) lets a review-screen edit replace a shape's exterior ring
with a hand-drawn polygon, following the exact override pattern the rest of
this area already uses: service-side validation (`digitizer_service/
app.py`, point count 3..500, finite numbers, shell validity, and the
sewability floor — a fast 400 on the common mistakes), core-side defense in
depth plus hole-containment checking (`digitizer_core/regions.py::
apply_shape_edits` — the one check that can only run here, since it alone
sees the shape's own existing holes; a rejected edit is always a clean
`ValueError`, never a crash or silently repaired geometry), `match_shape_
ids` carry-forward alongside the other five override keys, and a Studio
Layers-panel "Edit shape boundary" (✎) control (`DigitizePanel.svelte`) — a
small SVG editor with draggable vertex handles, click-a-midpoint-to-add,
right-click/Delete-to-remove, full keyboard equivalents (arrow-key nudge,
Enter/Space to add), and live client-side validation (`digitizer.js`'s
`boundaryIssues`, mirroring the server's own checks) that disables Save
before an invalid edit ever reaches the wire. On save the new polygon rides
through the SAME `setOverride` -> `shapeOverrides` -> "Apply layer changes"
flow every other override in this area already uses — no new save/apply
path invented. Verified live against the real service via Playwright MCP
(a full click-through including the invalid self-intersecting-shape
rejection path, screenshotted) and a new Playwright e2e spec
(`app/e2e/digitize-boundary-edit.spec.js`: drag a vertex, save, apply,
confirm the design actually reshapes and resews, Reset to auto undoes it).
Splitting/merging shapes — the other half of the original shape-
recognition gap — is explicitly untouched this pass; see area 5 below for
the honest scope line. Full suite re-run this pass: digitizer **708 passed
/ 3 failed / 3 skipped** (`digitizer/` commit `298eae0`) — the 3 failures
are the same long-standing container-environment golden mismatches this
doc has cited every pass since 2026-08-03
(`test_flat_lane_byte_identical[logo_alpha.png]`,
`test_pushcomp[logo_whitebg.png-towel]`,
`test_stage2_photo_segment[logo_alpha.png]`), not new regressions; Studio
`npx vitest run` **354/354** (25 files, up from 348 — 8 new unit tests for
the boundary-edit contract plus `outlineFull`/`boundaryIssues` coverage),
`app/` commit `ac11163`. Engine `node --test` untouched by this slice, not
re-run.

Prior update below, 2026-08-04, latest still — three more PRs landed on top of
the prior entry's CI + photo-plan-closeout wave, closing the last open
photo-plan row and fixing a real region-fragmentation defect on busy gradient
art. **PR #43** (`background-removal-rembg`, merged `7d07aea`) wires
`remove_background_seam` for real: it shells out to an isolated venv
(`digitizer/rembg_isolated/`, not committed — see its own README) running
`digitizer_core/rembg_worker.py` as a standalone subprocess, sidestepping the
`numba`-vs-`numpy==2.5.1` conflict the prior pass's probe doc flagged rather
than touching the shared venv's pin. Gated behind a new
`cfg.photo_prep_background_removal` flag layered on top of the existing
`photo_prep` gate; missing venv, worker crash, timeout, or bad output all
degrade to the documented no-op (`PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE`),
mirroring the YuNet face-priors fallback pattern. Verified end-to-end in that
PR's own worktree: a real isolated venv built from
`digitizer/rembg_isolated/requirements.txt`, a real cutout on
`skimage.data.astronaut()` through the actual subprocess, and the graceful
fallback in both its environment and runtime failure forms (`tests/
test_background_removal.py`, 350 lines). **This closes photo plan row 1, the
last row this doc was still tracking as open — rows 0–15 are now all built.**
**PR #44** (`delete-standalone-html`, merged `ad4bf52`) deleted
`EMB-Bot-standalone.html` (6,339 lines) and updated every live doc that
pointed at it (COOKBOOK.md, README.md, this file, `.claude/skills/
run-emb-bot/SKILL.md`, `.claude/agents/emb-bot-reviewer.md`); `tools/
bundle.mjs` became fully dead code then, left in place but not wired to
anything (and was deleted outright 2026-08-11, in the project-audit
doc-rot pass).
Re-checked this pass: no live doc still references the file — the only
remaining mentions are in dated planning/spec/audit docs
(`docs/superpowers/plans/2026-07-22-emb-bot.md`,
`docs/superpowers/plans/2026-07-27-font-editing-abilities.md`,
`docs/superpowers/specs/2026-07-27-font-library-expansion-design.md`,
`docs/font-license-audit-2026-07-31.md`) describing the state at the time
they were written, which is the same "kept as written for the historical
record" convention `docs/font-license-audit-2026-07-31.md` itself already
uses elsewhere — not a gap. **PR #45** (`gradient-fragmentation-fix`, merged
`fc40d53`, 4 commits) fixes a real region-COUNT fragmentation defect distinct
from the angle-fragmentation one closed 2026-08-03 (below): busy gradient art
was fragmenting into ~10x the photo plan's own 20–80-region accept band under
plain k-means (`drone_render.png` measured ~208 final regions). Fix:
`gradient`-classified designs now dispatch through `stage2_photo_segment`
(SLIC+RAG) instead of `stage2_quantize`, same as the photo classes, plus
`MERGE_DELTAE00_THRESH` retuned `10.0` → `20.0` (with `FACE_MERGE_FACTOR`
`0.5` → `0.25` in the same commit so the face-local absolute merge tolerance
stays decoupled from the retune). Landing this exposed two more real bugs,
both fixed same-PR: `stage2_photo_segment` didn't separate
`BACKGROUND_ENCLOSED` pixels from the main population the way
`stage2_quantize` always has (measured: 0 of 3 enclosed regions survived
their own tag on `repro_gradient_white_icon.png` before the fix), and the
`PHOTO_SEGMENT_REGION_COUNT` warning was reporting thread-colour count under
a message claiming region count. A new `CLASS_OVERRIDE_TECHNIQUE_MISMATCH`
preflight guard and a `stage6_blend` follow-up (widening `blend_fill`'s
shared-angle preference to fragments whose own fit reads "radial" by chance,
an interaction the routing switch exposed) round out the 4-commit PR.
**Region-count honesty note, checked directly against the regression tests'
own docstrings rather than taken from the commit message alone
(`tests/test_stage2_photo_segment.py`):** the 20–80 accept-band claim is
validated on exactly **two** real busy fixtures, `drone_render.png` (→65
regions) and a newly-built `summit_badge.png` (→30) — not a broader corpus
sweep. That is real, independently-checked evidence, not nothing, but it is
narrower than "fixed, full stop" would imply; re-verified this pass that a
third fixture, `repro_gradient_white_icon.png` (the *angle*-fragmentation
fix's own repro case), still produces exactly 23 regions after PR #45's
routing switch — same count as before, now via SLIC+RAG instead of k-means,
which is expected (that fixture's own fragmentation was never the
region-count defect PR #45 targets) but is worth stating plainly rather than
implying the routing change uniformly shrinks region counts everywhere.
Fragment count and radial-ramp angle sharing remain non-goals of the
*angle*-fragmentation fix specifically, unchanged from the entry below.

Fresh full suite run this pass (this worktree, HEAD `fc40d53`): digitizer
`cd digitizer && .venv/bin/python -m pytest tests/ -q` — **688 passed / 3
failed / 3 skipped** — the same three long-standing container-environment
goldens this doc has cited every pass since 2026-08-03
(`test_flat_lane_byte_identical[logo_alpha.png]`,
`test_pushcomp[logo_whitebg.png-towel]`,
`test_stage2_photo_segment[logo_alpha.png]`), not new regressions; engine
`node --test` re-run this pass too — **267/267**, unaffected (no `src/`
change survived this pass — see below). Studio (`vitest`) was **not**
re-run this pass, since nothing in `app/` changed across PRs #43–45; carrying
forward the prior entry's **348/348** (25 files) rather than re-asserting an
unverified number.

**UPDATE 2026-08-05: both laws below landed for real — see the top-of-doc
entry for the corrected coverage-budget recalibration that made it possible.
The account below of the reverted attempt is kept as the historical record
of why it needed care, not as current status.**

**Two corpus-law fixes evaluated this pass and reverted, not landed —
recorded here because they touched code before being backed out, not just
considered.** `docs/corpus-laws-round3-2026-08-01.md` law 26 (fabric preset
`fill_underlay` `edge_lattice` → `edge_run` for `pique_knit`/`jersey_tee`)
and law 23 (satin structural zigzag underlay pitch/width correction) are
both tagged "desk-safe" in that doc, and the corpus evidence behind each
looks solid on its own terms. But actually applying either one and running
the suite (not just reading the doc) showed a materially bigger blast radius
than "desk-safe" implies here: `pique_knit` is the default fabric for
untagged designs and for `left_chest`, so changing its fill underlay moved
**8 of the digitizer's hard byte-identical golden assertions across three
test files** (`test_flat_lane_byte_identical.py`, `test_stage2_photo_
segment.py`, `test_pushcomp.py`) that explicitly instruct "if this test ever
goes red, the change under review is wrong — not this test," and — more
consequentially — dropped `test_preflight.py`'s measured `coverage_p50` from
1.2 to 1.0 on the benchmark logo and silenced the `STABILIZER_CUTAWAY`
finding entirely on the constructed 26.7k-stitch heavy-design case: a real
behaviour change in a customer-facing warning, not a cosmetic hash diff. Law
23's zigzag correction, even scoped to a brand-new satin-only constant to
avoid also perturbing fill's unrelated crosshatch-lattice underlay style,
still auto-applies to every satin column over `SATIN_ZIGZAG_ABOVE_MM` via
`stage6_satin`'s existing width-based zigzag-promotion rule regardless of
fabric — so it moved the same preflight coverage/stabilizer numbers again,
independently confirmed by reverting law 26 alone and re-running. Both
changes were fully reverted (verified back to the exact 3-known-failure
baseline via a clean pytest run) rather than landed with a "fix the
preflight calibration too" scope-creep, since that calibration is itself
descriptively tuned to today's shipped geometry (`machine.py`'s coverage-
budget comments: "checked against what our own output actually produces")
and re-deriving it is its own project, not a desk-safe follow-on to a fabric
tweak. Two smaller items from the same review pass — law 19's stale
interleave-hedge comment on `machine.FILL_ROW_MM` and law 40's stale
"UNMEASURED" comment on `machine.BORDER_SEAM_OFFSET_MM` — WERE comment-only
and are landed (`digitizer_core/machine.py`, `digitizer_core/
stage6_border.py`); no constant moved, verified by the same clean pytest run
before and after.

Prior update below, 2026-08-04, still earlier the same day — a large batch
landed: **CI now exists** (Kent added a stock GitHub Actions conda
workflow, first run failed on wrong Python/no environment.yml; rewritten in
**PR #37** to run this repo's real suites — engine `node --test`, Studio
`vitest`, digitizer `pytest` with the 3 known container goldens deselected —
and every PR from here on is gated on its Actions run going green before
merge, not just local suite passes). On top of that, photo plan rows 11
(FDoG detail layer), 12 (sketch tier), 14 (depth-sorted sequencing), and a
15-guard subset (preflight) landed, plus the last two step-3 dependency
gaps closed: **PR #38** shipped the zero-dep photo-prep slice (CLAHE tone +
texture kill) with a full dependency probe (`docs/photo-prep-deps-probe-
2026-08-04.md`) establishing rembg/YuNet/contrib-opencv were all installable
but not yet wired; **PR #39** applied the probe-verified opencv-contrib
swap (`opencv-contrib-python-headless` replaces plain `opencv-python-
headless` in `requirements.txt`/`pyproject.toml`, same cv2 build plus
`cv2.ximgproc`), which lights up `rolling_guidance`'s real texture-kill path
instead of its bilateral fallback — golden-safe, re-verified in a fresh
throwaway venv both before and after landing; **PR #41** wired real YuNet
face detection into the face-priors seam PR #38 had landed as a documented
no-op — `cv2.FaceDetectorYN` on the committed, sha-pinned model
(`digitizer_core/model_data/face_detection_yunet_2023mar.onnx`), true-
positive detection proven on `skimage.data.astronaut()` (a rights-safe
public-domain photo shipped inside the scikit-image wheel, not a committed
photograph), wired into the face-local merge-threshold drop, region-class
mapping, and a new `FACE_TOO_SMALL` preflight guard. **This closes the
caveat this doc has carried since the palette-k-medoids pass** — the
eyes/skin class multipliers that used to run at a flat 1.0 "until step 3's
face priors exist" now receive real face regions. An independent geometry
audit (fresh measurement from raw output, not the shipped tests' own
assertions) confirmed all of PR #41's claims and caught one real defect
before merge: `FACE_BLOCK_HOOP_MM` used a rounded 100.0mm instead of this
codebase's own literal-inch hoop convention (`src/units.js`: `inch × 25.4`,
already used by the guard's sibling `FACE_MIN_HOOP_MM`), leaving a ~1.6mm
dead band where a design that still needed a real 4×4in hoop got no
warning — fixed to 101.6mm same-PR, with a boundary regression test. A
parallel geometry audit of PR #40 (sketch tier — `fill_technique="sketch"`,
a config preset over rows 10/11 with zero new algorithms, `stage6_streamline`
gaining an additive `darkness_scale` kwarg) independently re-derived its
seed-spacing and highlight-cutoff numbers from raw emitted stitch
coordinates and bit-exact-diffed the default-kwarg path against the
pre-change parent commit across 7 scenarios — full confirmation, no defects
found. Photo plan status: **rows 0, 2–15 are now all built** (row 1,
background removal via rembg, remains the one open row — installable per
the probe doc but blocked on a `numba` vs. this repo's `numpy==2.5.1` pin;
documented as a seam, `remove_background_seam`, not attempted this pass).
Combined suite on the final composed `main` (`354f075`): engine **267/267**,
Studio **348/348** (25 files), digitizer **654 passed / 3 failed / 1
skipped** — the 3 failures are the same long-standing container-environment
goldens this doc has cited every pass since 2026-08-03. Main-branch CI run
green on all 3 jobs.

Prior update below, 2026-08-04, later still — verification pass confirming
**all 11 PRs from the prior pass's "#16–#21 pending review" list, plus #22
though #28, are now merged to `main`** (`4cf8760`, the `backstitch-
underlay-control` merge; every PR number from #16 through #28 shows a
"Merge pull request" commit in `git log origin/main`, checked directly, not
inferred from titles), rebased and re-verified once more when **two more
PRs landed on top mid-pass — #29 (wizard-smoke e2e broadened along three
axes: garment type, image-content path, export formats) and #30 (a
real-jsPDF byte/text-extraction test tier for the worksheet export,
replacing "call-sequence-only" as the PDF coverage's honest description)**.
Fresh suite run against the final tip (`8544713`): engine `node --test`
**267/267**; Studio `cd app && npx vitest run` **347/347** (25 files, up
from 24 — #30's new spec file); digitizer `.venv/bin/python -m pytest
tests/ -q` **564 passed / 3 failed** — still exactly the same three
long-standing
container-environment golden mismatches this doc has cited every pass since
2026-08-03 (`test_flat_lane_byte_identical[logo_alpha.png]`,
`test_pushcomp[logo_whitebg.png-towel]`,
`test_stage2_photo_segment[logo_alpha.png]`), not new regressions.

What actually changed in the code, verified against source rather than PR
titles: the 13-font ShareAlike pull (**PR #16**, `src/fonts/manifest.json`
recounted directly at **55** entries, license breakdown 52 OFL-1.1 + 2 CC0 +
1 CC-BY-4.0, zero ShareAlike) and its legacy-registry follow-up (**PR #17**,
`satin-fonts.js` diff-verified 21 → 14 entries) together retire the
lawyer-consult gate as launch-blocking (area 2, and the cross-cutting
font-license section below, both rewritten this pass — they'd drifted out
of sync with each other, one already describing the post-pull state and one
still describing it as an unmerged proposal); the PES/EXP pyembroidery
cross-validation (**PR #18**, `docs/pes-crossval-verdict-2026-08-04.md`) —
mis-framed PES stitch stream, EXP's fatal-on-first-trim record — is now
corroborated evidence on `main`, not a pending finding (area 4,
cross-cutting DST section); the classifier-lens measurement (**PR #19**)
confirming the shipped stage-0 four-way router's thresholds should be left
alone is merged (area 1); the streamline thread-paint tier's mono slice
(**PR #20**) and its layered multi-colour follow-up (**PR #25**) are both
merged (photo plan row 10, area 1 — both slices now built, not one); the
stale-edit e2e spec and per-shape border-override UI (**PR #21**) closed
area 5's first two self-flagged gaps; the within-layer sew-order control
(**PR #26**) closed its third; the contour bare-core shrink (**PR #27**,
confirmed directly in `digitizer_core/config.py`'s `fill_technique` comment
block — all three of the 2026-08-02 audit's defects now read "FIXED
2026-08-04", including the bare-core dot this doc previously described as
"measured, not yet shrunk") closed the one remaining defect keeping contour
fill's quality bar down (area 1); and the per-shape underlay-style override
(**PR #28**, `digitizer_service/app.py`'s `_OVERRIDE_KEYS` re-read directly:
`{thread_index, fill_angle_deg, tier, border, layer, sew_order, stitched,
underlay_style}`) closed area 5's fourth. Every "open PR #N, pending
review" callout this doc was carrying for that range is folded into its
area's prose below and removed, per this doc's own convention for landed
work (see how #9/#10/#25's/#26's/#27's own predecessors were folded rather
than kept as standing callouts). One thing this pass did NOT find any new
evidence for: physical sew-out testing — still zero, see the cross-cutting
item below, unchanged.

Also landed 2026-08-07, same day: one Ember Design competitive-research
backlog item closed out — measured whether `digitizer_core/config.py`'s
fixed `simplify_tol_mm` (0.2 mm) needs to scale with `target_width_mm` the
way Ember's equivalent tolerance scales with design size. Measured, not
assumed: it does not — the fixed constant is already scale-invariant in
real millimetres by construction (`px_per_mm` cancels out of the round
trip), confirmed by a direct Hausdorff-deviation sweep (0.185-0.200 mm
across `px_per_mm` 3.0-40.0) and full end-to-end runs on every testdata
fixture at 40-180 mm. No pipeline behavior changed; two regression tests
pin the finding. Full writeup: this file's "`simplify_tol_mm` design-size
scaling" cross-cutting entry below. Branch `simplify-tol-mm-scaling-audit`.

Prior update 2026-08-04, earlier the same day: docs refresh once PRs #8–#15
had finished merging (written mid-batch, so it undercounted at first),
touched up twice more that pass as #23 (meander tonal tier) then #22
(opaque-alpha fix + `debugviz.direction_field` restore) landed mid-refresh.
Combined suite at that point: engine 266/266, Studio 331/331 (24 files),
digitizer 507/510 (same 3 known container goldens). Substance folded in
then: the full `BACKGROUND_ENCLOSED` stack (pipeline + service contract +
Studio Layers-panel restore UI), the rotation/hoop-fit auto-fit fix
(`8e668d3`), a passing Playwright wizard-smoke e2e, and PDF-worksheet test
coverage. Prior update 2026-08-04 (font-license audit items 4–10 + 12
executed — full license texts on disk/served/embedded, complete
attributions, credits links). Prior update 2026-08-03: the gradient
angle-fragmentation fix landed that session; `BACKGROUND_ENCLOSED`'s root
cause was corrected to `stage1_prep.py`, still unresolved at that time.

---

# Resolved cross-cutting issues

Moved out of `MASTER_SCOPE.md` on 2026-08-14. These were fully resolved, so
only a short standing summary was kept in the live document; the detail below
is the original record, preserved rather than condensed away.

## Font license compliance gap — RESOLVED 2026-08-04 by removal

`docs/font-license-audit-2026-07-31.md` action checklist: **items 1–3 done**
(the 4 flagged fonts pulled, 72 → 68 — see the audit's §7) and **items 4–10 +
12 done** the same day (see its §8): every surviving font had its full
upstream license text on disk (`src/fonts/<key>.LICENSE.txt`), shipped
by `copy-engine.mjs` at `/fonts/<key>.LICENSE.txt`, linked per-font in the
credits dialog, AND embedded verbatim in the `.embf` binary metadata (closes
the bare-download hole); manifest attributions are complete notices
(adapter + upstream copyright + Reserved-Font-Name declarations, emails
stripped); guard tests pin all of it.

**The one-hour lawyer consult this gap used to gate on (audit item 11) is
now optional, not launch-blocking — merged 2026-08-04 (PR #16,
`sharealike-pull`):** rather than wait on the consult, Kent's call was to
pull all 13 ShareAlike fonts (11 CC-BY-SA-4.0 + 2 CC-BY-SA-2.5) from the
shipping library outright. Recounted directly from `src/fonts/manifest.json`
this pass: **55 entries**, license breakdown 52 OFL-1.1 + 2 CC0 + 1
CC-BY-4.0 — zero ShareAlike remaining, zero Reserved Font Name as a primary
name anywhere. The ready-to-send brief,
`docs/lawyer-brief-cc-by-sa-2026-08-04.md`, stays on file as the restore
path if Kent ever wants those 13 fonts back, but booking the consult is no
longer something first dollar waits on. Stacked on it, **PR #17
(`legacy-font-audit`), merged same day,** removes the same 7 pulled fonts
(the original 2 + the 5 ShareAlike) from the legacy `satin-fonts.js`
registry — diff-verified this pass at 21 → 14 entries — so `EMB-Bot.html`
carries nothing pulled either. `EMB-Bot-standalone.html` (the only place
that still embedded a pre-audit inlined copy) is **deleted, 2026-08-04,
Kent's call** — no pre-audit font list ships anywhere. Still parked for
Kent: the bluenesia permission screenshots (audit §8).
