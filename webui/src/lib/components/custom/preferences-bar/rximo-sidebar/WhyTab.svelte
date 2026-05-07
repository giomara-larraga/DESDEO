<script lang="ts">
  import ShapImpactBars from './ShapImpactBars.svelte';
  import ShapMatrixDetails from './ShapMatrixDetails.svelte';

  export let shapValues: any = {};
  export let shapBaseline:number = 0;
  export let objectiveNames: string[] = [];
  export let focusObjective: string | null = null;
  export let selectedSolution: any = null;

  function matrixFromShap(values: any): number[][] {
    if (Array.isArray(values)) return values;
    if (Array.isArray(values?.values)) return values.values;
    if (Array.isArray(values?.shap_values)) return values.shap_values;
    if (Array.isArray(values?.matrix)) return values.matrix;
    return [];
  }

  function getObjectiveValue(solution: any, name: string | null): number | null {
    if (!solution || !name) return null;
    if (typeof solution[name] === 'number') return solution[name];
    if (solution.objective_values && typeof solution.objective_values[name] === 'number') {
      return solution.objective_values[name];
    }
    if (Array.isArray(solution.objective_values)) {
      const idx = objectiveNames.indexOf(name);
      return solution.objective_values[idx] ?? null;
    }
    return null;
  }

  $: matrix = matrixFromShap(shapValues);
  $: targetIndex = Math.max(0, objectiveNames.indexOf(focusObjective ?? ''));
  $: column = matrix.map((row) => Number(row?.[targetIndex] ?? 0));
  $: drivers = objectiveNames.map((name, i) => ({
    name,
    value: column[i] ?? 0,
    own: i === targetIndex
  })).sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

  $: strongestHurt = drivers.find((d) => d.value < 0 && !d.own);
  $: strongestHelp = drivers.find((d) => d.value > 0);
  $: ownEffect = drivers.find((d) => d.own);
  $: achievedValue = getObjectiveValue(selectedSolution, focusObjective);
</script>

<section class="card">
  <h3>
    Why is {focusObjective}
    {#if achievedValue !== null}
      = {achievedValue.toFixed(2)}
    {/if}
    ?
  </h3>

  {#if strongestHurt || strongestHelp || ownEffect}
    <ul>
      {#if strongestHurt}
        <li>
          <strong>{strongestHurt.name}</strong> is the main negative influence on
          <strong>{focusObjective}</strong>.
        </li>
      {/if}

      {#if strongestHelp}
        <li>
          <strong>{strongestHelp.name}</strong> helps <strong>{focusObjective}</strong>
          the most.
        </li>
      {/if}

      {#if ownEffect}
        <li>
          The own aspiration for <strong>{focusObjective}</strong>
          {ownEffect.value >= 0 ? 'supports' : 'hurts'} this outcome slightly.
        </li>
      {/if}
    </ul>
  {:else}
    <p class="muted">No SHAP explanation is available for this solution yet.</p>
  {/if}
</section>

<section class="section">
  <h3>Main drivers</h3>
  <ShapImpactBars {drivers} />
  
</section>

<details class="details">
  <summary>Show details: SHAP matrix</summary>
  <ShapMatrixDetails {matrix} {objectiveNames} />
</details>

<style>
  .card,
  .section,
  .details {
    background: white;
    border: 1px solid #d8e0eb;
    border-radius: 0.65rem;
    padding: 0.8rem;
  }

  h3 {
    margin: 0 0 0.55rem;
    font-size: 0.86rem;
  }

  ul {
    margin: 0;
    padding-left: 1.1rem;
    line-height: 1.45;
  }

  li + li {
    margin-top: 0.25rem;
  }

  .muted {
    margin: 0;
    color: #64748b;
  }

  .section {
    margin-top: 0.8rem;
  }

  .details {
    margin-top: 0.8rem;
  }

  summary {
    cursor: pointer;
    font-weight: 700;
  }
</style>