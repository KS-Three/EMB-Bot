# Lettering mastery — the type engine roadmap

Continues the numbered laws. 1–14 were geometry and pipeline; 15–38 were thread, needle, fabric and shop floor; 39–44 were the fill family. **45–58 are what embroidered type demands.**

Source tags: **[P]** primary (vendor doc, shipping source, spec) · **[T]** named trade expert · **[B]** blog-corroborated · **[D]** our own derivation or measurement · **[U]** unverified.
Status tags: **Desk-safe** (ship on published values) · **Corpus-gated** (needs a census of our own font corpus first) · **Sew-out-gated** (needs thread on fabric before the constant is real).

Scope is the satin-font path: `src/satinfont.js` (`layoutText`, `routeGlyph`), `src/satinplay.js` (`emitZigzag`, `centerRun`), `src/digitize.js` (`buildLetteringDesign`), `src/garments.js`, and the element schema in `app/src/lib/project.js`. The TTF-outline path (`src/fonts.js`, ~137 Google Fonts via opentype.js, reachable only from the legacy standalone `src/app.js:502-510`) is out of scope except where noted.

---

## Corrections before the laws

Four things the brief and the survey got wrong, all verified against shipped code.

1. **Mirror is not implemented.** No mirror field exists in `defaultTextElement` (`app/src/lib/project.js:6`). The only `mirror` hits in the tree are unrelated comments.
2. **The two-line circular badge is not a primitive.** `badge`/`circle` in `src/satinfont.js` appear only in comments describing the arc math. A badge is composable from two text elements with opposite `arcDeg`, but nothing owns it.
3. **Authored advances and kerning pair tables already exist** — the standing recommendation to "add" them is already done. Every glyph carries `{adv, cols:[{railA,railB,rungs}], runs}`, and the JSON fonts ship real pair tables: `apex_simple_AGS` 97,090 pairs, `amitaclo` 43,090, `mam_script` 39,856, `barstitch_regular` 33,116. Five of 22 ship **zero** pairs (`chicken_scratch`, `digory_doodles_bean`, `emilio_20`, `emilio_20_bold`, `medium_font`) — that is the actual gap, not the mechanism.
4. **Lettering has no underlay at all.** `layoutText` computes `doUnderlay` (`satinfont.js:245`) and passes it into `routeGlyph` (`:339`), which never reads it. The runs tagged `kind:"underlay"` (`:206`) are duplicated-Euler *travel paths* under the satin, not underlay. `satinplay.centerRun` (`:269`) has zero callers anywhere in the tree. The `underlay: true` field on every text element is inert, and the UI advertises a switch that does nothing.

---

# 1. The laws of embroidered type

### The measurement problem (45–46)

**Law 45 — A font's usable size range is set by its narrowest satin column, not by legibility.** [P] Ink/Stitch · Desk-safe.
The authoring procedure is published: measure the narrowest and widest stitch element across the **whole glyph set**, then set `min_scale`/`max_scale` so scaling never drives the narrowest under the satin floor or the widest over the ceiling. The shipped band table shows the law directly — monoline sans get 4–11× bands with 3.5–6.7 mm floors (Bathaus FI 4.5–45.0, Apex 6.72–75.4); modulated serifs get ~1.9× bands with 12.8–17.6 mm floors (DejaVu Serif 12.8–24.0, AGS Garamond 17.6–33.0); formal script gets a **1.5× band and a 30.6 mm floor** (Chopin Script 30.64–45.96). Script is not "hard to read small" — its hairline connectors set the floor for the whole alphabet.
*Us:* we ship no band. `sizeBand()` (`app/src/lib/fontFilter.js:14`) returns `0.75×–2.0×` of the authored `sizeMm`, is display-only in the font browser, and its own comment concedes the multipliers are a guess.

**Law 46 — Cap height is the contract; we measure the em, and the UI measures neither.** [D] measured · Desk-safe.
Every published rule — underlay ladder, small-text floor, monogram sizing, placement charts — is keyed to **upper-case height**. Our `emMm` converts font units by `u2px = (emMm / unitsPerEm) * pxPerMm` (`satinfont.js:253`), so it is em height. Measured cap/em across the 22 JSON fonts: **0.58 to 0.98** (`chicken_scratch` 0.58, `geneva_simple` 0.60, `medium_font` 0.63, `barstitch_*` 0.70, `mam_script` 0.82, `monicha` 0.97, `emilio_20_bold` 0.98; `digory_doodles_bean` is a 1.50 outlier whose `unitsPerEm=47` is smaller than its own cap). "18 mm" therefore delivers a 10.4 mm cap in one font and 17.6 mm in another.
Worse: the UI never asks for height at all. `element.sizeMm` is passed as `targetWidthMm` (`app/src/lib/generate.js:82`), so the user specifies a **design width** and cap height falls out of the fit. **There is currently no way to ask EMB-Bot for 6 mm letters.**
The lowercase trap compounds it: recommended heights are cap heights but lowercase runs ~70% of cap [P] Wilcom. Measured x/cap in our corpus: 0.44–0.81, median ~0.73 — the rule holds on average, and the script/serif tail is worse than the rule (`monicha` 0.52, `pacificlo` 0.54, `auberge_marif` 0.58, `mam_script` 0.63).

### The physical envelope (47–49)

**Law 47 — Satin is valid on [1.5 mm, 7 mm], and 7 mm is a split trigger, not a wall.** [P] Ink/Stitch, Wilcom, Melco · Desk-safe.
Floor 1.5 mm column width ("the value should be larger than 1.5 mm"); absolute minimum satin *stitch* 1.0 mm = 10 points, against a needle 0.7–0.8 mm across. Ceiling: brittleness onset >7 mm, Wilcom's auto-split length 7.00 mm "to preserve the satin effect", vendor-ideal max ~10–12 mm, "beyond 12 mm many machines are unable to handle it". Above 7 the answer is split satin with **randomized** split points (or tatami), not refusal.
*Us:* `emitZigzag` has no width logic whatsoever. Its only guard is `if (Math.hypot(pA-pB) < 0.3) continue` (`satinplay.js:211`) — 0.3 **pixels**, which at the lettering default `pxPerMm=8` is **0.0375 mm**. There is effectively no floor and no ceiling.

**Law 48 — The floor is consumables, not geometry. "4 mm" is a needle/thread boundary.** [T] Jagger; [P] Wilcom, Hatch, Melco · Desk-safe.
The traceable origin of the "4 mm rule" is trainer material: below 4 mm cap you must run a 65/9 ballpoint and 60wt thread; at or above, 70/10 and regular weight. It is not a minimum legible height. The vendor numbers near it govern different things: **5 mm** = underlay on/off and the bottom of Wilcom's lettering range; **6 mm** = Hatch's "small font" class; **1.0 mm** = Melco's minimum satin stitch; **1.5 mm** = minimum satin column. Ink/Stitch's Glacial Tiny reaches a 2.8 mm cap only because it declares size-8 needles and 60wt thread.
*Engine posture:* below 4 mm cap, state the consumables requirement. Do not silently allow, do not refuse.

