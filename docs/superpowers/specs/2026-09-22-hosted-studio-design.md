# Hosted Studio — design

*2026-09-22. Kent's call after the organic review
(`docs/organic-review-2026-09-22.md`): ship the Studio as a free hosted static
web app. Approved in brainstorm; this is the spec the implementation plan is
written from.*

## 1. The problem, measured

**Nothing in 1,999 commits packages this repo for a human who is not Kent.**
Swept the tree for `electron|tauri|pyinstaller|installer|code-sign|notariz`
across `*.md`, `*.json`, `*.mjs`, `*.py`: zero hits in EMB-Bot's own code. The
only matches are vendored `.venv` noise and docs describing *Ember's* Tauri
bridge.

Shipping today means: clone a public repo, `npm install`, hand-build a
`python3.12` venv, and run `tools/start-emb-bot.ps1`, which opens two
PowerShell windows that each block until Ctrl+C.

`PRODUCT.md`'s launch checklist is 6 of 7 green and **carries no row for "a
customer can install it"**, which is why this has stayed invisible.

## 2. The thing that makes this cheap: it already builds

Measured this session, not quoted:

```
cd app && npm run build
✓ built in 2.26s
```

| path | size |
|---|---|
| `app/dist/` total | **57 MB** |
| `app/dist/fonts/bin` | 53 MB (85 `.embf`) |
| `app/dist/assets` | 2.4 MB |
| `app/dist/engine` | 504 KB (25 files) |
| `app/dist/fonts/previews` | 388 KB |

`vite.config.js` already sets `base: "./"`, and the built `index.html` emits
`src="./engine/units.js"` — relative, no path rewrite needed to host it.

**First load is ~2.8 MB, not 57.** The font browser grid uses the pre-rendered
previews; a `.embf` binary is fetched only when a font is actually picked
(README, "browsing never downloads font data"). The 53 MB is host storage, not
transfer weight.

## 3. The hosted build is a complete product, not half of one

This was understated in the review's first draft and is the load-bearing fact
for the whole decision.

`app/src/lib/project.js:412`:

```js
export function resolveArtworkType(digitizerHealth) {
  return digitizerHealth ? "digitized" : "image";
}
```

With the service down, image artwork routes to `"image"` — the browser
engine's own flatten-and-sew lane (`src/flatten.js`, `src/digitize.js`), which
README pins at a ~3 mm satin cutoff against the Python lane's ~5 mm. And
`app/src/lib/digitizer.js:79` returns `null` on **any** health failure (down,
refused, non-ok, bad JSON), so the fallback is already the tested path.

Projects live in `localStorage` (`app/src/lib/projects.js`, every accessor
try/catch-safe), so the no-account promise costs nothing on a host either.

So `digitizer/` is a **quality upgrade on one lane**, not the missing half of
the app.

## 4. Decisions (Kent, 2026-09-22)

| # | Decision |
|---|---|
| 1 | **Hosted static web app.** GitHub Pages from the existing public repo, `ks-three.github.io/EMB-Bot`. No custom domain yet. |
| 2 | **Free.** No billing, no accounts, no entitlement, no backend of any kind. |
| 3 | **All lanes ship**, including browser image digitize, with honest-limits language surfaced where it matters — concretely and only: the ContentStep note in §5.2 and the three export reasons in §5.3. No new UI surface, no new warnings elsewhere. |
| 4 | **JEF/XXX/VP3 stay visible but disabled**, with the reason reworded to name the desktop version instead of a service a hosted user cannot start. |

Decision 2 is what makes this days rather than weeks: an entitlement check
would require a backend, and a backend breaks the no-account promise that the
local architecture currently keeps for free.

**Positioning note.** `PRODUCT.md:48` states "Desktop-only, stated on the
site." Hosting breaks the letter of that line while keeping every promise
underneath it — local data, no account, no subscription. The line was written
to differentiate against a subscription SaaS competitor; it is now costing
distribution. It gets amended, not quietly ignored.

## 5. Three defects the hosted build exposes

None of these break the app. All three are things a public site should not do.

**5.1 A doomed probe on every page load.** `digitizer.js:38` sets
`DEFAULT_DIGITIZER_URL = "http://127.0.0.1:8721"` and the app probes
`/health` at boot. From an HTTPS page that request is blocked as mixed
content and logged as an error. The `catch` handles it correctly — the cost is
console noise on the product's public face and a wasted round trip.

**5.2 The offline note says the opposite of what happens.**
`app/src/ui/ContentStep.svelte:241`:

> *"Artwork will be placed but not auto-digitized — that needs the local
> digitizer service. Start it, then [check again]."*

The code comment three lines above it already states the truth: *"it just
falls back to the browser engine's own flatten-and-sew lane."* On a host where
the service can never appear, this note would **permanently tell users the
product does not do the thing it is doing**, and the "check again" button is a
dead affordance pointing at something they cannot start.

**5.3 Three export formats have no browser encoder.**
`app/src/lib/exporters.js:97`:

```js
const SERVICE_ONLY_FORMATS = new Set(["jef", "xxx", "vp3"]);
```

