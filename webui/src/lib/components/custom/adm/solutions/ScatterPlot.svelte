<script lang="ts">
  import { onMount } from "svelte";
  import * as d3 from "d3";
  import type { ADMLog } from "$lib/adm/types";
  import { getIteration } from "$lib/adm/adapters";

  export let log: ADMLog;
  export let selectedIteration: number;
  export let xObjective = 0;
  export let yObjective = 1;

  let svgEl: SVGSVGElement;
  const width = 460;
  const height = 320;

  function draw() {
    const iteration = getIteration(log, selectedIteration);
    const data = iteration.composite_front;

    const svg = d3.select(svgEl);
    svg.selectAll("*").remove();

    const margin = { top: 20, right: 20, bottom: 40, left: 45 };
    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    const x = d3.scaleLinear().domain([0, 1]).range([0, innerW]);
    const y = d3.scaleLinear().domain([0, 1]).range([innerH, 0]);
    const color = d3.scaleOrdinal(d3.schemeTableau10).domain(log.methods);

    const g = svg
      .attr("viewBox", `0 0 ${width} ${height}`)
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    g.append("g")
      .attr("transform", `translate(0,${innerH})`)
      .call(d3.axisBottom(x));

    g.append("g").call(d3.axisLeft(y));

    g.selectAll("circle")
      .data(data)
      .join("circle")
      .attr("cx", (d) => x(d.objectives[xObjective]))
      .attr("cy", (d) => y(d.objectives[yObjective]))
      .attr("r", 5)
      .attr("fill", (d) => color(d.method) as string)
      .attr("opacity", 0.8)
      .append("title")
      .text((d) => `${d.solution_id}\n${d.method}`);
  }

  onMount(draw);
  $: if (svgEl) draw();
</script>

<svg bind:this={svgEl}></svg>

<style>
  svg {
    width: 100%;
    height: auto;
  }
</style>