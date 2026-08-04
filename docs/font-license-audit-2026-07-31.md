# Font License Audit — Launch Gate Report

**Product:** EMB-Bot font library (69 shipped fonts) · **Date:** 2026-07-31 · **Gate:** font-license compliance before first paid sale

---

## 1. Verdict

**Not launch-compliant today, but fixable in roughly two focused days of work plus one lawyer consult.** The three biggest blockers: **(1) The full-license-text gap** — all 51 OFL fonts currently ship with only a 100–400 character summary embedded in the binary, and the OFL requires the full license text and copyright notice to accompany every copy ("each copy contains the above copyright notice and this license"); 48 of 69 fonts have no license file on disk anywhere, and the build's copy step doesn't ship the 21 that do exist. **(2) Four pull-or-verify decisions** — milli_marif_bold (ad-hoc French email permission, standing decision is pull), tt_directors and tt_masters (OFL claim rests only on an aggregator listing while the TypeType foundry sells these families commercially), and dejavufont (labeled CC-BY-SA but upstream DejaVu is under a Bitstream Vera-derived license). **(3) The CC-BY-SA ShareAlike question** — whether the 14 CC-BY-SA-derived `.embf` binaries, and the stitch files customers generate from them, must themselves carry a BY-SA license. That one needs a lawyer; everything else is build-script and data work.

---

## 2. Per-font verdicts

**How to read "Action":** *OK* means the font is compliant **once the global license-file fix in section 3 ships** — no font is compliant today without it. *Fix attribution* means the shipped attribution string is itself defective (truncated, name dropped, notice missing) and needs a per-font correction on top of the global fix. All 12 CC-BY-SA-4.0 and 2 CC-BY-SA-2.5 fonts are additionally subject to the lawyer question in section 5.

> **Update 2026-08-04 (items 4–10, 12 executed — see §8):** the global license-file fix (§3) shipped, and all 27 *Fix attribution* rows below were corrected and verified against the new manifest (scripted per-row check, 27/27 pass). The per-row Action text below is kept as written for the historical record of *what was wrong*; §8 records what was done.

