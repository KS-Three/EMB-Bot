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
