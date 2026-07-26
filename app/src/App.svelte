<script>
  import { defaultProject, update, updateElement, selectElement, addElement, removeElement } from "./lib/project.js";
  import { applyTemplate } from "./lib/templates.js";
  import { canAdvance, nextStep, prevStep } from "./lib/flow.js";
  import {
    migrateLegacy,
    currentProjectId,
    setCurrentProject,
    loadProject,
    saveProject,
    createProject,
    renameProject,
    deleteProject,
    duplicateProject,
    listProjects,
  } from "./lib/projects.js";
  import { EMB } from "./lib/emb.js";
  import GarmentStep from "./ui/GarmentStep.svelte";
  import ContentStep from "./ui/ContentStep.svelte";
  import DownloadStep from "./ui/DownloadStep.svelte";
  import StepNav from "./ui/StepNav.svelte";
  import EmbroideryField from "./ui/EmbroideryField.svelte";
  import SizePanel from "./ui/SizePanel.svelte";
  import ProjectsDrawer from "./ui/ProjectsDrawer.svelte";
  import "./ui/theme.css";

  // The image itself never survives a reload (see `runtime` below), so a
  // persisted `_hasImage` flag on any element would let the flow gate pass
  // with nothing actually loaded — strip it from every element at boot AND
  // on every project switch (openProject/newDesign/deleteFromDrawer all
  // route through enterProject(), which calls this too).
  function resetHasImage(p) {
    if (!p.elements.some((el) => el._hasImage)) return p;
    return { ...p, elements: p.elements.map((el) => (el._hasImage ? { ...el, _hasImage: false } : el)) };
  }

  // Looks up a registry entry's display name from the current `projects`
  // snapshot; falls back if it's somehow missing (shouldn't happen, but
  // keeps the topbar from ever showing a blank name).
  function nameFor(id) {
    const entry = projects.find((p) => p.id === id);
    return entry ? entry.name : "Untitled design";
  }

  // ---- Boot (Slice 7 Task 2) ------------------------------------------------
  // migrateLegacy() first (one-time, no-op after the first successful run or
  // if there was never a legacy blob), then load whatever the registry says
  // is current. If there's no current project (first run) or its record is
  // missing/corrupt, loadProject returns null and we fall back to a brand
  // new project.
  migrateLegacy();
  let projects = listProjects();
  let currentId = currentProjectId();
  let bootProject = currentId ? loadProject(currentId) : null;
  if (!bootProject) {
    const created = createProject("Untitled design");
    currentId = created.id;
    bootProject = created.project;
    projects = listProjects();
  }

  let project = resetHasImage(bootProject);
  let projectName = nameFor(currentId);
  let step = "garment";
  let drawerOpen = false;
  // Runtime image state, owned here (not by ImagePanel) so it survives
  // ContentStep/ImagePanel being destroyed and recreated whenever the user
  // navigates steps or toggles Text/Image mode (both are {#if} blocks).
  // Keyed by element id (Task 4/Slice 5: was a single workImage/flat pair,
  // now a map so each image element in a multi-element project keeps its
  // own working image) -- see generate.js's generateAll(project, runtime).
  // workImages[id] is the prepped working source ({ rgba, w, h }, alpha-cut,
  // at WORK_MAX_PX) that ImagePanel re-flattens from; flats[id] is the
  // flattened palette derived from it. Neither is persisted -- only project
  // settings are (see persist() below).
  let runtime = { flats: {}, workImages: {} };
  // Dims of the SELECTED element's last generated design ({ widthMM, heightMM })
  // or null on failure/no-content -- fed to SizePanel so its W/H display
  // (and the below-5mm warning) always reflects the real current design,
  // including while the user drags the field's resize handles.
  let designDims = null;

  // The currently-selected element (SizePanel/ContentStep/the "create" step
  // summary all key off this one, not project.elements[0], so they stay in
  // sync with whatever the user clicked on the field).
  $: selectedElement = project.elements.find((el) => el.id === project.selectedId) || project.elements[0];

  const MM_PER_INCH = 25.4;

  // Single write path to the registry (Slice 7 Task 2) — replaces every old
  // saveLocal(project) call site. saveProject is a safe no-op if currentId
  // has since been deleted out from under an in-flight edit (see the A2/A10
  // no-op contract in projects.js), and bumps the registry's updatedAt, so
  // every persist also refreshes the `projects` snapshot (see instruction 3
  // in the task brief: refresh after every registry mutation).
  function persist() {
    saveProject(currentId, project);
    refreshProjects();
  }

  function refreshProjects() {
    projects = listProjects();
  }

  function apply(patch) {
    project = update(project, patch);
    persist();
  }

  // Patches a single element (by id) — used by EmbroideryField's drag/resize/
  // reclamp "elupdate" events and by ContentStep's element-scoped TextStep/
  // ImagePanel/SizePanel controls (see ContentStep.svelte), which all funnel
  // their patches through this same { id, patch } shape.
  function elUpdate(id, patch) {
    project = updateElement(project, id, patch);
    persist();
  }

  // Hoop width in mm for the current garment — new elements are seeded with
  // a size relative to it (see project.js's addElement). Falls back to a
  // sane default if the garment can't be resolved (shouldn't happen: the
  // "content" step, where adding elements happens, is unreachable until a
  // garment is picked — see flow.js's canAdvance).
  function hoopWidthMm(p) {
    const garment = p && EMB.getGarment(p.garmentId);
    return garment ? garment.widthIn * MM_PER_INCH : 300;
  }

  function onAddElement(type) {
    project = addElement(project, type, hoopWidthMm(project));
    persist();
  }

  function onRemoveElement(id) {
    project = removeElement(project, id);
    // Element ids can be reused (nextElementId in project.js picks the next
    // number after whatever's left once the removed one is gone), so a
    // stale runtime.flats/workImages entry for this id must be dropped now
    // — otherwise a LATER element that happens to land on the same id could
    // silently inherit this removed element's flattened art / working image.
    if (id in runtime.flats || id in runtime.workImages) {
      const flats = { ...runtime.flats };
      const workImages = { ...runtime.workImages };
      delete flats[id];
      delete workImages[id];
      runtime = { flats, workImages };
    }
    persist();
  }

  function pickTemplate(template) {
    project = applyTemplate(project, template);
    persist();
    step = "content";
  }

  function onSelect(id) {
    project = selectElement(project, id);
    persist();
  }

  function onImage(elementId, workImage) {
    runtime = { ...runtime, workImages: { ...runtime.workImages, [elementId]: workImage } };
  }

  function onFlat(elementId, flat) {
    runtime = { ...runtime, flats: { ...runtime.flats, [elementId]: flat } };
    elUpdate(elementId, { _hasImage: !!flat });
  }

  function onDims(detail) {
    designDims = detail;
  }

  function go(dir) {
    const s = dir > 0 ? nextStep(step) : prevStep(step);
    if (s) step = s;
  }

  function readable(id) {
    return (id || "")
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  }

  // ---- Project switching (Slice 7 Task 2) -----------------------------------
  //
  // Every path that moves the app to a different project (or a brand-new
  // one) routes through this: it resets the in-memory `project` (stripped of
  // any stale _hasImage flags), clears the per-element runtime image maps
  // and stale designDims (none of that survives a switch — see `runtime`'s
  // own comment above), and updates currentId/projectName/step together so
  // there's never a moment where one is stale relative to the others.
  function enterProject(id, proj, name, targetStep) {
    project = resetHasImage(proj);
    runtime = { flats: {}, workImages: {} };
    designDims = null;
    currentId = id;
    projectName = name;
    step = targetStep;
  }

  // Drawer "Open" (plan amendment A6): lands on "content", not "garment" --
  // switching to an existing, already-started project shouldn't dump the
  // user back at the beginning. Opening the CURRENTLY-open project just
  // closes the drawer.
  function openProject(id) {
    if (id === currentId) {
      drawerOpen = false;
      return;
    }
    const loaded = loadProject(id);
    if (!loaded) {
      // Shouldn't happen (the drawer only ever offers ids from `projects`),
      // but if the record's gone, don't leave the drawer open on a dead row.
      drawerOpen = false;
      return;
    }
    setCurrentProject(id);
    enterProject(id, loaded, nameFor(id), "content");
    drawerOpen = false;
  }

  // Drawer "+ New design": a genuinely blank project, so (unlike Open) it
  // lands on "garment" -- there's no content yet to jump into.
  function newDesign() {
    const created = createProject("Untitled design");
    enterProject(created.id, created.project, "Untitled design", "garment");
    drawerOpen = false;
    refreshProjects();
  }

  function renameCurrent(name) {
    const finalName = (name || "").trim() || "Untitled design";
    projectName = finalName;
    renameProject(currentId, finalName);
    refreshProjects();
  }

  function renameFromDrawer(id, name) {
    const finalName = (name || "").trim() || "Untitled design";
    renameProject(id, finalName);
    if (id === currentId) projectName = finalName;
    refreshProjects();
  }

  function duplicateFromDrawer(id) {
    // Never switches the app away from whatever's currently open (see
    // duplicateProject's own contract in projects.js).
    duplicateProject(id);
    refreshProjects();
  }

  // Plan amendment A2: deleting the CURRENTLY-open project must switch the
  // app to something else immediately -- the most-recently-updated
  // survivor, or a fresh "Untitled design" if that was the last project left
  // (delete-last is just this same fallback with zero survivors). currentId
  // and project are updated together (via enterProject) so there's never a
  // moment where an in-flight persist could fire against a half-switched
  // state -- and saveProject is a no-op for unknown ids regardless (see
  // projects.js).
  function deleteFromDrawer(id) {
    const wasCurrent = id === currentId;
    deleteProject(id);
    refreshProjects();
    if (!wasCurrent) return;

    if (projects.length > 0) {
      const next = projects[0]; // listProjects() sorts newest-updated first
      const loaded = loadProject(next.id);
      setCurrentProject(next.id);
      enterProject(next.id, loaded || defaultProject(), next.name, "content");
    } else {
      const created = createProject("Untitled design");
      enterProject(created.id, created.project, "Untitled design", "garment");
      refreshProjects();
    }
  }
