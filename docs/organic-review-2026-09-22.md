# Organic review, 2026-09-22 — read the goal, ignore the direction

Kent's instruction: read what EMB-Bot is *for*, deliberately **not** what has
been built or where the roadmap points, then say whether the steering has been
wrong and what has gone unexplored.

Method, stated so the bias is legible: `PRODUCT.md` and `README.md` were read
first and nothing else. `ROADMAP.md`, `MASTER_SCOPE.md`, `DOCTRINE.md` and the
112 files in `docs/` were opened only *after* a view had formed, and only to
check whether an idea was already explored — not to source one. Every number
below was measured in this session, not quoted from a doc.

**Headline:** the engine work is not wasted, but it is not what stands between
this repo and a customer. Two things are: nobody can install the product, and
the entire quality program is calibrated against one client's logo.

## 1. The goal, as the goal docs state it

- Local, browser-based, **no account, no subscription, desktop-only**.
- Benchmark is **Ember**; Wilcom and Hatch explicitly are not the bar.
- **Kent ruled 2026-08-11: engine quality is a parallel investment, NOT a
  launch gate.** The 7-row checklist is the launch bar.
- Launch checklist today: **6 of 7 green.** Row 3 (starter design pack) has no
  trace in the repo. Billing is `Open — not yet decided`.

## 2. Three real problems

### 2.1 There is no distribution path, and it is on no checklist

Swept the whole tree for `electron|tauri|pyinstaller|installer|code-sign|notariz`
across `*.md`, `*.json`, `*.mjs`, `*.py`. **Zero hits in EMB-Bot's own code.**
The only matches are vendored `.venv` noise and docs *describing Ember's* Tauri
bridge app.

So shipping today means: clone a public repo, `npm install`, build a
`python3.12` venv by hand, and run `tools/start-emb-bot.ps1`, which opens two
PowerShell windows that each block until Ctrl+C.

Every launch row is green and none of them is *"a customer can install it."*
This is a real problem, not a nitpick, and it is invisible precisely because
the checklist does not carry a row for it.

### 2.2 The quality program's ground truth is thin

> **CORRECTED 2026-09-28. This section originally claimed the ground truth was
> "n≈1 — one client, Becker", on the strength of a directory listing of
> `digitizer/testdata/reference/` (13 files). That was wrong, and the method
> was the error: the corpus is not a directory, it is a registry in code.**
>
> `digitizer/tools/pro_parity/blockcensus.py` defines `FIXTURES`, which at the
> time of the original review already paired **five genuine artwork files with
> five different clients** — Becker Marine, script TIRES, Hotel Fremont,
> Golden Tee and Precision Drone — and separately tagged the four Becker
> preview renders `pro-derived-render`, **skipped by default and never
> aggregated**. The circularity risk this review presented as a discovery was
> already documented in that module's own docstring, credited to MASTER_SCOPE
> "Corrections" / PR #222, and enforced in code.
>
> So the honest number was **n≈5 clients**, not n≈1. As of 2026-09-28 it is
> **11 artwork fixtures across 8 clients** — see §2.2a.
>
> The finding that survives is weaker and still worth stating: **five clients
> is thin** for a yardstick whose exit condition is agreeing with one person's
> eye. What does *not* survive is the claim that the whole program rests on a
> single logo family.

`scratch_corpus/` holds 37 third-party `.dst` files with **no source art**, so
those cannot ground a raster→stitch comparison at all — that part was right,
and it is why raw file counts mislead here.

Measured against that sample:

| area | measured |
|---|---|
| `digitizer/digitizer_core/` | **43,042** lines |
| `digitizer/tests/` | **55,620** lines |
| `docs/*.md` | **86,932** lines across **112** files |
| commits touching `digitizer/` | **743** of 1,999 |

`ROADMAP.md` Phase 1's exit condition is *"the metric's ranking agrees with
Kent's visual ranking."* Agreement measured across five designs is a weak
basis for that gate, and it has been the active phase for the project's whole
life. *(This paragraph originally said the gate was "unpassable as specified
from a single sample" — see the correction above.)*

### 2.2a What changed on 2026-09-28

The corpus went from **5 artwork fixtures / 5 clients** to **11 / 8**, at zero
cost, from files already on disk.

Most digitizing vendors ship a two-panel preview beside the stitch file: the
artwork the customer sent in one panel, a simulation of their own stitches in
the other. That artwork is a legitimate pipeline input — unlike the simulation,
it is not derived from the pro's answer — and it was simply never cut out.
`tools/pro_parity/preview_split.py` now does that, adding M-FAB (×2), C Golke
Roofing, To a T Machine (×2) and the Hotel Fremont patch.

**Two things that work is careful about, both learned the hard way here:**

- **Which panel is artwork is DATA, not inference.** Two image statistics were
  measured as candidate discriminators and both failed — colour count dies on
  a palettised source, and flatness scored Becker's preview (which contains no
  artwork at all, both panels being simulations) *above* a genuine artwork
  file. There is no threshold that accepts the real ones and refuses Becker, so
  a hand-set manifest records the choice and anything unlisted is refused
  rather than guessed at. The numbers are in that module's docstring.
