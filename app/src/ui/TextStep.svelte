<script>
  import FontGallery from "./FontGallery.svelte";
  import { createEventDispatcher } from "svelte";
  export let project;
  const d = createEventDispatcher();

  function rgbToHex([r, g, b]) {
    return "#" + [r, g, b].map((v) => v.toString(16).padStart(2, "0")).join("");
  }
  function hexToRgb(h) {
    return [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  }
</script>

<h2>Your text</h2>
<input
  class="textin"
  type="text"
  bind:value={project.text}
  on:input={() => d("update", { text: project.text })}
  placeholder="Type a name or word"
/>
<label>
  Color
  <input type="color" value={rgbToHex(project.colorRgb)} on:input={(e) => d("update", { colorRgb: hexToRgb(e.target.value) })} />
</label>
<h3>Font</h3>
<FontGallery selected={project.fontKey} on:pick={(e) => d("update", { fontKey: e.detail })} />
