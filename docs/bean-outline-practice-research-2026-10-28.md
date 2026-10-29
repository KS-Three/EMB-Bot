# Bean stitch and outline/border practice in professional digitizing

Research note, 2026-10-28. Web sources only; nothing here was measured on EMB-Bot
files. Each claim links to its source. Numbers marked **(unsourced)** are not from
any source. **(snippet)** means the number came from a search-result excerpt and the
page itself was not opened; check it before relying on it.

## Decision rules (summary)

1. **Use line weight to pick the stitch.** Use a run for lines under about 0.8 mm
   ([Campbell](https://graphics-pro.com/?p=109085)). Use satin from about 1.0 mm,
   or 0.8 mm for an experienced digitizer, up to 8–10 mm
   ([Bruce](https://graphics-pro.com/feature/stitching-guidelines-for-digitizing/)).
   Past about 10–12 mm, use split satin or fill
   ([Wilcom](https://wilcom.com/resources/blog/mastering-basic-stitch-types-satin-stitch-and-tatami-stitch)).
   A bean/triple run is for a line too heavy for a single run but not right for
   satin ([Ignition glossary](https://blog.ignitiondrawing.com/embroidery-glossary-stitch-types/print/),
   which is a vendor blog).
2. **Bean is a look, not just a weight.** It reads as hand-stitched, with heavy
   needle holes ([Campbell, Mr X Stitch](https://mrxstitch.com/bean-stitch/);
   [Wilcom](https://wilcom.com/resources/blog/run-stitch-outlines)). Choose it for
   redwork, hand-stitch effects, quilting, and lines that must stand out on pile.
   For a crisp corporate-logo outline, the thin single run is the usual choice
   ([Embird](https://www.embird.net/machine-embroidery-tutorials/studio-next/hw_digitize_3.htm)).
3. **Outlines are optional, not default.** Embrilliance says to use them only where
   the art needs to look crisper, and that the easiest way to avoid outline
   registration trouble "is not to use them"
   ([Embrilliance](https://embrilliance.com/Help/Platform%20Win%201165/registration.htm)).
4. **Follow the art.** If the art has outlines, use those and do not generate a
   second set. Wilcom's auto-digitizer says to drop the art's outline colour before
   switching on generated outlines
   ([Wilcom ES27](https://docs.wilcom.com/embroiderystudio/27/en/OnlineHelp/Automatic/automatic/automatic-10.htm)).
5. **Close gaps between butting fills with overlap or pull compensation, not an
   outline.** Experienced digitizers overlap objects as they digitize
   ([Hatch](https://hatchembroidery.com/resources/blog/what-you-need-to-know-about-pull-compensation));
   Ink/Stitch has fill "expand" for the same job
   ([Ink/Stitch fill](https://inkstitch.org/docs/stitches/fill-stitch/)).
6. **When an outline must hide registration, use a wider or offset stitch and inset
   it.** Backstitch or stemstitch hides misregistration better than a single run,
   bean holds better than a single or double run, and the outline is inset about
   half a needle width into the shape
   ([Embrilliance](https://embrilliance.com/Help/Platform%20Win%201165/registration.htm)).
   On caps, a wider border column gives more tolerance
   ([Freeman, ASI](https://members.asicentral.com/news/how-to/february-2018/edit-away-your-embroidery-issues/)).
7. **Gradients are built from interleaved, overlapping light-density layers at one
   stitch angle.** No source describes outlining the steps
   ([Bruce, Graphics Pro](https://graphics-pro.com/feature/creating-color-gradients-with-thread/)).
   Decorators tell customers to avoid gradients altogether
   ([Hegel, ASI](https://members.asicentral.com/news/how-to/july-2022/how-to-turn-your-logos-into-embroidery/);
   [Stadium](https://intercom.help/bystadium/en-us/articles/17177932-embroidery-guidelines)).
8. **An outline usually sews right after its own object.** It does not wait for a
   pass at the end of the design. Wilcom inserts generated outlines "immediately
   after" each object
   ([Wilcom ES27](https://docs.wilcom.com/embroiderystudio/27/en/OnlineHelp/Modifying/productivity/productivity-11.htm)).
   On caps, each letter gets its border right after its fill
   ([Freeman](https://members.asicentral.com/news/how-to/february-2018/edit-away-your-embroidery-issues/)),
   and each element is finished in all its colours before the next
   ([Melco](https://melco.com/cap-embroidery-with-melco-embroidery-machines/)).
9. **Travel goes inside or under later stitching.** In Ink/Stitch that is the
   fill's underpath ([Ink/Stitch](https://inkstitch.org/docs/stitches/fill-stitch/)).
   Wilcom describes connecting runs hidden beneath another object
   ([Wilcom ProductBlog](https://productblog.wilcom.com/?p=28148), snippet; the
   page returned 404 when fetched).

## 1. Bean stitch: what it is, uses, limits

**Construction.** Each stitch is sewn three or more times, always an odd number, on
the same needle holes, so the line keeps moving forward
([Campbell, Graphics Pro 2020](https://graphics-pro.com/?p=109085);
[Campbell, Mr X Stitch](https://mrxstitch.com/bean-stitch/)). Ink/Stitch's
"bean stitch number of repeats" works per stitch: 0 is a normal stitch, 1 is
forward-back-forward (three passes), and a pattern like `0 1` alternates single
and triple stitches
([Ink/Stitch running stitch](https://inkstitch.org/docs/stitches/running-stitch/)).
This is separate from the path-level "repeats" setting, which walks the whole path
back and forth. Wilcom's Triple Run repeats each stitch three times by default, and
Run Count changes that
([Wilcom ES28](https://docs.wilcom.com/embroiderystudio/28/en/OnlineHelp/Digitizing/stitches/stitches-5.htm)).
Embrilliance allows repeats up to 9
([Embrilliance Run Objects](https://embrilliance.com/Help/Platform%20Mac%201170/runobjects.htm)).
Melco calls it a walk "bean" that lays down three lengths of thread per stitch
([Melco DesignShop](https://www.melco-service.com/docs/DS_V9_090309/Digi_walk.htm)).

**How it reads.** The stitches are thick and bow out in the middle, the needle
holes are exaggerated, and the result looks hand-worked
([Campbell, Mr X Stitch](https://mrxstitch.com/bean-stitch/)). Wilcom notes that
the needle holes are "emphasized" because they land in the same place
([Wilcom blog 2025](https://wilcom.com/resources/blog/run-stitch-outlines)).
Campbell's quote: "Bean stitch is great for making lines that look like they were
stitched by hand with large, loose floss."
([Mr X Stitch](https://mrxstitch.com/bean-stitch/)).

**Uses.**
- **Visible-thread looks:** hand-stitch effects, dashed or "stitched" lines,
  homespun texture ([Campbell](https://graphics-pro.com/?p=109085)).
- **Thicker outlines:** Melco gives "a thicker outline around an element" as the
  bean's use ([Melco](https://www.melco-service.com/docs/DS_V9_090309/Digi_walk.htm)).
  Wilcom recommends triple run for "bold outlines"
  ([Wilcom blog](https://wilcom.com/resources/blog/run-stitch-outlines)).
- **Pile fabrics:** a heavier stitch "stands out better against a pile fabric"
  ([Embrilliance](https://embrilliance.com/Help/Platform%20Mac%201170/runobjects.htm)).
- **Redwork and quilting:** Goodall prefers bean over a double run for registration
  and for less looping, because it compresses the layers once and evenly
  ([Goodall, LindeeG blog, 2011/2019](https://lindeegembroidery.com/blog/item/the-truth-about-redwork-designs-2)).
- **Thin is the norm:** Ink/Stitch notes that a single repeated run is usually too
  thin, which is why running-stitch work is usually done as bean
  ([Ink/Stitch](https://inkstitch.org/docs/stitches/running-stitch/)).

**Stitch length.**
- **Wilcom, run in general:** about 1.8 mm on sharp curves, about 4.0 mm for a
  hand-made look
  ([Wilcom ES26](https://docs.wilcom.com/embroiderystudio/26/en/OnlineHelp/Digitizing/stitches/Stitch_length_settings.htm)).
- **Ink/Stitch:** the redwork template defaults to 2.5 mm
  ([Ink/Stitch template source](https://git.push-f.com/inkstitch/tree/templates/redwork.xml?h=nix), snippet).
- **Bernina redwork tutorial:** triple stitch at 4.0 mm, with another example at
  3.5 mm
  ([Bernina PDF](https://www.bernina.com/en-CA/Experience-CA/Sewing/Serger-projects/USA-ca/Software-ca/Embroidery-Software-6---Creating-Redwork-Outline-Designs/BERNINA-EmbSoftware6-RedworkOutlineDesigns-ca.pdf), snippet).
- **Electric Quilt:** bean edge length 3.0
  ([EQ support](https://support.electricquilt.com/?p=1532), snippet).
- **Embrilliance:** use a longer stitch when you add more bean repeats, so the
  fabric can take the tension
  ([Embrilliance](https://embrilliance.com/Help/Platform%20Mac%201170/runobjects.htm)).
- Goodall keeps the length fixed and shortens it only in intricate areas, with no
  number given ([Goodall](https://lindeegembroidery.com/blog/item/the-truth-about-redwork-designs-2)).
- Taken together, about 2.5–4 mm is the documented range. Any single "standard"
  bean length is **unsourced**.

**Limits.**
- **Path direction:** a bean runs from one end of a path to the other. A path that
  must start and end at the same point becomes a single run out and a bean back
  ([Goodall](https://lindeegembroidery.com/blog/item/the-truth-about-redwork-designs-2)).
- **Tight curves:** they turn angular when every pass hits the same holes. Campbell
  offsets the penetrations on the second pass to round them
  ([Campbell, Embrilliance 2025](https://embrilliance.com/archives/241247), written
  about double runs).
- **Thread on fabric:** light thread on dark fabric can make fine run lines look
  broken. Dark on light reads crisp
  ([Campbell](https://graphics-pro.com/?p=109085);
  [Corporate Casuals](https://www.corporatecasuals.com/articles/Digitizing_Custom_Embroidered_Designs_from_Graphics.asp)).
- **Puckering:** no first-party source gives a bean-specific pucker limit. Hooping
  and stabilizer are the general causes
  ([Madeira troubleshooting](https://www.madeirausa.com/services/troubleshooting/fabric-puckering/)).
- **Unsourced:** a minimum feature size or maximum length for bean.

**Bean or satin?** No source gives a mm crossover. Campbell's run limit is about
0.8 mm, and satin starts at about 1.0 mm (Bruce) or more than 1.5 mm (Ink/Stitch,
Embrilliance; see section 5). That puts bean in the band where a line is drawn
thin but must read heavier than a single run. Treating that band as about
0.8–1.5 mm is **unsourced** inference.

## 2. Outline or border on filled shapes: when to add, and which kind

- **The art has an outline.** Reproduce it. Wilcom's auto-digitizer can use the
  art's own outlines or generate them, but not both
  ([Wilcom ES27](https://docs.wilcom.com/embroiderystudio/27/en/OnlineHelp/Automatic/automatic/automatic-10.htm)).
  Embird's logo tutorial snaps the outline to the fill nodes and calls the thin
  running stitch "generally the most effective choice for corporate logos"
  ([Embird](https://www.embird.net/machine-embroidery-tutorials/studio-next/hw_digitize_3.htm)).
- **Crispness.** Embrilliance treats crisper edges as the only good reason for an
  outline
  ([Embrilliance](https://embrilliance.com/Help/Platform%20Win%201165/registration.htm)).
- **Registration or edge tolerance.**
  - A wider border column hides fill-to-border shift on caps
    ([Freeman, ASI 2018](https://members.asicentral.com/news/how-to/february-2018/edit-away-your-embroidery-issues/)).
  - An offset backstitch or stemstitch hides registration errors better than a run
    ([Embrilliance](https://embrilliance.com/Help/Platform%20Win%201165/registration.htm)).
  - No primary source said outright that a satin border is added to cover ragged
    fill edges. The common claim that it does is **unsourced** here.
- **Satin or run outline.** Satin outlines give "thicker borders or columns of even
  thickness"
  ([Bernina help](https://softwarehelp.bernina.com/en/MainHelp/PART_Digitizing/stitches/stitches-9.htm);
  [Wilcom](https://docs.wilcom.com/embroiderystudio/28/en/OnlineHelp/Digitizing/stitches/stitches-3.htm)).
  Run outlines suit fine detail, triple run suits bold outlines, and backstitch
  suits delicate curves
  ([Wilcom blog](https://wilcom.com/resources/blog/run-stitch-outlines);
  [Wilcom decorative outlines](https://docs.wilcom.com/embroiderystudio/28/en/OnlineHelp/Digitizing/stitches/stitches-17.htm)).
  Stemstitch can edge satin or motif fills (same page).
- **Large shapes.** Fill the body and put a satin border on the edge, instead of
  using wide satin. Satin over about 5–6 mm is fragile, by the wiki's rule
  ([EduTechWiki Ink/Stitch tutorial, 2018](https://EduTechWiki.unige.ch/en/InkStitch_-_from_satin_columns_to_fills_with_satin_borders),
  a university teaching wiki and secondary).
- **Small shapes.** Satin borders stop working on very small pieces, where a run
  outline is the alternative
  ([Embroidery Legacy](https://embroiderylegacy.com/?p=410309), a commercial blog
  and weak). No mm threshold is sourced.
- **Appliqué.** The satin cover stitch is the default edge. It can be switched to
  zigzag, E stitch or raised satin, or turned off. A negative offset moves it
  inward relative to the tack
  ([Wilcom applique](https://docs.wilcom.com/embroiderystudio/27/en/OnlineHelp/Mixed/applique/applique-10.htm)).
  The tackdown cannot be wider than the cover stitch
  ([Bernina applique](https://softwarehelp.bernina.com/en/MainHelp/PART_Special/applique/applique-8.htm), snippet).
  Patches end with a heavy satin or merrow border that seals the edge
  ([Fiverr listing](https://www.fiverr.com/adonis_ghl/do-custom-patch-embroidery-digitizing-badge-and-jacket-back-dst-pes),
  very weak).
- **Fabric.**
  - Fleece: raise pull compensation and density, and use knockdown under small
    lettering and details
    ([Impressions 2019](https://impressionsmagazine.com/process-technique/tips-for-digitizing-and-embroidering-difficult-fabrics/27324/), snippet).
  - Pique: use double zigzag underlay so satin edges stay on top (same source).
  - Pile in general: bean reads better than single run
    ([Embrilliance](https://embrilliance.com/Help/Platform%20Mac%201170/runobjects.htm)).
  - Heavy knits get denser satin borders (mySewnet density 2–3) and light fabrics
    lighter ones (5–6)
    ([mySewnet Satin Line](https://softwarehelp.mysewnet.com/MSW/100/Digitizing/Topics/Satin_Line.htm)).
  - Wilcom offsets can build the knockdown under a group of objects
    ([Wilcom blog 2019](https://wilcom.com/resources/blog/outlines-and-offsets)).
- **Garment contrast.** Wilcom tells logo digitizers to put text and outline on
  separate needles, so the outline colour can change per garment
  ([Wilcom blog](https://wilcom.com/resources/blog/run-stitch-outlines)). No source
  says to *add* an outline because of garment contrast. That claim is
  **unsourced**.

## 3. When NOT to outline

- **No outline in the art.** No primary source states a "don't add what's not in
  the art" rule in those words. Two sources come close:
  - Embrilliance limits outlines to where crispness matters and calls skipping them
    the easiest fix
    ([Embrilliance](https://embrilliance.com/Help/Platform%20Win%201165/registration.htm)).
  - Wilcom warns that generated outlines plus outlines already in the art double up
    ([Wilcom ES27](https://docs.wilcom.com/embroiderystudio/27/en/OnlineHelp/Automatic/automatic/automatic-10.htm)).

  The decorator side: a digitizer renders "the sense of a design, not every line"
  ([Hegel, ASI 2022](https://members.asicentral.com/news/how-to/july-2022/how-to-turn-your-logos-into-embroidery/)),
  and lines thinner than the satin minimum become a single run or are dropped
  ([Custom Ink](https://www.customink.com/help_center/embroidery-design-tips)).
  EMB-Bot's own census of pro files agrees: the pro borders what the art outlines
  (memory `border-from-outline-2026-10-24.md`, kappa 0.76, n 588). That is a
  measurement in this repo, not a web source.
- **Adjacent fills that butt.** Overlap them and add pull compensation instead
  ([Hatch](https://hatchembroidery.com/resources/blog/what-you-need-to-know-about-pull-compensation);
  [Wilcom](https://wilcom.com/resources/blog/push-and-pull-compensation);
  [Ink/Stitch expand](https://inkstitch.org/docs/stitches/fill-stitch/)). Satin
  over a neighbouring fill also gets a little extra overlap
  ([EduTechWiki](https://EduTechWiki.unige.ch/en/InkStitch_-_from_satin_columns_to_fills_with_satin_borders)).
  Wilcom's Advanced Outlines offers three ways to handle touching objects
  ([Wilcom ES27](https://docs.wilcom.com/embroiderystudio/27/en/OnlineHelp/Modifying/productivity/productivity-11.htm);
  [Wilcom blog](https://wilcom.com/resources/blog/outlines-and-offsets)):
  - **Individual:** every object gets a full outline.
  - **Common:** one outline around the merged group.
  - **Trimmed:** hidden overlaps removed.

  So "per colour region or around the silhouette" is a setting, not a fixed rule.
  No source says which one pros pick by default.
- **Gradients.** No stitched outlines appear in the gradient method. The steps
  blend by interleaving
  ([Bruce](https://graphics-pro.com/feature/creating-color-gradients-with-thread/)).
- **Small shapes and text.** Small text under about 4 mm, or under 1/4 in by other
  decorators' rules, is enlarged rather than detailed
  ([Hegel](https://members.asicentral.com/news/how-to/july-2022/how-to-turn-your-logos-into-embroidery/);
  [Corporate Casuals](https://www.corporatecasuals.com/articles/Digitizing_Custom_Embroidered_Designs_from_Graphics.asp)).
  Stadium tells customers to avoid thin outlines under 1 mm
  ([Stadium](https://intercom.help/bystadium/en-us/articles/17177932-embroidery-guidelines)),
  which is customer-facing advice. No source gives a size below which a filled
  shape loses its outline. That number is **unsourced**.

## 4. A multicolour gradient icon (Instagram-style ring, circle and dot)

**No source covers this case directly.** What the sources support:

- **The glyph is line art, not a filled shape with an outline.** The rounded-square
  ring, circle and dot are drawn as strokes and solids, so the parts are sewn as
  themselves. A ring stroke at satin width is a satin, and the dot is a satin or
  fill depending on size (rules in section 5). Nothing in the art is an outline
  around a filled region, so rule 4 says to add none. This is inference from rules
  3–4.
- **The gradient.** Bruce's method blends across stepped bands without outlining
  them:
  - divide the space into steps of 1/4 density;
  - layer light-density fills, each offset about 0.4 mm so stripes do not form;
  - keep one stitch angle across the whole gradient, perpendicular to the direction
    of the colour change;
  - use fewer threads than the art's bands, close in tone.

  ([Bruce, Graphics Pro 2019](https://graphics-pro.com/feature/creating-color-gradients-with-thread/)).
  Wilcom automates the same idea with Color Blending / Multi Blend (accordion
  spacing across two or more colours)
  ([Wilcom ES27 color blends](https://docs.wilcom.com/embroiderystudio/27/en/OnlineHelp/Decorative/specialty/specialty-17.htm)).
  Outlining each band would draw the steps the blend is meant to hide. That is an
  inference; no source states it.
- **Low-cost route.** If the gradient is not central to the design, drop it or
  approximate it with two or more solid colours
  ([Corporate Casuals](https://www.corporatecasuals.com/articles/Digitizing_Custom_Embroidered_Designs_from_Graphics.asp)).
  Decorators steer customers away from gradients
  ([Hegel](https://members.asicentral.com/news/how-to/july-2022/how-to-turn-your-logos-into-embroidery/);
  [Stadium](https://intercom.help/bystadium/en-us/articles/17177932-embroidery-guidelines);
  [Custom Ink](https://www.customink.com/help_center/embroidery-design-tips)).
- **If an outline is wanted anyway,** Wilcom's "Common" overlap method puts one
  outline around the merged silhouette instead of one per band
  ([Wilcom ES27](https://docs.wilcom.com/embroiderystudio/27/en/OnlineHelp/Modifying/productivity/productivity-11.htm)).
  The choice is a setting, not documented practice.

## 5. Typical widths and thresholds

| Quantity | Value | Source |
|---|---|---|
| Run stitch for lines under | ~0.8 mm | [Campbell 2020](https://graphics-pro.com/?p=109085) |
| Satin column minimum | 1.0 mm (0.8 with experience) | [Bruce 2019](https://graphics-pro.com/feature/stitching-guidelines-for-digitizing/) |
| Satin minimum (stroke-converted) | > 1.5 mm | [Ink/Stitch satin](https://inkstitch.org/docs/stitches/satin-column/) |
| Narrow satin that may pucker | ~1 mm; 1.5 mm preferred | [Embrilliance tapering](https://embrilliance.com/Help/Platform%20Mac%201146/satincolumntaperinglevel2.htm) (snippet) |
| Satin minimum line (decorator) | 0.05 in ≈ 1.27 mm; thinner → run or dropped | [Custom Ink](https://www.customink.com/help_center/embroidery-design-tips) |
| Satin maximum | 8–10 mm | [Bruce 2019](https://graphics-pro.com/feature/stitching-guidelines-for-digitizing/) |
| Satin maximum | ~12 ideal max, stay ≤10, 15 risks snags; auto-split 7 mm | [Wilcom 2024](https://wilcom.com/resources/blog/mastering-basic-stitch-types-satin-stitch-and-tatami-stitch) |
| Satin maximum (teaching wiki) | 5–6 mm | [EduTechWiki](https://EduTechWiki.unige.ch/en/InkStitch_-_from_satin_columns_to_fills_with_satin_borders) |
| Satin border width range | 1–12 mm; default 2 mm (Satin Border) or 4 mm (Satin Line, one version) | [mySewnet Satin Border](https://softwarehelp.mysewnet.com/MSM/100/Embroidery/Topics/Satin_Border1.htm); [mySewnet Satin Line](https://softwarehelp.mysewnet.com/MSW/100/Digitizing/Topics/Satin_Line.htm) |
| No edge-walk underlay below | 2 mm border width | same mySewnet pages |
| Example satin border on a fill | ~3 mm body, ~2 mm fine detail | [EduTechWiki](https://EduTechWiki.unige.ch/en/InkStitch_-_from_satin_columns_to_fills_with_satin_borders) |
| Run length on sharp curves | ~1.8 mm | [Wilcom ES26](https://docs.wilcom.com/embroiderystudio/26/en/OnlineHelp/Digitizing/stitches/Stitch_length_settings.htm) |
| Run length, hand-made look | ~4.0 mm | same |
| Bean / redwork length | 2.5 mm (Ink/Stitch default), 3.0 (EQ), 3.5–4.0 (Bernina) | see section 1 (snippets) |
| Outline inset into shape | ~½ needle width | [Embrilliance](https://embrilliance.com/Help/Platform%20Win%201165/registration.htm) |
| Gradient layer offset | ~0.4 mm, 1/4-density steps | [Bruce 2019](https://graphics-pro.com/feature/creating-color-gradients-with-thread/) |
| Text minimum height | 4 mm ([Hegel](https://members.asicentral.com/news/how-to/july-2022/how-to-turn-your-logos-into-embroidery/)); 1/4 in ([Custom Ink](https://www.customink.com/help_center/embroidery-design-tips), [Corporate Casuals](https://www.corporatecasuals.com/articles/Digitizing_Custom_Embroidered_Designs_from_Graphics.asp)) | — |
| Satin border width by element size | **unsourced**: no source scales border width with shape size | — |
| Bean ↔ satin crossover | **unsourced**: inferred 0.8–1.5 mm band | — |

## 6. Sequencing

- **Outline right after its object.** Wilcom's generated outlines go "immediately
  after" their object in the sequence
  ([Wilcom ES27](https://docs.wilcom.com/embroiderystudio/27/en/OnlineHelp/Modifying/productivity/productivity-11.htm)).
  Embird builds the outline after, and snapped to, the fills
  ([Embird](https://www.embird.net/machine-embroidery-tutorials/studio-next/hw_digitize_3.htm)).
- **Caps.** Freeman's fix for misregistration is to fill a letter, border it, then
  move to the next letter: more colour changes, less drift
  ([Freeman, ASI 2018](https://members.asicentral.com/news/how-to/february-2018/edit-away-your-embroidery-issues/)).
  Melco says to finish each free-standing element in all its colours before the
  next, and to work from the centre out
  ([Melco](https://melco.com/cap-embroidery-with-melco-embroidery-machines/)).
- **Nested shapes.** Sew outside-in; inner-first left gaps in Embrilliance's
  example. An outline can overlap a neighbour's edge run as an anchor
  ([Embrilliance](https://embrilliance.com/Help/Platform%20Win%201165/registration.htm)).
- **Order.** Large before small
  ([Bruce](https://graphics-pro.com/feature/stitching-guidelines-for-digitizing/)),
  and one side to the other to avoid trims and travel
  ([Wilcom tutorial](https://wilcom.com/resources/blog/simple-embroidery-digitizing-tutorial), snippet).
- **Hidden travel.**
  - Ink/Stitch's underpath runs travel inside the fill rather than around its edge
    ([Ink/Stitch](https://inkstitch.org/docs/stitches/fill-stitch/)).
  - Wilcom's QA article describes a connecting run under another object that
    joins same-colour parts without a trim
    ([Wilcom ProductBlog](https://productblog.wilcom.com/?p=28148), snippet; 404
    when fetched).
  - Goodall's bean paths are planned so they do not retrace or jump over finished
    work
    ([Goodall](https://lindeegembroidery.com/blog/item/the-truth-about-redwork-designs-2)).
- **Lettering arcs last on caps.** Melco says to sew lettering lines and arches as
  the last elements to avoid distortion
  ([Melco](https://melco.com/cap-embroidery-with-melco-embroidery-machines/)).

## Conflicts and weak evidence

- **"Outlines last" or "outline right after its fill"?** The sources describe
  outline-after-own-fill (Wilcom, Freeman, Melco's finish-each-element rule). Melco
  also sends lettering arcs last. No primary source states "all outlines at the end
  of the design". The common belief that they go last is **unsourced** in what I
  found.
- **Satin maximum width disagrees:** 5–6 mm (EduTechWiki), 8–10 (Bruce), 10–12
  (Wilcom).
- **Satin minimum disagrees:** 0.8–1.0 mm (Bruce), 1.27 mm (Custom Ink), more than
  1.5 mm (Ink/Stitch, Embrilliance).
- **mySewnet's satin default** is 2 mm on one page and 4 mm on another version's
  page.
- **Ink/Stitch bean repeat docs** changed between versions: an older or translated
  page says repeat 2 gives "quintuple" stitches, the current English page says
  "twice". Go by the current page.
- **Bruce's small-lettering figure.** "0.6 mm (0.25 in)" in
  [Bruce 2019](https://graphics-pro.com/feature/stitching-guidelines-for-digitizing/)
  is internally inconsistent, since 0.25 in is 6.35 mm. Likely a typo; do not
  quote it.
- **Attribution of the gradient article.** It is by Alexandria Bruce, though some
  search snippets credit Campbell's images. It is cited here as Bruce.
- **Gaps.** No source covers satin border width by shape size, a minimum shape size
  for an outline, or bean puckering on knits. Those claims remain **unsourced**.
- **Weak sources:** the Fiverr listing, the Embroidery Legacy blog, the Ignition
  glossary and the Stadium/Custom Ink customer guidelines. They are used only where
  nothing stronger exists, and are flagged inline.

## Sources and trust

| Source | Type | Trust |
|---|---|---|
| [Wilcom EmbroideryStudio help](https://docs.wilcom.com/) (ES26–28) | Vendor manual | High for what the tool does; it rarely states practice |
| [Wilcom blog](https://wilcom.com/resources/blog/run-stitch-outlines) (run outlines 2025, satin/tatami 2024, outlines/offsets 2019, pull comp) | Vendor technical blog | Medium-high; gives numbers, no author named |
| [Wilcom ProductBlog QA](https://productblog.wilcom.com/?p=28148) | Vendor blog | Snippet only (404 when fetched) |
| [Hatch blog, pull compensation 2024](https://hatchembroidery.com/resources/blog/what-you-need-to-know-about-pull-compensation) | Vendor (Wilcom consumer line) | Medium-high |
| [Ink/Stitch docs](https://inkstitch.org/docs/stitches/running-stitch/) (running, satin, fill) | Open-source manual | High for parameters |
| [Embrilliance help](https://embrilliance.com/Help/Platform%20Win%201165/registration.htm) (registration, run objects) | Vendor manual with practitioner advice | High; registration page is real practice |
| [Embird tutorial](https://www.embird.net/machine-embroidery-tutorials/studio-next/hw_digitize_3.htm) | Vendor tutorial | Medium-high |
| [Bernina help](https://softwarehelp.bernina.com/en/MainHelp/PART_Digitizing/stitches/stitches-9.htm) / [mySewnet help](https://softwarehelp.mysewnet.com/MSW/100/Digitizing/Topics/Satin_Line.htm) | Vendor manuals | High for defaults |
| [Melco cap guide](https://melco.com/cap-embroidery-with-melco-embroidery-machines/), [Melco DesignShop](https://www.melco-service.com/docs/DS_V9_090309/Digi_walk.htm) | Machine vendor | High for cap sequencing |
| Erich Campbell: [Graphics Pro 2020](https://graphics-pro.com/?p=109085), [Mr X Stitch](https://mrxstitch.com/bean-stitch/), [Embrilliance 2025](https://embrilliance.com/archives/241247) | Named practitioner (commercial digitizer since 2000) | High |
| Alexandria Bruce, Graphics Pro: [guidelines 2019](https://graphics-pro.com/feature/stitching-guidelines-for-digitizing/), [gradients 2019](https://graphics-pro.com/feature/creating-color-gradients-with-thread/) | Trade-magazine technical column | Medium-high; one internal typo |
| [Steve Freeman, ASI 2018](https://members.asicentral.com/news/how-to/february-2018/edit-away-your-embroidery-issues/) | Trade-magazine practitioner | Medium-high; a single worked case |
| [Theresa Hegel, ASI 2022](https://members.asicentral.com/news/how-to/july-2022/how-to-turn-your-logos-into-embroidery/) | Trade journalism quoting practitioners | Medium |
| [Lindee Goodall, LindeeG blog](https://lindeegembroidery.com/blog/item/the-truth-about-redwork-designs-2) | Named practitioner/educator | High for redwork |
| [Impressions 2019](https://impressionsmagazine.com/process-technique/tips-for-digitizing-and-embroidering-difficult-fabrics/27324/) | Trade magazine | Medium; snippet only (403 when fetched) |
| [EduTechWiki (Univ. Geneva)](https://EduTechWiki.unige.ch/en/InkStitch_-_from_satin_columns_to_fills_with_satin_borders) | Teaching wiki | Medium-low; hobby-level |
| [Corporate Casuals](https://www.corporatecasuals.com/articles/Digitizing_Custom_Embroidered_Designs_from_Graphics.asp), [Custom Ink](https://www.customink.com/help_center/embroidery-design-tips), [Stadium](https://intercom.help/bystadium/en-us/articles/17177932-embroidery-guidelines) | Decorator customer guidelines | Low-medium; customer-facing art rules, not digitizing practice |
| [Madeira troubleshooting](https://www.madeirausa.com/services/troubleshooting/fabric-puckering/) | Thread maker | Medium; general pucker causes only |
| [Ignition glossary](https://blog.ignitiondrawing.com/embroidery-glossary-stitch-types/print/), [Embroidery Legacy](https://embroiderylegacy.com/?p=410309), [Fiverr listing](https://www.fiverr.com/adonis_ghl/do-custom-patch-embroidery-digitizing-badge-and-jacket-back-dst-pes) | Commercial blogs and listings | Low; flagged inline |

Not found: Gunold or Isacord technical guides on outlines, Pulse or Tajima DG/ML
manuals, Brother PE-Design help on outlines, and John Deer / *Digitizing Made Easy*
text. Searches returned nothing usable for any of them.