- **Becker is deliberately excluded.** Its preview has no artwork panel to
  recover. That is exactly why `blockcensus.py` tags those files
  `pro-derived-render` and keeps them out of aggregates.

**A candidate the corpus did not have before:** `toat_machine` and
`toat_beanie` are the same logo digitized twice, into two different `.PES`
files (92,877 vs 93,313 bytes, differing md5). If those came from two
different professionals, that is a free sample of **inter-pro variance** — the
quantity §3.2 argues is worth paying for and which nothing in this repo has
ever measured. Provenance is unrecorded, so it is a candidate and not a result;
settling it costs one question to the shop.

### 2.3 The 2026-08-11 ruling was made and then never funded

`ROADMAP.md` gives the engine track five phases over ~30 lines. The launch
track is **one line**: *"Starter design pack (sourcing decision and billing
pending)."*

Commits by area, 2026-07-22 → 2026-09-22 (1,999 total in 62 days):

- `digitizer/` — **743**
- `docs/` — **627**
- `app/` — **308**

Font-license compliance got a hard gate, a full audit, two CI tests and four
fonts deleted on principle, because it *precedes the first dollar*. The
**mechanism** for the first dollar has been `Open — not yet decided` since
August. That inversion is the steering error. The ruling itself was right.

## 3. Unexplored opportunities

### 3.1 The browser-only half already builds and ships — measured

```
cd app && npm run build
✓ built in 2.26s
dist total: 57M    dist/engine: 25 files    dist/fonts/bin: 85 fonts
vite base: "./"    index.html: src="./engine/units.js" …
```

Self-contained, relative paths, no CDN runtime dependency. Text, the 85-font
satin library, shapes, manual draw, DST import and six export formats need
**no Python at all**, and `app/scripts/ensure-digitizer.mjs` already exits 0
when the venv is missing, falling back to the Studio's own offline note.

**And it is not even missing the image lane.** `project.js:412`
`resolveArtworkType(digitizerHealth)` returns `"digitized"` with the service up
and **`"image"` with it down** — the browser engine's own flatten + digitize
path (`src/flatten.js`, `src/digitize.js`), which README pins at a ~3 mm satin
cutoff against the Python lane's ~5 mm. Projects live in `localStorage`
(`app/src/lib/projects.js`), so nothing about the no-account promise depends on
the service either. The static dist is a **complete product**; `digitizer/` is a
quality upgrade on one lane, not the missing half of the app.

**A zero-install web version of the non-Python product is one deploy away
today.** It also lands exactly on Ember's proven tier boundary — manual tools
free, automation paid ($9.99/mo, 25k users) — which turns `digitizer/` from a
shipping blocker into the paid download rather than the thing holding the
product hostage.

The "desktop-only, local, no account" posture was chosen as a differentiator
*against* a subscription competitor. It is currently costing distribution while
the engine is being matched to that competitor anyway.

**Picked to act on 2026-09-22, then REVERSED by Kent 2026-09-28 — he does not
want a website now.** It was built and verified (PR #550: a `VITE_HOSTED` build
flag, a Pages deploy job, and a Playwright rig driving a real production build
with no digitizer service — engine 569/0, studio 60 files/1274 tests, hosted
e2e 6/6). Nothing was ever deployed: GitHub Pages was never enabled on the
repo, so no site exists. PR #550 was closed with the branch left intact at
`45464212` if this is ever revisited.

**The finding stands regardless of that reversal**, and is the reason it is
written down here rather than deleted with the branch: the distribution gap is
real, the static build genuinely works today, and whether to walk through that
door is a business call, not an engineering one.

### 3.2 Buy inter-pro variance — and only that

> **CORRECTED 2026-09-28.** This section originally proposed sending 20–30
> logos to 3–4 services "at $10–20 each" and called it **~$400**. The
> arithmetic was wrong: 20–30 × 3–4 × $10–20 is **$600–2,400**. It also
> proposed buying breadth that §2.2a then obtained for free.

