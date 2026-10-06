# Underlay under fills — research, 2026-10-05

**Summary (the ten lines).**

1. Kent's observation is **true, and it has two separate causes**. *(measured here)*
2. **Gradient lane: every fill is sewn with zero underlay** — not even an edge
   run. 10 of the 14 real-art fixtures run today were classed `gradient`; in all
   of them 100% of the fill area had no underlay stitch (e.g. Hotel Fremont
   patch 90 mm: 9 fills, 3,599 mm², 13,451 fill stitches, 0 underlay).
   `blend_fill` hardcodes `underlay_style="none"` and is never handed the
   fabric's style, the design-wide `underlay_style`, or the per-shape override.
3. **Flat lane on a knit (left chest, beanie, sleeve): one perimeter walk and
   nothing in the interior.** A 639 mm² fill carries 40 underlay stitches under
   1,875 fill stitches. That is corpus law 26 (2026-08-05), shipped on purpose.
4. The repo already saw this: an audit on 2026-08-06 measured fill interiors
   "up to 13 mm from the nearest underlay stitch" and closed it as declined on
   law 26's authority.
5. **Kent's own commissioned files do the opposite.** Under their large fills
   the professional sews a sparse tatami pass crossing the top fill at ~90°,
   rows ~1.0 mm apart, ~4 mm stitches, ~13% of the top fill's thread — read
   directly off the tracked Becker files and 27 of 45 large fills in the
   commissioned set. Law 26 was drawn from a corpus that held 4 of those files.
6. Vendor documentation agrees with the professional, not with law 26: an open
   crossing tatami, usually with an edge run, more on knits and large areas;
   none under gradient/variable-density fills.
7. Not a render misread this time. The Studio draws underlay *beneath* the top
   thread, so it is invisible either way — the eye cannot tell "none" from
   "covered"; only the run kinds can, and they say none.
8. Fix, cheapest first: (a) give gradient-lane fills that sew at full density
   the fabric's underlay; (b) restore an interior pass under large knit fills;
   (c) move the lattice constants toward the professional's. (b) and (c) touch
   fabric presets — gate 1 — and are Kent's ruling.
9. Not verified: the photo lane (both photo stubs sewed 0 stitches here), any
   physical effect (no sew-out), Wilcom/Hatch numeric defaults (unpublished).
10. Nothing in the engine was changed. Scripts and outputs are in the session
    scratchpad, not the repo.

Evidence labels used below: **[M]** measured here today · **[C]** read in code ·
**[D]** read in a repo doc · **[X]** external source · **[I]** my inference.
Commit read: `cf9f89f1` (main). Windows box, main checkout's venv.

---

## 1. What the engines sew under a fill today

### 1.1 Python digitizer (`digitizer/digitizer_core/`)

**Styles** [C] — `stage6_fill._underlay_paths` (`stage6_fill.py:1339-1408`):

| id | what is sewn |
|---|---|
| `none` | nothing |
| `edge_run` | one walk round each ring of the shape, inset |
| `center_run` | one line through the centroid along the principal axis |
| `zigzag` | one sparse tatami pass at fill angle + 90°, rows 2.0 mm |
| `edge_zigzag` | edge run + that pass |
| `edge_lattice` | edge run + sparse tatami at +90°, rows 2.5 mm |
| `double_lattice` | edge run + two passes at +45° and −45°, rows 2.5 mm |

**Constants** [C] — `machine.py:740-746`: inset `UNDERLAY_INSET_MM = 1.0`,
stitch `UNDERLAY_STITCH_MM = 2.5`, `UNDERLAY_ZIGZAG_MM = 2.0`,
`UNDERLAY_LATTICE_MM = 2.5`. All engine-wide; no per-fabric spacing or inset
(`docs/scope/machine-physics-backlog.md:58` records that as missing [D]).
Lattice rows are not staggered (`staggers=1`, `stage6_fill.py:1375`).

