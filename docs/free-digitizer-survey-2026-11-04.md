# Free auto-digitizing software — the field, and what to benchmark

*Surveyed 2026-11-04 at Kent's request ("find all of the free digitizing
softwares, and identify which ones we should be benchmarking"). Three Sonnet
researchers swept web tools, desktop software and research code; the top
candidates were re-fetched by hand. **Nothing here was tested with a real
upload** — every capability line is the vendor's or the README's own claim
until the benchmark in §2 runs. Claims a researcher could not open are tagged
UNVERIFIED.*

---

## 0. Why this did not exist before

The repo already holds six competitor documents, and every one is a teardown
of ONE product's documentation or code:

| Doc | Date | What it is |
|---|---|---|
| `docs/masters-teardown-2026-08-01.md` | 08-01 | Wilcom / Brother / Melco / Pulse patents |
| `docs/emberdesign-competitive-research-2026-08-07.md` + two Ember teardowns | 08-07..09 | Ember's app, pricing, architecture |
| `docs/hatch-manual-teardown-2026-08-08.md` | 08-08 | Hatch v3 online help, 20 pages |
| memory `dade-app-teardown-2026-11-04` | 11-04 | DADE crawl + MFab head-to-head |

None of them surveyed the field, and until DADE today **no competitor's engine
was ever run on our artwork**. The yardstick has been Kent's professional
digitizer's files (the 100-pair yardstick, the lettering board, the pro-pair
sitting), per ROADMAP and DOCTRINE. That was the right primary yardstick — a
free auto-digitizer is a weaker thing to beat than a hand digitizer — but it
left two gaps that cost nothing to close:

1. **The Hatch trial exports 30 unwatermarked stitch files in 30 days, and the
   Wilcom EmbroideryStudio 2026 trial runs 14 days with no stated export
   limit.** Both have been there the whole project. We tore down Hatch's manual
   and never ran Hatch.
2. **Three runnable open-source raster-to-DST engines appeared in 2026**
   (heatstitch, openstitch, Nuizu). They did not exist when the August
   teardowns were written; nothing since re-checked the field.

The literature side is the one place we are ahead: no paper or repo found
compares its output to a professional's stitch file. Our region kappa and
chance-corrected legibility figures have no published peer.

---

## 1. The field

### 1a. Web tools — free stitch-file DOWNLOAD (the ones that matter)

| Tool | Maker | Free tier | Formats | Auto features claimed | Catch |
|---|---|---|---|---|---|
| **Stitch AI** — dynamicmockups.com/stitch | Dynamic Mockups, Inc. | Free "while we learn", no card, no end date | DST only (PES/EXP "next") | Region planning, palette, per-region angle / density / puff / fill flow, production sheet with stitch count, trims, colour sequence, size in mm; ~15 s | Desktop browser only; free tier explicitly "a launch decision rather than a permanent promise" |
| **Stitchist** — stitchist.app | anonymous | 1 free Auto Digitize; DST + PES at one size | Free: DST, PES. Pro: 8 formats | Satin / fill / running / bean per shape, underlay, density, pull comp, trims, short-stitch removal, tie-ins, colour-block merge, 32 satin fonts | $50 one-time for unlimited (cheapest real unlock found) |
| **Embrowser** — embrowser.com | solo SF engineer | 2 image auto-traces per week, export free on every plan | PES, DST, JEF, VP3, EXP, U01 | Trace All = tatami per colour; node editor; Auto route (beta) | 2 traces a week makes a corpus run a quarter-long job; Hobby $9.99/mo |
| **click-stitch** — click-stitch.com | anonymous | 3 conversions/day, no watermark | PES, DST, JEF, SEW, EXP, VP3, XXX | Palette reduce, fill + satin, running-stitch line art, cross-stitch, ~50 fonts | **3 colours and 3 inches** — excludes nearly all of our corpus at the pro's size |
| **SewFlow** — sewflow.com | undisclosed | "Classic" digitise + download free with account | JEF, PES, DST, EXP, XXX, SEW | Classic = tatami fill only; AI tier adds satin on lettering | AI download paid; Classic is a fill-everything baseline |
| **EmbroidAI** — embroidai.com | VNK Labs Pvt Ltd (India), v1.3.0 | 10 credits at signup = ONE download | DST, PES, EXP, JEF, VP3, XXX, HUS | Auto underlay, pull comp, "smart pathing", colour optimisation; API | Marketing pages say "free download", pricing page says 10 credits per download; $5/50 credits ≈ $1 a design |
| dstfileconverter.com, sharkfoto.com/free-tools/embroidery, fullyfreetools.com | anonymous | "100% free, no signup" | DST, PES, + | Unspecified | UNVERIFIED engines; no terms read; quality unknown |