**Law 49 — Density does not scale with the glyph.** [P] Wilcom, Ink/Stitch · Sew-out-gated for the exact slope.
Spacing is an absolute mm value; scale a column down and penetrations per unit area rise. Small text needs *less* density, and the vendor rationale is fabric damage, not aesthetics: "in very narrow columns, stitch density may be too high and needle penetrations damage the fabric." Wilcom ships Auto Spacing **on by default** for satin — the vendor conceding correct spacing is a function of column width.
*Us:* we do the constant-mm thing correctly and the width-aware thing not at all. `buildLetteringDesign` divides by the fit scale (`spacingMm: densityMm / sc`, `digitize.js:589`) so final spacing lands at the requested 0.40 mm regardless of fit — right for scale-invariance, blind to column width. Anchor values to build from: Ink/Stitch `zigzag_spacing_mm` 0.40 per cycle; Madeira Classic 40 → 0.40 mm / 51 st per cm; Classic 60 → 0.35 mm.

### Underlay and the small-text regime (50–51)

**Law 50 — Underlay is a ladder keyed to cap height and column width, not a boolean.** [P] Wilcom, Ink/Stitch, Embrilliance · Desk-safe.

| Cap height | Underlay |
|---|---|
| under 5 mm | none — "Lettering with heights under 5 mm should not have underlay" |
| 6–10 mm | center run |
| over 10 mm | edge run (contour), inset 0.4 mm per side |
| extra-large (jacket backs) | second layer; double zigzag for loft |

Cross-cut by column width: center run stabilises 2–3 mm columns; zigzag/double-zigzag supports wide columns and belongs under satin cover stitching above ~4 mm. Ink/Stitch shipping defaults are the usable public numbers: center-walk 2 repeats at 3 mm stitch length, 50% position; contour 3 mm length, 0.4 mm inset each side; zigzag 3 mm spacing. Embrilliance derives the 0.4 mm inset from physics — "perhaps a half-needle width or slightly more." Most lettering is ≤15 mm with columns under 3 mm, so **center run is the common case and edge run is the exception.**
*Us:* see Correction 4. Zero underlay in lettering.

**Law 51 — A global minimum-stitch-length filter eats small satin.** [P] Ink/Stitch · Desk-safe.
"Stitches smaller than this value will be dropped… It also affects Satin stitches and therefore lettering fonts. You do not want that on small fonts." Raising the minimum from 0–0.5 mm to 1 mm visibly destroys tiny glyphs. This is the most likely cause of "looked fine in preview, shredded on the machine" at the bottom of a band. Ship the filter, default it **≤0.5 mm**, and never apply a 1 mm floor globally.

### Curves, corners, weight (52–54)

**Law 52 — On a bent letter, spacing must be measured somewhere other than the outer edge — but our arc does not bend letters.** [P] Wilcom for the mechanism; [D] for the correction · Desk-safe.
Wilcom: "Standard stitch spacing is calculated at the outside edge of a shape. With sharp curves, spacing which provides adequate coverage on the outside edge may cause bunching along the inside edge." The fix is fractional spacing — reference the spacing at a fraction of column width, 0.00 = outside, 1.00 = inside; published working values **0.33** to cut stitch count, **0.66** to eliminate bunching.
*Correction to the standing brief:* EMB-Bot's arc is a **rigid per-glyph rotation** of finished stitch points about the glyph's ink center (`satinfont.js:371-374`). Glyph interiors are never bent, so intra-glyph inner/outer bunching **does not occur today**. What does occur on tight radii is inter-glyph: rigid glyphs on a circle open a wedge gap at the outer edge and collide at the inner edge. The correct fix for that is **radius-aware letter spacing evaluated at the ink baseline radius**, not fractional spacing. Fractional spacing becomes mandatory the moment we ship envelopes or a digitized-path baseline, because those do bend interiors.

**Law 53 — Short-stitch handling must be gated off below a column width.** [P] Wilcom, Ink/Stitch, Melco · Desk-safe.
Ink/Stitch ships `short_stitch_distance_mm` 0.25 and `short_stitch_inset` 15% of column width. Wilcom's equivalent: trigger when spacing falls below a % of nominal, **at most 5 consecutive** short stitches, per-row length as a % of the original ("80% means shortened *to* 80%, not *by* 80%"), jagged alternation, and a Randomize option to kill the ridge the inset points otherwise form. Melco documents the trap: the same feature "can inadvertently generate excessively small stitches in detailed areas like narrow lettering." Newer software disables it below a threshold. So must we.

**Law 54 — Bold is a column-width term; pull compensation is a fabric term. Ours are the same number.** [P] Wilcom · Desk-safe.
Wilcom ships Column Width as a control distinct from Pull Compensation, explicitly for "creating bold lettering effects," and keeps pull comp as a pure fabric term. Wilcom's published pull-comp defaults: drills/cotton 0.20 mm, T-shirt 0.35, fleece 0.40, **lettering 0.2–0.3**.
*Us:* `WEIGHT_OFFSET_MM = { thin: -0.15, normal: 0, bold: +0.3 }` is added straight onto `pullCompMm` (`digitize.js:555-557`). Three consequences: bold at 0.5 mm total leaves Wilcom's lettering band; bold silently changes the fabric compensation; and widening at constant spacing reads *thin* — a 1.5 mm column widened to 2.0 mm at 0.40 mm spacing has ~25% fewer penetrations per unit area. Widening must trigger a spacing recompute. Reusing the existing mechanism was the right call to ship; keeping the two terms fused is the defect.

### Script, sequence, and honesty (55–58)

**Law 55 — Script joins are a metric, not a generated connector.** [P] Wilcom, Ink/Stitch · Desk-safe.
The authoring rule set: the tail of each letter coincides with the initial stroke of the next; a guideline is dragged to the **inside edge** of the stroke at the join and both reference points sit on it, so advance width is the distance between join lines, not the ink bbox; the join edge is approximately **perpendicular to the slope**; default letter spacing is **0%** (vs ~10% block) because any positive spacing opens the joins; and no manual overlap is authored on narrow strokes "as pull compensation will provide sufficient overlap." Italic extents are cloned from a single slope guide so reference points stay on the slant axis.
*Us:* our advances are inherited from the Ink/Stitch corpus so the metric is present. What is missing is a per-font `joined` flag that forces `letterSpacingMm` to 0, blocks tracking, and keeps pull comp inside the 0.2–0.3 band so the seam-sealing still works at bold.

**Law 56 — Auto-routing is the enemy of a joined font.** [P] Ink/Stitch · Corpus-gated.
Ink/Stitch's connected scripts ship `"auto_satin": false` precisely so the router will not re-order or re-enter glyph elements; the authored sequence *is* the answer. Our `routeGlyph` runs Chinese-Postman **within** a glyph, which is safe across joins, but its start node is `odd[0]` — the first odd-degree node in node-creation order — falling back to leftmost (`satinfont.js:176`). For a script glyph that is effectively arbitrary and may be the exit tail. **18 of our 69 fonts are Script.** Needs a per-font `autoRoute:false` plus an authored entry pin, or at minimum a pin at the glyph's join node.

**Law 57 — Spacing is a fraction of height, and short strings need more of it.** [P] Wilcom, Hatch · Desk-safe.
Letter spacing is "calculated automatically as a percentage of letter height" — ~10% for block, **0% for script**. Word spacing is a ratio of height, not mm (Wilcom Web API). And the embroidery-specific one with no type-world analogue: **Auto Letter Spacing keyed to character count**, a 2-to-6+ matrix over 0.10–100.00 mm, because a 3-letter monogram reads cramped at the spacing that suits a long word; multi-line uses the longest line.
*Us:* `letterSpacingMm` is absolute mm converted to units by `* unitsPerEm / emMm` (`satinfont.js:254`), so tracking does not scale with size. There is no word spacing, and no line spacing — leading is fixed at `font.leading` (`:255`).

