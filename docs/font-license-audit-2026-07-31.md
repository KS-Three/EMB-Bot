# Font License Audit — Launch Gate Report

**Product:** EMB-Bot font library (69 shipped fonts) · **Date:** 2026-07-31 · **Gate:** font-license compliance before first paid sale

---

## 1. Verdict

**Not launch-compliant today, but fixable in roughly two focused days of work plus one lawyer consult.** The three biggest blockers: **(1) The full-license-text gap** — all 51 OFL fonts currently ship with only a 100–400 character summary embedded in the binary, and the OFL requires the full license text and copyright notice to accompany every copy ("each copy contains the above copyright notice and this license"); 48 of 69 fonts have no license file on disk anywhere, and the build's copy step doesn't ship the 21 that do exist. **(2) Four pull-or-verify decisions** — milli_marif_bold (ad-hoc French email permission, standing decision is pull), tt_directors and tt_masters (OFL claim rests only on an aggregator listing while the TypeType foundry sells these families commercially), and dejavufont (labeled CC-BY-SA but upstream DejaVu is under a Bitstream Vera-derived license). **(3) The CC-BY-SA ShareAlike question** — whether the 14 CC-BY-SA-derived `.embf` binaries, and the stitch files customers generate from them, must themselves carry a BY-SA license. That one needs a lawyer; everything else is build-script and data work.

---

## 2. Per-font verdicts

**How to read "Action":** *OK* means the font is compliant **once the global license-file fix in section 3 ships** — no font is compliant today without it. *Fix attribution* means the shipped attribution string is itself defective (truncated, name dropped, notice missing) and needs a per-font correction on top of the global fix. All 12 CC-BY-SA-4.0 and 2 CC-BY-SA-2.5 fonts are additionally subject to the lawyer question in section 5.

