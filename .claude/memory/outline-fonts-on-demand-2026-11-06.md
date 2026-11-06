---
name: outline-fonts-on-demand-2026-11-06
description: Kent reopened outline (TTF/OTF) fonts 2026-11-06; the service lays them out and sews them through the Column lane on demand (POST /lettering), 21 OFL families vendored; the 07-24 "no outline fonts" ruling was about the browser auto-trace
metadata:
  type: project
---

**Kent, 2026-11-06:** "import some more fonts, that are not pre-digitized, but
embot will have the ability to digitize them (slower, but easier than importing
an image of the font)". He picked the **starter OFL set** over the full
137-family list and over own-TTF upload.

**What was built (PR from lane `size-recount-6897ad`):**
- `digitizer_core/outline_fonts.py`: registry + fontTools layout (cmap, advance
  widths, `kern` + GPOS PairPos kerning kept as classes, NOT expanded —
  Montserrat's expansion is ~1M pairs), NONZERO-winding fill (variable fonts
  keep overlapping contours; even-odd nesting read Roboto's B as two bodies and
  "Fab" as six regions), `build_text_result` → lettering-tagged auto-tier
  regions (`text_candidate`, tier "auto") so `columns.is_lettering` and
  `pipeline._lane_has_letters` take them.
- `POST /lettering` (same `/jobs/{id}` contract as `/digitize-manual` + a
  `lettering` echo), `GET /fonts/outline` (+ `/{key}/file`, `/{key}/license`,
  public like `/health` — a CSS `@font-face` cannot send the token).
- 21 families / 33 entries / 6.2 MB under `digitizer_core/outline_fonts/`,
  unmodified from google/fonts at commit `86aced91`, `tools/fetch_outline_fonts.py`
  (`--check` verifies sha256s). OFL only; Apache families (Permanent Marker)
  left out; Merriweather (4.6 MB) and Lato left out for size.
- Studio: `app/src/lib/outlineFonts.js`; key `outline:<key>` on a text element;
  result on the element as `result`/`appliedConfig`/`lettering`/`stats`;
  `staleness.js` + `flow.js` + `generate.js` know it; "Outline" chip in the
  font browser with `@font-face` previews; "Digitize lettering" button in
  TextStep (nothing runs on its own, 2026-10-05).

**Why:** the 2026-07-24 ruling ("outline fonts auto-trace worse than
hand-authored satin") predates the Column lane (ON 2026-10-20); the 09-19
lettering-route review already listed "bring-your-own-font-file" as the real
option once the Column construction existed, and the 09-12 sourcing doc named
"Kent reopening outline-font import" as the trigger. Spike evidence (same word,
same font, both routes, Kent's laptop): Fremont/Montserrat Bold cap 12 mm
15.5 s vector vs 24.2 s PNG; Lobster 21.8 vs 7.8 s but the PNG route tagged
0 of 5 shapes as letters; ENTHUSIAST cap 6 mm 2.0 vs 14.7 s.

**How to apply:** an outline font request goes in `FAMILIES` of the fetch
tool, not in `scratch_ink/` and not through `add-font`'s QC (that gate is for
hand-authored `.embf`). Do not expand GPOS class kerning. Keep the file route
public. Not built, not promised: own-TTF upload, arc, per-letter colour,
shaping/ligatures. Not sewn (gate 1). Related: [[lettering-board-2026-10-25]],
[[garment-size-like-pro-2026-10-26]].
