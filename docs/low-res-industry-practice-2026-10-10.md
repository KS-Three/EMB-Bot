# How the industry handles low-resolution artwork — 2026-10-10

**Question (Kent):** `docs/tracer-head-to-head-2026-10-10.md` measured that at
1.8–3 px/mm the outline error is set by the source, not the tracer. What does
the rest of the embroidery industry do about that, and what do they tell
customers?

**Short answer.** Nobody claims to recover detail from a small raster. Software
vendors tell the user to bring a better bitmap or go back to the vector
original; decorators publish hard minimums and simplify or delete what falls
under them; digitizing services redraw by hand and charge for it.

Marks: **[V]** = read on the vendor's own page today. **[U]** = page blocked or
only seen through search snippets; treat as unconfirmed.

Units: 300 DPI = 11.8 px/mm, 150 DPI = 5.9, 96 DPI = 3.8. A 146 px file at
80 mm is 1.8 px/mm, about 46 DPI.

## 1. Software

| Product | Auto-digitize input | Preprocessing | Stated resolution | Vector bypasses tracing? |
|---|---|---|---|---|
| Wilcom EmbroideryStudio | Bitmap and vector (Smart Design) [V][1] | Prepare Bitmap Colors: flattens colours, sharpens outlines, cuts noise; opens automatically if needed [V][2] | 300 DPI, not 96; PNG, no anti-aliasing, transparent background; each shape at least 1 sq mm [V][3] | Yes — and if the bitmap falls short, regenerate it from the vector original [V][3] |
| Hatch (Wilcom) | Bitmap and vector [V][4] | Same prep tool; auto-digitize is blocked until the image is processed [V][5] | 300 DPI, not 96 [V][5] | Yes [V][4] |
| Bernina (Wilcom-based) | Bitmap [V][6] | Same prep tool; scans may need manual touch-up (close gaps, reinforce outlines) [V][6] | None on the page read [V][6] | Not covered on that page |
| Tajima DG/ML by Pulse | Vector first (CorelDRAW/Illustrator import, Draw Fusion); bitmaps go through an Image Vectorizer wizard [V][7] | Vectorize, then pick stitch types [V][7] | None stated [V][7] | Yes. Page is the DG/ML 14 site; DG16 behaviour [U] |
| Embrilliance StitchArtist | None — vendor says it is not an auto-digitizer [V][8] | Bitmap is a backdrop to draw over; Magic Wand makes outlines [V][8] | None | SVG imports as objects from Level 2 [V][8] |
| Ink/Stitch | Vector only [V][9] | Inkscape Trace Bitmap; simplify the image first, then Simplify paths and run Cleanup Document, because tracing leaves fragments [V][9] | None [V][9] | Yes (it is the only path) |
| Brother PE-Design 11 | Auto Punch (raster) and a separate vector import (WMF/EMF/SVG) — both exist as manual sections [V][10] | Section contents not retrievable [U] | [U] | [U] |
| Janome Digitizer MBX | [U] — no vendor manual reachable | [U] | [U] | [U] |
| SewArt (S&S Computing) | [U] — vendor page 404; third-party listings only | [U] | [U] | [U] |

Already in the repo: `docs/hatch-manual-teardown-2026-08-08.md` §4.2–4.3 covers
the Hatch 300 DPI checklist and the block-until-processed behaviour.
`docs/ember-technical-teardown-2026-08-08.md` §5 shows Ember's auto-digitize is
a server-side raster trace with no resolution guidance.
`docs/masters-teardown-2026-08-01.md` covers the patent record. PRODUCT.md has
nothing on resolution.

The one direct quote, Hatch on vector input: "With vector artwork, there is no
need for preparation." [4]

## 2. Decorators and services

- **Printful** — 300 DPI; PNG or vector PDF, not JPG; text 0.25 in tall and
  0.05 in thick; lines 0.05 in; up to 6 colours from 15 threads. Under-size
  lines become a run stitch; textures and gradients are simplified.
  Digitization is a one-time fee per design. [V][11] (blog; the help-centre
  article returned 403 — [U]).
- **Printify** — 1200 x 1200 px at 300 DPI (1200 x 720 for caps); PNG or JPEG;
  lowercase 0.25 in, uppercase 0.3 in; text under 0.18 in is resized or
  removed; lines 0.05 in; 6 colours. [V][12]
- **Gelato** — PNG at 150 DPI minimum, or vector PDF; text 0.25 in; thickness
  0.05 in, thinner becomes run stitch; non-compliant art may be modified or
  rejected. [V][13]
- **Custom Ink** — text 0.25 in, lines 0.05 in; its artists simplify, remove or
  enlarge text that is too small. No resolution or format stated on the
  page. [V][14]
- **Digit-IT** — prefers AI/EPS/CDR, then the largest PNG/JPG available; names
  low-res art for fine lettering as a cause of delay. No numbers. [V][15]
- **Qdigitizing** — says resolution cannot be added to a raster and that
  enlarging one means a full hand redraw. [V][16] (FAQ page 404 — accepted
  formats [U].)
- **ZDigitizing** — small or blurry PNGs need manual redrawing because
  auto-trace follows the damaged pixel edges. [V][17]
- **Ignition Drawing** — sells vector redraw (priced per draw time) and
  digitizing as separate products [V][18]. The hand-drawn, no-auto-trace claim
  was seen only in a search snippet [U].
- **Absolute Digitizing** — no artwork-requirements page found. [U]

## (a) Stated minimums