**Law 58 — A fit that silently leaves the band is worse than a refusal.** [D] · Desk-safe.
The fit should clamp to the font's size band and **report which constraint bound**: band floor, band ceiling, garment box, or machine sew field — so the caller can suggest a different font instead of stitching out of band.
*Us:* `buildLetteringDesign` takes `min(garment fit, hoop)` (`digitize.js:564-589`) and reports nothing but final dimensions. `garments.exceedsHoop` is a flat **200×200 mm for every placement** (`garments.js:41-44`), including `hat_front`, where the real Brother cap frame is **130×60 mm**. A 140 mm cap arch passes our check and fails on the machine.

---

## 1b. What our own corpus actually says

69 fonts in `src/fonts/bin/*.embf` (manifest v1). Groups: **Display 18, Script 18, Small 14, Serif 10, Sans 9**. Authored `sizeMm` spans 5.08–137, median 26. 22 also present as JSON.

Bands derived from rail geometry on the 22 JSON fonts, following Law 45's procedure. Method: per satin column take the **median** rail-to-rail distance, then take the 5th and 95th percentile of those medians across A–Z a–z 0–9, expressed as a fraction of the font's own cap height. `minCap = 1.5 / w5`, `maxCap = 7.0 / w95`.

| Font | Group | w/cap p5 | p50 | p95 | minCap mm | maxCap mm | Band |
|---|---|---|---|---|---|---|---|
| milli_marif_bold | Display | 0.208 | 0.214 | 0.270 | 7.2 | 26 | 3.6× |
| barstitch_bold | Sans | 0.167 | 0.200 | 0.316 | 9.0 | 22 | 2.5× |
| tt_masters | Display | 0.170 | 0.294 | 0.489 | 8.8 | 14 | 1.6× |
| geneva_simple | Sans | 0.153 | 0.162 | 0.317 | 9.8 | 22 | 2.3× |
| medium_font | Small | 0.114 | 0.137 | 0.257 | 13.1 | 27 | 2.1× |
| aventurina | Script | 0.103 | 0.196 | 0.389 | 14.6 | 18 | 1.2× |
| pacificlo | Script | 0.103 | 0.156 | 0.258 | 14.6 | 27 | 1.9× |
| excalibur_KOR | Script | 0.093 | 0.197 | 0.342 | 16.2 | 20 | 1.3× |
| barstitch_regular | Sans | 0.088 | 0.111 | 0.264 | 17.1 | 27 | 1.6× |
| auberge_marif | Serif | 0.077 | 0.104 | 0.190 | 19.4 | 37 | 1.9× |
| roman_ags | Serif | 0.077 | 0.111 | 0.229 | 19.6 | 31 | 1.6× |
| mam_script | Script | 0.059 | 0.130 | 0.210 | 25.6 | 33 | 1.3× |
| apex_simple_AGS | Sans | 0.048 | 0.088 | 0.168 | 31.0 | 42 | 1.3× |
| **manga_impact** | Display | 0.080 | 0.262 | 0.401 | 18.8 | **17** | **inverted** |
| **monicha** | Script | 0.056 | 0.126 | 0.297 | 26.9 | **24** | **inverted** |
| **violin_serif** | Serif | 0.033 | 0.055 | 0.212 | 45.2 | **33** | **inverted** |

Four things this tells us, all [D], all Sew-out-gated before the constants ship:

1. **The published style pattern reproduces in our corpus.** Bold monoline faces get 2.5–3.6× bands with 7–9 mm floors; serifs and scripts collapse toward 1.2–1.9× with 15–26 mm floors. `violin_serif`'s p5/p50 of 0.033/0.055 is a genuinely hairline face.
2. **Three fonts invert** — no single size satisfies both bounds. That is not a broken font, it is Law 47 asking for split satin: relax the ceiling to the 12 mm machine wall with auto-split above 7 mm and all three become feasible.
3. **Method sensitivity is the real risk.** Taking the absolute narrowest rail-to-rail instead of the per-column median produces floors of 30–109 mm, because authored columns taper to zero at terminals and serif tips by design. The p2/p5/median choice swings the floor ~4×. Any band we ship must be validated by a sew-out card before it becomes a hard clamp — warn first, clamp later.
4. **The existing guess is right by accident and wrong by accident.** `sizeBand()` advertises 8–20 mm for `geneva_simple` against a geometric 9.8–22 — close. It advertises 21–56 mm for `violin_serif`, a font that cannot satisfy both bounds at any size.

---

# 2. Capability gap table

Every commercial lettering feature against EMB-Bot as shipped, ranked by **customer-visible value to a small embroidery shop** — a shop that sells left-chest logos, caps, towel monograms and name drops. Effort: **S** ≤1 day · **M** 2–4 days · **L** 1–2 weeks · **XL** >2 weeks.

Legend: ✅ full · ◐ partial · ❌ absent

