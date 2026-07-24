<script>
  import { defaultProject, update } from "./lib/project.js";
  import { canAdvance, nextStep, prevStep } from "./lib/flow.js";
  import { saveLocal, loadLocal } from "./lib/save.js";
  import GarmentStep from "./ui/GarmentStep.svelte";
  import TextStep from "./ui/TextStep.svelte";
  import DownloadStep from "./ui/DownloadStep.svelte";
  import StepNav from "./ui/StepNav.svelte";
  import EmbroideryField from "./ui/EmbroideryField.svelte";
  import "./ui/theme.css";

  let project = loadLocal() || defaultProject();
  let step = "garment";

  function apply(patch) {
    project = update(project, patch);
    saveLocal(project);
  }

  function go(dir) {
    const s = dir > 0 ? nextStep(step) : prevStep(step);
    if (s) step = s;
  }
</script>

<header class="topbar"><span class="logo">EMB&nbsp;Bot Studio</span></header>

<div class="studio">
  <aside class="panel">
    <div class="panel-body">
      {#if step === "garment"}
        <GarmentStep {project} on:update={(e) => apply(e.detail)} />
      {:else if step === "text"}
        <TextStep {project} on:update={(e) => apply(e.detail)} />
      {:else}
        <DownloadStep {project} />
      {/if}
    </div>
    <StepNav {step} canNext={canAdvance(step, project)} on:back={() => go(-1)} on:next={() => go(1)} />
  </aside>

  <section class="field">
    <EmbroideryField {project} />
  </section>
</div>
