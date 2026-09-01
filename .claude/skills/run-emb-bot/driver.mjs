#!/usr/bin/env node
// EMB-Bot Studio driver — a headless-Chromium REPL for driving the Svelte
// Studio from an agent session.
//
// Why this exists: `chromium-cli` is not present in this sandbox class, and
// the Playwright MCP server is session-scoped (it comes and goes with the
// MCP handshake) — neither is something a future agent can rely on. This
// file is checked in so "drive the Studio" is always one command.
//
// Run it from anywhere; paths are resolved off this file's own location.
//
//   node .claude/skills/run-emb-bot/driver.mjs smoke      # canned flow, exits
//   node .claude/skills/run-emb-bot/driver.mjs repl       # stdin commands
//   node .claude/skills/run-emb-bot/driver.mjs repl --serve --port 5174
//
// Every command prints a line starting with "<< " when it finishes, so a
// tmux-driven caller can poll `capture-pane` for the marker instead of
// sleeping. Errors print "<< ERR ..." and never kill the REPL.
import { createRequire } from "node:module";
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createInterface } from "node:readline";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, "..", "..", "..");      // .claude/skills/run-emb-bot -> repo root
const APP = join(REPO, "app");

// Playwright lives in app/node_modules, but this file lives at the repo root
// under .claude/ — Node's upward node_modules walk from here never reaches it.
// Anchor the require at app/package.json instead.
const appRequire = createRequire(join(APP, "package.json"));
const { chromium } = appRequire("playwright");

// Same executable pin as app/playwright.config.js and tools/mcp-playwright.mjs:
// this sandbox pre-caches a Chromium at /opt/pw-browsers/chromium and blocks
// Playwright's download CDN, so an unpinned launch fails with no fallback.
// On a machine without that path (Kent's Windows box) we fall through to
// Playwright's own managed browser.
const SANDBOX_CHROMIUM = "/opt/pw-browsers/chromium";
const launchOptions = {
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
  ...(existsSync(SANDBOX_CHROMIUM) ? { executablePath: SANDBOX_CHROMIUM } : {}),
};

const argv = process.argv.slice(2);
const mode = argv.find((a) => !a.startsWith("-")) || "repl";
const flag = (name, dflt) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[i + 1] : dflt;
};
const PORT = Number(flag("port", 5173));
const BASE = `http://localhost:${PORT}`;
const SHOTS = flag("shots", "/tmp/emb-shots");
const SERVE = argv.includes("--serve");

mkdirSync(SHOTS, { recursive: true });

const log = (...a) => console.log(...a);
const done = (m) => console.log("<< " + m);
const fail = (m) => console.log("<< ERR " + m);

let vite = null;
async function serverUp(ms = 1500) {
  try {
    const c = new AbortController();
    const t = setTimeout(() => c.abort(), ms);
    const r = await fetch(BASE + "/", { signal: c.signal });
    clearTimeout(t);
    return r.ok;
  } catch { return false; }
}

