// Two designs a customer cannot tell apart, and two backups they cannot tell
// apart either.
//
// Every project the Studio creates is called "Untitled design" and nothing
// ever changed that unless the customer found Rename in the drawer. Measured
// in the shipped app 2026-09-07, two designs deep: "My designs" listed
// `Untitled design / today` twice. The exported backup was the worse half,
// because it leaves the app — both downloaded as `untitled-design.embproj`,
// so backing up three designs put three indistinguishable files in a
// Downloads folder.
//
// The same drive found the topbar's name field lying. `value={projectName}`
// is a one-way binding and Svelte only touches the DOM when the EXPRESSION
// changes, so a name that normalises back to the stored one left the typed
// text in the field for good: clearing the field on a design called
// "Untitled design" left the topbar blank while the drawer one panel over
// still read "Untitled design". Same defect the size field had (SizePanel's
// resyncIfClamped), at a second site.
//
// This is e2e rather than unit because every one of these is a disagreement
// BETWEEN surfaces — the field, the drawer row, the stored index and the
// download filename are four renderings of one name, and only the real app
// puts all four in the same place at the same time. deriveProjectName's own
// rules are pinned in src/lib/project.spec.js; the registry's sticky-name
// contract in src/lib/projects.spec.js.
import { test, expect } from "@playwright/test";

const nameField = (page) => page.getByLabel("Project name");
const rows = (page) => page.locator(".drawer-row-name");

