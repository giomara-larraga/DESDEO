<script lang="ts">
  export let shapValues: any = {};
  export let objectiveNames: string[] = [];
  export let focusObjective: string | null = null;
  export let currentPreference: any = null;
  export let previousPreference: any = null;

  function vectorFromPreference(pref: any): number[] {
    if (!pref) return [];
    if (Array.isArray(pref)) return pref.map(Number);
    if (Array.isArray(pref.values)) return pref.values.map(Number);
    if (Array.isArray(pref.preference_values)) return pref.preference_values.map(Number);

    return objectiveNames.map((name) => Number(pref?.[name] ?? 0));
  }

  function matrixFromShap(values: any): number[][] {
    if (Array.isArray(values)) return values;
    if (Array.isArray(values?.values)) return values.values;
    if (Array.isArray(values?.shap_values)) return values.shap_values;
    if (Array.isArray(values?.matrix)) return values.matrix;
    return [];
  }

  $: current = vectorFromPreference(currentPreference);
  $: previous = vectorFromPreference(previousPreference);
  $: deltas = objectiveNames.map((name, i) => ({
    name,
    previous: previous[i],
    current: current[i],
    delta: (current[i] ?? 0) - (previous[i] ?? 0)
  }));

  $: changed = deltas
    .filter((d) => Number.isFinite(d.delta))
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));

  $: largestChange = changed[0];

  $: matrix = matrixFromShap(shapValues);
  $: targetIndex = Math.max(0, objectiveNames.indexOf(focusObjective ?? ''));
  $: impactRows = objectiveNames.map((name, i) => ({
    name,
    impact: Number(matrix?.[i]?.[targetIndex] ?? 0)
  })).sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact));
</script>

<section class="card">
  <h3>Change from previous iteration</h3>

  {#if largestChange}
    <p>
      Most notable preference change:
      <strong>{largestChange.name}</strong>
      {largestChange.delta >= 0 ? 'increased' : 'decreased'}
      by <strong>{Math.abs(largestChange.delta).toFixed(2)}</strong>.
    </p>
  {:else}
    <p class="muted">No previous preference vector is available.</p>
  {/if}
</section>

<section class="card">
  <h3>Impact on {focusObjective}</h3>

  <div class="impact-list">
    {#each impactRows.slice(0, 4) as row}
      <div class="impact-row">
        <span>{row.name}</span>
        <strong class:positive={row.impact > 0} class:negative={row.impact < 0}>
          {row.impact >= 0 ? '+' : ''}{row.impact.toFixed(2)}
        </strong>
      </div>
    {/each}
  </div>
</section>

<details class="details">
  <summary>Show preference changes</summary>

  <table>
    <thead>
      <tr>
        <th>Objective</th>
        <th>Previous</th>
        <th>Current</th>
        <th>Δ</th>
      </tr>
    </thead>
    <tbody>
      {#each deltas as row}
        <tr>
          <td>{row.name}</td>
          <td>{Number.isFinite(row.previous) ? row.previous.toFixed(2) : '—'}</td>
          <td>{Number.isFinite(row.current) ? row.current.toFixed(2) : '—'}</td>
          <td class:positive={row.delta > 0} class:negative={row.delta < 0}>
            {Number.isFinite(row.delta) ? `${row.delta >= 0 ? '+' : ''}${row.delta.toFixed(2)}` : '—'}
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
</details>

<style>
  .card,
  .details {
    background: white;
    border: 1px solid #d8e0eb;
    border-radius: 0.65rem;
    padding: 0.8rem;
  }

  .card + .card,
  .details {
    margin-top: 0.8rem;
  }

  h3 {
    margin: 0 0 0.5rem;
    font-size: 0.86rem;
  }

  p {
    margin: 0;
    line-height: 1.4;
  }

  .muted {
    color: #64748b;
  }

  .impact-list {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .impact-row {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    font-size: 0.82rem;
  }

  .positive {
    color: #059669;
  }

  .negative {
    color: #dc2626;
  }

  summary {
    cursor: pointer;
    font-weight: 700;
  }

  table {
    width: 100%;
    margin-top: 0.6rem;
    border-collapse: collapse;
    font-size: 0.75rem;
  }

  th,
  td {
    padding: 0.35rem;
    border-bottom: 1px solid #e2e8f0;
    text-align: right;
  }

  th:first-child,
  td:first-child {
    text-align: left;
  }
</style>