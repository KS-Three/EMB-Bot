// Shared drives for the configurator (spec §7). Every spec used to walk
// Next → Next → Next; the walk is gone, so the way to each place is stated
// once here. Assertions about WHAT is reached stay in each spec.
import { expect } from "@playwright/test";

export async function startStudio(page) {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Your design" })).toBeVisible();
}

export async function typeText(page, text) {
  const input = page.getByPlaceholder("Type a name or word");
  await input.fill(text);
  await expect(input).toHaveValue(text);
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible({ timeout: 60_000 });
}

// Every garment is reachable through More ›, by the engine's own label —
// so one path serves all ten, whether or not the garment has a pill.
export async function pickGarment(page, label) {
  await page.getByRole("button", { name: "More garments" }).click();
  await page.getByRole("menu", { name: "All garments" }).getByRole("menuitemradio", { name: label, exact: true }).click();
  await expect(page.getByRole("menu", { name: "All garments" })).toHaveCount(0);
  await expect(page.locator(".cfg-sub")).toContainText(label);
}

export async function pickTemplate(page, name) {
  await page.getByRole("button", { name: /^My designs/ }).click();
  await page.locator(".tcard", { hasText: name }).click();
  await expect(page.getByRole("dialog", { name: "My designs" })).toHaveCount(0);
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible({ timeout: 60_000 });
}

export async function openDownload(page) {
  await page.getByRole("button", { name: "Download", exact: true }).click();
  const sheet = page.getByRole("dialog", { name: "Download" });
  await expect(sheet).toBeVisible();
  await expect(page.getByRole("heading", { name: "Download", exact: true })).toBeVisible();
  return sheet;
}

export async function closeDownload(page) {
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Download" })).toHaveCount(0);
}

// Artwork goes in file-first (Kent 2026-10-05): "Upload file" and the Artwork
// tile open the OS file browser through one hidden input, and the element is
// only added once a file comes back. Setting the input's files is that same
// path minus the dialog. NOTHING digitizes on its own any more, so `run`
// presses "Auto Digitize Image" — pass `run: false` for the browser's own
// flatten lane (service unreachable), which has no such button, or to assert
// on the loaded-but-unrun state.
export async function uploadArtwork(page, file, { run = true } = {}) {
  await page.getByTestId("art-file").setInputFiles(file);
  if (!run) return;
  await runDigitize(page);
}

// Press the one control that starts a digitize, and wait for the run to
// have actually started so a caller polling for the RESULT cannot read the
// previous one.
export async function runDigitize(page) {
  const run = page.locator(".dgp-run");
  await expect(run).toBeEnabled({ timeout: 30_000 });
  await expect(run).toHaveText("Auto Digitize Image");
  await run.click();
}

// Console guard: collects what a customer's DevTools would show in red —
// console errors, uncaught page errors, failed requests — so a spec can fail
// on them. Call BEFORE the first navigation. The Studio probes the digitizer
// service's /health on load; where no service runs (a bare sandbox) that
// probe is refused by design and the app falls back to the browser lane, so
// it is ignored by default. Pass `ignore` (RegExps tested against the message
// or URL) for anything else a spec provokes on purpose.
const SERVICE_PROBE = /127\.0\.0\.1:8721\/health/;
export function watchConsole(page, { ignore = [] } = {}) {
  const skip = [SERVICE_PROBE, ...ignore];
  const quiet = (s) => skip.some((re) => re.test(s));
  const problems = [];
  page.on("console", (m) => {
    if (m.type() !== "error") return;
    const text = m.text(), url = m.location().url || "";
    if (!quiet(text) && !quiet(url)) problems.push("[console] " + text.slice(0, 160));
  });
  page.on("pageerror", (e) => { if (!quiet(e.message)) problems.push("[pageerror] " + e.message.slice(0, 160)); });
  page.on("requestfailed", (r) => { if (!quiet(r.url())) problems.push("[requestfailed] " + r.url()); });
  return { problems, expectClean: () => expect(problems).toEqual([]) };
}
