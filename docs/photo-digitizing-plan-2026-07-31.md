# Photographic & gradient art in EMB-Bot — what flawless can mean, and how to build it

This document supersedes the 2026-07-22 honest ceiling ("photographic/gradient art cannot be auto-digitized to pro quality by any tool — flat art in, pro out"). That line was correct for the engine we had and is now too blunt: the genre has four distinct input classes with four different ceilings, and three of them are reachable with algorithms whose patents are dead and whose math fits our existing stitch primitives. What replaces it is a per-class ceiling, stated in product copy, enforced in preflight.

Synthesized from five research lenses run 2026-07-31 (commercial survey, algorithm literature, craft practice, patent landscape, CV front end). Provenance tags where a claim is load-bearing: **[P]** primary source fetched, **[S]** secondhand, **[M]** measured on this machine this session, **[CNV]** could not verify. Untagged statements are our own analysis or plan.

Two facts verified locally today **[M]**: (1) the digitizer venv's cv2 5.0.0 is **main-modules only — no `cv2.ximgproc`** (`AttributeError` on import), so rolling-guidance/L0 smoothing requires swapping `opencv-python` for `opencv-contrib-python` at the same 5.0.0.93 pin (kmeans feeds goldens; the swap must byte-verify them). (2) `cv2.FaceDetectorYN`, `createCLAHE`, `pyrMeanShiftFiltering`, `bilateralFilter` exist in the current wheel, and skimage 0.26 has `structure_tensor`, `slic`, `felzenszwalb`, `rag_mean_color`, `merge_hierarchical`, `deltaE_ciede2000` — the region former and direction field need zero new deps.

---

## 1. The quality bar, per input class

Context that sets every bar: **no vendor — Wilcom, Hatch, Brother, Embird, or any 2023–2026 AI SaaS — claims one-click photorealism.** Every vendor's docs demand prepped input ("crisp images, well-defined subjects, strong contrasts" [P — Hatch]), and the paid pet-portrait market advertises "manually hand-punched, not auto-converted" as its selling point [S — Etsy listings]. "Flawless" therefore means: indistinguishable from the best output the genre actually produces, with the remainder stated plainly.

Correction that matters for the competitive map: Sfumato Stitch is **Embird's** product, not Wilcom's [P]. Wilcom/Hatch ship PhotoFlash (mono scan-line), Color PhotoStitch (layered run stipple), and Reef (single-color non-crossing meander) [P].

### (a) Flat spot-color logo — the current lane
- **Customer sees:** crisp satin lettering, clean tatami, correct thread run sheet.
- **Flawless =** commissioned-digitizer parity as measured by the playbook laws (satin rails 0.40–0.51 mm, trims/1k in the 0.1–4.1 corpus band, corners sewn through, borders at 1.4 mm). Closing this is the current stitch-quality round's job, not this doc's.
- **Impossible:** text under ~4 mm cap height, detail under ~0.7 mm — physics, already enforced.
- **Promise:** pro out. Unchanged.

### (b) Gradient / AI-render logo — the drone-render class
- **Customer sees today:** flatten posterizes the render into ~6 hard-edged bands; "approximate emblem" was the honest verdict on Kent's drone PNG.
- **Flawless =** what hand digitizers do: each ramp rendered as **3–5 thread shades interleaved as fractional-density tatami layers at ONE common angle, per-layer spacing = 0.4 mm × layer count, total coverage ≈ 1.0–1.2** — reads continuous at arm's length. This is Campbell's published blend math [P — mrxstitch.com/density], and it is a parameterization of our existing tatami, not a new stitch type.
- **Impossible (goes in product copy):** a literally continuous gradient (thread quantizes at 0.4 mm rows against a ~400-color chart, not 16M); glow/bloom/metallic specular (those are light, not pigment); small text embedded in renders at hat scale.
- **Promise:** smooth blends, no banding, honest shade count.

