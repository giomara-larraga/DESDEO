<script lang="ts">
  import type { ADMLog } from "$lib/adm/types";
  import { getIteration, getObjectives } from "$lib/adm/adapters";

  export let log: ADMLog;
  export let selectedIteration: number;

  $: iteration = getIteration(log, selectedIteration);
  $: objectives = getObjectives(log);
</script>

<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th>Solution</th>
        <th>Method</th>
        {#each objectives as obj}
          <th>{obj}</th>
        {/each}
      </tr>
    </thead>

    <tbody>
      {#each iteration.composite_front as solution}
        <tr>
          <td>{solution.solution_id}</td>
          <td>{solution.method}</td>
          {#each solution.objectives as value}
            <td>{value.toFixed(3)}</td>
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .table-wrap {
    max-height: 360px;
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;
  }

  th,
  td {
    padding: 0.5rem;
    border-bottom: 1px solid #e5e7eb;
    text-align: left;
  }

  th {
    background: #f8fafc;
    position: sticky;
    top: 0;
  }
</style>