| # | Capability | Wilcom | Hatch | Embird | PE-D 11 | **Us** | Value | Effort | Note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Lettering underlay (any)** | ✅ 4 types | ✅ | ✅ 3 types | ◐ | ❌ | ★★★ | M | Flag is wired and inert (Corr. 4). Biggest single quality delta. |
| 2 | **Ask for a letter height** | ✅ | ✅ | ✅ | ✅ | ❌ | ★★★ | S | `sizeMm` is design width. Blocks every published rule (Law 46). |
| 3 | **Per-font size band, enforced** | ✅ | ✅ | ◐ | ❌ | ◐ | ★★★ | M | Display-only guess in `fontFilter.js:14`. |
| 4 | **Auto underlay by letter height** | ✅ | ✅ | ❌ | ❌ | ❌ | ★★★ | M | Wilcom's ladder is publicly specified (Law 50). |
| 5 | **Real sew-field per placement** | ◐ | ◐ | ❌ | ❌ | ❌ | ★★★ | M | Flat 200×200 lets uncapfitable caps through. |
| 6 | **Monogram mode** (order + enlarged center) | ✅ | ✅ | ◐ | ✅ | ❌ | ★★★ | M | §3. Highest-margin product a small shop sells. |
| 7 | **Script-safe routing** (`autoRoute:false`) | ✅ As-Digitized | ✅ | ✅ | — | ❌ | ★★★ | S | 18 Script fonts entered at an arbitrary node (Law 56). |
| 8 | **Run-stitch mode below the satin floor** | ✅ run fonts | ✅ | ✅ | ✅ | ❌ | ★★ | S | We already compute centerlines; emit as top stitch, not underlay. |
| 9 | **Line spacing + word spacing** | ✅ | ✅ | ✅ | ✅ | ❌ | ★★ | S | Leading hardcoded to `font.leading`. |
| 10 | **Bold as column width, not pull comp** | ✅ | ✅ | ✅ | ❌ | ◐ | ★★ | S | Split the term, recompute spacing (Law 54). |
| 11 | **Split satin >7 mm** | ✅ | ✅ | ✅ | ❌ | ❌ | ★★ | M | Also un-inverts three fonts. |
| 12 | **Full circle baseline + above/below** | ✅ | ✅ | ✅ | ✅ | ◐ | ★★ | M | Arc sweep only. Badge prerequisite. |
| 13 | **Two-line circular badge** | ✅ Wreath | ✅ | ◐ | ❌ | ❌ | ★★ | M | Composable today, not a primitive. |
| 14 | **Envelopes** (Bridge/Pennant/Perspective/Diamond) | ✅ | ✅ Lettering Art | ✅ | ❌ | ❌ | ★★ | L | §2a. Largest structural gap. |
| 15 | **Laydown/knockdown for terry** | ✅ | ✅ | ◐ | ❌ | ❌ | ★★ | M | Towels are the dominant monogram substrate. |
| 16 | **Fixed-line auto-fit modes (5 named)** | ✅ | ✅ | ✅ | ❌ | ◐ | ★★ | M | We have one uniform strategy; names are public (§2b). |
| 17 | **Character-count spacing table** | ✅ | ✅ | ❌ | ❌ | ❌ | ★★ | S | Cheap, differentiating, fixes 3-letter monograms. |
| 18 | **Manual per-pair kerning edit** | ✅ | ✅ | ✅ | ✅ | ❌ | ★★ | M | Tables exist; exposing + overriding is the cheap half. |
| 19 | **Radius-aware arc spacing** | ✅ | ✅ | ✅ | ◐ | ❌ | ★★ | S | Inter-glyph gap/collision on tight radii (Law 52). |
| 20 | **Short-stitch handling, width-gated** | ✅ | ✅ | ◐ | ❌ | ❌ | ★★ | M | Ship gated or not at all (Law 53). |
| 21 | **Mirror** | ✅ | ✅ | ✅ | ✅ | ❌ | ★ | S | Trivial; ornament layer needs it anyway. |
| 22 | **Vertical baseline** | ✅ | ✅ | ✅ | ✅ | ❌ | ★ | S | Layout-only. Sleeves. |
| 23 | **Team names / batch name drop** | ✅ | ◐ | ❌ | ◐ | ❌ | ★★ | M | Real revenue; pure orchestration over existing engine. |
| 24 | **Borders + ornaments** | ✅ | ✅ | ◐ | ✅ | ❌ | ★ | L | §3.4. |
| 25 | **Per-letter reshape** | ✅ | ✅ | ✅ | ◐ | ❌ | ★ | L | Wants the envelope substrate first. |
| 26 | **Custom path / any-shape baseline** | ✅ | ✅ | ✅ | ◐ | ❌ | ★ | L | Needs fractional spacing (Law 52) to be usable. |
| 27 | **Appliqué lettering** | ✅ | ✅ | ◐ | ✅ | ❌ | ★ | L | |
| 28 | **TTF → embroidery conversion** | ✅ | ◐ | ✅ | ✅ | ◐ | ★ | — | Exists in the legacy standalone only, and produces fills/satin-for-thin, not true satin columns. |
| — | Uniform tracking | ✅ | ✅ | ✅ | ✅ | ✅ | | | `letterSpacingMm` |
| — | Justify L/C/R | ✅ | ✅ | ✅ | ✅ | ✅ | | | no full justification |
| — | Slant / italic | ✅ | ✅ | ✅ | ❌ | ✅ | | | `slantDeg`, ±45° is the vendor band |
| — | Whole-object rotation | ✅ | ✅ | ✅ | ✅ | ✅ | | | `rotationDeg` |
| — | Per-letter / per-word color | ✅ | ✅ | ✅ | ❌ | ✅ | | | `colorRanges` — better than PE-D |
| — | Density auto-scaled to fit | ✅ | ✅ | ◐ | ❌ | ✅ | | | two-pass fit, `digitize.js:564-589` |
| — | Auto-size-to-fit garment | ◐ | ◐ | ❌ | ❌ | ✅ | | | `fitScale` + clamp — **stronger than every peer** |
| — | Auto kerning from pair table | ✅ | ✅ | ◐ | ❌ | ✅ | | | up to 97k pairs; 5 fonts ship none |
| — | Sew sequence | ✅ | ✅ | ✅ | ❌ | ◐ | | | Chinese-Postman auto; not user-selectable |

**Where we already win:** auto-fit-to-garment and per-letter color are better than the mid-market. **Where we lose the sale:** no underlay, no letter-height control, no monogram, no cap sew field.

### 2a. Envelopes — depth

Wilcom's set is four names, confirmed from the Quick Reference: **Bridge, Pennant, Perspective, Diamond**, plus Delete Envelope. Handles are draggable; Shift moves the opposing handle, Ctrl moves both the same direction. Hatch calls the same idea Lettering Art and documents it as working best on a Fixed Line baseline. Embird goes furthest — per-axis edge type (Line vs Curve), symmetry options, and user envelopes saved as `.LTG` files.

**The math.** Wilcom publishes names, not formulas, so the parameterisation below is [D]. Normalise the laid-out text block's bbox to `u ∈ [0,1]` across, `v ∈ [0,1]` down, then apply a vertical scale-and-shift `s(u)`, `c(u)`:

| Envelope | Shape function | Parameters |
|---|---|---|
| Bridge | `c(u) = A·4u(1-u)`, `s(u) = 1` | one amplitude `A`; glyph heights preserved, whole block arches |
| Pennant | `s(u) = 1 - k·u` (or `1 - k(1-u)`), anchored on one horizontal edge | taper `k`, side flag |
| Perspective | `s(u) = 1 + k(2u-1)`, symmetric about the block center | taper `k`, signed |
| Diamond | `s(u) = 1 + k(1 - |2u-1|)` | bulge `k`, signed for pinch |

**The one engineering constraint that matters.** `layoutText` applies its per-glyph `place` transform to **finished stitch points** (`satinfont.js:377-381`). That is correct for the arc because a rigid rotation preserves distances. An envelope is a **non-rigid warp**: applied to stitch points it would stretch satin spacing and column widths non-uniformly, exactly the defect it is meant to create the illusion of avoiding. Envelopes must therefore be applied to **`cols` (railA/railB/rungs) at `satinfont.js:334-338`, before `routeGlyph`**, so that spacing, pull comp and routing are all computed on the warped geometry. The insertion point exists; the transform stage is one line lower than the arc's.

Second constraint: a warp that squeezes vertically drives column widths down. Envelope output must re-run the Law 47 width check on the warped rails, not the authored ones.

### 2b. Script connectors — depth

The published solution is not generated connectors (Law 55). Wilcom's five authoring rules make the advance metric *be* the join geometry, and Ink/Stitch reaches the same place by disabling auto-routing. Two practitioner rules corroborate: at crossovers, sequence so the stroke that stitches last sits on top; where a gap is likely, push the start point 0.5–1.0 mm deeper into the adjoining stem [B].

What we need, in order:

1. **`joined: true` per font** in the manifest (18 Script candidates, needs per-font review — not every Script face is connected). Forces `letterSpacingMm` 0, hides the tracking control, and keeps pull comp inside 0.2–0.3 mm so seam-sealing survives bold.
2. **`autoRoute: false`** — pin the glyph entry node instead of letting Hierholzer pick `odd[0]`. Minimum viable version: pick the start node nearest the glyph's authored entry reference point (leftmost node on the join guideline), which we can derive offline from rail geometry.
3. **Force-lockstitch on short inter-element hops**, Ink/Stitch-style, applied when a connection distance falls in a configured range. Required for accents and for any glyph whose components separate.
4. **Do not add overlap.** Pull comp already seals the seam; authored overlap on narrow strokes stacks density at the join.