**Breadth no longer needs buying.** The vendor previews already on disk
carried recoverable artwork, which took the corpus from 5 designs to 11 and
from 5 clients to 8 at zero cost (§2.2a). Anything further of that kind is
another look through the shop's own archive, not a purchase.

**Inter-pro variance is the one thing money still buys.** How much do two
professionals disagree with each other on the same logo? That number is the
ceiling the scorecard should be measured against — without it, "42.5 against a
pro's 75–84" has no denominator, and a target of 90 may be chasing noise.
Nothing in this repo measures it.

Researched properly on 2026-09-28
(`docs/paired-ground-truth-sourcing-2026-09-28.md`), the real cost is far
lower than this section first claimed:

- Published left-chest digitizing runs **$6–15 per logo**, not $10–20.
- **Four vendors offer a free or near-free first order**, so a panel of six
  vendors on one logo is ~$58, and a one-logo pilot lands around **$29**.
- No free source supplies professional pairs: the only open artwork+stitch
  pairs found were 21 hobbyist uploads, of which the 7 logo-like ones are all
  recreations of trademarked marks, under a licence chain that contradicts its
  own files. No academic stitch-file dataset exists — every "paired dataset" in
  the literature pairs images with images.

**And there may be a free sample already on disk.** `toat_machine` and
`toat_beanie` are the same logo digitized twice into two different `.PES`
files. If two different professionals produced them, that is inter-pro
variance for nothing; see §2.2a.

### 3.3 The non-goals are the jobs the engine already wins

`PRODUCT.md` parks **team names** and **monogram frames**. Both are typed-satin
jobs, and typed satin is the one documented *lead*: 85 hand-authored satin
fonts against Ember's 25, real columns rather than auto-traced outlines
(`docs/scope-digest/competitors.md`, "Not gaps — EMB-Bot ahead").

A roster feature (paste 30 names → 30 files + a production sheet) rides the
existing text lane. It is the only candidate feature where EMB-Bot would be
*better* than Ember rather than 60% of it.

Same shape of argument for **imported-design resize / re-density**, also a
non-goal: `src/dstimport.js` is already wired into `DesignPanel.svelte`, it is
the most frequent real job in a shop that receives customer files, and
re-spacing an existing stitch structure is a far easier problem than
raster→stitch.

Both reverse explicit rulings, so both are Kent's call, not a session's.

### 3.4 A VLM for the judgment layer — genuinely never considered

Grepped all 112 docs for `VLM|vision-language|LLM|GPT`: two hits, neither
relevant (one is a note that *Ember* ships no ML anywhere; one is a warning not
to trust an LLM summary of a rendered page).

The only ML ruling on file is *"no published end-to-end learned vector-art →
machine-stitch system exists"* (`masters-teardown-2026-08-01.md § 3.8`). That
is correct, and it answers a **different question**.

The recurring failure mode in this engine is semantic, not geometric — by the
project's own record: four separate thresholds calibrated on the wrong
population, the classifier misrouting real logos, stage 0 not scale-invariant.
That is the ten seconds of *looking* a human digitizer does before touching
geometry: this is a logo, these regions are text, these three greys are one
thread, this element is background.

Structured art interpretation is a well-posed task for a vision model now,
testable against the corpus that already exists, and it leaves the geometry
engine untouched. An optional call or a small local model keeps the local-first
promise intact.

### 3.5 Kent owns an embroidery business and nothing measures the tool in it

No production log anywhere in the repo. *"Did a real paying job go through
EMB-Bot, and what had to be fixed by hand?"* costs nothing, and would outrank
all 112 research docs for deciding what to build next. It is also the only
instrument that settles the 60%-of-Ember question in the way that matters.

## 4. What the direction got right

Stated so this review is not read as a repudiation:

- **Format correctness is a durable moat.** Six formats, round-trip verified
  against a reference implementation. Hobby tools do not have this.
- **The font library is legally shippable and ahead of the benchmark** — 85
  fonts, 85 sidecars, enforced in CI, four fonts deleted on principle rather
  than kept.
- **`DOCTRINE.md` and the measured-negatives discipline are genuinely
  unusual**, and are the reason a single session could separate explored ground
  from unexplored at all.

## 5. Loose end found in passing

`README.md` — the user-facing doc — says **"55-font"** twice. It is 85
(`src/fonts/bin/`, and `PRODUCT.md` row 7 says so). Small, but it is the
document a first customer reads.
