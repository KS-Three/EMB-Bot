# Fix Export Routing (DST/EXP/PES → pyembroidery service) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Studio's Download button routes DST/EXP/PES through the Python digitizer service's `/export` endpoint (pyembroidery convention — the trustworthy path for third-party software) whenever the service is reachable, instead of always using the browser's own encoder, while falling back to the browser encoder unchanged when the service is offline.

**Architecture:** Add one new client function `exportViaService()` to `app/src/lib/digitizer.js` (mirrors the existing `startDigitize`/`pollJob` fetch-with-injectable-`fetchFn` pattern already in that file) that POSTs the already-built combined Design to `POST /export` and returns `{bytes, filename, mime}`. Add one new orchestration function `exportDesignPreferService()` to `app/src/lib/exporters.js` that tries the service first for dst/exp/pes and falls back to the existing synchronous `exportDesign()` on any failure. `DownloadStep.svelte`'s `dl(fmt)` calls the new orchestration function instead of `exportDesign()` directly. `exportDesign()` itself, and every existing caller of it (svg, worksheet PDF, PNG), is untouched.

**Tech Stack:** Svelte 5 (Studio app), Vitest, FastAPI service already shipping `/export` (`digitizer_service/app.py:730`), pyembroidery.

## Global Constraints

- No new dependencies — the service endpoint already exists and is already used by other Studio code paths (`digitizer.js`'s existing `startDigitize`/`pollJob`).
- `exportDesign()` (the synchronous browser-encoder function) must keep its existing signature and behavior — `exporters.spec.js`'s 5 existing tests for it must pass unmodified.
- Service calls default to no auth header — `EMBBOT_SERVICE_TOKEN` is off by default (`digitizer_service/app.py:9`); do not add a token param, this fix doesn't touch that seam.
- Scope is exactly `dst`, `exp`, `pes` — the 3 formats Studio's Download panel already offers that the service can also produce. `svg` never touches the service (the service doesn't write SVG; it's Studio's own vector export). Adding a JEF button is a separate, later enhancement — not part of this fix.
- Silent fallback: when the service is unreachable or errors, `dl()` must produce EXACTLY today's output (browser encoder, no visible error) — Studio must keep working with the service off, same as every other digitizer-gated feature in this app.

---

### Task 1: `exportViaService()` in `app/src/lib/digitizer.js`

**Files:**
- Modify: `app/src/lib/digitizer.js` (add function near `startDigitize`/`pollJob`, after `httpDetail`)
- Test: `app/src/lib/digitizer.spec.js` (add tests near the existing `startDigitize` tests)

**Interfaces:**
- Consumes: `digitizerUrl()` (existing, same file), `httpDetail(r)` (existing, same file, currently module-private — must be reused, not duplicated)
- Produces: `exportViaService(design, format, label, fetchFn = globalThis.fetch): Promise<{bytes: Blob, filename: string, mime: string}>` — thrown `Error` on any non-ok response, message = the service's own detail sentence (via `httpDetail`). Later tasks (Task 2) import this by name.

- [ ] **Step 1: Write the failing tests**

Add to `app/src/lib/digitizer.spec.js`, near the existing `startDigitize` tests (same file already imports `TINY_PNG_B64` and follows this `fetchFn`-stub convention — match it exactly):