| Key | License | Creator | Action | Evidence |
|---|---|---|---|---|
| milli_marif_bold | SEE-LICENSE-FILE | Found — M.-F. BRIS (adapter); Jérémy Landes (original, Millimetre) | **PULLED 2026-08-04** (see §4, §7) | sidecar LICENSE.txt (5,528 B) |
| tt_directors | OFL-1.1 | Found — Jovanny Lemonad (TypeType); digitizer unknown | **PULLED 2026-08-04** (see §7) — OFL claim traceable only to 1001fonts; TypeType sells TT Directors commercially on MyFonts | [1001fonts listing](https://www.1001fonts.com/tt-directors-demo-font.html) |
| tt_masters | OFL-1.1 | Found — Jovanny Lemonad (TypeType); digitizer unknown | **PULLED 2026-08-04** (see §7) — same aggregator-only OFL sourcing; residual takedown exposure | [LICENSE](https://raw.githubusercontent.com/inkstitch/embroidery-fonts/main/src/tt_masters/LICENSE) |
| dejavufont | CC-BY-SA-4.0 | Partial — @Augusa (handle); DejaVu Serif authors | **PULLED 2026-08-04** (see §7) — researched; upstream is confirmed Bitstream Vera Fonts License v1.00 + Arev Fonts License, not CC-BY-SA; label was wrong | manifest + DejaVu upstream license (verbatim text fetched 2026-08-04, see §7) |
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

| # | Action | Size | Status |
|---|---|---|---|
| 1 | Pull `milli_marif_bold` from the build (add to exclusions in `tools/build-embf.mjs`), or send the permission-confirmation email to Jérémy Landes and pull until reply | 15 min | **Done 2026-08-04** — pulled |
| 2 | Decide `tt_directors` / `tt_masters`: pull both (recommended — 51 other OFL fonts remain), or commission foundry-grade license verification | 15 min to pull / hours to verify | **Done 2026-08-04** — both pulled |
| 3 | Decide `dejavufont`: pull, or research the actual DejaVu (Bitstream Vera) terms and relabel correctly | 15 min to pull / ~1 h to research | **Done 2026-08-04** — researched, then pulled (see §7) |
| 4 | Fix attribution extraction in `build-embf.mjs`: handle bare-CR line breaks (restores the apex_simple names), stop mid-sentence truncation, fix mojibake | 1–2 h | **Done 2026-08-04** (see §8 — the bare-CR claim was outdated; real fix was paragraph extraction) |
| 5 | Reconstruct the 48 missing `LICENSE.txt` files from `scratch_ink/<key>/LICENSE` and the upstream inkstitch/embroidery-fonts repo | 2–4 h | **Done 2026-08-04** — 46 (not 48; items 1–3 pulled 2 of them), all from upstream |
| 6 | Add `*.LICENSE.txt` to the copy list in `app/scripts/copy-engine.mjs` | 15 min | **Done 2026-08-04** |
| 7 | Extend `app/src/lib/credits.js`: author/copyright line, modification note, link to local LICENSE.txt per font | 1–2 h | **Done 2026-08-04** |
| 8 | Close the bare-binary hole: embed full license text in `.embf` metadata via `src/fontbin.js`, or remove the direct `binHref` download | 1–3 h | **Done 2026-08-04** — embed path chosen; no `fontbin.js` change needed (see §8) |
| 9 | Apply the 27 per-font attribution fixes from the table (mostly fall out of items 4–5; hand-check the six-team fonts, auberge_marif email removal, Geneva Hershey acknowledgement) | 1–2 h | **Done 2026-08-04** — 27/27 verified by scripted check (one caveat: bluenesia screenshots, see §8) |
| 10 | Verify no Reserved Font Name appears as a primary font name in UI/manifest/metadata (Sortefax, Nose Transport, Ouroboros, Grand Hotel, Kaushan Script, Reenie Beanie, Shojumaru, Instrument Serif, Linux Libertine) | 30 min | **Done 2026-08-04** — zero hits (one benign legacy-catalog note, see §8) |
| 11 | Book the one-hour lawyer consult; send section 5 of this report as the brief | 30 min prep + 1 h consult | **Brief prepared 2026-08-04** (`docs/lawyer-brief-cc-by-sa-2026-08-04.md`, ready to send) — booking is Kent's real-world action, still open |
| 12 | Rebuild, decode a sample of `.embf` binaries to confirm notices, click through credits screen, final pass | 1 h | **Done 2026-08-04** (see §8 — data-source verification in lieu of a live click-through) |

**Total build/data work: roughly 8–15 hours.** Items 1–3 are the gate for *which* fonts ship; items 4–9 are the gate for *whether anything* ships; item 11 determines labeling of the 14 CC-BY-SA fonts and can run in parallel — but get the consult booked before first dollar. **Items 1–3 done as of 2026-08-04 — see §7. Items 4–10 and 12 done later the same day — see §8.** The only open item is 11's real-world half: the brief is written (`docs/lawyer-brief-cc-by-sa-2026-08-04.md`); Kent books the consult.

---

## 7. Items 1–3 executed — 2026-08-04

All four flagged fonts were pulled from the shipping library (`src/fonts/manifest.json` + `src/fonts/bin/*.embf` + `src/fonts/previews/*.png`), 72 → 68 fonts. `tools/build-embf.mjs` gained an explicit `PULLED` exclusion set (checked before the license-policy/grandfather logic) so a future rebuild from `scratch_ink/` won't silently resurrect any of the four — see the comment block above `PULLED` in that file for the full per-font reasoning, summarized here:

- **`milli_marif_bold` — pulled.** Standing decision (§4) enacted as written: no written commercial-use confirmation from Jérémy Landes is on file, so it ships nowhere. Source `src/fonts/milli_marif_bold.json` and its `.LICENSE.txt` sidecar were deleted (the standing-decision path this doc recommended is "revisit later," not "keep as dead weight in the tree" — reconstructable from `git log` or a fresh `scratch_ink/` clone if the confirmation email ever arrives).
- **`tt_directors` — pulled.** Took the recommended path: OFL claim was traceable only to a 1001fonts aggregator listing, no foundry-grade verification was commissioned. No static source file existed for this one (it shipped only via a prior `scratch_ink`-tier build), so removal is just the manifest entry + `.embf` + preview.
- **`tt_masters` — pulled.** Same reasoning and same aggregator-only sourcing as `tt_directors`. Unlike `tt_directors`, this one *did* have a static `src/fonts/tt_masters.json` + `.LICENSE.txt` sidecar shipped in the repo (that's how it was grandfathered) — both were deleted along with the manifest entry, `.embf`, and preview, for the same reason as `milli_marif_bold`.
- **`dejavufont` — researched, then pulled.** Did the ~1 h research option first rather than jumping straight to pull: fetched the actual upstream `LICENSE` file for this exact Ink/Stitch font (`raw.githubusercontent.com/inkstitch/embroidery-fonts/main/src/dejavufont/LICENSE`, sourced from `fontsquirrel.com/license/dejavu-serif`) and read it in full. Confirmed the audit's suspicion: the underlying font is **not** CC-BY-SA at all — it's the **Bitstream Vera Fonts License v1.00** (Bitstream, 2003) plus the **Arev Fonts License** (Tavmjong Bah, 2006). The digitizer's own file-header line ("licensed CC-BY-SA…") only speaks to their own embroidery adaptation, not the Bitstream/Arev copyright underneath, and per the actual license text: (a) neither Bitstream Vera nor Arev is in `ALLOWED_LICENSES`, and (b) both explicitly forbid selling "one or more of the Font Software typefaces… by itself" — only as part of a larger package, which is a real product-policy question (see the bare-`.embf`-download hole in item 8) that's bigger than a label fix. A shallow relabel wasn't durable either: `build-embf.mjs`'s `licenseId()` auto-detector matches the CC-BY-SA regex against the adapter's own header line before it ever reaches the real license text further down the same blob, so it would keep mislabeling this font CC-BY-SA on every future rebuild unless the detector itself is fixed. Given that, pulled it rather than ship a fix that either silently reverts or requires build-script surgery beyond this item's scope. **Revisit path:** either fix `licenseId()` to prefer a recognized license block over a bare adapter claim, or have Kent decide whether Bitstream-Vera-derived fonts should join the allowed policy set (and whether EMB-Bot's distribution model — see item 8's bare `.embf` download — is compatible with the "no standalone sale" clause).

**Known residual gap, out of scope for items 1–3 but flagged here:** `src/fonts/satin-fonts.js` (the legacy, eagerly-bundled font registry that `EMB-Bot.html` / `EMB-Bot-standalone.html` still use — see COOKBOOK.md's "Binary font library" section, which explicitly says "do not delete it" pending its own separate audit) still contains `milli_marif_bold` and `tt_masters` verbatim. This audit and its action-checklist items 1–3 are scoped to the `manifest.json`/`.embf` pipeline (`tools/build-embf.mjs`) only, per the checklist's own wording ("add to exclusions in `tools/build-embf.mjs`"), so `satin-fonts.js` was deliberately left untouched rather than silently edited around an explicit repo directive not to delete/modify that file outside its own audit. **If `EMB-Bot.html`/`EMB-Bot-standalone.html` are ever actually distributed to customers, `milli_marif_bold` and `tt_masters` are still shipping there** — this needs its own pass (`tt_directors` and `dejavufont` are *not* in `satin-fonts.js`, so those two are fully pulled everywhere).

**Verification:** `node --test` (engine suite) 265/265 → 263/263 after the pull (2 fewer — `test/embf-guard.test.js`'s per-font decoder-guard loop reads `src/fonts/*.json`, which lost `milli_marif_bold.json` and `tt_masters.json`); `cd app && npx vitest run` (Studio suite) 321/321 → 321/321 unchanged (no template or spec fixture hardcodes any of the four keys). Confirmed `src/fonts/manifest.json` keys, `src/fonts/bin/*.embf` keys, and `src/fonts/previews/*.png` keys are exactly equal sets (no orphans) both before and after.
---

## 8. Items 4–10 and 12 executed — 2026-08-04

Executed in checklist order in a session **without `scratch_ink/`** (gitignored, local-only on Kent's machine — empty in this remote checkout). That constraint shaped the mechanics: 46 of the 68 shipped fonts have no local source JSON, so a full `node tools/build-embf.mjs` rebuild was impossible; the library was fixed **in place** instead, with the same logic wired into the build for future rebuilds. Do **not** run `build-embf.mjs --shipped-only` in a checkout like this — it would write a 22-font manifest.

- **Item 4 — attribution extraction. Done, and the audit's own claim needed correcting:** this doc said bare-CR handling "restores the apex_simple names," but the CR-safe `/\r\n|\r|\n/` split *already existed* in `build-embf.mjs` and the names were still dropped — because they sit on the line *after* "adapted for Ink/Stitch by", and the extractor only took line 1. The real fix is first-**paragraph** extraction (plus the upstream copyright/RFN notice when the paragraph lacks one), implemented in the new shared `tools/font-license.mjs` and used by both `build-embf.mjs` and the new in-place patcher. The other import-time root cause — `tools/build-font.mjs` truncating license text to 4 LF-lines at import — is also removed (full text stored verbatim now). **Mojibake:** none was reproducible in this checkout's data (manifest attributions and all 68 sidecars scan clean; the `Ã`-sequences in `mam_script.json`/`sunset.json` are *legitimate accented-glyph kerning keys*, not mojibake). A conservative double-encoding repair (`fixMojibake`) ships in the extractor anyway; it is a strict no-op on clean text.
- **Item 5 — license reconstruction. Done: 46 files, not 48** (items 1–3 pulled four fonts, two of which — `milli_marif_bold`, `tt_masters` — were among the audit's 48). All 46 fetched verbatim from the upstream source of record (`raw.githubusercontent.com/inkstitch/embroidery-fonts/main/src/<key>/LICENSE`), all HTTP 200, clean UTF-8, **and each file's detected license id matches the manifest's `licenseId` exactly (68/68 crosscheck, zero mismatches)** — no fabricated or guessed content, no gaps.
- **Item 6 — copy step. Done:** `app/scripts/copy-engine.mjs` copies `src/fonts/*.LICENSE.txt` → `public/fonts/<key>.LICENSE.txt` (68 files, orphan-cleaned like previews). Runs on `predev`/`prebuild`, so both dev and dist serve them.
- **Item 7 — credits. Done:** `creditLines()` entries now carry `licenseHref` (the local `/fonts/<key>.LICENSE.txt`) and `modificationNote` (exported `MODIFICATION_NOTE`, the CC-BY-SA 4.0 §3(a)(1)(B) modification indication); `FontCredits.svelte` renders a per-font "license" link and states the modification in its header note (whose old text — "full license texts are available from the collection" — was the pre-fix reality and is now corrected).
- **Item 8 — bare-binary hole. Done, embed path chosen** (this doc's own framing: OFL "explicitly blesses machine-readable metadata"; removing `binHref` would be a bigger UX/architecture call, left to Kent if ever wanted). Key discovery: **no `src/fontbin.js` change was needed** — the codec is schema-agnostic and the `license` field rides through the JSON skeleton untouched. All 68 binaries now embed the complete sidecar text (~4.5 KB each; one short-license font was already complete). Mechanics: new `tools/patch-embf-licenses.mjs` decodes each `.embf`, replaces `license`, trims `name`, re-encodes, and round-trip-verifies before writing; the 22 static `src/fonts/<key>.json` sources were updated in lockstep so `test/embf-guard.test.js`'s `decode(bin) == quantizeFont(srcJson)` pin holds. Idempotent (second run: 0 patches). `build-embf.mjs` does the same embedding on any future `scratch_ink` rebuild. A new guard test pins embedded-license == sidecar for all 68 permanently.
- **Item 9 — the 27 per-font fixes. Done, 27/27 verified by a scripted per-row check** against this doc's §2 requirements (names restored, upstream copyright + RFN notices present, six-team rosters complete, emails stripped). The audit's "mostly fall out of items 4–5" claim held: 25 of 27 fell out of the shared extractor; the two Geneva fonts needed the predicted hand-written override (`ATTRIBUTION_OVERRIDES` in `tools/font-license.mjs`: Schneider/TECFA credit + Hershey provenance; the mandatory 1967 Hershey acknowledgement text ships verbatim in the sidecar and embedded license). Also fixed while in there: `initials_medium`'s trailing-space name ("Initials Medium ") in manifest, binary, and future builds. **bluenesia_satin caveat:** the PR "#1686 permission grant" is archived at `docs/bluenesia-permission-archive-2026-08-04.md`, but note the citation was imprecise — #1686 is the 2022 Dinomouse/NickAinley PR and the Bluenesia permission lives in its **April 2025 comment thread as two screenshots**; the textual record around them is archived, the screenshots themselves need a manual browser save if Kent wants them (flagged in that file).
- **Item 10 — Reserved Font Name scan. Done, zero violations:** no RFN (Sortefax, Nose Transport, Ouroboros, Grand Hotel, Kaushan Script, Reenie Beanie, Shojumaru, Instrument Serif, Linux Libertine) appears as a primary font name in manifest `name`s, manifest keys, binary-embedded `name` fields (all 68 decoded and checked), or app UI source. One benign grep hit for the record: `src/fonts.js` (the legacy outline-font catalog for `EMB-Bot.html`) lists Google Fonts' **original, unmodified** "Kaushan Script" TTF under its own name — compliant, since OFL's RFN restriction applies only to *Modified* Versions. The §7 residual (`satin-fonts.js` legacy registry) is unchanged and still out of scope.
- **Item 11 — prepared, not booked:** the consult brief is written and ready to send (`docs/lawyer-brief-cc-by-sa-2026-08-04.md` — §5 of this doc, updated to the post-remediation state: attribution/notice duties now shipped, so only labeling and downstream-propagation ride on the answer). Booking is Kent's real-world action.
- **Item 12 — final pass. Done with one substitution:** full app build (`npm run build`) confirms `dist/` serves all 68 license files + 68 binaries; decode checks confirm embedded full license text (spot samples + the new all-68 guard test); the credits **data source** was verified end-to-end — `creditLines()` over the built manifest yields 68 rows and every row's `licenseHref`/`binHref` resolves to a real served file. A live browser click-through wasn't possible (Playwright MCP disconnected in this session) — the component itself is unchanged except two additive template lines, and its data path is what was verified.

**Verification (before → after this session's items 4–12):** `node --test` 265/265 → **266/266** (+1: the new embedded-license guard); `cd app && npx vitest run` **327 passed** (326 baseline measured today + 1 new credits spec; the `e2e/wizard-smoke.spec.js` *file* failure is pre-existing/environmental — a Playwright spec vitest can't host — identical before and after, and the COOKBOOK's "321/321" count had already drifted before this session). Two test changes were deliberate content updates, not regressions: the manifest attribution cap rose 200 → 500 (complete notices are longer; longest real one ~350 chars), and new guards pin: no truncation artifacts, trimmed names, sidecar present per font, embedded license == sidecar.