### 1b. Web tools — free PREVIEW, paid download (not benchmarkable for free)

StichAi (stichai.pro, 1 free then $4.99/5), Stitch AI by RosesAllDesign
(stitchai.us, beta, coins), Figitize ($1.99/design), StitchFast (£4.99),
Embify (£5/file, has a "Sew Score"), StitchPilot.ai ($29/mo, staging domain).
StitchForge: coming soon. DeployGod: DNS dead.

### 1c. Desktop — free or open source

| Tool | Licence | Auto-digitize a raster? | Free export? | Status |
|---|---|---|---|---|
| **Ink/Stitch** | GPL-3.0 | No — vector-first; Inkscape's Trace Bitmap, then assign stitch types by hand | Yes, all formats | v3.3.0 2026-07-31, commit 2026-11-03. Already clean-roomed for fonts; manual, not a peer |
| **Embroidermodder 2** | zlib | No — viewer / editor / converter, alpha | Yes | Nightly 2026-07-03; "don't rely on it" |
| **Embrilliance Express** | freeware | Lettering only (BX fonts) | Yes | Current |
| **My Editor** (Wings) | freeware | No | Yes | UNVERIFIED version |
| **Wilcom TrueSizer** | free w/ registration | No — resize / view | Limited | UNVERIFIED |
| **PEmbroider** (CMU) | GPLv3 + ACSL | Algorithmic: hatch fills from SVG / B&W bitmap, TSP-ordered | Yes, 7 formats | Last push 2025-06-13, 611 stars; code-driven, no colour or satin logic |
| Thred, SophieSew, Thred32 | freeware (UNVERIFIED, sites unreachable) | No — manual | — | Abandoned (2016 or older) |
| **Stitch Era Universal** | — | — | — | **Free edition ended July 2013.** Sierra lists only Liberty and Artist, paid |
| "Pebby" | — | — | — | Appears in one listicle; no publisher found. Treat as not real |

**No free desktop tool auto-digitizes a raster.** Every one that does is paid
or a trial.

### 1d. Desktop — trials that include auto-digitizing

