<script lang="ts">
  export let matrix: number[][] = [];
  export let objectiveNames: string[] = [];

  function cellColor(value: number) {
    const intensity = Math.min(Math.abs(value) / 0.25, 1);
    if (value > 0) return `rgba(34, 197, 94, ${0.15 + intensity * 0.45})`;
    if (value < 0) return `rgba(239, 68, 68, ${0.15 + intensity * 0.45})`;
    return '#f8fafc';
  }
</script>

<div class="matrix-wrap">
  <table>
    <thead>
      <tr>
        <th></th>
        {#each objectiveNames as name}
          <th>{name}</th>
        {/each}
      </tr>
    </thead>

    <tbody>
      {#each objectiveNames as rowName, i}
        <tr>
          <th>{rowName}</th>
          {#each objectiveNames as _, j}
            {@const value = Number(matrix?.[i]?.[j] ?? 0)}
            <td style={`background: ${cellColor(value)}`}>
              {value >= 0 ? '+' : ''}{value.toFixed(2)}
            </td>
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<div class="legend">
  <span class="red"></span> Hurts
  <span class="green"></span> Helps
</div>

<style>
  .matrix-wrap {
    overflow-x: auto;
    margin-top: 0.6rem;
  }

  table {
    width: 100%;
    min-width: 22rem;
    border-collapse: collapse;
    font-size: 0.72rem;
  }

  th,
  td {
    padding: 0.35rem;
    border: 1px solid #e2e8f0;
    text-align: center;
  }

  th {
    background: #f8fafc;
    font-weight: 700;
  }

  tbody th {
    text-align: left;
  }

  .legend {
    display: flex;
    gap: 0.45rem;
    align-items: center;
    margin-top: 0.5rem;
    color: #64748b;
    font-size: 0.72rem;
  }

  .legend span {
    width: 0.7rem;
    height: 0.7rem;
    border-radius: 0.15rem;
    display: inline-block;
  }

  .red {
    background: #ef4444;
  }

  .green {
    background: #22c55e;
  }
</style>