### (c) Portrait / pet photo
- **Flawless =** the top of the auto genre **plus the one thing no auto tool ships.** Genre best is PE-Design Photo Stitch 1-class layered 10–15-color run blending — reviewers' verdict "reads like a real portrait" [S — hoopingstation head-to-head] — and Embird Sfumato in skilled hands. What none of them have: **stitch direction that follows image structure** (hair flow, fur growth). That gap is exactly what the manual Etsy market monetizes. Our ceiling: layered tonal stitching driven by a direction field, per-zone shade ramps (3–5 shades/zone, 8–12 spools total [P/S — Sfumato manual, Elliott, Hatch]), eyes/whiskers as discrete top objects ending in a minimal satin glint [P — Embroidery Legacy], fabric left bare as a value.
- **Hard floors:** face work needs a **5×7" hoop minimum** [S — Brother's own guidance; corroborated by retail photo designs at 81×99 mm/16k st already being "small" [P]]; input **≥10 px per output mm** [P — Embird]; plain or removed background.
- **Impossible:** guaranteed likeness — a 0.4 mm grid does not reliably resolve soft-tissue proportions; the review screen exists because likeness lands sometimes, not always. Faces at 4×4". Hair-level matting (thread can't render sub-mm hair regardless). Busy backgrounds at subject fidelity.
- **Promise:** "portrait-style embroidery from your photo, reviewed before you stitch" — never "your photo, in thread."

### (d) Scenery / product photo
- **Flawless =** the meander/sfumato class: tone rendered as the density of a wandering **non-crossing** run line, fabric show-through as the highlight value, 1–3 colors, single-digit trims — or full-color layered work at ≥150 mm (marketplace scenery runs 110–150k st at 20–30 cm, 10–13 colors [S — embgallery]). Product shots usually decompose to subject cutout + the gradient lane (b): a bottle is ramps, not a photo.
- **Impossible:** scenery below ~120–150 mm (the genre barely sells it smaller); separating an iso-luminant subject from its background without a user click; full-coverage photorealism without the "stiff as a piece of wood" outcome [S] — sustained >3.5 st/mm² over a large area is a board.
- **Promise:** art-print-style tonal rendering with the size floor enforced.

**Stitch budgets, marketplace-measured [S]:** mono sketch/meander class ≈ 0.5–1.0 st/mm², 1–3 colors; color photo class ≈ 2.0–3.5 st/mm², 7–15 colors. Single-needle default caps color stops at ~10 (vendor defaults corroborate; forum evidence unverifiable [CNV]) with a multi-needle mode unlocking 15+.

---

## 2. The technique menu

Architecture rule first: **every photo tier emits polylines into the existing StitchRun/StitchBlock plan.** Streamlines, meanders, scan rows, and sketch passes are run/bean geometry; gradient blends are tatami with modulated row spacing and phase. Stage 5 (pull comp), stage 7 (sequencing), export, preflight, and the review UI stay untouched surfaces. The photo path replaces stages 1–2 for photo classes and adds tiers to stage 6.

