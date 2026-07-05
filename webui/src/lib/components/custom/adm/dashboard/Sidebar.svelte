<script lang="ts">
  import type { ADMLog } from "$lib/adm/types";

  export let log: ADMLog;
</script>

<aside class="sidebar">
  <h2>Experiment</h2>

  <div class="field">
    <label>Problem</label>
    <strong>{log.problem.name}</strong>
  </div>

  <div class="field">
    <label>Objectives</label>
    <strong>{log.problem.objectives}</strong>
  </div>

  <div class="field">
    <label>Variables</label>
    <strong>{log.problem.variables}</strong>
  </div>

  <div class="field">
    <label>Methods</label>
    {#each log.methods as method}
      <span class="method">{method}</span>
    {/each}
  </div>

  <h2>ADM</h2>

  <div class="field">
    <label>Learning iterations</label>
    <strong>{log.adm_configuration.learning_iterations}</strong>
  </div>

  <div class="field">
    <label>Decision iterations</label>
    <strong>{log.adm_configuration.decision_iterations}</strong>
  </div>

  <div class="field">
    <label>Generations / iteration</label>
    <strong>{log.adm_configuration.generations_per_iteration}</strong>
  </div>

  <div class="field">
    <label>Reference vectors</label>
    <strong>{log.adm_configuration.number_of_reference_vectors}</strong>
  </div>
</aside>

<style>
  .sidebar {
    background: #111827;
    color: white;
    padding: 1.5rem;
    min-height: 100vh;
  }

  h2 {
    font-size: 0.85rem;
    text-transform: uppercase;
    color: #9ca3af;
    margin: 1.25rem 0 0.75rem;
  }

  .field {
    margin-bottom: 1rem;
  }

  label {
    display: block;
    font-size: 0.75rem;
    color: #9ca3af;
    margin-bottom: 0.25rem;
  }

  .method {
    display: block;
    background: #1f2937;
    padding: 0.45rem 0.65rem;
    border-radius: 0.5rem;
    margin-top: 0.35rem;
  }
</style>