# Studio Slice 7: Saved Projects + Onboarding Hints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Users can keep MULTIPLE named designs (create, rename, duplicate, delete, reopen — all client-side) and first-time users get a few gentle, dismissible hints that teach the field's superpowers (drag to move, corners to resize, add elements).

**Architecture:** A localStorage **project registry** (`lib/projects.js`): an index entry per project (`{id, name, updatedAt}`) + one storage record per project id; the CURRENT project pointer replaces the single `embstudio:last` blob (which migrates in as "My first design"). App gains a topbar project-name control + a "My designs" drawer (list/open/rename/duplicate/delete/new). Onboarding = `lib/hints.js` (seen-flags in localStorage) + a small dismissible `Hint.svelte` bubble shown at 3 moments.

**Tech Stack:** unchanged. Branch `feat/studio-projects`.

## Global Constraints

- Client-only; no backend. Do NOT modify `src/*.js` (engine untouched this slice).
- Migration: an existing `embstudio:last` blob (v1 OR v2 project) must appear as a registry project named "My first design" on first load — nothing a user made may be lost. Idempotent (no duplicate migration on later loads).
- Storage keys: index `embstudio:index` (JSON array), project `embstudio:p:<id>`, current pointer `embstudio:current`, hints `embstudio:hints`. All localStorage ops wrapped in try/catch (quota/denied → app still works, just without persistence).
- Runtime image data (workImage/flat) is NOT persisted (existing behavior) — reopening an image project shows its elements with the existing "upload again" affordance (`_hasImage` stripped on load, as today).
- Hints: max 3, each shows ONCE (per flag), dismiss on X or on the action being performed; no overlays that block input; reduced-motion safe (no animation needed).
- Auto-save keeps current behavior (every change), now writing to the CURRENT project record + bumping its `updatedAt`.
- App tests `.spec.js`; suites stay green (engine 155, app 105+).

---

### Task 1: Project registry (lib) + migration

**Files:**
- Create: `app/src/lib/projects.js` (+`projects.spec.js`)
- Modify: `app/src/lib/save.js` (+spec) — becomes a thin compat layer or is absorbed; keep `serialize/deserialize` (migration logic) exported from wherever they live.

**Interfaces (all try/catch-safe, pure where possible):**
- `listProjects() → [{id, name, updatedAt}]` (sorted updatedAt desc)
- `createProject(name?) → {id, project}` (fresh `defaultProject()`, registers in index, sets current)
- `loadProject(id) → project|null` (runs `migrateProject`/deserialize on the stored record)
- `saveProject(id, project)` (writes record + bumps index updatedAt)
- `renameProject(id, name)`, `deleteProject(id)` (also clears current pointer if it pointed there), `duplicateProject(id, name?) → {id, project}`
- `currentProjectId() → id|null`, `setCurrentProject(id)`
- `migrateLegacy()` — if `embstudio:last` exists AND no index yet: create index with one project "My first design" from that blob, set current, REMOVE the legacy key. Called once at App boot before anything reads.
- Spec coverage: CRUD round-trips (mock localStorage via a simple in-memory shim — node env has no localStorage; build a `globalThis.localStorage` stub in beforeEach), legacy migration (v1 blob → registry project, legacy key gone, idempotent second call), delete-current clears pointer, list ordering.

- [ ] TDD; full app suite green; commit — `git commit -m "feat(app): client-side project registry with legacy migration"`

### Task 2: App wiring — topbar name + My designs drawer

**Files:**
- Create: `app/src/ui/ProjectsDrawer.svelte`
- Modify: `app/src/App.svelte`, `app/src/ui/theme.css`

