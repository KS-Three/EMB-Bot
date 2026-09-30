# Product name + SEO research — 2026-09-30

Kent's brief (2026-09-30, in the Studio design review): *"Come up with a new
name, do a little research and determine how we can leverage SEO so that this
is the FIRST tool that pops up when people want to get a digitized file."*

Researched the same day with ~45 web searches, 14 landing-page fetches,
Google's autocomplete endpoint, and DNS/HTTP probes on candidate domains.
**Caveats, all of which bound what this doc can claim:** no free source
exposes numeric monthly volumes (Keyword Planner and Ahrefs need a login), so
the demand signal is autocomplete ORDER plus what kind of page Google is
rewarding; reddit.com blocked the crawler, so community sizing is from a
third-party stats page; domain checks are DNS/HTTP only — "no live site" is
NOT "available". Every "who ranks" claim below is a SERP fetched that day and
will drift.

**Naming is Kent's call.** This doc ranks options; it decides nothing.

---

## A. Search demand and intent

### A1. What people type, and what ranks

Google autocomplete (US, `client=firefox`), completions in Google's own
popularity order:

| Seed | Top completions (in order) | Read |
|---|---|---|
| `convert image to embroidery` | pattern free · **file** · pattern · **file free** · **file free online** · design online free | "free" and "online" attach to almost every variant |
| `embroidery digitizing` | **software** · (bare) · services · software free · classes · software for mac · services near me | software > services; Mac is a real sub-intent |
| `png to pes` | **converter** · (bare) · converter free · converter online free · file · embroidery | pure converter phrasing |
| `jpg to dst` | **converter** · converter free · converter online free · converter software · converter app | same |
| `auto digitizing` | **embroidery software** · embroidery software free · embroidery online · wilcom · inkstitch | brand-modified tail exists |
| `digitize logo` | **for embroidery** · for embroidery online free · for embroidery free · online · software | logo intent collapses straight into embroidery |
| `free embroidery digitizing` | software · online · for ipad · for mac · course · app · website | device modifiers = "runs in a browser" is a selling point |
| `ai embroidery` | **digitizer** · machine · generator · generator free · digitizer free · digitizing software | "AI embroidery digitizer" is the emerging head term |

Who ranks per money term:

| Query | Intent | Page 1 is mostly… | Tools that appear |
|---|---|---|---|
| embroidery digitizing software | commercial | vendor homepages | Wilcom, Ink/Stitch, Embird, Hatch, Brother, Embrilliance, **Ember**, Threads |
| convert image to embroidery file | commercial-investigational | **blog guides from human digitizing services** (ZDigitizing, EmbPunch, Rise, SBS) + Brother support + MachineEmbroideryGeek; **Stitchique** is the only tool-shaped result and is actually a $9.90 manual service with H1 "Free Image to Embroidery File Converter Online" | — |
| image to embroidery file | mixed | Brother Artspira+, SewFlow, **VectoSolve**, EmbroideryDesigns.com, Hatch PhotoStitch blog | SewFlow, VectoSolve |
| convert jpg to pes | commercial (converter) | Etsy market page, OnlineConvertFree, **StitchFast**, Filestar, Digitizing Buddy, SharkFoto | StitchFast; generic converter farms that cannot digitize |
| convert png to dst | commercial (converter) | Filestar, **StitchFast**, OnlineConvertFree, Mega/Impact/Genius Digitizing blogs, SharkFoto | StitchFast |
| auto digitizing embroidery online | commercial | ZDigitizing blog, **Hatch feature page**, MaggieFrames/MagneticHoop blogs (hoop sellers content-farming), **Embrowser**, **Ember** | Embrowser, Ember |
| AI embroidery digitizing | commercial | Absolute Digitizing "AI digitizer" page, Hatch, OpenArt/Pixlio (image *generators*, not stitch files), **Ember** | Ember |
| free embroidery digitizing software | informational-commercial | SewingMachineFun roundup (Mar 2024: "no free auto-digitizing options" — now false), Ink/Stitch, Hatch trial, **Ember** | Ember |
| online embroidery digitizer | mixed | Migdigitizing ($8/design service), MaggieFrames, Ink/Stitch, Hatch, EmbroideryDesigns.com, **Ember** | Ember |
| digitize logo for embroidery | service-commercial | Printify blog, Etsy listing, Embroidery Legacy guide, EmbroideryDesigns.com ($10, 24h), Digitizing Ninjas ($10) | Hatch, Ember |
| embroidery file converter | converter (file→file) | MS Store "Embroidery Converter Studio", Embird, Brother PED, EmDigitizer viewer, SewFlow | SewFlow |

**Converter and digitizing are two different SERPs.** "png to dst / jpg to
pes" is held by generic file-converter farms (Filestar, OnlineConvertFree,
SharkFoto) that cannot produce a stitch file, plus Etsy. "Embroidery file
converter" means DST↔PES (Embird, Truesizer, Converter Studio). The
image→stitch intent lives under "convert image to embroidery file",
"digitize logo for embroidery", "auto digitizing … online" and "AI embroidery
digitizer" — and the first two are currently won by *service blogs*, not
tools. **That is the gap.**

### A2. Incumbents

| Name | Type / launched | Leads with | Pricing | Formats |
|---|---|---|---|---|
| **Ember** (emberdesign.net) | browser tool; on 7 of the 11 SERPs above | "Embroidery Digitizing Made Simple"; one-click Auto Digitize | Free / Pro $9.99/mo (auto-digitize is Pro) | PES, DST, EXP, JEF, VP3 +5 |
| **Embrowser** | browser tool | "Turn photos, logos, and text into machine embroidery, right in your browser" | Free (2 auto-traces/wk) / $9.99/mo | PES, DST, JEF, VP3, EXP, U01 |
| **StitchFast** (UK) | AI converter; per-format pages | "Convert any JPG to a PES embroidery file", "real AI digitizing… not auto-tracing", <60 s | £4.99/design, £29.99/mo | 7 per job |
| **SewFlow** | browser converter; own "best online digitizer 2026" blog | "Image, Logo & Photo to Embroidery Converter" | preview free, download paid | JEF, PES, DST, EXP, XXX, SEW |
| **EmbroidAI** | AI converter; per-format pages | "AI Image to Embroidery Converter", "free, online and instant" | free, optional account | DST, PES |
| **Stitch AI** (stitchai.us) | AI digitizer, beta | "UPLOAD. STITCH. DONE." — "98.4% accuracy" | coins: free 15 / $12/mo | 12 |
| **Stitchist** (stitchist.app) | browser digitizer | "Art goes in. Stitches come out." | Free / Pro $50 one-time | 8 export, reads 47 |
| **StitchForge** | AI, "Coming Soon", ©2026 | "From Image to Embroidery" | undisclosed | DST, PES, EMB, JEF |
| **VectoSolve** | tracer-based converter | "Convert Images to DST, PES and JEF"; shows sewn size in mm before you pay | $49/yr, 300 conversions | DST, PES, JEF |
| **Pixel Stitch** | free, pixel-art only | "Free Embroidery Digitizer" | free | many |
| **Stitchique** | *manual service* dressed as a tool | "Free Image to Embroidery File Converter Online", "100% Manual Digitizing" | $9.90–$50/design | 6 |
| Hatch (Wilcom) | desktop | "Turn any image into embroidery in seconds. No digitizing experience needed." | from $45/mo | all |
| Brother PE-Design 11 / Artspira+ | desktop / phone | Auto Punch, PhotoStitch | ~$1,078–$1,958 / sub | PES |
| Embrilliance | desktop | "Embroidery for the Rest of Us"; no auto-digitize on homepage | one-time tiers | all |
| SewArt | desktop | auto-digitize, "simple artwork" | ~$75 | all |
| Ink/Stitch | open-source (GPL-3) | Inkscape-based; does NOT advertise auto-digitize from images | free | all |
| Ricoma Chroma | cloud desktop | auto-digitize vector/PNG/JPEG | $559–$1,400/yr | all |
| Human services | EmbroideryDesigns.com, Digitizing Ninjas, Migdigitizing, Etsy | "$8–$10, 24-hour turnaround" | per design | any |

Two things stand out. **A wave of browser tools launched 2025–26** (Ember,
Embrowser, SewFlow, EmbroidAI, Stitch AI, Stitchist, StitchForge, VectoSolve,
Pixel Stitch) — the SewingMachineFun claim that "no free auto-digitizing
exists" is 18 months stale. And **nobody in that wave has a content moat
yet**: StitchFast and EmbroidAI have per-format pages; Ember ranks from its
homepage alone; the "convert image to embroidery file" SERP is still held by
digitizing-service blogs.

---

## B. Name candidates