```js
test("exportViaService POSTs the design as JSON to /export and returns bytes+filename+mime from the response", async () => {
  const { exportViaService } = await import("./digitizer.js");
  let seenUrl, seenOpts;
  const fakeBlob = new Blob([new Uint8Array([1, 2, 3])]);
  const fetchFn = async (url, opts) => {
    seenUrl = url;
    seenOpts = opts;
    return {
      ok: true,
      status: 200,
      blob: async () => fakeBlob,
      headers: {
        get: (k) => {
          if (k === "Content-Disposition") return 'attachment; filename="left_chest.dst"';
          if (k === "Content-Type") return "application/octet-stream";
          return null;
        },
      },
    };
  };
  const design = { stitches: [{ x: 0, y: 0, type: "stitch" }], colors: [], widthMM: 10, heightMM: 10 };
  const out = await exportViaService(design, "dst", "left_chest", fetchFn);

  expect(seenUrl).toBe("http://127.0.0.1:8721/export");
  expect(seenOpts.method).toBe("POST");
  expect(seenOpts.headers["Content-Type"]).toBe("application/json");
  const sentBody = JSON.parse(seenOpts.body);
  expect(sentBody).toEqual({ design, format: "dst", label: "left_chest" });

  expect(out.bytes).toBe(fakeBlob);
  expect(out.filename).toBe("left_chest.dst");
  expect(out.mime).toBe("application/octet-stream");
});

test("exportViaService falls back to a design.<format> filename when Content-Disposition is missing", async () => {
  const { exportViaService } = await import("./digitizer.js");
  const fetchFn = async () => ({
    ok: true,
    status: 200,
    blob: async () => new Blob([]),
    headers: { get: () => null },
  });
  const out = await exportViaService({ stitches: [] }, "exp", "x", fetchFn);
  expect(out.filename).toBe("design.exp");
  expect(out.mime).toBe("application/octet-stream");
});

test("exportViaService surfaces the service's own detail sentence on a non-ok response", async () => {
  const { exportViaService } = await import("./digitizer.js");
  const fetchFn = async () => ({
    ok: false, status: 400,
    json: async () => ({ detail: "payload.design must be a design with stitches." }),
  });
  await expect(exportViaService({ stitches: [] }, "dst", "x", fetchFn))
    .rejects.toThrow(/payload\.design must be a design with stitches/);
});
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `cd app && npx vitest run src/lib/digitizer.spec.js -t exportViaService`
Expected: FAIL — `exportViaService` is not exported (`SyntaxError`/`TypeError: ... is not a function` or similar import failure).

- [ ] **Step 3: Implement `exportViaService`**

In `app/src/lib/digitizer.js`, add directly after the existing `httpDetail` function (it currently ends around the `startDigitize` function — search for `async function httpDetail`):

```js
// POST /export (any EMB-Bot design -> a machine file, the pyembroidery-
// convention path — digitizer_service/app.py's one export route for every
// design type). Returns the same {bytes, filename, mime} shape
// exporters.js's exportDesign() returns, so callers don't care which one
// produced it. filename is read off Content-Disposition when present
// (the service always sends one); falls back to design.<format> so a
// service that omits the header (or a test double) never yields an
// extensionless download.
export async function exportViaService(design, format, label, fetchFn = globalThis.fetch) {
  const r = await fetchFn(digitizerUrl() + "/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ design, format, label }),
  });
  if (!r.ok) throw new Error(await httpDetail(r));
  const bytes = await r.blob();
  const cd = (r.headers && r.headers.get("Content-Disposition")) || "";
  const m = /filename="([^"]+)"/.exec(cd);
  const filename = m ? m[1] : `design.${format}`;
  const mime = (r.headers && r.headers.get("Content-Type")) || "application/octet-stream";
  return { bytes, filename, mime };
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd app && npx vitest run src/lib/digitizer.spec.js -t exportViaService`
Expected: PASS (3 new tests)

- [ ] **Step 5: Run the full digitizer.spec.js file to confirm nothing else broke**

Run: `cd app && npx vitest run src/lib/digitizer.spec.js`
Expected: PASS, all tests (existing count + 3 new)

- [ ] **Step 6: Commit**

```bash
git add app/src/lib/digitizer.js app/src/lib/digitizer.spec.js
git commit -m "feat(digitizer): add exportViaService, the pyembroidery-convention export client"
```

---

### Task 2: `exportDesignPreferService()` orchestration in `app/src/lib/exporters.js`

**Files:**
- Modify: `app/src/lib/exporters.js` (add import + function, `exportDesign` itself unchanged)
- Test: `app/src/lib/exporters.spec.js` (add tests near the existing DST/EXP/PES `exportDesign` tests)

**Interfaces:**
- Consumes: `exportViaService(design, format, label, fetchFn)` (Task 1), `exportDesign(design, format)` (existing, this file, unchanged)
- Produces: `exportDesignPreferService(design, format, opts = {}): Promise<{bytes, filename, mime}>` where `opts` is `{label?: string, exportViaServiceFn?: function, fetchFn?: function}`. Task 3 (DownloadStep.svelte) calls this by name.

- [ ] **Step 1: Write the failing tests**

Add to `app/src/lib/exporters.spec.js`, after the existing `test("unknown format throws", ...)` block (the `design` fixture from `beforeAll` is already in scope):

```js
test("exportDesignPreferService uses the service for dst/exp/pes when it succeeds", async () => {
  const { exportDesignPreferService } = await import("./exporters.js");
  const serviceOut = { bytes: new Blob(["x"]), filename: "svc.dst", mime: "application/octet-stream" };
  const exportViaServiceFn = async (d, fmt, label) => {
    expect(d).toBe(design);
    expect(fmt).toBe("dst");
    expect(label).toBe("My Design");
    return serviceOut;
  };
  const out = await exportDesignPreferService(design, "dst", { label: "My Design", exportViaServiceFn });
  expect(out).toBe(serviceOut);
});

