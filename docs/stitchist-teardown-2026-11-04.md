# Stitchist teardown — 2026-11-04

Source: live crawl of `stitchist.app` (site, blog, `/app` editor, every client
script and stylesheet, the unauthenticated GET endpoints), an editor walk in the
desktop app's browser pane, and one Auto Digitize run on the MFab hat logo at
DADE's 36.7 mm, rendered beside DADE's file and ours. Companion:
`dade-app-teardown-2026-11-04` in memory (DADE, same day, same artwork). Nothing
here was read from a pro's file; the only pro render made today
(`pro_renders/stitchist-teardown-2026-11-04/golf_hat_dade_*.png`) stays
gitignored and is not referenced.

Numbers below carry a size. A stitch count without one is meaningless for this
comparison, which is the one lesson of the DADE note that this one repeats.

## 1. What it is

- **Product.** "Stitchist. Embroidery Digitizing Studio": browser editor, free
  forever with DST + PES export, Pro **$50 once** (no subscription). Side tools
  `/converter` (stitch-file format conversion, 47 formats read, 8 written) and
  `/resizer`. Public counters (`/api/stats`): 1,700 designs saved, 4,800 files
  exported. Terms updated 17 Oct 2026, "operated from the United States",
  `support@stitchist.app`, Stripe checkout.
- **Architecture.** Internal name `appliquégen`, v1.1.0, build `08bbf5e7bace`
  (`/api/meta`). The client is **plain JS, no framework, no bundler**: 23 files,
  19.8k lines; `digitizer.js` alone is 610 KB. The engine is **server-side
  Python**: `Server: uvicorn` behind `Via: 1.1 Caddy`, the digitizer header
  says "FastAPI pipeline … pyembroidery writers", and client comments name the
  modules (`autodigitize/wand.py`, `autodigitize/analyze.py`, `build.py
  _layer_of`). The editor serialises shapes to SVG + a DesignConfig and every
  stitch is a round trip: `POST /api/import` (session, cached and evicted:
  "unknown session" re-imports) → `/api/sequence` (plan for the player) →
  `/api/build` → `GET /api/download/{session}` (zip).
- **API surface seen from the client.** `autodigitize/analyze|build|recovery`,
  `magicwand`, `pushpull` + `pushpull/materials`, `satin-angles`, `boolean`,
  `autoredwork`, `lettering`, `satin-text/fonts|preview|upload`,
  `stitch-fonts/read|render` (BX / letter-file font import), `fonts` (TTF
  catalogue + upload), `fill-patterns` (13 patterns baked as per-row
  needle programs from vendor PES files), `threads/match`, `convert`,
  `read_stitches`, `projects`, `billing/*`, `events`.
- **Posture.** CSP `connect-src 'self' https://api.stripe.com` (the page
  cannot fetch anything cross-origin), cookieless first-party event counting
  (`track.js`: name + feature, once per page load), `HttpOnly` device cookie.
  `plan.js` carries a `mode: "desktop"` branch where plan resolves to `pro`
  with no gates: a desktop build exists or is planned.

## 2. Pricing and gates (read from `/pricing` and `/api/meta`)

| | Free | Pro ($50 once) |
|---|---|---|
| Editor, node editing, satin columns, click-to-stitch | all | all |
| Text wizard | 32 satin fonts, 26 fill fonts, monograms | + private TTF/OTF uploads |
| Stitch types | running, bean, fill, satin, manual | + blanket, zigzag |
| Fill patterns | classic 5 | all 13, + gradient fills |
| Export | DST + PES, one size | all 8 (JEF EXP VP3 U01 PEC XXX) |
| Auto Digitize | **1 design, account required** | unlimited |
| Magic wand | 5 clicks | unlimited |
| Redwork, push/pull wizard, SVG import | no | yes |
| Cloud projects | 3 | unlimited + version history |

Trial accounting is server-side (`trials.autotrace.limit 1, needs_account
true`); an unauthenticated `POST /api/autodigitize/analyze` answers
`401 {"code":"auth_required","feature":"autotrace"}`. The wizard's last step
says "Your one free use. Errors don't use it."

## 3. Editor walk (what is actually there)

- **Hoops** 4x4 / 5x7 / 6x10 / 8x8 / custom; everything in mm; autosave to
  the browser, "Saved to this browser" until signed in.
- **Tool rail** S R C 1 2 3 4 6 7 W 9 M H: select, reshape, cut/knife, open
  path, pen, closed shape, primitives (rect, circle, triangle, heart, diamond:
  two clicks, not a drag), hole, angle guide, magic wand, click-to-stitch
  blocks, measure, pan. Boolean union/subtract/intersect, group, flip, rotate.
