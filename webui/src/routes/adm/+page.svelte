<script lang="ts">
  import Dashboard from "$lib/components/custom/adm/dashboard/Dashboard.svelte";
  import type { ADMLog } from "$lib/adm/types";

  import exampleLog from "$lib/data/example_adm_phi_log.json";

  const log = exampleLog as ADMLog;
</script>

<Dashboard {log} />