async function startServer() {
  if (await serverUp()) { log(`dev server already up on ${BASE}`); return; }
  if (!SERVE) throw new Error(`nothing serving ${BASE} — start it, or pass --serve`);
  log(`starting vite on :${PORT} …`);
  // detached:true puts vite in its own process group. npm does NOT forward
  // SIGTERM to the vite it spawns, so killing the npm wrapper leaves the
  // port bound and the next run dies on EADDRINUSE — kill the whole group
  // (see shutdown()).
  vite = spawn("npm", ["run", "dev", "--", "--port", String(PORT), "--strictPort"],
    { cwd: APP, stdio: ["ignore", "pipe", "pipe"], detached: true });
  const out = [];
  vite.stdout.on("data", (d) => out.push(String(d)));
  vite.stderr.on("data", (d) => out.push(String(d)));
  for (let i = 0; i < 120; i++) {
    if (await serverUp()) { log(`dev server up on ${BASE}`); return; }
    if (vite.exitCode !== null) throw new Error("vite died:\n" + out.join(""));
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error("vite never answered in 60s:\n" + out.join(""));
}

// ---------------------------------------------------------------- browser
let browser, ctx, page;
const consoleLog = [];   // {type, text}
const netLog = [];       // request lines — the fastest way to see whether a
                         // click actually reached the digitizer service
const pageErrors = [];

async function open() {
  browser = await chromium.launch(launchOptions);
  ctx = await browser.newContext({ viewport: { width: 1440, height: 960 } });
  page = await ctx.newPage();
  // Keep location(): a failed-resource console error's text is the generic
  // "Failed to load resource: …404…" — the URL that actually identifies it
  // (favicon vs. something real) is only in location().
  page.on("console", (m) => consoleLog.push({ type: m.type(), text: m.text(), url: (m.location() || {}).url || "" }));
  page.on("request", (r) => { if (!/^data:/.test(r.url())) netLog.push(`${r.method()} ${r.url()}`); });
  page.on("response", (r) => { if (r.status() >= 400) netLog.push(`  ^ ${r.status()} ${r.url()}`); });
  page.on("pageerror", (e) => pageErrors.push(String(e)));
  await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
  // The Studio boots the engine from /engine/*.js after first paint; the step
  // nav is the first thing that proves those modules resolved.
  await page.waitForSelector("body", { timeout: 15000 });
}

let shotN = 0;
async function shot(name) {
  const file = join(SHOTS, `${String(++shotN).padStart(2, "0")}-${name || "shot"}.png`);
  await page.screenshot({ path: file, fullPage: false });
  return file;
}

// A text map of what's actually clickable. The Studio is a Svelte wizard with
// generated class names — an agent that can't see the page needs this far more
// than a DOM dump, and page.accessibility.snapshot() returns near-nothing on
// this build.
async function outline() {
  return await page.evaluate(() => {
    const vis = (el) => {
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== "hidden";
    };
    const rows = [];
    for (const el of document.querySelectorAll("button, a[href], input, select, textarea, [role=button], [role=tab]")) {
      if (!vis(el)) continue;
      const tag = el.tagName.toLowerCase();
      const label = (el.getAttribute("aria-label") || el.value || el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 60);
      const id = el.id ? `#${el.id}` : "";
      const dis = el.disabled ? " [disabled]" : "";
      rows.push(`${tag}${id}${el.type ? `[${el.type}]` : ""} "${label}"${dis}`);
    }
    const heads = [...document.querySelectorAll("h1,h2,h3")].filter(vis)
      .map((h) => `${h.tagName.toLowerCase()}: ${h.textContent.trim().replace(/\s+/g, " ").slice(0, 80)}`);
    return { url: location.href, headings: heads, controls: rows };
  });
}

// ---------------------------------------------------------------- commands
const commands = {
  async nav(path = "/") { await page.goto(BASE + path, { waitUntil: "domcontentloaded" }); return page.url(); },
  async ss(name) { return await shot(name); },
  async outline() { return JSON.stringify(await outline(), null, 2); },
  async click(...sel) { await page.click(sel.join(" "), { timeout: 10000 }); return "clicked " + sel.join(" "); },
  // Click by visible label — the Studio's buttons are text, not ids.
  //
  // EXACT FIRST, deliberately. A substring match here is a live trap: the
  // digitize panel has both "Digitize" (runs the job) and "Digitize as flat
  // art" (only flips forced_class), and getByRole(...).first() on a
  // substring picks the wrong one in DOM order — the click "succeeds",
  // nothing is submitted, and you debug the service for an hour. So: try
  // exact, fall back to substring, and always print what was resolved and
  // how many candidates there were.
  async btn(...label) {
    const t = label.join(" ");
    let loc = page.getByRole("button", { name: t, exact: true });
    let how = "exact";
    let n = await loc.count();
    if (n === 0) {
      loc = page.getByRole("button", { name: t, exact: false });
      how = "substring";
      n = await loc.count();
    }
    if (n === 0) throw new Error(`no button matching ${JSON.stringify(t)}`);
    const names = [];
    for (let i = 0; i < Math.min(n, 5); i++) names.push((await loc.nth(i).innerText()).replace(/\s+/g, " ").trim());
    await loc.first().click({ timeout: 10000 });
    return `clicked [${how}] ${JSON.stringify(names[0])}` + (n > 1 ? `  (${n} matched: ${JSON.stringify(names)} — clicked the first)` : "");
  },
  async fill(sel, ...val) { await page.fill(sel, val.join(" "), { timeout: 10000 }); return "filled " + sel; },
  async type(sel, ...val) { await page.locator(sel).first().pressSequentially(val.join(" "), { delay: 20 }); return "typed into " + sel; },
  async press(key) { await page.keyboard.press(key); return "pressed " + key; },
  async reload() { await page.reload({ waitUntil: "domcontentloaded" }); return page.url(); },
  // Real file upload. The Studio's artwork input is hidden behind a styled
  // label, so setInputFiles on the <input type=file> is the only path that
  // works headless — and it does work, contrary to "agent browsers can't
  // upload". Path is resolved relative to the repo root.
  async upload(sel, ...file) {
    const f = resolve(REPO, file.join(" "));
    if (!existsSync(f)) throw new Error("no such file: " + f);
    await page.setInputFiles(sel, f, { timeout: 15000 });
    return "uploaded " + f;
  },
  // Dump the current design's stitch stats straight out of the canvas caption
  // — cheaper than reading a screenshot, and the number that actually matters.
  async stats() {
    return await page.evaluate(() => {
      const t = [...document.querySelectorAll("*")]
        .map((e) => e.childNodes.length === 1 && e.textContent ? e.textContent.trim() : "")
        .find((s) => /\d+\s+stitches/.test(s));
      return t || "(no stitch caption on screen)";
    });
  },
  // Wait for a button whose text is EXACTLY this. Needed because several
  // controls only mount after async work: the digitize panel's "Digitize"
  // button does not exist until the uploaded file has been read into
  // sourcePng, so an immediate click after `upload` hits the element chip
  // ("Digitized · empty") instead and silently does nothing.
  async waitbtn(...label) {
    const t = label.join(" ");
    await page.getByRole("button", { name: t, exact: true }).first()
      .waitFor({ state: "visible", timeout: 30000 });
    return `button ${JSON.stringify(t)} is present`;
  },
  async wait(...sel) { await page.waitForSelector(sel.join(" "), { timeout: 20000 }); return "visible: " + sel.join(" "); },
  async waittext(...t) { await page.getByText(t.join(" "), { exact: false }).first().waitFor({ timeout: 20000 }); return "text seen"; },
  async text(...sel) { return (await page.locator(sel.join(" ")).first().innerText()).slice(0, 2000); },
  async eval(...js) { return JSON.stringify(await page.evaluate(js.join(" ")), null, 2); },
  async console(which) {
    const rows = which === "errors"
      ? consoleLog.filter((m) => m.type === "error")
      : consoleLog;
    return [...rows.map((m) => `[${m.type}] ${m.text}${m.url ? "  <- " + m.url : ""}`), ...pageErrors.map((e) => `[pageerror] ${e}`)].join("\n") || "(nothing)";
  },
  // Requests the page made. Filter to the digitizer with: net 8721
  async net(filter) {
    const rows = filter ? netLog.filter((l) => l.includes(filter)) : netLog;
    return rows.slice(-60).join("\n") || "(no matching requests)";
  },
  async html(...sel) { return (await page.locator(sel.length ? sel.join(" ") : "body").first().innerHTML()).slice(0, 4000); },
  async quit() { await shutdown(); process.exit(0); },
};

async function shutdown() {
  try { await browser?.close(); } catch {}
  if (vite && vite.pid) {
    // Negative pid = the whole process group, which is what actually frees
    // the port. Fall back to the bare pid if the group is already gone.
    try { process.kill(-vite.pid, "SIGTERM"); }
    catch { try { vite.kill("SIGTERM"); } catch {} }
    // Give it a beat to release the listener before we exit.
    await new Promise((r) => setTimeout(r, 500));
  }
}

// ---------------------------------------------------------------- smoke
// Two representative flows, end to end. Both were run to build this driver;
// both produce screenshots you should actually open.
//
//   lane 1 (always)  text/lettering  — pure browser engine, no service
//   lane 2 (if up)   artwork         — the Python digitizer at :8721
//
// Exit 1 on a console error (favicon 404 and the digitizer-probe
// ERR_CONNECTION_REFUSED are filtered — both are expected noise).
const STITCH_RE = /[\d,]+ stitches[^\n]*/;

async function caption() {
  return await page.evaluate((src) => {
    const m = document.body.innerText.match(new RegExp(src));
    return m ? m[0] : null;
  }, STITCH_RE.source);
}

async function waitCaption(ms = 60000) {
  const t0 = Date.now();
  for (;;) {
    const c = await caption();
    if (c) return c;
    if (Date.now() - t0 > ms) return null;
    await page.waitForTimeout(500);
  }
}

async function digitizerUp() {
  try {
    const r = await fetch("http://127.0.0.1:8721/health");
    return r.ok;
  } catch { return false; }
}

async function smoke() {
  const shots = [];
  const results = [];

  // ---- lane 1: lettering ------------------------------------------------
  log("lane 1: text/lettering");
  await page.getByRole("button", { name: "Name on a hat", exact: false }).first().click();
  await page.waitForSelector("canvas", { timeout: 20000 });
  await page.fill("textarea", "FRITSCH'S");
  const textCap = await waitCaption(30000);
  shots.push(await shot("text-lettering"));
  results.push(`  text lane: ${textCap || "NO STITCH CAPTION"}`);
  if (!textCap) throw new Error("lettering produced no stitches");

  // ---- lane 2: artwork auto-digitize ------------------------------------
  if (await digitizerUp()) {
    log("lane 2: artwork auto-digitize (service is up)");
    await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: "Logo patch", exact: false }).first().click();
    const fixture = join(REPO, "app/e2e/fixtures/enthusiast_logo.png");
    await page.setInputFiles("input[type=file]", fixture);
    // NOTHING IS CLICKED HERE, deliberately. PR #296 ("uploading the image is
    // the whole interaction", Kent 2026-08-30) made the upload itself start
    // the run: DigitizePanel watches `element.sourcePng` and calls
    // `runDigitize` as soon as it changes, provided `health` is truthy.
    // `app/e2e/digitize-auto-start.spec.js` pins exactly that, with no
    // Digitize click anywhere in it.
    //
    // This used to wait for a button with the exact text "Digitize" and click
    // it, which now hangs the full 30s and then throws. The button was NOT
    // deleted — it is still the way back in when the service is offline, or
    // when the user re-picks the identical file — but its label is transient:
    //   pending ? "Digitizing…" : element.result ? "Digitize again" : "Digitize"
    // With the service up, the auto-start flips `pending` true before the
    // wait can see it, so exact "Digitize" never appears. Waiting on the
    // caption is the honest check: it proves stitches actually landed.
    const artCap = await waitCaption(120000);
    shots.push(await shot("artwork-digitize"));
    results.push(`  artwork lane: ${artCap || "NO STITCH CAPTION"}`);
    if (!artCap) throw new Error("auto-digitize produced no stitches");
  } else {
    results.push("  artwork lane: SKIPPED — no digitizer service on 127.0.0.1:8721");
  }

  const errs = [
    ...consoleLog.filter((m) => m.type === "error").map((m) => `${m.text}  <- ${m.url}`),
    ...pageErrors,
  ]
    .filter((t) => !/favicon/i.test(t))                   // always 404s, cosmetic
    .filter((t) => !/ERR_CONNECTION_REFUSED/i.test(t));   // digitizer probe when service is down

  log("\n" + results.join("\n"));
  log("\nscreenshots:\n" + shots.map((f) => "  " + f).join("\n"));
  if (errs.length) { log("\nCONSOLE ERRORS:\n" + errs.join("\n")); return 1; }
  log("\nno unexpected console errors");
  return 0;
}

// ---------------------------------------------------------------- main
await startServer();
await open();

if (mode === "smoke") {
  const code = await smoke();
  await shutdown();
  process.exit(code);
}

log(`ready — ${BASE}, shots -> ${SHOTS}`);
log("commands: " + Object.keys(commands).join(" "));
done("ready");

const rl = createInterface({ input: process.stdin, terminal: false });
for await (const line of rl) {
  const s = line.trim();
  if (!s || s.startsWith("#")) continue;
  const [cmd, ...rest] = s.split(/\s+/);
  const fn = commands[cmd];
  if (!fn) { fail(`unknown command ${JSON.stringify(cmd)} — have: ${Object.keys(commands).join(" ")}`); continue; }
  try {
    const out = await fn(...rest);
    if (out !== undefined) log(out);
    done(cmd);
  } catch (e) {
    fail(`${cmd}: ${String(e).split("\n").slice(0, 6).join("\n")}`);
  }
}
await shutdown();
