<script>
  import DesignFilter from "./DesignFilter.svelte";
  export let hoops = [];
  export let onCriteria = () => {};
  let criteria = {};
  $: onCriteria(criteria);
</script>

<DesignFilter {hoops} bind:criteria />
