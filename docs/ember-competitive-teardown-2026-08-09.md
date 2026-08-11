# Ember Competitive Teardown & Handoff — 2026-08-09

Source: full HTTrack mirror of emberdesign.net at `C:\My Web Sites\Ember Design\emberdesign.net` (manual, pricing, fill-pattern docs, convert tool, bridge tool, marketing pages, ~4,300 explore-gallery pages, ~370 user-profile pages). Cross-referenced against current EMB-Bot state (`main` @ `5c2332f`, 2026-08-09). Extends the earlier [hatch-manual-teardown-2026-08-08.md](hatch-manual-teardown-2026-08-08.md) competitor analysis and the standing [research-handoff-2026-08-07.md](research-handoff-2026-08-07.md) roadmap.

Companion prior memory: architecture-level teardown (2 Next.js apps + iframe, PixiJS/MobX/WASM editor, client-side codec) already on file — this doc adds the **feature and business-model layer** that teardown didn't cover.

---

## 1. Executive summary

Ember is a browser-only, freemium ($9.99/mo Pro) embroidery digitizer, live since 2022, with 25k+ users and 40k+ designs created. Its biggest surface-area advantage is **breadth of the fill-pattern/run-type library** (24 named fills, 7 run types, all with rich per-pattern parameters) and a **desktop companion app ("Ember Bridge")** that pushes designs straight to a Wi-Fi machine, bypassing manual export entirely. Its "AI Auto Digitize" is marketed hard but technically undocumented — legal boilerplate is the only place it's confirmed to be ML-backed at all.

EMB-Bot's engine is more rigorously tested and more transparent about its own limits than anything Ember publishes, and already beats Ember on font count (72 vs 25) and on using perceptually-correct (CIEDE2000) thread matching, which no vendor — Ember included — documents doing. But EMB-Bot is pre-revenue, pre-launch, and currently has **two unresolved correctness bugs (DST axis, fill density) that block shipping the default export path**, plus a much thinner fill-pattern and run-type library than what Ember ships today.

Bottom line: the "market-parity-vs-Ember" bar is closer on engine quality than on feature breadth and packaging. The two DST/density bugs are launch-blockers regardless of Ember; the fill-pattern gap and Bridge are the two biggest feature gaps worth a deliberate build/skip decision.

---

## 2. Side-by-side comparison

