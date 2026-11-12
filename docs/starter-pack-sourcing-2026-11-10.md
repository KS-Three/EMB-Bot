# Starter design pack: where the designs can come from (2026-11-10)

Decision doc for `PRODUCT.md` launch item 3, "Curated starter design pack
(12-24 licensed designs via DST import)", not started when this was written.
**Since then (status note, 2026-11-12): Kent ruled on it 2026-11-10 and the 12
designs are on main in `app/public/starter/` (PR #1382,
[`starter-pack-2026-11-10.md`](starter-pack-2026-11-10.md)); the Studio surface
is not built. `PRODUCT.md` row 3 carries the live status.** Research only:
no stitch file or artwork was downloaded into this repo by this doc's PR. Everything here is
world-readable (the repo is public), so no third-party design is named by file.

**Bar to clear.** Item 7 pulled every font whose grant was uncertain, including
one that had an adapter's permission email plus full OFL text, because nothing
confirmed the grant covered commercial embroidery distribution. All 13
CC-BY-SA fonts were pulled on Kent's 2026-08-04 call. A design enters the pack
only with a written grant that plainly covers redistribution inside a paid app.
No user-upload gallery (PRODUCT non-goals: copyright and moderation exposure
declined).

**How the pack would load.** `src/dstimport.js` (`decodeDST`) reads a `.dst`
into the internal stitch model, so a pack made of DST files needs no new
importer. Routes (d) and (e) need no stitch-file licence at all, since the
output is EMB-Bot's own.

Verification key: **V** = read on the primary page this session; **U** =
unverified (page blocked, snippet only, or not found).

## Summary

| Source | Cost | Effort | Redistribute in a paid app? | Verdict |
|---|---|---|---|---|
| (a) Open stitch files | $0 | high (hunt) | almost never clean | no usable supply found |
| (b) Commercial libraries | not published | medium, plus negotiation | default terms say no | needs a written deal |
| (c) Commission a digitizer | about $120-$2,400 for 12-24 | low | yes, if contract assigns rights | good, with paper |
| (d) Own digitizer on CC0 vectors | $0 | medium | yes, if art is truly CC0 | best |
| (e) Kent draws in Studio | $0, his time | high per design | yes | fills gaps only |

## (a) Openly licensed stitch files

**Delivers.** Almost nothing usable. Findings:

