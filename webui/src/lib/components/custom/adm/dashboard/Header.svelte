<script lang="ts">
  import type { ADMLog } from "$lib/adm/types";

  export let log: ADMLog;
  export let selectedIteration: number;
</script>

<header class="header">
  <div>
    <h1>ADM Visual Analytics</h1>
    <p>
      {log.problem.name} · {log.problem.objectives} objectives ·
      Iteration {selectedIteration}/{log.iterations.length}
    </p>
  </div>

  <div class="badges">
    <span>{log.experiment_id}</span>
    <span>{log.methods.join(" vs ")}</span>
  </div>
</header>

<style>
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.25rem 1.5rem;
    border-bottom: 1px solid #e5e7eb;
    background: white;
  }

  h1 {
    margin: 0;
    font-size: 1.35rem;
  }

  p {
    margin: 0.25rem 0 0;
    color: #64748b;
  }

  .badges {
    display: flex;
    gap: 0.5rem;
  }

  .badges span {
    background: #f3f4f6;
    border-radius: 999px;
    padding: 0.4rem 0.75rem;
    font-size: 0.8rem;
  }
</style>