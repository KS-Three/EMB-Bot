# Is there a citable source for "sharp satin angles under 15° break thread"? — 2026-10-01

**The question.** A feature list Kent pasted puts "sharp satin angles under 15°"
under thread-break risk. `preflight.py` has no such check; PR #597 left it out
because no threshold with a source was found (`ROADMAP.md` gate 1: no physical
constant without a trade source or a sew-out). Does any citable source exist —
for 15°, for any other angle, or for an equivalent rule?

Researched the same day: ~20 web searches, 16 page fetches, one source-file
read. Vendor docs were followed to the page that owns the claim. Nothing here
was sewn or measured.

---

## Verdict

**Nothing citable supports 15°. Only software defaults exist, and none of them
is 15°.**

- **No primary source states any corner angle below which thread breaks.** Not
  15°, not any other number. The figure was not found on any page reached —
  vendor, thread maker, needle maker, machine maker or trade press.
- **The only published corner angles are Wilcom's Smart Corners defaults**
  (cap below 20°, mitre below 45°, lap below 110°). They are user-editable
  settings that pick a corner *construction*. The page that carries them says
  nothing about breakage. A default is a design choice, not a physical limit.
- **Vendors do tie thread breaks to the thing a sharp turn causes — stitches
  bunching on the inside edge — but qualitatively, and they trigger on stitch
  spacing, never on angle.** Wilcom says so for sharp *curves*; Melco says so
  for "curves and sharper angles". The repo already measures that crowding
  directly.
- Wilcom's own sentence about sharp *corners* names hard spots and damage to
  "fabric or needle". It does not say thread.

So: gate 1 stands for an angle threshold. A negative result, stated plainly.

---

## Sources

Accessed 2026-10-01. "Fetch" says how the quote was obtained: **raw** = pulled
from the page's HTML with `curl` and read directly; **summarised** = returned by
a fetch tool that passes the page through a small model, so the wording is
probably right but was not seen in the raw page. Re-check a summarised quote
before it goes anywhere load-bearing.

### Primary — digitizing software vendors

