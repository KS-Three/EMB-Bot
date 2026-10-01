# Paired ground truth — is there a free route to "art + a pro's stitch file"? 2026-09-28

Question: can EMB-Bot get **paired** ground truth — source artwork plus a professional's
machine stitch file of that same design — for free or cheap, instead of the ~$400
`docs/organic-review-2026-09-22.md` §3.2 proposed spending on commercial digitizers?
"Paired" is the whole point: `scratch_corpus/`'s 37 third-party DSTs have no input
image, and a preview rendered FROM a stitch file is derived from the answer, so
comparing against it is circular. The target population is **flat-colour logos on
garments**, and calibrating on the wrong population is this repo's most repeated
failure mode, so craft motifs are counted as a miss, not a partial hit.

Verification legend, as `docs/external-repo-sourcing-2026-09-12.md` uses it:
**[V]** read this session from the cited primary source ·
**[M]** measured/counted this session by API or script ·
**[I]** inferred — reasoning, not a read ·
**[U]** not verified; what would settle it is named.

## Method limits

- Every external fact is dated 2026-09-28. Primary sources: GitHub REST API (`gh api`),
  archive.org metadata and item pages, Zenodo / Hugging Face Hub / arXiv / OpenAlex /
  Crossref APIs, vendor pricing pages, vendor terms pages.
- **Three pages could not be read:** `embroiderydesigns.com` (Cloudflare challenge, 403 —
  not bypassed), Springer's chapter page (login redirect), Fiverr (not fetched; bot-hostile).
  Anything about them below is a search-result snippet and is marked **[U]**.
- Several vendor and site pages were read through `WebFetch`, which summarises with a
  small model. Figures quoted from them are as returned; **re-read the page before quoting
  a price externally.**
- **One file was downloaded:** `data/samples/shamrockin.dst` (4,946 B) from
  `Embroidermodder/Embroidermodder`, to the session scratchpad (not the repo) to read its
  header. No archive.org zips were downloaded — zip *listings* and single text members
  (`LICENSE.txt`) were read in place.
- Nothing was added to the repo but this document. Nothing was committed.

---

## 1. Verdict

1. **No free source ships professional pairs.** Not for logos, and not for anything else.
   The only open stitch+art pairs that exist are **hobbyist** Thingiverse uploads
   (21 items, 3 people carry 18 of them) — and the logo-like ones are recreations of
   trademarked game/film emblems. That is a well-evidenced negative for this repo's purpose.
2. **The licence chain fails even where a licence exists.** For all 21 archive.org-mirrored
   pairs, the mirror's licence metadata (CC BY 4.0 for 18) **disagrees with the `LICENSE.txt`
   inside the download** (CC BY 3.0 — and **4 of the 21 are actually BY-SA 3.0**). Same
   failure shape as the BiRefNet tag-vs-file gap.
3. **The `competitors.md` claim about libembroidery is half wrong.** zlib is true for the
   code. `data/samples/` is **not in libembroidery at all** — it is in the sibling app repo —
   and it holds **one** stitch file (a 1,477-stitch single-colour shamrock, no source art),
   not a corpus. zlib's text does not mention data.
4. **Academia has no stitch-file dataset.** Every embroidery "paired dataset" found pairs
   *images with images* (sketch to rendered embroidery). Nothing new contradicts
   `masters-teardown-2026-08-01.md` §3.8.
5. **Cost is reducible, and part of it is avoidable.** Published prices put a left-chest
   logo at **$6-15 per vendor**; four vendors offer a free/near-free first order; a
   six-vendor panel is ~$58 per logo at list (~$75 with a premium anchor). And **this repo
   already holds pro stitch files for ~5 logos it has no art for** (§2) — recovering that
   art costs $0. The inter-pro measurement itself has no free route, but a ~$29 pilot is
   enough to decide whether the rest is worth buying.

---

## 2. One correction to the framing: what the repo already holds

The brief describes `digitizer/testdata/reference/` (13 files, Becker only). That is the
*committed* subset. The working paired corpus is larger and gitignored:

| | Count | Source |
|---|---|---|
| Committed reference set | 13 files = 4 variants x (jpg+dst+pes) + 1 dst — **Becker only** | `ls digitizer/testdata/reference/` [M] |
| Designs with **real customer art** + pro stitch file | **15 designs** across **7 logos** (Becker x5, Bridge x2, Hotel Fremont x2, MFAB x2, Gaulke x2, TIRES, Precision Drone) | `docs/pro-parity-real-art-2026-08-15.md` §2 [V] |
| Pro stitch files with **no art** | **10 designs**, ~5 logos (Gaulke plowing/JB, "Machine", TOAT, golf, Proseal) | same doc §9 [V] |
| `scratch_kent/Embroidery Files/` | 44 DST, 14 PES, 14 EMB, 15 JPG, 19 PDF across ~9 client folders + a 15-file "Test Files" pack | `find` count [M] |

Three things in that table matter for this question:

- **The committed `.jpg`s are not source art.** `DOCTRINE.md` (the "Four committed 'real
  customer artwork' fixtures" entry, ~line 1265) records them as two-panel vendor stitch
  simulations, md5-identical to files in the delivery zip. Genuine Becker art is
  `becker_marine_logo.png`; genuine TIRES art is `logo_script_tires.png`. [V]
  So even inside the repo, "a .jpg beside a .dst" is a trap, and any *acquired* corpus
  must be checked for the same thing (a vendor's returned JPG is a preview of the DST).
- **The pro-vs-pro ceiling (75-84) is n = 2, same digitizer.** `pro-parity-real-art` §11:
  `hotel_hat_vs_patch` 75.2 and `machine_beanie_two_files` 83.6 — "genuinely independent
  renditions" by *one* digitizer; PES-vs-DST pairs are refused and same-job pairs were
  discarded. **Inter-*digitizer* variance is unmeasured**, as the brief says. [V]
- **Free leads for it may already be on disk.** DST header labels and stitch counts
  (read this session [M]) show the Gaulke logo built at least two very different ways:
  `C GOLKE LC.DST` — 9,455 stitches, 6 colour changes — against `c golke logo LC.DST` —
  5,294 stitches, 0 colour changes. Becker also has a decorator's version
  (`To a T-Becker Beanies/beckers beanie.DST`, 11,486 st) beside the Becker Marine set.
  Whether these are different *digitizers* or one digitizer's revisions is **[U]** —
  settle it by asking Kent who made each, or by reading the Wilcom property set that
  `pro-parity-real-art` §10 says is readable in the `.EMB` files.

---

## 3. Q1 — do free or open sources ship genuine pairs?

### 3.1 Census

| Source checked | What is there | Pairs? | Logo-like? |
|---|---|---|---|
| **Embroidermodder `data/samples/` + `test/`** | 12 + 67 files (§5) | No — 1 lone DST; `test/` is 2 designs in dozens of formats | No |
| **archive.org mirror of Thingiverse** | 338 items match "embroidery/embroidered"; 24 hold a stitch file; **21 hold stitch + vector art** (§3.2) | **Yes, hobbyist** | 7 emblems, all trademarked IP |
| **Chad Gadya** (Paley & Gray) | 516 PES frames on archive.org (§3.3) | No source art released; algorithmic, not a pro | No (animation frames) |
| **Ink/Stitch sample files** | 33 samples: appliqué, lace, ripple fills, QR code, unicorn... | SVG-with-parameters, made in the tool | No |
| **Free design sites** (Embroidize, EmbKhazana; EmbroideryDesigns.com unreadable, 403) | Embroidize's page offers DST only, no source art; none names the digitizer; a site preview is a render of the stitch file [I] | No — circular by construction | Some, unlicensed |
| **Wikimedia Commons** | upload whitelist has 24 extensions; **none** is a stitch format | — | — |
| **GitHub** | `gh search repos "embroidery dataset"`: 2 repos, both hand-embroidery *photos* (§6). Code search does not index binary DST/PES — `extension:dst` returns NLP `.dst` text files | No | No |
| **Hugging Face, Zenodo, archive.org, arXiv** | §6 | No | No |
| **Kaggle** | JS-rendered, still untested | **[U]** | — |

Evidence: Embroidermodder trees via `gh api repos/Embroidermodder/*/git/trees/main?recursive=1`
[M]; archive.org search `identifier:thingiverse-* AND (embroidery OR embroidered)` + per-item
metadata + zip listings [M]; Ink/Stitch page `inkstitch.org/tutorials/resources/samples/`
[V] (states no licence, no formats); Commons `action=query&meta=siteinfo&siprop=fileextensions`
[M]; `gh api search/code` [M].

### 3.2 The one real cache: the Thingiverse mirror, counted

`archive.org` carries a bulk mirror of Thingiverse things (`identifier: thingiverse-<id>`,
uploader `eddy.hintze@gmail.com`). I listed every one of the 338 matches and opened each
zip's file list (not the files). **[M]**

- **24** items contain a stitch-format file; **21** also contain a vector art file
  (`.svg` or `.ai`) — genuine art + stitch pairs, 77 stitch files counting per-format copies
  in the CC-BY 3.0 subset alone.
- **Three people wrote 18 of the 21:** Christopher Norwich ("prescrumptuous", 7 — logos:
  N64, Destiny Omolon/Suros/Hakke, Alien Nostromo, two US-Tricentennial marks),
  Jordan Routhier ("tacobelle", 8 — Puffin Rock, Animal Crossing, Captain America shield,
  Incredibles: cartoon appliqué), Ann Victory ("aevictory", 3 — craft motifs).
- **Digitizer quality is hobbyist by the authors' own words.** Norwich's N64 upload:
  "I recently switched from Sophiesew to Embroideryware and I'm loving it" (in-zip
  `README.txt`). His Weyland-Yutani upload says "using SophieSew". These are consumer-software
  digitizations, not a Wilcom professional's production files. [V]
- **The "logo" pairs are trademarked third-party marks.** N64 (Nintendo), Destiny
  (Bungie), Nostromo (Alien) — the `.ai` is the uploader's recreation. A CC licence from
  the uploader cannot grant rights in the underlying mark. [I]
- **Only 7 of the 21 are logo-like at all** (all Norwich). The other 14 are cartoon
  characters and craft motifs — the wrong population.
- Coverage caveat: this is what a text search on the *mirror* found, not all of
  Thingiverse, and two zips could not be listed. It is a floor, not a census.

### 3.3 Chad Gadya (Paley & Gray) — open licence, wrong kind of pair

516 `.pes` files, one per frame of an embroidered animation, uploaded by Theodore Gray
himself: `archive.org/details/theodore_theodoregray_ChadGadyaEmbroidery`, `licenseurl`
CC BY-SA 3.0. Gray's own account: "we created all the embroidery designs using custom
software we wrote specifically for animation embroidery" — Paley's Flash frames imported
into Mathematica, polygon processing and stitch generation "using automated algorithms"
(`home.theodoregray.com/stitchblog/2015/7/10/embroidered-animation-finally`). [V]
So it is (a) **algorithmic output, not a professional's judgement** — which is what
EMB-Bot is trying to *match*, not to be graded against; (b) the source frames are not
released as separate art (the sibling item `ChadGadyaHD.H264` is the 2.4 GB *embroidered*
video); (c) share-alike — see §4.

### 3.4 Why pairs are structurally scarce [I]

A logo's art belongs to the client, the stitch file is the digitizer's product, and the
two travel together only inside a paid job. Marketplaces and freebie sites publish the
file and a render of it. The only people who publish both are hobbyists reproducing
fandom art — the one population that is neither a logo customer's nor a pro's.

**Verdict Q1: essentially none exist.** Best free yield = 7 hobbyist trademark-logo pairs.

---

## 4. Q2 — the actual licences, read from the file

| Candidate | Claimed | What the file says | Survives a public commercial repo? |
|---|---|---|---|
| **Thingiverse mirror pairs** (21) | metadata: CC BY 4.0 (18), BY-NC 4.0 (2), BY-NC-SA 4.0 (1) | In-zip `LICENSE.txt` for **all 21 disagrees**: 14 x BY 3.0, **4 x BY-SA 3.0**, BY-NC 3.0, BY-NC-SA 3.0, one unversioned "cc-nc". E.g. `thingiverse-3329982`: "licensed under the Creative Commons - Attribution - Share Alike license. http://creativecommons.org/licenses/by-sa/3.0/" while its item metadata reads `by/4.0` | **No.** Version mismatch, hidden SA, and — decisively — the uploader cannot license the trademarked logos. At most a *local* evaluation set; do not commit. |
| **Chad Gadya** | CC BY-SA 3.0 (uploader metadata) | No `LICENSE` file in the item; grant is metadata + the blog sentence "available under Creative Commons license" (no version) | **Not in this repo.** Share-alike is the exact question the 2026-08-04 font decision removed rather than answer (`docs/lawyer-brief-cc-by-sa-2026-08-04.md`, "RESOLVED BY REMOVAL"). |
| **Embroidermodder `data/samples/`** | "zlib" (`competitors.md`) | `LICENSE.md`: "Permission is granted to anyone to use **this software**..." — grants rights in *software*; no clause mentions designs or data (§5) | **Unestablished.** Code is fine; the data is unlicensed as far as the repo says. |
| **Ink/Stitch samples** | none stated | The samples page states no licence (read) | **Unestablished**; Ink/Stitch code is GPL-3.0, fonts are OFL/CC-BY-SA per the font audit. |
| **Embroidize free designs** | "Free DST Embroidery Designs for Commercial Use" | Terms: may use "for small business commercial products (physical items only)"; **prohibited** to "Resell or redistribute digital files", "Share files publicly or privately"; "All designs remain the intellectual property of Embroidize LLC." | **No.** Committing one to a public repo is the prohibited act. |
| **EmbKhazana** | "totally free to download and use... personal and commercial" | Page states no redistribution terms and does not say who made the designs | **Unestablished.** |
| **Liu et al. `embroidery-streamlines`** | `competitors.md`: "reference repo licence unverified" | `LICENSE`: "This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0"; README: "licensed under MPL2.0"; GitHub API says `NOASSERTION` | Code, not data. **Incidental correction** to `competitors.md`: the repo licence *is* stated. The paper's CC BY-NC-ND is a separate matter. |
| **MSEmbGAN dataset** | free download | Page: "intended for educational and informational purposes only"; no licence text | **No** — and images only anyway. |

**Rule confirmed:** "free to download and stitch" is not redistribution. The one written grant
that *does* transfer rights is a **vendor's**: AquaDigitizing's terms read "Customers have
full rights to use, reproduce, or resell the files" and "Aqua Digitizing does not claim
ownership of the final files once delivered", while making the customer responsible for
rights in submitted art (`aquadigitizing.com/terms-and-conditions/` [V]). Absolute
Digitizing's terms page states nothing on ownership (**[U]** for the rest of the vendors).
**Implication [I]:** the only *committable* pair is one built from art **Kent owns**, run
through a vendor whose terms transfer the file.

---

## 5. Q3 — the libembroidery claim, checked against the repository

Claim (`docs/scope-digest/competitors.md:37`): *"libembroidery — zlib. ... its
`data/samples/` as free extra corpus"*, citing `embroidermodder-research-2026-08-13.md` §8.

**Half 1 — zlib: TRUE, for code.** `LICENSE.md` in both repos opens "zlib/libpng License";
libembroidery: "Copyright (c) `2018-2025` `The Embroidermodder Team and Josh Varga`",
app: "Copyright (c) 2011-2026 Embroidermodder, Jonathan Greig, Josh Varga and all other
contributors". GitHub API reports `zlib` for both. [V, M]

**Half 2 — `data/samples/` in libembroidery: FALSE as written.**

- **libembroidery `main`** has **56 files, 855,123 bytes total: 41 `.c`, 2 `.h`, 3 `.md`, 3
  `.yml`, build scripts.** No `data/` directory, no samples, no stitch file of any kind.
  Its other branch (`clarity`) has none either. `src/test/*.c` is C test code. [M]
- **The directory is in the sibling repo `Embroidermodder/Embroidermodder`.** The research
  doc's own §8 said so ("`data/samples/` in the app repo"); the digest reworded it onto
  libembroidery. [V]
- **What `data/samples/` really is: 12 files, 3,568,074 bytes.** 6 DXF CAD drawings
  (Embroidermodder, Fleur-de-lis, OSHW-Logo, Omega, Puzzle, Tux), 4 CSV point lists
  (`spiral4/5/6.csv`, `spiralgrid.csv` = 2.86 MB), `shamrockin.rgb` (4 bytes), and **one**
  stitch file, `shamrockin.dst`. [M]
- **`shamrockin.dst`:** 4,946 B, header `ST: 1477`, 0 colour changes, label "Untitled",
  ~50 x 49 mm — a single-colour shamrock, no source artwork paired. Added 2014-03-11 by
  Jonathan Greig ("Added Shamrock Sample Files", `211189ba`); moved to `data/samples/` in
  the 2026-01-13 restructure. [M]
- **The bigger stitch cache is `test/`**: 67 files — 45 `Star*` and 17 `Embroidermodder*`,
  i.e. **two designs written in dozens of formats** (a format-conversion fixture).
  `test/README.md`: "should not be used unless you are a software developer testing
  libembroidery. They may not be valid files." [V]

**Does zlib cover the data? Not demonstrably.** The grant is for "this software"/"the
original software". `CREDITS.ini` marks three contributors `Designs=true` — Jonathan Greig,
Nina Paley, Theodore Gray — and Paley & Gray's designs are published elsewhere under
CC BY-SA 3.0 (§3.3), so the project itself knows designs have separate authors, yet
`data/samples/` carries no per-file licence. The DXFs include the OSHW logo and Tux,
third-party images [I] (I read neither licence primarily; a search summary attributes the
OSHW association logo to CC BY-SA 4.0 — **[U]**).

**Verdict Q3:** the format-reference use in the same bullet stands. "Free extra corpus" does
not: one unpaired 1,477-stitch shamrock, zero logo art, no data licence. Suggest amending
`competitors.md:37` to name the app repo and drop the corpus claim.

---

## 6. Q4 — academic and research datasets

| Item | Venue / host | What it is | Stitch files? | Access |
|---|---|---|---|---|
| Ye, Ji, Song, Feng, Song, "Towards End-to-End Embroidery Style Generation: A Paired Dataset and Benchmark" | PRCV 2021, LNCS (Crossref DOI `10.1007/978-3-030-88013-2_17`) | 9k sketch to embroidery-**image** pairs (search summary; abstract not readable) | No — preview images | **[U]** no download link found |
| MSEmbGAN dataset (Hu et al., Wuhan Textile Univ.) | IEEE TVCG 2024, `doi 10.1109/tvcg.2024.3447351`; hosted `hyper.ai/en/datasets/34570` | 30,000+ 256x256 images, 1000.37 MB, made with Wilcom 9.0 | **No — "only images"** | torrent / Google Drive; "educational and informational purposes only", no licence text |
| Liu et al., "Directionality-Aware Design of Embroidery Patterns" | CGF (Eurographics) 2023 | classical streamlines, not learning | example outputs only (`.exp`/`.emb`), no dataset | repo `desmondlzy/embroidery-streamlines`, MPL-2.0 |
| "One-shot Embroidery Customization via Contrastive LoRA Modulation" | arXiv 2509.18948 / ACM TOG | diffusion, appearance; own benchmark of 30 + 50 + 50 images, **no public release stated** | No | — |
| "Generating Embroidery Patterns Using Image-to-Image Translation" | arXiv 2003.02909 | preview-image generation | No | — |
| StitchOver | arXiv 2609.08311 (2026-09-08) | conductive-thread fabrication on seams | n/a | — |
| Shui Horsetail Embroidery dataset | GitHub `1yxc11/...`, Zenodo 20525105 | 1,005 photos + 1,005 hand-traced SVG centre-lines of **hand** embroidery | No | GitHub API + `LICENSE` file: MIT; the **README badge says CC BY 4.0** — same badge-vs-file conflict |
| `ly0313/Embroidery_dataset` | GitHub | 361 jpg + 304 png + 665 txt, butterflies etc. | No | no licence |
| `data_designs_codeNstitch` | Zenodo 7642304 | metadata spreadsheet for 217 student-**coded** DSTs; the DSTs themselves are not deposited | No | CC BY 4.0 |
| Hugging Face datasets | Hub API | 4 hits for "embroidery": a video-clip set (MIT), an API README, a lingerie photo set (licence "other"), an empty repo. Zero on-topic hits for `dst`, `tajima`, `machine embroidery`, `digitiz*` | No | — |

Sweeps: arXiv API `ti:embroidery` = 9 records, `abs:embroidery AND abs:stitch` = 12;
OpenAlex, three queries, works from 2023 on — all appearance synthesis, heritage image
recognition, or e-textile fabrication, plus the Liu CGF paper. [M]

**Has "no published end-to-end learned vector-art to machine-stitch system" changed? No
counterexample found.** The nearest text is arXiv 2509.18948 §5, which calls defining a
representation for "primitive embroidery instructions (EmbIns)" — "including stitch
coordinates, needle commands, and color sequences" — *future work*, and names a
"differentiable rasterizer for EmbIns" as a direction (read through `WebFetch` — **verify
the wording before quoting**). No evaluation dataset exists either: nothing pairs source art
with machine stitch files, at any size, under any access terms.

---

## 7. Q5 — what commercial digitizing actually costs

Published prices for a **left-chest / cap logo** (the size class that matters), as read from
each vendor's own pages on 2026-09-28. "First-order" = a stated new-customer offer.

| Vendor (page) | Left-chest / cap price | Larger | Turnaround | First-order / trial | Ownership terms |
|---|---|---|---|---|---|
| **1Dollar Digitizing** (`1dollardigitizing.com`) | $1 per 1,000 st, **$6 min** | — | 24 h; rush 12 h / 8 h | **First hat or left-chest logo $1 flat, up to 10,000 st, no code** | not read |
| **AquaDigitizing** (`/pricing/`, `/free-digitizing/`) | **$8 flat** (<= 4.5 x 4.5 in); or $1.25/1,000, $7 min | portrait $35; full front / jacket back $55; max $85.75 | 12-24 h guaranteed; 3-6 h priority (no weekends) | **Free digitizing up to 7,000 st, new accounts, "credit card or any other personal details are not required"**; excess billed (8,000 st = $1.25) | **"Customers have full rights to use, reproduce, or resell the files"** |
| **Absolute Digitizing** (`/embroidery-digitizing-pricing/`) | **$10 flat** (<= 4 x 4 in); basic logo $5 (<= 2 x 2); or $1/1,000, $10 min, $40 max | shirt front $22; jacket back $25 / $40 multicolour | "Within 12 hours"; 2-3 h rush +$10 | **"Get 50% OFF on Your First Order"** | page silent |
| **MIG Digitizing** (`/pricing-table`) | **$8** up to 5,000 st, +$1.5/1,000 | max $90 (100k st) | 3-24 h no weekends; 1-6 h priority | none stated | not read |
| **Impact Digitizing** (`/pricing/`) | **$10** up to 10,000 st, then $1/1,000 | jacket back $25 (<= 50k st) | urgent 4-5 h, normal 12-24 h | none stated | not read |
| **CheapDigitizing** (`/business/embroidery-digitizing/`) | **$11** flat (<= 4.5 x 4.5 in); or $1.50/1,000, $7.50 min | $41 (<= 8 x 8); $61 (> 8 x 8) | regular 8 h | **Free trial for embroiderers, screen printers, promo businesses** after business verification (Kent's shop is eligible [I]); no stitch limit stated | not read |
| **PRO digitizing** (`prodigitizing.com/service-pricing/`) | **$15-20** ("starting", complexity-adjusted) | LC + cap $20-40; 3D puff $25-35; full back $60-75 | next business day; rush 2-4 h | none | not read; "sew-quality edits at NO additional cost" |
| EmbroideryDesigns.com custom digitizing | "minimum $10, 24 h" — **snippet only, page 403** | | | | **[U]** |
| Royal Digitized | "from $15, 4-8 h" — snippet only | | | | **[U]** |
| Fiverr gigs | "$5" starting price — snippet only; checkout price **[U]** | | | | **[U]** |

**Arithmetic on the ~$400 in `organic-review` §3.2.** "20-30 logos to 3-4 services at $10-20
each" is **$600-$2,400** (20x3x$10 to 30x4x$20). ~$400 is right only for a smaller panel:
about **6 logos x 6 vendors x ~$11**, or 20 logos to one $20 vendor. The panel matters more
than the logo count for the question in §8.

**A six-vendor panel, list price, per logo** (1Dollar ~$7 at 7,000 st, Aqua $8, Absolute $10,
MIG ~$12.50 at 8,000 st, Impact $10, Cheap $11): **~$58**; adding PRO digitizing as a
higher-tier reference: **~$73-78**. First-order offers take roughly **$30** off the first
logo (1Dollar $7 to $1, Aqua $8 to $0, Absolute $10 to $5, Cheap trial $11 to $0).

**A caution on the word "pro" [U]:** these are volume services at $6-15; some now market
"AI" digitizing (Absolute has an `ai-embroidery-digitizer` page). If a vendor's output is
itself auto-digitized, scoring EMB-Bot against it measures auto-versus-auto. The Becker files
are Wilcom (`becker-pro-parity` doc, ES-65 worksheets). Include one premium-tier vendor as
the anchor, and ask each vendor how the file is made.

---

## 8. Inter-pro variance — can it be run free or cheap?

**What is unmeasured:** how far two *different* digitizers diverge on the *same* logo.
Existing n = 2 is one digitizer's own jobs (§2), so "75-84" is an intra-digitizer ceiling,
and it says nothing about how far EMB-Bot's 42.5 sits from the *spread* between pros.

| Route | Cost | What it gives | Catch |
|---|---|---|---|
| **A. Mine what is on disk** — the duplicate renditions of Gaulke and Becker in `scratch_kent/` | $0 | possible n >= 1-2 already scorable with `selfconsistency.py` | who digitized each is **[U]**; PES-vs-DST pairs are refused by the tool; ask Kent |
| **B. Vendor first-order offers, one logo** — 1Dollar $1, Aqua $0, Absolute ~$5, Cheap $0 | **~$6** with the four offers alone; **~$29** adding MIG (~$12.50) and Impact ($10) | a real 4-6 file inter-vendor spread on one logo, and a read on which vendors track a Wilcom pro | one logo, and each offer is per-account, one-shot |
| **C. Full panel** — 6 logos x 6 vendors | list **~$351** (six cheap vendors) to **~$470** (with a PRO anchor); ~$30 less with the offers | a usable variance estimate across logos | this *is* the ~$400 |
| **D. Free-only** — open corpora, academic data | $0 | **nothing** — §3, §6: no source ships two digitizers' work on one logo | — |

**There is no free route to the experiment itself** — it needs several independent
digitizers on one logo, and every free source ships one hobbyist's version of a trademarked
mark. What is free is *(A)* and the *first-order* slice of *(B)*. Volunteer or
community routes (embroidery forums, "digitizing contest" posts) were **not researched** and
carry no evidence here.

**Design notes if it is run [I]:** send **art Kent owns or that is synthetic** (the repo's
committed fixtures, if he authored them) so the returned files can be committed — a
customer's logo forces the result into gitignored `scratch_*`, and the customer's rights
are the sender's problem under Aqua's terms; register returned files with the existing
scorecard, but reject vendor JPG "proofs" as art (§2); and **do not mix PES and DST** in one
comparison (`pro-parity-real-art` §11).

---

## 9. What remains unverified

- **EmbroideryDesigns.com, Royal Digitized and Fiverr prices** — snippets only; the first is
  behind a Cloudflare challenge. Settle by reading them in a browser.
- **Whether vendor promos stack, are per-logo or per-account, and their fine print** —
  read once each; "7,000 stitches" is not stated as one design vs cumulative.
- **File-ownership terms** for every vendor except AquaDigitizing (Absolute's terms page
  says nothing). Settle by reading each Terms page or asking support.
- **Who digitized the duplicate Gaulke/Becker renditions on disk** — Kent, or the
  `.EMB` Wilcom property sets.
- **How each vendor makes its files** (human vs auto) — ask.
- **The PRCV 2021 dataset's access terms** — no download link found; Springer page not
  readable. Low value: images only.
- **Kaggle**, and **live Thingiverse** (the scan covered only the archive.org mirror, 338
  hits by text search; the other 317 items' `LICENSE.txt` were not read).
- **Tux and OSHW licences** in Embroidermodder's DXF samples — not read from primary
  sources; irrelevant to stitch files.
- **arXiv 2509.18948 wording** — read through a summarising fetch.
- **Not legal advice.** The trademark-chain point (§3.2, §4) is inference; counsel has a
  brief on a neighbouring CC-BY-SA question (`docs/lawyer-brief-cc-by-sa-2026-08-04.md`).

---

## 10. Recommendation

**The ~$400 is reducible and partly avoidable; the free/open route is a dead end.**

1. **Do not spend time on open corpora.** Best yield is 7 hobbyist trademark-logo pairs
   under a licence chain that fails its own file, plus share-alike. `data/samples/` is one
   file. Amend `docs/scope-digest/competitors.md:37`.
2. **$0, first: turn existing stitch files into pairs.** ~10 pro designs (about 5 logos —
   Gaulke plowing/JB, "Machine", TOAT, golf, Proseal) have DSTs in `scratch_kent/` and **no
   art**. Kent's shop received those logos from customers; recovering the originals takes
   the paired set from 7 logos to ~12 with no purchase. Confirm each is *original art*, not
   a vendor proof (§2).
3. **$0, second: check the duplicate renditions on disk** (§2, §8-A). If two are different
   digitizers, that is inter-pro n >= 1 already.
4. **Then ~$29, one pilot logo:** the four first-order offers plus MIG and Impact,
   one logo Kent owns, one premium anchor if budget allows. Score the spread with
   `selfconsistency.py`. **If the spread between vendors is small, the ceiling is real and
   the rest is unnecessary; if it is large, the pilot has already named which vendors are
   worth the next dollar.**
5. **Only then the panel** — 3 logos x 6 vendors is ~$175 at list; 6 logos ~$350
   (~$470 with a premium anchor) — and only if step 4 says the number will move a decision.
   Keep vendor files in gitignored `scratch_*` unless the vendor's terms transfer ownership
   (Aqua's do) *and* the art is Kent's own.

**Is the ~$400 necessary? The measurement is; $400 is not.** No free source measures
inter-pro variance. But the decision-grade version is ~$30, and steps 2-3 cost nothing.
Ask Kent before step 4: first-order offers create accounts and send art to outside vendors.

---

## Sources

Local: `digitizer/testdata/reference/`; `scratch_kent/Embroidery Files/` (DST headers read);
`DOCTRINE.md` (~L1265, ~L960); `docs/pro-parity-real-art-2026-08-15.md` §2, §9-§11;
`docs/organic-review-2026-09-22.md` §3.2; `docs/scope-digest/competitors.md` L37;
`docs/embroidermodder-research-2026-08-13.md` §8; `docs/lawyer-brief-cc-by-sa-2026-08-04.md`;
`CLAUDE.md` (third-party stitch-file rule).

Embroidermodder / libembroidery: `github.com/Embroidermodder/libembroidery` and
`.../Embroidermodder` — `LICENSE.md`, `CREDITS.ini`, `README.md`, `test/README.md`, recursive
git trees, `commits?path=data/samples`, branches (all via `gh api`).

archive.org: `archive.org/metadata/thingiverse-<id>` (338 items scanned; zip listings via
`archive.org/download/<id>/<zip>/`; `LICENSE.txt` members of 21); `thingiverse-3138216` (N64),
`thingiverse-3329982`, `thingiverse-3089391` (BY-SA 3.0 in-zip vs `by/4.0` metadata);
`theodore_theodoregray_ChadGadyaEmbroidery`, `ChadGadyaEmbroideryFiles`,
`ChadGadyaHD.H264`; `home.theodoregray.com/stitchblog/2015/7/10/embroidered-animation-finally`.

Academic / hosts: `api.crossref.org/works/10.1007/978-3-030-88013-2_17`;
`hyper.ai/en/datasets/34570`; `arxiv.org/html/2509.18948v1`; arXiv API (`export.arxiv.org`);
OpenAlex API; `github.com/desmondlzy/embroidery-streamlines`;
`github.com/1yxc11/Shui-Horsetail-Embroidery-datasets`; `github.com/ly0313/Embroidery_dataset`;
Hugging Face `api/datasets?search=`; Zenodo `api/records`; Commons `siteinfo` API;
`inkstitch.org/tutorials/resources/samples/`.

Sites and terms: `embroidize.com/terms-and-conditions`; `embkhazana.com/free-embroidery-designs`.

Vendors: `absolutedigitizing.com/embroidery-digitizing-pricing/`;
`migdigitizing.com/pricing-table`; `impactdigitizing.com/pricing/`;
`aquadigitizing.com/pricing/`, `/free-digitizing/`, `/terms-and-conditions/`;
`1dollardigitizing.com`; `cheapdigitizing.com/business/embroidery-digitizing/`;
`prodigitizing.com/service-pricing/`.

**Every fetch dated 2026-09-28.** Vendor prices and offers change without notice; the archive.org
mirror and the Hub listings will keep growing.