test("exportDesignPreferService falls back to the browser encoder when the service throws", async () => {
  const { exportDesignPreferService } = await import("./exporters.js");
  const exportViaServiceFn = async () => { throw new Error("fetch failed"); };
  const out = await exportDesignPreferService(design, "dst", { exportViaServiceFn });
  expect(out.filename.endsWith(".dst")).toBe(true);
  expect(out.bytes.length).toBeGreaterThan(100); // the real browser-encoded bytes, same as exportDesign()'s own test
});

test("exportDesignPreferService never calls the service for svg", async () => {
  const { exportDesignPreferService } = await import("./exporters.js");
  let called = false;
  const exportViaServiceFn = async () => { called = true; throw new Error("should not be called"); };
  const out = await exportDesignPreferService(design, "svg", { exportViaServiceFn });
  expect(called).toBe(false);
  expect(String(out.bytes)).toContain("<svg");
});
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `cd app && npx vitest run src/lib/exporters.spec.js -t exportDesignPreferService`
Expected: FAIL — `exportDesignPreferService` is not exported.

- [ ] **Step 3: Implement `exportDesignPreferService`**

In `app/src/lib/exporters.js`, add the import at the top and the function after the existing `exportDesign`:

```js
import { exportViaService } from "./digitizer.js";
```

```js
// dst/exp/pes prefer the Python digitizer service's pyembroidery-convention
// encoder (the trustworthy path for third-party software — see
// MASTER_SCOPE.md's DST codec axis bug section: the browser's own DST
// encoder is confirmed transposed a quarter-turn against the Tajima
// standard). Falls back to the browser encoder on ANY service failure
// (offline, network error, 4xx/5xx) so Download keeps working exactly as
// it always has when the service isn't running — no visible error, same
// bytes as before this function existed. svg (and any future non-stitch
// format) never touches the service; exportDesign() alone is authoritative
// for those.
const SERVICE_EXPORT_FORMATS = new Set(["dst", "exp", "pes"]);

export async function exportDesignPreferService(design, format, opts = {}) {
  const { label = "EMBBOT", exportViaServiceFn = exportViaService, fetchFn } = opts;
  if (SERVICE_EXPORT_FORMATS.has(format)) {
    try {
      return await exportViaServiceFn(design, format, label, fetchFn);
    } catch (e) {
      // service down or erroring -- fall through to the browser encoder.
    }
  }
  return exportDesign(design, format);
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd app && npx vitest run src/lib/exporters.spec.js`
Expected: PASS — all existing `exportDesign` tests still pass unmodified, plus the 3 new tests.

- [ ] **Step 5: Commit**

```bash
git add app/src/lib/exporters.js app/src/lib/exporters.spec.js
git commit -m "feat(exporters): prefer the digitizer service for dst/exp/pes, fall back to the browser encoder"
```

---

### Task 3: Wire `DownloadStep.svelte` to the new orchestration function

**Files:**
- Modify: `app/src/ui/DownloadStep.svelte:4` (import) and `:127-135` (`dl` function)