Ruled out by search (beyond the obvious brands): **StitchForge** (live AI
competitor), **PixelStitch** (four products), **Stitchify** (three services +
an app), **Stitchly**, **Threadify**, **Threadline**, **Digistitch** (an Ohio
shop), **Stitchsmith**, **StitchBot** (OML Embroidery's AI coach — too close
to "EMB Bot"), **Stitch Lab**, **Stitch AI**, **Stitchist**, **InstaStitch**,
**AutoPunch** (Brother's feature name), **Threadcraft**.

Also: **"Fritsch In Stitches"** (fritschinstitches.com, modern quilts, active
socials) already exists in the sewing space — any "Fritsch + Stitch" product
name will be confused with it in search.

| # | Name | Type | Why it works | SEO angle | Domain (unverified) | Collision |
|---|---|---|---|---|---|---|
| 1 | **Stitchable** | brandable | Says the promise: your image becomes *stitchable*. One word, verb-adjacent | Tagline carries keyword: "Stitchable — turn any image into an embroidery file" | .com registered, no live site; .app redirects; .io unresolved | None in embroidery. Low |
| 2 | **HoopReady** | brandable/descriptive | Embroiderers say "hoop-ready file"; instantly meaningful | "hoop-ready DST/PES from any image" pairs with every format term | .com/.app = a basketball tracker; .io unresolved | Non-embroidery only. Low–medium |
| 3 | **Punchr** / **Punchwork** | brandable (industry slang) | Insider credibility with shops | "auto-punch your logo" — but Brother owns "Auto Punch" as a feature name | .com/.io taken by unrelated apps | Medium |
| 4 | **LogoStitch** | descriptive | Contains "logo" — the highest-commercial sub-intent | near exact-match for logo digitizing pages | .com registered, no site | Low |
| 5 | **OneStitch** | descriptive | "One click, one file" | "OneStitch auto digitizer" | .com is a live unrelated site | Low–medium |
| 6 | **Digitizely** | descriptive | Carries the head keyword; reads as SaaS | strongest raw keyword carry | .com parked on Afternic (buyable) | Low |
| 7 | **Sewable** | brandable | Softer sibling of Stitchable | tagline | .com registered, no site | Low |
| 8 | **Threadwise** | brandable | The tool makes the smart stitch decisions | tagline | .com parked on Afternic | Low–medium ("Threads ES") |
| 9 | **HoopFile** | descriptive | The file you put in the hoop | "hoop file from image" | .com live unrelated | Low |
| 10 | **StitchPunch** | descriptive | Both industry words | "stitch punch digitizer" | .com registered | Low |
| 11 | **Fritsch Digitizer** | Fritsch tie | Keeps the family brand + the head noun | brand + keyword | unchecked | **Fritsch In Stitches** confusion. Medium |
| 12 | *"by Fritsch's Stitches"* byline | Fritsch tie | Company byline on any of #1–10 rather than in the product name | none needed | — | None |

### Top 3

1. **Stitchable** — pronounceable, self-explanatory, no embroidery collision,
   and it survives the "AI" fashion cycle (StitchForge / Stitch AI / EmbroidAI
   will date together). Tagline: *"Stitchable — image to embroidery file, no
   digitizing skills."*
2. **HoopReady** — the phrase embroiderers already use for the deliverable;
   strongest fit with the "no skill required" promise. Cost: .com is a
   basketball app, so .io/.app or `gethoopready.com`.
3. **Digitizely** — the SEO-led pick: carries the head keyword, domain parked
   and likely purchasable, no collisions. Catch: sounds like every "-ly" SaaS.

Recommendation: product name from the top two, **Fritsch's Stitches as the
company byline**. Do not put "Fritsch" in the product name — Fritsch In
Stitches already owns that SERP in the sewing niche.

---

## C. How to rank first

### C1. First five keyword clusters (intent × winnability)

| Priority | Cluster | Why |
|---|---|---|
| 1 | **convert image to embroidery file (free / online)** | Highest-intent; currently won by *service blog posts*, not a tool. A real free tool page with a live demo beats a 2,000-word guide. |
| 2 | **digitize logo for embroidery (online / free)** | SERP is Printify / Etsy / $10 services; no self-serve tool ranks. |
| 3 | **png to pes / jpg to dst / image to pes converter** | Huge long tail; incumbents are fake converters Google will eventually demote; StitchFast and EmbroidAI prove per-format pages rank. |
| 4 | **AI embroidery digitizer (free)** | Emerging head term; only a service and Ember hold it. |
| 5 | **free auto digitizing embroidery software (mac / ipad / online)** | The device modifiers are a gift for a browser app; every desktop incumbent loses on "iPad". |

Skip for now: "embroidery digitizing software" (Wilcom/Hatch/Embird own it);
"embroidery file converter" (wrong intent).

### C2. Site architecture

```
/                       <name> — turn any image into an embroidery file (tool above the fold)
/convert/png-to-pes     one page per (input × output): png|jpg|svg × pes|dst|jef|exp|vp3|xxx (~18)
/for/brother  /for/janome  /for/tajima  /for/bernina  /for/babylock   format + hoop sizes + USB loading
/use/hat  /use/left-chest  /use/patch  /use/towel                     size limits, stitch counts, what fails
/logo-digitizing        the "digitize logo for embroidery" money page (vs. a $10 service: instant, revise free)
/fonts                  lettering — "embroidery fonts online"
/free-tools/viewer  /free-tools/dst-to-pes                             link bait
/learn/what-is-a-dst-file  /learn/pes-vs-dst  /learn/embroidery-file-formats
/vs/hatch  /vs/ember  /vs/embrowser  /vs/sewart                         honest comparisons
```

Each format/brand page must contain something only the tool knows (real
sewn size in mm, stitch count, colour count from a sample) — VectoSolve's
"sewn size before you pay" is the model. Do not template 18 identical pages;
Google's thin-content filter folds them.

### C3. Content that earns links

- **The free tool itself**, with a no-login path (EmbroidAI's "free, no
  login" is why it ranks). Let the free tier download a real file at reduced
  size or with a stitch cap rather than watermarking.
- **Free DST/PES viewer + file→file converter** — the "5 free converters"
  roundups (SewingMachineFun, DigitEmb) will add it.
- **"Embroidery file formats" table** (extension, machine, max colours,
  trims, header quirks). Nobody in the tool wave has one.
- **A public benchmark**: the same 10 logos through Ember, Embrowser, SewFlow,
  Stitchist, Hatch auto-digitize, and ours — sewn out and photographed.
  Sew-outs are the one thing content farms cannot fake. (This also happens to
  be exactly the physical evidence ROADMAP gate 1 keeps asking for.)
- Get into the roundups that already rank: SewingMachineFun's free-software
  post, MachineEmbroideryGeek, EmbPunch's "we tested them all", SewFlow's own
  2026 list.

### C4. Technical SEO for this stack

`app/package.json` is **plain Vite + Svelte 5, not SvelteKit**, and
`index.html` ships `<title>EMB Bot Studio</title>` with no description. There
is no crawlable marketing surface at all today.

- **Split marketing from app.** Either (a) a SvelteKit site with
  `adapter-static` prerendering `/`, `/convert/*`, `/for/*`, `/learn/*` with
  the Studio mounted under `/app`, or (b) keep the Vite app as-is at
  `app.<domain>` and build the marketing pages with any SSG. (b) is the
  lower-risk path for the working app.
- Per page: unique `<title>` (≤60 chars, keyword first), meta description,
  canonical, OG/Twitter image showing a before/after sew-out.
- Structured data: `SoftwareApplication` (with `offers`,
  `applicationCategory`, `operatingSystem: "Web"`) on `/`; `FAQPage` on every
  format/brand page (every incumbent that ranks has one); `HowTo` on the
  "convert X to Y" pages; `BreadcrumbList` sitewide.
- `sitemap.xml` + `robots.txt`; Search Console day one.
- Core Web Vitals: marketing pages must not load the digitizer bundle or the
  font library; LCP should be a static image of a sew-out.
- The free tool must work without login and without JS-only routing so the
  demo URL is shareable and indexable.

### C5. Off-page

- **Reddit**: r/embroidery ~1.03M (mostly hand), **r/machine_embroidery
  ~39.5K** (the target). A tool link only in reply to "how do I turn this
  picture into a PES" threads, plus the sew-out benchmark post.
- **Facebook groups**: `groups/brothersewing` and `groups/hatchusergroup`
  surfaced repeatedly for "convert jpg for my Brother".
- **YouTube**: Embroidery Legacy 135K subs, Ricoma 195K, Embroidery Library
  71.5K. Send them the benchmark; make a 2-minute "png to pes free" video —
  YouTube results appear in these SERPs.
- **Etsy**: "convert jpg to pes file" is an Etsy *market page* on Google
  page 1 — those sellers are the $10 human competitors, and some will use the
  tool to speed their own work. A referral tier for Etsy digitizers is cheap
  distribution.
- **Roundup authors**: MachineEmbroideryGeek, SewingMachineFun, EmbPunch,
  MaggieFrames / MagneticHoop / HoopTalent (hoop retailers publishing "free
  digitizing" guides at volume; they take submissions).

### C6. Realistic timeline

- **Weeks 0–4**: name + domain, marketing site with tool embedded, 6 format
  pages, Search Console. Expect nothing yet.
- **Months 2–4**: long-tail format/brand pages start ranking (weak SERPs).
  "png to pes converter free" page 1 is plausible.
- **Months 4–9**: "convert image to embroidery file free" and "digitize logo
  for embroidery online" top-3 is achievable *if* the benchmark content and
  20–40 referring domains from the roundups land; the current holders are
  service blogs with no product.
- **"Embroidery digitizing software" #1**: not realistic against Wilcom /
  Hatch / Embird in under 2 years; target the "online / free / mac / ipad"
  modifiers instead.
- **The real race** is Ember (on 7 of 11 SERPs from the homepage alone) and
  StitchFast / EmbroidAI (already doing per-format pages). Whoever ships the
  C2 architecture first with a genuinely free demo owns the image→file
  cluster; none of them has done C3 yet.

---

## D. "Stitchable" — domains, trademark, SEO (follow-up, same day)

Kent asked for more on the top pick: *"ensure domains are not owned and are
reasonably priced … see if SEO is favorable with Stitchable."* Checked with
RDAP (Verisign, Google Registry, Identity Digital), registrar price pages,
aftermarket listings, trademark mirrors and searches. **Caveats:** USPTO's
own search refused every fetch, so marks are via Justia / BetterTrademark
mirrors; WIPO's database is a JS app and international marks are
unverified; Instagram, X and GitHub blocked the crawler where noted.

### D1. Domains

| Domain | Status | Registered → expires | Serving | Price |
|---|---|---|---|---|
| **stitchable.com** | **TAKEN** | 2015-03-12 → 2027-03-12 (Network Solutions) | HostGator-hosted site, answers 406 to crawlers; not parked | **Not for sale** on Afternic / Dan / Sedo; private offer only |
| stitchable.net | **available** | — | — | ~$11–13 |
| **stitchable.io** | **available** | — | — | ~$28–35 yr 1, ~$50 renew |
| stitchable.app | taken | 2026-05-10 → 2027 (Namecheap) | Cloudflare Access login wall (private project) | not listed |
| stitchable.co | taken, for sale | unverified | GoDaddy parked | **Afternic $1,988** buy-now |
| stitchable.ai | taken, **in use** | 2025-10-26 → 2027 | "Stitchable Pro — AI Video Editor", live freemium product, GitHub org `Stitchable-ai` | not for sale |
| stitchable.dev | taken | 2026-05-10 (same buyer as .app) | no response | not listed |
| stitchable.studio | taken | 2020-06-08 → 2027 (GoDaddy) | no response | not listed |
| getstitchable.com / trystitchable.com / stitchableapp.com | **available** | — | — | ~$10–11 each |
| stichable.com (typo) | **available** | — | — | ~$10 |

Registrar prices from Porkbun's own page and Cloudflare / Namecheap mirrors
dated 2026-09-29 and 2026-04-21. Verisign raises the .com wholesale fee
2026-11-01 (+$0.71).

**If bought:** `stitchable.io` primary + `getstitchable.com`,
`stitchableapp.com`, `stitchable.net`, `stichable.com` as redirects — about
**$65 first year, ~$95/yr after**. `.co` at $1,988 is a weak upgrade over
`.io`. **`.com` is the prize and it is not for sale** — it has been someone's
hosted site since 2015.

### D2. Trademark and existing use

- **USPTO (via mirrors):** three "STITCHABLE …" marks, **all dead** —
  STITCHABLE JOURNAL (class 26, abandoned 2010), STITCHABLE STENCILS (class
  16, cancelled 2009), STITCHABLE PILLOW TOPPER (class 26, abandoned 1998).
  No live mark found in class 9 / 40 / 42. Note every one of them paired the
  word with a noun — the pattern a descriptive word needs to register.
- **The direct collision is Stitch-Able, Mt. Pleasant SC** — an *embroidery*
  business (custom monogrammed and embroidered gifts, in-house production) at
  stitch-able.com since 2013, Etsy `StitchAbleDesigns`, **facebook.com/stitchable**,
  Instagram `@stitch_able`. Same industry, same spoken name, 13 years of use.
  No registered mark found, but common-law rights in embroidery services are
  plausible, and it is a customer-confusion problem on day one.
- **Other uses:** Stitchable Pro (the AI video editor above — unrelated class,
  same exact brand string); "Stitchable Neural Networks" (CVPR 2023, ranks
  page 1 for the bare word); Carly J. Stitchables (Etsy); StitchableCards;
  WaffleFlower "Stitchables" die line; two GitHub repos named `stitchable`
  (one a cross-stitch pattern app).
- **Handles:** facebook.com/stitchable **taken (Stitch-Able)**;
  tiktok.com/@stitchable **taken** (2016, dormant); youtube.com/@stitchable
  **taken** (1 video); instagram.com/stitchable unverified (login wall) but
  `@stitchable_` exists, which suggests the bare one is gone; x.com and
  github.com unverified (blocked).

### D3. SEO favorability

- **Page 1 for the bare word today:** three dictionary entries (Wordnik,
  Wiktionary, YourDictionary), Instagram `@stitchable_`, Etsy's
  `/market/stitchable`, Facebook Stitch-Able, the CVPR paper, WaffleFlower.
  "stitchable embroidery" → 123Stitch "Stitchable Embroidery Kits",
  Dimensions "Stitchable Cards" kits. **No single site owns the term, but the
  SERP is a crowd of adjective uses, not empty.**
- **The generic-adjective problem is in exactly this category.** Retail:
  "Stitchable Cross Stitch Kits", "Stamped Stitchable". Competing apps'
  copy: Stitchel "convert photographs … into *stitchable* charts", StitchALot
  "converts photos … into a *stitchable* pattern". Digitizing blogs: "into a
  *stitchable* reality", "into *stitchable* designs". **"Stitchable" is
  already the industry's word for the output of this product** — great for
  meaning, bad for ownability: a bare descriptive word is the kind USPTO
  refuses or pushes to the Supplemental Register.
- **No keyword in the name costs little.** Google's own guidance: pick the
  name that is best for the business; keywords in a domain have minimal
  effect. John Mueller (2023): not a fan of keyword domains — "everyone
  thinks you're a spammer … you have no brand name"; (2020) exact-match
  domains "don't get a ranking boost". Rankings for "embroidery digitizing"
  come from content either way. What a generic word DOES cost is the
  navigational query: people already type "stitchable" meaning other things.
- **Spelling / voice:** "stitch-able" (the SC competitor's spelling) is
  identical spoken. "stichable" is the obvious typo and its .com is free.

### D4. Verdict

**Domains: cautious yes; brand as-is: no.** `stitchable.io` plus the four
defensive `.com`s cost ~$65 and are worth holding while deciding; do not
chase `.com` (not for sale) or `.co` ($1,988). The two real risks are
**Stitch-Able of Mt. Pleasant SC** (same industry, same spoken name, the
Facebook handle, 13 years) and **the word being the category's own
adjective** (weak mark, a SERP shared permanently with dictionaries, kits
and a CVPR paper). If the direction survives those, the ownable forms are
"Stitchable" + a distinctive noun, or a compound such as *GetStitchable* —
the bare word is not. **HoopReady** and **Digitizely** from §B were not
re-checked at this depth and would need the same pass before a purchase.

---

## E. Ten names, measured (round 3, same day)

Kent: *"Provide 10 names with measurables and statistics alongside them to
review."* Measured from the sandbox: Verisign RDAP (.com), Identity Digital
registry RDAP (.io — rdap.org answers 404 even for registered .io names, so
only the registry endpoint counts), rdap.org (.app, control-checked against
stitch.app), a curl of each homepage, Afternic / HugeDomains / Sedo, the
Trademarkia mirror (Justia, uspto.report and USPTO itself returned 403 or a
JS wall), TikTok page JSON, YouTube @handles, web search. Registrar prices
fetched from Porkbun the same day: **.com $11.08, .io $28.12 first year /
$51.80 renew, .app $8.75 / $14.93.**

One substitution: **HoopFile** is dead on arrival — hoopfile.com (registered
2026-09-03) is a live "Embroidery File Converter & Viewer — Free Online".
Replaced by the coined **DigiHoop**; **Hoopwise** added as the tenth.

Composite score weights: cheap .com (high), no same-industry collision
(high), no live mark in class 9/40/42 (high), handles (medium), SERP
crowding (medium), keyword carried (low), mechanics (low).

| # | Name | .com | .io | .app | Mark (exact) | Same-industry collision | Handles TT/YT/IG | SERP | Chars/syll./keyword | Score |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **DigiHoop** | ✅ free ($11) | ✅ | ✅ | ✅ none | ✅ none (a 2011 LED-hoop Kickstarter; basketball "Digi Hoops") | ✅ / ❌ / ⚠️ | Med | 8 / 3 / digi-+hoop | **8** |
| 2 | **Digitizely** | ⚠️ reg. 2016, parked, no listing, price unknown | ✅ | ✅ | ✅ none | ✅ none (a PowerPoint template) | ✅ / ✅ / ⚠️ | Low | 10 / 4 / digitiz- | **6** |
| 3 | **GetStitchable** | ✅ free | ✅ | ✅ | ✅ none | ⚠️ Stitch-Able (SC shop), stitchable.com, **GetStitch** apparel brand | ✅ / ✅ / ⚠️ | Med-High | 13 / 4 / stitch | **6** |
| 4 | **StitchPunch** | ⚠️ reg. 2024, parked, no listing | ✅ | ✅ | ✅ none (PUNCH STITCH dead 1984) | ⚠️ "-Punch" is the human-digitizing-service namespace (EmbPunch, ExpertsPunch, DigitPunch…) | ❌ / ❌ / ⚠️ | Med | 11 / 2 / stitch+punch | **5** |
| 5 | **HoopReady** | ❌ live basketball tracker (reg. 2026-02) | ✅ | ❌ taken 2026-09-16 | ✅ none | ✅ none in embroidery | ✅ / ✅ / ⚠️ | Low | 9 / 3 / hoop | **4** |
| 6 | **Sewable** | ⚠️ reg. 2010, parked | ✅ | ✅ | ⚠️ SEWABLE cl. 7/26 filed 2022, dead 2023 | ⚠️ dictionary word (OED 1848); "SewAble" prosthesis | ❌ / ❌ / ⚠️ | High | 7 / 3 / sew | **3** |
| 7 | **LogoStitch** | ❌ held since 2001, dormant | ✅ | ✅ | ✅ none | ❌ four embroidery shops (Pittsburgh PA, UK, NSW, Jamaica) | ✅ / ✅ / ⚠️ | High | 10 / 3 / logo+stitch | **2** |
| 8 | **OneStitch** | ❌ **Afternic $23,995** | ✅ | ✅ | ✅ none exact | ❌ OneStitch UK embroidery/workwear; apparel; Etsy | ❌ / ❌ / ❌ | High | 9 / 3 / stitch | **2** |
| 9 | **Hoopwise** | ❌ **HugeDomains $2,495** | ✅ | ✅ | ⚠️ SPORTWISE® covers a "Hoopwise" program | ✅ none in embroidery; three basketball brands | ❌ / ❌ / ⚠️ | High | 8 / 2 / hoop | **2** |
| 10 | **Threadwise** | ❌ **Afternic $24,995** | ❌ | ❌ | ❌ ThreadWise AI (Denver, 2025, funded) reportedly holds a cl. 42 mark | ✅ none in embroidery | ❌ / ❌ / ⚠️ | High | 10 / 2 / thread | **1** |

IG = Instagram, a login wall from the sandbox; ⚠️ means search surfaced no
profile, not that the handle is free.

### Notes that decide it

- **DigiHoop** is the only triple-clean name: .com, .io and .app all
  unregistered (≈$50 to lock all three), no mark found, nothing in
  embroidery or sewing, TikTok free. Reads "digitize + hoop" on first
  hearing and spells unambiguously; digihoops.com (the plural typo) is free
  too. Weakness: "digi-" is a slightly dated prefix, and the LED-hoop
  Kickstarter would sit on page 1 until outranked.
- **Digitizely** has the cleanest namespace of the ten (nothing but a slide
  template) and free .io/.app and handles, but the .com is a 2016 parked
  registration with no visible price — a domainer, likely four figures.
  Both misspellings (digitisely, digitizly) are taken.
- **GetStitchable** is fully registrable but inherits every round-2
  Stitchable collision and adds GetStitch (an active embroidered-apparel
  brand); the "Get-" reads as the workaround it is.
- **StitchPunch** has the best mechanics (two syllables, both the trade's own
  words) but stitchpunch.com is parked at unknown price, both handles are
  taken, and "-Punch" names are how the *human* digitizing services brand
  themselves — most of them advertise "never auto-digitized".
- **HoopReady** lost its .app two weeks ago to the basketball app that owns
  the .com; a .io-only brand beside a same-name live app is a bad trade.
- Spare, domains only: **StitchSet** — .com/.io/.app all unregistered; no
  mark or collision search done.

### Ranked

1. **DigiHoop** — buy .com/.io/.app tonight for ~$50; no live mark, no
   embroidery collision, both target keywords in the name.
2. **Digitizely** — ties for first if the .com owner sells for low four
   figures; otherwise a .io brand.
3. **GetStitchable** — only if "Stitchable" as a *word* in the product is the
   goal and the brand can live with a prefix. StitchPunch is the alternative
   third if stitchpunch.com can be had cheaply.

### Not verifiable from the sandbox — check before buying

USPTO TESS/TSDR direct search for DIGIHOOP, DIGITIZELY and STITCHABLE (word
and design marks, classes 9/40/42), and whether ThreadWise AI's class-42 mark
and any HoopReady filing are real; Instagram `@digihoop`, `@digitizely`,
`@getstitchable` by hand; aftermarket prices for digitizely.com,
stitchpunch.com, sewable.com, logostitch.com (GoDaddy's for-sale pages
returned Access Denied — put each in a cart or a broker inquiry); and every
"available" reading confirmed in a registrar cart at checkout, since an RDAP
404 is "not in the registry", not a reservation.

---

## F. The cheeky register, measured (round 4, same day)

Kent: *"Something more clever, that my mother would be proud of, but maybe
offended by?"* Twenty-two puns generated, ten measured with the same
instruments as §E (Verisign / Identity Digital / rdap.org RDAP, Trademarkia —
Justia and USPTO block the sandbox — TikTok page JSON, YouTube handles, web
search; Instagram unverified throughout). Composite weights as before; **wit
is scored separately** so the two can be traded off.

Ruled out on sight: Stitch Witch (Dritz "Stitch Witchery"), Sucker Punch,
Just Hoop It (Nike), Punchline. Dropped after a look: Punch Drunk (Punchdrunk
theatre + the film), Sew It Goes (Afternic), Frayed Knot / Thread Zeppelin /
Sew Sue Me / Stitched Up / Sew Fetch / Get Stitched (all held, some live),
Needle Little Help (registered 2026-07-05 — someone had it three months ago),
Stitch Face (.com held).

| Name | .com | .io / .app | Live mark (exact) | Same-industry collisions | Handles TT / YT | SERP p1 | Mother test | Composite | Wit |
|---|---|---|---|---|---|---|---|---|---|
| Stitch Please | reg 2011, serves nothing; stitch-please.com a live starter site | ✅ / ✅ | **4 live**, incl. STITCH PLEASE INC. cl 25+40 "embroidery services", reg Aug 2026 | 5+ embroidery shops + a well-known podcast + a yarn line | ❌ / ❌ | 10/10 brands | proud + offended — on target | **2.1** | 5 |
| Stitch Happens | **Afternic $4,988** | ✅ / ✅ | none | 6+ sewing/embroidery shops (TX, ON, LA, FL, MI, VA) | ❌ / ❌ | 10/10 brands | proud + mildly offended | **4.1** | 5 |
| Son of a Stitch | reg 2001, dead Wix; **son-of-a-stitch.com free** | ✅ / ✅ | **LIVE cl 40 "embroidery services"** (Manning, Feb 2022) | 7+ embroidery businesses | ❌ / ✅ | 10/10 brands | offended first, proud second | **3.0** | 5 |
| Holy Stitch | **HugeDomains $4,795**; holy-stitch.com free | ✅ / ✅ | one, dead (abandoned May 2025) | one: Holy Stitch! Factory Fellowship, SF nonprofit sewing school since 2006 | ✅ / ✅ | 8/10 = the nonprofit | proud, eyebrow raised | **5.9** | 4 |
| Sew What | live embroidery & screen-print company since 1996 | ✅ / ❌ | none exact | **SewWhat-Pro** embroidery-file editor = direct category collision; theatrical drapery firm; 5+ shops | ❌ / ✅ | 10/10 brands | proud, not offended, bored | **3.4** | 3 |
| Thread Lightly | "Coming Soon" since 2005 | ✅ / ❌ (live AI tool) | two dead | 7 small businesses (embroidery, quilting, yarn, carpet) | ❌ 4.6K / ❌ | 9/10 brands | gets it only via Breaking Bad | **3.6** | 4 |
| **Hoop There It Is** | **HugeDomains $995** ($41/mo) | ❌ basketball scouting / ✅ | LIVE cl 41 "rental of sports equipment" (different class) | **none in embroidery** | ❌ 1.1K / ❌ (all basketball) | 7/10 basketball | proud; offended only by the bass line | **5.8** | 5 |
| Darn It | Darn It! Inc., garment repair/QC since 1996 | ❌ / ✅ | pending cl 25 (Darn Tough's parent) | Darn It All embroidery; Darn Knit Anyway | ❌ / ❌ | 5/10 brands | proud, zero offence | **3.3** | 3 |
| Stitch Perfect | for sale on BuyDomains, price unverified | ✅ / ❌ (live stitch-layout tool) | none | Stitch Perfect Embroidery Designs sells machine files; NeedlePaint "StitchPerfect"; DIME "Perfect Stitch" | ❌ / ✅ | 10/10 brands | proud, not offended | **4.7** | 3 |
| What the Stitch | **HugeDomains $2,995** | ✅ / ✅ | near-identical LIVE: WHAT'S THE STITCH cl 26 (needlepoint kits) | one Etsy needlepoint shop | ❌ / ❌ | 3/10 brands | offended, then laughs | **4.9** | 4 |

### Two ways to rank

**By measured risk:** Holy Stitch (5.9) · Hoop There It Is (5.8) · What the
Stitch (4.9).
**By wit:** Hoop There It Is · Son of a Stitch (unusable — live cl 40 mark) ·
Stitch Please (registered by an embroiderer, Aug 2026).

**The one name on both lists is Hoop There It Is**: the only candidate where
the trade word IS the joke; $995 buy-it-now for the .com, .app free, no
embroidery business on the phrase, the live mark is sports-equipment rental
(not software or embroidery). Its cost is social: every handle is basketball,
so it would be `@hoopthereitis-something`, and it is the longest name here at
13 characters / 4 syllables. **Holy Stitch** is the buyable offence-adjacent
option if $4,795 (or the hyphen for free) is acceptable; **Stitch Please**
and **Son of a Stitch**, the register's two flagships, are both already
someone's registered embroidery business.

Two all-free names surfaced and were NOT deep-measured: **Stitch It Good**
(Devo) and **EmbroidRage** — .com, .io and .app all unregistered on RDAP;
marks, handles and collisions unchecked.

Not verifiable from the sandbox, as in §D/§E: USPTO direct (every mark fact
is Trademarkia's index — "0 results" means none indexed, not clearance),
Instagram, Etsy shop counts (bot page), and the BuyDomains / GoDaddy lander
prices that returned 403 or no figure.

---

## G. Clever, not crude — and free (round 5, same day)

Kent, on the cheeky round: *"I don't like these, keep looking."* Register
this time: wit through meaning or an evocative craft object, the way Ember,
Loom or Figma are named — no bleeped swear, no -ify/-ly/-able/-AI. **143
names screened against Verisign RDAP**; the structural finding is that every
plain craft word (Tatami, Selvedge, Underlay, Tension, Backstitch, Bean
Stitch, Thimble, Skein…) and every obvious Stitch/Thread/Hoop + noun
compound (Stitchwright, Hooprint, Threadmap, Punchwork, Embroid…) is
registered. **The free ground is directional coinages (-ward, -side),
conjunction pairs, and pixel/bit + weft/bobbin story words.** All ten below
are **unregistered on .com, .io and .app** — registry price, no aftermarket
— with no exact-match mark on the Trademarkia mirror and TikTok / YouTube
handles free (Instagram unverified; USPTO direct not scriptable from here).

| Name | Chars/syll. | Keyword | Adjacent live marks (cl. 9/40/42) | Same-industry collision | Bare-word SERP | Composite | Clever |
|---|---|---|---|---|---|---|---|
| **Hoopward** | 8 / 2 | hoop | HOOP cl. 42 (an AI-marketing SaaS; different word) | none | empty; basketball neighbours | **9.0** | 4 |
| **Needlemap** | 9 / 3 | needle | none | none | empty | **8.5** | 4 |
| Threadnik | 9 / 2 | thread | none | none | empty | **8.5** | 3 |
| Needleside | 10 / 3 | needle | none | none | near-empty | 8.0 | 3 |
| **Needle & Nap** | 12 / 3 | needle | none; Tuft & Needle (mattresses) is a loud "needle + sleep" neighbour | none | fabric-nap how-tos | 7.0 | **5** |
| Stitchsong | 10 / 2 | stitch | none | none | Disney's Stitch, Shawn Mendes | 7.0 | 3 |
| Pixelweft | 9 / 3 | pixel | **WEFT cl. 42 live** (fabric-design SaaS) | PixelWeave apps; sibling of ruled-out PixelStitch | empty | 6.5 | 4 |
| Bitbobbin | 9 / 3 | bobbin | none in 9/40/42 | **"Bits and Bobbins"** quilt shops (OR, WA, Etsy) | those shops | 6.5 | 4 |
| Hoop & Spool | 12 / 3 | hoop | HOOP cl. 42 as above | supply shops (Bolt & Spool, Hoop and Frame); a kite winder | crowded | 6.5 | 3 |
| Evenweft | 8 / 3 | weft | **WEFT cl. 42 live** | "evenweave" is a fabric category that swallows it | drowned | 6.0 | 4 |

### The three that matter

- **Hoopward** — homeward / skyward / onward: *the image goes hoopward*. The
  story in one word, motion rather than a suffix, nothing colliding
  anywhere; the one cl. 42 HOOP mark is a whole-word AI-marketing product.
  Catch: "hoop" reads basketball to outsiders, which the Fritsch's Stitches
  byline settles.
- **Needlemap** — bitmap → needlemap: input and output in one compound, and
  "map" says the software does the routing. Zero marks, zero businesses,
  every domain and handle free. A point less witty for being descriptive.
- **Needle & Nap** — the best joke of any round that is not a swear: *nap*
  is the fabric term (velvet, fleece, towelling) and a nap is what you take
  while it digitizes. Two true meanings. Costs: an ampersand (handles become
  `needleandnap`), Tuft & Needle's national ads own "needle + sleep", and the
  bare phrase searches to sewing how-tos.

**Ranked by risk: Hoopward · Needlemap · Threadnik. By wit: Needle & Nap ·
Hoopward · Needlemap. Overlap: Hoopward and Needlemap.** Also free and not
measured further: Stitchward, Weftward, Bobbin Lane, Skein House,
Spool & Needle, and the -light / -song / -fold / -yard forms listed in the
agent's sweep (weftlight, spoollight, hoopfold, needleyard…).

Not verified: USPTO direct (Trademarkia's first page only for common-word
queries such as weft / hoop / bobbin), Instagram, state business
registrations, Etsy beyond what search surfaced. A registrar cart confirms
"free" at checkout; an RDAP 404 is not a reservation.

---

## H. Bold — the machine register (round 6, same day)

Kent's steer after round 5: *"Too soft — I want it bold"* and *"Right idea,
wrong words."* Short, hard consonants, one or two syllables, machine or verb;
the image-in-stitches-out story in plain words (punch, press, strike, set…),
no soft craft nouns, no suffix play. **115 candidates screened against the
.com registry: 30 free, 85 taken.** Every short -x / -ex / -on / -ok coinage
is gone, every single machine word (Tack, Bolt, Rivet, Anvil, Pylon) is
gone, every two-word bold pair tried (Hard Stitch, Iron Thread, Black
Needle) is gone. **What is open is verb + verb and the tack- compounds** —
the harder and less obvious the pair, the freer it is. All ten measured are
unregistered on .com, .io and .app at registry price.

| Name | Exact mark | Nearest live marks (cl. 9/40/42) | Same-industry collision | TikTok / YouTube | Bare-word SERP | Composite | Bold |
|---|---|---|---|---|---|---|---|
| **Tackpress** | none | generic TACK marks only | a London magazine publisher, closed 2019 | ✅ / ✅ | light | **8.0** | 4 |
| **Stitchset** | none | the generic STITCH set (a dating app, a health app, an API vendor, STITCH K cl. 40 sewing services, HP STITCH textile printers) | none; "stitch set" is Disney Lilo & Stitch merch | ✅ / ✅ | crowded | 7.5 | 3 |
| **Stitchrig** | none | same generic STITCH set | a Maya character rig on Gumroad (tiny) | ✅ / ✅ | light | 7.5 | 4 |
| Tackset | none | generic TACK | none; "tack set" is horse gear | ✅ / ✅ | crowded (equestrian) | 7.0 | 4 |
| Stitchjolt | none | JOLT cl. 9/42 ×2 (software) | none | ✅ / ✅ | empty | 7.0 | 4 |
| Stitchdone | none | DONE & DONE cl. 42; S STITCHDOWN pending is one letter away | none | ✅ / ✅ | empty | 7.0 | 2 |
| **Punchvolt** | none | **PUNCH! SOFTWARE cl. 9** (design software, live since 2007), VOLT cl. 9 ×3 | none in sewing | ✅ / ❌ | empty | 6.5 | **5** |
| Stitchgrit | none | GRIT cl. 9/42 | none | ✅ / ❌ | empty | 6.5 | 3 |
| Punchstrike | none | PUNCH! SOFTWARE cl. 9 | none; SERP is boxing | ✅ / ❌ | moderate | 6.0 | **5** |
| Tackbolt | **TACK BOLT — live, incontestable, cl. 6** (Allfast fasteners, since 2001) | as left | a western-tack retailer | ✅ / ✅ | moderate | 5.5 | 4 |

A lesson from the measurement: Trademarkia's one-word query MISSES spaced
marks — it said "no results" for `tackbolt` while TACK BOLT is a live
registration. Every name was re-queried as two words.

### The ones that matter

- **Tackpress** — *tack* is a real sewing verb (the temporary fastening
  stitch) and *press* is a machine; together it reads like a piece of shop
  equipment. Cleanest sheet of the ten: no mark, no prior site, every domain
  and handle open, the only namesake a dissolved magazine publisher. A
  customer hears a hardware brand first, which may be the point.
- **Stitchrig** — a *rig* is what an engineer calls the machine they built
  to do the work. Clean; the one collision is a 3D character rig. "Rig" can
  read as "rigged" to a suspicious ear.
- **Punchvolt** — the boldest thing still pronounceable: the trade's own
  word for digitizing plus an electrical unit. Clean SERP and domains, but
  YouTube is taken and **PUNCH! SOFTWARE is a live cl. 9 mark for design
  software** — a "Punch-" software brand in the design space is what an
  examiner cites. Not a bar; a real letter.
- **Stitchset** reads like *typeset* — the strongest verb analogy — but its
  .com had an unreadable live site 2019–2024 and Disney owns the phrase's
  search results.

**By risk: Tackpress · Stitchset · Stitchrig. By boldness: Punchvolt ·
Punchstrike · (Tackpress, Tackset, Stitchrig, Tackbolt). Overlap: Tackpress
and Stitchrig.** Also free, not measured: Tackstrike, Tackmint, Punchtack,
Tackpunch, Strikestitch, Stampstitch, Punchstruck, Stitchstruck, Punchjolt,
Threadgun, Stitchox, Punchox, Stitchak.

One flag for every Stitch- name in any round: HP holds STITCH (cl. 2/7) for
inkjet textile printers, and three unrelated STITCH software marks sit in
cl. 9/42 — none blocks a compound, but they belong in any attorney brief.

Not verified: USPTO direct; Wayback page bodies (stitchset.com 2019–2024 and
tackset.com 2017 are unreadable from here); GitHub handles; Instagram.

## I. "Just Stitch It" — Kent's proposal, measured (round 7, same day)

Kent asked *"just stitch it?"* after round 6. Measured the same way as
rounds 3–6, plus a trademark pass specific to the "JUST ___ IT" frame, and
two fallbacks that keep the idea: **Stitch It** and **JustStitch**.

**Composite: 2.5 / 10. Bold: 4 / 5.** It fails both high-weight gates —
the .com and the industry — and the boldness is Nike's on loan.

### Domains (RDAP, live fetch)

| Domain | State |
|---|---|
| **juststitchit.com** | **Taken since 2002-06-13** (GoDaddy, exp. 2027). Live Square Online store: "Just Stitch It Inc.", custom equine embroidery and garment printing, Tioga TX. Not parked, not for sale. |
| just-stitch-it.com, getjuststitchit.com | free |
| juststitchit.net / .io / .app / .co / .studio / .ai / .shop | all free |
| juststitch.com | taken 2006, **for sale at $4,895** (HugeDomains, or $203.96/mo × 24) |
| juststitch.io / .app / .co | free |
| stitchit.com | taken 2000 — "Stitch It" alterations and dry-cleaning chain, Canada, 50+ stores since 1989 |
| stitchit.app | taken 2022 (serves 502 today); stitchit.io / .co free |

### Trademark

- **Exact mark:** no live federal JUST STITCH IT / JUSTSTITCHIT found
  (Trademarkia `juststitchit` → 0 results; the fuzzy query surfaces
  STITCH IT USA, Ser. 76663818, **live cl. 40**, renewed 2018, and
  STITCH IT FOR U, Ser. 97450264, live cl. 35/40, 2022). Justia: STITCH IT
  (74219915, 1991) abandoned 1993; JUST STITCHIN' (1975) cancelled 1983.
  STITCHIT (Ser. 50069304, cl. 25) filed 2026, pending. USPTO direct not
  reachable from here, as in every prior round.
- **Nike's JUST DO IT.** The TTAB calls it "not only famous, but remarkably
  so," and Nike's stated policy is to oppose every "JUST ___ IT" filing.
  Outcomes, all Nike wins, none found lost:
  - *Nike v. Maher*, JUST JESU IT (2011, precedential) — confusion **and**
    dilution by blurring; "JUST ___ IT is a common template" rejected for
    lack of evidence; parody rejected ("trying to take a free ride").
  - *Nike v. Caldwell & Miles*, JUST DREW IT! (2020) — sustained; the Board
    reasoned that "DO" can implore the listener to *do* something, such as
    to *draw*. **"Stitch" is a verb and reads identically.**
  - *Nike v. Muntean*, JUST BELIEVE IT (2020) — **cl. 35 business
    consulting, not apparel** — sustained on both grounds. Different goods
    did not save it; dilution does not need related goods.
  - *Nike v. Tacvue*, JUST DAO IT (2021–2023) — "computer services, namely
    creating an online community" — a tech company; default judgment for
    Nike.
  - Also sustained: JUST DON IT! (masks), DON'T JUST DO IT, GET IT DONE
    (2024), JUST DID IT, JUSTSAYIT.
- **Read:** the mark is unregistrable in practice — filing draws an
  opposition with a 100 % observed win rate — and a C&D is likely once the
  brand is visible. Parody is not available to a commercial brand that is
  not commenting on Nike.

### Same-industry collisions

Four US businesses trade under the exact name; three embroider, one
**digitizes**:

1. **Just Stitch It, Inc.** — Tioga TX; owns the .com, IG @juststitchit,
   FB /JustStitchIt.inc; ~24 years.
2. **Just Stitch It Embroidery** — Dunnellon FL; "embroidering since 1988
   and **digitizing since 2004**". Sells the service EMB-Bot automates.
3. **Just Stitch It Embroidery** — Saint Paul MN; BBB A+, since 2004; Yelp
   updated Dec 2025.
4. **Just Stitch It Meisch Upholstery** — Caledonia MN; upholstery,
   quilting fabric, yarn; est. 1955.

All decades-old brick-and-mortar operations with common-law rights in the
embroidery field. No software or app of the name found.

### Handles and SERP

TikTok and YouTube @juststitchit **free**; Instagram **taken** (the Texas
company); Facebook /JustStitchIt.inc is the Texas company; X probably free,
unverified. Exact-phrase SERP page 1 is 100 % the four businesses above
(IG, FB ×3, Yellow Pages, Yelp ×2, the .com ×3). "stitch it" alone is the
Canadian chain, STITCH-IT Alterations (Nashville), STITCH IT (Garden City
NY, embroidery), and **Stitch AI (stitchai.us, "AI Embroidery Digitizing in
Seconds")** — a direct competitor already on "stitch" + AI digitizing.

### Fallbacks

- **Stitch It — ~2 / 10.** Worse than the candidate: live cl. 40
  registration (STITCH IT USA), the 50-store chain on the .com, STITCHIT
  pending in cl. 25, X @stitchit taken. No Nike issue, but nothing else
  clears either.
- **JustStitch — ~5.5 / 10.** .com buyable at $4,895; .io/.app/.co free;
  TikTok/YouTube free; X @JustStitch is a personal account; IG unverified.
  No JUST STITCH / JUSTSTITCH mark on Trademarkia or Justia; no company or
  app of the name found. Dropping "It" leaves the JUST ___ IT frame that
  every Nike case turned on — materially lower risk, still "Just"-adjacent
  and still generic enough to share a SERP with every shop that says "just
  stitch".

### Verdict

Two risks, either alone disqualifying for a brand meant to rank first:

- **Trademark:** the exact JUST-verb-IT pattern Nike has won on eight-plus
  times, including against non-apparel services.
- **Collision:** three decades-old embroidery shops, one a digitizer,
  already own the name, the .com, the Instagram handle, and the whole
  page-1 SERP. Ranking first for "just stitch it" would mean out-ranking
  the businesses that *are* Just Stitch It.

Not verified: USPTO direct; Instagram direct (429); X (no og:title on the
profile page); Facebook /juststitchit (login-walled).

## J. Commands without Nike's frame (round 8, same day)

Kent's direction after §I: keep the *Just Do It* energy — an imperative,
one breath, confident — on a frame Nike does not own. 26 names measured:
14 proposed, then 12 more added once a Verisign RDAP screen showed 13 of
the first 14 .coms taken (three of them registered this summer:
needledown 2026-06-11, makeitstitch 2026-06-06, threadit 2026-04-03).

Method as rounds 3–7. Unverified this round: USPTO direct (TSDR 401, TESS
404), Justia (403), every Instagram handle (302 to login), every .co
(rdap.nic.co blocked at the proxy), asking prices for punchit.com and
hoopup.com. Registrar prices from round 3: .com ≈$11, .io ≈$28, .app ≈$9.
"TT/YT/X" = TikTok / YouTube / X handle.

| # | Name | .com | .io / .app | TM (exact) | Collisions | TT/YT/X | SERP | Comp. | Bold |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Stitch Hard** | free | free / free (.ai free) | none | none | ❌/✅/✅ | low — Lilo & Stitch noise | **7.5** | **5** |
| 2 | **Stitch Loud** | free | free / free | none | none | ❌/✅/prob. | low — Lilo & Stitch clips | **7.5** | 4 |
| 3 | **Punch Anything** | free | free / free | none | none | ✅/✅/✅ | low — dictionary | **7** | 4 |
| 4 | **Punch Loud** | free | free / free | none | none | ✅/✅/✅ | low — sound effects | **7** | 4 |
| 5 | Stitch Sharp | free | free / free | none; SHARP famous cl.9 | "Sharp Stitch" tailoring channel | ✅/✅/prob. | med | 6.5 | 4 |
| 6 | Thread Hard | free | free / free | none | none | ✅/✅/✅ | med — machinists | 6.5 | 4 |
| 7 | Own the Hoop | free | free / free | none | none | ✅/✅/✅ | med — hula, basketball | 6.5 | 4 |
| 8 | Hoop Fast | free | free / free | none | generic hooping-station copy | ✅/❌/✅ | high — HoopMaster, Fast Frames | 6.5 | 4 |
| 9 | Fire the Needle | free | free / free | MOVE THE NEEDLE live cl.9 | none | ❌/✅/✅ | high — acupuncture | 6 | 4 |
| 10 | Stitch Clean | free | free / free | dead 1994 | Stitch & Clean, A Clean Stitch | ❌/✅/❌ | high — wash guides | 5.5 | 3 |
| 11 | Stitch Dead On | free | free / free | **DEAD ON live cl.9** ×5 | none | ✅/✅/✅ | Lilo & Stitch | 5.5 | 4 |
| 12 | Punch Sharp | free | free / free | none | **Prima Power "Punch Sharp"** machine | ❌/✅/✅ | Prima Power | 5 | 4 |
| 13 | Needle Down | **live site**, reg. 2026-06 (machine-review blog) | free / free | none | Needle Down Quilt Shop GA | ✅/❌/✅ | feature explainers | 4.5 | 4 |
| 14 | Get Stitching | HugeDomains **$2,695** | free / free | none | none | ✅/✅/❌ | hobby | 4.5 (6 w/ .com) | 3 |
| 15 | Stitch Now | HugeDomains **$4,795** | free / free | none | none | ❌/✅/❌ | generic | 4 (5.5) | 4 |
| 16 | Make It Stitch | HugeDomains **$1,995** | free / free | MAKE IT YOURS STITCH live cl.42 | none | ✅/✅/❌ | generic | 4 (5.5) | 3 |
| 17 | Punch It | parked since 1997, no price | ❌ / ❌ (.ai ❌) | PUNCH live cl.9 ×2 | the "-Punch" human-digitizer namespace | ❌/❌/❌ | game, film, idiom | 3.5 (5.5) | **5** |
| 18 | Go Stitch | Afternic **$9,995** | free / ❌ | none | none | ❌/❌/❌ | generic | 3.5 | 3 |
| 19 | Hoop Up | parked, no price | free / free | none | Hoop It Up Embroidery ×3 adjacent | ❌/❌/❌ | basketball | 3 | 3 |
| 20 | Punch Now | **$4,295** | free / free | none | PunchNow attendance app; Punch Me Now Embroidery | ❌/✅/❌ | the app | 3 (4.5) | 4 |
| 21 | Stitch Out | "Under Construction" since 2011 | free / free | dead cl.10 | **BERNINA Stitchout app** | ❌/❌/❌ | BERNINA | 2.5 | 4 |
| 22 | Stitch This | Afternic **$24,888** | ❌ / ❌ (all reg. 2026-03-13) | STITCH THIS dead ×2; STITCH THIS PRINT THAT live cl.40 | X @Stitchthis embroiderer | ❌/❌/❌ | generic | 2.5 | 4 |
| 23 | Hoop It | Afternic **$18,499** | ❌ / ❌ | HOOP IT UP live cl.41/28/25 | Hoop It Up Embroidery ×3; Sega arcade | ❌/❌/❌ | basketball | 2 | 4 |
| 24 | Thread It | Afternic **$27,995** | ❌ / ❌ | none | Google Threadit; THREAD IT LTD | ❌/❌/❌ | Google's app | 2 | 3 |
| 25 | Stitch On | **live** cross-stitch store, Lawrence KS | free / free | STITCH ON STITCH EMBROIDERY live cl.40 | Stitch On Stitch LLC | ❌/❌/❌ | the store | 1.5 | 3 |

### The four survivors

- **Stitch Hard — 7.5 / Bold 5.** The only name in the round that is
  triple-clean (domain, mark, industry) *and* reads as a flat command.
  .com/.io/.app/.ai all unregistered (≈$50 the set). Trademarkia page 1
  is STITCH generics (Stitch Fix cl.45, Stitch Health cl.9/42) — none
  confusable with a two-word imperative. No shop, app or Etsy store; the
  only hits are a hard-rock singer. YouTube and X free, TikTok taken
  (owner unverified). Ten characters, two syllables. Catch: "hard" implies
  effort, and the product's pitch is the opposite.
- **Stitch Loud — 7.5 / Bold 4.** Same clean sweep; X probably free
  ("Profile / X"), YouTube free, TikTok taken. Weakest keyword pull of the
  Stitch names — "loud" says nothing about digitizing — and it invites the
  wrong inference about density.
- **Punch Anything — 7 / Bold 4.** Every domain and handle free, no mark,
  no collision, and to anyone in the trade it *is* the product promise.
  Four syllables. Catch: outside the trade "punch" is a fist, and "-Punch"
  is where the human digitizers trade (Mystic Punch, Digit Punch, Quality
  Punch), several advertising "never auto-digitized".
- **Punch Loud — 7 / Bold 4.** Nine characters, all free, page 1 is
  sound-effect libraries. The "punch" caveat doubled: it reads as a boxing
  instruction outside the trade.

### Why the strong ideas fell

Punch It has no domain on any TLD checked (the .com parked 29 years, no
listing) and PUNCH is live twice in cl.9. Stitch Out is the name of
BERNINA's embroidery-machine app on both stores. Hoop It carries a live
three-class mark and an $18,499 price. Needle Down's .com turned into a
same-industry review site three months ago. A brand on a .io beside a
same-name embroidery app or blog is the round-3 HoopReady trade again.

### The register's cost

The twelve free names are free because nobody searches them. Every "low
SERP" is the same fact as "no collision": zero keyword demand. "Stitch ___"
shares page 1 with Lilo & Stitch and with Stitch AI (stitchai.us), which
already holds the "stitch + AI" position; "Punch ___" reads as violence to
the non-trade buyer. Ranking first for any of these is a brand-building
job, not an SEO one — which is what §A's demand data said the imperative
register would cost. The SEO plan in §C (content and landing pages on the
searched phrases) carries the ranking regardless of the name.

**By risk:** Stitch Hard · Stitch Loud · Punch Anything · Punch Loud ·
Thread Hard · Own the Hoop · Stitch Sharp · Hoop Fast · Fire the Needle ·
Stitch Clean. **By boldness:** Stitch Hard, Punch It (5); the rest 4.

An RDAP 404 means "not in the registry", not a reservation — confirm in a
registrar cart before announcing anything.

## K. Commands, second pass (round 9, same day)

Kent on §J's four: *"better, keep looking."* Same register. 72 command
names screened on Verisign RDAP first; 37 .coms were taken, several this
year (stitchready 2026-01, stitchfirst 2026-03, stitchbrave 2026-07,
stitchsure 2026-09-02 — someone is buying "stitch + adjective"). The 35
with a free .com went through the full pass.

Method as §J. **All 105 .io/.app/.ai lookups returned free** — no name
lost a TLD. New this round: **page-1 SERP is unverified** (Bing answers
only entity-strength phrases through the proxy; every other engine is
walled), substituted with Bing autosuggest (demand), the iTunes Search
API and Google Play (apps), and YouTube results (same-industry content).
No name has an App Store or Play app. Also new: **Google Stitch**
(stitch.withgoogle.com, "Design with AI") now tops every `stitch` query,
beside Stitch AI (stitchai.us) — "stitch + AI" is held twice.

| # | Name | TM | Collisions | TT/YT/X | Comp. | Bold |
|---|---|---|---|---|---|---|
| 1 | **Stitch Done** | none; DONE generics | none | ✅/✅/✅ | **7.5** | 4 |
| 2 | **Stitch Solved** | none; SOLVED generics | none | ✅/✅/✅ | **7.5** | 3 |
| 3 | **Hoop Anything** | none; HOOP generics | none | ✅/✅/✅ | **7** | 4 |
| 4 | **Own the Stitch** | THE STITCH cl.37/16; IN THE STITCH cl.25 | none | ✅/✅/✅ | **7** | 4 |
| 5 | **Needle First** | none | none | ✅/✅/✅ | **7** | 3 |
| 6 | Run the Needle | MOVE THE NEEDLE **live cl.9**/41/44 | none | ✅/✅/✅ | 6.5 | 4 |
| 7 | Rule the Hoop | none | none | ✅/✅/✅ | 6.5 | 4 |
| 8 | Hoop Everything | none | none | ✅/✅/✅ | 6.5 | 3 |
| 9 | Stitch Whatever | none | none | ✅/✅/❌ | 6 | 4 |
| 10 | Stitch Fearless | TAYLOR SWIFT FEARLESS **live cl.9**; FEARLESS **live cl.42** | none | ✅/✅/✅ | 6 | 4 |
| 11 | Drive the Needle | MOVE THE NEEDLE frame | none | ✅/✅/✅ | 6 | 4 |
| 12 | Stitch Fierce | FIERCE (A&F) cl.25 ×3 | small YT channel | ✅/✅/✅ | 6 | 4 |
| 13 | Stitch Once | ONCE ×10 incl. 37signals | "Count Twice Stitch Once" YT | ✅/✅/✅ | 6 | 3 |
| 14 | Punch Instant | PUNCH **live cl.9** ×2 | none | ✅/✅/✅ | 6 | 3 |
| 15 | Hoop Proud | none | none | ✅/✅/✅ | 6 | 3 |
| 16 | Stitch Instant | none | **Google Stitch "Instant prototypes"**; Stitch AI | ✅/✅/✅ | 5.5 | 2 |
| 17 | Punch Brave | PUNCH cl.9 | none | ✅/✅/❌ | 5.5 | 3 |
| 18 | Run the Stitch | THE STITCH | none | ✅/✅/❌ | 5.5 | 3 |
| 19 | Run the Hoop | none | football D-line drill | ✅/✅/✅ | 5.5 | 4 |
| 20 | Sew Instant | SEW-EURODRIVE ×6 | Liqui-Sew Instant | ✅/✅/✅ | 5.5 | 2 |
| 21 | Thread Fearless | FEARLESS cl.9/42 | Meta Threads SERP | ✅/✅/✅ | 5.5 | 3 |
| 22 | Nail the Stitch | NAILED IT frame | nail salons | ✅/✅/✅ | 5.5 | 4 |
| 23 | Stitch Proud | none | none | ❌/✅/❌ | 5 | 3 |
| 24 | Punch Proud | PUNCH cl.9 | none | ❌/✅/❌ | 5 | 3 |
| 25 | Stitch Nailed | NAILED IT! **Netflix live cl.41** | "stitch nailing" carpentry term | ✅/✅/✅ | 4.5 | 4 |
| 26 | Hit the Needle | MOVE THE NEEDLE frame | drug-slang reading | ✅/✅/✅ | 4.5 | 4 |
| 27 | Stitch Rogue | ROGUE **live cl.42** (AI assistant, 2025) +9 | Rogue x-stitch fabric | ✅/✅/✅ | 4 | 4 |
| 28 | Punch Fearless | FEARLESS cl.9/42 | **Tata "Punch Fearless" car trim** | ✅/✅/✅ | 4 | 4 |
| 29 | Punch Everything | PUNCH cl.9 | 2 YT channels; "Punching Everything" app | ❌/❌/✅ | 4 | 4 |
| 30 | Stitch Simple | THE SIMPLE STITCH live cl.12 | live crochet creator holds YT/X/TT | ❌/❌/❌ | 3.5 | 2 |
| 31 | Punch It Once | PUNCH cl.9 ×2 | Punch It Technologies | ✅/✅/✅ | 3.5 | 4 |
| 32 | Stitch Ahead | AHEAD ×9 | **A Stitch Ahead, Inc.** — embroidery + screen printing | ✅/✅/✅ | 3 | 3 |
| 33 | Stitch Straight | STRAIGHT STITCH SOCIETY live cl.16 | generic stitch name; Straight Stitch Sewing Co. on X | ✅/✅/❌ | 3 | 3 |
| 34 | Stitch Off | none | Wizard101 "Stitch-Off" holds all handles | ❌/❌/❌ | 3 | 3 |
| 35 | Stitch It Once | STITCH IT USA **live cl.40** | the 50-store Stitch It chain owns the core | ✅/✅/✅ | 3 | 3 |

### The five survivors

- **Stitch Done — 7.5 / Bold 4.** Triple-clean and reads as a verdict:
  "Stitch. Done." Ten characters, two beats; every handle free; four TLDs
  ≈ $50. Catch: a result, not a command — the energy is in the pause —
  and in running copy "stitch done" can read as past tense.
- **Stitch Solved — 7.5 / Bold 3.** Same sweep; the most on-message
  ("Digitizing, solved"). Catch: a claim, not an order, and it concedes
  stitching was a problem — the pitch, not Nike's register.
- **Hoop Anything — 7 / Bold 4.** §J's Punch Anything with the trade's
  other word; every domain and handle free; HOOP marks are basketball and
  kids' products. Catch: "hoop" names the frame the customer already owns,
  not the digitizing act, and reads hula or basketball outside the trade.
- **Own the Stitch — 7 / Bold 4.** All free; THE STITCH is an Atlanta
  highway-cap project (cl.37) and a 2006 cl.16 mark, IN THE STITCH cl.25,
  none software. The sports-cliché frame gives swagger without a famous
  mark. Catch: SERP is Oprah's OWN; "the Stitch" is a Disney character to
  half the internet.
- **Needle First — 7 / Bold 3.** All free; NEEDLE marks are archery,
  wine, quilting supplies. Reads as a design principle ("needle-first,
  like mobile-first"), which is what the product is. Catch: not an
  imperative, and it also reads medical.

Below them: Run the Needle is literal to the trade but MOVE THE NEEDLE is
live in cl.9 one verb away; Stitch Fearless has two live marks in exactly
the classes to file (Taylor Swift cl.9, Fearless IP cl.42); Stitch Whatever
has the most attitude and the wrong inference (indifferent to quality).

Nike-frame check: Stitch It Once and Punch It Once are verb-IT-adverb, not
JUST-verb-IT; neither trips §I's precedents, but both carry cores that
failed on their own.

**By risk:** Stitch Done · Stitch Solved · Hoop Anything · Own the Stitch ·
Needle First · Run the Needle · Rule the Hoop · Hoop Everything · Stitch
Whatever · Stitch Fearless. **By boldness:** no 5 this round; 4s — Stitch
Done, Stitch Whatever, Own the Stitch, Run the Needle, Rule the Hoop, Hoop
Anything, Drive the Needle, Stitch Fearless, Stitch Fierce.

**Two biggest risks:** the "stitch + AI" position is held twice (Stitch AI
for digitizing, Google Stitch for AI design), so any Stitch-name ranks
behind both from day one; and every clean name is clean because nobody
searches it (autosuggest empty for all five), so §C's plan carries the
ranking regardless.

Not verified: USPTO (TSDR 401, tmsearch 405), Justia (403), Instagram
(302), .co, page-1 SERP on any engine, Etsy (403), astitchahead.com (no
response; the YouTube channel is the evidence). An RDAP 404 is "not in the
registry", not a reservation.

## L. The pick — Stitch Done (2026-09-30)

Kent chose **Stitch Done** from §K. Re-verified live before writing the
buy list: stitchdone .com/.io/.app/.ai/.net/.studio and stitch-done.com
all free; YouTube, TikTok and X @stitchdone free (X returns an explicit
"User Profile Not Found"); Instagram and GitHub unverifiable from here;
Trademarkia returns no result containing the phrase. Buy list, handle
list and the attorney one-pager: `docs/stitch-done-buy-list-2026-09-30.md`.