async function startDesign(page, text) {
  await page.getByRole("button", { name: "Left Chest", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByPlaceholder("Type a name or word").fill(text);
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible();
}

async function openDrawer(page) {
  if (await page.locator(".drawer").count()) return;
  await page.getByRole("button", { name: /My designs/ }).first().click();
  await expect(page.locator(".drawer")).toBeVisible();
}

test("an unnamed design takes its name from what it says", async ({ page }) => {
  await page.goto("/");
  await startDesign(page, "FRITSCH'S STITCHES");
  await expect(nameField(page)).toHaveValue("FRITSCH'S STITCHES");

  // The guess follows the content — it is not a one-shot at creation.
  await page.getByPlaceholder("Type a name or word").fill("ACME CORP");
  await expect(nameField(page)).toHaveValue("ACME CORP");

  // ...and the drawer agrees, which is the surface the defect showed on.
  await openDrawer(page);
  await expect(rows(page)).toHaveText(["ACME CORP"]);
});

test("two designs list as two different rows, and export under two different filenames", async ({ page }) => {
  await page.goto("/");
  await startDesign(page, "HAT FRONT");

  await openDrawer(page);
  await page.getByRole("button", { name: "+ New design" }).click();
  await startDesign(page, "POLO LEFT CHEST");

  await openDrawer(page);
  // The defect was ["Untitled design", "Untitled design"].
  await expect(rows(page)).toHaveText(["POLO LEFT CHEST", "HAT FRONT"]);

  const [dl] = await Promise.all([
    page.waitForEvent("download"),
    page.locator(".drawer-row.current").getByRole("button", { name: "Export" }).click(),
  ]);
  // The defect was untitled-design.embproj for every design in the app.
  expect(dl.suggestedFilename()).toBe("polo-left-chest.embproj");
});

test("a name the customer types is never overwritten by a later edit", async ({ page }) => {
  await page.goto("/");
  await startDesign(page, "GUESSED");
  await expect(nameField(page)).toHaveValue("GUESSED");

  await nameField(page).fill("Kent's cap job");
  await nameField(page).blur();
  await expect(nameField(page)).toHaveValue("Kent's cap job");

  // Editing the design must not take the chosen name away again.
  await page.getByPlaceholder("Type a name or word").fill("SOMETHING ELSE");
  await expect(page.getByText(/^[\d,]+ stitches/)).toBeVisible();
  await expect(nameField(page)).toHaveValue("Kent's cap job");

  await openDrawer(page);
  await expect(rows(page)).toHaveText(["Kent's cap job"]);
});

test("the name field shows what the design is actually called, not what was typed at it", async ({ page }) => {
  await page.goto("/");
  await startDesign(page, "HELLO");
  await expect(nameField(page)).toHaveValue("HELLO");

  // Clearing the field asks for the app's guess back. Before the fix the
  // field kept the empty string, because projectName never changed value.
  await nameField(page).fill("");
  await nameField(page).blur();
  await expect(nameField(page)).toHaveValue("HELLO");

  // Whitespace normalises to the same place, and used to stick the same way.
  await nameField(page).fill("   ");
  await nameField(page).blur();
  await expect(nameField(page)).toHaveValue("HELLO");

  // The three surfaces have to agree, which is the whole point.
  await openDrawer(page);
  await expect(rows(page)).toHaveText(["HELLO"]);
});

test("a design saved before auto-naming existed gets caught up when it is opened", async ({ page }) => {
  // The population this matters most for: every project already sitting in a
  // customer's browser predates the autoName flag and is called "Untitled
  // design". They must not have to type into each one to get a name — so
  // boot catches them up, which is why App's enterProject() and its boot
  // path both call applyAutoName().
  await page.goto("/");
  await page.evaluate(() => {
    localStorage.clear();
    const id = "legacy-1";
    localStorage.setItem(
      "embstudio:p:" + id,
      JSON.stringify({
        version: 2, garmentId: "left_chest", selectedId: "e1", selectedIds: ["e1"],
        elements: [{ id: "e1", type: "text", text: "OLD PROJECT", fontKey: "medium_font",
                     colorRgb: [20, 20, 20], colorRanges: [], weightPreset: "normal",
                     slantDeg: 0, letterSpacingMm: 0, sizeMm: 60, offsetXMm: 0, offsetYMm: 0 }],
        fabricRgb: [235, 232, 223], hoopId: null,
      })
    );
    // No autoName key at all — exactly the shape already on disk out there.
    localStorage.setItem("embstudio:index", JSON.stringify([{ id, name: "Untitled design", updatedAt: Date.now() }]));
    localStorage.setItem("embstudio:current", id);
  });
  await page.reload();
  await expect(page.getByLabel("Project name")).toHaveValue("OLD PROJECT");
});

test("undo carries the name back with the text, and redo carries it forward", async ({ page }) => {
  // An undo is an edit as far as every surface downstream of it is
  // concerned. Measured 2026-09-07, the same day auto-naming shipped:
  // applyHistorySnapshot() was the one path that changed `project` without
  // going through persist(), so after an undo the design read HELLO while
  // the topbar, the drawer and the stored index all still read GOODBYE.
  await page.goto("/");
  await startDesign(page, "HELLO");
  await expect(nameField(page)).toHaveValue("HELLO");

  // history.js coalesces records landing within 500 ms into ONE step (the
  // drag/slider storm it exists for). Without this wait both edits merge and
  // a single undo correctly goes back past HELLO to the empty design -- the
  // app behaving right, and the test asking the wrong question. Do not
  // "optimise" this away.
  await page.waitForTimeout(700);
  await page.getByPlaceholder("Type a name or word").fill("GOODBYE");
  await expect(nameField(page)).toHaveValue("GOODBYE");

  await page.getByRole("button", { name: "Undo" }).click();
  await expect(page.getByPlaceholder("Type a name or word")).toHaveValue("HELLO");
  await expect(nameField(page)).toHaveValue("HELLO");
  await openDrawer(page);
  await expect(rows(page)).toHaveText(["HELLO"]);
  await page.keyboard.press("Escape");

  await page.getByRole("button", { name: "Redo" }).click();
  await expect(page.getByPlaceholder("Type a name or word")).toHaveValue("GOODBYE");
  await expect(nameField(page)).toHaveValue("GOODBYE");
});