| # | Source | Quote | Claims | Number? | Default or physical limit? | Fetch |
|---|---|---|---|---|---|---|
| 1 | Wilcom EmbroideryStudio help, *Adjust smart corner settings* — <https://docs.wilcom.com/embroiderystudio/26/en/OnlineHelp/Quality/quality/Adjust_smart_corner_settings.htm> (same text on the e4 page the repo already cites) | "The default is cap below 20°." | Which corner construction is applied at which angle. **No mention of breaks, bunching or damage on this page.** | Yes: cap < 20°, mitre < 45°, lap < 110° | **Software default**, user-editable | raw |
| 2 | Wilcom, *Controlling corner stitching* — <https://docs.wilcom.com/embroiderystudio/26/en/OnlineHelp/Quality/quality/Controlling_corner_stitching.htm> | "Sharp corners may cause stitch bunching which can create hard spots" | Bunching, hard spots, damage to **fabric or needle**. Not thread. | No | Neither — qualitative | raw |
| 3 | Wilcom, *Reducing stitch bunching* — <https://docs.wilcom.com/embroiderystudio/26/en/OnlineHelp/Quality/quality/Reducing_stitch_bunching.htm> | "This may cause thread breakage when stitching out." | **Thread break**, from inside-edge bunching on sharp **curves** (not corners). The closest thing to the feature-list claim. | No | Neither — qualitative | raw |
| 4 | Wilcom, *Apply stitch shortening* — <https://docs.wilcom.com/embroiderystudio/26/en/OnlineHelp/Quality/quality/Apply_stitch_shortening.htm> | "Default settings suit most designs." | The cure for #3. Trigger is spacing as a **% of nominal spacing**; at most five consecutive short stitches. No angle anywhere. | Mechanism only; the default % was not visible in the text reached | Software default | raw |
| 5 | Wilcom, *Eliminating small stitches* — <https://docs.wilcom.com/embroiderystudio/26/en/OnlineHelp/Quality/quality/Eliminating_small_stitches.htm> | "Small stitches can damage fabric and cause thread or needle breakage." | **Thread break**, from small stitches generally. Not corner-specific. | No (on the text reached) | Neither | raw |
| 6 | Hatch Embroidery 3 help, *Corner stitching* — <https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Editing/edit_advanced/Corner_stitching.htm> | "mitred or capped automatically depending on how sharp the corner turns" | Same Wilcom engine; repeats #2's sentence. No angle value on the page. | No | — | raw |
| 7 | Melco DesignShop help, *Stitches Too Small* — <https://www.melco-service.com/source1/Stitches_Too_Small.htm> | "It is meant to prevent thread breaks, thread build up" | **Thread break**, for the Short Stitches feature on "curves and sharper angles". Also gives minimum stitch lengths in points (satin ≥ 10 pt = 1.0 mm) and an auto-disable below 20 pt. | Lengths yes; **angle no** | Lengths are vendor guidance / defaults | summarised |
| 8 | Melco DesignShop v9 glossary — <https://melco-service.com/docs/DS_V9_090309/Glossary.htm> | "to prevent an excess of stitches at one point" | Defines short stitches as an anti-crowding device. No break claim, no angle. | No | — | summarised |
| 9 | Embrilliance help, *Satin Column Cornering (Level 2)* — <https://embrilliance.com/Help/Platform%20Win%201170/satincolumncorneringlevel2.htm> | "Mitered corners work well for corner angles at 90 degrees" | Appearance / construction advice. No break claim. 90° is an example, not a threshold. | No threshold | — | summarised |
| 10 | Ink/Stitch source, `lib/elements/satin_column/satin_column.py` on `main` — <https://raw.githubusercontent.com/inkstitch/inkstitch/main/lib/elements/satin_column/satin_column.py> | "Inset stitches if the distance between stitches is smaller than this." | Short-stitch trigger is a **distance** (default 0.25 mm), inset default **15 %** capped at 50 %. Grep of all 1,255 lines for `sharp`, `corner`, `degree`: only curve-tolerance tooltips and a comment — **no corner-angle logic at all**. | 0.25 mm, 15 % | **Software default** | raw |
| 11 | Ink/Stitch docs, *Satin Column* — <https://inkstitch.org/docs/stitches/satin-column/> | "Stitches in areas with high density will be inset by this amount" | Same parameters as #10. No break claim, no angle. | No | — | summarised |
| 12 | Tajima DG/Pulse product page (Custom Cornering) — <https://tajimaeurope.com/en/pulse-software-solutions/embroidery-software-tajima-software-dg16-pulse/> | none taken — seen in a search snippet only | Four corner styles chosen by corner sharpness. Appearance/bulk. No angle, no break claim in the snippet. | No | — | **snippet only** |

### Primary — thread and needle makers

| # | Source | Quote | Claims | Number? | Fetch |
|---|---|---|---|---|---|
| 13 | Madeira FAQ — <https://www.madeira.com/embroidery-solutions/service/support/faq> | "too many stitches lie on top of each other" | **Thread break** from density / stacked stitches. No corners, no angle. | No | summarised |
| 14 | Madeira USA, *Why does my thread break or fray?* — <https://www.madeirausa.com/services/troubleshooting/fraying-breaking/> | "Poor digitizing – This can also be a major contributor to frequent thread breaks" | **Thread break**, digitizing named as a category only. | No | summarised |
| 15 | Gunold, *What are the reasons for thread breaks* — <https://www.gunold.com/tips-training-shows/pro-tips/what-are-the-reasons-for-thread-breaks/> | none — the page lists mechanical causes only | Needle, tension, hook, bobbin. **Digitizing is not mentioned.** | No | summarised |
| 16 | Groz-Beckert embroidery-needle pages | none taken | Search snippets discuss needle deflection and eye geometry; nothing about design geometry or corner angles. | No | **snippet only** |