| Who | Min resolution | Min text height | Min line width | Preferred format | Source |
|---|---|---|---|---|---|
| Wilcom ES / Hatch | 300 DPI (11.8 px/mm) | — | shapes >= 1 sq mm (ES) | PNG, no AA; vector | [3][5] |
| Printful | 300 DPI | 0.25 in (6.35 mm) | 0.05 in (1.27 mm) | PNG / vector PDF | [11] |
| Printify | 1200 px, 300 DPI | 0.25 in lower, 0.3 in upper; <0.18 in removed | 0.05 in | PNG / JPEG | [12] |
| Gelato | 150 DPI (5.9 px/mm) | 0.25 in | 0.05 in | PNG / vector PDF | [13] |
| Custom Ink | not stated | 0.25 in | 0.05 in | not stated | [14] |
| Digit-IT | "largest you have" | not stated | not stated | AI / EPS / CDR | [15] |
| Ink/Stitch, StitchArtist, Pulse | none | — | — | vector | [7][8][9] |
| EMB-Bot today | warns under 4 px/mm (~102 DPI) | — | — | — | `digitizer_core/config.py` |

## (b) What the industry does about low-res

- **Sets the bar high and says so up front.** 300 DPI is the common number;
  150 DPI is the lowest published floor found. Nobody publishes a floor near
  46 DPI.
- **Sends the user back to the source.** Wilcom and Hatch say to regenerate the
  bitmap from the vector original rather than fix a poor one.
- **Treats vector as the clean lane.** Vector input skips bitmap prep in
  Wilcom, Hatch and Pulse, and is the only input in Ink/Stitch.
- **Simplifies rather than sharpens.** Decorators publish feature minimums
  (6.35 mm text, 1.27 mm lines) and convert, enlarge or delete what is under
  them. The file's resolution is not rescued; the design is reduced.
- **Uses a human redraw when the file is too poor.** Services say auto-trace
  copies damaged edges and that a redraw is the fix, sold as a paid step.

No vendor found claims an algorithmic fix for under-resolved art. That agrees
with the head-to-head.

## (c) Three options for EMB-Bot

**1. Tiered resolution message at upload, not one warning.** Today there is a
single line at 4 px/mm. Proposal: under 3 px/mm, say the file will sew soft and
ask for a larger file or a vector; 3–6 px/mm, proceed with a note; 6 px/mm and
up, no message; name 300 DPI as the target. Evidence: Gelato's floor is
5.9 px/mm [13]; Wilcom, Hatch, Printful and Printify all name 300 DPI
[3][5][11][12]; our own measurement shows curve fitting earns nothing at 1.8
and starts paying at 3. The band edges are a proposal, not an industry
standard.

**2. Vector-first upload path.** Put SVG/PDF ahead of raster in the upload
copy and route it straight past stages 0–4. Evidence: every professional tool
with a vector lane skips preparation on it [1][4][7]; Printful and Gelato take
vector PDF [11][13]; Digit-IT ranks vector first [15]. The repo has an SVG
parser (`src/svgimport.js`, PR #802) but **nothing calls it** — an uploaded SVG
is still rasterised and traced from pixels, so this is a build, not
positioning. The wiring is mapped in
`docs/low-res-outline-sparknotes-2026-10-10.md`.

**3. "What will change" preview with feature minimums.** Before stitching,
flag text under about 6.35 mm, strokes under about 1.27 mm, and edges that
came from an under-resolved source, and show what will be thinned, merged or
dropped. Evidence: Printify and Custom Ink tell customers small text gets
resized or removed [12][14]; Printful and Gelato say thin lines become run
stitch [11][13]; Wilcom sets a 1 sq mm minimum shape [3]. A paid redraw
hand-off is the service-side equivalent [16][17][18] and could sit behind the
same flag.

## Could not verify

Printful and Printify help-centre articles (403); Qdigitizing FAQ (404);
Absolute Digitizing; Ignition Drawing's no-auto-trace claim; Brother PE-Design
Auto Punch and vector-import detail (table of contents only); Janome Digitizer;
SewArt/SewWhat; Tajima DG16 specifically (only the DG/ML 14 page was read).

## Sources

1. https://docs.wilcom.com/embroiderystudio/27/en/OnlineHelp/Automatic/automatic/automatic-10.htm
2. https://docs.wilcom.com/embroiderystudio/27/en/OnlineHelp/Automatic/automatic/automatic-4.htm
3. https://docs.wilcom.com/embroiderystudio/28/en/OnlineHelp/Automatic/bitmaps/bitmaps-2.htm
4. https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Automatic/auto-digitize/Convert_vector_objects_in_Embroidery_Mode.htm
5. https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Artwork/artwork/Image_quality.htm
6. https://softwarehelp.bernina.com/en/MainHelp/PART_Automatic/image_processing/image_processing-3.htm
7. https://dgml14.pulsemicro.com/pulse-products-powerofvectors.htm
8. https://embrilliance.com/stitchartist
9. https://inkstitch.org/docs/workflow/
10. http://support.brother.com/g/s/hf/htmldoc/ped/im/ped11/en/PED11_EN/
11. https://www.printful.com/blog/how-to-design-a-logo-for-embroidery
12. https://printify.com/guide/embroidery-guide/
13. https://support.gelato.com/en/articles/8996221-embroidery-design-guidelines
14. https://www.customink.com/help_center/embroidery-design-tips
15. https://knowledgebase.digit-it.com/knowledge-base/article/preparing-artwork-for-digitizing
16. https://www.qdigitizing.com/blog/what-is-or-is-not-vector-art/
17. https://zdigitizing.com/how-to-convert-a-png-to-a-vector-file-format/
18. https://ignitiondrawing.com/
