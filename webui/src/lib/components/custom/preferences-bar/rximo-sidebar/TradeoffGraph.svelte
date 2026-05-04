<script lang="ts">
  export let shapValues: any = {};
  export let objectiveNames: string[] = [];
  export let focusObjective: string | null = null;

  function matrixFromShap(values: any): number[][] {
    if (Array.isArray(values)) return values;
    if (Array.isArray(values?.values)) return values.values;
    if (Array.isArray(values?.shap_values)) return values.shap_values;
    if (Array.isArray(values?.matrix)) return values.matrix;
    return [];
  }

  $: matrix = matrixFromShap(shapValues);
  $: targetIndex = Math.max(0, objectiveNames.indexOf(focusObjective ?? ''));

  $: nodes = objectiveNames.map((name, i) => {
    const angle = (2 * Math.PI * i) / Math.max(objectiveNames.length, 1) - Math.PI / 2;
    return {
      name,
      i,
      x: 120 + Math.cos(angle) * 78,
      y: 88 + Math.sin(angle) * 58
    };
  });

  $: edges = nodes
    .filter((n) => n.i !== targetIndex)
    .map((n) => ({
      from: n,
      to: nodes[targetIndex],
      value: Number(matrix?.[n.i]?.[targetIndex] ?? 0)
    }))
    .filter((e) => Math.abs(e.value) > 0.005);
</script>

<div class="graph">
  <svg viewBox="0 0 240 175" role="img" aria-label="Trade-off network">
    <defs>
      <marker id="arrow-red" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#ef4444" />
      </marker>
      <marker id="arrow-green" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#22c55e" />
      </marker>
    </defs>

    {#each edges as edge}
      <line
        x1={edge.from.x}
        y1={edge.from.y}
        x2={edge.to.x}
        y2={edge.to.y}
        stroke={edge.value < 0 ? '#ef4444' : '#22c55e'}
        stroke-width={1.5 + Math.min(Math.abs(edge.value) * 8, 4)}
        stroke-dasharray={edge.value > 0 ? '5 4' : '0'}
        marker-end={edge.value < 0 ? 'url(#arrow-red)' : 'url(#arrow-green)'}
        opacity="0.85"
      />
    {/each}

    {#each nodes as node}
      <circle
        cx={node.x}
        cy={node.y}
        r={node.i === targetIndex ? 11 : 9}
        fill={node.i === targetIndex ? '#3b82f6' : '#e2e8f0'}
        stroke="#334155"
        stroke-width="1"
      />
      <text x={node.x} y={node.y + 23} text-anchor="middle" font-size="10" fill="#334155">
        {node.name}
      </text>
    {/each}
  </svg>
</div>

<div class="legend">
  <span class="line red"></span> Conflict
  <span class="line green"></span> Synergy
</div>

<style>
  .graph {
    width: 100%;
    background: #f8fafc;
    border-radius: 0.5rem;
    overflow: hidden;
  }

  svg {
    width: 100%;
    height: auto;
    display: block;
  }

  .legend {
    display: flex;
    gap: 0.8rem;
    align-items: center;
    margin-top: 0.45rem;
    color: #64748b;
    font-size: 0.72rem;
  }

  .line {
    display: inline-block;
    width: 1.4rem;
    height: 0;
    border-top: 2px solid;
  }

  .red {
    border-color: #ef4444;
  }

  .green {
    border-color: #22c55e;
    border-style: dashed;
  }
</style>