| Tool | Trial | Auto-digitize | Export during trial | Source |
|---|---|---|---|---|
| **Hatch Embroidery 4** (Wilcom) | 30 days, every level (Organizer → Digitizer), no VM | Yes (Composer, Digitizer) | **30 stitch-file exports, no watermark** | help.hatchembroidery.com trial-restrictions article |
| **Wilcom EmbroideryStudio 2026** | 14 days, all four levels + Elements, Windows only, no VM, no card | "Advanced digitizing tools"; Smart Design one-step bitmap auto-digitizing is in the product | **No restriction stated** on the trial page (UNVERIFIED in practice) | wilcom.com/free-trial |
| Ricoma Chroma Luxe | "Unlimited" trial, Win/Mac | Yes (Inspire's one-click) | **Blocked** — export is the one excluded feature | info.ricoma.com/chroma-free-trial |
| Brother PE-Design 11 | length unstated | Auto Punch in paid product | **Blocked** — saving and exporting disabled | brother.com ped11trial |
| Embird + Sfumato | 30 days / 100 runs | Digitizing Tools, Sfumato photo stitch | **Blocked** — saving disabled in those modules | embird.net/free-trial |
| SewArt (S&S) | 30 days, ~$75 | Yes — built around it | Trial designs capped at 3 colours (2021 review; site unreachable, UNVERIFIED) | machineembroiderygeek review |
| Janome Artistic Digitizer 2.0 | windows only: Apr 2024, Apr 2025, Oct–Nov 2025, 1–30 Apr 2026, by emailed code | Yes | UNVERIFIED | janome.com 403 |
| Bernina Software 9 | 30 days | not confirmed | UNVERIFIED | bernina.com/V9trial |
| mySewnet | Basic free = view/edit; Silver/Gold 30-day trial | QuickCreate; tier UNVERIFIED | UNVERIFIED | plan pages 404 |
| Brother Artspira (mobile) | Artspira+ ~$12.99/mo, 1 month free w/ card | Image to Embroidery (Artspira+ only) | **No file export** — wireless to a Brother machine only | support.brother.com func2 |

### 1e. Research code — raster in, machine file out (all 2026 unless noted)

| Repo | Licence | Runs how | Output | Stitch logic | Why it matters |
|---|---|---|---|---|---|
| **pfedan/heatstitch** — heatstitch.app | MIT (Daniel Pfeffer) | Browser, no backend; `npm run dev` locally; Rust core + TypeScript; 608 commits | PES, PEC, DST, JEF, VP3, EXP, XXX + stitch sheet | Resample 0.1 mm/px; bilateral in Lab; weighted k-means + CIEDE2000 to Brother threads; **<1 mm run, ≤7 mm and even → satin, else fill**; fill direction from image streamlines (Jobard-Lefer); narrow regions sew last; underlay 90°, 3× spacing, 0.4 mm inset, skipped under 40 mm²; trim ≤1 mm stitch / ≤3 mm jump / else tie-off; DST trim = 3 jumps | Closest published-style analogue to our pipeline, permissive licence, hosted |
| **lb2002/openstitch** (OpenStitch Studio) | **AGPL-3.0+** | PySide6 GUI; Win/Mac/Linux binaries; `pip install -e .`; 43 commits, updated 11-04 | DST, PES, EXP, JEF, VP3, U01, PEC, PDF sheet | Medial-axis skeleton + distance transform; thin → triple/bean run; lettering/columns → satin w/ split + underlay; areas → tatami/contour w/ edge or lattice underlay; directional pull comp; hidden travel along outline; **virtual stitch-out score /100** + independent re-read of exports | Richest feature list; AGPL means **benchmark its output, never read its code into ours** |
| **Mokuichi147/Nuizu** | Apache-2.0 / MIT | `uvx nuizu dst photo.jpg -s 100` | DST, PES, JEF + PNG/SVG preview | k-means in Lab snapped to 60+ thread brands; contours w/ holes; colour-grouped nearest-neighbour order; fill angle by PCA/minAreaRect; underlay; pull comp; satin only for outlines | One-line CLI → scriptable over the whole corpus in an afternoon; fill-everything baseline |
| **habon-el/needler** | **no LICENSE file** | Local web server, Python 3.11+, launcher scripts; SAM2 optional | DST, PES, JEF, EXP, XXX, U01, PEC | Tatami w/ underlay + edge-following travel, satin columns w/ pull comp, run/bean, lettering; "every format read back before download" | Same SAM2 idea as our photo prep; no licence = output only |
| 9valleb9/embroidery-magic | MIT | Python → Ink/Stitch SVG → Ink/Stitch export | 6 formats | Lab k-means, vectorise; readback checks: hoop fit, ≤12.1 mm stitch, one block per colour | Depends on Ink/Stitch; not independent |
| Frankyface/satin-studio | none shown | Browser | PES, DST | Flat-colour art → sections w/ per-section type + pull comp | small |
| EXPFAL/Embroideryforge, 2Ahmedsquared2/Suture | none / MIT | Python CLI / web; DeepSeek or Gemini plans, rules stitch | DST | LLM emits a stitch plan, geometry is rule-based | curiosity |
| sanjithudupa/Embroidery-Digitizer | n/s | web, SVG only | n/s | undocumented | stale |

**Papers.** None go raster → machine file with code. Worth reading, not
running: *Directionality-Aware Design of Embroidery Patterns* (Liu, Piovarči,
Hafner, Charrondière, Bickel; CGF 42(2) 2023 — sources/sinks from the
divergence of a density × direction field, streamlines smoothed into connected
paths, sewn on a Bernina B590; no code); Tian et al. *Shape decomposition
algorithm in embroidery* (skeleton fork points → stroke-shaped sub-regions
with parallel satin lines — the one principled satin-column decomposition);
Tian & Luo spiral fills (CAD ~2005). MSEmbGAN (TVCG 31) outputs images only
but its **dataset is 13K content/embroidery pairs made in Wilcom 9.0** — weak
labels for satin-vs-fill if the licence allows. Patents US 9702070 (satin vs
step-fill by element size), 7359760 / 7302308 (tentative tatami/satin per
needle point, then refine), 11727615 (jump reduction by segment merge +
nearest-endpoint order) are the only places the optimisation criteria are
written down. StitchOver (arXiv 2609.08311, 2026) is conductive-thread work.

### 1f. "AI embroidery" image generators — not digitizers

Pixlio, Artspira AI, and every Midjourney / Stable Diffusion "embroidery style"
site output a picture that looks stitched. No stitch file. Ignore.

---

## 2. What to benchmark

"Benchmark" here means: same artwork, same target size, their machine file
through OUR instruments (`stitchviz.render_design`, trims / cuts / exposed
travel, word-legibility cc, region kappa against the pro's file, preflight),
beside ours and the pro's. Three tiers by cost and what each can tell us.

**Kent's pick (2026-11-04):** Tier 1 and Tier 3 now; the Hatch and Wilcom
trials (Tier 2) after those complete.

### Tier 1 — free, local, scriptable: run the whole corpus (recommended first)

| | heatstitch | openstitch | Nuizu |
|---|---|---|---|
| Delivers | A peer that makes the same satin/fill/run decision we do, from stated thresholds | The most complete free engine (skeleton classifier, split satin, underlay choice, pull comp, a /100 score) | A fill-everything floor with a one-line CLI |
| Cost | Browser app — drive with Playwright (we have the MCP) or run `npm run dev` locally; ~a day to wire | GUI only — 18 tripwire pairs by hand ≈ 2 h; or read its `analysis` CLI for the scorer | `uvx` loop over the corpus: an afternoon |
| Catch | 4 stars, one author; size handling unknown (DADE's 36.7 mm trap — check before quoting) | **AGPL**: benchmark the DST, do not read the source into ours (same ruling as Ink/Stitch) | Fill-only by design; tells us where fill alone already reads, like DADE did |

All three write DST, so one harness covers them. Their outputs are
third-party stitch files: keep them in a gitignored `scratch_bench/`
(`scratch_*` is already ignored) and never commit one without asking Kent
(CLAUDE.md "This repo is PUBLIC").

### Tier 2 — the industry's auto-digitizer, time-boxed: Kent's machine, Kent's call

| | Hatch 4 trial | Wilcom EmbroideryStudio 2026 trial |
|---|---|---|
| Delivers | What the market's reference auto-digitize does on our art, exportable | Wilcom's top-end Smart Design on the same art |
| Cost | 30 days, **30 exports** — exactly the 18 tripwire pairs + 12 spares; plan the list before installing | 14 days, Windows only, no VM; export limit unstated |
| Catch | One shot per machine; a wasted export is gone. Kent's email, Kent's box | Export in the trial is UNVERIFIED — first export decides whether the fortnight is worth anything |

These two are the only way to measure "a professional tool's automatic
output" rather than a hobbyist's engine or a hand digitizer. They also
re-check the Hatch manual teardown against Hatch's actual behaviour.

### Tier 3 — free web tools, while the free tier lasts

**Stitch AI (Dynamic Mockups)** is the one worth an afternoon: free now, DST,
and its production sheet prints trims and stitch count, so its own claims can
be checked against our instruments. Do the 18 committed tripwire pairs once.
**Stitchist** at $50 one-time is the cheapest unlimited unlock if a second web
engine is wanted. Skip click-stitch (3 colours, 3 in), Embrowser (2 a week),
SewFlow Classic (tatami only), and every pay-per-download site.

### Artwork rule for anything web-hosted

Upload only artwork already public in this repo (the 18 tripwire pairs:
Becker ×5 and the zip's 13 — memory `nightly-tripwire-2026-11-02`). MFab,
ProSeal, Fremont, Drone and the other `scratch_kent/` jobs are Kent's clients'
files; sending them to a third-party server needs his OK per job (DADE got
MFab today — note it, do not repeat it by default).

### Gate reminders

- Gate 4: quote chance-corrected figures (kappa, cc), never raw agreement.
- A render decides orientation and legibility claims (footgun 1), so every
  row in the comparison carries a picture at the stated size.
- Compare at the pro's size (hat 113.5 × 64, LC 96 × 76.5, beanie 94.5 × 56
  — memory `garment-size-like-pro`), not at whatever the tool defaults to.

---

## 3. Ideas worth taking regardless of the benchmark

1. **heatstitch's stated width rule** (run < 1 mm, satin ≤ 7 mm and even, else
   fill) and "narrow regions sew last" — a published-style baseline to put
   next to our stage-3 classifier and `fine_bars_satin`.
2. **openstitch's virtual stitch-out score /100 with Show / Fix buttons** —
   our preflight grades A–C; theirs is numeric and actionable per finding.
3. **Independent re-read of every export before download** (openstitch,
   Needler, embroidery-magic) — we have crossval for DST/PES/EXP; the
   12.1 mm max-stitch and one-block-per-colour checks are cheap additions.
4. **PEmbroider's TSP ordering of stitch segments** — a jump-minimising order
   the patents (11727615) also describe; relevant to the in-piece cuts work.
5. **Directionality-Aware streamline fills** for the photo lane — continuous
   thread, few trims, sewn in the paper.
6. **Tian's skeleton-fork shape decomposition** for satin columns — the
   literature's one principled column split.
7. **MSEmbGAN's 13K Wilcom-made pairs** as weak satin/fill labels — licence
   check first (`hf-hub-check` skill if it is on the Hub).
8. **DADE's user-set DST trim-jump count** — already in the DADE memory.

---

## 4. Sources

Web tools: embroidai.com (/, /pricing, /terms), sewflow.com/pricing,
click-stitch.com/free-embroidery-converter, embrowser.com, stitchist.app,
dynamicmockups.com/stitch/, stichai.pro, stitchai.us, figitize.ai,
stitchfast.co.uk, embify.ai, stitchpilot-frontend.pages.dev/pricing.
Desktop: inkstitch.org, api.github.com/repos/inkstitch/inkstitch,
github.com/Embroidermodder/Embroidermodder/releases, embird.net/free-trial,
brother.com/common/hsm/ped11/ped11trial.html,
support.brother.com/g/s/hf/mobileapp_info/artspira/plan/func2/en.html,
info.ricoma.com/chroma-free-trial, wilcom.com/free-trial,
help.hatchembroidery.com (trial restrictions), embrilliance.com/express,
edutechwiki.unige.ch/en/Stitch_Era, sierra-software.com,
machineembroiderygeek.com (SewArt review, 2021).
Research: github.com/pfedan/heatstitch, github.com/lb2002/openstitch,
github.com/Mokuichi147/Nuizu, github.com/habon-el/needler,
github.com/9valleb9/embroidery-magic, github.com/CreativeInquiry/PEmbroider,
onlinelibrary.wiley.com/doi/10.1111/cgf.14770, doi.org/10.1109/tvcg.2024.3447351,
hyper.ai/en/datasets/34570, researchgate.net/publication/291506839,
arxiv.org/abs/2609.08311.
Unreachable this day (claims from secondary sources, UNVERIFIED): sewart.com,
sophiesew.com, thredworks.com, janome.com (403), mysewnet.com (404),
printful.com/embroidery-digitization (404).