**Which style a fill gets** [C] — `stage7_sequence.py:1663-1664`:
`(cfg.underlay_style or class_default) if cfg.underlay else "none"`, where the
class default is the fabric preset's `fill_underlay`, or `edge_lattice` when the
design is sequenced as a photo (`stage7_sequence.py:137`). A per-shape
`meta["underlay_style"]` beats both (`stage7_sequence.py:1928-1930`).
`cfg.underlay` defaults `True`, `cfg.underlay_style` defaults `None`
(`config.py:1650-1651`).

**Fabric presets** [C] — `fabrics.py:61-100`, mirrored in `src/fabrics.js`:

| preset | garments mapped to it | `fill_underlay` | `satin_underlay` |
|---|---|---|---|
| `pique_knit` (the default) | left_chest | `edge_run` | `center_run` |
| `jersey_tee` | beanie, sleeve | `edge_run` | `center_run` |
| `canvas_tote` | tote, jacket_back, patch | `edge_run` | `center_run` |
| `woven_dress` | — | `edge_run` | `center_run` |
| `structured_cap` | hat_front | `edge_zigzag` | `center_run` |
| `fleece_sweatshirt` | full_back, blanket | `double_lattice` | `zigzag` |
| `terry_towel` | towel | `double_lattice` | `zigzag` |

So on five of seven presets — including the default — the whole of a fill's
underlay is one perimeter walk 1.0 mm inside the edge.

**When a fill gets NO underlay at all** [C], each confirmed where marked [M]:

1. **The design is classed `gradient`.** Every auto-tier fill routes to
   `blend_fill` (`stage7_sequence.py:2316-2327`), which is not passed an
   underlay style and hardcodes `underlay_style="none"` on both of its paths:
   the ramp bands (`stage6_blend.py:927`) and the flat-tatami **fallback**
   (`stage6_blend.py:715`) — which its own comment calls "the path nearly every
   real region actually takes". The line dates from 2026-08-02/03 (`git log -S`).
   [M] A design-wide `underlay_style="double_lattice"` on a gradient-classed
   fixture changed nothing: 5,531 stitches both ways, 0 fill underlay. The
   Studio's per-shape "Underlay style" control therefore does nothing on these
   shapes either [I from C — the override is read only in the branches that
   pass `eff_underlay_style`].