| Key | License | Creator | Action | Evidence |
|---|---|---|---|---|
| milli_marif_bold | SEE-LICENSE-FILE | Found — M.-F. BRIS (adapter); Jérémy Landes (original, Millimetre) | **PULL** (see §4) | sidecar LICENSE.txt (5,528 B) |
| tt_directors | OFL-1.1 | Found — Jovanny Lemonad (TypeType); digitizer unknown | **Needs decision** — OFL claim traceable only to 1001fonts; TypeType sells TT Directors commercially on MyFonts | [1001fonts listing](https://www.1001fonts.com/tt-directors-demo-font.html) |
| tt_masters | OFL-1.1 | Found — Jovanny Lemonad (TypeType); digitizer unknown | **Needs decision** — same aggregator-only OFL sourcing; residual takedown exposure | [LICENSE](https://raw.githubusercontent.com/inkstitch/embroidery-fonts/main/src/tt_masters/LICENSE) |
| dejavufont | CC-BY-SA-4.0 | Partial — @Augusa (handle); DejaVu Serif authors | **Needs decision** — upstream DejaVu is Bitstream Vera-derived, not CC-BY-SA; label questionable | manifest + DejaVu upstream license |
| alchemy | OFL-1.1 | Found — Ariel Martín Pérez / Velvetyne (Ouroboros); digitizer unnamed | Fix attribution — dangling fragment; add Ouroboros copyright + Reserved Font Name notice | [LICENSE](https://github.com/inkstitch/embroidery-fonts/blob/main/src/alchemy/LICENSE) |
| amitaclo | OFL-1.1 | Found — Claudette Venneugues-Aminot | Fix attribution — truncated mid-derivative-clause (Amita) | sidecar LICENSE.txt (4,686 B) |
| apex_simple_AGS | OFL-1.1 | Found — Françoise Lapierre Baillet; orig. Linux Libertine, Philipp H. Poll | Fix attribution — name dropped by bare-CR line-break bug ("adapted for Ink/Stitch by ") | [LICENSE](https://raw.githubusercontent.com/inkstitch/embroidery-fonts/main/src/apex_simple_AGS/LICENSE) |
| apex_simple_small_AGS | OFL-1.1 | Found — same as apex_simple_AGS | Fix attribution — same truncation defect | [LICENSE](https://raw.githubusercontent.com/inkstitch/embroidery-fonts/main/src/apex_simple_small_AGS/LICENSE) |
| auberge_marif | OFL-1.1 | Found — @Marie-Françoise BRIS | Fix attribution — strip personal email from user-facing credit; keep full notice in LICENSE file; RFN "Grand Hotel" notice must ship | manifest + sidecar |
| barstitch_bold | OFL-1.1 | Partial — orig. Barlow Bold, Jeremy Tribby; digitizer anonymous even upstream | Fix attribution — add "Copyright 2017 The Barlow Project Authors" | [LICENSE](https://raw.githubusercontent.com/inkstitch/embroidery-fonts/main/src/barstitch_bold/LICENSE) |
| barstitch_regular | OFL-1.1 | Found — Claudine Peyrat (digitizer); Barlow, Jeremy Tribby | Fix attribution — add digitizer + Barlow copyright notice | [repo](https://github.com/inkstitch/embroidery-fonts/tree/main/src/barstitch_regular) |
| barstitch_textured | OFL-1.1 | Found — Claudine Peyrat (digitizer); Barlow Bold, Jeremy Tribby | Fix attribution — same as barstitch_regular | [repo](https://github.com/inkstitch/embroidery-fonts/tree/main/src/barstitch_textured) |
| bathaus_FI | OFL-1.1 | Found — six-person adapter team | Fix attribution — truncated at 200 chars mid-clause | manifest |
| bathaus_FI_Small | OFL-1.1 | Found — six-person adapter team | Fix attribution — same truncation | manifest |
| bluenesia_satin | CC-BY-SA-4.0 | Found — Karen J. Cravens / Silver Seams | Fix attribution — truncated; archive a copy of the PR #1686 permission grant locally | [PR #1686](https://github.com/inkstitch/inkstitch/pull/1686) |
| caesarus_SC_FI | OFL-1.1 | Found — six-person adapter team | Fix attribution — truncated (largest blob, 411 chars) | manifest |
| digory_doodles_bean | OFL-1.1 | Partial — "Tina" (first name only); orig. Digory Doodles (OFL) | Fix attribution — truncated mid-derivative-clause | manifest |
| emilio_20_bold | CC-BY-SA-4.0 | Found — Célia Imbert Sabater; orig. Adien Gunarta | Fix attribution — truncated at "ORIGINAL FONT DOWNLOAD:…" | sidecar LICENSE.txt |
| geneva_rounded | CC-BY-SA-2.5 | Found — Daniel K. Schneider (TECFA); orig. Hershey Sans, Dr. A. V. Hershey (1967) | Fix attribution — credit Schneider + ship required Hershey acknowledgement; grandfathered (2.5 not in ALLOWED_LICENSES) | [LICENSE](https://github.com/inkstitch/embroidery-fonts/blob/main/src/geneva_rounded/LICENSE) |
| geneva_simple | CC-BY-SA-2.5 | Found — same as geneva_rounded | Fix attribution — same; sidecar already carries Hershey terms | [LICENSE](https://github.com/inkstitch/embroidery-fonts/blob/main/src/geneva_simple/LICENSE) |
| initials_medium | OFL-1.1 | Found — orig. Sortefax, gluk (Grzegorz Luk); digitizer unnamed | Fix attribution — add gluk 2014 copyright notice; fix trailing-space name | [LICENSE](https://github.com/inkstitch/embroidery-fonts/blob/main/src/initials_medium/LICENSE) |
| initials_XL | OFL-1.1 | Found — orig. Sortefax, gluk; digitizer unnamed | Fix attribution — add gluk notice; never rename back to reserved name "Sortefax" | [LICENSE](https://github.com/inkstitch/embroidery-fonts/blob/main/src/initials_XL/LICENSE) |
| mam_script | OFL-1.1 | Found — Marie-Ange Martin; orig. Kaushan Script (OFL, RFN) | Fix attribution — truncated mid-derivative-clause | manifest |
| medium_font | OFL-1.1 | Found — Lex Neva (Ink/Stitch author) | Fix attribution — ends mid-sentence at a colon | sidecar LICENSE.txt (4,334 B, full OFL) |
| mimosa_large | OFL-1.1 | Found — orig. Nose Transport (2022), Nose AG; digitizer unnamed | Fix attribution — dangling fragment; add Nose AG copyright notice | [LICENSE](https://github.com/inkstitch/embroidery-fonts/blob/main/src/mimosa_large/LICENSE) |
| mimosa_medium | OFL-1.1 | Found — same as mimosa_large | Fix attribution — same | [LICENSE](https://github.com/inkstitch/embroidery-fonts/blob/main/src/mimosa_medium/LICENSE) |
| neon | OFL-1.1 | Found — orig. Sportrop, gluk (1997–2008); digitizer unnamed | Fix attribution — dangling fragment; add gluk copyright line | [LICENSE](https://raw.githubusercontent.com/inkstitch/embroidery-fonts/main/src/neon/LICENSE) |
| pacificlo | OFL-1.1 | Found — Claudette Venneugues-Aminot; orig. Pacifico | Fix attribution — truncated mid-derivative-clause | manifest |
| pixel10 | OFL-1.1 | Found — orig. Jersey 10, Sarah Cadigan-Fried (Soft Type Project); digitizer unnamed | Fix attribution — dangling fragment; add 2023 Soft Type Project notice | [upstream repo](https://github.com/scfried/soft-type-jersey) |
| venezia | OFL-1.1 | Found — orig. Andada Pro, Carolina Giovagnoli (Huerta Tipografica); digitizer unnamed | Fix attribution — dangling fragment drops the OFL-required copyright notice | [LICENSE](https://raw.githubusercontent.com/inkstitch/embroidery-fonts/main/src/venezia/LICENSE) |
| venezia_small | OFL-1.1 | Found — same as venezia | Fix attribution — same | [LICENSE](https://raw.githubusercontent.com/inkstitch/embroidery-fonts/main/src/venezia_small/LICENSE) |
| allegria55 | OFL-1.1 | Found — orig. Euphoria Script, Sabrina Mariela Lopez / Typesenses | OK — ship the 2012 Typesenses notice via LICENSE file | [LICENSE](https://github.com/inkstitch/embroidery-fonts/blob/main/src/allegria55/LICENSE) |
| ambigue | OFL-1.1 | Found — orig. Ambidexter, Egor Belozerov / Paratype | OK — ship Paratype notice; adding designer name is safer but not required | [LICENSE](https://github.com/inkstitch/embroidery-fonts/blob/main/src/ambigue/LICENSE) |
| amitaclo_small | OFL-1.1 | Found — Claudette Venneugues-Aminot | OK | manifest |
| apex_lake | CC-BY-SA-4.0 | Found — Françoise Lapierre Baillet | OK | manifest |
| auberge_small | OFL-1.1 | Found — @Marie-Françoise BRIS | OK | manifest |
| aventurina | CC-BY-SA-4.0 | Found — Sandrine Ratkoff Rojnoff | OK | manifest |
| caffeine_KOR | OFL-1.1 | Found — Corinne Renaud | OK | manifest |
| caffeine_tiny | OFL-1.1 | Found — Corinne Renaud | OK | manifest |
| cats | OFL-1.1 | Found — orig. Cat Font (BioStim, CC0); digitizer Claudine Peyrat | OK — original is CC0, no attribution required | [repo](https://github.com/inkstitch/embroidery-fonts/tree/main/src/cats) |
| cherryforinkstitch | CC-BY-SA-4.0 | Found — six-person adapter team | OK | manifest |
| cherryforkaalleen | CC-BY-SA-4.0 | Found — six-person adapter team | OK | manifest |
| chicken_little | OFL-1.1 | Found — Corinne Renaud | OK | manifest |
| chicken_little_small | OFL-1.1 | Found — Corinne Renaud | OK | manifest |
| chicken_scratch | OFL-1.1 | Found — safire3002 (pseudonym); orig. Reenie Beanie (RFN, renamed — compliant) | OK | manifest |
| cogs_KOR | CC-BY-4.0 | Found — Corinne Renaud | OK — only CC-BY (non-SA) font; URI-style attribution suffices | manifest |
| cooper_marif | OFL-1.1 | Found — @Marie-Françoise BRIS | OK | manifest |
| emilio_20 | CC-BY-SA-4.0 | Found — Célia Imbert Sabater; orig. Adien Gunarta ("with permission") | OK — sidecar credits original author | sidecar LICENSE.txt (463 B) |
| emilio_20_simple | CC-BY-SA-4.0 | Found — Célia Imbert Sabater; frame removed by Karen Cravens | OK | manifest |
| emilio_20_simple_small | CC-BY-SA-4.0 | Found — same | OK | manifest |
| excalibur_KOR | CC0 | Found — Corinne Renaud | OK — note: CC0 label derived from "public domain" wording, not a literal CC0 grant | manifest |
| excalibur_small | CC0 | Found — Corinne Renaud | OK — same labeling note | manifest |
| gingo200 | CC-BY-SA-4.0 | Found — Sorm Prak (original creation for Ink/Stitch) | OK | manifest |
| glacial_tiny | OFL-1.1 | Found — Françoise Lapierre Baillet | OK | manifest |
| kum_tsoan_AGS | OFL-1.1 | Found — Françoise Lapierre Baillet | OK | manifest |
| magnolia_KOR | OFL-1.1 | Found — Corinne Renaud | OK | manifest |
| magnolia_small | OFL-1.1 | Found — Corinne Renaud | OK | manifest |
| magnolia_tamed | OFL-1.1 | Found — Corinne Renaud | OK | manifest |
| manga_impact | OFL-1.1 | Found — Célia Imbert Sabater; orig. Shojumaru (RFN, renamed — compliant) | OK | manifest |
| marifenda | OFL-1.1 | Found — Marie-Françoise BRIS | OK | manifest |
| monicha | CC-BY-SA-4.0 | Found — Sandrine Ratkoff Rojnoff | OK | manifest |
| pacificlo_tiny | OFL-1.1 | Found — Claudette Venneugues-Aminot | OK | manifest |
| pisankris | OFL-1.1 | Found — Françoise Lapierre Baillet | OK | manifest |
| roaring_twenties_KOR | OFL-1.1 | Found — Corinne Renaud | OK | manifest |
| roaring_twenties_KOR_small | OFL-1.1 | Found — Corinne Renaud | OK | manifest |
| roman_ags | OFL-1.1 | Found — Françoise Lapierre Baillet | OK | manifest |
| small_font | OFL-1.1 | Found — Lex Neva (Ink/Stitch author) | OK — no sidecar on disk; needs LICENSE reconstruction with the rest (§3) | manifest |
| stebor_AGS | OFL-1.1 | Found — Françoise Lapierre Baillet | OK | manifest |
| violin_serif | OFL-1.1 | Found — safire3002 (pseudonym); orig. Instrument Serif (RFN, renamed — compliant) | OK | manifest |

**Census check:** 69 fonts = 1 PULL + 3 needs-decision + 27 fix-attribution + 38 OK. Licenses: OFL-1.1 ×51, CC-BY-SA-4.0 ×12, CC-BY-SA-2.5 ×2, CC-BY-4.0 ×1, CC0 ×2, SEE-LICENSE-FILE ×1. (A 70th font, `precious`, is GPL-3.0 and is already correctly excluded by the build.)

---

## 3. The full-license-text gap

This is the single largest compliance failure, and it affects every font at once.

**What the licenses actually require:**

- **OFL-1.1 (51 fonts):** the full license text and the copyright notice must accompany **every copy**. The license says copies must contain "the above copyright notice and this license," deliverable as "stand-alone text files, human-readable headers or in the appropriate machine-readable metadata fields." **A link is not sufficient.**
- **CC-BY-SA 4.0 (12 fonts):** a URI is enough — "include the text of, or the URI or hyperlink to, this Public License" — plus creator credit, copyright notice, and an indication that the work was modified.
- **CC-BY-SA 2.5 (2 fonts):** "include a copy of, or the Uniform Resource Identifier for, this License with every copy" — URI suffices; plus author name and derivative credit. The Geneva fonts also carry the 1967 Hershey acknowledgement requirement.
- **CC-BY 4.0 (1 font), CC0 (2 fonts):** URI suffices / no conditions.

**What ships today:** each `.embf` binary embeds only a 104–411 character summary. `app/scripts/copy-engine.mjs` copies the manifest, binaries, and previews — **not** the `*.LICENSE.txt` files. Zero license files exist under `app/public/fonts/` or `app/dist/`. And only 21 of 69 fonts have a `LICENSE.txt` in `src/fonts/` at all — the other 48 have no full text or copyright notice on disk anywhere. **Every OFL font is therefore currently shipped in breach of OFL condition 2.**

**Minimal shipping fix:**

1. Reconstruct the 48 missing `LICENSE.txt` files from the upstream Ink/Stitch embroidery-fonts repo (most already exist locally under `scratch_ink/<key>/LICENSE`).
2. Add `*.LICENSE.txt` to the copy list in `copy-engine.mjs` so they're served at `/fonts/<key>.LICENSE.txt`. This alone satisfies OFL's "stand-alone text files" option — full texts do **not** need to be embedded in the binaries for app use.
3. Extend `credits.js` so each font's credit shows: name, author/copyright line, an "adapted for embroidery / compiled to .embf" modification note (required by CC §3(a)(1)(B)), and a link to the **local** LICENSE.txt. A local copy satisfies every license type uniformly.
4. **Bare-binary caveat:** `credits.js` exposes a direct `.embf` download. A bare OFL binary carrying only the summary arguably travels without "this license." Either embed the full OFL text + notice in the `.embf` metadata `license` field (OFL explicitly blesses machine-readable metadata; ~4.4 KB per font), or stop offering bare downloads and bundle the LICENSE with any export.
5. While in there, fix the attribution-string defects (truncation, dropped names, mojibake like "Marie-FranÃ§oise") — the manifest attribution is the user-visible notice.

**Reserved Font Names:** both the Ink/Stitch adaptation and the `.embf` compile are "Modified Versions" under the OFL, but the upstream renames (Grand Hotel→Auberge, Kaushan Script→MAM Script, Reenie Beanie→Chicken Scratch, Shojumaru→Manga Impact, Instrument Serif→Violin Serif, Linux Libertine→Apex Simple AGS) already satisfy condition 3. Two obligations persist: keep the "with Reserved Font Name X" declarations in the shipped notices, and never surface an RFN as the primary font name in the UI. Provenance mentions in credits ("based on Grand Hotel") are fine.

---

## 4. milli_marif_bold — standing decision

**Standing decision: PULL from the launch build unless written commercial permission is in hand.** That decision stands.

What the research found: the sidecar LICENSE.txt (5,528 B) opens with two French permission emails from Jérémy Landes (designer of Millimetre, StudioTriple) — "Vous avez ma bénédiction" ("you have my blessing") — followed by the **complete OFL-1.1 text**. The font is labeled SEE-LICENSE-FILE only because the 180-char summary embedded in the JSON contains just the email opening with no OFL keyword, so the build's license detector falls through. SEE-LICENSE-FILE is not in ALLOWED_LICENSES; the font ships today only because it's grandfathered.

Two paths forward, owner's call:

- **Cheap and safe (recommended for launch):** pull it now. One line in the build exclusions. Revisit later.
- **Keep it:** email Jérémy Landes for a one-line English confirmation that the OFL-1.1 grant covers commercial embroidery distribution, archive the reply next to the sidecar, and relabel the font OFL-1.1 in the build. The existing emails plus the appended full OFL text arguably already constitute this, but "arguably" is not what you want under a hard gate — get the confirmation or ship without the font.

---

## 5. The CC-BY-SA question for the lawyer (one-hour consult)

**Scope:** 12 CC-BY-SA-4.0 fonts + 2 CC-BY-SA-2.5 fonts (the two Geneva fonts).

**The question:** Is a compiled `.embf` stitch-data binary — quantized, delta-encoded satin-path coordinates mechanically derived from a CC-BY-SA-licensed vector font — itself "Adapted Material" (CC-BY-SA 4.0 §1(a)) or a "Derivative Work" (2.5 §1(a)) that must be licensed BY-SA?

**The hinge:** 4.0 §1(a) defines Adapted Material as material modified "in a manner requiring permission under the Copyright and Similar Rights held by the Licensor." If the `.embf` takes only unprotectable elements, ShareAlike never attaches. If it's a protected reproduction or adaptation, §3(b) forces the whole binary under BY-SA.

**Sub-issues to put on the table:**

1. Does stitch-path data derived from the Ink/Stitch vector sources copy protectable font software/vector data, or only unprotectable letterform shapes? (US: typeface designs uncopyrightable — Eltra Corp. v. Ringer, 37 CFR 202.1(e) — but digital font files are protected as data/programs — Adobe v. Southern Software. UK/DE protect typefaces as such.)
2. Is mechanical format conversion a mere reproduction (attribution duties only, license unchanged) or an adaptation (ShareAlike attaches)? Note 4.0's format-shifting carve-out applies only to the technical-modification cases in §2(a)(4).
3. **The commercial exposure:** if `.embf` is BY-SA, do the DST/PES stitch files customers generate — and physical sew-outs — become further Adapted Material? Does BY-SA propagate onto customer deliverables?
4. How does the answer vary by jurisdiction, given web distribution?

**Why launch doesn't wait on this:** either way — reproduction or adaptation — distribution triggers the attribution and notice duties in section 3, so those fixes are required regardless. Only the license labeling of the `.embf` files and downstream propagation ride on the lawyer's answer. If the answer is bad, worst case is relabeling 14 binaries BY-SA and adding a customer-facing note — or pulling 14 fonts.

---

## 6. Action checklist (in order)

| # | Action | Size |
|---|---|---|
| 1 | Pull `milli_marif_bold` from the build (add to exclusions in `tools/build-embf.mjs`), or send the permission-confirmation email to Jérémy Landes and pull until reply | 15 min |
| 2 | Decide `tt_directors` / `tt_masters`: pull both (recommended — 51 other OFL fonts remain), or commission foundry-grade license verification | 15 min to pull / hours to verify |
| 3 | Decide `dejavufont`: pull, or research the actual DejaVu (Bitstream Vera) terms and relabel correctly | 15 min to pull / ~1 h to research |
| 4 | Fix attribution extraction in `build-embf.mjs`: handle bare-CR line breaks (restores the apex_simple names), stop mid-sentence truncation, fix mojibake | 1–2 h |
| 5 | Reconstruct the 48 missing `LICENSE.txt` files from `scratch_ink/<key>/LICENSE` and the upstream inkstitch/embroidery-fonts repo | 2–4 h |
| 6 | Add `*.LICENSE.txt` to the copy list in `app/scripts/copy-engine.mjs` | 15 min |
| 7 | Extend `app/src/lib/credits.js`: author/copyright line, modification note, link to local LICENSE.txt per font | 1–2 h |
| 8 | Close the bare-binary hole: embed full license text in `.embf` metadata via `src/fontbin.js`, or remove the direct `binHref` download | 1–3 h |
| 9 | Apply the 27 per-font attribution fixes from the table (mostly fall out of items 4–5; hand-check the six-team fonts, auberge_marif email removal, Geneva Hershey acknowledgement) | 1–2 h |
| 10 | Verify no Reserved Font Name appears as a primary font name in UI/manifest/metadata (Sortefax, Nose Transport, Ouroboros, Grand Hotel, Kaushan Script, Reenie Beanie, Shojumaru, Instrument Serif, Linux Libertine) | 30 min |
| 11 | Book the one-hour lawyer consult; send section 5 of this report as the brief | 30 min prep + 1 h consult |
| 12 | Rebuild, decode a sample of `.embf` binaries to confirm notices, click through credits screen, final pass | 1 h |

**Total build/data work: roughly 8–15 hours.** Items 1–3 are the gate for *which* fonts ship; items 4–9 are the gate for *whether anything* ships; item 11 determines labeling of the 14 CC-BY-SA fonts and can run in parallel — but get the consult booked before first dollar.