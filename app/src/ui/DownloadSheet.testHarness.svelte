<script>
  import DownloadSheet from "./DownloadSheet.svelte";
  export let project;
  export let runtime = { flats: {}, workImages: {} };
  export let summaryRows = [];
  export let qualityEntries = [];
  export let qualityPartial = false;
  export let ready = true;
  export let onClose = () => {};
  export let onLocate = () => {};
</script>

<DownloadSheet
  {project}
  {runtime}
  digitizerHealth={null}
  {summaryRows}
  {qualityEntries}
  {qualityPartial}
  {ready}
  on:close={onClose}
  on:locate={(e) => onLocate(e.detail)}
/>