### Secondary — trade press and vendor blogs (last resort, labelled as such)

| # | Source | Quote | Claims | Number? | Fetch |
|---|---|---|---|---|---|
| 17 | ColDesi blog, *Creating Sharp Embroidered Corners* — <https://shop.coldesi.com/blogs/news/creating-sharp-embroidered-corners> | "Cramming stitches in the inside of a corner is brutal" | Bunching at inside corners; short stitches as the cure. ColDesi is a machine distributor, not a maker. | No | summarised |
| 18 | Impressions magazine, *Embroidery Tips for Corners and Capping* (J. Elliott, 2017-01-09) — <https://impressionsmagazine.com/process-technique/embroidery-tips-for-corners-and-capping/16307/>; original at <https://blog.ignitiondrawing.com/corners-and-capping/> | none — no sentence met the bar | Treats obtuse vs acute corners qualitatively. No degrees, no break claim. | No | summarised |

### What the search for "15°" itself returned

Four differently-worded searches for a 15° / "15 degrees" satin-corner or
thread-break rule returned no page stating one. The digitizing-service blogs
that surfaced say sharp angles and acute turns break thread, with no number and
no source; they were not opened and are not cited.

**One coincidence worth knowing, not a finding:** Ink/Stitch's
`short_stitch_inset` default is **15** — percent, not degrees (source #10). A
list that garbled "15 % short-stitch inset" into "15° angle" would look exactly
like the line in question. That is a guess about where the number came from and
nothing more; no evidence links the two.

### A correction to what the repo already records

`docs/research-handoff-2026-08-07.md` §5.5 lists Wilcom's defaults as cap < 20°,
mitre < 45°, lap < 110°. The numbers match the page. Two details do not:

- Under the *Mitre* heading the page's own sentence reads "The default is lap
  below 45°." — it says **lap**, in both the e4 and the ES 2026 help (raw HTML,
  read 2026-10-01). Almost certainly a typo in Wilcom's doc for "mitre", since
  the lap default is given separately as 110° — but the page does not literally
  say "mitre below 45°".