2. **Tonal tiers** — meander, scanline, streamline, sketch: no underlay by
   construction (`stage7_sequence.py:132-136`, each tier's docstring).
3. **The shape is under 2 mm wide everywhere.** The 1.0 mm inset empties it and
   `_underlay_paths` returns nothing (`stage6_fill.py:1353-1355`). [M] 6 of 16
   bare fills on the thermal badge, 7 of 21 on the owl, 5 of 12 on bridge.
4. **The inset splits the shape: only the largest piece gets underlay**
   (`stage6_fill.py:1356-1357`). [M] On Becker at 100 mm the main fill keeps
   29% of its inset area; on Fremont forced flat, 48%. The rest of the shape is
   bare under its fill. This one reads as an oversight, not a decision [I].
5. `cfg.underlay = False`, or a per-shape override of `none`.
6. **Contour tier** (default OFF, gate 3): rings at 3× the fill spacing rather
   than the named style (`stage6_contour.py:691-710`, `machine.py:309`); its
   finish patches get none (`stage6_contour.py:770`).
7. Run tier, bean letters, satin junction patches (`stage6_satin.py:5066`,
   `5195`): none.

**Satin, for completeness** [C]: centre run down the spine, plus zigzag at
1.45 mm pitch on columns over 2.5 mm (`machine.py:421`, `754`;
`stage6_satin.py:4330-4451`, `5600`); nothing under a satin shape whose artwork
extent is under 5 mm (`machine.py:445`, `stage7_sequence.py:2027`, `2039`);
nothing under hairlines. No edge-walk rung exists in Python satin
(`docs/quality-review-2026-09-08.md:444` [D]).
`satin_underlay_on_column` is built, default OFF (`config.py:1523`).

### 1.2 JS engine (`src/`)

**Shapes** [C] — `digitize.js underlayRuns` (`373-510`): the same seven ids.
Edge run inset `min(2 px, 0.6 mm)` (`:381`) or `EDGE_RUN_INSET_MM` under
`fillColumns` (`:746`); underlay stitch 2.0 mm, lattice rows 2.5 mm
(`:697-698`), zigzag rows 2.0 mm (`:384`); zigzag and lattice at fill angle
+90°, double lattice at ±45° (`:473-507`). Gated by `opts.underlay !== false`
(`:596`); the Studio's project default is `underlay: true`
(`app/src/lib/project.js:24`).

- With a fabric (every Studio lane passes one — `app/src/lib/generate.js:111`,
  `138`): the preset's `fillUnderlay`, so **`edge_run` on a knit**
  (`digitize.js:1009`).
- Without a fabric (legacy callers): edge run **plus** a 2.5 mm lattice at +90°
  (`digitize.js:1017-1025`).
- Both branches sit in `try { } catch (e) { /* underlay best-effort */ }`
  (`:1012`, `:1026`): an underlay that throws is dropped silently and the fill
  sews bare. Not observed firing today; it is a path to "no underlay" that
  reports nothing [C, I].
- There is no gradient/blend lane in JS, so cause 1 above is Python-only.

[M] A 102 mm square through `buildQualityDesign`: pique 203 underlay / 18,415
fill stitches (1.1%); structured cap 1,581; fleece 2,448; no-fabric 1,311;
`underlay:false` 0.

**Lettering** [C] — `satinfont.js:43-47`, Law 50's ladder by cap height: under
5 mm none, 5–10 mm centre walk (3 mm step, 2 repeats), over 10 mm edge/contour
(0.4 mm inset per side). The numbers are Ink/Stitch's defaults, cited as such
in the file. The JS and Python `UNDERLAY_INSET_MM` share a name and mean
different things (DOCTRINE.md:5584 [D]).

---

## 2. Is the observation true, and where?

### 2.1 Measured [M]

`digitize()` on tracked fixtures, default config except width, garment and
`max_colors=6`; runs tallied per `shape_id` by `StitchRun.kind` from
`plan.iter_runs()`. A "fill shape" is one that has any `fill` run.

| fixture (mm, garment) | stage-0 class | fill shapes | fill area mm² | fill stitches | underlay stitches under fills | fill area with ZERO underlay |
|---|---|---|---|---|---|---|
| logo_whitebg 80, left_chest | flat | 4 | 1,222 | 4,136 | 137 (3.3%) | 0% |
| logo_whitebg 80, hat_front | flat | 4 | 1,222 | 4,206 | 442 (10.5%) | 0% |
| logo_whitebg 80, full_back | flat | 4 | 1,222 | 4,748 | 691 (14.6%) | 0% |
| logo_whitebg 80, left_chest, `underlay_style=edge_lattice` | flat | 4 | 1,222 | 4,136 | 394 (9.5%) | 0% |
| becker_marine_logo 100 | flat | 2 | 1,154 | 403 | (shared with satin) | 0% |
| enthusiast_logo 80 | flat | 1 | 15 | 144 | 9 | 0% |
| logo_script_tires 90 | photo_scene | 1 | 14 | 98 | 12 | 0% |
| art/logo_hotel_fremont_patch 90 | gradient | 9 | 3,599 | 13,451 | **0** | **100%** |
| art/logo_golke_roofing 90 | gradient | 3 | 178 | 852 | **0** | **100%** |
| photo/logo_drone_thermal_badge 90 | gradient | 16 | 2,582 | 13,212 | **0** | **100%** |
| photo/summit_badge 90 | gradient | 9 | 2,172+ | 24,515 | **0** | **100%** |
| photo/logo_bridge_bar 90 | gradient | 12 | 1,324 | 7,372 | **0** | **100%** |
| photo/owl_kent 100 | gradient | 21 | 8,878 | 32,502 | **0** | **100%** |
| photo/gradient_ramp_radial 80 | gradient | 5 | n/a | 16,940 | **0** | **100%** |
| photo/logo_golden_tee 90 | gradient | 1 | 3 | 63 | 0 | 100% (one 1.45 mm shape) |
| art/logo_mfab_lc 90, art/logo_toat_machine 90 | gradient | 0 | — | — | — | all satin/run |
| golke 90, `forced_class=flat` | flat | 3 | 178 | 868 | 46 (5.3%) | 0% |
| fremont patch 90, `forced_class=flat` | flat | 9 | 3,485 | 13,564 | 644 (4.7%) | 0% |

Reading it:

- **Gradient lane: bare, without exception.** Forcing the same artwork flat
  brings the edge run back, which isolates the lane as the cause.
- **Flat lane on a knit: present but thin.** On logo_whitebg's largest fill
  (639 mm², 28 mm across) the underlay is 40 stitches / 88 mm of thread — one
  lap of the perimeter — under 1,875 stitches / 4,492 mm of fill. "Straight
  into the fill" is a fair description of the interior.
- Most real logos reach the gradient lane (ROADMAP phase 2 says so in its own
  words; 10 of 14 here did), so the bare case is the common one on real art.

Areas for blend-band shapes (`…-blend{n}` ids) could not be matched back to a
region, hence "n/a"/"+"; the zero-underlay counts are unaffected.

### 2.2 Could a viewer see underlay at all?

No — and that cuts both ways.

- **Studio preview** [C]: underlay is its own style, thin, dark, low sheen, and
  drawn at `z: 1` under fill/satin (`app/src/lib/preview.js:187-190`,
  `514-521`). Under a 0.15 mm-pitch fill it is fully painted over. Present or
  absent, the preview looks the same.
- **Eye-pairs sheets / `tools/thread_path_render.py`** [C]: every needle-down
  run is drawn in sew order, so underlay is again covered by its fill.
- `debugviz` draws underlay lighter and 1 px wide (`debugviz.py:156-157`) — the
  only render where it shows, and it is a debug artefact, not what Kent sees.

So the earlier "missing backfill" refutation and today's finding do not
conflict. That entry (`docs/scope/1-auto-digitizing-quality.md:1995-1999`,
memory `hotel-fremont-pro-parity-findings`) counted 78 underlay runs and
sampled "5 of 6 small **letter** shapes" — satin. It never looked under the
fills. On the Fremont patch fixture today the satin underlay is there (268
underlay stitches) and the fills have none. *(Different Fremont fixture file
than the 08-20 one — `art/…_patch.png` vs `photo/…webp` — so this is the same
design family, not a re-run of that exact measurement.)*

What Kent is seeing is therefore not the absence of drawn underlay. Two
readings remain and I cannot separate them without him [I]: he inspected the
needle path / stitch-out order (where "no pass before the fill" is directly
visible), or he is reading a consequence — fabric showing, a fill that looks
flat and unsupported. Worth one question.

---

## 3. What the professional files do

**Method, and its limits.** A stitch file has no underlay tag. I split each
colour block into rows (stretches between direction reversals over 120°),
measured each row's stitch length and the perpendicular distance to the row
before it, and called a multi-stitch row ≥ 4 mm long "sparse" when that pitch
was ≥ 0.9 mm and "dense" below. A **fill** is a block whose dense rows carry
≥ 1,500 mm of thread. A fill "has a crossing underlay" when sparse rows come
*before* its dense rows, amount to ≥ 3% of the dense thread, and their median
angle is ≥ 60° off the dense rows'. This is a scratch instrument written
today: **not validated on synthetic fixtures**, unlike the law-26 instrument,
and it will mislabel travel rows, layered fills and region changes. Trust the
directly-read timelines; treat the counts as indicative.

**Becker, read directly** [M] — `testdata/reference/becker_hat_polo_large_beckers_logolc.dst`
(tracked; 95.7 mm). Its two fill blocks sew, in order:

| phase | rows | stitch p50 | row pitch p50 | angle |
|---|---|---|---|---|
| sparse tatami | 46 | 3.93 mm | 0.99 mm | ~115° |
| top fill | 144 + 107 + … | 3.45 mm | 0.18 mm | ~22° |

Underlay crossing the top fill at ~93°, at about a fifth of its density, 13% of
the block's thread (second fill block: same recipe, sparse rows 1.0 mm / 4.0 mm
stitches at 112–114°). Confidence: high — the two phases are unmistakable in
the timeline. I did not find a clean edge-run phase in these blocks (a 40-stitch
run at 2.4 mm precedes the first; too short to be a full perimeter) — unsettled.

