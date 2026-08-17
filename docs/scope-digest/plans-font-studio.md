# Scope digest — early plans, guided studio, font library/editing

Sources: `docs/superpowers/specs|plans/2026-07-22-*`, `2026-07-24-*`, `2026-07-27-*`.

## The original intent

- `2026-07-22-pro-stitch-roadmap.md` = the project's first roadmap: four phases in a fixed order (trims+sequencing → fabric presets/pull comp/underlay → stitch direction+sheen → sequencing polish), all four recorded **DONE** in its own Build status.
- Its stated craft principle — "the tool encodes known digitizing rules as presets; Kent's on-machine sew-outs are the feedback loop; when a preset proves wrong we adjust the preset, not the file" — **never happened**: no sew-out has ever occurred (`MASTER_SCOPE.md` § No physical sew-out).
- Explicitly decided against, then and there: per-stroke satin lettering (skeletonization), SVG import, stitch simulation with fabric physics (`pro-stitch-roadmap § Out of scope`).
- Left as unscheduled "horizon" and never shipped: **directional pull comp** (Phase 2 specified pull comp perpendicular to the stitch axis; shipped as uniform outward-normal offset, documented as a deviation), **±30° adjacent-same-color angle contrast** (needs adjacency detection), SVG import (`pro-stitch-roadmap § Build status`, Phase 2.2, Phase 3.2).
- `2026-07-22-emb-bot-design.md` intended one self-contained local `EMB-Bot.html`, CDN opentype.js + jsPDF, ~100 curated Google Fonts fetched as TTF from a jsDelivr mirror, lettering as **fill + outline, no satin in v1**. All of that is gone: satin fonts replaced the TTF path (auto-tracing rejected 2026-07-24), and `EMB-Bot.html`, `EMB-Bot-standalone.html` and `tools/bundle.mjs` are absent from the repo.
- Silent substitution: the design specifies marching-squares region extraction (§3.3); the plan implemented flood-fill + Moore-neighbor tracing, outer boundary only (`2026-07-22-emb-bot.md` Task 5).
- `2026-07-24-guided-studio-design.md` set three differentiators (digitizing quality, font library+quality, realistic 2.5D preview) and an explicitly **validate-first MVP**: no accounts, billing or backend, tested by "a handful of real users" against a "would-pay signal" (§1, §Positioning). The tester-validation gate was **dropped silently** — scope moved to a market-parity launch benchmarked against Ember (`PRODUCT.md`) with no recorded validation round.
- Its slice order (1 text studio → 2 photo/logo digitize → 3 grow fonts → 4 onboarding polish) was **decided against** on 2026-07-27: fonts jumped to first, photo digitizing tabled (`2026-07-27-font-library-expansion-design.md § 0`).
- Also never happened from that spec: font count "toward/beyond Ember's 25" as a *later* slice, full rotatable 3D preview, accounts/cloud/sharing/paid tier/batch roster names, and the "revisit naming/branding before any public test" open question (§5, §8, §10).

## Design decisions that still govern