Fixed-line auto-fit, while we're here — Wilcom's five modes, whose names are the API surface customers expect (`spacing | letter | letter_prop | whole | whole_prop`): **Spacing** (size fixed, spread evenly, may overlap) · **Width** (letter width reduced, spacing kept) · **Size** (proportional, spacing kept) · **Spacing and Width** · **Spacing and Size** (proportional). Ship `spacing+size` as default — it is what our uniform fit already approximates — and expose the rest.

---

# 3. Monogram spec

Enough to build the feature from this section alone.

### 3.1 Letter order is a function of the size mode

The single highest-value rule, and the one a naive UI gets wrong: **enlarging the center letter changes the order.**

```json
{
  "orderRules": {
    "three_letter_enlarged_center": { "order": ["first", "last", "middle"],
      "centerIndex": 1, "centerScale": 1.35,
      "example": "Jane Anne Smith -> J S A" },
    "three_letter_equal": { "order": ["first", "middle", "last"],
      "centerScale": 1.0,
      "example": "Jane Anne Smith -> J A S" },
    "married_woman": { "order": ["first", "marriedSurname", "maidenInitial"],
      "centerIndex": 1, "note": "maiden, not middle" },
    "man_traditional": { "order": ["first", "middle", "last"], "centerScale": 1.0,
      "note": "same-size straight across is the traditional men's form" },
    "couple_traditional": { "order": ["wifeFirst", "sharedSurname", "wifeMaiden"], "centerIndex": 1 },
    "couple_modern":      { "order": ["wifeFirst", "sharedSurname", "husbandFirst"], "centerIndex": 1 },
    "single_adult":  { "order": ["last"] },
    "single_child":  { "order": ["first"] },
    "two_letter":    { "order": ["first", "last"], "centerScale": 1.0 }
  }
}
```