- §5.5 puts the "stitch bunching … hard spots" sentence alongside the angle
  table as if one page carried both. They are separate pages (#1 and #2). The
  page with the numbers makes no failure claim; the page with the failure claim
  has no numbers.

---

## What the repo already has

**No corner-angle break check, on purpose.** `digitizer/digitizer_core/preflight.py`
lines 3546–3549: the sharp-satin-angle check is "absent ON PURPOSE (2026-10-01)"
— no threshold in the repo and no trade source, i.e. gate 1.
`BREAK_RISK_CODES` is `STITCHES_TOO_SHORT`, `DENSITY_STACKED`, `SAME_HOLE_HEAVY`.
`docs/feature-landscape-2026-10-01.md` line 72 records the same gap.

**The mechanism the vendors actually describe is already measured, by distance
rather than angle:**

- `machine.py` 533–545 — `SATIN_SHORT_STITCH_AT_MM = 0.3`,
  `SATIN_SHORT_STITCH_PULL = 0.35`, `SATIN_SHORT_STITCH_PULL_MAX_MM = 0.6`:
  inside-rail crowding on a bend triggers a retraction. Mirrored in
  `src/satinfont.js` 83–92 and `src/satinplay.js` 324–449.
- `stage6_satin.py` — `_short_stitch_guard`; and the corner join
  (`_split_sharp_corners`, `_CORNER_BOUNDARY_TURN_DEG = 45.0`,
  `_CORNER_BOUNDARY_WINDOW_MM = 1.0`, lines 158–183). That 45° is a
  *construction* trigger measured on the pro corpus (1,436 corner events inside
  a continuing run against 18 splits), not a break claim.
- `preflight.py` — `STITCHES_TOO_SHORT` (line 149; `machine.TINY_STITCH_MM = 0.5`)
  and `SAME_HOLE_HEAVY` report the crowding where it lands, whatever caused it.
- `machine.py` 290–292 — `CONTOUR_MITRE_LIMIT = 2.0` is polygon-offset geometry,
  unrelated to satin corners.

**Prior research already said there is no number.**
`docs/machine-physics-playbook-2026-07-31.md` Law 37: no numeric
direction-change threshold exists in primary sources — "score smoothness
monotonically, don't invent a cutoff". `docs/hatch-manual-teardown-2026-08-08.md`
line 497: the Hatch manual carries no short-stitch rule for tight curves. This
pass agrees with both.

**Gate reading.** `DOCTRINE.md` line 4710 says gate 1 does not cover an angle
that is a design choice. That applies to *which corner to build*. A claim that
thread **breaks** below an angle is a claim about thread and cloth, so gate 1
does cover it — fabric settles it, geometry cannot.

---

## What a check could honestly claim

1. **A "satin angle under 15° — thread-break risk" finding: leave it out.** No
   source for 15°, no source for any angle, and no vendor frames the break as an
   angle. Shipping it would put an invented physical constant behind a
   break-risk label.
2. **Borrowing Wilcom's 20° instead: also no.** It is a cap-corner default on a
   page that makes no failure claim. Citing it as a break threshold would
   misrepresent the source.
3. **What the evidence does support is already in the file.** The sourced chain
   is: sharp turn → stitches bunch on the inside edge → thread may break
   (Wilcom #3, Melco #7). The repo flags the middle link by distance
   (`STITCHES_TOO_SHORT`, `SAME_HOLE_HEAVY`), which is how both vendors and
   Ink/Stitch trigger it too. If the feature list's line needs an answer, the
   honest one is: *covered by the crowding findings; no separate angle check.*
4. **If an angle note is ever wanted, it can only be advisory and must not say
   "break".** Wording the sources would bear: *"Sharp corner in a satin column —
   stitches may bunch on the inside. Wilcom's default caps corners under 20° and
   mitres under 45°."* That is a construction hint attributed to a named
   default, not a risk score, and it would not belong in `BREAK_RISK_CODES`.
   Adding it is a new constant in the angle code — Kent's call.
5. **What would actually settle it** is a sew-out: a satin V at a ladder of
   apex angles, same thread, needle and fabric, counting breaks. That is the
   instrument gate 1 names; `docs/sewout-calibration-brief-2026-09-30.md` is
   where such a strip would be added.

---

## Not reached or not verified

- **silverseams.com** *Satin joins and corners* — 302 to an auth error (403).
  Not read.
- **Wilcom *Adjust smart corner settings*, ES 2025 / v27–28** — only the e4 and
  v26 pages were read; whether the "lap below 45°" wording persists in newer
  help is unchecked.
- **Wilcom stitch-shortening default percentages** — the *Apply stitch
  shortening* page describes the fields; the default values sit in a dialog
  image and were not in the text reached. The percentages in
  `research-handoff-2026-08-07.md` §5.6 were not re-verified here.
- **Hatch default corner angles** — the Hatch page gives none. Whether Hatch
  ships the same 20° / 45° as EmbroideryStudio is unverified.
- **Tajima DG/Pulse help** — the in-product help for Custom Cornering was not
  found online; only a marketing page, via a search snippet. Any default angle
  it has is unknown.
- **Groz-Beckert, Schmetz** — search snippets only; no page was opened. Schmetz
  returned nothing relevant.
- **Amann / Isacord** — no relevant page surfaced.
- **Tajima, Barudan, ZSK machine manuals** — searches returned only third-party
  troubleshooting blogs. No maker-owned page discussing design geometry was
  found; the manuals themselves were not opened.
- **Summarised quotes** (#7, #8, #9, #11, #13, #14, #17) — obtained through a
  summarising fetch, not read in raw HTML. Treat the wording as probable.
- **Printed trade references** (digitizing textbooks, paywalled trade
  articles) — not accessible; a number could exist there. This pass covers the
  open web only.