Confirmed against `src/`: there are `dst.js`, `exp.js`, `pes.js`,
`svgexport.js` — and no JEF, XXX or VP3 encoder at all.

| Format | Machine | Written by |
|---|---|---|
| DST | Tajima / commercial | browser (`src/dst.js`) |
| PES | Brother | browser (`src/pes.js`) |
| EXP | Melco | browser (`src/exp.js`) |
| **JEF** | **Janome** | **service only** |
| **XXX** | **Singer** | **service only** |
| **VP3** | **Husqvarna Viking / Pfaff** | **service only** |

Their current failure message (`exporters.js:114`) is *"…is written by the
digitizer service, which isn't answering — start it and try again."* — advice
a hosted user cannot follow.

**This is the same shape as a bug `PRODUCT.md` row 1 already documents about
itself**: that row was verified against the module that *can* write JEF, not
the product that *exposes* it. Recording it here so it is not repeated
silently: **hosted v1 exports DST, PES, EXP, PNG, SVG and PDF.** Janome,
Singer, Husqvarna Viking and Pfaff owners get no stitch file from it.

## 6. Approach: a build-time flag, not a copy-only deploy

Deploying unchanged would work — the fallbacks are real and tested. It is
rejected because it leaves 5.1 and 5.2 live on a public site for the sake of
about two hours.

A single build-time flag (`VITE_HOSTED`) gates all three defects, and it is
the same seam a later desktop/Pro tier needs in reverse. One source, two
targets.

The three `*Available` reactive statements in `DownloadStep.svelte` already
share one shape:

```js
$: jefAvailable = !isServiceOnlyFormat("jef") || !!digitizerHealth;   // :133
$: xxxAvailable = !isServiceOnlyFormat("xxx") || !!digitizerHealth;   // :155
$: vp3Available = !isServiceOnlyFormat("vp3") || !!digitizerHealth;   // :159
```

`*Available` is already correct under hosting — it goes false, which is the
truth. **Only the `*Title` reason strings change.** No availability logic is
touched.

## 7. Changes

| File | Change |
|---|---|
| `app/src/lib/digitizer.js` | Hosted → health probe returns `null` **without calling `fetch`**. No mixed-content error, no wasted round trip. |
| `app/src/ui/ContentStep.svelte:241` | Hosted copy states what actually happens (art digitizes in-browser; the desktop digitizer adds finer satin on small detail). Dead "check again" button removed in hosted builds. |
| `app/src/ui/DownloadStep.svelte:134,156,160` | Hosted-specific unavailable reason on the three `*Title` strings, naming the desktop version. `*Available` untouched. |
| `.github/workflows/` | New Pages deploy job: `VITE_HOSTED=1 npm run build` after `npm ci` → publish `app/dist`, on push to `main`, gated on `engine`, `studio`, and `studio-e2e` — **deliberately not `digitizer`**, which runs 33-55 min against Python that ships nowhere near `app/dist/` and would add that whole wait to every publish for no signal about the thing being published. **The flag is set by the deploy job only** — a local `npm run dev`/`npm run build` stays unhosted and keeps probing the service, which is what Kent's own machine needs. |
| `README.md:17,61` | `55-font` → `85-font` (two occurrences; it is 85 per `src/fonts/bin/` and `PRODUCT.md` row 7). Add the hosted URL. |
| `PRODUCT.md:48` | Amend "Desktop-only, stated on the site." to match what ships. |

## 8. Verification

1. `node --test` (engine) and `cd app && npm test` (studio) stay green.
2. **New spec**: with the hosted flag set, the health probe returns `null` and
   `fetch` is never called — asserted against an injected `fetchFn` that fails
   the test if invoked. `digitizer.js:79` already takes an injected fetch, so
   no new seam is needed.
3. **New spec**: hosted `*Title` strings do not contain "start it" or
   "service"; unhosted strings are unchanged.
4. **Playwright against the built `dist` with no service running** — text,
   shapes, manual draw, DST import and image upload each reach a downloadable
   file; JEF/XXX/VP3 are present, disabled, and carry the hosted reason.
5. Drive the deployed URL in a browser and screenshot it before calling the
   work done. Evidence, not "should work."

## 9. Out of scope

Billing, accounts, service worker / PWA, custom domain, desktop installer, and
any change to `digitizer/`, `src/` stitch engines, or the Python service.

Explicitly **not** attempted here: browser encoders for JEF/XXX/VP3. That was
offered and declined for v1 — it is real engine work and would push the deploy
out by weeks.

## 10. What this does not settle

- **Whether anyone wants it.** A free hosted app answers demand, not
  willingness to pay. `PRODUCT.md`'s billing decision stays `Open`.
- **The three machine brands.** JEF/XXX/VP3 owners remain unserved on the web
  until either browser encoders or a desktop tier exists. Decision 4 makes
  that visible to them rather than silent; it does not fix it.
- **Whether the browser image lane is good enough to be the public face.**
  Decision 3 ships it with honest limits. That is a bet, and the organic
  review's §3.5 (a production log of real jobs) is the instrument that would
  settle it.