**Interfaces:**
- Consumes: `exportDesignPreferService(design, format, opts)` (Task 2)
- Produces: nothing new — this task only changes which function `dl()` calls; `DownloadStep`'s own external interface (props, dispatched events) is unchanged.

- [ ] **Step 1: Change the import**

In `app/src/ui/DownloadStep.svelte`, line 4:

```js
import { exportDesignPreferService, exportWorksheetPDF, exportPNG } from "../lib/exporters.js";
```

(was: `import { exportDesign, exportWorksheetPDF, exportPNG } from "../lib/exporters.js";`)

- [ ] **Step 2: Change `dl(fmt)`**

Replace the existing `dl` function (currently lines 127-135):

```js
async function dl(fmt) {
  try {
    await ensureFonts(fontKeysOf(project));
    const out = await exportDesignPreferService(buildDesign(), fmt, { label: project.name });
    triggerDownload(out);
    msg = "Downloaded " + fmt.toUpperCase();
  } catch (e) {
    msg = e.message;
  }
}
```

- [ ] **Step 3: Run the full app test suite to confirm nothing broke**

Run: `cd app && npx vitest run`
Expected: PASS — same pass count as the pre-change baseline plus the 6 tests from Tasks 1-2 (no test imports `dl` directly today; this step is a regression check, not new coverage).

- [ ] **Step 4: Live-browser verification (this component has no existing test harness — same posture DigitizePanel was in before its own harness was added; a live check is the acceptance test here, not a gap to fill in this task)**

1. Start the digitizer service: `cd digitizer && .venv/Scripts/python.exe -m digitizer_service --port 8721`
2. Start Studio: `cd app && npm run dev`, open the printed URL
3. Build any design (e.g. Content → + Text → type a word), reach the Download step
4. Click **DST**. In the service terminal, confirm a `POST /export` line appears (not just `/digitize`/`/jobs`)
5. Stop the service (Ctrl+C in its terminal), click **DST** again in Studio — confirm the download still succeeds (no error shown, `msg` still reads "Downloaded DST") — this proves the fallback path
6. Restart the service, repeat step 4 for **EXP** and **PES**

- [ ] **Step 5: Commit**

```bash
git add app/src/ui/DownloadStep.svelte
git commit -m "feat(studio): route DST/EXP/PES downloads through the digitizer service when available"
```

---

## Self-Review

**Spec coverage:** Task 1 covers the service client. Task 2 covers the service/fallback decision, explicitly scoped to dst/exp/pes only (svg excluded, tested). Task 3 covers the one call site (`DownloadStep.svelte`) that was the actual bug — confirmed by grep during planning that `exportDesign` has exactly one production call site (`dl` in `DownloadStep.svelte`); `exportWorksheetPDF`/`exportPNG` are separate functions this plan does not touch.

**Placeholder scan:** No TBD/TODO markers; every step has real code; the live-browser step (Task 3 Step 4) is explicit numbered actions with concrete pass/fail criteria, not "test it manually."

**Type consistency:** `exportViaService(design, format, label, fetchFn)` → `{bytes, filename, mime}` (Task 1) is the exact shape `exportDesignPreferService` (Task 2) both consumes (via `exportViaServiceFn`) and returns, which is the exact shape `exportDesign` already returns and `triggerDownload` already accepts (verified against `download.js` and the existing `exporters.spec.js` assertions before writing this plan).

## What this plan deliberately does NOT do

- Does not add a JEF button to Studio (the service supports it, Studio's UI doesn't offer it yet) — separate, smaller follow-up.
- Does not change `exportDesign`'s own DST/EXP/PES bytes, or fix the browser codec's transposition — that fix is explicitly Kent's call (every existing EMB-Bot DST is affected) per CLAUDE.md and the DST codec axis memory. This plan only changes which encoder is *tried first*; when the service is unreachable, output is byte-identical to today.
- Does not touch `EMB-Bot.html`'s legacy standalone digitize path (`exportDesign` there, if any) — Studio (`app/`) is the only product surface this plan scopes to, matching where the bug was found.