| # | Slot | Choice + citation | Why this one | License / status |
|---|---|---|---|---|
| 0 | Input classifier — `stage0_classify.py` | Unique-color mass + gradient-smoothness + alpha heuristics; 4-way flat / gradient / photo-subject / photo-scene; user-overridable | Flat class must route to today's pipeline **byte-identically** — the classifier protects the working lane | ours, trivial |
| 1 | Background removal | **rembg 2.0.77** harness (cp314 wheels [P]); `isnet-general-use` default, `birefnet-general-lite` quality tier, `u2net_human_seg` portrait fast tier. Binary mask + morphology at stitch scale, islands under min-sew-area dropped. **SAM 2** (install from Meta's git — the PyPI name `sam2` is a third party [P]) drops into the existing `Segmenter` ABC later for click-to-fix and instance splits | Zero-click cutout is what the honest floors demand; no alpha matting because thread can't render it | MIT / Apache-2.0 / MIT. **Never bria-rmbg (CC BY-NC)** [P] |
| 2 | Face priors | `cv2.FaceDetectorYN` (YuNet), main cv2 **[M present]**, model MIT [P] — 5 landmarks → elliptical importance masks | Protects eyes/mouth from smoothing, drops merge threshold locally, boosts palette weight 8–10×; 5 points suffice for embroidery-scale features | MIT |
| 3 | Tone prep | CLAHE on L of Lab (clip 2–3, tiles 8×8) **[M present]** + contrast stretch | Rescues shadow detail before region forming; milliseconds | in cv2 |
| 4 | Texture kill | `rollingGuidanceFilter` (scale-aware: erases weave/pores/JPEG noise below a chosen size, keeps structure) or `l0Smooth` for the flattest look — **requires the contrib swap [M: absent today]**. Zero-dep fallback shipping now: `bilateralFilter` / `pyrMeanShiftFiltering` **[M present]** | Manufactures "flat art" out of a photo before segmentation — the direct fix for posterize mush | Apache-2.0 (contrib) |
| 5 | Region former (replaces k-means for photo classes) | **SLIC in Lab (~800–2000 superpixels) → RAG `merge_hierarchical`** with ΔE00 edge weights, min-area floor (force-merge < ~2–3 mm² at hoop scale), face-local threshold drop **[M all present]** | Global k-means assigns pixels independently of adjacency — gradients dither into speckle; superpixels + perceptual merge is why regions come out sew-able (20–80 of them) with photographic boundaries | BSD (skimage) |
| 6 | Direction field | `skimage.feature.structure_tensor` **[M]** → **ETF smoothing reimplemented from Kang, *Coherent Line Drawing*, NPAR 2007** (~50 lines numpy; GitHub reference impls have unverified licenses — reimplement from the paper). Per region: dominant angle + coherence; low coherence falls back to house angle | The single biggest visible gap between "posterized patch fill" and pro photo stitch is stitches following structure; ETF is the NPR-standard, O(N)-ish way to know structure | paper; our code |
| 7 | **Gradient blend tier** — `stage6_blend.py` | Ramp detection (structured residual, not speckle) → decompose into 3–5 chart shades → N interleaved tatami layers, common angle, per-layer spacing 0.4×N, phase-offset rows, Σ coverage 1.0–1.2 [P — Campbell]. Color model: **Ostromoukhov–Hersch multi-color dithering, SIGGRAPH 1999** [P] — thread is opaque and side-by-side, so express each cell as barycentric coverage of 3–4 chart colors; realize fractions as interleaved rows | The drone-render fix. O–H's side-by-side non-overlap assumption is literally how thread works — it replaces naive nearest-thread quantization, the measured mush source | papers; existing tatami emitter |
| 8 | **Scan-line tonal tier** (mono) | Rows across a chosen grain; darkness → row spacing + zigzag amplitude. The PhotoFlash class; underlying commercial art expired/JP-only (§3) | Cheapest wow-per-effort in the genre; a variant of the existing fill row generator | clear |
| 9 | **Meander tonal tier** (mono — the Reef/Sfumato look) | **Hilbert-curve traversal with darkness-driven zigzag bursts — Velho & Gomes, space-filling-curve halftoning, SIGGRAPH 1991** [P]. O(N), deterministic, one continuous path | Non-crossing and single-trim **by construction** — Reef's two selling points fall out of the curve itself. Loose areas let fabric show; **no underlay beneath** [P — craft consensus]. Sfumato's parameter sheet (Highest Density 0.35–0.45 mm, shade thresholds, loose/heavy styles [P]) is the knob-set spec to mirror | paper; feeds run tier |
| 10 | **Streamline thread-paint tier** (color photo) | **Jobard–Lefer evenly-spaced streamlines (1997)** traced in the ETF field; d_sep = row pitch modulated by luminance per color layer; layers dark→light, long-sparse under then shorter-denser over (Hertzmann 1998 coarse-to-fine; random-needle multilayer recipe). **Read Liu et al., *Directionality-Aware Design of Embroidery Patterns*, CGF 2023 + its `embroidery-streamlines` repo FIRST** — the only published fabricable photo→stitch codebase; mine it for divergence-aware seeding and connectivity failure modes; license unverified, default is reimplement | This is the "what no auto tool has" tier: rows that follow fur and hair. Streamlines resampled at 2.5–4 mm are run stitches; connectivity optimization is our trim budget | papers; repo read-only until license check |
| 11 | Detail layer | FDoG coherent lines (same Kang 2007 machinery) → **bean runs** on top; eyes per the Embroidery Legacy recipe — pupil, dark iris, **satin glint LAST and minimal** [P] | Details never merge into fill quantization; the glint is the difference between a portrait and "dead eyes" | existing bean tier |
| 12 | **Sketch tier** — `stage6_sketch.py` | Playbook **law 10** — observed in the corpus (corgi/snowman/rose: ~6 runs, 12k st, 1 trim), never built. It IS the photo primitives: layered run passes + FDoG detail lines | Building tiers 8–11 delivers law 10 nearly free — a config preset, not a new engine | corpus-measured target |
| 13 | Palette vs chart | **Weighted k-medoids restricted to the in-repo chart** (68 brands / 19,857 colors, already policy-filtered), ΔE00 objective, region weight = area × class multiplier (eyes 8–10, skin 4–5, subject 2, background 1) | Chart data is a solved problem in this repo; this is ~100 lines of selection. Per-zone shade ramps, not global quantization [P — Sfumato/Elliott/Hatch] | ours |
| 14 | Sequencing + underlay deltas | Stage 7 photo override: **depth-sorted** — background→foreground, dark→light within an object, details last [P — universal craft consensus] — replacing largest-area-first. Underlay split: light mesh under full-coverage subject zones, **none** under meander/sketch, edge-run under top satin details [P] | Winners read as drawings executed in thread; losers read as uniform scan conversions | config in stages 6/7 |
| 15 | Guardrails (preflight) | px/mm < 10 → warn; face below the 5×7 floor → block with size-up suggestion; ΔL(subject, bg) small → "subject will vanish" warn; est. > 25k st → cutaway prescription on the worksheet [P — OESD]; nap fabric → WSS-topping line; single-needle 10-stop cap; background policy switch omit / half-density sketch / appliqué | Quality in this genre is decided before stitching — every vendor's docs say so. **Resize structurally re-digitizes in our architecture** (2026-07-27 fix), which dodges Hatch's shrink-after-generate needle-break failure — bake invalidation required | extends `preflight.py` |

---

## 3. Patent posture (engineering due diligence, not legal advice)

**Free — verified expired/lapsed on Google Patents; re-verify the load-bearing ones on USPTO Patent Center at the consult:**
- The whole classic auto-digitizing pipeline we already ship (Goldman/Soft Sight US6804573 / US7016756 / US9200397) — expired 2018. Current lane is clear.
- Wilcom curved fill US6587745B1 — dead 2019.
- **Tonal run/meander with density-from-tone: no live patent found anywhere.** Brother's early photo work was JP-only and term-expired (JP2001259268A); Embird never patented Sfumato. This is the safest lane and also the genre's classic look. Tiers 8 and 9 ship freely.

**Live — six to design around:**
- **Brother US7693598 (exp 2028), US7946235 (2030), US7996103 (2030), US8200357 (2031):** the per-pixel "angle characteristic" → colored line-segment pipeline plus specific improvements (rescale-then-recompute-angles; low-contrast angle correction; jump→run conversion rule; user-edited angle regions). Each is a multi-limitation combination. Our design differs structurally: **region-level** structure tensor/ETF on segmented regions feeding existing satin/tatami/streamline emitters — not per-pixel line-segment color data. Do not replicate any full claim chain.
- **Drawstitch US10132018 (exp 2037):** Sobel field → **median-cut to 10–15 colors** → same-color pixel polylines with perpendicular density offsets. We use weighted k-medoids against a real thread chart (not median-cut) and streamlines-in-ETF (not pixel-chained polylines). Distinguishable; confirm at consult.
- **Drawstitch US12518360 (granted 2026-01, exp 2044):** the grayscale → Gaussian blur → **color-dodge blend** → percentile-stretch sketch recipe. Our sketch tier is FDoG lines + layered runs — a different recipe. Simply never implement the color-dodge chain.
- **Cimpress US8798781 (exp 2031):** snap-to-thread-palette then iterative pair-merge by color similarity + edge characteristics. This is the closest live claim to our **existing** quantize→snap. Claim-chart it.

**For the already-planned one-hour IP consult:** (1) claim chart of existing quantize/snap vs US8798781 claim 1; (2) planned photo pipeline vs US10132018 and US12518360 claim 1, with full Drawstitch/Brother/Cimpress portfolio pulls (our search was keyword FTO-lite on machine-generated status fields); (3) confirm US8473090's lapse is final; (4) JP-only filings if Japan distribution ever matters. Build consequence: blend and tonal tiers (7–9) proceed now; the streamline tier (10) is built on distinguishable primitives but goes past counsel **before public launch**, since it sits nearest the live art.

**GPL hygiene:** StippleGen and Ink/Stitch are GPL — algorithms from the papers, never their code. TSP-tour rendering is dropped outright (Concorde's license is academic-only; the meander covers the same look). Thread palettes are already solved in-repo under the facts-doctrine policy decision of 2026-07-29.

---

## 4. Build order

Slots **after the current stitch-quality round closes** (chaining task #5, adversarial review #6). Every step lands the way stages 1–7 did: per-stage debug PNGs, deterministic goldens, smoke-before-test.

**Fixtures:**
- **F1** `Downloads/enthusiast enterprises logo.png` — flat control (the real benchmark, per standing rule).
- **F2** `Downloads/ChatGPT Image Jul 15....png` — Kent's drone render; the gradient class's founding complaint.
- **F3** `digitizer/testdata/photo/portrait.png` — NEW: front-lit face, ≥1200 px across, plain background, ≥300 px between the eyes (public-domain or Kent's own).
- **F4** `digitizer/testdata/photo/pet.png` — NEW: pet with directional fur and visible eyes, ≥1500 px.
- **F5** `digitizer/testdata/photo/scenery.png` — NEW: landscape with sky gradient + foliage.
- **F6** — NEW `tools/make_gradient_fixture.py`: seeded synthetic linear + radial ramps. Goldens must not depend on found photographs.

**Steps (sessions):**

1. **Classifier + honest copy (1).** `stage0_classify.py`, preflight surfacing, per-class ceiling copy in the UI. *Accept:* F1 → flat **and byte-identical plan vs today**; F2 → gradient; F3/F4 → photo-subject; F5 → photo-scene; misroutes user-overridable.
2. **Gradient blend tier (2–3).** Ramp detection, shade decomposition, interleaved tatami. *Accept:* F6 goldens — per-layer spacing = 0.4×N ± 0.02 mm and Σ coverage 1.0–1.2 **measured from emitted rows**; F2 at 90 mm — render A/B vs today's flatten shows no banding at arm's length, ≤5 shades per ramp, one common angle per blend group asserted in-plan.
3. **Contrib swap + photo prep (1–2).** `opencv-contrib-python==5.0.0.93` swap with **golden byte-verify as the gate** (kmeans is exact-pinned); rembg dep + model-cache policy; YuNet; CLAHE; rolling-guidance with face-mask blend. *Accept:* all existing goldens hold post-swap; F3 background removed + 5 landmarks found; prep debug PNGs; per-stage CPU time logged — the 3–8 s fast-tier figure is an estimate until this measures it.
4. **Photo region former (2).** SLIC + RAG(ΔE00) + min-area floor + face-local threshold. *Accept:* F3 at 5×7 — eye whites/iris/pupil survive as regions ≥1 mm; F4 — 20–80 regions, none under 2 mm² at hoop scale; seeded SLIC pinned deterministic.
5. **Direction field (1–2).** Structure tensor + reimplemented ETF, coherence gate. *Accept:* F4 angle-map debug PNG shows fur-following angles; low-coherence regions fall back to house angle; per-region angle feeds the existing tatami angle parameter on a real plan.
6. **Mono tonal tiers (2–3).** Scan-line + Hilbert meander. *Accept:* F3 mono at 5×7 = 1 color, ≤2 trims, 0.5–1.0 st/mm²; tone fidelity metric defined on F6 first (plan-density map vs source luminance, target r ≥ 0.8 — validate the metric on known-clean fixtures before trusting it, per the metric-hygiene rule); non-crossing asserted geometrically.
7. **Palette k-medoids (1).** Chart-restricted weighted selection. *Accept:* F3 ≤12 colors with eyes keeping dedicated darks; F4 fur ramp = 3–5 shades of one family; flat-lane snap regression-unchanged.
8. **Streamline color tier + details (3–4).** Liu et al. repo read first (license check; else paper-only); J-L streamlines in ETF with luminance d_sep; dark→light layers; FDoG bean details; eye glint recipe. *Accept:* F4 at 150 mm — 8–12 colors, 2.0–3.5 st/mm², trims/1k ≤ 4.1 (corpus band), fur direction visible in render; F3 — glint present as the final satin object; depth-sorted sequencing asserted.
9. **Sketch preset + background policy + guardrails (1–2).** Law-10 preset (target fingerprint class: ~6 runs / ~1 trim on F4); background switch omit / half-density sketch / appliqué; all §2 row-15 guards. *Accept:* every guard fires on a constructed negative (tiny face, low-res input, iso-luminant pair) and stays quiet on F1–F5 happy paths.
10. **Sew-out gate (1 + machine time).** Four-patch sampler on the Tajima, cutaway, tight woven: F2 blend at 90 mm, F3 mono meander at 5×7, F4 color at 150 mm, F5 scene. The fill-interleave question (law 7) and lock length (law 6) get answered here and go back into the playbook as laws. **Nothing in classes (c)/(d) is marketed before this gate passes.** Class (b) may ship after step 2's render A/B if Kent accepts screen evidence.

Total: **15–21 sessions.** Ordering rationale: each step lands independently; the classifier protects the flat lane from day one; the patent-free tiers (blend, scan-line, meander) deliver customer value before the hardest tier (streamlines) is attempted.

---

## 5. Non-goals

- **One-click photorealism.** Nobody has it. The review screen is part of the product, not an apology.
- **Neural stitch generation.** The 2020–2026 literature contains zero fabricable neural path generators — it is uniformly appearance rendering (MSEmbGAN et al.). Nothing to borrow; not building one. The only transplantable neural ideas (learned per-region stitch-type choice, commercial-digitizer-generated training data) are parked.
- **TSP-art tour rendering.** Concorde licensing plus the meander covering the same look. Dropped.
- **GPL or restricted deps.** No Ink/Stitch code, no StippleGen code, no bria-rmbg (NC), no dlib 68-point landmarks (NC training set), no mediapipe (no cp314 wheels — a sidecar 3.12 venv is not worth 5 landmarks we already get from YuNet).
- **GPU.** CPU budgets only. Full BiRefNet stays a labeled slow tier (~23 s/image, one community CPU datapoint [S]) or off.
- **Alpha matting / sub-millimeter hair.** Thread physics, not a software gap.
- **Full-frame uniform-density photo fill.** The measured amateur tell; fabric is a value.
- **Competing with hand digitizers on likeness commissions.** We sell speed, price, and honest ceilings; the manual market keeps the top end, and the product copy says so without embarrassment.

---

## Instrument limits, stated plainly

- Every CPU timing above is an estimate except the two **[M]** checks; the only primary-sourced performance numbers found in the entire research pass were Meta's A100 FPS and one community BiRefNet CPU report. Benchmark before promising latency.
- The 5×7 face floor is dealer/vendor-blog provenance [S] — Brother's page 403s crawlers. Treat as strong convention until our own sew-outs confirm or move it.
- The single-needle ~10-stop cap is vendor-default corroborated, forum-evidence unverifiable [CNV]. It is a config default, not physics.
- Fill interleave (0.20 effective vs two staggered 0.40 passes) and lock length (corpus 0.45 vs our 0.8) remain sew-out decisions; step 10 answers both.
- The patent read is keyword-level FTO-lite over Google Patents' machine-generated statuses. The consult re-verifies; until then, tier 10 does not ship publicly.