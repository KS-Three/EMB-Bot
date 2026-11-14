// Opening another design ends the field's edit modes (Kent's approval
// 2026-11-13). Element ids repeat across designs and the field is not
// remounted per design, so the only exit Reshape had (`reshape.elId !==
// project.selectedId`) let the mode carry into design B's same-id element,
// and Discard then wrote design A's entry snapshot into it. The hole draft
// and Move shape survived the same way, and a Move shape could even COMMIT
// A's move into B.
//
// Asserted on the source, like App.structuralUndo.spec.js: the field has no
// jsdom mount. The behaviour half is e2e/field-reshape-mode.spec.js (r2).
import { test, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIELD = readFileSync(join(HERE, "EmbroideryField.svelte"), "utf8");
const APP = readFileSync(join(HERE, "..", "App.svelte"), "utf8");

test("App tells the field which design it is showing", () => {
  expect(APP).toMatch(/<EmbroideryField[\s\S]*?projectId=\{currentId\}[\s\S]*?\/>/);
  expect(FIELD).toMatch(/export let projectId = null;/);
});

test("a change of design ends Reshape, the hole draft and Move shape, committing nothing", () => {
  expect(FIELD).toMatch(/\$: if \(projectId !== lastProjectId\) \{\s*lastProjectId = projectId;\s*leaveDesign\(\);\s*\}/);
  const body = FIELD.match(/function leaveDesign\(\) \{([\s\S]*?)\n  \}/);
  expect(body, "leaveDesign exists").not.toBeNull();
  const b = body[1];
  for (const call of ["endReshape()", "cancelHoleDraft()", "endShapeMove()", "pendingPatch = null", "dragMode = null"]) {
    expect(b, call).toContain(call);
  }
  // Leaving a design must never write into the next one.
  expect(b).not.toMatch(/commitShapeMove|discardReshape|dispatch\(/);
});

test("the design check runs before the selection block that compares element ids", () => {
  const sw = FIELD.indexOf("$: if (projectId !== lastProjectId)");
  const sel = FIELD.indexOf("$: if (project && project.selectedId !== undefined)");
  expect(sw).toBeGreaterThan(0);
  expect(sw).toBeLessThan(sel);
});
