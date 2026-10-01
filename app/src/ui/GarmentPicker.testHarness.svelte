<script>
  import GarmentPicker from "./GarmentPicker.svelte";
  export let garmentId = "left_chest";
  export let onUpdate = () => {};
</script>

<GarmentPicker {garmentId} on:update={onUpdate} />