- **Ink/Stitch the program is GPL-3.0** (V, [LICENSE](https://github.com/inkstitch/inkstitch/blob/main/LICENSE)). That covers the software, not a design library. DOCTRINE already holds Ink/Stitch to clean-room, concept-level use.
- **Ink/Stitch font repo**: "Please see the LICENSE files for usage rights", so licensing is per item, not blanket (search snippet of [embroidery-fonts](https://github.com/inkstitch/embroidery-fonts), U; DOCTRINE already rules there is no external font supply).
- **Community design collections** (C3D2): the README says "Please refer to the individual directories for their licenses", and a recent commit is titled "rm blanket license" (V, [embroidery-collections](https://gitea.c3d2.de/c3d2/embroidery-collections)). No single grant exists; each directory needs its own check. Not usable until read directory by directory.
- **Emoji embroidery project (University of Geneva)**: the pages disagree. One snippet says CC BY-SA 4.0, another CC BY-NC-SA (U, [edutechwiki](https://edutechwiki.unige.ch/en/Emoji_Embroidery_Project); the [tecfa listing](https://tecfa.unige.ch/guides/embroid/emoji) states no licence, V). Both readings are ShareAlike; one is also NC. Out.
- **Wikimedia Commons**: [Category:Machine embroidery](https://commons.wikimedia.org/wiki/Category:Machine_embroidery) holds 92 files, listed as JPG/PNG/video, no DST/PES seen (V). Commons footer: "Files are available under licenses specified on their description page." A search for `.dst` files found none (U: index incomplete). Commons hosts photos of embroidery, not stitch files.
- **archive.org**: hosts scans of public-domain pattern books, not machine files; no DST/PES collection found (U). Useful only as art source for (d).
- **"Free embroidery file" sites**: the one read in full is free for personal use only. Its FAQ: commercial use "costs EUR 100, covers up to 5,000 embroidered items", and "The digital embroidery files may not be shared, uploaded, redistributed, transferred, or resold." (V, [FAQ](https://free-embroidery-files.com/faq/)). That is the "personal use only" trap: free to download is not free to bundle.

**Licence terms.** None found that is both open and covers machine stitch files.
**Cost.** $0. **Effort.** High: per-file provenance work for a tiny yield.
**Risk.** ShareAlike and NC on the emoji set; "free" files with a no-redistribution clause; unknown provenance of uploads.
**Catch.** Public domain applies to the artwork, not to a digitizer's stitch file of it. A stitch file is the digitizer's own creative work, so a vintage-looking design does not make the file free.

## (b) Commercial design libraries

**Delivers.** Polished files in DST/PES etc.
**Licence terms.** Default terms are for stitching goods, not shipping files:

- Embroidery Library / Urban Threads bars "Selling, sharing, gifting, transferring, distributing ... or re-selling" of files, edited files included, and bars reusing designs in other media. No redistribution licence is offered; the only route is to email support about wholesale (V, [policy](https://urbanthreads.com/page/licensing)).
- Creative Fabrica: embroidery purchases carry a commercial licence "to make items to sell" with no cap on sales (search snippet of the [category page](https://www.creativefabrica.com/embroidery/), U). Its licence pages ([single sales](https://creativefabrica.com/de/single-sales-license), [subscription](https://creativefabrica.com/de/subscription-license)) returned 403, so the redistribution and "embed in an app" clauses are **unverified**. Third-party summaries say new products cannot be made after cancelling a subscription (U).
- Small shops commonly cap a standard licence (one shop: 250 end products per design) and sell extended licences separately, price on request (search snippet of [one shop's policy](https://payhip.com/SweetLittleClipart/blog/blog/licensing-use-policy), U).

**Does it permit commercial bundling in a paid app?** No by default. Every default licence read or summarised covers stitching physical goods, and those read in full forbid giving files to anyone else. A pack ships files to every customer, which is redistribution.
**Cost.** No published redistribution price found anywhere (U). Expect a negotiated quote per design.
**Effort.** Medium: outreach, a signed grant, then keeping the signature on file.
**Risk.** The grant must say "embedded in a paid desktop app, redistributed to end users, who may stitch and sell the result". Anything softer repeats the `milli_marif_bold` situation. Also check the vendor owns the art (many designs are digitized from licensed clipart).
**Catch.** A subscription or one-time commercial licence tempts, but it permits the buyer to stitch, not to hand files onward.

## (c) Commission a digitizer

**Delivers.** Original DST files made to spec, with Kent's own art or CC0 art as the brief.
**Licence terms.** Set by contract. The pricing page read does not say who owns the digitized file (V, [zdigitizing](https://zdigitizing.com/logo-digitizing-for-embroidery-a-guide-to-pricing/)). So ownership is not a given: the contract must assign copyright, or grant an exclusive, perpetual, sublicensable licence, and must warrant the digitizer did not copy another file.
**Cost.** Published ranges: $10-$100 per design, simple clip-art logos about $40-$50, intricate $75+, turnaround 2-7 days (V, same page; other guides say $10-$75, U). For 12-24 designs at $25-$60 each, about $300-$1,440; the full range $120-$2,400.
**Effort.** Low for Kent: write a brief, review proofs, stitch-test. Contract drafting is the real work.
**Risk.** A freelancer reselling the same file to others; a freelancer starting from copyrighted art; an assignment that is only verbal. ShareAlike/NC do not apply if the contract is clean.
**Catch.** Cheap per file, but a weak file ships under EMB-Bot's name; the starter pack is the first thing a customer opens, so stitch-test every file.

## (d) EMB-Bot digitizes CC0 / public-domain vector art itself

**Delivers.** A pack made by the product's own pipeline, which doubles as a showcase. No stitch-file licence is involved, because the stitch file is EMB-Bot's own output. Only the artwork licence matters.
**Licence terms (art sources).**

- **Openclipart**: artwork is released under the "Creative Commons Zero 1.0 Public Domain License", with "unlimited commercial use", modification allowed, attribution not required (V, [share page](https://openclipart.org/share)). **Catch on the same page:** clipart tagged `pd_issue` has a possible provenance doubt under investigation. A CC0 label on upload is the uploader's claim.
- **CC0 itself** does not touch other rights: "In no way are the patent or trademark rights of any person affected by CC0", and publicity/privacy rights survive (V, [deed](https://creativecommons.org/publicdomain/zero/1.0/)). So no brand marks, no character look-alikes, no real people.
- **Twemoji** graphics are CC-BY 4.0 (V, [repo](https://github.com/twitter/twemoji)): attribution required, so it adds a credit per design; the repo looks stale (v14.0 noted).
- **Fluent UI Emoji** code licence is MIT (V, [LICENSE](https://github.com/microsoft/fluentui-emoji/blob/main/LICENSE)); I did not read per-asset terms, so treat as U until read.
- **Avoid**: CC-BY-SA art (ShareAlike, same bar as the fonts), anything "free for personal use", and Wikimedia files not marked CC0 or PD (the Commons footer defers to each file page).
- Scans of old pattern books on Commons or archive.org can be art sources if the item page marks them public domain (U per item).

**Cost.** $0. **Effort.** Medium: pick art, simplify to a stitchable silhouette, digitize, stitch-test, repair. Keep a provenance note per design (URL, licence, access date) in the repo, like a font sidecar.
**Risk.** Mislabelled "CC0" art (`pd_issue`); trademarks hidden in generic-looking art; a CC0 file that is itself a copy of someone's copyrighted work. Mitigation: allowlist sources, record the licence page URL per design, skip anything doubtful.
**Catch.** Auto-digitized quality varies (see `MASTER_SCOPE.md` for current defects); the pack becomes a standing quality bar, and a design the pipeline handles badly needs hand repair in the Studio.

## (e) Kent draws the designs in the Studio

**Delivers.** Original designs from the manual draw and shapes tools (`manualShapes.js`, `shapePresets.js`; circle, rect, heart, star already exist).
**Licence terms.** Kent owns his work; no third party.
**Cost.** $0, his time. **Effort.** High per design, and it competes with product work.
**Risk.** Almost none legally. Quality ceiling is his drawing speed.
**Catch.** Does not scale past a handful; best for geometric and lettering items, and it dogfoods the tools.

## Ranked recommendation

1. **(d) with a CC0-only allowlist, topped up by (e).** Zero licence cost, no ShareAlike or NC exposure, matches the font bar, and the pack demonstrates the product. Catch: record provenance per design and skip `pd_issue`.
2. **(c) commission, with a signed assignment.** About $300-$1,440 for 12-24 files. Use for designs the pipeline handles badly. Catch: ownership is unspecified by default.
3. **(b) commercial library bundle licence.** Only if a vendor signs a redistribution grant; none publishes one. Catch: unpriced, slow, default terms forbid it.
4. **(a) open stitch files.** Not recommended: no clean supply found.

**Decision Kent must make.** Approve route (d) plus (e) under this allowlist: CC0 or explicitly public-domain art only; no CC-BY-SA, NC, ND, "personal use" or unknown terms; attribution licences (CC-BY, Twemoji) excluded unless he accepts a credits screen. Then pick launch pack size (12 or 24) and whether to spend roughly $300-$1,440 on (c) for the hard designs.

## Not verified

- Creative Fabrica licence text (403); whether any library sells a redistribution licence, and its price.
- Any `.dst` file on Wikimedia Commons or archive.org (searches found none; index coverage unknown).
- C3D2 per-directory licences; the Emoji Embroidery Project's real licence.
- Fluent UI Emoji per-asset terms.
- Freelance marketplace prices (Fiverr, Etsy); figures above come from digitizing-shop pages.
- Kimberbell's licensing article (HTTP 429).
- Not legal advice; the chosen grant text should be read by a lawyer, as already flagged for the pulled fonts.

## Kent's ruling (2026-11-10)

Asked as three multiple-choice questions, answered in order:

1. **Route:** "CC0 art + our digitizer (Recommended)", i.e. option (d) topped up by (e). No commissioning and no commercial library.
2. **Art sources:** "Strict CC0 / PD-mark (Recommended)". Only art whose own page shows CC0 or a Public Domain Mark, with the author and link logged per design. Allowed sources: Wikimedia Commons PD/CC0, Openclipart minus anything flagged `pd_issue`, and CC0 icon packs. Excluded: CC-BY (no credits screen), CC-BY-SA, NC, ND, "personal use", unknown terms, and every logo or brand mark (CC0 does not clear trademarks).
3. **Size:** "12 designs (Recommended)" for launch.