Edge cases to encode:
- **Hyphenated surname → four letters.** Carolee Wicklief Armstrong-Smith → `C A S W`: first, then both surname initials enlarged in the center, then middle. Drop the hyphen visually.
- **Prefix surnames** (DeGennaro, O'Connor): the first letter of the whole surname goes in the center.
- **Couple left/right is contested.** One published focus group found a majority preferred the man's initial on the left, against the "linens are the bride's domain" convention. Ship it as a user-facing toggle, never a hardcoded rule.
- **Timing:** a joint monogram is only valid after the marriage — no shared monogram on wedding programs.
- Practitioners overrule etiquette routinely: "consistency across the set matters more than allegiance to any tradition." The UI should default correctly and never block.

### 3.2 Style catalogue, and the hard truth about our fonts

Named families in commercial use: **interlocking/cipher, master circle, vine, split, script, stacked, diamond, framed/crest**. Shape vocabulary customers order by name: Circle Skewed, Circle Stacked, Master Circle, Round Squeeze, Oval, Scalloped Oval, Rounded Square, Six Sided, Shield, Octagon, Triangle, Diamond, Heart, Shell, Ribbon.

**Real monogram fonts ship three positional alphabets, not one.** A commercial master-circle set ships "all 26 letters in left, center and right positions," in 9 sizes (2″–6″) where size is the **center letter height**, with two frames per size (oval for spaced letters, round for overlapping), satin throughout, plus alignment grids. Font vendors encode the same thing in OTF as lowercase = left initial, uppercase = center, a special character = right, or contextual alternates.

So: **a monogram mode is not "same glyphs, scale the middle one up."** Left and right glyphs are different artwork — partial, tucked, tilted to nest against the center. Our 69 fonts have one alphabet each. Honest plan:

- **Ship now:** enlarged-center and equal-size straight-across using the same alphabet, with correct order logic and per-glyph scale. That is exactly the "3-Letter Traditional / 3-Letter Straight Across" pair the trade already sells. Label it honestly; do not call it a master circle.
- **Defer:** master circle, diamond, vine, interlocking. Those need authored L/C/R rails and negative/overlap kerning, i.e. a new font-authoring pass, not an engine change.

Engine requirement either way: `layoutText` needs **per-position glyph selection** and **per-glyph scale**, which the current single uniform `emMm` + `advance+kerning` loop cannot express.

### 3.3 Sizes — quoted by center-letter height

The trade sizes monograms by **center-letter height**, not by block bounding box. Store presets in those terms. Placement is §4.

| Item | Single letter | 3-letter center |
|---|---|---|
| Washcloth | 1″–1.25″ | 1″–1.25″ |
| Guest towel | 1.5″–1.75″ | 1.5″–2″ |
| Hand towel | 1.75″–2.5″ | 1.75″–2.5″ |
| **Bath towel** | 3.5″–5″ | **4″ (average)** |
| **Bath sheet** | 4″–5″ | **5″ (average)**; names 2″–3″ |
| Napkin | 1″–1.5″ | 1.5″–2.25″ |
| Placemat | 1.5″–2″ | 1.75″–2.5″ |
| Tablecloth | 6″–8″ | 6″–8″ |
| Pillowcase | 1.5″–2″ | 1.75″–2″ |
| Flat sheet | 1.5″–2″ | 1.75″–2″ (match the pillowcase) |
| Euro sham | 3.5″–4″ | 4″–5″ |
| Shower curtain | 10″–12″ | 12″ |
| Bath mat | 4″–5″ | 4.5″–5″ |
| Duvet / coverlet | 12″–14″ | 12″ |
| Decorative pillow | 6″–8″ | 4″–5″ |
| Left chest (garment) | — | 3.5″–4″ overall block |
| Shirt cuff | 0.25″–0.5″ | — |

Note the commercial exception: dress-shirt monograms run at **~6 mm tall** — right at the satin floor — and script needs more width than block at the same height (block/serif ~6 mm wide, script ~8 mm).

### 3.4 Borders, ornaments, laydown — the composition layer

Wilcom's data model is three composable layers: styles, border shapes, ornaments. Semantics worth copying verbatim because they are proven:

- **Up to four borders of the same shape**, each with its own offset.
- **Up to ten ornament sets, up to eight instances each.** The first selected ornament is the **anchor**; "all other ornaments are sized, rotated and mirrored in relation to it." Width/height with lock-aspect, plus a margin offset from the lettering. Ornaments come from motif patterns *or any design file*.
- **Laydown stitch** — "It is common to use laydown stitch with monograms in order to flatten the nap of textured fabrics like terry toweling," implemented as a laydown *fill* used as the outermost border, offset beyond letters and ornaments. This is a different object from center-run underlay and is the single biggest quality lever for towel work, which is the highest-volume monogram substrate.

Frames customers name: laurel wreath, scallop oval, scallop circle, bow frame, vintage oval, crest.

### 3.5 What customers actually order

Three-letter with enlarged center is the volume leader. A real monogram shop's menu is only three products: single initial, classic three-letter enlarged center, or a **name in script**. On towels, first names often outsell monograms. Font demand concentrates on **block, serif, script** — three faces, not 69. Common advice: monogram the hand towels, bath towels and bath sheets; leave washcloths plain.

---

# 4. Placement presets

`src/garments.js` ships flat boxes and nothing else:

```js
{ id: "hat_front", label: "Hat Front", widthIn: 5.0, heightIn: 2.25 },
{ id: "left_chest", label: "Left Chest", widthIn: 4.0, heightIn: 4.0 },
```

Both numbers are defensible — `hat_front` 5.0×2.25 matches Stahls' high-profile cap front exactly, and `left_chest` 4.0″ sits at the top of the 3.5–4.0″ consensus. What's missing is everything that makes a preset *placement-aware*.

### 4.1 Schema to add

```js
{
  id: "left_chest_polo_mens",
  label: "Left Chest — Polo (Men's)",
  code: "LC",                                  // SanMar location code
  design:   { widthIn: 4.0,  heightIn: 3.0 },  // default fit box (today's widthIn/heightIn)
  sewField: { widthMm: 130,  heightMm: 180 },  // HARD machine clamp, separate from design
  anchor: {
    datum: "shoulder_seam",                    // shoulder_seam | collar_seam | neck_edge |
    dyIn:  [7.0, 9.0],                         // hem | border | top_edge | front_seam | cuff_edge
    dxIn:  [4.0, 5.0],
    dxFrom: "center",                          // center | placket | side_seam
    dyTo:  "top"                               // top | center — which edge dyIn measures to
  },
  sizeStepIn: 0.5,                             // +0.5" per garment size up
  womensDyIn: -1.0,                            // women's sits ~1" higher
  textMinIn: { block: 0.25, serif: 0.375, script: 0.5 },
  pullCompMm: 0.20,
  sequence: { centerOut: false, bottomUp: false },
  seamGuard: null                              // caps only: ±0.25" exclusion at x=0
}
```

Three rules that are not geometry, all from the same vendor: **+½″ per size up** from the smallest shirt; **women's ~1″ higher** than men's; and "when in doubt, err toward centering the graphic toward the buttons" — that is what prevents the under-the-arm print.

### 4.2 Rows to encode

**Chest and front**

| Preset | Datum | Vertical | Horizontal | Design | Hard max |
|---|---|---|---|---|---|
| `left_chest_polo_mens` | shoulder seam | 7″–9″ down | 4″–5″ from center | 3.5–4.0 × 2.5–3.5″ | 4.5″ W |
| `left_chest_polo_womens` | shoulder seam | 4″–6″ down | 3″–5″ from center | 3.0–3.5″ W | 4.5″ W |
| `left_chest_tee` | shoulder seam | 7″–9″ down | 4″–6″ | adult 3.5×3.5″, youth 3.5, toddler 2.5 | 5×5″ |
| `left_chest_jacket` | shoulder seam | 6″–8″ down | 3.5″–4″ from center, ≥1″ off the zipper | 4–4.5 × 3″ | 4×4″ thick shells |
| `left_chest_sweatshirt` | crew-neck edge | 3″–3.5″ down | 4″–6″ | 3.5×3.5″ | — |
| `pocket` | pocket | ~0.5″ above pocket hem, or on it | — | ≤ pocket width | — |
| `full_front_tee` | collar | 3″–3.5″ (adult), 2″–3″ youth | centered | adult 11×11″ | 12 W × 14 H |
| `across_chest` | collar | as full front | centered | 4 H × 12 W | same |

**Back**

| Preset | Datum | Offset | Design | Note |
|---|---|---|---|---|
| `upper_back_yoke` | neck edging / collar seam | 2″–3″ down (name line) | ≤3″ H, ≤14″ W | jersey name line |
| `jacket_back` | collar seam | 6″–9″ down **to design center** | 10–14″ W | store `dyTo` — AllStitch's 9″–10″ measures to the top |
| `hoodie_back` | neck edging | 4″–4.5″ with hood up | adult 14×11.25″ | |
| `shirt_back_full` | collar | 5″–6″ (3″ small sizes) | 10–14″ W | |

**Sleeve, cuff, collar**

| Preset | Datum | Offset | Design |
|---|---|---|---|
| `upper_sleeve` | shoulder seam | 3″ down | 3.0 × 2.0″ (12 cm hoop) |
| `sleeve_vertical` | sleeve center seam | along seam | adult 2 × 11.5″ |
| `lower_sleeve` | cuff | 1″ above cuff | 3.5×3.5″ |
| `shirt_cuff` | cuff edge + buttonhole | ¼″–½″ above cuff edge, 1″–1⅜″ from cuff center toward the buttonhole | letters 0.25″–0.5″; faces away from the wearer |

**Caps — the tightest constraint set, per crown profile**

| Profile | Front | Side | Back | Bill |
|---|---|---|---|---|
| Low crown | 1.75 × 4.0″ | 1 × 2.25–2.5″ | 1 × 2.75″ | 2 × 5.5″ |
| Low profile | 1.75 × 4.0″ | 1 × 2.5″ | 1 × 2.75″ | 1.75 × 5.5″ |
| Mid profile | 2.0 × 5.0″ | 1 × 2.5″ | 1 × 2.75″ | 2 × 5.5″ |
| High profile | **2.25 × 5.0″** | 1 × 3.25″ | 1 × 2.75″ | 2 × 5.5″ |
| Visor | 1.5 × 5.0″ | 1 × 4.0″ | — | 2 × 5.5″ |

Cap rules to encode alongside the box: design centered over the front seam and as close to the brim as possible (0.5″–1″ above); **seam guard ±0.25″** at x=0 with a `splitAtSeam` hint so `layoutText` can bias a word break there; widen any satin that must cross the seam and slightly reduce density over it; sequence **bottom-up and center-out** (we do center-out at `digitize.js:317` and `:637`; bottom-up is not implemented and is the higher-value half because it anchors against the stiff bill); cap pull comp 0.40–0.45 mm as a *separate baseline* so "bold on a cap" doesn't stack to a blob; cap back arch text 4″–4.25″ W × 0.5″–0.75″ H with 0.25″–0.35″ characters. Warn at 2.25″ height, hard-fail at 2.5″ (cap-driver frame collision).

**Sew fields — the numbers `exceedsHoop` should actually compare against**

| Frame | Field |
|---|---|
| Brother PR standard | 60×40, 100×100, 180×130, 300×200 mm |
| Brother PR cap frame (PRPCF1) | **130 × 60 mm** |
| Brother cylinder | 90 × 80 mm |
| Tajima cap frame | up to 360 mm length, up to 270° around the cap |
| Barudan EX cap frame | width fixed 13¼″; **crown height sets the field height** |
| Ricoma cap / pocket / bag / sleeve | 5.51×5.98″ / 2.40–3.41 × 4.76″ / ≤5.55×7.09″ / ≤4.72×7.68″ |

Hoop margin rule: smallest hoop that fits design **+ ¼″ (6 mm) from outermost stitch to hoop inner edge**. So `exceedsHoop` becomes `designBBox + 2×6 mm > placement.sewField`, not a flat 200×200.

**Towels, linens, bags** — placement is remarkably consistent across four independent charts:

| Item | Above hem | Above woven border |
|---|---|---|
| Washcloth | 1″–1.5″ | 1″ |
| Guest towel | 2″ | 1.5″ |
| Hand towel | 2″–3″ | 1.5″ |
| Bath towel | **4″** | 2″ |
| Bath sheet | 5″ | 2.5″–3″ |
| Flat sheet | 2″ above the wide hem, top side | — |
| Napkin | 0.75″–1″ from bottom edge, or 2.5″–3″ up from the corner tip on point | — |
| Tablecloth | 5″ up from the corner tip | — |
| Tote | 2″–4″ down from top edge, centered between handles | — |
| Apron | 4″–6″ down from top | — |

Two universal rules that are cheap to encode and embarrassing to get wrong: **the monogram goes on the end opposite the label**, and **no design on the fret** (the raised dobby band). Flat sheets read from the foot of the bed once folded over the blanket. Robes: fold one flap over the other as if worn, fold the collar into position, then place as a jacket left chest; mark terry with straight pins, never chalk.

**Known conflicts — encode as ranges, never pick silently:** left-chest drop spans 5.5″–9″ across sources (default 7″–9″ men's, 4″–6″ women's); tote drop spans 2″–10″ (default 3″, expose the datum); jacket back reconciles only once you store whether the measurement runs to the design's top or its center.

---

# 5. Preflight additions

Today there is exactly one lettering check: `designDims.widthMM < 5 || designDims.heightMM < 5` → "Smaller than 5 mm — thread can't stitch this cleanly" (`app/src/ui/SizePanel.svelte:70`, echoed in `EmbroideryField.svelte:1208`). It tests the whole element's bounding box, so a 40 mm-wide word at a 4 mm cap passes clean.

Proposed check set. Severity: **block** (refuse to export) · **warn** (visible, exportable) · **note** (informational).

| id | Trigger | Threshold | Sev | Message | Law |
|---|---|---|---|---|---|
| `cap_below_font_floor` | effective cap < font `minCapMm` | per-font, derived | warn | "{Font} is rated down to {min} mm caps. This is {actual} mm — switch fonts or size up." | 45 |
| `cap_above_font_ceiling` | effective cap > font `maxCapMm` | per-font | warn | "Above {max} mm this font's widest columns exceed 7 mm and will need split satin." | 45, 47 |
| `lowercase_below_floor` | string has lowercase and cap×`xHeightRatio` < floor | per-font ratio (0.44–0.81 measured) | warn | "Lowercase runs {ratio}× cap in this font — the x-height here is {n} mm, below the {min} mm floor. Try all caps." | 46 |
| `consumables_below_4mm` | cap < 4.0 mm | 4.0 mm | note | "Under 4 mm: run a 65/9 ballpoint needle and 60wt thread." | 48 |
| `satin_column_too_narrow` | any emitted column median width < 1.5 mm | 1.5 mm | warn | "{n} columns are under 1.5 mm — needle holes merge into a slit. Size up or switch to run stitch." | 47 |
| `satin_column_critical` | any column < 1.0 mm | 1.0 mm | block | "{n} columns under 1.0 mm cannot be stitched. Auto-route to run stitch?" | 47 |
| `satin_column_too_wide` | any column median > 7.0 mm | 7.0 mm | warn | "{n} columns exceed 7 mm — splitting satin." (auto-fix once split lands) | 47 |
| `satin_column_unstitchable` | any column > 12.0 mm | 12.0 mm | block | "Columns over 12 mm exceed machine capability." | 47 |
| `underlay_missing` | cap ≥ 6 mm and no underlay emitted | 6 mm | warn | "No underlay at {n} mm caps — add center run." | 50 |
| `underlay_wrong_rung` | underlay style ≠ ladder pick | ladder | note | "Cap height {n} mm suggests {style} underlay." | 50 |
| `underlay_under_5mm` | underlay present and cap < 5 mm | 5 mm | warn | "Under 5 mm, underlay peeks through counters. Removing it." | 50 |
| `min_stitch_filter_high` | configured min stitch > 0.5 mm on a font whose floor is < 8 mm | 0.5 mm | warn | "A {n} mm minimum stitch length will delete satin in this font." | 51 |
| `arc_radius_too_tight` | arc radius < 3 × cap height | 3× | warn | "Letters will collide on the inside of this arc. Increase radius or reduce tracking." | 52 |
| `script_tracking_nonzero` | font `joined` and `letterSpacingMm` ≠ 0 | 0 | warn | "This is a connected script — any tracking opens the joins." | 55, 57 |
| `bold_exceeds_band` | `pullComp + weightOffset` > 0.35 mm | 0.35 mm | note | "Bold widening is doing double duty as fabric compensation." | 54 |
| `bold_starves_density` | widened column ≥ 1.3× authored and spacing unchanged | 1.3× | warn | "Bold at this spacing reads thin — density recompute needed." | 54 |
| `exceeds_sew_field` | bbox + 12 mm > placement `sewField` | per placement | block | "{W}×{H} mm won't fit the {frame} ({fw}×{fh} mm)." | 58 |
| `cap_height_ceiling` | cap placement design height > 2.25″ | 2.25″ / 2.5″ | warn / block | "Over 2.25″ needs a high-profile crown; over 2.5″ the cap driver collides." | 58 |
| `crosses_cap_seam` | any column centerline within ±0.25″ of x=0 on a cap | 0.25″ | warn | "Thin detail over the front seam. Split the word at the seam or widen the column." | §4 |
| `fit_bound_by` | always, on successful fit | — | note | "Sized to {garment box / hoop / band floor / band ceiling}." | 58 |
| `font_missing_kerning` | font ships 0 kerning pairs | — | note | "No kerning data for this font — spacing is metric only." | 57 |

Two design rules for the surface itself. First, **report which constraint bound the fit** on every generate, not only on failure — that one line converts "why is my text this size" support traffic into self-service. Second, **the block tier must be small**: only truly unstitchable geometry (sub-1.0 mm columns, over-12 mm columns, over-field designs). Everything else warns, because our derived bands are [D] until a sew-out card validates them (Law 45, note 3).

---

# 6. Build order with acceptance tests

Eight phases. Each is independently shippable and each has a test that fails today. Node's built-in runner drives `test/*.test.js`; vitest drives `app/src/lib/*.spec.js`. New font-corpus checks extend `tools/qc-font.mjs` (already wired to `test/qc-font.test.js`).

### P1 — Measure the corpus, then say what you measured  *(M, unblocks everything)*
New `tools/font-bands.mjs`: for each font in `src/fonts/bin`, compute `capUnits` (from `H`, falling back to `E`), `xHeightRatio`, per-column median widths, and `w5`/`w50`/`w95` as fractions of cap. Emit `minCapMm`, `maxCapMm`, `bandInverted` into `manifest.json` alongside the existing `group`. Replace `sizeBand()`'s guessed multipliers with the manifest values.
**Tests.** `qc-font` fails a font missing `capUnits`. `font-bands` on a synthetic font with uniform 2 mm columns at 20 mm cap returns `minCap = 15 mm`, `maxCap = 70 mm`. `sizeBand("violin_serif")` reports `bandInverted: true` rather than a range. Snapshot the full 69-font band table so future font imports diff visibly.

### P2 — Make size mean cap height  *(S, the unblocker for §3 and §5)*
Add `capHeightMm` to the text element, keep `sizeMm` as an alternative width constraint, and make `buildLetteringDesign` solve for the scale that lands the requested cap. Report `fitBoundBy: "cap" | "garment" | "hoop" | "bandFloor" | "bandCeiling"`.
**Tests.** Requesting a 6 mm cap in `geneva_simple` (cap/em 0.60) yields a measured `H` ink height of 6 mm ±0.1. The same request in `emilio_20_bold` (cap/em 0.98) also yields 6 mm. Requesting 6 mm in a font with a 9.8 mm floor returns `fitBoundBy: "bandFloor"` and a warning, and still generates.

### P3 — Underlay, for real  *(M, largest quality delta)*
Wire `routeGlyph` to consume its `underlay` option. Implement the Law 50 ladder: none below 5 mm cap; center run (`centerFromGeom`, 3 mm step, 2 repeats) 5–10 mm; contour/edge run at 0.4 mm inset above 10 mm; add zigzag at 3 mm spacing when column width > 4 mm. Emit underlay runs before the satin body, tagged distinctly from travel paths — rename the existing travel tag from `"underlay"` to `"underpath"` in the same commit.
**Tests.** A 12 mm-cap word emits runs tagged `underlay` whose count is > 0 and whose total length is 15–25% of the satin length. The same word at 4 mm caps emits zero. `underlay: false` emits zero at every size. Existing `satinfont.test.js` byte-comparison snapshots are regenerated once, deliberately, in this commit and never again by accident.

### P4 — Width guards and split satin  *(M)*
Compute per-column median width in `emitZigzag`'s caller and act on it: below 1.0 mm route the span to `centerFromGeom` as a **top** run stitch (Law 47 + capability row 8 — the mechanism already exists, it just needs to stop being underlay); above 7 mm split with randomized split points; hard-fail above 12 mm. Replace the 0.3 px separation guard with a real mm floor. Make min emitted stitch length configurable, default 0.5 mm.
**Tests.** A synthetic 0.8 mm column emits `kind: "run"`, not `"satin"`. A 9 mm column emits split satin whose split points are not collinear across rows. A 13 mm column raises `satin_column_unstitchable`. No emitted stitch is shorter than the configured minimum. Full-corpus sweep: render every font at its own `minCapMm` and assert zero `satin_column_critical`.

### P5 — Spacing, tracking, leading  *(S)*
`letterSpacingPct` (fraction of cap) alongside the absolute mm form; `wordSpacingRatio` (ratio of height); `lineSpacingPct` replacing the hardcoded `font.leading`; the 2-to-6+ character-count spacing table, longest line wins. Split `WEIGHT_OFFSET_MM` out of `pullCompMm` into a `columnWidthMm` term, and recompute spacing from the widened width.
**Tests.** Doubling `capHeightMm` at fixed `letterSpacingPct` doubles the gap between glyph ink boxes. `lineSpacingPct: 150` puts baselines 1.5× further apart. Bold at 1.5 mm authored width produces penetrations-per-mm² within 5% of normal. Pull comp at `normal` stays inside 0.2–0.3 mm on every fabric preset.

### P6 — Placement presets and the real sew field  *(M)*
Extend `GARMENTS` to the §4.1 schema. Add `sewField` per placement and rewrite `exceedsHoop(design, placement)` to compare `bbox + 12 mm` against it. Add cap `seamGuard` + `splitAtSeam`, and implement bottom-up ordering next to the existing center-out in `digitize.js`.
**Tests.** A 140 mm-wide cap-front design now fails against the 130×60 mm cap frame (it passes today). A left-chest design at 100×70 mm passes the 130×180 field. `hat_front` stitch order is bottom-up *and* center-out — assert the first block's centroid y is below the last's, and that consecutive blocks alternate sides of x=0. `garments.test.js` gains a case per preset asserting `anchor.dyIn` ranges are ordered and non-empty.

### P7 — Monogram mode  *(M)*
Order resolution from §3.1 as a pure function; per-position glyph scale in `layoutText`; item presets sized by center-letter height; laydown/knockdown fill for terry.
**Tests.** `monogramOrder({first:"J", middle:"A", last:"S", mode:"three_letter_enlarged_center"})` → `["J","S","A"]` with `scales [1, 1.35, 1]`. Equal-size mode → `["J","A","S"]`, scales all 1. Married-woman mode uses maiden, not middle. Hyphenated surname produces four letters with both surname initials centered. A 4″ bath-towel preset produces a **center letter** whose ink height is 4″ ±2%, not a 4″ block. Laydown fill extends ≥3 mm past the outermost letter ink and stitches first.

### P8 — Envelopes  *(L)*
Warp `cols` (rails + rungs) at `satinfont.js:334-338`, **before** `routeGlyph`. Four named envelopes per §2a plus Delete. Re-run the Law 47 width check on warped rails. Fractional spacing (0.33 / 0.66) becomes required here.
**Tests.** Identity envelope produces byte-identical output to no envelope. Bridge with `A=0` is the identity. A Diamond that squeezes a 2 mm column to 1.2 mm raises `satin_column_too_narrow` — proving the check runs on warped geometry, not authored. Satin spacing measured along the outer edge of a warped glyph stays within 15% of the inner edge with fractional spacing at 0.66, and diverges without it.

### Cross-cutting, every phase
- **A sew-out card gates the constants.** P1's bands, P4's split threshold and P5's density recompute are all [D] until a physical card exists: each font at its derived floor, at 1.5× floor, and at ceiling; block/serif/script at 4, 5, 6, 8 mm caps; bold vs normal at 1.5 mm columns. Ship them as **warn**, promote to **block** only after the card.
- **Script fonts get their flag before P8.** The `joined` / `autoRoute` audit across the 18 Script faces is a half-day of reading rails and is a prerequisite for trusting any script output at all.
- **Never regenerate `satinfont.test.js` snapshots except in P3.** They are the only thing standing between a spacing refactor and 69 silently altered fonts.

---

## Honest limits

- Hatch's and Wilcom's **per-font mm tables** could not be retrieved (403/404 to anonymous fetch). The Ink/Stitch font library is the substitute, and is arguably the better fit since our corpus descends from it.
- **No vendor publishes a default pull-compensation magnitude.** Ink/Stitch ships 0 and says explicitly it must be determined by test sew. Wilcom's 0.20/0.35/0.40/0.2–0.3 table is published guidance, not a default. Any number we adopt is our calibration.
- **No vendor publishes a minimum cap height by style.** They publish per-font ranges. That is the more defensible model and the one to copy; the block/serif/script pattern in Law 45 is inference from the band tables, and the numbers in §1b are our own measurements, sensitive to the percentile choice.
- The **`.BE`/`.BX` and `.OFA`** internal models are unverified — the claim that they recalculate density on scale rests on a trade blog. It does not affect anything we build.
- The claim that **18 Script fonts are connected** is a group-label inference, not a per-font inspection. Some Script faces in the corpus are disconnected brush styles for which `joined` would be wrong.

---

## Verification note (2026-08-01, main session)

This document was researched against `main`. Two of its four "corrections"
are stale on `feat/satin-rails`: mirror X/Y and the two-line circular badge
layout both landed there in commit 2ffa28e and are real, tested primitives.

The other two were verified TRUE on `feat/satin-rails` by direct code reading:

- `routeGlyph` destructures only `pxPerMm, spacingMm, pullCompMm, slantDeg`
  from its opts — `opts.underlay` is passed in and never read.
- The runs it tags `kind: "underlay"` are `centerFromGeom` traversal spans
  (Euler-walk travel between satin spans), not structural underlay, and
  `satinplay.centerRun` has zero callers. The element schema's
  `underlay: true` and the UI switch built on it are inert.

Law 50's underlay ladder is therefore built on a mechanism we do not have.
Fix queued: center-run underlay emitted in `routeGlyph` behind the existing
flag, with the cap-height ladder gating it in `layoutText`.
