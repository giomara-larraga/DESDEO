<script lang="ts">
  import Dashboard
    from "$lib/components/custom/adm/dashboard/Dashboard.svelte";

    

  export let data;
</script>

<Dashboard
  log={data.log}
  populationHistory={data.populationHistory}
/>