`tools/underlay_cover.py` on the same file reports 47.1% of all thread as back
stitching against 34.8% for ours (`docs/eye-pairs-2026-09-30/back-stitching-table.json`
[D]) and, per fill block, 72–78% [M]. **Do not quote those block figures as
underlay**: its rule is "covered by later thread", which also counts a base
fill that later colours sew over. The 10-01 DOCTRINE entry compared only the
MARINE satin band, found support equal (20.7% both) and went after the comb
split. The whole-design gap it printed (32.7% vs 21.8% of top thread sitting on
thread) was not followed up; the fills are where it lives [I].

**Kent's commissioned set** [M] — gitignored `scratch_kent/`, read only,
aggregates only. 45 fills ≥ 1,500 mm outside the `Test Files` folder (several
are hat/left-chest/beanie variants of one design, so **not 45 independent
decisions**; one digitizer's house style):

- crossing sparse pass first: **27** — pitch p50 1.05 mm (1.00–2.71), stitch
  p50 3.99 mm, 13% of the top fill's thread; top fill pitch p50 0.19 mm
- diagonal (30–60°) sparse pass first: 3
- near-parallel sparse pass first: 4
- no sparse pass first: 10 (running stitch first 8, nothing first 2)

Also seen [M]: three beanie files open with a full-design fill at 0.5 mm pitch,
3.5 mm stitches, with nothing under it — a knockdown layer, which the backlog
lists as unbuilt (`machine-physics-backlog.md:58` [D]).

**Third-party corpus** [M] — `scratch_corpus/` (36 free designs), 44 fills over
the same bar: crossing sparse pass first 8, diagonal 3, near-parallel 23, none
first 10. Messier, and the near-parallel majority is exactly what my crude rule
would produce from layered or re-entered fills, so I would not lean on it.

**Against law 26** [D] (`docs/corpus-laws-round3-2026-08-01.md:281-294`):
"a lattice is 7 cases in 507"; recipes interior walk 21.7%, edge run 17.6%,
none 14.2%, ~27% carrying a zigzag. Its corpus was the 36 third-party files
plus four of Kent's (`:8-12`); the Becker LC file and most of the commissioned
set were not in it. Its 507 fills have no size cut, and the same doc records
"a 1,913 mm² region carrying a sparse pass at 2.93" in one of Kent's files
(`:36`). My reading [I]: law 26 is probably right about the *population it
counted* (many small fills in script designs) and wrong as a rule for a large
fill on a knit in Kent's own trade work. The two instruments have not been run
on the same fills, so this is a disagreement to resolve, not a refutation.
Note also that even on law 26's own numbers about half of fills carry
something in the interior (walk or zigzag); `edge_run` supplies neither.

---

## 4. What primary sources say

Fetched 2026-10-05 by a research sub-agent; web pages came through a
summarising fetch, so short quotes are close paraphrase. The two PDFs (Stitch
Era, Madeira) were read directly.

| source | fill underlay | spacing / stitch | angle vs top | inset | default? | by fabric |
|---|---|---|---|---|---|---|
| **Ink/Stitch** source, `lib/elements/fill_stitch.py` | sparse fill of the same kind | 3× fill row spacing (0.75 mm at the 0.25 default); max stitch = fill's (4.0 mm) | fill angle + 90° | 0 mm | **ON** | tutorial: more on thick/high-pile, several directions |
| **Wilcom EmbroideryStudio** help (`docs.wilcom.com/…/stabilizing-7`, `-11`, `-6`, `-9`) | Tatami "to stabilize large, filled shapes"; typical pair Edge Run + Tatami; Double Tatami + Edge Run on soft/elastic | no numbers published | "counter to cover stitching" | margin exists, no number | set by Auto Fabric, table unpublished | knits/pique more than drill/leather; small objects one layer, large two |
| **Hatch** help [D — `docs/hatch-manual-teardown-2026-08-08.md` §3.1-3.2] | Underlay 1 + Underlay 2; "Edge Run with Tatami or Zigzag for larger objects" | none published | — | none published | — | "on knits, edge run is best"; larger areas and stretchy fabrics need more |
| **Stitch Era** "Underlay 101" (ColDesi PDF) | "Parallel", mostly for complex fills; Edge Walk + Parallel "desirable" on knits | examples 1.0–2.0 mm rows, 2.5–4.0 mm stitch; edge walk 2 mm stitch | perpendicular or diagonal | examples 0.7–1.0 mm; minimum 0.2 | examples | zigzag/double zigzag on terry and fleece |
| **Embird Studio** manual | Edge + Zig-Zag 1 + Zig-Zag 2 | none published | follows cover angle automatically | — | — | turn off on firm fabric |
| **mySewnet / Premier+** help | None/Low/Medium/High | named levels | "perpendicular to the stitches of the actual fill" | — | — | — |
| **Brother PE-Design 11** | "Under sewing" on fills | Dense/Medium/Light | — | — | — | — |
| **Madeira** "Avoid puckering" PDF | "Minimise underlay stitches" | — | — | — | — | anti-pucker context |

**Where they agree:** under a fill, an open crossing fill of the same kind,
much lighter than the top (0.75–2.0 mm), usually with an edge run on large
shapes and knits; more on stretchy/pile goods and large areas, less or none on
firm goods and small objects; **none under gradient or variable-density fills**
(Wilcom, mySewnet).

**Where they disagree:** inset (Ink/Stitch 0, Stitch Era 0.2–1.0, Wilcom
unstated); strictly 90° vs 45°/135° allowed; and *direction on knits* — the
software vendors say add, Madeira says minimise (different failure: pucker).
Hatch's "on knits, edge run is best" sits on a page the teardown reads as
lettering-scale; the same page says larger areas need more.

**Against this engine** [I]: the taxonomy matches. The numbers do not — our
lattice is 2.5 mm rows / 2.5 mm stitches, against 0.75 (Ink/Stitch default),
1.0–2.0 (Stitch Era examples) and ~1.0 / 4.0 (Kent's digitizer). Our 1.0 mm
inset is at the top of the published range. And we ship no area term at all,
which the Hatch teardown already flagged (`:271`, `:603`).

Ink/Stitch is GPL-3.0: numbers cited, no code proposed for porting.

---

## 5. What has already been decided or tried here

- **Law 26, shipped 2026-08-05** [D, C]: knit `fill_underlay`
  `edge_lattice → edge_run`. Browser half landed 2026-09-07 after a month of
  silent drift (DOCTRINE.md:1836-1848, `fabrics.js:32-38`). I found no entry
  recording this as Kent's ruling; it reads as a corpus-law landing.
- **The 13 mm gap, 2026-08-06** [D] (`docs/scope-history.md:3398-3418`,
  `3620-3634`): an audit flagged knit fill interiors "up to 13mm from the
  nearest underlay stitch (vs 1.6-1.8mm under the old `edge_lattice`)".
  `center_run` was measured as no help; "only a full grid/lattice pass …
  actually closes it"; closed as declined because law 26 says lattices are
  rare. This is Kent's observation, made by an instrument two months ago.
- **"Missing backfill" refuted, 2026-08-20** [D]: satin letters only — see 2.2.
- **Kent's "back stitching", 2026-10-01** [D] (DOCTRINE.md:8028-8045, memory
  `envelope-junction-escapes-2026-09-30`): his words about the pro's Becker —
  "back stitching to support the detail layering … helps support the top
  threading so it has structure and support". The session measured the MARINE
  satin band, found equal support, attributed the difference to the comb
  split, and built-then-reverted a zigzag-underlay flag that was a no-op. Its
  rule 1 — "measure what the eye saw, not the word it used" — took it away from
  underlay. Today's fill measurement says the word was also literally right,
  one band higher in the same design [I].
- **Lettering construction plan** [D]
  (`docs/superpowers/plans/2026-09-19-lettering-construction.md`): the "underlay
  lever left OFF" is `satin_underlay_on_column` — where a satin stroke's
  underlay *ends*, to save a hop and a trim. Satin only; nothing about fills.
- **"5 mm underlay rung"** [D] (memory `fine-lettering-design-review-2026-09-03`):
  no *satin* underlay under a 5 mm extent, "Kent gated it without a sew-out".
  Satin only — and a precedent that a published, non-fabric-settled number was
  ruled outside gate 1.
- **Sew-outs** [D]: 2026-09-01, Instagram icon, 80.5 mm, pique + cutaway, 6/10;
  "fabric shows through" was read as density and seams
  (`first-physical-sewout-2026-09-01`, `sewout-five-points-2026-09-03`,
  `docs/sewout-findings-2026-09-03.md`). Underlay was not among the five
  findings. That icon classes `gradient` (DOCTRINE 2026-09-30) and the blend
  tier's no-underlay line predates the sew-out, so **the one physical sample
  was very probably sewn with no fill underlay** [I — not re-run; I do not know
  the exact config that was sewn].
- `docs/sewout-findings-2026-09-03.md:63` warns that `_underlay_paths` "derives
  its lattice from `row_mm`" — stale: the lattice uses its own constants today [C].
- `docs/hatch-manual-teardown-2026-08-08.md:258-262` still tabulates knits as
  `edge_lattice`. True when written, three days after Python had moved [D, C].
- **Open lanes:** `git fetch --all`, 231 remote branches, none named for
  underlay, lattice, support, stabilizing or knockdown.
  `docs/scope/1-auto-digitizing-quality.md:1037` mentions an unmerged
  `digitizer-satin-underlay-cap-fix` (satin).

---

## 6. Gates, per candidate change

| change | gate 1 (sew-out for physical constants) | gate 3 (no OFF tier ON without its instrument) |
|---|---|---|
| Hand gradient-lane **full-density** fills (the `stage6_blend.py:715` fallback) the fabric's existing style | **Does not apply** [I]: no new constant; it stops one lane skipping a preset the other lane already sews. | Not a tier flip. Repo habit still says build behind a flag, OFF, and show Kent renders. |
| Same for true ramp bands (`:927`) | Not a constant question, but primary sources say **don't** (Wilcom, mySewnet). Leave bare. | — |
| Underlay every piece when the inset splits a shape | Does not apply — geometry fix, existing constants. | — |
| Knit preset `edge_run` → edge run + crossing pass | **Applies**: "fabric presets" are named in the gate. Fabric is what settles it. Evidence available without a new sew-out: Kent's commissioned files, sewn on garments — the class the gate accepted for `FILL_ROW_MM`. Whether that precedent carries is Kent's ruling, not mine. | — |
| Lattice rows 2.5 → ~1.0 mm, stitch 2.5 → ~4.0 mm | **Applies**, same evidence class, same ruling. | — |
| Area term (small fills edge run only, large fills add the pass) | The threshold is a number no vendor publishes and no file states. Readable from the commissioned set (not done here). Applies. | — |
| Inset 1.0 mm → smaller, so 1–2 mm fills get an edge run | **Applies**: sources disagree 0 / 0.2 / 0.4–1.0; only cloth says when it peeks. | — |
| Knockdown layer on beanies/pile | Density and extent are physical — applies. | New tier; would arrive OFF. |
| Preview: an "underlay only" view; preflight line for a fill with no underlay | Neither applies — no stitch moves. | — |

Gate 4 (no quality claim on a raw agreement number): none of the above should
be argued from a scorecard delta. ROADMAP's advisory ordering also says "pull
compensation before underlay".

---
---

## Options, ranked

*Separate from the findings above; these are proposals.*

1. **Stop the gradient lane sewing bare fills.** Pass the effective underlay
   style into `blend_fill` and use it on the full-density fallback path; keep
   true ramp bands bare. Behind a flag, OFF, with before/after renders.
   *Delivers:* underlay under the fills of most real logos, where today there
   is none; makes the Studio's per-shape underlay control work there.
   *Cost:* small — one parameter, tests, gradient goldens re-read. Stitch count
   up roughly 4–5% of fill stitches on a knit (Fremont forced-flat: +644 on
   13,564). *Catch:* on a knit this buys only the perimeter walk, so on its own
   it will not change what Kent sees in the interior.

2. **Ask Kent to rule on the knit preset, with the commissioned files as the
   evidence.** Put law 26 and the Becker timeline side by side and offer:
   keep `edge_run`; go back to `edge_lattice` as built; or edge run + a
   crossing pass at the professional's ~1.0 mm / ~4 mm.
   *Delivers:* interior support under every large knit fill, both engines.
   *Cost:* `edge_lattice` as built is +6% stitches on logo_whitebg (5,758 →
   6,024); the professional's density would be roughly 13% of fill thread.
   Coverage thresholds were recalibrated when law 26 landed and would need
   re-reading. *Catch:* gate 1 — his ruling or a sew-out, and it reverses a
   shipped corpus law, so the law-26 instrument should be re-run on the
   commissioned fills first so the disagreement is settled rather than
   overruled.

3. **Underlay every piece of a split shape.** *Delivers:* removes a silent bare
   patch (71% of Becker's main fill inset today). *Cost:* small.
   *Catch:* more underlay-to-underlay hops; the trim count needs watching —
   underlay is already the largest trim kind on some fixtures
   (`1-auto-digitizing-quality.md:2677`).

4. **Make underlay inspectable.** An "underlay only" view in the Studio and a
   preflight note when a fill over some area has none. *Delivers:* Kent can
   check this himself, and the next lane that forgets underlay is caught.
   *Cost:* small–medium, no engine risk. *Catch:* changes no stitch.

5. **Add it to the next sew-out card.** One fill block three ways on pique —
   edge run / edge + 2.5 mm lattice / edge + 1.0 mm crossing pass.
   *Delivers:* the only evidence that actually settles 2 and the inset.
   *Cost:* Kent's machine time. *Catch:* memory `sew-out-accepted-as-is` — he
   has ruled sew-outs are not a standing to-do; this is his call to make.

6. **Area term and knockdown layer.** Real, both supported by sources and the
   commissioned files, both larger and both gated. Not before 1–2.

## Could not verify

- **Photo lane.** `photo_subject_stub` and `photo_scene_stub` produced 0
  stitches in this checkout, and `owl_kent` classed `gradient`. Whether that is
  the environment (segmenter/rembg availability) or current behaviour I did not
  chase. Photo-lane underlay (`edge_lattice` for fills, none on tonal tiers) is
  read in code only.
- `repro_gradient_white_icon.png` failed to decode here; not measured.
- **Physical effect.** Nothing here shows that the missing underlay causes what
  Kent sees on cloth. That is trade consensus and vendor documentation, not a
  measurement.
- **What Kent was looking at** — stitch order, a render, or a sew-out.
- **Wilcom/Hatch numeric defaults, Tajima Pulse, Coats/A&E, Gunold, Janome:**
  unpublished or not reached. Ink/Stitch satin underlay toggles being OFF by
  default is inferred, not read as a literal.
- **Edge run in the professional's fills:** not cleanly identified.
- My pro-file classifier is unvalidated; the commissioned set is one house
  style with repeated designs; the `Test Files` folder (85 fills, unknown
  provenance, mostly no crossing pass) was excluded from the headline and
  would dilute it.
- The config sewn on 2026-09-01 was not reconstructed.
- JS lettering fills and the JS `try/catch` drop were read, not exercised.
- **The working tree moved under the measurements.** Another session edited
  `digitizer_core/pipeline.py` and `digitizer_service/app.py` in the main
  checkout at 20:24–20:25 local, uncommitted, while these runs were in
  progress. The diff is one additive metadata field (`art_box_frac`) and places
  no stitch, so I do not expect it to move a number here — but the runs are
  "`cf9f89f1` plus that edit for the later ones", not a clean commit.