**Behavior:**
- Boot: `migrateLegacy()`; load `currentProjectId()`'s project (else `createProject("Untitled design")`). All existing `saveLocal(project)` call sites become `saveProject(currentId, project)` (wrap in one `persist()` helper in App).
- Topbar: editable project name (inline input, one-way + change dispatch → renameProject) + a "My designs" button (count badge) opening the drawer.
- Drawer (right-side overlay panel, closes on backdrop click / Esc): rows (name, updatedAt "today/date"), actions per row: Open (loads project + resets runtime maps + step→"garment"), Duplicate, Rename (inline), Delete (confirm via two-tap: button becomes "Really delete?" for 3s — no window.confirm). "+ New design" at top. Current project row highlighted; Open on current = just closes.
- Switching projects: clear `runtime` (flats/workImages) and strip `_hasImage` flags on load (image data doesn't persist — existing convention).

- [ ] Implement; suite green; build clean; commit — `git commit -m "feat(app): project name + My designs drawer (open/rename/duplicate/delete/new)"`

### Task 3: Onboarding hints

**Files:**
- Create: `app/src/lib/hints.js` (+spec), `app/src/ui/Hint.svelte`
- Modify: `app/src/ui/EmbroideryField.svelte` (or its wrapper markup in App), `app/src/ui/ContentStep.svelte`, `app/src/ui/theme.css`

**Behavior:**
- `hints.js`: `shouldShow(key) → bool`, `dismiss(key)` (persists `embstudio:hints` set; try/catch-safe). Keys: `"drag-field"`, `"add-elements"`, `"templates"`.
- `Hint.svelte`: small floating bubble (icon + one sentence + ✕), absolutely positioned by the host, `role="status"`, no animation.
- Placements (each renders only while `shouldShow`):
  1. `templates` — on the garment step near the Quick-start row: "One click starts a ready-made design."
  2. `drag-field` — over the field's corner the first time a design EXISTS: "Drag the design to move it — corners resize." Auto-dismiss on first pointerdown on the canvas (plus ✕).
  3. `add-elements` — on the content step by the +Text/+Image buttons: "Combine text and a logo in one design." Auto-dismiss when a second element is added (plus ✕).
- Spec: hints.js flag logic (default show, dismissed stays dismissed across instances, storage-throw → treated as show:false? NO — storage-throw → default SHOW but dismiss becomes no-op; document).

- [ ] TDD lib; implement UI; suite green; build clean; commit — `git commit -m "feat(app): first-run onboarding hints (3, dismissible)"`

### Task 4: Browser acceptance + docs (controller)

- [ ] Live: legacy blob migrates to "My first design"; create second project, build a design in each, switch back and forth (fields restore); rename inline; duplicate copies elements; two-tap delete; hints appear once each, dismiss properly (incl. auto-dismiss paths), never reappear after reload; regression: full text+image flow.
- [ ] README; ledger; commit. FINAL REVIEW via multi-lens workflow (correctness / state-and-storage / UX-a11y lenses + adversarial verification), fix loop, merge to main + push.

## Notes for the implementer
- `defaultProject()`/`migrateProject` live in `app/src/lib/project.js` (v2 model, Slice 5).
- App currently boots via `loadLocal() || defaultProject()` + strips `_hasImage` — that logic moves into the registry load path.
- Keep `save.js`'s exported names working if other modules import them (grep first).

---

## PLAN AMENDMENTS (from 4-lens adversarial critique — these OVERRIDE the sections above)

**A1 (BLOCKING) — migrateLegacy write-ordering, no data loss ever:** migrateLegacy MUST: (1) write the project record `embstudio:p:<id>`; (2) READ IT BACK and verify it parses; (3) write index + current pointer; (4) ONLY THEN `removeItem("embstudio:last")`. On ANY failure along the way, leave `embstudio:last` untouched (migration retries next boot). Spec test: a storage stub whose `setItem` throws → legacy key still present, no partial index.

**A2 (BLOCKING) — delete-current semantics:** After the drawer deletes the CURRENTLY-OPEN project, App must immediately switch: load the most-recent remaining project, or `createProject("Untitled design")` if none — updating in-memory `currentId` BEFORE any persist can fire. `saveProject(id, project)` with an id NOT in the index is a defined NO-OP (spec-tested) — auto-save can never resurrect a deleted record. Task 4 acceptance adds: delete-current and delete-last flows.

**A3 — ids:** all minted ids use `crypto.randomUUID()` (fallback `"p" + Date.now() + "-" + Math.random().toString(36).slice(2, 8)` if unavailable). Spec: two consecutive createProject/duplicateProject calls yield distinct ids.

**A4 — migration spec coverage:** Task 1 specs must cover BOTH a v1 blob AND a v2 blob in `embstudio:last`, plus a corrupt/unparseable blob (→ no registry entry created, legacy key removed only if unparseable-and-unrecoverable... NO: on corrupt blob, create a project from `defaultProject()`? SIMPLEST SAFE: corrupt blob → leave key, create nothing, boot proceeds to createProject; document).

**A5 — two-tap delete hardening:** after the button arms ("Really delete?"), IGNORE clicks for 300ms (double-click protection); disarm after 3s.

**A6 — Open lands on "content"** (the editing hub), not "garment" — switching projects mid-work shouldn't dump users at the start. (Open-on-current still just closes.)

**A7 — hint semantics:** hints are show-until-dismissed (✕ or auto-dismiss action) — reword "shows ONCE" accordingly. AND at most ONE hint is visible at a time, priority `drag-field` > `add-elements` > `templates` (lower-priority hints stay hidden while a higher one is eligible; they may appear later if still un-dismissed).

**A8 — drag-field trigger:** eligible only when the generated design has `stitchCount > 0` (an empty default project has an element but no stitches — must NOT trigger).

**A9 — hint presentation:** hints `templates` and `add-elements` are IN-FLOW callout rows (icon + sentence + ✕, distinct background) inserted in the panel markup next to their anchor — no absolute positioning inside the scrollable panel. Only `drag-field` floats (over the canvas corner, where nothing interactive underlies it). Task 3 file list therefore also includes `app/src/ui/GarmentStep.svelte` (hosts the templates callout above TemplateRow).

**A10 — saveProject upsert-vs-noop:** explicitly: update-only (no-op for unknown ids) per A2; `renameProject`/`deleteProject` on unknown ids are also safe no-ops.