- **One internal stitch model is the source of truth for every exporter** — absolute integer 0.1 mm DST units, origin at design center, +X right, +Y up; exporters flip Y as their format needs (`emb-bot-design § 3.1`, `2026-07-22-emb-bot.md § Global Constraints`). Reason: independent encoders must never re-derive geometry.
- **DST is primary and most reliable; PES is best-effort and labeled "verify on your machine"** (`emb-bot-design § 2, § 4`). Rationale: PEC block complexity.
- **Dual-mode IIFE engine modules, classic `<script>`, zero build step, zero dependencies** so the same file runs under `node --test` and in the browser (`2026-07-22-emb-bot.md § Global Constraints`; restated in `2026-07-27-font-binary-stage-a.md`).
- **Engine is the untouched source of truth; app code lives only under `app/`; the app never re-derives stitches** (`2026-07-24-guided-text-studio.md § Global Constraints`). This is why the Studio/engine seam still exists.
- **Preview and export consume the same stitch list** — "what you see is what you sew" (`guided-studio-design § 4 Data flow`).
- **Flatten is user-visible and authoritative**: Generate consumes the current flattened indices, not a re-quantization, and `absorbSmallRegions` reassigns small patches rather than dropping them so coverage stays solid (`2026-07-22-color-flatten-design.md § Feature`). Rationale: color merge is the judgment call a human digitizer makes.
- **Trim policy**: trim before any travel longer than `trimAtMm` and before every color change; short hops stay jumps because excess trims slow the machine (`pro-stitch-roadmap § Phase 1`).
- **Garment auto-picks fabric with an override dropdown; auto angles with per-color override** (`pro-stitch-roadmap` header).
- **Every new element field defaults to today's behavior when absent, so no saved-project migration is needed** (`2026-07-27-font-editing-abilities.md § Global Constraints`; back-compat rationale in `font-editing-abilities-design § 2.2`).
- **Risk taxonomy for text features**: pure post-transforms on finished stitches (rotation) carry zero quality risk; anything that reshapes column geometry (bold, slant) is rated, bounded and guarded (`font-editing-abilities-design § 1, § 2`).
- **Presets, not a continuous slider, for bold** — presets keep users inside a range verified to stitch cleanly; slant bounded to ±20° so rungs still meet rails at junctions (`font-editing-abilities-design § 2.3, § 2.4`).
- **Reuse the existing `pullCompMm` rail-offset mechanism for weight instead of new geometry** (`font-editing-abilities.md § Task 3`).
- **Character indices are `text.slice(startIdx,endIdx)` / native textarea `selectionStart|End` semantics** (`font-editing-abilities-design § 2.2`; `charIdx` tagging in `layoutText`). Reason: no custom index math anywhere in the UI.
- **Verified-tier-only ships; tiers live in the manifest as data, not code** — a mis-tiered font is a one-field fix, and unverified is an internal work queue, not a reject pile (`font-library-expansion-design § 2, § 3.7, § 10.6`).
- **Binary `.embf` font format** (quantize ×4, per-ring delta, Int16, HTTP brotli/gzip), measured 24.5× smaller than JSON at 0.02–0.03 mm error — below machine placement resolution (`font-library-expansion-design § 4.1a`).
- **Manifest is the single source of truth for font metadata**; license/attribution are extracted by the importer and never hand-maintained; the credits screen is generated from it (`font-library-expansion-design § 4.1, § 7`; `2026-07-27-font-browser-stage-b.md § Task 5`).
- **Lazy per-font fetch with a lazy `EMB.SATIN_FONTS` accessor** so existing synchronous call sites keep working (`font-library-expansion-design § 4.1`).
- **The browsing grid never fetches font binaries** — pre-rendered PNGs carry it; only selection (and the selected font's live preview) fetches (`font-browser-stage-b.md § Architecture`).
- **QC checks each encode a failure this project already hit**, satin counted per *glyph* not per file, and aesthetic rejection stays a human call (`font-library-expansion-design § 5`; `font-browser-stage-b.md § Task 1`).
- **Font stitch-out validation is Kent's loop; the harness owns everything machine-checkable short of thread** (`font-library-expansion-design § 0`).

## Deferred and cut work

- **SVG import PARKED at Task 1** on `feat/svg-import-shapes`, taking the `shape` element type, the shape grid and the v2→v3 model migration with it (`font-library-expansion-design § 0, § 4.3, § 9`). Closed as never-resumed: `MASTER_SCOPE.md` standing ruling "`feat/svg-import-shapes` is not resumed" — shapes later shipped by a different route (`PRODUCT.md` item 4).
- **The `ltr/` directory importer extension (5 fonts incl. `mai_en_fleur`)** — named as the cheapest promotion available and "first candidate AFTER this slice" (`font-library-expansion-design § 9`). **Closed**: `PRODUCT.md` marks it done, `mai_en_fleur` ships.
- **DST design import** — roadmap item 2, seam named as "decode logic already exists in `tools/render-dst.mjs`, needs porting into the engine" (`font-library-expansion-design § 0, § 9`). **Partly closed**: `src/dstimport.js` exists; the curated starter pack that depends on it is still not started (`PRODUCT.md` item 3).
- **Retiring `EMB-Bot.html` deferred pending a feature audit** — it may still expose per-swatch stitch-angle override and the explicit fabric dropdown that Studio lacks (`font-library-expansion-design § 3`; `font-binary-stage-a.md § Global Constraints` keeps it untouched). **Closed by deletion, not by audit** — the file is gone and no audit result is recorded.
- **Round 2 font editing: condensed/expanded width and mixed per-letter size**, deferred with a prototype-first requirement (real stitch-out renders reviewed before any ship commitment) because both distort satin column width unevenly along a curve and could interact with the resize-density fix (`font-editing-abilities-design § 3`). Still open — no such fields exist in `app/src/lib/project.js`.
- **69 unverified fonts as a queue with named promotion paths**: 44 fill-artwork (needs SVG import), 10 multi-color/applique/tartan (needs per-glyph multi-color engine work), 9 non-Latin (RTL/layout proving), 6 missing digits + 6 missing uppercase (per-font call), 6 advance ≤ 0 (importer metrics repair), 5 `ltr/` layout, 5 unidentified (`font-library-expansion-design § 2`).
- Also out of scope there: monogram sets, texture variants, pictogram/shape packs, stroke→satin conversion, outline-font (.otf/.ttf) import (§ 9).
- **`opts.minimizeColorChanges`** shipped default-off, engine-only, no UI — a no-op under flatten, kept for future repeated-color inputs i.e. SVG import (`pro-stitch-roadmap § Phase 4c`).
- **Lowercase-"e"/tight-curl satin fan**: known open item with the fix already named — density-adaptive correspondence, resampling rung-sections by length instead of a fixed count, in `satinplay` (`guided-studio-design § 6`; `guided-text-studio.md § Notes`).
- Flatten deferrals: per-pixel painting/eyedropper, real thread brand codes (`color-flatten-design § Out of scope`) — brand palettes later shipped anyway (`PRODUCT.md` item 5).
- MVP non-goals kept as deferrals: custom user font upload, complex-photo/portrait promises, marketplace, cloud sync (`guided-studio-design § 9`).

## Rejected alternatives

- **Auto-tracing outline fonts** — rejected on quality 2026-07-24 (fragmented curves and junctions, worse than commercial tools). This is the entire reason hand-authored pre-digitized satin fonts exist (`font-editing-abilities-design § 1`; `font-library-expansion-design § 3.2, § 9`).
- **A restricted "local-only" font tier** — skipped: its only plausible content was free-for-personal-use *outline* fonts, which need the rejected auto-tracing (`font-library-expansion-design § 3.2`).
- **Badging unverified fonts, or a toggle to enable them** — rejected in favor of not shipping them at all, so a user can never pick a font that might fail (`§ 2`).
- **A longer dropdown** — rejected for a full font browser (`§ 3.6`); then Stage A's own fetch-all thumbnail dropdown was killed as a ~30 MB fetch storm (`font-browser-stage-b.md § Goal, § Task 4`).
- **On-demand live thumbnails for ~150 fonts** — will not perform; previews are pre-rendered at import time (`§ 4.2`).
- **The eager combined `satin-fonts.js` registry** — dead at scale (7.7 MB for 21 fonts; the 70-font trial import produced 62 MB of JSON) (`§ 4.1`).
- **`EMB-Bot-standalone.html`** — retired: ~145 inlined fonts would be tens of MB in a local file where gzip does not apply; the standing "rebuild the standalone after any `src/` change" rule retires with it (`§ 3.3`).
- **A continuous bold slider** — rejected for three tuned presets (`font-editing-abilities-design § 2.3`).
- **React+Vite (heavier than needed) and vanilla+Vite (too much hand-written state)** — rejected for Svelte+Vite (`guided-studio-design § 4`).
- **A full canvas/node/layer editor for the MVP** — rejected for a guided generator (`guided-studio-design § 2`). Later reversed: manual draw and node editing shipped (`PRODUCT.md`, `MASTER_SCOPE.md` area 5).
- **Perpendicular-to-stitch-axis pull comp** — replaced by a uniform outward-normal offset (`pro-stitch-roadmap § Build status` Phase 2).
- **Estimating the font library from directory names** — overcounted 2.5× (~125 estimated vs 50 measured); remote probes produced a false "missing font.json" finding, so the local clone is ground truth and "any surviving estimate" is to be treated with suspicion (`font-library-expansion-design § 0, § 2`).

## Sequence claims

- Trims+sequencing **first**, ahead of everything else, because jump-only travel drags thread across the design — a stitchability defect, not a polish item (`pro-stitch-roadmap § Phase 1`).
- Fabric presets must precede pull comp and underlay selection, which are derived from them (`§ Phase 2`).
- **Roadmap reset 2026-07-27** (third and final reorder): fonts first → DST import of found designs → auto-digitizing tabled → market later; SVG import parked because the reset removed its justification (`font-library-expansion-design § 0, § 3.4`).
- **Fonts and vector import are independent** — nothing in the font slice depends on SVG-import code (`§ 3.4`).
- **Stage A before Stage B**, deliberately: the risky change (removing the eager registry every call site depends on) is verified against *unchanged* UI, so any regression is unambiguously the delivery change and not the new picker (`§ 3a`).
- **The decoder guard must be green before the JSON font path is removed** — `decode(encode(font))` deep-equals `quantizeFont(font)` for all 21 shipped fonts, plus a separate rendered-diff proving quantization is visually invisible (`§ 4.1a`; `font-binary-stage-a.md § Global Constraints`).
- **QC gates shipping**: a font that cannot render a sample is demoted to unverified rather than shipped (`font-binary-stage-a.md § Task 5`).
- **Bold constants must be tuned against the library's tightest letterforms — not the roomiest — before shipping** (`font-editing-abilities-design § 2.3`; `font-editing-abilities.md § Task 3 Step 5`).
- Slant already existed in the older auto-satin image path (`satin.js`) and had to be *extended* to the pre-digitized font path, where it did not reach (`font-editing-abilities-design § 2.4`).
- Studio Slice 1 required the engine to stay unchanged; any needed engine change was to stop and be raised (`guided-text-studio.md § Notes`).
- Licensing deliverables (manifest fields, credits screen, public derived-data route) are **in-slice scope, not follow-up paperwork** (`font-library-expansion-design § 7`).

## Contradictions

- **The sew-out feedback loop these docs are built on has never run.** The roadmap's craft principle, the fabric presets, and the font size bands all assume Kent's on-machine loop; `MASTER_SCOPE.md` states zero sew-out testing has occurred anywhere and calls it the project's biggest confidence ceiling. Every preset and band number here is unvalidated.
- **Validate-first MVP vs market-parity launch.** `guided-studio-design § 1` demands beginner/would-pay validation with real testers before growing the product; `PRODUCT.md` describes a launch scope benchmarked against Ember with billing merely "tabled". No validation round is recorded anywhere.
- **License policy.** `font-library-expansion-design § 3.2` sets OFL + CC-BY + **CC-BY-SA** with a public derived-data route, and Stage B builds the credits `.embf` links to satisfy ShareAlike. `PRODUCT.md` / `MASTER_SCOPE.md`: all 13 ShareAlike fonts were pulled 2026-08-04 — zero ship — so that mechanism now serves a policy that no longer applies.
- **Font count and ambition.** The font slice treats "hundreds of fonts" as the point and targets 71 verified; 55 ship, and `PRODUCT.md` rules "~70 fonts is enough — launch does not wait on font expansion".
- **The whole `emb-bot-design` deliverable is superseded.** One self-contained local HTML file with a JS quantize/trace/fill pipeline is now a frozen browser engine retired in favour of the Python digitizer (`MASTER_SCOPE.md` area 1), and browser DST is flagged internal-only over an axis bug the design never anticipated.
- **Auto-digitizing.** `font-library-expansion-design § 0.3` tables it as "not the product"; `PRODUCT.md` records it un-tabled the same day the launch scope was set, and most engineering effort since has gone into it.
- **Manual editing.** `emb-bot-design § 11` puts manual stitch/node editing out of scope; node-level canvas editing has since shipped (`MASTER_SCOPE.md` area 5), while `PRODUCT.md` non-goals now draw the narrower line "stitch-level editing".
- **`EMB-Bot.html` retirement** was explicitly gated on a feature audit for controls Studio lacked; the file is simply gone, so the parity question (per-swatch angle override, fabric dropdown) is unanswered rather than resolved.
- **Size-band guidance ships unvalidated.** `§ 6` says the 0.75×–2.0× multipliers "are a starting point, not measured values, and should be validated against real stitch-outs before being treated as authoritative" — they are surfaced to users today and no stitch-out has happened.