- **Inspector** has four tabs per shape. *Stitch*: type + parameters (fill:
  angle 45°, row spacing 0.2 mm, stitch length 4.0 mm, stagger 1/3; satin:
  width 2.0, density 0.4, pull comp 0, short stitch 0.25, corner mitre, split
  satin off, auto-split above 7 mm; running 2.5 mm; bean 3 passes). *Underlay*:
  "Auto" ("an edge run for small shapes and adds open tatami for larger
  fills; decorative fills use closer support rows") or chosen, with edge inset,
  length, spacing, angle-to-fill; multiple underlays per shape. *Effects*:
  fill pattern, pattern size, gradient (Pro), **angle lines drawn on the
  shape** to steer fill direction. *Controls*: knock out under overlaps,
  tie-in, tie-off, trim after object, machine stop after object, start/end
  points.
- **Sequence panel** (Objects / Colors) with drag reorder, per-object **live
  stitch count** from the engine, eye and lock per row.
- **Preview** is a scrubbable sew-out player (pass n/n, 0.5–4×, "Stitch-out
  ready: 2,909 stitches, 3.6 m of thread"). **Realistic** is `thread_paint.js`:
  Canvas2D only, CC0 PBR fabric maps, every stitch a lit capsule with a twist
  normal map, baked in a worker, no WebGL "so every machine renders the same
  pixels".
- **Export** dialog: format chips, basting frame (margin 5 mm), max stitch
  7 mm (split on export), PES v6/v1. The download is a zip:
  `Untitled_color-chart.pdf`, `Untitled_preview.png` (2096 × 857, thread
  textured), `5x7/Untitled_5x7.dst`, `5x7/Untitled_5x7.pes`.
- **Import** menu: project file, trace-over image (reference behind the canvas,
  the free manual route), SVG (Pro), stitch file ("lossless", every stitch
  editable).
- **Learn** (`learn.js`): a 16-step tutorial that runs on the real canvas,
  never traps the pointer, and advances by observing `Digitizer._state()` and
  the DOM rather than on "Next".

## 4. Auto Digitize: what it asks and what it sends

Upload PNG/JPEG/WebP/GIF/BMP/SVG ≤ 20 MiB (SVG rasterised client-side first).
`analyze` takes `target_mm` (longest side; default 90 % of the hoop's short
side, capped at 100), `tolerance` 0–100 (default 20, "Magic Wand units"),
`detail` 0–100 (default 50, auto-raised to 64 then 75 on this logo), `auto`,
`max_colors`, `thread_brand`. The answer is `objects` (id, name, color, kind,
`stitch`, `rings`, `bbox`, `head.kind` line / background, `members`),
`colors`, `findings` (kinds seen in code: `enclosed`, `similar_colors`,
`gaps`; levels warn / check / suggest / info; each with `choices` and a
default), `canvas_mm`, `design_bbox`, `vector`.

Four steps: **Trace** (views Trace / Original / Stitch types, cloth colour,
sliders) → **Suggestions**, one card each, answer pre-picked, with a "Why?"
that carries numbers → **Stitches** per object (Satin / Fill / Running / Off,
machine stop, more options) → **Colors** (Brother chart by default, merge or
turn off a colour). `build` posts the plan back: `colors`, `objects` with
rings, `ops` (`stitch`, `merge`, `recolor`), `fabric` (11 fabrics, each with
a `give` factor from `/api/pushpull/materials`: leather 0.55, felt 0.7,
denim 0.85, woven 1.0, linen 1.2, …), `satin_conversion: "studio"`. Build
order is fills first, then line-work (satin, bean, running) on top, "fills
traced reaching under the lines sewn over them".

On the MFab hat logo the three cards were: *Stitch these inner areas?*
("They match the background colour (134 mm² in all) … stitched in white
thread, which looks right on any fabric"), *How should these lines stitch?*
(keep as fill / satin / triple run), *Keep the background?* (leave as fabric).

**The trace is re-run at the chosen size.** At the 100 mm default it found
13 objects, 3 colours, ~5,536 stitches; typing 36.7 mm re-traced to **4
objects, 2 colours** (Background off, Black area, White area 1, White area 2,
White lines): the small white letters merged into one "White lines" fill.

## 5. Head-to-head at 36.7 mm (MFab hat, the 418-px PNG DADE received)

One renderer for every file (0.4 mm thread, 24 px/mm, khaki cloth), block
colours as the files sew them:
[`sheet_mfab_36.7.png`](renders/stitchist-teardown-2026-11-04/sheet_mfab_36.7.png).
Stitchist's own thread-textured preview of the same file:
[`stitchist_own_preview.jpg`](renders/stitchist-teardown-2026-11-04/stitchist_own_preview.jpg).

| file | stitches | trims | jumps | colour changes | thread | under 0.3 mm | 0.3–1 mm |
|---|---|---|---|---|---|---|---|
| Stitchist, defaults (woven) | 3,018 | 18 | 24 | 1 (black → white) | 3.7 m | black 11 %, white 36 % | black 18 %, white 46 % |
| DADE, defaults | 2,561 | 0 | 35 uncut | 2 | 1.7 m | black 45 % | black 30 % |
| EMB-Bot default (`photo_scene` route) | 5,348 | 12 | 23 | 1 (black → white) | 7.7 m | 2 % | 32–34 % |
| EMB-Bot `forced_class=flat` | 4,364 | 13 | 27 | 1 (white → black) | 5.8 m | 2 % | 30–36 % |

What the picture shows:

- **Stitchist reads at thumbnail size** and layers the white keyline OVER the
  black ground, the way the pro's hat does and the way our flat route does
  not. It does it with tatami rows across a ~0.5 mm stroke, so **82 % of the
  white block's stitches are under 1 mm** (36 % under 0.3): the same
  needle-pile class DADE's black block is in (75 % under 1 mm), with trims
  and a sane colour order added. "AND WELDING LLC" is marginal in its own
  preview and in ours.
- **DADE** sews one black mass, leaves the keyline bare, and strays grey.
- **Ours default** is denser (7.7 m), sews the keyline as sub-mm satin and
  smears the small line; **ours flat** buries the white under the black and
  reads as a blob (both as measured in the DADE note).

Caveats: fabric stayed "Cotton / woven" (the Cap front choice did not take in
the browser pane), and this is one logo at one size, chosen because DADE's
file already existed at it. Stitchist's trace at 100 mm kept the small
letters as their own objects; a hat-size (113.5 mm) run would need a second
free run or Pro.

## 6. Worth taking (ideas, not builds)

1. **Suggestions as questions with the answer pre-picked and a "Why?" with
   numbers.** Three cards, each a decision the digitizer would otherwise
   make silently (enclosed white: stitch or fabric; lines: fill, satin or
   triple run; background: keep). Maps straight onto our review step.
2. **Re-trace at the output size, and show the recount.** The object count
   changing with `target_mm` is visible in the footer before anything is
   built. Ours decides size-dependent things too; the user never sees the
   count move.
3. **Per-object live stitch counts in the sequence list**, and a preview
   footer that states thread length.
4. **The export bundle**: colour-chart PDF, thread-textured preview PNG,
   per-hoop folders, basting frame, max-stitch split at export, PES v1/v6.
   Our service already writes the formats.
5. **"Errors don't spend the free run"** and server-side trial accounting
   (`trials` in `/api/meta`), if a free tier ever exists.
6. **A tutorial that observes editor state** instead of a modal tour.
7. **Deterministic Canvas2D thread render baked in a worker** (no WebGL),
   with real PBR fabric maps.
8. The fabric `give` table is **their** constant and nothing here verifies
   it; ROADMAP gate 1 applies before any number from it enters ours.

## 7. Traps met today

- Auto Digitize is account-gated and single-use on Free; the gate is a 401
  on `analyze`, so a curl probe confirms it without spending anything.
- The page's CSP blocks cross-origin fetches, so a file cannot be pulled from
  GitHub into the page; it was base64-injected into the hidden
  `.dz-file-auto` input via `DataTransfer` (a lossless WebP of the PNG,
  pixel-identical, 21 KB instead of 46).
- The built-in browser pane wrote the zip to `Downloads` as a UUID `.tmp`
  (1.36 MB, `PK` header); it is the complete zip.
- Primitives are placed with two clicks, not a drag; the native fabric
  `<select>` ignores keyboard picks in the pane.
- The `/api/build` endpoint shows as GET in the pane's network log for the
  editor's cached-session polling and POST for the export; read the method.

## 8. Files

- `docs/renders/stitchist-teardown-2026-11-04/` — the comparison sheet and
  Stitchist's own preview (no pro file in either).
- `pro_renders/stitchist-teardown-2026-11-04/` (gitignored) — the zip,
  extracted DST/PES/PDF/PNG, every per-file render, DADE's and our 36.7 mm
  files copied out of the DADE session's scratchpad, and the Golf Hat pro
  renders.
- Crawl (scripts, CSS, pages, API JSON) — session scratchpad only;
  everything is public and re-crawlable in minutes.