</script>

<header class="topbar">
  <span class="logo">EMB&nbsp;Bot Studio</span>
  <input
    class="projectname"
    value={projectName}
    on:change={(e) => renameCurrent(e.currentTarget.value)}
    aria-label="Project name"
  />
  <button type="button" class="mydesigns" on:click={() => (drawerOpen = !drawerOpen)}>
    My designs <span class="badge">{projects.length}</span>
  </button>
</header>

{#if drawerOpen}
  <ProjectsDrawer
    {projects}
    {currentId}
    on:open={(e) => openProject(e.detail)}
    on:new={newDesign}
    on:rename={(e) => renameFromDrawer(e.detail.id, e.detail.name)}
    on:duplicate={(e) => duplicateFromDrawer(e.detail)}
    on:delete={(e) => deleteFromDrawer(e.detail)}
    on:close={() => (drawerOpen = false)}
  />
{/if}

<div class="studio">
  <aside class="panel">
    <div class="panel-body">
      {#if step === "garment"}
        <GarmentStep {project} on:update={(e) => apply(e.detail)} on:template={(e) => pickTemplate(e.detail)} />
      {:else if step === "content"}
        <ContentStep
          {project}
          workImage={runtime.workImages[project.selectedId]}
          flat={runtime.flats[project.selectedId]}
          {designDims}
          on:elupdate={(e) => elUpdate(e.detail.id, e.detail.patch)}
          on:select={(e) => onSelect(e.detail)}
          on:addelement={(e) => onAddElement(e.detail)}
          on:removeelement={(e) => onRemoveElement(e.detail)}
          on:image={(e) => onImage(project.selectedId, e.detail)}
          on:flat={(e) => onFlat(project.selectedId, e.detail)}
        />
      {:else if step === "create"}
        <div class="createstep">
          <h2>Ready to stitch</h2>
          <p>Looks good? The field on the right is your stitch-out.</p>
          <dl class="summary">
            <div><dt>Garment</dt><dd>{readable(project.garmentId)}</dd></div>
            {#if selectedElement.type === "image"}
              <div><dt>Content</dt><dd>Logo / image</dd></div>
              <div><dt>Colors</dt><dd>{selectedElement.nColors}{selectedElement.removeBg ? " · background removed" : ""}</dd></div>
            {:else}
              <div><dt>Content</dt><dd>Text — "{selectedElement.text}"</dd></div>
              <div><dt>Font</dt><dd>{readable(selectedElement.fontKey)}</dd></div>
            {/if}
          </dl>
          <p class="hint">Not quite right? Go back to adjust the garment or content — the field updates live.</p>
          <SizePanel project={{ ...project, ...selectedElement }} {designDims} on:update={(e) => elUpdate(selectedElement.id, e.detail)} />
        </div>
      {:else}
        <DownloadStep {project} {runtime} />
      {/if}
    </div>
    <StepNav {step} canNext={canAdvance(step, project)} on:back={() => go(-1)} on:next={() => go(1)} />
  </aside>

  <section class="field">
    <EmbroideryField
      {project}
      {runtime}
      on:elupdate={(e) => elUpdate(e.detail.id, e.detail.patch)}
      on:select={(e) => onSelect(e.detail)}
      on:dims={(e) => onDims(e.detail)}
    />
  </section>
</div>
