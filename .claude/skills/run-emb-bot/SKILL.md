---
name: run-emb-bot
description: Launch, build, and test EMB-Bot — the Svelte Studio app, the JS stitch engine's Node test harness, and the Python digitizer service. Use when Kent says "run embot", "run emb bot", "start embot", "pull up emb bot", or otherwise asks to run, start, build, verify, or test EMB-Bot, or after changing src/, app/, tools/, or digitizer/.
---

# Running EMB-Bot

EMB-Bot has two independent stacks: a browser-side JS stitch engine (primary
product, no backend) and an optional Python digitizer service.

## First — decide which kind of "run" this is

This matters more than anything else in this file, and getting it wrong wastes
everyone's time.

**Kent wants to use EMB-Bot in his own browser** ("run embot", "pull up emb
bot", "start it up"). This is the common case. He is on **Windows**, at
`<repo-root>`. Do **not** start a server in your own
sandbox — a server you start lives on *your* localhost, which his browser
can never reach, and handing him a `localhost:5173` link from a cloud
container is a dead end. Jump to *Launch on Kent's machine* below and give
him the paste blocks verbatim.

**You need to run it yourself** to verify a change you just made. Then the
sandbox sections apply — *Verifying a UI change live*, *JS engine tests*, and
the Linux forms under *Python digitizer*.

When it's genuinely ambiguous, ask which one before starting anything.

## Launch on Kent's machine (Windows)

Give him exactly this, in this shape. Both windows stay occupied — each
command holds its terminal until Ctrl+C, so they cannot share one window.

**Terminal Window 1 — Studio (required).** Paste:

```powershell
cd <repo-root>\app
npm install
npm run dev
```

**Terminal Window 2 — auto-digitizer (optional).** Paste:

```powershell
cd <repo-root>\digitizer
if (-not (Test-Path .venv\Scripts\python.exe)) { py -3.12 -m venv .venv; .venv\Scripts\python -m pip install -e ".[service,dev]" }
.venv\Scripts\python -m digitizer_service
```

**Then open the browser** to `http://localhost:5173` — typed into the address
bar with the `http://` prefix.

`npm install` is a no-op after the first run, so the Window 1 block is safe to
paste every time. The Window 2 block self-heals: it builds the venv on first
use and skips straight to the service afterward. First-time setup pulls
OpenCV, numpy, scipy, shapely and scikit-image, so it takes a few minutes.

Window 2 is only needed for **image auto-digitize**. Text and lettering work
with Window 1 alone; without the service the Studio just logs a failed probe
to `127.0.0.1:8721`.

### One-command alternative

`tools/start-emb-bot.ps1` does all of the above — opens both windows, waits
for the port to actually accept connections, then launches the browser. From
any PowerShell window:

```powershell
<repo-root>\tools\start-emb-bot.ps1
```

Add `-NoDigitizer` to skip Window 2. The script resolves its own repo root
from `$PSScriptRoot`, so it survives the repo being moved or cloned elsewhere.

### Prerequisite: Python 3.12+

`digitizer/pyproject.toml` sets `requires-python = ">=3.12"`. On 3.11 the
install dies with `ERROR: Package 'digitizer-core' requires a different
Python: 3.11.x not in '>=3.12'`. Check with `py --list` and substitute the
version that's actually installed. Note the Windows launcher form `py -3.12`
is what the paste block uses — a bare `python` may resolve to an older
interpreter even when 3.12 is present.

### When it "doesn't work" — confirmed failure modes

Each of these has actually happened. Check in this order:

1. **No server is running.** By far the most common. `Test-NetConnection
   -ComputerName localhost -Port 5173` reporting `TcpTestSucceeded : False`
   means nothing is listening — the fix is to start Window 1, not to debug
   the browser. Note `PingSucceeded : True` in that same output means only
   that loopback resolves; it says nothing about the server.
2. **`Test-NetConnection` run with no arguments.** It silently falls back to
   an internet check against `internetbeacon.msedge.net` and reports success
   while telling you nothing about port 5173. The arguments are required.
3. **The URL typed into PowerShell.** `http://localhost:5173` in a shell
   returns `CommandNotFoundException` — it belongs in the browser address bar.
4. **Scheme omitted in the browser.** Chrome and Edge auto-upgrade a bare
   `localhost:5173` to HTTPS; Vite serves plain HTTP, so a healthy server
   still fails to load. Type the `http://` prefix.
5. **A different port.** Vite auto-increments to 5174, 5175… when 5173 is
   taken, and prints whichever it bound. Read Window 1's own output rather
   than assuming. `start-emb-bot.ps1` assumes 5173 and will open the wrong
   URL if Vite moved — check Window 1 in that case.
6. **The server never started.** `app/scripts/copy-engine.mjs` hard-throws
   `missing engine file: <name>` if any of the 23 files it copies is absent
   from `src/`, and that runs in `predev` — so Vite never boots. The error is
   in Window 1's output, above where the Vite banner would be.
7. **Wrong tree.** If a `.claude/worktrees/` lane is checked out, `app/` there
   has its own `node_modules` and its own `src/` state. `git worktree list`
   confirms which tree is being served.

Expect a cosmetic `favicon.ico` 404 in the console in all cases.

## Studio app internals (`app/`)

Svelte + Vite. This is what most feature work touches.

- `npm run build` — production build (also runs `predev`/`prebuild`'s
  `node scripts/copy-engine.mjs` automatically, which syncs the engine from
  `src/` into the app).
- `npm run test` — Vitest (`vitest run`).
- `npm run preview` — serve the production build locally.

If you changed anything under `src/`, the Studio picks it up via
`copy-engine.mjs` on its own `predev`/`prebuild` hook — no manual step needed.

## Verifying a UI change live

Two ways, both real browsers. Prefer either over claiming a frontend change
works from reading the diff.

**The e2e suite** (`app/e2e/*.spec.js`, 7 specs) starts its own dev server on
port 5183 and tears it down again, so it needs nothing running first:

```
cd app
npx playwright test                    # or: npx playwright test e2e/wizard-smoke.spec.js
```

Chromium browsers are installed on Kent's machine as of 2026-08-14 (`npx
playwright install chromium` if a fresh machine reports a missing browser).

**Interactive driving** — with `npm run dev` running **in your own sandbox**,
the `playwright` MCP server (declared in `.mcp.json`, launched via
`tools/mcp-playwright.mjs`) drives a headless browser against
`http://localhost:5173`: navigate the wizard, click through garment/font
pickers, take snapshots. Use this for exploring; use the suite for proving.

## Standalone bundle — deleted, do not rebuild

`EMB-Bot-standalone.html` is **deleted, 2026-08-04 (Kent's call)**.
`tools/bundle.mjs` is dead code — do not run it, do not regenerate the file.
Test the plain `EMB-Bot.html` + `src/` combo, or the Studio, instead.

## JS engine tests — no browser needed

`src/*.js` modules double as CommonJS for Node tests (`test/*.test.js`,
covers every non-DOM module):

```
node --test
```

To exercise the digitizing pipeline itself against a real image without a
browser, use the Node-side harness in `tools/`:

- `tools/run-digitize.mjs` — run the full digitize pipeline on an image
- `tools/run-flatten.mjs` — run just the color-flatten step
- `tools/render-dst.mjs` — render a `.DST` file to PNG for visual inspection
- `tools/png.mjs` — PNG decode/encode helper used by the above

These exist specifically because the browser tool available in agent
sessions can't do file uploads — this is the way to test digitizing on a
real image in this environment.

## Python digitizer (`digitizer/`)

Setup, test and service commands live in `digitizer/README.md` — follow it
rather than duplicating it here. Two things that file gets wrong or omits:

- **In a Linux sandbox**, use `.venv/bin/python`, not the
  `.venv/Scripts/python.exe` form the README shows (that's Windows). Swap
  `Scripts` for `bin` and drop `.exe` throughout. Where the default `python3`
  is older than 3.12, create the venv with an explicit `python3.12`.
- Run tests as `python -m pytest`, never a bare `pytest` — the module form
  puts the working directory on `sys.path` so `digitizer_core` imports
  without a separate install step.

`GET /health` on `127.0.0.1:8721` returns the brand and format inventory —
confirms the service is really up, not merely launched.

## Where things live, and the DST trap

Architecture and the which-folder-does-what map are in COOKBOOK.md; the DST
codec's axis bug is footgun #1 in CLAUDE.md. Both are read before this skill,
so they aren't repeated here. The one operational consequence worth carrying:
when verifying DST output for **correctness** rather than round-tripping,
decode through pyembroidery, never through `src/dstimport.js`.