| Area | Ember | EMB-Bot (today) | Verdict |
|---|---|---|---|
| **Platform** | Browser-only Next.js app, zero install | Svelte 5 web app (Studio) + optional local Python service | Comparable |
| **Auto-digitize (image→stitch)** | "Auto Digitize" one-click, marketed as AI/ML; **zero manual documentation found** for it | Classical CV pipeline (k-means/CIEDE2000, SLIC superpixels, 4-way input classifier); openly documented, openly limited ("flat art in, pro out") | EMB-Bot is more honest; Ember's is more heavily marketed. Neither publishes accuracy benchmarks. |
| **Guided/semi-auto digitize** | "Click-to-Stitch" (Pro) — pick regions, apply fill/run settings | Python service has a full per-shape review UI (recolor, tier override, delete/restore) — functionally similar, just not marketed as a named mode | Comparable capability, Ember has better naming/packaging |
| **Manual digitize** | Full path/node/shape tool + hole cutting, on Free tier | No freehand draw / basic-shapes tool — explicit non-goal in `PRODUCT.md` | **Gap**: EMB-Bot has no manual vector tool at all |
| **Fill patterns** | **24 named patterns** per manual/pricing copy (Tatami, Original, Triangle, Waves, Columns, Hearts, Diamonds, Zig-Zag, Circles, Heartbeat, Spiral, Staircase, Rainfall, Hexweave, Tornado, Streamlines, Circular Fill, etc. — Hearts/Diamonds/Circles each ship 3 size variants, which is likely why this count reads higher than the 13 counted in the 2026-08-08 architecture teardown from the live editor; unreconciled, see §6) | Tatami (default), contour rings (off by default, buggy), gradient blend (photo tier only) — effectively **1 shipped fill pattern** | **Large gap either way** |
| **Run/outline types** | 7 (Single, Triple, Satin, E-Stitch, Double Rope, Triple Rope, Manual) | Satin, tatami, running/bean (small-shape rescue), border/outline (Python-only, not in browser engine), appliqué (off by default) | **Gap**, especially decorative run types (rope, E-stitch) |
| **Gradient fill modifier** | Universal modifier (Ramp/Plateau mode) applicable to any fill pattern, Pro-gated | Only exists as a separate photo-tier blend stage, not a general modifier | Gap |
| **Fonts (built-in)** | 25 | **72**, verified pre-digitized | **EMB-Bot leads** |
| **Custom font upload** | Yes (TTF/OTF/TTC), Pro-gated | No | Gap |
| **Thread color matching** | 15,809 colors / 78 brands, searchable + eyedropper | 68 manufacturer `.gpl` charts, CIEDE2000 perceptual matching | Ember has more brand breadth; EMB-Bot's matching *method* is ahead of documented industry practice |
| **Stitch preview** | Dedicated Stitch Player (scrubber, speed control) + "Realistic View" render toggle | 2.5D canvas preview (`preview.js`), no scrubber/playback | Gap, likely cheap to close |
| **File formats (export)** | PES, DST, EXP, JEF, VP3, HUS, XXX, VIP (10+ total incl. converter-only U01/PEC/TBF/G-code) | DST (buggy), EXP, PES (best-effort), JEF | **Gap** — but EMB-Bot's Python side already runs on `pyembroidery`, which supports VP3/HUS/XXX natively; likely a low-lift expansion (see §4.6) |
| **Standalone format converter** | Free, no-signup, fully client-side browser tool, reuses main engine | None | Gap — but low priority (SEO/funnel play, not core product) |
| **DST correctness** | Unknown (not independently verified in this teardown) but it's their default/primary format at scale (25k+ users) with no public complaints found | **Known-broken**: axis table transposed vs Tajima standard, plus a byte bug that hides color changes from third-party readers. No sew-out done. | **EMB-Bot launch blocker, unrelated to Ember** |
| **Fill density accuracy** | Unknown/not verifiable from marketing site | Credibly running ~2× lighter than professional density (`FILL_ROW_MM = 0.40` vs. ~0.20 mm industry rows); unresolved, no sew-out | **EMB-Bot launch blocker, unrelated to Ember** |
| **Direct-to-machine transfer** | **"Ember Bridge"** — free/open-source desktop app, Wi-Fi auto-discovery, sends straight from the web editor to the machine, works even with non-Ember files, needs an "EmberConnect dongle" for machines without native Wi-Fi | None — export file, transfer manually | **Large gap** — Ember's most distinctive feature, no EMB-Bot equivalent even conceptually |
| **Project persistence** | Cloud auto-save, version history, cross-device | Local `.embproj` file, no cloud, no version history | Gap |
| **Community/social** | Explore gallery (trending/popular, ~4,300+ public designs), public user profiles with view/like/favorite counts | None — explicit non-goal (parked) | Gap, but deliberately deprioritized by Kent already |
| **Pricing model** | Live freemium: Free (5 private/10 published projects, 6 fills, 3 runs, 25 fonts) vs Pro $9.99/mo or $99.50/yr (everything unlocked) | No billing/entitlement system built yet; pricing tiers explicitly "tabled" per `PRODUCT.md` | Gap, but expected at this stage — Ember's tier boundaries are a useful reference (see §4.7) |
| **Test rigor / self-honesty** | Not observable externally | 265+321+402 passing tests across the three engines, independently re-verified live; project explicitly documents its own known defects instead of hiding them (COOKBOOK.md) | **EMB-Bot leads** on engineering discipline, even though feature-complete-ness trails |

---

## 3. Where EMB-Bot is already ahead

1. **Font library depth** — 72 verified pre-digitized fonts vs. Ember's 25 built-in.
2. **Perceptual color matching** — CIEDE2000-based thread snapping is more rigorous than any published vendor method, Ember included (Ember's palette is large but nothing in its docs claims perceptual-distance matching).
3. **Engineering transparency** — EMB-Bot's docs record real defects with severity and repro fixtures (chaining bare-thread jumps, contour bare-core gaps, a classifier that's provably worse than what it replaces). Ember shows no equivalent public rigor; its "AI" claim is backed by nothing more specific than privacy-policy boilerplate. This is a legitimate trust/marketing angle later ("we show our work").
4. **Auto-digitize pipeline transparency** — a documented 4-way classifier and an explicit quality contract ("flat art in, pro out") is a clearer promise to a customer than Ember's undocumented one-click black box.

---

## 4. Opportunities for improvement (prioritized)

### 4.1 Fix the two launch-blocking bugs first — independent of Ember
- **DST axis transposition** (`src/dst.js`) and the `0x43`/`0xC3` color-change byte bug. Every DST the browser engine has ever written is suspect for third-party machines. Schedule the sew-out (`docs/sewout-card-2026-07-31.md`) — this has been sitting unscheduled and is the single highest-risk open item in the whole project.
- **Fill density** (`FILL_ROW_MM = 0.40` in `digitizer_core/machine.py:41`) — four independent vendor sources plus your own arithmetic check say it should be ~0.20mm. Same sew-out should settle both at once.
- Neither of these is an Ember-gap issue — they're correctness bugs that would matter even with zero competitors. They block trusting *any* other comparison in this document, since a broken default export undermines every other strength.

### 4.2 Close the fill-pattern gap — the single biggest feature-count gap
Ember's 24-pattern library (with per-pattern parameters like Tightness/Rotations for Spiral, Chaos/Density for Rainfall, Cell Size for Hexweave) is pure geometry — no ML required, and EMB-Bot's `stage6_fill.py`/`fill.js` architecture already supports pluggable fill algorithms (contour and gradient-blend already exist as stages). This is the most replicable gap on this list. Recommend picking 4-6 decorative fills (waves, columns, circles, diamonds are the easiest chevron/motif-repeat patterns) as a fast-follow rather than trying to match all 24 at once.

