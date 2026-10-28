<script>
  import GarmentPicker from "./GarmentPicker.svelte";
  export let garmentId = "left_chest";
  export let placementId = null;
  export let onUpdate = () => {};
</script>

<GarmentPicker {garmentId} {placementId} on:update={onUpdate} />
