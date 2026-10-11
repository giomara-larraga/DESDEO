<script lang="ts">
  import { onMount } from "svelte";
  import * as d3 from "d3";
  import type { ADMLog } from "$lib/adm/types";
  import { getIteration } from "$lib/adm/adapters";

  export let log: ADMLog;
  export let selectedIteration: number;
  export let selectedVector: string | null = null;
  export let xObjective = 0;
  export let yObjective = 1;
  export let onSelectVector: (id: string | null) => void = () => {};
  let svgEl: SVGSVGElement;
  const width = 560;
  const height = 330;

  function draw() {
    if (!svgEl) return;
    const interaction = getIteration(log, selectedIteration);
    const data = interaction.composite_front;
    const membership = new Map<string, string>();
    for (const assignment of interaction.reference_vector_assignments) {
      for (const id of assignment.assigned_solution_ids) membership.set(id, assignment.vector_id);
    }
    const svg = d3.select(svgEl);
    svg.selectAll("*").remove();
    svg.attr("viewBox", `0 0 ${width} ${height}`);
    if (!data.length) return;
    const margin = { top: 16, right: 20, bottom: 43, left: 52 };
    const w = width - margin.left - margin.right;
    const h = height - margin.top - margin.bottom;
    const x = d3.scaleLinear().domain(d3.extent(data, d => d.objectives[xObjective]) as [number, number]).nice().range([0, w]);
    const y = d3.scaleLinear().domain(d3.extent(data, d => d.objectives[yObjective]) as [number, number]).nice().range([h, 0]);
    const group = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);
    group.append("g").attr("transform", `translate(0,${h})`).call(d3.axisBottom(x).ticks(6));
    group.append("g").call(d3.axisLeft(y).ticks(6));
    group.append("text").attr("x",w/2).attr("y",h+36).attr("text-anchor","middle").attr("font-size",12).text(`f${xObjective+1}`);
    group.append("text").attr("transform","rotate(-90)").attr("x",-h/2).attr("y",-39).attr("text-anchor","middle").attr("font-size",12).text(`f${yObjective+1}`);
    group.selectAll("circle.solution")
      .data(data).join("circle").attr("class","solution")
      .attr("cx",d=>x(d.objectives[xObjective])).attr("cy",d=>y(d.objectives[yObjective]))
      .attr("r",d=>selectedVector && membership.get(d.solution_id)===selectedVector ? 5.5 : 3.6)
      .attr("fill",d=>selectedVector && membership.get(d.solution_id)===selectedVector ? "#e11d48" : "#64748b")
      .attr("opacity",d=>!selectedVector || membership.get(d.solution_id)===selectedVector ? .9 : .12)
      .attr("stroke", "white").attr("stroke-width",.7)
      .style("cursor","pointer")
      .on("click", (_event,d) => onSelectVector(membership.get(d.solution_id) ?? null))
      .append("title").text(d=>`${d.solution_id}
Vector: ${membership.get(d.solution_id) ?? "none"}
${d.objectives.map((v,i)=>`f${i+1}=${v.toFixed(4)}`).join(" · ")}`);
  }
  onMount(draw);
  $: if (svgEl) draw();
</script>
<div class="plot-shell">
  <div class="axes">
    <label>Horizontal <select bind:value={xObjective}>{#each Array(log.problem.objectives) as _,i}<option value={i}>f{i+1}</option>{/each}</select></label>
    <label>Vertical <select bind:value={yObjective}>{#each Array(log.problem.objectives) as _,i}<option value={i}>f{i+1}</option>{/each}</select></label>
  </div>
  <svg bind:this={svgEl} aria-label="ADM composite-front objective projection"></svg>
  <p>End-of-interaction ADM front. Click a solution to select its assigned vector.</p>
</div>
<style>
 .plot-shell{min-width:0}svg{width:100%;height:auto}.axes{display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:.4rem}.axes label{font-size:.76rem;color:#475569}.axes select{margin-left:.3rem;padding:.2rem;border:1px solid #cbd5e1;border-radius:4px}p{font-size:.72rem;color:#64748b;margin:.25rem 0}
</style>