### 4.3 Generalize gradient fill as a universal modifier
Ember applies Ramp/Plateau gradient density to *any* fill pattern as a Pro-gated add-on, not just to photo-tier art. EMB-Bot's gradient-blend logic already exists (`stage6_blend.py`) — worth evaluating whether it can be lifted out of the photo-only path and exposed as a general per-shape modifier. Likely smaller lift than building new fill patterns from scratch.

### 4.4 Cheap UX win: stitch playback scrubber
Ember's Stitch Player (scrubber + speed control) is a polish feature EMB-Bot's existing `preview.js` 2.5D canvas is probably close to already — likely a front-end-only addition, no engine changes needed. Good low-risk, high perceived-value item for the Studio wizard.

### 4.5 Decide deliberately on Ember Bridge, don't default to "later"
Direct machine transfer over Wi-Fi is Ember's most distinctive, hardest-to-copy feature (it requires a desktop companion app and, for older machines, a hardware dongle). This is a real engineering investment, not a quick add — flagging it explicitly so it's a conscious roadmap decision rather than something that falls off the list by omission the way the community gallery already has.

### 4.6 Low-lift export format expansion
EMB-Bot's Python `/export` already routes through `pyembroidery`, which natively supports VP3, HUS, XXX, and others Ember lists. Since the hard part (a working, tested `pyembroidery` integration) is already done, adding these formats to the export menu is likely a small, contained task — worth scoping before assuming format breadth is a big gap.

### 4.7 Use Ember's tier boundaries as a reference when billing gets built
When `PRODUCT.md`'s "tabled" pricing/entitlement work starts, Ember's Free/Pro split (fill-pattern count, run-type count, auto-digitize, custom fonts, project limits) is a validated, live reference point for where to draw the line — no need to design tier gating from scratch.

### 4.8 Housekeeping found along the way (low priority, unrelated to Ember)
- `digitizer/README.md` still says the per-shape review UI ("step 10") is "still to come" — it's actually built and wired (`DigitizePanel.svelte`, `digitizer.js`). Stale doc, quick fix.
- `PRODUCT.md` lists "decorative fills" as an explicit non-goal, but `digitizer/` already ships contour and gradient-blend fill tiers. This contradiction was already flagged in `hatch-manual-teardown-2026-08-08.md` §6 as unresolved — still open, still worth a decision from Kent given §4.2 above would deepen exactly the thing that's marked as a non-goal.

---

## 5. Open questions for Kent

1. Fill-pattern library: pick a target count (e.g. "match 8 of Ember's 24") and reconcile against the `PRODUCT.md` "decorative fills = non-goal" line — these two things currently point opposite directions.
2. Is a Bridge-style direct-to-machine feature ever in scope, or permanently out? Worth a yes/no now so it stops being an ambiguous gap.
3. Sew-out scheduling — both launch-blocking bugs (§4.1) depend on the same physical test. What's actually blocking scheduling it?
4. Community/gallery: Ember's growth stats (25k users, 40k designs) suggest the Explore feature is a real acquisition channel, not just a nice-to-have. Worth revisiting as parked vs. permanently cut.

---

## 6. Discrepancy vs. prior teardown

The 2026-08-08 architecture teardown (from the live editor UI) counted **13 fill patterns, 6 free / 7 paid**. This document's manual-derived count is **24**, because Hearts/Diamonds/Circles each list 3 size variants (sm/md/lg) as separate picker entries — 18 base names + 9 extra size variants ≈ 24. Not independently re-verified against the live editor for this pass. Either way the gap vs. EMB-Bot's effectively-1-pattern library is large; use 13 as the conservative planning number, 24 as the upper bound, and re-check against the live editor before committing to a specific match target in §4.2.

## 7. Sources
- Ember mirror: `C:\My Web Sites\Ember Design\emberdesign.net\manual\`, `pricing.html`, `convert.html`, `bridge.html`, `about.html`, `index.html`, `explore.html`, sample `explore\*.html`, sample `user\*.html`, `_next\static\chunks\app\(marketing)\*`
- EMB-Bot: `README.md`, `PRODUCT.md`, `CLAUDE.md`, `COOKBOOK.md`, `BACKUPS.md`, `src/dst.js`, `src/digitize.js`, `digitizer/digitizer_core/machine.py`, `digitizer/digitizer_core/config.py`, `app/src/ui/DigitizePanel.svelte`, `docs/dst-axis-verdict-2026-07-31.md`, `docs/law19-fill-spacing-2026-08-02.md`, `docs/research-handoff-2026-08-07.md`, `docs/hardening-closeout-2026-08-02.md`, `docs/hatch-manual-teardown-2026-08-08.md`
